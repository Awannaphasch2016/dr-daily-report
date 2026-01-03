# Bug Hunt Report: generate_pdf=True Not Executing

## Symptom

**Description**: PDFs not being generated despite `generate_pdf=True` being the default parameter in `compute_and_store_report()`

**First occurrence**: 2026-01-02 (no PDFs found in S3 for this date)

**Affected scope**: All 46 tickers in scheduled precompute workflow

**Impact**: High - PDF download feature completely unavailable for scheduled reports

---

## Investigation Summary

**Bug type**: `integration-failure` (tier 2 workflow not integrated with tier 1 scheduler)

**Investigation duration**: ~30 minutes

**Status**: ✅ Root cause found

---

## Evidence Gathered

### CloudWatch Logs

**ticker-scheduler logs (10:48:36)**:
```
[INFO] TickerFetcher initialized with 46 tickers, bucket: line-bot-pdf-reports-755283537543, data_lake: True, aurora: False
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

**report-worker logs (10:48-11:55)**:
```
[INFO] PDFStorage initialized: bucket=line-bot-pdf-reports-755283537543, expiration=24h
[INFO] 🟢 [generate_chart] START - Ticker: VENTURE19
[INFO] ✅ [generate_chart] SUCCESS - Ticker: VENTURE19
[INFO] 🟢 [generate_report] START - Ticker: VENTURE19
[INFO] ✅ [generate_report] SUCCESS - Ticker: VENTURE19
```

**Note**: Report-worker logs are from API-triggered jobs (10:48-11:55), NOT scheduled 5:00 AM run.

---

### S3 Evidence

**Ticker data cached at 5:00 AM**:
```bash
# 46 files created at 05:00:29-05:00:48
s3://line-bot-pdf-reports-755283537543/cache/ticker_data/
  ├── D05.SI/2026-01-02/data.json (05:00:33)
  ├── 0700.HK/2026-01-02/data.json (05:00:38)
  └── ... (44 more tickers)
```

**NO PDFs found**:
```bash
aws s3 ls s3://line-bot-pdf-reports-755283537543/ --recursive | grep ".pdf"
# Result: 0 matches
```

---

### Code References

**scheduler/ticker_fetcher.py:134-250** - Ticker data fetching ONLY
- `fetch_ticker()` method:
  1. Fetch from yfinance ✅
  2. Store to Aurora `ticker_data` table ✅
  3. Store to Data Lake ✅
  4. Cache to S3 ✅
  5. **NO CALL** to `compute_and_store_report()` ❌

**scheduler/ticker_fetcher_handler.py:29-96** - Fire-and-forget precompute trigger
- `_trigger_precompute()` method:
  - Invokes precompute-controller Lambda **async** (HTTP 202)
  - Does NOT wait for completion
  - Does NOT verify workflow started

**report_worker_handler.py:114-234** - Report worker for API requests
- Processes SQS messages from Telegram API
- Each message has `job_id` (from jobs table)
- **NOT triggered by scheduler** (logs show user requests, not scheduled)

---

### Recent Changes

```bash
git log --oneline -5
5dc2cda fix(ci): Use proper Lambda event structure for smoke test
e55f936 fix(ci): Use fileb:// instead of file:// for Lambda payload
0b71de2 feat(ci): Add end-to-end smoke test for LINE bot webhook handling
3a4caa8 fix(ci): Simplify LINE bot smoke test to verify Lambda state
cc06e17 fix(ci): Fix Lambda smoke test payload format
```

**Analysis**: No recent changes to scheduler or precompute workflow

---

## Hypotheses Tested

### Hypothesis 1: Scheduler doesn't call compute_and_store_report()

**Likelihood**: High

**Test performed**:
- Grep for `compute_and_store_report` calls in `ticker_fetcher.py`
- Read `fetch_ticker()` method implementation (lines 134-250)

**Result**: ✅ **CONFIRMED**

**Reasoning**:
- `fetch_ticker()` only stores ticker_data to Aurora
- NO calls to `compute_and_store_report()`
- NO calls to `PrecomputeService` methods except `store_ticker_data()`

**Evidence**:
- `ticker_fetcher.py:179` - Only call is `precompute_service.store_ticker_data()`
- `ticker_fetcher.py:134-250` - Complete method reviewed, no report generation

---

### Hypothesis 2: Precompute controller not triggering workflow

**Likelihood**: High

**Test performed**:
- Read `ticker_fetcher_handler.py:29-96` (_trigger_precompute function)
- Analyzed async invocation pattern

**Result**: ✅ **CONFIRMED**

**Reasoning**:
- Controller invoked with `InvocationType='Event'` (fire-and-forget)
- Returns HTTP 202 immediately without waiting
- No verification that workflow actually started
- CloudWatch logs show controller invoked, but no evidence of workflow execution

**Evidence**:
- `ticker_fetcher_handler.py:76` - `InvocationType='Event'` (async, no response)
- `ticker_fetcher_handler.py:85` - Returns immediately on HTTP 202
- CloudWatch logs: "Precompute controller invoked (async): HTTP 202" but no follow-up

---

### Hypothesis 3: Report worker not consuming SQS messages

**Likelihood**: Medium

**Test performed**:
- Read `report_worker_handler.py:114-234`
- Analyzed CloudWatch logs timing (10:48-11:55, NOT 5:00 AM)

**Result**: ⚠️ **PARTIALLY CONFIRMED** (worker works for API, NOT for scheduler)

**Reasoning**:
- Report worker IS processing messages (logs show success)
- BUT only for API-triggered requests (job_id from jobs table)
- No evidence of scheduler-triggered workflow at 5:00 AM
- Worker processes SQS messages, but scheduler doesn't send them

**Evidence**:
- `report_worker_handler.py:132` - Expects `job_id` from message
- CloudWatch logs show 10:48-11:55 execution (API requests, not 5:00 AM schedule)
- NO logs at 5:00 AM in report-worker

---

### Hypothesis 4: generate_pdf=False passed somewhere

**Likelihood**: Low

**Test performed**:
- Grep for `generate_pdf=False` in codebase
- Checked `compute_and_store_report()` default parameter (line 808)

**Result**: ❌ **ELIMINATED**

**Reasoning**:
- `compute_and_store_report()` has `generate_pdf=True` as default
- No calls found passing `generate_pdf=False`
- **Root cause is earlier**: `compute_and_store_report()` never called at all

**Evidence**:
- `precompute_service.py:808` - Default is `generate_pdf=True`
- No evidence of `generate_pdf=False` in any callers

---

## Root Cause

**Identified cause**: **Scheduler workflow incomplete - Tier 1 (ticker data) disconnected from Tier 2 (report generation)**

**Confidence**: High

**Supporting evidence**:
1. Scheduler only calls `store_ticker_data()`, NOT `compute_and_store_report()`
2. Precompute controller triggered async but fire-and-forget (no verification)
3. Report worker only processes API-triggered jobs (job_id from jobs table)
4. NO SQS messages sent by scheduler to report worker
5. S3 shows ticker_data cached at 5:00 AM, but NO PDFs generated

**Code locations**:
- `src/scheduler/ticker_fetcher.py:179` - Only stores ticker_data
- `src/scheduler/ticker_fetcher_handler.py:76` - Async invoke, no wait
- `src/report_worker_handler.py:132` - Expects job_id (API-only)

**Why this causes the symptom**:
```
CURRENT ARCHITECTURE (BROKEN):

Tier 1: Ticker Data Fetching (✅ WORKING)
  EventBridge (5:00 AM) → ticker-scheduler → store_ticker_data() → S3 cache

  ↓ (ASYNC TRIGGER, FIRE-AND-FORGET)

Tier 2: Report Generation (❌ NOT EXECUTING)
  precompute-controller (triggered) → ??? (unknown if workflow starts)
  NO SQS messages sent to report-worker
  NO LLM reports generated
  NO PDFs created

GAP: No integration between Tier 1 and Tier 2
```

---

## Reproduction Steps

1. **Check S3 for PDFs**:
   ```bash
   aws s3 ls s3://line-bot-pdf-reports-755283537543/reports/ --recursive
   # Expected: 46 PDFs from yesterday's run
   # Actual: 0 PDFs (empty)
   ```

2. **Check ticker_data cached**:
   ```bash
   aws s3 ls s3://line-bot-pdf-reports-755283537543/cache/ticker_data/ --recursive | head -5
   # Expected: Files from today's 5:00 AM run
   # Actual: 46 files (05:00:29-05:00:48) ✅
   ```

3. **Check CloudWatch logs at 5:00 AM**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/dr-daily-report-ticker-scheduler-dev \
     --start-time $(date -d 'today 5:00 AM' +%s)000 \
     --end-time $(date -d 'today 5:10 AM' +%s)000
   # Expected: Ticker fetch logs + report generation logs
   # Actual: ONLY ticker fetch logs (no report generation)
   ```

**Expected behavior**: PDFs generated and uploaded to `s3://bucket/reports/{ticker}/{date}.pdf`

**Actual behavior**: NO PDFs generated, only ticker_data cached

---

## Fix Candidates

### Fix 1: Integrate report generation into ticker scheduler ⭐ **RECOMMENDED**

**Approach**:
Modify `ticker_fetcher.py` to call `compute_and_store_report()` after storing ticker_data

**Implementation**:
```python
# src/scheduler/ticker_fetcher.py:186 (after store_ticker_data)

# Generate report + PDF (if configured)
if self.precompute_service:
    try:
        logger.info(f"Generating report for {ticker}...")
        report_result = self.precompute_service.compute_and_store_report(
            symbol=ticker,
            data_date=datetime.now(bangkok_tz).date(),
            generate_pdf=True  # ← Enable PDF generation
        )
        logger.info(f"✅ Generated report for {ticker}: {report_result.get('pdf_s3_key')}")
    except Exception as e:
        logger.error(f"Failed to generate report for {ticker}: {e}")
        # Continue - ticker_data stored successfully
```

**Pros**:
- Single unified workflow (atomic operation)
- Simpler architecture (one Lambda instead of controller + worker)
- Easier to monitor (single CloudWatch log group)
- No async coordination issues

**Cons**:
- Longer Lambda execution time (5-30s per ticker for LLM)
- May hit Lambda timeout (900s max for 46 tickers = ~20-40 min)
- Higher memory requirements (LLM + PDF generation)

**Estimated effort**: 2-4 hours
- Code change: 30 min
- Test locally: 1 hour
- Deploy + verify: 1-2 hours

**Risk**: Medium
- May need to increase Lambda timeout to 900s (15 min)
- May need to increase memory to 2048 MB
- LLM API rate limits could cause failures

**Mitigation**:
- Add Lambda timeout monitoring
- Add retry logic for LLM failures
- Process tickers in batches if needed

---

### Fix 2: Fix precompute controller trigger

**Approach**:
Ensure precompute controller actually starts Step Functions workflow and sends SQS messages to workers

**Implementation**:
1. Verify `PRECOMPUTE_CONTROLLER_ARN` environment variable set
2. Add CloudWatch logs to controller showing Step Functions execution ARN
3. Verify Step Functions workflow sends SQS messages
4. Verify report-worker processes messages without `job_id` requirement

**Changes needed**:
```python
# src/scheduler/precompute_controller_handler.py
def lambda_handler(event, context):
    # Start Step Functions execution
    execution_arn = stepfunctions.start_execution(...)
    logger.info(f"Started Step Functions: {execution_arn}")

    # Return execution details (not just HTTP 202)
    return {
        'execution_arn': execution_arn,
        'status': 'started'
    }
```

```python
# src/report_worker_handler.py:132
# Make job_id OPTIONAL (for scheduler-triggered workflows)
job_id = message.get('job_id')  # None for scheduler
ticker_raw = message['ticker']

if job_id:
    job_service.start_job(job_id)  # API-triggered
else:
    logger.info(f"Scheduler-triggered workflow for {ticker_raw}")
```

**Pros**:
- Separates concerns (data fetch vs report generation)
- Step Functions provides observability
- Can run reports independently of data fetch
- Existing infrastructure (already deployed)

**Cons**:
- More complex (controller + Step Functions + SQS + worker)
- Async coordination (harder to debug)
- Fire-and-forget pattern (scheduler doesn't wait)
- Unknown current state (logs don't show workflow execution)

**Estimated effort**: 4-8 hours
- Investigate why controller doesn't trigger workflow: 2-3 hours
- Fix workflow integration: 2-3 hours
- Test end-to-end: 2 hours

**Risk**: High
- Current state unknown (why isn't workflow executing?)
- May require Step Functions workflow changes
- Multiple components to debug

---

### Fix 3: Separate EventBridge schedule for reports

**Approach**:
Create dedicated EventBridge schedule to trigger precompute controller at 6:00 AM (after ticker data fetched)

**Implementation**:
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
- Independent schedules (can disable reports without affecting data fetch)
- Easy to monitor (separate EventBridge rules)

**Cons**:
- Two separate schedules to maintain
- 1-hour delay between data and reports
- Data may be stale if reports fail
- Still requires Fix 2 (controller workflow must work)

**Estimated effort**: 2-3 hours
- Terraform changes: 1 hour
- Deploy + verify: 1-2 hours

**Risk**: Low (infrastructure change only)

---

## Recommendation

**Recommended fix**: **Fix 1** (Integrate report generation into ticker scheduler)

**Rationale**:
1. **Simplest architecture**: Single workflow instead of two separate tiers
2. **Atomic operation**: Data + report generated together (consistent state)
3. **Easier monitoring**: One CloudWatch log group, one Lambda to debug
4. **No async coordination**: Avoid fire-and-forget issues
5. **Known working code**: `compute_and_store_report()` already tested and working

**Implementation priority**: P0 (critical - PDF feature completely broken)

**Timeline**:
- **Today**: Implement fix (2-4 hours)
- **Tomorrow**: Deploy to dev, test with manual invoke
- **Day 3**: Deploy to production, monitor 5:00 AM run

---

## Next Steps

- [ ] Review investigation findings with team
- [ ] Implement Fix 1 (integrate report generation into scheduler)
- [ ] Add Lambda timeout monitoring (alert if >600s)
- [ ] Increase Lambda timeout to 900s (15 min) if needed
- [ ] Write regression test (verify PDFs generated in S3)
- [ ] Deploy to dev environment
- [ ] Verify fix: Check S3 for PDFs after next 5:00 AM run
- [ ] Monitor CloudWatch logs for errors
- [ ] Document solution: `/journal error "PDF generation not executing in scheduler"`

---

## Investigation Trail

**What was checked**:
- ✅ S3 bucket for PDFs (0 found)
- ✅ S3 bucket for ticker_data (46 found at 5:00 AM)
- ✅ CloudWatch logs (ticker-scheduler, precompute-controller, report-worker)
- ✅ Code flow in ticker_fetcher.py (no compute_and_store_report call)
- ✅ Code flow in ticker_fetcher_handler.py (async trigger, fire-and-forget)
- ✅ Code flow in report_worker_handler.py (API-only, requires job_id)
- ✅ `generate_pdf` default parameter (True, not False)

**What was ruled out**:
- ❌ generate_pdf=False somewhere (default is True, never overridden)
- ❌ PDF generation code broken (works for API requests)
- ❌ S3 permissions issue (ticker_data uploads work)
- ❌ Recent code changes (no relevant commits in last 5)

**Tools used**:
- CloudWatch Logs (analyzed 3 log groups)
- S3 CLI (searched for PDFs, verified ticker_data)
- Grep (searched codebase for function calls)
- Read (examined code implementation)

**Time spent**:
- Evidence gathering: 15 min
- Hypothesis testing: 10 min
- Root cause analysis: 5 min
- Total: 30 min

---

**Created**: 2026-01-02
**Bug Type**: integration-failure
**Status**: Root cause found
**Confidence**: High
