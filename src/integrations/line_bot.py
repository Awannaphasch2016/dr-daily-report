# -*- coding: utf-8 -*-
import json
import os
import hmac
import hashlib
import base64
import requests
import logging
from datetime import date
from src.agent import TickerAnalysisAgent
from src.data.ticker_matcher import TickerMatcher
from src.data.data_fetcher import DataFetcher
from src.data.database import TickerDatabase
from src.formatters.pdf_storage import PDFStorage
from src.data.s3_cache import S3Cache

logger = logging.getLogger(__name__)

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.agent = TickerAnalysisAgent()
        # Initialize ticker matcher with ticker map (load directly to ensure it's available)
        data_fetcher = DataFetcher()
        ticker_map = data_fetcher.load_tickers()
        self.ticker_matcher = TickerMatcher(ticker_map)

        # Initialize S3 cache (if enabled)
        self.s3_cache = None
        cache_backend = os.getenv("CACHE_BACKEND", "hybrid")  # hybrid, s3, or sqlite
        if cache_backend in ("s3", "hybrid"):
            try:
                pdf_bucket = os.getenv("PDF_BUCKET_NAME")
                cache_ttl = int(os.getenv("CACHE_TTL_HOURS", "24"))
                if pdf_bucket:
                    self.s3_cache = S3Cache(bucket_name=pdf_bucket, ttl_hours=cache_ttl)
                    logger.info(f"✅ S3 cache initialized (backend={cache_backend}, TTL={cache_ttl}h)")
                else:
                    logger.warning("PDF_BUCKET_NAME not set, S3 cache disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 cache: {e}")

        # Initialize database for caching (with S3 cache integration)
        self.db = TickerDatabase(s3_cache=self.s3_cache)

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

        # Return welcome message
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
                
                # Generate PDF and get URL (if PDF storage is available)
                final_message = report
                pdf_template_message = None
                pdf_url = None

                if self.pdf_storage and self.pdf_storage.is_available():
                    try:
                        # Check if PDF already exists in S3 cache
                        if self.s3_cache:
                            pdf_url = self.s3_cache.get_pdf_url(matched_ticker, today)
                            if pdf_url:
                                logger.info(f"✅ PDF cache hit for {matched_ticker}, reusing existing PDF")

                        # Generate new PDF if not cached
                        if not pdf_url:
                            logger.info(f"📄 Generating PDF for {matched_ticker}...")
                            pdf_bytes = self.agent.generate_pdf_report(matched_ticker)
                            pdf_url = self.pdf_storage.upload_and_get_url(pdf_bytes, matched_ticker)
                            logger.info(f"✅ PDF generated and uploaded: {pdf_url[:50]}...")

                        # Format message with PDF link (returns tuple: report_text, template_message)
                        final_message, pdf_template_message = self.format_message_with_pdf_link(report, pdf_url, matched_ticker)

                    except Exception as pdf_error:
                        # PDF generation failed - fallback to text-only report
                        logger.warning(f"⚠️  PDF generation failed for {matched_ticker}: {str(pdf_error)}")
                        # Continue with text-only report
                        final_message = report
                        pdf_template_message = None
                else:
                    logger.debug("PDF storage not available, skipping PDF generation")
                
                # Save to cache for future use (save original report text, not PDF link version)
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
                    final_message = f"{suggestion}\n\n{final_message}"
                
                # Return tuple: (message_text, template_message)
                # template_message will be sent first, then message_text
                return (final_message, pdf_template_message)
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
