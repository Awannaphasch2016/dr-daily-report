# Telegram Mini App - Manual Deployment Runbook

**Purpose**: Step-by-step manual testing guide from local development to production.
**Last Updated**: 2025-11-28

---

## Quick Reference

| Phase | Command | Pass Criteria |
|-------|---------|---------------|
| Local | `just setup-local-dynamodb && just dev-api` | Health returns `{"status": "ok"}` |
| Dev | `./scripts/deploy-backend.sh dev` | Smoke tests pass, alias updated |
| E2E | `pytest tests/test_e2e_frontend.py -k "not slow" -v` | 12 tests pass |
| Staging | `./scripts/deploy-backend.sh staging` | Same as dev |
| Prod | `./scripts/deploy-backend.sh prod` | Same as dev |

---

## Phase 0: Prerequisites

### 0.1 Tools Check

```bash
# Run each command - all should return version numbers
docker --version          # Docker 20.x+
aws --version             # AWS CLI 2.x
terraform --version       # Terraform 1.x
doppler --version         # Doppler CLI
jq --version              # JSON processor
```

**If any fails**: Install the missing tool before proceeding.

### 0.2 Python Virtual Environment

**IMPORTANT**: Always use the project's virtual environment for consistent dependencies.

```bash
# Activate virtual environment
source venv/bin/activate

# Verify you're in venv (should show venv path)
which python
# Expected: /home/anak/dev/dr-daily-report_telegram/venv/bin/python

# Install dependencies if needed
pip install -r requirements_minimal.txt
```

**If venv doesn't exist**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements_minimal.txt
```

### 0.3 AWS Credentials

```bash
aws sts get-caller-identity
```

**Expected**: Returns your AWS account ID and ARN
```json
{
    "UserId": "AIDAXXXXXXXXXX",
    "Account": "755283537543",
    "Arn": "arn:aws:iam::755283537543:user/your-username"
}
```

**If fails**: Run `aws configure` or check `~/.aws/credentials`

### 0.4 Doppler Authentication

```bash
doppler configure get project
```

**Expected**: `dr-daily-report` or similar project name
**If fails**: Run `doppler login` and `doppler setup`

---

## Phase 1: Local Testing

### 1.1 Start DynamoDB Local

```bash
# If container doesn't exist
docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local

# If container exists but stopped
docker start dynamodb-local

# Verify it's running
docker ps | grep dynamodb-local
```

**Expected**: Container running on port 8000
**If fails**:
- "name already in use": Run `docker start dynamodb-local` instead
- Port in use: `docker rm -f dynamodb-local`, then retry
- Docker not running: Start Docker Desktop

### 1.2 Create Local Tables

```bash
# Make sure venv is activated first!
source venv/bin/activate

just setup-local-dynamodb
```

**Expected output**:
```
Creating tables (using doppler for consistent credentials)...
 Created table: dr-daily-report-telegram-watchlist-dev
 Created table: dr-daily-report-telegram-jobs-dev
 Created table: dr-daily-report-telegram-cache-dev

Verifying tables...
dr-daily-report-telegram-cache-dev
dr-daily-report-telegram-jobs-dev
dr-daily-report-telegram-watchlist-dev
```

**If fails**:
- "Docker is not running": Start Docker
- Connection refused: DynamoDB Local not running (step 1.1)
- Empty tables list: Re-run `just setup-local-dynamodb`

### 1.3 Verify Tables Created

```bash
doppler run -- aws dynamodb list-tables --endpoint-url http://localhost:8000 --region ap-southeast-1
```

**Expected**:
```json
{
    "TableNames": [
        "dr-daily-report-telegram-cache-dev",
        "dr-daily-report-telegram-jobs-dev",
        "dr-daily-report-telegram-watchlist-dev"
    ]
}
```

**If empty**: Re-run `just setup-local-dynamodb`

### 1.4 Start Local API Server

```bash
# In a NEW terminal - activate venv first!
source venv/bin/activate

just dev-api
```

**Expected**: Server starts on port 8001
```
Starting FastAPI with Local DynamoDB
========================================
Configuration:
  - USE_LOCAL_DYNAMODB=true
  - WATCHLIST_TABLE_NAME=dr-daily-report-telegram-watchlist-dev
  - JOBS_TABLE_NAME=dr-daily-report-telegram-jobs-dev
  ...
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**If fails**:
- Port 8001 in use: `lsof -i :8001` to find process, kill it
- ModuleNotFoundError: Activate venv first (`source venv/bin/activate`)
- DynamoDB errors: Make sure tables were created (step 1.2)

### 1.5 Test Local Endpoints

Run these in another terminal:

```bash
# Test 1: Health endpoint
curl -s http://localhost:8001/api/v1/health | jq
```
**Expected**: `{"status": "ok", "version": "1.0.0"}`

```bash
# Test 2: Search endpoint
curl -s "http://localhost:8001/api/v1/search?q=NVDA" | jq '.results[:2]'
```
**Expected**: Array with ticker results like `[{"ticker": "NVDA19", ...}]`

```bash
# Test 3: Rankings endpoint
curl -s "http://localhost:8001/api/v1/rankings?category=top_gainers" | jq '.tickers[:2]'
```
**Expected**: Array with ranking items (field is `tickers`, not `rankings`)

```bash
# Test 4: Watchlist GET (empty initially)
curl -s "http://localhost:8001/api/v1/watchlist" -H "X-Telegram-User-Id: test123" | jq
```
**Expected**: `{"tickers": []}`

```bash
# Test 5: Watchlist POST (add ticker)
curl -s -X POST "http://localhost:8001/api/v1/watchlist" \
  -H "X-Telegram-User-Id: test123" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA19"}' | jq
```
**Expected**: `{"status": "ok", "ticker": "NVDA19"}`

```bash
# Test 6: Watchlist GET (verify persistence)
curl -s "http://localhost:8001/api/v1/watchlist" -H "X-Telegram-User-Id: test123" | jq
```
**Expected**: `{"tickers": [{"ticker": "NVDA19", "company_name": "NVIDIA Corporation", ...}]}`

### 1.6 Local Testing Limitations

**These endpoints DON'T work locally:**

| Endpoint | Why | Test in Dev |
|----------|-----|-------------|
| `POST /api/v1/report/{ticker}` | Requires SQS (async queue) | Yes |
| `GET /api/v1/report/{ticker}` | Takes 50-60s, will timeout | Yes |
| `GET /api/v1/report/status/{job_id}` | Requires async job first | Yes |

### 1.7 Local Testing Checklist

| Test | Command | Expected | Pass? |
|------|---------|----------|-------|
| Health | `curl localhost:8001/api/v1/health` | `{"status": "ok"}` | [ ] |
| Search | `curl "localhost:8001/api/v1/search?q=NVDA"` | Results array | [ ] |
| Rankings | `curl "localhost:8001/api/v1/rankings?category=top_gainers"` | Tickers array | [ ] |
| Watchlist GET | `curl localhost:8001/api/v1/watchlist -H "X-Telegram-User-Id: test"` | Empty or items | [ ] |
| Watchlist POST | `curl -X POST ... -d '{"ticker":"NVDA19"}'` | Status ok | [ ] |

**ALL MUST PASS before proceeding to Phase 2**

### 1.8 Cleanup Local Testing

```bash
# Stop API server: Ctrl+C in the terminal running just dev-api

# Stop DynamoDB Local (optional - keeps data for next session)
docker stop dynamodb-local

# Remove DynamoDB Local (clears all data)
docker rm -f dynamodb-local
```

---

## Phase 2: Dev Environment

### 2.1 Terraform Infrastructure (if needed)

Only run if infrastructure changed:

```bash
cd terraform
terraform init
doppler run -- terraform plan -var-file=terraform.tfvars
```

**Expected**: Plan shows resources to create/update (no errors)
**If fails**:
- "Backend configuration changed": `terraform init -reconfigure`
- Missing variables: Check `terraform.tfvars` exists

```bash
# Apply only if plan looks correct
doppler run -- terraform apply -var-file=terraform.tfvars
```

### 2.2 Deploy Backend to Dev

```bash
cd /home/anak/dev/dr-daily-report_telegram
./scripts/deploy-backend.sh dev
```

**Expected output sequence**:
```
 Deploying backend to dev...
 ECR Repository: 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev
 Logging in to ECR...
 Building Docker image...
 Pushing image to ECR...
 Updating Lambda functions...
 Running smoke tests on $LATEST...
   Testing Telegram API health...
   Telegram API health check passed
 Publishing new versions...
  Telegram API: Version 42
  Report Worker: Version 42
 Updating 'live' aliases...
  Telegram API: live -> v42
  Report Worker: live -> v42
 Backend deployed successfully!
```

**If smoke test fails**:
- $LATEST is updated but "live" alias NOT moved (users unaffected)
- Check Lambda logs: `aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow`
- Fix code, redeploy

### 2.3 Get Dev API URL

```bash
cd terraform
terraform output telegram_api_invoke_url
```

**Expected**: `https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1`

### 2.4 Test Dev Endpoints

```bash
API_URL="https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com"

# Test 1: Health
curl -s "${API_URL}/api/v1/health" | jq
```
**Expected**: `{"status": "ok"}`

```bash
# Test 2: Search
curl -s "${API_URL}/api/v1/search?q=NVDA" | jq '.results[:2]'
```
**Expected**: Results array

```bash
# Test 3: Rankings
curl -s "${API_URL}/api/v1/rankings?category=top_gainers" | jq '.tickers[:2]'
```
**Expected**: Tickers array

```bash
# Test 4: Async report flow (this is the critical test)
JOB_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/report/DBS19")
echo "Job created: $JOB_RESPONSE"
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# Poll for completion (wait ~60s for report generation)
sleep 30
curl -s "${API_URL}/api/v1/report/status/${JOB_ID}" | jq '{status, ticker}'
# Repeat until status is "completed" or "failed"
```
**Expected**: Status progresses from `pending` -> `in_progress` -> `completed`

### 2.5 Dev Testing Checklist

| Test | Pass? |
|------|-------|
| Deploy script completes without errors | [ ] |
| Smoke tests pass (health check) | [ ] |
| Health endpoint returns ok | [ ] |
| Search returns results | [ ] |
| Rankings returns tickers | [ ] |
| Async report POST returns job_id | [ ] |
| Job status shows completed (after ~60s) | [ ] |

**ALL MUST PASS before proceeding to Phase 3**

---

## Phase 3: Staging Environment

> **Note**: Staging environment not yet deployed. These are placeholder instructions.

### 3.1 Deploy to Staging

```bash
./scripts/deploy-backend.sh staging
```

### 3.2 Test Staging Endpoints

```bash
STAGING_URL="https://staging-xxxxxxxx.execute-api.ap-southeast-1.amazonaws.com"

# Same tests as dev
curl -s "${STAGING_URL}/api/v1/health" | jq
curl -s "${STAGING_URL}/api/v1/search?q=NVDA" | jq '.results[:2]'
curl -s -X POST "${STAGING_URL}/api/v1/report/DBS19" | jq
```

### 3.3 Staging Checklist

| Test | Pass? |
|------|-------|
| Deploy script completes | [ ] |
| Health endpoint returns ok | [ ] |
| Search returns results | [ ] |
| Async report completes | [ ] |

---

## Phase 4: Production Environment

> **Note**: Production environment not yet deployed.

### 4.1 Pre-Production Checklist

Before deploying to production:

| Item | Status |
|------|--------|
| All staging tests pass | [ ] |
| Doppler prod secrets configured | [ ] |
| CloudWatch alarms set up | [ ] |
| Rollback plan documented | [ ] |

### 4.2 Deploy to Production

```bash
./scripts/deploy-backend.sh prod
```

### 4.3 Verify Production

```bash
PROD_URL="https://prod-xxxxxxxx.execute-api.ap-southeast-1.amazonaws.com"

# Health check
curl -s "${PROD_URL}/api/v1/health" | jq
```

### 4.4 Rollback (if needed)

```bash
# Get current version
aws lambda get-alias \
    --function-name dr-daily-report-telegram-api-prod \
    --name live \
    --query 'FunctionVersion' \
    --output text

# Rollback to previous version (e.g., version 41)
aws lambda update-alias \
    --function-name dr-daily-report-telegram-api-prod \
    --name live \
    --function-version 41

aws lambda update-alias \
    --function-name dr-daily-report-report-worker-prod \
    --name live \
    --function-version 41
```

---

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: slowapi` | Not using venv | `source venv/bin/activate` |
| `ResourceNotFoundException` | DynamoDB table missing | Run `just setup-local-dynamodb` (local) or check Terraform (AWS) |
| `Connection refused :8000` | DynamoDB Local not running | `docker start dynamodb-local` |
| `Connection refused :8001` | API server not running | `just dev-api` |
| Empty `TableNames` list | Credential mismatch | Use `doppler run --` for all commands |
| `504 Gateway Timeout` | Lambda timeout (sync endpoint) | Use async POST endpoint instead |
| `401 Unauthorized` | Missing/invalid API keys | Check Doppler secrets |
| Smoke test fails | Code bug in $LATEST | Check Lambda logs, fix code, redeploy |
| `AccessDenied` on ECR push | IAM permissions | Check IAM policy for ECR access |
| `InvalidAddress` SQS error | SQS not available locally | This endpoint only works in AWS (dev/staging/prod) |

---

## Quick Commands Reference

```bash
# Virtual Environment (ALWAYS DO THIS FIRST)
source venv/bin/activate

# Local Development
just setup-local-dynamodb    # Create local DynamoDB tables
just dev-api                 # Start local API server
docker start dynamodb-local  # Start DynamoDB Local container
docker stop dynamodb-local   # Stop DynamoDB Local container

# Verify Local Tables
doppler run -- aws dynamodb list-tables --endpoint-url http://localhost:8000 --region ap-southeast-1

# Deployment
./scripts/deploy-backend.sh dev      # Deploy to dev
./scripts/deploy-backend.sh staging  # Deploy to staging
./scripts/deploy-backend.sh prod     # Deploy to prod

# Monitoring
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow

# Rollback
aws lambda update-alias --function-name FUNC --name live --function-version PREV

# Terraform
cd terraform && terraform plan -var-file=terraform.tfvars
cd terraform && doppler run -- terraform apply -var-file=terraform.tfvars
```

---

## Phase 5: E2E Frontend Testing

### 5.1 Prerequisites

```bash
# Ensure Playwright browsers are installed
playwright install chromium

# Verify pytest-playwright is installed
pip show pytest-playwright
```

### 5.2 Run E2E Tests Against Dev

```bash
# Quick tests (30 seconds) - homepage, search, tabs
pytest tests/test_e2e_frontend.py -k "not slow" -v

# All tests including full report generation (2+ minutes)
pytest tests/test_e2e_frontend.py -v

# Watch browser during tests (debugging)
pytest tests/test_e2e_frontend.py -v --headed

# Test against local frontend
FRONTEND_URL=http://localhost:5500 pytest tests/test_e2e_frontend.py -k "not slow" -v
```

### 5.3 E2E Test Coverage

| Test Class | Tests | What's Verified |
|------------|-------|-----------------|
| `TestHomePage` | 3 | Page loads, tabs visible, ranking buttons |
| `TestSearchFlow` | 3 | Search input, autocomplete, ticker info |
| `TestReportGeneration` | 4 | Modal opens, loading state, report completes, close |
| `TestRankingsTab` | 2 | Category switching, empty state handling |
| `TestWatchlistTab` | 1 | Tab switching |
| `TestResponsiveness` | 2 | Mobile (375px) and tablet (768px) viewports |

### 5.4 E2E Testing Checklist

| Test | Command | Pass? |
|------|---------|-------|
| Quick tests pass | `pytest tests/test_e2e_frontend.py -k "not slow" -v` | [ ] |
| Full report generation | `pytest tests/test_e2e_frontend.py::TestReportGeneration::test_report_generation_completes -v` | [ ] |
| Mobile viewport works | `pytest tests/test_e2e_frontend.py::TestResponsiveness -v` | [ ] |

### 5.5 Common E2E Test Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `playwright._impl._errors.Error: Browser closed` | Browser not installed | `playwright install chromium` |
| `TimeoutError` on report test | API slow or failing | Check API Gateway logs |
| `strict mode violation` | Multiple elements match selector | Use more specific CSS selector |
| `element not found` | UI changed | Update test selectors in `test_e2e_frontend.py` |

---

## Environment URLs

| Environment | API Gateway URL | Frontend URL | Status |
|-------------|-----------------|--------------|--------|
| Local | `http://localhost:8001/api/v1` | `http://localhost:5500` | Development |
| Dev | `https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1` | `https://demjoigiw6myp.cloudfront.net` | Deployed |
| Staging | TBD | TBD | Not deployed |
| Prod | TBD | TBD | Not deployed |
