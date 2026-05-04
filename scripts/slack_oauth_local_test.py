#!/usr/bin/env python3
"""
Local OAuth callback harness — exercises src/integrations/slack_oauth.py without
deploying Lambda or applying Aurora migration 041.

Two modes:
  --print-install-url  Mint a signed install URL using current SLACK_* env vars
  (default: server)    Run a local HTTP server that handles GET /slack/oauth/callback

The server monkey-patches SlackInstallationsRepository BEFORE handle_oauth_callback
is invoked, so the install path runs end-to-end (state verify → oauth.v2.access →
"DB write") with the upsert call captured in-memory and printed loudly.

Setup:
  1. Start ngrok:    ngrok http 8765
  2. Update SLACK_REDIRECT_URI to <ngrok-url>/slack/oauth/callback (env override
     or doppler secrets set), and register the same URL at api.slack.com/apps
     → OAuth & Permissions → Redirect URLs.
  3. Run server:     doppler run --project rag-chatbot-worktree --config dev \\
                       -- python scripts/slack_oauth_local_test.py
  4. Mint URL:       doppler run --project rag-chatbot-worktree --config dev \\
                       -- python scripts/slack_oauth_local_test.py --print-install-url
  5. Paste URL in browser → Allow on a test workspace → server logs the install.
"""

import argparse
import logging
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# Ensure `src.*` is importable regardless of cwd.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_PORT = 8765
DEFAULT_SCOPE = "app_mentions:read,chat:write"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("slack_oauth_local_test")


class _MockRepo:
    """Loud in-memory replacement for SlackInstallationsRepository.

    Per Tier-0 Principle #7 (Loud Mock Pattern): every call is logged with
    bot_token redacted; the captured tuples are printed at the end so the test
    operator sees exactly what would have been written to Aurora.
    """

    captured: list = []

    def upsert_installation(
        self,
        team_id: str,
        team_name: str,
        bot_token: str,
        bot_user_id: str,
        scope: str,
    ) -> None:
        redacted = f"{bot_token[:10]}…{bot_token[-4:]}" if len(bot_token) > 14 else "xoxb-***"
        record = {
            "team_id": team_id,
            "team_name": team_name,
            "bot_token_preview": redacted,
            "bot_user_id": bot_user_id,
            "scope": scope,
        }
        type(self).captured.append(record)
        logger.info("=" * 60)
        logger.info("MOCK upsert_installation called (would write to Aurora):")
        for k, v in record.items():
            logger.info("  %s = %s", k, v)
        logger.info("=" * 60)

    def get_token_by_team_id(self, team_id: str):
        for record in type(self).captured:
            if record["team_id"] == team_id:
                return "<bot_token-redacted>"
        return None


def _patch_repo():
    """Replace the repository inside slack_oauth before any callback runs."""
    from src.integrations import slack_oauth

    slack_oauth.SlackInstallationsRepository = _MockRepo
    logger.info("Patched slack_oauth.SlackInstallationsRepository → _MockRepo")
    return slack_oauth


class _CallbackHandler(BaseHTTPRequestHandler):
    slack_oauth = None  # Injected by run_server before serving.

    def log_message(self, fmt, *args):  # quiet default access log; we have our own
        logger.debug("%s - %s", self.address_string(), fmt % args)

    def do_GET(self):  # noqa: N802  (BaseHTTPRequestHandler API)
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/slack/oauth/callback":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found\n")
            return

        logger.info(">>> GET %s", self.path)
        event = {
            "rawQueryString": parsed.query,
            "requestContext": {"http": {"method": "GET", "path": parsed.path}},
        }
        try:
            response = type(self).slack_oauth.handle_oauth_callback(event)
        except Exception:
            logger.exception("handle_oauth_callback raised")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Internal error (see server logs)\n")
            return

        status = response.get("statusCode", 500)
        headers = response.get("headers", {})
        body = response.get("body", "")
        logger.info("<<< %s (body=%d bytes)", status, len(body))

        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body.encode("utf-8") if isinstance(body, str) else body)


def run_server(port: int) -> None:
    slack_oauth = _patch_repo()
    _CallbackHandler.slack_oauth = slack_oauth

    logger.info("CLIENT_ID      = %s", slack_oauth.CLIENT_ID)
    logger.info("REDIRECT_URI   = %s", slack_oauth.REDIRECT_URI)
    logger.info("Listening on http://127.0.0.1:%d  (route ngrok here)", port)
    logger.info("Waiting for GET /slack/oauth/callback ...")

    httpd = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down. Captured installs: %d", len(_MockRepo.captured))
        for record in _MockRepo.captured:
            logger.info("  %s", record)


def print_install_url(scope: str) -> None:
    from src.integrations import slack_oauth

    state = slack_oauth.build_install_state()
    params = {
        "client_id": slack_oauth.CLIENT_ID,
        "scope": scope,
        "redirect_uri": slack_oauth.REDIRECT_URI,
        "state": state,
    }
    url = "https://slack.com/oauth/v2/authorize?" + urllib.parse.urlencode(params)
    logger.info("Install URL (paste in a browser logged into your test workspace):")
    print(url)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print-install-url", action="store_true", help="Print a signed install URL and exit")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default {DEFAULT_PORT})")
    ap.add_argument("--scope", default=DEFAULT_SCOPE, help=f"OAuth scope string (default {DEFAULT_SCOPE!r})")
    args = ap.parse_args()

    if args.print_install_url:
        print_install_url(args.scope)
        return 0

    run_server(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
