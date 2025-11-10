import json
import os
import hmac
import hashlib
import base64
import requests
from datetime import date
from src.agent import TickerAnalysisAgent
from src.ticker_matcher import TickerMatcher
from src.data_fetcher import DataFetcher
from src.database import TickerDatabase

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.agent = TickerAnalysisAgent()
        # Initialize ticker matcher with ticker map (load directly to ensure it's available)
        data_fetcher = DataFetcher()
        ticker_map = data_fetcher.load_tickers()
        self.ticker_matcher = TickerMatcher(ticker_map)
        # Initialize database for caching
        self.db = TickerDatabase()

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

    def get_help_message(self):
        """Get help/usage instructions message"""
        return """สวัสดีครับ! 👋

ยินดีต้อนรับสู่ Daily Report Bot 🤖

บอทนี้ช่วยวิเคราะห์ข้อมูลหุ้ DR และสร้างรายงานการวิเคราะห์ให้คุณ

📝 วิธีใช้งาน:
- ส่งชื่อ ticker ที่ต้องการวิเคราะห์ เช่น:
  • DBS19
  • UOB19
  • PFIZER19
  
บอทจะวิเคราะห์และส่งรายงานการวิเคราะห์ให้คุณทันที

มีคำถามเพิ่มเติม? ส่ง ticker มาลองใช้ดูได้เลยครับ! 🚀"""

    def get_error_message(self, ticker=None):
        """Get user-friendly error message"""
        if ticker:
            return f"""ขออภัยครับ 😔

ไม่สามารถวิเคราะห์ข้อมูลสำหรับ {ticker.upper()} ได้ในขณะนี้

กรุณาลองใหม่อีกครั้งในภายหลัง หรือลองส่ง ticker อื่น เช่น:
• DBS19
• UOB19
• PFIZER19

หากปัญหายังคงมีอยู่ กรุณาติดต่อทีมสนับสนุนครับ"""
        else:
            return """ขออภัยครับ 😔

เกิดข้อผิดพลาดในการประมวลผลคำขอของคุณ

กรุณาลองใหม่อีกครั้งในภายหลัง หรือส่ง "help" เพื่อดูวิธีใช้งาน

หากปัญหายังคงมีอยู่ กรุณาติดต่อทีมสนับสนุนครับ"""

    def handle_follow(self, event):
        """Handle follow event (when user adds bot as friend)"""
        event_type = event.get("type")

        if event_type != "follow":
            return None

        # Extract user information if available
        source = event.get("source", {})
        user_id = source.get("userId", "")

        # Return welcome message
        return self.get_help_message()

    def handle_message(self, event):
        """Handle incoming message"""
        try:
            message_type = event.get("type")

            if message_type != "message":
                return None

            message = event.get("message", {})
            if message.get("type") != "text":
                return "กรุณาส่งชื่อ ticker เป็นข้อความ"

            text = message.get("text", "").strip()
            text_lower = text.lower()

            # Check if it's a help command
            if text_lower == "help" or text_lower == "วิธีใช้" or text_lower == "ใช้งาน":
                return self.get_help_message()

            # Check if it's a ticker request
            if not text:
                return "กรุณาส่งชื่อ ticker เช่น DBS19, UOB19"

            # Use fuzzy matching to find best ticker match
            matched_ticker, suggestion = self.ticker_matcher.match_with_suggestion(text)
            
            # Check cache first (key: ticker + today's date)
            today = date.today().isoformat()
            cached_report = self.db.get_cached_report(matched_ticker, today)
            
            if cached_report:
                # Cache hit - return cached report
                print(f"✅ Cache hit for {matched_ticker} on {today}")
                
                # Prepend suggestion if available
                if suggestion:
                    return f"{suggestion}\n\n{cached_report}"
                
                return cached_report
            
            # Cache miss - generate new report
            print(f"❌ Cache miss for {matched_ticker} on {today}, generating new report...")
            
            try:
                report = self.agent.analyze_ticker(matched_ticker)
                
                # Check if report is None or empty
                if not report or not isinstance(report, str) or len(report.strip()) == 0:
                    return self.get_error_message(matched_ticker)
                
                # Save to cache for future use
                try:
                    self.db.save_report(matched_ticker, today, {
                        'report_text': report,
                        'context_json': None,
                        'technical_summary': None,
                        'fundamental_summary': None,
                        'sector_analysis': None
                    })
                    print(f"💾 Cached report for {matched_ticker} on {today}")
                except Exception as cache_error:
                    # Log cache error but don't fail the request
                    print(f"⚠️  Error caching report: {str(cache_error)}")
                
                # Prepend suggestion if available (suggestion already contains emoji)
                if suggestion:
                    return f"{suggestion}\n\n{report}"
                
                return report
            except Exception as e:
                # Log error for debugging but don't expose technical details to user
                print(f"Error analyzing ticker {matched_ticker}: {str(e)}")
                return self.get_error_message(matched_ticker)
        except Exception as e:
            # Catch any unexpected errors in message handling
            print(f"Error handling message: {str(e)}")
            return self.get_error_message()

    def handle_webhook(self, body, signature):
        """Handle LINE webhook"""
        # Verify signature
        if not self.verify_signature(body, signature):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Invalid signature"}, ensure_ascii=False)
            }

        # Parse body
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON"}, ensure_ascii=False)
            }

        # Process events
        events = data.get("events", [])
        responses = []

        for event in events:
            event_type = event.get("type")
            reply_token = event.get("replyToken")

            # Skip events without reply token (they don't need replies)
            if not reply_token:
                continue

            # Handle different event types with error handling
            response_text = None

            try:
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
            except Exception as e:
                # Catch any unexpected errors in event handling
                print(f"Error handling event type {event_type}: {str(e)}")
                response_text = self.get_error_message()

            # Always send a reply if we have response text and reply token
            # This ensures users always get a response even on errors
            if response_text and reply_token:
                # In test mode (test_signature), return the response text instead of sending to LINE API
                if signature == 'test_signature':
                    print(f"DEBUG: Test mode - response_text length: {len(response_text) if response_text else 0}")
                    print(f"response_text: {response_text }")
                    responses.append(response_text)
                else:
                    try:
                        self.reply_message(reply_token, response_text)
                    except Exception as e:
                        # If sending reply fails, log but don't fail the webhook
                        # LINE will retry if needed
                        print(f"Error sending reply message: {str(e)}")
            else:
                if signature == 'test_signature':
                    print(f"DEBUG: No response_text or reply_token. response_text={response_text}, reply_token={reply_token}")

        # Return response
        if signature == 'test_signature' and responses:
            # In test mode, return the actual response text
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "OK",
                    "responses": responses
                })
            }
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"})
        }
