---
name: proof
description: Construct formal deductive proofs about system properties given constraints and axioms
accepts_args: true
arg_schema:
  - name: theorem
    required: true
    description: "Statement to prove or disprove (quoted if spaces)"
  - name: save
    required: false
    description: "Optional: 'save' to create persistent proof document in .claude/proofs/"
composition:
  - skill: research
---

# Proof Command

**Purpose**: Construct formal deductive proofs about system properties from constraints and axioms

**Core Principle**: "What MUST be true given constraints?" - deductive reasoning from first principles

**When to use**:
- Verify capacity constraints before scaling
- Prove type safety properties
- Validate resource cleanup guarantees
- Check architectural invariants
- Reason about performance bounds

---

## Quick Reference

```bash
# Capacity planning
/proof "Lambda with 512MB can process 100MB images"

# Type safety
/proof "All API endpoints return JSON-serializable data"

# Resource management
/proof "All database connections are properly closed"

# Architectural properties
/proof "Data never flows from Lambda without Aurora cache"

# Save proof document
/proof "System can handle 1000 req/s" save
```

---

## Proof vs Validate

| Aspect | `/validate` (Empirical) | `/proof` (Deductive) |
|--------|------------------------|---------------------|
| **Question** | "What IS true?" | "What MUST be true?" |
| **Method** | Observe reality | Derive from axioms |
| **Reasoning** | Inductive | Deductive |
| **Evidence** | Code, metrics, logs | Constraints, properties |
| **Example** | "Does code sanitize inputs?" | "Can system handle 1000 req/s?" |

**Use both**:
```bash
/proof "Lambda can handle 100 req/s"    # Theoretical: should work
/validate "Lambda handles 100 req/s"    # Empirical: does work
```

---

## Proof Types (Auto-Detected)

### 1. Direct Proof
**Pattern**: Given axioms → derive conclusion step by step

**Keywords**: "can", "will", "if...then"

**Example**:
```bash
/proof "Lambda with 512MB can process 100MB images"
```

### 2. Proof by Contradiction
**Pattern**: Assume opposite → derive contradiction

**Keywords**: "all", "every", "never"

**Example**:
```bash
/proof "All database queries use transactions"
```

### 3. Proof by Counterexample
**Pattern**: Find single case that violates property

**Keywords**: "all", "every", "always"

**Example**:
```bash
/proof "All Lambda functions have timeout < 30s"
```

### 4. Proof by Construction
**Pattern**: Build explicit example satisfying property

**Keywords**: "exists", "there is", "can we build"

**Example**:
```bash
/proof "There exists a workflow completing in < 1s"
```

### 5. Proof by Induction
**Pattern**: Base case + inductive step

**Keywords**: "adding X always improves Y", "scaling"

**Example**:
```bash
/proof "Adding caching at level N always improves response time at level N+1"
```

---

## Execution Flow

### Step 1: Parse Theorem and Detect Proof Type

**Auto-detection patterns**:
```
"can X do Y"              → Direct proof
"all X have Y"            → Counterexample search
"there exists X"          → Construction
"if X then Y"             → Direct proof or contrapositive
"X always leads to Y"     → Induction
"never", "impossible"     → Proof by contradiction
```

**Parse arguments**:
```bash
THEOREM="$1"
SAVE_FLAG="${2:-}"  # Optional "save" argument

# Detect proof type from theorem keywords
if [[ "$THEOREM" =~ (can|will|sufficient) ]]; then
  TYPE="direct"
elif [[ "$THEOREM" =~ (all|every|always) ]]; then
  TYPE="counterexample"
elif [[ "$THEOREM" =~ (exists|there is) ]]; then
  TYPE="construction"
elif [[ "$THEOREM" =~ (never|impossible) ]]; then
  TYPE="contradiction"
elif [[ "$THEOREM" =~ (adding.*always|scaling) ]]; then
  TYPE="induction"
else
  TYPE="direct"  # Default
fi
```

---

### Step 2: Gather Axioms from Codebase

**Sources** (prioritized):
1. **Terraform configs** - Infrastructure constraints
2. **CLAUDE.md** - Architectural principles
3. **Code constants** - Memory limits, timeouts, thresholds
4. **Database schema** - Data constraints, types
5. **API specs** - Interface contracts
6. **Documentation** - Performance requirements

**Search strategy**:
```bash
# Example: For theorem about Lambda memory
grep -r "memory" terraform/lambda.tf
grep -r "memory_size" terraform/*.tf
grep -r "Lambda memory" .claude/CLAUDE.md
grep -r "MEMORY" src/**/*.py
```

**Extract axioms**:
```
A1: Lambda memory = 512MB (terraform/lambda.tf:45)
A2: Lambda timeout = 30s (terraform/lambda.tf:46)
A3: Processing time = 0.5s/MB (src/processor.py:12)
A4: Memory requirement = 3x image size (src/processor.py:15)
```

---

### Step 3: Construct Formal Proof

**Template structure**:
```markdown
THEOREM: {statement}

TYPE: {direct | contradiction | counterexample | construction | induction}

AXIOMS:
  A1: {axiom 1} (source reference)
  A2: {axiom 2} (source reference)
  A3: {axiom 3} (source reference)

PROOF:
  1. {step 1}                                    [justification]
  2. {step 2}                                    [A1, A2]
  3. {step 3}                                    [1, 2, arithmetic/logic]
  ...
  n. ∴ {conclusion}                              [1, ..., n-1]

CONCLUSION: ✅ PROVEN | ❌ DISPROVEN | ⚠️ INCOMPLETE

{Additional analysis if proven/disproven}

REFERENCES:
  - {file:line} - {description}
  - {CLAUDE.md section} - {principle}
  - {docs URL} - {specification}

QED
```

---

### Step 4: Execute Proof by Type

#### Direct Proof Template

```markdown
THEOREM: Lambda with 512MB can process 100MB images

TYPE: Direct proof

AXIOMS:
  A1: Lambda memory allocation = 512MB
      Source: terraform/lambda.tf:45
      Config: memory_size = 512

  A2: Image processing memory = 3x image size
      Source: src/processor.py:12
      Code: buffer_size = image_size * 3

  A3: 100MB image memory requirement
      Derivation: 100MB * 3 = 300MB

PROOF:
  1. Lambda has 512MB memory available          [A1]
  2. 100MB image requires 300MB memory          [A2, A3]
  3. 512MB > 300MB                              [arithmetic]
  4. 512MB - 300MB = 212MB headroom             [arithmetic]
  5. ∴ Sufficient memory exists                 [1, 2, 3, 4]

CONCLUSION: ✅ PROVEN

Memory analysis:
  - Required: 300MB
  - Available: 512MB
  - Headroom: 212MB (41% margin)
  - Safety: Adequate for memory fragmentation

Implications:
  - Current configuration supports 100MB images
  - Could potentially handle up to ~150MB images
  - No immediate scaling needed

Caveats:
  - Assumes no other memory consumers
  - Assumes PIL memory model (3x multiplier)
  - Does not account for OS overhead (~50MB)

REFERENCES:
  - terraform/lambda.tf:45 - Lambda configuration
  - src/processor.py:12 - Buffer allocation
  - CLAUDE.md "Cold Start Optimization"

QED
```

---

#### Proof by Counterexample Template

```markdown
THEOREM: All Lambda functions have timeout < 30s

TYPE: Proof by counterexample

SEARCH STRATEGY:
  1. List all Lambda functions from Terraform
  2. Check timeout configuration for each
  3. Find any λ where timeout ≥ 30s

LAMBDA FUNCTIONS:
  λ₁ (handler):
    - File: terraform/lambda.tf:23
    - Timeout: 10s ✓

  λ₂ (processor):
    - File: terraform/lambda.tf:67
    - Timeout: 30s ✗ (not < 30s)

  λ₃ (scheduler):
    - File: terraform/lambda.tf:102
    - Timeout: 5s ✓

COUNTEREXAMPLE FOUND:
  Function: processor
  Location: terraform/lambda.tf:67
  Timeout: 30s
  Violates: timeout < 30s (30 is not less than 30)

CONCLUSION: ❌ DISPROVEN

The theorem "All Lambda functions have timeout < 30s" is false.

Counterexample: processor Lambda has exactly 30s timeout.

To make theorem true:
  Option 1: Change theorem to "timeout ≤ 30s"
  Option 2: Reduce processor timeout to 29s
  Option 3: Exclude processor from "all" claim

REFERENCES:
  - terraform/lambda.tf:67 - processor timeout config

QED (by counterexample)
```

---

#### Proof by Construction Template

```markdown
THEOREM: There exists a workflow completing in < 1s

TYPE: Proof by construction

CONSTRUCTION:
  Build workflow W that satisfies execution_time(W) < 1000ms

WORKFLOW DESIGN:
  W = minimal_workflow
  W.nodes = [validate_input, return_cached_result]

NODE ANALYSIS:
  Node 1: validate_input
    - Function: src/workflow/nodes.py:23
    - Operations: Schema check, type validation
    - Time complexity: O(1)
    - Measured time: 50ms (from logs)

  Node 2: return_cached_result
    - Function: src/workflow/nodes.py:67
    - Operations: Cache lookup (no DB query)
    - Time complexity: O(1)
    - Measured time: 100ms (Redis latency)

EXECUTION TIME:
  Total = validate_input + return_cached_result
  Total = 50ms + 100ms
  Total = 150ms

VERIFICATION:
  150ms < 1000ms ✓

CONCLUSION: ✅ PROVEN (by construction)

Constructed workflow: minimal_workflow
Execution time: 150ms (15% of target)

This proves existence - at least one workflow satisfies property.

Example implementation:
  - File: src/workflow/minimal.py
  - Usage: For health checks, cached data retrieval
  - Performance: 85% faster than full workflow

REFERENCES:
  - src/workflow/nodes.py:23 - validate_input
  - src/workflow/nodes.py:67 - return_cached_result
  - CloudWatch logs - execution time measurements

QED
```

---

### Step 5: Handle Incomplete Proofs

**When axioms insufficient**:
```markdown
⚠️ INCOMPLETE PROOF

Cannot prove or disprove theorem due to missing axioms.

THEOREM: System can handle 10,000 concurrent users

AXIOMS FOUND:
  A1: Lambda concurrency = 1000 (terraform/lambda.tf:45)
  A2: Average request duration = 200ms (CloudWatch)

AXIOMS MISSING:
  ❌ Maximum file upload size (not in config)
  ❌ Database connection pool size (not documented)
  ❌ CloudFront cache hit ratio (needed for load calculation)
  ❌ User session duration (affects concurrency)

TO COMPLETE PROOF:
  1. Add MAX_UPLOAD_SIZE to doppler config
  2. Document connection pool in docs/DATABASE.md
  3. Measure cache hit ratio in CloudWatch
  4. Define user session duration in requirements

PARTIAL ANALYSIS:
  With Lambda concurrency = 1000 and duration = 200ms:
  - Theoretical max throughput = 1000 / 0.2s = 5000 req/s
  - If each user makes 1 req/s: max 5000 concurrent users
  - Conclusion: 10,000 users would exceed capacity

However, cannot prove rigorously without missing axioms.

RECOMMENDATION:
  Gather missing axioms, then re-run proof.
```

---

### Step 6: Save Proof Document (if requested)

**If second argument is "save"**:
```bash
if [[ "$SAVE_FLAG" == "save" ]]; then
  DATE=$(date +%Y-%m-%d)
  SLUG=$(echo "$THEOREM" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
  FILEPATH=".claude/proofs/${DATE}-${SLUG}.md"

  # Create .claude/proofs/ directory if doesn't exist
  mkdir -p .claude/proofs

  # Write proof document
  cat > "$FILEPATH" << 'EOF'
---
title: {theorem}
type: {proof_type}
date: {date}
status: {proven | disproven | incomplete}
confidence: {high | medium | low}
tags: []
---

# Theorem: {theorem}

**Status**: {✅ PROVEN | ❌ DISPROVEN | ⚠️ INCOMPLETE}

---

{Full proof content from Step 3}

---

*Proof verified: {date}*
*Method: {proof_type}*
EOF

  echo "✅ Proof document saved: $FILEPATH"
fi
```

---

## Examples

### Example 1: Capacity Planning (Direct Proof)

```bash
/proof "Lambda can handle 1000 concurrent requests"
```

**Output**:
```
THEOREM: Lambda can handle 1000 concurrent requests

TYPE: Direct proof

AXIOMS:
  A1: Lambda concurrency limit = 1000
      Source: AWS account limit (terraform/lambda.tf:8)

  A2: Each request uses 1 Lambda instance
      Source: AWS Lambda execution model

  A3: Request duration = 200ms average
      Source: CloudWatch metrics (last 7 days)

PROOF:
  1. Concurrency limit = 1000                    [A1]
  2. Each request needs 1 instance               [A2]
  3. Max concurrent = limit / instances_per_req  [Definition]
  4. Max concurrent = 1000 / 1 = 1000           [1, 2, 3]
  5. ∴ Can handle exactly 1000 concurrent        [4]

CONCLUSION: ✅ PROVEN

System can handle exactly 1000 concurrent requests.

WARNING: At maximum capacity (no headroom)
  - Any spike beyond 1000 will throttle
  - Recommendation: Increase limit to 1500 for 50% safety margin
  - Request AWS support for limit increase

REFERENCES:
  - terraform/lambda.tf:8 - Concurrency configuration
  - AWS Lambda limits: https://docs.aws.amazon.com/lambda/latest/dg/limits.html

QED
```

---

### Example 2: Type Safety (Counterexample)

```bash
/proof "All API endpoints return JSON-serializable data"
```

**Output**:
```
THEOREM: All API endpoints return JSON-serializable data

TYPE: Proof by counterexample

ENDPOINTS ANALYZED:
  ✓ GET /report/{ticker}
    - Returns: Dict[str, Any]
    - JSON-serializable: Yes

  ✓ GET /rankings
    - Returns: List[Dict[str, Any]]
    - JSON-serializable: Yes

  ✗ GET /health
    - Returns: pd.DataFrame
    - JSON-serializable: No (pandas DataFrame not JSON-serializable)

COUNTEREXAMPLE:
  Endpoint: GET /health
  Location: src/api/health.py:45
  Return type: pd.DataFrame
  Issue: DataFrame must be converted to dict

CONCLUSION: ❌ DISPROVEN

Found counterexample: /health endpoint returns non-JSON-serializable type.

FIX:
  # Before (broken):
  return health_df

  # After (fixed):
  return health_df.to_dict(orient='records')

REFERENCES:
  - src/api/health.py:45 - Endpoint implementation
  - CLAUDE.md "JSON Serialization Requirement"

QED (by counterexample)
```

---

### Example 3: Resource Cleanup (Direct Proof)

```bash
/proof "All database connections are properly closed"
```

**Output**:
```
THEOREM: All database connections are properly closed

TYPE: Direct proof (via code pattern analysis)

AXIOMS:
  A1: All DB access uses context manager
      Source: CLAUDE.md "Code Style & Principles"
      Principle: "Always use with statement for resources"

  A2: Context managers guarantee __exit__ call
      Source: Python language specification
      Ref: PEP 343

  A3: __exit__ closes connection
      Source: pymysql documentation
      Behavior: Connection.__exit__ calls close()

PROOF:
  1. All DB access via context manager           [A1, code review]
  2. Context manager calls __exit__ on exit      [A2, Python spec]
  3. __exit__ calls connection.close()           [A3, pymysql docs]
  4. ∴ All connections closed                    [1, 2, 3]

CODE VERIFICATION:
  Files reviewed:
    - src/data/ticker_data.py ✓ (uses context manager)
    - src/data/news_fetcher.py ✓ (uses context manager)
    - src/data/rankings.py ✓ (uses context manager)

  Pattern found:
    with get_db_connection() as conn:
        # ... operations ...
    # Connection auto-closed here

CONCLUSION: ✅ PROVEN

All database connections are properly closed via context manager pattern.

Verification method: Code review + pattern matching
Confidence: High (enforced by CLAUDE.md principle)

REFERENCES:
  - CLAUDE.md "Code Style & Principles"
  - src/data/*.py (all DB access files)
  - PEP 343: The "with" Statement

QED
```

---

### Example 4: Save Proof Document

```bash
/proof "System can handle 1000 req/s" save
```

**Output**:
```
THEOREM: System can handle 1000 req/s

TYPE: Direct proof

[... proof content ...]

CONCLUSION: ✅ PROVEN

✅ Proof document saved: .claude/proofs/2025-12-24-system-can-handle-1000-req-s.md

Next steps:
  - Review proof in .claude/proofs/
  - Reference in architecture decisions
  - Use as evidence in ADR if needed
```

---

## Integration with Other Commands

### Workflow 1: Proof → Validate → Journal

```bash
# Theoretical analysis
/proof "Lambda 512MB can process 100MB images"
# → ✅ PROVEN (300MB < 512MB)

# Empirical verification
/validate "Lambda successfully processes 100MB images"
# → ✅ TRUE (CloudWatch confirms)

# Document the finding
/journal architecture "Lambda memory sizing rationale"
```

---

### Workflow 2: What-If → Proof → Specify

```bash
# Explore counterfactual
/what-if "Lambda timeout was 15s instead of 30s"
# → Suggests: Image processing might fail

# Prove the concern
/proof "Lambda with 15s timeout cannot process 100MB images"
# → ❌ DISPROVEN (would need 50s)

# Design alternative
/specify "Async image processing with SQS"
```

---

### Workflow 3: Proof → Journal → ADR

```bash
# Prove capacity limit
/proof "Current architecture maxes at 5000 req/s" save
# → ❌ DISPROVEN (need 10k req/s)

# Document decision
/journal architecture "Why we need to scale beyond 5k req/s"

# Formalize in ADR
# Create docs/adr/015-scale-to-10k-req-s.md
# Reference proof as evidence
```

---

## Tips

### Do
- **State theorems precisely** (avoid ambiguity)
- **Check axiom sources** (reference actual configs/code)
- **Use formal language** (∀, ∃, →, ∴)
- **Show all steps** (don't skip derivations)
- **Include counterexamples** (if disproven)
- **Save significant proofs** (use "save" argument)

### Don't
- **Assume without axioms** (must cite sources)
- **Skip intermediate steps** (proof must be complete)
- **Confuse correlation with causation** (deductive only)
- **Ignore edge cases** (counterexamples matter)

---

## Common Proof Patterns

### Pattern 1: Resource Sufficiency
```
Theorem: Resource R can handle load L
Axioms: R capacity, L requirements
Proof: Show R_capacity > L_requirements
```

### Pattern 2: Type Safety
```
Theorem: All values of type T satisfy property P
Method: Counterexample search
Proof: Find value v:T where ¬P(v)
```

### Pattern 3: Performance Bounds
```
Theorem: Operation O completes in time < T
Axioms: O time complexity, input size
Proof: Calculate worst-case time, show < T
```

### Pattern 4: Invariant Preservation
```
Theorem: Property P holds before and after operation O
Method: Direct proof
Proof: Show O preserves P (P ∧ O → P)
```

---

## See Also

- `.claude/commands/validate.md` - Empirical validation (checks reality)
- `.claude/commands/what-if.md` - Counterfactual exploration (reveals constraints)
- `.claude/commands/journal.md` - Document findings
- `docs/adr/README.md` - Use proofs as evidence in ADRs
