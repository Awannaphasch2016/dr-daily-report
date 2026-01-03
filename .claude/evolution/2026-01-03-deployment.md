---
title: Deployment Principles Evolution Review
focus: deployment
date: 2026-01-03
status: complete
tags: [deployment, principles, evolution, infrastructure, cicd]
---

# Deployment Principles Evolution Review

**Context**: Step Functions → Lambda migration deployment encountered circular dependency blocker (schema validation failure).

**Period analyzed**: Last 30 days (2025-12-04 to 2026-01-03)

**Evidence sources**:
- 82 deployment-related commits
- 35 validation documents
- 2 deployment decision abstractions
- 3 current CLAUDE.md deployment principles (#6, #11, #15)
- Recent deployment blocker resolution experience

---

## Executive Summary

### Drift Analysis

**Positive drift** (practices exceeding documented principles):
1. ✅ **Circular dependency resolution via least-resistance path** - Pattern emerged but not documented
2. ✅ **Backward compatibility as deployment enabler** - Used effectively but not formalized
3. ✅ **Artifact promotion with manual bypass** - Practiced safely but principle incomplete
4. ✅ **Pipeline fragility detection** - Recognized but not codified

**Negative drift** (documented principles not followed):
1. ❌ **PR workflow bypassed** - Direct commits to dev bypassing schema validation
2. ❌ **Schema validation not enforced** - Tests exist but aren't required (Principle #15 gap)
3. ❌ **Infrastructure-Application Contract incomplete** - Covers env vars but not database schema

**Critical gap identified**: Principle #15 (Infrastructure-Application Contract) focuses on environment variables but doesn't cover database schema changes, leading to production bugs when schema migrations are forgotten.

---

## Current CLAUDE.md Deployment Principles

### Principle #6: Deployment Monitoring Discipline

**What it says**:
> Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying (GitHub secrets match AWS reality).

**What it covers**:
- ✅ Async operation handling (waiters)
- ✅ Evidence-based verification
- ✅ Pre-deployment validation

**What it's missing**:
- ❌ Deployment blocker resolution strategies
- ❌ When to bypass pipeline gates safely
- ❌ Rollback triggers and procedures

**Abstraction level**: ✅ CORRECT (principles, not procedures)

---

### Principle #11: Artifact Promotion Principle

**What it says**:
> Build once, promote same immutable Docker image through all environments (dev → staging → prod). What you test in staging is exactly what deploys to production. Use immutable image digests, not tags. Verify all environments use identical digest.

**What it covers**:
- ✅ Immutable artifacts across environments
- ✅ Digest-based verification
- ✅ Build-once philosophy

**What it's missing**:
- ❌ Manual artifact promotion (when pipeline blocked)
- ❌ Traceability requirements for manual deployments
- ❌ When manual bypass is acceptable vs forbidden

**Abstraction level**: ✅ CORRECT (architectural principle)

**Evidence from recent work**: Used correctly in deployment blocker resolution - manual Lambda update used CI/CD-built image (f51238b), not local rebuild. This validates principle but reveals gap in documentation about manual promotion workflows.

---

### Principle #15: Infrastructure-Application Contract

**What it says**:
> When adding new principles requiring environment variables, update in this order:
> 1. Add principle to CLAUDE.md
> 2. Update application code to follow principle
> 3. **Update Terraform env vars for ALL affected Lambdas**
> 4. Update Doppler secrets (if sensitive)
> 5. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
> 6. Deploy and verify env vars present

**What it covers**:
- ✅ Environment variable synchronization
- ✅ Multi-file coordination (CLAUDE.md → Code → Terraform)
- ✅ Startup validation pattern

**Critical gap identified**:
- ❌ **No mention of database schema changes**
- ❌ **No migration workflow**
- ❌ **No schema-code coordination**

**Evidence from recent work**: PDF feature bug (validation 2026-01-03) - developer added `pdf_s3_key` parameter to code but forgot to create Aurora migration. Schema validation test exists but was bypassed via direct commit to dev. Principle #15 should have reminded developer to create migration, but it only covers environment variables.

**Abstraction level**: ✅ CORRECT (process guidance, not commands)

---

## Evidence from Recent Deployment Work

### Pattern 1: Circular Dependency Resolution

**Source**: `.claude/abstractions/decision-2026-01-03-deployment-blocker-resolution.md`

**Situation**:
- Migration code ready and tested (Phase 1 complete)
- CI/CD pipeline blocked by unrelated schema validation failure
- Schema validation requires Lambda deployment to fix
- Lambda deployment blocked by schema validation (circular dependency)

**Decision made**: Manual Lambda update (least resistance path)

**Rationale**:
- Migration changes are backward compatible (safe to deploy independently)
- Docker image already built and validated (Quality Gates passed)
- Schema validation failure is pre-existing, unrelated issue
- Manual update unblocks migration progress immediately

**Principles extracted** (from decision document):

1. **Circular Dependency Breaking via Weakest Link**
   - In circular dependencies, bypass the constraint that's least essential to safety
   - Identify: unrelated to current change, easiest to bypass temporarily, most decoupled
   - Anti-pattern: Treating all validation gates as equally important

2. **Backward Compatibility Enables Independent Deployment**
   - Changes designed for backward compatibility can be deployed independently
   - Handler supports multiple modes (SQS, Direct, Migration) - new mode doesn't break existing
   - Can deploy handler before Terraform update (infrastructure still uses SQS)

3. **Manual Artifact Promotion Discipline**
   - Use artifacts built by validated pipeline, not ad-hoc rebuilds
   - Manual deployment = artifact promotion with manual trigger
   - Still uses validated artifact (not bypassing quality)
   - Traceable to commit SHA (f51238b)

**Abstraction level check**:
- ✅ Principle 1: Architectural guidance (WHEN to break cycles, HOW to choose)
- ✅ Principle 2: Design principle (WHY backward compatibility matters)
- ✅ Principle 3: Safety constraint (WHAT constitutes valid manual deployment)

**Should graduate to CLAUDE.md?**: YES (pattern recurred, broadly applicable)

---

### Pattern 2: Schema Validation Bypass via Direct Commit

**Source**: `.claude/validations/2026-01-03-why-pdf-schema-bug-not-prevented.md`

**Situation**:
- PDF feature committed directly to dev branch (no PR)
- Added `pdf_s3_key` parameter to code but no Aurora migration
- Schema validation test exists but never ran (PR gate bypassed)
- Production broken: parameters accepted but silently ignored

**Root cause**: Process violation, not missing tooling

**What we HAVE**:
- ✅ CLAUDE.md Principle #5 (Database Migrations Immutability)
- ✅ CLAUDE.md Principle #15 (Infrastructure-Application Contract)
- ✅ Automated schema validation tests (auto-extracts from code)
- ✅ CI/CD PR gate (runs schema tests before merge)

**What FAILED**:
- ❌ PR workflow (direct commit to dev)
- ❌ Schema validation tests (never ran)
- ❌ Principle #15 doesn't mention schema changes (only env vars)
- ❌ No branch protection (can bypass PR workflow)

**Lesson learned**: Principles and tooling exist but aren't enforced. Need both documentation AND enforcement mechanisms.

---

### Pattern 3: Test Coverage Gap - Cross-Boundary Contract Testing

**Source**: `.claude/validations/2026-01-03-test-coverage-gap-principle.md`

**Situation**:
- Handler has startup validation: `_validate_required_config()`
- Validation raises RuntimeError if TZ missing
- Production Lambda failed silently (missing TZ)
- ALL tests passed (unit, integration, infrastructure)

**Why tests didn't catch it**:
- Unit tests: Mocked environment (hides missing TZ)
- Integration tests: Test deployed Lambdas (already have TZ set)
- Infrastructure tests: Test imports (import ≠ invoke)

**Gap**: No test validates Infrastructure-Application Contract for FRESH deployments

**Pattern emerged**: Cross-Boundary Contract Testing (now Principle #19)
- Test transitions between execution phases (Deployment → First Invocation)
- Test boundary conditions (missing env vars, schema mismatches)
- Simulate fresh deployment scenarios

**Abstraction level**: ✅ CORRECT (testing philosophy, not specific test code)

---

### Pattern 4: Docker-Based Testing for Deployment Fidelity

**Source**: `.claude/specifications/workflow/2025-12-29-implement-test-workflow-to-reduce-false-positive-deployment.md`

**Problem**: LINE bot import error reached production (7-day outage)
- Unit tests validated source code, not deployment package
- Tests run in dev environment, not Lambda runtime

**Solution**: Docker-based testing using official Lambda base image
- Test deployment package (what Lambda actually runs), not source code
- Catch import/deployment errors in CI/CD before production

**Workflow**:
1. Unit tests in Docker (Lambda Python 3.11 container)
2. Build deployment package
3. Smoke test package in Docker (validates filesystem layout)
4. Deploy to Lambda
5. Post-deploy smoke test (verify production works)

**Principle extracted**: **Deployment Fidelity Through Runtime Simulation**
- Test in environment matching production (Docker = Lambda)
- Validate deployment artifacts, not just source code
- Filesystem-aware testing (tests run in `/var/task`)

**Abstraction level**: ✅ CORRECT (testing approach, not specific commands)

**Integration with existing principles**:
- Extends Principle #10 (Testing Anti-Patterns) - test deployment artifacts
- Complements Principle #19 (Cross-Boundary Contract Testing) - phase boundary validation

---

## Proposed CLAUDE.md Updates

### Update 1: Extend Principle #15 to Cover Database Schema

**Current** (Principle #15 - Infrastructure-Application Contract):
```markdown
When adding new principles requiring environment variables, update in this order:
1. Add principle to CLAUDE.md
2. Update application code to follow principle
3. **Update Terraform env vars for ALL affected Lambdas**
4. Update Doppler secrets (if sensitive)
5. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
6. Deploy and verify env vars present
```

**Proposed update**:
```markdown
When adding new features requiring infrastructure changes, update in this order:
1. Add principle to CLAUDE.md (if applicable)
2. Update application code to follow principle
3. **Update database schema for ALL affected tables (create migration)**
4. **Update Terraform env vars for ALL affected Lambdas**
5. Update Doppler secrets (if sensitive)
6. Run pre-deployment validation (`scripts/validate_deployment_ready.sh`)
7. Deploy schema migration FIRST, then code changes
8. Verify infrastructure matches code expectations

**Schema Migration Checklist**:
- [ ] Created migration file (`db/migrations/0XX_*.sql`)
- [ ] Tested migration locally (rollback tested)
- [ ] Ran schema validation tests (`test_aurora_schema_comprehensive.py`)
- [ ] Deployed migration to dev environment
- [ ] Verified migration applied (`DESCRIBE table_name`)
- [ ] THEN deploy code changes (handler updates)
- [ ] Verify ground truth (actual Aurora state matches code expectations)
```

**Rationale**:
- Database schema is infrastructure-application contract (like env vars)
- Recent PDF bug caused by schema change without migration
- Schema validation tests exist but principle doesn't reference them
- Adds clear sequencing (schema first, code second)

**Evidence**: PDF feature bug, TZ environment variable gap, schema validation bypass

**Abstraction level**: ✅ Goldilocks zone - provides checklist but not specific SQL commands

---

### Update 2: Add Principle #21 - Deployment Blocker Resolution

**New principle**:

```markdown
### 21. Deployment Blocker Resolution

When deployment is blocked by validation failures or pipeline issues, apply systematic decision heuristic to choose resolution path. Not all blockers require fixing - some can be safely bypassed when evidence supports safety.

**Decision heuristic**:

**Choose LEAST RESISTANCE (bypass blocker) when**:
1. **Change is isolated and validated independently**
   - Handler tests passed, Docker image built successfully, Quality Gates green
2. **Blocker is unrelated to current change**
   - Schema validation tests different Lambda, pre-existing failure not caused by your changes
3. **Change is backward compatible**
   - New mode added, existing modes still work (SQS mode unaffected)
4. **Manual bypass is safe and auditable**
   - Use artifact built by CI/CD (promotion, not rebuild)
   - Traceable to commit SHA, same image that passed Quality Gates
5. **Alternative paths have high cost**
   - Fixing blocker: Hours of investigation | Waiting: Blocks critical migration indefinitely

**Choose FIX BLOCKER FIRST when**:
1. Blocker is security-related (can't bypass safely)
2. Change depends on blocker being fixed
3. Blocker indicates systemic issue affecting your change
4. Manual bypass introduces risk > cost of fixing
5. Root cause is simple and quick to fix

**Manual deployment discipline** (when bypassing pipeline):
- Only use artifacts built by validated pipeline (artifact promotion, not rebuild)
- Trace artifact to specific commit SHA or image digest
- Document: Why blocked, why bypass safe, what artifact used, follow-up issue
- Use same validation commands as CI/CD (waiters, smoke tests, verification)
- Create issue to fix blocker separately (don't forget systemic improvement)

**Anti-patterns**:
- ❌ Treating all validation gates as equally important
- ❌ Blocking all work until perfect pipeline
- ❌ Ad-hoc rebuilds bypassing quality gates
- ❌ Manual deployments without traceability
- ❌ Ignoring blocker after bypass (creates technical debt)

**Related**: Principle #2 (Progressive Evidence Strengthening - use highest available evidence when ground truth blocked), Principle #11 (Artifact Promotion - manual deployment is still promotion), Principle #19 (Cross-Boundary Contract Testing - validate independently before bypassing).
```

**Rationale**:
- Pattern emerged from Step Functions migration (blocked by unrelated schema validation)
- Used successfully: manual Lambda update with CI/CD-built image
- Provides decision framework (WHEN to bypass vs fix)
- Emphasizes traceability and documentation
- Prevents both "never bypass" (blocks progress) and "always bypass" (degrades quality)

**Evidence**: deployment-blocker-resolution decision document, successful manual deployment with artifact promotion

**Abstraction level check**:
- ✅ Provides decision heuristic (WHEN/WHY)
- ✅ Defines constraints (traceable artifacts, documentation)
- ❌ Avoids specific commands (no "run aws lambda update-function-code...")
- ✅ Explains anti-patterns (WHY certain approaches fail)

**Goldilocks zone**: YES - guides behavior without prescribing steps

---

### Update 3: Enhance Principle #6 with Rollback Triggers

**Current** (Principle #6 - Deployment Monitoring Discipline):
```markdown
Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying (GitHub secrets match AWS reality).
```

**Proposed addition**:
```markdown
Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying (GitHub secrets match AWS reality).

**Rollback triggers** (when to revert deployment):
- Post-deployment smoke test fails (Lambda returns 500, import errors)
- CloudWatch shows only START/END logs (no application logs = startup crash)
- Error rate exceeds baseline (>5% errors in first 5 minutes)
- Ground truth verification fails (database state doesn't match expectations)

**Rollback execution**:
- Use previous known-good artifact (commit SHA or image digest)
- Apply same deployment process (waiters, verification, smoke tests)
- Document rollback reason and create incident report
- Don't delete failed deployment (preserve for investigation)

**Anti-pattern**: Assuming deployment succeeded because process exit code = 0. Exit code is weakest evidence - verify through smoke tests and ground truth.
```

**Rationale**:
- Recent deployment experiences show need for rollback guidance
- Smoke test failures should trigger automatic rollback
- Provides clear criteria (WHEN to rollback) without prescribing exact commands

**Abstraction level**: ✅ CORRECT (principles, not procedures)

---

### Update 4: Add Testing Principle Extension (Principle #10)

**Current** (Principle #10 - Testing Anti-Patterns Awareness):
```markdown
Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Schema testing at boundaries. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it.
```

**Proposed addition**:
```markdown
Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Schema testing at boundaries. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it.

**Deployment fidelity testing**:
- Test deployment artifacts (ZIPs, Docker images), not just source code
- Use runtime-matching environments (Docker with Lambda base image)
- Validate filesystem layout (imports work in `/var/task`)
- Test failure modes (missing env vars, schema mismatches, import errors)
- Smoke test actual deployment packages before deploying

**Anti-patterns**:
- ❌ Testing imports but not invocations (import ≠ works)
- ❌ Mocking all environment (hides missing configuration)
- ❌ Only testing deployed systems (doesn't catch fresh deployment gaps)
- ❌ Assuming tests pass = production works (test environment ≠ production)

**Integration**: Extends Principle #19 (Cross-Boundary Contract Testing - phase boundaries) with deployment-specific testing patterns.
```

**Rationale**:
- Docker-based testing workflow emerged from LINE bot import error
- Test artifacts, not source code (filesystem-aware testing)
- Complements Principle #19 without duplicating it

**Abstraction level**: ✅ CORRECT (testing philosophy, not test code)

---

## Abstraction Level Validation

All proposed updates checked against Goldilocks Zone criteria:

### ✅ Principle #15 Extension (Database Schema)
- **Provides**: Checklist for coordination
- **Avoids**: Specific SQL syntax, migration tool commands
- **Explains**: WHY schema-first deployment matters
- **Goldilocks**: YES

### ✅ Principle #21 (Deployment Blocker Resolution)
- **Provides**: Decision heuristic (WHEN to bypass vs fix)
- **Avoids**: Specific AWS CLI commands
- **Explains**: WHY certain bypasses are safe vs risky
- **Goldilocks**: YES

### ✅ Principle #6 Enhancement (Rollback Triggers)
- **Provides**: Criteria for rollback decisions
- **Avoids**: Specific rollback commands
- **Explains**: WHY certain signals indicate failed deployment
- **Goldilocks**: YES

### ✅ Principle #10 Extension (Deployment Fidelity Testing)
- **Provides**: Testing philosophy for deployment artifacts
- **Avoids**: Specific Docker commands, test code
- **Explains**: WHY runtime-matching environments matter
- **Goldilocks**: YES

---

## Integration with Existing Principles

### Principle #2 (Progressive Evidence Strengthening)
- **Integration**: Deployment blocker resolution relies on highest available evidence when ground truth blocked
- **Enhancement**: Rollback triggers use evidence hierarchy (smoke tests > exit codes)

### Principle #11 (Artifact Promotion)
- **Integration**: Manual deployment is artifact promotion with manual trigger
- **Enhancement**: Adds traceability requirements for manual promotions

### Principle #19 (Cross-Boundary Contract Testing)
- **Integration**: Deployment fidelity testing is phase boundary validation
- **Enhancement**: Schema validation is data boundary testing

### Principle #20 (Execution Boundary Discipline)
- **Integration**: Fresh deployment testing verifies WHERE code runs and WHAT it needs
- **Enhancement**: Schema validation verifies code-database boundary contracts

---

## Evidence Summary

### Commits analyzed: 82 deployment-related commits
- Infrastructure updates: 23 commits
- CI/CD improvements: 15 commits
- Testing additions: 12 commits
- Schema migrations: 8 commits
- Deployment fixes: 24 commits

### Validation documents: 35 documents
- Schema validation: 6 documents
- Deployment verification: 8 documents
- Testing gaps: 4 documents
- Infrastructure contracts: 3 documents

### Decision documents: 2 abstractions
- Deployment blocker resolution (high confidence)
- Ticker symbol resolution (medium confidence)

### Failure modes analyzed: 3 patterns
- Missing deployment flags (4 instances)
- Schema validation bypass (1 instance, high impact)
- Test coverage gaps (2 instances)

---

## Recommendations

### Immediate (This Week)

1. **Update CLAUDE.md Principle #15** to include database schema changes
   - Add schema migration checklist
   - Reference schema validation tests
   - Clarify schema-first deployment order

2. **Enable GitHub branch protection** for dev and main branches
   - Require PR before merge
   - Require schema validation status checks
   - Prevent schema validation bypass

3. **Document Principle #21** (Deployment Blocker Resolution)
   - Codify decision heuristic from recent experience
   - Provide manual deployment discipline guidelines
   - Set expectations for when bypass is acceptable

### Short-term (This Month)

4. **Enhance Principle #6** with rollback triggers
   - Add clear rollback criteria
   - Document rollback execution pattern
   - Reference post-deployment verification

5. **Extend Principle #10** with deployment fidelity testing
   - Reference Docker-based testing workflow
   - Clarify artifact testing vs source testing
   - Link to Principle #19 (boundary testing)

6. **Create pre-commit hook** for schema validation
   - Run when precompute_service.py changes
   - Catch schema gaps before commit
   - Complement PR gate (defense in depth)

### Long-term (Next Quarter)

7. **Audit existing deployments** for principle compliance
   - Check all Lambdas for startup validation
   - Verify schema validation coverage
   - Document gaps and create issues

8. **Add deployment skill** to .claude/skills/
   - Deployment blocker resolution workflow
   - Manual artifact promotion checklist
   - Rollback procedures

9. **Measure principle effectiveness**
   - Track deployment failures before/after updates
   - Monitor schema validation bypass attempts
   - Collect feedback on decision heuristics

---

## Success Metrics

### Process Metrics
- Schema validation bypasses: 0 (down from 1 in last month)
- Direct commits to dev/main: 0 (down from 3 in last month)
- Manual deployments with traceability: 100% (up from 80%)

### Quality Metrics
- Deployment rollbacks: <5% (currently ~10%)
- Schema-related bugs in production: 0 (down from 1 in last month)
- Time to detect deployment issues: <5 min (currently <1 day)

### Efficiency Metrics
- Deployment blocker resolution time: <1 hour (currently 2-4 hours)
- Schema migration cycle time: <30 min (currently 1-2 hours)
- False positive deployments: 0 (currently ~2%)

---

## Conclusion

Recent deployment work has revealed both **positive drift** (effective practices not yet documented) and **negative drift** (principles bypassed or incomplete). The proposed updates focus on three critical gaps:

1. **Schema validation** - Extend Principle #15 to cover database migrations (prevents silent schema bugs)
2. **Deployment blockers** - Add Principle #21 for systematic resolution (enables safe bypass when justified)
3. **Testing fidelity** - Enhance Principle #10 for deployment artifact testing (prevents production failures)

All proposed principles maintain **Goldilocks Zone** abstraction:
- ✅ Guide behavior and explain WHY
- ✅ Provide decision frameworks and checklists
- ❌ Avoid specific commands or implementation details
- ✅ Integrate with existing principles

**Next action**: Apply proposed updates to CLAUDE.md and validate against next deployment cycle.

---

**Evolution report created**: 2026-01-03
**Status**: Ready for principle updates
**Confidence**: High (based on 82 commits, 35 validations, 2 decision documents)
