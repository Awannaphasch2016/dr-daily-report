# Step Command (Thinking Tuple Protocol)

**Purpose**: Instantiate a Thinking Tuple - the atomic unit of disciplined reasoning that forces composition of constraints, invariants, principles, process, actions, and verification.

**Core Principle**: Layers (principles, skills, commands) are static definitions. The Thinking Tuple is the **runtime protocol** that forces their composition at each reasoning step, enabling bounded error growth in long-running tasks.

**When to use**:
- Complex tasks (> 3 steps) where drift is possible
- Long-running work where you need checkpoints
- When you want explicit reasoning structure
- Before any significant action in autonomous mode
- When you notice yourself "thrashing" without progress

**When NOT to use**:
- Simple lookups or single-action tasks
- Trivial changes (typo fixes, small edits)
- Pure information retrieval

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `goal_oriented`

`/step` has **full tuple control** - it can instantiate, modify, and verify all components:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **FULL**: Explicitly states current known state |
| **Invariant** | **FULL**: Defines what must be true at completion |
| **Principles** | **FULL**: Selects Tier-0 + task-specific principles |
| **Strategy** | **ORCHESTRATE**: Composes other modes into pipeline |
| **Check** | **FULL**: Evaluates against invariant with evidence layers |

**Strategy Orchestration**:
Unlike other modes that execute within a Strategy, `/step` can **define** the Strategy:

```yaml
# /step can compose other modes into a pipeline
strategy:
  - mode: "/decompose"
    prompt: "break down the deployment task"
  - mode: "/invariant"
    prompt: "identify what must hold"
  - mode: "/explore"
    prompt: "find deployment approaches"
  - mode: "/consolidate"
    prompt: "synthesize deployment plan"
```

**Tuple Chaining**:
For long-running tasks, `/step` chains tuples:

```
Frame_0: (C₀, I₀, P₀, Strategy₀, Check₀)
    │
    ▼ (Check passes, update constraints)
Frame_1: (C₁, I₁, P₁, Strategy₁, Check₁)
    │
    ▼ (Check passes, update constraints)
Frame_N: (Cₙ, Iₙ, Pₙ, Strategyₙ, Checkₙ)
    │
    ▼ (Final invariant satisfied)
DONE: Ground truth verified
```

---

## Local Check (Mode Completion Criteria)

The `/step` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Constraints Stated** | Current known state explicitly documented |
| **Invariant Defined** | Success criteria measurable |
| **Principles Selected** | Relevant principles identified with rationale |
| **Strategy Executed** | All pipeline modes completed |
| **Evidence Collected** | Layers 1-4 evidence gathered per Principle #2 |
| **Invariant Satisfied** | Ground truth verification passes |

**Check Result Mapping**:
- **PASS**: Invariant satisfied with Layer 4 evidence → can claim "done"
- **PARTIAL**: Invariant partially satisfied → spin new tuple with updated constraints
- **FAIL**: Invariant violated → change Strategy, try different approach

**Error Bound Analysis**:
```
Without tuples:
  Error ∝ (steps × drift_rate)  # Unbounded

With tuples:
  Error ∝ (undetected_drift × steps_between_checks)  # Bounded by check frequency

/step ensures check_frequency = 1 per tuple, bounding error per reasoning step.
```

**Recovery Protocol**:
```yaml
if check_result == FAIL:
  options:
    1. extend_strategy:
        action: "Add more modes to pipeline"
        when: "Progress made but incomplete"
    2. spin_new_tuple:
        action: "Update Constraints with learned info"
        when: "Assumptions invalidated"
    3. escape_hatch:
        action: "Report failure with diagnostics"
        when: "Stuck, need human input"
```

---

## Quick Reference

```bash
# Explicit tuple instantiation
/step "deploy new scoring feature"
/step "refactor authentication module"
/step "investigate timeout bug"

# With explicit mode selection
/step --mode=diverge "explore caching strategies"
/step --mode=converge "select best approach"
/step --mode=decompose "break down migration plan"
```

---

## The Thinking Tuple Structure

Each tuple has 6 components that must be instantiated together:

```
┌────────────────────────────────────────────────────────────────┐
│                    THINKING TUPLE                               │
├────────────────────────────────────────────────────────────────┤
│ 1. CONSTRAINTS (Start State)                                    │
│    - What is currently known?                                   │
│    - What resources, tools, inputs are available?               │
│    - What limits or blockers exist?                             │
│    - Current partial outputs from previous steps                │
├────────────────────────────────────────────────────────────────┤
│ 2. INVARIANT (Target State)                                     │
│    - What must be true at step completion?                      │
│    - Success criteria (measurable)                              │
│    - Safety boundaries (non-negotiable)                         │
│    - Maps to /invariant output (Levels 0-4)                     │
├────────────────────────────────────────────────────────────────┤
│ 3. PRINCIPLES (Navigation Rules)                                │
│    - Tier-0 principles always active                            │
│    - Task-specific principles from clusters                     │
│    - Tradeoff rationale for this specific step                  │
├────────────────────────────────────────────────────────────────┤
│ 4. PROCESS (Thinking Mode)                                      │
│    - Selected from: diverge | converge | decompose |            │
│      compare | reframe | escape                                 │
│    - Rationale for why this mode is appropriate                 │
├────────────────────────────────────────────────────────────────┤
│ 5. ACTIONS (Execution Steps)                                    │
│    - Concrete tool calls, commands, edits                       │
│    - Ordered by dependency                                      │
│    - Drawn from Skills layer patterns                           │
├────────────────────────────────────────────────────────────────┤
│ 6. CHECK (Verification)                                         │
│    - Did Actions satisfy Invariant?                             │
│    - Evidence level (Layer 1-4 per Principle #2)                │
│    - If failed: update Constraints, spin new tuple              │
└────────────────────────────────────────────────────────────────┘
```

---

## Execution Flow

### Step 1: State Constraints

```markdown
## Constraints (Start State)

**Known facts**:
- {What we know to be true}
- {Results from previous steps}
- {Environmental conditions}

**Available resources**:
- Tools: {Read, Write, Bash, MCP servers, etc.}
- Data: {What data we have access to}
- Time: {Any time constraints}

**Current partial state**:
- {What has been completed so far}
- {Intermediate outputs}

**Limits/Blockers**:
- {Known constraints or obstacles}
- {What we cannot do}
```

---

### Step 2: State Invariant

```markdown
## Invariant (Target State)

**Must be true after this step**:
- {Specific measurable condition 1}
- {Specific measurable condition 2}

**Success criteria**:
- {How we will know we succeeded}
- {Measurable outcome}

**Safety boundaries**:
- {What must NOT happen}
- {Non-negotiable constraints}

**Invariant level** (from Principle #25):
- Level 4 (Config): {if applicable}
- Level 3 (Infra): {if applicable}
- Level 2 (Data): {if applicable}
- Level 1 (Service): {if applicable}
- Level 0 (User): {if applicable}
```

---

### Step 3: Select Principles

```markdown
## Principles (Navigation Rules)

**Tier-0 (always active)**:
- #1 Defensive Programming: {how it applies}
- #2 Progressive Evidence: {how it applies}
- {other relevant Tier-0}

**Task-specific (from clusters)**:
- #{N} {Principle name}: {why selected, how it guides}

**Tradeoff being made**:
- {What we're optimizing for}
- {What we're accepting as cost}
```

---

### Step 4: Select Process (Thinking Mode)

```markdown
## Process (Thinking Mode)

**Mode**: {diverge | converge | decompose | compare | reframe | escape}

**Why this mode**:
- {Rationale for selection}
- {What this mode will help us achieve}

**Mode definitions**:
- **diverge**: Generate multiple options, explore broadly
- **converge**: Narrow down, select from options
- **decompose**: Break into subproblems
- **compare**: Evaluate alternatives side-by-side
- **reframe**: Change perspective on the problem
- **escape**: Break out of local optimum, try different approach
```

---

### Step 5: Plan Actions

```markdown
## Actions (Execution Steps)

1. {Action 1}
   - Tool: {specific tool to use}
   - Expected output: {what we expect}

2. {Action 2}
   - Tool: {specific tool to use}
   - Expected output: {what we expect}

3. {Action 3}
   - ...

**Dependency order**: {1 → 2 → 3 | 1,2 parallel → 3}
```

---

### Step 6: Execute and Check

```markdown
## Check (Verification)

**Invariant satisfied?**: {YES | NO | PARTIAL}

**Evidence collected**:
- Layer 1 (Surface): {status codes, exit codes}
- Layer 2 (Content): {payloads, outputs}
- Layer 3 (Observability): {logs, traces}
- Layer 4 (Ground truth): {actual state changes}

**If satisfied**:
→ Proceed to next step or claim "done"

**If NOT satisfied**:
→ Update constraints with what we learned
→ Consider changing Process mode
→ Spin new tuple with updated state
```

---

## Thinking Mode Reference

| Mode | When to Use | Output |
|------|-------------|--------|
| **diverge** | Need more options, exploring solution space | List of candidates |
| **converge** | Have options, need to select/refine | Single selected option |
| **decompose** | Problem too large, need smaller pieces | Subproblem list |
| **compare** | Multiple viable options, need evaluation | Ranked comparison |
| **reframe** | Current approach not working | New problem framing |
| **escape** | Stuck in local optimum | Fundamentally different approach |

### Mode Transitions

```
diverge ──────► converge ──────► decompose
    ▲               │                │
    │               ▼                ▼
    └────────── reframe ◄────── compare
                    │
                    ▼
                 escape
                    │
                    └──────► diverge (restart with new frame)
```

---

## Integration with Existing Layers

The Thinking Tuple **composes** existing layers at runtime:

```
Your Existing Layers              Tuple Component
─────────────────────────────────────────────────────────
CLAUDE.md Principles    ────────► Principles slot
Skills                  ────────► Actions slot (patterns)
Slash Commands          ────────► Pre-assembled tuples
Thinking Process Arch   ────────► Process slot (modes)
/invariant command      ────────► Invariant slot
Progressive Evidence    ────────► Check slot (evidence levels)
```

The tuple doesn't replace these—it **forces their composition**.

---

## Long-Running Task Protocol

For tasks spanning multiple steps, chain tuples:

```
Frame_0: (C₀, I₀, P₀, Proc₀, A₀, Check₀)
    │
    ▼ (Check passes, update constraints)
Frame_1: (C₁, I₁, P₁, Proc₁, A₁, Check₁)
    │
    ▼ (Check passes, update constraints)
Frame_2: (C₂, I₂, P₂, Proc₂, A₂, Check₂)
    │
    ...
    │
    ▼ (Final invariant satisfied)
DONE: All constraints satisfied, ground truth verified
```

**Key insight**: Each tuple is a **checkpoint** with full context. If Check fails, you don't abandon the run—you spin a new tuple with updated constraints.

---

## Error Bound Analysis

Without tuples:
- Error ∝ (steps × drift_rate)
- Stale assumptions compound silently
- No recovery mechanism

With tuples:
- Error ∝ (undetected_drift × steps_between_checks)
- Constraints refreshed each tuple
- Failed Check → new tuple with updated state
- Each tuple is observable checkpoint

---

## Output Template

When executing `/step`, produce:

```markdown
# Thinking Tuple: {Brief description}

## 1. Constraints
**Known**: ...
**Resources**: ...
**Partial state**: ...
**Limits**: ...

## 2. Invariant
**Must be true**: ...
**Success criteria**: ...
**Safety boundaries**: ...

## 3. Principles
**Active**: #1, #2, #{N}
**Tradeoff**: ...

## 4. Process
**Mode**: {diverge | converge | ...}
**Rationale**: ...

## 5. Actions
1. ...
2. ...
3. ...

## 6. Check
**Result**: {PASS | FAIL | PARTIAL}
**Evidence**: ...
**Next**: {proceed | spin new tuple with: ...}
```

---

## Examples

### Example 1: Deployment Step

```markdown
# Thinking Tuple: Deploy new scoring feature

## 1. Constraints
**Known**:
- Code merged to dev branch
- Tests passing locally
- Lambda function exists

**Resources**:
- AWS CLI, GitHub Actions
- Doppler secrets configured

**Partial state**:
- Code ready, not deployed

**Limits**:
- Must not disrupt existing functionality

## 2. Invariant
**Must be true**:
- Lambda updated with new code
- New scoring endpoint responds 200
- Langfuse traces appear

**Success criteria**:
- POST /score returns valid response
- CloudWatch logs show no errors

**Safety boundaries**:
- Existing /report endpoint must still work

## 3. Principles
**Active**:
- #1 Defensive Programming (validate at startup)
- #2 Progressive Evidence (verify through ground truth)
- #6 Deployment Monitoring (use waiters)
- #11 Artifact Promotion (same artifact through envs)

**Tradeoff**:
- Optimizing for safety over speed (full verification)

## 4. Process
**Mode**: converge
**Rationale**: We have a clear plan, need to execute and verify

## 5. Actions
1. Push to trigger GitHub Actions
2. Wait for deployment completion (gh run watch)
3. Invoke Lambda health check
4. Verify Langfuse trace appears
5. Test /report still works (regression)

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
**Known**:
- Lambda timing out after 30s
- Error: ConnectTimeoutError
- Started after recent deploy

**Resources**:
- CloudWatch logs, X-Ray traces
- AWS CLI access

**Partial state**:
- Error identified, root cause unknown

**Limits**:
- Cannot reproduce locally (VPC-specific)

## 2. Invariant
**Must be true**:
- Root cause identified
- At least 3 hypotheses generated

**Success criteria**:
- Can explain why timeout occurs
- Have actionable next step

**Safety boundaries**:
- Don't modify production during investigation

## 3. Principles
**Active**:
- #2 Progressive Evidence (work through evidence layers)
- #9 Feedback Loop Awareness (identify loop type)

**Tradeoff**:
- Thoroughness over speed (need correct diagnosis)

## 4. Process
**Mode**: diverge
**Rationale**: Need multiple hypotheses before converging on solution

## 5. Actions
1. Query CloudWatch logs for error patterns
2. Check X-Ray traces for latency breakdown
3. Review recent infrastructure changes
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

## Relationship to Other Commands

| Command | Relationship to /step |
|---------|----------------------|
| `/invariant` | Generates content for Invariant slot |
| `/reconcile` | Fixes violations found in Check slot |
| `/explore` | Executes in diverge Process mode |
| `/what-if` | Executes in compare Process mode |
| `/decompose` | Executes in decompose Process mode |
| `/reflect` | Triggered when Check fails repeatedly |

---

## See Also

- [CLAUDE.md - Principle #26](./../CLAUDE.md) - Thinking Tuple Protocol
- [Thinking Process Architecture](./../diagrams/thinking-process-architecture.md) - Cognitive strategies
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Invariant hierarchy
- [/invariant command](./invariant.md) - Invariant identification
- [/reconcile command](./reconcile.md) - Violation reconciliation
- [Thinking Tuple Guide](../../docs/guides/thinking-tuple-protocol.md) - Implementation guide
