---
title: "What-if: Cutover to new EventBridge Scheduler (Phase 3)"
scenario_type: modification
date: 2025-12-30
status: planned
confidence: High
---

# What-If Analysis: Cutover to New EventBridge Scheduler (Phase 3)

**Assumption**: "If the new scheduler works, proceed to cutover to new scheduler"

**Type**: Configuration change (modification)

**Date**: 2025-12-30 02:00 Bangkok

---

## Current Reality (Phase 2: Parallel Shadow Run)

**Current Configuration**:
- **Old EventBridge Rule**: ENABLED (`dr-daily-report-daily-ticker-fetch-dev`)
- **New EventBridge Scheduler**: ENABLED (`dr-daily-report-daily-ticker-fetch-v2-dev`)
- **Both target**: Lambda :live alias (version 87 with Bangkok timezone fix)
- **Expected behavior**: 2x Lambda invocations per day at 5 AM Bangkok

**Sources**:
- terraform/scheduler.tf:178: `state = var.old_scheduler_enabled ? "ENABLED" : "DISABLED"`
- terraform/scheduler.tf:290: `state = var.new_scheduler_enabled ? "ENABLED" : "DISABLED"`
- .claude/validations/2025-12-30-both-schedulers-deployed.md: Infrastructure validation

**Current State Variables** (inferred from code):
```hcl
# terraform/scheduler.tf behavior suggests:
var.old_scheduler_enabled = true   # Phase 2: Legacy fallback enabled
var.new_scheduler_enabled = true   # Phase 2: New scheduler enabled
```

**Migration Phase Logic** (terraform/scheduler.tf:366-371):
```hcl
output "ticker_scheduler_migration_phase" {
  value = var.old_scheduler_enabled && !var.new_scheduler_enabled ? "phase-1-new-disabled" : (
    var.old_scheduler_enabled && var.new_scheduler_enabled ? "phase-2-parallel" : (
      !var.old_scheduler_enabled && var.new_scheduler_enabled ? "phase-3-cutover" : "phase-4-cleanup"
    )
  )
}
```

**Current Phase**: `phase-2-parallel`

---

## Under New Assumption: Cutover to New Scheduler (Phase 3)

### What Changes Immediately

**Configuration change**:
```hcl
# Before (Phase 2)
var.old_scheduler_enabled = true
var.new_scheduler_enabled = true

# After (Phase 3)
var.old_scheduler_enabled = false  # ⬅️ DISABLE old scheduler
var.new_scheduler_enabled = true   # ⬅️ KEEP new scheduler
```

**Terraform resources affected**:
```hcl
# terraform/scheduler.tf:178
resource "aws_cloudwatch_event_rule" "daily_ticker_fetch" {
  state = var.old_scheduler_enabled ? "ENABLED" : "DISABLED"
  # Will become: state = "DISABLED"
}

# terraform/scheduler.tf:290
resource "aws_scheduler_schedule" "daily_ticker_fetch_v2" {
  state = var.new_scheduler_enabled ? "ENABLED" : "DISABLED"
  # Stays: state = "ENABLED"
}
```

### Cascading Effects

**Level 1 (Direct)**:
- Old EventBridge Rule: ENABLED → DISABLED ✅
- New EventBridge Scheduler: ENABLED (no change) ✅
- Lambda invocations: 2x per day → 1x per day ✅

**Level 2 (Indirect)**:
- CloudWatch logs: Will show only 1 invocation at 5 AM Bangkok ✅
- Aurora data: 46 rows per day (instead of 92 if both completed) ✅
- Precompute jobs: Triggered once per day ✅

**Level 3 (System-wide)**:
- Cost: Slight reduction (1 Lambda invocation instead of 2) ✅
- Migration phase: `phase-2-parallel` → `phase-3-cutover` ✅
- Risk: Single point of failure (no fallback scheduler) ⚠️

### Components Affected

**Terraform Resources**:
- ✅ `aws_cloudwatch_event_rule.daily_ticker_fetch`: State changes to DISABLED
- ✅ `aws_scheduler_schedule.daily_ticker_fetch_v2`: No change (stays ENABLED)
- ✅ Output `ticker_scheduler_migration_phase`: Changes to "phase-3-cutover"

**AWS Infrastructure**:
- ✅ EventBridge Rule disabled (stops triggering)
- ✅ EventBridge Scheduler continues triggering
- ✅ Lambda :live alias (no change, both schedulers used same target)

**Application Behavior**:
- ✅ Ticker data fetched once per day at 5 AM Bangkok
- ✅ Data stored with correct Bangkok date (version 87 fix)
- ✅ Precompute triggered once per day

---

## What Breaks

### Critical Failures

**None identified** - assuming new scheduler works correctly.

**However, if new scheduler fails**:
- ❌ **No fallback scheduler**
  - Impact: Ticker data not fetched, reports unavailable
  - Frequency: If new scheduler fails
  - Severity: High (data pipeline breaks)
  - Workaround: Re-enable old scheduler (`old_scheduler_enabled = true`)
  - Recovery time: ~5 minutes (Terraform apply + wait for next scheduled run)

### Degraded Functionality

**None** - new scheduler provides identical functionality to old scheduler.

---

## What Improves

### Performance Gains

- **Reduced Lambda invocations**
  - Metric: Lambda invocations per day
  - Magnitude: 2x → 1x (50% reduction)
  - Value: Minor cost savings, clearer logs

### Cost Reductions

- **Lambda execution cost**
  - Before: 2 invocations × 35s × $0.0000166667/GB-second × 0.5GB = ~$0.0006/day
  - After: 1 invocation × 35s × $0.0000166667/GB-second × 0.5GB = ~$0.0003/day
  - Savings: ~$0.0003/day × 30 days = ~$0.009/month (negligible)

### Simplifications

- **Semantic timezone clarity**
  - Complexity reduced: No UTC offset mental math
  - Old: `cron(0 22 * * ? *)` in UTC (confusing!)
  - New: `cron(0 5 * * ? *)` in Asia/Bangkok (clear!)
  - Maintenance: Easier (explicit timezone, no DST confusion)

- **Single scheduler architecture**
  - Complexity reduced: 1 scheduler instead of 2 parallel schedulers
  - Logs: Clearer (1 invocation instead of 2)
  - Monitoring: Simpler (1 schedule to track)

---

## Insights Revealed

### Assumptions Exposed

- **New scheduler reliability assumption**
  - Assumed: "New EventBridge Scheduler is reliable"
  - Evidence: Phase 2 parallel runs will validate this
  - Criticality: High (if unreliable, data pipeline breaks)
  - Validation: Monitor Phase 2 for 24-48 hours before cutover

- **No fallback needed assumption**
  - Assumed: "Single scheduler is sufficient (no redundancy needed)"
  - Reality: Old scheduler provided fallback during Phase 2
  - Trade-off: Simplicity vs Redundancy
  - Acceptable: Yes (AWS EventBridge Scheduler has 99.9% SLA)

### Trade-offs Clarified

- **Simplicity vs Redundancy**
  - Original choice: 2 schedulers (redundancy during migration)
  - Phase 3 choice: 1 scheduler (simplicity, semantic clarity)
  - Validated: Yes (after 24-48 hours of successful parallel runs)

- **UTC offset math vs Explicit timezone**
  - Old scheduler: `cron(0 22 * * ? *)` UTC (confusing)
  - New scheduler: `cron(0 5 * * ? *)` Asia/Bangkok (clear)
  - Win: Semantic clarity, DST-proof (Bangkok doesn't use DST)

### Boundary Conditions

- **Minimum validation period: 24-48 hours**
  - Threshold: At least 1-2 successful parallel runs
  - Current margin: Deployed 2025-12-30 00:40 Bangkok, first run at 05:00
  - Safety factor: After 2 days (4 runs), confidence = High

- **Rollback time: ~5 minutes**
  - Threshold: If new scheduler fails, how fast can we recover?
  - Rollback: Set `old_scheduler_enabled = true`, Terraform apply
  - Next run: Wait for next scheduled time (max 24 hours)
  - Mitigation: Manual Lambda invocation (`aws lambda invoke`) for immediate fix

### Design Rationale

**Why cutover after validation**:
1. **Constraint 1**: New scheduler must prove reliability (24-48 hours of successful runs)
2. **Constraint 2**: Semantic clarity is valuable (explicit Bangkok timezone)
3. **Constraint 3**: Simplicity reduces maintenance burden (1 scheduler instead of 2)
4. **Conclusion**: Cutover is beneficial AFTER validation period

**Why NOT cutover immediately**:
- Risk: New scheduler untested in production
- Impact: Data pipeline breaks if new scheduler fails
- Mitigation: Phase 2 parallel run validates reliability first

---

## Recommendation

### Should We Make This Change?

**Decision**: ⚠️ CONDITIONALLY YES

**Rationale**:
Cutover to new scheduler is beneficial for semantic clarity (explicit Bangkok timezone) and simplicity (single scheduler architecture). However, should only proceed AFTER validating new scheduler works correctly in Phase 2 parallel runs.

**Conditions**:
1. ✅ **New scheduler deployed**: Both schedulers currently ENABLED (Phase 2)
2. ⏳ **Validation period complete**: Wait 24-48 hours (1-2 successful runs)
3. ⏳ **No failures observed**: CloudWatch logs show successful invocations
4. ⏳ **Data correctness verified**: Aurora data stored with correct Bangkok dates

### Action Items

**Prerequisites** (Before Cutover):
- [ ] Monitor tomorrow's 5 AM Bangkok run (2025-12-30 05:00)
- [ ] Verify both schedulers triggered successfully
- [ ] Verify data stored with correct date (2025-12-30)
- [ ] Check CloudWatch logs for 2 invocations ~1 second apart
- [ ] Wait 24-48 hours (1-2 more successful runs)

**Cutover Steps** (Phase 3):
1. [ ] Create terraform.dev.tfvars entry or variable override:
   ```hcl
   old_scheduler_enabled = false  # Disable old scheduler
   new_scheduler_enabled = true   # Keep new scheduler
   ```

2. [ ] Apply Terraform changes:
   ```bash
   cd terraform
   ENV=dev doppler run -- terraform plan -var-file=terraform.dev.tfvars
   ENV=dev doppler run -- terraform apply -var-file=terraform.dev.tfvars
   ```

3. [ ] Verify cutover via AWS CLI:
   ```bash
   # Old scheduler should be DISABLED
   ENV=dev doppler run -- aws events describe-rule \
     --name dr-daily-report-daily-ticker-fetch-dev \
     --query 'State' --output text
   # Expected: "DISABLED"

   # New scheduler should be ENABLED
   ENV=dev doppler run -- aws scheduler get-schedule \
     --name dr-daily-report-daily-ticker-fetch-v2-dev \
     --group-name default \
     --query 'State' --output text
   # Expected: "ENABLED"
   ```

4. [ ] Monitor next scheduled run (only 1 invocation expected)

5. [ ] Document cutover:
   ```bash
   /validate "Only new scheduler triggered at 5 AM Bangkok"
   /journal deployment "Phase 3 cutover to EventBridge Scheduler"
   ```

**If Failure Detected** (Rollback):
1. [ ] Re-enable old scheduler:
   ```hcl
   old_scheduler_enabled = true   # Rollback to Phase 2
   new_scheduler_enabled = true
   ```
2. [ ] Apply Terraform changes immediately
3. [ ] Manual invocation for immediate fix (if needed):
   ```bash
   ENV=dev doppler run -- aws lambda invoke \
     --function-name dr-daily-report-ticker-scheduler-dev:live \
     --payload '{"action":"precompute","include_report":true}' \
     --cli-binary-format raw-in-base64-out \
     /tmp/rollback-response.json
   ```
4. [ ] Investigate new scheduler failure via CloudWatch logs

---

## Risk Analysis

### Risk 1: New Scheduler Fails After Cutover

**Description**: New EventBridge Scheduler fails to trigger Lambda after old scheduler disabled

**Likelihood**: Low (EventBridge Scheduler 99.9% SLA, Phase 2 validates reliability)

**Impact**: High (data pipeline breaks, reports unavailable)

**Mitigation**:
- **Prevention**: 24-48 hour validation period in Phase 2
- **Detection**: CloudWatch alarm on missing Lambda invocations
- **Recovery**: Rollback to Phase 2 (re-enable old scheduler) in ~5 minutes
- **Workaround**: Manual Lambda invocation for immediate data fetch

### Risk 2: Terraform State Drift

**Description**: AWS resources exist but Terraform state doesn't match (already observed in Phase 2)

**Likelihood**: Medium (already happened during Phase 2 deployment)

**Impact**: Medium (Terraform apply fails, manual AWS CLI intervention needed)

**Mitigation**:
- **Prevention**: Import existing resources to Terraform state before Phase 3
- **Detection**: `terraform plan` will show drift
- **Recovery**: AWS CLI commands to manually update resources
- **Long-term fix**: Import resources to Terraform state (Phase 4)

### Risk 3: Lambda Alias Not Updated

**Description**: Lambda :live alias points to old version without Bangkok timezone fix

**Likelihood**: Very Low (already verified :live points to version 87)

**Impact**: High (data stored with wrong dates)

**Mitigation**:
- **Prevention**: Verify :live alias before cutover
- **Detection**: Check Lambda response date field
- **Recovery**: Update :live alias to version 87

---

## Timeline

### Phase 2 (Current): Parallel Shadow Run
**Duration**: 24-48 hours (1-2 successful runs)

**Goals**:
- Validate new scheduler triggers correctly
- Verify data stored with correct Bangkok dates
- Confirm both schedulers can coexist

**Success Criteria**:
- ✅ Both schedulers trigger at 5 AM Bangkok
- ✅ Data stored with date=2025-12-30 (correct Bangkok date)
- ✅ No errors in CloudWatch logs
- ✅ Precompute jobs triggered successfully

### Phase 3 (Planned): Cutover to New Scheduler
**Timing**: After 24-48 hours of successful Phase 2 runs

**Duration**: ~10 minutes (Terraform apply + verification)

**Goals**:
- Disable old EventBridge Rule
- Keep new EventBridge Scheduler enabled
- Verify single-scheduler operation

**Success Criteria**:
- ✅ Old scheduler DISABLED
- ✅ New scheduler ENABLED
- ✅ Single Lambda invocation at 5 AM Bangkok
- ✅ Data pipeline continues working

### Phase 4 (Future): Cleanup
**Timing**: After 1 week of successful Phase 3 operation

**Duration**: ~30 minutes

**Goals**:
- Remove old EventBridge Rule resources
- Import new Scheduler to Terraform state (if needed)
- Update documentation

---

## Expected Behavior After Cutover

### Daily 5 AM Bangkok Run

**What will happen**:

1. **05:00 Bangkok (22:00 UTC previous day)**:
   - New EventBridge Scheduler triggers → invokes Lambda :live (v87)
   - Old EventBridge Rule: DISABLED (no trigger)

2. **Lambda Execution** (1 invocation):
   - Fetches 46 tickers from Yahoo Finance
   - Stores data with date = `2025-12-30` (Bangkok timezone fix applied ✅)
   - Triggers precompute controller
   - Duration: ~35 seconds

3. **Aurora Data**:
   - After run: 46 rows with date=`2025-12-30`
   - Query: `SELECT COUNT(*) FROM ticker_data WHERE date='2025-12-30'`
   - Expected: 46 rows (not 92, since only 1 invocation)

4. **CloudWatch Logs**:
   - Shows 1 invocation at 05:00 Bangkok
   - No duplicate invocations
   - Clearer logs (no confusion from parallel runs)

---

## Contradicting Evidence

**None found** - assuming Phase 2 validation succeeds.

**However, if Phase 2 reveals issues**:
- If new scheduler fails to trigger → Do NOT proceed to Phase 3
- If data stored with wrong dates → Fix timezone handling first
- If Lambda errors occur → Debug before cutover

---

## Missing Evidence

**Required before cutover**:
1. ⏳ **Phase 2 validation results**: 24-48 hours of successful runs
2. ⏳ **CloudWatch logs**: Evidence of both schedulers triggering
3. ⏳ **Aurora data verification**: Correct Bangkok dates stored
4. ⏳ **Error analysis**: Any failures during Phase 2

**Evidence collection commands**:
```bash
# After tomorrow's 5 AM run, collect evidence:

# 1. CloudWatch logs (verify 2 invocations)
ENV=dev doppler run -- aws logs tail \
  /aws/lambda/dr-daily-report-ticker-scheduler-dev \
  --since 1h \
  --follow

# 2. Aurora data (verify correct date)
just aurora-query "SELECT COUNT(*) FROM ticker_data WHERE date='2025-12-30'"

# 3. Scheduler states (verify both enabled)
ENV=dev doppler run -- aws events describe-rule \
  --name dr-daily-report-daily-ticker-fetch-dev \
  --query 'State' --output text

ENV=dev doppler run -- aws scheduler get-schedule \
  --name dr-daily-report-daily-ticker-fetch-v2-dev \
  --group-name default \
  --query 'State' --output text
```

---

## Comparison: Phase 2 vs Phase 3

| Aspect | Phase 2 (Current) | Phase 3 (Cutover) |
|--------|------------------|-------------------|
| **Old Scheduler** | ENABLED | DISABLED |
| **New Scheduler** | ENABLED | ENABLED |
| **Invocations/day** | 2 | 1 |
| **Aurora rows/day** | 46 or 92 | 46 |
| **Cost/month** | ~$0.018 | ~$0.009 |
| **Complexity** | High (2 schedulers) | Low (1 scheduler) |
| **Redundancy** | Yes (fallback) | No (single point) |
| **Timezone clarity** | Mixed (UTC + Bangkok) | Clear (Bangkok only) |
| **Migration phase** | phase-2-parallel | phase-3-cutover |

---

## Follow-Up

### Journal This (After Cutover)

**Title**: "Phase 3 Cutover to EventBridge Scheduler - Bangkok Timezone Migration"

**Capture**:
- Why cutover: Semantic timezone clarity, simplicity
- Validation period: 24-48 hours of successful parallel runs
- Risks: New scheduler failure, rollback plan
- Outcome: Single scheduler with explicit Bangkok timezone

**Command**:
```bash
/journal deployment "Phase 3 cutover to EventBridge Scheduler"
```

### Validate Assumptions (During Phase 2)

**Claims to validate**:
1. "New scheduler triggers at 5 AM Bangkok" → Check CloudWatch logs
2. "Data stored with correct Bangkok date" → Query Aurora
3. "Both schedulers can coexist" → Verify 2 invocations

**Commands**:
```bash
/validate "New scheduler triggered at 5 AM Bangkok (2025-12-30)"
/validate "Data stored with date=2025-12-30 in Aurora"
```

### Prove Implications (Optional)

**If formal proof needed**:
```bash
/proof "Single scheduler with explicit timezone is clearer than UTC offset math"
```

---

## Next Steps

### Immediate (Phase 2 Monitoring)

1. **Wait for tomorrow's 5 AM Bangkok run** (2025-12-30 05:00)
2. **Collect evidence** (CloudWatch logs, Aurora data, scheduler states)
3. **Validate success criteria** (both schedulers triggered, correct dates)

### After 24-48 Hours (Phase 3 Decision)

**If validation successful**:
- ✅ Proceed with Phase 3 cutover (disable old scheduler)
- ✅ Follow action items above
- ✅ Monitor for 1 week before Phase 4 cleanup

**If validation reveals issues**:
- ❌ Do NOT proceed to Phase 3
- ❌ Debug issues (use `/bug-hunt`)
- ❌ Fix problems before cutover
- ❌ Restart Phase 2 validation

### Long-term (Phase 4 Cleanup)

**After 1 week of successful Phase 3**:
1. Remove old EventBridge Rule resources from Terraform
2. Import new Scheduler to Terraform state (resolve state drift)
3. Update documentation with final architecture
4. Close migration project

---

## References

### Terraform Resources

**Old Scheduler (EventBridge Rules)**:
- Resource: `aws_cloudwatch_event_rule.daily_ticker_fetch`
- File: terraform/scheduler.tf:170-186
- Toggle: `var.old_scheduler_enabled`

**New Scheduler (EventBridge Scheduler)**:
- Resource: `aws_scheduler_schedule.daily_ticker_fetch_v2`
- File: terraform/scheduler.tf:270-324
- Toggle: `var.new_scheduler_enabled`

**Migration Phase Output**:
- Output: `ticker_scheduler_migration_phase`
- File: terraform/scheduler.tf:365-372
- Logic: Determines phase based on toggle values

### Documentation

- Validation report: `.claude/validations/2025-12-30-both-schedulers-deployed.md`
- Bug hunt (timezone): `.claude/bug-hunts/2025-12-30-wrong-date-utc-instead-of-bangkok.md`
- Bug hunt (terraform): `.claude/bug-hunts/2025-12-30-terraform-vpc-resource-reference-error.md`

### AWS Resources

**Old Scheduler**:
- Rule: `dr-daily-report-daily-ticker-fetch-dev`
- Target: Lambda :live alias

**New Scheduler**:
- Schedule: `dr-daily-report-daily-ticker-fetch-v2-dev`
- IAM Role: `dr-daily-report-eventbridge-scheduler-role-dev`
- Target: Lambda :live alias

**Lambda Function**:
- Alias: `dr-daily-report-ticker-scheduler-dev:live`
- Version: 87 (Bangkok timezone fix)

---

## Validation Metadata

**Analysis date**: 2025-12-30 02:00 Bangkok

**Scenario type**: Configuration modification (Phase 2 → Phase 3)

**Confidence level**: High (assumes Phase 2 validation succeeds)

**Reproducible**: Yes (Terraform configuration documented)

**Recommendation**: ⚠️ CONDITIONALLY YES (after 24-48 hour validation)
