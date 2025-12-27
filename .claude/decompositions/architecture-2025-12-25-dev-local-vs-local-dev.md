---
title: "Architecture Decision: dev_local vs local_dev"
type: architecture
date: 2025-12-25
depth: deep
status: analysis
tags: [doppler, secrets-management, architecture-decision, config-inheritance]
---

# Decomposition: dev_local vs local_dev

**Decision**: Choose between two Doppler config approaches for local development
**Depth**: Deep
**Date**: 2025-12-25

---

## Context

Two Doppler configs exist for local development in the `rag-chatbot-worktree` project:

1. **`dev_local`** (OLD) - Created 2025-12-16, in `dev` environment, no inheritance
2. **`local_dev`** (NEW) - Created 2025-12-25, in `local` environment, inherits from `dev`

Need to understand the architectural trade-offs and choose one approach.

---

## Configuration Comparison

### dev_local (OLD)

**Metadata**:
- **Name**: `dev_local`
- **Environment**: `dev` (Development)
- **Type**: Branch config (root: false)
- **Inherits**: None (`[]`)
- **Inheritable**: No
- **Created**: 2025-12-16T15:55:56.066Z (9 days ago)
- **Last Fetch**: 2025-12-25T08:24:26.320Z (recently used)

**Secrets** (16 total):
```
AURORA_DATABASE=ticker_data
AURORA_HOST=127.0.0.1
AURORA_PASSWORD=AuroraDevDb2025SecureX1
AURORA_PORT=3307
AURORA_USERNAME=admin
AURORA_MASTER_PASSWORD=AuroraDevDb2025SecureX1
DOPPLER_CONFIG=dev_local
DOPPLER_ENVIRONMENT=dev
DOPPLER_PROJECT=rag-chatbot-worktree
OPENROUTER_API_KEY=sk-or-v1-...
RDS_DATABASE=linebot
RDS_HOST=linebot-db.c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com
RDS_PASSWORD=TOvarRuPTu6FdryxQOwlQQ5A0MO57Q
RDS_PORT=5432
RDS_USER=linebot_app
TELEGRAM_BOT_TOKEN=7573949249:...
```

**Architecture**:
- Self-contained config with all secrets defined locally
- No inheritance (all secrets manually set)
- Uses both `AURORA_*` and `RDS_*` prefixes
- `AURORA_*` points to localhost (local development)
- `RDS_*` points to AWS RDS (remote database)

---

### local_dev (NEW)

**Metadata**:
- **Name**: `local_dev`
- **Environment**: `local` (Local Development)
- **Type**: Branch config (root: false)
- **Inherits**: `rag-chatbot-worktree.dev` ✅
- **Inheritable**: No
- **Created**: 2025-12-25T08:16:46.084Z (today)
- **Last Fetch**: Never (not yet used in practice)

**Secrets** (13 total):
```
# Local overrides (4):
RDS_HOST=localhost
RDS_PORT=3307
MOCK_AURORA=true
TELEGRAM_API_URL=http://localhost:8001

# Inherited from dev (9):
AURORA_MASTER_PASSWORD=AuroraDevDb2025SecureX1
DOPPLER_CONFIG=local_dev (auto-set)
DOPPLER_ENVIRONMENT=local (auto-set)
DOPPLER_PROJECT=rag-chatbot-worktree
OPENROUTER_API_KEY=sk-or-v1-...
RDS_DATABASE=linebot
RDS_PASSWORD=TOvarRuPTu6FdryxQOwlQQ5A0MO57Q
RDS_USER=linebot_app
TELEGRAM_BOT_TOKEN=7573949249:...
```

**Architecture**:
- Inherits from `dev` config (11 shared secrets)
- Only 4 local overrides defined
- Uses `RDS_*` prefix only (no `AURORA_*`)
- Separate `local` environment (not `dev`)
- Includes `MOCK_AURORA` flag (local dev optimization)

---

## Architectural Differences

### 1. Inheritance Model

| Aspect | dev_local (OLD) | local_dev (NEW) |
|--------|-----------------|-----------------|
| **Inheritance** | None | Inherits from `dev` |
| **Secret Duplication** | All 16 secrets duplicated | Only 4 local overrides |
| **Maintenance** | Update secrets in 2 places | Update once in `dev` |
| **Drift Risk** | High (configs diverge) | Low (inheritance ensures consistency) |

**Trade-off**: Simplicity (dev_local) vs Maintainability (local_dev)

---

### 2. Environment Separation

| Aspect | dev_local (OLD) | local_dev (NEW) |
|--------|-----------------|-----------------|
| **Environment** | `dev` | `local` |
| **Semantics** | Local is variant of dev | Local is separate environment |
| **Doppler UI** | Mixed with AWS dev configs | Clearly separated |
| **DOPPLER_ENVIRONMENT** | `dev` (misleading) | `local` (accurate) |

**Trade-off**: Familiarity (dev_local) vs Clarity (local_dev)

---

### 3. Naming Convention

| Aspect | dev_local (OLD) | local_dev (NEW) |
|--------|-----------------|-----------------|
| **Naming Pattern** | `{env}_{variant}` | `{variant}_{env}` |
| **Doppler Requirement** | Free naming (in `dev` env) | Must start with `local_` (in `local` env) |
| **Consistency** | `dev_local`, `dev_personal` | `local_dev`, (future: `local_ci`) |

**Trade-off**: Arbitrary naming (dev_local) vs Convention-enforced naming (local_dev)

---

### 4. Secret Schema

| Aspect | dev_local (OLD) | local_dev (NEW) |
|--------|-----------------|-----------------|
| **Database Prefix** | Both `AURORA_*` and `RDS_*` | `RDS_*` only |
| **Aurora Config** | `127.0.0.1:3307` | (None - relies on `RDS_*`) |
| **RDS Config** | AWS endpoint (remote) | `localhost:3307` (local) |
| **Consistency** | Confusing (two prefixes) | Clear (one prefix) |

**Issue**: `dev_local` has inconsistent usage:
- `AURORA_*` → localhost (local dev via SSM tunnel)
- `RDS_*` → AWS RDS (remote)

This suggests **two different databases** or **naming inconsistency**.

**Clarification needed**: What is `ticker_data` (AURORA_DATABASE) vs `linebot` (RDS_DATABASE)?

---

### 5. Local Development Flags

| Aspect | dev_local (OLD) | local_dev (NEW) |
|--------|-----------------|-----------------|
| **MOCK_AURORA** | ❌ Not present | ✅ `true` |
| **TELEGRAM_API_URL** | ❌ Not present | ✅ `http://localhost:8001` |
| **Local Optimization** | None | Explicit local dev flags |

**Trade-off**: Minimal config (dev_local) vs Explicit local behavior (local_dev)

---

## Dependency Analysis

### Preconditions for dev_local (OLD)

**Required**:
- ✅ Doppler project `rag-chatbot-worktree` exists
- ✅ Environment `dev` exists
- ✅ All 16 secrets manually set

**Assumptions**:
- Local code understands both `AURORA_*` and `RDS_*` prefixes
- `AURORA_*` → ticker data database (SSM tunnel)
- `RDS_*` → LINE bot database (remote AWS RDS)
- No inheritance needed (all secrets self-contained)

**Risks**:
- ⚠️ Secret drift: If `dev` config secrets change, `dev_local` won't inherit changes
- ⚠️ Naming confusion: Two database prefixes (`AURORA_*` vs `RDS_*`)
- ⚠️ Maintenance burden: Update secrets in multiple places

---

### Preconditions for local_dev (NEW)

**Required**:
- ✅ Doppler project `rag-chatbot-worktree` exists
- ✅ Environment `local` exists (created today)
- ✅ Config `dev` exists and is inheritable
- ✅ Only 4 local overrides manually set
- ✅ Inheritance configured: `local_dev` → `dev`

**Assumptions**:
- Local code only needs `RDS_*` prefix (no `AURORA_*`)
- `RDS_HOST=localhost` connects to SSM tunnel (port 3307)
- `MOCK_AURORA=true` enables local dev optimizations
- `TELEGRAM_API_URL=http://localhost:8001` points to local dev server
- Inherited secrets from `dev` are correct

**Risks**:
- ⚠️ Inheritance dependency: If `dev` config changes break local dev, impact is immediate
- ⚠️ New pattern: Team must learn inheritance model
- ⚠️ Not yet tested: Created today, no production usage

---

## Hidden Complexity

### dev_local Complexity

**Simple on surface**:
- Self-contained config
- All secrets visible in one place
- No inheritance to understand

**Hidden complexity**:
1. **Two database schemas?**: `AURORA_*` vs `RDS_*` suggests two separate databases
   - `ticker_data` (AURORA_DATABASE) - What is this?
   - `linebot` (RDS_DATABASE) - LINE bot database
   - Are both used locally? Or is this legacy naming?

2. **Secret duplication**:
   - If `OPENROUTER_API_KEY` changes in `dev`, must update `dev_local` manually
   - Same for `TELEGRAM_BOT_TOKEN`, passwords, etc.

3. **Inconsistent host mapping**:
   - `AURORA_HOST=127.0.0.1` (localhost)
   - `RDS_HOST=linebot-db...amazonaws.com` (AWS)
   - Why different? Should both be localhost for local dev?

4. **No local dev flags**:
   - No `MOCK_AURORA` - slower local dev (real DB queries)
   - No `TELEGRAM_API_URL` override - connects to production?

---

### local_dev Complexity

**Appears complex**:
- Inheritance from `dev`
- Separate `local` environment
- New naming convention

**Hidden complexity**:
1. **Inheritance dependency**:
   - If `dev` config has wrong value, `local_dev` inherits it
   - Breaking change in `dev` breaks local dev
   - Must understand parent-child relationship

2. **Environment semantics**:
   - Is `local` truly a separate environment?
   - Or is it a variant of `dev`?
   - Doppler enforces `local_*` naming - is this limiting?

3. **Missing AURORA_* secrets**:
   - Does code still expect `AURORA_*` prefix?
   - Or has code been migrated to `RDS_*` only?
   - If code expects both, `local_dev` is incomplete

4. **Not yet validated**:
   - Created today
   - Not tested in actual local development
   - May have missing secrets or wrong values

---

## Hypotheses (Testable)

### Hypothesis 1: dev_local supports two databases

**Claim**: `dev_local` config has both `AURORA_*` and `RDS_*` because local dev uses two separate databases:
- `AURORA_*` → ticker data (dr-daily-report project)
- `RDS_*` → LINE bot data (legacy LINE bot project)

**Test**:
```bash
# Check if code references both prefixes
grep -r "AURORA_HOST\|RDS_HOST" src/
```

**Evidence**:
- `AURORA_DATABASE=ticker_data` (ticker data)
- `RDS_DATABASE=linebot` (LINE bot data)
- Different hosts (localhost vs AWS)

**Likelihood**: High

---

### Hypothesis 2: local_dev is incomplete

**Claim**: `local_dev` is missing `AURORA_*` secrets needed for ticker data database, making it unusable.

**Test**:
```bash
# Try to run app with local_dev config
doppler run --config local_dev -- python -c "import os; print(os.getenv('AURORA_HOST'))"
```

**Expected**:
- If code needs `AURORA_*`: Returns `None` (missing) → Config incomplete
- If code uses `RDS_*` only: Returns nothing (expected) → Config correct

**Likelihood**: Medium

---

### Hypothesis 3: dev_local has legacy naming

**Claim**: `AURORA_*` is legacy naming from before migration to `RDS_*` prefix. Both point to same database, just different naming.

**Test**:
```bash
# Check if AURORA_* and RDS_* values are consistent
# If both exist, do they point to same database?
```

**Evidence AGAINST**:
- `AURORA_DATABASE=ticker_data` ≠ `RDS_DATABASE=linebot`
- Different database names suggest different databases

**Likelihood**: Low

---

### Hypothesis 4: local_dev inheritance will reduce drift

**Claim**: Using inheritance in `local_dev` will prevent secret drift between `dev` and local configs.

**Test**:
- Update `OPENROUTER_API_KEY` in `dev` config
- Check if `local_dev` automatically inherits new value
- Check if `dev_local` still has old value

**Expected**:
- `local_dev`: New value (inherited) ✅
- `dev_local`: Old value (no inheritance) ❌

**Likelihood**: High (this is how inheritance works)

---

## Investigation Plan

### Priority 1: Understand Database Schema (CRITICAL)

**Why**: Cannot choose config without understanding if code needs `AURORA_*` and/or `RDS_*`.

**Tasks**:
1. **Search codebase for database prefix usage**:
   ```bash
   grep -r "AURORA_HOST\|AURORA_PORT\|AURORA_DATABASE" src/ --include="*.py"
   grep -r "RDS_HOST\|RDS_PORT\|RDS_DATABASE" src/ --include="*.py"
   ```

2. **Check environment variable usage**:
   ```bash
   # Find all os.getenv or os.environ references
   grep -r "getenv.*AURORA\|getenv.*RDS" src/ --include="*.py"
   ```

3. **Verify database connections**:
   - Does code connect to one database or two?
   - Is `ticker_data` a separate database from `linebot`?
   - Are both used in local development?

**Outcome**: Determines if `local_dev` needs `AURORA_*` secrets.

---

### Priority 2: Test local_dev Config (HIGH)

**Why**: Verify if new config works before switching.

**Tasks**:
1. **Test basic secret access**:
   ```bash
   doppler run --config local_dev -- env | grep -E "RDS_|MOCK_AURORA|TELEGRAM_API_URL"
   ```

2. **Test application startup**:
   ```bash
   doppler run --config local_dev -- python -m src.main
   ```

3. **Check for missing secrets**:
   - Does app crash due to missing env vars?
   - Are all required secrets accessible?

**Outcome**: Confirms `local_dev` is usable.

---

### Priority 3: Compare Inheritance Behavior (MEDIUM)

**Why**: Validate that inheritance reduces maintenance burden.

**Tasks**:
1. **Test inheritance**:
   ```bash
   # Verify local_dev inherits from dev
   doppler secrets --config dev --json | jq '.OPENROUTER_API_KEY.computed'
   doppler secrets --config local_dev --json | jq '.OPENROUTER_API_KEY.computed'
   # Should be identical
   ```

2. **Test override behavior**:
   ```bash
   # Verify local_dev overrides work
   doppler secrets --config dev --json | jq '.RDS_HOST.computed'
   # Should be: linebot-db...amazonaws.com (AWS)

   doppler secrets --config local_dev --json | jq '.RDS_HOST.computed'
   # Should be: localhost (overridden)
   ```

**Outcome**: Confirms inheritance model works correctly.

---

### Priority 4: Document Decision (LOW)

**Why**: Once choice made, document reasoning for future reference.

**Tasks**:
1. Create ADR (Architecture Decision Record)
2. Update specification with chosen approach
3. Clean up unused config (after verification period)

---

## Trade-Off Analysis

### Option A: Use dev_local (OLD)

**Pros**:
- ✅ Already exists and has been used (9 days)
- ✅ Self-contained (no inheritance to understand)
- ✅ Supports both `AURORA_*` and `RDS_*` (if needed)
- ✅ Last accessed recently (2025-12-25) - likely working

**Cons**:
- ❌ No inheritance (secret duplication)
- ❌ Secret drift risk (must update manually)
- ❌ Confusing naming (two database prefixes)
- ❌ No local dev flags (`MOCK_AURORA`, `TELEGRAM_API_URL`)
- ❌ In `dev` environment (semantically incorrect)

**When to choose**:
- Code requires both `AURORA_*` and `RDS_*` secrets
- Team prefers simple, self-contained configs
- Don't want to change existing working setup
- Short-term solution acceptable

---

### Option B: Use local_dev (NEW)

**Pros**:
- ✅ Inheritance reduces duplication (4 overrides vs 16 total)
- ✅ Automatic updates when `dev` secrets change
- ✅ Clear separation (`local` environment)
- ✅ Local dev flags (`MOCK_AURORA`, `TELEGRAM_API_URL`)
- ✅ Consistent `RDS_*` naming only
- ✅ Follows Doppler best practices

**Cons**:
- ❌ New pattern (team must learn)
- ❌ Not yet tested in practice
- ❌ Missing `AURORA_*` secrets (if code needs them)
- ❌ Inheritance dependency (breaking changes propagate)
- ❌ More complex conceptual model

**When to choose**:
- Code only needs `RDS_*` secrets (or can be migrated)
- Team values maintainability over simplicity
- Want to prevent secret drift long-term
- Willing to test new approach

---

### Option C: Hybrid - Migrate dev_local → local_dev

**Approach**:
1. Copy missing `AURORA_*` secrets to `local_dev`
2. Test `local_dev` works identically to `dev_local`
3. Gradually migrate workflows to `local_dev`
4. After 1-2 weeks, delete `dev_local`

**Pros**:
- ✅ Best of both worlds (complete secrets + inheritance)
- ✅ Safe migration path (test before switching)
- ✅ Backwards compatible (keep both during transition)

**Cons**:
- ❌ Temporary overhead (maintain both configs)
- ❌ Still need to understand if `AURORA_*` needed

**When to choose**:
- Uncertain if code needs `AURORA_*` secrets
- Want safe migration path
- Team needs time to learn new pattern

---

## Recommended Implementation Order

### Phase 1: Investigation (Today)

**Tasks**:
1. ✅ Compare configs (completed above)
2. [ ] Search codebase for `AURORA_*` vs `RDS_*` usage
3. [ ] Determine if both database prefixes needed
4. [ ] Test `local_dev` config with actual app

**Blocker**: Cannot choose config until we know if code needs `AURORA_*`.

---

### Phase 2: Decision (After Investigation)

**Scenario A: Code needs both AURORA_* and RDS_***
→ **Use dev_local** (Option A)
   - Already has both prefixes
   - Works today
   - Document as legacy until migration

**Scenario B: Code only needs RDS_***
→ **Use local_dev** (Option B)
   - Clean architecture
   - Inheritance benefits
   - Add `MOCK_AURORA`, `TELEGRAM_API_URL` flags

**Scenario C: Uncertain**
→ **Hybrid migration** (Option C)
   - Add `AURORA_*` to `local_dev` temporarily
   - Test both configs work identically
   - Choose one after validation

---

### Phase 3: Migration (After Decision)

**If choosing local_dev**:
1. Add any missing secrets to `local_dev`
2. Update local `.doppler.yaml` to use `local_dev`
3. Test all local dev workflows
4. Document new pattern in `docs/deployment/DOPPLER_CONFIG.md`
5. After 1 week: Delete `dev_local`, `dev_personal`

**If choosing dev_local**:
1. Document current setup in `docs/deployment/DOPPLER_CONFIG.md`
2. Add local dev flags to `dev_local` (`MOCK_AURORA`, etc.)
3. Delete unused `local_dev` config
4. Plan future migration to inheritance model

---

## Success Criteria

### How to verify decision is correct:

**For dev_local (Option A)**:
- [ ] Local development works without errors
- [ ] Can connect to both databases (if needed)
- [ ] Team understands which config to use
- [ ] Documented: When to update secrets in `dev_local`

**For local_dev (Option B)**:
- [ ] Local development works without errors
- [ ] Inheritance working (changes in `dev` auto-propagate)
- [ ] No missing secrets errors
- [ ] `MOCK_AURORA` flag speeds up local dev
- [ ] Team understands inheritance model

**For both**:
- [ ] Clear documentation: Which config to use for local dev
- [ ] No duplicate configs confusing the team
- [ ] Secrets stay in sync with `dev` environment

---

## Investigation Results (2025-12-25)

### ✅ Priority 1: Database Prefix Usage - COMPLETED

**Finding**: **Code uses AURORA_* exclusively. RDS_* is NOT used in codebase.**

**Evidence**:
```bash
# AURORA_* usage: 74 matches across src/, tests/, scripts/
grep -r "AURORA_HOST|AURORA_PORT|AURORA_DATABASE" src/ --include="*.py"
→ 74 matches found

# RDS_* usage: 0 matches
grep -r "RDS_HOST|RDS_PORT|RDS_DATABASE" src/ --include="*.py"
→ No matches found
```

**Critical Files Using AURORA_***:
1. **src/data/aurora/client.py:93-97** - Aurora client reads `AURORA_HOST`, `AURORA_PORT`, `AURORA_DATABASE`, `AURORA_USER`, `AURORA_PASSWORD`
2. **src/scheduler/get_ticker_list_handler.py:56-60** - Scheduler Lambda requires `AURORA_*` env vars
3. **src/report_worker_handler.py:57** - Report worker uses `AURORA_HOST` for caching
4. **scripts/run_aurora_migration.py:203** - Migration script requires `AURORA_HOST`, `AURORA_PASSWORD`

**Conclusion**:
- ✅ `dev_local` is **COMPLETE** (has `AURORA_*` secrets)
- ❌ `local_dev` is **INCOMPLETE** (missing `AURORA_*` secrets)
- `RDS_*` secrets in both configs are **UNUSED** (likely legacy from LINE Bot project)

---

### Decision: Use dev_local (OLD) OR Fix local_dev

**Two paths forward**:

#### Path A: Use dev_local (Keep existing, working config)
**Pros**:
- ✅ Has all required `AURORA_*` secrets
- ✅ Already working (used for 9 days)
- ✅ No migration needed
- ✅ Zero risk

**Cons**:
- ❌ No inheritance (secret duplication)
- ❌ Has unused `RDS_*` secrets (confusing)
- ❌ Missing local dev flags (`MOCK_AURORA`, `TELEGRAM_API_URL`)

**Action**:
1. Keep `dev_local` as-is
2. Delete unused `local_dev` config
3. Optionally add local dev flags to `dev_local`

---

#### Path B: Fix local_dev (Add missing AURORA_* secrets)
**Pros**:
- ✅ Inheritance model (long-term maintainability)
- ✅ Has local dev flags already
- ✅ Clear environment separation (`local` vs `dev`)
- ✅ Follows Doppler best practices

**Cons**:
- ❌ Need to add 5 `AURORA_*` secrets
- ❌ Need to test thoroughly
- ❌ Migration effort

**Action**:
1. Add missing secrets to `local_dev`:
   ```bash
   doppler secrets set AURORA_HOST localhost --project rag-chatbot-worktree --config local_dev
   doppler secrets set AURORA_PORT 3307 --project rag-chatbot-worktree --config local_dev
   doppler secrets set AURORA_DATABASE ticker_data --project rag-chatbot-worktree --config local_dev
   doppler secrets set AURORA_USERNAME admin --project rag-chatbot-worktree --config local_dev
   # AURORA_PASSWORD already inherited from dev (AURORA_MASTER_PASSWORD)
   ```

2. Test `local_dev` config works
3. Migrate from `dev_local` → `local_dev`
4. Delete `dev_local` after verification

---

## Recommended Path: **Path B (Fix local_dev)**

**Reasoning**:
1. **Long-term value**: Inheritance prevents secret drift
2. **Already invested**: Created `local` environment and `local_dev` config today
3. **Low effort**: Only 4 additional secrets needed (1 already inherited)
4. **Better architecture**: Separate `local` environment is clearer

**Implementation**:
```bash
# Step 1: Add missing AURORA_* secrets to local_dev
doppler secrets set AURORA_HOST localhost \
  --project rag-chatbot-worktree \
  --config local_dev

doppler secrets set AURORA_PORT 3307 \
  --project rag-chatbot-worktree \
  --config local_dev

doppler secrets set AURORA_DATABASE ticker_data \
  --project rag-chatbot-worktree \
  --config local_dev

doppler secrets set AURORA_USERNAME admin \
  --project rag-chatbot-worktree \
  --config local_dev

# Note: AURORA_PASSWORD can use inherited AURORA_MASTER_PASSWORD
# Or set explicitly if different:
doppler secrets set AURORA_PASSWORD "$(doppler secrets get AURORA_MASTER_PASSWORD --plain --project rag-chatbot-worktree --config dev)" \
  --project rag-chatbot-worktree \
  --config local_dev
```

---

## Next Steps

1. **[✅] Investigate database prefix usage** (Priority 1) - **COMPLETED**
   - Finding: Code uses `AURORA_*` only, not `RDS_*`
   - `local_dev` missing 5 required `AURORA_*` secrets

2. **[ ] Fix local_dev config** (Priority 2 - NEW)
   ```bash
   # Add missing AURORA_* secrets (see commands above)
   ```

3. **[ ] Test local_dev config** (Priority 3)
   ```bash
   doppler run --config local_dev -- python -c "
import os
print('AURORA_HOST:', os.getenv('AURORA_HOST'))
print('AURORA_PORT:', os.getenv('AURORA_PORT'))
print('AURORA_DATABASE:', os.getenv('AURORA_DATABASE'))
print('AURORA_USERNAME:', os.getenv('AURORA_USERNAME'))
print('AURORA_PASSWORD:', 'SET' if os.getenv('AURORA_PASSWORD') else 'MISSING')
print('MOCK_AURORA:', os.getenv('MOCK_AURORA'))
   "
   ```

4. **[ ] Migrate to local_dev** (After testing)
   - Update local setup: `doppler setup --config local_dev`
   - Test all local dev workflows
   - After 1 week: Delete `dev_local`, `dev_personal`

5. **[ ] Clean up unused RDS_* secrets** (Optional)
   - Remove `RDS_*` from both configs (unused by code)
   - Document that LINE Bot project has separate Doppler project

6. **[ ] Update documentation** (Priority 4)
   - `docs/deployment/DOPPLER_CONFIG.md`
   - `.claude/CLAUDE.md` (Secret Management section)
   - Document decision in ADR

---

## References

**Doppler Configs**:
- Project: `rag-chatbot-worktree`
- Old: `dev_local` (environment: `dev`, created: 2025-12-16)
- New: `local_dev` (environment: `local`, created: 2025-12-25)

**Specification**:
- `.claude/specifications/workflow/2025-12-24-doppler-config-organization-for-multi-env.md`

**Comparison Data**:
- `/tmp/config_comparison.json`
- `/tmp/dev_local_secrets.json`
- `/tmp/local_dev_secrets.json`

---

## Summary

**Question**: dev_local (OLD) or local_dev (NEW)?

**Answer**: **Depends on codebase requirements** (investigation needed)

**Critical Unknown**: Does code need `AURORA_*` secrets, `RDS_*` secrets, or both?

**Next Action**: Search codebase for database prefix usage to determine which config is complete.

**Recommendation**: After investigation, likely **local_dev** (Option B) for long-term maintainability, but only if `AURORA_*` secrets can be migrated or are not needed.
