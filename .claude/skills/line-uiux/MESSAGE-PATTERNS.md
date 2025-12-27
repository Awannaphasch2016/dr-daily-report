# LINE Message Patterns

LINE Flex Message formatting patterns for financial reports.

**Status:** Legacy - Maintenance only

---

## LINE Message Types

### Text Messages (Simple)

```python
from linebot.models import TextSendMessage

def send_simple_message(ticker: str) -> TextSendMessage:
    """Simple text message for quick responses"""
    return TextSendMessage(text=f"กำลังวิเคราะห์ {ticker}...")
```

**Use When:**
- Acknowledgment messages
- Error messages
- Simple status updates

### Flex Messages (Rich UI)

```python
from linebot.models import FlexSendMessage

def create_report_card(report_data: dict) -> FlexSendMessage:
    """Rich card for financial report"""
    return FlexSendMessage(
        alt_text=f"รายงาน {report_data['ticker']}",
        contents={
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": report_data['ticker'],
                        "weight": "bold",
                        "size": "xl"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": report_data['summary'],
                        "wrap": True
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "ดูรายงานฉบับเต็ม",
                            "uri": report_data['full_report_url']
                        }
                    }
                ]
            }
        }
    )
```

**Use When:**
- Financial report summaries
- Interactive dashboards
- Multi-section content

---

## Thai Language Patterns

### Number Formatting

```python
def format_thai_number(value: float) -> str:
    """Format numbers with Thai conventions"""

    # Use comma separator
    formatted = f"{value:,.2f}"

    # Thai currency
    return f"฿{formatted}"

# Example:
# format_thai_number(1234567.89) → "฿1,234,567.89"
```

### Date Formatting

```python
from datetime import datetime

def format_thai_date(date: datetime) -> str:
    """Format date in Thai style"""

    thai_months = [
        'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
        'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'
    ]

    # Buddhist calendar (add 543 years)
    buddhist_year = date.year + 543

    return f"{date.day} {thai_months[date.month - 1]} {buddhist_year}"

# Example:
# format_thai_date(datetime(2024, 1, 15)) → "15 ม.ค. 2567"
```

### Financial Terms

```python
THAI_FINANCIAL_TERMS = {
    'price': 'ราคา',
    'volume': 'ปริมาณ',
    'market_cap': 'มูลค่าตลาด',
    'pe_ratio': 'อัตราส่วน P/E',
    'dividend_yield': 'ผลตอบแทนเงินปันผล',
    'revenue': 'รายได้',
    'profit': 'กำไร',
    'growth': 'การเติบโต',
    'recommendation': 'คำแนะนำ'
}

def translate_term(english: str) -> str:
    """Get Thai translation for financial term"""
    return THAI_FINANCIAL_TERMS.get(english, english)
```

---

## Report Structure Pattern

### Complete Report Flex Message

```python
def create_full_report(state: dict) -> FlexSendMessage:
    """Create complete financial report as Flex Message"""

    ticker = state['ticker']
    indicators = state.get('indicators', {})
    news_summary = state.get('news_summary', '')
    recommendation = state.get('recommendation', '')

    return FlexSendMessage(
        alt_text=f"รายงานวิเคราะห์ {ticker}",
        contents={
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": ticker,
                        "weight": "bold",
                        "size": "xxl",
                        "color": "#1DB446"
                    },
                    {
                        "type": "text",
                        "text": f"ราคาปัจจุบัน: {format_thai_number(indicators.get('price', 0))}",
                        "size": "md",
                        "color": "#555555"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # Technical indicators section
                    {
                        "type": "text",
                        "text": "ตัวชี้วัดทางเทคนิค",
                        "weight": "bold",
                        "size": "lg",
                        "margin": "md"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    _create_indicator_box("SMA 20", indicators.get('sma_20', 0)),
                    _create_indicator_box("SMA 50", indicators.get('sma_50', 0)),
                    _create_indicator_box("RSI", indicators.get('rsi', 0)),

                    # News section
                    {
                        "type": "text",
                        "text": "สรุปข่าว",
                        "weight": "bold",
                        "size": "lg",
                        "margin": "xl"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": news_summary,
                        "wrap": True,
                        "margin": "md"
                    },

                    # Recommendation section
                    {
                        "type": "text",
                        "text": "คำแนะนำ",
                        "weight": "bold",
                        "size": "lg",
                        "margin": "xl"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": recommendation,
                        "wrap": True,
                        "margin": "md",
                        "color": "#1DB446" if "ซื้อ" in recommendation else "#FF0000"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "ข้อมูล ณ วันที่ " + format_thai_date(datetime.now()),
                        "size": "xs",
                        "color": "#888888",
                        "align": "center"
                    }
                ]
            }
        }
    )

def _create_indicator_box(label: str, value: float) -> dict:
    """Helper to create indicator display box"""
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {
                "type": "text",
                "text": label,
                "flex": 1,
                "size": "sm"
            },
            {
                "type": "text",
                "text": f"{value:,.2f}",
                "flex": 1,
                "size": "sm",
                "align": "end",
                "weight": "bold"
            }
        ],
        "margin": "sm"
    }
```

---

## Error Message Patterns

```python
def create_error_message(error_type: str, details: str = "") -> TextSendMessage:
    """Standardized error messages in Thai"""

    error_messages = {
        'ticker_not_found': f"ไม่พบข้อมูลหุ้น กรุณาตรวจสอบรหัสหุ้น\n{details}",
        'api_error': f"เกิดข้อผิดพลาดในการดึงข้อมูล กรุณาลองใหม่อีกครั้ง\n{details}",
        'invalid_input': f"รูปแบบข้อมูลไม่ถูกต้อง\n{details}",
        'timeout': "การประมวลผลใช้เวลานานเกินไป กรุณาลองใหม่"
    }

    message = error_messages.get(error_type, f"เกิดข้อผิดพลาด: {details}")

    return TextSendMessage(text=message)
```

---

## Character Limits

LINE has message size limits:

| Message Type | Limit | Notes |
|--------------|-------|-------|
| **Text Message** | 5,000 chars | Plain text |
| **Flex Message** | 50 KB JSON | Structure + content |
| **Alt Text** | 400 chars | Fallback text |

**Pattern:** If report exceeds limit, split into multiple messages or link to full report.

```python
def send_long_report(report_text: str, line_bot_api, reply_token: str):
    """Handle reports longer than 5000 characters"""

    MAX_LENGTH = 5000

    if len(report_text) <= MAX_LENGTH:
        # Short enough for single message
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=report_text)
        )
    else:
        # Split into chunks
        chunks = [
            report_text[i:i+MAX_LENGTH]
            for i in range(0, len(report_text), MAX_LENGTH)
        ]

        messages = [TextSendMessage(text=chunk) for chunk in chunks]

        # LINE allows up to 5 messages per reply
        line_bot_api.reply_message(reply_token, messages[:5])
```

---

## Quick Reference

### Common Thai Phrases

```python
COMMON_PHRASES = {
    'processing': 'กำลังประมวลผล...',
    'please_wait': 'กรุณารอสักครู่',
    'complete': 'เสร็จสิ้น',
    'error': 'เกิดข้อผิดพลาด',
    'thank_you': 'ขอบคุณครับ/ค่ะ',
    'welcome': 'ยินดีต้อนรับ'
}
```

### Color Codes (LINE Brand)

```python
LINE_COLORS = {
    'primary_green': '#1DB446',  # LINE brand green
    'success': '#00B900',
    'error': '#FF0000',
    'warning': '#FF9900',
    'text_primary': '#111111',
    'text_secondary': '#555555',
    'text_tertiary': '#888888'
}
```

---

## References

- [LINE Flex Message Simulator](https://developers.line.biz/flex-simulator/)
- [LINE Design Guidelines](https://developers.line.biz/en/docs/messaging-api/flex-message-design-guidelines/)
- [Thai Language Processing](https://github.com/PyThaiNLP/pythainlp)
