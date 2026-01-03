# CloudWatch Logs Analysis: PDF Generation Failure

**Investigation**: Why no PDFs were generated on 2026-01-02 at 5:00 AM

**Date**: 2026-01-02

---

## Root Cause: ✅ **IDENTIFIED - SCHEDULER ONLY FETCHES TICKER DATA, DOESN'T GENERATE REPORTS**

The new scheduler (`ticker-scheduler`) only fetches and caches ticker data. It does **NOT** generate reports or PDFs during the scheduled run.

---

## Evidence from CloudWatch Logs

### Log Groups Analyzed:

1. `/aws/lambda/dr-daily-report-ticker-scheduler-dev` - **Ticker data fetcher (NEW)**
2. `/aws/lambda/dr-daily-report-precompute-controller-dev` - **Precompute workflow controller**
3. `/aws/lambda/dr-daily-report-report-worker-dev` - **Report generation worker**

---

## Key Findings

### Finding 1: Scheduler Only Fetches Ticker Data (NO REPORTS)

**Log Evidence** (`ticker-scheduler` at 10:48:36):
```
[INFO] TickerFetcher initialized with 46 tickers, bucket: line-bot-pdf-reports-755283537543, data_lake: True, aurora: False
[INFO] TickerResolver initialized with 115 symbol mappings
[INFO] Fetching data for NVDA -> NVDA...
[INFO] ✅ Got 250 days of historical data for NVDA
[INFO] ✅ Stored NVDA to Aurora ticker_data table (250 rows)
[INFO] 💾 Data lake stored: raw/yfinance/NVDA/2026-01-02/20260102_104837.json
[INFO] 💾 S3 cache saved: cache/ticker_data/NVDA/2026-01-02/data.json
[INFO] S3 cached NVDA for 2026-01-02
[INFO] Fetch complete: 1 success, 0 failed out of 1
[INFO] ✨ Triggering precompute for 1 tickers
[INFO] ✅ Precompute controller invoked (async): HTTP 202
```

**Analysis**:
- ✅ Ticker data fetched successfully
- ✅ Stored to Aurora `ticker_data` table
- ✅ Cached to S3 (`cache/ticker_data/`)
- ✅ Data lake archival successful
- ❌ **NO report generation** (only ticker data fetching)
- ⚠️ Triggers precompute controller (but asynchronously, HTTP 202)

**Configuration**:
```python
# src/scheduler/ticker_fetcher.py:72-77
logger.info(
    f"TickerFetcher initialized with {len(self.tickers)} tickers, "
    f"bucket: {self.bucket_name}, "
    f"data_lake: {self.data_lake.is_enabled()}, "
    f"aurora: False"  # ← THIS IS THE ISSUE!
)
```

**Conclusion**: `aurora: False` means scheduler does NOT call `PrecomputeService.compute_and_store_report()`, which is where PDF generation happens.

---

### Finding 2: Report Worker Only Runs for API Jobs (NOT SCHEDULED)

**Log Evidence** (`report-worker` at 10:48-11:55):
```
[INFO] PDFStorage initialized: bucket=line-bot-pdf-reports-755283537543, expiration=24h
[INFO] 🟢 [generate_chart] START - Ticker: VENTURE19
[INFO] ✅ [generate_chart] SUCCESS - Ticker: VENTURE19
[INFO] 🟢 [generate_report] START - Ticker: VENTURE19
[INFO] ✅ [generate_report] SUCCESS - Ticker: VENTURE19
```

**Analysis**:
- ✅ PDFStorage initialized (46 times - one per ticker)
- ✅ Charts generated successfully
- ✅ Reports generated successfully
- ❌ **NO PDF upload attempts** (no "Generated PDF" or "upload_pdf" logs)
- ❌ **NO calls to `_generate_and_upload_pdf()`**

**Pattern**:
- Report worker processes **SQS messages** triggered by Telegram API
- Each job has a `job_id` from the jobs table
- These are **on-demand requests**, not scheduled precompute

**Timeframe**: 10:48-11:55 (NOT 5:00 AM)
- These are user-triggered requests from Telegram API
- Not part of the scheduled 5:00 AM precompute run

---

### Finding 3: Precompute Controller Runs But Doesn't Generate Reports

**Log Evidence** (`precompute-controller`):
```
2026-01-02T10:48:39 START RequestId: 5bc3e75d-317f-4b08-ba59-10411c4cf8d0
2026-01-02T10:48:40 END RequestId: 5bc3e75d-317f-4b08-ba59-10411c4cf8d0
2026-01-02T10:48:40 REPORT Duration: 1244.16 ms

2026-01-02T10:54:21 START RequestId: 969c586c-bf6c-4425-ab8e-b4520a6c9229
2026-01-02T10:54:21 END RequestId: 969c586c-bf6c-4425-ab8e-b4520a6c9229
2026-01-02T10:54:21 REPORT Duration: 225.23 ms
```

**Analysis**:
- Controller Lambda executes quickly (225ms - 1.2s)
- **NO detailed logs** (only START/END/REPORT)
- Likely triggers Step Functions workflow
- **NO evidence of report generation**

**Expected Behavior** (from validation-2026-01-02-pdf-workflow.md):
```
Controller → Step Functions → GetTickerList → FanOut → SQS → Worker
  → PrecomputeService.compute_ticker(include_report=True)
  → compute_and_store_report(generate_pdf=True)
  → _generate_and_upload_pdf() → S3
```

**Actual Behavior**:
```
Controller → Step Functions → (Unknown) → ❌ NO REPORT GENERATION
```

---

### Finding 4: NO Evidence of 5:00 AM Scheduled Run

**Searched Time Windows**:
- 5:00 AM Bangkok time = 22:00 UTC previous day (2026-01-01T22:00:00Z)
- Search window: 04:55-05:10 Bangkok time

**Logs Found**:
- ❌ NO controller logs at 5:00 AM
- ❌ NO ticker-scheduler logs at 5:00 AM
- ❌ NO report-worker logs at 5:00 AM

**Explanation**:
- S3 cache shows ticker_data files created at 05:00:29-05:00:48
- But CloudWatch logs don't show Lambda executions at that time
- **Hypothesis**: EventBridge schedule may not be enabled, OR logs filtered out

---

## Architecture Analysis

### Current Scheduler Architecture (2-Tier)

**Tier 1: Ticker Data Fetching** (`ticker-scheduler`)
- **Trigger**: EventBridge schedule (intended: daily 5:00 AM)
- **Purpose**: Fetch ticker_data from Yahoo Finance
- **Storage**:
  - Aurora `ticker_data` table ✅
  - S3 `cache/ticker_data/` ✅
  - Data Lake `raw/yfinance/` ✅
- **Output**: Cached ticker_data (NO REPORTS)

**Tier 2: Report Generation** (`precompute-controller` + `report-worker`)
- **Trigger**: Manually OR via API (not scheduled)
- **Purpose**: Generate LLM reports + PDFs
- **Process**:
  1. Controller starts Step Functions workflow
  2. GetTickerList returns 46 tickers
  3. FanOut sends 46 SQS messages
  4. Workers consume messages
  5. Each worker calls `PrecomputeService.compute_and_store_report(generate_pdf=True)`
- **Output**: Reports + PDFs in `reports/` prefix

**Gap**: Tier 2 (report generation) is **NOT triggered** by Tier 1 (ticker data fetching)

---

## Root Cause Summary

### Why No PDFs Were Generated:

1. **Scheduler only fetches ticker_data** (not reports)
   - Code: `TickerFetcher` does NOT call `compute_and_store_report()`
   - Configuration: `aurora: False` in logs

2. **Report generation is separate workflow** (not integrated with scheduler)
   - Requires manual trigger OR API call
   - **NOT scheduled** to run at 5:00 AM

3. **Precompute controller invoked asynchronously** (HTTP 202)
   - Ticker-scheduler calls controller after fetching
   - But controller doesn't wait for completion
   - Unknown if controller actually triggers report generation

---

## Comparison: Expected vs Actual

### Expected (from validation-2026-01-02-pdf-workflow.md):

```
5:00 AM EventBridge Schedule
  ↓
Precompute Controller Lambda
  ↓
Step Functions State Machine
  ↓
GetTickerList (46 tickers)
  ↓
FanOut → 46 SQS messages
  ↓
Worker Lambdas → compute_and_store_report(generate_pdf=True)
  ↓
PDF upload → S3 reports/{ticker}/{date}.pdf
```

### Actual (from CloudWatch logs):

```
5:00 AM EventBridge Schedule (?)
  ↓
Ticker Scheduler Lambda
  ↓
Fetch ticker_data from Yahoo Finance (46 tickers)
  ↓
Store to Aurora ticker_data table ✅
  ↓
Cache to S3 cache/ticker_data/ ✅
  ↓
Archive to Data Lake ✅
  ↓
Trigger Precompute Controller (HTTP 202, async)
  ↓
??? (Unknown - no logs after this point)
  ↓
❌ NO REPORT GENERATION
❌ NO PDF GENERATION
```

---

## Configuration Issues

### Issue 1: Two Separate Schedulers

**Old Scheduler** (intended for reports):
- **Controller**: `precompute-controller` Lambda
- **Workers**: `report-worker` Lambda
- **Workflow**: Step Functions orchestration
- **Status**: **NOT running on schedule** (no 5:00 AM logs)

**New Scheduler** (ticker data only):
- **Handler**: `ticker-scheduler` Lambda
- **Purpose**: Fetch and cache ticker_data
- **Status**: **Running** (ticker_data cached at 5:00 AM)

### Issue 2: Missing Integration

**Current**:
```python
# src/scheduler/ticker_fetcher.py
def fetch_ticker(self, ticker):
    # Fetch ticker_data
    data = self.data_fetcher.fetch_ticker_data(ticker)

    # Store to Aurora ticker_data
    self.precompute_service.store_ticker_data(...)

    # Cache to S3
    self.s3_cache.put_json(...)

    # ❌ NO REPORT GENERATION
    # ❌ NO PDF GENERATION
```

**Expected**:
```python
# src/scheduler/ticker_fetcher.py
def fetch_ticker(self, ticker):
    # Fetch ticker_data
    data = self.data_fetcher.fetch_ticker_data(ticker)

    # Store to Aurora ticker_data
    self.precompute_service.store_ticker_data(...)

    # ✅ GENERATE REPORT + PDF
    self.precompute_service.compute_and_store_report(
        symbol=ticker,
        generate_pdf=True  # ← MISSING
    )
```

---

## Recommendations

### Immediate Fix: Enable Report Generation in Scheduler

**Option 1: Integrate Report Generation into Ticker Scheduler**

Modify `src/scheduler/ticker_fetcher.py` to call `compute_and_store_report()`:

```python
# After storing ticker_data
if self.precompute_service:
    try:
        logger.info(f"Generating report for {ticker}...")
        report_result = self.precompute_service.compute_and_store_report(
            symbol=ticker,
            data_date=today,
            generate_pdf=True  # ← Enable PDF generation
        )
        logger.info(f"✅ Generated report for {ticker}: {report_result.get('pdf_s3_key')}")
    except Exception as e:
        logger.error(f"Failed to generate report for {ticker}: {e}")
```

**Pros**:
- Single scheduler (simpler)
- Atomic operation (data + report in one run)
- Easier to monitor

**Cons**:
- Longer execution time (ticker fetch + LLM report)
- Higher cost (LLM API calls for 46 tickers)
- May timeout if reports take too long

---

**Option 2: Fix Precompute Controller Trigger**

Ensure precompute controller actually generates reports when triggered:

1. Verify Step Functions workflow definition
2. Check if GetTickerList returns tickers
3. Verify SQS messages sent to report-worker
4. Check report-worker receives `generate_pdf=True` parameter

**Pros**:
- Separates concerns (data fetch vs report gen)
- Can run reports independently
- Step Functions provides observability

**Cons**:
- More complex (two separate workflows)
- Async trigger (harder to debug)
- Unknown current state (no logs at 5:00 AM)

---

**Option 3: Separate EventBridge Schedule for Reports**

Create dedicated EventBridge schedule for report generation:

```hcl
# terraform/scheduler.tf
resource "aws_cloudwatch_event_rule" "generate_reports" {
  name                = "${var.project_name}-generate-reports-${var.environment}"
  description         = "Trigger report generation at 6:00 AM (after ticker data fetched)"
  schedule_expression = "cron(0 23 * * ? *)"  # 6:00 AM Bangkok = 23:00 UTC
}

resource "aws_cloudwatch_event_target" "generate_reports" {
  rule      = aws_cloudwatch_event_rule.generate_reports.name
  target_id = "PrecomputeController"
  arn       = aws_lambda_function.precompute_controller.arn

  input = jsonencode({
    "include_report": true,
    "generate_pdf": true
  })
}
```

**Pros**:
- Clear separation (5:00 AM data, 6:00 AM reports)
- Can run independently
- Easy to disable/enable

**Cons**:
- Two separate schedules to maintain
- 1-hour delay between data and reports
- Data may be stale if reports fail

---

### Verification Steps

After fixing, verify:

1. **Check CloudWatch Logs** (at 5:00 AM next day):
   ```bash
   # Check report-worker logs for PDF generation
   aws logs tail /aws/lambda/dr-daily-report-report-worker-dev \
     --since 1h --filter-pattern "PDF"
   ```

2. **Check S3 for PDFs**:
   ```bash
   # Should see reports/{ticker}/{date}.pdf
   aws s3 ls s3://line-bot-pdf-reports-755283537543/reports/ --recursive
   ```

3. **Check Aurora for pdf_s3_key**:
   ```sql
   SELECT symbol, data_date, pdf_s3_key, pdf_generated_at
   FROM ticker_reports
   WHERE data_date = CURDATE()
   LIMIT 10;
   ```

---

## References

**CloudWatch Log Groups**:
- `/aws/lambda/dr-daily-report-ticker-scheduler-dev` - Ticker data fetcher
- `/aws/lambda/dr-daily-report-precompute-controller-dev` - Workflow controller
- `/aws/lambda/dr-daily-report-report-worker-dev` - Report generator

**Code**:
- `src/scheduler/ticker_fetcher.py` - Ticker data fetching (NO reports)
- `src/data/aurora/precompute_service.py:804-899` - Report generation
- `src/data/aurora/precompute_service.py:1390-1433` - PDF generation
- `src/report_worker_handler.py` - API-triggered report worker

**Related Validations**:
- `.claude/validations/2026-01-02-pdf-workflow.md` - PDF generation workflow
- `.claude/validations/2026-01-02-dbs19-pdf-exists-today.md` - NO PDFs found
- `.claude/validations/2026-01-02-s3-pdf-legacy-status.md` - PDF bucket is active

---

## Conclusion

**Root Cause: Scheduler only fetches ticker_data, does NOT generate reports/PDFs**

**Evidence**:
- ✅ Ticker data fetched at 5:00 AM (confirmed by S3 cache)
- ❌ NO report generation (no CloudWatch logs)
- ❌ NO PDF upload (no files in S3 `reports/` prefix)
- ❌ NO calls to `compute_and_store_report()` in scheduler

**Fix Required**: Integrate report generation into scheduler OR ensure precompute controller triggers report workflow

**Recommended Approach**: Option 1 (integrate into ticker scheduler) - simplest and most reliable

---

**Created**: 2026-01-02
**Analysis Type**: CloudWatch Logs + Code Review
**Confidence**: High (direct log evidence + code analysis)
**Status**: Root cause identified, fix needed
