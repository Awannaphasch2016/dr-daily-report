#!/usr/bin/env python3
"""
Test LINE bot follow event handling
"""

import json
from unittest.mock import patch, MagicMock
from src.integrations.line_bot import LineBot

def test_line_follow():
    """Test LINE bot with a follow event"""
    print("=" * 80)
    print("?? Testing LINE Bot Follow Event")
    print("=" * 80)
    print()

    # Mock the agent to avoid requiring OpenAI API key
    with patch('src.line_bot.TickerAnalysisAgent'):
        # Initialize bot
        bot = LineBot()

        # Create simulated LINE webhook follow event
        event = {
            "events": [
                {
                    "type": "follow",
                    "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
                    "source": {
                        "userId": "U4af4980629...",
                        "type": "user"
                    },
                    "timestamp": 1462629479859
                }
            ]
        }

        body = json.dumps(event)
        signature = "test_signature"

        print("?? Simulated LINE Follow Event:")
        print(json.dumps(event, indent=2))
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
            print("?? Bot is processing follow event...")
            print()

            # Process the webhook
            result = bot.handle_webhook(body, signature)

            print("=" * 80)
            print("?? Bot Response (Welcome Message):")
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
                print("? No message was sent")

            print("=" * 80)
            print("?? Webhook Result:")
            print("=" * 80)
            print(json.dumps(result, indent=2))
            print()

            if result['statusCode'] == 200 and sent_messages:
                print("? Follow event test PASSED")
                print("? Welcome message sent successfully")
            else:
                print("? Follow event test FAILED")

        return result, sent_messages

def test_line_follow_direct():
    """Test handle_follow method directly"""
    print("=" * 80)
    print("?? Testing handle_follow Method Directly")
    print("=" * 80)
    print()

    # Mock the agent to avoid requiring OpenAI API key
    with patch('src.line_bot.TickerAnalysisAgent'):
        bot = LineBot()

        # Create follow event
        follow_event = {
            "type": "follow",
            "replyToken": "test_token",
            "source": {
                "userId": "U123456789",
                "type": "user"
            },
            "timestamp": 1462629479859
        }

        print("?? Follow Event:")
        print(json.dumps(follow_event, indent=2))
        print()

        # Call handle_follow directly
        welcome_message = bot.handle_follow(follow_event)

        print("=" * 80)
        print("?? Welcome Message:")
        print("=" * 80)
        print(welcome_message)
        print()

        if welcome_message and len(welcome_message) > 0 and "Daily Report Bot" in welcome_message:
            print("? handle_follow method works correctly")
        else:
            print("? handle_follow method failed")
            print(f"   Message length: {len(welcome_message) if welcome_message else 0}")

        return welcome_message

if __name__ == '__main__':
    print()
    print("=" * 80)
    print("?? LINE Bot Follow Event Tests")
    print("=" * 80)
    print()

    # Test handle_follow directly
    test_line_follow_direct()
    print()
    print()

    # Test full webhook flow
    test_line_follow()

    print()
    print("=" * 80)
    print("?? All tests completed!")
    print("=" * 80)