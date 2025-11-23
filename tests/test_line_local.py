#!/usr/bin/env python3
"""
Local test server for LINE bot integration
Run this with: python3 test_line_local.py
"""

from flask import Flask, request, jsonify
from src.integrations.line_bot import LineBot
import json

app = Flask(__name__)
bot = LineBot()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle LINE webhook"""
    # Get request body
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')

    print("=" * 80)
    print("📥 Received webhook request")
    print("=" * 80)
    print(f"Signature: {signature[:20]}...")
    print(f"Body: {body[:200]}...")
    print()

    # Handle webhook
    result = bot.handle_webhook(body, signature)

    print("=" * 80)
    print("📤 Response")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print()

    return jsonify(result), result['statusCode']

@app.route('/test', methods=['POST'])
def test():
    """Test endpoint with simulated LINE message"""
    ticker = request.json.get('ticker', 'DBS19')

    print("=" * 80)
    print(f"🧪 Testing with ticker: {ticker}")
    print("=" * 80)

    # Simulate LINE webhook event
    test_event = {
        "events": [
            {
                "type": "message",
                "replyToken": "test_reply_token_12345",
                "message": {
                    "type": "text",
                    "text": ticker
                },
                "source": {
                    "userId": "test_user_123"
                }
            }
        ]
    }

    body = json.dumps(test_event)

    # Test without signature (for local testing)
    result = bot.handle_webhook(body, 'test_signature')

    print("=" * 80)
    print("✅ Test completed")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print()

    return jsonify({
        "ticker": ticker,
        "result": result
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot": "LINE Bot for Financial Ticker Reports"
    })

def main():
    """Run the test server"""
    print("=" * 80)
    print("🚀 Starting LINE Bot Test Server")
    print("=" * 80)
    print()
    print("Endpoints:")
    print("  - POST /webhook      - LINE webhook (for real LINE requests)")
    print("  - POST /test         - Test endpoint (JSON: {\"ticker\": \"DBS19\"})")
    print("  - GET  /health       - Health check")
    print()
    print("=" * 80)
    print()

    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
