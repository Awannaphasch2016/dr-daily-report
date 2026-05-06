# -*- coding: utf-8 -*-
"""
Slack Bot Lambda Handler

AWS Lambda handler for the Slack Events API webhook AND the OAuth v2 install
callback. Path-dispatches inside `lambda_handler` so a single Lambda + single
Function URL serves both surfaces.

Required env per surface:
  - Events path  (POST / or POST /slack/events):
      SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
  - OAuth path   (GET /slack/oauth/callback):
      SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_SIGNING_SECRET, SLACK_REDIRECT_URI
      (validated at module load by src.integrations.slack_oauth)

Other env reused from shared modules:
  - AURORA_HOST / AURORA_USER / AURORA_PASSWORD / AURORA_DATABASE / AURORA_PORT
  - PDF_STORAGE_BUCKET / PDF_BUCKET_NAME / PDF_URL_EXPIRATION_HOURS
  - OPENROUTER_API_KEY (imported by shared agent module at startup)
"""

import json
import logging
import os
import urllib.parse
from typing import Any, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point — dispatches by HTTP method + path."""
    request_id = getattr(context, "request_id", "unknown")

    method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "")
    path = (event.get("requestContext", {}).get("http", {}) or {}).get("path", "")
    logger.info(f"📥 Slack Lambda invoked (request_id={request_id} method={method} path={path})")

    # Install link — GET /slack/install. Mints fresh OAuth state per request and
    # 302-redirects to slack.com/oauth/v2/authorize. The shareable artifact is
    # this endpoint URL (never expires); the embedded `state` is < 1 s old at
    # click-time so the 10-min TTL in slack_oauth._verify_state never bites.
    if method == "GET" and path == "/slack/install":
        try:
            from src.integrations.slack_oauth import (
                CLIENT_ID,
                INSTALL_SCOPE,
                REDIRECT_URI,
                build_install_state,
            )
        except (ImportError, RuntimeError) as e:
            logger.error(f"❌ Failed to import slack_oauth for install redirect: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body": "<h1>Server misconfiguration</h1><p>Install endpoint unavailable.</p>",
            }

        authorize_url = "https://slack.com/oauth/v2/authorize?" + urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "scope": INSTALL_SCOPE,
            "redirect_uri": REDIRECT_URI,
            "state": build_install_state(),
        })
        logger.info(f"🔗 Minted Slack install redirect (scope={INSTALL_SCOPE})")
        return {
            "statusCode": 302,
            "headers": {
                "Location": authorize_url,
                "Cache-Control": "no-store",
            },
            "body": "",
        }

    # OAuth install callback path — GET /slack/oauth/callback (explicit match required)
    if method == "GET" and path == "/slack/oauth/callback":
        try:
            from src.integrations.slack_oauth import handle_oauth_callback
        except (ImportError, RuntimeError) as e:
            # RuntimeError fires when module-load env-var validation fails
            logger.error(f"❌ Failed to import slack_oauth module: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body": "<h1>Server misconfiguration</h1><p>OAuth handler unavailable.</p>",
            }

        try:
            return handle_oauth_callback(event)
        except Exception as e:
            logger.error(f"❌ Unexpected error in OAuth callback: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body": "<h1>Install failed</h1><p>Please try again later.</p>",
            }

    # Default → events/webhook path. This handles:
    #   - Function URL POST / (Slack Events API default Request URL)
    #   - Function URL POST /slack/events (alternative path)
    #   - AWS direct invoke (no requestContext, e.g. CI smoke test, console test)
    # The webhook itself does signature verification + url_verification handshake.
    try:
        from src.integrations.slack_bot import handle_webhook
        logger.info("✅ Slack bot handler imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import Slack bot handler: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": {"code": "IMPORT_ERROR", "message": "Failed to load Slack bot handler"}}),
        }

    required_vars = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
    missing_vars = [v for v in required_vars if not os.environ.get(v)]
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": {"code": "CONFIGURATION_ERROR", "message": "Server misconfiguration"}}),
        }

    try:
        response = handle_webhook(event)
        logger.info(f"📤 Slack Bot response: {response.get('statusCode', 'unknown')}")
        return response
    except Exception as e:
        logger.error(f"❌ Error handling Slack webhook: {e}", exc_info=True)
        # Ack 200 anyway — Slack retries on non-200, and a 500 won't help us recover
        return {"statusCode": 200, "body": ""}


if __name__ == "__main__":
    print("Slack Bot Lambda Handler")
    print("=" * 50)
    print("This module is intended for AWS Lambda deployment.")
    print("=" * 50)
