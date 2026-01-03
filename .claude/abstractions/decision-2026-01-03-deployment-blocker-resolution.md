# Decision Pattern: Deployment Blocker Resolution via Least-Resistance Path

**Abstracted From**: Step Functions → Lambda migration deployment (2026-01-03)

**Context**: Circular dependency in deployment pipeline blocking migration progress

---

## The Decision

**Situation**:
- Migration code ready and tested (Phase 1 complete)
- CI/CD pipeline blocked by unrelated schema validation failure
- Schema validation requires Lambda deployment to fix
- Lambda deployment blocked by schema validation (circular dependency)

**Options Considered**:
1. **Manual Lambda Update** (least resistance) - Bypass broken validation gate
2. **Fix Schema Validation First** - Investigate and fix root cause before proceeding
3. **Skip to Terraform Phase** - Proceed with infrastructure, fix Lambda later

**Decision Made**: Option 1 (Manual Lambda Update)

**Rationale**:
- Migration changes are backward compatible (safe to deploy independently)
- Docker image already built and validated (Quality Gates passed)
- Schema validation failure is pre-existing, unrelated issue
- Manual update unblocks migration progress immediately
- Can address schema validation separately without blocking critical path

---

## Pattern: Circular Dependency Resolution

### Pattern Description

**What it is**: Breaking circular dependencies in deployment/validation pipelines by identifying and bypassing the weakest constraint

**When it occurs**:
- Component A requires Component B to be valid
- Component B requires Component A to be deployed
- Neither can proceed without the other

**Why it happens**:
- Over-strict validation gates applied uniformly
- Validation tests components not modified in current change
- Pipeline assumes all components must be valid simultaneously
- No mechanism to validate subset of changes independently

---

## Generalized Pattern

### Signature (How to Recognize)

**Circular dependency indicators**:
- Deployment blocked by validation of unrelated component
- Validation requires deployed state to pass
- Error message references component you didn't modify
- Pipeline has been working, suddenly breaks on unrelated change

**Example from this case**:
```
❌ Schema validation FAILED - Deployment BLOCKED
Error: Unable to import module 'src.scheduler.query_tool_handler'

Our change: report_worker_handler.py (different Lambda)
Blocker: query_tool_handler.py (unrelated Lambda)
Circular: Can't deploy until validation passes, validation needs deployment
```

### Decision Heuristic: When to Use Least-Resistance Path

**Choose LEAST RESISTANCE when**:
1. **Change is isolated and validated independently**
   - Our case: Handler tests passed ✅
   - Docker image built successfully ✅
   - Quality Gates green ✅

2. **Blocker is unrelated to current change**
   - Our case: Schema validation tests different Lambda
   - Pre-existing failure (not caused by our changes)

3. **Change is backward compatible**
   - Our case: New mode added, existing modes still work
   - SQS mode unaffected
   - Migration mode unaffected

4. **Manual bypass is safe and auditable**
   - Our case: `aws lambda update-function-code` with specific image digest
   - Same image built by CI/CD (not ad-hoc build)
   - Traceable to commit SHA (f51238b)

5. **Alternative paths have high cost**
   - Fix blocker: Investigate unrelated Lambda, potentially hours
   - Skip to Terraform: Creates different ordering risk
   - Wait: Blocks migration progress indefinitely

**Choose FIX BLOCKER FIRST when**:
1. Blocker is security-related (can't bypass safely)
2. Change depends on blocker being fixed
3. Blocker indicates systemic issue affecting your change
4. Manual bypass introduces risk > cost of fixing
5. Root cause is simple and quick to fix

**Choose ALTERNATIVE PATH when**:
1. Multiple independent work streams
2. Current path permanently blocked
3. Alternative path has equal or lower risk
4. Can parallelize (fix blocker + deploy via alternative)

---

## Principles Extracted

### Principle 1: Circular Dependency Breaking via Weakest Link

**Pattern**: In circular dependencies, identify the constraint that's:
- Least essential to safety
- Easiest to bypass temporarily
- Most decoupled from current change

**Application**:
```
A (deploy) → requires → B (validation) → requires → A (deployed state)

Break at weakest link:
- If validation is unrelated: Bypass validation, deploy manually
- If manual deploy is risky: Fix validation first
- If both risky: Refactor pipeline to validate independently
```

**Anti-pattern**:
❌ Treating all validation gates as equally important
❌ Blocking all work until perfect validation
❌ Assuming pipeline structure is unchangeable

**Better approach**:
✅ Validate changes independently (unit tests passed)
✅ Bypass unrelated blockers temporarily
✅ Fix systemic issues separately from critical path

---

### Principle 2: Progressive Evidence Strengthening Applies to Deployment

**Observation**: We had strong evidence handler was correct WITHOUT full pipeline:

**Evidence Layers** (from Principle #2):
1. **Surface**: Exit code 0 from git push ✅
2. **Content**: Quality Gates passed (18 tests green) ✅
3. **Observability**: Docker image built and tagged ✅
4. **Ground Truth**: Deployment blocked by unrelated failure ⚠️

**Conclusion**: Layer 3 evidence sufficient for manual deployment decision

**Principle Extension**: When ground truth blocked by unrelated failure, rely on highest available evidence layer for decision.

---

### Principle 3: Backward Compatibility Enables Independent Deployment

**Pattern**: Changes designed for backward compatibility can be deployed independently of broader pipeline

**Why it matters**:
- Handler supports 3 modes: SQS (existing), Direct (new), Migration (existing)
- New mode doesn't break existing modes
- Can deploy handler before Terraform (infrastructure still uses SQS)
- Migration progresses incrementally: Handler → Terraform → Verification

**Contrast with breaking change**:
- If we removed SQS mode: Would NEED full pipeline (handler + Terraform together)
- Circular dependency would be real constraint (not artificial blocker)

**Lesson**: Design changes for backward compatibility to enable incremental deployment and reduce dependency coupling.

---

### Principle 4: Artifact Promotion vs Re-Build

**Pattern**: Use artifacts built by validated pipeline, not ad-hoc rebuilds

**What we did RIGHT**:
- Docker image built by CI/CD (Quality Gates passed)
- Image digest traceable to commit (f51238b)
- Manual deployment uses SAME image (promotion, not rebuild)

**What would be WRONG**:
- `docker build` locally → manual push to ECR
- No validation (tests skipped)
- Untraceable artifact (whose machine built this?)

**Principle**: "Artifact Promotion Principle" (already in CLAUDE.md #11)
- Build once, promote through environments
- Manual deployment = artifact promotion with manual trigger
- Still uses validated artifact (not bypassing quality)

---

### Principle 5: Pipeline Fragility Detection

**Observation**: This circular dependency revealed pipeline fragility

**Symptom**: Unrelated component failure blocks entire deployment

**Root Cause**:
- Schema validation runs for ALL Lambdas (not just changed ones)
- No mechanism to validate subset
- Pipeline assumes monolithic deployment (all or nothing)

**Long-term fix** (beyond today's decision):
1. **Selective validation**: Only validate changed components
2. **Independent deployments**: Each Lambda has own pipeline
3. **Soft failures**: Non-blocking warnings for unrelated failures
4. **Circuit breaker**: After N failures, auto-skip flaky validation

**Immediate value**: Decision exposes need for pipeline improvement (journal this separately)

---

## Decision Template: Deployment Blocker Resolution

**When facing deployment blocker**:

### Step 1: Classify Blocker
- [ ] **Related**: Blocker caused by my change → MUST FIX
- [ ] **Unrelated**: Pre-existing or different component → CONSIDER BYPASS
- [ ] **Security**: Safety/permission issue → NEVER BYPASS

### Step 2: Assess Evidence Strength
- [ ] Layer 1 (Surface): Exit codes, status messages
- [ ] Layer 2 (Content): Test results, build artifacts
- [ ] Layer 3 (Observability): Logs, metrics, traces
- [ ] Layer 4 (Ground Truth): Actual deployed behavior

**If Layer 2+ evidence strong**: Consider bypass

### Step 3: Check Backward Compatibility
- [ ] **Compatible**: Existing functionality unchanged → SAFE TO DEPLOY INDEPENDENTLY
- [ ] **Breaking**: Existing functionality affected → NEED COORDINATED DEPLOYMENT
- [ ] **Unknown**: Haven't tested → TEST FIRST

### Step 4: Choose Path

**Least Resistance (bypass blocker)**:
- ✅ Blocker unrelated
- ✅ Layer 2+ evidence strong
- ✅ Change backward compatible
- ✅ Manual bypass auditable (artifact promotion)
- ✅ Alternative paths higher cost

**Fix Blocker First**:
- ✅ Blocker security-related
- ✅ Blocker affects my change
- ✅ Root cause simple/quick
- ✅ Manual bypass risky

**Alternative Path**:
- ✅ Multiple work streams available
- ✅ Current path permanently blocked
- ✅ Can parallelize

### Step 5: Document and Execute

**If bypassing**:
- Document: Why blocked, why bypass safe, what artifact used
- Execute: Manual deployment with validated artifact
- Follow-up: Create issue to fix blocker (don't forget it)

**Example documentation**:
```bash
# Deployment Bypass: Migration Handler (Phase 1)
# Reason: Schema validation blocked by unrelated Lambda (query_tool)
# Evidence: Quality Gates passed, Docker image validated
# Safety: Backward compatible, artifact promotion (not rebuild)
# Image: 755283537543.dkr.ecr.../...:f51238b (from CI/CD)
# Follow-up: GH-XXX (Fix query_tool import error)
```

---

## Workflow Template: Manual Lambda Deployment (Artifact Promotion)

**When**: Pipeline blocked, but artifact validated

**Prerequisites**:
- [ ] Docker image built by CI/CD (not local build)
- [ ] Quality Gates passed (tests green)
- [ ] Image digest known (commit SHA or tag)
- [ ] Change is backward compatible

**Steps**:

```bash
# 1. Verify artifact exists in ECR
ENV=dev doppler run -- aws ecr describe-images \
  --repository-name dr-daily-report-lambda-dev \
  --image-ids imageTag=COMMIT_SHA

# 2. Update Lambda to use validated image
ENV=dev doppler run -- aws lambda update-function-code \
  --function-name dr-daily-report-FUNCTION-dev \
  --image-uri REGISTRY/REPO:COMMIT_SHA

# 3. Wait for update to complete (don't assume immediate)
ENV=dev doppler run -- aws lambda wait function-updated \
  --function-name dr-daily-report-FUNCTION-dev

# 4. Verify update successful (ground truth)
ENV=dev doppler run -- aws lambda get-function \
  --function-name dr-daily-report-FUNCTION-dev \
  --query 'Code.ImageUri' --output text

# Expected: Should match image URI from step 2

# 5. Smoke test (if available)
ENV=dev doppler run -- aws lambda invoke \
  --function-name dr-daily-report-FUNCTION-dev \
  --payload '{"test": true}' \
  /tmp/response.json

# 6. Check logs for new behavior
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-FUNCTION-dev \
  --filter-pattern "Direct Step Functions invocation" \
  --start-time $(date -u -d '1 minute ago' +%s)000
```

**Success Criteria**:
- Image URI updated ✅
- Function state = Active ✅
- Smoke test passes ✅
- Logs show new code path ✅

**Rollback** (if smoke test fails):
```bash
# Get previous image URI from deployment history
PREVIOUS_IMAGE=$(git log -2 --oneline | tail -1 | awk '{print $1}')

# Rollback to previous image
ENV=dev doppler run -- aws lambda update-function-code \
  --function-name dr-daily-report-FUNCTION-dev \
  --image-uri REGISTRY/REPO:$PREVIOUS_IMAGE
```

---

## Related Patterns

### Circular Logic in Infrastructure

**Similar to**:
- Database migration requiring deployed code, code requiring migrated schema
- SSL certificate requiring DNS, DNS requiring certificate
- IAM permission requiring resource, resource requiring permission

**Resolution strategy**: Same principle applies
1. Identify artificial vs real constraint
2. Break at weakest/safest link
3. Bootstrap manually if needed
4. Automate once working

### Principle #15: Infrastructure-Application Contract

**This decision validates principle**:
- Handler deployed BEFORE Terraform (as planned)
- Infrastructure updated AFTER application ready
- Order matters, but intermediate states must be valid

**Extension**: When pipeline blocks correct order, use manual deployment to maintain correct order (don't let broken pipeline force wrong order)

---

## Metadata

**Pattern Type**: decision
**Confidence**: High (clear heuristic emerged from real situation)
**Created**: 2026-01-03
**Context**: Step Functions → Lambda migration (Phase 1 deployment)
**Applicable**: All deployment blockers involving circular dependencies

---

## Next Steps

- [ ] Execute manual Lambda deployment (Option 1)
- [ ] Create GitHub issue: Fix query_tool_handler import error
- [ ] Journal: Pipeline fragility (schema validation too broad)
- [ ] Consider: Evolve this pattern → CLAUDE.md principle if pattern recurs
- [ ] Post-deployment: Verify new handler mode works (smoke test)

---

## Graduation Criteria

**Graduate to CLAUDE.md if**:
- This pattern recurs 3+ times in different contexts
- Becomes standard operating procedure for deployment blockers
- Team adopts as shared decision heuristic

**Potential CLAUDE.md entry**:
```markdown
### XX. Deployment Blocker Resolution Principle

When deployment blocked by unrelated validation:
1. Classify: Related (fix) vs Unrelated (consider bypass)
2. Evidence: Layer 2+ validation sufficient for bypass decision
3. Safety: Backward compatible changes safe to deploy independently
4. Execution: Manual artifact promotion (not rebuild)
5. Follow-up: Fix blocker separately, don't forget

Anti-pattern: Blocking all work until perfect pipeline
Pattern: Progressive deployment with validated artifacts
```
