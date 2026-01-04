# Validation Report: PDF Generation Fallback Behavior

**Claim**: "Should we remove the fallback path for PDF generation that uses today's date and instead terminate when date is not provided?"

**Type**: `behavior` (Application design decision)

**Date**: 2026-01-05 15:30

---

## Status: ✅ YES - Remove Fallback, Fail Fast

The fallback to "today's date" should be **REMOVED**. With EventBridge input_transformer implemented, the fallback path is now a code smell that hides configuration issues and violates defensive programming principles.

---

## Evidence Summary

### Supporting Evidence for REMOVAL (6 items)

#### 1. **Principle #1: Defensive Programming**

**Source**: `.claude/CLAUDE.md` - Core Principles

**Finding**:

> "Fail fast and visibly when something is wrong. Silent failures hide bugs. Validate configuration at startup, not on first use."

**Application to fallback**:
- ❌ Fallback = silent failure (WARNING log easily missed)
- ✅ Termination = visible failure (Lambda error, alarms trigger)
- ❌ Fallback executes with wrong date (produces incorrect PDFs)
- ✅ Termination prevents data corruption (no PDFs for wrong date)

**Evidence**:
```python
# CURRENT (BAD - Silent fallback)
else:
    report_date = datetime.now(bangkok_tz).date()
    logger.warning(
        f"⚠️ No report_date in event, using today's Bangkok date: {report_date}"
    )
    # Continues execution with potentially wrong date

# RECOMMENDED (GOOD - Fail fast)
else:
    raise ValueError(
        "Missing required report_date in event. "
        "EventBridge input_transformer should provide this. "
        "Check EventBridge rule configuration."
    )
```

**Confidence**: Very High (principle directly addresses this pattern)

---

#### 2. **EventBridge Input Transformer Now Implemented**

**Source**: `terraform/pdf_workflow.tf:445-464` (just implemented)

**Finding**:

EventBridge input_transformer will **ALWAYS** provide `report_date` when triggered by precompute completion:

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

**Implication**:
- ✅ Automatic triggers (nightly scheduler): `report_date` ALWAYS present
- ❓ Manual triggers: Should explicitly provide `report_date` (test what you deploy)

**Evidence**: With input_transformer, the fallback path becomes **UNREACHABLE** in normal operation.

**Confidence**: Very High (infrastructure guarantees input)

---

#### 3. **Manual Execution Should Be Explicit**

**Source**: Current behavior analysis

**Finding**:

Manual execution currently takes two paths:

**Path 1: Implicit (BAD)**:
```bash
# No date provided → fallback to today
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:pdf-workflow \
  --input '{}'
# Uses TODAY (could be wrong date for testing historical reports)
```

**Path 2: Explicit (GOOD)**:
```bash
# Date explicitly provided
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:pdf-workflow \
  --input '{"report_date": "2026-01-04"}'
# Uses SPECIFIED date (exactly what you intend)
```

**Problem with fallback**:
- Developer intends to test Jan 4 PDFs
- Forgets to pass `report_date`
- Lambda silently uses Jan 5 (today)
- Developer sees PDFs generated, assumes Jan 4 worked
- ❌ **False positive** - wrong date, no error

**Without fallback**:
- Developer forgets to pass `report_date`
- Lambda raises ValueError
- Developer immediately sees error, adds `report_date`
- ✅ **Fail fast** - explicit error, correct usage enforced

**Confidence**: High (defensive programming best practice)

---

#### 4. **Observability Argument: Errors > Warnings**

**Source**: Principle #18 (Logging Discipline)

**Finding**:

**Current fallback behavior**:
```
⚠️ No report_date in event, using today's Bangkok date: 2026-01-05
✅ Found 46 reports needing PDFs
```

**Problem**:
- WARNING log buried in normal execution logs
- No alarm triggered (WARNING ≠ ERROR)
- Developer doesn't notice misconfiguration
- PDFs generated for wrong date

**Recommended fail-fast behavior**:
```
❌ Missing required report_date in event
ERROR: ValueError: Missing required report_date in event
Lambda execution failed
```

**Benefits**:
- ✅ CloudWatch alarm triggers on Lambda error
- ✅ Step Function execution shows FAILED status
- ✅ Developer immediately investigates
- ✅ No incorrect PDFs generated

**Evidence**: Errors are more observable than warnings.

**Confidence**: High (operational best practice)

---

#### 5. **Type of Error: Configuration vs Runtime**

**Source**: Error classification analysis

**Finding**:

Missing `report_date` is a **CONFIGURATION ERROR**, not a runtime error.

**Configuration errors** (developer mistake):
- Missing environment variable
- Missing required event field
- Wrong IAM permissions
- **Should fail loudly** (crash Lambda, trigger alarms)

**Runtime errors** (external system failure):
- Aurora connection timeout
- S3 bucket not found
- API rate limit exceeded
- **Might warrant retry/fallback** (transient issues)

**Current fallback treats configuration error as runtime error**:
- ❌ Silently recovers from developer mistake
- ❌ Hides infrastructure misconfiguration
- ❌ Produces incorrect output instead of failing

**Recommended approach**: Treat missing `report_date` as configuration error
- ✅ Fail immediately with descriptive error
- ✅ Forces developer to fix configuration
- ✅ Prevents wrong data from being generated

**Confidence**: Very High (error classification best practice)

---

#### 6. **Real-World Scenario Analysis**

**Source**: Operational reasoning

**Scenario 1: EventBridge misconfiguration**

**With fallback**:
1. Developer accidentally breaks EventBridge input_transformer (typo in Terraform)
2. Deploy to production
3. Nightly scheduler triggers at 8 AM Bangkok
4. Lambda falls back to "today's date"
5. Generates PDFs for WRONG date (one day behind)
6. Users receive incorrect reports
7. **Issue discovered hours later** when user complains

**Without fallback**:
1. Developer accidentally breaks EventBridge input_transformer
2. Deploy to production
3. Nightly scheduler triggers at 8 AM Bangkok
4. Lambda raises ValueError
5. CloudWatch alarm triggers
6. Developer investigates IMMEDIATELY
7. **Issue discovered within minutes**, no incorrect data

**Scenario 2: Manual testing**

**With fallback**:
1. Developer wants to regenerate Jan 4 PDFs
2. Runs manual trigger, forgets `report_date`
3. Lambda uses Jan 5 (today)
4. Sees 46 PDFs generated
5. Assumes Jan 4 worked
6. **False positive** - tested wrong date

**Without fallback**:
1. Developer wants to regenerate Jan 4 PDFs
2. Runs manual trigger, forgets `report_date`
3. Lambda raises ValueError
4. Developer adds `--input '{"report_date": "2026-01-04"}'`
5. Runs again, generates correct PDFs
6. **Correct test** - verified what will actually deploy

**Evidence**: Fallback creates **silent failures** in both scenarios.

**Confidence**: Very High (operational analysis)

---

### Contradicting Evidence for KEEPING fallback (1 item)

#### 1. **Graceful Degradation Argument**

**Source**: General resilience principle

**Argument**:
- Systems should degrade gracefully, not crash
- Providing a "best guess" (today's date) is better than failing
- Users get some PDFs instead of no PDFs

**Counter-argument**:
- ❌ **Wrong PDFs are WORSE than no PDFs** (data corruption vs service outage)
- ❌ Graceful degradation applies to **runtime errors** (transient), not **configuration errors** (permanent)
- ❌ "Today's date" is not a reasonable default (could be any date from last successful run)
- ✅ Fail-fast prevents incorrect data from entering system

**Confidence**: Low (graceful degradation doesn't apply to configuration errors)

---

### Missing Evidence

**What we couldn't verify**:
- Historical incidents where fallback saved production (no evidence found)
- User requirements for "always generate something" (no documented requirement)

**How to get it**:
- Check incident logs for fallback triggering in production
- Ask stakeholders if "no PDFs" is acceptable when date missing

---

## Analysis

### Overall Assessment

**The fallback to "today's date" is a code smell that should be removed.**

**Why it exists** (historical context):
- Likely implemented before EventBridge input_transformer
- Defensive coding: "better to generate something than crash"
- Manual testing convenience: don't have to specify date every time

**Why it should be removed** (current reality):
1. **EventBridge now guarantees input** (input_transformer provides report_date)
2. **Fallback hides configuration bugs** (silently uses wrong date)
3. **Violates Principle #1** (fail fast, not silent fallback)
4. **Wrong data worse than no data** (incorrect PDFs vs service outage)
5. **Manual execution should be explicit** (test what you deploy)

---

### Key Findings

**Finding 1: Fallback is unreachable in normal operation**

With input_transformer implemented, EventBridge will **always** provide `report_date`. The fallback only triggers when:
- Manual execution without `report_date` (developer mistake)
- EventBridge misconfiguration (infrastructure bug)

Both cases should **fail loudly**, not silently recover.

---

**Finding 2: Silent fallback creates false positives**

Developer mistakes (forgot `report_date`) result in:
- ❌ Execution succeeds (wrong date)
- ❌ PDFs generated (for today, not intended date)
- ❌ No error visible (just WARNING log)
- ❌ Developer assumes success

**This is worse than a crash** because it produces incorrect data.

---

**Finding 3: Configuration errors should fail fast**

Missing `report_date` is a **configuration error** (developer/infrastructure mistake), not a **runtime error** (transient failure).

Configuration errors should:
- ✅ Crash immediately (don't silently recover)
- ✅ Trigger alarms (CloudWatch errors)
- ✅ Force investigation (visible failure)
- ✅ Prevent bad data (no PDFs for wrong date)

---

### Confidence Level: **Very High** (95%)

**Reasoning**:
1. ✅ Principle #1 explicitly forbids silent fallbacks
2. ✅ EventBridge input_transformer guarantees input in normal operation
3. ✅ Manual execution should be explicit (defensive programming)
4. ✅ Wrong data worse than no data (data integrity principle)
5. ✅ Errors more observable than warnings (operational principle)

**Why not 100%**: Theoretical edge case where stakeholder requirement is "always generate PDFs no matter what" (not documented, unlikely).

---

## Recommendations

### ✅ Claim is TRUE → Remove Fallback, Implement Fail-Fast

**Implementation**:

**BEFORE (current code with fallback)**:
```python
report_date_str = event.get('report_date')
bangkok_tz = ZoneInfo("Asia/Bangkok")

if report_date_str:
    if 'T' in report_date_str:
        # ISO8601 from EventBridge
        dt_utc = datetime.fromisoformat(report_date_str.replace('Z', '+00:00'))
        dt_bangkok = dt_utc.astimezone(bangkok_tz)
        report_date = dt_bangkok.date()
    else:
        # Date-only from manual
        report_date = date.fromisoformat(report_date_str)
else:
    # ❌ FALLBACK (BAD)
    report_date = datetime.now(bangkok_tz).date()
    logger.warning(f"⚠️ No report_date in event, using today: {report_date}")
```

**AFTER (recommended fail-fast)**:
```python
report_date_str = event.get('report_date')

if not report_date_str:
    # ✅ FAIL FAST (GOOD)
    raise ValueError(
        "Missing required 'report_date' in event. "
        "EventBridge input_transformer should provide this automatically. "
        "For manual execution, provide explicit date: "
        "{\"report_date\": \"2026-01-04\"}"
    )

bangkok_tz = ZoneInfo("Asia/Bangkok")

if 'T' in report_date_str:
    # ISO8601 from EventBridge (UTC)
    dt_utc = datetime.fromisoformat(report_date_str.replace('Z', '+00:00'))
    dt_bangkok = dt_utc.astimezone(bangkok_tz)
    report_date = dt_bangkok.date()
    logger.info(
        f"✅ Using report_date from EventBridge: {report_date} "
        f"(UTC: {report_date_str}, Bangkok: {dt_bangkok.strftime('%Y-%m-%d %H:%M:%S %Z')})"
    )
else:
    # Date-only from manual execution
    report_date = date.fromisoformat(report_date_str)
    logger.info(f"✅ Using report_date from manual input: {report_date}")
```

---

### Benefits of Fail-Fast Implementation

**1. Prevents Data Corruption**:
- No PDFs generated for wrong date
- No false positives in testing

**2. Improves Observability**:
- CloudWatch alarms trigger on Lambda error
- Step Function shows FAILED status (not SUCCESS with hidden warning)

**3. Forces Correct Usage**:
- Manual execution must be explicit
- Infrastructure misconfiguration caught immediately

**4. Aligns with Principles**:
- ✅ Principle #1: Fail fast and visibly
- ✅ Principle #2: Progressive evidence strengthening (error is stronger signal than warning)
- ✅ Principle #15: Infrastructure-application contract (validate inputs at boundary)

---

### Migration Path

**Step 1: Update Lambda handler** (remove fallback)
- Change `else:` block to `raise ValueError`
- Add descriptive error message

**Step 2: Update manual execution docs**
- Document required `report_date` parameter
- Provide example commands

**Step 3: Deploy to dev**
- Test automatic trigger (EventBridge → should work)
- Test manual trigger without date (should fail with clear error)
- Test manual trigger with date (should work)

**Step 4: Monitor first production run**
- Verify EventBridge provides date correctly
- Verify no fallback path triggered

---

## Next Steps

- [x] Validate claim: Should fallback be removed? ✅ YES
- [ ] Update Lambda handler to remove fallback (HIGH priority)
- [ ] Update manual execution documentation
- [ ] Deploy to dev and verify fail-fast behavior
- [ ] Add test case for missing report_date (should raise ValueError)

---

## References

**Principles**:
- [Principle #1: Defensive Programming](.claude/CLAUDE.md#1-defensive-programming)
- [Principle #2: Progressive Evidence Strengthening](.claude/CLAUDE.md#2-progressive-evidence-strengthening)
- [Principle #15: Infrastructure-Application Contract](.claude/CLAUDE.md#15-infrastructure-application-contract)
- [Principle #18: Logging Discipline](.claude/CLAUDE.md#18-logging-discipline-storytelling-pattern)

**Related Validations**:
- [Input Transformer Timezone Config](.claude/validations/2026-01-05-input-transformer-timezone-config.md) - Confirmed Lambda must handle timezone conversion
- [PDF Generation Two-Path Understanding](.claude/validations/2026-01-04-pdf-generation-two-path-understanding.md) - Identified the two execution paths

**Code References**:
- `src/scheduler/get_report_list_handler.py:90-95` - Current fallback implementation (to be removed)
- `terraform/pdf_workflow.tf:445-464` - EventBridge input_transformer (guarantees input)

---

## Summary

**Claim**: "Should we remove the fallback path for PDF generation that uses today's date?"

**Status**: ✅ **YES - Remove Fallback**

**Evidence**:
- Principle #1 forbids silent fallbacks (fail fast)
- EventBridge input_transformer guarantees input
- Manual execution should be explicit (no implicit defaults)
- Wrong PDFs worse than no PDFs (data integrity)
- Errors more observable than warnings (operational)

**Implication**:
Remove the `else:` fallback block and raise `ValueError` when `report_date` missing.

**Action required**:
Update Lambda handler to fail fast when report_date missing (remove lines 90-95).

**Confidence**: 95% (Very High)
