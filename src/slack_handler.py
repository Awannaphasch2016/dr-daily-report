# -*- coding: utf-8 -*-
"""
Slack Bot Lambda Handler

AWS Lambda handler for the Slack Events API webhook. Mirrors
`src.lambda_handler` (LINE bot). Reads a precomputed report from Aurora and
posts it back via Slack `chat.postMessage`.

Required env (validated at request time):
  - SLACK_BOT_TOKEN     (xoxb-…) for chat.postMessage
  - SLACK_SIGNING_SECRET for HMAC v0= verification

Other env reused from shared modules:
  - AURORA_HOST / AURORA_USER / AURORA_PASSWORD / AURORA_DATABASE / AURORA_PORT
  - PDF_STORAGE_BUCKET / PDF_BUCKET_NAME / PDF_URL_EXPIRATION_HOURS
  - OPENROUTER_API_KEY (imported by shared agent module at startup)
"""

import json
import logging
import os
from typing import Any, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point for the Slack Events API webhook."""
    request_id = getattr(context, "request_id", "unknown")
    logger.info(f"📥 Slack Bot Lambda invoked (request_id: {request_id})")

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
