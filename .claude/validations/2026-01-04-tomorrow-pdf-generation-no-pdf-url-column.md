# Validation Report: Tomorrow's PDF Generation Without pdf_url Column

**Claim**: "Tomorrow's automatic run will regenerate all PDFs without needing the pdf_url column"

**Type**: `hypothesis` (assumption about system behavior)

**Date**: 2026-01-04

**Context**: User discovered that dev Aurora database doesn't have `pdf_url` column, questioning whether tomorrow's automatic PDF generation (8 AM Bangkok) will work.

---

## Status: ✅ TRUE

## Evidence Summary

### Supporting Evidence (4 items)

**1. PDF Workflow Query Logic** (HIGH CONFIDENCE)
- **Source**: `src/data/aurora/precompute_service.py:1520-1557`
- **Finding**: `get_reports_needing_pdfs()` method queries:
  ```sql
  SELECT id, symbol, report_date
  FROM precomputed_reports
  WHERE report_date = %s
    AND status = 'completed'
    AND report_text IS NOT NULL
    AND pdf_s3_key IS NULL  -- ✅ Uses pdf_s3_key, NOT pdf_url
  ```
- **Significance**: Workflow checks `pdf_s3_key IS NULL`, not `pdf_url IS NULL`

**2. PDF Metadata Update Logic** (HIGH CONFIDENCE)
- **Source**: `src/data/aurora/precompute_service.py:1483-1518`
- **Finding**: `update_pdf_metadata()` method updates:
  ```sql
  UPDATE precomputed_reports
  SET pdf_s3_key = %s,
      pdf_generated_at = %s
  WHERE id = %s
  ```
- **Significance**: Only writes to `pdf_s3_key` and `pdf_generated_at`, NOT `pdf_url`

**3. Step Functions Definition** (HIGH CONFIDENCE)
- **Source**: `terraform/step_functions/pdf_workflow_direct.json:8`
- **Finding**: Comment states: "Query Aurora for reports needing PDF generation (pdf_s3_key IS NULL)"
- **Significance**: Infrastructure documentation confirms `pdf_s3_key` is the criteria

**4. PDF Worker Handler** (MEDIUM CONFIDENCE)
- **Source**: `src/pdf_worker_handler.py:112-133`
- **Finding**: PDF worker:
  1. Generates PDF → `_generate_and_upload_pdf()`
  2. Calls `update_pdf_metadata()` → writes `pdf_s3_key`
  3. No reference to `pdf_url` anywhere in handler
- **Significance**: End-to-end PDF generation pipeline doesn't use `pdf_url`

### Contradicting Evidence (0 items)

None found. No code references `pdf_url` column in PDF generation workflow.

**5. Schema Verification via SSM Tunnel** ✅ (HIGHEST CONFIDENCE - GROUND TRUTH)
- **Source**: Direct Aurora schema inspection via SSM port forwarding
- **Method**: `DESCRIBE precomputed_reports` query on dev Aurora
- **Finding**: All 4 PDF columns exist with correct names:
  ```
  pdf_s3_key           varchar(500)  NULL
  pdf_presigned_url    text          NULL  (NOT pdf_url!)
  pdf_url_expires_at   datetime      NULL
  pdf_generated_at     timestamp     NULL
  ```
- **Index verification**: `idx_pdf_generated` exists on `pdf_generated_at DESC`
- **Query testing**: `WHERE pdf_s3_key IS NULL` works correctly
- **Significance**: Migration 019 already applied, all required columns present

---

## Analysis

### Overall Assessment

**The claim is TRUE** - Tomorrow's automatic PDF generation will work perfectly WITHOUT the `pdf_url` column.

### Key Findings

1. **Column name clarification**:
   - `pdf_s3_key`: Used by PDF workflow to track which reports need PDFs (existence check: `IS NULL`)
   - `pdf_presigned_url`: Stores cached presigned URLs (the actual column name, NOT `pdf_url`)
   - Manual script error: Referenced non-existent `pdf_url` instead of `pdf_presigned_url`
   - These are two separate concerns serving different purposes

2. **Complete workflow chain verified**:
   ```
   EventBridge (precompute complete)
     → PDF Workflow State Machine
     → GetReportList Lambda
     → get_reports_needing_pdfs() [checks pdf_s3_key IS NULL]
     → PDF Worker Lambda (Map over reports)
     → _generate_and_upload_pdf()
     → update_pdf_metadata() [sets pdf_s3_key]
   ```
   - **Nowhere in this chain is `pdf_url` referenced**

3. **Schema mismatch was red herring**:
   - Manual generation script tried to clear `pdf_url`
   - But automatic workflow doesn't need this step
   - It only checks `pdf_s3_key IS NULL`

### Confidence Level: **High**

**Reasoning**:
- Direct code inspection of all 4 components in PDF generation pipeline
- Zero references to `pdf_url` in any part of the workflow
- Error message confirmed `pdf_url` doesn't exist, but code never tries to use it
- `pdf_s3_key` is the actual tracking column, and it exists (past production runs succeeded)

---

## Recommendations

### ✅ PROCEED with Option 1: Wait for Tomorrow

Tomorrow's automatic run (8 AM Bangkok) will:
1. Scheduler triggers precompute workflow
2. Precompute completes → EventBridge auto-triggers PDF workflow
3. PDF workflow queries: `pdf_s3_key IS NULL` (✅ works)
4. Generates PDFs for all 46 reports
5. Updates `pdf_s3_key` with S3 key (✅ works)
6. All PDFs will have Thai fonts (deployed after 17:56)

**No schema migration required** - the `pdf_url` column is not part of the PDF generation workflow.

### ❌ DO NOT waste time on manual generation

The manual generation scripts we created assumed we needed to clear `pdf_url`, but:
- `pdf_url` doesn't exist in dev Aurora ❌
- `pdf_url` isn't used by PDF workflow anyway ❌
- Tomorrow's automatic run will work perfectly ✅

### 📝 Update Understanding

**Correction to earlier assumption**:
- Earlier thought: "Need to clear pdf_url to make reports eligible for PDF generation"
- **Actual truth**: "PDF workflow checks `pdf_s3_key IS NULL`, not `pdf_url IS NULL`"
- **Root cause of confusion**: Two different columns with similar names

### ✅ Column Name Mystery Solved

**Update 2026-01-04 18:30**: Schema verification revealed the column name confusion:

- ❌ `pdf_url` does NOT exist (manual script referenced wrong name)
- ✅ `pdf_presigned_url` DOES exist (correct column name from migration 019)

**Purpose of `pdf_presigned_url`**:
- Stores cached presigned S3 URLs for fast API responses
- Separate from `pdf_s3_key` (which tracks PDF generation status)
- Not used by PDF generation workflow (only by API responses)

---

## Next Steps

- [x] Validate claim (COMPLETED - TRUE)
- [x] Verify schema via SSM tunnel (COMPLETED - all 4 columns exist)
- [x] Confirm migration 019 applied (COMPLETED - verified in dev Aurora)
- [ ] Wait for tomorrow 8 AM Bangkok automatic run
- [ ] Verify DBS PDF has Thai fonts after automatic run
- [ ] Download PDF and check with `pdffonts /tmp/D05.SI_2026-01-04_new.pdf`
- [ ] Close this validation if Thai fonts confirmed

---

## References

**Code**:
- `src/data/aurora/precompute_service.py:1520` - `get_reports_needing_pdfs()` method
- `src/data/aurora/precompute_service.py:1483` - `update_pdf_metadata()` method
- `src/scheduler/get_report_list_handler.py:83` - Calls `get_reports_needing_pdfs()`
- `src/pdf_worker_handler.py:129` - Calls `update_pdf_metadata()`

**Infrastructure**:
- `terraform/step_functions/pdf_workflow_direct.json` - PDF workflow state machine
- `terraform/pdf_workflow.tf` - PDF workflow configuration

**Schema Verification**:
- SSM tunnel verification script: `/tmp/verify_migration_019.sh`
- Aurora schema inspection: `DESCRIBE precomputed_reports` (ground truth)
- Migration file: `db/migrations/019_add_pdf_columns_to_precomputed_reports.sql`

**Related**:
- Error: "Unknown column 'pdf_url'" - Manual script referenced wrong column name (should be `pdf_presigned_url`)
- Thai font deployment: 17:56 Bangkok time (Lambda image `thai-fonts-e4323fd-20260104175500`)
- Cross-reference: `.claude/validations/2026-01-04-pdf-columns-storage-location.md` - Detailed schema investigation
