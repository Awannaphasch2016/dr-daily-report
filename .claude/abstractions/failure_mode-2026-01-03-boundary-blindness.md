---
pattern_type: failure_mode
confidence: high
created: 2026-01-03
instances: 3
tags: [investigation, debugging, execution-context, service-boundaries, runtime-environment]
---

# Failure Pattern: Boundary Blindness in Code Investigation

## Abstracted From

**Instances analyzed**: 3

1. **Precompute Not Scheduled - Missing TZ Environment Variable** (2026-01-03)
   - Source: Investigation of LINE bot errors for today's date
   - What I did wrong: Verified `_trigger_precompute()` code exists → Saw `PRECOMPUTE_CONTROLLER_ARN` needed → Concluded "precompute triggered" → **STOPPED**
   - What I missed: ticker_fetcher (scheduler Lambda) → invokes → precompute_controller (DIFFERENT Lambda) = **service boundary crossing**
   - Missing check: Does precompute_controller have TZ env var? (Different container, different environment)
   - Impact: Missed root cause, stopped investigation at Layer 1 (weakest evidence)
   - Detection: User pointed out "you didn't check WHERE the code runs"

2. **PDF Generation Not Executing - Lambda Container Cache** (2026-01-03)
   - Source: `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md`
   - What happened: Verified PDF code present in Docker image → Verified Lambda uses correct image digest → Concluded "code should execute"
   - What was missed: Build image (development boundary) ≠ Running container (runtime boundary)
   - Missing check: Is Lambda using FRESH container or CACHED container from previous deployment?
   - Boundary: Docker image build → Lambda container runtime (phase boundary)
   - Impact: 45 minutes debugging, required forced container refresh

3. **Generate PDF=True Not Executing - Tier Integration Gap** (2026-01-02)
   - Source: `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`
   - What happened: Verified `compute_and_store_report(generate_pdf=True)` exists → Checked default parameter is True → Concluded "PDFs should generate"
   - What was missed: Scheduler only calls `store_ticker_data()`, NOT `compute_and_store_report()` = **workflow boundary**
   - Missing check: WHERE is this function called? WHAT invokes it?
   - Boundary: Tier 1 (ticker data fetch) → Tier 2 (report generation) - separate workflows, not integrated
   - Impact: Complete PDF generation failure, took 30 minutes to find root cause

---

## Pattern Description

### What It Is

**Boundary Blindness**: When investigating code correctness, verifying that logic/functions exist WITHOUT identifying:
1. WHERE the code executes (which service, container, environment)
2. HOW execution crosses boundaries (Lambda → Lambda, Build → Runtime, Tier 1 → Tier 2)
3. WHAT initial conditions are required at each boundary (env vars, configuration, permissions)

This leads to concluding "code is correct" while missing that **code runs in different execution contexts** with different configurations.

### When It Occurs

**Trigger conditions**:
1. Multi-service architecture (Lambda → Lambda, API → Worker, Scheduler → Controller)
2. Multi-phase execution (Build → Deploy → Runtime, Development → Production)
3. Multi-tier workflows (Data Fetch → Report Generation, API Request → Background Worker)
4. Code verified in isolation without mapping execution context

**Common scenarios**:
- "Function exists in codebase" → But never called in this execution path
- "Code deployed to Lambda" → But running in cached container with old code
- "Environment variable set" → But in different Lambda function
- "Tests pass locally" → But production crosses service boundaries with different configs

### Why It Happens

**Root causes**:

1. **Code-centric investigation**:
   - Focus: "Does this function exist? Is the logic correct?"
   - Missing: "Where does this run? What boundaries does it cross?"
   - Result: Verify code correctness without execution context

2. **Assumption of monolithic execution**:
   - Implicit assumption: Code runs in single environment
   - Reality: Distributed system with multiple execution contexts
   - Example: ticker_fetcher invokes precompute_controller (2 different Lambdas, 2 different env configurations)

3. **Boundary invisibility**:
   - Service boundaries: Lambda function names look similar, easy to conflate
   - Phase boundaries: "Deployed" doesn't mean "running fresh container"
   - Workflow boundaries: Separate schedulers, separate triggers, separate execution paths
   - No visual diagram showing execution flow across boundaries

4. **Stopping at weak evidence**:
   - Layer 1 (status code): "Lambda invoked successfully (HTTP 202)" → Doesn't verify what Lambda does
   - Layer 2 (payload): "Function definition found in codebase" → Doesn't verify function is called
   - Layer 3 (logs): Not checked because assumed code correctness
   - Layer 4 (ground truth): Not checked because stopped at Layer 1

---

## Concrete Instances

### Instance 1: Precompute Not Scheduled (Primary Example - This Session)

**From**: Investigation of LINE bot returning errors for 2026-01-03

**Context**: Users report "report not ready" errors for today's date

**My Investigation (WRONG - Boundary-Blind)**:

```
Step 1: Find code that does precompute
  → Found: _trigger_precompute() in ticker_fetcher_handler.py

Step 2: Verify function exists
  → Read function definition
  → Saw: Invokes Lambda with PRECOMPUTE_CONTROLLER_ARN
  → Saw: Returns HTTP 202 (async invocation)

Step 3: Conclude
  → "Precompute is triggered by scheduler"
  → "Maybe precompute hasn't run today yet"
  → STOPPED INVESTIGATION (wrong conclusion!)

Missing questions:
  ❌ WHERE does _trigger_precompute() run? (ticker_fetcher Lambda)
  ❌ WHAT does it invoke? (precompute_controller Lambda - DIFFERENT service)
  ❌ What are initial conditions for precompute_controller?
  ❌ Does precompute_controller have required env vars? (TZ, etc.)
```

**Boundary-Aware Investigation (CORRECT)**:

```
Step 1: Find code that does precompute
  → Found: _trigger_precompute() in ticker_fetcher_handler.py

Step 2: WHERE DOES THIS RUN? (boundary identification)
  → Runs in: ticker_fetcher Lambda container
  → What it does: Invokes another Lambda (precompute_controller)
  → Boundary crossed: Service boundary (Lambda → Lambda)
  → Evidence: boto3.client('lambda').invoke(FunctionName=...)

Step 3: What are INITIAL CONDITIONS at boundary?
  → ticker_fetcher side:
    - Needs PRECOMPUTE_CONTROLLER_ARN (env var)
    - Has IAM permission to invoke Lambda
  → precompute_controller side:
    - Needs TZ env var (for Bangkok timezone queries)
    - Needs STEP_FUNCTIONS_ARN (to start workflow)
    - Has IAM permission to start Step Functions
  → Boundary contract: Event payload, IAM permissions, env vars

Step 4: Verify BOTH SIDES of boundary
  → ticker_fetcher: ✅ Has PRECOMPUTE_CONTROLLER_ARN (checked Terraform)
  → precompute_controller: ❌ Missing TZ (DIDN'T CHECK - but should have!)

Result: Would have found missing TZ immediately
```

**What I missed**:
- **Service boundary**: ticker_fetcher ≠ precompute_controller (different Lambdas, different configs)
- **Boundary crossing**: Lambda invocation = crossing service boundary with separate environment
- **Initial conditions**: Each side has own env vars, must verify BOTH

**Impact**: Stopped at Layer 1 (weakest evidence), missed root cause

---

### Instance 2: PDF Code Not Executing (Container Cache Boundary)

**From**: `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md`

**Context**: PDF generation code deployed but not executing

**Investigation Pattern (Boundary-Blind)**:

```
Step 1: Verify code exists
  → Docker image contains PDF generation code ✅
  → Python compiles successfully ✅

Step 2: Verify deployment
  → Lambda function config shows correct image digest ✅
  → CodeSha256 matches Docker image ✅

Step 3: Conclude
  → "Code is deployed, should execute"
  → BUT: CloudWatch logs show ZERO DEBUG statements (code not running!)
```

**Missing boundary awareness**:

```
Boundary: Docker Image Build → Lambda Container Runtime

Build side (✅ verified):
  - Docker image contains PDF code
  - Image pushed to ECR
  - Lambda config points to image digest

Runtime side (❌ NOT verified):
  - Is Lambda using FRESH container?
  - OR using CACHED container from previous deployment?
  - Container cache = phase boundary (old code still running)

Boundary contract:
  - Lambda eventually refreshes containers
  - But warm containers persist for minutes/hours
  - Deployment updates config, but not running containers
```

**What was missed**:
- **Phase boundary**: Build-time code ≠ Runtime code (cached containers)
- **Container lifecycle**: Deployment updates image pointer, not running containers
- **Verification needed**: Not just "image deployed" but "containers refreshed"

**Resolution**: Force container refresh (set concurrency to 0, wait, restore)

---

### Instance 3: Generate PDF Not Executing (Workflow Boundary)

**From**: `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md`

**Context**: `generate_pdf=True` parameter exists but PDFs not generated

**Investigation Pattern (Boundary-Blind)**:

```
Step 1: Verify function signature
  → compute_and_store_report(generate_pdf=True) ✅
  → Default parameter is True ✅

Step 2: Check for overrides
  → Grep for generate_pdf=False
  → None found ✅

Step 3: Conclude
  → "PDFs should generate"
  → BUT: S3 has 0 PDFs (function never called!)
```

**Missing boundary awareness**:

```
Boundary: Scheduler Workflow Tier 1 → Tier 2

Tier 1 (Data Fetch):
  - EventBridge → ticker_fetcher Lambda
  - Fetches ticker data from Yahoo Finance
  - Stores to Aurora ticker_data table
  - ✅ This executes successfully

Tier 2 (Report Generation):
  - precompute_controller → Step Functions → report workers
  - Calls compute_and_store_report(generate_pdf=True)
  - ❌ This is NOT integrated with Tier 1

Boundary contract:
  - Tier 1 triggers Tier 2 (OR Tier 2 separately scheduled)
  - Actual: Tier 1 triggers async (fire-and-forget HTTP 202)
  - Missing: Verification that Tier 2 actually starts
```

**What was missed**:
- **Workflow boundary**: Data fetch ≠ Report generation (separate tiers)
- **Execution path**: Scheduler only calls `store_ticker_data()`, NOT `compute_and_store_report()`
- **Integration gap**: No automatic trigger from Tier 1 to Tier 2

**Resolution**: Add scheduled trigger for Tier 2 OR integrate into Tier 1

---

## Generalized Pattern

### Signature (How to Recognize It)

**Observable characteristics**:

1. **Code verification without context mapping**:
   - "Function exists" ✅
   - "WHERE is it called?" ❌
   - "WHAT service runs it?" ❌

2. **Stopping at weak evidence layers**:
   - Layer 1: Status code 200/202 (execution started)
   - Layer 2: Function definition found (code exists)
   - **SKIP Layer 3**: CloudWatch logs (what actually happened)
   - **SKIP Layer 4**: Ground truth (side effects, state changes)

3. **Implicit monolithic assumption**:
   - Assume: Code runs in single environment
   - Reality: Code crosses service boundaries (Lambda → Lambda, Tier → Tier)
   - Miss: Each boundary has own configuration, initial conditions

4. **"Code is correct" without "Code executes correctly"**:
   - Code logic verified ✅
   - Code deployed ✅
   - Code RUNS? ❌ (not checked)

### Preconditions (What Enables It)

**Conditions that must hold**:

1. **Distributed system architecture**:
   - Multiple services (Lambdas, containers, workers)
   - Service boundaries (invocations, triggers, message passing)
   - Each service has own environment configuration

2. **Multi-phase execution**:
   - Build → Deploy → Runtime (each phase has own state)
   - Development → Staging → Production (each env has own config)
   - Cached state (containers, artifacts) persists across phases

3. **No execution context diagram**:
   - Code exists in files
   - But execution flow crosses boundaries
   - No visual map of "this Lambda invokes that Lambda"

4. **Investigation focuses on code, not execution**:
   - Read code to verify logic
   - But don't trace execution path
   - Don't identify service boundaries

### Components (What's Involved)

**Entities**:

1. **Execution contexts** (each with own environment):
   - Lambda functions (separate containers, env vars)
   - Docker images vs running containers (build vs runtime)
   - Workflow tiers (data fetch vs report generation)

2. **Boundaries** (transitions between contexts):
   - Service boundary: Lambda → Lambda invocation
   - Phase boundary: Docker image → Running container
   - Workflow boundary: Scheduler → Worker (separate execution paths)
   - Time boundary: Deploy → Runtime (cached vs fresh state)

3. **Initial conditions** (required at each boundary):
   - Environment variables (TZ, API keys, table names)
   - IAM permissions (invoke Lambda, start Step Functions)
   - Configuration (function ARNs, bucket names)
   - State (fresh container vs cached container)

**Dependency chain**:

```
Code exists in repository
    ↓ (built into)
Docker Image (build boundary)
    ↓ (deployed as)
Lambda Function Configuration (deployment boundary)
    ↓ (runs in)
Lambda Container (runtime boundary - may be cached!)
    ↓ (invokes)
Other Lambda Function (service boundary - different env vars!)
    ↓ (starts)
Step Functions Workflow (workflow boundary - separate execution)
```

**Failure point**: Investigation stops at "Code exists" without tracing execution through boundaries

### Mechanism (How It Works/Fails)

**Failure flow**:

```
Step 1: User Reports Error
├─ Example: "LINE bot returns error for today's reports"
└─ Symptom: Cache miss for 2026-01-03

Step 2: Investigate Code (Boundary-Blind)
├─ Read: _trigger_precompute() function definition
├─ Verify: Function invokes precompute_controller
├─ Check: Returns HTTP 202 (async invocation)
└─ Conclude: "Precompute is triggered"

Step 3: Stop Investigation (Wrong Conclusion!)
├─ Assumption: "Code is correct"
├─ Missing: "WHERE does this run?"
├─ Missing: "WHAT does precompute_controller need?"
└─ Result: Missed root cause (missing TZ env var)

Step 4: User Points Out Boundary
├─ "You didn't check WHERE code runs"
├─ ticker_fetcher ≠ precompute_controller (different Lambdas)
└─ precompute_controller missing TZ env var

Step 5: Correct Investigation (Boundary-Aware)
├─ Map execution: ticker_fetcher → precompute_controller (service boundary)
├─ Identify initial conditions: precompute_controller needs TZ env var
├─ Verify: Check Terraform for precompute_controller env vars
└─ Find: Missing TZ → Root cause identified
```

**Why it's hard to detect**:

- Code verification feels thorough ("function exists, parameter correct")
- Service boundaries not visible in code (boto3.invoke looks like function call)
- Environment configuration separate from code (Terraform, not Python)
- No "execution context map" showing service boundaries
- Stopping at Layer 1 (weak evidence) feels sufficient

---

## Pattern Template

### Failure Mode Template: Boundary Blindness

**Pattern Name**: Boundary Blindness in Code Investigation

**Category**: Investigation methodology, debugging, system analysis

**Symptoms**:

1. **Investigation pattern**:
   - ✅ Verify code exists (function definition found)
   - ✅ Verify code logic (parameter defaults correct)
   - ❌ Verify code EXECUTES (where? with what config?)
   - ❌ Verify boundary crossings (service → service, build → runtime)

2. **Conclusion pattern**:
   - "Code is correct" ← Logic verified
   - "Code is deployed" ← Image/artifact verified
   - "Should work" ← Assumption without execution context
   - **BUT**: Production fails (wrong environment, missing config, cached state)

3. **Evidence pattern**:
   - Stop at Layer 1 (status code, function exists)
   - Skip Layer 3 (CloudWatch logs - what actually happened)
   - Skip Layer 4 (ground truth - state changes, side effects)
   - Miss root cause (boundary configuration issue)

**Root Cause**:

**What actually causes this**:
- Investigation focuses on code correctness without execution context
- Service boundaries invisible in code (Lambda invocation looks like function call)
- Initial conditions per boundary not identified (env vars, permissions, config)
- Stopping at weak evidence (code exists) without strong evidence (execution verified)

**Detection**:

**Mandatory boundary identification checklist** (use BEFORE verifying code):

```markdown
## Execution Context Mapping (MANDATORY FIRST STEP)

### 1. WHERE does this code run?
- [ ] Which service/Lambda/container?
- [ ] What triggers execution?
- [ ] What environment (dev/staging/prod)?

### 2. WHAT boundaries does execution cross?
- [ ] Service boundaries: Lambda → Lambda, API → Worker
- [ ] Phase boundaries: Build → Deploy → Runtime
- [ ] Workflow boundaries: Tier 1 → Tier 2, Scheduler → Worker
- [ ] Time boundaries: Fresh deployment → Cached state

### 3. WHAT are initial conditions at EACH boundary?
For each boundary identified:
- [ ] Environment variables needed (which side?)
- [ ] IAM permissions needed (which side?)
- [ ] Configuration needed (ARNs, table names, etc.)
- [ ] State assumptions (fresh container? cached?)

### 4. HOW to verify boundary contract?
- [ ] Check Terraform for env vars (BOTH sides of service boundary)
- [ ] Check CloudWatch logs (verify execution, not just invocation)
- [ ] Check ground truth (S3 files, database state, side effects)
- [ ] Force boundary refresh if needed (container, cache, etc.)
```

**Investigation template (boundary-aware)**:

```markdown
## Code Investigation: [Feature/Function Name]

### Step 1: Map Execution Context
**WHERE does this run?**
- Service: [Lambda name / Container / Worker]
- Trigger: [EventBridge / API / Manual]
- Environment: [dev / staging / prod]

**Execution flow** (list ALL steps):
1. [Service A] receives trigger
2. [Service A] → [Service B] (boundary: [type])
3. [Service B] → [Service C] (boundary: [type])
4. Final outcome: [S3 upload / DB write / etc.]

### Step 2: Identify Boundaries
For each step in execution flow:
- Boundary type: [Service / Phase / Workflow / Time]
- Crossing mechanism: [Lambda invoke / Container start / Step Functions]
- Contract: [What must be true for crossing to succeed?]

### Step 3: Verify Initial Conditions (BOTH SIDES)
For each boundary:
- **Side A** (caller):
  - [ ] Has permission to cross boundary?
  - [ ] Has correct target identifier (ARN, etc.)?
  - [ ] Provides required input?

- **Side B** (callee):
  - [ ] Has required env vars? (check Terraform)
  - [ ] Has required permissions? (check IAM)
  - [ ] Has required config? (check Doppler)

### Step 4: Progressive Evidence Strengthening
- [ ] Layer 1 (weak): Status code / Exit code
- [ ] Layer 2 (stronger): Response payload / Function exists
- [ ] Layer 3 (stronger): CloudWatch logs (actual execution trace)
- [ ] Layer 4 (strongest): Ground truth (S3 files, DB records, side effects)

### Step 5: Verify Boundary Contract
For each boundary:
- [ ] Check logs on BOTH sides
- [ ] Verify state on BOTH sides
- [ ] Confirm contract upheld (or identify violation)
```

**Prevention**:

1. **Always start with execution context mapping**:
   - Draw diagram: Service A → Service B → Service C
   - Identify each boundary type
   - List initial conditions for each boundary

2. **Never skip Layer 3 (logs) and Layer 4 (ground truth)**:
   - Code exists (Layer 2) ≠ Code executes (Layer 3)
   - Code deployed (Layer 2) ≠ Running fresh (Layer 4)

3. **Create execution context diagrams**:
   - Visual map of service boundaries
   - "This Lambda invokes that Lambda"
   - "This container is built here, runs there"

4. **Boundary checklist in investigation skill**:
   - Add to `.claude/skills/error-investigation/INVESTIGATION-CHECKLIST.md`
   - Add to `.claude/skills/research/INVESTIGATION-CHECKLIST.md`
   - Mandate: "Map boundaries BEFORE verifying code"

**Resolution**:

**Immediate fix** (for current investigation):

```bash
# 1. Stop current investigation
# 2. Map execution context:
#    - WHERE: ticker_fetcher Lambda → precompute_controller Lambda
#    - BOUNDARY: Service boundary (Lambda invocation)
#    - CONTRACT: precompute_controller needs TZ env var

# 3. Verify BOTH sides:
# Side A (ticker_fetcher):
aws lambda get-function-configuration \
  --function-name ticker_fetcher \
  | jq '.Environment.Variables.PRECOMPUTE_CONTROLLER_ARN'

# Side B (precompute_controller):
aws lambda get-function-configuration \
  --function-name precompute_controller \
  | jq '.Environment.Variables.TZ'  # Check if exists!

# 4. If missing, check Terraform:
grep -A 20 "resource.*precompute_controller" terraform/*.tf | grep -A 10 "environment"

# 5. Fix missing config:
# Add to terraform/precompute_controller.tf:
#   environment {
#     variables = {
#       TZ = "Asia/Bangkok"
#       ...
#     }
#   }
```

**Long-term prevention** (update investigation methodology):

1. Add to error-investigation skill:
   ```markdown
   ## Mandatory Pre-Investigation Step: Execution Context Mapping

   BEFORE verifying code correctness:
   1. Map execution flow (Service A → Service B → ...)
   2. Identify boundaries (Service / Phase / Workflow / Time)
   3. List initial conditions for EACH boundary
   4. Verify conditions on BOTH sides of EACH boundary
   ```

2. Add to research skill:
   ```markdown
   ## Investigation Anti-Pattern: Boundary Blindness

   ❌ WRONG: "Code exists → Should work"
   ✅ RIGHT: "Code exists → WHERE runs? → WHAT needs? → Contract verified?"
   ```

3. Create new CLAUDE.md principle:
   ```markdown
   ### 19. Cross-Boundary Contract Testing

   Code correctness ≠ Execution correctness. Map execution boundaries
   (Service, Phase, Workflow, Time) BEFORE verifying code logic. Each
   boundary has initial conditions (env vars, permissions, config) that
   must be verified on BOTH sides. Tests must verify boundary contracts,
   not just code in isolation.
   ```

---

## Variations

**Observed variations** across instances:

### Variation 1: Boundary Type

**Service Boundary** (Lambda → Lambda):
- Crossing: boto3.client('lambda').invoke()
- Contract: Caller has invoke permission, callee has env vars
- Detection: Check Terraform for BOTH Lambdas
- Example: ticker_fetcher → precompute_controller (Instance #1)

**Phase Boundary** (Build → Runtime):
- Crossing: Docker image deployed → Container starts
- Contract: Fresh container uses new code, cached container uses old code
- Detection: Check container lifecycle, force refresh if needed
- Example: Deployed PDF code not executing (Instance #2, cached container)

**Workflow Boundary** (Tier → Tier):
- Crossing: Tier 1 completes → Tier 2 starts
- Contract: Tier 1 triggers Tier 2 OR Tier 2 separately scheduled
- Detection: Check workflow orchestration (EventBridge, Step Functions)
- Example: Data fetch doesn't trigger report generation (Instance #3)

**Time Boundary** (Deploy → Runtime):
- Crossing: Deployment updates config → Running containers adopt changes
- Contract: Eventual consistency (containers refresh over time)
- Detection: Wait for refresh OR force refresh (concurrency manipulation)

**Implication**: Each boundary type has different contract verification method

### Variation 2: Evidence Layer Where Investigation Stops

**Stop at Layer 1** (weakest):
- Evidence: HTTP 202 (async invocation returned)
- Conclusion: "Precompute triggered"
- Missing: Did it actually START? (Layer 3 - logs)
- Impact: High (completely miss root cause)

**Stop at Layer 2** (stronger but insufficient):
- Evidence: Function definition exists, parameter correct
- Conclusion: "PDFs should generate"
- Missing: Is function CALLED? (Layer 3 - execution trace)
- Impact: Medium (verify code but not execution path)

**Reach Layer 3** (logs) but misinterpret:
- Evidence: CloudWatch logs show Lambda invoked
- Conclusion: "Lambda executed successfully"
- Missing: Check logs on OTHER SIDE of boundary (callee, not just caller)

**Implication**: Must progress to Layer 3-4 AND check BOTH sides of boundary

### Variation 3: Boundary Visibility

**Invisible boundary** (looks like function call):
- Code: `boto3.client('lambda').invoke(FunctionName='other_lambda')`
- Looks like: Normal function call
- Actually: Service boundary crossing (different environments)
- Easy to miss

**Visible boundary** (explicit crossing):
- Code: `docker build ... && docker push ... && kubectl apply ...`
- Clearly: Build → Deploy → Runtime phases
- Harder to miss

**Implication**: Invisible boundaries (Lambda invocations, async triggers) most dangerous

---

## When to Deviate

**Scenarios where boundary awareness might be excessive**:

1. **True monolithic execution**:
   - Single Lambda, single execution context
   - No service boundaries to cross
   - BUT: Still has phase boundary (build → runtime, deploy → execution)

2. **Development environment only**:
   - Local development (single machine, single environment)
   - No distributed services
   - BUT: Production WILL have boundaries, so practice still valuable

3. **Time-critical debugging**:
   - Production outage, need quick fix
   - Can verify code quickly, deploy fast
   - BUT: Must verify execution after deploy (don't skip Layer 3-4)

**Modification needed**:

Even in simple cases, minimum boundary awareness:
```markdown
## Quick Investigation (Still Boundary-Aware)

1. WHERE: [Single Lambda / Local process / etc.]
2. BOUNDARIES: [Minimal: Build → Runtime at least]
3. VERIFY: [Check logs after deploy to confirm execution]
```

---

## Graduation Path

### Pattern Confidence: **HIGH** (3 clear instances, user explicitly identified pattern)

**Graduation steps**:

#### 1. Update Error-Investigation Skill

File: `.claude/skills/error-investigation/SKILL.md`

Add section:

```markdown
### Principle 5: Execution Context Precedes Code Verification

**From This Session (Boundary Blindness Pattern)**:
> "You conclude that code is true without taking into account that code has to be run somewhere or different pieces can be run in different services, and without identifying the 'boundary' you miss things like 'testing initial condition' that's required to execute correctly."

**Why This Matters**:

Code correctness ≠ Execution correctness. Code must run SOMEWHERE, with SOME initial conditions, crossing SOME boundaries.

**The Problem**:

```python
# ❌ WRONG Investigation
# 1. Verify: _trigger_precompute() function exists ✅
# 2. Verify: Invokes precompute_controller Lambda ✅
# 3. Conclude: "Precompute is triggered"
# 4. STOP (missed root cause!)

# Missing:
# - WHERE does _trigger_precompute() run? (ticker_fetcher Lambda)
# - WHAT does it invoke? (precompute_controller Lambda - DIFFERENT service)
# - What are initial conditions? (precompute_controller needs TZ env var)
```

**The Solution**:

```markdown
## Mandatory Pre-Investigation: Execution Context Mapping

BEFORE verifying code correctness, answer:

1. WHERE does this code run?
   - Which service/Lambda/container?
   - What environment (dev/staging/prod)?

2. WHAT boundaries does execution cross?
   - Service boundaries: Lambda A → Lambda B
   - Phase boundaries: Build → Deploy → Runtime
   - Workflow boundaries: Tier 1 → Tier 2

3. WHAT are initial conditions at EACH boundary?
   For each boundary:
   - Environment variables (which side?)
   - IAM permissions (which side?)
   - Configuration (ARNs, secrets, etc.)
   - State assumptions (fresh? cached?)

4. HOW to verify boundary contract?
   - Check Terraform env vars (BOTH sides)
   - Check CloudWatch logs (BOTH sides)
   - Check ground truth (S3, DB, side effects)
```

**Example (Correct Investigation)**:

```markdown
## Investigation: Precompute Not Running

### Step 1: Map Execution Context
WHERE: ticker_fetcher Lambda (scheduler)
TRIGGER: EventBridge schedule (5:00 AM Bangkok)

EXECUTION FLOW:
1. EventBridge → ticker_fetcher Lambda
2. ticker_fetcher → precompute_controller Lambda (SERVICE BOUNDARY)
3. precompute_controller → Step Functions workflow
4. Step Functions → report worker Lambdas

### Step 2: Identify Boundaries
Boundary #1: ticker_fetcher → precompute_controller
- Type: Service boundary (Lambda invocation)
- Mechanism: boto3.client('lambda').invoke()
- Contract:
  - Caller needs: PRECOMPUTE_CONTROLLER_ARN env var
  - Callee needs: TZ env var, STEP_FUNCTIONS_ARN

### Step 3: Verify Initial Conditions (BOTH SIDES)
ticker_fetcher (caller):
- [x] Has PRECOMPUTE_CONTROLLER_ARN? → Check Terraform
- [x] Has IAM permission to invoke? → Check IAM role

precompute_controller (callee):
- [ ] Has TZ env var? → CHECK TERRAFORM (not just assume!)
- [ ] Has STEP_FUNCTIONS_ARN? → Check Terraform
- [ ] Has IAM permission to start Step Functions?

### Step 4: Verification
# Check caller env vars
aws lambda get-function-configuration \
  --function-name ticker_fetcher \
  | jq '.Environment.Variables.PRECOMPUTE_CONTROLLER_ARN'

# Check CALLEE env vars (THIS IS CRITICAL!)
aws lambda get-function-configuration \
  --function-name precompute_controller \
  | jq '.Environment.Variables.TZ'  # Missing? ROOT CAUSE!

### Step 5: Verify Execution (Layer 3)
# Not just "invoke returned 202" (Layer 1)
# Check CloudWatch logs on BOTH sides:
aws logs tail /aws/lambda/precompute_controller --since 5m
```
```

#### 2. Update Research Skill Investigation Checklist

File: `.claude/skills/research/INVESTIGATION-CHECKLIST.md`

Add section at TOP (before all other checks):

```markdown
## Pre-Investigation: Execution Context Mapping (MANDATORY)

**DO THIS FIRST** before checking code, recent changes, or errors:

### Execution Flow Diagram

Draw the execution flow:
```
[Trigger] → [Service A] → [Service B] → [Service C] → [Outcome]
            (Boundary 1) (Boundary 2) (Boundary 3)
```

For this investigation:
```
_________________ → _________________ → _________________ → _________________
(Boundary type:    ) (Boundary type:    ) (Boundary type:    )
```

### Boundary Identification Checklist

For EACH boundary in execution flow:

- [ ] **Boundary type**:
  - Service boundary (Lambda → Lambda, API → Worker)
  - Phase boundary (Build → Deploy, Deploy → Runtime)
  - Workflow boundary (Tier 1 → Tier 2, Scheduler → Worker)
  - Time boundary (Fresh deploy → Cached state)

- [ ] **Crossing mechanism**:
  - boto3.client('lambda').invoke()
  - Docker image → Container start
  - EventBridge → Lambda trigger
  - Step Functions state transition

- [ ] **Initial conditions (LEFT side)**:
  - Environment variables needed
  - IAM permissions needed
  - Configuration needed (ARNs, etc.)

- [ ] **Initial conditions (RIGHT side)**:
  - Environment variables needed
  - IAM permissions needed
  - Configuration needed
  - State assumptions (fresh? cached?)

- [ ] **How to verify contract**:
  - Check Terraform for env vars
  - Check CloudWatch logs
  - Check ground truth (S3, DB, etc.)

### Common Boundary Mistakes

❌ **WRONG**: "Function exists → Should work"
✅ **RIGHT**: "Function exists → WHERE called? → WHAT service? → WHAT env vars?"

❌ **WRONG**: "Lambda returns 202 → Success"
✅ **RIGHT**: "Lambda returns 202 → Check logs on INVOKED Lambda → Verify execution"

❌ **WRONG**: "Code deployed → Should run"
✅ **RIGHT**: "Code deployed → Fresh container? → Cached container? → Force refresh?"

---

**AFTER completing execution context mapping**, proceed with standard investigation checklist:

## 1. What Changed Recently?
(... existing content ...)
```

#### 3. Create New CLAUDE.md Principle #19

File: `.claude/CLAUDE.md`

Add after Principle #18:

```markdown
### 19. Cross-Boundary Contract Testing

**Context**: Distributed systems have execution boundaries (Service, Phase, Workflow, Time) where code crosses from one context to another. Each boundary has initial conditions and contracts that must be verified.

**Investigation anti-pattern**: Verifying code logic correctness WITHOUT mapping execution boundaries, leading to "code is correct but doesn't execute correctly" failures.

**Principle**: Code correctness ≠ Execution correctness. Map execution boundaries BEFORE verifying code logic. Each boundary has two sides with own initial conditions (env vars, permissions, config). Investigation must verify boundary contracts on BOTH sides, not just verify code exists.

**Boundary types**:
- **Service**: Lambda A → Lambda B (different containers, different env vars)
- **Phase**: Docker build → Container runtime (fresh vs cached state)
- **Workflow**: Tier 1 → Tier 2 (separate schedulers, separate execution paths)
- **Time**: Deploy → Runtime (eventual consistency, container lifecycle)

**Mandatory investigation checklist** (BEFORE code verification):
1. **WHERE** does code run? (which service, container, environment)
2. **WHAT** boundaries does execution cross? (service, phase, workflow, time)
3. **WHAT** initial conditions at each boundary? (env vars, permissions, config - BOTH sides)
4. **HOW** to verify boundary contract? (Terraform, logs, ground truth - BOTH sides)

**Anti-patterns**:
- ❌ "Function exists → Should work" (missing WHERE it runs)
- ❌ "Lambda invoked → Success" (only checked caller, not callee)
- ❌ "Code deployed → Should execute" (missing fresh vs cached container check)
- ❌ Stopping at Layer 1-2 evidence (weak signals like status codes, skip logs)

**Correct pattern**:
```markdown
## Investigation: [Feature/Function]

### 1. Map Execution (MANDATORY FIRST)
WHERE: [Service name, container, environment]
FLOW: [Step 1] → [Step 2] → [Step 3] → [Outcome]
BOUNDARIES: [List each boundary type]

### 2. Identify Initial Conditions (EACH BOUNDARY, BOTH SIDES)
Boundary: [Left] → [Right]
- Left needs: [env vars, permissions, config]
- Right needs: [env vars, permissions, config, state]

### 3. Verify Contract (BOTH SIDES)
- Check Terraform (env vars, IAM)
- Check CloudWatch logs (execution traces)
- Check ground truth (S3, DB, side effects)
```

See [Boundary Blindness Pattern](.claude/abstractions/failure_mode-2026-01-03-boundary-blindness.md) for detailed examples.

**Related**: Integrates with Principle #2 (Progressive Evidence Strengthening - verify execution, not just code), Principle #1 (Defensive Programming - validate at boundaries), Principle #15 (Infrastructure-Application Contract - boundary configuration).
```

#### 4. Create Boundary-Aware Investigation Template

File: `.claude/skills/error-investigation/BOUNDARY-AWARE-TEMPLATE.md`

```markdown
# Boundary-Aware Investigation Template

**Use this template for ALL investigations** (especially distributed system failures)

---

## Pre-Investigation: Execution Context Mapping

### Step 1: Draw Execution Flow

```
Execution Flow:
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Trigger   │─────>│  Service A  │─────>│  Service B  │─────>│   Outcome   │
│             │      │             │      │             │      │             │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
                          │                     │                     │
                     Boundary 1           Boundary 2           Boundary 3
                     Type: ______         Type: ______         Type: ______
```

For this investigation:
- Trigger: ___________________________
- Service A: _________________________
- Service B: _________________________
- Outcome: ___________________________

### Step 2: Identify Boundaries

| Boundary | Type | Left (Caller) | Right (Callee) | Crossing Mechanism |
|----------|------|---------------|----------------|-------------------|
| 1        |      |               |                |                   |
| 2        |      |               |                |                   |
| 3        |      |               |                |                   |

Boundary types: Service / Phase / Workflow / Time

### Step 3: Initial Conditions (EACH Boundary)

#### Boundary 1: [Left] → [Right]

**Left side** ([Service/Phase name]):
- [ ] Environment variables: __________________
- [ ] IAM permissions: __________________
- [ ] Configuration: __________________
- [ ] How to verify: __________________

**Right side** ([Service/Phase name]):
- [ ] Environment variables: __________________
- [ ] IAM permissions: __________________
- [ ] Configuration: __________________
- [ ] State assumptions: __________________
- [ ] How to verify: __________________

**Boundary contract**:
- What must be true for crossing to succeed? __________________
- How to verify contract? __________________

#### Boundary 2: [Left] → [Right]

(Repeat for each boundary)

### Step 4: Verification Commands

```bash
# Verify Left side
aws lambda get-function-configuration \
  --function-name [left-service] \
  | jq '.Environment.Variables'

# Verify Right side
aws lambda get-function-configuration \
  --function-name [right-service] \
  | jq '.Environment.Variables'

# Check logs (Left)
aws logs tail /aws/lambda/[left-service] --since 5m

# Check logs (Right)
aws logs tail /aws/lambda/[right-service] --since 5m

# Check ground truth
[Command to verify actual outcome: S3 ls, DB query, etc.]
```

---

## Investigation: Code & Logic

**ONLY AFTER completing execution context mapping above**

### Code Verification
- [ ] Function/feature exists in codebase
- [ ] Logic is correct
- [ ] Parameters have correct defaults
- [ ] No syntax errors

### Deployment Verification
- [ ] Code deployed to correct service
- [ ] Docker image contains code
- [ ] Lambda config points to correct image

---

## Progressive Evidence Strengthening

### Layer 1: Surface Signals (Weakest)
- [ ] Status code: __________________
- [ ] Exit code: __________________
- Conclusion: Execution finished, but NOT necessarily correct

### Layer 2: Content Signals (Stronger)
- [ ] Response payload: __________________
- [ ] Function definition exists: __________________
- Conclusion: Code exists, but NOT necessarily executed

### Layer 3: Observability Signals (Stronger Still)
- [ ] CloudWatch logs (Left side): __________________
- [ ] CloudWatch logs (Right side): __________________
- [ ] Execution traces: __________________
- Conclusion: What actually happened

### Layer 4: Ground Truth (Strongest)
- [ ] S3 files: __________________
- [ ] Database records: __________________
- [ ] Side effects: __________________
- Conclusion: Actual outcome verified

---

## Boundary Failure Checklist

If execution fails, check EACH boundary:

### Service Boundary (Lambda → Lambda)
- [ ] Caller has invoke permission?
- [ ] Caller has correct ARN/name?
- [ ] Callee has required env vars?
- [ ] Callee has required permissions?
- [ ] Logs on BOTH sides checked?

### Phase Boundary (Build → Runtime)
- [ ] Code in Docker image?
- [ ] Lambda config updated?
- [ ] Fresh container OR cached?
- [ ] Container refresh forced if needed?

### Workflow Boundary (Tier → Tier)
- [ ] Tier 1 triggers Tier 2?
- [ ] OR Tier 2 separately scheduled?
- [ ] Integration verified (not fire-and-forget)?
- [ ] Step Functions execution started?

### Time Boundary (Deploy → Runtime)
- [ ] Deployment completed?
- [ ] Sufficient time for propagation?
- [ ] State refreshed (not cached)?

---

## Root Cause Analysis

### Boundary Where Failure Occurred
Boundary: __________________ → __________________

### Which Side Failed?
- [ ] Left side (caller): Missing __________________
- [ ] Right side (callee): Missing __________________

### Initial Condition Violated
Required: __________________
Actual: __________________

### Fix Required
- [ ] Update Terraform: __________________
- [ ] Update Doppler: __________________
- [ ] Force refresh: __________________
- [ ] Integration change: __________________

---

## Post-Fix Verification

- [ ] Boundary contract now satisfied?
- [ ] Logs show execution on BOTH sides?
- [ ] Ground truth verified (S3, DB, etc.)?
- [ ] Progressive evidence (Layer 1 → 4) all pass?
```

---

## Action Items

- [x] Pattern extracted from 3 instances
- [x] Template created for failure mode
- [ ] Update error-investigation skill (Principle 5: Execution Context Precedes Code Verification)
- [ ] Update research skill investigation checklist (Pre-Investigation: Execution Context Mapping)
- [ ] Create CLAUDE.md Principle #19 (Cross-Boundary Contract Testing)
- [ ] Create boundary-aware investigation template
- [ ] Add boundary awareness to thinking process architecture
- [ ] Update deployment skill with boundary verification patterns

---

## References

### Bug Hunts

- `.claude/bug-hunts/2026-01-03-linebot-returns-default-error-for-today.md` - Precompute not scheduled (Instance #1)
- `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md` - Container cache boundary (Instance #2)
- `.claude/bug-hunts/2026-01-02-generate-pdf-true-not-executing.md` - Workflow tier boundary (Instance #3)

### Related Patterns

- `.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md` - Infrastructure-Application Contract (service boundary config)

### Principles

- CLAUDE.md Principle #2: Progressive Evidence Strengthening (verify execution, not just code)
- CLAUDE.md Principle #1: Defensive Programming (validate at boundaries)
- CLAUDE.md Principle #15: Infrastructure-Application Contract (boundary configuration)

---

## Metadata

**Pattern Type**: failure_mode (investigation methodology)

**Confidence**: High (3 clear instances, user explicitly identified pattern)

**Created**: 2026-01-03

**Instances**: 3 (all from recent debugging sessions)

**Last Updated**: 2026-01-03

**Graduation Status**: Ready for skill/principle integration

**Impact**: Critical (prevents boundary-blind investigations that miss root causes)
