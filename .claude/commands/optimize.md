---
name: optimize
description: Performance optimization workflow with invariant preservation (delta = 0)
accepts_args: true
arg_schema:
  - name: target
    required: true
    description: What to optimize (e.g., "Lambda cold start", "API latency", "Aurora queries")
  - name: scope
    required: false
    description: Scope of optimization - quick (1-2 changes), standard (full workflow), thorough (with A/B testing)
tier: 2
depends:
  - /perf
  - /design
  - /invariant
  - /reconcile
composition:
  - command: perf
  - command: design
  - command: invariant
  - skill: performance-investigation
---

# Optimize Command

**Purpose**: Performance optimization workflow that improves metrics while preserving behavioral invariants (delta = 0).

**Mode**: `optimize` (Tuple Effect: Transforms Constraints while maintaining Invariant stability)

**Tier**: 2 (Composed from `/perf`, `/design`, `/invariant`, `/reconcile`)

---

## Core Principle

> "Optimize with guardrails" - Performance improvements must not break existing functionality.

**Success criteria**:
```
Performance ↑  AND  Invariant delta = 0
```

If invariants break, optimization fails regardless of performance gain.

---

## Quick Reference

```bash
# Standard optimization workflow
/optimize "Lambda cold start latency"
/optimize "API response time"
/optimize "Aurora query performance"

# With scope modifier
/optimize "telegram-api P95 latency" quick      # 1-2 targeted changes
/optimize "report generation time" standard     # Full workflow (default)
/optimize "overall system latency" thorough     # Includes A/B testing
```

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    /optimize workflow                        │
│                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │
│  │ MEASURE │ → │ DESIGN  │ → │IMPLEMENT│ → │ VERIFY  │    │
│  │ /perf   │   │ /design │   │  (user) │   │/invariant│   │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘    │
│       ↑                                          │         │
│       └──────── if delta ≠ 0: ROLLBACK ──────────┘         │
│                                                             │
│  Invariant: performance↑ AND delta = 0                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: MEASURE (Baseline)

**Command**: `/perf status` + `/perf diagnose {target}`

**Purpose**: Establish baseline metrics and identify optimization targets.

**Output**:
```markdown
## Baseline Metrics

**Target**: Lambda cold start latency
**Time**: 2026-01-15 14:30 UTC
**Environment**: dev

### Current State
| Metric | Value | Target | Gap |
|--------|-------|--------|-----|
| P50 latency | 1.2s | 0.5s | -0.7s |
| P95 latency | 5.2s | 2.0s | -3.2s |
| P99 latency | 8.5s | 3.0s | -5.5s |
| Cold start % | 25% | 5% | -20% |
| Error rate | 2.1% | <1% | -1.1% |

### Bottleneck Analysis
1. **Cold start** (45% of latency) - Primary target
2. **Aurora query** (32% of latency) - Secondary target
3. **LLM call** (18% of latency) - Optimized recently

### Optimization Potential
- Addressing cold start alone could reduce P95 by 60%
- Combined improvements could achieve target metrics
```

---

## Phase 2: IDENTIFY INVARIANTS

**Command**: `/invariant "optimization: {target}"`

**Purpose**: Identify what MUST NOT break during optimization.

**Output**:
```markdown
## Invariants to Preserve

### Level 0 (User)
- [ ] User can request and receive reports
- [ ] Response time < 30s (timeout threshold)
- [ ] Thai language output renders correctly

### Level 1 (Service)
- [ ] Lambda returns 200 for valid requests
- [ ] Error rate < 1%
- [ ] No increase in 5xx errors

### Level 2 (Data)
- [ ] Report content accuracy unchanged
- [ ] All placeholders replaced
- [ ] No data corruption

### Level 3 (Infrastructure)
- [ ] Lambda → Aurora connectivity maintained
- [ ] Lambda → S3 connectivity maintained
- [ ] Memory usage < 90% of allocation

### Level 4 (Configuration)
- [ ] Environment variables unchanged
- [ ] IAM permissions sufficient
- [ ] VPC security groups allow traffic

### Performance Invariants (from optimization)
- [ ] Error rate does not increase
- [ ] P99 latency does not increase
- [ ] Functionality unchanged
```

---

## Phase 3: DESIGN (Optimization Plan)

**Command**: `/design performance "{target}"`

**Purpose**: Create optimization plan with expected improvements.

**Output**:
```markdown
## Optimization Plan: Lambda Cold Start

### Approach 1: Provisioned Concurrency (Recommended)
**Expected improvement**: P95 5.2s → 2.0s (62% reduction)
**Effort**: Low (Terraform only)
**Risk**: Low
**Cost**: +$15/month

**Changes**:
```hcl
# terraform/telegram_api.tf
resource "aws_lambda_provisioned_concurrency_config" "telegram_api" {
  function_name                     = aws_lambda_function.telegram_api.function_name
  provisioned_concurrent_executions = 5
  qualifier                         = aws_lambda_alias.telegram_api_live.name
}
```

### Approach 2: Increase Memory
**Expected improvement**: Duration -10-20%
**Effort**: Low (Terraform only)
**Risk**: Low
**Cost**: +$8/month

### Approach 3: Optimize Imports (Code)
**Expected improvement**: Cold start -500ms
**Effort**: Medium (code refactoring)
**Risk**: Medium (regression risk)

### Recommended Sequence
1. Apply Approach 1 (quick win, low risk)
2. Measure improvement
3. If target not met, apply Approach 2
4. If still not met, consider Approach 3

### Rollback Plan
- Remove provisioned concurrency config
- Revert memory to 512MB
- Terraform apply with previous state
```

---

## Phase 4: IMPLEMENT (User-Controlled)

**Purpose**: Apply changes with user confirmation at each step.

**Workflow**:
```markdown
## Implementation

### Step 1 of 2: Add Provisioned Concurrency

**What I'll do**: Add Terraform resource for provisioned concurrency
**Why**: Eliminate cold starts for telegram-api Lambda
**Reversible**: Yes (remove resource)
**Risk**: Low

**File**: `terraform/telegram_api.tf`
**Change**:
```hcl
+ resource "aws_lambda_provisioned_concurrency_config" "telegram_api" {
+   function_name                     = aws_lambda_function.telegram_api.function_name
+   provisioned_concurrent_executions = 5
+   qualifier                         = aws_lambda_alias.telegram_api_live.name
+ }
```

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]

---

### Step 2 of 2: Apply Terraform

**What I'll do**: Run `terraform apply` to provision resources
**Why**: Activate provisioned concurrency
**Reversible**: Yes (terraform destroy resource)
**Risk**: Low

**Command**: `terraform apply -target=aws_lambda_provisioned_concurrency_config.telegram_api`

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]
```

---

## Phase 5: VERIFY (Delta = 0)

**Command**: `/invariant "optimization: {target}"` (re-run) + `/perf status`

**Purpose**: Confirm invariants preserved AND performance improved.

**Output**:
```markdown
## Verification Results

### Invariant Check
| Level | Invariant | Before | After | Delta |
|-------|-----------|--------|-------|-------|
| 0 | User can request reports | ✅ | ✅ | 0 |
| 1 | Lambda returns 200 | ✅ | ✅ | 0 |
| 1 | Error rate < 1% | ✅ | ✅ | 0 |
| 2 | Report accuracy | ✅ | ✅ | 0 |
| 3 | Aurora connectivity | ✅ | ✅ | 0 |
| 4 | Env vars unchanged | ✅ | ✅ | 0 |

**Invariant Delta**: 0 ✅

### Performance Comparison
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| P50 latency | 1.2s | 0.8s | 33% ✅ |
| P95 latency | 5.2s | 1.9s | 63% ✅ |
| P99 latency | 8.5s | 2.8s | 67% ✅ |
| Cold start % | 25% | 2% | 92% ✅ |
| Error rate | 2.1% | 0.8% | 62% ✅ |

**Performance Improvement**: Yes ✅

### Final Status
```
✅ OPTIMIZATION SUCCESSFUL

Performance improved:
- P95 latency: 5.2s → 1.9s (63% reduction)
- Cold start: 25% → 2% (92% reduction)

Invariants preserved:
- All 6 invariants: delta = 0

Cost impact: +$15/month
```
```

---

## Scope Modifiers

### `quick` - Targeted Changes

```bash
/optimize "Lambda latency" quick
```

- Skips detailed design phase
- Applies 1-2 high-confidence changes
- Faster verification
- Best for: Known optimizations, minor tuning

### `standard` (default) - Full Workflow

```bash
/optimize "Lambda latency"
/optimize "Lambda latency" standard
```

- Full 5-phase workflow
- Comprehensive invariant checking
- Best for: Most optimizations

### `thorough` - With A/B Testing

```bash
/optimize "API response time" thorough
```

- Includes A/B testing phase
- Statistical validation of improvement
- Extended monitoring period
- Best for: Critical paths, production optimizations

---

## Rollback Procedure

If invariants break (delta ≠ 0):

```markdown
## Rollback Required

**Reason**: Invariant violation detected
**Violated**: Level 1 - Error rate increased from 0.8% to 3.2%

### Automatic Rollback Steps

1. **Revert Terraform changes**
   ```bash
   git checkout HEAD~1 -- terraform/telegram_api.tf
   terraform apply
   ```

2. **Verify rollback**
   ```bash
   /perf status
   /invariant "optimization: Lambda latency"
   ```

3. **Confirm restoration**
   - Error rate returned to baseline
   - All invariants: delta = 0

### Post-Rollback Analysis
- Why did optimization break invariants?
- What was missed in design phase?
- How to prevent next time?
```

---

## Integration with Thinking Tuple

```
Tuple = (Constraints, Invariant, Principles, Strategy, Check)

Constraints:
- Current performance metrics (from /perf)
- Infrastructure state (Terraform)
- Cost budget

Invariant:
- Performance targets (P95 < 2s)
- Behavioral invariants (delta = 0)

Principles:
- #2: Progressive Evidence
- #25: Behavioral Invariant Verification

Strategy:
- [/perf diagnose] → [/design] → [implement] → [/invariant]

Check:
- Performance improved? ✅/❌
- Invariant delta = 0? ✅/❌
```

---

## Examples

### Example 1: Lambda Cold Start Optimization

```bash
/optimize "Lambda cold start for telegram-api"
```

**Workflow**:
1. `/perf diagnose telegram-api` → Identifies 25% cold start rate
2. `/invariant` → Lists behavioral contracts
3. `/design performance` → Recommends provisioned concurrency
4. Implement → User approves Terraform change
5. Verify → P95 improved, invariants preserved

### Example 2: Aurora Query Optimization

```bash
/optimize "Aurora query performance for daily_prices table"
```

**Workflow**:
1. `/perf trace aurora` → Identifies slow queries
2. `/invariant` → Data integrity, schema stability
3. `/design schema` → Recommends index addition
4. Implement → Migration with idempotent pattern
5. Verify → Query time reduced, data intact

### Example 3: Quick Memory Tuning

```bash
/optimize "Lambda memory" quick
```

**Workflow**:
1. Quick measurement → Memory at 94%
2. Skip detailed design → Known pattern
3. Implement → Increase to 1024MB
4. Quick verify → Memory usage healthy, no errors

---

## Related Commands

| Command | Relationship |
|---------|--------------|
| `/perf` | Phase 1: Measurement and diagnostics |
| `/design` | Phase 3: Optimization planning |
| `/invariant` | Phase 2 & 5: Invariant identification and verification |
| `/reconcile` | If invariants violated, converge back |
| `/handholding` | Can wrap `/optimize` for step-by-step guidance |

---

## Invariant Files Referenced

- `.claude/invariants/deployment-invariants.md` - Lambda, Terraform
- `.claude/invariants/frontend-invariants.md` - Web Vitals, performance
- `.claude/invariants/data-invariants.md` - Aurora, schema
- `.claude/invariants/system-invariants.md` - Critical path

---

## Anti-Patterns

### 1. Optimizing Without Measurement

```bash
# ❌ Bad: Jump straight to solution
"Add provisioned concurrency"

# ✅ Good: Measure first
/optimize "Lambda latency"  # Measures, then recommends
```

### 2. Ignoring Invariants

```bash
# ❌ Bad: Performance at any cost
"Make it faster, don't care about errors"

# ✅ Good: Preserve invariants
/optimize "Lambda latency"  # Checks delta = 0
```

### 3. Big Bang Changes

```bash
# ❌ Bad: Multiple changes at once
"Add concurrency + increase memory + change VPC + add caching"

# ✅ Good: Incremental with verification
/optimize "Lambda latency"  # One change → verify → next change
```

---

## See Also

- `.claude/commands/perf.md` - Performance monitoring
- `.claude/commands/invariant.md` - Invariant identification
- `.claude/commands/design.md` - Solution design
- `.claude/skills/performance-investigation/` - Optimization patterns
- `docs/guides/behavioral-invariant-verification.md` - Invariant framework
