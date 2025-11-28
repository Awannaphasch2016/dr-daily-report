# -*- coding: utf-8 -*-
"""
Telegram Mini App Lambda Handler

AWS Lambda handler for Telegram Mini App REST API.
Uses Mangum to adapt FastAPI application for Lambda/API Gateway.
"""

import os
import logging
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastAPI app
try:
    from src.api.app import app as fastapi_app
    logger.info("✅ FastAPI app imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import FastAPI app: {e}")
    raise

# Import Mangum adapter
try:
    from mangum import Mangum
    logger.info("✅ Mangum adapter imported successfully")
except ImportError:
    logger.error("❌ Mangum not installed. Install with: pip install mangum")
    raise ImportError(
        "Mangum is required for Lambda deployment. "
        "Add 'mangum>=0.17.0' to requirements.txt"
    )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Telegram Mini App API

    This function is invoked by API Gateway and routes requests to FastAPI.

    Args:
        event: API Gateway event (HTTP request data)
        context: Lambda context object

    Returns:
        API Gateway response (HTTP response data)

    Environment Variables:
        OPENROUTER_API_KEY: OpenRouter API key
        TELEGRAM_BOT_TOKEN: Telegram Bot Token
        TELEGRAM_APP_ID: Telegram App ID
        TELEGRAM_APP_HASH: Telegram App Hash
        DYNAMODB_WATCHLIST_TABLE: DynamoDB watchlist table name
        DYNAMODB_CACHE_TABLE: DynamoDB cache table name
        PDF_STORAGE_BUCKET: S3 bucket for PDF storage
        ENVIRONMENT: dev | staging | prod
        LOG_LEVEL: DEBUG | INFO | WARNING | ERROR
    """
    # Log request details
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'

    # Extract path and method for logging
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 'UNKNOWN')
    path = event.get('requestContext', {}).get('http', {}).get('path', '/')

    logger.info(f"📥 Lambda invoked: {http_method} {path} (request_id: {request_id})")

    # Environment info
    environment = os.environ.get('ENVIRONMENT', 'unknown')
    logger.info(f"🌍 Environment: {environment}")

    # Validate required environment variables
    required_vars = [
        'OPENROUTER_API_KEY',
        'DYNAMODB_WATCHLIST_TABLE',
        'DYNAMODB_CACHE_TABLE',
        'PDF_STORAGE_BUCKET'
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"error": {"code": "CONFIGURATION_ERROR", "message": "Server misconfiguration"}}'
        }

    # Create Mangum handler (cached across invocations)
    if not hasattr(handler, '_mangum_handler'):
        logger.info("🔧 Creating Mangum handler (cold start)")
        handler._mangum_handler = Mangum(
            fastapi_app,
            lifespan="off",  # Disable lifespan for Lambda
            api_gateway_base_path="/"  # API Gateway routes already include /api/v1
        )
        logger.info("✅ Mangum handler created")

    try:
        # Route request through Mangum to FastAPI
        response = handler._mangum_handler(event, context)

        # Log response
        status_code = response.get('statusCode', 'unknown')
        logger.info(f"📤 Response: {status_code} for {http_method} {path}")

        return response

    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': '{"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred"}}'
        }


# For local testing
if __name__ == "__main__":
    print("Telegram Lambda Handler")
    print("=" * 50)
    print("This module is intended for AWS Lambda deployment.")
    print("For local testing, use: just dev-api")
    print("=" * 50)
