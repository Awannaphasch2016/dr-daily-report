# PRD – Telegram Mini App for Financial Securities AI Report

## 1. Overview
The Telegram Mini App enables users to search any financial security ticker and receive a structured, multi-panel AI-generated research report. It replaces chat-style report delivery with an intuitive dashboard for faster consumption, comparison, and sharing of insights.

The backend agent is already capable of generating reports. The Mini App provides the UI and UX layer that turns raw analysis into an interactive investment research product.

## 2. Objectives & Success Metrics

### 2.1 Business Objectives
| Goal | KPI |
|------|-----|
| Grow adoption of automated financial reports | DAU / WAU |
| Increase report consumption | Avg. reports opened per session |
| Encourage habit formation | Watchlist recall rate (users return to re-check tickers) |
| Amplify organic distribution | # of PDF shares per 100 users |

### 2.2 User Objectives
- Understand why a stock is bullish/bearish without reading long paragraphs.
- Compare multiple tickers quickly.
- Store and revisit tickers of interest.
- Export and share reports easily.

## 3. Target Users

| Type | Characteristics |
|------|----------------|
| Beginner Retail Investors | Curious but not technical; want simple explanations |
| Intermediate Investors | Understand signals/indicators; compare tickers weekly |
| Financial Telegram Group Users | Like sharing insights and research material |

## 4. Core Value Proposition
> Bloomberg-style analysis but inside Telegram — fast, digestible, AI-powered.

## 5. Full User Journey (Long-Form)

### 5.1 First Entry
The user opens the Mini App for the first time.  
The Home screen has a big search bar and empty Watchlist and no Recently Viewed.

User types: `NVDA`. Autocomplete appears showing ticker + company name + exchange. User taps it.

### 5.2 Loading → First Report
If cached, the report opens instantly.  
If not cached, animated skeleton loaders and the message **“Generating research report…”** appear.

The Summary tab opens automatically with:
- stance (bullish / bearish / neutral)
- estimated upside %
- confidence level
- key takeaways, price drivers, risks to watch

### 5.3 Exploration Through Tabs
User navigates between:
- Summary
- Technicals
- Fundamentals
- News & Sentiment
- Risk
- Peers
- Notes / Data Sources

User taps RSI → bottom sheet explains the signal and interpretation.

### 5.4 Watchlist Adoption
User taps ⭐ Add to Watchlist.  
NVDA now appears in the Watchlist on the Home screen.

### 5.5 Next Visit / Retention Loop
User returns days later.  
Home now shows:
- Recently Viewed → NVDA
- Watchlist → NVDA with price / % change
- Search bar still top priority

User searches AAPL, views its report, adds it to Watchlist.

### 5.6 Discovery Flow
User taps Market Movers → Top Gainers → taps TSLA → opens TSLA report.

### 5.7 Comparison Flow
Inside AAPL report → Peers tab lists MSFT, GOOGL, NVDA.  
User taps NVDA → instant cached load.

### 5.8 Sharing Flow
User exports NVDA PDF and shares in a Telegram group.  
New users join the Mini App frictionlessly.

### 5.9 Long-Term Retention
User continues to return for:
- Watchlist monitoring
- Peer comparison
- Checking sentiment/stance shifts
- Sharing insights with others

The recurring loop becomes:
**Check → Interpret → Compare → Save → Return**

## 6. Product Scope

### 6.1 In-Scope (v1)
- Ticker search + autocomplete
- Watchlist
- Recently Viewed
- Market Movers (basic)
- Report with multi-tab structure
- PDF export + Telegram share
- Robust loading & error handling
- Dark theme support preferred

### 6.2 Out-of-Scope (v1)
- Alerts (push notifications)
- Real-time streaming price feed
- Portfolio performance tracking
- In-app community/social features

## 7. Functional Requirements

### 7.1 Home Dashboard
- Search bar with autocomplete
- Watchlist cards
- Recently Viewed chips
- Market Movers entry points

### 7.2 Report Screen
- Fetches data from backend by ticker
- Tabs render only when corresponding data exists
- Peers tab → tap opens another report
- Export PDF + Share buttons

### 7.3 Watchlist
- ⭐ toggles add/remove state
- Stored locally (cloud sync optional later)

### 7.4 UX Constraints
- No scrolling walls of text
- Summaries must be bullet-based
- Expand/collapse for long narrative blocks

## 8. Non-Functional Requirements

| Category | Target |
|----------|--------|
| Performance | Cold load < 1500ms; cached load < 500ms |
| Uptime | 99% |
| Mobile Layout | Fits 5–6″ screens perfectly |
| Accessibility | Large tap targets & readable font sizes |
| Safety | Informational tone — no trading advice |

## 9. Data Contract / JSON Schema
Backend returns a structured object containing:
- Top-level metadata (ticker, company, price, timestamp, etc.)
- `summary_sections`
- `technical_metrics`
- `fundamentals`
- `risk`
- `news_items`
- `peers`
- `pdf_report_url`
- `generation_metadata`

*(Full JSON schema already established — backend must respect contract.)*

## 10. Technical Constraints

| Topic | Constraint |
|-------|-----------|
| Platform | Telegram WebApp API |
| Frontend | React preferred (or vanilla JS) |
| Styling | TailwindCSS preferred |
| Data | REST JSON |
| Hosting | Static (Netlify / Vercel / S3 static hosting) |
| Backend | Frontend must not generate AI — only render backend responses |
| Visualization | Static chart images OK; heavy chart libs discouraged |
| Caching | Client-side caching of report JSON required |
| Legal | No BUY/SELL directives; language informational only |
| Analytics | Must not collect personal identifying financial info |

## 11. Tools

| Component | Tools |
|-----------|-------|
| Telegram Integration | Telegram WebApp SDK |
| Frontend | React + Tailwind |
| State | Zustand / Redux Toolkit / React Context |
| HTTP | Axios or Fetch |
| Deployment | Vercel / Netlify / S3 |
| QA | Playwright or Cypress |
| Monitoring | Sentry (optional) |

## 12. Acceptance Criteria

| Area | Pass Condition |
|------|----------------|
| Search | Autocomplete appears after 2+ chars |
| Report | Opens successfully for any valid ticker |
| Tabs | No crash even if a tab has missing data |
| Layout | Entire report readable without desktop |
| Watchlist | Items persist after app reload |
| Sharing | PDF opens and can be forwarded in Telegram |
| Performance | Cached load < 1s |
| Failure Mode | If backend down → retry button, not crash |

A feature is **shippable only if all AC for that feature are satisfied.**

## 13. Release Plan

### Phase 1 — MVP
- Home dashboard + search
- Report screen + all tabs
- Watchlist
- Recent tickers
- PDF export

### Phase 1.1 — Quality & polish
- Market Movers
- Better caching
- Improved tooltips & loaders

### Phase 2
- Alerts
- Premium tier
- Cloud-synced watchlist

## 14. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slow report generation | Use skeleton loader + cached fallback |
| Information overload | Tabs + bullet summaries |
| Data gaps | Tabs autohide |
| Advice liability | Avoid imperative trade suggestions |

## 15. Open Questions
| Question | Owner |
|----------|-------|
| Crypto/ETFs included at launch? | Product |
| Cloud sync vs device-only watchlist for v1? | Product |
| Market movers refresh rate? | Engineering |
| PDF rendering backend or client? | Engineering |
