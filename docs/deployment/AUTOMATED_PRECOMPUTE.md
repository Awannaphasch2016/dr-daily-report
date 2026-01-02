# Automated Precompute Workflow

## Overview

**Status:** ✅ **ENABLED** - EventBridge Scheduler v2 with native Bangkok timezone support

**Architecture:** EventBridge Scheduler triggers ticker data fetch at 5:00 AM Bangkok daily. Precompute workflow can be triggered manually or scheduled separately.

**Migration Note:** Old EventBridge Rules architecture removed 2025-12-31 after successful EventBridge Scheduler v2 cutover.

---

## Architecture

### Current Flow (EventBridge Scheduler v2)
```
EventBridge Scheduler (5:00 AM Bangkok daily)
    ↓
Scheduler Lambda
    ↓
Fetch 46 tickers from Yahoo Finance
    ↓
Store raw data to Aurora ticker_data table
    ↓
✅ COMPLETES (~5-15 min)

[MANUAL TRIGGER for Precompute]
    ↓
Precompute Controller Lambda
    ↓
Start Step Functions state machine
    ↓
Fan out 46 SQS messages (one per ticker)
    ↓
Report Worker Lambdas (parallel processing)
    ↓
Generate AI reports for all tickers
    ↓
Store complete reports in Aurora precomputed_reports table
    ↓
✅ Telegram API & LINE Bot serve cached reports instantly
```

**Key Features:**
- **Native timezone support**: Schedule uses `Asia/Bangkok` timezone (no UTC conversion needed)
- **Single scheduler**: One EventBridge Scheduler replaces old EventBridge Rules
- **Manual precompute**: Reports generated on-demand via Lambda invoke or Step Functions

---

## Implementation Details

### EventBridge Scheduler (Current)

| Schedule | Cron Expression | Timezone | Status | Triggers | Purpose |
|----------|----------------|----------|--------|----------|---------|
| `daily-ticker-fetch-v2` | `cron(0 5 * * ? *)` | `Asia/Bangkok` | ✅ ENABLED | Scheduler Lambda | Fetch raw data from Yahoo Finance at 5:00 AM Bangkok |

**Note**: Precompute workflow is triggered manually. For automatic scheduling, create a separate EventBridge Scheduler schedule that invokes the Precompute Controller Lambda.

### Terraform Configuration

**File:** `terraform/scheduler.tf`

**Current EventBridge Scheduler:**
```hcl
resource "aws_scheduler_schedule" "daily_ticker_fetch_v2" {
  name        = "${var.project_name}-daily-ticker-fetch-v2-${var.environment}"
  group_name  = "default"
  description = "Daily ticker data fetch at 5:00 AM Bangkok (EventBridge Scheduler v2)"

  flexible_time_window {
    mode = "OFF"  # Exact time execution
  }

  schedule_expression          = "cron(0 5 * * ? *)"  # 5:00 AM daily
  schedule_expression_timezone = "Asia/Bangkok"        # Native timezone support!
  state                        = "ENABLED"

  target {
    arn      = aws_lambda_function.ticker_scheduler.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}
```

**Key Improvements Over Old EventBridge Rules:**
- ✅ Native timezone support (`Asia/Bangkok` instead of UTC offset calculation)
- ✅ Simpler configuration (no separate rule + target resources)
- ✅ Built-in retry policy
- ✅ No UTC conversion errors

**To Add Automatic Precompute Scheduling:**
Create a second EventBridge Scheduler schedule in `terraform/scheduler.tf` that invokes the Precompute Controller Lambda at a scheduled time (e.g., 5:30 AM Bangkok).

---

## Manual Precompute Triggering

**Current Workflow (Manual):**
1. Scheduler runs automatically at 5:00 AM Bangkok (fetches raw data)
2. **Manually** trigger precompute after scheduler completes

### Method 1: Trigger Precompute Controller Directly (Recommended)

```bash
# Trigger precompute for all 47 tickers
aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --payload '{"source":"manual","limit":null}' \
  /tmp/precompute.json

cat /tmp/precompute.json

# Trigger precompute for specific number of tickers (testing)
aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --payload '{"source":"manual","limit":5}' \
  /tmp/precompute.json
```

### Method 2: Start Step Functions Directly

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(cd terraform && ENV=dev doppler run -- terraform output -raw precompute_workflow_arn)

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name "manual-$(date +%Y%m%d-%H%M%S)" \
  --input '{"limit":null,"triggered_by":"manual"}'

# Monitor execution
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --max-results 5
```

### Method 3: Via AWS Console

1. Go to Step Functions Console: https://console.aws.amazon.com/states/
2. Select state machine: `dr-daily-report-precompute-workflow-dev`
3. Click "Start execution"
4. Input JSON:
   ```json
   {
     "limit": null,
     "triggered_by": "console-manual"
   }
   ```
5. Click "Start execution"
6. Monitor progress in visual workflow

---

## Deployment Instructions

### 1. Apply Terraform Changes

```bash
# Dev environment
cd terraform
ENV=dev doppler run -- terraform plan -var-file=environments/dev.tfvars
ENV=dev doppler run -- terraform apply -var-file=environments/dev.tfvars

# Staging environment
ENV=staging doppler run -- terraform plan -var-file=environments/staging.tfvars
ENV=staging doppler run -- terraform apply -var-file=environments/staging.tfvars

# Production environment
ENV=prod doppler run -- terraform plan -var-file=environments/prod.tfvars
ENV=prod doppler run -- terraform apply -var-file=environments/prod.tfvars
```

### 2. Verify EventBridge Scheduler

```bash
# Check EventBridge Scheduler schedule
ENV=dev doppler run -- aws scheduler get-schedule \
  --name dr-daily-report-daily-ticker-fetch-v2-dev \
  --group-name default

# Verify schedule is ENABLED and timezone is Asia/Bangkok
# Expected output:
#   State: ENABLED
#   ScheduleExpression: cron(0 5 * * ? *)
#   ScheduleExpressionTimezone: Asia/Bangkok
```

### 3. Test the Flow

**Option A: Test scheduler only (manual trigger)**
```bash
# Trigger scheduler manually
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"tickers":["NVDA","DBS19"]}' \
  /tmp/scheduler-test.json

cat /tmp/scheduler-test.json
```

**Option B: Test precompute controller only**
```bash
# Trigger precompute manually (assumes scheduler already ran)
aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --payload '{"limit":5,"source":"manual-test"}' \
  /tmp/precompute-test.json

cat /tmp/precompute-test.json
```

**Option C: Test end-to-end (wait for scheduled time)**
```bash
# Wait for 8:00 AM Bangkok, then monitor CloudWatch Logs
aws logs tail /aws/lambda/dr-daily-report-ticker-scheduler-dev --follow

# 20 minutes later (8:20 AM), monitor precompute controller
aws logs tail /aws/lambda/dr-daily-report-precompute-controller-dev --follow

# Monitor Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn <state-machine-arn> \
  --max-results 5
```

---

## Monitoring & Troubleshooting

### CloudWatch Logs

**Scheduler Lambda:**
```bash
aws logs tail /aws/lambda/dr-daily-report-ticker-scheduler-dev --follow --since 5m
```

**Precompute Controller:**
```bash
aws logs tail /aws/lambda/dr-daily-report-precompute-controller-dev --follow --since 5m
```

**Step Functions:**
- View executions in AWS Console:
  `https://console.aws.amazon.com/states/home?region=ap-southeast-1#/statemachines`
- Check CloudWatch Logs:
  ```bash
  aws logs tail /aws/vendedlogs/states/dr-daily-report-precompute-workflow-dev --follow
  ```

### Verify Data Flow

**1. Check scheduler fetched data:**
```bash
# Query Aurora to verify ticker_data populated
# (Requires SSM port forwarding - see docs/AWS_OPERATIONS.md)
mysql -h localhost -P 3307 -u admin -p daily_report_dev

SELECT symbol, data_date, COUNT(*) as price_points
FROM ticker_data
WHERE data_date = CURDATE()
GROUP BY symbol, data_date
ORDER BY symbol;
```

**2. Check precompute generated reports:**
```sql
SELECT symbol, generated_at, LENGTH(report_json) as report_size
FROM precomputed_reports
WHERE DATE(generated_at) = CURDATE()
ORDER BY generated_at DESC;
```

### Common Issues

**Issue 1: Precompute triggers before scheduler finishes**
- **Symptom:** Precompute fails because no ticker_data available
- **Fix:** Increase buffer time by adjusting cron schedule:
  ```hcl
  schedule_expression = "cron(30 1 * * ? *)" # 8:30 AM instead of 8:20 AM
  ```

**Issue 2: Scheduler takes longer than 20 minutes**
- **Symptom:** Scheduler still running when precompute starts
- **Root cause:** Yahoo Finance API slow or retry logic triggered
- **Fix:** Increase buffer or add completion check (see Alternative Solutions below)

**Issue 3: EventBridge Scheduler not triggering Lambda**
- **Verify schedule state:**
  ```bash
  ENV=dev doppler run -- aws scheduler get-schedule \
    --name dr-daily-report-daily-ticker-fetch-v2-dev \
    --group-name default
  ```
- **Check IAM role permissions:** Ensure scheduler role has lambda:InvokeFunction permission
- **Check CloudWatch Logs:** `/aws/lambda/dr-daily-report-ticker-scheduler-dev` for execution logs

---

## Alternative Solutions

### Option 1: EventBridge Scheduler v2 (CURRENT - Implemented)
**Pros:**
- ✅ Native timezone support (no UTC conversion)
- ✅ Simpler configuration (single resource vs rule + target)
- ✅ Clean separation of concerns
- ✅ Easy to monitor independently
- ✅ Built-in retry policy

**Cons:**
- ❌ Manual precompute triggering required (can be automated with second schedule)

### Option 2: Scheduler Invokes Controller (Tighter Coupling)
Modify `ticker_fetcher_handler.py` to invoke Precompute Controller after completion.

**Pros:**
- ✅ Dynamic - starts immediately after scheduler finishes
- ✅ No wasted time waiting

**Cons:**
- ❌ Tighter coupling (scheduler depends on controller)
- ❌ Harder to test independently
- ❌ If controller fails, scheduler shows as failed (mixed concerns)

**Implementation (NOT recommended):**
```python
# In ticker_fetcher_handler.py (at end of lambda_handler)
import boto3
lambda_client = boto3.client('lambda')

# After fetcher.fetch_all_tickers() completes
lambda_client.invoke(
    FunctionName=os.environ['PRECOMPUTE_CONTROLLER_FUNCTION'],
    InvocationType='Event',  # Async
    Payload=json.dumps({'source': 'scheduler', 'limit': None})
)
```

### Option 3: Step Functions Parent Workflow (Most Infrastructure)
Create parent Step Functions that orchestrates: Scheduler → Wait → Precompute.

**Pros:**
- ✅ Full observability in one workflow
- ✅ Built-in retry/error handling
- ✅ Conditional logic (skip precompute if scheduler failed)

**Cons:**
- ❌ More infrastructure complexity
- ❌ Nested Step Functions (parent → child)
- ❌ Higher cost (Step Functions transitions)

---

## Cost Implications

**EventBridge:**
- Free tier: 14 million events/month
- Cost after: $1.00 per million events
- **Impact:** Negligible (2 events/day = 60/month)

**Lambda Invocations:**
- Free tier: 1 million requests/month
- Cost after: $0.20 per million requests
- **Impact:** Negligible (2 invocations/day = 60/month)

**Step Functions:**
- Free tier: 4,000 state transitions/month
- Cost after: $0.025 per 1,000 transitions
- **Current:** ~47 transitions/day (one per ticker) = 1,410/month (within free tier)

**Total additional cost:** $0.00 (all within free tier)

---

## Rollback Procedure

**If issues occur with EventBridge Scheduler:**

```bash
# Option 1: Disable the schedule (emergency stop)
ENV=dev doppler run -- aws scheduler update-schedule \
  --name dr-daily-report-daily-ticker-fetch-v2-dev \
  --group-name default \
  --state DISABLED \
  --schedule-expression "cron(0 5 * * ? *)" \
  --schedule-expression-timezone "Asia/Bangkok" \
  --flexible-time-window Mode=OFF \
  --target '{"Arn":"<lambda-arn>","RoleArn":"<role-arn>"}'

# Option 2: Revert Terraform changes
cd terraform
git revert HEAD
ENV=dev doppler run -- terraform apply -var-file=environments/dev.tfvars

# Option 3: Manual schedule deletion (use with caution)
ENV=dev doppler run -- aws scheduler delete-schedule \
  --name dr-daily-report-daily-ticker-fetch-v2-dev \
  --group-name default
```

**Note**: EventBridge Scheduler v2 is the current production implementation. Reverting to old EventBridge Rules would require restoring deleted Terraform code from git history (commits before 6766300).

---

## References

- [CI/CD Architecture](CI_CD.md) - Multi-app deployment workflows
- [AWS Operations Guide](../AWS_OPERATIONS.md) - Aurora access via SSM
- [Semantic Layer Architecture](../SEMANTIC_LAYER_ARCHITECTURE.md) - Data flow
- Step Functions Console: `terraform output precompute_workflow_console_url`
