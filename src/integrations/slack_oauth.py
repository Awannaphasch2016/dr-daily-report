# -*- coding: utf-8 -*-
"""Slack OAuth v2 install callback handler.

Handles the GET request Slack redirects to after a workspace admin clicks
"Allow" on the consent screen. Exchanges the one-time `code` for a
per-workspace `bot_token` and persists it in `slack_installations`.

Required env (validated at module load):
  - SLACK_CLIENT_ID        — public app id
  - SLACK_CLIENT_SECRET    — proves "I really am that bot" during code exchange
  - SLACK_SIGNING_SECRET   — reused as HMAC key for the OAuth `state` parameter
  - SLACK_REDIRECT_URI     — must EXACTLY match the URL registered in
                              the Slack app config (api.slack.com/apps → OAuth)

Generating an "Add to Slack" install URL (do this once on a landing page or
share as a link):

    https://slack.com/oauth/v2/authorize
      ?client_id=<SLACK_CLIENT_ID>
      &scope=app_mentions:read,chat:write
      &redirect_uri=<SLACK_REDIRECT_URI>
      &state=<HMAC_SIGNED_TIMESTAMP>      # see build_install_state()

See: https://api.slack.com/authentication/oauth-v2
"""

import hashlib
import hmac
import html
import logging
import os
import time
import urllib.parse
from typing import Any, Dict

import requests

from src.data.aurora.slack_installations_repository import SlackInstallationsRepository

logger = logging.getLogger(__name__)

SLACK_OAUTH_ACCESS_URL = "https://slack.com/api/oauth.v2.access"
STATE_MAX_AGE_SECONDS = 600  # 10 min — covers slow consent flow without leaving stale state usable


def _required_env(name: str) -> str:
    """Read env var at module load. Empty string is treated as missing."""
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(
            f"slack_oauth: required env var {name} is missing. "
            f"Set TF_VAR_{name} in Doppler and redeploy."
        )
    return value


# Module-level config: read once at import. Fails fast (Defensive Programming #1).
CLIENT_ID = _required_env("SLACK_CLIENT_ID")
CLIENT_SECRET = _required_env("SLACK_CLIENT_SECRET")
SIGNING_SECRET = _required_env("SLACK_SIGNING_SECRET").encode("utf-8")
REDIRECT_URI = _required_env("SLACK_REDIRECT_URI")

# Optional: gate Aurora write so the OAuth path can run before migration 041 is applied.
# Set to "false" to log the install record (token redacted) and skip the DB write.
# Defaults to true so production behavior is unchanged when the flag is unset.
PERSIST_INSTALLS = os.environ.get("SLACK_INSTALL_PERSIST", "true").strip().lower() in ("true", "1", "yes")

# Scopes requested when minting an install URL. Must match the scopes registered
# in the Slack app config (api.slack.com/apps → OAuth & Permissions → Bot Token
# Scopes); Slack rejects oauth.v2.access if you ask for a scope the app isn't
# granted. Used by the GET /slack/install redirect endpoint in slack_handler.py.
INSTALL_SCOPE = "app_mentions:read,chat:write"


def build_install_state() -> str:
    """Generate a stateless `state` parameter for the install URL.

    Format: `{ts}.{hmac_sha256(SIGNING_SECRET, ts)}`
    The receiving callback verifies the HMAC with the same secret, bounding
    requests to ones we minted. No server-side state needed.
    """
    ts = str(int(time.time()))
    sig = hmac.new(SIGNING_SECRET, ts.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _verify_state(state: str) -> bool:
    """Validate the HMAC-signed state nonce. Constant-time comparison."""
    if not state or "." not in state:
        return False
    try:
        ts_str, sig = state.split(".", 1)
        ts = int(ts_str)
    except (ValueError, AttributeError):
        return False

    if abs(time.time() - ts) > STATE_MAX_AGE_SECONDS:
        logger.warning(f"⚠️  Slack OAuth state expired (age={int(time.time()) - ts}s)")
        return False

    expected = hmac.new(SIGNING_SECRET, ts_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _exchange_code(code: str) -> Dict[str, Any]:
    """POST to oauth.v2.access. Returns the parsed JSON body.

    Raises requests.RequestException on transport error. The caller checks
    `response["ok"]` to detect Slack-level rejection.
    """
    response = requests.post(
        SLACK_OAUTH_ACCESS_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=10,
    )
    return response.json() if response.content else {}


def _html_ok(team_name: str) -> Dict[str, Any]:
    safe = html.escape(team_name)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": (
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Installed</title></head><body style='font-family:sans-serif;padding:40px;'>"
            f"<h1>✅ Installed in {safe}</h1>"
            f"<p>You can close this tab. Mention <code>@dr-daily-report</code> in any "
            f"channel where the bot is invited to get a daily ticker report.</p>"
            f"</body></html>"
        ),
    }


def _html_error(status_code: int, message: str) -> Dict[str, Any]:
    safe = html.escape(message)
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": (
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Install failed</title></head><body style='font-family:sans-serif;padding:40px;'>"
            f"<h1>❌ Install failed</h1>"
            f"<p>{safe}</p>"
            f"</body></html>"
        ),
    }


def handle_oauth_callback(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process Slack's OAuth redirect. Invoked by `slack_handler.lambda_handler`
    when method/path matches `GET /slack/oauth/callback`.

    Steps:
      1. Parse `code` and `state` from query string.
      2. Verify `state` HMAC (CSRF + freshness check).
      3. Exchange `code` for access_token + team metadata via Slack's API.
      4. UPSERT into slack_installations.
      5. Return a friendly HTML success page.

    On any error: log full context (NEVER the bot_token), return generic HTML
    error to browser. We never echo Slack's internal error codes downstream.
    """
    qs = event.get("rawQueryString") or ""
    params = {k: v[0] if v else "" for k, v in urllib.parse.parse_qs(qs).items()}
    code = params.get("code", "")
    state = params.get("state", "")

    if not code:
        logger.warning("⚠️  Slack OAuth callback missing 'code' query param")
        return _html_error(400, "Invalid install request — missing authorization code.")

    if not _verify_state(state):
        logger.warning("⚠️  Slack OAuth callback state invalid or expired")
        return _html_error(400, "Invalid install request — state validation failed.")

    try:
        body = _exchange_code(code)
    except requests.RequestException as e:
        logger.error(f"❌ Slack oauth.v2.access transport error: {e}")
        return _html_error(502, "Could not contact Slack to complete the install.")

    if not body.get("ok"):
        # Slack returned ok:false — log the error for ops, hide details from user.
        logger.error(f"❌ Slack oauth.v2.access rejected install: {body.get('error')}")
        return _html_error(502, "Slack rejected the install. Please try again.")

    try:
        team = body["team"]
        team_id = team["id"]
        team_name = team["name"]
        bot_token = body["access_token"]
        bot_user_id = body["bot_user_id"]
        scope = body["scope"]
    except KeyError as e:
        logger.error(f"❌ Slack oauth.v2.access response missing field: {e}")
        return _html_error(502, "Slack response was incomplete. Please try again.")

    if PERSIST_INSTALLS:
        repo = SlackInstallationsRepository()
        repo.upsert_installation(
            team_id=team_id,
            team_name=team_name,
            bot_token=bot_token,
            bot_user_id=bot_user_id,
            scope=scope,
        )
    else:
        # Loud Mock Pattern (#7): log every field we'd persist with bot_token redacted
        # so ops can verify the install path from CloudWatch even without Aurora.
        token_preview = f"{bot_token[:10]}…{bot_token[-4:]}" if len(bot_token) > 14 else "xoxb-***"
        logger.warning(
            "⚠️  SLACK_INSTALL_PERSIST=false — skipping DB write. "
            "Would have persisted: team_id=%s team_name=%s bot_user_id=%s scope=%s bot_token=%s",
            team_id, team_name, bot_user_id, scope, token_preview,
        )

    logger.info(f"🎉 Slack install complete: team={team_name} ({team_id}) scopes={scope}")
    return _html_ok(team_name)
