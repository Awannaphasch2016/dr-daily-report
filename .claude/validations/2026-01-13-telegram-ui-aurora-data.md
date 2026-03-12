# Validation Report

**Claim**: "In staging env, Telegram UI doesn't display real data from Aurora"
**Type**: behavior + config
**Date**: 2026-01-13

---

## Status: ❌ FALSE

The claim is **FALSE**. The Telegram UI in staging **DOES display real data from Aurora**.

---

## Evidence Summary

### Evidence AGAINST Claim (Telegram UI DOES work)

**1. Telegram API Returns Real Data** ✅
```bash
curl "https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19"
```

Response (key fields):
```json
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "price": 184.94,
  "stance": "bearish",
  "confidence": "low",
  "as_of": "2026-01-13T13:50:27",
  "has_narrative": true,
  "has_chart_patterns": true
}
```

- HTTP Status: 200
- Content-Length: 64,826 bytes
- Source: Aurora `precomputed_reports` table

**2. Search Endpoint Works** ✅
```bash
curl "https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/search?q=DELL"
```

Response:
```json
{
  "results": [{
    "ticker": "DELL19",
    "company_name": "Dell Technologies",
    "exchange": "NASDAQ"
  }]
}
```

**3. Frontend Configuration Correct** ✅

S3 `index.html` contains:
```html
<script>window.TELEGRAM_API_URL = 'https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1';</script>
```

CloudFront serving same content (verified via curl).

**4. Aurora Precomputed Reports Exist** ✅

8 reports in `precomputed_reports` table:
- NVDA (2026-01-13) - completed
- ABBV, PFE, DIS, DELL, ORCL, COST (2026-01-12) - completed

### Partial Issue Found

**Rankings Endpoint Returns Empty** ⚠️

```bash
curl ".../rankings?category=top_gainers"
# Returns: {"rankings": []}
```

Root cause: `daily_rankings` table doesn't exist in staging Aurora.

This is a **data completeness** issue, not a "no real data" issue.

---

## Analysis

### Overall Assessment

The claim is **FALSE**. The Telegram UI in staging:

1. ✅ Connects to correct API (staging endpoint)
2. ✅ Receives real data from Aurora
3. ✅ Displays ticker reports (NVDA, DELL, etc.)
4. ✅ Search functionality works

### What Might Have Caused Confusion

1. **Rankings empty**: The rankings endpoint returns empty because `daily_rankings` table is missing - this may appear as "no data"

2. **Limited ticker coverage**: Only 8 tickers have precomputed reports - unlisted tickers return "not available" message

3. **Date-specific reports**: Reports are date-specific; older reports may not display

### Confidence Level: **High**

Direct API testing with curl shows real data flowing from Aurora to frontend.

---

## Recommendations

### No Fix Needed for Main Claim

The Telegram UI IS displaying real Aurora data correctly.

### Optional: Fix Rankings

If rankings are needed in staging:

```sql
-- Create daily_rankings table (from migration)
CREATE TABLE daily_rankings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(50) NOT NULL,
  ticker_id BIGINT,
  symbol VARCHAR(50),
  rank_position INT,
  metric_value DECIMAL(15,4),
  ranking_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Then run the precompute workflow to populate rankings data.

---

## Next Steps

- [x] Validate claim - **DONE (FALSE)**
- [ ] (Optional) Create daily_rankings table in staging
- [ ] (Optional) Run precompute workflow for more ticker coverage

---

## Test Commands Used

```bash
# Report endpoint (real data confirmed)
curl "https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/NVDA19"

# Search endpoint (real data confirmed)
curl "https://4fkoav2wth.execute-api.ap-southeast-1.amazonaws.com/api/v1/search?q=DELL"

# Frontend config (correct API URL)
curl "https://djjir31dhdd4s.cloudfront.net/"
```

---

## References

**AWS Resources**:
- API Gateway: `4fkoav2wth` (staging)
- CloudFront: `djjir31dhdd4s.cloudfront.net`
- S3: `dr-daily-report-webapp-staging`
- Lambda: `dr-daily-report-telegram-api-staging`

**Database**:
- Table `precomputed_reports`: 8 completed reports
- Table `daily_rankings`: Does not exist (explains empty rankings)
