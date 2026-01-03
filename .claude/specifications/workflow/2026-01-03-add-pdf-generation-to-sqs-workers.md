---
title: Add PDF Generation to SQS Workers (Option A)
focus: workflow
date: 2026-01-03
status: draft
tags: [pdf-generation, sqs-workers, bug-fix]
related_bug_hunt: .claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md
related_validation: .claude/validations/2026-01-02-sqs-workers-generate-pdfs.md
---

# Workflow Specification: Add PDF Generation to SQS Workers (Option A)

## Goal

**What does this workflow accomplish?**

Fix PDF generation for scheduled precompute workflow by adding PDF generation step to existing SQS workers after LLM report completion.

**Problem**: SQS workers currently use `store_report_from_api()` which explicitly sets `pdf_s3_key=None`. Workers generate LLM reports but skip PDF generation.

**Solution**: Add PDF generation step after LLM report generation, before storing to Aurora.

---

## Current Workflow (Broken)

```
EventBridge (5:00 AM)
  ↓
ticker-scheduler Lambda
  ↓
Async invoke → precompute-controller Lambda
  ↓
Step Functions State Machine (GetTickerList → Map)
  ↓
SQS messages (46 tickers)
  ↓
report-worker Lambda (processes SQS)
  ↓
Run TickerAnalysisAgent (LLM report)  ← 5-30 seconds
  ↓
Transform result to API format
  ↓
Store to DynamoDB jobs table (if job_id exists)
  ↓
Cache to Aurora (store_report_from_api)  ← pdf_s3_key=None ❌
```

**Problem**: Workers skip PDF generation because they use API code path (`store_report_from_api()`)

---

## Proposed Workflow (Fixed)

```
EventBridge (5:00 AM)
  ↓
ticker-scheduler Lambda
  ↓
Async invoke → precompute-controller Lambda
  ↓
Step Functions State Machine (GetTickerList → Map)
  ↓
SQS messages (46 tickers)
  ↓
report-worker Lambda (processes SQS)
  ↓
Run TickerAnalysisAgent (LLM report)  ← 5-30 seconds
  ↓
Transform result to API format
  ↓
[NEW] Generate PDF from LLM report  ← +1-2 seconds ✅
  ↓
[NEW] Upload PDF to S3  ← +0.5-1 second ✅
  ↓
Store to DynamoDB jobs table (if job_id exists)
  ↓
Cache to Aurora (store_report_from_api)  ← [MODIFIED] Include pdf_s3_key ✅
```

**Fix**: Add PDF generation step after LLM report, before Aurora cache

---

## Implementation Details

### File to Modify

**Location**: `src/report_worker_handler.py`

**Function**: `lambda_handler()` (lines 114-234)

**Insertion point**: After line 215 (after `transform_report()`, before storing to Aurora)

---

### Code Changes

#### Change 1: Add PDF Generation After LLM Report

**Location**: `src/report_worker_handler.py:215` (AFTER `transform_report()`)

**Add new section**:

```python
# ========================================
# STEP 4.5: Generate PDF (for scheduled workflows)
# ========================================
# Context: Workers are triggered by:
#   1. Telegram API requests (user-initiated) - job_id exists, no PDF needed
#   2. Scheduled workflows (Step Functions) - no job_id, PDF needed
#
# Strategy: Generate PDF if:
#   - No job_id (scheduled workflow), OR
#   - Message explicitly requests PDF (generate_pdf flag)
#
# Graceful degradation: If PDF fails, continue without it (report is still valid)

pdf_s3_key = None
pdf_generated_at = None

should_generate_pdf = (
    not job_id or  # Scheduled workflow (no job_id from API)
    message.get('generate_pdf', False)  # Explicit flag in SQS message
)

if should_generate_pdf and final_state.get('report'):
    try:
        logger.info(f"📄 Generating PDF for {ticker}...")

        from src.data.aurora.precompute_service import PrecomputeService
        from datetime import datetime, date

        ps = PrecomputeService()

        # Generate and upload PDF using existing method
        pdf_s3_key = ps._generate_and_upload_pdf(
            symbol=ticker,
            data_date=date.today(),
            report_text=final_state.get('report', ''),
            chart_base64=final_state.get('chart_base64', '')
        )

        if pdf_s3_key:
            pdf_generated_at = datetime.now()
            logger.info(f"✅ Generated PDF: {pdf_s3_key}")
        else:
            logger.warning(f"⚠️ PDF generation returned None for {ticker}")

    except Exception as e:
        logger.warning(f"⚠️ PDF generation failed for {ticker}: {e}")
        # Continue without PDF - report is still valid
        # Don't re-raise - graceful degradation

else:
    if not final_state.get('report'):
        logger.info(f"ℹ️ Skipping PDF generation (no report text) for {ticker}")
    else:
        logger.info(f"ℹ️ Skipping PDF generation (API request, job_id={job_id}) for {ticker}")
```

**Why this works**:
- ✅ Uses existing `_generate_and_upload_pdf()` method (no code duplication)
- ✅ PDF generated AFTER LLM report (no duplicate LLM calls)
- ✅ Graceful degradation (report succeeds even if PDF fails)
- ✅ Optional (only for scheduled workflows or if flag set)
- ✅ Clear logging for debugging

---

#### Change 2: Update Aurora Cache Call to Include PDF

**Location**: `src/report_worker_handler.py:221` (store_report_from_api call)

**Current code**:
```python
cache_result = precompute_service.store_report_from_api(
    symbol=ticker,
    report_text=result.get('narrative_report', ''),
    report_json=result,
    chart_base64=final_state.get('chart_base64', ''),
)
```

**Problem**: `store_report_from_api()` doesn't accept `pdf_s3_key` parameter

**Solution**: Need to modify `store_report_from_api()` signature to accept optional PDF parameters

---

#### Change 3: Modify store_report_from_api() to Accept PDF Parameters

**Location**: `src/data/aurora/precompute_service.py:991-1057`

**Current signature** (line 999):
```python
def store_report_from_api(
    self,
    symbol: str,
    report_text: str,
    report_json: dict,
    chart_base64: str = ''
) -> dict:
```

**New signature**:
```python
def store_report_from_api(
    self,
    symbol: str,
    report_text: str,
    report_json: dict,
    chart_base64: str = '',
    pdf_s3_key: Optional[str] = None,        # [ADDED]
    pdf_generated_at: Optional[datetime] = None  # [ADDED]
) -> dict:
```

**Current call to _store_completed_report** (lines 1043-1044):
```python
rowcount = self._store_completed_report(
    ticker_id=ticker_id,
    symbol=yahoo_symbol,
    data_date=data_date,
    report_text=report_text,
    report_json=report_json,
    generation_time_ms=generation_time_ms,
    chart_base64=chart_base64,
    pdf_s3_key=None,          # ← HARDCODED None
    pdf_generated_at=None,    # ← HARDCODED None
)
```

**Modified call**:
```python
rowcount = self._store_completed_report(
    ticker_id=ticker_id,
    symbol=yahoo_symbol,
    data_date=data_date,
    report_text=report_text,
    report_json=report_json,
    generation_time_ms=generation_time_ms,
    chart_base64=chart_base64,
    pdf_s3_key=pdf_s3_key,              # [MODIFIED] Use parameter
    pdf_generated_at=pdf_generated_at,  # [MODIFIED] Use parameter
)
```

**Updated docstring** (add to line 999):
```python
def store_report_from_api(
    self,
    symbol: str,
    report_text: str,
    report_json: dict,
    chart_base64: str = '',
    pdf_s3_key: Optional[str] = None,
    pdf_generated_at: Optional[datetime] = None
) -> dict:
    """Store a report generated by the API worker to Aurora cache.

    This method enables cache write-through from the async report worker,
    allowing subsequent requests for the same ticker to hit the cache
    instead of regenerating the report.

    [ADDED] PDF support: If pdf_s3_key provided, report will include PDF
    (used by scheduled workflows that generate PDFs).

    Args:
        symbol: Ticker symbol (e.g., "AAPL")
        report_text: LLM-generated report text
        report_json: Complete report structure
        chart_base64: Base64-encoded chart image
        pdf_s3_key: S3 key for generated PDF (optional, for scheduled workflows)
        pdf_generated_at: Timestamp when PDF generated (optional)

    Returns:
        dict: Cache result with success status
    """
```

---

#### Change 4: Update Worker Call to Pass PDF Parameters

**Location**: `src/report_worker_handler.py:221`

**Modified code**:
```python
# ========================================
# STEP 5: Cache to Aurora (with PDF if generated)
# ========================================
cache_result = precompute_service.store_report_from_api(
    symbol=ticker,
    report_text=result.get('narrative_report', ''),
    report_json=result,
    chart_base64=final_state.get('chart_base64', ''),
    pdf_s3_key=pdf_s3_key,              # [ADDED] Pass PDF S3 key
    pdf_generated_at=pdf_generated_at   # [ADDED] Pass PDF timestamp
)
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_report_worker_handler.py`

**Test cases**:

1. **Test PDF generation for scheduled workflow** (no job_id)
   - Mock SQS message without job_id
   - Mock LLM report generation
   - Verify `_generate_and_upload_pdf()` called
   - Verify `store_report_from_api()` receives pdf_s3_key

2. **Test PDF skipped for API request** (has job_id)
   - Mock SQS message with job_id
   - Mock LLM report generation
   - Verify `_generate_and_upload_pdf()` NOT called
   - Verify `store_report_from_api()` receives pdf_s3_key=None

3. **Test graceful degradation on PDF failure**
   - Mock `_generate_and_upload_pdf()` to raise exception
   - Verify worker continues (doesn't fail)
   - Verify report still stored to Aurora
   - Verify pdf_s3_key=None in Aurora

4. **Test explicit generate_pdf flag**
   - Mock SQS message with `generate_pdf=True` AND job_id
   - Verify PDF generated even with job_id present

---

### Integration Tests

**File**: `tests/integration/test_scheduled_workflow.py`

**Test cases**:

1. **Test end-to-end scheduled workflow**
   - Trigger precompute controller
   - Verify Step Functions executes
   - Verify workers process all 46 tickers
   - Verify PDFs uploaded to S3
   - Verify Aurora ticker_reports has pdf_s3_key

2. **Test S3 PDF accessibility**
   - Generate PDF via worker
   - Retrieve PDF from S3 using pdf_s3_key
   - Verify PDF is valid (not corrupted)

---

### Manual Verification

**Checklist**:

```bash
# 1. Deploy updated worker Lambda
just deploy-lambda report-worker

# 2. Trigger manual precompute (single ticker)
ENV=dev doppler run -- aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --invocation-type Event \
  --payload '{"limit": 1}' \
  /tmp/response.json

# 3. Wait for Step Functions to complete (~30 seconds)
sleep 30

# 4. Check S3 for PDF
aws s3 ls s3://line-bot-pdf-reports-755283537543/reports/ --recursive | grep $(date +%Y-%m-%d)

# 5. Check Aurora for pdf_s3_key
ENV=dev doppler run -- python -c "
from src.data.aurora.precompute_service import PrecomputeService
from datetime import date
ps = PrecomputeService()
# Query ticker_reports for today's date
# Verify pdf_s3_key is NOT NULL
"

# 6. Check CloudWatch logs for PDF generation
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-report-worker-dev \
  --filter-pattern "Generated PDF" \
  --start-time $(($(date +%s) - 600))000  # Last 10 minutes
```

---

## Performance Impact

### Expected Duration Changes

**Current workflow** (without PDF):
```
Ticker data fetch:   1-3 seconds
LLM report:          5-30 seconds
Aurora cache:        0.1-0.5 second
---
Total per ticker:    6.1-33.5 seconds
```

**New workflow** (with PDF):
```
Ticker data fetch:   1-3 seconds
LLM report:          5-30 seconds
PDF generation:      1-2 seconds      ← ADDED
S3 upload:           0.5-1 second     ← ADDED
Aurora cache:        0.1-0.5 second
---
Total per ticker:    7.7-36.5 seconds  (+1.5-3 seconds per ticker)
```

**Impact on scheduled workflow** (46 tickers):
- Current: ~5 minutes (Step Functions duration)
- New: ~5.5-6 minutes (Step Functions duration)
- Delta: +30-60 seconds total (+6-10%)

**Lambda timeout consideration**:
- Current worker timeout: 300 seconds (5 minutes)
- New worst-case per ticker: 36.5 seconds
- Safe: ✅ (36.5s << 300s)

---

## Error Handling

### Error Scenario 1: PDF Generation Fails

**Cause**: S3 upload error, PDF library error, etc.

**Handling**:
```python
except Exception as e:
    logger.warning(f"⚠️ PDF generation failed for {ticker}: {e}")
    # Continue without PDF - report is still valid
```

**Outcome**:
- Report stored to Aurora (pdf_s3_key=None)
- Worker succeeds (no exception raised)
- User gets report without PDF
- CloudWatch logs show warning

**Mitigation**: Monitor CloudWatch for PDF failures, investigate if > 5% failure rate

---

### Error Scenario 2: LLM Report Fails

**Cause**: LLM API timeout, rate limit, etc.

**Handling**: Existing error handling in agent workflow

**Outcome**:
- No report generated → PDF skipped (no report_text)
- Worker logs error
- DynamoDB job status = "failed" (if job_id exists)
- No Aurora cache entry

**Impact**: Same as current behavior (no change)

---

### Error Scenario 3: Aurora Cache Fails

**Cause**: Database connection error, constraint violation, etc.

**Handling**: Existing error handling in `store_report_from_api()`

**Outcome**:
- Report generated ✅
- PDF generated ✅
- PDF uploaded to S3 ✅
- Aurora cache FAILED ❌

**Problem**: PDF orphaned in S3 (not referenced in Aurora)

**Mitigation**:
- Monitor Aurora cache failure rate
- Add S3 lifecycle policy to delete orphaned PDFs after 7 days
- Consider adding cleanup job to delete unreferenced PDFs

---

## Deployment Plan

### Phase 1: Code Changes (1-2 hours)

- [ ] Modify `src/report_worker_handler.py` (add PDF generation step)
- [ ] Modify `src/data/aurora/precompute_service.py` (update `store_report_from_api()` signature)
- [ ] Add unit tests (`tests/unit/test_report_worker_handler.py`)
- [ ] Run local tests: `pytest tests/unit/test_report_worker_handler.py`

---

### Phase 2: Integration Testing (1-2 hours)

- [ ] Deploy to dev environment: `just deploy-lambda report-worker`
- [ ] Trigger manual precompute (1 ticker): Test Step Functions workflow
- [ ] Verify PDF in S3: Check `s3://bucket/reports/TICKER/DATE.pdf`
- [ ] Verify Aurora pdf_s3_key: Query ticker_reports table
- [ ] Check CloudWatch logs: Verify "Generated PDF" messages
- [ ] Test graceful degradation: Mock PDF failure, verify worker continues

---

### Phase 3: Scheduled Run Verification (overnight)

- [ ] Wait for scheduled 5:00 AM run
- [ ] Verify 46 PDFs generated: `aws s3 ls s3://bucket/reports/ --recursive | grep $(date +%Y-%m-%d)`
- [ ] Check Aurora for all 46 tickers: Query ticker_reports for today
- [ ] Monitor CloudWatch for PDF failures: Filter for "PDF generation failed"
- [ ] Verify Step Functions duration: Should be ~5.5-6 minutes (vs 5 minutes before)

---

### Phase 4: Production Deployment (after dev verification)

- [ ] Merge to `main` branch (staging deployment)
- [ ] Wait for staging 5:00 AM run (verify PDFs)
- [ ] Tag release `v*.*.*` (production deployment)
- [ ] Monitor production 5:00 AM run
- [ ] Document fix in bug hunt report

---

## Rollback Plan

**If PDF generation causes issues**:

1. **Quick rollback** (revert code):
   ```bash
   git revert <commit-hash>
   git push origin dev
   # Wait for CI/CD to deploy (~8 minutes)
   ```

2. **Feature flag rollback** (if implemented):
   - Set `ENABLE_PDF_GENERATION=false` in Doppler
   - Workers skip PDF generation
   - No code deployment needed

3. **Verification**:
   - Check next scheduled run (no PDFs generated)
   - Verify workers still cache reports (without PDFs)
   - Verify no errors in CloudWatch logs

---

## Open Questions

- [ ] **Should we add ENABLE_PDF_GENERATION feature flag?**
  - Pros: Easy rollback without code deployment
  - Cons: Adds complexity, temporary branching path
  - Decision: Skip for now (rollback via git revert is fast enough)

- [ ] **Should API requests also generate PDFs?**
  - Current: Only scheduled workflows generate PDFs
  - Alternative: API requests could set `generate_pdf=True` in SQS message
  - Decision: Skip for now (API users don't need PDFs, they get JSON response)

- [ ] **What if PDF generation becomes a bottleneck?**
  - Current: PDF adds 1.5-3 seconds (tolerable)
  - If problem: Move PDF generation to separate async job (after report cached)
  - Decision: Monitor performance, optimize if needed

- [ ] **Should we cleanup orphaned PDFs in S3?**
  - Scenario: PDF uploaded but Aurora cache fails
  - Solution: S3 lifecycle policy to delete PDFs not referenced in Aurora after 7 days
  - Decision: Implement if orphan rate > 1%

---

## Next Steps

- [ ] **Review this specification** (validate approach)
- [ ] **Answer open questions** (if any blocking issues)
- [ ] **If approved, implement changes** (Phase 1: Code changes)
- [ ] **Test locally** (unit tests + manual verification)
- [ ] **Deploy to dev** (Phase 2: Integration testing)
- [ ] **Verify scheduled run** (Phase 3: Overnight verification)
- [ ] **Deploy to production** (Phase 4: After dev verification)
- [ ] **Close bug hunt** (document fix in `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`)

---

## Success Criteria

**Fix is successful if**:
- ✅ PDFs generated for all 46 tickers in scheduled workflow
- ✅ PDFs uploaded to S3 (`s3://bucket/reports/TICKER/DATE.pdf`)
- ✅ Aurora ticker_reports has non-null pdf_s3_key
- ✅ API requests still work (no PDFs generated, no errors)
- ✅ Worker execution time < 40 seconds per ticker (within Lambda timeout)
- ✅ PDF failure rate < 5% (graceful degradation working)
- ✅ Step Functions duration < 7 minutes (vs 5 minutes before)

---

## References

**Bug Hunt Report**: `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`
- Root cause: Scheduler doesn't call `compute_and_store_report()`
- Fix options: 3 approaches documented
- Recommended: Option A (this specification)

**Validation Report**: `.claude/validations/2026-01-02-sqs-workers-generate-pdfs.md`
- Status: FALSE - SQS workers don't generate PDFs
- Evidence: Workers use `store_report_from_api()` (pdf_s3_key=None)
- Fix needed: Add PDF generation to workers

**Code References**:
- `src/report_worker_handler.py:114-234` - Worker Lambda handler
- `src/data/aurora/precompute_service.py:991-1057` - store_report_from_api()
- `src/data/aurora/precompute_service.py:1390-1433` - _generate_and_upload_pdf()
- `src/data/aurora/precompute_service.py:804-899` - compute_and_store_report() (for reference)

**CLAUDE.md Principles**:
- Principle #1: Defensive Programming (fail-fast, explicit error detection)
- Principle #2: Progressive Evidence Strengthening (verify through logs, S3, Aurora)
- Principle #8: Error Handling Duality (graceful degradation for PDF failures)
