# Reconcile Command

**Purpose**: Converge invariant violations back to compliance by generating specific fix actions

**Core Principle**: Knowing delta is good, but converging delta to zero is essential. This command closes the feedback loop: **detect → fix → verify**.

**When to use**:
- After `/invariant` identifies violations
- When codebase members drift from established invariants
- During code review to enforce consistency
- Before deployment to ensure all invariants hold

---

## Quick Reference

```bash
# Pattern 1: Reconcile by domain (auto-detect violations)
/reconcile deployment
/reconcile data
/reconcile api
/reconcile langfuse
/reconcile frontend

# Pattern 2: Reconcile specific invariant
/reconcile "LANGFUSE_RELEASE must be set in all deploy workflows"

# Pattern 3: Reconcile with explicit member scope
/reconcile deployment --members ".github/workflows/*.yml"

# Pattern 4: After /invariant check (uses last invariant context)
/invariant "deploy telegram"
# → Shows violations
/reconcile
# → Generates fixes for those violations

# Pattern 5: Preview only (no file changes)
/reconcile deployment --preview

# Pattern 6: Auto-apply fixes (with confirmation)
/reconcile deployment --apply
```

---

## Conceptual Model

### The Invariant Triangle

```
        INVARIANT (I)
           /\
          /  \
         /    \
        /      \
    DETECT    CONVERGE
   (/invariant) (/reconcile)
        \      /
         \    /
          \  /
           \/
      MEMBERS (M)
```

**Invariant (I)**: What must remain true
**Members (M)**: Things that should satisfy I
**Detect**: `/invariant` identifies I and checks M against I
**Converge**: `/reconcile` fixes M to satisfy I

### Delta Function

```
δ(m, I) = 0   if m satisfies I  ✅
δ(m, I) > 0   if m violates I   ❌

/reconcile goal: ∀m ∈ M: δ(m, I) → 0
```

---

## Relationship to Other Commands

| Command | Direction | Question | Output |
|---------|-----------|----------|--------|
| `/invariant` | Divergent | "What must hold?" | Checklist of invariants |
| `/validate` | Checking | "Does it hold?" | Pass/fail status |
| `/reconcile` | Convergent | "How to make it hold?" | Fix actions |

**Workflow**:
```bash
/invariant "goal"     # 1. Identify what should hold
     ↓
[violations found]    # 2. Some members violate
     ↓
/reconcile            # 3. Generate fixes
     ↓
[apply fixes]         # 4. Execute fixes
     ↓
/invariant "goal"     # 5. Verify delta = 0
```

---

## Execution Flow

### Step 1: Parse Input

```bash
DOMAIN_OR_INVARIANT="$1"
FLAGS="${@:2}"

# Detect input type
if [[ "$DOMAIN_OR_INVARIANT" =~ ^(deployment|data|api|langfuse|frontend)$ ]]; then
  TYPE="domain"
  INVARIANT_FILE=".claude/invariants/${DOMAIN_OR_INVARIANT}-invariants.md"
elif [[ -z "$DOMAIN_OR_INVARIANT" ]]; then
  TYPE="last_context"  # Use last /invariant check
else
  TYPE="explicit"
  INVARIANT_STATEMENT="$DOMAIN_OR_INVARIANT"
fi

# Parse flags
PREVIEW_ONLY=false
AUTO_APPLY=false
MEMBER_SCOPE=""

for flag in $FLAGS; do
  case $flag in
    --preview) PREVIEW_ONLY=true ;;
    --apply) AUTO_APPLY=true ;;
    --members) MEMBER_SCOPE="$NEXT_ARG" ;;
  esac
done
```

---

### Step 2: Load Invariants

**For domain type**:
```markdown
Load: .claude/invariants/{domain}-invariants.md
Extract: All checklist items (- [ ] ...)
Parse: Level, category, verification command
```

**For explicit type**:
```markdown
Invariant: "{user-provided statement}"
Infer: Domain, level, verification approach
```

**For last_context**:
```markdown
Load: Last /invariant command output
Extract: Violations identified
```

---

### Step 3: Identify Member Scope

**Determine what to check**:

| Domain | Default Member Scope |
|--------|---------------------|
| deployment | `.github/workflows/*.yml`, `terraform/*.tf`, Doppler configs |
| data | `src/data/**/*.py`, `migrations/*.sql`, `src/data/aurora/table_names.py` |
| api | `src/api/**/*.py`, `src/handlers/*.py`, API routes |
| langfuse | `src/integrations/langfuse*.py`, `src/evaluation/*.py`, `.github/workflows/*.yml` |
| frontend | `frontend/**/*.tsx`, `frontend/**/*.ts`, `frontend/**/package.json` |

**Override with --members**:
```bash
/reconcile deployment --members ".github/workflows/deploy-*.yml"
```

---

### Step 4: Scan for Violations

**For each invariant, check each member**:

```markdown
## Scanning: {invariant}

Members checked: {count}
Violations found: {count}

| Member | Status | Delta | Detail |
|--------|--------|-------|--------|
| file1.yml | ✅ | 0 | Compliant |
| file2.yml | ❌ | 1 | Missing LANGFUSE_RELEASE |
| file3.yml | ❌ | 1 | Missing LANGFUSE_RELEASE |
```

**Violation detection patterns**:

```python
# Pattern: Environment variable must exist
def check_env_var(file, var_name):
    content = read_file(file)
    if var_name not in content:
        return Violation(
            member=file,
            invariant=f"{var_name} must be set",
            delta=1,
            detail=f"Missing {var_name}"
        )
    return None

# Pattern: Constant must be defined
def check_constant(file, const_name, registry_file):
    registry = read_file(registry_file)
    if const_name not in registry:
        return Violation(...)

# Pattern: Configuration consistency
def check_config_consistency(files, key):
    values = [extract_value(f, key) for f in files]
    if len(set(values)) > 1:
        return Violation(
            detail=f"Inconsistent {key}: {values}"
        )
```

---

### Step 5: Generate Fix Actions

**For each violation, generate specific fix**:

```markdown
## Convergence Actions

### Fix 1: {file_path}

**Violation**: {what's wrong}
**Invariant**: {what should hold}
**Delta**: {violation count}

**Action**:
```{language}
# Location: {file_path}:{line_number}
# Add/Change:
{specific code to add or change}
```

**Verification**:
```bash
{command to verify fix worked}
```

**Confidence**: {HIGH | MEDIUM | LOW}
- HIGH: Mechanical fix, pattern well-understood
- MEDIUM: Fix clear but context-dependent
- LOW: May need human review
```

---

### Step 6: Fix Templates by Domain

#### Deployment Fixes

**Missing env var in workflow**:
```yaml
# Fix: Add LANGFUSE_RELEASE to .github/workflows/deploy-line-bot.yml
# Location: env: section (around line 45)

env:
  LANGFUSE_RELEASE: ${{ env.ENVIRONMENT }}-${{ github.ref_name }}-${{ steps.short-sha.outputs.sha }}
```

**Missing Terraform variable**:
```hcl
# Fix: Add to terraform/variables.tf

variable "langfuse_release" {
  description = "Langfuse release version for tracing"
  type        = string
}
```

**Missing Doppler secret**:
```bash
# Fix: Add secret to Doppler
doppler secrets set LANGFUSE_RELEASE "dev-local" -p dr-daily-report -c dev
```

#### Data Fixes

**Missing table constant**:
```python
# Fix: Add to src/data/aurora/table_names.py

TICKER_FUNDAMENTALS = "ticker_fundamentals"
```

**Missing timezone in query**:
```python
# Fix: Add explicit timezone to src/data/queries.py:45

# Before
today = datetime.now().date()

# After
from zoneinfo import ZoneInfo
bangkok_tz = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok_tz).date()
```

#### API Fixes

**Missing validation**:
```python
# Fix: Add Pydantic validation to src/api/routes.py:23

from pydantic import BaseModel, validator

class ReportRequest(BaseModel):
    ticker: str

    @validator('ticker')
    def ticker_must_be_valid(cls, v):
        if not v or len(v) > 10:
            raise ValueError('Invalid ticker symbol')
        return v.upper()
```

#### Langfuse Fixes

**Missing @observe decorator**:
```python
# Fix: Add decorator to src/agent.py:45

from src.evaluation import observe

@observe(name="analyze_ticker")
def analyze_ticker(self, ticker: str):
    ...
```

**Missing flush() call**:
```python
# Fix: Add flush before return in src/handlers/lambda_handler.py:78

from src.evaluation import flush

def handler(event, context):
    result = process(event)
    flush()  # Add this line
    return result
```

**Missing score name constant**:
```python
# Fix: Add to src/config/langfuse.py

class SCORE_NAMES:
    FAITHFULNESS = "faithfulness"
    COMPLETENESS = "completeness"
    REASONING_QUALITY = "reasoning_quality"
    COMPLIANCE = "compliance"
    CONSISTENCY = "consistency"
    NEW_SCORE = "new_score"  # Add this
```

#### Frontend Fixes

**Missing TypeScript type**:
```typescript
// Fix: Add to frontend/twinbar/src/types/report.ts

export interface ChartPattern {
  type: string;
  startIndex: number;
  endIndex: number;
  confidence: number;
}
```

**Missing error handling**:
```typescript
// Fix: Add error boundary to frontend/twinbar/src/App.tsx

import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <Router>
        ...
      </Router>
    </ErrorBoundary>
  );
}
```

---

### Step 7: Generate Reconciliation Report

```markdown
# Reconciliation Report: {domain or invariant}

**Generated**: {timestamp}
**Scope**: {member pattern}

---

## Summary

| Metric | Value |
|--------|-------|
| Invariants checked | {count} |
| Members scanned | {count} |
| Violations found | {count} |
| Fixes generated | {count} |
| Auto-applicable | {count} |

**Overall Delta**: {total violations}
**Target Delta**: 0

---

## Violations by Level

### Level 4: Configuration
| Member | Invariant | Status |
|--------|-----------|--------|
| {file} | {invariant} | ❌ |

### Level 3: Infrastructure
[...]

### Level 2: Data
[...]

### Level 1: Service
[...]

### Level 0: User
[...]

---

## Convergence Actions

### Fix 1: {file_path}
[... detailed fix ...]

### Fix 2: {file_path}
[... detailed fix ...]

---

## Application Plan

### Phase 1: Configuration Fixes (Safe)
```bash
# These fixes are mechanical and safe to apply
{list of file edits}
```

### Phase 2: Code Fixes (Review Recommended)
```bash
# These fixes change behavior, review before applying
{list of file edits}
```

### Phase 3: Manual Actions Required
```bash
# These require human action (Doppler, AWS Console, etc.)
{list of manual steps}
```

---

## Verification

After applying fixes, verify with:

```bash
# Re-run invariant check
/invariant "{original goal}"

# Or run verification commands
{specific verification commands}
```

---

## Post-Reconciliation Checklist

- [ ] All Phase 1 fixes applied
- [ ] Phase 2 fixes reviewed and applied
- [ ] Phase 3 manual actions completed
- [ ] Verification passed (delta = 0)
- [ ] Changes committed with message: "fix: reconcile {domain} invariants"
```

---

### Step 8: Apply Fixes (if --apply)

**With --apply flag**:
```bash
# For each auto-applicable fix:
1. Show diff preview
2. Ask confirmation: "Apply this fix? [y/N]"
3. If confirmed, apply edit
4. Log action

# After all fixes:
5. Show summary of applied changes
6. Suggest commit message
7. Run verification commands
```

**Safety rules**:
- Never auto-apply without confirmation
- Never modify files outside member scope
- Always create backup before editing
- Log all changes for rollback

---

## Examples

### Example 1: Reconcile Deployment Domain

```bash
/reconcile deployment
```

**Output**:
```markdown
# Reconciliation Report: deployment

**Generated**: 2026-01-12T15:30:00+07:00
**Scope**: .github/workflows/*.yml, terraform/*.tf

---

## Summary

| Metric | Value |
|--------|-------|
| Invariants checked | 12 |
| Members scanned | 8 |
| Violations found | 3 |
| Fixes generated | 3 |
| Auto-applicable | 2 |

**Overall Delta**: 3
**Target Delta**: 0

---

## Violations by Level

### Level 4: Configuration

| Member | Invariant | Status |
|--------|-----------|--------|
| deploy-telegram.yml | LANGFUSE_RELEASE set | ✅ |
| deploy-line-bot.yml | LANGFUSE_RELEASE set | ❌ |
| deploy-scheduler.yml | LANGFUSE_RELEASE set | ❌ |

---

## Convergence Actions

### Fix 1: .github/workflows/deploy-line-bot.yml

**Violation**: Missing `LANGFUSE_RELEASE` environment variable
**Invariant**: All deploy workflows must set LANGFUSE_RELEASE
**Delta**: 1

**Action**:
```yaml
# Location: .github/workflows/deploy-line-bot.yml
# Add to env: section (after line 42)

env:
  ENVIRONMENT: ${{ github.ref == 'refs/heads/main' && 'stg' || 'dev' }}
  LANGFUSE_RELEASE: ${{ env.ENVIRONMENT }}-${{ github.ref_name }}-${{ steps.short-sha.outputs.sha }}
```

**Verification**:
```bash
grep "LANGFUSE_RELEASE" .github/workflows/deploy-line-bot.yml
```

**Confidence**: HIGH (mechanical fix)

---

### Fix 2: .github/workflows/deploy-scheduler.yml

**Violation**: Missing `LANGFUSE_RELEASE` environment variable
**Invariant**: All deploy workflows must set LANGFUSE_RELEASE
**Delta**: 1

**Action**:
```yaml
# Location: .github/workflows/deploy-scheduler.yml
# Add to env: section (after line 38)

env:
  LANGFUSE_RELEASE: ${{ env.ENVIRONMENT }}-${{ github.ref_name }}-${{ steps.short-sha.outputs.sha }}
```

**Verification**:
```bash
grep "LANGFUSE_RELEASE" .github/workflows/deploy-scheduler.yml
```

**Confidence**: HIGH (mechanical fix)

---

### Fix 3: Doppler Configuration (Manual)

**Violation**: LANGFUSE_RELEASE not set in local_dev config
**Invariant**: All environments must have LANGFUSE_RELEASE
**Delta**: 1

**Action**:
```bash
# Manual action required
doppler secrets set LANGFUSE_RELEASE "dev-local" -p dr-daily-report -c local_dev
```

**Verification**:
```bash
doppler secrets get LANGFUSE_RELEASE -p dr-daily-report -c local_dev
```

**Confidence**: HIGH (but requires manual execution)

---

## Application Plan

### Phase 1: Configuration Fixes (Safe)
```bash
# Auto-applicable fixes
Edit: .github/workflows/deploy-line-bot.yml
Edit: .github/workflows/deploy-scheduler.yml
```

### Phase 2: Manual Actions Required
```bash
# Requires Doppler access
doppler secrets set LANGFUSE_RELEASE "dev-local" -p dr-daily-report -c local_dev
```

---

## Verification

After applying fixes:

```bash
# Re-run invariant check
/invariant deployment "verify LANGFUSE_RELEASE"

# Or manual verification
grep -l "LANGFUSE_RELEASE" .github/workflows/*.yml | wc -l
# Expected: 3 (all deploy workflows)
```

---

## Post-Reconciliation Checklist

- [ ] Fix 1 applied (deploy-line-bot.yml)
- [ ] Fix 2 applied (deploy-scheduler.yml)
- [ ] Fix 3 completed (Doppler manual)
- [ ] Verification passed (delta = 0)
- [ ] Commit: "fix: reconcile LANGFUSE_RELEASE across all deploy workflows"
```

---

### Example 2: Reconcile After /invariant

```bash
/invariant "deploy new scoring feature"
# Output shows: ❌ Missing score name constant

/reconcile
```

**Output**:
```markdown
# Reconciliation Report: Last Invariant Check

**Context**: "deploy new scoring feature"
**Violations from /invariant**: 1

---

## Convergence Actions

### Fix 1: src/config/langfuse.py

**Violation**: New score "compliance" not in SCORE_NAMES constant
**Invariant**: Score names must be defined in SCORE_NAMES

**Action**:
```python
# Location: src/config/langfuse.py:15
# Add to SCORE_NAMES class

class SCORE_NAMES:
    FAITHFULNESS = "faithfulness"
    COMPLETENESS = "completeness"
    REASONING_QUALITY = "reasoning_quality"
    COMPLIANCE = "compliance"  # Add this line
    CONSISTENCY = "consistency"
```

**Verification**:
```bash
grep "COMPLIANCE" src/config/langfuse.py
```

**Confidence**: HIGH

---

Apply fix? Use: `/reconcile --apply`
```

---

### Example 3: Preview Only

```bash
/reconcile langfuse --preview
```

**Output**:
```markdown
# Reconciliation Preview: langfuse

**Mode**: Preview only (no changes will be made)

## Would Fix

1. **src/handlers/report_worker.py:89**
   - Add: `flush()` call before return

2. **src/workflow/workflow_nodes.py:156**
   - Add: `@observe(name="generate_report")` decorator

3. **.github/workflows/deploy-telegram.yml:45**
   - Add: `LANGFUSE_RELEASE` env var

---

To apply fixes, run:
```bash
/reconcile langfuse --apply
```
```

---

## Integration with Invariant Workflow

### Complete Workflow

```bash
# 1. Before implementation: Know what must hold
/invariant "add new API endpoint"
# → Generates checklist of invariants

# 2. Implement feature
# ... write code ...

# 3. Check for violations
/invariant "add new API endpoint"
# → Shows: 2 violations found

# 4. Generate fixes
/reconcile api
# → Generates specific fixes for violations

# 5. Apply fixes
/reconcile api --apply
# → Applies fixes with confirmation

# 6. Verify convergence
/invariant "add new API endpoint"
# → All invariants satisfied (delta = 0)

# 7. Commit
git commit -m "feat: add new API endpoint with invariant compliance"
```

### Incident Response Workflow

```bash
# 1. Incident: "Traces not appearing in Langfuse"
/invariant langfuse "trace submission"
# → Reveals: Level 1 invariant "flush() called" violated

# 2. Find all violations
/reconcile langfuse
# → Scans all Langfuse-related code
# → Finds 3 handlers missing flush()

# 3. Fix all violations
/reconcile langfuse --apply
# → Adds flush() to all handlers

# 4. Verify
/invariant langfuse "trace submission"
# → All invariants satisfied

# 5. Deploy fix
# ... deploy ...
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| Apply without review | May break working code | Use --preview first |
| Fix symptoms not cause | Violations return | Find root cause |
| Skip verification | Don't know if fixed | Always run /invariant after |
| Reconcile too narrow | Miss related violations | Use domain-wide reconcile |
| Ignore LOW confidence | May need human insight | Review before applying |

---

## Tips

### Do
- **Preview first** with `--preview` flag
- **Review fixes** before applying
- **Verify after** with `/invariant`
- **Commit with context** explaining what was reconciled
- **Use domain scope** to catch related violations

### Don't
- **Blindly apply** all fixes
- **Skip verification** after reconciliation
- **Ignore LOW confidence** fixes
- **Reconcile in production** without testing
- **Apply partial fixes** (fix all or none per invariant)

---

## See Also

- [/invariant](./invariant.md) - Identify invariants for a goal
- [/validate](./validate.md) - Check if claims hold
- [Invariants Directory](../invariants/) - Domain-specific invariant files
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Detailed guide

---

*Command: /reconcile*
*Related: Principle #25 (Behavioral Invariant Verification)*
*Completes the invariant feedback loop: detect → fix → verify*
