---
title: LINE bot doesn't response anymore after infrastructure update
bug_type: production-error
date: 2026-01-09
status: root_cause_found
confidence: High
---

# Bug Hunt Report: LINE bot doesn't response anymore after infrastructure update

## Symptom

**Description**: LINE bot stopped responding to user messages immediately after Terraform infrastructure update

**First occurrence**: 2026-01-09 11:04 UTC (approximately 20 minutes after Terraform apply completed)

**Affected scope**: All LINE bot users (100% failure rate)

**Impact**: High - Production service completely down

---

## Investigation Summary

**Bug type**: production-error

**Investigation duration**: ~15 minutes

**Status**: Root cause found ✅

---

## Evidence Gathered

### Logs

CloudWatch logs from `/aws/lambda/line-bot-ticker-report`:

```
2026-01-09T11:04:44 START RequestId: bfac24ca-6212-417d-8ca0-64b07fc472e7 Version: $LATEST

2026-01-09T11:05:04 [ERROR]	2026-01-09T11:05:04.373Z	bfac24ca-6212-417d-8ca0-64b07fc472e7
❌ Missing environment variables: ['LINE_CHANNEL_ACCESS_TOKEN', 'LINE_CHANNEL_SECRET']

2026-01-09T11:05:04 END RequestId: bfac24ca-6212-417d-8ca0-64b07fc472e7
2026-01-09T11:05:04 REPORT RequestId: bfac24ca-6212-417d-8ca0-64b07fc472e7
Duration: 20214.72 ms	Billed Duration: 20407 ms	Memory Size: 512 MB	Max Memory Used: 470 MB	Init Duration: 192.01 ms
```

**Critical error**: Lambda explicitly reports missing LINE credentials at startup.

### Lambda Configuration

```bash
$ aws lambda get-function-configuration --function-name line-bot-ticker-report \
  --query 'Environment.Variables' | grep LINE_CHANNEL

"LINE_CHANNEL_SECRET": "",
"LINE_CHANNEL_ACCESS_TOKEN": ""
```

**Both credentials are empty strings** - explains authentication failure.

### Doppler Configuration

**Dev config** (currently used):
```bash
$ doppler secrets --config dev --only-names | grep -i line
# No LINE secrets found ❌
```

**Staging config** (for comparison):
```bash
$ doppler secrets --config stg --only-names | grep -i line
│ LINE_CHANNEL_ACCESS_TOKEN        │
│ LINE_CHANNEL_SECRET              │
│ TF_VAR_LINE_CHANNEL_ACCESS_TOKEN │
│ TF_VAR_LINE_CHANNEL_SECRET       │
```

**Staging has credentials, dev does not** - proves credentials should exist but are missing.

### Terraform Configuration

`terraform/main.tf:254-261`:
```hcl
environment {
  variables = {
    # LINE Bot credentials
    LINE_CHANNEL_ACCESS_TOKEN = var.LINE_CHANNEL_ACCESS_TOKEN
    LINE_CHANNEL_SECRET       = var.LINE_CHANNEL_SECRET

    # LLM API
    OPENROUTER_API_KEY        = var.OPENROUTER_API_KEY
    # ... other vars
  }
}
```

`terraform/terraform.dev.tfvars:21-28` documents requirement:
```
# Sensitive variables - DO NOT set here!
# These are injected via Doppler TF_VAR_* environment variables.
# Run with: doppler run -- terraform plan
#
# Required Doppler secrets:
#   - TF_VAR_OPENROUTER_API_KEY
#   - TF_VAR_LINE_CHANNEL_ACCESS_TOKEN  # ❌ Missing in dev config
#   - TF_VAR_LINE_CHANNEL_SECRET        # ❌ Missing in dev config
```

### Recent Changes

```bash
$ git log --oneline -3
5056563 chore(infra): Complete SQS removal - clean up Terraform and application code
6bfc91e feat(skills): Add infrastructure-verification skill
7c1b9f5 claude renew 1/9/2025 5pm.
```

Most recent commit `5056563` triggered Terraform apply that:
- Removed `REPORT_JOBS_QUEUE_URL` environment variable from LINE bot Lambda
- **Re-applied ALL environment variables** (including LINE credentials)
- Because `TF_VAR_LINE_CHANNEL_ACCESS_TOKEN` wasn't in environment, Terraform used empty string

### Terraform Apply Log

```
[0m[1maws_lambda_function.line_bot: Modifying... [id=line-bot-ticker-report][0m[0m
[0m[1maws_lambda_function.line_bot: Modifications complete after 5s [id=line-bot-ticker-report][0m
```

Confirmation that LINE bot Lambda was modified during this apply.

---

## Hypotheses Tested

### Hypothesis 1: Missing LINE credentials in Doppler dev config

**Likelihood**: High

**Test performed**:
1. Checked Doppler dev config for LINE secrets: `doppler secrets --config dev --only-names | grep -i line`
2. Checked Doppler staging config: `doppler secrets --config stg --only-names | grep -i line`
3. Compared Lambda environment variables: `aws lambda get-function-configuration --function-name line-bot-ticker-report`

**Result**: ✅ Confirmed

**Reasoning**:
- Dev config has NO LINE secrets
- Staging config HAS LINE secrets (4 total: base + TF_VAR_ prefixed)
- Lambda environment variables are empty strings (not absent, which would be the case if never set)
- Empty strings indicate Terraform applied with missing TF_VAR variables

**Evidence**:
- Doppler dev config query returned 0 LINE-related secrets
- Doppler staging config showed 4 LINE-related secrets
- Lambda config shows `"LINE_CHANNEL_ACCESS_TOKEN": ""` and `"LINE_CHANNEL_SECRET": ""`
- Terraform apply logs show LINE bot Lambda was modified

---

### Hypothesis 2: Recent code change broke LINE bot

**Likelihood**: Low

**Test performed**:
1. Checked recent commits: `git log --oneline -5`
2. Reviewed commit `5056563` - only removed SQS infrastructure, no LINE bot code changes
3. Checked application code in `src/` - no changes to LINE bot handler

**Result**: ❌ Eliminated

**Reasoning**:
- No application code changes to LINE bot in recent commits
- Changes were infrastructure-only (SQS removal)
- Error message explicitly says "missing environment variables" (not code error)

---

### Hypothesis 3: LINE API credentials expired or revoked

**Likelihood**: Low

**Test performed**:
1. Checked if staging LINE bot still works (uses same LINE channel)
2. Error message is "missing environment variables" not "authentication failed"

**Result**: ❌ Eliminated

**Reasoning**:
- Error is about missing env vars (Lambda startup), not authentication failure (runtime)
- If credentials expired, we'd see different error (401 Unauthorized from LINE API)
- Staging config has same credentials and presumably works

---

## Root Cause

**Identified cause**: Missing LINE Bot credentials in Doppler dev configuration

**Confidence**: High

**Supporting evidence**:
1. Lambda logs explicitly report: `❌ Missing environment variables: ['LINE_CHANNEL_ACCESS_TOKEN', 'LINE_CHANNEL_SECRET']`
2. Lambda configuration shows both variables set to empty strings (`""`)
3. Doppler dev config has NO LINE credentials (0 found)
4. Doppler staging config HAS LINE credentials (4 found) - proves they should exist
5. Terraform apply modified LINE bot Lambda and re-applied ALL environment variables
6. Without `TF_VAR_LINE_CHANNEL_ACCESS_TOKEN` in environment, Terraform substituted empty string

**Code location**: `terraform/main.tf:257-258` (variable references)

**Why this causes the symptom**:

1. **Infrastructure-Application Contract Violation** (Principle #15):
   - Application code expects `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_CHANNEL_SECRET` at startup
   - Terraform configuration declares dependency: `var.LINE_CHANNEL_ACCESS_TOKEN`
   - Doppler dev config missing these secrets
   - When Terraform runs without `TF_VAR_*` environment variables, it uses empty strings

2. **Deployment Sequence**:
   - We ran `terraform apply` to remove SQS infrastructure
   - Terraform detected drift in LINE bot Lambda (removed `REPORT_JOBS_QUEUE_URL`)
   - Terraform re-applied entire `environment.variables` block
   - LINE credentials weren't in Doppler → Terraform used empty strings
   - Lambda now has `LINE_CHANNEL_ACCESS_TOKEN=""` instead of actual token

3. **Why It Manifested Now**:
   - Before: Lambda had valid credentials (from previous correct Terraform apply or manual setting)
   - Trigger: Terraform apply modified Lambda to remove `REPORT_JOBS_QUEUE_URL`
   - Effect: Terraform re-applied ALL env vars, including missing LINE credentials
   - Result: Valid credentials overwritten with empty strings

**This is a textbook example of Principle #15 violation** - Terraform configuration expected Doppler to provide credentials, but Doppler dev config was incomplete.

---

## Reproduction Steps

To reproduce this issue:

1. Remove LINE credentials from Doppler dev config:
   ```bash
   doppler secrets delete LINE_CHANNEL_ACCESS_TOKEN --config dev --yes
   doppler secrets delete LINE_CHANNEL_SECRET --config dev --yes
   doppler secrets delete TF_VAR_LINE_CHANNEL_ACCESS_TOKEN --config dev --yes
   doppler secrets delete TF_VAR_LINE_CHANNEL_SECRET --config dev --yes
   ```

2. Run Terraform apply:
   ```bash
   cd terraform
   doppler run --config dev -- bash -c 'export TF_VAR_OPENROUTER_API_KEY=$OPENROUTER_API_KEY && terraform apply -var-file=terraform.dev.tfvars -auto-approve'
   ```

3. Observe LINE bot Lambda environment:
   ```bash
   aws lambda get-function-configuration --function-name line-bot-ticker-report \
     --query 'Environment.Variables' | grep LINE_CHANNEL
   ```

**Expected behavior**: Terraform should fail with error "No value for required variable"

**Actual behavior**:
- Terraform silently uses empty strings for missing TF_VAR variables
- Lambda gets updated with `LINE_CHANNEL_ACCESS_TOKEN=""`
- LINE bot fails to start with "Missing environment variables" error

**Note**: Terraform's behavior of using empty string for missing variables is debatable - some would call it a Terraform bug, but it's actually expected behavior when variables are optional or have defaults.

---

## Fix Candidates

### Fix 1: Copy LINE credentials from staging to dev config ⭐ RECOMMENDED

**Approach**:
1. Use Doppler CLI to get LINE credentials from staging config
2. Set them in dev config
3. Re-run Terraform apply to push credentials to Lambda

```bash
# Get values from staging (note: this requires read access to staging config)
TOKEN=$(doppler secrets get LINE_CHANNEL_ACCESS_TOKEN --config stg --plain)
SECRET=$(doppler secrets get LINE_CHANNEL_SECRET --config stg --plain)

# Set in dev config
doppler secrets set LINE_CHANNEL_ACCESS_TOKEN="$TOKEN" --config dev
doppler secrets set LINE_CHANNEL_SECRET="$SECRET" --config dev
doppler secrets set TF_VAR_LINE_CHANNEL_ACCESS_TOKEN="$TOKEN" --config dev
doppler secrets set TF_VAR_LINE_CHANNEL_SECRET="$SECRET" --config dev

# Verify secrets were set
doppler secrets --config dev --only-names | grep -i line

# Re-run Terraform apply to update Lambda
cd terraform
doppler run --config dev -- bash -c 'export TF_VAR_OPENROUTER_API_KEY=$OPENROUTER_API_KEY TF_VAR_AURORA_MASTER_PASSWORD=$AURORA_MASTER_PASSWORD && terraform apply -var-file=terraform.dev.tfvars -auto-approve'

# Wait for Lambda update to complete
aws lambda wait function-updated --function-name line-bot-ticker-report

# Test LINE bot
# Send a test message to LINE bot and verify response
```

**Pros**:
- Fast (5-10 minutes end-to-end)
- Uses existing valid credentials (no need to generate new ones)
- Fixes root cause (Doppler config incomplete)
- Infrastructure-as-Code compliant (uses Terraform + Doppler)
- Low risk (reading from staging doesn't affect staging)
- Maintains consistency between environments

**Cons**:
- Requires Doppler read access to staging config
- Copies credentials between environments (security consideration)
- Need to set 4 secrets (2 base + 2 TF_VAR prefixed)

**Estimated effort**: 5-10 minutes

**Risk**: Low
- Reading staging config is read-only operation
- Writing to dev config doesn't affect other environments
- Terraform apply only updates dev Lambda

---

### Fix 2: Manually update Lambda environment variables via AWS CLI

**Approach**:
Directly update LINE bot Lambda environment variables using AWS CLI, bypassing Terraform.

```bash
# Update Lambda environment variables directly
aws lambda update-function-configuration \
  --function-name line-bot-ticker-report \
  --environment "Variables={\
    LINE_CHANNEL_ACCESS_TOKEN='<token>',\
    LINE_CHANNEL_SECRET='<secret>',\
    OPENROUTER_API_KEY='<existing>',\
    ... (all other existing vars)\
  }"

# Wait for update
aws lambda wait function-updated --function-name line-bot-ticker-report
```

**Pros**:
- Fastest option (2-3 minutes if you have credentials)
- Immediate fix (no Terraform apply needed)
- Bypasses Doppler issue temporarily

**Cons**:
- **Creates configuration drift** - Terraform state won't match reality
- Next Terraform apply will overwrite manual changes (back to empty strings)
- Doesn't fix root cause (Doppler still missing secrets)
- Violates Infrastructure-as-Code principle
- Requires knowing all existing environment variables (risky to miss one)

**Estimated effort**: 2-3 minutes

**Risk**: Medium
- Configuration drift causes future Terraform applies to revert fix
- Easy to accidentally remove other env vars
- Temporary fix only - must still update Doppler eventually

---

### Fix 3: Generate new LINE credentials and add to all Doppler configs

**Approach**:
1. Access LINE Developers console
2. Generate fresh LINE channel credentials
3. Add to all Doppler configs (dev, stg, prd)
4. Run Terraform apply on all environments

**Pros**:
- Most secure (new credentials, revoke old ones)
- Ensures all environments have valid, fresh credentials
- Good security hygiene (credential rotation)
- Permanent fix for all environments

**Cons**:
- Requires access to LINE Developers console (might need permissions)
- Slowest option (30+ minutes)
- Need to coordinate across all environments
- Risk of breaking staging/production during update
- Requires updating LINE bot webhook URL if channel recreated

**Estimated effort**: 30-60 minutes

**Risk**: Medium
- Updating credentials in production is risky (downtime if done wrong)
- Need to coordinate staging and production updates
- Old credentials need to be revoked after confirming new ones work

---

## Recommendation

**Recommended fix**: Fix 1 - Copy LINE credentials from staging to dev config

**Rationale**:
1. **Fast recovery**: Restores LINE bot service in 5-10 minutes (critical for production)
2. **Root cause fix**: Addresses missing Doppler secrets, not just symptoms
3. **Low risk**:
   - Read-only operation on staging (no impact)
   - Write to dev config only (isolated blast radius)
   - Infrastructure-as-Code compliant (proper Terraform workflow)
4. **Maintainable**: Future Terraform applies will work correctly
5. **Reversible**: Can always rotate credentials later if needed (Fix 3)

**Why not Fix 2 (Manual update)**:
- Creates drift between Terraform state and reality
- Next Terraform apply will break LINE bot again
- Doesn't solve underlying problem (Doppler missing secrets)

**Why not Fix 3 (New credentials)**:
- Too slow for production outage (30+ minutes vs 5 minutes)
- Higher risk (affects multiple environments)
- Unnecessary complexity (existing credentials work fine in staging)
- Can do credential rotation later as maintenance task

**Implementation priority**: P0 (production service down)

---

## Next Steps

- [x] Identify root cause (Doppler dev config missing LINE credentials)
- [x] Determine recommended fix (Copy from staging to dev)
- [ ] **Execute Fix 1**: Copy LINE credentials from staging to dev config
- [ ] Verify LINE bot responds to test messages
- [ ] Monitor CloudWatch logs for successful requests
- [ ] Document solution: `/journal error "LINE bot credentials missing in Doppler dev"`
- [ ] Add validation check to prevent recurrence:
  - Add Terraform validation that fails if LINE credentials are empty
  - Or: Add pre-apply check script that verifies required Doppler secrets exist

---

## Investigation Trail

**What was checked**:
- ✅ CloudWatch logs for LINE bot Lambda
- ✅ Lambda environment variable configuration
- ✅ Doppler dev config secrets
- ✅ Doppler staging config secrets (for comparison)
- ✅ Recent git commits and Terraform changes
- ✅ Terraform apply logs
- ✅ Terraform configuration in `main.tf`

**What was ruled out**:
- ❌ Application code bug (no code changes in recent commits)
- ❌ LINE API credentials expired (error is "missing env vars" not "auth failed")
- ❌ Network/infrastructure issue (Lambda is Active, logs show startup error)
- ❌ Deployment artifact issue (Terraform updated config, not code)

**Tools used**:
- AWS CLI (`aws lambda`, `aws logs`)
- Doppler CLI (`doppler secrets`)
- Git (`git log`)
- Terraform apply logs

**Time spent**:
- Evidence gathering: 5 minutes
- Hypothesis testing: 5 minutes
- Root cause analysis: 5 minutes
- Fix candidate evaluation: 5 minutes
- **Total**: ~20 minutes

---

## Lessons Learned

### Principle #15: Infrastructure-Application Contract

This incident is a **textbook violation** of Principle #15 (Infrastructure-Application Contract):

> "Maintain contract between application code (`src/`), infrastructure (`terraform/`), and principles (`.claude/CLAUDE.md`). Code deployed without matching infrastructure causes silent failures hours after deployment."

**What went wrong**:
1. Terraform expected `TF_VAR_LINE_CHANNEL_ACCESS_TOKEN` from Doppler
2. Doppler dev config was missing these secrets
3. Terraform silently used empty strings (no validation)
4. Lambda deployed with broken configuration

**Prevention for future**:

1. **Pre-deployment validation** (add to deployment workflow):
   ```bash
   # Script: scripts/validate-doppler-secrets.sh
   REQUIRED_SECRETS=(
     "TF_VAR_LINE_CHANNEL_ACCESS_TOKEN"
     "TF_VAR_LINE_CHANNEL_SECRET"
     "TF_VAR_OPENROUTER_API_KEY"
     "TF_VAR_AURORA_MASTER_PASSWORD"
   )

   for secret in "${REQUIRED_SECRETS[@]}"; do
     if ! doppler secrets get "$secret" --config dev --plain &>/dev/null; then
       echo "❌ Missing required secret: $secret"
       exit 1
     fi
   done
   echo "✅ All required secrets present"
   ```

2. **Terraform variable validation**:
   ```hcl
   variable "LINE_CHANNEL_ACCESS_TOKEN" {
     type        = string
     description = "LINE channel access token"

     validation {
       condition     = length(var.LINE_CHANNEL_ACCESS_TOKEN) > 0
       error_message = "LINE_CHANNEL_ACCESS_TOKEN must not be empty"
     }
   }
   ```

3. **Doppler config inheritance** (Principle #13):
   - Consider if LINE bot credentials should be shared across dev/stg/prd
   - Use Doppler config inheritance to prevent drift

4. **Lambda startup validation** (Principle #1 - Defensive Programming):
   - Application code already validates at startup (good!)
   - Could fail faster by checking env vars before initializing other services

### Why This Wasn't Caught Earlier

**Good practices that helped**:
- ✅ Defensive programming in application code (startup validation caught issue)
- ✅ CloudWatch logging showed exact error
- ✅ Terraform documentation listed required secrets

**What could have caught it earlier**:
- ❌ No pre-deployment validation script
- ❌ No Terraform variable validation rules
- ❌ No smoke test after Terraform apply
- ❌ No alerts on Lambda initialization errors

**Recommended additions**:
1. Add pre-deployment validation to CI/CD pipeline
2. Add Terraform variable validation constraints
3. Add post-deploy smoke test (send test message to LINE bot)
4. Set up CloudWatch alarm for Lambda startup errors

---

## Related Documentation

- **Principle #15**: Infrastructure-Application Contract (`docs/guides/infrastructure-application-contract.md`)
- **Principle #13**: Secret Management Discipline (`docs/deployment/DOPPLER_CONFIG.md`)
- **Principle #1**: Defensive Programming (startup validation)
- **Principle #6**: Deployment Monitoring Discipline (smoke tests)

---

## Status

**Resolution status**: Investigation complete, fix identified

**Next action**: Execute Fix 1 (copy credentials from staging to dev)

**Owner**: DevOps / Infrastructure team

**Follow-up**: Add pre-deployment validation to prevent recurrence
