# Principle Compliance Audit: EventBridge Envelope Passthrough

**Audit Date**: 2026-01-04
**Scope**: DESIGN_REVIEW
**Context**: Proposal to pass EventBridge envelope from precompute Step Function to PDF generation Step Function

**Proposal**: Instead of using EventBridge input transformer to extract and reshape data, pass the entire EventBridge envelope to PDF workflow.

---

## Audit Summary

**Principles audited**: 7 (service integration & code quality)
**Status**:
- ✅ Compliant: 1
- ⚠️ Partial: 2
- ❌ Violations: 4

**Overall compliance**: **29%** (2/7 compliant)

**Recommendation**: ❌ **DO NOT IMPLEMENT** - Multiple principle violations, high technical debt

---

## Compliance Results

### Principle #1: Defensive Programming

**Compliance question**: Does the proposed design validate prerequisites and fail fast?

**Analysis**:

**Current (with input transformer)**:
```terraform
input_transformer {
  input_template = <<EOF
{
  "report_date": "2026-01-04"
}
EOF
}
```
→ Lambda receives: `{"report_date": "2026-01-04"}`
→ Validation: Simple key check `event.get('report_date')`

**Proposed (pass envelope)**:
```json
{
  "version": "0",
  "id": "17fbc6b2-...",
  "detail-type": "Step Functions Execution Status Change",
  "source": "aws.states",
  "detail": {
    "executionArn": "...",
    "status": "SUCCEEDED",
    "input": "{}",
    "output": "{\"status\":\"completed\",...}"
  }
}
```
→ Lambda must: Parse envelope structure, extract nested data, handle missing fields
→ Validation: Complex parsing with multiple failure points

**Status**: ❌ **VIOLATION**

**Gaps**:
1. **No fail-fast**: Lambda must parse complex nested structure before detecting issues
2. **Silent failures**: Missing `detail` or `detail.input` would fail deep in execution
3. **Error handling complexity**: Must validate envelope structure, not just parameter presence

**Impact**:
- Lambda fails later (after parsing attempt) instead of immediately
- Error messages less clear (parsing error vs missing parameter)
- Harder to debug (which nested field caused failure?)

**Principle #1 quote**:
> "Fail fast and visibly when something is wrong. Silent failures hide bugs. Validate configuration at startup, not on first use."

**Verdict**: Passing envelope **violates fail-fast principle** by adding parsing complexity before validation.

---

### Principle #4: Type System Integration Research

**Compliance question**: Are type conversions explicit when crossing system boundaries?

**Analysis**:

**Current boundary** (with input transformer):
```
EventBridge (JSON string)
  → Input transformer (reshapes to simple structure)
  → Lambda (receives {"report_date": "2026-01-04"})
  → Direct .get() access
```
**Type conversion**: None needed (EventBridge handles it)

**Proposed boundary** (pass envelope):
```
EventBridge (JSON string)
  → Lambda (receives complex nested structure)
  → Must parse: event['detail']['output'] (JSON string)
  → Must deserialize: json.loads(event['detail']['output'])
  → Must extract: parsed_output.get('results')
  → Multiple type conversions
```

**Code required**:
```python
def lambda_handler(event, context):
    # Step 1: Validate envelope structure
    if 'detail' not in event:
        raise ValueError("Missing 'detail' in EventBridge envelope")

    # Step 2: Extract nested output (still a JSON string!)
    output_str = event['detail'].get('output')
    if not output_str:
        raise ValueError("Missing 'output' in EventBridge detail")

    # Step 3: Parse JSON string to dict
    try:
        output_data = json.loads(output_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in EventBridge output: {e}")

    # Step 4: Extract report_date (if it even exists in output)
    report_date = output_data.get('report_date')  # Doesn't exist!

    # Precompute output doesn't include report_date
    # Must use event['detail']['input'] instead
    input_str = event['detail'].get('input')  # Also JSON string!
    input_data = json.loads(input_str) if input_str else {}
    report_date = input_data.get('report_date')  # Still might not exist!

    # Fallback to today
    if not report_date:
        report_date = datetime.now(bangkok_tz).date()
```

**Status**: ❌ **VIOLATION**

**Gaps**:
1. **Multiple implicit conversions**: JSON string → dict → extract → fallback
2. **No explicit type research**: Assumed envelope structure without verification
3. **Fragile parsing**: Depends on undocumented EventBridge schema
4. **No schema validation**: What if AWS changes envelope format?

**Impact**:
- 15+ lines of parsing code vs 1 line with input transformer
- Multiple failure points (missing fields, invalid JSON, wrong types)
- Maintenance burden (must update if EventBridge schema changes)

**Principle #4 quote**:
> "Research type compatibility BEFORE integrating heterogeneous systems. Type mismatches cause silent failures."

**Verdict**: Passing envelope **violates type system research** - didn't verify envelope schema, multiple conversions, no validation.

---

### Principle #19: Cross-Boundary Contract Testing

**Compliance question**: Are service integration boundaries tested?

**Analysis**:

**Current boundary** (with input transformer):
```
Boundary: EventBridge → Step Functions
Contract: EventBridge sends {"report_date": "YYYY-MM-DD"}
Test: Verify Step Functions receives correct format
```

**Test code**:
```python
def test_eventbridge_input_transformer():
    """Service boundary: EventBridge → Step Functions

    Tests that EventBridge input transformer correctly
    reshapes envelope to PDF workflow expected format.
    """
    # Simulate EventBridge envelope
    envelope = {
        "version": "0",
        "time": "2026-01-04T11:15:07Z",
        "detail": {"status": "SUCCEEDED"}
    }

    # Apply transformer (extract $.time, format to report_date)
    transformed = {"report_date": "2026-01-04"}

    # Verify Lambda receives correct format
    assert 'report_date' in transformed
    assert transformed['report_date'] == "2026-01-04"
```

**Proposed boundary** (pass envelope):
```
Boundary: EventBridge → Step Functions → Lambda
Contract: Lambda must parse EventBridge envelope structure
Test: ??? How to test envelope parsing logic?
```

**Test complexity**:
```python
def test_eventbridge_envelope_parsing():
    """Service boundary: EventBridge → Lambda

    Tests that Lambda can correctly parse EventBridge envelope.

    But what's the contract?
    - Which fields are required?
    - Which fields are optional?
    - What if AWS changes envelope format?
    - What if 'output' JSON structure changes?
    """
    # Test case 1: Full envelope
    full_envelope = {...}  # 50+ lines of JSON
    result = lambda_handler(full_envelope, {})
    # How to verify correct parsing?

    # Test case 2: Missing 'detail'
    missing_detail = {"version": "0", "id": "..."}
    with pytest.raises(ValueError):
        lambda_handler(missing_detail, {})

    # Test case 3: Invalid JSON in 'output'
    invalid_json = {
        "detail": {"output": "{invalid json}"}
    }
    with pytest.raises(ValueError):
        lambda_handler(invalid_json, {})

    # Test case 4: Missing 'input' in detail
    # Test case 5: Empty 'input'
    # Test case 6: 'input' is not JSON
    # ... 10+ edge cases
```

**Status**: ❌ **VIOLATION**

**Gaps**:
1. **No contract definition**: Unclear what envelope fields are required
2. **Difficult to test**: Must mock complex nested structure
3. **Fragile tests**: Break if AWS changes envelope format
4. **Many edge cases**: Missing fields, invalid JSON, wrong types

**Impact**:
- 10+ test cases to cover envelope parsing (vs 1 test with transformer)
- Tests depend on undocumented AWS behavior
- Maintenance burden when AWS changes EventBridge schema

**Principle #19 quote**:
> "Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary."

**Verdict**: Passing envelope **violates boundary testing** - creates untestable, fragile service integration.

---

### Principle #20: Execution Boundary Discipline

**Compliance question**: Are execution boundaries verified (WHERE code runs, WHAT it needs)?

**Analysis**:

**Execution boundary**: EventBridge → Step Functions → Lambda

**Questions**:
1. **WHERE does envelope parsing run?** Lambda (adds compute cost)
2. **WHAT does Lambda need?** EventBridge envelope schema knowledge
3. **HOW to verify contract?** Must test against actual EventBridge events

**Current (with input transformer)**:
```
EventBridge → Input Transformer → Simple JSON → Lambda
Lambda needs: {"report_date": "YYYY-MM-DD"} (simple contract)
Verification: Test with simple JSON input
```

**Proposed (pass envelope)**:
```
EventBridge → Raw Envelope → Lambda
Lambda needs: Knowledge of EventBridge envelope structure
Verification: Must test with actual EventBridge events (complex)
```

**Coupling analysis**:

**Current**: Lambda **decoupled** from EventBridge schema
- Lambda only knows about `{"report_date": "..."}`
- EventBridge schema changes don't affect Lambda
- Input transformer handles schema evolution

**Proposed**: Lambda **tightly coupled** to EventBridge schema
- Lambda must know EventBridge envelope structure
- AWS changes to envelope format require Lambda code updates
- No isolation layer between services

**Status**: ❌ **VIOLATION**

**Gaps**:
1. **Tight coupling**: Lambda code depends on AWS EventBridge schema
2. **No verification**: Can't verify envelope structure without AWS documentation
3. **Fragile integration**: AWS changes break Lambda code
4. **Violation of separation of concerns**: Lambda shouldn't know about EventBridge internals

**Impact**:
- Lambda code becomes dependent on AWS implementation details
- Breaking changes if AWS evolves EventBridge envelope format
- Harder to test (need real EventBridge events or complex mocks)

**Principle #20 quote**:
> "Reading code ≠ Verifying code works. Before concluding 'code is correct', systematically identify execution boundaries and verify contracts at each boundary match reality."

**Verdict**: Passing envelope **violates execution boundary discipline** - creates tight coupling to AWS schema, unverifiable contract.

---

### Principle #2: Progressive Evidence Strengthening

**Compliance question**: Are operations verified through ground truth, not just status codes?

**Analysis**:

**Current (with input transformer)**:
- Layer 1 (Surface): Step Functions execution status
- Layer 2 (Content): `{"report_date": "2026-01-04"}` simple structure
- Layer 3 (Observability): CloudWatch logs show "Using explicit report_date"
- Layer 4 (Ground truth): Aurora query uses correct date

**Proposed (pass envelope)**:
- Layer 1 (Surface): Step Functions execution status
- Layer 2 (Content): Complex envelope with nested JSON strings
- Layer 3 (Observability): CloudWatch logs show envelope parsing (harder to read)
- Layer 4 (Ground truth): Aurora query uses correct date (if parsing succeeds)

**Debugging scenario**:

**With input transformer**:
```
Bug: PDF workflow found 0 reports
Debug: Check what report_date was passed
Log: "Using explicit report_date from event: 2026-01-04"
Root cause: Reports already have PDFs for 2026-01-04
Fix: Clear PDFs or use different date
```

**With envelope passthrough**:
```
Bug: PDF workflow found 0 reports
Debug: Check what envelope was passed
Log: "Received EventBridge envelope: {...500 chars...}"
Parse log to find: event['detail']['input'] or event['detail']['output']
Extract JSON string: "{\"status\":\"completed\",...}"
Parse JSON: Find report_date field (doesn't exist!)
Realize: Must parse event['detail']['input'] instead
Parse again: "{}" (empty input!)
Fallback: Using today's date
Root cause: Multiple layers of parsing, unclear which date was used
Fix: Trace through parsing logic to understand data flow
```

**Status**: ⚠️ **PARTIAL VIOLATION**

**Gaps**:
1. **Harder to observe**: Envelope structure obscures actual data
2. **More parsing**: Multiple JSON parse steps to extract date
3. **Unclear data flow**: Must trace through nested structure

**Impact**:
- Debugging takes longer (must parse logs to understand data)
- Evidence layer 2 (content) becomes weaker (nested structure)
- Harder to verify correct behavior (multiple parsing steps)

**Verdict**: Passing envelope **degrades evidence quality** - makes observation harder, weakens content signal.

---

### Principle #18: Logging Discipline (Storytelling Pattern)

**Compliance question**: Do logs tell a narrative with beginning, middle, and end?

**Analysis**:

**Current log narrative** (with input transformer):
```
[INFO] ====== Get Report List Lambda Started ======
[INFO] Using explicit report_date from event: 2026-01-04
[INFO] Querying reports needing PDFs for date: 2026-01-04
[INFO] ✅ Found 1 reports needing PDFs
```
**Story**: Clear, linear, self-explanatory

**Proposed log narrative** (with envelope):
```
[INFO] ====== Get Report List Lambda Started ======
[DEBUG] Received EventBridge envelope: {"version":"0","id":"17fbc6b2-...","detail":{"executionArn":"...","status":"SUCCEEDED","input":"{}","output":"{\"status\":\"completed\",\"total_tickers\":46,...}"}}
[DEBUG] Parsing envelope detail field
[DEBUG] Extracting output JSON string
[DEBUG] Deserializing output: {"status":"completed","total_tickers":46,...}
[DEBUG] report_date not found in output, checking input
[DEBUG] Parsing input JSON string: {}
[DEBUG] report_date not found in input, using today
[INFO] Using today's Bangkok date: 2026-01-04
[INFO] Querying reports needing PDFs for date: 2026-01-04
[INFO] ✅ Found 1 reports needing PDFs
```
**Story**: Cluttered, verbose, hard to follow

**Status**: ⚠️ **PARTIAL VIOLATION**

**Gaps**:
1. **Signal-to-noise ratio low**: 7 debug lines vs 1 info line
2. **Narrative interrupted**: Parsing details break story flow
3. **Harder to grep**: Must parse JSON in logs to extract date

**Impact**:
- Logs harder to read (must skip parsing details)
- CloudWatch Insights queries more complex (must parse nested JSON)
- Production debugging slower (more log lines to analyze)

**Verdict**: Passing envelope **degrades logging quality** - adds noise, breaks narrative flow.

---

### Principle #12: OWL-Based Relationship Analysis

**Compliance question**: Was the design decision analyzed with formal relationships?

**Analysis**:

**Two design alternatives**:
1. **Input Transformer** (current recommendation)
2. **Envelope Passthrough** (proposed)

**Relationship analysis**:

**Part-Whole**:
- Input transformer is **part of** EventBridge (AWS-provided feature)
- Envelope parsing is **part of** Lambda (custom code)
- Transformer is AWS-managed, parsing is self-managed

**Complement**:
- Input transformer **complements** Lambda by decoupling from envelope
- Lambda **complements** Step Functions by processing data
- Both work together but handle different concerns

**Substitution**:
- Transformer **cannot fully substitute** envelope parsing (but better separation)
- Envelope parsing **can substitute** transformer (but worse design)

**Composition**:
```
EventBridge Envelope
  + Input Transformer (AWS-managed)
    = Simple JSON
      + Lambda (application code)
        = Business logic
```
vs
```
EventBridge Envelope
  + Lambda (mixed: parsing + business logic)
    = Tightly coupled
```

**Trade-off matrix**:

| Aspect | Input Transformer | Envelope Passthrough |
|--------|-------------------|----------------------|
| **Simplicity** | ✅ Simple Lambda code | ❌ Complex parsing code |
| **Coupling** | ✅ Decoupled from AWS | ❌ Tightly coupled to AWS |
| **Testability** | ✅ Easy to test | ❌ Hard to test |
| **Maintainability** | ✅ AWS manages schema | ❌ We manage parsing |
| **Performance** | ✅ No parsing overhead | ❌ JSON parsing cost |
| **Debuggability** | ✅ Clear logs | ❌ Verbose logs |

**Status**: ✅ **COMPLIANT** (relationship analysis performed)

**Verdict**: Analysis shows input transformer is superior in **all aspects** except... (none found).

---

## Overall Assessment

### Principle Violations Summary

| Principle | Status | Severity | Impact |
|-----------|--------|----------|--------|
| #1 Defensive Programming | ❌ VIOLATION | HIGH | Delayed failure, unclear errors |
| #4 Type System Integration | ❌ VIOLATION | HIGH | Complex parsing, fragile code |
| #19 Cross-Boundary Testing | ❌ VIOLATION | CRITICAL | Untestable integration |
| #20 Execution Boundaries | ❌ VIOLATION | CRITICAL | Tight AWS coupling |
| #2 Evidence Strengthening | ⚠️ PARTIAL | MEDIUM | Harder debugging |
| #18 Logging Discipline | ⚠️ PARTIAL | MEDIUM | Verbose logs |
| #12 Relationship Analysis | ✅ COMPLIANT | N/A | Correct analysis |

**Compliance**: 29% (2/7 principles compliant)

---

## Recommendations

### Priority: CRITICAL - Do Not Implement

**Recommendation**: ❌ **REJECT PROPOSAL**

**Rationale**:
1. **Violates 4 core principles** (Defensive Programming, Type System, Boundary Testing, Execution Boundaries)
2. **No benefits identified** - All trade-offs favor input transformer
3. **High technical debt** - Complex parsing code, hard to test, tightly coupled
4. **Maintenance burden** - Must update Lambda if AWS changes envelope schema

---

### Alternative: Use Input Transformer (Recommended)

**Implementation**:
```terraform
resource "aws_cloudwatch_event_target" "start_pdf_workflow" {
  rule      = aws_cloudwatch_event_rule.precompute_complete.name
  target_id = "StartPDFWorkflow"
  arn       = aws_sfn_state_machine.pdf_workflow.arn
  role_arn  = aws_iam_role.eventbridge_sfn_role.arn

  # Transform envelope to Lambda expected format
  input_transformer {
    input_paths = {
      event_time = "$.time"
    }
    input_template = <<EOF
{
  "report_date": "<event_time>"
}
EOF
  }
}
```

**Benefits**:
- ✅ Complies with all 7 principles
- ✅ Simple Lambda code (1 line: `event.get('report_date')`)
- ✅ Decoupled from AWS EventBridge schema
- ✅ Easy to test (simple JSON input)
- ✅ Clear logs (no parsing noise)
- ✅ AWS-managed transformation (no maintenance burden)

---

## Action Items

### 1. **[CRITICAL]** Reject envelope passthrough proposal
   - **Reason**: Violates 4 core principles
   - **Action**: Use input transformer instead
   - **Verification**: Code review checks for envelope parsing logic
   - **Time**: Immediate

### 2. **[HIGH]** Implement input transformer in Terraform
   - **File**: `terraform/pdf_workflow.tf`
   - **Change**: Add `input_transformer` block to `aws_cloudwatch_event_target`
   - **Verification**: `terraform plan` shows input_transformer configuration
   - **Time**: 10 minutes

### 3. **[MEDIUM]** Document decision rationale
   - **Command**: `/journal architecture "Why input transformer over envelope passthrough"`
   - **Content**: Link to this audit, principle violations, trade-off analysis
   - **Verification**: Check `.claude/journals/architecture/` for entry
   - **Time**: 5 minutes

### 4. **[LOW]** Add principle check to code review checklist
   - **File**: `.github/PULL_REQUEST_TEMPLATE.md`
   - **Add**: "Does this PR parse EventBridge envelopes? (Should use input transformer)"
   - **Verification**: PR template updated
   - **Time**: 2 minutes

---

## Next Audit

**Timing**: After EventBridge input transformer implementation
**Focus**: Verify input transformer correctly reshapes envelope to `{"report_date": "..."}`
**Command**:
```bash
# Deploy input transformer
terraform apply

# Trigger precompute workflow
# Wait for EventBridge to trigger PDF workflow
# Verify PDF workflow received correct input format
aws stepfunctions describe-execution --execution-arn <pdf_workflow_execution> \
  --query 'input'

# Should show: {"report_date": "2026-01-04"}
# NOT: EventBridge envelope
```

---

## References

**Principles violated**:
- Principle #1: Defensive Programming
- Principle #4: Type System Integration Research
- Principle #19: Cross-Boundary Contract Testing
- Principle #20: Execution Boundary Discipline

**Validations**:
- `.claude/validations/2026-01-04-nightly-scheduler-workflow-chain.md` - EventBridge integration analysis
- `.claude/validations/2026-01-04-pdf-generation-two-path-understanding.md` - Parameter handling
- `.claude/what-if/2026-01-04-date-vs-report-date-parameter-naming.md` - Parameter naming

**Patterns**:
- `.claude/patterns/service-integration-verification.md` - Service boundary best practices

---

## Summary

**Proposal**: Pass EventBridge envelope to Lambda (instead of using input transformer)

**Compliance**: 29% (2/7 principles)

**Violations**:
- ❌ Principle #1: Delayed failure, complex validation
- ❌ Principle #4: Multiple type conversions, no schema research
- ❌ Principle #19: Untestable service boundary
- ❌ Principle #20: Tight coupling to AWS schema

**Recommendation**: ❌ **DO NOT IMPLEMENT**

**Alternative**: Use EventBridge input transformer (complies with all principles)

**Next steps**:
1. Reject envelope passthrough
2. Implement input transformer
3. Document decision
4. Add to code review checklist
