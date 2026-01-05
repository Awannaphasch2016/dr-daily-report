# Analysis: Should Principles Address Entity Configuration and Intention?

**Date**: 2026-01-03
**Question**: After identifying entities, should principles guide us to understand entity configuration, properties, and intended usage?
**Type**: Conceptual/Philosophical analysis

---

## Question Reframed

**User's insight**:
> "Sure, now we identify entities involved, but entities may have different configuration and properties or even 'intention' (of its usage). Do you think our principles should provide this guidance as well?"

**Progression of understanding**:
1. **Level 1**: Identify boundaries (code → database)
2. **Level 2**: Identify entities (Lambda X → Aurora Y)
3. **Level 3**: Understand entity configuration/properties/intention
   - Lambda X has timeout=180s, memory=1024MB
   - Lambda X is INTENDED for async processing (not synchronous API)
   - Aurora Y has read replicas (INTENDED for read scaling)

**Core question**: Is Level 3 a natural extension of boundary verification, or does it require separate principle guidance?

---

## The Gap: Entity Identity vs Entity Nature

### Current State (Entity Identification)

**What we identify**:
- Entity name: `dr-daily-report-report-worker-dev`
- Entity type: Lambda function
- Entity ARN: `arn:aws:lambda:ap-southeast-1:123456789012:function:...`

**What we DON'T know**:
- **Configuration**: Timeout? Memory? Concurrent executions?
- **Properties**: Stateful or stateless? Synchronous or async?
- **Intention**: What is this Lambda MEANT to do? What is it NOT meant to do?

### Example: Two Lambdas, Different Intentions

**Entity 1**: `dr-daily-report-api-handler-dev`
- **Configuration**: Timeout=30s, Memory=512MB, Concurrency=100
- **Properties**: Synchronous, stateless, API Gateway-triggered
- **Intention**: Handle synchronous API requests, return response immediately

**Entity 2**: `dr-daily-report-report-worker-dev`
- **Configuration**: Timeout=180s, Memory=1024MB, Concurrency=46
- **Properties**: Asynchronous, stateful, SQS-triggered
- **Intention**: Process long-running report generation, can take minutes

**Why intention matters**:
If I use Worker Lambda for API requests, it will "work" but violate design intent:
- ❌ Wastes memory (1024MB for simple API call)
- ❌ Blocks worker capacity (46 concurrent limit)
- ❌ Wrong trigger (SQS instead of API Gateway)

**This is a NEW kind of boundary violation**: Not "can't connect", but "CAN connect but SHOULDN'T"

---

## Philosophical Analysis: Types of "Correctness"

### Type 1: Syntactic Correctness
**Question**: Does code compile/run?
```python
cursor.execute("INSERT INTO reports VALUES (%s)", (data,))
```
**Answer**: ✅ Syntactically correct (Python syntax valid)

---

### Type 2: Semantic Correctness
**Question**: Does code do what it says?
```python
def calculate_average(numbers):
    return sum(numbers) / len(numbers)  # Correct implementation
```
**Answer**: ✅ Semantically correct (calculates average correctly)

---

### Type 3: Boundary Correctness (Principle #20)
**Question**: Can code reach what it needs?
```python
# Can Lambda connect to Aurora?
# Check: VPC, security group, IAM permissions
```
**Answer**: ✅ Boundary correct (Lambda CAN connect to Aurora)

---

### Type 4: Configuration Correctness (NEW)
**Question**: Does entity configuration match intended usage?

**Example 1**: Lambda timeout
```python
# Code makes external API call with 60s timeout
response = requests.get(url, timeout=60)

# Lambda configured with 30s timeout
# Configuration MISMATCH: Code needs 60s, Lambda times out at 30s
```

**Example 2**: Memory allocation
```python
# Code loads 500MB dataset into memory
data = load_large_dataset()  # Requires 500MB

# Lambda configured with 256MB memory
# Configuration MISMATCH: Code needs 500MB, Lambda has 256MB → OOM error
```

**Example 3**: Concurrency limit
```python
# Code expects to process 100 requests/second
# Lambda configured with concurrency=10
# Configuration MISMATCH: Code expects 100 RPS, Lambda throttles at 10
```

**Answer**: ⚠️ **Configuration correctness is a NEW dimension**

---

### Type 5: Intentional Correctness (NEW)
**Question**: Does usage match entity's designed purpose?

**Example 1**: Using async Lambda for sync API
```python
# Lambda DESIGNED FOR: Async SQS processing (3-minute reports)
# Lambda USED FOR: Synchronous API Gateway requests
# Intention VIOLATION: Lambda will work but wastes resources
```

**Example 2**: Using read replica for writes
```python
# Aurora read replica DESIGNED FOR: Read-only queries (scaling reads)
# Code tries: INSERT INTO table (write operation)
# Intention VIOLATION: Read replica rejects writes
```

**Example 3**: Using DynamoDB for analytics
```python
# DynamoDB DESIGNED FOR: Key-value lookups (fast point queries)
# Code tries: Full table scans for analytics
# Intention VIOLATION: Works but extremely slow and expensive
```

**Answer**: ⚠️ **Intentional correctness is ANOTHER new dimension**

---

## Conceptual Framework: Five Layers of Correctness

```
Layer 1: Syntactic Correctness
  ├─ Code compiles/runs
  └─ Covered by: Language compiler/interpreter

Layer 2: Semantic Correctness
  ├─ Code does what it claims to do
  └─ Covered by: Unit tests, logic verification

Layer 3: Boundary Correctness (Principle #20)
  ├─ Code can reach what it needs
  ├─ Entities identified
  ├─ Contracts verified
  └─ Covered by: Execution Boundary Discipline

Layer 4: Configuration Correctness (NEW?)
  ├─ Entity configuration matches code requirements
  ├─ Timeout sufficient for operations
  ├─ Memory sufficient for data
  ├─ Concurrency sufficient for load
  └─ NOT YET COVERED

Layer 5: Intentional Correctness (NEW?)
  ├─ Usage matches entity's designed purpose
  ├─ Right tool for the job
  ├─ Respects architectural intent
  └─ NOT YET COVERED
```

**Question**: Should Layers 4 and 5 be covered by principles, or are they already implicit in existing principles?

---

## Evidence: Where Configuration/Intention Gaps Caused Bugs

### Instance 1: Lambda Timeout Insufficient (Configuration Gap)

**Scenario**: External API call times out

**What happened**:
- Code: `requests.get(url, timeout=60)` (expects 60s)
- Lambda: Configured with 30s timeout
- Result: Lambda times out before request completes

**What was verified** (Principle #20):
- ✅ Lambda can reach external API (network boundary)
- ✅ Lambda has internet access (NAT gateway)

**What was NOT verified** (Configuration gap):
- ❌ Lambda timeout (30s) < Code timeout (60s)
- **Configuration mismatch**: Lambda kills request at 30s, before code's 60s timeout

**Would existing principles catch this?**
- Principle #1 (Defensive Programming): Could validate timeout at startup, but doesn't GUIDE you to check configuration
- Principle #20 (Execution Boundary Discipline): Identifies Lambda entity but doesn't say "check timeout config"

**Gap**: No principle says "verify entity configuration matches code requirements"

---

### Instance 2: Using Worker Lambda for API (Intention Gap)

**Scenario**: Developer uses SQS-triggered Lambda for synchronous API

**What happened**:
- Entity: `dr-daily-report-report-worker-dev` (designed for async processing)
- Usage: Invoked directly from API Gateway (synchronous)
- Result: Works but violates design intent, wastes resources

**What was verified** (Principle #20):
- ✅ API Gateway can invoke Lambda (permission boundary)
- ✅ Lambda can return response (network boundary)

**What was NOT verified** (Intention gap):
- ❌ Lambda INTENDED for SQS processing, NOT API Gateway
- ❌ Lambda configuration optimized for long-running tasks, NOT API latency
- **Intention violation**: Lambda CAN handle API requests but SHOULDN'T

**Would existing principles catch this?**
- Principle #20: Verifies CAN connect, doesn't verify SHOULD connect
- No principle says "verify entity usage matches intended purpose"

**Gap**: No principle says "respect architectural intent"

---

### Instance 3: Aurora Read Replica Used for Writes (Intention Gap)

**Scenario**: Code tries to write to read replica

**What happened**:
- Entity: Aurora read replica (designed for read scaling)
- Usage: Code executes INSERT/UPDATE
- Result: Database rejects writes (read-only)

**What was verified** (Principle #20):
- ✅ Lambda can connect to Aurora (VPC boundary)
- ✅ Lambda has database credentials (permission boundary)

**What was NOT verified** (Intention gap):
- ❌ Aurora endpoint is read replica (read-only by design)
- ❌ Code should use WRITER endpoint for writes
- **Intention violation**: Read replica CAN'T accept writes

**Would existing principles catch this?**
- Principle #20: Verifies connection, doesn't verify endpoint TYPE
- Principle #4 (Type System Integration): Covers data types, not infrastructure types

**Gap**: No principle says "verify entity type matches operation type"

---

## Metacognitive Analysis: When to Add Principles

### Criteria for Adding Principle

**A principle belongs in CLAUDE.md if**:
1. ✅ Guides behavior (changes how you think/act)
2. ✅ Explains rationale (WHY it matters)
3. ✅ Prevents bugs (violating it causes failures)
4. ✅ Frequently violated (pattern recurs)
5. ✅ Not covered by existing principles

**Apply to Configuration/Intention**:

| Criterion | Configuration Correctness | Intentional Correctness |
|-----------|---------------------------|-------------------------|
| **Guides behavior** | ✅ "Check entity config before using" | ✅ "Verify usage matches intent" |
| **Explains rationale** | ✅ "Mismatched config causes runtime failures" | ✅ "Violating intent wastes resources" |
| **Prevents bugs** | ✅ Lambda timeout, memory, concurrency bugs | ⚠️ Works but suboptimal |
| **Frequently violated** | ⚠️ Moderate frequency | ⚠️ Less frequent |
| **Not covered** | ⚠️ Partly covered by #1, #20 | ⚠️ Partly covered by architecture docs |

**Analysis**:
- **Configuration**: Stronger case (prevents runtime failures)
- **Intention**: Weaker case (prevents waste, not failures)

---

### Alternative: Extend Existing Principles

**Option A**: Add separate principles (#21 Configuration, #22 Intention)

**Option B**: Extend Principle #20 with configuration/intention verification

**Option C**: Address in checklist, not principles

**Comparison**:

| Aspect | Option A: New Principles | Option B: Extend #20 | Option C: Checklist Only |
|--------|-------------------------|---------------------|--------------------------|
| **Goldilocks Zone** | ⚠️ 3 separate principles (boundary, config, intent) | ✅ One unified principle | ✅ Principle stays focused |
| **Clarity** | ✅ Each concern explicit | ⚠️ #20 becomes long | ✅ Clear separation |
| **Actionability** | ⚠️ Must remember 3 principles | ✅ One checklist for all | ✅ Detailed checklist |
| **Stability** | ⚠️ Configuration properties evolve | ⚠️ Config details change | ✅ Checklist can evolve |

**Recommendation**: **Option C** - Address in checklist, add minimal guidance to Principle #20

---

## Proposed Solution: Enhance Principle #20 + Extend Checklist

### Principle #20 Enhancement (Add 2-3 Lines)

**Current** (verification questions):
```markdown
**Verification questions**:
- WHERE does this code run? → WHICH Lambda function?
- WHAT environment does it require? → WHICH env vars in WHICH config?
- WHAT external systems does it call? → WHICH Aurora cluster, S3 bucket?
- HOW do I verify the contract? → WHICH AWS resources to inspect?
```

**Proposed addition**:
```markdown
**Verification questions**:
- WHERE does this code run? → WHICH Lambda function?
- WHAT environment does it require? → WHICH env vars in WHICH config?
- WHAT external systems does it call? → WHICH Aurora cluster, S3 bucket?
- **WHAT are entity properties?** → **Configuration (timeout, memory), intended usage (sync vs async)**
- HOW do I verify the contract? → WHICH AWS resources to inspect?
```

**Impact**: Minimal addition (one bullet point), prompts configuration/intention awareness

---

### Checklist Extension: Entity Configuration & Intention

**New section in `.claude/checklists/execution-boundaries.md`**:

```markdown
## Entity Configuration Verification

After identifying entities, verify their configuration matches code requirements.

### Lambda Configuration Verification

**Timeout**:
```bash
# Get Lambda timeout
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'Timeout' --output text
# Returns: 180 (seconds)

# Compare with code requirements
# Code has: requests.get(url, timeout=60)
# Lambda has: 180s timeout
# ✅ Lambda timeout (180s) > Code timeout (60s) → OK
# ❌ Lambda timeout (30s) < Code timeout (60s) → INSUFFICIENT
```

**Memory**:
```bash
# Get Lambda memory
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'MemorySize' --output text
# Returns: 1024 (MB)

# Compare with code requirements
# Code loads 500MB dataset
# Lambda has: 1024MB
# ✅ Lambda memory (1024MB) > Data size (500MB) → OK
# ❌ Lambda memory (256MB) < Data size (500MB) → INSUFFICIENT
```

**Concurrency**:
```bash
# Get reserved concurrency
aws lambda get-function-concurrency \
  --function-name dr-daily-report-report-worker-dev
# Returns: ReservedConcurrentExecutions: 46

# Compare with expected load
# Expected: 46 tickers processed in parallel
# Lambda has: 46 concurrent executions
# ✅ Concurrency matches expected load
```

**Checklist**:
- [ ] Lambda timeout ≥ longest operation timeout
- [ ] Lambda memory ≥ largest dataset size
- [ ] Lambda concurrency ≥ expected parallel executions
- [ ] Lambda VPC has NAT gateway (if needs internet)
- [ ] Lambda layers include required dependencies

---

### Aurora Configuration Verification

**Read vs Write Endpoint**:
```bash
# Get cluster endpoints
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{Writer:Endpoint,Reader:ReaderEndpoint}'

# Returns:
# Writer: dr-daily-report-aurora-dev.cluster-xxx.rds.amazonaws.com
# Reader: dr-daily-report-aurora-dev.cluster-ro-xxx.rds.amazonaws.com

# Verify code uses correct endpoint for operation type
# Writes (INSERT, UPDATE, DELETE) → Use Writer endpoint ✅
# Reads (SELECT) → Can use Reader endpoint ✅
# DON'T: Use Reader endpoint for writes ❌
```

**Connection Limits**:
```bash
# Get max connections
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{MaxConnections:EngineVersion}'

# Compare with expected connection count
# Expected: 46 Lambdas × 1 connection each = 46 connections
# Aurora max_connections: 1000 (default for db.r5.large)
# ✅ Max connections (1000) > Expected (46) → OK
```

**Checklist**:
- [ ] Using Writer endpoint for writes, Reader for reads
- [ ] Max connections ≥ expected concurrent connections
- [ ] Connection timeout configured appropriately
- [ ] Database parameter group settings match requirements

---

## Entity Intention Verification

### Intention: What Is Entity Designed For?

**Lambda Intention Examples**:

| Lambda Function | Intended For | NOT Intended For |
|----------------|--------------|------------------|
| `api-handler` | Synchronous API requests (<3s) | Long-running tasks |
| `report-worker` | Async SQS processing (30-180s) | Synchronous API responses |
| `precompute-controller` | Triggering Step Functions | Data processing |

**Aurora Intention Examples**:

| Aurora Endpoint | Intended For | NOT Intended For |
|----------------|--------------|------------------|
| Writer endpoint | Writes (INSERT, UPDATE) | Read scaling |
| Reader endpoint | Read scaling (SELECT) | Writes |
| Cluster endpoint | Automatic failover | Write performance |

**S3 Intention Examples**:

| S3 Feature | Intended For | NOT Intended For |
|------------|--------------|------------------|
| Standard storage | Frequently accessed data | Archival (use Glacier) |
| Glacier | Archival, rare access | Frequent access |
| Intelligent tiering | Unknown access patterns | Known patterns |

### How to Discover Entity Intention

**Method 1: Documentation/Comments**
```python
# Lambda function docstring
"""
Lambda handler for async report generation.

INTENDED USE:
  - Triggered by SQS messages
  - Processes 1 ticker per invocation
  - Takes 30-180 seconds per report
  - Graceful degradation if external APIs fail

NOT INTENDED FOR:
  - Synchronous API responses
  - Real-time user requests
  - Bulk processing (use Step Functions instead)
"""
```

**Method 2: Terraform/CloudFormation Comments**
```hcl
# terraform/lambda_worker.tf
resource "aws_lambda_function" "worker" {
  # INTENTION: Async report generation from SQS
  # NOT for: API Gateway synchronous responses
  function_name = "dr-daily-report-report-worker-dev"
  timeout       = 180  # Long timeout for report generation
  memory_size   = 1024 # Large memory for data processing
}
```

**Method 3: Architecture Diagrams**
```
# docs/architecture/workflow.md
Worker Lambda:
  - Triggered by: SQS (NOT API Gateway)
  - Purpose: Generate reports asynchronously
  - SLA: No user waiting, can take 3 minutes
```

**Method 4: Git History**
```bash
# Check why entity was created
git log --all --oneline -- terraform/lambda_worker.tf
git show <commit_hash>

# Read PR description
gh pr list --search "worker lambda" --state merged
gh pr view <pr_number>
```

### Intention Verification Checklist

- [ ] **Trigger type matches intention**: SQS for async, API Gateway for sync
- [ ] **Timeout matches intention**: Long timeout for async, short for sync
- [ ] **Concurrency matches intention**: High for user-facing, controlled for batch
- [ ] **Resource type matches intention**: Lambda for compute, Step Functions for orchestration
- [ ] **Storage type matches intention**: DynamoDB for KV, Aurora for relational

---

## Configuration vs Intention: When Do They Overlap?

**Configuration**: Technical properties (timeout, memory, concurrency)
**Intention**: Designed purpose (what it's FOR)

**Overlap example**:
- Lambda timeout=180s (configuration)
- Lambda intended for async processing (intention)
- **Relationship**: Long timeout SUPPORTS async intention

**Mismatch example**:
- Lambda timeout=3s (configuration)
- Lambda intended for async processing (intention)
- **Conflict**: Short timeout CONTRADICTS async intention

**Key insight**: Configuration should ALIGN with intention. Misalignment indicates:
1. Configuration error (wrong timeout set)
2. Usage error (using entity for unintended purpose)

---

## Recommendation

### Primary: Extend Principle #20 (Minimal Addition)

**Add one bullet point to verification questions**:
```markdown
- WHAT are entity properties? → Configuration (timeout, memory), intended usage (sync vs async)
```

**Rationale**:
- Prompts awareness without adding new principle
- Maintains Goldilocks Zone (one sentence)
- Naturally extends entity identification

---

### Secondary: Comprehensive Checklist Sections

**Add to `.claude/checklists/execution-boundaries.md`**:

1. **Entity Configuration Verification** (detailed)
   - Lambda: timeout, memory, concurrency, VPC
   - Aurora: endpoints, connection limits, parameter groups
   - S3: storage class, lifecycle, encryption

2. **Entity Intention Verification** (conceptual)
   - How to discover intention (docs, comments, git history)
   - Verify usage matches intention
   - Flag intention violations (works but wrong)

**Rationale**:
- Checklist is right place for HOW-TO details
- Configuration properties evolve (new AWS features)
- Intention discovery methods are stable

---

### Tertiary: Update Abstractions/ADRs

**When creating new entities**:
- Add intention documentation in Terraform comments
- Document configuration rationale (why timeout=180s?)
- Create ADR for major architectural decisions

**Example Terraform comment**:
```hcl
resource "aws_lambda_function" "worker" {
  # INTENTION: Async report generation (30-180s per ticker)
  # TRIGGER: SQS queue (not API Gateway)
  # CONCURRENCY: Limited to 46 (one per ticker)
  # TIMEOUT: 180s (handles slow external APIs)
  # MEMORY: 1024MB (loads price history + news data)

  function_name = "dr-daily-report-report-worker-dev"
  timeout       = 180
  memory_size   = 1024
  reserved_concurrent_executions = 46
}
```

---

## Answer to User's Question

**Question**: "Should our principles provide guidance on entity configuration and intention?"

**Answer**: **Yes, but minimally in principles, extensively in checklist**

**Rationale**:

1. **Configuration verification is critical** (prevents runtime failures)
   - Lambda timeout insufficient → timeout errors
   - Lambda memory insufficient → OOM errors
   - Configuration must match code requirements

2. **Intention verification prevents waste** (not always failures)
   - Using async Lambda for sync API → works but inefficient
   - Using read replica for writes → fails (good)
   - Using DynamoDB for analytics → works but expensive

3. **Abstraction level separation**:
   - **Principle #20**: Add one sentence prompting awareness
   - **Checklist**: Comprehensive verification procedures
   - **Terraform/ADRs**: Document intention at creation

4. **Precedent in existing principles**:
   - Principle #20 already asks "WHAT environment does it require?"
   - Extending to "WHAT are entity properties?" is natural progression

**Proposed changes**:
- ✅ Add 1 sentence to Principle #20 (minimal, Goldilocks Zone)
- ✅ Add 2 sections to checklist (comprehensive HOW-TO)
- ✅ Update Terraform templates to document intention
- ❌ Don't create separate principles (#21, #22) - too granular

---

## Next Steps

- [ ] Update Principle #20 with entity properties bullet point
- [ ] Add "Entity Configuration Verification" section to checklist
- [ ] Add "Entity Intention Verification" section to checklist
- [ ] Update Terraform templates with intention comments
- [ ] Test verification workflow on next validation task

---

**Analysis complete**: Configuration and intention verification should be guided minimally in principles, extensively in checklist.
