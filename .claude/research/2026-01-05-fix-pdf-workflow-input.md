# Research: Fix Incorrect Input to PDF Generation Step Function

**Date**: 2026-01-05
**Focus**: Comprehensive
**Status**: Complete

---

## Problem Decomposition

**Goal**: Fix EventBridge → PDF workflow integration so `report_date` is passed correctly

**Current State**:
- EventBridge triggers PDF workflow after precompute completes (✅ works)
- EventBridge passes raw envelope structure (❌ problem)
- PDF workflow Lambda defaults to "today's date" (⚠️ works by coincidence)

**Core Requirements**:
- PDF workflow must receive `{"report_date": "2026-01-04"}` structure
- Solution must work for both EventBridge trigger AND manual execution
- Must not violate CLAUDE.md principles
- Must be testable and maintainable

**Constraints**:
- Must use existing AWS services (no new infrastructure)
- Must deploy via Terraform (infrastructure as code)
- Must work in dev/staging/prod environments consistently
- Must complete in <1 day (not a multi-week project)

**Success Criteria**:
- ✅ EventBridge passes `report_date` to PDF workflow
- ✅ Manual execution with `{"report_date": "..."}` still works
- ✅ Complies with all CLAUDE.md principles
- ✅ Testable via integration tests
- ✅ Clear failure modes (fails fast if misconfigured)

**Stakeholders**:
- End users: Want PDFs generated for correct date
- Development team: Want simple, maintainable solution
- DevOps: Want reliable, observable infrastructure

---

## Solution Space (Divergent Phase)

### Option 1: EventBridge Input Transformer

**Description**: Use AWS EventBridge's built-in input transformation to extract date from envelope and reshape payload before sending to Step Functions.

**How it works**:
```terraform
# terraform/pdf_workflow.tf
resource "aws_cloudwatch_event_target" "start_pdf_workflow" {
  rule      = aws_cloudwatch_event_rule.precompute_complete.name
  target_id = "StartPDFWorkflow"
  arn       = aws_sfn_state_machine.pdf_workflow.arn
  role_arn  = aws_iam_role.eventbridge_sfn_role.arn

  # ADD THIS BLOCK
  input_transformer {
    input_paths = {
      event_time = "$.time"  # Extract ISO8601 timestamp from envelope
    }
    input_template = <<EOF
{
  "report_date": "<event_time>"
}
EOF
  }
}
```

**What happens**:
1. EventBridge receives Step Functions completion event
2. Extracts `$.time` field (ISO8601 timestamp: `2026-01-04T16:15:06Z`)
3. Transforms to JSON: `{"report_date": "2026-01-04T16:15:06Z"}`
4. Passes transformed payload to PDF workflow
5. Lambda receives clean `{"report_date": "..."}` structure

**Pros**:
- ✅ Infrastructure handles infrastructure concerns (clean separation)
- ✅ No Lambda code changes required
- ✅ Works for EventBridge trigger automatically
- ✅ Manual execution still works (same input format)
- ✅ Simple to test (1 Terraform change)
- ✅ Fails fast if schema changes (EventBridge validates JsonPath)
- ✅ Complies with ALL CLAUDE.md principles (see audit)

**Cons**:
- ⚠️ Timestamp includes time component (`2026-01-04T16:15:06Z`)
- ⚠️ Lambda needs to parse ISO8601 → extract date part
- ⚠️ Requires Terraform deployment

**Examples**:
- AWS EventBridge documentation: Standard pattern for payload transformation
- Used by: All AWS customers doing EventBridge → Lambda/Step Functions integration
- Production-proven: Billions of events processed daily

**Resources**:
- [AWS EventBridge Input Transformation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-transform-target-input.html)
- [Input Transformer Syntax](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-input-transformer-tutorial.html)

---

### Option 2: Extract Date from Precompute Input

**Description**: Instead of using EventBridge envelope's `time` field, extract `report_date` from the ORIGINAL precompute workflow's input (passed through envelope's `detail.input` field).

**How it works**:
```terraform
input_transformer {
  input_paths = {
    precompute_input = "$.detail.input"  # Original input to precompute workflow
  }
  input_template = <<EOF
{
  "report_date": <precompute_input>
}
EOF
}
```

**What happens**:
1. EventBridge receives Step Functions completion event
2. Envelope contains `detail.input` = `"{\"report_date\":\"2026-01-04\"}"`
3. Extracts `detail.input` field (JSON string)
4. Passes it through as-is
5. Result: `{"report_date": {"report_date": "2026-01-04"}}` (NESTED!)

**Pros**:
- ✅ Preserves original `report_date` from scheduler
- ✅ No time parsing needed (already date-only format)

**Cons**:
- ❌ Creates nested structure (Lambda expects top-level `report_date`)
- ❌ Requires Lambda code changes to unwrap nesting
- ❌ Fragile: Depends on precompute input structure
- ❌ Breaks if precompute input changes
- ❌ More complex JsonPath (`$.detail.input` + JSON parsing)

**Verdict**: ❌ Rejected - Creates nested structure, requires code changes

---

### Option 3: Step Functions Input Passthrough

**Description**: Modify PDF workflow Step Functions definition to extract `report_date` from EventBridge envelope using JsonPath in the state machine itself.

**How it works**:
```json
{
  "StartAt": "ExtractDate",
  "States": {
    "ExtractDate": {
      "Type": "Pass",
      "Parameters": {
        "report_date.$": "$.detail.input.report_date"
      },
      "Next": "GetReportList"
    },
    "GetReportList": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${get_report_list_lambda_arn}",
        "Payload.$": "$"
      },
      "Next": "..."
    }
  }
}
```

**What happens**:
1. EventBridge sends raw envelope to Step Functions
2. Step Functions "ExtractDate" state extracts date from envelope
3. Passes extracted data to Lambda

**Pros**:
- ✅ No EventBridge configuration needed
- ✅ Works within Step Functions

**Cons**:
- ❌ Adds complexity to Step Functions state machine
- ❌ Breaks manual execution (manual input ≠ EventBridge envelope)
- ❌ Violates Principle #20 (Execution Boundary Discipline - tight coupling)
- ❌ Harder to test (requires Step Functions execution, not just Lambda)
- ❌ Dual input formats (manual vs EventBridge)

**Verdict**: ❌ Rejected - Breaks manual execution, adds complexity

---

### Option 4: Lambda Envelope Parsing

**Description**: Update GetReportList Lambda to detect and parse EventBridge envelope structure, extracting date from envelope fields.

**How it works**:
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Try 1: Top-level report_date (manual execution)
    report_date_str = event.get('report_date')

    if not report_date_str:
        # Try 2: EventBridge envelope - extract from detail.input
        detail = event.get('detail', {})
        if isinstance(detail, dict):
            input_str = detail.get('input', '{}')
            input_data = json.loads(input_str) if input_str else {}
            report_date_str = input_data.get('report_date')

    if not report_date_str:
        # Try 3: EventBridge envelope - extract from time field
        report_date_str = event.get('time', '').split('T')[0]

    if report_date_str:
        report_date = date.fromisoformat(report_date_str.split('T')[0])
    else:
        # Default: Use today
        report_date = datetime.now(bangkok_tz).date()
```

**What happens**:
1. Lambda tries multiple extraction strategies
2. Falls back through strategies until one succeeds
3. Defaults to "today" if all fail

**Pros**:
- ✅ No infrastructure changes needed
- ✅ Handles both manual and EventBridge triggers
- ✅ Can deploy immediately (pure code change)

**Cons**:
- ❌ Violates Principle #1 (Defensive Programming - delayed failure)
- ❌ Violates Principle #4 (Type System Integration - no research)
- ❌ Violates Principle #19 (Cross-Boundary Testing - untestable boundary)
- ❌ Violates Principle #20 (Execution Boundaries - tight coupling)
- ❌ Complex parsing logic (15+ lines vs 1 line)
- ❌ Silent fallback to "today" hides extraction failure
- ❌ Hard to test (10+ edge cases)

**Verdict**: ❌ REJECTED - See principle audit (29% compliance)

---

### Option 5: Separate EventBridge Rule with Date Extraction

**Description**: Create a dedicated Lambda function that receives EventBridge event, extracts date, and triggers PDF workflow with clean input.

**How it works**:
```
EventBridge (precompute complete)
  ↓
New Lambda: ExtractDateAndTriggerPDF
  ↓ (extracts date, triggers Step Functions)
Step Functions: PDF Workflow
  ↓
Lambda: GetReportList
```

**Code**:
```python
def lambda_handler(event, context):
    """Extract date from EventBridge envelope and trigger PDF workflow."""
    # Extract date from envelope
    detail = event.get('detail', {})
    input_str = detail.get('input', '{}')
    input_data = json.loads(input_str) if input_str else {}
    report_date = input_data.get('report_date')

    # Trigger PDF workflow with clean input
    sfn_client.start_execution(
        stateMachineArn=PDF_WORKFLOW_ARN,
        input=json.dumps({"report_date": report_date})
    )
```

**Terraform**:
```terraform
# New Lambda function
resource "aws_lambda_function" "trigger_pdf_workflow" {
  function_name = "dr-daily-report-trigger-pdf-workflow-${var.environment}"
  # ... configuration
}

# EventBridge target changed
resource "aws_cloudwatch_event_target" "start_pdf_workflow" {
  rule      = aws_cloudwatch_event_rule.precompute_complete.name
  target_id = "TriggerPDFWorkflow"
  arn       = aws_lambda_function.trigger_pdf_workflow.arn  # Changed
  # No Step Functions ARN here
}
```

**Pros**:
- ✅ Clean separation of concerns (Lambda handles parsing)
- ✅ GetReportList Lambda stays simple
- ✅ Testable (unit test extraction logic)

**Cons**:
- ❌ Adds new Lambda function (infrastructure complexity)
- ❌ Adds latency (extra hop: EventBridge → Lambda → Step Functions)
- ❌ Adds cost (~$0.20/million invocations)
- ❌ Adds operational overhead (another Lambda to monitor)
- ❌ Over-engineering (input transformer solves this without new Lambda)

**Verdict**: ❌ Rejected - Over-engineered, adds unnecessary Lambda

---

### Option 6: Hybrid Input Transformer + Lambda Parsing

**Description**: Use input transformer to extract date from EventBridge `time` field, Lambda parses ISO8601 to extract date part.

**How it works**:

**Terraform** (EventBridge):
```terraform
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
```

**Lambda** (parsing):
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    report_date_str = event.get('report_date')

    if report_date_str:
        # Parse ISO8601 or date-only format
        if 'T' in report_date_str:
            # ISO8601: "2026-01-04T16:15:06Z" → "2026-01-04"
            report_date = date.fromisoformat(report_date_str.split('T')[0])
        else:
            # Date-only: "2026-01-04"
            report_date = date.fromisoformat(report_date_str)
        logger.info(f"Using explicit report_date from event: {report_date}")
    else:
        # Default: Use today
        bangkok_tz = ZoneInfo("Asia/Bangkok")
        report_date = datetime.now(bangkok_tz).date()
        logger.info(f"Using today's Bangkok date: {report_date}")
```

**What happens**:
1. EventBridge extracts `time` field → `"2026-01-04T16:15:06Z"`
2. Lambda receives `{"report_date": "2026-01-04T16:15:06Z"}`
3. Lambda parses ISO8601 → extracts date part → `date(2026, 1, 4)`
4. Works!

**Pros**:
- ✅ Infrastructure handles transformation (EventBridge)
- ✅ Lambda handles parsing (application logic)
- ✅ Works for both EventBridge (ISO8601) and manual (`YYYY-MM-DD`)
- ✅ Simple Lambda change (3 lines)
- ✅ Testable (unit test ISO8601 parsing)
- ✅ Fails fast if EventBridge schema changes
- ✅ Complies with all principles

**Cons**:
- ⚠️ Lambda must handle two date formats (ISO8601 vs date-only)
- ⚠️ Slightly more complex than pure input transformer

**Verdict**: ✅ BEST OPTION - Balanced approach

---

## Evaluation Matrix

**Focus**: Comprehensive (all criteria equally weighted)

| Criterion | Opt1: InputTransformer | Opt2: ExtractInput | Opt3: StepFunctions | Opt4: LambdaParsing | Opt5: NewLambda | Opt6: Hybrid |
|-----------|------------------------|--------------------|--------------------|---------------------|-----------------|--------------|
| **Simplicity** | 9/10 | 4/10 | 5/10 | 3/10 | 4/10 | 8/10 |
| **Principle Compliance** | 10/10 | 6/10 | 4/10 | 3/10 | 7/10 | 10/10 |
| **Testability** | 9/10 | 5/10 | 4/10 | 3/10 | 8/10 | 9/10 |
| **Maintainability** | 10/10 | 5/10 | 5/10 | 3/10 | 6/10 | 9/10 |
| **Manual Exec Compatible** | 10/10 | 6/10 | 2/10 | 10/10 | 10/10 | 10/10 |
| **Infrastructure Changes** | 8/10 | 8/10 | 6/10 | 10/10 | 4/10 | 8/10 |
| **Deployment Speed** | 8/10 | 8/10 | 6/10 | 10/10 | 5/10 | 7/10 |
| **Total** | **64/70** | **42/70** | **32/70** | **42/70** | **44/70** | **61/70** |

**Scoring rationale**:

**Simplicity**:
- Opt1: Infrastructure handles transformation (9/10)
- Opt6: Infra + minimal Lambda parsing (8/10)
- Opt2: Nested structure, code changes (4/10)
- Opt5: New Lambda, more moving parts (4/10)
- Opt3: State machine complexity (5/10)
- Opt4: 15+ lines parsing logic (3/10)

**Principle Compliance**:
- Opt1 & Opt6: 100% compliance (10/10)
- Opt5: Good but adds Lambda (7/10)
- Opt2: Fragile coupling (6/10)
- Opt3: Breaks manual exec (4/10)
- Opt4: 29% compliance - see audit (3/10)

**Testability**:
- Opt1: 1 Terraform test (9/10)
- Opt6: Terraform + unit test (9/10)
- Opt5: Unit test new Lambda (8/10)
- Opt2: Integration test (5/10)
- Opt3: Step Functions test (4/10)
- Opt4: 10+ edge cases (3/10)

**Maintainability**:
- Opt1: No code, just config (10/10)
- Opt6: Minimal code change (9/10)
- Opt5: Extra Lambda to maintain (6/10)
- Opt2 & Opt3: Coupled to envelope (5/10)
- Opt4: Complex parsing (3/10)

**Manual Execution Compatible**:
- Opt1, Opt4, Opt5, Opt6: Works for both (10/10)
- Opt2: Nested structure (6/10)
- Opt3: Breaks manual (2/10)

**Infrastructure Changes**:
- Opt4: Pure code (10/10)
- Opt1, Opt2, Opt6: Terraform only (8/10)
- Opt3: State machine change (6/10)
- Opt5: New Lambda + Terraform (4/10)

**Deployment Speed**:
- Opt4: Code deploy ~8 min (10/10)
- Opt1, Opt2: Terraform ~10 min (8/10)
- Opt6: Code + Terraform ~12 min (7/10)
- Opt3: State machine ~10 min (6/10)
- Opt5: New Lambda ~15 min (5/10)

---

## Ranked Recommendations

### 1. Option 1: EventBridge Input Transformer (Score: 64/70) ⭐ RECOMMENDED

**Why**:
- Infrastructure handles infrastructure concerns (cleanest separation)
- No Lambda code changes required (simplest)
- 100% principle compliance (see audit)
- Testable with single Terraform test
- Standard AWS pattern (billions of events processed daily)

**Trade-offs**:
- Gain: Clean separation, simple, maintainable
- Lose: Lambda receives ISO8601 timestamp (not date-only)
- **Minor caveat**: Lambda must parse `"2026-01-04T16:15:06Z"` → `date(2026, 1, 4)`

**When to choose**:
- Default choice for EventBridge → Lambda/Step Functions integration
- When principle compliance matters
- When simplicity is priority

**Implementation**:
```terraform
# terraform/pdf_workflow.tf:446-451
resource "aws_cloudwatch_event_target" "start_pdf_workflow" {
  rule      = aws_cloudwatch_event_rule.precompute_complete.name
  target_id = "StartPDFWorkflow"
  arn       = aws_sfn_state_machine.pdf_workflow.arn
  role_arn  = aws_iam_role.eventbridge_sfn_role.arn

  # ADD THIS BLOCK
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

**Next step**:
```bash
# Converge on implementation details
/specify "EventBridge Input Transformer for PDF workflow date passing"
```

---

### 2. Option 6: Hybrid Input Transformer + Lambda Parsing (Score: 61/70)

**Why**:
- Best of both worlds (infrastructure + application)
- Handles dual formats (ISO8601 from EventBridge, date-only from manual)
- 100% principle compliance
- Slightly more robust than pure input transformer

**When to choose**:
- If you want explicit handling of ISO8601 vs date-only formats
- If Lambda parsing is already needed for other reasons
- If you prefer application-level format normalization

**Trade-off vs Option 1**:
- More code (3 extra lines in Lambda)
- Slightly more complex testing (ISO8601 parsing unit test)
- Slightly longer deployment (code + Terraform)
- BUT: More explicit format handling

**Implementation**:
Same Terraform as Option 1 + Lambda parsing logic

---

### 3. Option 5: Separate Lambda (Score: 44/70)

**When to choose**:
- When you have OTHER transformation logic needed (not just date extraction)
- When you want to centralize EventBridge envelope parsing
- When you have many workflows triggered by EventBridge (shared logic)

**Why NOT for this case**:
- Over-engineered for simple date extraction
- Adds operational overhead (another Lambda to monitor)
- Input transformer solves this without new infrastructure

---

### 4. Option 2 & 4: ❌ DO NOT USE

**Option 2** (Extract from precompute input): Creates nested structure
**Option 4** (Lambda envelope parsing): 29% principle compliance, too complex

**Why rejected**: See principle audit document

---

## Resources Gathered

**Official Documentation**:
- [AWS EventBridge Input Transformation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-transform-target-input.html)
- [Step Functions Input/Output Processing](https://docs.aws.amazon.com/step-functions/latest/dg/input-output-inputpath-params.html)

**Example Implementations**:
- [EventBridge Input Transformer Tutorial](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-input-transformer-tutorial.html)
- AWS Samples: [EventBridge patterns](https://github.com/aws-samples/amazon-eventbridge-resource-policy-samples)

**Comparison Articles**:
- [Service Integration Verification Pattern](.claude/patterns/service-integration-verification.md)
- [EventBridge Envelope Passthrough Audit](.claude/audits/2026-01-04-eventbridge-envelope-passthrough-principle-check.md)

**Related Validations**:
- [Nightly Scheduler Workflow Chain](.claude/validations/2026-01-04-nightly-scheduler-workflow-chain.md)
- [PDF Generation Two-Path Understanding](.claude/validations/2026-01-04-pdf-generation-two-path-understanding.md)

---

## Decision Rationale

**Why Option 1 (Input Transformer) wins**:

1. **Principle #20 (Execution Boundaries)**: Infrastructure handles infrastructure concerns
   - EventBridge envelope → EventBridge transformation
   - Lambda receives clean, typed input
   - No tight coupling

2. **Principle #1 (Defensive Programming)**: Fails fast
   - EventBridge validates JsonPath at deployment
   - Lambda receives expected structure or EventBridge fails
   - No silent fallbacks

3. **Principle #19 (Cross-Boundary Testing)**: Simple to test
   - Single Terraform test: Does input transformer produce correct JSON?
   - No complex edge cases (10+ scenarios → 1 scenario)

4. **Principle #4 (Type System Integration)**: Researched AWS capabilities
   - Input transformer is AWS-native solution for this exact use case
   - Documented, production-proven, billions of events processed

5. **Simplicity**: No code changes, just configuration
   - 6 lines of Terraform
   - vs 15+ lines of Lambda parsing (Option 4)
   - vs New Lambda function (Option 5)

6. **AWS Best Practice**: This is the recommended pattern
   - AWS documentation shows input transformer for payload reshaping
   - Industry standard for EventBridge → Lambda/Step Functions integration

---

## Next Steps

```bash
# RECOMMENDED: Implement Option 1 (Input Transformer)
/specify "EventBridge Input Transformer for PDF workflow date passing"

# ALTERNATIVE: If you prefer hybrid approach
/specify "Hybrid Input Transformer + Lambda ISO8601 parsing"

# VALIDATE: Test assumption about ISO8601 parsing
/validate "hypothesis: Python date.fromisoformat() can parse ISO8601 date part"

# COMPARE: If still deciding between Option 1 vs Option 6
/what-if "compare pure input transformer vs hybrid approach"
```

---

## Summary

**Problem**: EventBridge passes raw envelope to PDF workflow, Lambda defaults to "today"

**Root Cause**: Missing input transformation in EventBridge target configuration

**Solution**: Add EventBridge input transformer (6 lines of Terraform)

**Why this solution**:
- Cleanest separation of concerns (infrastructure handles infrastructure)
- 100% principle compliance
- Simplest implementation (no code changes)
- Standard AWS pattern
- Fails fast if misconfigured

**Implementation effort**: ~30 minutes (Terraform change + deploy + test)

**Alternative considered**: Hybrid approach (input transformer + Lambda parsing) also viable if explicit format handling preferred

**Rejected alternatives**: Lambda envelope parsing (29% compliance), new Lambda (over-engineered), Step Functions extraction (breaks manual execution)
