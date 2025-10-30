#!/usr/bin/env python3
"""
Test LINE integration end-to-end with mock reply
"""

import json
from unittest.mock import patch, MagicMock
from src.line_bot import LineBot

def test_line_integration(ticker):
    """Test LINE bot integration with mocked reply"""
    print("=" * 80)
    print(f"🧪 Testing LINE Integration: {ticker}")
    print("=" * 80)
    print()

    # Initialize bot
    bot = LineBot()

    # Create LINE webhook event
    event = {
        "events": [
            {
                "type": "message",
                "replyToken": "mock_reply_token_123",
                "source": {
                    "userId": "U123456789",
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
    signature = "test_signature"

    print("📨 LINE Webhook Event:")
    print(f"   User sends: '{ticker}'")
    print()

    # Mock the reply_message to capture what would be sent
    sent_messages = []

    def mock_reply(reply_token, text):
        sent_messages.append({
            "reply_token": reply_token,
            "text": text,
            "length": len(text)
        })
        return True

    # Patch the reply_message method
    with patch.object(bot, 'reply_message', side_effect=mock_reply):
        print("🤖 Bot is processing request...")
        print()

        # Process webhook
        result = bot.handle_webhook(body, signature)

        print("=" * 80)
        print("📤 Bot Response (what LINE would send to user):")
        print("=" * 80)
        print()

        if sent_messages:
            for i, msg in enumerate(sent_messages, 1):
                print(f"Message {i}:")
                print(f"Reply Token: {msg['reply_token']}")
                print(f"Length: {msg['length']} characters")
                print()
                print("Content:")
                print("-" * 80)
                print(msg['text'])
                print("-" * 80)
                print()
        else:
            print("❌ No message was sent")

        print("=" * 80)
        print("📊 Webhook Result:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        if result['statusCode'] == 200:
            print("✅ Integration test PASSED")
        else:
            print("❌ Integration test FAILED")

    return result, sent_messages

def main():
    """Run integration tests"""
    print()
    print("=" * 80)
    print("🚀 LINE Bot Integration Tests")
    print("=" * 80)
    print()

    # Test with valid ticker
    test_line_integration("DBS19")

    print()
    print("=" * 80)
    print("🎉 All tests completed!")
    print("=" * 80)

if __name__ == '__main__':
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'DBS19'
    test_line_integration(ticker)
