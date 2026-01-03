---
title: Boundary Blindness Pattern - Integration Roadmap
type: meta-cognitive-principle
status: ready_for_graduation
created: 2026-01-03
---

# Boundary Blindness Pattern: From Failure Mode to Investigation Principle

## Executive Summary

**Pattern discovered**: Boundary Blindness in Code Investigation

**Core insight**: Code correctness ≠ Execution correctness. Verifying that code exists or logic is correct WITHOUT mapping WHERE and HOW it executes leads to missing root causes in distributed systems.

**User's exact diagnosis**:
> "you conclude that code is true without taking into account that code has to be run somewhere or different pieces can be run in different services, and without identifying the 'boundary' you miss things like 'testing initial condition' that's required to execute correctly."

**Impact**: 3 major debugging sessions where I missed root causes by stopping investigation too early (verified code but not execution context).

---

## The Problem Pattern (What I Did Wrong)

### My Typical Investigation Flow (Boundary-Blind)

```
Step 1: User reports error
  ↓
Step 2: Find relevant code
  ✅ "Function exists"
  ✅ "Logic looks correct"
  ✅ "Parameters have right defaults"
  ↓
Step 3: Verify deployment
  ✅ "Code is in Docker image"
  ✅ "Lambda config points to image"
  ↓
Step 4: Conclude
  "Code is correct, should work"
  ↓
Step 5: STOP (Wrong!)
  ❌ Never asked: "WHERE does this run?"
  ❌ Never checked: "WHAT boundaries does it cross?"
  ❌ Never verified: "WHAT initial conditions at each boundary?"
```

### What I Missed (Boundary-Aware Investigation Should Be)

```
Step 1: User reports error
  ↓
Step 2: MAP EXECUTION CONTEXT (MANDATORY FIRST)
  ❓ WHERE does code run? (which service, container, environment)
  ❓ WHAT triggers execution?
  ❓ WHAT boundaries are crossed? (service → service, build → runtime, tier → tier)
  ↓
Step 3: IDENTIFY INITIAL CONDITIONS (EACH BOUNDARY, BOTH SIDES)
  For ticker_fetcher → precompute_controller:
    - Left (ticker_fetcher): Needs PRECOMPUTE_CONTROLLER_ARN
    - Right (precompute_controller): Needs TZ env var ← DIDN'T CHECK!
  ↓
Step 4: VERIFY CONTRACT (BOTH SIDES)
  ✅ Check Terraform for ticker_fetcher env vars
  ✅ Check Terraform for precompute_controller env vars ← SKIPPED THIS!
  ✅ Check CloudWatch logs BOTH sides ← SKIPPED THIS!
  ↓
Step 5: Find root cause
  Missing TZ env var in precompute_controller
```

---

## Concrete Example: This Session's Failure

### What I Did (Boundary-Blind)

**Investigation**: LINE bot returning errors for today's reports

**My approach**:
1. ✅ Read `_trigger_precompute()` function definition
2. ✅ Saw it invokes Lambda with `PRECOMPUTE_CONTROLLER_ARN`
3. ✅ Saw it returns HTTP 202 (async invocation)
4. ❌ **CONCLUDED**: "Precompute is triggered by scheduler"
5. ❌ **STOPPED**: Didn't check what precompute_controller needs

**What I missed**:
- **Boundary identification**: ticker_fetcher (scheduler Lambda) → precompute_controller (DIFFERENT Lambda)
- **Boundary type**: Service boundary (Lambda invocation = different containers, different env vars)
- **Initial conditions**: Each Lambda has OWN environment configuration
- **Verification needed**: Check precompute_controller Terraform for required env vars (TZ)

**Impact**: Stopped at Layer 1 (weakest evidence - "HTTP 202 returned"), never reached Layer 3 (logs) or Layer 4 (ground truth)

### What I Should Have Done (Boundary-Aware)

**Mandatory first step: Execution Context Mapping**

```markdown
## Execution Flow

EventBridge (5:00 AM Bangkok)
  ↓ (triggers)
ticker_fetcher Lambda [Container A, Env Config A]
  ↓ (invokes via boto3) ← SERVICE BOUNDARY
precompute_controller Lambda [Container B, Env Config B]
  ↓ (starts)
Step Functions workflow
  ↓ (triggers)
report_worker Lambdas [Containers C1-C46, Env Config C]

## Boundary #1: ticker_fetcher → precompute_controller

**Type**: Service boundary (Lambda invocation)

**Left side** (ticker_fetcher):
- Needs: PRECOMPUTE_CONTROLLER_ARN env var
- Needs: IAM permission to invoke Lambda
- Verify: Check terraform/scheduler.tf

**Right side** (precompute_controller):
- Needs: TZ env var (for Bangkok timezone queries)
- Needs: STEP_FUNCTIONS_ARN env var
- Needs: IAM permission to start Step Functions
- Verify: Check terraform/precompute_controller.tf ← I NEVER DID THIS!

## Verification Commands

# Check caller (I did this)
aws lambda get-function-configuration \
  --function-name ticker_fetcher \
  | jq '.Environment.Variables.PRECOMPUTE_CONTROLLER_ARN'

# Check CALLEE (I DIDN'T do this - root cause!)
aws lambda get-function-configuration \
  --function-name precompute_controller \
  | jq '.Environment.Variables.TZ'  # Missing!
```

**If I had done this**: Would have found missing TZ env var immediately (5 minutes vs 30 minutes debugging)

---

## Pattern Instances (Evidence)

### Instance 1: Precompute Not Scheduled (This Session - Primary)

**Bug hunt**: `.claude/bug-hunts/2026-01-03-linebot-returns-default-error-for-today.md`

**Boundary missed**: Service boundary (ticker_fetcher → precompute_controller)

**What I verified**: Code exists, function invokes Lambda, returns 202

**What I didn't verify**: Does INVOKED Lambda have required env vars?

**Root cause**: precompute_controller missing TZ env var

**Time wasted**: 15-30 minutes (user had to point out boundary blindness)

### Instance 2: PDF Code Not Executing (Container Cache)

**Bug hunt**: `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md`

**Boundary missed**: Phase boundary (Docker image build → Lambda container runtime)

**What I verified**: Code in Docker image, Lambda config points to image

**What I didn't verify**: Is Lambda using FRESH container or CACHED container?

**Root cause**: Lambda running cached container with old code

**Time wasted**: 45 minutes (tried syntax checks, imports, permissions - all wrong direction)

### Instance 3: Generate PDF=True Not Executing (Workflow Tier)

**Bug hunt**: `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`

**Boundary missed**: Workflow boundary (Tier 1 data fetch → Tier 2 report generation)

**What I verified**: Function signature correct, default parameter True

**What I didn't verify**: Is function CALLED in execution path? What triggers Tier 2?

**Root cause**: Scheduler only calls Tier 1 (data fetch), doesn't integrate with Tier 2 (report generation)

**Time wasted**: 30 minutes (searched for `generate_pdf=False`, checked S3 permissions - all wrong)

---

## Root Cause of Pattern (Why I Keep Making This Mistake)

### 1. Code-Centric Investigation Habit

**Current habit**: "Find code → Verify logic → Done"

**Missing**: "Map execution → Identify boundaries → Verify contracts"

**Why**: Training focuses on code correctness, not system execution

### 2. Boundary Invisibility in Code

**What code shows**:
```python
# Looks like a simple function call
boto3.client('lambda').invoke(FunctionName='other_lambda')
```

**What actually happens**:
```
Service Boundary Crossing:
┌─────────────────────┐         ┌─────────────────────┐
│  Lambda A           │         │  Lambda B           │
│  Environment A      │─invoke─>│  Environment B      │
│  - TZ=<missing>     │         │  - TZ=<missing>     │
│  - ARN=<set>        │         │  - ARN=<set>        │
└─────────────────────┘         └─────────────────────┘
```

**Problem**: Code looks monolithic, execution is distributed

### 3. Stopping at Weak Evidence Layers

**My pattern**: Check Layer 1-2, conclude success

**Should be**: Progress through ALL layers

| Layer | Signal | My Check | Should Check |
|-------|--------|----------|--------------|
| 1 | Status code | ✅ "200/202 returned" | ⚠️ Weak evidence only |
| 2 | Payload/Code | ✅ "Function exists" | ⚠️ Doesn't mean it executes |
| 3 | Logs | ❌ Skipped | ✅ MUST CHECK (what actually happened) |
| 4 | Ground truth | ❌ Skipped | ✅ MUST CHECK (side effects verified) |

### 4. No Execution Context Diagrams

**Missing**: Visual map of service boundaries

**Should have**:
```
System Execution Map:
┌──────────────┐
│ EventBridge  │ (Trigger)
└──────┬───────┘
       ↓
┌──────────────────────────┐
│ ticker_fetcher Lambda    │ ← Boundary: EventBridge → Lambda
│ Env: TZ, CONTROLLER_ARN  │
└──────┬───────────────────┘
       ↓ invoke()
┌──────────────────────────┐
│ precompute_controller    │ ← Boundary: Lambda → Lambda (SERVICE)
│ Env: TZ, SF_ARN          │ ← VERIFY BOTH SIDES!
└──────┬───────────────────┘
       ↓ start_execution()
┌──────────────────────────┐
│ Step Functions Workflow  │ ← Boundary: Lambda → Step Functions
└──────┬───────────────────┘
       ↓ SQS messages
┌──────────────────────────┐
│ report_worker Lambdas    │ ← Boundary: Step Functions → Workers
│ Env: TZ, JOBS_TABLE      │
└──────────────────────────┘
```

---

## Proposed Solution: Update Investigation Methodology

### 1. Add to Error-Investigation Skill

File: `.claude/skills/error-investigation/SKILL.md`

**New Principle #5**: Execution Context Precedes Code Verification

```markdown
### Principle 5: Execution Context Precedes Code Verification

**Pattern name**: Boundary Blindness

**Problem**: Verifying code logic without mapping execution boundaries leads to "code is correct but doesn't execute correctly" failures.

**Mandatory pre-investigation checklist** (BEFORE code verification):

1. **WHERE** does this code run?
   - Which service/Lambda/container?
   - What environment (dev/staging/prod)?
   - What triggers execution?

2. **WHAT** boundaries does execution cross?
   - Service boundaries: Lambda A → Lambda B
   - Phase boundaries: Build → Deploy → Runtime
   - Workflow boundaries: Tier 1 → Tier 2
   - Time boundaries: Fresh → Cached state

3. **WHAT** are initial conditions at EACH boundary?
   For each boundary, identify:
   - Left side (caller): Needs what env vars? permissions? config?
   - Right side (callee): Needs what env vars? permissions? config? state?

4. **HOW** to verify boundary contract?
   - Check Terraform env vars (BOTH sides)
   - Check CloudWatch logs (BOTH sides)
   - Check ground truth (S3, DB, side effects)

**Anti-pattern examples**:
- ❌ "Function exists → Should work" (missing WHERE it runs)
- ❌ "Lambda returns 202 → Success" (only checked caller, not callee)
- ❌ "Code deployed → Should execute" (missing fresh vs cached container check)

**Correct pattern**:
```markdown
## Investigation: [Feature]

### 1. Map Execution (MANDATORY FIRST)
WHERE: [Service, container, env]
FLOW: [A] → [B] → [C] → [Outcome]
BOUNDARIES: [Service / Phase / Workflow / Time]

### 2. Identify Initial Conditions (EACH BOUNDARY, BOTH SIDES)
Boundary: [Left] → [Right]
- Left needs: [env vars, permissions, config]
- Right needs: [env vars, permissions, config, state]

### 3. Verify Contract (BOTH SIDES)
[Terraform commands]
[CloudWatch commands]
[Ground truth commands]
```

See [Boundary Blindness Pattern](.claude/abstractions/failure_mode-2026-01-03-boundary-blindness.md) for complete examples.
```

### 2. Add to Research Skill Investigation Checklist

File: `.claude/skills/research/INVESTIGATION-CHECKLIST.md`

**Add at TOP** (before "What Changed Recently?"):

```markdown
## Pre-Investigation: Execution Context Mapping (MANDATORY)

**DO THIS FIRST** before checking code, changes, or errors.

### Execution Flow Diagram

Draw the execution flow (use this template):

```
[Trigger] → [Service A] → [Service B] → [Service C] → [Outcome]
            (Boundary 1) (Boundary 2) (Boundary 3)
```

For this investigation:
```
_________________ → _________________ → _________________ → _________________
(Type: _________ ) (Type: _________ ) (Type: _________ )
```

### Boundary Checklist (EACH Boundary)

For EACH boundary in execution flow above:

- [ ] **Boundary type identified**:
  - Service (Lambda → Lambda, API → Worker)
  - Phase (Build → Runtime, Deploy → Execution)
  - Workflow (Tier → Tier, Scheduler → Worker)
  - Time (Fresh → Cached)

- [ ] **Left side (caller) initial conditions**:
  - Env vars needed: __________________
  - Permissions needed: __________________
  - Config needed: __________________

- [ ] **Right side (callee) initial conditions**:
  - Env vars needed: __________________
  - Permissions needed: __________________
  - Config needed: __________________
  - State assumptions: __________________

- [ ] **Verification commands prepared**:
  ```bash
  # Left side
  aws lambda get-function-configuration --function-name [left] | jq '.Environment.Variables'

  # Right side
  aws lambda get-function-configuration --function-name [right] | jq '.Environment.Variables'

  # Logs (BOTH sides)
  aws logs tail /aws/lambda/[left] --since 5m
  aws logs tail /aws/lambda/[right] --since 5m
  ```

### Common Boundary Mistakes

❌ **WRONG**: "Function exists → Should work"
✅ **RIGHT**: "Function exists → WHERE called? → WHAT service? → WHAT env vars needed?"

❌ **WRONG**: "Lambda returns 202 → Triggered successfully"
✅ **RIGHT**: "Lambda returns 202 → Check logs on INVOKED Lambda → Verify execution started"

❌ **WRONG**: "Code deployed to Lambda → Should run with new code"
✅ **RIGHT**: "Code deployed → Fresh container? Or cached? → Force refresh if needed"

---

**AFTER completing execution context mapping**, proceed with:

## 1. What Changed Recently?
(... existing checklist ...)
```

### 3. Create New CLAUDE.md Principle #19

**Add to CLAUDE.md** after Principle #18:

```markdown
### 19. Cross-Boundary Contract Testing

Code correctness ≠ Execution correctness. Map execution boundaries (Service, Phase, Workflow, Time) BEFORE verifying code logic. Each boundary has two sides with own initial conditions (env vars, permissions, config) that must be verified.

**Investigation anti-pattern**: Verifying code exists and logic is correct WITHOUT asking:
1. WHERE does this code run? (which service, container, environment)
2. WHAT boundaries does execution cross? (Lambda → Lambda, Build → Runtime, Tier → Tier)
3. WHAT are initial conditions at each boundary? (env vars, permissions - BOTH sides)

**Boundary types**:
- **Service**: Lambda A → Lambda B (different containers, different env configs)
- **Phase**: Docker build → Container runtime (fresh vs cached state)
- **Workflow**: Tier 1 → Tier 2 (separate schedulers, separate execution paths)
- **Time**: Deploy → Runtime (eventual consistency, container lifecycle)

**Mandatory investigation steps** (BEFORE code verification):

```markdown
## Execution Context Mapping (MANDATORY FIRST)

### 1. Draw Execution Flow
[Trigger] → [Service A] → [Service B] → [Outcome]
            (Boundary 1) (Boundary 2)

### 2. Identify Initial Conditions (EACH BOUNDARY, BOTH SIDES)
Boundary: [Left] → [Right]
- Left needs: [env vars, permissions, config]
- Right needs: [env vars, permissions, config, state]

### 3. Verify Contract (BOTH SIDES)
- Check Terraform (env vars, IAM)
- Check CloudWatch logs (execution traces)
- Check ground truth (S3, DB, side effects)
```

**Anti-patterns**:
- ❌ "Function exists → Should work" (missing WHERE it runs)
- ❌ "Lambda invoked → Success" (only checked caller, not callee)
- ❌ "Code deployed → Should execute" (missing fresh vs cached container check)
- ❌ Stopping at Layer 1-2 (weak evidence like status codes, skip logs/ground truth)

**Example (Correct Investigation)**:

```markdown
Investigation: Precompute not running

1. Map Execution:
   EventBridge → ticker_fetcher (Lambda A) → precompute_controller (Lambda B)
   Boundary: Service (Lambda A → Lambda B)

2. Initial Conditions:
   - ticker_fetcher needs: PRECOMPUTE_CONTROLLER_ARN ✅
   - precompute_controller needs: TZ, STEP_FUNCTIONS_ARN ← CHECK THIS!

3. Verify Contract:
   # Check BOTH sides
   aws lambda get-function-configuration --function-name ticker_fetcher | jq '.Environment.Variables'
   aws lambda get-function-configuration --function-name precompute_controller | jq '.Environment.Variables.TZ'  # Missing? Root cause!
```

See [Boundary Blindness Pattern](.claude/abstractions/failure_mode-2026-01-03-boundary-blindness.md) for detailed failure mode analysis and prevention strategies.

**Related**: Integrates with Principle #2 (Progressive Evidence Strengthening - verify execution, not just code), Principle #1 (Defensive Programming - validate at boundaries), Principle #15 (Infrastructure-Application Contract - boundary configuration).
```

### 4. Create Boundary-Aware Investigation Template

**New file**: `.claude/skills/error-investigation/BOUNDARY-AWARE-TEMPLATE.md`

(Full template created in main failure mode document)

---

## Integration Checklist

### Immediate Actions (Update Investigation Skills)

- [ ] **Update error-investigation skill**: Add Principle #5 (Execution Context Precedes Code Verification)
- [ ] **Update research skill checklist**: Add Pre-Investigation: Execution Context Mapping (at top, mandatory first step)
- [ ] **Create boundary-aware template**: New file with step-by-step boundary investigation workflow

### Medium-term Actions (Update Core Principles)

- [ ] **Add CLAUDE.md Principle #19**: Cross-Boundary Contract Testing
- [ ] **Update Principle #2**: Add note linking to boundary awareness (Progressive Evidence = verify across boundaries)
- [ ] **Update Principle #15**: Add note about boundary configuration (Infrastructure-Application Contract at boundaries)

### Long-term Actions (Prevent Future Instances)

- [ ] **Create execution context diagrams**: Visual maps of service boundaries for major workflows
- [ ] **Add boundary tests**: Contract tests that verify boundary configurations (Terraform env vars match requirements)
- [ ] **Update deployment skill**: Add boundary verification to deployment checklist
- [ ] **Thinking process integration**: Add boundary awareness to feedback loops (synchronize loop = update boundary knowledge)

---

## Success Criteria

### Investigation Methodology Improved When:

1. **Every investigation starts with**: "WHERE does this run? WHAT boundaries?"
2. **Boundary identification is automatic**: Draw execution flow before reading code
3. **Both sides always checked**: Never verify caller without verifying callee
4. **Progressive evidence mandatory**: Never stop at Layer 1-2, always reach Layer 3-4

### Pattern Prevented When:

1. **No more "code exists → should work" conclusions**
2. **No more stopping at HTTP 202/200** without checking logs
3. **No more missing service boundary configurations** (always check BOTH Lambdas)
4. **No more cached container surprises** (always consider phase boundaries)

---

## Meta-Learning: Why This Pattern Emerged

### What Makes This Pattern Particularly Insidious

1. **Code verification feels complete**: Reading function definition, checking parameters feels thorough
2. **Boundaries are invisible in code**: `boto3.invoke()` looks like function call, hides service boundary
3. **Weak evidence is reassuring**: "HTTP 202 returned" feels like success
4. **Distributed systems are complex**: Multiple execution contexts hard to track mentally

### What User's Feedback Reveals

**User's insight**: "you didn't check WHERE code runs"

**What this shows**: I have strong code analysis skills BUT weak execution context mapping skills

**Why this matters**: Modern systems are distributed. Code correctness is necessary but NOT sufficient. Must also verify execution context correctness.

### How to Prevent Similar Patterns

1. **Always start with system view**: Map execution flow before diving into code
2. **Make boundaries visible**: Draw diagrams, list contexts, identify crossings
3. **Progressive evidence is mandatory**: Layer 1 (weak) → Layer 4 (strong), always
4. **Both sides of boundaries**: Caller AND callee, build AND runtime, trigger AND execution

---

## References

### Pattern Documentation

- **Failure mode**: `.claude/abstractions/failure_mode-2026-01-03-boundary-blindness.md`
- **This document**: Meta-analysis and integration roadmap

### Bug Hunt Evidence

- Instance #1: `.claude/bug-hunts/2026-01-03-linebot-returns-default-error-for-today.md`
- Instance #2: `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md`
- Instance #3: `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`

### Related Patterns

- **Infrastructure-Application Contract**: `.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md` (boundary configuration violations)

### Skills to Update

- `.claude/skills/error-investigation/SKILL.md` (add Principle #5)
- `.claude/skills/research/INVESTIGATION-CHECKLIST.md` (add Pre-Investigation section)
- `.claude/skills/error-investigation/BOUNDARY-AWARE-TEMPLATE.md` (new file)

### Principles to Update

- `.claude/CLAUDE.md` Principle #19 (new: Cross-Boundary Contract Testing)
- `.claude/CLAUDE.md` Principle #2 (note: boundaries in Progressive Evidence)
- `.claude/CLAUDE.md` Principle #15 (note: boundaries in Infrastructure-Application Contract)

---

## Metadata

**Pattern Type**: Meta-cognitive principle (investigation methodology)

**Confidence**: Very High (3 clear instances, user explicitly identified pattern, affects fundamental investigation approach)

**Created**: 2026-01-03

**Impact**: Critical (affects ALL future distributed system debugging)

**Graduation Status**: Ready for immediate integration (high confidence, clear fix, affects core methodology)

**Next Actions**: Update investigation skills → Update CLAUDE.md → Create templates → Practice boundary-aware investigations
