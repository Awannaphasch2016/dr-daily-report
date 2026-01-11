---
title: Telegram Mini App serves Twinbar with shared DR-Report data
category: architecture
date: 2026-01-10
status: documented
related_adrs: []
tags: [telegram, twinbar, frontend, data-sharing]
---

# Telegram Mini App serves Twinbar with shared DR-Report data

## Context

**What is the architecture?**

The Telegram Mini App frontend (`d3uuexs20crp9s.cloudfront.net`) serves **Twinbar** (a prediction markets application), NOT a Daily Report-specific UI. However, both applications share the same underlying data infrastructure.

**Key insight**: This is intentional design, not a deployment error.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SHARED BACKEND                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Aurora MySQL (staging)                                        │
│   ├── precomputed_reports (46 tickers)                         │
│   ├── daily_prices                                              │
│   ├── daily_indicators                                          │
│   └── ticker_master                                             │
│                                                                 │
│   API Gateway + Lambda                                          │
│   ├── /api/v1/report/{ticker}  → ReportResponse                │
│   ├── /api/v1/tickers          → Ticker list                   │
│   └── /api/v1/backtest         → Backtest results              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│   Twinbar Frontend  │           │   LINE Bot / Other  │
│   (Telegram Mini)   │           │   Consumers         │
├─────────────────────┤           ├─────────────────────┤
│ - Prediction markets│           │ - Stock reports     │
│ - Uses DR data for  │           │ - Direct API calls  │
│   market prices     │           │                     │
│ - Mock UI preview   │           │                     │
└─────────────────────┘           └─────────────────────┘
```

## Data Sharing Model

| Data Source | Used By Twinbar | Used By DR-Report |
|------------|-----------------|-------------------|
| Aurora precomputed_reports | Yes (market prices) | Yes (full reports) |
| Yahoo Finance (via Lambda) | Yes (real-time) | Yes (real-time) |
| Technical indicators | Yes (predictions) | Yes (analysis) |

## Implications

**For Development**:
- Changes to backend affect both Twinbar and DR-Report
- Precompute workflow populates data for both apps
- API endpoints serve both frontends

**For Testing**:
- Testing staging API validates data for both apps
- Frontend-specific testing requires knowing which app is deployed
- CloudFront URL serves Twinbar, not DR-Report UI

**For Validation**:
- API returning real data ✅ → Backend works for both apps
- Twinbar showing mock data → Twinbar-specific frontend issue (not data issue)

## Clarification

**What I observed** (during bug-hunt):
- CloudFront serves "Twinbar - Predictive Markets" UI
- Console shows "Loaded 6 mock markets for UI preview"

**What this means**:
- This is **correct behavior** - Telegram Mini App IS Twinbar
- Mock data is Twinbar's UI preview, not related to Aurora data
- Aurora data IS available and working (verified via direct API calls)

## Consequences

**Positive**:
- Single backend serves multiple frontends (DRY)
- Precompute workflow benefits all consumers
- Unified data model

**Considerations**:
- Must understand which frontend is deployed where
- "Telegram staging" = Twinbar, not DR-Report UI
- Direct API testing is the reliable way to validate backend

## References

- CloudFront staging: `https://d3uuexs20crp9s.cloudfront.net` → Twinbar
- API Gateway staging: `https://ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com`
- Frontend source: `frontend/twinbar/`
