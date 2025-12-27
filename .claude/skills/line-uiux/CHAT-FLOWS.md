# LINE Bot Chat Flows

Conversation patterns for LINE Bot financial report interactions.

**Status:** Legacy - Maintenance only

---

## Basic Request-Response Flow

```
User: NVDA19
  ↓
Bot: กำลังวิเคราะห์ NVDA19...
  ↓ (3-5 seconds processing)
Bot: [Flex Message with report]
```

**Implementation:**

```python
@app.route("/webhook", methods=['POST'])
def webhook():
    """LINE webhook handler"""

    # Parse incoming message
    events = parser.parse(request.get_data(as_text=True), signature)

    for event in events:
        if isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessage):
                ticker = event.message.text.strip().upper()

                # Immediate acknowledgment
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"กำลังวิเคราะห์ {ticker}...")
                )

                # Process in background (or sync if quick)
                report = generate_report(ticker)

                # Send result
                line_bot_api.push_message(
                    event.source.user_id,
                    create_report_card(report)
                )

    return 'OK'
```

---

## Error Handling Flow

```
User: INVALID_TICKER
  ↓
Bot: กำลังวิเคราะห์ INVALID_TICKER...
  ↓ (API call fails)
Bot: ไม่พบข้อมูลหุ้น กรุณาตรวจสอบรหัสหุ้น
```

**Pattern:**

```python
def generate_report(ticker: str) -> dict:
    """Generate report with error handling"""

    try:
        # Validate ticker format
        if not re.match(r'^[A-Z0-9]+$', ticker):
            raise ValueError("Invalid ticker format")

        # Fetch data
        data = fetch_ticker_data(ticker)

        if not data:
            raise ValueError("Ticker not found")

        # Generate report
        return workflow.run({'ticker': ticker})

    except ValueError as e:
        # User error - friendly message
        return {
            'error': True,
            'message': f"ไม่พบข้อมูลหุ้น: {str(e)}"
        }

    except Exception as e:
        # System error - generic message
        logger.error(f"Report generation failed: {e}")
        return {
            'error': True,
            'message': "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่"
        }
```

---

## Multi-Turn Conversation (Not Recommended)

LINE Bot is stateless. Multi-turn conversations require state management.

**Avoid:**

```
# ❌ DON'T: Complex multi-turn flows
User: รายงาน
Bot: หุ้นไหนครับ?
User: NVDA19
Bot: ต้องการรายละเอียดไหนครับ?
User: ทั้งหมด
Bot: [Report]
```

**Problems:**
- Requires session state storage
- Confusing for users
- More complex to maintain

**Prefer:**

```
# ✅ DO: Single-turn with clear input
User: NVDA19
Bot: [Report]
```

**If Multi-Turn Needed:**

```python
# Use Redis or DynamoDB for session state
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def handle_message(user_id: str, message: str) -> str:
    """Handle message with session state"""

    # Get user session
    session_key = f"line_session:{user_id}"
    session = redis_client.get(session_key)

    if session:
        # Continue conversation
        state = json.loads(session)

        if state['step'] == 'waiting_for_ticker':
            ticker = message.strip().upper()
            # ... process ticker

            # Clear session
            redis_client.delete(session_key)

    else:
        # Start new conversation
        if message == 'รายงาน':
            # Set session
            redis_client.setex(
                session_key,
                300,  # 5 minutes TTL
                json.dumps({'step': 'waiting_for_ticker'})
            )
            return "หุ้นไหนครับ?"

        else:
            # Direct ticker request
            return process_ticker(message)
```

---

## Rich Menu Flow

LINE supports persistent menu buttons (Rich Menu).

```
┌──────────────────────────┐
│   Chat Area              │
│   User: NVDA19          │
│   Bot: [Report]         │
├──────────────────────────┤
│   Rich Menu (Always     │
│   Visible)              │
│  ┌──────┬──────┬──────┐ │
│  │ วิเคราะห์ │ ช่วยเหลือ │ ข่าว  │
│  │ หุ้น   │      │      │ │
│  └──────┴──────┴──────┘ │
└──────────────────────────┘
```

**Implementation:**

```python
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, MessageAction

def create_rich_menu():
    """Create persistent menu for LINE Bot"""

    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=843),
        selected=True,
        name="Financial Analysis Menu",
        chat_bar_text="เมนูหลัก",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=MessageAction(label="วิเคราะห์หุ้น", text="วิเคราะห์หุ้น")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                action=MessageAction(label="ช่วยเหลือ", text="ช่วยเหลือ")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                action=MessageAction(label="ข่าว", text="ข่าวหุ้น")
            )
        ]
    )

    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)

    # Upload image for menu (2500x843 px)
    with open('rich_menu_image.png', 'rb') as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', f)

    # Set as default menu
    line_bot_api.set_default_rich_menu(rich_menu_id)
```

**Handler:**

```python
def handle_menu_action(message_text: str, user_id: str):
    """Handle rich menu button taps"""

    if message_text == "วิเคราะห์หุ้น":
        return TextSendMessage(text="กรุณาส่งรหัสหุ้น (เช่น NVDA19, AAPL19)")

    elif message_text == "ช่วยเหลือ":
        return create_help_message()

    elif message_text == "ข่าวหุ้น":
        return create_news_carousel()

    else:
        # Treat as ticker symbol
        return process_ticker(message_text)
```

---

## Postback Actions (Button Clicks)

Flex Messages can have buttons that trigger postback events.

```python
# In Flex Message:
{
    "type": "button",
    "action": {
        "type": "postback",
        "label": "ดูรายละเอียด",
        "data": "action=detail&ticker=NVDA19"
    }
}

# Handle postback:
@handler.add(PostbackEvent)
def handle_postback(event):
    """Handle button clicks"""

    # Parse postback data
    params = dict(parse_qsl(event.postback.data))

    action = params.get('action')
    ticker = params.get('ticker')

    if action == 'detail':
        # Generate detailed report
        report = generate_detailed_report(ticker)

        line_bot_api.reply_message(
            event.reply_token,
            create_detailed_flex_message(report)
        )
```

---

## Quick Reply Suggestions

Provide quick reply buttons for common actions.

```python
from linebot.models import QuickReply, QuickReplyButton, MessageAction

def send_with_quick_replies(reply_token: str, message: str):
    """Send message with suggested actions"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(
            text=message,
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(
                        action=MessageAction(label="NVDA19", text="NVDA19")
                    ),
                    QuickReplyButton(
                        action=MessageAction(label="AAPL19", text="AAPL19")
                    ),
                    QuickReplyButton(
                        action=MessageAction(label="TSLA19", text="TSLA19")
                    ),
                    QuickReplyButton(
                        action=MessageAction(label="ช่วยเหลือ", text="ช่วยเหลือ")
                    )
                ]
            )
        )
    )
```

---

## Carousel (Multiple Reports)

Show multiple ticker reports in swipeable carousel.

```python
from linebot.models import FlexSendMessage, CarouselContainer

def create_multi_ticker_carousel(tickers: list) -> FlexSendMessage:
    """Create carousel of multiple ticker reports"""

    bubbles = []

    for ticker in tickers:
        report = generate_report(ticker)
        bubble = create_report_bubble(report)
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text=f"รายงาน {len(tickers)} หุ้น",
        contents=CarouselContainer(contents=bubbles)
    )

# Usage:
# User: NVDA19,AAPL19,TSLA19
# Bot: [Carousel with 3 reports]
```

---

## Rate Limiting

LINE has rate limits for messages.

**Limits:**
- Reply messages: No limit (within 30 seconds of event)
- Push messages: 500/month (free tier), unlimited (paid)

**Pattern:** Use reply_message instead of push_message when possible.

```python
# ✅ GOOD: Use reply (free, no limit)
line_bot_api.reply_message(
    event.reply_token,
    TextSendMessage(text="Response")
)

# ⚠️  AVOID: Push consumes monthly quota
line_bot_api.push_message(
    user_id,
    TextSendMessage(text="Notification")
)
```

---

## Quick Reference

### Flow Decision Matrix

| Scenario | Pattern | Complexity |
|----------|---------|------------|
| **Simple query** | Direct request-response | Low |
| **Invalid input** | Error message | Low |
| **Long processing** | Acknowledgment → Result | Medium |
| **Multiple options** | Rich Menu | Medium |
| **Multi-turn** | Session state (avoid) | High |

### Message Type Selection

| Use Case | Message Type |
|----------|--------------|
| **Quick response** | TextSendMessage |
| **Financial report** | FlexSendMessage (Bubble) |
| **Multiple tickers** | FlexSendMessage (Carousel) |
| **Error** | TextSendMessage |
| **Menu** | Rich Menu |
| **Suggestions** | Quick Reply |

---

## References

- [LINE Messaging API Types](https://developers.line.biz/en/reference/messaging-api/#message-objects)
- [Rich Menu](https://developers.line.biz/en/docs/messaging-api/using-rich-menus/)
- [Quick Reply](https://developers.line.biz/en/docs/messaging-api/using-quick-reply/)
