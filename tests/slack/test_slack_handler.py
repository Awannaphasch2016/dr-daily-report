# -*- coding: utf-8 -*-
"""
Tests for the Slack Bot integration.

Heavy dependencies (DataFetcher, PrecomputeService) are mocked in `mock_deps`.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest


SIGNING_SECRET = "abcdef0123456789abcdef0123456789"
BOT_TOKEN = "xoxb-test-token"


def _slack_sign(body: str, timestamp: str, secret: str = SIGNING_SECRET) -> str:
    base = f"v0:{timestamp}:{body}".encode("utf-8")
    return "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()


@pytest.fixture
def mock_deps():
    """Patch heavy dependencies that SlackBot.__init__ pulls in."""
    with patch("src.integrations.slack_bot.DataFetcher") as mock_fetcher, \
         patch("src.integrations.slack_bot.PrecomputeService") as mock_precompute, \
         patch.dict("os.environ", {
             "SLACK_BOT_TOKEN": BOT_TOKEN,
             "SLACK_SIGNING_SECRET": SIGNING_SECRET,
         }):
        fetcher_instance = MagicMock()
        fetcher_instance.load_tickers.return_value = {"AAPL": "AAPL", "DBS19": "D05.SI"}
        mock_fetcher.return_value = fetcher_instance

        precompute_instance = MagicMock()
        precompute_instance.get_cached_report.return_value = None
        mock_precompute.return_value = precompute_instance

        yield {"fetcher": mock_fetcher, "precompute": precompute_instance}


class TestSignatureVerification:
    def test_valid_signature_passes(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        ts = str(int(time.time()))
        body = '{"type":"event_callback"}'
        sig = _slack_sign(body, ts)
        assert bot.verify_signature(ts, body, sig) is True

    def test_tampered_signature_rejected(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        ts = str(int(time.time()))
        body = '{"type":"event_callback"}'
        bad = "v0=" + "0" * 64
        assert bot.verify_signature(ts, body, bad) is False

    def test_stale_timestamp_rejected(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        old_ts = str(int(time.time()) - 60 * 10)  # 10 min old
        body = '{"type":"event_callback"}'
        sig = _slack_sign(body, old_ts)
        assert bot.verify_signature(old_ts, body, sig) is False

    def test_missing_signature_rejected(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        ts = str(int(time.time()))
        assert bot.verify_signature(ts, "{}", "") is False

    def test_non_numeric_timestamp_rejected(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.verify_signature("not-a-number", "{}", "v0=deadbeef") is False


class TestTickerExtraction:
    def test_strips_mention_prefix(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.extract_ticker_from_mention("<@U0A8GQTREN7> AAPL") == "AAPL"

    def test_uppercases_lowercase_ticker(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.extract_ticker_from_mention("<@U0A8GQTREN7> aapl") == "AAPL"

    def test_first_token_only(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.extract_ticker_from_mention("<@U0A8GQTREN7> DBS19 please") == "DBS19"

    def test_mention_only_returns_empty(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.extract_ticker_from_mention("<@U0A8GQTREN7>") == ""

    def test_empty_text_returns_empty(self, mock_deps):
        from src.integrations.slack_bot import SlackBot
        bot = SlackBot()
        assert bot.extract_ticker_from_mention("") == ""


class TestUrlVerification:
    def test_url_verification_echoes_challenge(self, mock_deps):
        from src.integrations.slack_bot import handle_webhook
        body = json.dumps({"type": "url_verification", "challenge": "xyzzy"})
        event = {"headers": {}, "body": body}
        resp = handle_webhook(event)
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["challenge"] == "xyzzy"


class TestRetryHeader:
    def test_retry_header_acks_without_processing(self, mock_deps):
        from src.integrations.slack_bot import handle_webhook
        # No need for valid signature — handler should short-circuit on retry header
        event = {
            "headers": {"X-Slack-Retry-Num": "1", "X-Slack-Retry-Reason": "http_timeout"},
            "body": '{"type":"event_callback","event":{"type":"app_mention"}}',
        }
        resp = handle_webhook(event)
        assert resp["statusCode"] == 200
        # PrecomputeService.get_cached_report should NOT have been called
        mock_deps["precompute"].get_cached_report.assert_not_called()


class TestSignatureRejection:
    def test_event_callback_with_bad_sig_returns_401(self, mock_deps):
        from src.integrations.slack_bot import handle_webhook
        body = '{"type":"event_callback","event":{"type":"app_mention","channel":"C1","text":"<@U1> AAPL"}}'
        event = {
            "headers": {
                "X-Slack-Request-Timestamp": str(int(time.time())),
                "X-Slack-Signature": "v0=" + "0" * 64,
            },
            "body": body,
        }
        resp = handle_webhook(event)
        assert resp["statusCode"] == 401
        # Should not have queried Aurora or posted to Slack
        mock_deps["precompute"].get_cached_report.assert_not_called()


class TestAppMentionDispatch:
    def _make_event(self, body: str):
        ts = str(int(time.time()))
        sig = _slack_sign(body, ts)
        return {
            "headers": {
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": sig,
            },
            "body": body,
        }

    def test_cache_hit_posts_report_text(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        mock_deps["precompute"].get_cached_report.return_value = {
            "report_text": "AAPL is up today.",
            "pdf_presigned_url": "https://s3.example/aapl.pdf?sig=abc",
        }

        body = json.dumps({
            "type": "event_callback",
            "event": {"type": "app_mention", "channel": "C123", "text": "<@U1> AAPL"},
        })

        with patch.object(slack_mod.SlackBot, "post_message", return_value=True) as mock_post:
            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        mock_post.assert_called_once()
        args, _ = mock_post.call_args
        assert args[0] == "C123"
        assert "AAPL is up today." in args[1]
        assert "https://s3.example/aapl.pdf" in args[1]

    def test_cache_miss_posts_not_ready_message(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        mock_deps["precompute"].get_cached_report.return_value = None

        body = json.dumps({
            "type": "event_callback",
            "event": {"type": "app_mention", "channel": "C123", "text": "<@U1> ZZZZ99"},
        })

        with patch.object(slack_mod.SlackBot, "post_message", return_value=True) as mock_post:
            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        args, _ = mock_post.call_args
        assert args[0] == "C123"
        assert "isn't ready" in args[1]

    def test_mention_without_ticker_posts_help(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        body = json.dumps({
            "type": "event_callback",
            "event": {"type": "app_mention", "channel": "C123", "text": "<@U1>"},
        })

        with patch.object(slack_mod.SlackBot, "post_message", return_value=True) as mock_post:
            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        args, _ = mock_post.call_args
        assert "ticker" in args[1].lower()
        # Should not have hit Aurora when there's no ticker to look up
        mock_deps["precompute"].get_cached_report.assert_not_called()

    def test_non_app_mention_event_is_ignored(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        body = json.dumps({
            "type": "event_callback",
            "event": {"type": "message", "channel": "C123", "text": "hi"},
        })

        with patch.object(slack_mod.SlackBot, "post_message", return_value=True) as mock_post:
            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        mock_post.assert_not_called()


class TestPerWorkspaceTokenLookup:
    """Multi-tenant read path: bot_token comes from slack_installations keyed by
    team_id from the event envelope, with SLACK_BOT_TOKEN env as fallback so the
    original (un-backfilled) workspace keeps working during transition.
    """

    def _make_event(self, body: str):
        ts = str(int(time.time()))
        sig = _slack_sign(body, ts)
        return {
            "headers": {
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": sig,
            },
            "body": body,
        }

    def test_resolved_token_used_for_post_message(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        mock_deps["precompute"].get_cached_report.return_value = {
            "report_text": "AAPL is up.", "pdf_presigned_url": None,
        }

        body = json.dumps({
            "type": "event_callback",
            "team_id": "T_OTHER_WORKSPACE",
            "event": {"type": "app_mention", "channel": "C9", "text": "<@U1> AAPL"},
        })

        with patch(
            "src.data.aurora.slack_installations_repository.SlackInstallationsRepository"
        ) as repo_cls, patch(
            "src.integrations.slack_bot.requests.post"
        ) as mock_post:
            repo = MagicMock()
            repo.get_token_by_team_id.return_value = "xoxb-other-workspace-token"
            repo_cls.return_value = repo

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"{}"
            mock_resp.json.return_value = {"ok": True, "ts": "1.2"}
            mock_post.return_value = mock_resp

            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        repo.get_token_by_team_id.assert_called_once_with("T_OTHER_WORKSPACE")
        # post_message must have used the per-workspace token, not the env token
        _, post_kwargs = mock_post.call_args
        assert post_kwargs["headers"]["Authorization"] == "Bearer xoxb-other-workspace-token"

    def test_db_miss_falls_back_to_env_token(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        mock_deps["precompute"].get_cached_report.return_value = {
            "report_text": "AAPL is up.", "pdf_presigned_url": None,
        }

        body = json.dumps({
            "type": "event_callback",
            "team_id": "T_NEW_BUT_UNREGISTERED",
            "event": {"type": "app_mention", "channel": "C9", "text": "<@U1> AAPL"},
        })

        with patch(
            "src.data.aurora.slack_installations_repository.SlackInstallationsRepository"
        ) as repo_cls, patch(
            "src.integrations.slack_bot.requests.post"
        ) as mock_post:
            repo = MagicMock()
            repo.get_token_by_team_id.return_value = None  # not in DB
            repo_cls.return_value = repo

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"{}"
            mock_resp.json.return_value = {"ok": True, "ts": "1.2"}
            mock_post.return_value = mock_resp

            resp = slack_mod.handle_webhook(self._make_event(body))

        assert resp["statusCode"] == 200
        # Falls back to SLACK_BOT_TOKEN env (BOT_TOKEN constant from mock_deps)
        _, post_kwargs = mock_post.call_args
        assert post_kwargs["headers"]["Authorization"] == f"Bearer {BOT_TOKEN}"

    def test_db_error_falls_back_to_env_token(self, mock_deps):
        from src.integrations import slack_bot as slack_mod

        mock_deps["precompute"].get_cached_report.return_value = {
            "report_text": "AAPL is up.", "pdf_presigned_url": None,
        }

        body = json.dumps({
            "type": "event_callback",
            "team_id": "T_ANY",
            "event": {"type": "app_mention", "channel": "C9", "text": "<@U1> AAPL"},
        })

        with patch(
            "src.data.aurora.slack_installations_repository.SlackInstallationsRepository",
            side_effect=RuntimeError("aurora down"),
        ), patch(
            "src.integrations.slack_bot.requests.post"
        ) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"{}"
            mock_resp.json.return_value = {"ok": True, "ts": "1.2"}
            mock_post.return_value = mock_resp

            resp = slack_mod.handle_webhook(self._make_event(body))

        # DB hiccup must NOT take the bot down — fall back to env, ack 200.
        assert resp["statusCode"] == 200
        _, post_kwargs = mock_post.call_args
        assert post_kwargs["headers"]["Authorization"] == f"Bearer {BOT_TOKEN}"


class TestLambdaHandler:
    # Events arrive at the Lambda Function URL as POST / (Slack default) — the
    # path dispatcher in lambda_handler routes by method+path before delegating
    # to handle_webhook.
    _EVENTS_REQUEST_CONTEXT = {"requestContext": {"http": {"method": "POST", "path": "/"}}}

    def test_missing_env_returns_500(self, mock_deps):
        # Override env to drop required vars
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "", "SLACK_SIGNING_SECRET": ""}, clear=False):
            from src.slack_handler import lambda_handler
            ctx = MagicMock()
            ctx.request_id = "req-1"
            event = {"headers": {}, "body": "{}", **self._EVENTS_REQUEST_CONTEXT}
            resp = lambda_handler(event, ctx)
            assert resp["statusCode"] == 500
            assert "CONFIGURATION_ERROR" in resp["body"]

    def test_url_verification_passes_through(self, mock_deps):
        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-2"
        body = json.dumps({"type": "url_verification", "challenge": "abc123"})
        event = {"headers": {}, "body": body, **self._EVENTS_REQUEST_CONTEXT}
        resp = lambda_handler(event, ctx)
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["challenge"] == "abc123"

    def test_aws_direct_invoke_no_request_context_routes_to_webhook(self, mock_deps):
        # AWS direct invoke (e.g. CI smoke test) sends events with no requestContext.
        # Dispatch must default these to the webhook handler so url_verification works.
        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-3"
        body = json.dumps({"type": "url_verification", "challenge": "smoke"})
        event = {"headers": {}, "body": body}  # no requestContext
        resp = lambda_handler(event, ctx)
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["challenge"] == "smoke"


class TestInstallRedirect:
    """GET /slack/install mints a fresh OAuth state and 302-redirects to Slack.

    The shareable artifact for clients is `<lambda-fn-url>/slack/install`. The
    actual slack.com/oauth/v2/authorize URL (with the time-limited state) lives
    only inside the 302 response — clients never see or store it.
    """

    _CLIENT_ID = "1234567890.987654"
    _CLIENT_SECRET = "test-client-secret"
    _REDIRECT_URI = "https://example.lambda-url.us-east-1.on.aws/slack/oauth/callback"
    _INSTALL_REQUEST = {"requestContext": {"http": {"method": "GET", "path": "/slack/install"}}}

    @pytest.fixture(autouse=True)
    def oauth_env(self, mock_deps):
        """Stub OAuth env vars and reload slack_oauth so module-level constants pick them up.

        Mirrors the autouse fixture in test_slack_oauth.py — slack_oauth.py reads
        CLIENT_ID/CLIENT_SECRET/REDIRECT_URI at import via _required_env, so the
        module must be reloaded after env is patched. SLACK_SIGNING_SECRET is
        already patched by mock_deps.
        """
        import importlib
        with patch.dict(
            "os.environ",
            {
                "SLACK_CLIENT_ID": self._CLIENT_ID,
                "SLACK_CLIENT_SECRET": self._CLIENT_SECRET,
                "SLACK_REDIRECT_URI": self._REDIRECT_URI,
                "SLACK_INSTALL_PERSIST": "true",
            },
            clear=False,
        ):
            import src.integrations.slack_oauth as mod
            importlib.reload(mod)
            yield mod

    def _invoke_install(self):
        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-install"
        return lambda_handler({**self._INSTALL_REQUEST}, ctx)

    def test_returns_302(self):
        resp = self._invoke_install()
        assert resp["statusCode"] == 302

    def test_location_targets_slack_authorize_with_correct_params(self):
        from urllib.parse import parse_qs, urlparse

        resp = self._invoke_install()
        parsed = urlparse(resp["headers"]["Location"])

        assert parsed.scheme == "https"
        assert parsed.netloc == "slack.com"
        assert parsed.path == "/oauth/v2/authorize"

        params = parse_qs(parsed.query)
        assert params["client_id"] == [self._CLIENT_ID]
        assert params["redirect_uri"] == [self._REDIRECT_URI]
        assert params["scope"] == ["app_mentions:read,chat:write"]
        assert "state" in params

    def test_state_is_freshly_minted_per_request(self):
        """State carries a current timestamp + valid HMAC — proves it's minted at request time.

        Layer-2 evidence (Principle #2): we don't trust that the handler called
        build_install_state(); we verify the value's structure and that the
        timestamp is bounded by wall-clock 'now'.
        """
        import time
        from urllib.parse import parse_qs, urlparse

        before = int(time.time())
        resp = self._invoke_install()
        after = int(time.time())

        state = parse_qs(urlparse(resp["headers"]["Location"]).query)["state"][0]
        ts_str, hex_sig = state.split(".", 1)
        assert before <= int(ts_str) <= after
        assert len(hex_sig) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in hex_sig)

    def test_response_is_uncacheable(self):
        """Cache-Control: no-store — proxies/CDNs must never cache a state value."""
        resp = self._invoke_install()
        assert resp["headers"].get("Cache-Control") == "no-store"

    def test_post_to_install_path_falls_through_to_webhook(self):
        """Only the exact (GET, /slack/install) tuple triggers the redirect."""
        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-install-post"
        event = {
            "headers": {},
            "body": json.dumps({"type": "url_verification", "challenge": "fallthrough"}),
            "requestContext": {"http": {"method": "POST", "path": "/slack/install"}},
        }
        resp = lambda_handler(event, ctx)
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["challenge"] == "fallthrough"

    def test_misconfigured_oauth_module_returns_500(self):
        """If slack_oauth fails to import (e.g. missing env), respond 500 — don't crash silently."""
        import builtins
        original_import = builtins.__import__

        def _failing_import(name, *args, **kwargs):
            if name == "src.integrations.slack_oauth":
                raise RuntimeError("simulated _required_env failure")
            return original_import(name, *args, **kwargs)

        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-install-broken"
        with patch("builtins.__import__", side_effect=_failing_import):
            resp = lambda_handler({**self._INSTALL_REQUEST}, ctx)
        assert resp["statusCode"] == 500
        assert "misconfiguration" in resp["body"].lower()
