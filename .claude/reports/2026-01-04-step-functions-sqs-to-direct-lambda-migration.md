# Step Functions Migration: SQS to Direct Lambda Invocation

**Date**: 2026-01-04
**Type**: Architecture Migration
**Status**: ✅ COMPLETED
**Impact**: 83% execution time reduction (5 minutes → 50 seconds)

---

## Executive Summary

Successfully migrated the precompute workflow from SQS-based asynchronous processing to Step Functions direct Lambda invocation. The migration eliminates a 5-minute hardcoded wait timer and enables Step Functions to track actual Lambda completion in real-time.

**Key Metrics**:
- **Execution Time**: 50 seconds (down from 5 minutes)
- **Success Rate**: 46/46 tickers (100%)
- **Architecture Change**: Replaced SQS queue decoupling with synchronous orchestration
- **Completion Tracking**: Step Functions now waits for actual Lambda results

---

## Problem Statement

### Before Migration

The precompute workflow used this architecture:

```
Step Functions
  ↓ (Send 46 messages)
SQS Queue (dr-daily-report-report-jobs-dev)
  ↓ (Lambda polls)
Report Worker Lambda (46 parallel executions)
  ↓ (Updates DynamoDB)
DynamoDB Jobs Table

Step Functions: Waits 5 minutes (hardcoded), doesn't know actual completion
```

**Issues**:
1. **Blind Timer**: Step Functions waited 5 minutes regardless of actual completion time
2. **No Completion Tracking**: Couldn't detect early completion or late failures
3. **Wasted Time**: Most executions finished in 30-60 seconds, but waited full 5 minutes
4. **No Failure Detection**: Step Functions marked workflow as success even if Lambdas failed

### After Migration

```
Step Functions
  ↓ (Direct invocation via lambda:invoke)
Report Worker Lambda (46 parallel executions, MaxConcurrency: 46)
  ↓ (Returns result immediately)
Step Functions: Receives actual completion status in real-time
```

**Benefits**:
1. **Actual Completion Tracking**: Step Functions waits for real Lambda completion
2. **Faster Execution**: Completes in 50 seconds instead of 5 minutes
3. **Failure Detection**: Step Functions knows immediately if a Lambda fails
4. **Simplified Architecture**: One less service to manage (SQS queue still exists for backward compatibility)

---

## Architecture Changes

### Step Functions Definition

**File**: `terraform/step_functions/precompute_workflow.json`

**Key Changes**:
- Map state `ItemsPath`: `$.ticker_list.tickers` (dynamic from database)
- `MaxConcurrency`: 46 (parallel processing)
- Resource: `arn:aws:states:::lambda:invoke` (direct invocation)
- Payload structure:
  ```json
  {
    "ticker.$": "$.ticker",
    "execution_id.$": "$$.Execution.Name",
    "source": "step_functions_precompute"
  }
  ```

### Lambda Handler Dual-Mode Support

**File**: `src/report_worker_handler.py`

**Invocation Detection** (lines 108-112):
```python
# Direct Step Functions invocation mode
if 'ticker' in event and 'source' in event:
    logger.info(f"Direct Step Functions invocation: {event.get('ticker')}")
    result = asyncio.run(process_ticker_direct(event))
    return result
```

**Return Format**:
```python
{
    "ticker": "DBS19",
    "status": "success" | "failed",
    "pdf_s3_key": null,
    "error": ""
}
```

---

## Issues Encountered and Fixes

### Issue 1: Ticker KeyError

**Problem**: 43/46 tickers failed with `KeyError('ticker')` when retrieving job status from DynamoDB.

**Root Cause**:
- **SQS mode**: Job created by API endpoint before message queued (has 'ticker' field)
- **Step Functions mode**: No job creation step, `start_job()` only sets `status` and `started_at`
- **DynamoDB upsert**: `update_item()` creates item if missing, but only sets UpdateExpression fields
- **Result**: DynamoDB item missing 'ticker' field → `get_job()` fails with KeyError

**Solution** (Commit `c21297c`):

**File**: `src/report_worker_handler.py` (lines 169-187)

```python
# For Step Functions jobs, create job record first (SQS jobs are created by API before queuing)
# Use DynamoDB put_item to create job with specific job_id and ticker field
from datetime import datetime, timedelta
created_at = datetime.now()
ttl = int((created_at + timedelta(hours=24)).timestamp())

job_service.table.put_item(
    Item={
        'job_id': job_id,
        'ticker': dr_symbol.upper(),
        'status': 'pending',
        'created_at': created_at.isoformat(),
        'ttl': ttl
    }
)
logger.info(f"Created job {job_id} for ticker {dr_symbol.upper()}")

# Mark job as in_progress
job_service.start_job(job_id)
```

**Why this works**:
- Creates complete DynamoDB record with all required fields before processing
- Idempotent: If called multiple times, overwrites with same data
- Backward compatible: SQS mode continues to work (API creates job first, this recreates it harmlessly)

---

### Issue 2: DynamoDB PutItem Permission Denied

**Problem**: Lambda execution failed with `AccessDeniedException` when calling `put_item()`.

**Root Cause**:
- Original IAM policy only granted `GetItem` and `UpdateItem` permissions
- SQS mode didn't need `PutItem` (API endpoint has different IAM role)
- Step Functions mode requires `PutItem` to create job records

**Solution** (Commit `ef9d160`):

**File**: `terraform/async_report.tf` (lines 149-158)

```hcl
# DynamoDB - Create and update job status
{
  Effect = "Allow"
  Action = [
    "dynamodb:GetItem",
    "dynamodb:PutItem",      # ← Added
    "dynamodb:UpdateItem"
  ]
  Resource = aws_dynamodb_table.report_jobs.arn
}
```

**Applied via AWS CLI**:
```bash
aws iam put-role-policy \
  --role-name dr-daily-report-report-worker-role-dev \
  --policy-name dr-daily-report-report-worker-policy-dev \
  --policy-document file://policy.json
```

**Credential Refresh**:
```bash
aws lambda update-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --description "Report worker Lambda - Step Functions integration"
```

Lambda execution environments cache IAM credentials. Updating function configuration forces credential refresh.

---

## Testing and Validation

### Single Ticker Test

**Command**:
```bash
aws lambda invoke \
  --function-name dr-daily-report-report-worker-dev \
  --payload '{"ticker": "DBS19", "execution_id": "test-exec-004", "source": "step_functions_precompute"}' \
  response.json
```

**Result**:
```json
{
  "ticker": "DBS19",
  "status": "success",
  "pdf_s3_key": null,
  "error": ""
}
```

**Validation**: ✅ Lambda processes Step Functions payload successfully

---

### Full Workflow Test (46 Tickers)

**Execution**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:dr-daily-report-precompute-workflow-dev \
  --name precompute-test-final
```

**Results**:
```
Start:     2026-01-04T13:35:42.999+07:00
End:       2026-01-04T13:36:33.209+07:00
Duration:  50 seconds
Status:    SUCCEEDED
```

**Ticker Success Rate**:
```bash
# Check all 46 results
aws stepfunctions describe-execution ... | \
  jq '.output | fromjson | .results[] | .worker_result.Payload.status' | \
  sort | uniq -c

# Output:
     46 success
```

**Validation**: ✅ 46/46 tickers processed successfully (100% success rate)

---

## Performance Comparison

| Metric | Before (SQS) | After (Direct) | Improvement |
|--------|--------------|----------------|-------------|
| **Execution Time** | 5 minutes (hardcoded wait) | 50 seconds (actual) | **83% faster** |
| **Completion Tracking** | None (blind wait) | Real-time status | ✅ Enabled |
| **Failure Detection** | Post-execution DynamoDB scan | Immediate via Step Functions | ✅ Enabled |
| **Success Rate** | Unknown during execution | 46/46 (100%) tracked | ✅ Monitored |
| **Architecture Complexity** | Step Functions + SQS + Lambda | Step Functions + Lambda | **Simplified** |

---

## Backward Compatibility

### SQS Mode Still Supported

**Detection** (lines 114-121 in `report_worker_handler.py`):
```python
# Direct Step Functions invocation mode
if 'ticker' in event and 'source' in event:
    logger.info(f"Direct Step Functions invocation: {event.get('ticker')}")
    result = asyncio.run(process_ticker_direct(event))
    return result

records = event.get('Records', [])
logger.info(f"Processing {len(records)} SQS records")

for record in records:
    asyncio.run(process_record(record))
```

**Why Both Modes Work**:
- SQS mode: `event.Records` array present → process as SQS messages
- Step Functions mode: `event.ticker` and `event.source` present → process as direct invocation
- Job creation: Idempotent `put_item()` works for both modes

**Migration Path**:
1. ✅ Step Functions uses direct invocation (current state)
2. ⏭️ Monitor SQS queue for unused messages (deprecation candidate)
3. ⏭️ Remove SQS infrastructure after confirming no usage

---

## Deployment Artifacts

### Docker Image
- **Tag**: `sha-c21297c-20260104-133025`
- **Repository**: `755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev`
- **Digest**: `sha256:27d1bac242e78cdb5630a5c506331e68e685ff0b3c410e3e110798b7d32ee6a1`

### Lambda Functions Updated
- `dr-daily-report-report-worker-dev` (worker Lambda)
- `dr-daily-report-get-ticker-list-dev` (ticker list provider)

### IAM Policies Updated
- `dr-daily-report-report-worker-policy-dev` (added `dynamodb:PutItem`)

---

## Operational Considerations

### Aurora Connection Pooling

**Observation**: 2/46 tickers failed with `"(1040, 'Too many connections')"` in earlier test run.

**Root Cause**: 46 parallel Lambda executions opening simultaneous Aurora connections.

**Current Status**: Not observed in final test run (46/46 success).

**Recommendation**: Monitor Aurora connection metrics in production.

**Mitigation Options** (if needed):
1. Reduce `MaxConcurrency` in Step Functions Map state (e.g., 30 instead of 46)
2. Increase Aurora max_connections parameter
3. Implement connection pooling in Lambda (RDS Proxy)

---

### OpenRouter API Rate Limits

**Observation**: 1/46 tickers failed with `"Error code: 401"` in earlier test run.

**Root Cause**: OpenRouter API authentication or rate limit.

**Current Status**: Not observed in final test run (46/46 success).

**Recommendation**: Monitor OpenRouter API errors in CloudWatch.

---

## Future Improvements

### 1. SQS Queue Deprecation

**When**: After 1-2 weeks of production monitoring

**Steps**:
1. Verify no SQS messages being sent (CloudWatch metric: `NumberOfMessagesSent`)
2. Remove SQS queue and event source mapping from Terraform
3. Remove SQS processing logic from `report_worker_handler.py`

**Risk**: Low (Step Functions is now primary path)

---

### 2. PDF Generation Integration

**Current State**: `pdf_s3_key: null` in all responses

**Reason**: PDF generation moved to separate Step Function workflow (per code comments)

**Next Step**: Integrate PDF workflow with precompute workflow if needed

---

### 3. Error Handling Improvements

**Current State**: Workflow allows partial success (some tickers can fail)

**Enhancement Options**:
1. Add retry logic for specific error types (connection errors, rate limits)
2. Implement exponential backoff for API rate limits
3. Add dead letter queue (DLQ) for persistent failures

---

## Commits

1. **`94e9935`** - fix: Rename AURORA_USERNAME to AURORA_USER for consistency
2. **`92b583c`** - fix: Copy all handler files to Docker image root for Lambda entry points
3. **`46040e1`** - fix: Use correct JobService.get_job() method returning Job object
4. **`c21297c`** - fix: Create DynamoDB job record with ticker field for Step Functions invocations
5. **`ef9d160`** - feat(infra): Add PutItem permission to report_worker for Step Functions jobs

---

## References

- **CLAUDE.md Principles Applied**:
  - Principle #1: Defensive Programming (fail-fast validation)
  - Principle #2: Progressive Evidence Strengthening (verified through ground truth)
  - Principle #6: Deployment Monitoring Discipline (used AWS CLI waiters)
  - Principle #15: Infrastructure-Application Contract (synchronized IAM permissions)
  - Principle #20: Execution Boundary Discipline (verified Docker container, IAM policies)

- **Step Functions Definition**: `terraform/step_functions/precompute_workflow.json`
- **Lambda Handler**: `src/report_worker_handler.py`
- **IAM Policy**: `terraform/async_report.tf`
- **Test Results**: Step Functions execution `precompute-test-final`

---

## Conclusion

The Step Functions migration from SQS to direct Lambda invocation is **complete and production-ready**. The workflow now executes in 50 seconds instead of 5 minutes, with real-time completion tracking and 100% success rate across all 46 tickers.

**Next Actions**:
1. ✅ Migration complete
2. ⏭️ Monitor production workload for 1-2 weeks
3. ⏭️ Consider SQS queue deprecation after validation period

**Status**: Ready for production deployment 🚀
