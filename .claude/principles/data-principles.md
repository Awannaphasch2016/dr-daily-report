# Data Principles Cluster

**Load when**: Aurora queries, database migrations, ETL operations, timezone handling, data precomputation

**Principles**: #3, #5, #14, #16

**Related skills**: [database-migration](../skills/database-migration/)

---

## Principle #3: Aurora-First Data Architecture

Aurora is the source of truth. Data precomputed nightly via scheduler (46 tickers). Report APIs are read-only and query Aurora directly. If data missing, APIs return error (fail-fast) instead of falling back to external APIs. Ensures consistent performance and prevents unpredictable latency.

**Key insight**: External API calls during requests = unpredictable latency. Precomputed data = consistent performance.

**Data flow**:
```
Nightly scheduler → yfinance/NewsAPI → Aurora (precompute)
                                            ↓
User request → Lambda → Aurora (read-only) → Response
```

**Anti-patterns**:
- ❌ Calling external APIs during user requests
- ❌ Falling back to external APIs when Aurora data missing
- ❌ Caching external API responses in Lambda memory

---

## Principle #5: Database Migrations Immutability

Migration files are immutable once committed—never edit them. Always create new migrations for schema changes. Use reconciliation migrations (idempotent operations: CREATE TABLE IF NOT EXISTS) when database state is unknown. Prevents migration conflicts and unclear execution states. Verify with `DESCRIBE table_name` after applying.

**Migration workflow**:
1. Create new migration file: `db/migrations/0XX_description.sql`
2. Use idempotent operations where possible
3. Apply migration BEFORE deploying code that uses new schema
4. Verify with `DESCRIBE table_name`

**Reconciliation migration pattern**:
```sql
-- Idempotent: safe to run multiple times
CREATE TABLE IF NOT EXISTS new_table (...);
ALTER TABLE existing_table ADD COLUMN IF NOT EXISTS new_col VARCHAR(255);
```

See [database-migration skill](../skills/database-migration/).

---

## Principle #14: Table Name Centralization

All Aurora table names defined in `src/data/aurora/table_names.py` as constants. Centralized constants (not env vars) since names don't vary per environment. Use f-string interpolation for table names, parameterized queries for user data (SQL injection safety).

**Usage pattern**:
```python
from src.data.aurora.table_names import DAILY_PRICES, TICKER_MASTER

# Table names via f-string (safe - centralized constants)
query = f"SELECT * FROM {DAILY_PRICES} WHERE symbol = %s"

# User data via parameterized query (safe - prevents SQL injection)
cursor.execute(query, (symbol,))
```

**Renaming workflow**: Update constant → create migration → run tests → deploy.

See [Code Style Guide](../../docs/CODE_STYLE.md#database-patterns).

---

## Principle #16: Timezone Discipline

Use Bangkok timezone (Asia/Bangkok, UTC+7) consistently across all system components. Single-timezone standardization eliminates mental conversion overhead and prevents date boundary bugs.

**Infrastructure**:
- Aurora: `time_zone = "Asia/Bangkok"` (RDS parameter group)
- Lambda: `TZ = "Asia/Bangkok"` (environment variable)
- EventBridge: UTC cron → Bangkok equivalent

**Code pattern**:
```python
from zoneinfo import ZoneInfo

# ALWAYS explicit timezone for business dates
bangkok_tz = ZoneInfo("Asia/Bangkok")
today = datetime.now(bangkok_tz).date()
```

**Anti-patterns**:
- ❌ Using `datetime.utcnow()` (implicit UTC)
- ❌ Using `datetime.now()` without explicit timezone
- ❌ Missing TZ env var in Lambda

**Date boundary bug**: At 21:00 UTC Dec 30 = 04:00 Bangkok Dec 31. Cache key with wrong timezone causes cache miss.

See [Timezone Discipline Guide](../../docs/guides/timezone-discipline.md).

---

## Quick Checklist

Before Aurora queries:
- [ ] Table names from `table_names.py` constants
- [ ] User input via parameterized queries
- [ ] Timezone-aware datetime operations

Before migrations:
- [ ] New migration file (never edit existing)
- [ ] Idempotent operations where possible
- [ ] Migration applied BEFORE code deployment
- [ ] Verified with DESCRIBE after applying

Data freshness checks:
- [ ] `SELECT COUNT(*) FROM daily_prices WHERE date = CURDATE()` → 46 rows
- [ ] `SELECT MAX(date) FROM daily_prices` → today's date

---

*Cluster: data-principles*
*Last updated: 2026-01-12*
