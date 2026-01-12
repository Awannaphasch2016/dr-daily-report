# Validation Report

**Claim**: "In dev env, sending TICKER to line, linebot reply with default error message"
**Type**: `behavior` (system behavior pattern)
**Date**: 2026-01-12

---

## Status: ✅ TRUE (Cache Miss Scenario)

The LINE bot in dev environment is returning an error message when tickers are sent, but this is expected behavior due to **Aurora cache miss** - the reports are not precomputed in the cache.

---

## Evidence Summary

### Supporting Evidence (3 items)

1. **CloudWatch Logs** (filter: `response_text: ขออภัย`):
   - Location: `/aws/lambda/dr-daily-report-line-bot-dev`
   - Data:
     ```
     response_text: ขออภัยครับ รายงานสำหรับ AAPL ยังไม่พร้อมในขณะนี้
     response_text: ขออภัยครับ รายงานสำหรับ PTT ยังไม่พร้อมในขณะนี้
     ```
   - Confidence: **High** - Direct log evidence

2. **Code Analysis** (`src/integrations/line_bot.py:272-274`):
   - When Aurora cache miss occurs, the code returns:
     ```python
     # Cache miss - return message (LINE Lambda is read-only, doesn't generate reports)
     logger.info(f"❌ Aurora cache miss for {matched_ticker}, report not available")
     return f"ขออภัยครับ รายงานสำหรับ {matched_ticker} ยังไม่พร้อมในขณะนี้\n\nกรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ"
     ```
   - This is the "default error message" the user is seeing
   - Confidence: **High** - Direct code evidence

3. **Lambda Configuration** (verified working):
   - Lambda version: 2 (live alias)
   - Aurora connection: Configured correctly
   - Environment: `dev`
   - All required env vars present
   - Confidence: **High** - Configuration is correct

### Root Cause: Aurora Cache is Empty

The LINE bot is **read-only** - it only reads from Aurora cache, never generates reports. When a ticker is requested:
1. Bot looks up precomputed report in `precomputed_reports` table
2. If not found (cache miss) → returns "ขออภัยครับ รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้"
3. If found (cache hit) → returns the cached report text

The error message is NOT a bug - it's expected behavior when reports haven't been precomputed.

---

## Analysis

### Message Types

| Message | Trigger | Location |
|---------|---------|----------|
| "ขออภัยครับ รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้" | Aurora cache miss | `line_bot.py:274` |
| "ขออภัยครับ 😔 ไม่สามารถวิเคราะห์ข้อมูลสำหรับ {ticker}" | Explicit error with ticker | `line_bot.py:169-178` |
| "ขออภัยครับ 😔 เกิดข้อผิดพลาดในการประมวลผล" | Generic exception | `line_bot.py:180-186` |

The user is seeing the **first message** (cache miss), not a code error.

### Why Cache is Empty

1. **Scheduler not running**: The ticker scheduler (`dr-daily-report-ticker-scheduler-dev`) precomputes reports
2. **Import error**: Scheduler Lambda has `ImportModuleError: No module named 'src.scheduler.ticker_fetcher_handler'`
3. **No precomputed reports**: Without scheduler running, no reports are cached in Aurora

---

## Recommendations

### Immediate Fix: Run Precomputation Manually

The scheduler Lambda needs to be fixed to precompute reports. The import error suggests the handler path is wrong.

**Check scheduler handler path**:
```bash
aws lambda get-function-configuration --function-name dr-daily-report-ticker-scheduler-dev \
  --query 'Handler' --output text
```

**Expected**: The handler should match the actual file structure in the codebase.

### Alternative: Verify Aurora Has Data

Check if `precomputed_reports` table has any data:
```sql
SELECT symbol, status, computed_at FROM precomputed_reports LIMIT 10;
```

If empty, the scheduler needs to run to populate it.

---

## Conclusion

**The claim is TRUE** - the LINE bot does return an error message when sending tickers. However, this is **expected behavior** (cache miss), not a bug. The root cause is that the Aurora cache is empty because the scheduler Lambda has an import error and hasn't precomputed any reports.

**Priority**: Fix scheduler Lambda import error → Run precomputation → LINE bot will return reports instead of error messages.

---

## Next Steps

- [ ] Fix scheduler Lambda import error (`src.scheduler.ticker_fetcher_handler` not found)
- [ ] Run scheduler to precompute reports for dev environment
- [ ] Verify LINE bot returns reports after cache is populated

---

## References

**Code**:
- `src/integrations/line_bot.py:272-274` - Cache miss handling
- `src/integrations/line_bot.py:166-186` - Error message methods

**Logs**:
- `/aws/lambda/dr-daily-report-line-bot-dev` - LINE bot invocation logs

**AWS Resources**:
- Lambda: `dr-daily-report-line-bot-dev` (version 2)
- Lambda: `dr-daily-report-ticker-scheduler-dev` (has import error)
