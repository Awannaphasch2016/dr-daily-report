# ADR-006: Two Separate Apps (LINE Bot + Telegram Mini App)

**Status:** ✅ Accepted
**Date:** 2024-03
**Deciders:** Development Team

## Context

The project provides Thai language financial reports. Initial deployment was LINE Bot (chat-based). Product wants to add richer UI with charts, interactive elements, and dashboard features.

### LINE Bot Constraints

- Text-only messages (no embedded charts)
- Limited message types (text, flex messages, images as attachments)
- No web view embedding
- No interactive UI components (buttons limited to postbacks)

### User Needs

- View price charts inline (not as image attachments)
- Interactive elements (toggle between timeframes, compare tickers)
- Dashboard UI (multiple tickers, rankings, watchlist)
- Rich formatting (tables, expandable sections)

## Decision

Build Telegram Mini App as separate FastAPI application instead of extending LINE Bot.

### Architecture

```
Core Backend (Shared):
  - src/agent.py
  - src/workflow/
  - src/data/
  - src/analysis/

LINE Bot Interface:
  - src/integrations/line_bot.py
  - AWS Lambda Function URL
  - Chat-based UX (text messages)

Telegram Mini App Interface:
  - src/api/ (FastAPI REST API)
  - API Gateway + Lambda
  - Web-based dashboard UX (HTML/CSS/JS)
```

### Shared Infrastructure

- Both apps use same agent/workflow/data layers
- Resources tagged via AWS tags: `App = line-bot | telegram-api | shared`
- Single Aurora database, single DynamoDB tables
- Separate CloudFront distributions

## Consequences

### Positive

- ✅ **Platform-Specific UX**: Each platform optimized for its strengths
  - LINE: Simple chat for quick queries
  - Telegram: Rich dashboard for analysis
- ✅ **Feature Parity Not Required**: Don't need to limit Telegram to LINE's constraints
- ✅ **Independent Deployment**: Can deploy Telegram without affecting LINE users
- ✅ **Technology Choice**: FastAPI + Vue.js for Telegram, LINE SDK for LINE Bot

### Negative

- ❌ **Maintenance Burden**: Two interfaces to maintain
- ❌ **Code Duplication Risk**: Must keep business logic in shared layer
- ❌ **Testing Complexity**: Must test both interfaces
- ❌ **User Confusion**: Different features available on different platforms

### Mitigation

- **Shared Backend**: 90% of code in `src/` shared between apps
- **Clear Separation**: Interface code in separate directories (`src/integrations/`, `src/api/`)
- **Unified Data Model**: Both apps read from same Aurora cache

## Alternatives Considered

### Alternative 1: Extend LINE Bot with Web View

**Approach:** Use LINE's webview feature to embed dashboard

**Why Rejected:**
- LINE webview limited (no full web app)
- Still requires chat-based entry point
- Can't use Telegram's native features (Mini Apps, bot commands)

### Alternative 2: Build Telegram Bot (Chat-Based)

**Approach:** Mirror LINE Bot functionality in Telegram

**Why Rejected:**
- Doesn't solve UX limitations (still chat-based)
- Telegram's strength is Mini Apps (web-based), not traditional bots
- Missing opportunity for rich dashboard UI

### Alternative 3: Unified Web App (No Platform-Specific Apps)

**Approach:** Single web app accessible from browser, link from LINE/Telegram

**Why Rejected:**
- Loses platform integration (no LINE/Telegram auth)
- Users must leave app to view reports
- Can't use platform features (notifications, inline buttons)

### Alternative 4: Mobile App (iOS/Android)

**Approach:** Build native mobile apps

**Why Rejected:**
- Development cost: 3x (iOS + Android + web)
- Distribution: App store approval, updates
- Discovery: Users must find and install app
- LINE/Telegram already installed on users' phones

## References

- **LINE Bot Code**: `src/integrations/line_bot.py`
- **Telegram API**: `src/api/` (FastAPI routes)
- **Shared Infrastructure Tags**: `App = line-bot | telegram-api | shared`
- **Telegram Mini Apps**: https://core.telegram.org/bots/webapps

## Decision Drivers

1. **Platform Capabilities**: Telegram Mini Apps support full web tech stack
2. **User Experience**: Dashboard UX needs charts, tables, interactive elements
3. **Development Speed**: FastAPI + Vue.js faster than extending LINE's limited SDK

## Feature Comparison

| Feature | LINE Bot | Telegram Mini App |
|---------|----------|-------------------|
| Quick ticker query | ✅ Chat command | ✅ Search bar |
| Price chart | ❌ Image only | ✅ Interactive chart |
| Rankings | ✅ Text list | ✅ Sortable table |
| Watchlist | ❌ Not available | ✅ Full CRUD UI |
| Multi-ticker compare | ❌ Not practical | ✅ Side-by-side view |
| Report history | ❌ Limited | ✅ Full history UI |

**Verdict:** Telegram Mini App enables features impossible in LINE Bot.

## Deployment Strategy

- **Phase 1**: LINE Bot (production, stable)
- **Phase 2**: Telegram Mini App API (REST endpoints)
- **Phase 3**: Telegram Mini App frontend (Vue.js dashboard)
- **Phase 4**: Feature parity where it makes sense (not all features need both)

**Current Status (Dec 2024):** Phase 3 complete, both apps in production.
