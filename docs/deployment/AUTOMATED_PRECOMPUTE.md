# Automated Precompute Workflow

## Overview

**Status:** ⚠️ **CURRENTLY DISABLED** - Manual precompute triggering only

**Problem:** Scheduler fetches raw ticker data but doesn't trigger report generation automatically.

**Solution (when enabled):** EventBridge chaining - two scheduled rules working in sequence.

---

## Architecture

### Before (Manual Triggering Required)
```
EventBridge (8:00 AM) → Scheduler Lambda → fetch & store raw data → ❌ STOPS

                        Precompute Controller exists but NEVER invoked
```

### After (When Enabled - Currently DISABLED)
```
EventBridge Rule 1 (5:00 AM Bangkok / 22:00 UTC prev day)
    ↓
Scheduler Lambda
    ↓
Fetch 47 tickers from Yahoo Finance
    ↓
Store raw data to Aurora ticker_data table
    ↓
⏰ 20 minute buffer (scheduler completes in ~5-15 min)
    ↓
EventBridge Rule 2 (5:20 AM Bangkok / 22:20 UTC prev day) ⚠️ DISABLED
    ↓
[MANUAL TRIGGER REQUIRED]
    ↓
Precompute Controller Lambda
    ↓
Start Step Functions state machine
    ↓
Fan out 47 SQS messages (one per ticker)
    ↓
Report Worker Lambdas (parallel processing)
    ↓
Generate AI reports for all tickers
    ↓
Store complete reports in Aurora precomputed_reports table
    ↓
✅ Telegram API & LINE Bot serve cached reports instantly
```

---

## Implementation Details

### EventBridge Rules

| Rule | Schedule | Status | Triggers | Purpose |
|------|----------|--------|----------|---------|
| `daily-ticker-fetch` | 5:00 AM Bangkok (22:00 UTC prev day) | ✅ ENABLED | Scheduler Lambda | Fetch raw data from Yahoo Finance |
| `daily-precompute` | 5:20 AM Bangkok (22:20 UTC prev day) | ⚠️ DISABLED | Precompute Controller | Generate AI reports (manual trigger required) |

### Terraform Changes

**File:** `terraform/precompute_workflow.tf`

**Added:**
1. `aws_cloudwatch_event_rule.daily_precompute` - EventBridge rule at 8:20 AM
2. `aws_cloudwatch_event_target.precompute_controller` - Connects rule to Lambda
3. `aws_lambda_permission.eventbridge_invoke_precompute_controller` - Allows invocation

**Key Configuration:**
```hcl
resource "aws_cloudwatch_event_rule" "daily_precompute" {
  schedule_expression = "cron(20 22 * * ? *)" # 22:20 UTC = 05:20 Bangkok next day
  state               = "DISABLED" # Manual triggering only for now
}

resource "aws_cloudwatch_event_target" "precompute_controller" {
  arn = aws_lambda_alias.precompute_controller_live.arn

  input = jsonencode({
    source      = "eventbridge-scheduler"
    limit       = null # Process all 47 tickers
    description = "Daily automatic precompute after scheduler data fetch"
  })
}
```

**To Enable Automatic Precompute:**
1. Change `state = "DISABLED"` to `state = "ENABLED"` in `terraform/precompute_workflow.tf`
2. Run `terraform apply`

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

### 2. Verify EventBridge Rules

```bash
# List all EventBridge rules
aws events list-rules --name-prefix "dr-daily-report"

# Check specific rules
aws events describe-rule --name dr-daily-report-daily-ticker-fetch-dev
aws events describe-rule --name dr-daily-report-daily-precompute-dev

# Verify targets
aws events list-targets-by-rule --rule dr-daily-report-daily-precompute-dev
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

**Issue 3: EventBridge not triggering Lambda**
- **Verify permission:** `aws lambda get-policy --function-name <name>`
- **Check rule state:** `aws events describe-rule --name <rule-name>`
- **Check CloudWatch metrics:** EventBridge → Metrics → Invocations

---

## Alternative Solutions

### Option 1: EventBridge Chaining (CURRENT - Implemented)
**Pros:**
- ✅ Simple to implement (just EventBridge rules)
- ✅ Clean separation of concerns
- ✅ Easy to monitor independently

**Cons:**
- ❌ Fixed time buffer (scheduler might finish earlier, wasting time)
- ❌ Scheduler could take longer than buffer (rare)

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

**If issues occur after Terraform apply:**

```bash
# Disable the new precompute rule (emergency stop)
aws events disable-rule --name dr-daily-report-daily-precompute-dev

# Revert Terraform changes
cd terraform
git revert HEAD
ENV=dev doppler run -- terraform apply -var-file=environments/dev.tfvars

# Manual cleanup if needed
aws events delete-rule --name dr-daily-report-daily-precompute-dev
aws lambda remove-permission \
  --function-name dr-daily-report-precompute-controller-dev \
  --statement-id AllowEventBridgeInvokePrecomputeController
```

---

## References

- [CI/CD Architecture](CI_CD.md) - Multi-app deployment workflows
- [AWS Operations Guide](../AWS_OPERATIONS.md) - Aurora access via SSM
- [Semantic Layer Architecture](../SEMANTIC_LAYER_ARCHITECTURE.md) - Data flow
- Step Functions Console: `terraform output precompute_workflow_console_url`
