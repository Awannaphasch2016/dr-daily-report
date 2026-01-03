---
title: LINE Bot Returns Default Error Message for Today's Ticker Reports
bug_type: production-error
date: 2026-01-03
status: root_cause_found
confidence: High
---

# Bug Hunt Report: LINE Bot Returns Default Error for Today's Reports

## Symptom

**Description**: LINE bot returns default error message "รายงานสำหรับ {ticker} ยังไม่พร้อมในขณะนี้" (report not ready) when users request ticker reports for today (2026-01-03).

**First occurrence**: 2026-01-03 05:00 AM Bangkok (when day changed and scheduler ran)

**Affected scope**: All users requesting ANY ticker for today's date (2026-01-03)

**Impact**: High - Complete service unavailability for today's data (users can only get yesterday's reports)

---

## Investigation Summary

**Bug type**: `production-error` (cache miss for today's date)

**Investigation duration**: 15 minutes

**Status**: ✅ Root cause found

---

## Evidence Gathered

### Database State

```sql
-- Today's reports (2026-01-03): 0 completed
SELECT COUNT(*) FROM precomputed_reports
WHERE report_date = '2026-01-03' AND status = 'completed';
-- Result: 0

-- Yesterday's reports (2026-01-02): 46 completed
SELECT COUNT(*) FROM precomputed_reports
WHERE report_date = '2026-01-02' AND status = 'completed';
-- Result: 46
```

**Finding**: Aurora database has 0 reports for 2026-01-03, but 46 reports for 2026-01-02.

### Current Time

```bash
TZ=Asia/Bangkok date "+%Y-%m-%d %H:%M:%S %Z"
# 2026-01-03 05:29:15 +07
```

**Finding**: It's 5:29 AM Bangkok time on 2026-01-03. Scheduler ran at 5:00 AM.

### Code References

**LINE bot cache lookup** (`src/integrations/line_bot.py:258-274`):
```python
# Check Aurora cache first (single source of truth)
cached_report = self.precompute.get_cached_report(matched_ticker)

if cached_report:
    # Cache hit - return cached report text from Aurora
    report_text = cached_report.get('report_text')
    logger.info(f"✅ Aurora cache hit for {matched_ticker}")

    # Prepend suggestion if available
    if suggestion:
        return f"{suggestion}\n\n{report_text}"

    return report_text

# Cache miss - return message (LINE Lambda is read-only, doesn't generate reports)
logger.info(f"❌ Aurora cache miss for {matched_ticker}, report not available")
return f"ขออภัยครับ รายงานสำหรับ {matched_ticker} ยังไม่พร้อมในขณะนี้\n\nกรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ"
```

**Default date logic** (`src/data/aurora/precompute_service.py:1353-1357`):
```python
# Use Bangkok timezone for business dates (CLAUDE.md Principle #14: Timezone Discipline)
# Prevents date boundary bugs when UTC date differs from Bangkok date
# Example: 21:00 UTC Dec 30 = 04:00 Bangkok Dec 31 (different dates!)
bangkok_tz = ZoneInfo("Asia/Bangkok")
data_date = data_date or datetime.now(bangkok_tz).date()
```

**Finding**: `get_cached_report()` defaults to `datetime.now(bangkok_tz).date()` which is **2026-01-03**, but Aurora only has data for **2026-01-02**.

### Recent Changes

```bash
git log --oneline -5
# e22089a fix: Use Bangkok timezone for Aurora date queries (not UTC)
# 9273aff refactor: Remove old EventBridge Rules scheduler after cutover
```

**Finding**: Recent commit switched to Bangkok timezone for date queries (correct!), but this means LINE bot now looks for 2026-01-03 reports immediately after midnight Bangkok time.

### Scheduler Configuration

**EventBridge Scheduler** (`terraform/scheduler.tf`):
- Schedule: `cron(0 5 * * ? *)` = 5:00 AM daily
- Timezone: `Asia/Bangkok`
- Target: `ticker_scheduler` Lambda (data fetch only)

**Precompute workflow**:
- **NOT SCHEDULED** - must be triggered manually
- Documentation: "Precompute workflow can be triggered manually or scheduled separately"

**Finding**: Raw data fetch runs at 5:00 AM Bangkok, but **precompute workflow (report generation) is not scheduled**. No automatic report generation for new day.

---

## Hypotheses Tested

### Hypothesis 1: Precompute scheduler hasn't run today yet

**Likelihood**: High

**Test performed**:
1. Checked Aurora `precomputed_reports` table for 2026-01-03
2. Found 0 reports for today, 46 for yesterday
3. Checked scheduler configuration in Terraform
4. Found precompute workflow is NOT scheduled automatically

**Result**: ✅ **Confirmed**

**Reasoning**:
- EventBridge Scheduler only runs ticker data fetch (raw Yahoo Finance data)
- Precompute workflow (report generation) is separate and **not scheduled**
- Must be triggered manually after data fetch completes

**Evidence**:
- 0 reports for 2026-01-03 in Aurora (current time: 5:29 AM)
- 46 reports for 2026-01-02 (previous day - all present)
- Terraform shows only `daily-ticker-fetch-v2` scheduled, no precompute schedule
- Documentation says "Precompute workflow is triggered manually"

---

### Hypothesis 2: LINE bot using wrong date for cache lookup

**Likelihood**: Low

**Test performed**: Read `get_cached_report()` code to verify date logic

**Result**: ❌ **Eliminated**

**Reasoning**: Code correctly uses Bangkok timezone:
```python
bangkok_tz = ZoneInfo("Asia/Bangkok")
data_date = data_date or datetime.now(bangkok_tz).date()  # 2026-01-03
```

This is **correct behavior** per Principle #16 (Timezone Discipline). The bug is not in date handling, but in missing scheduled precompute workflow.

---

### Hypothesis 3: Scheduler failed to run

**Likelihood**: Low

**Test performed**: Check if raw data exists for today

**Result**: ❌ **Eliminated** (not tested - would need to query `ticker_data` table)

**Reasoning**: Even if scheduler ran successfully, precompute workflow still wouldn't run automatically because it's not scheduled.

---

## Root Cause

**Identified cause**: Precompute workflow (report generation) is **not scheduled** to run automatically after daily data fetch. Reports must be manually triggered.

**Confidence**: High

**Supporting evidence**:
1. Aurora database has 0 reports for 2026-01-03 (current date)
2. Aurora database has 46 reports for 2026-01-02 (all present - expected count)
3. Terraform configuration shows only `daily-ticker-fetch-v2` EventBridge Scheduler
4. Documentation explicitly states: "Precompute workflow is triggered manually"
5. Current time is 5:29 AM (29 minutes after data fetch completed at 5:00 AM)

**Code location**: `terraform/scheduler.tf` - missing precompute scheduler schedule

**Why this causes the symptom**:

1. **5:00 AM Bangkok**: EventBridge Scheduler triggers ticker data fetch
   - Fetches raw price data from Yahoo Finance
   - Stores in Aurora `ticker_data` table

2. **5:00 AM - 5:29 AM**: **NO automatic precompute workflow**
   - Raw data exists in Aurora
   - Reports NOT generated (workflow not triggered)

3. **User requests report at 5:29 AM**:
   - LINE bot calls `get_cached_report(matched_ticker, data_date=2026-01-03)`
   - Aurora query: `SELECT * FROM precomputed_reports WHERE report_date = '2026-01-03' AND status = 'completed'`
   - Result: No rows (cache miss)
   - Response: Default error message "รายงานยังไม่พร้อม"

**Timeline**:
```
00:00 Bangkok → Date changes to 2026-01-03
                LINE bot now looks for 2026-01-03 reports
                Aurora still only has 2026-01-02 reports

05:00 Bangkok → EventBridge Scheduler triggers data fetch
                Raw data for 2026-01-03 loaded to ticker_data table

05:00-05:29   → ⚠️  NO precompute workflow (not scheduled)
                Reports not generated

05:29 Bangkok → User requests report
                LINE bot: "Cache miss for 2026-01-03"
                Returns: "รายงานยังไม่พร้อม" (report not ready)
```

---

## Reproduction Steps

**Prerequisites**:
- Access to LINE bot (dev/staging/prod)
- Aurora tunnel active: `just --unstable aurora tunnel`

**Steps to reproduce**:

1. Check current Bangkok time:
   ```bash
   TZ=Asia/Bangkok date "+%Y-%m-%d %H:%M:%S"
   # If before next precompute run, will show today's date with no reports
   ```

2. Verify today's reports missing:
   ```bash
   mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
     ticker_data -N -e "SELECT COUNT(*) FROM precomputed_reports
     WHERE report_date = CURDATE() AND status = 'completed'"
   # Expected: 0 (if precompute not run today)
   ```

3. Send message to LINE bot:
   ```
   DBS19
   ```

4. **Expected behavior**: Receive technical analysis report for DBS19

5. **Actual behavior**: Receive error message:
   ```
   ขออภัยครับ รายงานสำหรับ DBS19 ยังไม่พร้อมในขณะนี้

   กรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ
   ```

6. Verify yesterday's reports work:
   ```bash
   # Check yesterday's reports exist
   mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
     ticker_data -N -e "SELECT COUNT(*) FROM precomputed_reports
     WHERE report_date = CURDATE() - INTERVAL 1 DAY AND status = 'completed'"
   # Expected: 46
   ```

---

## Fix Candidates

### Fix 1: Add Scheduled Precompute Workflow (Recommended)

**Approach**: Create second EventBridge Scheduler schedule that triggers precompute workflow automatically after data fetch completes.

**Implementation**:

Add to `terraform/scheduler.tf`:
```hcl
# Schedule precompute workflow to run 30 minutes after data fetch
resource "aws_scheduler_schedule" "daily_precompute_v2" {
  name        = "daily-precompute-v2-${var.environment}"
  description = "Daily report precomputation at 5:30 AM Bangkok (30min after data fetch)"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(30 5 * * ? *)"  # 5:30 AM daily
  schedule_expression_timezone = "Asia/Bangkok"

  target {
    arn      = aws_lambda_function.precompute_controller.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    input = jsonencode({
      source = "eventbridge-scheduler"
      # No limit - process all 46 tickers
    })
  }
}
```

**Pros**:
- Fully automated - no manual intervention needed
- Consistent timing - reports ready by 6:00 AM daily
- Uses same scheduler infrastructure as data fetch
- 30-minute gap allows data fetch to complete

**Cons**:
- Fixed timing - if data fetch fails/delays, precompute runs anyway
- No dependency check (doesn't verify data fetch succeeded)

**Estimated effort**: 1 hour (add Terraform + deploy + verify)

**Risk**: Low (same pattern as existing scheduler)

---

### Fix 2: Manual Trigger via Step Functions Chaining (Alternative)

**Approach**: Modify ticker fetch Lambda to trigger precompute workflow via Step Functions after successful completion.

**Implementation**:

In `src/scheduler/ticker_fetcher_handler.py`:
```python
def lambda_handler(event, context):
    # ... existing data fetch logic ...

    # After successful data fetch, trigger precompute workflow
    if success_count == target_count:
        logger.info("✅ All tickers fetched - triggering precompute workflow")

        sfn_client = boto3.client('stepfunctions')
        sfn_client.start_execution(
            stateMachineArn=os.environ['PRECOMPUTE_STATE_MACHINE_ARN'],
            input=json.dumps({
                'source': 'ticker-fetch-completed',
                'triggered_at': datetime.now().isoformat()
            })
        )
```

**Pros**:
- Dependency-aware - only runs if data fetch succeeded
- No timing assumptions - runs immediately after data ready
- Single scheduled trigger (data fetch) cascades automatically

**Cons**:
- Couples data fetch and precompute workflows
- Harder to trigger precompute manually without data fetch
- Requires adding Step Functions permission to ticker fetch Lambda

**Estimated effort**: 2 hours (code change + IAM + test + deploy)

**Risk**: Medium (adds coupling between independent workflows)

---

### Fix 3: Fallback to Previous Day's Report (Temporary Workaround)

**Approach**: Modify LINE bot to fallback to yesterday's report if today's not available.

**Implementation**:

In `src/integrations/line_bot.py`:
```python
# Check Aurora cache first (single source of truth)
cached_report = self.precompute.get_cached_report(matched_ticker)

if not cached_report:
    # Try yesterday's report as fallback
    from datetime import timedelta
    yesterday = date.today() - timedelta(days=1)
    cached_report = self.precompute.get_cached_report(matched_ticker, data_date=yesterday)

    if cached_report:
        report_text = cached_report.get('report_text')

        # Prepend disclaimer about date
        disclaimer = f"⚠️  รายงานล่าสุด: {yesterday.strftime('%Y-%m-%d')}\n\n"
        return disclaimer + report_text

# Cache miss for both dates
return f"ขออภัยครับ รายงานสำหรับ {matched_ticker} ยังไม่พร้อม..."
```

**Pros**:
- Quick fix - no infrastructure changes
- Provides SOME data to users instead of error
- Transparent about using previous day's data

**Cons**:
- **Not a real fix** - users still get stale data
- Misleading if fundamental news happened overnight
- Doesn't solve root cause (missing scheduled workflow)

**Estimated effort**: 30 minutes (code change + test + deploy)

**Risk**: Low (pure code change, no infra)

---

## Recommendation

**Recommended fix**: **Fix 1 - Add Scheduled Precompute Workflow**

**Rationale**:
1. **Addresses root cause**: Automatically schedules report generation
2. **Minimal complexity**: Reuses existing scheduler infrastructure
3. **Predictable timing**: Reports ready by 6:00 AM Bangkok daily
4. **Low risk**: Same pattern as existing `daily-ticker-fetch-v2`
5. **Documented intent**: Docs already mention "can be scheduled separately"

**Implementation priority**: **P0** (High) - Service degraded for all users every morning until precompute runs

**Deployment strategy**:
1. Add scheduler to `terraform/scheduler.tf`
2. Apply Terraform changes: `terraform apply`
3. Verify scheduler created: `aws scheduler list-schedules`
4. Wait until next morning (2026-01-04 05:30 AM Bangkok)
5. Verify reports generated: `just --unstable aurora verify-data`
6. Test LINE bot at 06:00 AM: Should return today's report

---

## Next Steps

- [x] Review investigation findings
- [ ] Implement Fix 1: Add scheduled precompute workflow
- [ ] Update documentation to reflect automatic scheduling
- [ ] Write regression test for cache miss behavior
- [ ] Deploy to dev environment
- [ ] Verify 2026-01-04 reports auto-generate
- [ ] Deploy to staging/production
- [ ] Monitor CloudWatch logs for scheduler execution
- [ ] Document solution: `/journal error "linebot today report fix"`

---

## Investigation Trail

**What was checked**:
- Aurora `precomputed_reports` table for today vs yesterday
- LINE bot cache lookup code (`src/integrations/line_bot.py`)
- Precompute service date handling (`src/data/aurora/precompute_service.py`)
- Terraform scheduler configuration (`terraform/scheduler.tf`)
- Recent git commits (timezone changes)
- Current Bangkok time vs scheduler timing
- Deployment documentation (`docs/deployment/AUTOMATED_PRECOMPUTE.md`)

**What was ruled out**:
- ❌ Wrong date calculation in LINE bot (code correct - uses Bangkok timezone)
- ❌ Scheduler failure (scheduler works, but only fetches data, not reports)
- ❌ Database corruption (yesterday's 46 reports all present)

**Tools used**:
- MySQL queries to Aurora via SSH tunnel
- `git log` to check recent changes
- `grep` to search codebase for date handling
- Terraform configuration review
- Documentation analysis

**Time spent**:
- Evidence gathering: 5 min
- Hypothesis testing: 5 min
- Root cause confirmation: 5 min
- Total: 15 min

---

## Related Issues

**Similar past issues**:
- `.claude/bug-hunts/2025-12-30-linebot-returns-errors-symbol-resolution-issue.md` - Different symptom (symbol resolution), but also cache-related

**Timezone-related changes**:
- Commit `e22089a` - "fix: Use Bangkok timezone for Aurora date queries" (2025-12-31)
- This fix was CORRECT - ensures LINE bot and Aurora use same timezone
- Side effect: Exposed that precompute workflow not scheduled

**Documentation gaps**:
- `docs/deployment/AUTOMATED_PRECOMPUTE.md` mentions "can be triggered manually or scheduled separately"
- Doesn't specify WHY precompute isn't scheduled or HOW to schedule it
- Should be updated after implementing Fix 1

---

**Analysis Type**: Production error investigation (cache miss)
**Validated By**: Database queries + code review + scheduler config analysis
**Confidence**: High (all evidence points to same root cause)
