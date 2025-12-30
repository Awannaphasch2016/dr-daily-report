---
title: "What-If: Rename local_dev to dev_local (keep inheritance)"
type: what-if
date: 2025-12-25
scenario: "Use dev_local name with inheritance from dev config"
tags: [doppler, naming, inheritance, migration]
---

# What-If Analysis: Rename local_dev → dev_local (Keep Inheritance)

**Scenario**: Keep the `dev_local` name (familiar) but add inheritance from `dev` config

**Proposed Change**:
- Config name: `dev_local` (familiar, already used)
- Inheritance: Inherit from `dev` ✅ (new behavior)
- Environment: `dev` (current) or `local` (new) - TBD

**Motivation**:
- User preference: "We have been using dev_local"
- Keep familiarity while gaining inheritance benefits
- Avoid renaming overhead if not necessary

---

## Current Reality (Baseline)

### Existing Configs

**dev_local (OLD)**:
```
Name: dev_local
Environment: dev
Type: Branch config (root: false)
Inherits: [] (NONE)
Inheritable: false
Created: 2025-12-16
Secrets: 16 (all defined locally, no inheritance)
Status: Working, in use
```

**local_dev (NEW)**:
```
Name: local_dev
Environment: local
Type: Branch config (root: false)
Inherits: [rag-chatbot-worktree.dev] ✅
Inheritable: false
Created: 2025-12-25
Secrets: 13 (4 local + 9 inherited)
Missing: AURORA_* secrets (incomplete)
Status: Not yet used
```

### Doppler Naming Constraints

**Discovered constraint**: Configs in `local` environment **MUST** start with `local_`

**Evidence**:
```bash
# Attempted to create dev_local in local environment
$ doppler configs create dev_local --project rag-chatbot-worktree --environment local
ERROR: Config name must start with "local_" (ex: local_backend).
```

**Implication**: Cannot have inheritance AND `dev_local` name in `local` environment.

---

## Under New Assumption: dev_local Name + Inheritance

### Option 1: dev_local in `dev` Environment (with inheritance)

**Configuration**:
```
Name: dev_local
Environment: dev
Inherits: [rag-chatbot-worktree.dev]
```

**What This Requires**:
1. Delete current `dev_local` (no inheritance)
2. Recreate `dev_local` in `dev` environment
3. Configure inheritance: `--inherits rag-chatbot-worktree.dev`
4. Add local overrides (AURORA_HOST=localhost, etc.)

**Doppler Constraint Check**:
```bash
# Can configs in same environment inherit?
# Tested: ❌ NO - Doppler error:
"Config cannot inherit from another config in the same environment"
```

**Result**: ❌ **BLOCKED BY DOPPLER CONSTRAINT**

Doppler does not allow inheritance between configs in the same environment.

---

### Option 2: Rename local_dev → dev_local (keep `local` environment)

**Configuration**:
```
Name: dev_local  # Familiar name
Environment: local  # Separate environment (required for inheritance)
Inherits: [rag-chatbot-worktree.dev]
```

**Doppler Constraint Check**:
```bash
# Can we name it dev_local in local environment?
# Tested: ❌ NO - Doppler enforces naming:
"Config name must start with 'local_' (ex: local_backend)."
```

**Result**: ❌ **BLOCKED BY DOPPLER NAMING CONVENTION**

Configs in `local` environment must start with `local_` prefix.

---

## What Breaks

### Critical Constraint: Doppler's Inheritance Model

**Constraint 1: Same-Environment Inheritance Forbidden**
```
dev_local (env: dev)
    ↓ inherits from
dev (env: dev)

ERROR: "Config cannot inherit from another config in the same environment"
```

**Why**: Doppler enforces environment boundaries for inheritance to prevent circular dependencies and maintain clear hierarchy.

**Impact**: Cannot have `dev_local` inherit from `dev` if both are in `dev` environment.

---

**Constraint 2: Environment-Based Naming Convention**
```
Config in `local` environment
    MUST start with: local_*

dev_local → ❌ REJECTED
local_dev → ✅ ACCEPTED
```

**Why**: Doppler enforces naming conventions to make config-environment relationship explicit.

**Impact**: Cannot use `dev_local` name in `local` environment.

---

### Combination Analysis

| Goal | Name | Environment | Inherits | Doppler Allows? |
|------|------|-------------|----------|-----------------|
| Familiar name, no inheritance | `dev_local` | `dev` | None | ✅ Current state |
| Familiar name, with inheritance | `dev_local` | `dev` | `dev` | ❌ Same-env forbidden |
| Familiar name, separate env | `dev_local` | `local` | `dev` | ❌ Naming convention |
| Unfamiliar name, inheritance | `local_dev` | `local` | `dev` | ✅ New approach |

**Conclusion**: **Cannot have both `dev_local` name AND inheritance.**

---

## What Improves (Workarounds)

### Workaround 1: Use `local_dev` (Accept New Name)

**Configuration**:
```
Name: local_dev
Environment: local
Inherits: rag-chatbot-worktree.dev
```

**Pros**:
- ✅ Inheritance works (long-term maintainability)
- ✅ Doppler compliant (no naming conflicts)
- ✅ Clear semantics (`local` environment)

**Cons**:
- ❌ Name change (from `dev_local` to `local_dev`)
- ❌ Team must learn new name

**Risk**: Low (name change is low-risk, just requires communication)

---

### Workaround 2: Keep `dev_local` (No Inheritance)

**Configuration**:
```
Name: dev_local
Environment: dev
Inherits: None
```

**Pros**:
- ✅ Familiar name (no change)
- ✅ Already working (9 days in use)
- ✅ Zero migration risk

**Cons**:
- ❌ No inheritance (secret duplication)
- ❌ Manual sync with `dev` config
- ❌ Long-term drift risk

**Risk**: Medium (secret drift over time)

---

### Workaround 3: Alias Pattern (Symbolic Link)

**Idea**: Use `local_dev` (real config) + documentation alias

**Implementation**:
```bash
# Real config
doppler run --config local_dev -- python app.py

# Documentation
# ALIAS: You can think of local_dev as "dev_local with inheritance"
# Old name: dev_local
# New name: local_dev
# Same purpose: Local development
```

**Pros**:
- ✅ Inheritance works
- ✅ Documentation bridges mental model
- ✅ Low technical risk

**Cons**:
- ❌ Still requires name change in commands
- ❌ Documentation workaround (not technical solution)

**Risk**: Low (just communication)

---

## Insights Revealed

### Assumption 1: "Naming is flexible"

**Reality**: Doppler enforces strict naming conventions based on environment.

**Evidence**:
- Configs in `local` env must start with `local_`
- Cannot override this (hard constraint)

**Impact**: Name choice is constrained by environment choice.

---

### Assumption 2: "Inheritance is orthogonal to environment"

**Reality**: Inheritance is tightly coupled to environment separation.

**Evidence**:
- Cannot inherit within same environment
- Inheritance requires parent-child in different environments

**Impact**: To have inheritance, MUST have separate environments. To have separate environments, MUST follow naming convention.

---

### Assumption 3: "Config name change is risky"

**Challenge**: Is renaming `dev_local` → `local_dev` actually risky?

**Risk Analysis**:

**What changes**:
```bash
# Old command
doppler run --config dev_local -- python app.py

# New command
doppler run --config local_dev -- python app.py
```

**Impact areas**:
1. **Local development**: Developer commands (low-risk, explicit)
2. **Scripts**: Hardcoded config names (need grep + update)
3. **Documentation**: References to `dev_local` (need update)
4. **Mental model**: Team familiarity (communication)

**Risk assessment**:
- Technical risk: **Low** (just string replacement)
- Communication risk: **Medium** (team must learn new name)
- Execution risk: **Low** (one-time migration)

**Conclusion**: Name change is **low-risk** if communicated clearly.

---

### Trade-Off: Familiarity vs Maintainability

**Option A: Keep dev_local (Familiarity)**
- Short-term: Easy (no change)
- Long-term: Painful (secret drift, manual sync)
- Team: Happy now (no learning curve)

**Option B: Switch to local_dev (Maintainability)**
- Short-term: Small friction (new name)
- Long-term: Easy (inheritance, auto-sync)
- Team: Learn once, benefit forever

**Revealed insight**: Familiarity is short-term comfort. Maintainability is long-term value.

---

## Alternative Approaches

### Alternative 1: Hybrid - Keep Both Temporarily

**Approach**:
1. Keep `dev_local` (working, familiar)
2. Create `local_dev` with inheritance
3. Migrate gradually:
   - Week 1: Introduce `local_dev`, both work
   - Week 2: Document `local_dev` as preferred
   - Week 3: Deprecate `dev_local`
   - Week 4: Delete `dev_local`

**Pros**:
- ✅ Zero disruption (both configs work)
- ✅ Safe migration (gradual)
- ✅ Team learns at their pace

**Cons**:
- ❌ Temporary overhead (maintain both)
- ❌ Confusion (which one to use?)

---

### Alternative 2: Document as "dev_local v2"

**Approach**:
1. Rename mentally: `local_dev` = "dev_local version 2"
2. Update docs:
   ```
   # Old: dev_local (deprecated)
   # New: local_dev (with inheritance)
   # Migration: One-line change in commands
   ```

**Pros**:
- ✅ Frames as upgrade (v1 → v2)
- ✅ Clear migration path
- ✅ Benefits obvious (inheritance)

**Cons**:
- ❌ Still requires name change

---

### Alternative 3: Accept Doppler's Convention

**Mindset shift**: Doppler's naming convention is **design guidance**, not limitation.

**Interpretation**:
```
Environment: local
Config name: local_dev
           ↓
Semantic: "This is the DEV config for LOCAL environment"

NOT: "This is the LOCAL config for DEV environment"
```

**Benefit**:
- Config name reflects "what environment am I in" (local)
- Suffix reflects "what base does it derive from" (dev)
- Convention makes configs self-documenting

**Example**:
```
local_dev    → Local environment, derived from dev
local_stg    → Local environment, derived from staging (for testing)
local_prod   → Local environment, derived from prod (dangerous!)
```

**Insight**: Doppler's convention is **better** for clarity once you understand the pattern.

---

## Recommendation

### Decision: ✅ YES - Use `local_dev` Name (Accept Doppler Convention)

**Rationale**:

1. **Technical constraint**: Cannot have `dev_local` with inheritance in Doppler
   - Same-environment inheritance: Forbidden
   - `local` environment naming: Must start with `local_`

2. **Risk assessment**: Name change is **low-risk**
   - Impact: Commands, scripts, docs (all searchable/replaceable)
   - Benefit: Inheritance prevents secret drift (high value)
   - One-time migration cost vs ongoing maintenance burden

3. **Long-term value**: Inheritance > Familiarity
   - Secret drift is real problem (costs debugging time)
   - Manual sync is error-prone (forgot to update key)
   - Inheritance is one-time learning, permanent benefit

4. **Doppler convention makes sense**: `local_dev` is actually clearer
   - Reads as: "Local environment, dev variant"
   - Scales to: `local_stg`, `local_prod` if needed
   - Self-documenting (environment clear from prefix)

---

### Action Items

**Phase 1: Fix local_dev Config (Today)**
```bash
# Add missing AURORA_* secrets to local_dev
doppler secrets set AURORA_HOST localhost --project rag-chatbot-worktree --config local_dev
doppler secrets set AURORA_PORT 3307 --project rag-chatbot-worktree --config local_dev
doppler secrets set AURORA_DATABASE ticker_data --project rag-chatbot-worktree --config local_dev
doppler secrets set AURORA_USERNAME admin --project rag-chatbot-worktree --config local_dev
doppler secrets set AURORA_PASSWORD "$(doppler secrets get AURORA_MASTER_PASSWORD --plain --project rag-chatbot-worktree --config dev)" --project rag-chatbot-worktree --config local_dev
```

**Phase 2: Test local_dev (Today)**
```bash
# Verify all secrets present
doppler run --config local_dev -- env | grep AURORA

# Test app startup
doppler run --config local_dev -- python -c "
import os
required = ['AURORA_HOST', 'AURORA_PORT', 'AURORA_DATABASE', 'AURORA_USERNAME', 'AURORA_PASSWORD']
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'❌ Missing: {missing}')
else:
    print('✅ All AURORA_* secrets present')
"
```

**Phase 3: Migrate from dev_local → local_dev (This Week)**
```bash
# Update local setup
doppler setup --project rag-chatbot-worktree --config local_dev

# Update any scripts referencing dev_local
grep -r "dev_local" scripts/ .github/ justfile

# Update documentation
# - docs/deployment/DOPPLER_CONFIG.md
# - .claude/CLAUDE.md
# - README.md (if applicable)
```

**Phase 4: Communicate Change (This Week)**
```markdown
# Team Communication Template

Subject: Doppler Config Rename: dev_local → local_dev

What changed:
  - OLD: doppler run --config dev_local -- <command>
  - NEW: doppler run --config local_dev -- <command>

Why:
  - Enables inheritance from `dev` config
  - Follows Doppler naming convention (local_* for local environment)
  - Prevents secret drift (auto-sync with dev)

How to migrate:
  1. Run: doppler setup --config local_dev
  2. Update your commands: dev_local → local_dev
  3. Benefit: Secrets auto-inherit from dev (no manual sync)

Questions: Ask in #dev-infra channel
```

**Phase 5: Clean Up (After 1 Week Verification)**
```bash
# After confirming local_dev works for everyone
doppler configs delete dev_local --project rag-chatbot-worktree --yes
doppler configs delete dev_personal --project rag-chatbot-worktree --yes
```

---

### Follow-Up Actions

**Journal this decision**:
```bash
/journal architecture "Why local_dev instead of dev_local for Doppler config"
```

**Document in**:
- `.claude/CLAUDE.md` - Secret Management Principle section
- `docs/deployment/DOPPLER_CONFIG.md` - Configuration guide
- `.claude/decompositions/architecture-2025-12-25-dev-local-vs-local-dev.md` - Update with final decision

**Update specification**:
- `.claude/specifications/workflow/2025-12-24-doppler-config-organization-for-multi-env.md` - Mark as implemented with final naming

---

## Key Insights Summary

### 1. Doppler Constraints are Design Guidance

**Constraint**: Configs in `local` environment must start with `local_`

**Insight**: This isn't arbitrary—it makes environment explicit in config name, improving self-documentation.

**Example**: `local_dev`, `local_stg`, `local_prod` clearly show environment + variant.

---

### 2. Inheritance Requires Environment Separation

**Constraint**: Cannot inherit within same environment

**Insight**: Prevents circular dependencies and enforces clear parent-child hierarchy.

**Implication**: To get inheritance benefits, MUST use separate environments (and their naming conventions).

---

### 3. Name Change is Low-Risk (Not Zero-Risk)

**Risk assessment**:
- Technical: Low (string replacement)
- Communication: Medium (team learning)
- Execution: Low (one-time migration)

**Insight**: Short-term friction (learning new name) < Long-term pain (secret drift).

---

### 4. Familiarity is Short-Term, Maintainability is Long-Term

**Trade-off revealed**:
- Keep `dev_local`: Familiar now, painful later (secret drift)
- Switch to `local_dev`: Small learning curve, easy forever (inheritance)

**Insight**: Optimize for long-term value, not short-term comfort.

---

## Conclusion

**Question**: Can we use `dev_local` name with inheritance?

**Answer**: ❌ **NO** - Doppler constraints prevent this:
1. Same-environment inheritance: Forbidden
2. `local` environment naming: Must start with `local_`

**Recommendation**: ✅ **YES** - Use `local_dev` (accept Doppler convention)

**Why**:
- Technical: Only way to get inheritance
- Risk: Name change is low-risk (one-time migration)
- Value: Inheritance prevents secret drift (high long-term value)
- Convention: `local_dev` is actually clearer once you understand pattern

**Next Step**: Add missing `AURORA_*` secrets to `local_dev`, test, migrate, communicate.

---

## References

**Doppler Documentation**:
- [Config Inheritance](https://docs.doppler.com/docs/config-inheritance)
- [Branch Configs](https://docs.doppler.com/docs/branch-configs)
- [Environment-Based Naming](https://docs.doppler.com/docs/environment-based-configuration)

**Project Documentation**:
- `.claude/decompositions/architecture-2025-12-25-dev-local-vs-local-dev.md` - Full comparison
- `.claude/specifications/workflow/2025-12-24-doppler-config-organization-for-multi-env.md` - Original spec

**Evidence**:
```bash
# Same-environment inheritance test
$ doppler configs update dev_local --project rag-chatbot-worktree --inherits rag-chatbot-worktree.dev
ERROR: Config cannot inherit from another config in the same environment

# Naming convention test
$ doppler configs create dev_local --project rag-chatbot-worktree --environment local
ERROR: Config name must start with "local_" (ex: local_backend).
```
