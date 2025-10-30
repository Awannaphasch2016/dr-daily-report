#!/usr/bin/env python3
"""
Simple test to simulate LINE message without running a server
"""

import json
from src.line_bot import LineBot

def test_line_message(ticker):
    """Test LINE bot with a ticker message"""
    print("=" * 80)
    print(f"🧪 Testing LINE Bot with ticker: {ticker}")
    print("=" * 80)
    print()

    # Initialize bot
    bot = LineBot()

    # Create simulated LINE webhook event
    event = {
        "events": [
            {
                "type": "message",
                "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
                "source": {
                    "userId": "U4af4980629...",
                    "type": "user"
                },
                "timestamp": 1462629479859,
                "message": {
                    "type": "text",
                    "id": "325708",
                    "text": ticker
                }
            }
        ]
    }

    body = json.dumps(event)

    # For testing, we'll skip signature verification
    # In production, LINE will send proper signature
    signature = "test_signature"

    print("📨 Simulated LINE Event:")
    print(json.dumps(event, indent=2))
    print()
    print("=" * 80)
    print()

    # Process the webhook
    print("🤖 Bot is processing...")
    print()

    result = bot.handle_webhook(body, signature)

    print("=" * 80)
    print("📊 Result:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print()

    return result

def main():
    """Run tests"""
    # Test with different tickers
    test_tickers = ['DBS19', 'HONDA19', 'INVALID_TICKER']

    for ticker in test_tickers:
        result = test_line_message(ticker)

        if result['statusCode'] == 200:
            print(f"✅ {ticker} - Success")
        else:
            print(f"❌ {ticker} - Failed")

        print()
        print()

if __name__ == '__main__':
    # Quick test with one ticker
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'DBS19'
    test_line_message(ticker)
