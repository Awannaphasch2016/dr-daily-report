# Validation Report: Telegram App on Staging Branch

**Claim**: "Telegram app on staging branch should work now"

**Type**: `config` + `behavior` (infrastructure configuration + functional behavior)

**Date**: 2026-01-09

**Status**: ⚠️ **PARTIALLY TRUE - Infrastructure Ready, Credentials Missing**

---

## Executive Summary

**Infrastructure**: ✅ Fully deployed and configured
**Code**: ⚠️ Old image (Nov 30, 2024), not latest from staging branch
**Configuration**: ❌ **Missing Telegram bot credentials**
**Branch Strategy**: ⚠️ **Misunderstanding detected** - No "staging branch" exists

**Conclusion**: Staging environment infrastructure is ready, but **Telegram app will NOT work** due to:
1. Missing Telegram credentials (TELEGRAM_BOT_TOKEN, TELEGRAM_APP_ID, TELEGRAM_APP_HASH are empty strings)
2. Deployed Lambda image is 40+ days old (Nov 30, 2024), not latest code
3. No "staging branch" exists - project uses `dev` branch → dev environment, `main` branch → staging environment

---

## Evidence Analysis

### ✅ Evidence FOR "Infrastructure Ready"

#### 1. AWS Infrastructure Deployed Successfully
**Source**: Terraform apply output (2026-01-09)

**Staging Resources**:
- ✅ **API Gateway**: `ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com`
  - CORS configured for staging webapp: `https://d3uuexs20crp9s.cloudfront.net`
  - All HTTP methods enabled (GET, POST, PUT, DELETE, OPTIONS)
  - Telegram headers allowed: `x-telegram-init-data`, `x-telegram-user-id`

- ✅ **Lambda Functions**:
  - `dr-daily-report-telegram-api-staging`: Active, LastUpdateStatus: Successful
  - `dr-daily-report-report-worker-staging`: Active
  - `dr-daily-report-pdf-worker-staging`: Active
  - 9 additional Lambda functions deployed

- ✅ **Aurora MySQL Cluster**:
  - Identifier: `dr-daily-report-aurora-staging`
  - Endpoint: `dr-daily-report-aurora-staging.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com`
  - Status: available
  - Engine: aurora-mysql 8.0

- ✅ **DynamoDB Tables**:
  - `dr-daily-report-telegram-jobs-staging`: ACTIVE
  - `dr-daily-report-telegram-watchlist-staging`: ACTIVE

- ✅ **S3 VPC Endpoint**: `vpce-0767ec23ca7652a7c` (available) - for PDF upload reliability

**Confidence**: High (verified via AWS CLI queries)

---

#### 2. Required Infrastructure Variables Present
**Source**: Lambda environment variables

Lambda `dr-daily-report-telegram-api-staging` has:
- ✅ `AURORA_HOST`: `dr-daily-report-aurora-staging.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com`
- ✅ `TELEGRAM_WEBAPP_URL`: `https://d3uuexs20crp9s.cloudfront.net`
- ✅ `OPENROUTER_API_KEY`: Present (redacted)

**Confidence**: High (direct Lambda query)

---

### ❌ Evidence AGAINST "App Will Work"

#### 1. **CRITICAL**: Missing Telegram Bot Credentials
**Source**: Lambda environment variables (`aws lambda get-function-configuration`)

```json
{
  "TELEGRAM_BOT_TOKEN": "",      // ❌ EMPTY STRING
  "TELEGRAM_APP_ID": "",          // ❌ EMPTY STRING
  "TELEGRAM_APP_HASH": ""         // ❌ EMPTY STRING
}
```

**Impact**:
- Telegram bot **cannot authenticate** with Telegram API
- All Telegram bot operations will fail at startup
- Violates **Principle #1 (Defensive Programming)**: "Validate configuration at startup"
- Violates **Principle #15 (Infrastructure-Application Contract)**: Missing env vars cause silent failures

**Root Cause**:
- Doppler staging config missing Telegram credentials
- Only contains `TELEGRAM_API_URL` (the API Gateway endpoint)
- Terraform variables have `default = ""` which deployed empty strings

**Verification**:
```bash
$ doppler secrets --config stg | grep -i telegram
│ TELEGRAM_API_URL        │ https://ta0g00v0c7.exec │
# No TELEGRAM_BOT_TOKEN, TELEGRAM_APP_ID, TELEGRAM_APP_HASH
```

**Confidence**: High (verified via both Lambda config and Doppler secrets list)

**Historical Context**: This is the **exact same failure pattern** as the LINE bot incident (2026-01-09) documented in `.claude/bug-hunts/2026-01-09-linebot-no-response.md` where missing credentials caused production outage.

---

#### 2. Deployed Lambda Image is 40+ Days Old
**Source**: ECR image metadata

```json
{
    "Digest": "sha256:c54645f81a860bc8917d3494da863a220ee5bb9647269bad1ad1b44d04803f78",
    "Tags": ["latest"],
    "PushedAt": "2025-11-30T14:05:30+07:00"  // ❌ 40+ days old
}
```

**Current Date**: 2026-01-09
**Image Age**: 40+ days old
**Latest Commit**: `a80906d` (2026-01-09) - feat(validation): Add pre-deployment secret validation

**Impact**:
- Staging Lambda running code from November 30, 2024
- Missing 40+ days of commits including:
  - Pre-deployment validation (commit a80906d)
  - SQS removal cleanup (commit 5056563)
  - S3 VPC Endpoint fix (commit 221ca50)
  - PDF workflow fixes (commits 6d32e1f, ebce60f)
  - Timezone handling fixes (commits 1a3fb44, ebce60f)

**Confidence**: High (ECR metadata + git log comparison)

---

#### 3. Branch Strategy Misunderstanding
**Source**: `.claude/CLAUDE.md` line 17

**Documented Branch Strategy**:
```markdown
**Branch Strategy:** `dev` → dev environment (~8 min) | `main` → staging environment (~10 min) | Tags `v*.*.*` → production (~12 min)
```

**Git Branch Check**:
```bash
$ git branch --show-current
dev

$ git branch -a | grep staging
# No output - "staging" branch doesn't exist
```

**Clarification**:
- ✅ `dev` branch → deploys to **dev environment**
- ✅ `main` branch → deploys to **staging environment**
- ✅ Tags `v*.*.*` → deploy to **production environment**
- ❌ **No "staging branch" exists**

**Impact**: User asked about "staging branch" but:
1. We just deployed to staging **environment** (not from staging branch)
2. Code is from November 30 image (not current `dev` or `main` branch)
3. To update staging with latest code, need to:
   - Merge `dev` → `main` branch
   - CI/CD automatically deploys `main` to staging environment

**Confidence**: High (documented in CLAUDE.md + git verification)

---

## Missing Evidence

### 1. Database Schema State
**What we need**: Verify staging Aurora has required tables (ticker_master, daily_prices, etc.)
**Why important**: Lambda will fail if schema not migrated
**How to verify**:
```bash
# Connect to staging Aurora and check schema
aws secretsmanager get-secret-value --secret-id dr-daily-report/aurora/staging
# Use credentials to run: SHOW TABLES;
```

### 2. Actual Functional Test
**What we need**: Smoke test - call Telegram API endpoint and verify response
**Why important**: Infrastructure "Active" ≠ App works (Progressive Evidence Strengthening)
**How to verify**:
```bash
curl -X POST https://ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com/api/v1/report \
  -H "Content-Type: application/json" \
  -H "x-telegram-init-data: <test_data>"
```

### 3. CloudWatch Logs
**What we need**: Recent invocation logs from staging Lambda
**Why important**: Logs reveal startup validation failures
**How to verify**:
```bash
aws logs tail /aws/lambda/dr-daily-report-telegram-api-staging --follow
```

---

## Analysis

### Why App Will NOT Work (Despite Infrastructure Being Ready)

**Primary Blocker**: Missing Telegram credentials violates multiple principles:

1. **Principle #1 (Defensive Programming)**:
   - Code should "validate configuration at startup, not on first use"
   - If app has startup validation, Lambda will fail immediately with: `❌ Missing environment variables: ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_APP_ID', 'TELEGRAM_APP_HASH']`

2. **Principle #15 (Infrastructure-Application Contract)**:
   - Infrastructure deployed ✅
   - Application code expects credentials ✅
   - **Contract broken**: Terraform deployed empty strings instead of actual credentials

3. **Repeat of LINE Bot Incident**:
   - Same root cause: Missing Doppler credentials → Terraform empty strings → Lambda fails
   - Same investigation pattern: Infrastructure looks good, but app doesn't work
   - Same fix needed: Copy credentials to Doppler staging config

**Secondary Issues**:
- Old Lambda image (40+ days) means latest bug fixes and features not deployed
- Branch strategy confusion means unclear how to update staging with latest code

---

### Key Findings

1. **Infrastructure is production-ready** (API Gateway, Lambda, Aurora, DynamoDB, CORS, VPC)
2. **Configuration is incomplete** (missing Telegram credentials)
3. **Code is stale** (40+ days old, missing recent commits)
4. **Branch strategy misunderstood** (no "staging branch", uses `main` → staging env)

---

## Confidence Level: **High**

**Reasoning**:
- ✅ Direct AWS CLI queries confirm infrastructure state
- ✅ Lambda environment variables directly show empty Telegram credentials
- ✅ ECR metadata confirms image age
- ✅ Git history confirms branch structure
- ✅ Documentation confirms branch strategy
- ❌ Missing: Functional smoke test, database schema verification

**Confidence in "App Will NOT Work"**: **Very High** (99%)
- Empty credentials will cause immediate startup failure
- Historical precedent: LINE bot incident with identical symptoms

---

## Recommendations

### Immediate Actions (Fix Telegram Credentials)

**Step 1: Add Telegram credentials to Doppler staging**

```bash
# If credentials exist in dev:
TELEGRAM_BOT_TOKEN=$(doppler secrets get TELEGRAM_BOT_TOKEN --config dev --plain)
TELEGRAM_APP_ID=$(doppler secrets get TELEGRAM_APP_ID --config dev --plain)
TELEGRAM_APP_HASH=$(doppler secrets get TELEGRAM_APP_HASH --config dev --plain)

doppler secrets set TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" --config stg
doppler secrets set TELEGRAM_APP_ID="$TELEGRAM_APP_ID" --config stg
doppler secrets set TELEGRAM_APP_HASH="$TELEGRAM_APP_HASH" --config stg

# If credentials don't exist in dev:
# Get from @BotFather (TELEGRAM_BOT_TOKEN)
# Get from https://my.telegram.org/apps (TELEGRAM_APP_ID, TELEGRAM_APP_HASH)
doppler secrets set TELEGRAM_BOT_TOKEN='<token-from-botfather>' --config stg
doppler secrets set TELEGRAM_APP_ID='<app-id>' --config stg
doppler secrets set TELEGRAM_APP_HASH='<app-hash>' --config stg
```

**Step 2: Re-run Terraform apply to update Lambda**

```bash
cd terraform
doppler run --config stg -- terraform apply -var-file=terraform.staging.tfvars -auto-approve
```

**Step 3: Verify credentials deployed**

```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-staging \
  --query 'Environment.Variables.TELEGRAM_BOT_TOKEN' \
  --output text

# Should output token, not empty string
```

**Step 4: Smoke test**

```bash
# Test API endpoint
curl -X GET https://ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com/api/v1/health

# Check CloudWatch logs for startup validation
aws logs tail /aws/lambda/dr-daily-report-telegram-api-staging --since 5m
```

---

### Follow-Up Actions (Update Code)

**Step 1: Clarify deployment strategy**

**Current understanding**:
- `dev` branch → dev environment
- `main` branch → staging environment
- Tags `v*.*.*` → production environment

**Question for user**: How do we want to deploy latest code to staging?
- **Option A**: Merge `dev` → `main` (triggers CI/CD to staging) ← Recommended
- **Option B**: Build + push new image manually (bypasses CI/CD)
- **Option C**: Update staging to use `dev` branch image (breaks convention)

**Step 2: Deploy latest code** (assuming Option A)

```bash
# Merge dev to main
git checkout main
git merge dev
git push origin main

# CI/CD should automatically:
# 1. Build new Docker image
# 2. Push to ECR with tag
# 3. Update Lambda function code
# 4. Deploy to staging environment
```

**Step 3: Verify deployment**

```bash
# Check Lambda image updated
aws lambda get-function --function-name dr-daily-report-telegram-api-staging \
  --query 'Code.ImageUri'

# Check ECR image pushed recently
aws ecr describe-images --repository-name dr-daily-report-lambda-staging \
  --query 'sort_by(imageDetails, &imagePushedAt)[-1].{PushedAt:imagePushedAt}'
```

---

### Prevention (Apply Learnings from LINE Bot Incident)

**Already implemented** (from previous incident):
- ✅ Pre-deployment validation script: `scripts/validate-doppler-secrets.sh`
- ✅ Terraform variable validation constraints
- ✅ Documentation: `docs/deployment/PRE_DEPLOYMENT_VALIDATION.md`

**Needs extension for Telegram**:

1. **Update validation script** to include Telegram credentials:

```bash
# Edit scripts/validate-doppler-secrets.sh
# Add to REQUIRED_SECRETS:
["TELEGRAM_BOT_TOKEN"]="Telegram Bot token for Mini App"
["TELEGRAM_APP_ID"]="Telegram App ID"
["TELEGRAM_APP_HASH"]="Telegram App Hash"
```

2. **Add Terraform validation** for Telegram variables:

```hcl
# Edit terraform/variables.tf
variable "telegram_bot_token" {
  validation {
    condition     = length(var.telegram_bot_token) > 0
    error_message = "telegram_bot_token must not be empty for Telegram Mini App."
  }
}
# Similar for telegram_app_id, telegram_app_hash
```

3. **Run validation before every deploy**:

```bash
# Before terraform apply:
./scripts/validate-doppler-secrets.sh stg

# Should verify ALL required secrets including Telegram
```

---

## Next Steps (Priority Order)

### Priority 1: Fix Credentials (BLOCKER) ⚠️

- [ ] Verify Telegram credentials exist somewhere (dev config? local? create new?)
- [ ] Add Telegram credentials to Doppler staging config
- [ ] Re-run Terraform apply to update Lambda env vars
- [ ] Verify credentials deployed (non-empty strings)

### Priority 2: Verify Functionality ⚠️

- [ ] Smoke test API endpoint
- [ ] Check CloudWatch logs for startup errors
- [ ] Verify database schema exists (if not, run migrations)

### Priority 3: Update Code (Optional, if latest features needed)

- [ ] Clarify: Should staging have latest `dev` branch code?
- [ ] If yes: Merge `dev` → `main`, let CI/CD deploy
- [ ] If no: Document that staging is intentionally 40+ days behind

### Priority 4: Extend Validation (Prevention)

- [ ] Update `scripts/validate-doppler-secrets.sh` with Telegram credentials
- [ ] Add Terraform validation constraints for Telegram variables
- [ ] Test validation script on all environments

---

## References

**Related Incidents**:
- `.claude/bug-hunts/2026-01-09-linebot-no-response.md` - Identical failure pattern (missing Doppler credentials)

**Related Documentation**:
- `.claude/CLAUDE.md` line 17 - Branch strategy
- `.claude/CLAUDE.md` Principle #1 - Defensive Programming
- `.claude/CLAUDE.md` Principle #15 - Infrastructure-Application Contract
- `docs/deployment/PRE_DEPLOYMENT_VALIDATION.md` - Multi-layer validation strategy

**Infrastructure Resources**:
- API Gateway: `ta0g00v0c7` (ta0g00v0c7.execute-api.ap-southeast-1.amazonaws.com)
- Lambda: `dr-daily-report-telegram-api-staging`
- Aurora: `dr-daily-report-aurora-staging`
- ECR: `dr-daily-report-lambda-staging`

**Code References**:
- `terraform/variables.tf:126-145` - Telegram variable definitions
- `terraform/telegram_api.tf:172-174` - Telegram env var mapping to Lambda
- `scripts/validate-doppler-secrets.sh` - Pre-deployment validation script

---

## Validation Metadata

**Validation Type**: config + behavior
**Evidence Strength**: High (direct AWS queries, git verification)
**Confidence**: High (99% certain app will NOT work due to missing credentials)
**Time to Fix**: ~10 minutes (add credentials + re-apply Terraform)
**Risk if not fixed**: Telegram app unusable, same as LINE bot incident

**Last Updated**: 2026-01-09
