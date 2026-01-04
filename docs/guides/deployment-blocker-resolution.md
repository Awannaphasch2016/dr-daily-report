# Deployment Blocker Resolution Guide

**Principle**: Principle #21 in CLAUDE.md
**Category**: Deployment, Decision Making, Risk Management
**Abstraction**: [decision-2026-01-03-deployment-blocker-resolution.md](../../.claude/abstractions/decision-2026-01-03-deployment-blocker-resolution.md)

---

## Overview

When deployment is blocked by validation failures or pipeline issues, apply systematic decision heuristic to choose resolution path. **Not all blockers require fixing**—some can be safely bypassed when evidence supports safety.

**Core insight**: Treating all validation gates as equally important blocks progress. When evidence shows change is safe (tests passed, backward compatible, auditable artifact), bypass unrelated blockers and fix them separately from critical path.

---

## Core Problem

**Circular dependency scenario**:
- Component A (your change) requires validation to pass
- Validation tests Component B (unrelated)
- Component B failing blocks Component A deployment
- Fixing Component B requires deployment
- **Result**: Neither can proceed without the other

**Common triggers**:
- Deployment blocked by validation of unrelated component
- Validation requires deployed state to pass
- Error message references component you didn't modify
- Pipeline has been working, suddenly breaks on unrelated change

---

## Decision Heuristic

### Choose LEAST RESISTANCE (Bypass Blocker) When

All 5 conditions met:

#### 1. Change is isolated and validated independently
- Handler tests passed ✅
- Docker image built successfully ✅
- Quality Gates green (linting, type checking, unit tests) ✅

**Evidence**: Layer 2+ (Content) signals strong enough for decision

#### 2. Blocker is unrelated to current change
- Schema validation tests different Lambda (not yours)
- Pre-existing failure (existed before your change)
- Error message references component you didn't modify

**Pattern**: Your PR touches `report_worker.py`, error in `query_tool.py`

#### 3. Change is backward compatible
- New mode added, existing modes still work (SQS mode unaffected)
- No breaking changes to existing functionality
- Old behavior preserved (can deploy incrementally)

**Verification**: Test that existing code paths still work

#### 4. Manual bypass is safe and auditable
- Use artifact built by CI/CD (promotion, not rebuild)
- Traceable to commit SHA or image digest
- Same image that passed Quality Gates
- Not ad-hoc local build

**Anti-pattern**: `docker build` locally → manual push (untraceable)

#### 5. Alternative paths have high cost
- **Fixing blocker**: Hours of investigation into unrelated component
- **Waiting**: Blocks critical migration indefinitely
- **Alternative path**: Creates different ordering risk

**Trade-off**: 15 min manual deployment vs 4 hours debugging unrelated issue

---

### Choose FIX BLOCKER FIRST When

Any condition met:

1. **Blocker is security-related** (can't bypass safely)
   - Permission error, credential issue, IAM misconfiguration
   - SSL/TLS validation failure
   - Code injection vulnerability

2. **Change depends on blocker being fixed**
   - Your code calls the failing component
   - Schema migration required for your INSERT
   - Network access needed for your service call

3. **Blocker indicates systemic issue affecting your change**
   - All tests failing (infrastructure broken)
   - Network partition (can't reach any AWS service)
   - Credentials expired (blocking all deployments)

4. **Manual bypass introduces risk > cost of fixing**
   - Rebuilding artifact locally (bypasses quality gates)
   - Skipping essential validation (security scan, vulnerability check)
   - Breaking deployment order (code before schema migration)

5. **Root cause is simple and quick to fix**
   - Typo in env var name (5 min fix)
   - Missing import (1 min fix)
   - Obvious syntax error (2 min fix)

---

### Choose ALTERNATIVE PATH When

1. **Multiple independent work streams available**
   - Can work on different feature while blocker being fixed
   - Parallel tracks don't depend on each other

2. **Current path permanently blocked**
   - Blocker won't be fixed (deprecated component)
   - Alternative approach simpler

3. **Can parallelize**
   - Fix blocker + deploy via alternative simultaneously
   - No dependency between paths

---

## Manual Deployment Discipline

When bypassing pipeline, follow these rules to maintain safety:

### 1. Artifact Promotion (Not Rebuild)

**✅ CORRECT**:
```bash
# Use image built by CI/CD (Quality Gates passed)
ENV=dev doppler run -- aws lambda update-function-code \
  --function-name dr-daily-report-worker-dev \
  --image-uri 755283537543.dkr.ecr.us-east-1.amazonaws.com/dr:f51238b
  # ↑ Image digest traceable to commit SHA
  # ↑ Same image that passed Quality Gates
```

**❌ WRONG**:
```bash
# Ad-hoc local rebuild (bypasses quality gates)
docker build -t my-lambda .
docker tag my-lambda 755283537543.dkr.ecr.../dr:latest
docker push 755283537543.dkr.ecr.../dr:latest

# Problems:
# - No test execution (unit tests skipped)
# - Untraceable artifact (whose machine built this?)
# - Not validated (linting, type checking skipped)
# - Different dependencies (local venv vs CI/CD venv)
```

---

### 2. Traceability

Document 4 key facts:

```markdown
# Deployment Bypass: Migration Handler (Phase 1)

**Why blocked**: Schema validation blocked by unrelated Lambda (query_tool_handler)
**Why bypass safe**: Quality Gates passed, Docker image validated, backward compatible
**Artifact used**: 755283537543.dkr.ecr.us-east-1.amazonaws.com/dr:f51238b (from CI/CD)
**Follow-up**: GH-123 (Fix query_tool_handler import error)
```

**Purpose**: Future debugging ("why was this deployed manually?")

---

### 3. Same Validation Commands

Use AWS CLI waiters and smoke tests, just like CI/CD:

```bash
# 1. Update function code
aws lambda update-function-code \
  --function-name FUNCTION_NAME \
  --image-uri IMAGE_URI

# 2. Wait for update (don't assume immediate)
aws lambda wait function-updated \
  --function-name FUNCTION_NAME

# 3. Verify ground truth (image URI actually changed)
aws lambda get-function \
  --function-name FUNCTION_NAME \
  --query 'Code.ImageUri' --output text

# 4. Smoke test (invoke handler)
aws lambda invoke \
  --function-name FUNCTION_NAME \
  --payload '{"test": true}' \
  /tmp/response.json

# 5. Check logs (new code path executed)
aws logs filter-log-events \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --filter-pattern "NEW_FEATURE_LOG_MESSAGE" \
  --start-time $(date -u -d '1 minute ago' +%s)000
```

**Why**: Manual deployment should have same verification rigor as automated

---

### 4. Create Follow-Up Issue

**Don't forget the blocker**:

```markdown
# GitHub Issue: Fix query_tool_handler Import Error

**Problem**: Lambda fails to import `src.scheduler.query_tool_handler`

**Impact**: Blocks CI/CD schema validation

**Workaround**: Manual deployment bypasses validation (see commit f51238b)

**To Fix**:
1. Investigate import error (missing dependency? wrong path?)
2. Add test to prevent regression
3. Update schema validation to skip unrelated Lambdas

**Priority**: Medium (workaround exists, but blocks automation)
```

**Purpose**: Systemic improvement (fix root cause, not just bypass)

---

## Step-by-Step Decision Template

Use this when facing deployment blocker:

### Step 1: Classify Blocker

```markdown
- [ ] **Related**: Blocker caused by my change → MUST FIX
- [ ] **Unrelated**: Pre-existing or different component → CONSIDER BYPASS
- [ ] **Security**: Safety/permission issue → NEVER BYPASS
```

**How to determine**:
- Read error message (which file/component failing?)
- Check git diff (did I modify that file?)
- Check git log (when did this start failing?)

---

### Step 2: Assess Evidence Strength

Apply Principle #2 (Progressive Evidence Strengthening):

```markdown
- [ ] Layer 1 (Surface): Exit codes, status messages (weakest)
- [ ] Layer 2 (Content): Test results, build artifacts
- [ ] Layer 3 (Observability): Logs, metrics, traces
- [ ] Layer 4 (Ground Truth): Actual deployed behavior (strongest)
```

**Decision rule**: If Layer 2+ evidence strong, bypass is safe

**Example**:
- ✅ Layer 2: Quality Gates passed (18 tests green)
- ✅ Layer 3: Docker image built and tagged
- ❌ Layer 4: Deployment blocked (but blocker unrelated)

**Conclusion**: Layer 2-3 sufficient for manual deployment decision

---

### Step 3: Check Backward Compatibility

```markdown
- [ ] **Compatible**: Existing functionality unchanged → SAFE TO DEPLOY INDEPENDENTLY
- [ ] **Breaking**: Existing functionality affected → NEED COORDINATED DEPLOYMENT
- [ ] **Unknown**: Haven't tested → TEST FIRST
```

**How to verify**:
```bash
# Test existing code paths still work
pytest tests/ -k "test_existing_functionality"

# Check for breaking changes
git diff main..HEAD -- src/ | grep -E "^-.*def |^-.*class "

# Verify API contract unchanged
git diff main..HEAD -- src/types.py src/api/
```

**Pattern**: If new mode added, old mode still works → backward compatible

---

### Step 4: Choose Path

**Least Resistance (Bypass)**:
```
✅ Blocker unrelated
✅ Layer 2+ evidence strong
✅ Change backward compatible
✅ Manual bypass auditable (artifact promotion)
✅ Alternative paths higher cost

→ Execute manual deployment
```

**Fix Blocker First**:
```
✅ Blocker security-related
✅ Blocker affects my change
✅ Root cause simple/quick
✅ Manual bypass risky

→ Investigate and fix blocker
```

**Alternative Path**:
```
✅ Multiple work streams available
✅ Current path permanently blocked
✅ Can parallelize

→ Work on different feature while blocker being fixed
```

---

### Step 5: Document and Execute

**If bypassing**, create documentation:

```bash
# Create deployment record
cat > .claude/deployments/2026-01-03-manual-lambda-update.md << 'EOF'
# Manual Lambda Deployment: report_worker (Phase 1)

**Date**: 2026-01-03
**Commit**: f51238b
**Function**: dr-daily-report-worker-dev

## Why Manual Deployment

**Blocker**: Schema validation failed on unrelated Lambda (query_tool_handler)
**Error**: `Unable to import module 'src.scheduler.query_tool_handler'`

**Our change**: report_worker_handler.py (different Lambda)
**Blocker**: query_tool_handler.py (unrelated Lambda)

## Safety Evidence

- ✅ Quality Gates passed (18 tests green)
- ✅ Docker image validated
- ✅ Backward compatible (new mode added, SQS mode unaffected)
- ✅ Artifact promotion (not rebuild)

## Image Digest

`755283537543.dkr.ecr.us-east-1.amazonaws.com/dr-daily-report-lambda-dev:f51238b`

## Follow-Up

- [ ] GH-123: Fix query_tool_handler import error
- [ ] Refactor schema validation to skip unrelated Lambdas

EOF
```

**Execute deployment**:
```bash
# Use workflow from next section
./scripts/manual_lambda_deploy.sh report-worker f51238b
```

---

## Manual Lambda Deployment Workflow

Complete workflow for safe manual deployment:

### Prerequisites Checklist

```markdown
- [ ] Docker image built by CI/CD (not local build)
- [ ] Quality Gates passed (tests green)
- [ ] Image digest known (commit SHA or tag)
- [ ] Change is backward compatible
- [ ] Blocker documented
```

### Deployment Script

```bash
#!/bin/bash
# scripts/manual_lambda_deploy.sh
# Usage: ./manual_lambda_deploy.sh FUNCTION_NAME COMMIT_SHA

set -euo pipefail

FUNCTION_NAME=$1
COMMIT_SHA=$2
ENV=${ENV:-dev}

# ECR repository
REGISTRY="755283537543.dkr.ecr.us-east-1.amazonaws.com"
REPO="dr-daily-report-lambda-${ENV}"
IMAGE_URI="${REGISTRY}/${REPO}:${COMMIT_SHA}"

echo "======================================================"
echo "Manual Lambda Deployment: ${FUNCTION_NAME}"
echo "======================================================"
echo "Environment: ${ENV}"
echo "Commit SHA: ${COMMIT_SHA}"
echo "Image URI: ${IMAGE_URI}"
echo ""

# Step 1: Verify artifact exists in ECR
echo "Step 1: Verifying artifact exists in ECR..."
ENV=$ENV doppler run -- aws ecr describe-images \
  --repository-name $REPO \
  --image-ids imageTag=$COMMIT_SHA \
  --query 'imageDetails[0].imageTags' --output table

# Step 2: Update Lambda function code
echo ""
echo "Step 2: Updating Lambda function code..."
ENV=$ENV doppler run -- aws lambda update-function-code \
  --function-name dr-daily-report-${FUNCTION_NAME}-${ENV} \
  --image-uri $IMAGE_URI \
  --query 'FunctionName' --output text

# Step 3: Wait for update to complete
echo ""
echo "Step 3: Waiting for function update..."
ENV=$ENV doppler run -- aws lambda wait function-updated \
  --function-name dr-daily-report-${FUNCTION_NAME}-${ENV}

echo "✅ Function updated"

# Step 4: Verify ground truth (image URI changed)
echo ""
echo "Step 4: Verifying image URI updated..."
DEPLOYED_IMAGE=$(ENV=$ENV doppler run -- aws lambda get-function \
  --function-name dr-daily-report-${FUNCTION_NAME}-${ENV} \
  --query 'Code.ImageUri' --output text)

if [ "$DEPLOYED_IMAGE" = "$IMAGE_URI" ]; then
  echo "✅ Image URI matches: $DEPLOYED_IMAGE"
else
  echo "❌ Image URI mismatch!"
  echo "Expected: $IMAGE_URI"
  echo "Deployed: $DEPLOYED_IMAGE"
  exit 1
fi

# Step 5: Smoke test (invoke handler)
echo ""
echo "Step 5: Running smoke test..."
ENV=$ENV doppler run -- aws lambda invoke \
  --function-name dr-daily-report-${FUNCTION_NAME}-${ENV} \
  --payload '{"mode": "health_check"}' \
  /tmp/response.json

cat /tmp/response.json | jq .
rm /tmp/response.json

# Step 6: Check logs for new behavior
echo ""
echo "Step 6: Checking CloudWatch logs (last 2 minutes)..."
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-${FUNCTION_NAME}-${ENV} \
  --start-time $(($(date +%s) - 120))000 \
  --query 'events[*].message' --output text | tail -10

echo ""
echo "======================================================"
echo "✅ Manual deployment complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "1. Create follow-up issue to fix blocker"
echo "2. Document deployment in .claude/deployments/"
echo "3. Monitor CloudWatch logs for errors"
```

### Success Criteria

```markdown
- [ ] Image URI updated (verified via get-function)
- [ ] Function state = Active (not Pending/Failed)
- [ ] Smoke test passes (handler returns 200)
- [ ] Logs show new code path (expected log messages)
```

### Rollback Procedure

**If smoke test fails**:

```bash
#!/bin/bash
# Rollback to previous image

FUNCTION_NAME=$1
ENV=${ENV:-dev}

# Get previous commit SHA (from git log)
PREVIOUS_SHA=$(git log -2 --oneline | tail -1 | awk '{print $1}')

echo "Rolling back to: $PREVIOUS_SHA"

# Redeploy previous image
./scripts/manual_lambda_deploy.sh $FUNCTION_NAME $PREVIOUS_SHA
```

---

## Common Patterns

### Pattern 1: Circular Dependency (Validation → Deployment)

**Scenario**:
- Schema validation requires Lambda deployed (tests against Aurora)
- Lambda deployment requires schema validation passed (pipeline gate)
- **Result**: Circular dependency

**Resolution**:
1. Deploy Lambda manually (bypass schema validation)
2. Schema validation now passes (Lambda deployed)
3. Future deployments use automated pipeline

**Lesson**: Bootstrap manually, automate once working

---

### Pattern 2: Unrelated Component Failure

**Scenario**:
- Your PR: Update `report_worker.py`
- Pipeline error: Import error in `query_tool.py`
- **Result**: Unrelated failure blocks your deployment

**Resolution**:
1. Verify your changes safe (Quality Gates passed)
2. Deploy manually (bypass unrelated failure)
3. Create issue to fix `query_tool.py` separately

**Lesson**: Don't block working code for unrelated issues

---

### Pattern 3: Pre-Existing Failure

**Scenario**:
- Test has been failing for 3 days (not your change)
- Your PR introduces unrelated feature
- **Result**: Pipeline blocks your deployment

**Resolution**:
1. Verify test failure pre-dated your PR (git log)
2. Deploy manually (your changes validated independently)
3. Create issue to fix flaky test

**Lesson**: Flaky tests shouldn't block unrelated work

---

## Anti-Patterns

### ❌ Treating All Validation Gates as Equally Important

**Problem**: Some gates are critical (security scans), others informational (code coverage)

**Example**:
```
❌ Blocked deployment:
- Security scan: PASSED ✅
- Unit tests: PASSED ✅
- Integration tests: PASSED ✅
- Code coverage: 79.9% (threshold 80%) ❌

→ Deployment blocked by 0.1% coverage gap
→ Security validated, functionality validated
→ Blocking deployment for minor coverage delta
```

**Solution**: Classify gates by importance, allow bypass for non-critical

---

### ❌ Blocking All Work Until Perfect Pipeline

**Problem**: Pipeline will never be perfect, waiting indefinitely blocks progress

**Example**:
```
❌ "We can't deploy until we fix all flaky tests"
→ 3 weeks later, still fixing tests
→ Critical feature delayed
→ Customer blocked

✅ "We deploy with validated artifact, fix flaky tests separately"
→ Feature deployed in 1 day
→ Tests fixed over next 2 weeks
→ Customer unblocked
```

**Solution**: Deploy validated changes, fix pipeline separately

---

### ❌ Ad-Hoc Rebuilds Bypassing Quality Gates

**Problem**: Local builds skip linting, testing, validation

**Example**:
```bash
❌ WRONG:
# Build locally (no tests)
docker build -t my-lambda .

# Push to ECR (no validation)
docker push 755283537543.dkr.ecr.../dr:latest

# Deploy (untested code in production)
aws lambda update-function-code ...
```

**Solution**: Use artifact built by CI/CD (artifact promotion)

---

### ❌ Manual Deployments Without Traceability

**Problem**: Can't trace deployment to specific commit or validation run

**Example**:
```
❌ Slack: "I deployed the fix manually"
→ Which commit?
→ Which image digest?
→ Did it pass tests?
→ Who knows? 🤷

✅ Documented:
→ Commit f51238b
→ Image digest: 755...f51238b
→ Quality Gates: 18/18 passed
→ Deployed by: @user
→ Reason: Unrelated blocker (GH-123)
```

**Solution**: Document all manual deployments in `.claude/deployments/`

---

### ❌ Ignoring Blocker After Bypass

**Problem**: Blocker never gets fixed, technical debt accumulates

**Example**:
```
❌ Deploy manually, move on
→ Blocker still exists
→ Next developer hits same issue
→ Another manual deployment
→ Pattern repeats indefinitely

✅ Deploy manually + create issue
→ Blocker documented (GH-123)
→ Fixed in next sprint
→ Future deployments automated
```

**Solution**: Always create follow-up issue to fix blocker

---

## Real-World Example

### Step Functions → Lambda Migration (2026-01-03)

**Situation**:
- Migration code ready (Phase 1 complete)
- Quality Gates passed (18 tests green)
- Docker image built and validated
- **Blocked**: Schema validation failing on unrelated Lambda

**Decision Analysis**:

```markdown
Step 1: Classify blocker
✅ Unrelated (query_tool_handler, not report_worker)

Step 2: Evidence strength
✅ Layer 2: Quality Gates passed
✅ Layer 3: Docker image validated

Step 3: Backward compatibility
✅ New mode added, SQS mode unaffected

Step 4: Choose path
✅ All conditions for bypass met

Step 5: Execute
→ Manual Lambda deployment
→ Image: f51238b (from CI/CD)
→ Documented in .claude/deployments/
→ Follow-up: GH-123 (fix query_tool)
```

**Outcome**:
- Migration unblocked (15 min manual deployment)
- Avoided 4+ hours debugging unrelated Lambda
- Blocker fixed separately (next day)
- Future deployments automated

**Time saved**: 3.75 hours

---

## Integration with Other Principles

**Principle #2 (Progressive Evidence Strengthening)**:
- Use highest available evidence when ground truth blocked
- Layer 2-3 sufficient for bypass decision (don't need Layer 4)

**Principle #11 (Artifact Promotion)**:
- Manual deployment = artifact promotion with manual trigger
- Still uses validated artifact (not bypassing quality)

**Principle #19 (Cross-Boundary Contract Testing)**:
- Validate changes independently before bypassing
- Boundary tests prove change safe in isolation

**Principle #6 (Deployment Monitoring Discipline)**:
- Same waiters and smoke tests for manual deployment
- Verify through ground truth (don't assume success)

---

## When to Apply

✅ **When deployment blocked by unrelated validation**
- Schema validation tests different Lambda
- Flaky test failing (pre-existing issue)
- Circular dependency (validation needs deployed state)

✅ **When evidence shows change is safe**
- Quality Gates passed (tests green)
- Docker image validated
- Backward compatible

✅ **When manual bypass is auditable**
- Artifact built by CI/CD (not local rebuild)
- Traceable to commit SHA
- Documented deployment record

✅ **When alternative paths have high cost**
- Fixing blocker: Hours of investigation
- Waiting: Blocks critical work indefinitely

❌ **Never bypass when**:
- Blocker is security-related (permission error, vulnerability)
- Change depends on blocker being fixed (schema migration, dependency)
- Manual bypass introduces risk > cost of fixing
- No validated artifact available (only local build)

---

## Rationale

**Why systematic blocker resolution matters**:

Not all validation gates are equal. Some are critical (security scans, core functionality tests), others informational (code coverage, linting). Blocking all deployments for any gate failure creates:
- **Circular dependencies** (validation needs deployed state)
- **Unrelated blockers** (flaky tests in different component)
- **Progress paralysis** (waiting for perfect pipeline)

**Benefits of systematic approach**:
- Unblock critical work (deploy validated changes)
- Fix systemic issues separately (don't block on unrelated failures)
- Maintain safety (artifact promotion, documentation, smoke tests)
- Improve pipeline over time (identify and fix flaky tests)

**Key insight**: Deployment blocked ≠ Change is unsafe. When evidence shows change is safe (tests passed, backward compatible, auditable artifact), bypass blocker and fix it separately.

---

## See Also

- **Abstraction**: [Deployment Blocker Resolution](.claude/abstractions/decision-2026-01-03-deployment-blocker-resolution.md) - Complete decision pattern analysis
- **Skill**: [deployment](.claude/skills/deployment/) - Deployment workflows and verification
- **Checklist**: [lambda-deployment](.claude/checklists/lambda-deployment.md) - Deployment verification workflow
- **Guide**: [Multi-Environment Deployment](../deployment/MULTI_ENV.md) - Artifact promotion across environments

---

*Guide version: 2026-01-04*
*Principle: #21 in CLAUDE.md*
*Status: Graduated from decision pattern to principle to implementation guide*
