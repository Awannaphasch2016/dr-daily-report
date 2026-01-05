# Progress Report: PDF Generation Integration into Scheduler Workflow

**Date**: 2026-01-03
**Status**: ⚠️ PARTIALLY COMPLETE - Schema Mismatch Discovered

---

## Executive Summary

PDF generation has been successfully integrated into the scheduler workflow at the code level. The system generates 46 PDFs nightly at 5 AM Bangkok time and uploads them to S3. However, a critical schema mismatch was discovered: Aurora database does not store PDF S3 keys, causing silent data loss.

**What Works**: ✅
- PDF generation integrated into Worker Lambda (after LLM report generation)
- 46 PDFs generated nightly (72-84 KB each)
- PDFs uploaded to S3 successfully
- Graceful degradation (PDF failure doesn't fail job)
- Timestamps use Bangkok timezone (UTC+7)

**What Doesn't Work**: ❌
- Aurora table missing `pdf_s3_key`, `pdf_generated_at` columns
- Code silently ignores PDF parameters during Aurora insert
- No way to retrieve PDFs from Aurora-cached reports

**Root Cause**: Process violation - Direct commit to dev branch bypassed PR gate and automated schema validation tests.

---

## Technical Implementation Status

### 1. Workflow Architecture ✅

**EventBridge Scheduler → Step Functions → SQS Fan-Out → 46 Worker Lambdas**

```
EventBridge Scheduler (5 AM Bangkok)
    ↓
Precompute Controller Lambda
    ↓
Step Functions (precompute_workflow.json)
    ↓
Map State: Fan-out to 46 SQS messages
    ↓
46 Worker Lambdas (parallel execution)
    ↓
Each Worker (SINGLE LAMBDA EXECUTION):
  1. Fetch data from Aurora
  2. Run LLM analysis (8-12s)
  3. Mark job COMPLETED
  4. Generate PDF (2-3s) ← SAME LAMBDA
  5. Upload PDF to S3
  6. Store report to Aurora cache
```

**Key finding**: PDF generation happens INSIDE the Worker Lambda, as a sequential step AFTER LLM generation completes. This is not a separate Lambda or Step Functions state.

**Code location**: `src/report_worker_handler.py:240-265`

### 2. PDF Generation ✅

**Implementation**: Fully functional

**Evidence**:
- CloudWatch logs show 46 successful PDF generations (2026-01-02 20:49-20:50 Bangkok time)
- S3 bucket contains 46 PDFs (72-84 KB each)
- PDF format: ReportLab-based multi-page documents with charts and text

**Sample log**:
```
2026-01-02T20:49:57.852Z  📄 Generating PDF for DBS19...
2026-01-02T20:49:59.123Z  ✅ PDF uploaded to S3: reports/2026-01-02/DBS19.pdf
```

**Timezone**: PDFs use Bangkok time (UTC+7) via `datetime.now()` respecting `TZ=Asia/Bangkok` environment variable.

**Code location**: `src/formatters/pdf_generator.py:759`

### 3. Aurora Storage ⚠️ PARTIALLY WORKING

**What works**:
- Reports stored in `precomputed_reports` table
- Text content, JSON data, chart_base64 persisted
- Status tracking (completed/failed)
- Cache expiration logic

**What DOESN'T work**:
- `pdf_s3_key` parameter passed to `store_report_from_api()` but NOT persisted
- `pdf_generated_at` timestamp passed but NOT persisted
- Parameters silently ignored (no error, no warning)

**Schema mismatch**:
```sql
-- ACTUAL Aurora schema
CREATE TABLE precomputed_reports (
    id bigint PRIMARY KEY,
    ticker_id int,
    symbol varchar(20),
    report_date date,
    report_text text,
    report_json json,
    chart_base64 longtext,
    status enum('pending','completed','failed'),
    computed_at timestamp,
    expires_at timestamp,
    generation_time_ms int unsigned,
    error_message text
    -- MISSING: pdf_s3_key, pdf_generated_at
);

-- EXPECTED (based on code)
ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) DEFAULT NULL,
ADD COLUMN pdf_generated_at TIMESTAMP DEFAULT NULL,
ADD INDEX idx_pdf_s3_key (pdf_s3_key);
```

**Code location**: `src/data/aurora/precompute_service.py:932-989`

**Impact**:
- PDFs exist in S3 but cannot be retrieved from Aurora-cached reports
- Cache read API returns reports without PDF references
- API consumers cannot access PDFs generated during precompute

---

## Validation Work Completed

### Validation 1: Timezone Confirmation ✅
**Question**: "Is PDF timestamp Bangkok time or UTC?"

**Answer**: Bangkok time (UTC+7)

**Evidence**:
- Lambda environment variable: `TZ=Asia/Bangkok`
- Python `datetime.now()` respects TZ env var
- CLAUDE.md Principle #16 (Timezone Discipline) compliance

**Confidence**: High (verified via code + Lambda config)

### Validation 2: Aurora Data Population ⚠️
**Question**: "Does scheduler populate Aurora with reports AND PDFs?"

**Answer**: Partially - Reports YES, PDF references NO

**Evidence**:
- CloudWatch logs: `source: aurora` (46 successful fetches)
- S3 PDFs: 46 files uploaded
- Aurora schema: Missing `pdf_s3_key` column
- Code: Parameter passed but not persisted

**Confidence**: High (direct table inspection + code analysis)

**Validation report**: `.claude/validations/2026-01-03-scheduler-populates-aurora-and-pdf.md`

### Validation 3: Why Safeguards Failed ❌
**Question**: "How can this bug happen? Don't we have principles to prevent this?"

**Answer**: We DO have comprehensive safeguards, but they were bypassed

**Safeguards that exist**:
1. ✅ CLAUDE.md Principle #5 (Database Migrations Immutability)
2. ✅ CLAUDE.md Principle #15 (Infrastructure-Application Contract)
3. ✅ Automated schema validation test (`test_aurora_schema_comprehensive.py`)
4. ✅ CI/CD PR gate requiring tests to pass

**What went wrong**:
- Commit `eb30b74` pushed directly to dev branch (no PR)
- PR gate never triggered
- Schema validation tests never ran
- Test would have caught missing columns

**Root cause**: Process violation, not missing tooling

**Validation report**: `.claude/validations/2026-01-03-why-pdf-schema-bug-not-prevented.md`

### Validation 4: Precompute Workflow Architecture ✅
**Question**: "Is report generation part of precompute workflow?"

**Answer**: YES - Report generation IS the precompute workflow

**Clarification**:
- "Precompute" means generate THE ENTIRE REPORT ahead of time
- Not just partial values - the full LLM-generated narrative
- Architecture: Data Fetcher → Step Functions → SQS Fan-Out → Report Generation

**Confidence**: High (verified via workflow definition + documentation)

### Validation 5: PDF Generation Timing ✅
**Question**: "Is PDF generation inside precompute Lambda or a separate step?"

**Answer**: INSIDE the same Worker Lambda, AFTER LLM generation

**Sequential execution order**:
1. LLM generates report (8-12s)
2. Job marked COMPLETED
3. PDF generation (2-3s) ← SAME LAMBDA
4. Aurora caching

**Rationale**: Graceful degradation - if PDF fails, job still succeeds

**Confidence**: High (verified via code inspection)

---

## Root Cause Analysis

### How the Bug Happened

**Timeline**:
1. Developer implemented PDF generation feature
2. Updated code to pass `pdf_s3_key` parameter
3. Committed directly to dev branch (commit `eb30b74`)
4. Bypassed PR workflow
5. CI/CD deployed code without running schema validation tests
6. Code deployed with schema mismatch

**Git evidence**:
```bash
$ git log --oneline --first-parent dev | grep "feat: Add PDF generation"
eb30b74 feat: Add PDF generation to SQS workers  ← DIRECT COMMIT (no PR)
```

**Why automated safeguards didn't catch it**:
- Schema validation test exists: `tests/infrastructure/test_aurora_schema_comprehensive.py:213-255`
- Test automatically extracts expected columns from code
- Test would have FAILED with: `❌ Aurora schema missing columns: ['pdf_s3_key', 'pdf_generated_at']`
- BUT: Test never ran because PR gate was bypassed

**CLAUDE.md principles violated**:
- **Principle #5**: Database Migrations Immutability - Should have created migration first
- **Principle #15**: Infrastructure-Application Contract - Code and schema must match

---

## Recommendations

### Immediate Actions (Fix Current Bug)

**Priority 1**: Create database migration

```sql
-- db/migrations/019_add_pdf_tracking.sql
ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) DEFAULT NULL COMMENT 'S3 key for generated PDF report',
ADD COLUMN pdf_generated_at TIMESTAMP DEFAULT NULL COMMENT 'When PDF was generated',
ADD INDEX idx_pdf_s3_key (pdf_s3_key);
```

**Priority 2**: Update INSERT query in `_store_completed_report()`

```python
query = f"""
    INSERT INTO {PRECOMPUTED_REPORTS} (
        ticker_id, symbol, report_date,
        report_text, report_json,
        generation_time_ms,
        chart_base64,
        pdf_s3_key,              -- ADD
        pdf_generated_at,        -- ADD
        status, expires_at, computed_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s,                      -- pdf_s3_key
        %s,                      -- pdf_generated_at
        %s, %s, %s
    )
"""
```

**Priority 3**: Deploy via proper PR workflow
- Create PR with migration + code changes
- Schema validation tests will run automatically
- Verify tests pass before merging

**Timeline**: 1-2 days

### Week 1 (Process Improvements)

**Priority 1**: Enable GitHub branch protection

```yaml
# Settings for dev and main branches
required_pull_request_reviews:
  required_approving_review_count: 1
  dismiss_stale_reviews: true

required_status_checks:
  strict: true
  contexts:
    - schema-validation  # Must pass
    - unit-tests         # Must pass

enforce_admins: true  # No bypass allowed
```

**Priority 2**: Update team process documentation
- Document PR-only workflow (no direct commits)
- Explain why safeguards exist
- Add migration creation checklist

**Priority 3**: Audit recent commits
- Review all direct commits to dev in last 3 months
- Check for similar schema mismatches

**Timeline**: 1 week

### Week 2 (Preventive Measures)

**Priority 1**: Extend CLAUDE.md Principle #15

Add explicit database schema requirement:
```markdown
When adding new principles requiring database changes, update in this order:
1. Add principle to CLAUDE.md
2. Create database migration SQL file       ← ADD THIS
3. Update application code
4. Update Terraform env vars (if needed)
5. Run schema validation tests locally
6. Deploy via PR workflow
```

**Priority 2**: Add pre-commit hook (optional)

```bash
#!/bin/bash
# .git/hooks/pre-commit
echo "Running schema validation tests..."
pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v

if [ $? -ne 0 ]; then
    echo "❌ Schema validation failed. Commit aborted."
    exit 1
fi
```

**Priority 3**: Monitoring and alerts
- CloudWatch alarm for NULL `pdf_s3_key` in new reports
- Weekly audit of schema-code contract
- Dashboard showing PDF generation success rate

**Timeline**: 2 weeks

---

## Lessons Learned

### What Went Well ✅

1. **Comprehensive safeguards existed**
   - CLAUDE.md principles covered this scenario
   - Automated tests would have caught the bug
   - CI/CD pipeline configured correctly

2. **Progressive evidence strengthening worked**
   - Started with surface signals (PDF exists in S3)
   - Progressed to observability (CloudWatch logs)
   - Reached ground truth (Aurora schema inspection)
   - Discovered mismatch at Layer 4 validation

3. **Graceful degradation worked**
   - PDF generation failures don't fail jobs
   - System continued operating despite schema mismatch
   - No user-facing errors

### What Didn't Work ❌

1. **Process discipline failed**
   - Developer bypassed PR workflow
   - Direct commit to dev branch
   - No peer review

2. **Schema-code contract not enforced**
   - Code deployed before schema ready
   - Silent parameter ignore (no error)
   - Missing startup validation

3. **Safeguards require execution**
   - Having tests ≠ Running tests
   - Branch protection not enabled
   - Enforcement mechanism missing

### Key Takeaway

**Technical safeguards (principles, tests, CI/CD) are necessary but not sufficient.**

**Process enforcement (branch protection, PR requirements) is critical to ensure safeguards actually run.**

---

## Metrics

### PDF Generation (Jan 2, 2026)
- **Total PDFs generated**: 46/46 (100%)
- **Upload success rate**: 46/46 (100%)
- **Average PDF size**: 72-84 KB
- **Generation time**: 2-3s per PDF
- **Total execution time**: ~2.5 minutes (parallel)

### Aurora Storage
- **Reports stored**: 46/46 (100%)
- **PDF references stored**: 0/46 (0%) ← BUG
- **Schema columns missing**: 2 (`pdf_s3_key`, `pdf_generated_at`)

### Safeguards
- **CLAUDE.md principles applicable**: 3 (#5, #15, #16)
- **Automated tests available**: 1 (schema validation)
- **Tests executed**: 0 (PR gate bypassed)
- **Branch protection enabled**: No

---

## References

### Validation Reports Created
- `.claude/validations/2026-01-03-scheduler-populates-aurora-and-pdf.md` - Aurora data population
- `.claude/validations/2026-01-03-why-pdf-schema-bug-not-prevented.md` - Root cause analysis
- `.claude/validations/2026-01-03-aurora-data-populated-from-pdf-success.md` - PDF-based validation

### Code Locations
- **PDF generation**: `src/formatters/pdf_generator.py:759`
- **Worker Lambda**: `src/report_worker_handler.py:216-294`
- **Aurora storage**: `src/data/aurora/precompute_service.py:932-989`
- **Workflow definition**: `terraform/step_functions/precompute_workflow.json:21-57`
- **Schema test**: `tests/infrastructure/test_aurora_schema_comprehensive.py:213-255`

### CLAUDE.md Principles Applied
- **Principle #2**: Progressive Evidence Strengthening - Used to discover schema mismatch
- **Principle #5**: Database Migrations Immutability - Violated, caused bug
- **Principle #15**: Infrastructure-Application Contract - Violated, caused bug
- **Principle #16**: Timezone Discipline - Correctly applied

### AWS Resources
- **Aurora Cluster**: `dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com`
- **Database**: `ticker_data`
- **Table**: `precomputed_reports`
- **S3 Bucket**: `dr-daily-report-dev-storage` (PDFs in `reports/` prefix)
- **CloudWatch Log Group**: `/aws/lambda/dr-daily-report-report-worker-dev`

---

## Conclusion

PDF generation has been successfully integrated into the scheduler workflow from a **code execution** perspective. The system generates 46 PDFs nightly, uploads them to S3, and handles failures gracefully.

However, the integration is **incomplete from a data persistence** perspective. Aurora database does not store PDF references, making cached reports incomplete and preventing API consumers from accessing precomputed PDFs.

**Current state**: ⚠️ **Functional but incomplete**
- ✅ PDFs generate successfully
- ✅ PDFs upload to S3 successfully
- ❌ PDFs not linked in Aurora (data loss)
- ❌ Cache API cannot return PDF URLs

**Next step**: Create migration to add `pdf_s3_key` column, deploy via proper PR workflow with schema validation.

**Estimated time to completion**: 1-2 days for bug fix + 2 weeks for process improvements.

---

**Report Status**: COMPLETE
**Risk Level**: Medium (safe for development, risky for production without schema fix)
**Blocking Issue**: Yes - Schema migration required before production deployment
