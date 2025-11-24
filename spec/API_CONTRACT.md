# API_CONTRACT – Telegram Mini App for Financial Securities AI Report

## 1. Overview

This document defines the API contract between:

- **Frontend**: Telegram Mini App (WebApp)
- **Backend**: Ticker analysis service that returns structured AI-generated reports

All endpoints use JSON over HTTPS. Versioning is assumed via base path `/api/v1`.

Base URL (example):

- `https://your-backend-domain.com/api/v1`

Adjust to your actual deployment environment.

---

## 2. Authentication

For v1, the app can run in either:

- **No-auth mode** (public read-only endpoints)
- Or **Telegram-verified mode**: Telegram WebApp provides `initData` which backend can validate.

Minimum assumption for this contract:

- All endpoints support **no-auth** read access.
- If Telegram verification is added, frontend must attach a header:

`X-Telegram-Init-Data: <raw_init_data>`

Backend may validate, but this is out of scope for this document.

---

## 3. Common Conventions

- All timestamps: ISO 8601, UTC. Example: `"2025-11-24T12:00:00Z"`
- All numeric fields that are monetary values must include a `currency` field at top-level or be clearly implied.
- Errors use a common structure (see section 9).

---

## 4. Endpoint Summary

| Method | Path                  | Description                             |
|--------|-----------------------|-----------------------------------------|
| GET    | `/search`             | Search tickers by query string          |
| GET    | `/report/:ticker`     | Get full AI report for a ticker         |
| GET    | `/rankings`           | Get market movers / ranked tickers      |
| GET    | `/watchlist`          | Get user watchlist (optional v1)        |
| POST   | `/watchlist`          | Add ticker to watchlist (optional v1)   |
| DELETE | `/watchlist/:ticker`  | Remove ticker from watchlist (optional) |

`/watchlist` endpoints can initially be stubbed or use local storage on frontend only.

---

## 5. `GET /search`

Search for tickers by partial query.

### Request

`GET /search?q=<query>&limit=<limit>`

Query parameters:

- `q` (required): string, partial ticker or company name. Min length 1–2 characters.
- `limit` (optional): integer, default 10, max 50.

### Response 200

```json
{
  "results": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "exchange": "NASDAQ",
      "currency": "USD",
      "type": "equity"
    },
    {
      "ticker": "NVDS",
      "company_name": "T-Rex 2X Inverse NVIDIA Daily Target ETF",
      "exchange": "NASDAQ",
      "currency": "USD",
      "type": "etf"
    }
  ]
}
```

### Error Responses

- 400 if `q` missing or invalid.
- 500 for internal errors.

See section 9 for error format.

---

## 6. `GET /report/:ticker`

Fetch the full AI-generated report for a ticker.

### Request

`GET /report/NVDA`

Path parameter:

- `ticker` (required): string, canonical ticker symbol used by backend.

Optional query parameters:

- `force_refresh` (bool, default false): if true, backend recomputes report even if cache exists.
- `lang` (string, optional): language code (for future localization).

### Response 200

```json
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "price": 123.45,
  "price_change_pct": 2.34,
  "currency": "USD",
  "as_of": "2025-11-24T12:00:00Z",

  "stance": "bullish",
  "estimated_upside_pct": 18.0,
  "confidence": "high",
  "investment_horizon": "6-12 months",

  "summary_sections": {
    "key_takeaways": [
      "Short bullet 1",
      "Short bullet 2"
    ],
    "price_drivers": [
      "Driver bullet 1"
    ],
    "risks_to_watch": [
      "Risk bullet 1"
    ]
  },

  "technical_metrics": [
    {
      "name": "RSI",
      "value": 55.71,
      "percentile": 35.2,
      "category": "momentum",
      "status": "bearish",
      "explanation": "Short explanation"
    },
    {
      "name": "MACD",
      "value": 0.45,
      "percentile": 22.2,
      "category": "momentum",
      "status": "bullish",
      "explanation": "Short explanation"
    }
  ],

  "fundamentals": {
    "valuation": [
      { "name": "P/E", "value": 40.2, "percentile": 80, "comment": "Expensive vs peers" }
    ],
    "growth": [
      { "name": "Revenue growth YoY", "value": 18.3, "percentile": 70, "comment": "" }
    ],
    "profitability": [
      { "name": "ROE", "value": 26.1, "percentile": 85, "comment": "" }
    ]
  },

  "news_items": [
    {
      "title": "NVIDIA beats earnings expectations",
      "url": "https://finance.yahoo.com/...",
      "source": "Yahoo Finance",
      "published_at": "2025-11-24T09:00:00Z",
      "sentiment_label": "positive",
      "sentiment_score": 0.78
    }
  ],

  "overall_sentiment": {
    "positive_pct": 73,
    "neutral_pct": 15,
    "negative_pct": 12
  },

  "risk": {
    "risk_level": "medium",
    "volatility_score": 6,
    "uncertainty_score": {
      "value": 51.39,
      "percentile": 64.8
    },
    "risk_bullets": [
      "Risk 1",
      "Risk 2"
    ]
  },

  "peers": [
    {
      "ticker": "AMD",
      "company_name": "Advanced Micro Devices, Inc.",
      "estimated_upside_pct": 12.0,
      "stance": "bullish",
      "valuation_label": "fair"
    }
  ],

  "data_sources": [
    "Yahoo Finance - price, volume",
    "Internal dataset - technical percentiles",
    "News - curated feeds"
  ],

  "pdf_report_url": "https://example.com/reports/NVDA.pdf",

  "generation_metadata": {
    "agent_version": "v1.0.0",
    "strategy": "multi_stage_analysis",
    "generated_at": "2025-11-24T12:00:00Z",
    "cache_hit": true
  }
}
```

### Notes:

Omitted sections should be either:

- Present but empty (for frontend simplicity), or
- Omitted completely, in which case frontend hides tab.

### Error Responses

- 404 if ticker not supported.
- 502/504 if upstream analysis failed or timed out.

---

## 7. `GET /rankings`

Returns lists of ranked tickers for discovery features such as Market Movers.

### Request

`GET /rankings?category=top_gainers&limit=10`

Query parameters:

- `category` (required): one of
  - `top_gainers`
  - `top_losers`
  - `volume_surge`
  - `trending`
- `limit` (optional): integer, default 10, max 50.

### Response 200

```json
{
  "category": "top_gainers",
  "as_of": "2025-11-24T12:00:00Z",
  "tickers": [
    {
      "ticker": "TSLA",
      "company_name": "Tesla, Inc.",
      "price": 210.55,
      "price_change_pct": 6.78,
      "currency": "USD",
      "stance": "bullish",
      "estimated_upside_pct": 12.0,
      "risk_level": "high"
    }
  ]
}
```

---

## 8. Watchlist Endpoints (Optional v1)

If you decide to back watchlist by backend instead of pure local storage.

### 8.1 `GET /watchlist`

Returns current user's saved tickers.

`GET /watchlist`

Response 200:

```json
{
  "tickers": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "added_at": "2025-11-24T10:00:00Z"
    },
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "added_at": "2025-11-24T11:00:00Z"
    }
  ]
}
```

### 8.2 `POST /watchlist`

Add ticker to watchlist.

`POST /watchlist`

Body:

```json
{
  "ticker": "NVDA"
}
```

Response 200:

```json
{
  "status": "ok",
  "ticker": "NVDA"
}
```

### 8.3 `DELETE /watchlist/:ticker`

Remove ticker.

`DELETE /watchlist/NVDA`

Response 200:

```json
{
  "status": "ok",
  "ticker": "NVDA"
}
```

---

## 9. Error Format

All non-2xx responses should use a standard envelope.

```json
{
  "error": {
    "code": "REPORT_NOT_FOUND",
    "message": "No report found for ticker NVDA",
    "details": {
      "ticker": "NVDA"
    }
  }
}
```

- `code`: machine-readable error code.
- `message`: safe to show in UI.
- `details`: optional object for debugging.

Example codes:

- `INVALID_REQUEST`
- `TICKER_NOT_SUPPORTED`
- `REPORT_NOT_FOUND`
- `INTERNAL_ERROR`
- `UPSTREAM_TIMEOUT`
- `RATE_LIMITED`

---

## 10. Versioning

v1 base path: `/api/v1`

Breaking changes require:

- New version path `/api/v2`, or
- New fields with feature flags.

---

## 11. Performance Considerations

`GET /report/:ticker` should:

- Use server-side caching where possible.
- Set appropriate HTTP cache headers if safe.

Frontend will:

- Cache recently fetched reports in memory or local storage.
- Prefer cached data for watchlist and recently viewed tickers where fresh enough.
