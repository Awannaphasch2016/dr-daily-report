# UI_SPEC – Telegram Mini App for Financial Securities AI Report

## 1. Overview

This document describes the UI layout, components, and interaction patterns for the Telegram Mini App front end.

The app is a Telegram WebApp, rendered inside Telegram. It must be optimized for mobile screens and short interactions.

Main screens:

- Home (Dashboard)
- Report
- Market Movers (optional separate view, can be inline)
- Error and loading states

---

## 2. Global Layout and Style

- Mobile-first design (rough target: 375 x 667 logical points).
- Use a single-column layout.
- Use cards and tabs instead of long paragraphs.
- Primary actions as clear buttons.
- Telegram WebApp theme should be respected:
  - Use Telegram-provided background and text colors when possible.

Typography:

- Title: 18–20 px, bold
- Section headings: 16 px, semi-bold
- Body text: 14 px

---

## 3. Home Screen (Dashboard)

### 3.1 Layout Structure

Sections from top to bottom:

1. App header
2. Search section
3. Recently Viewed
4. Watchlist
5. Market Movers (optional v1)

### 3.2 Components

#### App Header

- Left: app name text, e.g., `AI Ticker Reports`
- Right: optional icon (help / info).

#### Search Section

- Large search input field:
  - Placeholder: `Search ticker or company`
- As user types:
  - Show dropdown list of suggestions below input.

Autocomplete list item:

- Ticker (bold)
- Company name (subtext)
- Exchange and type in smaller muted text.

Interaction:

- Tapping a suggestion:
  - Closes dropdown.
  - Navigates to Report screen for that ticker.

#### Recently Viewed

- Section title: `Recently Viewed`
- Display as horizontal scrollable chips.

Chip content:

- `TICKER`
- Optional small label for stance (Bullish / Neutral / Bearish).

Interaction:

- Tapping a chip opens Report screen for that ticker.

#### Watchlist

- Section title: `Watchlist`
- Vertical list of cards.

Each watchlist card:

- Ticker and company name.
- Latest price and day change.
- Stance tag (e.g., `Bullish`, `Bearish`, `Neutral`).
- Risk tag (`Low`, `Medium`, `High`).
- Button or icon: `Open report`.
- Optional small star icon indicating watchlist membership.

Interaction:

- Tapping card or `Open report` opens Report screen.
- Tapping star in the card header removes from watchlist.

#### Market Movers (Optional)

- Section title: `Market Movers`
- Four pill buttons:
  - `Top Gainers`
  - `Top Losers`
  - `Volume Surge`
  - `Trending`

Interaction:

- Tapping a pill:
  - Opens a simple list view overlay or inline expansion:
    - List of ranked tickers with price, % change.
    - Each row has `Open report` action.

---

## 4. Report Screen

### 4.1 Layout Overview

Vertical structure:

1. Ticker header
2. Summary banner
3. Tabs (Summary, Technicals, Fundamentals, News, Risk, Peers, Notes)
4. Tab content area
5. Bottom sticky actions (optional)

### 4.2 Ticker Header

Displays:

- Ticker and company name.
- Current price and day change.
- Currency.
- Report timestamp, e.g., `As of 2025-11-24 12:00 UTC`.
- Star toggle for watchlist.

Interaction:

- Tapping star toggles watchlist state and shows small toast.

### 4.3 Summary Banner

Card just under header.

Fields:

- Stance (`Bullish`, `Bearish`, `Neutral`).
- Estimated upside or downside (e.g., `+18 % upside`).
- Confidence level (e.g., `High`, `Medium`, `Low`).
- Investment horizon (text, e.g., `6-12 months`).

Visual:

- Use background color or accent line to differentiate stance:
  - Bullish: positive tone.
  - Bearish: negative tone.
  - Neutral: muted tone.

---

## 5. Tabs and Content

Tabs are a horizontal row at top of content area:

- `Summary`
- `Technicals`
- `Fundamentals`
- `News & Sentiment`
- `Risk`
- `Peers`
- `Notes`

Tabs should be scrollable horizontally if screen space is limited.

If a section has no data, hide the tab.

### 5.1 Summary Tab

Components:

1. `Key Takeaways` section
   - Title
   - List of bullets (1–5 items).

2. `Price Drivers` section
   - Title
   - List of bullets.

3. `Risks to Watch` section
   - Title
   - Bullet list.

4. Action Row (bottom of tab)
   - Button: `Export PDF`
   - Button: `Share`

Interactions:

- `Export PDF`:
  - Opens `pdf_report_url` in browser or Telegram viewer.
- `Share`:
  - Uses Telegram share methods to forward link or file.

### 5.2 Technicals Tab

Sections within this tab:

- Trend indicators
- Momentum indicators
- Volatility indicators
- Liquidity indicators

Each section:

- Title
- List of rows.

Metric row:

- Left:
  - Metric name (e.g., `RSI`)
  - Value (e.g., `55.71`)
- Middle:
  - Percentile as a bar or small tag (e.g., `35th percentile`).
- Right:
  - Status tag (`Bullish`, `Bearish`, `Neutral`, `Elevated risk`).

Interaction:

- Tapping a row opens a bottom sheet:
  - Name and value.
  - Explanation text.
  - Brief guidance on how to interpret the current value.

Optional:

- Small static mini-chart image at top of tab showing recent price or indicator trend.

### 5.3 Fundamentals Tab

Sections:

- `Valuation`
- `Growth`
- `Profitability`

Each section:

- Title
- Metric rows similar to technicals:

Metric row:

- Metric name (e.g., `P/E`)
- Value
- Optional percentile
- Short comment (e.g., `Expensive vs peers`)

If no fundamentals data:

- Tab is hidden.

### 5.4 News & Sentiment Tab

Components:

1. Sentiment summary card:
   - Text: `Overall sentiment: Positive 73 %`
   - Visual representation (simple segmented bar for positive / neutral / negative).

2. News list:

Each news card:

- Headline (title)
- Source and published time
- Sentiment tag (`Positive`, `Neutral`, `Negative`)
- External link icon.

Interaction:

- Tapping a card opens the news URL in Telegram or browser.

If there are no news items:

- Show placeholder text such as `No recent news found`.

### 5.5 Risk Tab

Components:

1. Risk summary card:
   - Risk level (`Low`, `Medium`, `High`)
   - Volatility score (numeric)
   - Uncertainty score (numeric and percentile).

2. `Key Risks` section:
   - List of risk bullets.

Interaction:

- None required beyond scrolling.
- Optional: tooltips or info icons explaining what `Risk level` means.

### 5.6 Peers Tab

Components:

- Simple comparison table.

Columns:

- `Ticker`
- `Upside`
- `Stance`
- `Valuation` label (`Cheap`, `Fair`, `Expensive`)

Each row:

- Displays peer info.
- Has a small `Open` button or row tap triggers navigation.

Interaction:

- Tapping a row opens that ticker's Report screen.

### 5.7 Notes / Data Sources Tab

Components:

1. `Data Sources Used` section:
   - List of human-readable descriptions:
     - Example: `Yahoo Finance – price, volume`
     - Example: `Internal quantitative dataset – technical metrics`

2. `Model & Generation Info` section:
   - Agent version string.
   - Generation time.
   - Strategy description (short).

These are primarily for transparency and advanced users.

---

## 6. Loading and Error States

### 6.1 Loading States

For report screen:

- Show skeleton placeholders for header, summary banner, and tab content.
- Text placeholder for `Loading report...`.

For search autocomplete:

- Show spinner or `Searching...` row while HTTP call pending.

For rankings:

- Skeleton rows or `Loading market movers...`.

### 6.2 Error States

Examples:

- Network error:
  - Show message: `Could not load data. Check your connection and try again.`
  - Provide `Retry` button.

- Ticker not supported:
  - Show message: `No report is available for this ticker yet.`
  - Link back to search.

- Backend internal error:
  - Generic message: `Something went wrong while generating the report. Please try again later.`

---

## 7. Navigation Flows

### 7.1 Home → Report

- User taps a search result, recently viewed chip, watchlist card, or market mover row.
- App navigates to Report screen (same in-app view, different state).

### 7.2 Report → Report

- Inside Peers tab, user taps a peer.
- Replace current report state with new ticker report.
- Optionally add a back arrow that returns to previous ticker.

### 7.3 Back Navigation

- Use Telegram WebApp built-in back or custom back button in header.
- Back from Report:
  - Returns to Home and preserves scroll position.

---

## 8. Responsive Behavior

- On larger screens (tablet or desktop Telegram):

  - Tabs may be wider and show full labels.
  - Cards can have more padding.

- On narrow screens:

  - Tabs should be scrollable horizontally.
  - Avoid side-by-side columns; keep content stacked.

---

## 9. State Management Overview (Frontend)

Key state slices:

- `search`:
  - `query`, `suggestions`, `isLoading`, `error`.

- `report`:
  - `currentTicker`, `reportData`, `isLoading`, `error`.

- `watchlist`:
  - `tickers` (array), `isPersisted` (bool to check if using backend or local).

- `recentlyViewed`:
  - Array of tickers, stored in local storage.

Persistence:

- Watchlist and Recently Viewed can be saved using local storage for v1.

---

## 10. Telemetry (Optional)

Events to log (if analytics is used):

- `search_performed`
- `report_viewed`
- `watchlist_added`
- `watchlist_removed`
- `peer_opened`
- `pdf_export_triggered`
- `share_triggered`

Each event should include `ticker` where relevant.
