#!/usr/bin/env python3
"""
Production server for LINE bot
Run with: python3 run_server.py
"""

from flask import Flask, request, jsonify
from src.integrations.line_bot import LineBot
import json
import os

app = Flask(__name__)

# Initialize bot once at startup
print("🤖 Initializing LINE Bot...")
bot = LineBot()
print("✅ Bot initialized successfully")
print()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle LINE webhook"""
    # Get request body and signature
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')

    print("=" * 80)
    print("📥 Received LINE Webhook")
    print("=" * 80)
    print(f"Time: {request.headers.get('Date', 'N/A')}")
    print(f"Signature: {signature[:30]}..." if signature else "Signature: None")
    print(f"Body length: {len(body)} bytes")

    # Parse and show event
    try:
        data = json.loads(body)
        events = data.get("events", [])
        for event in events:
            msg = event.get("message", {})
            if msg.get("type") == "text":
                print(f"User message: '{msg.get('text')}'")
    except:
        pass

    print()

    # Handle webhook
    try:
        result = bot.handle_webhook(body, signature)

        print("=" * 80)
        print("📤 Response Status")
        print("=" * 80)
        print(f"Status Code: {result['statusCode']}")

        if result['statusCode'] == 200:
            print("✅ Successfully processed")
        else:
            print(f"⚠️  Issue: {result.get('body', 'Unknown error')}")

        print()

        return jsonify(json.loads(result['body'])), result['statusCode']

    except Exception as e:
        print("=" * 80)
        print("❌ Error Processing Webhook")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()

        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "LINE Bot Financial Ticker Report",
        "version": "1.0.0"
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "message": "LINE Bot Financial Ticker Report",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "health": "/health (GET)"
        }
    })

def main():
    """Run the server"""
    port = int(os.getenv('PORT', 5500))

    print("=" * 80)
    print("🚀 LINE Bot Server Starting")
    print("=" * 80)
    print()
    print(f"Port: {port}")
    print(f"Cloudflared tunnel: http://localhost:{port}")
    print()
    print("Endpoints:")
    print(f"  - POST http://localhost:{port}/webhook  (LINE webhook)")
    print(f"  - GET  http://localhost:{port}/health   (Health check)")
    print(f"  - GET  http://localhost:{port}/         (Info)")
    print()
    print("LINE Environment:")
    line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    line_secret = os.getenv("LINE_CHANNEL_SECRET")
    print(f"  - LINE_CHANNEL_ACCESS_TOKEN: {'✅ Set' if line_token else '❌ Missing'}")
    print(f"  - LINE_CHANNEL_SECRET: {'✅ Set' if line_secret else '❌ Missing'}")
    print()
    print("=" * 80)
    print("Ready to receive LINE messages!")
    print("=" * 80)
    print()

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,  # Set to False for production
        threaded=True
    )

if __name__ == '__main__':
    main()
