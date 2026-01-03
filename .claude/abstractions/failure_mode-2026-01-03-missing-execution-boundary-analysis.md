# Failure Mode: Missing Execution Boundary Analysis

**Pattern Type**: failure_mode
**Abstracted From**: User feedback on PDF integration analysis
**Date**: 2026-01-03
**Confidence**: High (pattern recognized across multiple analyses)

---

## Pattern Description

**What it is**:
A systematic failure to identify and validate execution boundaries when analyzing code correctness. Concluding "code is correct" by reading source code without considering WHERE code executes, WHAT environment it requires, and WHAT initial conditions must be satisfied for execution to succeed.

**When it occurs**:
- Analyzing distributed systems (Lambda, Step Functions, Aurora, S3)
- Validating multi-component workflows
- Investigating "code looks correct but doesn't work" bugs
- Reviewing deployment configurations

**Why it happens**:
- **Code-centric bias**: Focus on Python/application logic, ignore infrastructure layer
- **Implicit assumptions**: Assume environment variables exist, databases have correct schema
- **Missing layer verification**: Validate code logic (Layer 1) but skip infrastructure contract (Layer 2-4)
- **Boundary blindness**: Don't identify WHERE code runs determines WHAT preconditions must hold

---

## Concrete Instances

### Instance 1: PDF Schema Bug Analysis (2026-01-03)

**Context**: Validating "If scheduler invokes Lambda, does Aurora store PDF references?"

**What I did WRONG**:
```markdown
# My analysis (INCOMPLETE)
✅ Code passes `pdf_s3_key` parameter to `store_report_from_api()`
✅ Function signature accepts `pdf_s3_key` parameter
✅ INSERT query... wait, missing column!

# Discovered bug at final step (Layer 4 ground truth)
```

**What I SHOULD have done** (boundary-aware):
```markdown
# Execution boundary analysis
1. CODE LAYER: Python function accepts `pdf_s3_key` ✅
2. DEPLOYMENT LAYER: Lambda has env vars? TZ? AURORA_HOST? [VERIFY]
3. INFRASTRUCTURE LAYER: Aurora table has `pdf_s3_key` column? [VERIFY]
4. INTEGRATION CONTRACT: Code INSERT matches schema? [VERIFY]

# Would have discovered bug at step 3 (before claiming "code works")
```

**Boundary I missed**: **Code → Aurora schema contract**
- Code runs in Lambda (Layer 1)
- Code writes to Aurora (Layer 2)
- Aurora has schema constraints (Layer 3)
- INSERT must match schema (Layer 4)

**Why boundary matters**:
- Python function signature doesn't guarantee database column exists
- Code can compile and run but fail silently if schema doesn't support operation

---

### Instance 2: Timezone Validation (2026-01-03)

**Context**: User asked "Is PDF timestamp Bangkok time or UTC?"

**What I did CORRECTLY** (this time):
```markdown
# Boundary-aware analysis
1. CODE: `datetime.now()` without explicit timezone
2. RUNTIME: Python respects TZ environment variable
3. DEPLOYMENT: Lambda has TZ=Asia/Bangkok? [VERIFIED via Terraform]
4. EXECUTION: PDF shows 20:50 → matches Bangkok time ✅

# Identified execution boundary: Lambda runtime environment
```

**Boundary I identified**: **Code → Lambda environment variables**
- Code uses `datetime.now()` (context-dependent)
- Lambda runtime sets TZ via environment variable
- Terraform configuration defines environment variables
- Must verify Terraform → Lambda contract holds

**Why boundary matters**:
- `datetime.now()` behavior depends on WHERE it executes
- Same code returns different values in different environments
- Cannot validate code correctness without environment context

---

### Instance 3: Progress Report - Workflow Architecture (2026-01-03)

**What I did CORRECTLY**:
```markdown
# Identified execution boundaries:
EventBridge Scheduler (AWS service, cron-triggered)
    ↓ [Boundary 1: EventBridge → Lambda invocation]
Precompute Controller Lambda (Python, runs in Lambda runtime)
    ↓ [Boundary 2: Lambda → Step Functions execution]
Step Functions (AWS service, state machine)
    ↓ [Boundary 3: Step Functions → SQS message send]
SQS Fan-Out (AWS service, message queue)
    ↓ [Boundary 4: SQS → Lambda trigger]
46 Worker Lambdas (Python, runs in Lambda runtime)
    ↓ [Boundary 5: Lambda → Aurora connection]
Aurora MySQL (AWS service, database)
```

**Boundaries I identified**:
1. Service invocation boundaries (EventBridge → Lambda)
2. Data passing boundaries (Lambda → Step Functions payload)
3. Service integration boundaries (Step Functions → SQS)
4. Trigger boundaries (SQS → Lambda event source)
5. Database connection boundaries (Lambda → Aurora)

**Why these boundaries matter**:
- Each boundary has contract: input format, permissions, network access
- Failure at any boundary breaks entire workflow
- Must validate EACH boundary independently

---

### Instance 4: Missing Pattern (User Observation)

**User feedback**:
> "another thing I see you make mistake alot is 'identify boundary' thats involve in a workflow, architecture, services. for example, it seems like you conclude that code is true without taking into account that code has to be run some where or different pieces can be run in different services, and without identifing the 'boundary' you miss things like 'testing initial condition' that's required to execute correctly."

**Pattern user observed**:
- I read Python code and conclude "this should work"
- I don't ask "WHERE does this run?"
- I don't validate "WHAT initial conditions must hold?"
- I miss execution boundaries between services
- I skip verification of environment contracts

**Examples of boundaries I miss**:
1. **Code → Runtime environment** (env vars, filesystem, network)
2. **Code → Database schema** (table exists, columns exist, types match)
3. **Code → AWS service** (permissions, quotas, API versions)
4. **Service A → Service B** (payload format, authentication, network access)
5. **Local → Deployed** (works on laptop ≠ works in Lambda)

---

## Generalized Pattern

### Signature (how to recognize this failure mode)

**Symptoms**:
- ✅ "Code looks correct" (Python syntax valid, logic sound)
- ❌ "But doesn't work in production" (execution fails)
- ❌ "Silent failures" (no error, wrong behavior)
- ❌ "Works locally but not in Lambda" (environment mismatch)
- ❌ "Passes parameters but they're ignored" (schema mismatch)

**Diagnostic questions that reveal boundary issues**:
- WHERE does this code execute? (Lambda, EC2, local, Docker?)
- WHAT environment does it need? (env vars, files, network access?)
- WHAT services does it call? (Aurora, S3, SQS, external APIs?)
- WHAT schema does it expect? (database columns, API response format?)
- WHAT permissions does it need? (IAM roles, security groups?)

---

### Preconditions (what enables this failure)

**Code characteristics**:
- Multi-service architecture (distributed system)
- External dependencies (databases, APIs, message queues)
- Environment-dependent behavior (`os.environ.get()`, file paths)
- Implicit contracts (function accepts parameter → assume storage supports it)

**Analysis approach that enables failure**:
- **Code-first thinking**: Read Python source, ignore infrastructure
- **Single-layer validation**: Verify logic, skip environment
- **Implicit assumptions**: Assume env vars exist, schemas match
- **Missing checklist**: Don't systematically verify each boundary

---

### Components (what's involved)

**Execution layers** (boundaries between these):
1. **Code layer**: Python functions, business logic
2. **Runtime layer**: Lambda container, environment variables, filesystem
3. **Infrastructure layer**: AWS services (Aurora, S3, SQS), network, permissions
4. **Integration layer**: Service-to-service contracts (payloads, schemas, APIs)

**Boundary types**:
- **Process boundaries**: Code → Lambda runtime
- **Network boundaries**: Lambda → Aurora (VPC, security groups)
- **Data boundaries**: Code INSERT → Aurora schema (columns, types)
- **Permission boundaries**: Lambda role → Aurora access (IAM policies)
- **Environment boundaries**: Local development → AWS deployment

---

### Mechanism (how the failure manifests)

**Step-by-step breakdown**:

1. **Analyst reads code**:
   ```python
   # Code accepts pdf_s3_key parameter
   def store_report(..., pdf_s3_key: Optional[str] = None):
       pass
   ```
   **Conclusion**: "Code supports PDF tracking" ✅

2. **Analyst misses boundary**:
   - WHERE does this write data? → Aurora
   - WHAT schema does Aurora have? → [SKIPPED VERIFICATION]
   - Does Aurora table have `pdf_s3_key` column? → [ASSUMED YES]

3. **Deployment executes**:
   ```python
   # Code runs in Lambda
   store_report(symbol='DBS19', pdf_s3_key='s3://...')

   # Inside function:
   query = "INSERT INTO reports (symbol, ...) VALUES (%s, ...)"
   # NOTE: Query doesn't include pdf_s3_key!
   # Parameter silently ignored
   ```

4. **Silent failure**:
   - No error raised (query succeeds)
   - No warning logged (defensive checks missing)
   - Data lost (pdf_s3_key not persisted)
   - Analyst unaware (didn't verify ground truth)

**Root cause**: **Boundary between code signature and database schema not validated**

---

## Pattern Template

### Failure Mode: Missing Execution Boundary Verification

**Symptoms**:
- Error: Code "looks correct" but produces wrong behavior
- Timing: After deployment to actual environment
- Frequency: Common in distributed systems, multi-service workflows

**Root Cause**:
- Analyst validates code logic (Layer 1) but skips infrastructure contract (Layers 2-4)
- Missing systematic boundary identification
- Implicit assumptions about execution environment

**Detection**:
- Ask: "WHERE does this code run?"
- Ask: "WHAT initial conditions must hold for this to work?"
- Check: Does code match infrastructure configuration?
- Verify: Progressive evidence strengthening through all 4 layers

**Prevention**:

**Pre-analysis checklist** (identify boundaries BEFORE validating code):
```markdown
## Execution Boundary Checklist

### 1. Identify WHERE code executes
- [ ] Local development? (laptop, venv)
- [ ] Lambda function? (which function, what runtime)
- [ ] Container? (Docker, ECS, Fargate)
- [ ] EC2 instance? (which instance, what OS)

### 2. Identify WHAT environment code needs
- [ ] Environment variables? (TZ, AURORA_HOST, API_KEY, ...)
- [ ] Filesystem access? (read /tmp, write logs, ...)
- [ ] Network access? (VPC, security groups, internet access)
- [ ] Permissions? (IAM role, resource policies)

### 3. Identify WHAT services code calls
- [ ] Aurora database? (verify schema matches code)
- [ ] S3 buckets? (verify bucket exists, permissions)
- [ ] SQS queues? (verify queue exists, message format)
- [ ] External APIs? (verify endpoint reachable, auth works)

### 4. Identify WHAT contracts must hold
- [ ] Code → Database: INSERT columns match schema
- [ ] Code → API: Request format matches API spec
- [ ] Service A → Service B: Payload format matches expectation
- [ ] Local → Deployed: Environment parity verified
```

**Resolution**:

When you discover execution boundary violation:

1. **Identify the boundary** (which layers are mismatched)
   ```
   Example: Code (Layer 1) → Aurora schema (Layer 3)
   Mismatch: Code expects `pdf_s3_key` column, Aurora doesn't have it
   ```

2. **Verify current state** (what actually exists)
   ```bash
   # Don't assume - verify ground truth
   mysql> SHOW COLUMNS FROM precomputed_reports;
   # Result: No pdf_s3_key column
   ```

3. **Fix the contract** (align layers)
   ```sql
   -- Option 1: Update infrastructure to match code
   ALTER TABLE precomputed_reports ADD COLUMN pdf_s3_key VARCHAR(255);

   -- Option 2: Update code to match infrastructure
   # Remove pdf_s3_key parameter (not supported yet)
   ```

4. **Add defensive checks** (prevent silent failures)
   ```python
   # Validate initial conditions at runtime
   def _validate_schema():
       """Verify Aurora schema matches code expectations."""
       cursor.execute("SHOW COLUMNS FROM precomputed_reports")
       columns = {row['Field'] for row in cursor.fetchall()}

       required = {'id', 'symbol', 'report_date', 'pdf_s3_key'}
       missing = required - columns

       if missing:
           raise RuntimeError(f"Aurora schema missing columns: {missing}")

   # Call at Lambda startup (fail-fast)
   def lambda_handler(event, context):
       _validate_schema()  # Fails LOUD if schema wrong
       ...
   ```

---

## Variations

**Variation 1: Local works, Lambda fails**
- Boundary: Local environment → Lambda runtime
- Cause: Missing env var (works locally via .env, fails in Lambda)
- Example: `TZ` not set in Terraform, Lambda defaults to UTC

**Variation 2: Code passes, schema rejects**
- Boundary: Application code → Database schema
- Cause: Type mismatch (Python dict → MySQL JSON string required)
- Example: PyMySQL rejects dict, requires `json.dumps()`

**Variation 3: Lambda invokes, service rejects**
- Boundary: Lambda → AWS service (Aurora, S3, SQS)
- Cause: Missing permission (IAM role doesn't have policy)
- Example: Lambda can't write to S3 bucket (403 Forbidden)

**Variation 4: Service A sends, Service B can't parse**
- Boundary: Service A → Service B (payload format)
- Cause: Format mismatch (Service A sends JSON, Service B expects XML)
- Example: Step Functions sends dict, SQS expects string body

---

## When to Deviate

**Don't use this checklist for**:
- ✗ Pure computation (no external dependencies)
- ✗ Single-process systems (no service boundaries)
- ✗ Well-tested stable code (boundaries already validated)

**Do use this checklist for**:
- ✓ Distributed systems (multiple services)
- ✓ New integrations (adding service dependencies)
- ✓ Environment changes (local → staging → production)
- ✓ Schema changes (database migrations)
- ✓ "Code looks right but doesn't work" bugs

---

## Graduation Path

**Confidence**: High (user observed this pattern repeatedly)

**Action items**:
- [x] Document pattern in abstraction
- [ ] Add to CLAUDE.md as Principle #19 (Execution Boundary Verification)
- [ ] Create checklist template in `.claude/checklists/execution-boundaries.md`
- [ ] Update research skill to include boundary analysis step
- [ ] Update code-review skill to check boundary contracts

---

## Proposed CLAUDE.md Principle

### Principle #19: Execution Boundary Verification

**Context**: Distributed systems have multiple execution layers (code, runtime, infrastructure, services). Code correctness depends on WHERE it runs and WHAT contracts hold at each boundary.

**Principle**: Before concluding "code is correct", systematically identify and validate ALL execution boundaries: (1) WHERE does code run, (2) WHAT environment does it need, (3) WHAT services does it call, (4) WHAT contracts must hold.

**Boundary types**:
- **Process boundary**: Code → Runtime environment (env vars, filesystem, permissions)
- **Network boundary**: Service A → Service B (connectivity, authentication, quotas)
- **Data boundary**: Code → Storage (schema match, type compatibility)
- **Deployment boundary**: Local → AWS (environment parity, IAM roles)

**Validation pattern**:
```python
# 1. Identify boundaries
# This code runs in: Lambda
# This code calls: Aurora MySQL
# This code assumes: TZ env var, Aurora schema has pdf_s3_key column

# 2. Validate each boundary
assert os.environ.get('TZ') == 'Asia/Bangkok'  # Runtime boundary
assert aurora_has_column('precomputed_reports', 'pdf_s3_key')  # Data boundary

# 3. Fail fast if contract violated
# Don't proceed if initial conditions don't hold
```

**Anti-patterns**:
- ❌ Reading code and concluding "this works" without checking WHERE it runs
- ❌ Assuming environment variables exist (check Terraform/Doppler)
- ❌ Assuming database schema matches code (verify with SHOW COLUMNS)
- ❌ Assuming service is accessible (verify network, permissions)
- ❌ Silent fallbacks that hide boundary violations (fail loud instead)

**Related principles**:
- **Principle #1** (Defensive Programming): Validate initial conditions, fail fast
- **Principle #2** (Progressive Evidence Strengthening): Verify through all layers
- **Principle #4** (Type System Integration): Research boundaries before integrating
- **Principle #15** (Infrastructure-Application Contract): Code and infrastructure must match

**See**: `.claude/abstractions/failure_mode-2026-01-03-missing-execution-boundary-analysis.md`

---

## Real-World Impact

**Without boundary analysis**:
```
Iteration 1: "Code looks correct, deploy" → Silent failure (8 min wasted)
Iteration 2: "Add logging, deploy" → Same failure (8 min wasted)
Iteration 3: "Check schema... oh no column!" → Root cause found (16 min wasted)

Total: 32 minutes + 3 deployments
```

**With boundary analysis**:
```
Pre-deployment:
1. WHERE: Lambda (verified Terraform)
2. WHAT env: TZ=Asia/Bangkok (verified Terraform)
3. WHAT services: Aurora (verified schema)
4. WHAT contract: INSERT needs pdf_s3_key column → NOT FOUND

Root cause found: 5 minutes, 0 deployments

Fix: Add migration first, then deploy code
Total: 15 minutes + 1 deployment (correct)
```

**Savings**: 17 minutes, 2 deployments avoided, higher confidence

---

## Action Items

### Immediate (Create Resources)
- [ ] Create `.claude/checklists/execution-boundaries.md` checklist template
- [ ] Update `.claude/skills/research/INVESTIGATION-CHECKLIST.md` to include boundary analysis
- [ ] Update `.claude/skills/code-review/` to verify boundary contracts

### Week 1 (Integrate into Workflow)
- [ ] Add Principle #19 to CLAUDE.md
- [ ] Update validation workflow to require boundary checklist
- [ ] Test checklist on next multi-service validation task

### Week 2 (Habituate)
- [ ] Practice boundary identification on 3-5 analyses
- [ ] Refine checklist based on real usage
- [ ] Document "saved time" metrics to reinforce pattern

---

## Metadata

**Pattern Type**: failure_mode
**Confidence**: High (user-reported recurring pattern, confirmed across multiple instances)
**Created**: 2026-01-03
**Instances**: 4+ (PDF schema bug, timezone validation, workflow architecture, user general observation)
**Last Updated**: 2026-01-03
**Status**: Ready for graduation to CLAUDE.md principle

---

## References

### User Feedback
> "another thing I see you make mistake alot is 'identify boundary' thats involve in a workflow, architecture, services. for example, it seems like you conclude that code is true without taking into account that code has to be run some where or different pieces can be run in different services, and without identifing the 'boundary' you miss things like 'testing initial condition' that's required to execute correctly."

### Evidence Files
- `.claude/validations/2026-01-03-scheduler-populates-aurora-and-pdf.md` - Schema boundary missed
- `.claude/reports/2026-01-03-pdf-scheduler-integration-progress.md` - Workflow boundaries identified
- `.claude/validations/2026-01-03-why-pdf-schema-bug-not-prevented.md` - Process boundary analysis

### Related CLAUDE.md Principles
- **Principle #1**: Defensive Programming - Validate initial conditions
- **Principle #2**: Progressive Evidence Strengthening - Verify all layers
- **Principle #4**: Type System Integration - Research before integrating
- **Principle #15**: Infrastructure-Application Contract - Sync code and infra

### Related Skills
- `.claude/skills/research/` - Investigation methodology
- `.claude/skills/code-review/` - Code correctness verification
- `.claude/skills/error-investigation/` - AWS-specific debugging
