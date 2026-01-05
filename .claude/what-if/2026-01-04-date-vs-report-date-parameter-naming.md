# What-If Analysis: Using "date" Instead of "report_date" as Parameter Name

**Scenario**: Use `{"date": "2026-01-04"}` instead of `{"report_date": "2026-01-04"}` for nightly scheduler

**Type**: `parameter_naming` (API design decision)

**Date**: 2026-01-04

**Context**: User suggests that "date" is more appropriate than "report_date" for the nightly scheduler, since it runs every day and the date context is obvious.

---

## Current Reality

### Current Parameter Name: `report_date`

**Usage in codebase**:
```python
# src/scheduler/get_report_list_handler.py:67
report_date_str = event.get('report_date')
```

**Input format**:
```json
{
  "report_date": "2026-01-04"
}
```

**Rationale** (implicit):
- Explicit about what the date represents (report generation date)
- Distinguishes from other date types (data_date, execution_date, etc.)
- Self-documenting parameter name

---

## Under New Assumption: Parameter Name = `date`

### What Changes

**Lambda handler code**:
```python
# BEFORE
report_date_str = event.get('report_date')

# AFTER
report_date_str = event.get('date')
```

**Input format**:
```json
{
  "date": "2026-01-04"
}
```

**EventBridge input transformer**:
```terraform
# BEFORE
input_template = <<EOF
{
  "report_date": "<event_time>"
}
EOF

# AFTER
input_template = <<EOF
{
  "date": "<event_time>"
}
EOF
```

---

## Analysis

### User's Argument: "date" is More Appropriate

**Reasoning**:
1. **Context is obvious**: Nightly scheduler runs daily, so "date" clearly means "which date to generate reports for"
2. **Simpler naming**: Shorter, less verbose
3. **Natural language**: "Run reports for date X" is natural phrasing
4. **Consistent with daily workflow**: Every day has one date, one report run

**Strengths of this argument**:
- ✅ True that context makes meaning clear in scheduler scenario
- ✅ "date" is simpler and more concise
- ✅ Natural language alignment

---

### Counter-Analysis: Why "report_date" is Better

#### 1. **Naming Collision Risk**

**Problem**: "date" is generic and appears in many contexts

**Evidence from codebase**:
```bash
# Found 11 different uses of .get('date') in codebase:
src/scheduler/query_tool_handler.py:        check_date = event.get('date', ...)
src/api/transformer.py:        ticker_timestamp = ticker_data.get("date")
src/report/section_formatters.py:            if last_buy_signal.get('date'):
src/formatters/pdf_generator.py:        date = ticker_data.get('date', ...)
src/data/aurora/precompute_service.py:        history_start_date = price_history[0].get('date')
```

**Types of "date" in the system**:
- `ticker_data.get('date')` - Market data timestamp
- `price_history[0].get('date')` - Historical price date
- `last_buy_signal.get('date')` - Signal generation date
- `event.get('date')` - Query tool check date (different Lambda!)

**Collision example**:
```python
# Query tool handler already uses 'date'!
# src/scheduler/query_tool_handler.py
check_date = event.get('date', str(datetime.utcnow().date()))
```

**Result**: Two different Lambda handlers would use `event.get('date')` for **different purposes**:
- `query_tool_handler`: Date to check data status
- `get_report_list_handler`: Date to generate reports for

**Confusion risk**: HIGH (same parameter name, different semantics)

---

#### 2. **Multiple Date Contexts in Workflow**

**The system has multiple date concepts**:

1. **report_date**: Date for which report is generated (business date)
2. **data_date**: Date of market data used (might lag report_date)
3. **execution_date**: When scheduler actually runs
4. **computed_at**: When computation finished (timestamp)

**Example scenario**:
```
Execution: 2026-01-05 08:00 Bangkok time (execution_date)
Generating report for: 2026-01-04 (report_date)
Using market data from: 2026-01-04 (data_date)
Completed at: 2026-01-05 08:02 (computed_at)
```

**With generic "date"**:
```python
# Which date is this?
date = event.get('date')  # ??? Ambiguous
```

**With explicit "report_date"**:
```python
# Clear meaning
report_date = event.get('report_date')  # The date we're generating reports for
```

**Clarity improvement**: Explicit name documents intent

---

#### 3. **API Design Best Practices**

**Principle**: Parameter names should be **self-documenting** and **unambiguous**

**Good naming**:
```python
# Clear intent without looking at context
report_date = event.get('report_date')  # Generating report for this date
ticker = event.get('ticker')             # Which ticker symbol
limit = event.get('limit')               # Result limit
```

**Poor naming**:
```python
# Requires context to understand
date = event.get('date')  # Which date? For what purpose?
name = event.get('name')  # Ticker name? User name? Report name?
value = event.get('value')  # What value?
```

**Industry standard**: AWS APIs use specific names
- `StartDate` / `EndDate` (not just `Date`)
- `ExecutionDate` / `ScheduleDate` (not just `Date`)
- `ReportDate` / `DataDate` / `CreatedDate` (distinguishes types)

**Example from AWS Step Functions**:
```json
{
  "startDate": "2026-01-04T08:00:00Z",  // Not "date"
  "stopDate": "2026-01-04T08:02:00Z"    // Not "end"
}
```

---

#### 4. **Extensibility and Future-Proofing**

**Current use case**: Nightly scheduler (one date, simple)

**Future scenarios** that break with generic "date":

**Scenario A: Historical backfill**
```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-01-31"
}
```
- Need TWO dates → "date" is insufficient
- Must rename to `start_date` and `end_date` (breaking change)

**Scenario B: Data date vs report date differ**
```json
{
  "report_date": "2026-01-05",
  "data_date": "2026-01-04"  // Using yesterday's data
}
```
- Need to distinguish dates → "date" is ambiguous
- Must add `report_date` anyway (breaking change)

**Scenario C: Scheduled execution date tracking**
```json
{
  "report_date": "2026-01-04",
  "scheduled_date": "2026-01-05"  // When it was supposed to run
}
```
- Need both dates for debugging late runs
- Generic "date" doesn't support this

**With "report_date" from start**: No breaking changes needed, just add more dates

---

#### 5. **Error Messages and Debugging**

**Generic "date" error**:
```python
# Error message
ValueError: Missing required parameter: 'date'
```
**Question**: Which date? Report generation date? Data date? Execution date?

**Specific "report_date" error**:
```python
# Error message
ValueError: Missing required parameter: 'report_date'
```
**Answer**: Clear - the date for which reports should be generated

**Debugging benefit**: Logs, errors, and stack traces are self-documenting

---

#### 6. **Code Readability**

**Generic "date"**:
```python
def lambda_handler(event, context):
    date = event.get('date')
    if date:
        report_date = date.fromisoformat(date)
    else:
        report_date = datetime.now(bangkok_tz).date()
```
**Problem**: Variable name `date` shadows Python's `date` type
**Confusion**: `date.fromisoformat(date)` - which `date` is which?

**Specific "report_date"**:
```python
def lambda_handler(event, context):
    report_date_str = event.get('report_date')
    if report_date_str:
        report_date = date.fromisoformat(report_date_str)
    else:
        report_date = datetime.now(bangkok_tz).date()
```
**Clear**: `report_date_str` is string, `report_date` is `date` object, no shadowing

---

## What Improves with "date"

**Conciseness**:
- Shorter parameter name (4 chars vs 11 chars)
- Slightly less typing

**Simplicity**:
- Simpler mental model for "daily scheduler" use case
- Natural language alignment ("run for date X")

---

## What Breaks or Degrades with "date"

**Collision with existing code**:
- ❌ Query tool handler already uses `event.get('date')`
- ❌ Same parameter name, different semantics across Lambdas

**Ambiguity in multi-date scenarios**:
- ❌ Cannot distinguish report_date vs data_date vs execution_date
- ❌ Breaking change needed if scenarios expand

**Code clarity**:
- ❌ Shadows Python `date` type (readability issue)
- ❌ Error messages less specific
- ❌ Logs harder to grep (too generic)

**API design quality**:
- ❌ Violates self-documenting parameter principle
- ❌ Inconsistent with AWS naming conventions
- ❌ Poor extensibility

---

## Insights Revealed

### Hidden Assumption Exposed

**User's assumption**: "Date context is always obvious in scheduler"

**Reality**: System has **multiple date concepts** (report_date, data_date, execution_date, computed_at)

**Evidence**: Even in current simple scenario, we need to distinguish:
- When scheduler runs (execution_date: 08:00)
- What date reports are for (report_date: previous day)
- When data was collected (data_date: might lag)

**Lesson**: Generic names work only in **trivial single-concept** scenarios

---

### Trade-Off Clarified

**Simplicity vs Clarity**:
- "date" is simpler (shorter, less typing)
- "report_date" is clearer (self-documenting, unambiguous)

**Current decision**: Favor **clarity over brevity**
- Cost: 7 extra characters to type
- Benefit: No ambiguity, better errors, easier debugging, future-proof

**Validated**: Clarity wins for API design (industry standard: AWS uses specific names)

---

### Boundary Condition

**When generic "date" is acceptable**:
- Single-date system (no other date concepts)
- No existing code using `event.get('date')`
- No future scenarios requiring multiple dates
- Private API (only you use it)

**When specific "report_date" is required**:
- ✅ Multiple date types exist (report_date, data_date, execution_date) ← **TRUE**
- ✅ Existing code uses `event.get('date')` ← **TRUE** (query_tool_handler)
- ✅ Future scenarios likely (backfills, data lag) ← **TRUE**
- ✅ Shared API (multiple Lambdas, EventBridge) ← **TRUE**

**Conclusion**: Current system requires specific naming

---

## Recommendation

### Decision: ❌ NO - Keep "report_date"

**Rationale**:

1. **Collision avoidance**: Query tool handler already uses `event.get('date')`
2. **Self-documenting**: "report_date" clearly means "date for which report is generated"
3. **Future-proof**: Supports multiple date types without breaking changes
4. **Industry standard**: AWS uses specific date names (StartDate, ExecutionDate, etc.)
5. **Code clarity**: Avoids shadowing Python's `date` type
6. **Better debugging**: Specific error messages and log entries

**Cost of "date"**:
- Name collision (query_tool_handler conflict)
- Ambiguity in multi-date scenarios
- Breaking change if we ever need start_date/end_date
- Poor error messages
- Code readability issues (shadows `date` type)

**Benefit of "date"**:
- 7 fewer characters to type (marginal)

**Trade-off**: Clarity and maintainability >> 7 characters of typing

---

### Alternative Considered: "scheduled_date"

**If we wanted to be even more specific**:
```json
{
  "scheduled_date": "2026-01-04"
}
```

**Benefit**: Emphasizes this is the **scheduled execution date** for nightly run

**Problem**: Conflicts with "execution_date" (when it actually runs, might differ if delayed)

**Conclusion**: "report_date" is the sweet spot (specific but not over-specific)

---

### Action Items

**Current**:
- [x] Keep `report_date` as parameter name
- [x] Document rationale (this what-if analysis)
- [ ] Add comment in handler explaining parameter naming choice
- [ ] Ensure EventBridge input transformer uses `report_date` consistently

**If we reconsider later** (not recommended):
- Would need to update: Lambda handler, EventBridge transformer, tests, docs
- Breaking change for any manual invocations
- Must ensure no collision with query_tool_handler's `date` parameter

---

## Related Decisions

**Similar naming decisions in codebase**:
- `ticker` not `symbol` (explicit, matches DB column name)
- `report_text` not `text` (specific, avoids ambiguity)
- `chart_base64` not `chart` (explicit format)
- `pdf_s3_key` not `pdf_path` (specific storage location)

**Pattern**: Favor **specific, self-documenting names** over generic ones

**Principle**: Code is read 10x more than written - optimize for clarity

---

## References

**Current implementation**:
- `src/scheduler/get_report_list_handler.py:67` - Uses `report_date`
- `src/scheduler/query_tool_handler.py` - Already uses `date` (collision risk)

**API design principles**:
- AWS API naming conventions (StartDate, ExecutionDate, etc.)
- Self-documenting code principle
- Defensive programming (Principle #1: Fail fast with clear errors)

**Related analyses**:
- `.claude/validations/2026-01-04-nightly-scheduler-workflow-chain.md` - EventBridge input transformation
- `.claude/validations/2026-01-04-pdf-generation-two-path-understanding.md` - Parameter handling

---

## Summary

**Should we use "date" instead of "report_date"?** ❌ **NO**

**Why**:
1. Collision with existing query_tool_handler's `event.get('date')`
2. System has multiple date concepts (needs specific names)
3. Future scenarios require distinguishing date types
4. Industry standard favors specific names (AWS: StartDate, ExecutionDate)
5. Code clarity (avoids shadowing Python `date` type)
6. Better error messages and debugging

**User's intuition is correct for trivial cases**, but this system has:
- Multiple Lambdas (query_tool already uses 'date')
- Multiple date types (report, data, execution, computed)
- Future scenarios (backfills, data lag tracking)

**Trade-off**: 7 characters of typing vs clarity, maintainability, and collision-free API

**Decision**: Clarity wins. Keep `report_date`.
