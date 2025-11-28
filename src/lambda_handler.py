# -*- coding: utf-8 -*-
"""
LINE Bot Lambda Handler

AWS Lambda handler for LINE Messaging API webhook.
Processes LINE webhook events and responds with ticker analysis reports.
"""

import os
import logging
import json
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for LINE Bot webhook

    Args:
        event: API Gateway/Lambda Function URL event
        context: Lambda context object

    Returns:
        Response dict with statusCode, headers, body

    Environment Variables:
        LINE_CHANNEL_ACCESS_TOKEN: LINE channel access token
        LINE_CHANNEL_SECRET: LINE channel secret
        OPENROUTER_API_KEY: OpenRouter API key
        PDF_STORAGE_BUCKET: S3 bucket for PDFs
    """
    # Log request
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'
    logger.info(f"📥 LINE Bot Lambda invoked (request_id: {request_id})")

    # Import LINE bot handler
    try:
        from src.integrations.line_bot import handle_webhook
        logger.info("✅ LINE bot handler imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import LINE bot handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'IMPORT_ERROR',
                    'message': 'Failed to load LINE bot handler'
                }
            })
        }

    # Validate environment variables
    required_vars = ['LINE_CHANNEL_ACCESS_TOKEN', 'LINE_CHANNEL_SECRET', 'OPENROUTER_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': {
                    'code': 'CONFIGURATION_ERROR',
                    'message': 'Server misconfiguration'
                }
            })
        }

    try:
        # Handle LINE webhook event
        response = handle_webhook(event)

        logger.info(f"📤 LINE Bot response: {response.get('statusCode', 'unknown')}")
        return response

    except Exception as e:
        logger.error(f"❌ Error handling LINE webhook: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An internal error occurred'
                }
            })
        }


# For local testing
if __name__ == "__main__":
    print("LINE Bot Lambda Handler")
    print("=" * 50)
    print("This module is intended for AWS Lambda deployment.")
    print("For local testing, use: just dev")
    print("=" * 50)
