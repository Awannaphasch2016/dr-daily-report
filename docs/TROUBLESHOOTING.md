# Troubleshooting Guide

Common issues and solutions for DR Daily Report Telegram Mini App.

---

## Deployment Issues

### Lambda Permission Errors

**Problem:** `User is not authorized to perform: lambda:UpdateFunctionCode`

**Solution:**
1. Check IAM policies attached to deployment user
2. See [docs/deployment/PERMISSIONS_REQUIRED.md](deployment/PERMISSIONS_REQUIRED.md) for full list
3. Use AWS IAM policy simulator to verify permissions

**Quick fix:**
```bash
# Verify current permissions
aws iam list-attached-user-policies --user-name <your-user>

# If missing Lambda permissions, attach policy
aws iam attach-user-policy \
  --user-name <your-user> \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess
```

---

### Lambda Timeout in Production

**Problem:** Function times out after 30s, but works locally

**Root Cause:** API Gateway HTTP API has 30s max timeout (AWS hard limit)

**Solution:**
Use async report generation pattern:
```bash
# 1. Start report (returns immediately)
POST /api/v1/report/DBS19
→ {"job_id": "rpt_xxx", "status": "pending"}

# 2. Poll for completion
GET /api/v1/report/status/rpt_xxx
→ {"status": "completed", "result": {...}}
```

**Why sync endpoint fails:**
- Report generation: ~50-60s
- API Gateway timeout: 30s
- Lambda timeout: 120s (irrelevant, gateway cuts first)

---

### CloudFront 404 After Deployment

**Problem:** Frontend returns 404 immediately after deploying new version

**Root Cause:** CloudFront invalidation not yet complete

**Solution:**
Wait 2-3 minutes for invalidation to propagate globally.

**Verify invalidation status:**
```bash
# Check latest invalidation
aws cloudfront list-invalidations \
  --distribution-id <dist-id> \
  --max-items 1

# Wait for completion
aws cloudfront wait invalidation-completed \
  --distribution-id <dist-id> \
  --id <invalidation-id>
```

**Prevention:**
Use two-CloudFront pattern (TEST + APP) - see `.claude/CLAUDE.md` line 1586+

---

### Terraform State Lock

**Problem:** `Error acquiring state lock`

**DO NOT force-unlock unless:**
- ✅ Terraform process crashed (verify with `ps aux | grep terraform`)
- ✅ No active terraform operations (check AWS console)

**Correct workflow:**
```bash
# 1. Check if terraform is running
ps aux | grep terraform

# 2. If process exists, WAIT for it to finish
# 3. If process is dead, then force-unlock
terraform force-unlock <lock-id>
```

**Why this matters:**
Force-unlocking an active operation corrupts state → requires manual recovery

---

## Development Issues

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Install dependencies
just setup
# or
pip install -r requirements.txt

# Verify installation
python -c "import src; print('OK')"
```

---

### Doppler Secrets Not Loading

**Problem:** Environment variables empty when running locally

**Solution:**
```bash
# 1. Verify Doppler CLI installed
doppler --version

# 2. Login to Doppler
doppler login

# 3. Select correct project/config
doppler setup

# 4. Test secrets loading
doppler run -- env | grep OPENROUTER_API_KEY

# 5. Run commands with doppler
doppler run -- python -m uvicorn src.api.app:app --reload
```

**Alternative (without Doppler):**
Create `.env` file with required variables (NOT recommended for production)

---

### Pytest Collection Errors

**Problem:** `ERROR collecting tests/test_*.py`

**Root Cause:** Missing test dependencies or syntax errors

**Solution:**
```bash
# 1. Install test dependencies
pip install -r requirements-test.txt

# 2. Check syntax errors
python -m py_compile tests/test_*.py

# 3. Run specific test file
pytest tests/test_agent.py -v

# 4. Show full traceback
pytest tests/ --tb=long
```

---

## Test Failures

### E2E Tests Timeout

**Problem:** `TimeoutError: waiting for selector "[data-testid='mini-chart']"`

**Root Cause:**
1. CloudFront not deployed
2. Frontend build outdated
3. Selector changed

**Solution:**
```bash
# 1. Verify CloudFront deployed
curl -I https://d24cidhj2eghux.cloudfront.net

# 2. Check if TEST CloudFront updated
aws cloudfront get-distribution \
  --id <test-dist-id> \
  --query 'Distribution.Status'

# 3. Increase timeout in test
# tests/e2e/conftest.py
page.set_default_timeout(30000)  # 30s instead of 10s

# 4. Run single test with verbose output
E2E_BASE_URL="https://..." pytest tests/e2e/test_twinbar_enhanced.py::test_chart_renders -v
```

---

### Schema Contract Tests Failing

**Problem:** `AssertionError: Missing required field: user_facing_scores`

**Root Cause:** Scheduler writes data that doesn't match UI expectations

**Solution:**
1. Check canonical schema: `tests/contracts/cached_report_schema.py`
2. Fix scheduler to populate missing field
3. Re-run schema tests before deploying:
```bash
pytest tests/infrastructure/test_scheduler_schema_contract.py -v
pytest tests/telegram/test_rankings_schema_contract.py -v
```

**Prevention:**
Always run schema contract tests before deploying (CI should enforce this)

---

## Production Issues

### Aurora Cache Empty

**Problem:** Rankings API returns empty arrays

**Root Cause:** Aurora cache not populated

**Solution:**
```bash
# 1. Trigger cache population
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action":"parallel_precompute","include_report":true}' \
  /tmp/result.json

# 2. Monitor progress
# Use script from /tmp/monitor_cache_population.sh

# 3. Verify cache populated
python scripts/check_aurora_cache.py
```

---

### DynamoDB Job Stuck in "pending"

**Problem:** Job status remains "pending" for >5 minutes

**Root Cause:**
1. Lambda worker not processing queue
2. SQS → Lambda trigger disconnected

**Solution:**
```bash
# 1. Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessages

# 2. Verify Lambda event source mapping
aws lambda list-event-source-mappings \
  --function-name dr-daily-report-sqs-worker-dev

# 3. Check if mapping is enabled
# State should be "Enabled", not "Disabled"

# 4. If disabled, enable it
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --enabled
```

---

### High Lambda Costs

**Problem:** Monthly Lambda bill exceeds expectations

**Root Cause:**
1. Sync report endpoint timing out → retries
2. No caching → regenerating reports

**Solution:**
```bash
# 1. Check invocation counts
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --start-time 2025-12-01T00:00:00Z \
  --end-time 2025-12-07T23:59:59Z \
  --period 86400 \
  --statistics Sum

# 2. Enable Aurora caching (if not already)
# See terraform/aurora.tf

# 3. Use async pattern (no retries)
# Replace sync GET /api/v1/report/{ticker}
# With async POST → poll pattern
```

---

## Network Issues

### CORS Errors in Frontend

**Problem:** `Access to fetch blocked by CORS policy`

**Root Cause:** API Gateway CORS not configured for CloudFront origin

**Solution:**
```bash
# 1. Verify CloudFront URL in terraform
# terraform/envs/dev/terraform.tfvars
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net"  # Must match actual URL
]

# 2. Apply terraform changes
cd terraform
terraform apply -var-file=envs/dev/terraform.tfvars

# 3. Verify CORS headers
curl -H "Origin: https://demjoigiw6myp.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS \
  https://bkma0w5ij7.execute-api.ap-southeast-1.amazonaws.com/api/v1/report/DBS19
```

---

## Database Issues

### Aurora Connection Timeout

**Problem:** `OperationalError: (2003, "Can't connect to MySQL server")`

**Root Cause:**
1. Lambda not in VPC
2. Security group blocking port 3306

**Solution:**
```bash
# 1. Verify Lambda is in correct VPC
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'VpcConfig'

# 2. Check security group rules
aws ec2 describe-security-groups \
  --group-ids <lambda-sg-id>

# 3. Verify Aurora security group allows Lambda SG
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].VpcSecurityGroups'
```

---

## Monitoring & Debugging

### Check Lambda Logs

```bash
# Tail latest logs
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow

# Filter errors only
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "ERROR"

# Specific time range
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev \
  --since 1h \
  --filter-pattern "job_id"
```

---

### GitHub Actions Deployment Failures

**Problem:** CI/CD pipeline fails at deploy step

**Solution:**
```bash
# 1. View failed run logs
gh run view <run-id> --log-failed

# 2. Re-run failed jobs
gh run rerun <run-id> --failed

# 3. Check secrets are set
gh secret list

# 4. Verify required secrets exist
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.
```

---

## Getting Help

**If issue not listed here:**
1. Check [CLAUDE.md](.claude/CLAUDE.md) for architectural context
2. Search GitHub issues: https://github.com/your-repo/issues
3. Check AWS service health: https://status.aws.amazon.com
4. Review recent commits for breaking changes: `git log --oneline -20`

**When reporting issues, include:**
- Error message (full traceback)
- Environment (dev/staging/prod)
- Steps to reproduce
- Expected vs actual behavior
- Logs from CloudWatch/terminal
