import json
import os
import hmac
import hashlib
import base64
import requests
from agent import TickerAnalysisAgent

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.agent = TickerAnalysisAgent()

    def verify_signature(self, body, signature):
        """Verify LINE webhook signature"""
        if not self.channel_secret:
            return True  # Skip verification in development

        hash_digest = hmac.new(
            self.channel_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()

        computed_signature = base64.b64encode(hash_digest).decode('utf-8')
        return hmac.compare_digest(signature, computed_signature)

    def reply_message(self, reply_token, text):
        """Send reply message via LINE Messaging API"""
        url = "https://api.line.me/v2/bot/message/reply"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }

        # Split long messages into chunks (LINE limit is 5000 characters)
        max_length = 4500
        messages = []

        if len(text) > max_length:
            # Split into chunks
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            messages = [{"type": "text", "text": chunk} for chunk in chunks[:5]]  # Max 5 messages
        else:
            messages = [{"type": "text", "text": text}]

        data = {
            "replyToken": reply_token,
            "messages": messages
        }

        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200

    def handle_message(self, event):
        """Handle incoming message"""
        message_type = event.get("type")

        if message_type != "message":
            return None

        message = event.get("message", {})
        if message.get("type") != "text":
            return "กรุณาส่งชื่อ ticker เป็นข้อความ"

        text = message.get("text", "").strip()

        # Check if it's a ticker request
        if not text:
            return "กรุณาส่งชื่อ ticker เช่น DBS19, UOB19"

        # Show processing message
        processing_msg = f"🔍 กำลังวิเคราะห์ {text.upper()}...\nโปรดรอสักครู่"

        # Generate report
        report = self.agent.analyze_ticker(text)

        return report

    def handle_webhook(self, body, signature):
        """Handle LINE webhook"""
        # Verify signature
        if not self.verify_signature(body, signature):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Invalid signature"})
            }

        # Parse body
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON"})
            }

        # Process events
        events = data.get("events", [])

        for event in events:
            reply_token = event.get("replyToken")

            if not reply_token:
                continue

            # Handle message
            response_text = self.handle_message(event)

            if response_text:
                self.reply_message(reply_token, response_text)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"})
        }
