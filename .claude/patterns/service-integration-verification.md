# Pattern: Service Integration Verification

**Pattern Type**: Architecture / Debugging
**Domain**: AWS Service Integration (Step Functions, EventBridge, SQS, SNS, Lambda)
**Date Discovered**: 2026-01-04
**Incident**: PDF workflow Step Functions → Lambda payload passthrough bug

---

## Problem

When integrating AWS services (Step Functions → Lambda, EventBridge → Step Functions, etc.), configuration bugs at service boundaries cause silent failures or unexpected behavior. Traditional debugging approaches verify individual components but miss integration contract violations.

**Symptoms**:
- Lambda receives empty event despite service sending data
- Service integration works in isolation but fails end-to-end
- Manual invocation succeeds, automated trigger fails
- Zero-gradient debugging pattern (multiple attempts, same outcome)

---

## Anti-Pattern: Assume Integration Works

```terraform
# Step Functions definition
"Parameters": {
  "FunctionName": "${lambda_arn}",
  "Payload": {}  # ❌ Hardcoded empty payload
}
```

**What happens**:
1. Step Functions receives input: `{"report_date": "2026-01-04"}`
2. Step Functions invokes Lambda with: `{}` (empty)
3. Lambda falls back to default behavior (today's date)
4. Workflow appears successful but uses wrong data
5. Bug invisible until manual testing reveals discrepancy

**Root cause**: Assumed service integration passes input automatically

---

## Solution: 4-Layer Evidence Verification

Apply **Progressive Evidence Strengthening** (Principle #2) to service boundaries:

### Layer 1: Surface Signal (Weakest)
```bash
# Check workflow execution status
aws stepfunctions describe-execution --execution-arn "$ARN" --query 'status'
# Output: "SUCCEEDED"
# ⚠️ Status alone doesn't confirm correct behavior
```

### Layer 2: Content Signal (Stronger)
```bash
# Check Lambda CloudWatch logs
aws logs tail /aws/lambda/function-name --follow
# Look for: What event did Lambda receive?
```

**Example log output**:
```
[INFO] Using today's Bangkok date: 2026-01-04
```

**Question**: Why "today's date"? Should have explicit report_date from event.

### Layer 3: Observability Signal (Stronger Still)
```bash
# Inspect Step Functions execution history
aws stepfunctions get-execution-history --execution-arn "$ARN" > history.json

# Extract Lambda input
jq '.events[] | select(.type=="TaskScheduled") | .taskScheduledEventDetails.parameters' history.json
```

**Reveals**:
```json
{
  "FunctionName": "arn:...:function:my-lambda",
  "Payload": {}  // ❌ Empty payload sent to Lambda
}
```

**Finding**: Step Functions definition hardcoded empty payload.

### Layer 4: Ground Truth (Strongest)
```bash
# Direct Lambda invocation
aws lambda invoke \
  --function-name my-lambda \
  --cli-binary-format raw-in-base64-out \
  --payload '{"report_date":"2026-01-04"}' \
  response.json

cat response.json
# Output: {"reports": [{"id": 2081, "symbol": "D05.SI"}]}
# ✅ Lambda DOES find report when invoked directly
```

**Conclusion**: Lambda code correct, Step Functions integration broken.

---

## Correct Pattern: Explicit Payload Passthrough

```terraform
# Step Functions definition (CORRECTED)
"Parameters": {
  "FunctionName": "${lambda_arn}",
  "Payload.$": "$"  # ✅ JsonPath reference to input
}
```

**How it works**:
1. Step Functions receives input: `{"report_date": "2026-01-04"}`
2. `"Payload.$": "$"` passes entire input as Lambda payload
3. Lambda receives: `{"report_date": "2026-01-04"}`
4. Lambda uses explicit date from event
5. Workflow behaves correctly

**JsonPath syntax**:
- `"Payload.$": "$"` → Pass entire input
- `"Payload.$": "$.report_date"` → Pass specific field
- `"Payload": {}` → Hardcoded empty object (WRONG)

---

## Debugging Protocol

### When to Apply

Use this protocol when:
- ✅ Service integration fails end-to-end
- ✅ Individual components work in isolation
- ✅ Zero-gradient pattern detected (2+ attempts, same outcome)
- ✅ Logs suggest service not receiving expected input

### Step-by-Step Debugging

**1. Verify Surface Signal** (30 seconds)
```bash
# Check final workflow status
aws stepfunctions describe-execution --execution-arn "$ARN" --query 'status'
```

**2. Check Lambda Logs** (Layer 2) (2 minutes)
```bash
# What event did Lambda receive?
aws logs tail /aws/lambda/function-name --since 5m --filter-pattern "event"
```

**Look for**:
- Default behavior triggered? (e.g., "Using today's date")
- Missing expected fields? (e.g., no "report_date" logged)

**3. Invoke Lambda Directly** (Layer 4) (5 minutes)
```bash
# Isolate Lambda from service integration
aws lambda invoke \
  --function-name my-lambda \
  --cli-binary-format raw-in-base64-out \
  --payload '{"report_date":"2026-01-04"}' \
  response.json
```

**Result interpretation**:
- Lambda returns correct result → Integration bug (proceed to step 4)
- Lambda returns same error → Lambda bug (fix Lambda first)

**4. Inspect Service Execution History** (Layer 3) (5 minutes)
```bash
# What payload did Step Functions send?
aws stepfunctions get-execution-history --execution-arn "$ARN" > history.json
jq '.events[2].taskScheduledEventDetails.parameters' history.json
```

**Look for**:
- `"Payload": {}` → Hardcoded empty (BUG)
- `"Payload.$": "$"` → JsonPath reference (CORRECT)

**5. Fix Integration Contract**

Update service definition:
```diff
- "Payload": {}
+ "Payload.$": "$"
```

Deploy and re-test through all 4 evidence layers.

---

## Integration Test Pattern

### Preventive Testing

**Test the integration, not just the components:**

```python
def test_step_functions_passes_payload_to_lambda():
    """Integration test: Step Functions → Lambda payload passthrough

    Tests service boundary contract (Principle #19).
    Prevents configuration regressions.
    """
    # Trigger Step Functions with test input
    execution_arn = sfn_client.start_execution(
        stateMachineArn="arn:...:stateMachine:pdf-workflow-dev",
        input='{"report_date":"2026-01-04"}'
    )

    # Wait for completion
    waiter = sfn_client.get_waiter('execution_succeeded')
    waiter.wait(executionArn=execution_arn)

    # Verify Lambda received correct payload (Layer 3: Observability)
    history = sfn_client.get_execution_history(executionArn=execution_arn)
    lambda_input = next(
        event['taskScheduledEventDetails']['parameters']
        for event in history['events']
        if event['type'] == 'TaskScheduled'
    )

    # Assert: Lambda received report_date
    payload = json.loads(lambda_input['Payload'])
    assert 'report_date' in payload, "Step Functions didn't pass report_date to Lambda"
    assert payload['report_date'] == '2026-01-04'
```

**Why this test prevents the bug**:
- Tests actual service integration (not mocked)
- Verifies payload at boundary (Layer 3 evidence)
- Catches configuration regressions before deployment
- Runs in CI/CD pipeline automatically

### Where to Add Test

**File**: `tests/integration/test_step_functions_integration.py`

**When to run**:
- ✅ Before merging Step Functions definition changes
- ✅ In CI/CD pipeline (GitHub Actions)
- ✅ After Terraform infrastructure updates

---

## Checklist: Service Integration Verification

Use this checklist when integrating AWS services:

### Pre-Deployment

- [ ] **Contract defined**: Explicit payload format documented
- [ ] **JsonPath syntax verified**: `"Payload.$": "$"` (not `"Payload": {}`)
- [ ] **Integration test written**: Tests service boundary contract
- [ ] **Terraform validated**: `terraform plan` shows correct payload reference

### Post-Deployment

- [ ] **Layer 1 (Surface)**: Execution status = SUCCEEDED
- [ ] **Layer 2 (Content)**: Lambda logs show expected event structure
- [ ] **Layer 3 (Observability)**: Execution history shows correct payload
- [ ] **Layer 4 (Ground Truth)**: Aurora/S3 state matches expectations

### Zero-Gradient Debugging

If 2+ attempts with same outcome:

- [ ] **Stop retrying**: Zero-gradient detected (stuck pattern)
- [ ] **Inspect execution history**: Check actual payload sent
- [ ] **Invoke Lambda directly**: Isolate service boundary
- [ ] **Compare working vs broken**: What changed in integration?
- [ ] **Fix root cause**: Update service definition, not workaround

---

## Related Patterns

- **Progressive Evidence Strengthening** (Principle #2): 4-layer verification framework
- **Execution Boundary Discipline** (Principle #20): Service boundaries are execution boundaries
- **Cross-Boundary Contract Testing** (Principle #19): Service integration testing
- **Infrastructure-Application Contract** (Principle #15): Terraform ↔ Application alignment

---

## Common Service Integration Bugs

### 1. Step Functions → Lambda
**Bug**: `"Payload": {}` hardcoded
**Fix**: `"Payload.$": "$"`
**Detection**: Lambda logs show default behavior

### 2. EventBridge → Step Functions
**Bug**: Event pattern mismatch (Step Functions not triggered)
**Fix**: `aws events test-event-pattern`
**Detection**: Step Functions execution count = 0

### 3. Lambda → SQS
**Bug**: Message body not JSON-serialized
**Fix**: `json.dumps(message)` before `send_message()`
**Detection**: Consumer Lambda fails to parse message

### 4. API Gateway → Lambda
**Bug**: Lambda expects `event['body']`, API Gateway sends `event`
**Fix**: API Gateway integration type (Lambda vs Lambda Proxy)
**Detection**: Lambda crashes with KeyError

---

## Real-World Example

**Incident**: PDF workflow returned "0 reports found" despite database having eligible reports

**Debugging Timeline**:
1. **00:00**: Workflow triggered → 0 reports found
2. **00:05**: Retry #2 → 0 reports found (zero-gradient detected)
3. **00:10**: Check Lambda logs → "Using today's date" (Layer 2)
4. **00:15**: Invoke Lambda directly → Finds 1 report! (Layer 4)
5. **00:20**: Inspect execution history → `"Payload": {}` found (Layer 3)
6. **00:25**: Fix Step Functions → `"Payload.$": "$"`
7. **00:30**: Re-test → Success! PDF generated

**Lesson**: Layer 3 (execution history) would have revealed root cause immediately, but was checked last instead of second.

**Optimal debugging order**:
1. Layer 1: Surface signal (confirm failure)
2. **Layer 3: Execution history** (identify integration bug)
3. Layer 4: Direct invocation (confirm Lambda works)
4. Layer 2: Logs (optional, for additional context)

---

## References

- **Incident**: PDF workflow debugging (2026-01-04)
- **Validation**: `.claude/validations/2026-01-04-single-ticker-pdf-generation.md`
- **Principle #2**: Progressive Evidence Strengthening
- **Principle #15**: Infrastructure-Application Contract
- **Principle #19**: Cross-Boundary Contract Testing
- **Principle #20**: Execution Boundary Discipline

---

## Summary

**Pattern**: When debugging AWS service integrations, apply 4-layer evidence verification. Don't assume configuration is correct—inspect execution history to verify payload contracts at service boundaries. Write integration tests to prevent regressions.

**Key Insight**: "Service integration bugs hide between working components. Verify boundaries, not just endpoints."
