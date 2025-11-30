# Telegram Mini App - Manual Deployment Runbook

**Purpose**: Step-by-step manual testing guide from local development to production.
**Last Updated**: 2025-11-30

---

## Quick Reference

| Phase | Command | Pass Criteria |
|-------|---------|---------------|
| CI/CD Lint | `just ci-lint` | No actionlint errors |
| CI/CD Dry-run | `just ci-dryrun test` | All jobs pass dry-run |
| Local | `just setup-local-dynamodb && just dev-api` | Health returns `{"status": "ok"}` |
| **All Envs (CI/CD)** | `git push origin telegram` | Auto-deploys to dev → staging → prod |
| Manual Deploy | `./scripts/deploy-backend.sh <env>` | Smoke tests pass, alias updated |
| Rollback | `./scripts/rollback.sh <env> <version>` | Alias moved to previous version |
| E2E | `pytest tests/test_e2e_frontend.py -k "not slow" -v` | 12 tests pass |

---

## Zero-Downtime Deployment Architecture

### Lambda Version/Alias Model

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                               │
│         (Always invokes "live" alias, never $LATEST)        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   "live" Alias       │ ← Users hit this
              │   (Pointer to vN)    │
              └──────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    Version 41      Version 42       $LATEST
    (immutable)     (immutable)      (mutable)
    [OLD CODE]      [NEW CODE]       [STAGING]
```

**Key concepts:**
- `$LATEST`: Mutable staging area where new code lands first
- Published versions (v1, v2, ...): Immutable snapshots
- `live` alias: Pointer that API Gateway uses (users hit this)

**Why this matters (Zero-Downtime):**
- New code goes to `$LATEST` but users still see old version
- Smoke tests run against `$LATEST` BEFORE alias update
- If tests fail, alias is NEVER updated → users see no errors
- Rollback = move alias pointer (~100ms, no rebuild)

### Deployment Flow

```
1. update-function-code    → Code lands in $LATEST
   (users still on v41)

2. aws lambda invoke       → Test $LATEST directly
   (users still on v41)

3. IF TESTS PASS:
   - publish-version       → Create v42 snapshot
   - update-alias          → Move "live" to v42
   (users NOW on v42)

4. IF TESTS FAIL:
   - Pipeline stops
   - Alias NOT updated
   (users still on v41, never saw broken code)
```

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

### 0.5 CI/CD Tools (for GitHub Actions testing)

```bash
# Check act is installed
~/.local/bin/act --version         # act version 0.2.x

# Check actionlint is installed
~/.local/bin/actionlint --version  # actionlint 1.7.x
```

**If not installed**:
```bash
# Install act (GitHub Actions local runner)
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b ~/.local/bin

# Install actionlint (static analyzer)
curl -sL https://github.com/rhysd/actionlint/releases/download/v1.7.4/actionlint_1.7.4_linux_amd64.tar.gz | tar xz -C ~/.local/bin actionlint

# Configure act with medium Docker image
mkdir -p ~/.config/act
echo "-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest" > ~/.config/act/actrc
```

---

## Phase 0.5: CI/CD Workflow Testing (TDD)

**Purpose**: Validate GitHub Actions workflow locally before pushing to avoid CI failures.

### 0.5.1 Static Analysis (Fast)

```bash
just ci-lint
```

**Expected**:
```
🔍 Running actionlint on workflows...
✅ All workflows pass actionlint
```

**If fails**: Fix syntax errors in `.github/workflows/*.yml`

### 0.5.2 Dry-Run Jobs

```bash
# Dry-run the environment detection job
just ci-dryrun environment

# Dry-run the test job
just ci-dryrun test
```

**Expected**: All steps show `✅ Success`

### 0.5.3 Full CI/CD Validation

```bash
just ci-test
```

**Expected**: Lint passes, dry-runs succeed for environment and test jobs.

### 0.5.4 Run Jobs Locally (Optional, requires Docker)

```bash
# Run the test job locally with actual execution
just ci-run test
```

**Note**: This runs the actual job in Docker, which takes longer but gives more confidence.

### 0.5.5 CI/CD Testing Checklist

| Test | Command | Pass? |
|------|---------|-------|
| Actionlint passes | `just ci-lint` | [ ] |
| Environment job dry-run | `just ci-dryrun environment` | [ ] |
| Test job dry-run | `just ci-dryrun test` | [ ] |

**ALL MUST PASS before pushing workflow changes**

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

Only run if infrastructure changed (e.g., new Lambda memory, new DynamoDB table):

```bash
cd terraform

# Initialize with dev backend
terraform init -backend-config=envs/dev/backend.hcl

# Plan with dev vars
terraform plan -var-file=envs/dev/terraform.tfvars
```

**Expected**: Plan shows resources to create/update (no errors)
**If fails**:
- "Backend configuration changed": `terraform init -backend-config=envs/dev/backend.hcl -reconfigure`
- Missing variables: Check `envs/dev/terraform.tfvars` exists

```bash
# Apply only if plan looks correct
terraform apply -var-file=envs/dev/terraform.tfvars

# IMPORTANT: After applying to dev, also apply to staging and prod
terraform init -backend-config=envs/staging/backend.hcl -reconfigure
terraform apply -var-file=envs/staging/terraform.tfvars

terraform init -backend-config=envs/prod/backend.hcl -reconfigure
terraform apply -var-file=envs/prod/terraform.tfvars
```

**Note**: Terraform is only for infrastructure changes. Code deploys via CI/CD (no terraform).

### 2.2 Deploy via GitHub Actions (Recommended)

Push to `telegram` branch triggers **auto-progressive deployment to ALL environments**:

```bash
git add .
git commit -m "Your changes"
git push origin telegram
```

**Pipeline Flow:**
```
git push to telegram
       ↓
┌──────────────────┐
│   Quality Gates  │  Unit tests, syntax check
└────────┬─────────┘
         ↓
┌──────────────────┐
│   Build Image    │  Docker build → ECR (ONE image for all envs)
└────────┬─────────┘
         ↓
┌──────────────────┐
│   Deploy Dev     │  update-function-code → smoke test → promote
└────────┬─────────┘
         ↓ (only if dev succeeds)
┌──────────────────┐
│  Deploy Staging  │  update-function-code → smoke test → promote
└────────┬─────────┘
         ↓ (only if staging succeeds)
┌──────────────────┐
│   Deploy Prod    │  update-function-code → smoke test → promote
└──────────────────┘
```

**Monitor deployment:**
```bash
# Watch the workflow in terminal
gh run watch

# Or view in browser
gh run view --web

# List recent runs
gh run list --workflow=deploy.yml
```

**Key Points:**
- Single push deploys to dev → staging → prod automatically
- Same Docker image promoted through all environments
- Each environment smoke-tested before promotion
- NO terraform in CI/CD (infrastructure assumed to exist)

**If smoke test fails:**
- Pipeline stops at that environment
- `$LATEST` is updated but "live" alias NOT moved
- Users continue seeing old (working) version
- Downstream environments NOT affected
- Check logs: `gh run view --log-failed`
- Fix code, push again

### 2.2a Manual Deploy (Alternative)

For local testing or when CI/CD is unavailable:

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

**Note:** The script follows the same zero-downtime pattern as CI/CD.

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

### 2.6 CI/CD Deployment Monitoring

#### Watch GitHub Actions Run

```bash
# List recent runs
gh run list --workflow=deploy.yml

# Watch current run (auto-refreshes)
gh run watch

# View specific run with logs
gh run view <run-id> --log

# View only failed steps
gh run view --log-failed
```

#### Verify Deployment Success

After workflow completes:

```bash
# Check which version is live
aws lambda get-alias \
    --function-name dr-daily-report-telegram-api-dev \
    --name live \
    --query 'FunctionVersion' \
    --output text

# Verify health via API Gateway
curl -s "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com/api/v1/health" | jq
```

#### Manual Rollback (if needed)

```bash
# List recent versions
aws lambda list-versions-by-function \
    --function-name dr-daily-report-telegram-api-dev \
    --query 'Versions[-5:].{Version:Version,Description:Description}' \
    --output table

# Rollback to previous version (e.g., v41)
aws lambda update-alias \
    --function-name dr-daily-report-telegram-api-dev \
    --name live \
    --function-version 41

# Also rollback worker if needed
aws lambda update-alias \
    --function-name dr-daily-report-report-worker-dev \
    --name live \
    --function-version 41

# Verify rollback
aws lambda get-alias \
    --function-name dr-daily-report-telegram-api-dev \
    --name live
```

**Rollback is instant** (~100ms) - just moves the alias pointer, no rebuild needed.

---

## Phase 3: Staging Environment

### 3.1 Staging Deployment

**Staging is auto-deployed** after dev succeeds (no manual step needed).

When you push to `telegram`, the CI/CD pipeline automatically:
1. Deploys to dev (smoke tests)
2. If dev passes → deploys to staging (smoke tests)
3. If staging passes → deploys to prod

**Manual deploy (if needed):**
```bash
./scripts/deploy-backend.sh staging
```

### 3.2 Test Staging Endpoints

```bash
STAGING_URL="https://ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com"

# Same tests as dev
curl -s "${STAGING_URL}/api/v1/health" | jq
curl -s "${STAGING_URL}/api/v1/search?q=NVDA" | jq '.results[:2]'
curl -s -X POST "${STAGING_URL}/api/v1/report/DBS19" | jq
```

### 3.3 Staging Checklist

| Test | Pass? |
|------|-------|
| CI/CD workflow shows staging complete | [ ] |
| Smoke tests pass (pre-promotion) | [ ] |
| Health endpoint returns ok | [ ] |
| Search returns results | [ ] |
| Async report completes | [ ] |

---

## Phase 4: Production Environment

### 4.1 Pre-Production Checklist

Production is auto-deployed after staging succeeds. Before pushing to `telegram`:

| Item | Status |
|------|--------|
| Code tested locally | [ ] |
| All unit tests pass | [ ] |
| Doppler prod secrets configured | [ ] |
| CloudWatch alarms set up | [ ] |
| Rollback plan understood (see 4.4) | [ ] |

### 4.2 Production Deployment

**Production is auto-deployed** after staging succeeds (no manual step needed).

The CI/CD pipeline:
1. Deploys to dev → smoke tests pass
2. Deploys to staging → smoke tests pass
3. Deploys to prod → smoke tests pass
4. All environments get the SAME Docker image

**Manual deploy (if needed):**
```bash
./scripts/deploy-backend.sh prod
```

**Production deployment includes:**
1. Same zero-downtime pattern as dev/staging
2. Pre-promotion smoke tests on `$LATEST`
3. Post-promotion verification via API Gateway
4. If tests fail, alias NOT updated (users see old version)

### 4.3 Verify Production

```bash
PROD_URL="https://prod-xxxxxxxx.execute-api.ap-southeast-1.amazonaws.com"  # TBD

# Health check
curl -s "${PROD_URL}/api/v1/health" | jq

# Verify version
aws lambda get-alias \
    --function-name dr-daily-report-telegram-api-prod \
    --name live \
    --query 'FunctionVersion' \
    --output text
```

### 4.4 Rollback (if needed)

**Rollback is instant** - just moves the alias pointer (~100ms):

```bash
# Use the rollback script (recommended)
./scripts/rollback.sh prod           # Interactive - shows versions, prompts for selection
./scripts/rollback.sh prod 41        # Rollback both Lambdas to version 41
./scripts/rollback.sh prod telegram 41  # Rollback only Telegram API

# Or manual AWS CLI commands:
# List recent versions
aws lambda list-versions-by-function \
    --function-name dr-daily-report-telegram-api-prod \
    --query 'Versions[-5:].{Version:Version}' \
    --output table

# Rollback to previous version (e.g., version 41)
aws lambda update-alias \
    --function-name dr-daily-report-telegram-api-prod \
    --name live \
    --function-version 41

# Also rollback worker
aws lambda update-alias \
    --function-name dr-daily-report-report-worker-prod \
    --name live \
    --function-version 41
```

**No rebuild needed** - previous versions are immutable snapshots.

---

## Common Failure Modes

### Local Development Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: slowapi` | Not using venv | `source venv/bin/activate` |
| `ResourceNotFoundException` | DynamoDB table missing | Run `just setup-local-dynamodb` |
| `Connection refused :8000` | DynamoDB Local not running | `docker start dynamodb-local` |
| `Connection refused :8001` | API server not running | `just dev-api` |
| Empty `TableNames` list | Credential mismatch | Use `doppler run --` for all commands |
| `InvalidAddress` SQS error | SQS not available locally | This endpoint only works in AWS |

### Deployment Errors (Zero-Downtime Pattern)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Pre-promotion smoke test fails | Code bug in `$LATEST` | Users NOT affected. Check `gh run view --log-failed`, fix code, push again |
| Post-promotion verification fails | API Gateway routing issue | Automatic rollback triggered. Check CloudWatch logs |
| `504 Gateway Timeout` | Lambda timeout (sync endpoint) | Use async POST endpoint instead |
| `401 Unauthorized` | Missing/invalid API keys | Check Doppler secrets for environment |
| `AccessDenied` on ECR push | IAM permissions | Check IAM policy for ECR access |
| Workflow stuck at "Deploy" | Previous deployment in progress | Wait or cancel: `gh run cancel <run-id>` |

### Rollback Scenarios

| Symptom | What Happened | What To Do |
|---------|---------------|------------|
| Smoke test failed | Code didn't pass health check on `$LATEST` | Alias NOT updated - users see old version. Fix code and redeploy |
| Post-promotion failed | Health check passed but API Gateway verification failed | Automatic rollback triggered. Check logs |
| Manual rollback needed | Issue found after deployment | Run rollback commands in section 4.4 |

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

# Code Deployment (CI/CD - auto-deploys to all envs)
git push origin telegram     # Triggers: dev → staging → prod

# Manual Deployment (backup)
./scripts/deploy-backend.sh dev      # Deploy to dev only
./scripts/deploy-backend.sh staging  # Deploy to staging only
./scripts/deploy-backend.sh prod     # Deploy to prod only

# Rollback
./scripts/rollback.sh dev 41          # Rollback dev to version 41
./scripts/rollback.sh staging 41      # Rollback staging to version 41
./scripts/rollback.sh prod 41         # Rollback prod to version 41

# Monitoring
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --follow
gh run watch                          # Watch CI/CD workflow

# Terraform (infrastructure changes only)
cd terraform
terraform init -backend-config=envs/dev/backend.hcl
terraform apply -var-file=envs/dev/terraform.tfvars
# Then apply to staging and prod too!
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
| Staging | `https://ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com/api/v1` | (shares dev CloudFront) | Deployed |
| Prod | TBD | TBD | Planned |

### CI/CD: Auto-Progressive Deployment

**Single branch deploys to ALL environments:**

| Trigger | Deploys To |
|---------|------------|
| `git push origin telegram` | dev → staging → prod (automatic chain) |

**Deployment Flow:**
```
git push to telegram
       ↓
   Build Image (once)
       ↓
   Deploy Dev → smoke test
       ↓ (if pass)
   Deploy Staging → smoke test
       ↓ (if pass)
   Deploy Prod → smoke test
       ↓
   Done (all envs updated)
```

**Key Points:**
- NO separate branches for staging/prod
- Same Docker image promoted through all environments
- Each environment smoke-tested before promotion
- If any environment fails, downstream environments are NOT deployed
