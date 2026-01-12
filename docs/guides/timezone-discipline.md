# Timezone Discipline Guide

**Principle #16** | Use Bangkok timezone (Asia/Bangkok, UTC+7) consistently across all system components.

---

## Overview

### Core Problem
Mixed timezones across system components cause date boundary bugs. When Lambda uses UTC but Aurora uses Bangkok time, cache lookups fail at date boundaries (21:00 UTC Dec 30 ≠ 04:00 Bangkok Dec 31).

### Key Insight
For Bangkok-based users with no UTC requirements, single-timezone standardization eliminates mental conversion overhead and prevents date boundary bugs. Choose ONE timezone and enforce it everywhere.

---

## Infrastructure Configuration

### Aurora MySQL

Set timezone in RDS parameter group:

```
Parameter: time_zone
Value: Asia/Bangkok
```

Verify after applying:

```sql
SELECT @@time_zone;
-- Should return: Asia/Bangkok
```

### Lambda Functions

Set TZ environment variable in Terraform:

```hcl
resource "aws_lambda_function" "api" {
  environment {
    variables = {
      TZ = "Asia/Bangkok"
    }
  }
}
```

Verify in Lambda:

```python
import os
print(os.environ.get("TZ"))  # Asia/Bangkok
```

### EventBridge Scheduler

EventBridge uses UTC cron expressions (platform limitation), but schedules execute at Bangkok time equivalent:

```hcl
# Run at 6:00 AM Bangkok = 23:00 UTC previous day
resource "aws_scheduler_schedule" "daily_etl" {
  schedule_expression = "cron(0 23 * * ? *)"  # UTC
}
```

**Conversion table**:
| Bangkok Time | UTC Cron |
|--------------|----------|
| 06:00 | `cron(0 23 * * ? *)` (prev day) |
| 08:00 | `cron(0 1 * * ? *)` |
| 18:00 | `cron(0 11 * * ? *)` |
| 23:00 | `cron(0 16 * * ? *)` |

---

## Code Patterns

### Explicit Timezone (Recommended)

Always use explicit timezone, never rely on environment:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

# CORRECT: Explicit Bangkok timezone
bangkok_tz = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok_tz).date()
now = datetime.now(bangkok_tz)

# For business dates (report dates, cache keys)
business_date = datetime.now(bangkok_tz).date()
```

### Implicit Timezone (Environment-Dependent)

Less safe but acceptable when TZ env var is guaranteed:

```python
from datetime import datetime

# ACCEPTABLE: Relies on TZ=Asia/Bangkok env var
today = datetime.now().date()

# Lambda with TZ=Asia/Bangkok will return Bangkok date
```

---

## Common Operations

### Cache Key Generation

```python
from datetime import datetime
from zoneinfo import ZoneInfo

def get_cache_key(symbol: str) -> str:
    """Generate cache key using Bangkok date."""
    bangkok = ZoneInfo("Asia/Bangkok")
    date_str = datetime.now(bangkok).strftime("%Y-%m-%d")
    return f"report:{symbol}:{date_str}"
```

### Date Boundary Handling

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def get_trading_date() -> date:
    """Get current trading date (Bangkok timezone)."""
    bangkok = ZoneInfo("Asia/Bangkok")
    now = datetime.now(bangkok)

    # If before market open (9:30 AM), use previous day
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return (now - timedelta(days=1)).date()
    return now.date()
```

### Database Queries

```python
from datetime import datetime
from zoneinfo import ZoneInfo

def query_prices(symbol: str, date: date) -> list:
    """Query prices for a specific Bangkok date."""
    # Aurora is configured with Asia/Bangkok timezone
    # Date comparisons work correctly without conversion
    query = """
        SELECT * FROM daily_prices
        WHERE symbol = %s AND trade_date = %s
    """
    return execute(query, (symbol, date))
```

### Timestamp Storage

```python
from datetime import datetime
from zoneinfo import ZoneInfo

def save_with_timestamp(data: dict) -> None:
    """Save data with Bangkok timestamp."""
    bangkok = ZoneInfo("Asia/Bangkok")
    data["created_at"] = datetime.now(bangkok)
    # Aurora stores as Bangkok time (no conversion needed)
    save_to_db(data)
```

---

## Anti-Patterns

### 1. Using datetime.utcnow()

```python
# WRONG: Implicit UTC, wrong for Bangkok business dates
from datetime import datetime

today = datetime.utcnow().date()  # UTC date!

# CORRECT: Explicit Bangkok
from zoneinfo import ZoneInfo
today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
```

### 2. Using datetime.now() Without Timezone

```python
# WRONG: Ambiguous, depends on TZ env var
today = datetime.now().date()  # Which timezone?

# CORRECT: Explicit timezone
from zoneinfo import ZoneInfo
today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
```

### 3. Missing TZ Environment Variable

```python
# WRONG: Silent default hides missing config
tz = os.environ.get("TZ", "UTC")  # Silently wrong!

# CORRECT: Fail fast
tz = os.environ.get("TZ")
if not tz:
    raise RuntimeError("TZ environment variable required")
```

### 4. Mixing Timezones

```python
# WRONG: UTC timestamp compared with Bangkok date
utc_now = datetime.utcnow()
bangkok_date = get_bangkok_date()
if utc_now.date() == bangkok_date:  # Bug at date boundary!
    ...

# CORRECT: Same timezone throughout
bangkok_tz = ZoneInfo("Asia/Bangkok")
bangkok_now = datetime.now(bangkok_tz)
bangkok_date = get_bangkok_date()
if bangkok_now.date() == bangkok_date:
    ...
```

### 5. Hardcoding UTC in Cron

```python
# WRONG: Cron comment says Bangkok but expression is wrong
# "Run at 6 AM Bangkok"
schedule = "cron(0 6 * * ? *)"  # This is 6 AM UTC!

# CORRECT: Convert Bangkok to UTC
# "Run at 6 AM Bangkok = 23:00 UTC previous day"
schedule = "cron(0 23 * * ? *)"
```

---

## Date Boundary Bug Scenario

### The Problem

```
Timeline (Bangkok is UTC+7):

  UTC:     Dec 30 21:00 ─────────────────── Dec 31 00:00
  Bangkok: Dec 31 04:00 ─────────────────── Dec 31 07:00
                   ↑
                   User requests report at this time
```

### Without Timezone Discipline

```python
# Lambda with TZ=UTC (wrong)
today = datetime.now().date()  # Dec 30 (UTC)

# User expects Dec 31 report (Bangkok)
# Lambda fetches Dec 30 data
# Cache miss or wrong data returned!
```

### With Timezone Discipline

```python
# Lambda with TZ=Asia/Bangkok (correct)
today = datetime.now().date()  # Dec 31 (Bangkok)

# Or explicit (safest)
bangkok = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok).date()  # Dec 31

# Lambda fetches Dec 31 data
# Correct data returned!
```

---

## Verification Checklist

### Infrastructure

- [ ] Aurora RDS parameter group: `time_zone = Asia/Bangkok`
- [ ] Lambda environment variable: `TZ = Asia/Bangkok`
- [ ] EventBridge cron converted to UTC equivalent
- [ ] Doppler config includes TZ for all environments

### Code

- [ ] `datetime.now()` uses explicit `ZoneInfo("Asia/Bangkok")`
- [ ] No usage of `datetime.utcnow()` for business dates
- [ ] Cache keys use Bangkok dates
- [ ] Database queries use Bangkok dates

### Testing

- [ ] Test at date boundary (23:00 UTC = 06:00 Bangkok next day)
- [ ] Verify cache keys match across Lambda and client
- [ ] Verify scheduled jobs run at correct Bangkok time

---

## Real Incident: Cache Miss at Date Boundary

### Timeline

1. **05:30 Bangkok (22:30 UTC)**: User requests report
2. **Lambda (TZ=UTC)**: Generates cache key with Dec 30
3. **Cache lookup**: Finds cached report for Dec 30 ✓
4. **06:30 Bangkok (23:30 UTC)**: User requests report again
5. **Lambda (TZ=UTC)**: Still Dec 30 in UTC
6. **User expects**: Dec 31 report (it's Dec 31 in Bangkok!)
7. **Result**: Wrong report served

### Fix

```python
# Before: Implicit UTC
today = datetime.now().date()

# After: Explicit Bangkok
bangkok = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok).date()
```

---

## Integration with Principles

| Principle | Integration |
|-----------|-------------|
| #1 Defensive Programming | Fail-fast if TZ missing |
| #15 Infrastructure Contract | TZ is part of Lambda contract |
| #19 Cross-Boundary Testing | Test date boundary scenarios |
| #23 Configuration Variation | TZ varies by environment → Doppler |

---

## See Also

- [CLAUDE.md Principle #16](../../.claude/CLAUDE.md) - Core principle
- [Timezone Verification](.claude/validations/2025-12-30-etl-bangkok-timezone-verification.md) - Original validation
- [Infrastructure-Application Contract Guide](infrastructure-application-contract.md) - TZ as contract element

---

*Guide version: 2026-01-12*
*Principle: #16 Timezone Discipline*
*Status: Active - extracted from CLAUDE.md for right abstraction level*
