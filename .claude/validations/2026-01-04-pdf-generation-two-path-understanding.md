# Validation Report: PDF Generation Two-Path Understanding

**Claim**: "There are 2 paths to execute PDF generation: 1. Extract date from EventBridge envelope (main path) and 2. Today's date (default path). When you trigger manually, the main path always fails and the default is triggered."

**Type**: `hypothesis` (understanding of system behavior)

**Date**: 2026-01-04

**Context**: User's understanding of how the PDF workflow determines which date to use for querying reports needing PDFs.

---

## Status: ❌ FALSE (Misunderstanding of Implementation)

## Evidence Summary

### User's Understanding (What You Think Happens)

**Path 1 (Main Path)**: Extract date from EventBridge envelope
- EventBridge event contains date information
- PDF workflow tries to extract it from envelope
- **Claim**: This path fails when triggered manually

**Path 2 (Default Path)**: Use today's date
- Fallback when main path fails
- Always uses current Bangkok date
- **Claim**: This is what actually executes

---

### Actual Implementation (What Really Happens)

**There is only ONE path, not two paths.**

The GetReportList Lambda handler (`src/scheduler/get_report_list_handler.py:66-77`) has a **single conditional** that checks for `report_date` in the event:

```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Get report date from event or use today (Bangkok timezone)
    report_date_str = event.get('report_date')
    if report_date_str:
        # ✅ Path A: Explicit date provided
        report_date = date.fromisoformat(report_date_str)
        logger.info(f"Using explicit report_date from event: {report_date}")
    else:
        # ✅ Path B: No date provided, default to today
        from zoneinfo import ZoneInfo
        from datetime import datetime
        bangkok_tz = ZoneInfo("Asia/Bangkok")
        report_date = datetime.now(bangkok_tz).date()
        logger.info(f"Using today's Bangkok date: {report_date}")
```

---

### Correction to Understanding

**Path A (Explicit Date)**: ✅ Works when event contains `report_date` key
- **Triggered by**: Manual Step Functions execution with `{"report_date": "2026-01-04"}`
- **Looks for**: Top-level `event['report_date']` key
- **Result**: Uses the provided date

**Path B (Default to Today)**: ✅ Works when event does NOT contain `report_date` key
- **Triggered by**:
  - EventBridge event (passes envelope, no `report_date` key)
  - Manual execution with empty input `{}`
  - Manual execution with EventBridge envelope structure
- **Looks for**: Checks `event.get('report_date')` → returns `None`
- **Result**: Uses today's Bangkok date

---

### Key Misconception Corrected

**Your Understanding**: "Main path tries to extract from EventBridge envelope and fails"

**Reality**: There is NO code that attempts to extract date from EventBridge envelope

**What Actually Happens**:
1. Lambda receives event (either `{"report_date": "..."}` or EventBridge envelope or empty)
2. Checks if `event['report_date']` exists (simple dictionary key lookup)
3. If exists → use it (Path A)
4. If doesn't exist → use today (Path B)
5. **No extraction logic**, **no parsing logic**, **no failure** - just a simple if/else

---

## Evidence Analysis

### Evidence 1: Code Implementation

**Source**: `src/scheduler/get_report_list_handler.py:66-77`

**Finding**: Single `if/else` conditional, not two separate code paths

```python
# Line 67: Get from event (simple dictionary access)
report_date_str = event.get('report_date')

# Line 68-70: Path A (explicit date provided)
if report_date_str:
    report_date = date.fromisoformat(report_date_str)
    logger.info(f"Using explicit report_date from event: {report_date}")

# Line 71-77: Path B (default to today)
else:
    bangkok_tz = ZoneInfo("Asia/Bangkok")
    report_date = datetime.now(bangkok_tz).date()
    logger.info(f"Using today's Bangkok date: {report_date}")
```

**Critical Observation**:
- **NO** code attempts to extract from `event['detail']` (EventBridge envelope)
- **NO** code parses EventBridge event structure
- **NO** try/except for extraction failures
- **Simple if/else** based on key presence

---

### Evidence 2: Manual Execution Behavior

**Manual execution with explicit date** (`{"report_date": "2026-01-04"}`):
```json
Input: {"report_date": "2026-01-04"}
Result: event.get('report_date') → "2026-01-04"
Path: A (explicit date)
Log: "Using explicit report_date from event: 2026-01-04"
Query: WHERE report_date = '2026-01-04'
```

**Manual execution with empty input** (`{}`):
```json
Input: {}
Result: event.get('report_date') → None
Path: B (default to today)
Log: "Using today's Bangkok date: 2026-01-04"
Query: WHERE report_date = '2026-01-04'
```

**Finding**: Both work correctly - no "failure" occurs

---

### Evidence 3: EventBridge Execution Behavior

**EventBridge-triggered execution**:
```json
Input: {
  "version": "0",
  "id": "17fbc6b2-...",
  "detail-type": "Step Functions Execution Status Change",
  "source": "aws.states",
  "detail": {...}
  // ❌ NO "report_date" key at top level
}
Result: event.get('report_date') → None
Path: B (default to today)
Log: "Using today's Bangkok date: 2026-01-04"
Query: WHERE report_date = '2026-01-04'
```

**Finding**: EventBridge execution doesn't "fail" - it just doesn't have `report_date` key, so defaults to today

---

### Evidence 4: CloudWatch Logs (Production Evidence)

**Manual execution log** (from previous validation):
```
[INFO] Using explicit report_date from event: 2026-01-04
[INFO] Querying reports needing PDFs for date: 2026-01-04
[INFO] ✅ Found 1 reports needing PDFs
```

**EventBridge-triggered execution log** (from execution 17fbc6b2-...):
```
[INFO] Using today's Bangkok date: 2026-01-04
[INFO] Querying reports needing PDFs for date: 2026-01-04
[INFO] ✅ Found 0 reports needing PDFs
```

**Finding**:
- Manual execution: Path A (explicit) ✅
- EventBridge execution: Path B (default) ✅
- **No failures** - both paths execute successfully

---

## Analysis

### What You Got Right ✅

1. **Two different behaviors exist**: Correct
   - Explicit date vs default to today
   - This is accurate

2. **EventBridge trigger uses today's date**: Correct
   - EventBridge event doesn't contain `report_date` key
   - Defaults to today
   - This is accurate

3. **Manual execution can provide explicit date**: Correct
   - Manual execution with `{"report_date": "..."}` uses that date
   - This is accurate

---

### What You Got Wrong ❌

1. **"Main path" and "default path" terminology**: Incorrect
   - There aren't two separate code paths that fail/succeed
   - There's ONE conditional: if date provided, use it; else use today
   - Both are equally valid paths, not main/fallback

2. **"Main path always fails"**: Incorrect
   - No path "fails"
   - EventBridge execution doesn't attempt extraction and fail
   - It simply doesn't provide `report_date` key, so condition is false

3. **"Extract date from EventBridge envelope"**: Incorrect
   - Code does NOT attempt to extract from envelope
   - Code does NOT parse `event['detail']` or `event['time']`
   - Code simply checks if `event['report_date']` exists (top-level key)

4. **"When triggered manually, main path fails"**: Incorrect
   - Manual execution with `{"report_date": "..."}` works perfectly (Path A)
   - Manual execution with `{}` uses today (Path B)
   - Neither "fails" - they're just different inputs

---

### Correct Mental Model

**Simple If/Else Logic**:

```
Lambda receives event
    ↓
Does event have 'report_date' key?
    ├─ YES → Use that date (Path A)
    └─ NO  → Use today (Path B)
    ↓
Query Aurora with chosen date
```

**Not**:
```
Lambda receives event
    ↓
Try to extract date from EventBridge envelope (Main Path)
    ├─ SUCCESS → Use extracted date
    └─ FAILURE → Fall back to today (Default Path)
```

---

### Why This Matters

**Your mental model implies**:
- EventBridge integration is "broken" (main path fails)
- There's attempted extraction logic that doesn't work
- Default path is a "fallback" for failures

**Actual situation**:
- EventBridge integration works correctly (just doesn't pass date)
- There's no extraction attempt (simple key lookup)
- Default path is intentional design (not a fallback)

**Real problem**:
- EventBridge doesn't pass `report_date` key (missing input transformation)
- PDF workflow defaults to today (which happens to be correct for daily scheduler)
- This is a **configuration gap**, not a "path failure"

---

## Recommendations

### 1. Update Mental Model

**Old mental model** (incorrect):
- Main path: Extract from EventBridge → Fails
- Fallback path: Use today → Works

**New mental model** (correct):
- If `report_date` provided → Use it
- If `report_date` not provided → Use today
- Both are valid, no failures

---

### 2. Understand the Real Issue

**Issue**: EventBridge doesn't pass `report_date` to PDF workflow

**Not because**: Extraction fails
**But because**: EventBridge target has no `input_transformer` configured

**Fix**: Add input transformation in Terraform (not in Lambda code)

---

### 3. Terminology Clarification

**Better terminology**:
- **Path A**: Explicit date mode (event contains `report_date`)
- **Path B**: Auto-detect date mode (defaults to today)

**Avoid**:
- "Main path" / "Default path" (implies hierarchy)
- "Extraction" / "Parsing" (doesn't exist in code)
- "Failure" / "Fallback" (no failures occur)

---

## Confidence Level: **Very High** (100%)

**Reasoning**:
- ✅ Code reviewed directly (source of truth)
- ✅ Execution logs confirm behavior (production evidence)
- ✅ No extraction logic exists in codebase
- ✅ Simple if/else conditional verified
- ✅ No exceptions or try/catch for "failed extraction"

---

## Summary

**Claim Status**: ❌ **FALSE**

**What's Correct**:
- ✅ Two different behaviors exist (explicit date vs today)
- ✅ EventBridge execution uses today's date
- ✅ Manual execution can provide explicit date

**What's Incorrect**:
- ❌ No "main path" that extracts from EventBridge envelope
- ❌ No "failure" of extraction
- ❌ No "fallback" to default path
- ❌ Simple if/else, not two separate code paths

**Correct Understanding**:
```python
# Simple conditional logic
if 'report_date' in event:
    use_provided_date()  # Works for manual execution
else:
    use_today()          # Works for EventBridge (no date provided)
```

**Real Problem**:
EventBridge target missing `input_transformer` configuration (Terraform issue, not Lambda code issue).

---

## Next Steps

- [ ] Update understanding: No extraction, just key lookup
- [ ] Fix real issue: Add EventBridge input transformation in Terraform
- [ ] Test tomorrow's 08:00 automatic run (should work because today = correct date)
- [ ] Consider explicit date passing for better reliability

---

## References

**Code**:
- `src/scheduler/get_report_list_handler.py:66-77` - Actual implementation

**Validation**:
- `.claude/validations/2026-01-04-nightly-scheduler-workflow-chain.md` - Original analysis

**Infrastructure**:
- `terraform/pdf_workflow.tf:446-451` - EventBridge target (missing input_transformer)
