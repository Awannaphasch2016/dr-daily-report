# CI/CD Architecture

Branch-based deployment with independent environment promotion and multi-app support through GitHub Actions.

---

## Multi-App Architecture

This project supports **two separate applications** sharing a common backend:

- **Telegram Mini App**: Web-based dashboard with REST API (`src/api/**`, `frontend/twinbar/**`)
- **LINE Bot**: Chat-based Thai financial reports (`src/integrations/line_bot.py`)

Both apps share:
- Same Docker image (built from same Dockerfile)
- Same backend code (`src/agent.py`, `src/workflow/**`, `src/data/**`)
- Same Aurora database

**Path filters** determine which app deploys based on code changes.

---

## Pipeline Overview

**Branch-based triggers for independent environment deployment:**

```yaml
# Dev deployment - deploy-telegram-dev.yml
on:
  push:
    branches: [dev]
    paths: ['src/api/**', 'frontend/**', 'src/**']  # Telegram + shared

# Dev deployment - deploy-line-dev.yml
on:
  push:
    branches: [dev]
    paths: ['src/integrations/line_bot.py', 'src/**']  # LINE + shared

# Staging/Production - similar pattern for both apps
```

---

## Deployment Workflow Files

### Telegram Mini App Workflows

| Workflow | Trigger | Deploys To | Duration |
|----------|---------|------------|----------|
| `deploy-telegram-dev.yml` | Push to `dev` (Telegram/shared paths) | Dev environment | ~8 min |
| `deploy-telegram-staging.yml` | Push to `main` (Telegram/shared paths) | Staging environment | ~10 min |
| `deploy-telegram-prod.yml` | Tag `v-telegram-*.*.*` | Production environment | ~12 min |

### LINE Bot Workflows

| Workflow | Trigger | Deploys To | Duration |
|----------|---------|------------|----------|
| `deploy-line-dev.yml` | Push to `dev` (LINE/shared paths) | Dev environment | ~6 min |
| `deploy-line-staging.yml` | Push to `main` (LINE/shared paths) | Staging environment | ~8 min |
| `deploy-line-prod.yml` | Tag `v-line-*.*.*` | Production environment | ~10 min |

### Scheduler Workflows

| Workflow | Trigger | Deploys To | Duration |
|----------|---------|------------|----------|
| `deploy-scheduler-dev.yml` | Push to `dev` (scheduler/data paths) | Dev environment | ~5 min |
| `deploy-scheduler-staging.yml` | Push to `main` (scheduler/data paths) | Staging environment | ~6 min |
| `deploy-scheduler-prod.yml` | Tag `v-scheduler-*.*.*` | Production environment | ~7 min |

**What the Scheduler Does:**
- **Daily Schedule:** 5:00 AM Bangkok time (22:00 UTC previous day) via EventBridge
- **Task:** Fetches 47 tickers from Yahoo Finance
- **Storage:** Raw data to Aurora `ticker_data` table
- **Precompute:** Currently manual (automatic triggering disabled)

**Deployment Behavior:**

| Code Change | Telegram | LINE | Scheduler | Why |
|-------------|----------|------|-----------|-----|
| `src/api/**` | ✅ Deploy | ❌ Skip | ❌ Skip | Telegram REST API only |
| `src/integrations/line_bot.py` | ❌ Skip | ✅ Deploy | ❌ Skip | LINE bot code only |
| `src/scheduler/**` | ❌ Skip | ❌ Skip | ✅ Deploy | Scheduler code only |
| `src/agent.py` | ✅ Deploy | ✅ Deploy | ❌ Skip | Used by apps, not scheduler |
| `src/data/**` | ✅ Deploy | ✅ Deploy | ✅ Deploy | Shared by all (Aurora access) |
| `frontend/twinbar/**` | ✅ Deploy | ❌ Skip | ❌ Skip | Telegram frontend only |
| `docs/**` | ❌ Skip | ❌ Skip | ❌ Skip | Documentation only |

**Key Benefits:**
- ✅ Independent deployments (no cascading failures)
- ✅ Fast dev iteration (deploy only what changed)
- ✅ App-specific versioning (`v-telegram-1.2.3`, `v-line-1.2.3`)
- ✅ Shared code automatically deploys both apps
- ✅ Same artifact promotion pattern for both apps
- ✅ All safety gates preserved (schema validation, smoke tests, E2E)

---

## Artifact Promotion Pattern

**Build once, promote everywhere:**

```
dev branch push
    ↓
┌─────────────────────┐
│ deploy-dev.yml:     │
│ - Build Docker image│  → ECR (sha-abc123-20250122-143000)
│ - Push to ECR       │
│ - Store metadata    │  → GitHub Artifacts (dev-artifact-metadata)
└─────────┬───────────┘
          ↓
main branch push
    ↓
┌─────────────────────┐
│ deploy-staging.yml: │
│ - Download artifact │  ← GitHub Artifacts (dev-artifact-metadata)
│ - Deploy same image │  → Staging (zero rebuild)
│ - Store metadata    │  → GitHub Artifacts (staging-artifact-metadata)
└─────────┬───────────┘
          ↓
v1.2.3 tag created
    ↓
┌─────────────────────┐
│ deploy-prod.yml:    │
│ - Validate tag      │  (must be on main branch)
│ - Download artifact │  ← GitHub Artifacts (staging-artifact-metadata)
│ - Deploy same image │  → Production (manual approval required)
│ - Create release    │  → GitHub Release with changelog
└─────────────────────┘
```

**Same immutable image** tested in dev gets promoted to production.

---

## Pipeline Flow

### Dev Environment (`deploy-dev.yml`)

```
git push origin dev
       ↓
┌──────────────────┐
│ detect-changes   │  Path filters: backend/frontend
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Quality Gates    │  Syntax, unit tests, security audit
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Build Image      │  Docker build → ECR
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Aurora Schema    │  BLOCKING GATE - schema validation
│ Validation       │  (compares Aurora vs code expectations)
└────────┬─────────┘
         ↓ (only if schema valid)
┌──────────────────┐
│ Deploy Dev       │  update-function-code → smoke test → promote
└────────┬─────────┘
         ↓
┌──────────────────┐
│ VPC Tests        │  CodeBuild - Aurora connectivity tests
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Frontend (TEST)  │  S3 + TEST CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ E2E Tests        │  Playwright against TEST CloudFront
└────────┬─────────┘
         ↓ (only if E2E passes)
┌──────────────────┐
│ Promote Frontend │  Invalidate APP CloudFront (users see new version)
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Store Artifact   │  Upload metadata for staging
└──────────────────┘
```

**Duration:** ~8 minutes

---

### Staging Environment (`deploy-staging.yml`)

```
git push origin main
       ↓
┌──────────────────┐
│ detect-changes   │  Path filters: backend/frontend
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Quality Gates    │  Syntax, unit tests, security audit
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Get Dev Artifact │  Download artifact-uri from dev build
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Deploy Staging   │  Use dev's Docker image (no rebuild)
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Frontend (TEST)  │  S3 + TEST CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ E2E Tests        │  Playwright against TEST CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Promote Frontend │  Invalidate APP CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Store Artifact   │  Upload metadata for production
└──────────────────┘
```

**Duration:** ~10 minutes

---

### Production Environment (`deploy-prod.yml`)

```
git tag -a v1.2.3 -m "Release v1.2.3" && git push origin v1.2.3
       ↓
┌──────────────────┐
│ Validate Tag     │  Ensure tag is on main branch (security gate)
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Get Staging      │  Download artifact-uri from staging build
│ Artifact         │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Deploy Prod      │  Use staging's Docker image (no rebuild)
│                  │  ⚠️ Requires manual approval via GitHub environment
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Frontend (TEST)  │  S3 + TEST CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ E2E Tests        │  Playwright against TEST CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Promote Frontend │  Invalidate APP CloudFront
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Create Release   │  GitHub Release with changelog + rollback instructions
└──────────────────┘
```

**Duration:** ~12 minutes (excluding manual approval wait time)

---

## Quality Gates

All workflows include these safety gates:

### 1. Syntax Check
```yaml
- name: Syntax check
  run: |
    python -m py_compile src/**/*.py src/api/*.py dr_cli/**/*.py
```

### 2. Unit Tests
```yaml
- name: Unit tests
  run: |
    pytest tests/shared tests/telegram -v --tb=short \
      -k "not integration and not smoke and not e2e"
```

### 3. Security Audit
```yaml
- name: Security audit
  run: pip-audit --strict --desc
  continue-on-error: true  # Non-blocking
```

### 4. Aurora Schema Validation (Dev Only)
```yaml
- name: Validate Aurora schema
  run: |
    pytest tests/infrastructure/test_aurora_schema_comprehensive.py \
      -v --tb=short -m integration
```

**BLOCKING GATE:** If schema validation fails, deployment is blocked. This ensures code expectations match database reality.

### 5. Smoke Tests (All Environments)
```yaml
- name: Smoke test $LATEST
  run: |
    # Test health endpoint
    aws lambda invoke --function-name $FUNCTION --payload $PAYLOAD /tmp/health.json

    # Test search endpoint
    aws lambda invoke --function-name $FUNCTION --payload $PAYLOAD /tmp/search.json
```

### 6. E2E Tests (All Environments)
```yaml
- name: Run E2E Tests
  env:
    E2E_BASE_URL: ${{ needs.deploy-frontend.outputs.test_url }}
  run: |
    playwright install chromium
    pytest tests/e2e/ -m e2e -v --tb=short
```

---

## Path Filters - What Triggers Deployment

| File Change | Backend Deploy? | Frontend Deploy? | Why |
|-------------|-----------------|------------------|-----|
| `src/**/*.py` | ✅ Yes | ❌ No | Backend code changes |
| `frontend/twinbar/**` | ❌ No | ✅ Yes | Frontend code changes |
| `Dockerfile*` | ✅ Yes | ❌ No | Container config changes |
| `requirements*.txt` | ✅ Yes | ❌ No | Dependencies changed |
| `terraform/**` | ✅ Yes | ❌ No | Infrastructure changes (manual apply needed) |
| `tests/*.py` | ❌ No | ❌ No | Tests don't affect production |
| `docs/*.md` | ❌ No | ❌ No | Documentation is git-only |

**Smart Deployment:**
- Backend changes → Rebuilds Docker image, deploys Lambdas
- Frontend changes → Skips build, deploys frontend only
- Both changed → Deploys both

---

## Zero-Downtime Pattern

All environments use the same zero-downtime deployment pattern:

```
1. update-function-code → $LATEST (users still see old version)
2. aws lambda invoke → smoke test $LATEST directly
3. publish-version → create immutable snapshot
4. update-alias → point "live" alias to new version

Users NEVER see broken code - tested before promotion.
```

**Rollback procedure:**
```bash
# If issues detected post-deployment
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live \
  --function-version <previous-version>
```

---

## Typical Workflows

### Fast Dev Iteration (Telegram-only changes)
```bash
# Make Telegram-specific changes
git checkout dev
# Edit src/api/endpoints.py
git add .
git commit -m "feat(telegram): add new ranking endpoint"
git push origin dev

# → Only deploy-telegram-dev.yml runs (~8 min)
# → LINE bot not affected
```

### Fast Dev Iteration (LINE-only changes)
```bash
# Make LINE-specific changes
git checkout dev
# Edit src/integrations/line_bot.py
git add .
git commit -m "feat(line): improve message formatting"
git push origin dev

# → Only deploy-line-dev.yml runs (~6 min)
# → Telegram not affected
```

### Shared Backend Changes (Both apps deploy)
```bash
# Make shared backend changes
git checkout dev
# Edit src/agent.py
git add .
git commit -m "feat(backend): improve LLM prompt"
git push origin dev

# → Both deploy-telegram-dev.yml AND deploy-line-dev.yml run (~8 min each, in parallel)
# → Both apps get the update
```

### Promote to Staging
```bash
# Create PR from dev → main
gh pr create --base main --head dev --title "Release: Feature X"
# After approval and merge
# → deploy-telegram-staging.yml runs if Telegram/shared code changed
# → deploy-line-staging.yml runs if LINE/shared code changed
```

### Production Release (Telegram)
```bash
# After staging testing passes
git checkout main
git pull
git tag -a v-telegram-1.2.3 -m "Release: Telegram Feature X"
git push origin v-telegram-1.2.3

# → deploy-telegram-prod.yml runs
# → Requires manual approval
# → GitHub Release created automatically
```

### Production Release (LINE Bot)
```bash
# After staging testing passes
git checkout main
git pull
git tag -a v-line-1.2.3 -m "Release: LINE Bot Feature Y"
git push origin v-line-1.2.3

# → deploy-line-prod.yml runs
# → Requires manual approval
# → GitHub Release created automatically
```

### Production Release (Both Apps)
```bash
# When both apps need production release
git checkout main
git pull

# Tag both apps
git tag -a v-telegram-1.3.0 -m "Release: Backend improvements"
git tag -a v-line-1.3.0 -m "Release: Backend improvements"

git push origin v-telegram-1.3.0
git push origin v-line-1.3.0

# → Both deploy-telegram-prod.yml AND deploy-line-prod.yml run
# → Each requires manual approval
# → Two GitHub Releases created
```

---

## Monitoring Deployment

### Watch workflow runs
```bash
# List recent runs
gh run list --limit 10

# Watch specific run
gh run watch <run-id> --exit-status

# View logs
gh run view <run-id> --log
```

### Check deployed versions
```bash
# Dev
aws lambda get-alias \
  --function-name dr-daily-report-telegram-api-dev \
  --name live

# Staging
aws lambda get-alias \
  --function-name dr-daily-report-telegram-api-staging \
  --name live

# Production
aws lambda get-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live
```

---

## Environment Variables

Managed via Doppler - injected during Terraform deployment.

**Required secrets per environment:**
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- `CLOUDFRONT_DISTRIBUTION_ID` (APP distribution)
- `CLOUDFRONT_TEST_DISTRIBUTION_ID` (TEST distribution for E2E)
- `TELEGRAM_API_URL`
- `WEBAPP_BUCKET_NAME`

See [Multi-Environment Guide](MULTI_ENV.md) for complete configuration.

---

## Troubleshooting

### "No dev artifact found" in staging
**Cause:** Staging triggered before dev built this code.
**Fix:** Push to dev first, wait for dev build to complete, then merge to main.

### "Tag not on main branch" in production
**Cause:** Tag created from dev or other branch.
**Fix:**
```bash
git tag -d v1.2.3
git push origin :refs/tags/v1.2.3
git checkout main
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

### E2E tests fail on TEST CloudFront
**Cause:** Frontend not fully propagated through CloudFront edge locations.
**Wait:** 30-60 seconds and retry manually, or workflow will retry automatically.

### Schema validation blocks deployment
**Cause:** Code expects columns that don't exist in Aurora.
**Fix:** Create migration first, then deploy code. See [Database Migrations](../DATABASE_MIGRATIONS.md).

---

## Related Documentation

- [Lambda Versioning Strategy](LAMBDA_VERSIONING.md) - Zero-downtime deployment pattern
- [Multi-Environment Guide](MULTI_ENV.md) - Environment configuration
- [Deployment Workflow](WORKFLOW.md) - Manual deployment commands
- [ADR-009: Artifact Promotion](../adr/009-artifact-promotion-over-per-env-builds.md) - Why we build once
