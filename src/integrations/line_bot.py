# -*- coding: utf-8 -*-
import json
import os
import hmac
import hashlib
import base64
import requests
import logging
import boto3
from datetime import date
from src.agent import TickerAnalysisAgent
from src.data.ticker_matcher import TickerMatcher
from src.data.data_fetcher import DataFetcher
from src.data.aurora.precompute_service import PrecomputeService
from src.formatters.pdf_storage import PDFStorage

logger = logging.getLogger(__name__)
# AWS Lambda pre-configures root logger at WARNING. Explicitly set INFO for this module.
logger.setLevel(logging.INFO)

# Beta testing configuration
# BETA_USER_LIMIT: 0 = unlimited, N = limit to N users (next N, not total)
BETA_USER_LIMIT = int(os.getenv("BETA_USER_LIMIT", "0"))
BETA_USERS_S3_KEY = "beta-users.json"

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.agent = TickerAnalysisAgent()
        # Initialize ticker matcher with ticker map (load directly to ensure it's available)
        data_fetcher = DataFetcher()
        ticker_map = data_fetcher.load_tickers()
        self.ticker_matcher = TickerMatcher(ticker_map)

        # Initialize Aurora precompute service (single source of truth for caching)
        self.precompute = PrecomputeService()
        logger.info("✅ Aurora precompute service initialized")

        # Initialize PDF storage (gracefully handle if S3 not available)
        try:
            self.pdf_storage = PDFStorage()
            if self.pdf_storage.is_available():
                logger.info("PDF storage initialized and available")
            else:
                logger.debug("PDF storage initialized but S3 not available (likely local env)")
        except Exception as e:
            logger.warning(f"Failed to initialize PDF storage: {e}")
            self.pdf_storage = None

        # Initialize beta user management (S3-based persistence)
        self.beta_bucket = os.getenv("PDF_BUCKET_NAME")
        self.beta_enabled = bool(self.beta_bucket)
        if self.beta_enabled:
            try:
                self.s3_client = boto3.client('s3')
                self.beta_users = self._load_beta_users()
                limit_str = str(BETA_USER_LIMIT) if BETA_USER_LIMIT > 0 else "unlimited"
                logger.info(f"✅ Beta user management initialized ({len(self.beta_users)}/{limit_str} users)")
            except Exception as e:
                logger.warning(f"Failed to initialize beta user management: {e}")
                self.beta_enabled = False
                self.beta_users = set()
        else:
            logger.debug("Beta user management disabled (no PDF_BUCKET_NAME)")
            self.beta_users = set()

    def _load_beta_users(self) -> set:
        """Load beta users from S3 on cold start"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.beta_bucket,
                Key=BETA_USERS_S3_KEY
            )
            data = json.loads(response['Body'].read())
            users = set(data.get('users', []))
            logger.info(f"📥 Loaded {len(users)} beta users from S3")
            return users
        except self.s3_client.exceptions.NoSuchKey:
            logger.info("📥 No beta-users.json found, starting fresh")
            return set()
        except Exception as e:
            logger.warning(f"⚠️ Failed to load beta users from S3: {e}")
            return set()

    def _save_beta_users(self):
        """Persist beta users to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.beta_bucket,
                Key=BETA_USERS_S3_KEY,
                Body=json.dumps({'users': list(self.beta_users)}, ensure_ascii=False),
                ContentType='application/json'
            )
            logger.info(f"📤 Saved {len(self.beta_users)} beta users to S3")
        except Exception as e:
            logger.error(f"❌ Failed to save beta users to S3: {e}")

    def _is_beta_user(self, user_id: str) -> bool:
        """Check if user is in beta program"""
        if not self.beta_enabled:
            return True  # Beta disabled = allow all
        return user_id in self.beta_users

    def _try_add_beta_user(self, user_id: str) -> bool:
        """Try to add user to beta. Returns True if added/exists, False if full.

        Note: BETA_USER_LIMIT=0 means unlimited (no restriction).
        """
        if not self.beta_enabled:
            return True  # Beta management disabled = allow all
        if user_id in self.beta_users:
            return True  # Already a beta user

        # Check limit (0 = unlimited)
        if BETA_USER_LIMIT > 0 and len(self.beta_users) >= BETA_USER_LIMIT:
            logger.info(f"❌ Beta full ({len(self.beta_users)}/{BETA_USER_LIMIT}), rejecting user: {user_id[:10]}...")
            return False  # Beta full

        self.beta_users.add(user_id)
        self._save_beta_users()
        limit_str = f"/{BETA_USER_LIMIT}" if BETA_USER_LIMIT > 0 else " (unlimited)"
        logger.info(f"✅ Beta user added: {user_id[:10]}... ({len(self.beta_users)}{limit_str})")
        return True

    def _get_beta_full_message(self) -> str:
        """Get message for users when beta is full"""
        return """ขออภัยครับ 🙏

ขณะนี้ Daily Report Bot อยู่ในช่วงทดสอบ (Beta) และรับผู้ใช้ครบจำนวนแล้ว

กรุณาติดต่อทีมพัฒนาหากต้องการเข้าร่วมทดสอบ

ขอบคุณที่สนใจครับ! 🙂"""

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

    def reply_message(self, reply_token, text=None, template_message=None):
        """Send reply message via LINE Messaging API
        
        Args:
            reply_token: LINE reply token
            text: Text message to send (optional if template_message is provided)
            template_message: Optional template message dict (if provided, sends template instead of text)
        """
        url = "https://api.line.me/v2/bot/message/reply"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }

        # If template message provided, use it
        if template_message:
            messages = [template_message]
        elif text:
            # Split long messages into chunks (LINE limit is 5000 characters)
            max_length = 4500
            messages = []

            if len(text) > max_length:
                # Split into chunks
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                messages = [{"type": "text", "text": chunk} for chunk in chunks[:5]]  # Max 5 messages
            else:
                messages = [{"type": "text", "text": text}]
        else:
            # No message to send
            return False

        data = {
            "replyToken": reply_token,
            "messages": messages
        }

        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200

    def reply_message_multiple(self, reply_token, messages_list):
        """Send multiple messages via LINE Messaging API
        
        Args:
            reply_token: LINE reply token
            messages_list: List of messages (can be template dicts or text strings)
        """
        url = "https://api.line.me/v2/bot/message/reply"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }

        messages = []
        for msg in messages_list:
            if isinstance(msg, dict):
                # Template message
                messages.append(msg)
            elif isinstance(msg, str):
                # Text message - split if too long
                max_length = 4500
                if len(msg) > max_length:
                    chunks = [msg[i:i+max_length] for i in range(0, len(msg), max_length)]
                    messages.extend([{"type": "text", "text": chunk} for chunk in chunks[:5]])
                else:
                    messages.append({"type": "text", "text": msg})

        data = {
            "replyToken": reply_token,
            "messages": messages[:5]  # LINE limit: max 5 messages per reply
        }

        logger.info(f"📤 Sending {len(messages)} messages to LINE API (reply_token: {reply_token[:20]}...)")
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            logger.info(f"📥 LINE API response: status={response.status_code}")
            if response.status_code != 200:
                logger.error(f"❌ LINE API error: {response.status_code} - {response.text[:200]}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Exception calling LINE API: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

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

        # Beta user limit check
        if user_id and not self._try_add_beta_user(user_id):
            # Beta is full, return rejection message
            return self._get_beta_full_message()

        # Return welcome message for accepted beta users
        return self.get_help_message()

    def format_message_with_pdf_link(self, report_text: str, pdf_url: str, ticker: str = "") -> tuple:
        """
        Format message with PDF link
        
        Args:
            report_text: Current report text output
            pdf_url: Presigned URL to PDF
            ticker: Ticker symbol (e.g., "DBS19")
            
        Returns:
            Tuple of (report_text_with_link, None)
            - report_text_with_link: Report text with PDF link at the top
            - None: No template message (LINE URI limit is 1000 chars, S3 URLs are longer)
        """
        # LINE API has a 1000 character limit for template button URIs
        # S3 presigned URLs are longer than that, so we send as text instead
        button_label = f"{ticker} รายงานฉบับเต็ม" if ticker else "📄 รายงานฉบับเต็ม"
        
        # Format message with PDF link at top
        formatted_message = f"""📄 {button_label}
🔗 {pdf_url}
⏰ ใช้งานได้ 24 ชั่วโมง

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{report_text}"""
        
        # Return formatted message and None (no template message due to URI length limit)
        return formatted_message, None
    
    def handle_message(self, event):
        """Handle incoming message"""
        try:
            message_type = event.get("type")

            if message_type != "message":
                return None

            # Beta user check - reject non-beta users
            source = event.get("source", {})
            user_id = source.get("userId", "")
            if user_id and not self._is_beta_user(user_id):
                logger.info(f"🚫 Non-beta user message rejected: {user_id[:10]}...")
                return self._get_beta_full_message()

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

            # Check Aurora cache first (single source of truth)
            cached_report = self.precompute.get_cached_report(matched_ticker)

            if cached_report:
                # Cache hit - return cached report text from Aurora
                report_text = cached_report.get('report_text')
                logger.info(f"✅ Aurora cache hit for {matched_ticker}")

                # Prepend suggestion if available
                if suggestion:
                    return f"{suggestion}\n\n{report_text}"

                return report_text

            # Cache miss - return message (LINE Lambda is read-only, doesn't generate reports)
            logger.info(f"❌ Aurora cache miss for {matched_ticker}, report not available")
            return f"ขออภัยครับ รายงานสำหรับ {matched_ticker} ยังไม่พร้อมในขณะนี้\n\nกรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ"
        except Exception as e:
            # Catch any unexpected errors in message handling
            print(f"Error handling message: {str(e)}")
            return self.get_error_message()

    def handle_webhook(self, body, signature):
        """Handle LINE webhook"""
        logger.info(f"🔔 Webhook received (signature: {signature[:20] if signature else 'None'}...)")
        # Verify signature
        if not self.verify_signature(body, signature):
            logger.warning(f"⚠️  Invalid signature - rejecting request")
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Invalid signature"}, ensure_ascii=False)
            }
        logger.info(f"✅ Signature verified")

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
            template_message = None

            try:
                if event_type == "follow":
                    # User added bot as friend
                    response_text = self.handle_follow(event)
                elif event_type == "message":
                    # User sent a message - may return tuple (text, template) or just text
                    result = self.handle_message(event)
                    if isinstance(result, tuple):
                        response_text, template_message = result
                    else:
                        response_text = result
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
                    if template_message:
                        print(f"DEBUG: Template message available: {template_message.get('template', {}).get('title', 'N/A')}")
                    print(f"response_text: {response_text}")
                    responses.append(response_text)
                else:
                    try:
                        # Send template message first if available, then text message
                        # Note: LINE reply token can only be used once, so send both in one call
                        logger.info(f"📤 Preparing to send reply (has_template={template_message is not None}, text_len={len(response_text) if response_text else 0})")
                        if template_message:
                            logger.info(f"📤 Sending template message + text report")
                            # Send both template message and text message together
                            success = self.reply_message_multiple(reply_token, [template_message, response_text])
                            if success:
                                logger.info(f"✅ Successfully sent template message and text report")
                            else:
                                logger.error(f"❌ Failed to send template message and text report")
                        else:
                            logger.info(f"📤 Sending text report only")
                            # Send text message only
                            success = self.reply_message(reply_token, response_text)
                            if success:
                                logger.info(f"✅ Successfully sent text report")
                            else:
                                logger.error(f"❌ Failed to send text report")
                    except Exception as e:
                        # If sending reply fails, log but don't fail the webhook
                        # LINE will retry if needed
                        logger.error(f"❌ Error sending reply message: {str(e)}")
                        import traceback
                        traceback.print_exc()
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


# Module-level wrapper function for Lambda handler compatibility
def handle_webhook(event):
    """Module-level wrapper for Lambda handler.

    Lambda handler expects a module-level function, but LineBot is a class.
    This wrapper instantiates the class and delegates to its handle_webhook method.

    Args:
        event: Lambda event dict with body, headers, requestContext

    Returns:
        Response dict with statusCode, headers, body
    """
    bot = LineBot()

    # Extract signature from headers
    headers = event.get('headers', {})
    # LINE uses 'x-line-signature' header (case-insensitive)
    signature = headers.get('x-line-signature') or headers.get('X-Line-Signature', '')

    # Extract body
    body = event.get('body', '')

    return bot.handle_webhook(body, signature)
