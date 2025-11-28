import json
import os
import logging

# Load heavy dependencies from S3 before importing modules that need them
from src.utils.dependency_loader import load_heavy_dependencies
load_heavy_dependencies()

from src.integrations.line_bot import LineBot

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize bot (cold start optimization)
bot = None

def get_bot():
    """Get or create bot instance"""
    global bot
    if bot is None:
        bot = LineBot()
    return bot

def lambda_handler(event, context):
    """
    AWS Lambda handler for LINE bot webhook

    Expected environment variables:
    - OPENROUTER_API_KEY: OpenRouter API key
    - LINE_CHANNEL_ACCESS_TOKEN: LINE channel access token
    - LINE_CHANNEL_SECRET: LINE channel secret
    """

    # Get bot instance
    line_bot = get_bot()

    # Get request body and signature
    body = event.get('body', '')
    signature = event.get('headers', {}).get('x-line-signature', '')

    # Handle webhook
    try:
        result = line_bot.handle_webhook(body, signature)
        return result
    except Exception as e:
        print(f"Error handling webhook: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

def test_handler():
    """Test handler locally"""
    # Load test event
    test_event = {
        "body": json.dumps({
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_token",
                    "message": {
                        "type": "text",
                        "text": "DBS19"
                    }
                }
            ]
        }),
        "headers": {
            "x-line-signature": "test_signature"
        }
    }

    # Test
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    # For local testing
    test_handler()
