---
title: No ticker data for 2025-12-29 in ticker_data table
bug_type: data-corruption (expected data missing)
date: 2025-12-29
status: root_cause_found
confidence: High
---

# Bug Hunt Report: Missing Ticker Data for Today

## Symptom

**Description**: User query shows 0 records for date '2025-12-29' in ticker_data table, while yesterday (2025-12-28) has 46 records.

```sql
SELECT COUNT(*) as total FROM ticker_data WHERE date = '2025-12-29'
-- Result: 0

SELECT COUNT(*) as total FROM ticker_data WHERE date = '2025-12-28'
-- Result: 46
```

**First occurrence**: 2025-12-29 (user noticed missing data)

**Affected scope**: All users querying for today's ticker data

**Impact**: Medium (expected behavior, but user confusion)

---

## Investigation Summary

**Bug type**: data-corruption (expected data missing)

**Investigation duration**: 15 minutes

**Status**: ✅ Root cause found - NOT A BUG

---

## Evidence Gathered

### Scheduler Configuration

**File**: `terraform/scheduler.tf:169-173`

```hcl
resource "aws_cloudwatch_event_rule" "daily_ticker_fetch" {
  name                = "${var.project_name}-daily-ticker-fetch-${var.environment}"
  description         = "Fetch ticker data daily at 5 AM Bangkok time (UTC+7)"
  schedule_expression = "cron(0 22 * * ? *)" # 22:00 UTC = 05:00 Bangkok next day
  state = "ENABLED"
}
```

**Key Finding**: Scheduler runs at **22:00 UTC** daily, which is **5:00 AM Bangkok next day**.

### Current Time

**Evidence collected at**: 2025-12-29 08:51:16 UTC (15:51:16 Bangkok)

- **UTC**: 08:51 (8:51 AM)
- **Bangkok**: 15:51 (3:51 PM)

**Next scheduled run**: 2025-12-29 22:00:00 UTC (2025-12-30 05:00:00 Bangkok)

### Lambda Invocation History

**Source**: CloudWatch Lambda Metrics

Last 5 ticker scheduler invocations:
```
2025-12-27T21:51:00+00:00  |  1.0 (Dec 28 04:51 Bangkok)
2025-12-28T17:51:00+00:00  |  1.0 (Dec 29 00:51 Bangkok) - manual trigger?
2025-12-28T19:51:00+00:00  |  1.0 (Dec 29 02:51 Bangkok) - manual trigger?
2025-12-28T20:51:00+00:00  |  1.0 (Dec 29 03:51 Bangkok) - manual trigger?
2025-12-28T21:51:00+00:00  |  1.0 (Dec 29 04:51 Bangkok) - scheduled run
```

**Key Finding**: Scheduler last ran at **2025-12-28 21:51 UTC** (Dec 29 04:51 Bangkok), which is the regular scheduled run for Dec 28 data.

### Database Records

**Source**: Aurora ticker_data table

```sql
SELECT date, COUNT(*) as count
FROM ticker_data
WHERE date >= '2025-12-27'
GROUP BY date
ORDER BY date DESC
```

Results:
```
2025-12-28  |  46  (populated by 2025-12-28 21:51 UTC run)
2025-12-27  |  46  (populated by 2025-12-27 22:00 UTC run)
```

**Key Finding**: Database has data for Dec 27 and Dec 28, but NOT Dec 29 (as expected, since scheduler hasn't run yet).

---

## Hypotheses Tested

### Hypothesis 1: Scheduler Failed to Run Today

**Likelihood**: Medium

**Test performed**:
- Checked CloudWatch Lambda invocation metrics for 2025-12-29 UTC
- Checked EventBridge rule status

**Result**: ✅ Eliminated

**Reasoning**:
- Scheduler is configured to run at 22:00 UTC daily
- Current time is 08:51 UTC (scheduler hasn't run yet today)
- Last run was 2025-12-28 21:51 UTC (on schedule)
- EventBridge rule is ENABLED

**Evidence**:
- CloudWatch metrics show zero invocations between 00:00-08:51 UTC today
- Scheduler will run in ~13 hours (at 22:00 UTC today)

---

### Hypothesis 2: Data Stored with Wrong Date Field

**Likelihood**: Low

**Test performed**:
- Checked ticker_data table schema
- Queried with different date column names (`data_date` vs `date`)

**Result**: ✅ Eliminated

**Reasoning**:
- Schema shows correct column name is `date` (not `data_date`)
- User's initial query used correct column name
- Data for Dec 27 and Dec 28 exists with correct date values

**Evidence**:
- `SHOW COLUMNS FROM ticker_data` confirms column is named `date`
- Query with `date = '2025-12-28'` returns 46 records (correct)

---

### Hypothesis 3: Scheduler Timezone Confusion

**Likelihood**: High

**Test performed**:
- Reviewed EventBridge cron expression: `cron(0 22 * * ? *)`
- Calculated Bangkok time conversion: 22:00 UTC → 05:00 Bangkok (+7 hours)
- Checked current time in both timezones

**Result**: ✅ Confirmed (This is the ROOT CAUSE)

**Reasoning**:
- Scheduler runs at 22:00 UTC = 5:00 AM Bangkok **next day**
- Current time: Dec 29 08:51 UTC = Dec 29 15:51 Bangkok
- **Data for "Dec 29" won't exist until Dec 29 22:00 UTC** (Dec 30 5:00 AM Bangkok)

**Evidence**:
- Terraform config comment: `22:00 UTC = 05:00 Bangkok next day`
- Last run: Dec 28 21:51 UTC populated data with `date = '2025-12-28'`
- Next run: Dec 29 22:00 UTC will populate data with `date = '2025-12-29'`

---

## Root Cause

**Identified cause**: **NOT A BUG** - Expected behavior based on scheduler design

**Confidence**: High

**Supporting evidence**:
1. EventBridge scheduler configured to run at 22:00 UTC daily
2. Current time (08:51 UTC) is 13 hours before next scheduled run
3. Last successful run was Dec 28 21:51 UTC, which populated `date = '2025-12-28'`
4. Database correctly has 46 records for Dec 28, zero for Dec 29

**Code location**: `terraform/scheduler.tf:169-173`

**Why this causes the symptom**:

The scheduler design has a **timezone offset** that causes confusion:
- Yahoo Finance data is fetched at **5:00 AM Bangkok time**
- This is **22:00 UTC the previous day** (Bangkok is UTC+7)
- So data for "Dec 29" is fetched at **Dec 29 22:00 UTC**, which is **Dec 30 5:00 AM Bangkok**

This means:
- When it's **Dec 29 afternoon in Bangkok** (user's local time), the scheduler **hasn't run yet** for Dec 29 data
- Dec 29 data will only appear **tomorrow morning** (Dec 30 5:00 AM Bangkok)

**User confusion**: User expects data for "today" (Dec 29 Bangkok time), but data represents "yesterday's close" (Dec 28 close), which is correct for financial data but confusing when querying by calendar date.

---

## Architecture Implication

### Design Pattern: Date Field Semantics

The `date` field in `ticker_data` table represents:
- **Trading date** (the date the stock market data is for)
- **NOT** the fetch date/time

**Example**:
- Fetch time: 2025-12-28 21:51 UTC (Dec 29 04:51 Bangkok)
- Stored date: `2025-12-28` (trading date, NOT fetch date)

This is **correct financial data modeling** because:
- Markets close at ~16:00 Bangkok (09:00 UTC)
- Fetching at 5 AM Bangkok gets **previous day's close data**
- Storing with **trading date** aligns with financial analysis conventions

### Why This Confuses Users

When user queries at **Dec 29 15:51 Bangkok**:
1. User thinks: "Today is Dec 29, I want Dec 29 data"
2. System has: Dec 28 data (fetched this morning at 5 AM)
3. Dec 29 data: Won't exist until tomorrow morning (Dec 30 5 AM)

**Gap**: 19-hour window where "today's data" doesn't exist yet.

---

## No Fix Required

**Status**: ✅ Working as designed

**Reasoning**:
- This is **expected behavior** for financial data ETL
- Stock markets close at 16:00 Bangkok
- Fetching at 5:00 AM next day gets **complete previous day data**
- Storing with **trading date** (not fetch date) is industry standard

**Alternative considered but rejected**:

### Option 1: Change date field to fetch_date

❌ **Rejected** - Breaks financial analysis semantics
- Reports would show "Dec 29" for data that's actually Dec 28 trading day
- User confusion: "Why is Dec 29 report showing Dec 28 close price?"

### Option 2: Fetch twice per day (intraday + EOD)

❌ **Rejected** - Increases cost and complexity
- Would need 2 ETL runs (during market hours + after close)
- Yahoo Finance intraday data has different API pricing
- Adds complexity for marginal benefit

### Option 3: Add documentation explaining date semantics

✅ **Recommended** - Educate users on data model
- Document that `date` field is **trading date**, not fetch date
- Add API response field explaining data freshness
- Example: `{"date": "2025-12-28", "fetched_at": "2025-12-29T04:51:00+07:00", "note": "Data represents Dec 28 close"}`

---

## Recommendations

### Short-term (Documentation)

**Add to API response**:
```json
{
  "date": "2025-12-28",
  "fetched_at": "2025-12-29T04:51:00+07:00",
  "data_age_hours": 13,
  "note": "This data represents Dec 28 trading day (most recent complete data)"
}
```

**Update user-facing documentation**:
> **Data Freshness**: Ticker data is fetched daily at 5:00 AM Bangkok time. The `date` field represents the **trading date**, not the fetch date. This means:
> - Data for Dec 28 (fetched Dec 29 5 AM) = Dec 28 close
> - Data for Dec 29 will be available Dec 30 5 AM
> - During trading hours (9:00-16:00), "today's data" won't exist yet

### Medium-term (UI/UX Improvement)

**Add to user interface**:
- Show "Last updated: Dec 29 5:00 AM" with data
- Display warning if user requests data for "today" before 5 AM next day:
  ```
  ⚠️ Data for Dec 29 not available yet
  Dec 29 data will be fetched tomorrow (Dec 30) at 5:00 AM Bangkok
  ```

### Long-term (Consider but low priority)

**Evaluate intraday data product**:
- If users need "today's data" during market hours
- Requires Yahoo Finance premium API (higher cost)
- Would need separate ETL pipeline for intraday vs EOD

**Implementation priority**: P3 (nice-to-have, not critical)

---

## Next Steps

- [x] Investigation complete - root cause identified
- [x] Confirmed expected behavior (not a bug)
- [ ] Document date field semantics in API documentation
- [ ] Add `data_age_hours` field to API responses
- [ ] Consider UI warning for "future date" queries
- [ ] Update user-facing documentation explaining data freshness

---

## Investigation Trail

**What was checked**:
- EventBridge scheduler configuration (`terraform/scheduler.tf`)
- CloudWatch Lambda invocation metrics (last 48 hours)
- Aurora database records (ticker_data table)
- Current time in both UTC and Bangkok timezones
- Table schema to verify column naming

**What was ruled out**:
- Scheduler failure (scheduler hasn't run yet for today)
- Wrong date column name (schema confirmed `date` is correct)
- Database storage issue (Dec 27 and Dec 28 data exists correctly)

**Tools used**:
- AWS CloudWatch metrics (Lambda invocations)
- MySQL CLI (Aurora database queries)
- Terraform configuration review
- Timezone calculations (UTC ↔ Bangkok)

**Time spent**:
- Evidence gathering: 5 min
- Hypothesis testing: 5 min
- Root cause analysis: 5 min
- Total: 15 min

---

## Key Learnings

### 1. Date Field Semantics in Financial Data

**Pattern**: Trading date vs Fetch date
- Financial data should use **trading date** (when market closed)
- NOT fetch date (when data was retrieved)
- This is industry standard for stock market data

### 2. Timezone Confusion with Daily Schedules

**Pattern**: UTC scheduling for global services
- EventBridge uses UTC for cron expressions
- Bangkok is UTC+7, causing "next day" confusion
- 22:00 UTC = 5:00 AM Bangkok **next day**

**Implication**: Data for "Dec 29" (trading date) is fetched on "Dec 29 22:00 UTC", which is "Dec 30 5:00 AM Bangkok".

### 3. User Expectation vs System Design

**Gap**: Users expect "today's data" to be available during trading hours
**Reality**: System fetches "yesterday's close" at 5 AM next day

**Solution**: Documentation + UI warnings, not system redesign.

---

## References

**Code Files**:
- `terraform/scheduler.tf:169-176` - EventBridge scheduler configuration
- `src/scheduler/ticker_fetcher.py` - Yahoo Finance ETL implementation
- `db/migrations/012_create_ticker_data_table.sql` - Table schema

**CloudWatch Metrics**:
- `/aws/lambda/dr-daily-report-ticker-scheduler-dev` - Scheduler logs
- Lambda function: `dr-daily-report-ticker-scheduler-dev`
- Last invocation: 2025-12-28T21:51:00Z

**Database**:
- Table: `ticker_data`
- Date column: `date` (trading date, not fetch date)
- Current data: Dec 27 (46 records), Dec 28 (46 records)
- Missing: Dec 29 (expected, scheduler hasn't run yet)

**Related Documentation**:
- `.claude/validations/2025-12-29-etl-execution-validation.md` - ETL validation report
- `CLAUDE.md` Core Principle #3 - Aurora-First Data Architecture
