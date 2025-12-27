# Deployment Monitoring Guide

Proper monitoring patterns for AWS and GitHub Actions deployments.

---

## AWS CLI Waiters - The Blocking Pattern

**CRITICAL: Never use `sleep X` to wait for AWS operations.**

### Why Waiters Matter

Time-based waiting leads to incorrect conclusions:
- **Too short**: Conclude "bug exists" when deployment isn't done yet
- **Too long**: Waste time waiting for already-completed operations
- **Variable**: Same operation takes different time based on load/complexity

### Lambda Waiters

```bash
# Pattern: Update → Wait → Test → Promote

# 1. Update function code
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-dev \
  --image-uri $ECR_REPO:$TAG

# 2. Wait for update (CRITICAL - blocks until done)
aws lambda wait function-updated \
  --function-name dr-daily-report-telegram-api-dev

# 3. Now safe to test (Lambda is ACTUALLY updated)
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --qualifier '$LATEST' \
  --payload '{"httpMethod": "GET", "path": "/api/v1/health"}' \
  /tmp/smoke-test.json
```

**Anti-Pattern:**
```bash
# WRONG: Time-based waiting
aws lambda update-function-code ...
sleep 60  # ❌ Might not be ready, or wastes time

# RIGHT: Use waiter
aws lambda update-function-code ...
aws lambda wait function-updated --function-name $FUNC  # ✅ Blocks until done
```

### CloudFront Waiters

```bash
# Create invalidation
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

# Wait for completion (CRITICAL)
aws cloudfront wait invalidation-completed \
  --distribution-id $DIST_ID \
  --id $INVALIDATION_ID

# Now CloudFront ACTUALLY serves new files
echo "✅ Cache invalidated, new files live"
```

### Available AWS Waiters

| Service | Waiter | Command |
|---------|--------|---------|
| Lambda | Function updated | `aws lambda wait function-updated --function-name X` |
| Lambda | Function active | `aws lambda wait function-active --function-name X` |
| Lambda | Function exists | `aws lambda wait function-exists --function-name X` |
| CloudFront | Invalidation completed | `aws cloudfront wait invalidation-completed --distribution-id X --id Y` |
| CloudFront | Distribution deployed | `aws cloudfront wait distribution-deployed --id X` |
| DynamoDB | Table exists | `aws dynamodb wait table-exists --table-name X` |
| API Gateway | API deployed | `aws apigatewayv2 wait deployment-completed --api-id X` |

---

## GitHub Actions Monitoring

### The `gh run watch` Pattern

**CRITICAL: Use `--exit-status` to get proper exit codes.**

```bash
# Correct: Watch with exit status (blocks until done)
gh run watch --exit-status

# Or for specific run
gh run watch 12345 --exit-status
```

**Why `--exit-status` matters:**
- Without it: `gh run watch` always exits 0 (even if workflow failed)
- With it: Returns non-zero exit code if workflow fails
- CI/CD scripts can properly detect failures

### Checking Workflow Status

**CRITICAL: Check BOTH `status` and `conclusion`.**

```bash
# Check specific run
gh run view 12345 --json status,conclusion --jq '{status, conclusion}'

# Output examples:
# {"status": "completed", "conclusion": "success"}  → ✅ Deploy succeeded
# {"status": "completed", "conclusion": "failure"}  → ❌ Deploy failed
# {"status": "completed", "conclusion": "cancelled"} → ⚠️ Someone cancelled it
# {"status": "in_progress", "conclusion": null}     → ⏳ Still running
```

**Completion vs Success - The Critical Distinction:**

| Status | Conclusion | Meaning |
|--------|------------|---------|
| `completed` | `success` | ✅ Workflow achieved its goal |
| `completed` | `failure` | ❌ Workflow finished but failed (tests failed, build error, etc.) |
| `completed` | `cancelled` | ⚠️ Someone manually cancelled the workflow |
| `in_progress` | `null` | ⏳ Workflow still running |

**Anti-Pattern:**
```bash
# WRONG: Only checking status
gh run view 12345 --json status
# {"status": "completed"}  ← This does NOT mean success!

# RIGHT: Check both status AND conclusion
gh run view 12345 --json status,conclusion
# {"status": "completed", "conclusion": "success"}  ← Now we know it worked
```

### Monitoring in Real-Time

```bash
# Watch deployment in real-time
gh run watch --exit-status

# Get logs if failed
gh run view 12345 --log-failed

# Check latest run status
gh run list --limit 1 --json status,conclusion,databaseId
```

### CI/CD Script Pattern

```bash
#!/bin/bash
set -euo pipefail

# Trigger deployment
git push origin telegram

# Get latest run ID
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

# Watch with proper exit handling
echo "🚀 Monitoring deployment (Run ID: $RUN_ID)..."
if gh run watch $RUN_ID --exit-status; then
  echo "✅ Deployment succeeded!"
  exit 0
else
  echo "❌ Deployment failed!"
  echo "Fetching failed logs..."
  gh run view $RUN_ID --log-failed | tail -100
  exit 1
fi
```

---

## Lambda Monitoring

### CloudWatch Logs Streaming

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow

# Filter for errors only
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev \
  --follow \
  --filter-pattern "ERROR"

# Tail from specific time
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev \
  --since 5m \
  --follow
```

### Getting Specific Log Streams

```bash
# List recent log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --order-by LastEventTime \
  --descending \
  --max-items 5

# Get logs from specific stream
LOG_STREAM='2025/12/07/[$LATEST]abc123'
aws logs get-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --log-stream-name "$LOG_STREAM" \
  --limit 100
```

### Lambda Metrics

```bash
# Get invocation count (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600

# Get error count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600
```

---

## DynamoDB Monitoring

### Table Scan for Job Status

```bash
# Count completed jobs
aws dynamodb scan \
  --table-name dr-daily-report-telegram-jobs-dev \
  --filter-expression "#s = :completed" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":completed":{"S":"completed"}}' \
  --select COUNT

# Count failed jobs
aws dynamodb scan \
  --table-name dr-daily-report-telegram-jobs-dev \
  --filter-expression "#s = :failed" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":failed":{"S":"failed"}}' \
  --select COUNT
```

### Monitoring Parallel Job Execution

```bash
#!/bin/bash
# Monitor parallel report generation

BASELINE_COMPLETED=$(aws dynamodb scan \
  --table-name dr-daily-report-telegram-jobs-dev \
  --filter-expression "#s = :completed" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":completed":{"S":"completed"}}' \
  --select COUNT \
  --output json | jq -r '.Count')

echo "Baseline: $BASELINE_COMPLETED completed jobs"

for i in {1..30}; do
  sleep 10

  COMPLETED=$(aws dynamodb scan \
    --table-name dr-daily-report-telegram-jobs-dev \
    --filter-expression "#s = :completed" \
    --expression-attribute-names '{"#s":"status"}' \
    --expression-attribute-values '{":completed":{"S":"completed"}}' \
    --select COUNT \
    --output json | jq -r '.Count')

  NEW_JOBS=$((COMPLETED - BASELINE_COMPLETED))
  echo "[$i] New completions: $NEW_JOBS/46"

  if [ "$NEW_JOBS" -ge 46 ]; then
    echo "✅ All jobs completed!"
    break
  fi
done
```

---

## Common Monitoring Mistakes

### Mistake 1: Not Using Waiters

**Wrong:**
```bash
aws lambda update-function-code --function-name X --image-uri Y
sleep 60  # Guessing completion time
aws lambda invoke --function-name X ...
```

**Right:**
```bash
aws lambda update-function-code --function-name X --image-uri Y
aws lambda wait function-updated --function-name X  # Blocks until ready
aws lambda invoke --function-name X ...
```

### Mistake 2: Ignoring Exit Codes

**Wrong:**
```bash
# gh run watch without --exit-status always returns 0
gh run watch 12345
# Script continues even if workflow failed!
```

**Right:**
```bash
if ! gh run watch 12345 --exit-status; then
  echo "❌ Deployment failed!"
  exit 1
fi
```

### Mistake 3: Only Checking Status, Not Conclusion

**Wrong:**
```bash
STATUS=$(gh run view 12345 --json status --jq '.status')
if [ "$STATUS" = "completed" ]; then
  echo "✅ Success!"  # WRONG - might have failed!
fi
```

**Right:**
```bash
RESULT=$(gh run view 12345 --json status,conclusion --jq '{status, conclusion}')
if echo "$RESULT" | grep -q '"conclusion":"success"'; then
  echo "✅ Success!"
else
  echo "❌ Failed or cancelled"
fi
```

### Mistake 4: Not Tailing Logs Before Concluding "Bug"

**Wrong:**
```bash
# Deployment fails
echo "Must be a bug in the code!"  # Jump to conclusion
```

**Right:**
```bash
# Deployment fails
echo "Checking logs..."
gh run view 12345 --log-failed
# → Reveals: "Permission denied" (not a code bug, IAM issue!)
```

---

## Infrastructure-Deployment Contract Validation

**Principle:** Query AWS infrastructure, validate secrets match reality.

### The Problem: Configuration Drift

**Scenario:** Terraform creates CloudFront distribution with ID `E123ABC`. GitHub secret `CLOUDFRONT_DISTRIBUTION_ID` is set to `E123ABC`.

**Months later:** Someone manually creates new distribution in AWS console, deletes old one. Terraform doesn't track manual changes. GitHub secret still points to `E123ABC` (which no longer exists).

**Result:** Deployment fails with "DistributionNotFound" error.

### The Solution: Pre-Deployment Validation

**Pattern:** First job in every deployment pipeline queries AWS, validates secrets match reality.

```yaml
# .github/workflows/deploy.yml
jobs:
  validate-deployment-config:
    name: Validate Infrastructure & Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-1

      - name: Validate CloudFront Distributions
        env:
          GITHUB_TEST_DIST: ${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }}
          GITHUB_APP_DIST: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}
        run: |
          # Query actual infrastructure from AWS (single source of truth)
          ACTUAL_TEST=$(aws cloudfront list-distributions \
            --query 'DistributionList.Items[?Comment==`dr-daily-report TEST CloudFront - dev`].Id' \
            --output text)

          ACTUAL_APP=$(aws cloudfront list-distributions \
            --query 'DistributionList.Items[?Comment==`dr-daily-report APP CloudFront - dev`].Id' \
            --output text)

          # Validate secrets match reality
          if [ "$ACTUAL_TEST" != "$GITHUB_TEST_DIST" ]; then
            echo "❌ Mismatch: CLOUDFRONT_TEST_DISTRIBUTION_ID"
            echo "   AWS (reality):    $ACTUAL_TEST"
            echo "   GitHub (secret):  $GITHUB_TEST_DIST"
            echo ""
            echo "Update GitHub secret to match AWS infrastructure:"
            echo "  gh secret set CLOUDFRONT_TEST_DISTRIBUTION_ID --body \"$ACTUAL_TEST\""
            exit 1  # Fail fast - blocks entire pipeline
          fi

          if [ "$ACTUAL_APP" != "$GITHUB_APP_DIST" ]; then
            echo "❌ Mismatch: CLOUDFRONT_DISTRIBUTION_ID"
            echo "   AWS (reality):    $ACTUAL_APP"
            echo "   GitHub (secret):  $GITHUB_APP_DIST"
            echo ""
            echo "Update GitHub secret to match AWS infrastructure:"
            echo "  gh secret set CLOUDFRONT_DISTRIBUTION_ID --body \"$ACTUAL_APP\""
            exit 1
          fi

          echo "✅ All secrets match actual infrastructure"

      - name: Validate S3 Buckets
        env:
          GITHUB_BUCKET: ${{ secrets.S3_FRONTEND_BUCKET }}
        run: |
          # Check bucket exists
          if ! aws s3 ls s3://$GITHUB_BUCKET > /dev/null 2>&1; then
            echo "❌ S3 bucket does not exist: $GITHUB_BUCKET"
            exit 1
          fi

          # Validate bucket is in correct region
          BUCKET_REGION=$(aws s3api get-bucket-location \
            --bucket $GITHUB_BUCKET \
            --query 'LocationConstraint' --output text)

          if [ "$BUCKET_REGION" != "ap-southeast-1" ]; then
            echo "❌ Bucket in wrong region: $BUCKET_REGION (expected: ap-southeast-1)"
            exit 1
          fi

          echo "✅ S3 bucket validated"

      - name: Validate Lambda Functions
        run: |
          # Check Lambda functions exist
          FUNCTIONS=(
            "dr-daily-report-worker-dev"
            "dr-daily-report-scheduler-dev"
          )

          for FUNC in "${FUNCTIONS[@]}"; do
            if ! aws lambda get-function --function-name $FUNC > /dev/null 2>&1; then
              echo "❌ Lambda function does not exist: $FUNC"
              exit 1
            fi
          done

          echo "✅ All Lambda functions validated"

  build:
    needs: validate-deployment-config  # Won't run if validation fails
    runs-on: ubuntu-latest
    steps:
      # ... rest of build/deploy pipeline
```

**Benefits:**
- ✅ Self-healing: Automatically detects when secrets are stale
- ✅ No manual checklist: Code queries AWS, compares to secrets
- ✅ Catches drift: Even if someone changed AWS console manually
- ✅ Single source of truth: AWS infrastructure is reality
- ✅ Fail fast: First job, blocks deployment if secrets wrong (< 30 seconds)
- ✅ Helpful error messages: Shows exact command to fix mismatch

### When to Validate

**Always validate:**
- CloudFront distribution IDs (for cache invalidation)
- S3 bucket names (for file sync)
- Lambda function names (if not in Terraform variables)
- Any AWS resource ID referenced in deployment scripts

**DON'T validate:**
- Secrets managed by Doppler (already version-controlled)
- Terraform-managed resources (Terraform state is source of truth)
- Resources created during deployment (don't exist yet)

---

## Monitoring Checklist

Before declaring a deployment "successful" or "failed", verify:

- [ ] Used AWS waiters (not `sleep`)
- [ ] Checked GitHub Actions `conclusion` (not just `status`)
- [ ] Tailed Lambda CloudWatch logs for errors
- [ ] Verified smoke test passes
- [ ] Checked metrics (invocation count, error rate)
- [ ] Monitored job status if parallel execution
- [ ] Used `--exit-status` with `gh run watch`
- [ ] Validated infrastructure-deployment contract (secrets match AWS reality)

---

## See Also

- [Lambda Versioning](LAMBDA_VERSIONING.md) - Zero-downtime pattern
- [Deployment Workflow](WORKFLOW.md) - Complete deployment process
- [CI/CD Architecture](CI_CD.md) - GitHub Actions integration
