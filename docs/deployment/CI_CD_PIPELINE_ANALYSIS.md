# CI/CD Pipeline Analysis - Comprehensive Overview

## Executive Summary

**Pipeline Type**: Auto-progressive deployment (dev → staging → prod)
**Trigger Branch**: `telegram` (single branch triggers all environments)
**Deployment Strategy**: Zero-downtime with pre-promotion testing
**Infrastructure**: GitHub Actions + AWS Lambda + ECR + CloudFront + S3

---

## Pipeline Architecture

### 1. Workflow Files

| File | Purpose | Triggers |
|------|---------|----------|
| `.github/workflows/deploy.yml` | Main deployment pipeline | Push to `telegram` branch |
| `.github/workflows/pr-check.yml` | PR validation (no deployment) | PRs to `main`/`telegram` |
| `.github/workflows/terraform-test.yml` | Infrastructure TDD (OPA + Terratest) | PRs/push with `terraform/**` changes |

### 2. Pipeline Flow Diagram

```
git push origin telegram
       ↓
┌─────────────────────────┐
│  detect-changes         │  Path-based change detection
│  (backend/frontend)     │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  test                   │  Quality gates (syntax, unit tests, security)
│  (Quality Gates)        │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  build                  │  Docker build → ECR (immutable SHA tag)
│  (Build Image)          │  Only if backend changed
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  validate-aurora-schema │  Schema validation gate (CI/CD, no mocking)
│  (Schema Validation)    │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  deploy-dev             │  Zero-downtime: $LATEST → smoke test → live alias
│  (Deploy Dev Backend)   │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  vpc-integration-tests  │  CodeBuild for Aurora connectivity (if enabled)
│  (VPC Tests)            │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  deploy-dev-frontend    │  Deploy to TEST CloudFront (S3 + invalidation)
│  (Deploy Dev Frontend)  │  Only if frontend changed
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  e2e-test-dev           │  Playwright E2E tests against TEST CloudFront
│  (E2E Tests Dev)        │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  promote-dev-frontend   │  Invalidate APP CloudFront (users see new frontend)
│  (Promote Dev Frontend) │
└───────────┬─────────────┘
            ↓ (only if dev succeeds)
┌─────────────────────────┐
│  deploy-staging         │  Same zero-downtime pattern
│  (Deploy Staging)       │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  deploy-staging-frontend│  TEST CloudFront → E2E → APP CloudFront
│  e2e-test-staging       │
│  promote-staging-frontend│
└───────────┬─────────────┘
            ↓ (only if staging succeeds)
┌─────────────────────────┐
│  deploy-prod            │  Same zero-downtime pattern
│  (Deploy Prod)          │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  deploy-prod-frontend   │  TEST CloudFront → E2E → APP CloudFront
│  e2e-test-prod         │
│  promote-prod-frontend  │
└─────────────────────────┘
```

---

## Key Components Analysis

### 1. Change Detection (`detect-changes` job)

**Purpose**: Path-based change detection to conditionally deploy components

**Change Categories**:
- `shared`: Core agent/workflow/data layers (affects all Lambdas)
- `api`: Telegram API Lambda only
- `scheduler`: Scheduler Lambda only
- `worker`: Report worker Lambda only
- `backend`: Any backend change (triggers all Lambdas)
- `frontend`: Frontend React app changes

**Logic**:
- If `backend == true` → Deploy all Lambda functions
- If `frontend == true` → Deploy frontend (separate from backend)
- If `shared == true` → All Lambdas need update

**Files Monitored**:
```yaml
shared:
  - 'src/agent.py'
  - 'src/workflow/**'
  - 'src/data/**'
  - 'src/analysis/**'
  - 'src/report/**'
  - 'src/types.py'
  - 'src/config.py'
  - 'requirements*.txt'
  - 'Dockerfile*'
api:
  - 'src/api/**'
scheduler:
  - 'src/scheduler/**'
worker:
  - 'src/report_worker_handler.py'
backend:
  - 'src/**'
  - 'Dockerfile*'
  - 'requirements*.txt'
frontend:
  - 'frontend/twinbar/**'
```

---

### 2. Quality Gates (`test` job)

**Purpose**: Pre-deployment validation (runs on PR and push)

**Steps**:
1. **Syntax Check**: `python -m py_compile` for all Python files
2. **Unit Tests**: `pytest tests/shared tests/telegram` (excludes integration/e2e)
3. **Security Audit**: `pip-audit --strict` (non-blocking, warns only)

**Test Filtering**:
- ✅ Includes: Unit tests, shared tests, Telegram tests
- ❌ Excludes: Integration tests, smoke tests, E2E tests
- ❌ Ignores: `tests/integration/`, `tests/line_bot/`, `tests/telegram/test_e2e_frontend.py`

**Why This Matters**:
- Fast feedback loop (unit tests only)
- Integration/E2E tests run later (after deployment)
- Prevents broken code from reaching deployment stage

---

### 3. Build Stage (`build` job)

**Purpose**: Build immutable Docker image, promote through all environments

**Key Features**:
- **Immutable Tags**: `sha-${SHA_SHORT}-${TIMESTAMP}` (e.g., `sha-abc123-20251209-143022`)
- **Single Build**: One image for dev → staging → prod (artifact promotion)
- **ECR Repository**: `dr-daily-report-lambda-dev` (dev repo, image promoted)
- **Security Scanning**: Trivy scans for CRITICAL/HIGH vulnerabilities (non-blocking)

**Build Process**:
```bash
# Generate tag
SHA_SHORT=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="sha-${SHA_SHORT}-${TIMESTAMP}"

# Build
docker build -f Dockerfile.lambda.container -t ${ECR_REPO}:${IMAGE_TAG} .

# Push
docker push ${ECR_REPO}:${IMAGE_TAG}
```

**Conditional Execution**:
- Only runs if `backend == true` (skips if only frontend changed)
- Requires `test` job to succeed

---

### 4. Schema Validation (`validate-aurora-schema` job)

**Purpose**: Validate Aurora schema matches code expectations (CI/CD gate)

**Key Features**:
- **No Mocking**: Queries real Aurora via Lambda (following CLAUDE.md principles)
- **CI/CD Gate**: Blocks deployment if schema mismatch detected
- **Script**: `scripts/validate_aurora_schema.py`
- **Environment**: Uses `development` environment (Doppler secrets)

**Why This Exists**:
- Prevents deployment when code expects columns that don't exist
- Catches schema drift before it causes runtime errors
- Follows "Schema Testing at System Boundaries" principle

**Conditional Execution**:
- Only runs if `backend == true`
- Requires `build` job to succeed
- ⚠️ **Currently non-blocking** (can be skipped) - should be required

---

### 5. Backend Deployment Pattern (Dev/Staging/Prod)

**Zero-Downtime Strategy**: Test Before Promote

**Deployment Steps** (same for all environments):

#### Step 1: Update $LATEST (Staging Area)
```bash
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-dev \
  --image-uri ${IMAGE_URI}
aws lambda wait function-updated --function-name ${FUNCTION}
```
- Users still see old version (via "live" alias)
- New code uploaded to `$LATEST` pointer

#### Step 2: Smoke Test $LATEST
```bash
# Health endpoint test
aws lambda invoke \
  --function-name ${FUNCTION} \
  --payload '{"version":"2.0","routeKey":"GET /api/v1/health",...}' \
  /tmp/health.json

# Search endpoint test
aws lambda invoke \
  --function-name ${FUNCTION} \
  --payload '{"version":"2.0","routeKey":"GET /api/v1/search",...}' \
  /tmp/search.json
```
- Tests new code BEFORE users see it
- Fails fast if smoke tests fail (deployment blocked)

#### Step 3: Promote to Live Alias
```bash
# Publish immutable version
VERSION=$(aws lambda publish-version --function-name ${FUNCTION} --query 'Version' --output text)

# Update "live" alias (zero-downtime cutover)
aws lambda update-alias \
  --function-name ${FUNCTION} \
  --name live \
  --function-version ${VERSION}
```
- Only promoted after smoke tests pass
- Users see tested code immediately

**Functions Deployed**:
- `dr-daily-report-telegram-api-{env}` (Telegram API)
- `dr-daily-report-report-worker-{env}` (Report Worker)
- `dr-daily-report-ticker-scheduler-{env}` (Scheduler, optional)

**Environment Variables**:
- `ENV_NAME`: dev/staging/prod
- `TELEGRAM_FUNCTION`: Function name per environment
- `WORKER_FUNCTION`: Worker function name
- `SCHEDULER_FUNCTION`: Scheduler function name

---

### 6. Frontend Deployment Pattern (Dev/Staging/Prod)

**Zero-Risk Strategy**: Two CloudFront Distributions

**Deployment Steps**:

#### Step 1: Deploy to TEST CloudFront
```bash
# Build React app
cd frontend/twinbar
npm ci && npm run build

# Inject API URL
sed -i "s|</head>|<script>window.TELEGRAM_API_URL = '${API_URL}';</script></head>|g" dist/index.html

# Upload to S3
aws s3 sync dist/ s3://${BUCKET}/ --delete

# Invalidate TEST CloudFront ONLY
aws cloudfront create-invalidation \
  --distribution-id ${TEST_DIST_ID} \
  --paths "/*"
```
- Users still see old version (via APP CloudFront)
- E2E tests run against TEST CloudFront

#### Step 2: E2E Tests
```bash
E2E_BASE_URL="https://${TEST_DOMAIN}" pytest tests/e2e/ -m e2e -v
```
- Tests new frontend code BEFORE users see it
- Fails fast if E2E tests fail (APP CloudFront not updated)

#### Step 3: Promote to APP CloudFront
```bash
aws cloudfront create-invalidation \
  --distribution-id ${APP_DIST_ID} \
  --paths "/*"
```
- Only invalidated after E2E tests pass
- Users see tested frontend immediately

**Why Two CloudFronts**:
- Mirrors Lambda `$LATEST` vs "live" alias pattern
- TEST = staging area for E2E testing
- APP = user-facing (only updated after tests pass)
- Zero-risk: Users never see untested frontend code

**Infrastructure Validation**:
- Validates GitHub secrets match actual AWS infrastructure
- Queries CloudFront distributions from AWS
- Compares against GitHub secrets
- Fails fast if mismatch detected

---

### 7. VPC Integration Tests (`vpc-integration-tests` job)

**Purpose**: Test Aurora connectivity inside VPC (CodeBuild)

**Key Features**:
- **CodeBuild Project**: `dr-daily-report-vpc-tests-dev`
- **VPC Access**: CodeBuild runs inside VPC (can reach Aurora)
- **Tests**: Aurora connectivity, cache-first behavior
- **Conditional**: Only runs if `vars.AURORA_ENABLED == 'true'`

**Process**:
1. Start CodeBuild project
2. Poll for completion (30s intervals, 20min timeout)
3. Fail if tests fail (blocks deployment)

**Why CodeBuild**:
- GitHub Actions runners don't have VPC access
- CodeBuild can run inside VPC
- Tests real Aurora connectivity (not mocked)

---

### 8. Infrastructure TDD (`terraform-test.yml` workflow)

**Purpose**: Infrastructure validation (OPA policies + Terratest)

**Two-Stage Process**:

#### Stage 1: OPA Policy Validation (Pre-Apply)
- **Runs On**: Every PR and push with `terraform/**` changes
- **Process**:
  1. `terraform plan` → JSON output
  2. `conftest test` → Validate against Rego policies
  3. Blocks PR if policy violations detected
- **Policies**: Security (IAM, S3, encryption), tagging, best practices

#### Stage 2: Terratest Integration Tests (Post-Apply)
- **Runs On**: Push to `telegram`/`telegram-staging` branches only
- **Process**:
  1. Terraform apply (if needed)
  2. Go tests verify infrastructure works
  3. Tests Lambda invocations, DynamoDB, API Gateway
- **Language**: Go (Terratest framework)

**Why This Matters**:
- Shift-left security (catch issues before deployment)
- Policy-as-code (version-controlled security rules)
- Integration confidence (verify infra actually works)

---

## Deployment Environments

### Environment Progression

| Environment | Trigger | Auto-Progressive? | Manual Gates? |
|-------------|---------|-------------------|---------------|
| **Dev** | Push to `telegram` | ✅ Yes | ❌ No |
| **Staging** | After dev succeeds | ✅ Yes | ❌ No |
| **Prod** | After staging succeeds | ✅ Yes | ❌ No |

**Key Point**: Single push to `telegram` branch automatically deploys through all environments (no manual approval gates).

---

## Path Filters - What Triggers Deployment

| Path Pattern | Triggers Deploy? | Why |
|--------------|------------------|-----|
| `src/**` | ✅ Yes | Backend code changes |
| `frontend/twinbar/**` | ✅ Yes | Frontend code changes |
| `Dockerfile*` | ✅ Yes | Container config changes |
| `requirements*.txt` | ✅ Yes | Dependencies changed |
| `terraform/**` | ✅ Yes | Infrastructure changes |
| `.github/workflows/**` | ✅ Yes | CI/CD config changes |
| `tests/**` | ✅ Yes | Test changes (may affect behavior) |
| `docs/**` | ❌ No | Documentation only |
| `.claude/**` | ❌ No | Dev instructions only |

**Note**: Path filters are AND conditions - all matching paths trigger deployment.

---

## Zero-Downtime Deployment Patterns

### Backend (Lambda)

**Pattern**: `$LATEST` (staging) → Smoke Test → `live` alias (production)

```
$LATEST (mutable) ← New code lands here first
 │
 │ smoke test passes?
 ▼
Version N (immutable) ← Snapshot created
 │
 ▼
"live" alias ← API Gateway invokes this (users see this)
```

**Benefits**:
- Users never see untested code
- Instant rollback (move alias pointer back)
- Zero downtime (no service interruption)

### Frontend (CloudFront)

**Pattern**: TEST CloudFront → E2E Tests → APP CloudFront

```
Same S3 Bucket
 │
 ├── TEST CloudFront → Invalidated first, E2E tests run here
 │
 └── APP CloudFront → Invalidated ONLY after E2E tests pass
```

**Benefits**:
- Users never see untested frontend
- E2E tests run against real CloudFront
- Zero-risk deployment

---

## Artifact Promotion Strategy

**Principle**: Build once, promote same immutable image through all environments

```
Docker Image: sha-abc123-20251209-143022 (IMMUTABLE)
     │
     ├──▶  DEV:     Uses sha-abc123-20251209-143022
     │              (auto on push to telegram)
     │
     ├──▶  STAGING: Uses sha-abc123-20251209-143022
     │              (same image, after dev succeeds)
     │
     └──▶  PROD:    Uses sha-abc123-20251209-143022
                    (same image, after staging succeeds)
```

**Why This Matters**:
- What you test in staging is EXACTLY what deploys to prod
- No "works in staging, fails in prod" surprises
- Fast rollback (just point alias back to previous version)

---

## Secrets Management

### GitHub Secrets (Per Environment)

**Required Secrets**:
- `AWS_ACCESS_KEY_ID` - Deployment user credentials
- `AWS_SECRET_ACCESS_KEY` - Deployment user secret
- `CLOUDFRONT_DISTRIBUTION_ID` - APP CloudFront ID
- `CLOUDFRONT_TEST_DISTRIBUTION_ID` - TEST CloudFront ID
- `CLOUDFRONT_TEST_DOMAIN` - TEST CloudFront domain
- `WEBAPP_BUCKET_NAME` - S3 bucket for frontend
- `TELEGRAM_API_URL` - API URL for frontend (injected into HTML)

**Environment-Specific**:
- Secrets are scoped to GitHub environments (`development`, `staging`, `production`)
- Each environment has separate secrets
- Secrets validated against actual AWS infrastructure

### Doppler Secrets (Runtime)

**Purpose**: Application runtime secrets (not deployment secrets)

**Examples**:
- `AURORA_HOST`, `AURORA_USER`, `AURORA_PASSWORD`
- `OPENROUTER_API_KEY`
- `PDF_BUCKET_NAME`

**Injection**: Doppler → Terraform → Lambda environment variables

---

## Monitoring & Observability

### GitHub Actions Monitoring

```bash
# Watch deployment in real-time
gh run watch --exit-status

# Check specific run
gh run view 12345 --json conclusion
# → {"conclusion": "success"}

# Get logs if failed
gh run view 12345 --log-failed
```

**Critical**: Check BOTH `status` and `conclusion`:
- `status: completed` = Workflow finished running
- `conclusion: success` = Workflow achieved its goal

### AWS CloudWatch Logs

**Lambda Log Groups**:
- `/aws/lambda/dr-daily-report-telegram-api-{env}`
- `/aws/lambda/dr-daily-report-report-worker-{env}`
- `/aws/lambda/dr-daily-report-ticker-scheduler-{env}`

**Monitoring**:
- X-Ray tracing enabled
- CloudWatch alarms configured
- Log retention: 30 days

---

## Rollback Procedures

### Backend Rollback

```bash
# 1. Find previous working version
aws lambda list-versions-by-function \
  --function-name dr-daily-report-telegram-api-prod \
  --max-items 5

# 2. Update alias to previous version
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live \
  --function-version <previous-version>

# 3. Verify rollback
aws lambda get-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live
```

**Benefits**:
- Instant rollback (no rebuild needed)
- Previous versions are immutable snapshots
- Always available for rollback

### Frontend Rollback

**Option 1**: Re-deploy previous git commit
```bash
git checkout <previous-commit>
npm run build
aws s3 sync dist/ s3://${BUCKET}/
aws cloudfront create-invalidation --distribution-id ${DIST_ID} --paths "/*"
```

**Option 2**: S3 versioning (if enabled)
```bash
aws s3 cp s3://${BUCKET}/ s3://${BUCKET}/ \
  --recursive \
  --metadata-directive COPY \
  --source-version-id <previous-version-id>
```

---

## Current Pipeline Status

### ✅ What's Working

1. **Auto-Progressive Deployment**: Single push deploys through all environments
2. **Zero-Downtime Backend**: Lambda versioning with pre-promotion testing
3. **Zero-Risk Frontend**: Two CloudFront distributions with E2E testing
4. **Quality Gates**: Syntax check, unit tests, security audit
5. **Infrastructure TDD**: OPA policies + Terratest integration tests
6. **Change Detection**: Path-based conditional deployment
7. **Artifact Promotion**: Same image through all environments

### ⚠️ Known Limitations

1. **No Manual Approval Gates**: Auto-progressive means no human approval between environments
2. **No Automatic Rollback**: Rollback is manual (future improvement planned)
3. **Frontend E2E Tests**: Can be skipped if TEST CloudFront not configured (should fail fast)
4. **VPC Tests**: CodeBuild dependency (adds complexity)
5. **Schema Validation**: Can be skipped (non-blocking) - should be required

### 🔍 Missing Components

1. **Fund Data Sync Pipeline**: Not integrated into CI/CD
   - Currently deployed manually
   - No automated deployment workflow
   - No CI/CD integration for `fund_data_sync` Lambda

2. **Database Migrations**: Not automated
   - Migrations run manually
   - No migration validation in CI/CD
   - No rollback strategy for migrations

3. **Performance Testing**: Not included
   - No load testing before production
   - No performance regression detection

4. **Canary Deployments**: Not implemented
   - All-or-nothing deployment
   - No gradual rollout strategy

---

## Recommendations

### High Priority

1. **Integrate Fund Data Sync into CI/CD**
   - Add `fund_data_sync` Lambda to deployment pipeline
   - Include in change detection logic
   - Add smoke tests for fund data sync

2. **Require Schema Validation**
   - Make `validate-aurora-schema` job blocking (not skippable)
   - Fail deployment if schema mismatch detected

3. **Add Automatic Rollback**
   - Rollback on smoke test failure
   - Rollback on E2E test failure
   - Alert on rollback events

### Medium Priority

4. **Add Manual Approval Gates**
   - Optional manual approval before prod deployment
   - Keep auto-progressive for dev/staging

5. **Automate Database Migrations**
   - Run migrations as part of deployment pipeline
   - Validate migrations before deployment
   - Add migration rollback strategy

6. **Improve Frontend E2E Testing**
   - Fail fast if TEST CloudFront not configured
   - Add more E2E test scenarios
   - Parallelize E2E tests for speed

### Low Priority

7. **Add Performance Testing**
   - Load testing before production
   - Performance regression detection
   - Baseline performance metrics

8. **Implement Canary Deployments**
   - Gradual rollout for high-risk changes
   - Automatic rollback on error rate increase

---

## Pipeline Execution Time Estimates

| Stage | Estimated Time | Notes |
|-------|----------------|-------|
| Change Detection | ~10s | Fast path filtering |
| Quality Gates | ~2-5 min | Unit tests, syntax check |
| Build Image | ~5-10 min | Docker build + push to ECR |
| Schema Validation | ~30s | Lambda invocation |
| Deploy Dev Backend | ~2-3 min | Update + smoke test + promote |
| VPC Integration Tests | ~5-10 min | CodeBuild execution |
| Deploy Dev Frontend | ~2-3 min | Build + S3 sync + CloudFront |
| E2E Tests Dev | ~3-5 min | Playwright browser tests |
| Promote Dev Frontend | ~10s | CloudFront invalidation |
| Deploy Staging | ~2-3 min | Same as dev |
| Deploy Staging Frontend | ~2-3 min | Same as dev |
| E2E Tests Staging | ~3-5 min | Same as dev |
| Deploy Prod | ~2-3 min | Same as dev |
| Deploy Prod Frontend | ~2-3 min | Same as dev |
| E2E Tests Prod | ~3-5 min | Same as dev |

**Total Pipeline Time**: ~30-50 minutes (all environments)

**Parallelization Opportunities**:
- Frontend deployment can run parallel to backend deployment
- E2E tests can run parallel to other stages
- Staging deployment can start while dev E2E tests run

---

## Conclusion

The CI/CD pipeline implements a robust auto-progressive deployment strategy with zero-downtime patterns for both backend (Lambda) and frontend (CloudFront). Key strengths include artifact promotion, pre-promotion testing, and infrastructure TDD. The main gap is the missing integration of the Fund Data Sync pipeline, which currently requires manual deployment.
