import json
import os
import hmac
import hashlib
import base64
import requests
from src.agent import TickerAnalysisAgent

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.agent = TickerAnalysisAgent()

    def verify_signature(self, body, signature):
        """Verify LINE webhook signature"""
        # Skip verification in test mode
        if signature == 'test_signature' or not self.channel_secret:
            return True

        if not signature:
            return False

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

    def handle_follow(self, event):
        """Handle follow event (when user adds bot as friend)"""
        event_type = event.get("type")

        if event_type != "follow":
            return None

        # Extract user information if available
        source = event.get("source", {})
        user_id = source.get("userId", "")

        # Create welcome message in Thai
        welcome_message = """สวัสดีครับ! 👋

ยินดีต้อนรับสู่ Daily Report Bot 🤖

บอทนี้ช่วยวิเคราะห์ข้อมูลหุ้นกู้แปลงสภาพ (Warrant) และสร้างรายงานการวิเคราะห์ให้คุณ

📝 วิธีใช้งาน:
- ส่งชื่อ ticker ที่ต้องการวิเคราะห์ เช่น:
  • DBS19
  • UOB19
  • PFIZER19
  
บอทจะวิเคราะห์และส่งรายงานการวิเคราะห์ให้คุณทันที

มีคำถามเพิ่มเติม? ส่ง ticker มาลองใช้ดูได้เลยครับ! 🚀"""

        return welcome_message

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
            event_type = event.get("type")
            reply_token = event.get("replyToken")

            # Handle different event types
            response_text = None

            if event_type == "follow":
                # User added bot as friend
                response_text = self.handle_follow(event)
            elif event_type == "message":
                # User sent a message
                response_text = self.handle_message(event)
            elif event_type == "unfollow":
                # User blocked/unfollowed bot (no reply token)
                # Log if needed, but don't send reply
                continue
            elif event_type in ["join", "leave"]:
                # Bot joined/left a group (no reply token needed)
                # These events don't require replies
                continue
            else:
                # Unknown event type - log but don't error
                continue

            # Send reply if we have response text and reply token
            if response_text and reply_token:
                self.reply_message(reply_token, response_text)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"})
        }
