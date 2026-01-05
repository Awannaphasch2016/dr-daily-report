# Validation Report: SQS Usage Across Environments

**Claim**: "SQS is deprecated in dev, but does SQS still used in staging and prod?"
**Type**: config (infrastructure validation)
**Date**: 2026-01-04

---

## Status: ⚠️ **PARTIALLY TRUE**

**Short answer**:
- SQS for **PDF workflow** is deprecated in dev ✅
- SQS for **async report workflow** is **NOT deprecated** in any environment ❌
- Staging **uses SQS** for async reports ✅
- Production **not deployed** (no infrastructure exists) ⚠️

---

## Evidence Summary

### Supporting Evidence (PDF Workflow Deprecated)

**1. PDF Workflow Migration Report**
- **Source**: `.claude/reports/2026-01-04-pdf-workflow-sqs-to-direct-lambda-migration.md`
- **Finding**: PDF workflow migrated from SQS to direct Lambda invocation on 2026-01-04
- **Status**: ✅ Complete
- **Impact**: PDF workflow no longer uses SQS in any environment

**Quote**:
> Successfully migrated PDF generation workflow from SQS-based pattern to direct Lambda invocation via Step Functions

**Architecture change**:
```
Before: Step Functions → SQS Queue → Lambda Event Source → PDF Worker
After:  Step Functions → Direct Lambda Invocation → PDF Worker
```

**2. Terraform Configuration**
- **Source**: `terraform/pdf_workflow.tf`
- **Finding**: SQS resources commented out with `# DEPRECATED` markers
- **Lines**: 125-180 (based on validation reference)
- **Confidence**: High

---

### Contradicting Evidence (Async Report Workflow Still Uses SQS)

**1. Active SQS Queues in AWS**
- **Source**: AWS SQS ListQueues API
- **Finding**: 4 active SQS queues for async report workflow

**Dev environment**:
```
https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-report-jobs-dlq-dev
https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-dev
```

**Staging environment**:
```
https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-report-jobs-dlq-staging
https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-staging
```

**Production environment**: ❌ No queues (infrastructure not deployed)

**Confidence**: High (AWS ground truth)

---

**2. Lambda Environment Variables Reference SQS**
- **Source**: AWS Lambda GetFunctionConfiguration API

**Dev Lambda** (`dr-daily-report-telegram-api-dev`):
```
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-dev
```

**Staging Lambda** (`dr-daily-report-telegram-api-staging`):
```
REPORT_JOBS_QUEUE_URL=https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-staging
```

**Analysis**: Both dev and staging Lambda functions have active SQS queue URLs configured

**Confidence**: High (AWS ground truth)

---

**3. Terraform Infrastructure Definitions**
- **Source**: `terraform/async_report.tf`
- **Finding**: Active SQS queue resources (NOT deprecated)

**Resources defined**:
```hcl
resource "aws_sqs_queue" "report_jobs_dlq" {
  name = "${var.project_name}-report-jobs-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days
}

resource "aws_sqs_queue" "report_jobs" {
  name = "${var.project_name}-telegram-queue-${var.environment}"
  visibility_timeout_seconds = 900  # 15 min
}
```

**NO DEPRECATED markers found** (unlike `pdf_workflow.tf`)

**Confidence**: High (source code analysis)

---

**4. Recent Git History**
- **Source**: `git log terraform/async_report.tf`
- **Latest commit**: `ef9d160` - "feat(infra): Add PutItem permission to report_worker for Step Functions jobs"
- **Date**: Recent (2026-01-04 timeframe based on PDF migration report)

**Analysis**: No commits removing or deprecating SQS resources in async_report.tf

**Confidence**: High

---

### Missing Evidence

**Production Environment**: ❌ No infrastructure deployed
- No production Lambda functions exist
- No production SQS queues exist
- Cannot validate production SQS usage (infrastructure not created)

---

## Analysis

### Overall Assessment

**The claim is PARTIALLY TRUE with important clarifications:**

1. **TRUE**: SQS is deprecated for **PDF workflow** in dev (and all environments)
   - Migrated on 2026-01-04
   - PDF workflow now uses direct Lambda invocation via Step Functions
   - SQS resources commented out in `terraform/pdf_workflow.tf`

2. **FALSE**: SQS is **NOT deprecated** for **async report workflow**
   - Active SQS queues exist in dev and staging
   - Lambda functions reference queue URLs
   - Terraform still defines active SQS resources
   - No deprecation markers or migration plans found

3. **PARTIALLY TRUE**: Staging uses SQS ✅
   - Staging has 2 active SQS queues (main + DLQ)
   - Staging Lambda references queue URL
   - Infrastructure deployed via Terraform

4. **UNKNOWN**: Production SQS usage ⚠️
   - Production infrastructure not deployed
   - Cannot verify whether production would use SQS
   - Based on Terraform config, production **would** use SQS if deployed

---

### Key Findings

**Finding 1: Two Separate SQS Use Cases**
- **PDF workflow SQS**: ✅ Deprecated (migrated 2026-01-04)
- **Async report workflow SQS**: ❌ Still active (not deprecated)

**Significance**: The claim conflates two different workflows. Only PDF workflow deprecated SQS.

---

**Finding 2: Async Report Workflow Architecture**

**Current pattern** (SQS-based):
```
Telegram API
    ↓
    Enqueue report job to SQS
    ↓
SQS Queue (async)
    ↓
Lambda Event Source Mapping
    ↓
Report Worker Lambda (processes job)
```

**Status**: Active in dev and staging
**NOT migrated** to direct Lambda invocation (unlike PDF workflow)

**Significance**: Async report workflow intentionally uses SQS for decoupling

---

**Finding 3: Architectural Inconsistency**

**PDF workflow**: Direct Lambda invocation via Step Functions ✅
**Async report workflow**: SQS-based pattern ❌

**Observation**: Architectural inconsistency between workflows
**Possible reason**: Different requirements (PDF: batch processing, Async: request-response decoupling)

---

### Confidence Level: **High**

**Reasoning**:
- AWS API queries provide ground truth (queues exist, Lambda configs reference them)
- Terraform source code analysis confirms infrastructure definitions
- Migration report explicitly documents PDF workflow SQS deprecation
- Missing production data doesn't affect dev/staging validation

**Uncertainty**:
- Production behavior unknown (infrastructure not deployed)
- Cannot confirm if async report workflow deprecation is planned

---

## Recommendations

### If Assumption Was: "All SQS usage deprecated in dev"

**Status**: ❌ FALSE

**DO NOT** proceed with assumption that all SQS is deprecated

**Corrected understanding**:
- **PDF workflow**: SQS deprecated ✅ (use direct Lambda invocation)
- **Async report workflow**: SQS active ❌ (still uses queue-based pattern)

**Action**: Update mental model to distinguish between workflows

---

### If Question Was: "Should we migrate async report SQS to direct invocation?"

**Consider**:

1. **Why PDF workflow migrated**:
   - Real-time completion tracking
   - Architectural consistency
   - Better visibility

2. **Why async report workflow might keep SQS**:
   - Request-response decoupling (user doesn't wait)
   - Rate limiting via queue throttling
   - Built-in retry with DLQ
   - Different use case from batch PDF generation

3. **Trade-offs**:
   - **Direct invocation**: Faster feedback, simpler architecture
   - **SQS**: Buffering, rate limiting, retry handling

**Recommendation**: Evaluate use case before migrating. SQS provides value for async workflows.

---

### If Deploying to Production

**Current state**: Production infrastructure not deployed

**When deploying production**:
- ✅ PDF workflow: Will use direct Lambda invocation (no SQS)
- ⚠️ Async report workflow: **Will create SQS queues** (active in Terraform)

**Action**: If SQS deprecation intended for async reports, update Terraform **before** production deployment

---

## Clarifying Questions for User

1. **Which workflow** were you asking about?
   - PDF generation workflow? → SQS deprecated ✅
   - Async report workflow? → SQS still active ❌

2. **Do you want** to deprecate SQS for async report workflow too?
   - If yes: Need migration plan (similar to PDF workflow)
   - If no: Clarify that async reports still use SQS

3. **For production deployment**, should async report workflow:
   - Use SQS (current Terraform config)?
   - Use direct Lambda invocation (requires Terraform changes)?

---

## Next Steps

### Immediate Actions

- [ ] **Clarify scope** with user: Which workflow SQS usage were they asking about?
- [ ] **Document architectural decision**: Why async reports keep SQS vs PDF workflow migrated
- [ ] **Update CLAUDE.md** if needed: Clarify SQS deprecation scope

### If Migrating Async Report Workflow

- [ ] **Review PDF migration report**: `.claude/reports/2026-01-04-pdf-workflow-sqs-to-direct-lambda-migration.md`
- [ ] **Create migration plan**: Apply same pattern to async report workflow
- [ ] **Update Terraform**: Remove SQS resources from `async_report.tf`
- [ ] **Test deployment**: Validate Lambda invocation pattern works
- [ ] **Deploy to environments**: Dev → Staging → Prod

### If Keeping SQS for Async Reports

- [ ] **Document rationale**: Why async reports need SQS (decoupling, rate limiting)
- [ ] **Update architecture docs**: Clarify two patterns coexist
- [ ] **Create ADR**: Document decision to keep SQS for async reports

---

## References

### Observations
- `.claude/reports/2026-01-04-pdf-workflow-sqs-to-direct-lambda-migration.md` - PDF workflow SQS deprecation

### Code
- `terraform/async_report.tf` - Async report SQS resources (ACTIVE)
- `terraform/pdf_workflow.tf:125-180` - PDF workflow SQS resources (DEPRECATED)
- `terraform/telegram_api.tf` - Lambda env var: `REPORT_JOBS_QUEUE_URL`

### AWS Resources

**Dev environment**:
- SQS Queue: `dr-daily-report-telegram-queue-dev`
- SQS DLQ: `dr-daily-report-report-jobs-dlq-dev`
- Lambda: `dr-daily-report-telegram-api-dev` (references queue)

**Staging environment**:
- SQS Queue: `dr-daily-report-telegram-queue-staging`
- SQS DLQ: `dr-daily-report-report-jobs-dlq-staging`
- Lambda: `dr-daily-report-telegram-api-staging` (references queue)

**Production environment**: ❌ No infrastructure deployed

---

## Summary Table

| Workflow | Dev | Staging | Production | Status |
|----------|-----|---------|------------|--------|
| **PDF Generation** | ✅ Deprecated (Direct Lambda) | ✅ Deprecated (Direct Lambda) | N/A (not deployed) | Migrated 2026-01-04 |
| **Async Reports** | ❌ Uses SQS | ❌ Uses SQS | N/A (not deployed) | Active (not deprecated) |

---

**Validation completed**: 2026-01-04
**Confidence**: High
**Type**: Config + Infrastructure
**Methodology**: AWS API queries + Terraform source analysis + Migration report review
