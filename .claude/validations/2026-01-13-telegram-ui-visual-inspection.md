# Validation Report

**Claim**: "Real data is not displayed in Telegram Mini App (staging)"
**Type**: behavior (visual inspection via Playwright)
**Date**: 2026-01-13

---

## Status: ⚠️ PARTIALLY TRUE

The claim is **PARTIALLY TRUE**:
- ✅ **Ticker list data IS displayed** (from API)
- ❌ **Chart data NOT displayed** ("No chart data available")
- ❌ **Scoring data NOT displayed** ("No scoring data available")

---

## Evidence Summary

### Visual Evidence (Screenshot)

![Telegram Mini App Staging](/tmp/telegram_miniapp_staging.png)

**What IS displayed:**
- Ticker names: SMFG19, VHM19, ORCL19, ITOCHU19, GOLDUS19, COSTCO19, HONDA19, MUFG19, MITSU19, VCB19
- Company names (e.g., "SUMITOMO MITSUI FINANCIAL GROUP")
- Volume data (e.g., "Vol: $308.0K")
- Agree counts (e.g., "154 agree")
- Progress bars (e.g., "$308K/$500K (62%)")
- "High Conv." badges

**What is NOT displayed:**
- Chart thumbnails → Shows "No chart data available" placeholder
- Scoring data → Shows "No scoring data available" placeholder

### API Evidence

**Request made:**
```
GET https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/rankings?category=trending
```

**Response (200 OK):**
```json
{
  "category": "trending",
  "as_of": "2026-01-13T12:44:02.735791",
  "tickers": [
    {
      "ticker": "VCB19",
      "company_name": "JS COMM BANK FOREIGN TRADE VIET",
      "price": 74000.0,
      "price_change_pct": 1.79,
      "currency": "VND",
      ...
    }
  ]
}
```

The API is returning data successfully - the rankings endpoint works.

---

## Root Cause Analysis

### Why "No chart data available"?

The frontend expects chart data in the ticker cards. Looking at the API response structure, the rankings endpoint returns basic ticker info but likely NOT:
- `chart_base64` - Mini chart image
- Chart historical data for rendering

### Why "No scoring data available"?

The scoring/rating data is likely expected from:
- Precomputed reports (which exist for only 8 tickers)
- A separate scoring endpoint

### Data Flow Gap

```
Rankings API → Returns basic ticker list ✅
          ↓
Frontend expects → chart_base64, scoring_data
          ↓
But rankings API doesn't include these fields ❌
```

---

## Evidence Details

### Console Warnings (Non-critical)
```
[Telegram.WebApp] Closing confirmation is not supported in version 6.0
[Telegram.WebApp] BackButton is not supported in version 6.0
```
These are Telegram WebApp SDK warnings, not data issues.

### Page Elements Found
- Ticker cards: 10 displayed
- Chart placeholders: All show "No chart data available"
- Scoring placeholders: All show "No scoring data available"
- Error messages: None
- Loading indicators: None (page fully loaded)

---

## Conclusion

| Data Type | Status | Source |
|-----------|--------|--------|
| Ticker list | ✅ Displayed | Rankings API |
| Company names | ✅ Displayed | Rankings API |
| Volume/Agree | ✅ Displayed | Rankings API |
| Progress bars | ✅ Displayed | Rankings API |
| Chart thumbnails | ❌ Missing | Not in rankings response |
| Scoring data | ❌ Missing | Not in rankings response |

**The claim is PARTIALLY TRUE:**
- Basic data IS flowing from Aurora → API → Frontend
- But chart and scoring data are missing from the rankings endpoint response

---

## Recommendations

### Option 1: Enrich Rankings API Response

Add `chart_base64` and scoring fields to `/rankings` endpoint:

```python
# In rankings endpoint
for ticker in tickers:
    # Fetch mini chart from precomputed_reports
    report = precompute_service.get_cached_report(ticker['symbol'])
    if report:
        ticker['chart_base64'] = report.get('chart_base64')
        ticker['stance'] = report.get('stance')
        ticker['confidence'] = report.get('confidence')
```

### Option 2: Frontend Lazy Loading

Have frontend fetch chart/scoring data separately when card is visible:

```javascript
// On card render, fetch additional data
const report = await fetch(`/api/v1/report/${ticker}`);
```

### Option 3: Pre-generate Mini Charts

Run precompute workflow more frequently to ensure all trending tickers have chart data.

---

## Next Steps

- [ ] Check if rankings API should include chart_base64 field
- [ ] Verify precomputed_reports has chart data for trending tickers
- [ ] Decide: enrich API vs lazy-load on frontend
- [ ] Update frontend to handle missing chart/scoring gracefully (current placeholder is fine)

---

## References

**Screenshot**: `/tmp/telegram_miniapp_staging.png`

**API Endpoint**:
- `https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/rankings?category=trending`

**Frontend URL**:
- `https://djjir31dhdd4s.cloudfront.net/`

**Related Validation**:
- `.claude/validations/2026-01-13-telegram-ui-aurora-data.md` - API returns data correctly
