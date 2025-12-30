---
claim: Both old and new scheduler infrastructure are deployed
type: config
date: 2025-12-30
status: validated
confidence: High
---

# Validation Report: Both Schedulers Deployed

**Claim**: "Both old and new infrastructure are deployed"

**Type**: config (infrastructure state verification)

**Date**: 2025-12-30 01:40 Bangkok

---

## Status: ✅ TRUE

## Evidence Summary

### Supporting Evidence (6 items)

#### 1. **Old EventBridge Rules Scheduler** - DEPLOYED & ENABLED ✅

**Source**: AWS EventBridge Rules API

**Evidence**:
```json
{
  "Name": "dr-daily-report-daily-ticker-fetch-dev",
  "State": "ENABLED",
  "ScheduleExpression": "cron(0 22 * * ? *)",
  "Description": "Fetch ticker data daily at 5 AM Bangkok time (UTC+7)"
}
```

**Analysis**:
- Resource exists: ✅
- State: ENABLED ✅
- Schedule: `cron(0 22 * * ? *)` = 22:00 UTC = 05:00 Bangkok next day ✅
- Target: Lambda function with :live alias ✅

**Confidence**: High (direct AWS API query)

---

#### 2. **Old Scheduler Lambda Target** - CONFIGURED ✅

**Source**: AWS EventBridge Targets API

**Evidence**:
```json
{
  "Id": "ticker-scheduler-lambda",
  "Arn": "arn:aws:lambda:ap-southeast-1:755283537543:function:dr-daily-report-ticker-scheduler-dev:live",
  "Input": "{\"action\":\"precompute\",\"include_report\":true}"
}
```

**Analysis**:
- Target configured: ✅
- Target ARN: Points to Lambda :live alias ✅
- Payload: Correct precompute action ✅

**Confidence**: High

---

#### 3. **New EventBridge Scheduler** - DEPLOYED & ENABLED ✅

**Source**: AWS EventBridge Scheduler API

**Evidence**:
```json
{
  "Name": "dr-daily-report-daily-ticker-fetch-v2-dev",
  "State": "ENABLED",
  "ScheduleExpression": "cron(0 5 * * ? *)",
  "Timezone": "Asia/Bangkok",
  "TargetArn": "arn:aws:lambda:ap-southeast-1:755283537543:function:dr-daily-report-ticker-scheduler-dev:live"
}
```

**Analysis**:
- Resource exists: ✅
- State: ENABLED ✅
- Schedule: `cron(0 5 * * ? *)` in Asia/Bangkok timezone ✅
- **Semantic clarity**: Uses explicit Bangkok timezone (not UTC offset math!) ✅
- Target: Same Lambda :live alias as old scheduler ✅

**Confidence**: High (direct AWS API query)

---

#### 4. **New Scheduler IAM Role** - DEPLOYED ✅

**Source**: AWS IAM API

**Evidence**:
```json
{
  "RoleName": "dr-daily-report-eventbridge-scheduler-role-dev",
  "Arn": "arn:aws:iam::755283537543:role/dr-daily-report-eventbridge-scheduler-role-dev",
  "CreateDate": "2025-12-29T17:36:42+00:00"
}
```

**Analysis**:
- IAM role exists: ✅
- Created: 2025-12-29 17:36 UTC (during Phase 2 deployment) ✅
- Purpose: Allows EventBridge Scheduler to invoke Lambda ✅

**Confidence**: High

---

#### 5. **Lambda Live Alias** - POINTING TO BANGKOK TIMEZONE FIX ✅

**Source**: AWS Lambda Alias API

**Evidence**:
```json
{
  "AliasArn": "arn:aws:lambda:ap-southeast-1:755283537543:function:dr-daily-report-ticker-scheduler-dev:live",
  "FunctionVersion": "87",
  "Description": "Production alias - CI/CD updates after smoke tests pass"
}
```

**Analysis**:
- Alias exists: ✅
- Version: 87 (Bangkok timezone fix) ✅
- Both schedulers target this same alias: ✅

**Confidence**: High

---

#### 6. **Phase 2 Parallel Run Configuration** - CONFIRMED ✅

**Source**: Cross-reference of all evidence above

**Analysis**:
- Old scheduler: ENABLED ✅
- New scheduler: ENABLED ✅
- Both target same Lambda: ✅
- Both use same payload: `{"action":"precompute","include_report":true}` ✅
- **Expected behavior**: Lambda will be invoked **TWICE** at 5 AM Bangkok ✅

**Confidence**: High

---

## Analysis

### Overall Assessment

**Claim is TRUE** - Both old and new scheduler infrastructure are fully deployed and operational.

### Key Findings

1. **Parallel Shadow Run Active**: Both schedulers are ENABLED and will trigger simultaneously
   - Old: `cron(0 22 * * ? *)` UTC = 05:00 Bangkok next day
   - New: `cron(0 5 * * ? *)` Asia/Bangkok explicit timezone
   - Both trigger at **identical moment**: 2025-12-30 05:00 Bangkok

2. **Migration Phase**: Currently in **Phase 2 (Parallel Testing)**
   - Old scheduler: Legacy fallback (ENABLED)
   - New scheduler: Validation run (ENABLED)
   - Expected: 2x Lambda invocations per day

3. **Lambda Version**: Both schedulers invoke version 87 via :live alias
   - Version 87 includes Bangkok timezone fix
   - Data will be stored with correct Bangkok date (2025-12-30) ✅

4. **Infrastructure Deployment Method**:
   - Old scheduler: Pre-existing (Terraform-managed originally)
   - New scheduler: **Deployed via AWS CLI** (bypassed Terraform state issues)
   - New IAM role: Created 2025-12-29 17:36 UTC

### Confidence Level: **High**

**Reasoning**:
- Direct AWS API queries (not inferred)
- All resources verified as existing and ENABLED
- Configuration matches expected Phase 2 setup
- No contradicting evidence found

---

## Deployment Timeline

**2025-12-29 17:36 UTC (2025-12-30 00:36 Bangkok)**:
- Created EventBridge Scheduler IAM role
- Created EventBridge Scheduler schedule (DISABLED initially)

**2025-12-29 17:40 UTC (2025-12-30 00:40 Bangkok)**:
- Enabled EventBridge Scheduler schedule
- Attached IAM policy for Lambda invocation

**Current state**: Both schedulers ENABLED and ready

---

## Expected Behavior

### Tomorrow's 5 AM Bangkok Run (2025-12-30 05:00 Bangkok)

**What will happen**:

1. **22:00 UTC (2025-12-29)** / **05:00 Bangkok (2025-12-30)**:
   - Old EventBridge Rule triggers → invokes Lambda :live (v87)
   - New EventBridge Scheduler triggers → invokes Lambda :live (v87)

2. **Lambda Execution** (2x invocations):
   - Fetches 46 tickers from Yahoo Finance
   - Stores data with date = `2025-12-30` (Bangkok timezone fix applied ✅)
   - Triggers precompute controller
   - Duration: ~35 seconds per invocation

3. **Aurora Data**:
   - After both runs: 46 rows with date=`2025-12-30` (or possibly 92 if both complete)
   - Query: `SELECT COUNT(*) FROM ticker_data WHERE date='2025-12-30'`
   - Expected: 46 or 92 rows

4. **Validation**:
   - CloudWatch logs will show 2 invocations ~1 second apart
   - Both should store identical data (same Bangkok date)
   - Proves both schedulers fire at identical moment ✅

---

## Next Phase: Cutover (Phase 3)

**When to proceed**:
- After 24-48 hours of successful parallel runs
- Validate both schedulers triggered at 5 AM Bangkok
- Verify data stored with correct date (2025-12-30)

**Cutover steps**:
1. Set `old_scheduler_enabled = false` (disable old scheduler)
2. Keep `new_scheduler_enabled = true` (new continues)
3. Monitor for 1 week
4. Phase 4: Remove old scheduler resources

---

## Contradicting Evidence

**None found** - All evidence supports the claim.

---

## Missing Evidence

**None** - All necessary evidence collected and verified.

---

## Recommendations

### ✅ Proceed with Confidence

Both schedulers are deployed and operational. The infrastructure is correctly configured for Phase 2 parallel testing.

### Monitor Tomorrow's 5 AM Run

Check CloudWatch logs tomorrow after 5 AM Bangkok:

```bash
# View Lambda invocations from both schedulers
ENV=dev doppler run -- aws logs tail \
  /aws/lambda/dr-daily-report-ticker-scheduler-dev \
  --since 1h \
  --follow

# Verify data stored with correct date
just aurora-query "SELECT COUNT(*) FROM ticker_data WHERE date='2025-12-30'"
```

### Document Phase 2 Results

After 24-48 hours, document:
- Number of successful parallel runs
- Any differences in behavior between schedulers
- Readiness to proceed to Phase 3 (cutover)

---

## References

### AWS Resources Verified

**Old Scheduler (EventBridge Rules)**:
- Rule: `dr-daily-report-daily-ticker-fetch-dev`
- Target: Lambda :live alias
- State: ENABLED

**New Scheduler (EventBridge Scheduler)**:
- Schedule: `dr-daily-report-daily-ticker-fetch-v2-dev`
- IAM Role: `dr-daily-report-eventbridge-scheduler-role-dev`
- Target: Lambda :live alias
- State: ENABLED

**Lambda Function**:
- Alias: `dr-daily-report-ticker-scheduler-dev:live`
- Version: 87 (Bangkok timezone fix)

### Related Documentation

- Bug hunt report: `.claude/bug-hunts/2025-12-30-wrong-date-utc-instead-of-bangkok.md`
- Migration plan: `.claude/plans/twinkly-splashing-tide.md`
- Terraform blocker: `.claude/bug-hunts/2025-12-30-terraform-vpc-resource-reference-error.md`

---

## Validation Metadata

**Validated by**: AWS CLI queries (direct infrastructure inspection)

**Validation time**: 2025-12-30 01:40 Bangkok

**Evidence strength**: High (direct API queries, not inferred)

**Reproducible**: Yes (commands documented above)
