# Deployment Principles Cluster

**Load when**: Deploying to any environment, CI/CD work, releases, rollbacks, Lambda updates

**Principles**: #6, #11, #15, #19, #21

**Related skills**: [deployment](.claude/skills/deployment/), [testing-workflow](.claude/skills/testing-workflow/)

---

## Principle #6: Deployment Monitoring Discipline

Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. Apply Progressive Evidence Strengthening (Principle #2): verify status code + payload + logs + actual behavior. Validate infrastructure-deployment contract before deploying.

**Rollback triggers**: Post-deployment smoke test fails, CloudWatch shows only START/END logs (startup crash), error rate exceeds baseline (>5% in first 5 minutes), ground truth verification fails.

**Anti-pattern**: Assuming deployment succeeded because process exit code = 0. Exit code is weakest evidence.

See [deployment skill](../.claude/skills/deployment/) for rollback execution workflow, verification checklists, and manual deployment procedures.

---

## Principle #11: Artifact Promotion Principle

Build once, promote same immutable Docker image through all environments (dev → staging → prod). What you test in staging is exactly what deploys to production. Use immutable image digests, not tags. Verify all environments use identical digest.

**Key insight**: Rebuild = risk. Same artifact = confidence.

See [deployment skill MULTI_ENV](../skills/deployment/MULTI_ENV.md) and [docs/deployment/MULTI_ENV.md](../../docs/deployment/MULTI_ENV.md).

---

## Principle #15: Infrastructure-Application Contract

Maintain contract between application code (`src/`), infrastructure (`terraform/`), and principles. Code deployed without matching infrastructure causes silent failures hours after deployment.

**Deployment order**: Update code → Create migration → Update Terraform → Update Doppler → Deploy migration FIRST → Deploy code → Verify ground truth.

**Startup validation**: Validate required env vars at Lambda startup (fail fast). No silent fallbacks.

**Common failures**: Missing env var, schema not migrated before code, copy-paste inheritance.

See [Infrastructure-Application Contract Guide](../../docs/guides/infrastructure-application-contract.md) for deployment order, schema migration checklist, startup validation patterns, VPC endpoint verification, NAT Gateway saturation patterns, and real failure instances.

---

## Principle #19: Cross-Boundary Contract Testing (Deployment Context)

Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary.

**Deployment-specific boundaries**:
- **Phase boundary**: Build → Runtime (Docker container import tests)
- **Service boundary**: API Gateway → Lambda (event structure validation)
- **Configuration boundary**: Terraform → Lambda (env var verification)

**When to apply for deployments**:
- Before deployment: Test Docker container imports
- After deployment: Verify Lambda responds correctly
- Fresh deployment: Test cold start without cached state

See [Cross-Boundary Contract Testing Guide](../../docs/guides/cross-boundary-contract-testing.md).

---

## Principle #21: Deployment Blocker Resolution

When deployment blocked by validation failures or pipeline issues, apply systematic heuristic to choose resolution path. Not all blockers require fixing—some can be safely bypassed when evidence supports safety.

**Choose LEAST RESISTANCE (bypass)** when: (1) Change validated independently, (2) Blocker unrelated to change, (3) Change backward compatible, (4) Manual bypass auditable (artifact promotion), (5) Alternative paths high cost.

**Choose FIX BLOCKER FIRST** when: Security-related, change depends on fix, systemic issue, manual bypass risky, or root cause quick to fix.

**Manual deployment discipline**: Artifact promotion (not rebuild), traceable to commit SHA, document why/what/follow-up, use same validation as CI/CD (waiters, smoke tests), create issue to fix blocker separately.

See [Deployment Blocker Resolution Guide](../../docs/guides/deployment-blocker-resolution.md).

---

## Quick Checklist

Before deployment:
- [ ] Artifact built and tested in dev
- [ ] Infrastructure contract validated (Terraform matches code needs)
- [ ] Migrations run BEFORE code deployment
- [ ] Docker container import tests pass
- [ ] State invariants documented
- [ ] File permissions correct (644 for .py files) - `find src/ -name "*.py" -perm 600`

After deployment:
- [ ] AWS CLI waiter confirms function updated
- [ ] Smoke test passes
- [ ] CloudWatch logs show application logs (not just START/END)
- [ ] Ground truth verified (actual user flow works)

**Post-Deployment Invariant Verification (MANDATORY for workflows)**:
- [ ] Run `/invariant "affected workflow"` immediately after deploy
- [ ] Verify Lambda logs show successful imports (no PermissionError, ImportError)
- [ ] Verify Aurora tables have expected data (Layer 4 ground truth)
- [ ] Test each Lambda independently, not just via workflow orchestrator
- [ ] Verify scheduled runs will work tomorrow (temporal invariant)

---

## Anti-Pattern: Victory Declaration on Weak Evidence

**What happened** (2026-01-16 incident):
- Deployed parallel workflow to Step Functions
- Test execution showed "SUCCEEDED"
- Declared task complete
- Next day: No data populated, users saw empty responses

**Root cause**:
- report_worker Lambda crashed on import (PermissionError: file permissions 600)
- Step Functions reported "SUCCEEDED" because Catch handlers existed
- Stopped at Layer 1 evidence (status code) without checking Layer 3 (logs) or Layer 4 (data)

**Lesson learned**:
> "SUCCEEDED" status ≠ "Workers ran correctly" ≠ "Data populated"

**Prevention**:
1. After workflow deployment, always check worker Lambda logs independently
2. Verify ground truth (Aurora data) before declaring success
3. Run `/invariant` to systematically check all 5 levels

---

## Environment Parity Verification

**File permissions**: Docker COPY preserves source file permissions. If files have 600 (owner-only) permissions locally, Lambda runtime cannot read them.

**Check before deployment**:
```bash
# Find Python files with restrictive permissions
find src/ -name "*.py" -perm 600 -ls

# Fix if any found
find src/ -name "*.py" -perm 600 -exec chmod 644 {} \;
```

**Add to pre-commit hook** (recommended):
```bash
# .git/hooks/pre-commit
if find src/ -name "*.py" -perm 600 | grep -q .; then
  echo "ERROR: Python files with 600 permissions found"
  find src/ -name "*.py" -perm 600 -ls
  exit 1
fi
```

---

*Cluster: deployment-principles*
*Last updated: 2026-01-17*
