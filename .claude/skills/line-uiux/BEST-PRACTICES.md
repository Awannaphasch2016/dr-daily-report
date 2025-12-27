# LINE Bot Best Practices

Guidelines for maintaining LINE Bot code (legacy).

**Status:** Legacy - Maintenance mode only

---

## Development Guidelines

### 1. No New Features

```python
# ❌ DON'T: Add new features to LINE Bot
def add_portfolio_tracking():
    """New feature: Track user portfolio"""
    # This should go in Telegram Mini App instead!

# ✅ DO: Bug fixes and maintenance only
def fix_thai_encoding_bug():
    """Fix: Correct Thai character encoding in messages"""
    # Legacy bug fixes are acceptable
```

### 2. Share Backend Logic

```python
# ✅ GOOD: LINE and Telegram share workflow
from src.workflow.graph import WorkflowGraph

# LINE Bot handler
def line_handler(ticker: str):
    workflow = WorkflowGraph()
    result = workflow.run({'ticker': ticker})
    return format_as_flex_message(result)

# Telegram API handler
def telegram_handler(ticker: str):
    workflow = WorkflowGraph()  # Same workflow!
    result = workflow.run({'ticker': ticker})
    return result  # Return JSON directly
```

**Never:** Duplicate business logic between LINE and Telegram.

### 3. Mark Tests as Legacy

```python
import pytest

# ✅ Always mark LINE Bot tests
@pytest.mark.legacy
class TestLINEBotWebhook:
    """LINE Bot webhook tests"""

    def test_handle_text_message(self):
        # Test implementation
        pass
```

---

## Performance Considerations

### 1. Webhook Response Time

LINE requires webhook response within **30 seconds**.

```python
@app.route("/webhook", methods=['POST'])
def webhook():
    """LINE webhook must respond quickly"""

    # ❌ BAD: Long processing blocks webhook
    for event in events:
        report = generate_report(ticker)  # Takes 5-10 seconds
        line_bot_api.reply_message(...)  # Blocks webhook

    return 'OK'  # Might timeout!

# ✅ GOOD: Acknowledge immediately, process async
@app.route("/webhook", methods=['POST'])
def webhook():
    """Quick acknowledgment"""

    for event in events:
        # Immediate acknowledgment
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="กำลังประมวลผล...")
        )

        # Process in background
        threading.Thread(
            target=process_and_send,
            args=(event.source.user_id, ticker)
        ).start()

    return 'OK'  # Fast response

def process_and_send(user_id: str, ticker: str):
    """Background processing"""
    report = generate_report(ticker)
    line_bot_api.push_message(user_id, create_flex_message(report))
```

### 2. Message Size Optimization

```python
# ❌ BAD: Large Flex Message (>50 KB)
def create_huge_flex_message(data):
    return {
        "type": "bubble",
        "body": {
            "contents": [
                # ... 1000 items (too large!)
            ]
        }
    }

# ✅ GOOD: Limit content, link to full report
def create_optimized_flex_message(data):
    return {
        "type": "bubble",
        "body": {
            "contents": [
                # ... Top 10 items only
            ]
        },
        "footer": {
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "ดูรายงานฉบับเต็ม",
                        "uri": "https://example.com/report/full"
                    }
                }
            ]
        }
    }
```

---

## Security Considerations

### 1. Verify LINE Signature

```python
import hashlib
import hmac
import base64

def verify_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """Verify LINE webhook signature"""

    hash = hmac.new(
        channel_secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()

    expected_signature = base64.b64encode(hash).decode('utf-8')

    return hmac.compare_digest(signature, expected_signature)

@app.route("/webhook", methods=['POST'])
def webhook():
    # Get signature from header
    signature = request.headers.get('X-Line-Signature')

    # Verify signature
    if not verify_signature(request.get_data(), signature, CHANNEL_SECRET):
        abort(400)  # Invalid signature

    # Process webhook
    # ...
```

### 2. Sanitize User Input

```python
import re

def sanitize_ticker(user_input: str) -> str:
    """Sanitize ticker input"""

    # Remove whitespace
    ticker = user_input.strip()

    # Convert to uppercase
    ticker = ticker.upper()

    # Validate format (alphanumeric only)
    if not re.match(r'^[A-Z0-9]+$', ticker):
        raise ValueError("Invalid ticker format")

    # Length check
    if len(ticker) > 10:
        raise ValueError("Ticker too long")

    return ticker

# Usage:
try:
    ticker = sanitize_ticker(user_message)
    report = generate_report(ticker)
except ValueError as e:
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=f"รูปแบบไม่ถูกต้อง: {e}")
    )
```

### 3. Rate Limiting

```python
from functools import wraps
import time

# Simple in-memory rate limiter
user_last_request = {}
RATE_LIMIT_SECONDS = 5  # 5 seconds between requests

def rate_limit(func):
    """Rate limit decorator for webhook handlers"""

    @wraps(func)
    def wrapper(event):
        user_id = event.source.user_id
        now = time.time()

        last_request = user_last_request.get(user_id, 0)

        if now - last_request < RATE_LIMIT_SECONDS:
            # Too fast, reject
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="กรุณารอสักครู่ก่อนส่งคำขอใหม่")
            )
            return

        user_last_request[user_id] = now
        return func(event)

    return wrapper

@rate_limit
def handle_message(event):
    # Process message
    pass
```

---

## Error Handling

### 1. Graceful Degradation

```python
def generate_report(ticker: str) -> dict:
    """Generate report with fallbacks"""

    try:
        # Try full report with all data sources
        return generate_full_report(ticker)

    except yfinance.YahooFinanceException:
        # Fallback: Use cached data
        logger.warning(f"YFinance failed for {ticker}, using cache")
        return generate_cached_report(ticker)

    except Exception as e:
        # Last resort: Error message
        logger.error(f"Report generation failed: {e}")
        return {
            'error': True,
            'message': "เกิดข้อผิดพลาด กรุณาลองใหม่ภายหลัง"
        }
```

### 2. User-Friendly Error Messages

```python
ERROR_MESSAGES_THAI = {
    'ticker_not_found': 'ไม่พบหุ้น {ticker} กรุณาตรวจสอบรหัส',
    'api_timeout': 'ระบบไม่ตอบสนอง กรุณาลองใหม่',
    'rate_limit': 'คุณส่งคำขอบ่อยเกินไป กรุณารอ {seconds} วินาที',
    'maintenance': 'ระบบปรับปรุง กรุณาลองใหม่ในเวลา {time}',
    'invalid_format': 'รูปแบบรหัสหุ้นไม่ถูกต้อง (เช่น NVDA19)'
}

def get_error_message(error_type: str, **kwargs) -> str:
    """Get Thai error message with formatting"""
    template = ERROR_MESSAGES_THAI.get(error_type, 'เกิดข้อผิดพลาด')
    return template.format(**kwargs)
```

---

## Logging

### 1. Structured Logging for LINE Events

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_line_event(event_type: str, user_id: str, data: dict):
    """Structured logging for LINE events"""

    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        **data
    }

    logger.info(f"LINE_EVENT: {json.dumps(log_data)}")

# Usage:
log_line_event('message_received', user_id, {
    'message_type': 'text',
    'text': ticker
})
```

### 2. Error Tracking

```python
# Track errors by type for monitoring
error_counts = {}

def track_error(error_type: str):
    """Track error occurrence"""
    error_counts[error_type] = error_counts.get(error_type, 0) + 1

    logger.error(f"LINE_ERROR: {error_type} (count: {error_counts[error_type]})")

# Usage:
try:
    report = generate_report(ticker)
except yfinance.YahooFinanceException:
    track_error('yfinance_api_error')
except Exception as e:
    track_error('unknown_error')
```

---

## Testing Best Practices

### 1. Mock LINE API Calls

```python
from unittest.mock import Mock, patch

@pytest.mark.legacy
class TestLINEBotWebhook:
    """LINE Bot webhook tests"""

    @patch('app.line_bot_api')
    def test_handle_text_message(self, mock_line_bot_api):
        """Test text message handling"""

        # Setup mock
        mock_line_bot_api.reply_message = Mock()

        # Simulate webhook event
        event = Mock()
        event.message.text = "NVDA19"
        event.reply_token = "test_token"

        # Handle event
        handle_message(event)

        # Verify reply was sent
        mock_line_bot_api.reply_message.assert_called_once()
```

### 2. Test Flex Message Structure

```python
import json

@pytest.mark.legacy
def test_flex_message_structure():
    """Validate Flex Message JSON structure"""

    report_data = {'ticker': 'NVDA19', 'price': 500}
    flex_message = create_report_card(report_data)

    # Validate structure
    contents = flex_message.contents

    assert contents['type'] == 'bubble'
    assert 'header' in contents
    assert 'body' in contents
    assert 'footer' in contents

    # Validate JSON size (< 50 KB)
    json_size = len(json.dumps(contents))
    assert json_size < 50 * 1024, f"Flex Message too large: {json_size} bytes"
```

---

## Migration Preparation

### 1. Document LINE-Specific Logic

```python
# LINE Bot handler
def line_specific_format(data: dict) -> FlexSendMessage:
    """
    LINE-specific formatting.

    MIGRATION NOTE: Telegram uses different message format.
    See telegram_format() for equivalent.
    """
    # LINE Flex Message formatting
    pass

# Telegram handler (equivalent)
def telegram_format(data: dict) -> dict:
    """
    Telegram-specific formatting.

    MIGRATION NOTE: Equivalent to line_specific_format()
    but returns JSON instead of Flex Message.
    """
    # Telegram JSON formatting
    pass
```

### 2. Extract Shared Logic

```python
# ✅ GOOD: Shared logic in src/
# src/report/formatter.py
def format_indicators(indicators: dict) -> dict:
    """Format indicators (used by both LINE and Telegram)"""
    return {
        'sma_20': f"{indicators['sma_20']:.2f}",
        'rsi': f"{indicators['rsi']:.1f}",
        # ...
    }

# LINE Bot
from src.report.formatter import format_indicators

def create_line_message(data):
    formatted = format_indicators(data['indicators'])
    # ... LINE-specific wrapping

# Telegram API
from src.report.formatter import format_indicators

def create_telegram_response(data):
    formatted = format_indicators(data['indicators'])
    # ... Return JSON directly
```

---

## Quick Reference

### DO

- ✅ Fix bugs in LINE Bot
- ✅ Share backend logic with Telegram
- ✅ Mark tests with `@pytest.mark.legacy`
- ✅ Respond to webhooks within 30 seconds
- ✅ Verify LINE signature
- ✅ Use reply_message over push_message
- ✅ Sanitize user input
- ✅ Log errors with context

### DON'T

- ❌ Add new features (use Telegram instead)
- ❌ Duplicate business logic
- ❌ Block webhook with long processing
- ❌ Skip signature verification
- ❌ Trust user input without validation
- ❌ Create Flex Messages > 50 KB
- ❌ Use push_message excessively

---

## References

- [LINE Messaging API Best Practices](https://developers.line.biz/en/docs/messaging-api/development-guidelines/)
- [Webhook Security](https://developers.line.biz/en/docs/messaging-api/receiving-messages/#verifying-signatures)
- [Rate Limits](https://developers.line.biz/en/docs/messaging-api/development-guidelines/#rate-limiting)
