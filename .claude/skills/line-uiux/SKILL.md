---
name: line-uiux
description: LINE Bot UI/UX patterns for chat-based financial reports. **LEGACY**: LINE Bot is in maintenance mode. New development focuses on Telegram Mini App. Use this skill only when maintaining existing LINE Bot code.
---

# LINE Bot UI/UX Skill (Legacy)

**Tech Stack**: LINE Messaging API, Python 3.11+, Flask/FastAPI webhooks

**Status**: 🔶 **LEGACY** - Maintenance mode only. No new features.

**Source**: Extracted from existing LINE Bot implementation patterns.

---

## ⚠️ Important: Legacy Status

**From CLAUDE.md:**
> "LINE Bot: Chat-based Thai financial reports (production)" - marked with `@pytest.mark.legacy`

**What This Means:**
- ✅ Still in production, serving users
- ✅ Bug fixes and maintenance allowed
- ❌ No new feature development
- ❌ Skip in Telegram CI (marked `@pytest.mark.legacy`)
- 🔄 Future migration path: Telegram Mini App

**When to Use This Skill:**
- Fixing bugs in LINE Bot
- Maintaining existing LINE features
- Understanding legacy code

**When NOT to Use:**
- Building new features (use Telegram Mini App)
- New integrations (use Telegram)
- Refactoring (unless critical bug)

---

## LINE vs Telegram Architecture

### LINE Bot (Current/Legacy)

```
User sends message
   ↓
LINE Platform webhook → Flask/FastAPI endpoint
   ↓
Parse LINE message event
   ↓
Generate report (same workflow as Telegram)
   ↓
Format as LINE Flex Message
   ↓
Reply via LINE Messaging API
```

**Characteristics:**
- Push-based (webhook)
- Rich Flex Messages (cards, carousels)
- Thai language focus
- Chat-based interaction

### Telegram Mini App (Future)

```
User opens Mini App
   ↓
React SPA loads
   ↓
REST API calls (authenticated)
   ↓
Generate report (same workflow)
   ↓
Return JSON
   ↓
Client-side rendering
```

**Characteristics:**
- Pull-based (REST API)
- Web UI (React components)
- Multi-language support
- Dashboard-based interaction

**Shared:** Both use identical `src/agent/`, `src/workflow/`, `src/data/` layers.

---

## LINE Message Patterns

See [MESSAGE-PATTERNS.md](MESSAGE-PATTERNS.md) for LINE-specific message formatting.

---

## Chat Flow Patterns

See [CHAT-FLOWS.md](CHAT-FLOWS.md) for conversation flows.

---

## Best Practices

See [BEST-PRACTICES.md](BEST-PRACTICES.md) for LINE Bot development guidelines.

---

## Testing LINE Bot Code

**Pattern:** Mark LINE Bot tests as `@pytest.mark.legacy`

```python
import pytest

@pytest.mark.legacy
class TestLINEBot:
    """LINE Bot tests - legacy code"""

    def test_webhook_handler(self):
        # Test LINE webhook handling
        pass

    def test_flex_message_formatting(self):
        # Test LINE Flex Message generation
        pass
```

**Running tests:**

```bash
# Run all tests EXCEPT legacy LINE Bot tests
pytest -m "not legacy"

# Run ONLY LINE Bot tests
pytest -m legacy

# Run in Telegram CI (skips LINE)
pytest -m "not legacy and not e2e"
```

---

## Migration Strategy

### Current State (2024)

- LINE Bot: Production, maintenance mode
- Telegram Mini App: Active development

### Migration Path

**Phase 1: Parallel Operation**
- LINE Bot continues serving existing users
- Telegram Mini App onboards new users
- Shared backend (agent/workflow/data)

**Phase 2: User Migration**
- Announce Telegram Mini App to LINE users
- Provide migration incentive
- Monitor LINE usage decline

**Phase 3: Sunset LINE Bot**
- Deprecation notice (3-6 months)
- Redirect to Telegram Mini App
- Archive LINE Bot code

**Phase 4: Complete Migration**
- Remove LINE Bot code
- Remove LINE dependencies
- Remove `@pytest.mark.legacy` tests

---

## Quick Reference

### LINE Bot File Locations

```
src/line_bot/          # LINE Bot handlers (legacy)
tests/line_bot/        # LINE Bot tests (mark: legacy)
```

### Testing Commands

```bash
# Skip LINE Bot tests (default in Telegram CI)
pytest -m "not legacy"

# Test only LINE Bot
pytest -m legacy tests/line_bot/

# Full test suite (includes LINE)
pytest
```

### Deployment

**LINE Bot is NOT deployed via GitHub Actions.** Uses separate deployment process (if still deployed).

**Telegram deployment:** See deployment skill.

---

## File Organization

```
.claude/skills/line-uiux/
├── SKILL.md                # This file (entry point)
├── MESSAGE-PATTERNS.md     # LINE Flex Message patterns
├── CHAT-FLOWS.md           # Conversation flows
└── BEST-PRACTICES.md       # LINE Bot guidelines
```

---

## Next Steps

- **For message formatting**: See [MESSAGE-PATTERNS.md](MESSAGE-PATTERNS.md)
- **For chat flows**: See [CHAT-FLOWS.md](CHAT-FLOWS.md)
- **For guidelines**: See [BEST-PRACTICES.md](BEST-PRACTICES.md)
- **For testing**: See testing-workflow skill
- **For new development**: Use telegram-uiux skill instead

---

## References

- [LINE Messaging API](https://developers.line.biz/en/docs/messaging-api/)
- [LINE Flex Message Simulator](https://developers.line.biz/flex-simulator/)
- [Migration to Telegram](../telegram-uiux/SKILL.md)
