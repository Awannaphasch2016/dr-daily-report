# Validation Report: Terraform Update Required for Precompute Fix

**Claim**: "Given the error we found, do we have to update terraform at all?"

**Type**: `code` + `config` (infrastructure configuration)

**Date**: 2026-01-05

---

## Status: ❌ NO - Terraform Already Correct

Terraform does **NOT** need updating. The Step Functions definition already has the correct `"source"` field. The issue was the Lambda function using an **old Docker image**.

---

## Evidence Summary

### Evidence AGAINST needing Terraform update (3 items)

#### 1. **Terraform Step Functions Definition Already Correct**

**Source**: `terraform/step_functions/precompute_workflow.json:36-41`

**Finding**:
```json
"Payload": {
  "ticker.$": "$.ticker",
  "execution_id.$": "$.execution_id",
  "source": "step_functions_precompute"  // ✅ Already present
}
```

**Location**: Line 40

**Confidence**: **Very High** - Direct code inspection confirms field exists

---

#### 2. **Lambda Handler Expects Matching Source Value**

**Source**: `src/report_worker_handler.py:127`

**Finding**:
```python
# Step Functions invocation mode (for precompute workflow)
# Event structure: {'ticker': 'YYY', 'source': 'precompute'}
# NOTE: No job_id field (distinguishes from direct invocation)
if 'ticker' in event and 'source' in event:
    logger.info(f"Step Functions invocation: {event.get('ticker')}")
    result = asyncio.run(process_ticker_direct(event))
    return result
```

**Issue**: Handler expects `'source': 'precompute'` but Terraform sends `'source': 'step_functions_precompute'`

**Implication**: There's a **name mismatch**, but **NOT a missing field**

**Confidence**: **Very High** - Both configurations exist, just different values

---

#### 3. **Precompute Workflow Actually Succeeded After Lambda Update**

**Source**: AWS Step Functions execution history

**Finding**:
- **Execution ARN**: `arn:aws:states:...:execution:dr-daily-report-precompute-workflow-dev:115bc701-ad2b-40c0-8869-4d86a0f613a0`
- **Status**: `SUCCEEDED` ✅
- **Duration**: 33 seconds
- **Timestamp**: 2026-01-05 03:41:56 → 03:42:29

**Action Taken**: Updated `report_worker` Lambda to new Docker image (`input-transformer-20260105-031311`)

**Result**: Workflow succeeded **without any Terraform changes**

**Confidence**: **Very High** - Actual production evidence that fix worked

---

### Supporting Evidence (What Was Actually Wrong)

#### **Root Cause: Stale Lambda Docker Image**

**Source**: Lambda function configuration

**Finding**:
- **Before fix**: Lambda used old image without updated handler code
- **After fix**: Lambda updated to `input-transformer-20260105-031311`
- **Terraform**: Already had correct `"source"` field configured

**Evidence**:
```bash
# What we did to fix:
aws lambda update-function-code \
  --function-name dr-daily-report-report-worker-dev \
  --image-uri 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:input-transformer-20260105-031311
```

**No Terraform changes made** ✅

---

## Analysis

### Overall Assessment

**Terraform does NOT need updating.** The original bug hunt analysis was **partially incorrect** in its diagnosis.

**What we thought**:
- Bug hunt report suggested: "Add `'source': 'precompute'` to Map state Parameters"
- Hypothesis: Terraform missing the `'source'` field

**What was actually true**:
- ✅ Terraform **already had** `"source": "step_functions_precompute"` (line 40)
- ❌ Lambda was using **old Docker image** without updated handler code
- ✅ Updating Lambda image **fixed the issue** (no Terraform changes)

---

### Key Findings

**Finding 1: Terraform Configuration Was Already Correct**

The Step Functions definition at `terraform/step_functions/precompute_workflow.json:40` already includes:
```json
"source": "step_functions_precompute"
```

This field was **not missing**. The infrastructure was correctly configured.

---

**Finding 2: Minor Name Mismatch (But Not the Root Cause)**

There's a **name mismatch** between what Terraform sends vs what Lambda expects:
- Terraform sends: `"source": "step_functions_precompute"`
- Lambda expects: `'source': 'precompute'` (per handler comment)

However, this mismatch was **NOT the root cause** because:
1. The actual Lambda code checks: `if 'ticker' in event and 'source' in event:`
2. It checks for **existence** of `'source'` field, not the **value**
3. As long as `'source'` exists (with any truthy value), detection succeeds

---

**Finding 3: Actual Root Cause Was Stale Lambda Image**

The real issue:
1. Lambda function was using **old Docker image**
2. Old image had outdated handler code
3. Handler couldn't properly process Step Functions invocations
4. Updating Lambda to new image **immediately fixed the problem**

**Proof**: Precompute workflow succeeded after Lambda update, **zero Terraform changes**.

---

### Confidence Level: **Very High** (95%)

**Reasoning**:
1. ✅ Direct code inspection shows `"source"` field exists in Terraform (line 40)
2. ✅ Workflow succeeded after Lambda update (production evidence)
3. ✅ No Terraform changes were made during successful fix
4. ✅ CloudWatch logs confirm correct event structure received by Lambda

**Why not 100%**: Theoretically, there could be edge cases in how Step Functions processes the `Payload` block, but production success proves current configuration works.

---

## Recommendations

### ✅ Claim is FALSE → No Terraform Update Needed

**Current state**: Terraform configuration is **correct as-is**

**What to do**:
1. ✅ **Keep Terraform unchanged** - Configuration already correct
2. ⚠️ **Optional: Standardize naming** - Consider changing Terraform to `"source": "precompute"` for consistency with Lambda comment, but **NOT required**
3. ✅ **Document finding** - Update bug hunt report to correct the misdiagnosis

---

### Optional Improvement: Name Consistency (Low Priority)

**If you want naming consistency** (Terraform matches Lambda comments):

**Before** (current, working):
```json
// terraform/step_functions/precompute_workflow.json:40
"source": "step_functions_precompute"
```

**After** (optional standardization):
```json
"source": "precompute"
```

**Benefits**:
- Matches Lambda handler comment expectations
- Clearer intent (source is "precompute workflow")

**Risks**:
- **None** - Lambda checks for field existence, not value
- No behavior change

**Priority**: **P3** (nice-to-have, not urgent)

---

### Correcting the Bug Hunt Report

**Original bug hunt diagnosis** (`.claude/bug-hunts/2026-01-05-precompute-workflow-checkworkersuccess-failure.md`):

**Incorrect conclusion**:
> "Step Functions Map state doesn't pass required `'source': 'precompute'` field"

**Correct conclusion**:
> "Lambda function was using stale Docker image without updated handler code. Terraform configuration was already correct."

**Recommended action**: Add addendum to bug hunt report clarifying the actual root cause.

---

## Next Steps

- [x] ~~Update Terraform~~ - **NOT NEEDED**
- [x] Update Lambda Docker image - **COMPLETED** ✅
- [x] Verify precompute workflow - **SUCCEEDED** ✅
- [ ] **Optional**: Standardize `"source"` value to `"precompute"` for consistency
- [ ] Add addendum to bug hunt report correcting diagnosis
- [ ] Document lesson learned: "Verify infrastructure state before assuming misconfiguration"

---

## References

**Terraform Configuration**:
- `terraform/step_functions/precompute_workflow.json:36-41` - Correct `"source"` field configuration

**Lambda Handler**:
- `src/report_worker_handler.py:127` - Step Functions mode detection logic

**Production Evidence**:
- Execution ARN: `arn:aws:states:ap-southeast-1:755283537543:execution:dr-daily-report-precompute-workflow-dev:115bc701-ad2b-40c0-8869-4d86a0f613a0`
- Status: `SUCCEEDED`
- No Terraform changes made

**Bug Hunt Report** (needs correction):
- `.claude/bug-hunts/2026-01-05-precompute-workflow-checkworkersuccess-failure.md`

---

## Lesson Learned

**Principle**: "Verify infrastructure state before assuming misconfiguration"

When debugging infrastructure issues:
1. ✅ **Check actual deployed state first** (read Terraform files, query AWS)
2. ✅ **Verify application code version** (Docker image tags, Lambda configuration)
3. ❌ **Don't assume infrastructure is wrong** without evidence

In this case:
- We assumed Terraform was missing `'source'` field
- Reality: Terraform was correct, Lambda image was stale
- Lesson: Always verify infrastructure **before** assuming it needs changes

---

## Summary

**Claim**: "Do we have to update Terraform at all?"

**Answer**: **NO** ❌

**Reasoning**:
1. Terraform already has `"source": "step_functions_precompute"` field (line 40)
2. Precompute workflow succeeded after **Lambda update only**
3. Zero Terraform changes were required to fix the issue
4. Root cause was **stale Lambda Docker image**, not Terraform misconfiguration

**Confidence**: Very High (95%)

**Action**: No Terraform update needed. Optionally standardize naming for consistency (P3 priority).
