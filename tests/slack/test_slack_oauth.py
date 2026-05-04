# -*- coding: utf-8 -*-
"""Tests for src.integrations.slack_oauth — OAuth install callback.

Module-load env vars are stubbed by `oauth_env` autouse fixture so import
succeeds. Slack API calls and Aurora writes are both mocked; no network or DB.
"""

import hashlib
import hmac
import importlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest


CLIENT_ID = "1234567890.987654"
CLIENT_SECRET = "test-client-secret"
SIGNING_SECRET = "abcdef0123456789abcdef0123456789"
REDIRECT_URI = "https://example.lambda-url.us-east-1.on.aws/slack/oauth/callback"


def _make_state(ts: int, secret: str = SIGNING_SECRET) -> str:
    sig = hmac.new(secret.encode("utf-8"), str(ts).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _make_event(query_string: str) -> dict:
    return {
        "rawQueryString": query_string,
        "requestContext": {"http": {"method": "GET", "path": "/slack/oauth/callback"}},
    }


@pytest.fixture(autouse=True)
def oauth_env():
    """Set required env vars and reload the module so module-level constants pick them up."""
    with patch.dict(
        "os.environ",
        {
            "SLACK_CLIENT_ID": CLIENT_ID,
            "SLACK_CLIENT_SECRET": CLIENT_SECRET,
            "SLACK_SIGNING_SECRET": SIGNING_SECRET,
            "SLACK_REDIRECT_URI": REDIRECT_URI,
            # Default fixture pins persist=true so happy-path tests assert the upsert is called.
            # The TestPersistFlag class overrides this for the dry-run case.
            "SLACK_INSTALL_PERSIST": "true",
        },
        clear=False,
    ):
        # Force re-import so module-level _required_env() reads the patched env
        import src.integrations.slack_oauth as mod
        importlib.reload(mod)
        yield mod


@pytest.fixture
def mock_repo():
    """Patch SlackInstallationsRepository so DB writes don't touch Aurora."""
    with patch("src.integrations.slack_oauth.SlackInstallationsRepository") as repo_cls:
        instance = MagicMock()
        repo_cls.return_value = instance
        yield instance


def _ok_slack_response() -> MagicMock:
    response = MagicMock()
    response.content = b"ok"
    response.json.return_value = {
        "ok": True,
        "access_token": "xoxb-fake-token-for-T0BETA",
        "team": {"id": "T0BETA", "name": "Beta LLC"},
        "bot_user_id": "U0BOT123",
        "scope": "app_mentions:read,chat:write",
    }
    return response


class TestStateValidation:
    def test_valid_fresh_state_accepted(self, oauth_env):
        state = _make_state(int(time.time()))
        assert oauth_env._verify_state(state) is True

    def test_tampered_state_rejected(self, oauth_env):
        state = f"{int(time.time())}.{'0' * 64}"
        assert oauth_env._verify_state(state) is False

    def test_state_signed_with_wrong_secret_rejected(self, oauth_env):
        state = _make_state(int(time.time()), secret="not-the-real-secret")
        assert oauth_env._verify_state(state) is False

    def test_expired_state_rejected(self, oauth_env):
        # 11 minutes old — beyond the 600s window
        state = _make_state(int(time.time()) - 660)
        assert oauth_env._verify_state(state) is False

    def test_missing_state_rejected(self, oauth_env):
        assert oauth_env._verify_state("") is False
        assert oauth_env._verify_state(None) is False  # type: ignore[arg-type]

    def test_malformed_state_rejected(self, oauth_env):
        assert oauth_env._verify_state("no-dot-here") is False
        assert oauth_env._verify_state("not-an-int.deadbeef") is False


class TestHandleOAuthCallback:
    def test_happy_path_persists_install_and_returns_200(self, oauth_env, mock_repo):
        state = _make_state(int(time.time()))
        event = _make_event(f"code=ABCD1234&state={state}")

        with patch(
            "src.integrations.slack_oauth.requests.post",
            return_value=_ok_slack_response(),
        ) as post:
            response = oauth_env.handle_oauth_callback(event)

        # Layer 1 — status code
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"].startswith("text/html")
        # Layer 2 — body content
        assert "Beta LLC" in response["body"]
        # Token must NEVER appear in user-facing HTML
        assert "xoxb-fake-token-for-T0BETA" not in response["body"]

        # Layer 4 — DB write happened with the right tuple
        mock_repo.upsert_installation.assert_called_once_with(
            team_id="T0BETA",
            team_name="Beta LLC",
            bot_token="xoxb-fake-token-for-T0BETA",
            bot_user_id="U0BOT123",
            scope="app_mentions:read,chat:write",
        )

        # The exchange POST went to oauth.v2.access with the right payload
        post.assert_called_once()
        kwargs = post.call_args.kwargs
        assert kwargs["data"]["client_id"] == CLIENT_ID
        assert kwargs["data"]["client_secret"] == CLIENT_SECRET
        assert kwargs["data"]["code"] == "ABCD1234"
        assert kwargs["data"]["redirect_uri"] == REDIRECT_URI

    def test_missing_code_returns_400_no_db_write(self, oauth_env, mock_repo):
        state = _make_state(int(time.time()))
        event = _make_event(f"state={state}")

        with patch("src.integrations.slack_oauth.requests.post") as post:
            response = oauth_env.handle_oauth_callback(event)

        assert response["statusCode"] == 400
        post.assert_not_called()
        mock_repo.upsert_installation.assert_not_called()

    def test_invalid_state_returns_400_no_exchange(self, oauth_env, mock_repo):
        event = _make_event("code=ABCD1234&state=tampered.deadbeef")

        with patch("src.integrations.slack_oauth.requests.post") as post:
            response = oauth_env.handle_oauth_callback(event)

        assert response["statusCode"] == 400
        post.assert_not_called()
        mock_repo.upsert_installation.assert_not_called()

    def test_slack_returns_ok_false_returns_502(self, oauth_env, mock_repo):
        state = _make_state(int(time.time()))
        event = _make_event(f"code=ABCD1234&state={state}")

        rejected = MagicMock()
        rejected.content = b"x"
        rejected.json.return_value = {"ok": False, "error": "invalid_code"}

        with patch("src.integrations.slack_oauth.requests.post", return_value=rejected):
            response = oauth_env.handle_oauth_callback(event)

        assert response["statusCode"] == 502
        # Internal Slack error code must NOT leak to user-facing HTML
        assert "invalid_code" not in response["body"]
        mock_repo.upsert_installation.assert_not_called()

    def test_slack_response_missing_team_returns_502(self, oauth_env, mock_repo):
        state = _make_state(int(time.time()))
        event = _make_event(f"code=ABCD1234&state={state}")

        partial = MagicMock()
        partial.content = b"x"
        partial.json.return_value = {"ok": True, "access_token": "xoxb-x"}  # missing team/etc.

        with patch("src.integrations.slack_oauth.requests.post", return_value=partial):
            response = oauth_env.handle_oauth_callback(event)

        assert response["statusCode"] == 502
        mock_repo.upsert_installation.assert_not_called()

    def test_transport_error_returns_502(self, oauth_env, mock_repo):
        import requests

        state = _make_state(int(time.time()))
        event = _make_event(f"code=ABCD1234&state={state}")

        with patch(
            "src.integrations.slack_oauth.requests.post",
            side_effect=requests.ConnectionError("boom"),
        ):
            response = oauth_env.handle_oauth_callback(event)

        assert response["statusCode"] == 502
        mock_repo.upsert_installation.assert_not_called()


class TestBuildInstallState:
    def test_state_round_trips(self, oauth_env):
        state = oauth_env.build_install_state()
        assert oauth_env._verify_state(state) is True

    def test_state_format(self, oauth_env):
        state = oauth_env.build_install_state()
        ts_str, sig = state.split(".", 1)
        assert ts_str.isdigit()
        assert len(sig) == 64  # sha256 hex


class TestPersistFlag:
    """SLACK_INSTALL_PERSIST=false skips the DB write but still returns 200.

    This is the "deploy without Aurora" mode used to ship the OAuth path before
    migration 041 is applied.
    """

    def test_persist_false_skips_upsert_and_returns_200(self, mock_repo, caplog):
        import importlib
        with patch.dict(
            "os.environ",
            {
                "SLACK_CLIENT_ID": CLIENT_ID,
                "SLACK_CLIENT_SECRET": CLIENT_SECRET,
                "SLACK_SIGNING_SECRET": SIGNING_SECRET,
                "SLACK_REDIRECT_URI": REDIRECT_URI,
                "SLACK_INSTALL_PERSIST": "false",
            },
            clear=False,
        ):
            import src.integrations.slack_oauth as mod
            importlib.reload(mod)

            state = _make_state(int(time.time()))
            event = _make_event(f"code=ABCD1234&state={state}")

            with patch(
                "src.integrations.slack_oauth.requests.post",
                return_value=_ok_slack_response(),
            ), caplog.at_level("WARNING", logger="src.integrations.slack_oauth"):
                response = mod.handle_oauth_callback(event)

        assert response["statusCode"] == 200
        # DB write must NOT have happened
        mock_repo.upsert_installation.assert_not_called()
        # Loud log must mention the team and the redacted token preview
        log_text = " ".join(r.message for r in caplog.records)
        assert "SLACK_INSTALL_PERSIST=false" in log_text
        assert "T0BETA" in log_text
        assert "Beta LLC" in log_text
        # Full token must NOT appear in the log line (redacted preview only)
        assert "xoxb-fake-token-for-T0BETA" not in log_text
