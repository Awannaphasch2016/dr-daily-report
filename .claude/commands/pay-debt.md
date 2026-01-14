---
name: pay-debt
description: Identify technical debt with payment plan using complexity and hotspot analysis
accepts_args: true
arg_schema:
  - name: scope
    required: true
    description: "Directory or file path to analyze (e.g., 'src/workflow/', 'src/agent/')"
  - name: budget
    required: false
    description: "Optional effort budget: quick, sprint, quarter (default: sprint)"
composition:
  - skill: refacter
---

# Pay-Debt Command (Technical Debt Management)

**Purpose**: Identify technical debt with a concrete "payment plan" - prioritized actions with effort estimates and interest calculations

**Core Principle**: Technical debt is a financial metaphor. This command makes it concrete: what do we owe, what's the interest, and what's our repayment plan?

**When to use**:
- Before sprint planning -> Identify debt to pay down
- After feature completion -> Assess debt introduced
- Periodic health check -> Monitor debt trajectory
- When code feels "slow" -> Quantify the pain

**When NOT to use**:
- Immediate refactoring -> Use `/refacter` skill directly
- One-off complexity check -> Use complexity scripts directly
- Already know what to fix -> Just fix it

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `analyze`

When `/pay-debt` executes, it surfaces debt inventory and payment strategy:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **REVEAL**: Surfaces complexity metrics, hotspots, debt inventory |
| **Invariant** | **DEFINE**: Sets debt reduction targets (complexity thresholds) |
| **Principles** | **ADD**: Refactoring principles from refacter skill |
| **Strategy** | Generates prioritized payment plan with effort estimates |
| **Check** | Outputs before/after complexity targets for verification |

**Debt Inventory Example**:
```yaml
debt_inventory:
  critical:
    - file: "src/workflow/workflow_nodes.py"
      complexity: 45
      churn: 32
      interest: "High - blocks new features"
      principal: "2-3 days refactoring"
  high:
    - file: "src/agent/scoring.py"
      complexity: 28
      churn: 18
      interest: "Medium - slows debugging"
      principal: "1 day refactoring"
payment_plan:
  sprint_1:
    - "Extract methods from workflow_nodes.py"
    - "Add missing tests (safety net)"
  sprint_2:
    - "Simplify scoring.py conditionals"
```

---

## Local Check (Mode Completion Criteria)

The `/pay-debt` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Scope Analyzed** | Complexity and hotspot analysis completed |
| **Debt Inventoried** | All P0/P1/P2 items identified with metrics |
| **Interest Calculated** | Cost of NOT fixing documented |
| **Payment Plan Generated** | Prioritized actions with effort estimates |
| **Budget Fit** | Plan fits specified budget (quick/sprint/quarter) |

**Check Result Mapping**:
- **PASS**: Debt inventory complete, payment plan actionable
- **PARTIAL**: Some areas couldn't be analyzed -> note limitations
- **FAIL**: Unable to generate meaningful payment plan

---

## Quick Reference

```bash
# Analyze a directory with default budget (sprint)
/pay-debt "src/workflow/"

# Analyze with specific budget
/pay-debt "src/" quick        # Minimal effort, quick wins only
/pay-debt "src/" sprint       # One sprint worth of work (default)
/pay-debt "src/" quarter      # Quarterly debt reduction plan

# Focus on specific component
/pay-debt "src/agent/"
/pay-debt "frontend/twinbar/src/"
```

---

## Output Format

```markdown
## Technical Debt Analysis: {scope}

**Budget**: {quick | sprint | quarter}
**Analysis Date**: {YYYY-MM-DD}

---

## Debt Inventory

### 🔥 Critical (P0) - Pay Immediately
High churn + High complexity = Blocking work

| File | CC | Cognitive | Churn | Interest |
|------|----|-----------+-------|----------|
| {file1} | {cc} | {cog} | {commits} | {impact} |

**Total Principal**: {X} days

### ⚠️ High (P1) - Pay This Sprint
High churn OR High complexity

| File | CC | Cognitive | Churn | Interest |
|------|----|-----------+-------|----------|
| {file2} | {cc} | {cog} | {commits} | {impact} |

**Total Principal**: {Y} days

### 📝 Medium (P2) - Schedule Payment
Moderate metrics, accumulating interest

| File | CC | Cognitive | Churn | Interest |
|------|----|-----------+-------|----------|
| {file3} | {cc} | {cog} | {commits} | {impact} |

**Total Principal**: {Z} days

### ✅ Low (P3) - Monitor Only
Acceptable metrics, no immediate action

{Summary of healthy code}

---

## Interest Calculation

**What are we paying if we DON'T fix?**

| Debt Item | Monthly Interest | Compounding Effect |
|-----------|------------------|-------------------|
| {critical_item} | +{X}h debugging | Blocks {feature} |
| {high_item} | +{Y}h per change | Slows velocity |

**Total Monthly Interest**: ~{Z} hours wasted

---

## Payment Plan: {budget}

### Phase 1: Safety Net
Before refactoring, ensure test coverage:
- [ ] Add tests for {file1} ({effort})
- [ ] Add tests for {file2} ({effort})

### Phase 2: Critical Debt (P0)
Estimated: {X} days

1. **{Refactoring 1}**
   - File: {file}
   - Pattern: {Extract Method | Simplify Conditionals | ...}
   - Effort: {hours/days}
   - Expected Improvement: CC {before} → {after}

2. **{Refactoring 2}**
   - File: {file}
   - Pattern: {pattern}
   - Effort: {hours/days}
   - Expected Improvement: Cognitive {before} → {after}

### Phase 3: High Debt (P1)
Estimated: {Y} days

{Similar structure}

### Phase 4: Medium Debt (P2)
{If budget allows}

---

## Verification Criteria

After payment, verify:
```bash
# Re-run complexity analysis
python .claude/skills/refacter/scripts/analyze_complexity.py {scope}

# Targets:
# - No file with CC > 15 (was: {X} files)
# - No file with Cognitive > 20 (was: {Y} files)
# - All tests passing
```

---

## Summary

| Metric | Before | Target | Change |
|--------|--------|--------|--------|
| P0 Items | {n} | 0 | -{n} |
| P1 Items | {m} | {m/2} | -{m/2} |
| Avg Complexity | {x} | {y} | -{delta} |
| Monthly Interest | {z}h | {w}h | -{saved}h |

**ROI**: {principal} days investment → {interest_saved} hours/month saved
**Break-even**: {months} months
```

---

## Budget Levels

### `quick` - Quick Wins Only (1-2 days)
- Focus on P0 only
- Extract obvious methods
- No architectural changes
- Minimal test additions

### `sprint` - One Sprint (5-10 days) [DEFAULT]
- P0 + P1 debt
- Add safety net tests
- Refactoring patterns
- Some architectural improvements

### `quarter` - Quarterly Investment (20-40 days)
- Full P0 + P1 + P2
- Comprehensive test coverage
- Architectural refactoring
- Documentation updates

---

## Execution Flow

### Step 1: Run Complexity Analysis

```bash
python .claude/skills/refacter/scripts/analyze_complexity.py {scope}
```

Extract:
- Cyclomatic complexity (CC) per function
- Cognitive complexity per function
- Lines of code (LOC)
- Parameter count

### Step 2: Run Hotspot Analysis

```bash
python .claude/skills/refacter/scripts/analyze_hotspots.py {scope}
```

Extract:
- Commit frequency (churn)
- Recent change dates
- Authors (for context)

### Step 3: Calculate Priority Matrix

```
For each file:
  IF churn > 15 AND complexity > 10:
    priority = P0 (Critical)
  ELIF churn > 15 OR complexity > 10:
    priority = P1 (High)
  ELIF churn > 5 OR complexity > 5:
    priority = P2 (Medium)
  ELSE:
    priority = P3 (Low)
```

### Step 4: Estimate Principal (Effort)

```
For each debt item:
  IF CC > 20: principal += 2 days
  ELIF CC > 10: principal += 1 day

  IF cognitive > 25: principal += 1 day
  ELIF cognitive > 15: principal += 0.5 days

  IF LOC > 200: principal += 1 day

  IF no tests exist: principal += 0.5 days (safety net)
```

### Step 5: Calculate Interest

```
For P0 items:
  monthly_interest = churn * 0.5 hours (debugging overhead)

For P1 items:
  monthly_interest = churn * 0.25 hours

Total monthly interest = sum of all items
```

### Step 6: Generate Payment Plan

Based on budget:
- `quick`: Include only P0, limit to 2 days
- `sprint`: Include P0 + P1, limit to 10 days
- `quarter`: Include P0 + P1 + P2, limit to 40 days

### Step 7: Output Report

Generate markdown following output format.

---

## Examples

### Example 1: Sprint Planning

```bash
/pay-debt "src/workflow/" sprint
```

**Use case**: Before sprint planning, identify which tech debt to include in sprint backlog.

### Example 2: Quick Health Check

```bash
/pay-debt "src/" quick
```

**Use case**: Quick assessment before a release to see if any critical debt blocks release.

### Example 3: Quarterly Review

```bash
/pay-debt "src/" quarter
```

**Use case**: Quarterly planning to allocate dedicated refactoring time.

---

## Integration with Other Commands

### /pay-debt -> /step
```bash
/pay-debt "src/workflow/"      # Identify debt
# Select specific debt item
/step "refactor workflow_nodes.py extract_methods"
```

### /pay-debt -> /invariant
```bash
/pay-debt "src/"               # Get complexity targets
/invariant "reduce complexity" # Track as invariant
# After refactoring:
/invariant "reduce complexity" # Verify targets met
```

### /pay-debt -> /journal
```bash
/pay-debt "src/agent/"         # Analyze debt
# After paying debt:
/journal pattern "Refactored scoring.py using Extract Method"
```

---

## Relationship to /refacter Skill

| Aspect | `/refacter` Skill | `/pay-debt` Command |
|--------|-------------------|---------------------|
| **Invocation** | Auto-discovered when refactoring | Explicit `/pay-debt scope` |
| **Focus** | HOW to refactor (patterns, techniques) | WHAT to refactor (prioritization) |
| **Output** | Refactored code | Debt inventory + payment plan |
| **Scope** | Single file/function | Directory/component |
| **Metaphor** | Technical | Financial |

**Workflow**:
```
/pay-debt → Identify what to pay → /refacter skill → HOW to pay
```

---

## Best Practices

### Do
- Run before sprint planning
- Include in quarterly reviews
- Use budget levels appropriately
- Track debt trends over time
- Celebrate debt payments (it's progress!)

### Don't
- Treat all debt as equal (use priority)
- Pay debt without tests (risky)
- Ignore interest calculations (they compound)
- Over-engineer payment plans (start small)
- Forget to verify after payment

---

## See Also

- `.claude/skills/refacter/SKILL.md` - Refactoring patterns and techniques
- `.claude/skills/refacter/CODE-COMPLEXITY.md` - Complexity metrics guide
- `.claude/skills/refacter/HOTSPOT-ANALYSIS.md` - Code churn analysis
- `.claude/commands/refactor.md` - Single-file refactoring command
- `.claude/commands/invariant.md` - Track debt reduction as invariant
