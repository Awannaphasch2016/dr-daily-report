# Validation Report

**Claim**: "Daily scheduler data (precompute + chart patterns etc.) prepopulated correctly in Aurora prod"
**Type**: config + data
**Date**: 2026-01-22T12:21:00+07:00

---

## Status: ⚠️ PARTIALLY TRUE

## Evidence Summary

**Supporting evidence** (4 items):

1. **Precomputed Reports - Complete** ✅
   - Today (2026-01-22): 56 completed reports
   - Yesterday (2026-01-21): 56 completed reports
   - All 56 tickers have reports
   - Status: All `completed`, none `failed`
   - Confidence: High

2. **Ticker Data (Price History) - Complete** ✅
   - Today (2026-01-22): 56 tickers with price data
   - Yesterday (2026-01-21): 56 tickers
   - Total records: 433 (across ~8 trading days)
   - Latest date: 2026-01-22
   - Confidence: High

3. **Ticker Master & Aliases - Complete** ✅
   - 56 active tickers in `ticker_master`
   - 112 aliases in `ticker_aliases` (56 DR + 56 Yahoo)
   - Confidence: High

4. **Fund Data - Complete** ✅
   - 17,087 records
   - 49 unique tickers
   - Synced: 2026-01-21
   - Confidence: High

**Missing/Empty tables** (3 items):

1. **daily_indicators** ❌
   - Records: 0 (empty)
   - Expected: Technical indicators (RSI, MACD, SMA, etc.)
   - Impact: Chart patterns may not work

2. **daily_prices** ❌
   - Records: 0 (empty)
   - Expected: Daily OHLCV data
   - Impact: Duplicate of ticker_data? May not be used

3. **indicator_percentiles** ❌
   - Records: 0 (empty)
   - Expected: Percentile calculations for indicators
   - Impact: Percentile-based analysis unavailable

**Also empty** (likely optional):
- `ticker_cache_metadata`: 0 records
- `ticker_info`: 0 records

---

## Analysis

### Overall Assessment

The **core daily scheduler functionality is working correctly**:
- Price data fetched for all 56 tickers
- Precomputed reports generated for all 56 tickers
- Both completed today (2026-01-22)

However, **advanced analytics tables are empty**:
- `daily_indicators`, `daily_prices`, `indicator_percentiles` all have 0 records
- These tables exist but are never populated

### Data Architecture

```
Working (populated daily):
├── ticker_data (price history)     → 433 records, 56 tickers ✅
├── precomputed_reports             → 387 records, 56 today ✅
└── fund_data                       → 17,087 records ✅

Empty (never populated):
├── daily_indicators                → 0 records ❌
├── daily_prices                    → 0 records ❌
└── indicator_percentiles           → 0 records ❌
```

### Key Findings

1. **Price data and reports work**: The scheduler successfully fetches price data and generates reports daily.

2. **Empty analytics tables**: `daily_indicators`, `daily_prices`, and `indicator_percentiles` tables exist with proper schemas but contain no data. These are likely designed for future features or the population logic isn't deployed.

3. **Chart patterns unclear**: Without `daily_indicators`, chart pattern detection would need to calculate indicators on-the-fly rather than from cached data.

### Confidence Level: HIGH (for core functionality), MEDIUM (for chart patterns)

**Reasoning**:
- Direct verification of Aurora data confirms core tables populated
- Empty tables verified with `COUNT(*)` queries
- Schema exists for empty tables, suggesting intended but not implemented population

---

## Recommendations

**For core functionality (TRUE)**:
- No action needed - precompute and price data working correctly
- Continue monitoring daily completeness

**For empty tables (INVESTIGATE)**:
1. Check if `daily_indicators`, `daily_prices`, `indicator_percentiles` are actually used
2. If used, implement population logic in scheduler
3. If not used, consider removing tables to avoid confusion

**To investigate**:
```bash
# Check if any code references these tables
grep -r "daily_indicators\|daily_prices\|indicator_percentiles" src/
```

---

## Verified Components

| Table | Status | Records | Latest Date |
|-------|--------|---------|-------------|
| ticker_master | ✅ | 56 active | - |
| ticker_aliases | ✅ | 112 | - |
| ticker_data | ✅ | 433 | 2026-01-22 |
| precomputed_reports | ✅ | 387 (56 today) | 2026-01-22 |
| fund_data | ✅ | 17,087 | 2026-01-21 |
| daily_indicators | ❌ Empty | 0 | - |
| daily_prices | ❌ Empty | 0 | - |
| indicator_percentiles | ❌ Empty | 0 | - |

---

## References

**AWS Resources**:
- Aurora Cluster: `dr-daily-report-aurora-prod`
- Database: `ticker_data`

**Tables Verified**:
- `ticker_master`, `ticker_aliases`
- `ticker_data`, `precomputed_reports`
- `fund_data`
- `daily_indicators`, `daily_prices`, `indicator_percentiles`
