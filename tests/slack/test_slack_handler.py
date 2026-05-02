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


class TestLambdaHandler:
    def test_missing_env_returns_500(self, mock_deps):
        # Override env to drop required vars
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "", "SLACK_SIGNING_SECRET": ""}, clear=False):
            from src.slack_handler import lambda_handler
            ctx = MagicMock()
            ctx.request_id = "req-1"
            resp = lambda_handler({"headers": {}, "body": "{}"}, ctx)
            assert resp["statusCode"] == 500
            assert "CONFIGURATION_ERROR" in resp["body"]

    def test_url_verification_passes_through(self, mock_deps):
        from src.slack_handler import lambda_handler
        ctx = MagicMock()
        ctx.request_id = "req-2"
        body = json.dumps({"type": "url_verification", "challenge": "abc123"})
        resp = lambda_handler({"headers": {}, "body": body}, ctx)
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["challenge"] == "abc123"
