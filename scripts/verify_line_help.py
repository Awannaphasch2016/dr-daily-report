#!/usr/bin/env python3
"""
Verify LINE bot help command handling.

Usage: python scripts/verify_line_help.py
"""

import json
from unittest.mock import patch
from src.integrations.line_bot import LineBot

def test_help_command():
    """Test LINE bot with help command"""
    print("=" * 80)
    print("?? Testing LINE Bot Help Command")
    print("=" * 80)
    print()

    # Mock the agent to avoid requiring OpenAI API key
    with patch('src.line_bot.TickerAnalysisAgent'):
        # Initialize bot
        bot = LineBot()

        # Test different help command variations
        help_commands = ["help", "HELP", "Help", "???????", "??????"]

        for help_cmd in help_commands:
            print(f"Testing command: '{help_cmd}'")
            print("-" * 80)

            # Create simulated LINE webhook event
            event = {
                "events": [
                    {
                        "type": "message",
                        "replyToken": "test_reply_token_123",
                        "source": {
                            "userId": "U123456789",
                            "type": "user"
                        },
                        "timestamp": 1462629479859,
                        "message": {
                            "type": "text",
                            "id": "325708",
                            "text": help_cmd
                        }
                    }
                ]
            }

            body = json.dumps(event)
            signature = "test_signature"

            # Mock the reply_message to capture what would be sent
            sent_messages = []

            def mock_reply(reply_token, text):
                sent_messages.append({
                    "reply_token": reply_token,
                    "text": text,
                    "length": len(str(text)) if text else 0
                })
                return True

            # Patch the reply_message method
            with patch.object(bot, 'reply_message', side_effect=mock_reply):
                # Process the webhook
                result = bot.handle_webhook(body, signature)

                if sent_messages:
                    help_text = sent_messages[0]['text']
                    text_length = len(str(help_text))
                    print(f"? Success! Message sent ({text_length} chars)")
                    
                    # Check if it's actually the help message
                    if isinstance(help_text, str) and text_length > 200:
                        if "Daily Report Bot" in help_text or "????????????" in help_text:
                            print(f"? Verified: Help message returned correctly")
                            print(f"   Preview: {help_text[:80]}...")
                        else:
                            print(f"??  Message sent but content unclear")
                            print(f"   Preview: {help_text[:80]}...")
                    else:
                        print(f"? Unexpected response type or length")
                        print(f"   Type: {type(help_text)}")
                        print(f"   Content: {str(help_text)[:100]}")
                else:
                    print("? Failed! No message was sent")

                if result['statusCode'] != 200:
                    print(f"??  Webhook status: {result['statusCode']}")

            print()
            print()

def test_help_message_direct():
    """Test get_help_message method directly"""
    print("=" * 80)
    print("?? Testing get_help_message Method Directly")
    print("=" * 80)
    print()

    # Mock the agent to avoid requiring OpenAI API key
    with patch('src.line_bot.TickerAnalysisAgent'):
        bot = LineBot()

        # Get help message directly
        help_message = bot.get_help_message()

        print("Help Message:")
        print("=" * 80)
        print(help_message)
        print("=" * 80)
        print()

        if help_message and len(help_message) > 0:
            has_bot_name = "Daily Report Bot" in help_message
            has_instructions = "DBS19" in help_message or "???????" in help_message
            if has_bot_name and has_instructions:
                print("? get_help_message method works correctly")
                print(f"   Message length: {len(help_message)} characters")
                print(f"   Contains: 'Daily Report Bot' ?")
                print(f"   Contains usage instructions ?")
            else:
                print("? Help message missing required content")
                print(f"   Has bot name: {has_bot_name}")
                print(f"   Has instructions: {has_instructions}")
        else:
            print("? Help message is empty")

        return help_message

if __name__ == '__main__':
    print()
    print("=" * 80)
    print("?? LINE Bot Help Command Tests")
    print("=" * 80)
    print()

    # Test get_help_message directly
    test_help_message_direct()
    print()
    print()

    # Test help command through webhook
    test_help_command()

    print()
    print("=" * 80)
    print("?? All tests completed!")
    print("=" * 80)