# Thinking Tuple Protocol Guide

## Overview

The Thinking Tuple Protocol is the **runtime composition mechanism** that forces all layers (Principles, Skills, Commands, Thinking Process Architecture) to be applied together at each reasoning step. It's not a new layer—it's the glue that ensures disciplined reasoning in complex and long-running tasks.

**Core Insight**: Layers (principles, skills, commands) are static definitions. The Tuple is what forces their composition at runtime, enabling bounded error growth.

---

## Why This Matters

### The Problem

| What We Have | What Happens | The Gap |
|--------------|--------------|---------|
| Principles (25+) | May or may not be applied | No enforcement |
| Skills (10+) | Auto-discovered sometimes | Inconsistent |
| Commands (50+) | User must invoke | Manual |
| Thinking Process | Guides but doesn't enforce | Descriptive only |

**Result**: Claude can complete tasks without systematically applying all relevant guidance, leading to:
- Stale assumptions compounding over multiple steps
- Principles forgotten mid-task
- No checkpoints for long-running work
- Error growth proportional to task length

### The Solution

The Thinking Tuple forces a structured checkpoint at each significant reasoning step:

```
Tuple = (Constraints, Invariant, Principles, Process, Actions, Check)
```

Each component draws from existing layers, ensuring they're all composed together.

---

## Tuple Structure

### 1. Constraints (Start State)

**Question**: What do we have/know right now?

**Sources**:
- Previous tuple outputs
- Environmental facts (files, data, tools)
- Resource limits (time, permissions)
- Blockers discovered

**Template**:
```markdown
## Constraints

**Known facts**:
- {What we know to be true}
- {Results from previous steps}

**Available resources**:
- Tools: {Read, Write, Bash, MCP, etc.}
- Data: {What data we have access to}

**Current partial state**:
- {What has been completed so far}

**Limits/Blockers**:
- {Known constraints or obstacles}
```

---

### 2. Invariant (Target State)

**Question**: What must be true at the end of this step?

**Sources**:
- `/invariant` command output
- Task success criteria
- Safety boundaries

**Maps to Principle #25 Hierarchy**:
| Level | Type | Example |
|-------|------|---------|
| 4 | Configuration | Env var set |
| 3 | Infrastructure | Lambda → Aurora works |
| 2 | Data | Data is fresh |
| 1 | Service | Lambda returns 200 |
| 0 | User | User can complete flow |

**Template**:
```markdown
## Invariant

**Must be true after this step**:
- {Specific measurable condition}

**Success criteria**:
- {How we know we succeeded}

**Safety boundaries**:
- {What must NOT happen}

**Invariant level focus**:
- Level {N}: {condition}
```

---

### 3. Principles (Navigation Rules)

**Question**: What tradeoffs guide our decisions?

**Sources**:
- CLAUDE.md Tier-0 (always active)
- Task-specific clusters (loaded based on task type)

**Selection Logic**:
```
If deploying → Load deployment-principles (#6, #11, #15, #19, #21)
If testing   → Load testing-principles (#10, #19)
If data work → Load data-principles (#3, #5, #14, #16)
...
```

**Template**:
```markdown
## Principles

**Tier-0 (always active)**:
- #1 Defensive Programming: {how it applies here}
- #2 Progressive Evidence: {how it applies here}

**Task-specific**:
- #{N} {Name}: {why selected, how it guides}

**Tradeoff being made**:
- Optimizing for: {X}
- Accepting as cost: {Y}
```

---

### 4. Process (Thinking Mode)

**Question**: What cognitive strategy should we use now?

**Sources**:
- Thinking Process Architecture (Sections 4, 5, 6, 11)

**Mode Selection**:

| Mode | When to Use | Section Reference |
|------|-------------|-------------------|
| **diverge** | Need more options, exploring solution space | Section 4 |
| **converge** | Have options, need to select/refine | Section 4 |
| **decompose** | Problem too large, need smaller pieces | Section 5 |
| **compare** | Multiple viable options, need evaluation | Section 11 |
| **reframe** | Current approach not working | Section 6 |
| **escape** | Stuck in local optimum | Section 6 |

**Mode Transitions**:
```
diverge ──────► converge ──────► decompose
    ▲               │                │
    │               ▼                ▼
    └────────── reframe ◄────── compare
                    │
                    ▼
                 escape
                    │
                    └──────► diverge (restart)
```

**Template**:
```markdown
## Process

**Mode**: {diverge | converge | decompose | compare | reframe | escape}

**Why this mode**:
- {Rationale for selection}

**Expected output**:
- {What this mode will produce}
```

---

### 5. Actions (Execution Steps)

**Question**: What concrete steps do we take now?

**Sources**:
- Skills layer (patterns for specific domains)
- Tool capabilities (Read, Write, Bash, MCP)
- Command compositions

**Template**:
```markdown
## Actions

1. {Action 1}
   - Tool: {specific tool}
   - Expected output: {what we expect}

2. {Action 2}
   - Tool: {specific tool}
   - Expected output: {what we expect}

**Dependency order**: {1 → 2 → 3 | 1,2 parallel → 3}
```

---

### 6. Check (Verification)

**Question**: Did our actions satisfy the invariant?

**Sources**:
- Progressive Evidence Strengthening (Principle #2)
- Invariant Feedback Loop (Section 11.5)

**Evidence Levels**:
| Layer | Type | Strength |
|-------|------|----------|
| 1 | Surface | Status codes, exit codes (weakest) |
| 2 | Content | Payloads, data structures |
| 3 | Observability | Logs, traces |
| 4 | Ground truth | Actual state changes (strongest) |

**Check Results**:
- **PASS**: Proceed to next step or claim "done"
- **PARTIAL**: Critical invariant? If yes → FAIL path. If no → proceed with caution
- **FAIL**: Update Constraints, possibly change Process, spin new tuple

**Template**:
```markdown
## Check

**Invariant satisfied?**: {PASS | PARTIAL | FAIL}

**Evidence collected**:
- Layer 1: {status codes, exit codes}
- Layer 2: {payloads, outputs}
- Layer 3: {logs, traces}
- Layer 4: {actual state changes}

**If PASS**:
→ {Proceed to next step | Claim "done"}

**If FAIL**:
→ Updated Constraints: {what we learned}
→ Process change: {if needed}
→ Spin new tuple
```

---

## Layer Integration

The Tuple composes existing layers at runtime:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING LAYERS                               │
├─────────────────────────────────────────────────────────────────┤
│ CLAUDE.md Principles    ────────► Principles slot               │
│ Skills                  ────────► Actions slot (patterns)       │
│ Slash Commands          ────────► Pre-assembled tuples          │
│ Thinking Process Arch   ────────► Process slot (modes)          │
│ /invariant command      ────────► Invariant slot                │
│ Progressive Evidence    ────────► Check slot (evidence levels)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tuple Chaining for Long-Running Tasks

For tasks spanning multiple steps, chain tuples:

```
Frame₀: (C₀, I₀, P₀, Proc₀, A₀, Check₀)
    │
    ▼ (Check passes, update constraints)
Frame₁: (C₁, I₁, P₁, Proc₁, A₁, Check₁)
    │
    ▼ (Check passes, update constraints)
Frame₂: (C₂, I₂, P₂, Proc₂, A₂, Check₂)
    │
    ...
    │
    ▼ (Final invariant satisfied)
DONE: All invariants verified (δ = 0)
```

**Key insight**: Each tuple is a **checkpoint with full context**. If Check fails, spin a new tuple with updated constraints—don't abandon the run.

---

## Error Bound Analysis

### Without Tuples

```
Error ∝ (steps × drift_rate)

Problems:
- Stale assumptions compound silently
- No recovery mechanism
- Debugging is archaeology
- Error grows unbounded with task length
```

### With Tuples

```
Error ∝ (undetected_drift × steps_between_checks)

Benefits:
- Constraints refreshed each tuple
- Failed Check → new tuple with updated state
- Each tuple is observable checkpoint
- Error bounded by check frequency
```

**Mathematical intuition**:
- If Check frequency = every step, and Check quality is high, error growth is bounded
- Drift detected at Check → corrected in next tuple
- Long-running tasks become sequences of verified checkpoints

---

## Check Failure Protocol

When Check reveals violations:

### Step 1: Update Constraints
Add what was learned to the Constraints for the next tuple:
```markdown
**New constraints from failed Check**:
- {What we learned doesn't work}
- {New facts discovered}
- {Resources now unavailable}
```

### Step 2: Consider Process Change
Maybe the thinking mode needs to change:
- Was converging but need more options? → Switch to diverge
- Stuck in local optimum? → Switch to escape
- Problem too large? → Switch to decompose

### Step 3: Spin New Tuple
Don't abandon the run. Create a new tuple with:
- Updated Constraints
- Same or updated Process mode
- Same Invariant (unless scope changed)

---

## When to Use Tuples

| Condition | Tuple Required? | Rationale |
|-----------|----------------|-----------|
| Simple lookup | No | Single action, no drift possible |
| Single-action task | No | No checkpoints needed |
| Complex task (> 3 steps) | Yes | Drift possible between steps |
| Long-running task | Yes (at each step) | Multiple checkpoints needed |
| After Check failure | Yes (spin new) | Recovery mechanism |
| Autonomous mode | Yes (always) | No human oversight |

---

## Explicit vs Implicit Tuples

### Explicit Tuple (via `/step`)

Use `/step` command to force explicit tuple instantiation:

```bash
/step "deploy new scoring feature"
```

**When to use explicit**:
- Complex tasks requiring visible structure
- When you want to audit reasoning
- Long-running autonomous work

### Implicit Tuple (mental model)

For shorter tasks, apply tuple structure mentally without explicit output:
- Still think through Constraints, Invariant, Principles, Process, Actions, Check
- But don't produce explicit document

---

## Examples

### Example 1: Deployment Step (Converge Mode)

```markdown
# Thinking Tuple: Deploy new scoring feature

## 1. Constraints
**Known**: Code merged to dev, tests passing locally, Lambda exists
**Resources**: AWS CLI, GitHub Actions, Doppler secrets
**Partial state**: Code ready, not deployed
**Limits**: Must not disrupt existing /report endpoint

## 2. Invariant
**Must be true**: Lambda updated, /score endpoint responds 200, Langfuse traces appear
**Success criteria**: POST /score returns valid response, CloudWatch shows no errors
**Safety**: Existing /report must still work

## 3. Principles
**Tier-0**: #1 (validate at startup), #2 (verify through ground truth)
**Task-specific**: #6 (use waiters), #11 (same artifact through envs)
**Tradeoff**: Safety over speed (full verification)

## 4. Process
**Mode**: converge
**Rationale**: Clear plan exists, need execution and verification

## 5. Actions
1. Push to trigger GitHub Actions (Bash: git push)
2. Wait for deployment (Bash: gh run watch --exit-status)
3. Invoke Lambda health check (Bash: aws lambda invoke)
4. Verify Langfuse trace (WebFetch: Langfuse dashboard)
5. Test /report regression (Bash: curl)

## 6. Check
**Result**: PASS
**Evidence**:
- Layer 1: Exit code 0, HTTP 200
- Layer 2: Response contains expected fields
- Layer 3: CloudWatch logs show startup
- Layer 4: Langfuse dashboard shows new traces
**Next**: Proceed to staging deployment
```

---

### Example 2: Investigation Step (Diverge Mode)

```markdown
# Thinking Tuple: Investigate Lambda timeout

## 1. Constraints
**Known**: Lambda timing out after 30s, ConnectTimeoutError, started after deploy
**Resources**: CloudWatch logs, X-Ray traces, AWS CLI
**Partial state**: Error identified, root cause unknown
**Limits**: Cannot reproduce locally (VPC-specific)

## 2. Invariant
**Must be true**: Root cause identified, at least 3 hypotheses generated
**Success criteria**: Can explain why timeout occurs, have actionable next step
**Safety**: Don't modify production during investigation

## 3. Principles
**Tier-0**: #2 (work through evidence layers)
**Task-specific**: #9 (identify loop type if stuck)
**Tradeoff**: Thoroughness over speed

## 4. Process
**Mode**: diverge
**Rationale**: Need multiple hypotheses before converging on solution

## 5. Actions
1. Query CloudWatch logs (MCP: cloudwatch)
2. Check X-Ray traces (MCP: cloudwatch)
3. Review recent infrastructure changes (Bash: git log terraform/)
4. Generate hypothesis list
5. Rank by likelihood

## 6. Check
**Result**: PARTIAL
**Evidence**:
- Layer 3: Logs show S3 connection timeout
- Layer 3: X-Ray shows 10s wait on S3 API
**Next**: Spin new tuple in converge mode with hypothesis "NAT Gateway saturation"
```

---

### Example 3: Check Failure Recovery

```markdown
# Thinking Tuple: Fix test failures (Attempt 1)

## 6. Check
**Result**: FAIL
**Evidence**:
- Layer 1: Exit code 1
- Layer 2: 3 tests failing
- Layer 3: TypeError in test output

**Recovery**:
→ Updated Constraints: Tests use async fixtures incorrectly
→ Process change: None needed (still converge)
→ Spin new tuple

---

# Thinking Tuple: Fix test failures (Attempt 2)

## 1. Constraints
**Known**: (previous) + Tests use async fixtures incorrectly
**Resources**: Same as before
**Partial state**: Problem identified, fix not yet applied
**Limits**: Same as before

## 2. Invariant
**Must be true**: All tests pass

## 3. Principles
**Tier-0**: #1, #2
**Task-specific**: #10 (test anti-patterns)

## 4. Process
**Mode**: converge

## 5. Actions
1. Fix async fixture usage
2. Run tests again

## 6. Check
**Result**: PASS
**Next**: Done
```

---

## Anti-Patterns

### 1. Skipping Constraints Update After Failure

**Bad**:
```
Check fails → Retry same tuple
```

**Good**:
```
Check fails → Update Constraints with learnings → Spin new tuple
```

### 2. Not Changing Process When Stuck

**Bad**:
```
Converge → fail → converge → fail → converge...
```

**Good**:
```
Converge → fail → /reflect → "stuck" → escape → new approach
```

### 3. Weak Check Evidence

**Bad**:
```
Check: PASS (exit code 0)
```

**Good**:
```
Check: PASS
- Layer 1: Exit code 0
- Layer 2: Response valid
- Layer 3: Logs show success
- Layer 4: Database state changed correctly
```

### 4. Tuple Without Invariant

**Bad**:
```
Constraints: ...
Principles: ...
Process: ...
Actions: ...
Check: "Looks good"  ← No measurable criteria!
```

**Good**:
```
Invariant:
- Must be true: Lambda responds with 200
- Success criteria: Response contains "status": "success"
- Safety: Latency < 5s
```

---

## Relationship to Other Commands

| Command | Relationship |
|---------|--------------|
| `/invariant` | Generates content for Invariant slot |
| `/reconcile` | Fixes violations found in Check slot |
| `/explore` | Executes in diverge Process mode |
| `/what-if` | Executes in compare Process mode |
| `/decompose` | Executes in decompose Process mode |
| `/reflect` | Triggered when Check fails repeatedly |

---

## Integration with Todo System

Each todo item can map to a tuple:

| Todo Component | Tuple Component |
|----------------|-----------------|
| `content` | Invariant |
| `status: in_progress` | Actions executing |
| `status: completed` | Check passed |

---

## See Also

- [CLAUDE.md - Principle #26](../../.claude/CLAUDE.md) - Thinking Tuple Protocol
- [/step command](../../.claude/commands/step.md) - Explicit tuple instantiation
- [Thinking Process Architecture - Section 12](../../.claude/diagrams/thinking-process-architecture.md#12-thinking-tuple-protocol) - Architecture integration
- [Behavioral Invariant Guide](behavioral-invariant-verification.md) - Invariant slot details
- [Principle #2 Progressive Evidence](../../.claude/CLAUDE.md) - Check slot evidence levels
