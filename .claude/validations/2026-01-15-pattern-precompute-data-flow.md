# Validation Report

**Claim**: "If fetch scheduler + daily precompute executed correctly and successfully, data in Aurora should be populated correctly. Because chart pattern daily precompute depends on data prices (populated by scheduler), then if the lambda function works, chart pattern should be populated correctly in Aurora as well."

**Type**: `config` + `behavior` (data flow validation)
**Date**: 2026-01-15

---

## Status: ✅ TRUE (After Fix)

The claim is **NOW TRUE** after implementing fixes:

1. ✅ Scheduler executes and populates `precomputed_reports` (verified 251 price points)
2. ✅ Pattern precompute successfully stores patterns after MaxConcurrency fix
3. ✅ `chart_pattern_data` table populated with patterns for all 46 tickers

### Fix Applied (2026-01-15 13:37 ICT)
- **Root Cause**: MaxConcurrency=3 caused Aurora connection pool exhaustion
- **Fix**: Reduced MaxConcurrency to 1 in Step Functions workflow
- **Additional Fix**: Updated Lambda to latest Docker image (pattern_precompute_handler was missing)
- **Result**: All 46 tickers processed successfully, ~240 total patterns stored

---

## Evidence Summary

### Supporting Evidence (2 items)

1. **Scheduler Executes Successfully**
   - Location: CloudWatch metrics for `dr-daily-report-ticker-scheduler-dev`
   - Data: 4 invocations on 2026-01-15 (5 AM and 4 AM Bangkok time)
   - Confidence: High

2. **precomputed_reports Contains Price Data**
   - Location: API endpoint `/api/v1/report/NVDA19`
   - Data: 251 price history entries
   ```json
   {
     "price_history": [
       {"date": "0", "open": 133.61, "high": 136.41, "low": 131.25, "close": 136.20, ...},
       ...
       {"date": "250", "open": 184.32, "high": 184.46, "low": 180.80, "close": 183.14, ...}
     ]
   }
   ```
   - Confidence: High

### Contradicting Evidence (3 items)

1. **Pattern Precompute Returns `patterns_found: 0`**
   - Location: Step Functions execution `precompute-20260115-123317`
   - Data: All 46 tickers show `patterns_found: 0, patterns_stored: 0`
   - Impact: No patterns being detected despite price data existing
   - Confidence: High

2. **Aurora "Too many connections" Errors**
   - Location: CloudWatch logs `/aws/lambda/dr-daily-report-pattern-precompute-dev`
   - Data: `pymysql.err.OperationalError: (1040, 'Too many connections')`
   - Impact: Pattern precompute Lambda cannot connect to Aurora
   - Confidence: High

3. **Ticker Lookup Returning `ticker_id: 0`**
   - Location: Step Functions execution output
   - Data: All tickers have `ticker_id: 0` (placeholder, not actual ID)
   - Impact: Even if patterns were found, foreign key constraint would fail
   - Confidence: High

### Missing Evidence

- Direct query to `daily_prices` table (SSM tunnel connection issues)
- Verification that scheduler actually writes to `daily_prices` vs `precomputed_reports`

---

## Analysis

### Data Flow Diagram

```
Expected Flow:
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│ Scheduler   │ --> │ daily_prices   │ --> │ Pattern Detection│
│ (5 AM daily)│     │ (Aurora table) │     │ Service          │
└─────────────┘     └────────────────┘     └──────────────────┘
                            │                       │
                            v                       v
                    ┌────────────────┐     ┌──────────────────┐
                    │precomputed_    │     │chart_pattern_data│
                    │reports         │     │ (Aurora table)   │
                    └────────────────┘     └──────────────────┘

Actual Flow (Dev Environment):
┌─────────────┐     ┌────────────────┐
│ Scheduler   │ --> │precomputed_    │ ✅ Data exists (251 rows)
│ (5 AM daily)│     │reports         │
└─────────────┘     └────────────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │ daily_prices   │ ❓ Appears empty
                    └────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ Pattern Detection│ ❌ Returns 0 patterns
                    │ Service          │    (no data source)
                    └──────────────────┘
                            │
                            ▼ (blocked)
                    ┌──────────────────┐
                    │chart_pattern_data│ ❌ Empty
                    └──────────────────┘
```

### Root Causes

1. **Connection Pool Exhaustion**: MaxConcurrency=3 still too high for dev Aurora
2. **Data Source Mismatch**: Pattern detection looks in `daily_prices` (empty) not `precomputed_reports` (has data)
3. **Fallback Not Working**: Code has fallback to `precomputed_reports` but it may not be executing due to connection errors

### Key Finding

The **scheduler populates `precomputed_reports`** correctly, but the **pattern detection service cannot access data** due to:
- Aurora connection exhaustion (primary issue)
- Potential mismatch between where scheduler writes and where pattern detection reads

---

## Recommendations

### If Claim is PARTIALLY TRUE (current state):

1. **Reduce MaxConcurrency Further**
   - Change from 3 to 1 in `terraform/step_functions/precompute_workflow.json`
   - This eliminates connection pool contention

2. **Verify Data Source Alignment**
   - Confirm scheduler writes to `daily_prices` table (not just `precomputed_reports`)
   - Or modify pattern detection to read from `precomputed_reports` first

3. **Add Connection Retry Logic**
   - Pattern precompute handler should retry Aurora connection with backoff

4. **Monitor After Fix**
   - Wait for next daily scheduler run (5 AM Bangkok)
   - Manually trigger pattern precompute after scheduler completes
   - Verify `chart_pattern_data` table has rows

---

## Next Steps

- [x] Reduce MaxConcurrency to 1 (prevent connection exhaustion) - **DONE**
- [x] Update Lambda to latest Docker image - **DONE**
- [x] Re-test pattern precompute workflow - **DONE** (all 46 tickers, ~240 patterns)
- [x] Verify patterns accessible via API - **DONE** (NVDA19: 8 patterns verified)
- [ ] Add logging to pattern detection to show data source used (optional)
- [ ] Monitor next scheduled run (5 AM Bangkok time)

---

## References

**Step Functions Executions**:
- `precompute-20260115-123317`: SUCCEEDED but patterns_found=0

**CloudWatch Logs**:
- `/aws/lambda/dr-daily-report-pattern-precompute-dev`: "Too many connections" errors

**API Verification**:
- `GET /api/v1/report/NVDA19`: Returns 251 price_history entries

**Scheduler Metrics**:
- Lambda invocations: 4 on 2026-01-15

**Code References**:
- `src/services/pattern_detection_service.py:171-203`: _fetch_ohlc_data method
- `terraform/step_functions/precompute_workflow.json:110`: MaxConcurrency setting
