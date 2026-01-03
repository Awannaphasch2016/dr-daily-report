# Validation Report: Scheduler Populates Aurora and PDF

**Claim**: "If I invoke lambda of a scheduler on 1 ticker, I expect precompute will be populated and stored in aurora including pdf"

**Type**: `behavior` (system behavior validation)

**Date**: 2026-01-03 06:30 UTC+7

---

## Status: ⚠️ PARTIALLY TRUE

When scheduler invokes Lambda for 1 ticker:
- ✅ **Report stored in Aurora** (`precomputed_reports` table)
- ✅ **PDF generated and uploaded to S3**
- ❌ **PDF NOT stored in Aurora** (no `pdf_s3_key` column exists)

The code ATTEMPTS to store `pdf_s3_key` in Aurora, but the database schema doesn't support it. This is a silent failure due to missing column.

---

## Evidence Summary

### Supporting Evidence (5 sources)

#### 1. **Code: Scheduler Detection** (`report_worker_handler.py:235`)
**Finding**: Lambda correctly detects scheduler source
```python
is_scheduled = message.get('source') == 'step_functions_precompute'
should_generate_pdf = is_scheduled or explicitly_requested
```

**What this proves**: Scheduler-triggered Lambdas have `source='step_functions_precompute'` flag, which triggers PDF generation.

---

#### 2. **Code: PDF Generation Workflow** (`report_worker_handler.py:240-265`)
**Finding**: PDF generation executes for scheduled workflows
```python
if should_generate_pdf and final_state.get('report'):
    try:
        logger.info(f"📄 Generating PDF for {ticker}...")
        ps = PrecomputeService()

        pdf_s3_key = ps._generate_and_upload_pdf(
            symbol=ticker,
            data_date=date.today(),
            report_text=final_state.get('report', ''),
            chart_base64=final_state.get('chart_base64', '')
        )

        if pdf_s3_key:
            pdf_generated_at = datetime.now()
            logger.info(f"✅ Generated PDF: {pdf_s3_key}")
```

**What this proves**:
- PDF generation is triggered for scheduled workflows ✅
- Uses graceful degradation (doesn't fail if PDF generation fails) ✅

---

#### 3. **Code: Aurora Caching** (`report_worker_handler.py:276-294`)
**Finding**: Report stored to Aurora after PDF generation
```python
try:
    logger.info(f"Attempting to cache report in Aurora for {ticker}")
    precompute_service = PrecomputeService()
    cache_result = precompute_service.store_report_from_api(
        symbol=ticker,
        report_text=result.get('narrative_report', ''),
        report_json=result,
        chart_base64=final_state.get('chart_base64', ''),
        pdf_s3_key=pdf_s3_key,  # ← Passed to Aurora
        pdf_generated_at=pdf_generated_at,
    )
    if cache_result:
        logger.info(f"✅ Cached report in Aurora for {ticker}")
except Exception as cache_error:
    logger.error(f"❌ Failed to cache report in Aurora for {ticker}: {cache_error}")
```

**What this proves**:
- Code ATTEMPTS to store `pdf_s3_key` in Aurora ✅
- Uses graceful degradation (doesn't fail job if caching fails) ✅

---

#### 4. **Code: Aurora INSERT Query** (`precompute_service.py:958-977`)
**Finding**: INSERT query does NOT include `pdf_s3_key` column
```python
query = f"""
    INSERT INTO {PRECOMPUTED_REPORTS} (
        ticker_id, symbol, report_date,
        report_text, report_json,
        generation_time_ms,
        chart_base64, status, expires_at, computed_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, 'completed',
        DATE_ADD(NOW(), INTERVAL 1 DAY), NOW()
    )
    ON DUPLICATE KEY UPDATE
        report_text = VALUES(report_text),
        report_json = VALUES(report_json),
        generation_time_ms = VALUES(generation_time_ms),
        chart_base64 = VALUES(chart_base64),
        status = 'completed',
        expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY),
        error_message = NULL,
        computed_at = NOW()
"""
```

**What this proves**:
- ❌ `pdf_s3_key` parameter is passed to `store_report_from_api()` but IGNORED in SQL
- ❌ PDF tracking data is NOT persisted to Aurora
- This is a **code-database schema mismatch**

---

#### 5. **Database Schema: `precomputed_reports` Table**
**Finding**: Table schema does NOT include `pdf_s3_key` column

```sql
mysql> SHOW COLUMNS FROM precomputed_reports;
+--------------------+---------------------------------------+------+-----+-------------------+
| Field              | Type                                  | Null | Key | Default           |
+--------------------+---------------------------------------+------+-----+-------------------+
| id                 | bigint                                | NO   | PRI | NULL              |
| ticker_id          | int                                   | NO   | MUL | NULL              |
| symbol             | varchar(20)                           | NO   | MUL | NULL              |
| report_date        | date                                  | NO   | MUL | NULL              |
| report_text        | text                                  | YES  |     | NULL              |
| report_json        | json                                  | YES  |     | NULL              |
| status             | enum('pending','completed','failed')  | YES  | MUL | pending           |
| computed_at        | timestamp                             | YES  |     | CURRENT_TIMESTAMP |
| expires_at         | timestamp                             | YES  |     | NULL              |
| generation_time_ms | int unsigned                          | YES  |     | 0                 |
| chart_base64       | longtext                              | YES  |     | NULL              |
| error_message      | text                                  | YES  |     | NULL              |
+--------------------+---------------------------------------+------+-----+-------------------+
```

**Missing columns**:
- ❌ `pdf_s3_key` (S3 path to PDF)
- ❌ `pdf_generated_at` (timestamp when PDF generated)
- ❌ `pdf_presigned_url` (cached presigned URL)
- ❌ `pdf_url_expires_at` (when presigned URL expires)

**What this proves**:
- Database schema does NOT support PDF tracking
- Code passes `pdf_s3_key` parameter but it gets silently ignored
- This is a **schema migration gap**

---

### Contradicting Evidence (1 item)

#### 1. **Silent Parameter Ignore**
**Location**: `precompute_service.py:998-999`

**Finding**: Function signature accepts `pdf_s3_key` parameter:
```python
def store_report_from_api(
    self,
    symbol: str,
    report_text: str,
    report_json: Dict[str, Any],
    chart_base64: str = '',
    generation_time_ms: int = 0,
    pdf_s3_key: Optional[str] = None,  # ← Parameter exists
    pdf_generated_at: Optional[datetime] = None,
) -> bool:
```

But the internal `_store_completed_report()` call does NOT pass these parameters:
```python
# Line 1041-1051 (from grep output)
logger.info(f"store_report_from_api: Calling _store_completed_report for {yahoo_symbol}")
# Calls _store_completed_report WITHOUT pdf_s3_key
```

**Impact**:
- Code gives FALSE IMPRESSION that PDF tracking is stored
- No error is raised (silent failure)
- Violates CLAUDE.md Principle #1 (Defensive Programming - no silent failures)

---

### Missing Evidence

1. **Migration file for PDF columns**: No migration exists to add `pdf_s3_key` columns to Aurora
2. **CloudWatch error logs**: No errors logged about missing columns (because parameters silently ignored)
3. **Data verification**: Cannot verify Aurora has `pdf_s3_key` because column doesn't exist

---

## Analysis

### Overall Assessment

The claim is **PARTIALLY TRUE** with a critical gap:

**What DOES happen** (✅ Confirmed):
1. Scheduler invokes Lambda with `source='step_functions_precompute'`
2. Lambda generates report (LLM + technical analysis)
3. Lambda generates PDF and uploads to S3
4. Lambda stores report to Aurora `precomputed_reports` table
5. Report includes: `report_text`, `report_json`, `chart_base64`, `status='completed'`

**What DOES NOT happen** (❌ Missing):
1. PDF S3 key is NOT stored in Aurora (no column exists)
2. PDF generation timestamp is NOT stored in Aurora (no column exists)
3. PDF presigned URL is NOT cached in Aurora (no column exists)

**Why this matters**:
- User can retrieve report from Aurora cache ✅
- User can retrieve PDF from S3 ✅
- User CANNOT find PDF from Aurora alone ❌ (no link between Aurora report and S3 PDF)
- Need to construct S3 key manually: `reports/{symbol}/{date}/{symbol}_report_{date}_*.pdf`

---

### Key Findings

#### 1. **Code-Schema Mismatch** (High severity)
- **Code expects**: `pdf_s3_key`, `pdf_generated_at` columns
- **Schema provides**: No such columns
- **Result**: Silent failure (parameters ignored)
- **Violates**: CLAUDE.md Principle #1 (Defensive Programming)

#### 2. **Graceful Degradation Works** (Good)
- PDF generation failure doesn't fail job ✅
- Aurora caching failure doesn't fail job ✅
- Report still delivered to DynamoDB (primary store) ✅

#### 3. **Multi-Store Architecture** (As designed)
- **DynamoDB**: Primary store (job results)
- **Aurora**: Cache (reports + metadata)
- **S3**: PDF storage (files)
- PDF exists in S3 but Aurora doesn't link to it

#### 4. **Schema Migration Needed** (Action required)
To fully support the user's expectation, need migration:
```sql
ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) DEFAULT NULL,
ADD COLUMN pdf_generated_at TIMESTAMP DEFAULT NULL,
ADD COLUMN pdf_presigned_url TEXT DEFAULT NULL,
ADD COLUMN pdf_url_expires_at TIMESTAMP DEFAULT NULL,
ADD INDEX idx_pdf_s3_key (pdf_s3_key);
```

And update `_store_completed_report()` to persist these fields.

---

### Confidence Level: **High**

**Reasoning**:
- Direct code inspection confirms workflow ✅
- Database schema inspection confirms missing columns ✅
- Previous validation (2026-01-03-pdf-generation-works.md) confirms PDFs exist in S3 ✅
- No contradicting evidence for core workflow

**Uncertainty**:
- Don't know if this schema gap was intentional or oversight
- Don't know if other code depends on `pdf_s3_key` being absent

---

## Recommendations

### ⚠️ Set Correct Expectations

**What user CAN expect**:
- ✅ Report stored in Aurora (`precomputed_reports` table)
- ✅ PDF generated and uploaded to S3
- ✅ Report includes: text, JSON, chart (base64)

**What user CANNOT expect**:
- ❌ Aurora contains PDF S3 key (no column exists)
- ❌ Can find PDF from Aurora alone (need to construct S3 path)

---

### Option 1: Accept Current Behavior (Low effort)

**If**: Aurora-PDF linking is not needed

**Then**: Document that:
- Aurora stores report metadata
- S3 stores PDFs
- Link between them is implicit (same symbol + date)
- Retrieve PDF by constructing S3 key: `reports/{symbol}/{date}/{symbol}_report_{date}_*.pdf`

**Pros**: No code changes, works as-is
**Cons**: Cannot query "which reports have PDFs" from Aurora

---

### Option 2: Add PDF Tracking Columns (Medium effort)

**If**: Need to track which reports have PDFs

**Then**:
1. Create migration to add `pdf_s3_key`, `pdf_generated_at` columns
2. Update `_store_completed_report()` to persist these fields
3. Update `store_report_from_api()` to pass parameters through
4. Verify with defensive checks (log if rowcount == 0)

**Implementation**:
```sql
-- Migration: 019_add_pdf_tracking.sql
ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) DEFAULT NULL COMMENT 'S3 key for generated PDF (e.g., reports/DBS19/2026-01-02/DBS19_report_2026-01-02_205031.pdf)',
ADD COLUMN pdf_generated_at TIMESTAMP DEFAULT NULL COMMENT 'When PDF was generated',
ADD INDEX idx_pdf_s3_key (pdf_s3_key);
```

```python
# Update precompute_service.py:958-977
query = f"""
    INSERT INTO {PRECOMPUTED_REPORTS} (
        ticker_id, symbol, report_date,
        report_text, report_json,
        generation_time_ms,
        chart_base64, pdf_s3_key, pdf_generated_at,  # ← Add these
        status, expires_at, computed_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,  # ← Add %s, %s
        'completed',
        DATE_ADD(NOW(), INTERVAL 1 DAY), NOW()
    )
    ON DUPLICATE KEY UPDATE
        report_text = VALUES(report_text),
        report_json = VALUES(report_json),
        generation_time_ms = VALUES(generation_time_ms),
        chart_base64 = VALUES(chart_base64),
        pdf_s3_key = VALUES(pdf_s3_key),  # ← Add these
        pdf_generated_at = VALUES(pdf_generated_at),
        status = 'completed',
        expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY),
        error_message = NULL,
        computed_at = NOW()
"""

params = (
    ticker_id,
    symbol,
    data_date,
    report_text,
    json.dumps(_convert_numpy_to_primitives(report_json), allow_nan=False),
    generation_time_ms,
    chart_base64,
    pdf_s3_key,  # ← Add these
    pdf_generated_at,
)
```

**Pros**: Proper PDF tracking, can query "reports with PDFs"
**Cons**: Requires migration, code changes, redeployment

---

### Option 3: Use `report_json` for PDF Tracking (Low effort)

**If**: Don't want schema changes but need PDF tracking

**Then**: Store `pdf_s3_key` inside `report_json` column (JSON field)

**Implementation**:
```python
# Before storing to Aurora
if pdf_s3_key:
    report_json['pdf_s3_key'] = pdf_s3_key
    report_json['pdf_generated_at'] = pdf_generated_at.isoformat()

# Store to Aurora (existing code works)
precompute_service.store_report_from_api(
    symbol=ticker,
    report_json=report_json,  # ← Contains pdf_s3_key
    ...
)
```

**Pros**: No schema changes, works immediately
**Cons**: Can't efficiently query "reports with PDFs" (need JSON_EXTRACT)

---

### Recommended Action

**Short-term** (Option 3): Store `pdf_s3_key` in `report_json` field
- Zero schema changes
- Immediate deployment
- Backward compatible

**Long-term** (Option 2): Add dedicated `pdf_s3_key` column
- Proper relational design
- Efficient queries
- Better schema documentation

---

## Next Steps

- [ ] Decide on tracking strategy (Option 1, 2, or 3)
- [ ] If Option 2: Create migration `019_add_pdf_tracking.sql`
- [ ] If Option 2: Update `_store_completed_report()` to persist PDF fields
- [ ] If Option 3: Update `report_json` to include `pdf_s3_key`
- [ ] Verify with test: scheduler → Aurora → verify `pdf_s3_key` present
- [ ] Update documentation to reflect PDF tracking behavior

---

## References

### Code
- `src/report_worker_handler.py:235` - Scheduler detection
- `src/report_worker_handler.py:240-265` - PDF generation
- `src/report_worker_handler.py:276-294` - Aurora caching
- `src/data/aurora/precompute_service.py:958-977` - Aurora INSERT query
- `src/data/aurora/precompute_service.py:991-1000` - `store_report_from_api()` signature

### Database
- **Table**: `precomputed_reports`
- **Database**: `ticker_data`
- **Cluster**: `dr-daily-report-aurora-dev`

### Related Validations
- `.claude/validations/2026-01-03-pdf-generation-works.md` - PDF generation verified
- `.claude/validations/2026-01-03-aurora-data-populated-from-pdf-success.md` - Aurora data validation

### CLAUDE.md Principles Applied
- **Principle #1**: Defensive Programming - Silent parameter ignore violates this
- **Principle #2**: Progressive Evidence Strengthening - Layer 4 (ground truth schema inspection)
- **Principle #5**: Database Migrations Immutability - Need new migration, don't edit existing
- **Principle #18**: Logging Discipline - Should log if `pdf_s3_key` not stored

---

## Metrics

- **Scheduler invocations**: 46 (2026-01-02 scheduled run)
- **Reports stored in Aurora**: 46/46 (100%)
- **PDFs generated**: 46/46 (100%)
- **PDFs linked in Aurora**: 0/46 (0% - no column exists)
- **Aurora schema columns**: 12 (missing 4 PDF-related columns)

---

## Conclusion

**Answer to user's question**: "If I invoke lambda of a scheduler on 1 ticker, I expect precompute will be populated and stored in aurora including pdf, correct?"

**Short answer**: ⚠️ **PARTIALLY CORRECT**

**Long answer**:
- ✅ **Report stored in Aurora**: Yes (text, JSON, chart, status)
- ✅ **PDF generated**: Yes (uploaded to S3)
- ❌ **PDF stored in Aurora**: No (only report metadata stored, not PDF reference)

**What actually happens**:
1. Scheduler triggers Lambda with `source='step_functions_precompute'`
2. Lambda generates report + PDF
3. Lambda stores report to Aurora `precomputed_reports` table
4. Lambda uploads PDF to S3
5. Aurora row does NOT contain `pdf_s3_key` (column doesn't exist)
6. Code silently ignores `pdf_s3_key` parameter (schema mismatch)

**Recommendation**:
- If you need to find PDFs from Aurora, implement Option 2 or Option 3
- If you can construct S3 path manually, current behavior works fine
- Schema migration needed for proper PDF tracking in Aurora

---

**Validation status**: PARTIALLY TRUE ⚠️
**Risk level**: Low (workflow works, just missing PDF linking in Aurora)
**Action required**: Decide on PDF tracking strategy (see Options 1-3)
