---
name: deploy
description: Safe deployment workflow with pre-deployment verification, step-by-step plan, and post-deployment validation
accepts_args: true
arg_schema:
  - name: change_description
    required: true
    description: "What you're deploying (e.g., 'Lambda timeout increase to 120s', 'new PDF generation feature')"
composition:
  - skill: deployment
---

# Deploy Command

**Purpose**: Execute safe deployments with forced pre-checks and validation

**Core Principle**: "Verify before deploy, validate after deploy" - never skip safety checks

**When to use**:
- Deploying Lambda functions (code or configuration changes)
- Deploying infrastructure changes (Terraform)
- Deploying Docker images (ECR → Lambda)
- Any deployment to AWS environments

**When NOT to use**:
- Local testing (no deployment)
- Read-only operations (no changes)
- Emergency rollbacks (use direct commands)

---

## Quick Reference

```bash
# Deploy Lambda configuration change
/deploy "Lambda timeout increase to 120s"
→ Runs /check-principles (scope: DEPLOYMENT)
→ Verifies infrastructure-application contract
→ Provides step-by-step deployment plan
→ Waits for approval
→ Executes deployment with waiters
→ Validates deployment success

# Deploy new feature
/deploy "PDF generation in SQS workers"
→ Checks for deployment blockers (CRITICAL violations)
→ If blockers found: STOPS deployment, shows fixes needed
→ If clear: Proceeds with safe deployment workflow
```

---

## Execution Flow

### Phase 1: Pre-Deployment Verification

**Run compliance audit** (forced, cannot skip):

```bash
/check-principles
→ Scope: DEPLOYMENT
→ Principles audited: #6, #11, #13, #15, #16
```

**Verification checklist**:
- ✅ Principle #6: Using AWS CLI waiters (not sleep)?
- ✅ Principle #11: Promoting same Docker image digest across environments?
- ✅ Principle #13: Secrets in Doppler, validated at startup?
- ✅ Principle #15: Terraform env vars match application requirements?
- ✅ Principle #16: Timezone consistent (Bangkok) across all components?

**Blocker detection**:
```
CRITICAL violations found: 2

Violation 1 (CRITICAL):
- Principle #15: Missing env var CACHE_TTL in Terraform
- Impact: Lambda will fail at startup with KeyError
- Fix: Add CACHE_TTL to terraform/lambda.tf environment block
- BLOCKS DEPLOYMENT

Violation 2 (HIGH):
- Principle #20: Lambda timeout not verified against code requirements
- Impact: Might timeout in production
- Fix: Verify code execution time, adjust timeout accordingly
- SHOULD FIX BEFORE DEPLOYMENT

Action: Fix CRITICAL issues before proceeding
```

**If CRITICAL violations found**: STOP deployment, show required fixes

**If violations cleared**: Proceed to Phase 2

---

### Phase 2: Deployment Planning

**Generate deployment plan** using deployment skill:

**1. Identify deployment type**:
- Lambda code change (ZIP/container update)
- Lambda configuration change (timeout, memory, env vars)
- Infrastructure change (Terraform)
- Multi-component change (Lambda + Terraform)

**2. Determine deployment method**:
```
Lambda code:
→ Method: Update function code
→ Command: aws lambda update-function-code
→ Wait: aws lambda wait function-updated

Lambda config:
→ Method: Update function configuration
→ Command: aws lambda update-function-configuration
→ Wait: aws lambda wait function-updated

Terraform:
→ Method: terraform apply
→ Command: terraform plan → review → terraform apply
→ Wait: depends on resources changed

Docker image:
→ Method: Build → Push ECR → Update Lambda
→ Commands: docker build → docker push → aws lambda update-function-code
→ Wait: aws lambda wait function-updated
```

**3. Identify affected resources**:
```
Changed resources:
- Lambda: dr-daily-report-worker-dev
- Terraform: aws_lambda_function.worker
- Docker: ECR image digest

Impact:
- Functions: 1 Lambda
- Duration: ~2 minutes
- Downtime: None (Lambda handles gracefully)
```

**4. Generate step-by-step plan**:
```markdown
## Deployment Plan

**Change**: Lambda timeout increase to 120s

**Resources affected**:
- Lambda: dr-daily-report-worker-dev
- Terraform: aws_lambda_function.worker (timeout = 120)

**Steps**:

### Step 1: Update Terraform Configuration
```bash
# Edit terraform/lambda.tf
# Change: timeout = 30
# To: timeout = 120
```

### Step 2: Plan Infrastructure Changes
```bash
cd terraform/environments/dev
terraform plan -out=tfplan
# Review: Verify only timeout changed
```

### Step 3: Apply Infrastructure Changes
```bash
terraform apply tfplan
# Wait for completion
```

### Step 4: Wait for Lambda Update
```bash
aws lambda wait function-updated \
  --function-name dr-daily-report-worker-dev
```

### Step 5: Verify Deployment
```bash
# Check timeout applied
aws lambda get-function-configuration \
  --function-name dr-daily-report-worker-dev \
  --query 'Timeout'

# Expected: 120
```

### Step 6: Smoke Test
```bash
# Invoke Lambda with test event
aws lambda invoke \
  --function-name dr-daily-report-worker-dev \
  --payload '{"test": true}' \
  /tmp/response.json

# Verify: StatusCode = 200, no errors in response
```

**Estimated duration**: 2-3 minutes
**Rollback plan**: Revert Terraform timeout to 30, terraform apply
```

---

### Phase 3: User Approval

**Present plan to user**:
```
Deployment plan ready.

CRITICAL violations: 0 (all clear)
HIGH violations: 0
Affected resources: 1 Lambda
Estimated duration: 2-3 minutes
Downtime: None

Review plan above. Proceed with deployment?
[Requires explicit user approval]
```

**Wait for user confirmation**:
- User approves: Proceed to Phase 4
- User rejects: Abort deployment, provide exit message

---

### Phase 4: Execute Deployment

**Execute step-by-step plan** (using deployment skill):

**1. Pre-deployment state capture**:
```bash
# Capture current state for rollback
aws lambda get-function-configuration \
  --function-name dr-daily-report-worker-dev \
  > /tmp/pre-deployment-config.json

# Save current Terraform state
cd terraform/environments/dev
terraform show > /tmp/pre-deployment-terraform.txt
```

**2. Execute deployment steps** (from plan):
```bash
# Step 1: Update Terraform
# (show progress to user)

# Step 2: Plan changes
# (show plan output)

# Step 3: Apply changes
# (show apply progress)

# Step 4: Wait for Lambda update
# (show waiter progress)
```

**3. Handle failures**:
```
If deployment fails at any step:
→ Capture error details
→ Log failure to CloudWatch
→ Provide rollback instructions
→ Do NOT continue to next step
```

**4. Monitor deployment progress**:
```
[Step 1/6] Updating Terraform configuration... ✅ Done
[Step 2/6] Planning infrastructure changes... ✅ Done (1 resource to change)
[Step 3/6] Applying infrastructure changes... ⏳ In progress...
[Step 3/6] Applying infrastructure changes... ✅ Done
[Step 4/6] Waiting for Lambda update... ⏳ Waiting (30s elapsed)...
[Step 4/6] Waiting for Lambda update... ✅ Done
[Step 5/6] Verifying deployment... ✅ Done (Timeout = 120)
[Step 6/6] Smoke testing... ✅ Done (StatusCode = 200)

Deployment completed successfully!
```

---

### Phase 5: Post-Deployment Validation

**Validate deployment success** (Progressive Evidence Strengthening):

**Layer 1: Surface Evidence** (exit codes):
```bash
# Terraform apply exit code
echo $?  # Should be 0

# AWS CLI command exit code
# Already verified during execution
```

**Layer 2: Content Evidence** (payloads):
```bash
# Verify Lambda configuration changed
aws lambda get-function-configuration \
  --function-name dr-daily-report-worker-dev \
  --query 'Timeout'
# Expected: 120 (not 30)

# Verify Terraform state matches
terraform show | grep timeout
# Expected: timeout = 120
```

**Layer 3: Observability Evidence** (logs):
```bash
# Check CloudWatch logs for Lambda startup
aws logs tail /aws/lambda/dr-daily-report-worker-dev --since 5m

# Look for:
# - ✅ START RequestId (Lambda started)
# - ✅ Application logs (not just START/END = startup crash)
# - ❌ No ERROR logs
# - ✅ END RequestId (completed successfully)
```

**Layer 4: Ground Truth** (actual behavior):
```bash
# Smoke test: Invoke Lambda
aws lambda invoke \
  --function-name dr-daily-report-worker-dev \
  --payload '{"test": true}' \
  /tmp/response.json

# Verify:
cat /tmp/response.json
# Expected: Valid response, no errors

# Verify timeout NOT triggered (should complete < 120s)
# Check Duration in CloudWatch metrics
```

**Validation result**:
```
✅ Layer 1: Exit codes = 0 (deployment executed)
✅ Layer 2: Timeout = 120 (config applied)
✅ Layer 3: Application logs present (Lambda started correctly)
✅ Layer 4: Smoke test passed (actual behavior correct)

Deployment validated successfully!
```

**If validation fails**:
```
❌ Layer 3: Only START/END logs, no application logs

Diagnosis: Lambda startup crash
Root cause: Missing environment variable

Action: ROLLBACK deployment
```

---

### Phase 6: Rollback (If Needed)

**Rollback triggers** (when to revert):
- Smoke test fails (Lambda returns 500)
- CloudWatch shows startup crash (only START/END logs)
- Error rate exceeds baseline (>5% errors in first 5 minutes)
- Ground truth verification fails (timeout still occurring)

**Rollback execution**:
```bash
# Option 1: Terraform rollback
cd terraform/environments/dev
git diff HEAD~1 terraform/lambda.tf  # Show what changed
git checkout HEAD~1 -- terraform/lambda.tf  # Revert
terraform plan  # Verify rollback plan
terraform apply  # Execute rollback
aws lambda wait function-updated  # Wait for rollback

# Option 2: Direct Lambda update (faster)
aws lambda update-function-configuration \
  --function-name dr-daily-report-worker-dev \
  --timeout 30  # Previous known-good value
aws lambda wait function-updated

# Verify rollback
aws lambda get-function-configuration \
  --function-name dr-daily-report-worker-dev \
  --query 'Timeout'
# Expected: 30 (reverted)
```

**Rollback verification**:
```bash
# Re-run smoke test
aws lambda invoke \
  --function-name dr-daily-report-worker-dev \
  --payload '{"test": true}' \
  /tmp/rollback-test.json

# Verify: Back to working state
```

**Document rollback**:
```markdown
# Deployment Rollback

**Date**: 2026-01-03 11:30 UTC+7
**Deployment**: Lambda timeout increase to 120s
**Rollback reason**: Smoke test failed (Lambda returned 500)
**Root cause**: Missing CACHE_TTL environment variable
**Rollback method**: Terraform revert + apply
**Rollback success**: Yes (smoke test passed after rollback)

**Action items**:
1. Fix: Add CACHE_TTL to Terraform
2. Re-deploy: After fix applied
3. Post-mortem: Why was CACHE_TTL missing in plan?
```

---

## Output Format

```markdown
# Deployment: {change_description}

**Date**: {YYYY-MM-DD HH:MM UTC+7}
**Environment**: {dev | stg | prd}

---

## Phase 1: Pre-Deployment Verification

### Compliance Audit Results

**Principles audited**: 5 (deployment-related)

**Violations**:
- ✅ No CRITICAL violations
- ⚠️ 1 HIGH violation (Principle #20: timeout not verified)

**Assessment**: Deployment can proceed (no blockers)

---

## Phase 2: Deployment Plan

### Resources Affected

- Lambda: {function-name}
- Terraform: {resource}
- Docker: {image}

### Deployment Steps

#### Step 1: {Step description}
```bash
{Command}
```

[Repeat for each step]

### Estimated Duration

{X} minutes

### Rollback Plan

{How to rollback if deployment fails}

---

## Phase 3: User Approval

**Plan presented**: {timestamp}
**User approved**: {Yes/No}
**Approved at**: {timestamp}

---

## Phase 4: Execution

### Deployment Progress

- [✅] Step 1: {description}
- [✅] Step 2: {description}
- [⏳] Step 3: {description} (in progress...)

### Deployment Result

**Status**: {SUCCESS | FAILED}
**Completed at**: {timestamp}
**Duration**: {actual duration}

---

## Phase 5: Validation

### Evidence Layers

**Layer 1 (Surface)**: ✅ Exit codes = 0
**Layer 2 (Content)**: ✅ Configuration applied (timeout = 120)
**Layer 3 (Observability)**: ✅ Application logs present
**Layer 4 (Ground Truth)**: ✅ Smoke test passed

### Validation Result

**Status**: ✅ VALIDATED
**Confidence**: High

---

## Summary

**Deployment**: {SUCCESS | FAILED | ROLLED BACK}

{If success}: Deployment completed successfully and validated.

{If failed}: Deployment failed at step X. Rollback executed. Root cause: {reason}.

**Next steps**:
- {Action 1}
- {Action 2}
```

---

## Examples

### Example 1: Successful Deployment

```bash
/deploy "Lambda timeout increase to 120s"
```

**Output**:
```markdown
# Deployment: Lambda timeout increase to 120s

## Phase 1: Pre-Deployment Verification

✅ No CRITICAL violations
✅ Deployment can proceed

## Phase 2: Deployment Plan

Resources: dr-daily-report-worker-dev
Steps: 6
Duration: 2-3 minutes

## Phase 3: User Approval

[Plan presented, awaiting user approval...]

User: "proceed"

## Phase 4: Execution

[✅] Step 1/6: Update Terraform configuration
[✅] Step 2/6: Plan infrastructure changes
[✅] Step 3/6: Apply infrastructure changes
[✅] Step 4/6: Wait for Lambda update
[✅] Step 5/6: Verify deployment
[✅] Step 6/6: Smoke test

Deployment completed successfully!

## Phase 5: Validation

✅ All 4 evidence layers validated
✅ Deployment success confirmed

## Summary

✅ Deployment succeeded
Duration: 2 minutes 15 seconds
Confidence: High
```

---

### Example 2: Blocked Deployment

```bash
/deploy "New PDF generation feature"
```

**Output**:
```markdown
# Deployment: New PDF generation feature

## Phase 1: Pre-Deployment Verification

❌ CRITICAL violations found: 2

Violation 1 (CRITICAL):
- Principle #15: Missing env var PDF_S3_BUCKET
- Impact: Lambda will crash at startup
- Fix: Add to terraform/lambda.tf

Violation 2 (CRITICAL):
- Principle #19: No boundary tests for PDF generation
- Impact: Deployment fidelity gap
- Fix: Add test_pdf_generation_boundary()

## Action Required

Fix CRITICAL issues before deployment can proceed:

1. Add PDF_S3_BUCKET environment variable
2. Add boundary test for PDF generation

After fixing, re-run /deploy command.

## Summary

❌ Deployment BLOCKED
Reason: CRITICAL violations present
```

---

### Example 3: Deployment with Rollback

```bash
/deploy "Lambda memory increase to 2048MB"
```

**Output**:
```markdown
# Deployment: Lambda memory increase to 2048MB

## Phase 4: Execution

[✅] Step 1/6: Update Terraform
[✅] Step 2/6: Plan changes
[✅] Step 3/6: Apply changes
[✅] Step 4/6: Wait for update
[✅] Step 5/6: Verify deployment (Memory = 2048)
[❌] Step 6/6: Smoke test FAILED

Error: Lambda returned 500 Internal Server Error

## Phase 6: Rollback

Rollback triggered: Smoke test failed

Executing rollback:
[✅] Revert Terraform to 1024MB
[✅] Apply rollback
[✅] Wait for rollback complete
[✅] Verify rollback (Memory = 1024)
[✅] Smoke test after rollback: PASSED

## Root Cause Analysis

Smoke test failure reason: Out of memory error in logs
Issue: 2048MB exceeded Lambda limits for function type

## Summary

❌ Deployment FAILED, ✅ ROLLBACK SUCCESSFUL
Duration: 4 minutes (2 min deploy + 2 min rollback)
Status: Back to working state (1024MB)

Next steps:
1. Investigate memory requirements
2. Check Lambda limits for function configuration
3. Consider alternative approach (optimize memory usage)
```

---

## Best Practices

### Do
- **Always run /check-principles first** (forced verification)
- **Use AWS CLI waiters** (never sleep)
- **Capture pre-deployment state** (enables rollback)
- **Validate through all 4 evidence layers** (don't stop at exit code)
- **Document rollbacks** (what happened, why, how to prevent)
- **Test rollback procedure** (before needing it)

### Don't
- **Don't skip CRITICAL fixes** (will cause production failure)
- **Don't deploy without approval** (forced user confirmation)
- **Don't assume success from exit code** (verify through ground truth)
- **Don't delete failed deployments** (preserve for investigation)
- **Don't rush validation** (thorough > fast)

---

## Integration with Principles

**Principle #6 (Deployment Monitoring)**:
- Uses AWS CLI waiters (not sleep)
- Monitors deployment progress
- Validates completion

**Principle #2 (Progressive Evidence Strengthening)**:
- Layer 1: Exit codes (weakest)
- Layer 2: Configuration payloads
- Layer 3: CloudWatch logs
- Layer 4: Smoke test (strongest)

**Principle #15 (Infrastructure-Application Contract)**:
- Verifies Terraform env vars match application requirements
- Checks before deployment (not after failure)

**Principle #21 (Deployment Blocker Resolution)**:
- Applies decision heuristic (bypass vs fix)
- Documents when manual deployment acceptable

---

## See Also

- **Commands**:
  - `/check-principles` - Pre-deployment compliance audit
  - `/validate` - Validate deployment success
  - `/trace` - Root cause analysis if deployment fails

- **Skills**:
  - [deployment](../skills/deployment/) - Deployment methodology
  - [error-investigation](../skills/error-investigation/) - Incident analysis

- **Principles**:
  - Principle #6: Deployment Monitoring Discipline
  - Principle #11: Artifact Promotion Principle
  - Principle #15: Infrastructure-Application Contract
  - Principle #21: Deployment Blocker Resolution

---

## Prompt Template

You are executing the `/deploy` command with arguments: $ARGUMENTS

**Change description**: $1

---

### Execution Steps

**Phase 1: Pre-Deployment Verification** (REQUIRED, cannot skip)

Run `/check-principles` with scope=DEPLOYMENT:
- Audit Principles #6, #11, #13, #15, #16
- If CRITICAL violations: STOP, show fixes required
- If no CRITICAL violations: Proceed to Phase 2

**Phase 2: Deployment Planning**

Using deployment skill:
1. Identify deployment type (Lambda code/config, Terraform, Docker)
2. Determine deployment method (update-function-code, terraform apply, etc.)
3. Identify affected resources (which Lambdas, Terraform resources)
4. Generate step-by-step plan (specific commands with waiters)
5. Estimate duration
6. Provide rollback plan

**Phase 3: User Approval** (REQUIRED, cannot skip)

Present plan to user, wait for approval:
- Show: CRITICAL violations, affected resources, duration, downtime
- Ask: "Proceed with deployment?"
- If approved: Proceed to Phase 4
- If rejected: Abort, show exit message

**Phase 4: Execute Deployment**

1. Capture pre-deployment state (for rollback)
2. Execute each step from plan sequentially
3. Use AWS CLI waiters (not sleep)
4. Show progress to user (Step X/N: description)
5. If any step fails: Stop, capture error, provide rollback instructions

**Phase 5: Post-Deployment Validation**

Validate using Progressive Evidence Strengthening:
1. Layer 1: Exit codes (deployment executed)
2. Layer 2: Configuration payloads (changes applied)
3. Layer 3: CloudWatch logs (application started correctly)
4. Layer 4: Smoke test (actual behavior correct)

If any layer fails: Trigger rollback

**Phase 6: Rollback (If Needed)**

If validation fails:
1. Identify rollback method (Terraform revert, direct Lambda update)
2. Execute rollback
3. Verify rollback success (re-run smoke test)
4. Document rollback (what, why, how to prevent)

---

### Output

Use the output format above, including all 6 phases with clear status indicators.
