# Validation Report

**Claim**: "When sending TICKER, LINE Bot responds with error default message"
**Type**: behavior (system response to user input)
**Date**: 2026-01-13

---

## Status: 🤔 INCONCLUSIVE

Cannot definitively validate the claim due to lack of real user request logs with valid LINE signatures.

---

## Evidence Summary

### Evidence Available

**1. Code Analysis** - Shows multiple error paths:

| Error Path | Condition | Message |
|------------|-----------|---------|
| Cache miss | Report not precomputed | "ขออภัยครับ รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้" |
| Exception in handle_message | Any error | `get_error_message()` - generic error |
| Exception in event handling | Any error | `get_error_message()` - generic error |

Source: `src/integrations/line_bot.py:258-278`, `src/integrations/line_bot.py:339-342`

**2. Precomputed Reports Exist** (8 reports found):
```
NVDA - completed - 2026-01-13
ABBV - completed - 2026-01-12
PFE  - completed - 2026-01-12
DIS  - completed - 2026-01-12
DELL - completed - 2026-01-12
ORCL - completed - 2026-01-12
COST - completed - 2026-01-12
```

Source: Aurora `precomputed_reports` table

**3. Lambda Import Error FIXED**:
- Previous: `IMPORT_ERROR: cannot import name 'handle_webhook'`
- Current: Lambda responds with "Invalid signature" (correct behavior for test requests)
- Fix: Updated Lambda to use image `staging-20260110142903`

**4. Cache Lookup Logic Appears Correct**:
```python
# get_cached_report() resolves ticker to all aliases
# Example: "NVDA19" → searches for "NVDA19", "NVDA", ticker_id
```

Source: `src/data/aurora/precompute_service.py:1381-1408`

### Evidence NOT Available

1. **No real user requests logged** - All CloudWatch logs show test requests with invalid signatures
2. **No "Signature verified" entries** - Indicates no legitimate LINE webhook calls in past 7 days
3. **No cache lookup logs** - No evidence of actual ticker lookups being performed

---

## Analysis

### Possible Causes for Error Response

1. **Cache Miss** (Most Likely for Untested Tickers):
   - Only 8 tickers have precomputed reports
   - If user sends unlisted ticker (e.g., "AAPL19"), cache lookup returns None
   - Response: "รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้"

2. **Fuzzy Match Failure**:
   - If input is too short (e.g., "19"), fuzzy matcher may not find good match
   - Returns input as-is, which likely won't have a cached report

3. **Aurora Connection Error**:
   - If PrecomputeService fails to connect to Aurora, exception triggers `get_error_message()`

4. **Date Mismatch**:
   - Precomputed reports are date-specific
   - If today's report doesn't exist but yesterday's does, cache miss occurs

### Key Finding

The LINE Bot code looks correct for cache lookup. The "error default message" is likely the **cache miss message**, not the generic error message - which is expected behavior when:
- User requests ticker without precomputed report
- Reports are date-specific and today's hasn't been generated yet

---

## Recommendations

### To Definitively Validate

1. **Test with Real LINE Request**:
   ```bash
   # Send "NVDA19" via actual LINE app to staging webhook
   # Check CloudWatch for "Cache lookup" and "Cache HIT/MISS" logs
   ```

2. **Check Report Date Currency**:
   ```sql
   SELECT symbol, report_date, computed_at
   FROM precomputed_reports
   WHERE symbol = 'NVDA' AND report_date = CURDATE()
   ```

3. **Trigger Precompute Workflow**:
   - If today's reports don't exist, the "error" is expected behavior
   - Run precompute workflow to generate fresh reports

### If Cache Miss is Confirmed

This is **expected behavior**, not a bug. The message should be:
> "ขออภัยครับ รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้"

This indicates the report hasn't been precomputed, not a system error.

### If Generic Error is Confirmed

Check for Aurora connection issues or exceptions in the code path.

---

## Next Steps

- [ ] Send real ticker request via LINE app to staging
- [ ] Check CloudWatch for cache lookup logs
- [ ] Verify precompute workflow is running daily for staging
- [ ] Distinguish between "cache miss" (expected) vs "error" (bug)

---

## References

**Code**:
- `src/integrations/line_bot.py:258-278` - handle_message cache lookup
- `src/data/aurora/precompute_service.py:1348-1408` - get_cached_report implementation

**AWS Resources**:
- Lambda: `dr-daily-report-line-bot-staging`
- Image: `staging-20260110142903`
- CloudWatch: `/aws/lambda/dr-daily-report-line-bot-staging`

**Database**:
- Table: `precomputed_reports` (8 reports found)
