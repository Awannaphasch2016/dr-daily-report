# Bug Hunt: LINE Bot Returns Error Messages Instead of Reports

**Date**: 2025-12-30
**Type**: production-error
**Severity**: High (User-facing, all tickers failing)
**Status**: Root Cause Identified

---

## Problem Statement

LINE Bot always returns error messages instead of reports when users request ticker analysis.

**User-facing error message** (Thai):
> ขออภัยครับ รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้
>
> กรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ

Translation: "Sorry, report for {ticker} is not ready at this time. Please try again later or contact support."

---

## User Feedback (Critical Correction)

**User statement**:
> "hmm, but we have ticker_alias? and we also have function that resolve ticker alias? what confused me was that using old scheduler, linebot and telegram miniapp work fine, but after new scheduler is used. linebot and telegram miniapp stop working"

**Key insights**:
1. ✅ `ticker_aliases` table EXISTS and has resolution functions
2. ✅ **This is a REGRESSION**: Old scheduler worked, new scheduler broke it
3. ✅ The issue is NOT missing infrastructure, it's a **behavior change**

---

## Investigation Timeline

### Evidence Gathering (Progressive Evidence Strengthening)

**1. Surface Evidence** (Lambda execution logs):
- ✅ LINE Bot Lambda executes successfully (200 status)
- ✅ No ERROR-level logs in LINE Bot
- ✅ No exceptions thrown

**2. Content Evidence** (LINE Bot code analysis):
```python
# src/integrations/line_bot.py:259-274
cached_report = self.precompute.get_cached_report(matched_ticker)

if cached_report:
    # Cache hit - return cached report text from Aurora
    report_text = cached_report.get('report_text')
    logger.info(f"✅ Aurora cache hit for {matched_ticker}")
    return report_text

# Cache miss - return message (LINE Lambda is read-only, doesn't generate reports)
logger.info(f"❌ Aurora cache miss for {matched_ticker}, report not available")
return f"ขออภัยครับ รายงานสำหรับ {matched_ticker} ยังไม่พร้อมในขณะนี้..."
```

**Finding**: LINE Bot returns error when `precomputed_reports` table has no cached report.

**3. Observability Evidence** (Precompute workflow logs):
- ✅ Step Functions workflow: `precompute-20251229-220059` SUCCEEDED
- ✅ 46 tickers submitted to SQS
- ❌ Report workers failing with "Data not available in Aurora"

**4. Step Functions Execution History**:
```json
// Step Functions successfully submitted 46 DR symbols to SQS:
{"ticker": "DBS19", "execution_id": "precompute-20251229-220059"}
{"ticker": "NVDA19", "execution_id": "precompute-20251229-220059"}
{"ticker": "GOLD19", "execution_id": "precompute-20251229-220059"}
// ... 43 more tickers
```

**5. Ground Truth** (Aurora database state):
```bash
# Ticker scheduler populated ticker_data successfully
✅ Stored NVDA to Aurora ticker_data table (250 rows)
✅ Stored D05.SI to Aurora ticker_data table (252 rows)
✅ Stored 1378.HK to Aurora ticker_data table (246 rows)
# ... 46 tickers total (Yahoo symbols)

# But report workers fail
❌ Data not available in Aurora for DBS19
❌ Data not available in Aurora for NVDA19
❌ Data not available in Aurora for GOLD19
# ... all 46 workers fail
```

---

## Root Cause

**Symbol Format Mismatch Between Data Storage and Report Workers**

### Architecture Change Analysis

**Old Scheduler (WORKED)**:
```
EventBridge Rules (disabled)
  ↓
Ticker Fetcher Lambda
  ├─ Loads tickers from CSV: {DBS19: D05.SI, NVDA19: NVDA, ...}
  ├─ Fetches Yahoo data using Yahoo symbols
  └─ Stores to ticker_data with Yahoo symbols (D05.SI, NVDA, ...)
  ↓
(No precompute workflow - reports generated on-demand)
  ↓
LINE Bot requests report
  ├─ Receives DR symbol from user (DBS19)
  ├─ Uses ticker_resolver to resolve DBS19 → D05.SI
  ├─ Queries ticker_data with Yahoo symbol (D05.SI)
  └─ ✅ Data found, report generated
```

**New Scheduler (BROKEN)**:
```
EventBridge Scheduler v2 (active)
  ↓
Ticker Fetcher Lambda (UNCHANGED)
  ├─ Loads tickers from CSV: {DBS19: D05.SI, NVDA19: NVDA, ...}
  ├─ Fetches Yahoo data using Yahoo symbols
  └─ Stores to ticker_data with Yahoo symbols (D05.SI, NVDA, ...)
  ↓
Precompute Controller invoked asynchronously
  ↓
Step Functions Workflow
  ├─ PrepareTickerList: GetTickerList Lambda
  │   ├─ Queries ticker_master + ticker_aliases
  │   └─ Returns DR symbols: [DBS19, NVDA19, GOLD19, ...]
  ├─ FanOutToWorkers: Submit to SQS
  │   └─ 46 messages with DR symbols
  └─ Workers receive DR symbols from SQS
      ├─ Query ticker_data using DR symbol (DBS19)
      ├─ ❌ NOT FOUND (ticker_data has D05.SI, not DBS19)
      └─ Fail with "Data not available in Aurora"
  ↓
LINE Bot requests report
  ├─ Queries precomputed_reports
  └─ ❌ Cache miss (no reports generated) → Error message
```

### Symbol Format Mismatch

**Ticker Fetcher** stores data with Yahoo symbols:
- `NVDA` (US stocks)
- `D05.SI` (Singapore stocks)
- `1378.HK` (Hong Kong stocks)
- `8001.T` (Japan stocks)

**Report Workers** query using DR symbols:
- `NVDA19` → Not found (looking for `NVDA`)
- `DBS19` → Not found (looking for `D05.SI`)
- `GOLD19` → Not found (looking for `1378.HK`)

**Example Error**:
```python
# Report worker tries to fetch data for "DBS19"
❌ Data not available in Aurora for DBS19

# But ticker_data table has:
✅ ticker_data.symbol = "D05.SI" (Yahoo format)
```

---

## Why This Happened

### Architectural Evolution

**Phase 1** (Old Scheduler):
- EventBridge Rules → Ticker Fetcher → CSV-based ticker loading
- Reports generated on-demand by LINE Bot/Telegram Mini App
- Symbol resolution worked: user sends DBS19 → ticker_resolver resolves to D05.SI → query ticker_data

**Phase 2** (New Scheduler with Precompute):
- EventBridge Scheduler v2 → Ticker Fetcher (UNCHANGED) → Precompute Controller → Step Functions
- Reports pre-generated via Step Functions workflow
- **GetTickerList** queries `ticker_master` + `ticker_aliases` for DR symbols
- Workers receive DR symbols but query `ticker_data` with those symbols → MISMATCH

### Missing Symbol Resolution in Workers

**Expected Behavior** (what should happen):
```python
# Report worker receives DR symbol from SQS
dr_symbol = "DBS19"

# SHOULD resolve to Yahoo symbol before querying
from src.data.aurora.ticker_resolver import get_ticker_resolver
resolver = get_ticker_resolver()
ticker_info = resolver.resolve(dr_symbol)  # DBS19 → D05.SI
yahoo_symbol = ticker_info.yahoo_symbol if ticker_info else dr_symbol

# Query ticker_data with Yahoo symbol
ticker_data = precompute_service.get_ticker_data(yahoo_symbol, data_date)
```

**Actual Behavior** (what's happening now):
```python
# Report worker receives DR symbol from SQS
dr_symbol = "DBS19"

# Query ticker_data directly with DR symbol (NO RESOLUTION)
ticker_data = precompute_service.get_ticker_data(dr_symbol, data_date)
# ❌ NOT FOUND → Error: "Data not available in Aurora for DBS19"
```

---

## Regression Analysis

### What Changed

| Component | Old Scheduler | New Scheduler | Impact |
|-----------|--------------|--------------|---------|
| **Ticker Data Storage** | Yahoo symbols | Yahoo symbols | ✅ Same |
| **Report Generation** | On-demand by apps | Pre-generated by workers | ⚠️ Changed |
| **Ticker List Source** | CSV file | Aurora (ticker_master + ticker_aliases) | ⚠️ Changed |
| **Symbol Format Used** | DR → Resolved to Yahoo | DR (not resolved) | ❌ BROKEN |
| **Symbol Resolution** | In apps (ticker_resolver) | ❌ Missing in workers | ❌ BROKEN |

### Why It Worked Before

**Old architecture**: Reports generated on-demand by LINE Bot/Telegram Mini App
- Apps load tickers from CSV: `{DBS19: D05.SI, ...}`
- User sends DR symbol (DBS19)
- App resolves DBS19 → D05.SI using CSV map
- App queries ticker_data with D05.SI → ✅ Found

**Why it works**: Symbol resolution happens in the app before querying Aurora

### Why It Broke After

**New architecture**: Reports pre-generated by Step Functions workflow
- GetTickerList queries Aurora for DR symbols: `[DBS19, NVDA19, ...]`
- Workers receive DR symbols from SQS
- Workers query ticker_data with DR symbols directly → ❌ Not found
- **Missing**: Symbol resolution step (DR → Yahoo)

---

## Fix Strategy

### Option 1: Add Symbol Resolution to Workers (RECOMMENDED) ✅

**Approach**: Workers resolve DR symbols → Yahoo symbols BEFORE querying Aurora

**Changes**:
```python
# src/report_worker_handler.py

from src.data.aurora.ticker_resolver import get_ticker_resolver

async def process_record(record):
    # Extract ticker from SQS message
    dr_ticker = body.get('ticker')  # "DBS19"

    # Resolve to Yahoo symbol
    resolver = get_ticker_resolver()
    ticker_info = resolver.resolve(dr_ticker)
    yahoo_ticker = ticker_info.yahoo_symbol if ticker_info else dr_ticker  # "D05.SI"

    logger.info(f"Resolved {dr_ticker} → {yahoo_ticker}")

    # Use yahoo_ticker for all Aurora queries
    agent_result = await agent.run(ticker=yahoo_ticker, ...)
```

**Pros**:
- ✅ Minimal change (10-20 lines)
- ✅ Uses existing ticker_resolver (already works)
- ✅ Consistent with how apps resolve symbols
- ✅ No database schema changes

**Cons**:
- ❌ Depends on ticker_resolver being populated (ticker_master + ticker_aliases)

**Risk**: Low (ticker_resolver has fallback to CSV)

### Option 2: Change GetTickerList to Return Yahoo Symbols

**Approach**: GetTickerList returns Yahoo symbols instead of DR symbols

**Changes**:
```python
# src/scheduler/get_ticker_list_handler.py

query = """
    SELECT DISTINCT a.symbol
    FROM ticker_master m
    JOIN ticker_aliases a ON m.id = a.ticker_id
    WHERE m.is_active = TRUE
      AND a.symbol_type = 'yahoo'  -- Changed from 'dr'
    ORDER BY a.symbol
"""
```

**Pros**:
- ✅ No changes to workers
- ✅ Symbols match ticker_data format

**Cons**:
- ❌ Breaks Step Functions assumption (expects DR symbols)
- ❌ Would need to update DynamoDB jobs table schema
- ❌ Breaks user-facing job IDs (currently use DR symbols)

**Risk**: Medium (requires coordination across multiple components)

### Option 3: Store to ticker_data with DR Symbols

**Approach**: Change Ticker Fetcher to store with DR symbols instead of Yahoo symbols

**Changes**:
```python
# src/scheduler/ticker_fetcher.py

# Load ticker map
ticker_map = self.data_fetcher.load_tickers()  # {DBS19: D05.SI}

for dr_symbol, yahoo_symbol in ticker_map.items():
    # Fetch with Yahoo symbol
    data = yf.Ticker(yahoo_symbol).history(...)

    # Store with DR symbol (changed)
    self.precompute_service.store_ticker_data(
        symbol=dr_symbol,  # Changed from yahoo_symbol
        ...
    )
```

**Pros**:
- ✅ No changes to workers or GetTickerList
- ✅ Consistent symbol format throughout

**Cons**:
- ❌ Changes data storage format (breaking change)
- ❌ Requires migration of existing ticker_data
- ❌ Yahoo symbol information lost (need to store separately)

**Risk**: High (affects fundamental data storage)

---

## Recommended Fix

**Immediate Fix**: **Option 1** - Add symbol resolution to workers

**Why**:
1. **Lowest risk** - Uses existing, working ticker_resolver
2. **Fastest** - 10-20 lines of code
3. **No breaking changes** - Doesn't affect data storage or Step Functions
4. **Fallback exists** - ticker_resolver falls back to CSV if Aurora tables empty

**Implementation**:
```python
# File: src/report_worker_handler.py

# Add at top
from src.data.aurora.ticker_resolver import get_ticker_resolver

# In handler function, before calling agent
async def process_record(record):
    # Extract ticker from SQS message
    dr_ticker = body.get('ticker')  # "DBS19"

    # Resolve to Yahoo symbol
    resolver = get_ticker_resolver()
    ticker_info = resolver.resolve(dr_ticker)
    yahoo_ticker = ticker_info.yahoo_symbol if ticker_info else dr_ticker

    logger.info(f"Resolved {dr_ticker} → {yahoo_ticker}")

    # Use yahoo_ticker for all Aurora queries
    agent_result = await agent.run(ticker=yahoo_ticker, ...)
```

**Testing**:
```bash
# 1. Deploy fix to dev
git add src/report_worker_handler.py
git commit -m "fix: Resolve DR symbols to Yahoo symbols in report worker"
git push origin dev

# 2. Trigger precompute workflow manually
ENV=dev doppler run -- aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --payload '{"limit": 5}' \
  response.json

# 3. Wait 5-10 minutes, check DynamoDB jobs table
ENV=dev doppler run -- aws dynamodb scan \
  --table-name dr-daily-report-telegram-jobs-dev \
  --filter-expression "#st = :status" \
  --expression-attribute-names '{"#st":"status"}' \
  --expression-attribute-values '{":status":{"S":"completed"}}' \
  --select COUNT

# 4. Test LINE Bot with test message
# Send "DBS19" to LINE Bot → Should receive report, not error
```

---

## Validation Criteria

**Success Metrics**:
1. ✅ Report workers complete successfully (no "Data not available" errors)
2. ✅ `precomputed_reports` table populated with 46 rows
3. ✅ LINE Bot returns reports instead of error messages
4. ✅ CloudWatch logs show "Cache HIT" instead of "Cache MISS"

**Failure Indicators**:
- ❌ Report workers still fail with symbol resolution errors
- ❌ `precomputed_reports` table remains empty
- ❌ LINE Bot still returns error messages

---

## Related Documents

- **Understanding**: `.claude/understanding-2025-12-30-ticker-info-usage-by-apps.md` (How apps use ticker metadata)
- **Understanding**: `.claude/understanding-2025-12-30-scheduler-storage-tables.md` (Which tables scheduler writes to)
- **Refactoring**: `.claude/skills/refacter/SUMMARY-enable-aurora-refactoring.md` (ticker_info legacy path)
- **Validation**: `.claude/validations/2025-12-30-ticker-info-data-populated.md` (ticker_info population status)
- **Validation**: `.claude/validations/2025-12-30-both-schedulers-deployed.md` (Scheduler migration timeline)

---

## Lessons Learned

1. **Symbol Format Consistency**: When multiple components interact (scheduler, workers, apps), ensure consistent symbol format across the entire data pipeline.

2. **Regression Testing**: New architecture changes (on-demand → pre-generated reports) require testing all integration points, not just new code.

3. **Explicit Symbol Resolution**: Don't assume symbol resolution happens automatically - must be explicit at integration boundaries.

4. **CSV vs Database**: Using CSV file as source of truth worked for LINE Bot and Telegram Mini App (on-demand generation), but caused symbol mismatch when report workers tried to use Aurora directly.

5. **Step Functions + Aurora Integration**: When Step Functions workflow queries Aurora for ticker list, and workers query Aurora for ticker data, **symbol formats must match** at all stages.

---

**Bug Hunt Completed**: 2025-12-30
**Next Step**: Implement Option 1 fix (add symbol resolution to workers) and deploy to dev for testing
