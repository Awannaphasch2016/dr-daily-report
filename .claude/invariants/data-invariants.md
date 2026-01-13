# Data Invariants

**Domain**: Database, Aurora, Migrations, Schema, Timezone
**Load when**: database, migration, aurora, table, schema, data, timezone, ETL

**Related**: [Data Principles](../principles/data-principles.md), [Principle #3, #5, #14, #16]

---

## Critical Path

```
Schema Change → Migration → Deploy → Query → Display
```

Every data operation must preserve this invariant: **Data integrity is never compromised.**

---

## Level 4: Configuration Invariants

### Table Names
- [ ] New tables registered in `src/data/aurora/table_names.py`
- [ ] No hardcoded table names in queries (use constants)
- [ ] Removed tables removed from constants file

### Timezone
- [ ] `TZ = "Asia/Bangkok"` set in Lambda environment
- [ ] Aurora RDS parameter group has `time_zone = "Asia/Bangkok"`
- [ ] No `datetime.utcnow()` in code (use explicit Bangkok timezone)

### Database Connection
- [ ] `AURORA_HOST` configured in Doppler (all environments)
- [ ] `AURORA_USER` configured in Doppler
- [ ] `AURORA_PASSWORD` configured in Doppler
- [ ] `AURORA_DATABASE` configured in Doppler

### Verification Commands
```bash
# Check table names constant
grep "NEW_TABLE" src/data/aurora/table_names.py

# Check timezone config
doppler secrets get TZ -p dr-daily-report -c dev

# Verify no UTC usage
grep -r "utcnow" src/ && echo "FAIL: Found utcnow" || echo "PASS"
```

---

## Level 3: Infrastructure Invariants

### Aurora Connectivity
- [ ] Lambda can reach Aurora (VPC configuration)
- [ ] Security group allows Lambda → Aurora (port 3306)
- [ ] Connection pool healthy (not exhausted)
- [ ] SSL/TLS configured (if required)

### Migration Infrastructure
- [ ] Migration files exist in `migrations/` directory
- [ ] Migrations numbered sequentially (001_, 002_, etc.)
- [ ] No gaps in migration numbers

### Verification Commands
```bash
# Test Aurora connectivity
/dev "SELECT 1"

# Check VPC endpoint (if using)
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.*.rds"

# List migrations
ls -la migrations/*.sql
```

---

## Level 2: Data Invariants

### Schema Integrity
- [ ] Table schema matches code expectations
- [ ] All required columns exist
- [ ] Column types match Python type hints
- [ ] Indexes exist for query patterns

### Foreign Key Integrity
- [ ] No orphaned records
- [ ] Foreign keys reference valid records
- [ ] Cascade deletes configured correctly (if any)

### Data Quality
- [ ] No NULL in required fields
- [ ] Dates in Bangkok timezone
- [ ] JSON columns contain valid JSON
- [ ] DECIMAL precision appropriate (no truncation)

### Migration Safety
- [ ] Migration file immutable (never edited after commit)
- [ ] Reconciliation migrations use `IF NOT EXISTS`
- [ ] Rollback path documented
- [ ] Data backup taken before destructive migrations

### Verification Commands
```bash
# Check table schema
/dev "DESCRIBE daily_prices"

# Check for orphaned records
/dev "SELECT COUNT(*) FROM precomputed_reports r
      LEFT JOIN ticker_master t ON r.symbol = t.symbol
      WHERE t.symbol IS NULL"

# Check data freshness
/dev "SELECT MAX(date) FROM daily_prices"

# Verify JSON validity
/dev "SELECT symbol FROM daily_prices
      WHERE JSON_VALID(ohlcv) = 0 LIMIT 10"
```

---

## Level 1: Service Invariants

### Query Behavior
- [ ] Queries return expected results
- [ ] Query performance acceptable (< 1s for typical queries)
- [ ] No SQL injection vulnerabilities (parameterized queries)
- [ ] Transactions commit/rollback correctly

### Data Access Patterns
- [ ] Read operations don't modify data
- [ ] Write operations use transactions where needed
- [ ] Bulk operations don't timeout
- [ ] Connection released after operation

### Error Handling
- [ ] Database errors logged with context
- [ ] Failed operations don't leave partial data
- [ ] Connection errors trigger retry logic
- [ ] Deadlock handling implemented (if concurrent writes)

### Verification Commands
```bash
# Test query performance
/dev "EXPLAIN SELECT * FROM daily_prices WHERE symbol = 'ADVANC' ORDER BY date DESC LIMIT 30"

# Check for slow queries
/dev "SELECT * FROM information_schema.PROCESSLIST WHERE TIME > 5"

# Verify transaction isolation
/dev "SELECT @@transaction_isolation"
```

---

## Level 0: User Invariants

### Data Display
- [ ] Reports show correct data values
- [ ] Dates displayed in Bangkok timezone
- [ ] Numbers formatted correctly (decimals, thousands)
- [ ] No stale data shown to users

### Data Operations
- [ ] Users can view their data
- [ ] Data refreshes within expected timeframe
- [ ] Missing data shows helpful error (not blank)
- [ ] Charts display correct date ranges

### End-to-End
- [ ] Ticker search returns correct results
- [ ] Report generation uses fresh data
- [ ] Export functionality includes all data
- [ ] Historical data accessible

### Verification Commands
```bash
# Manual verification via Telegram
# Send: /report ADVANC
# Check: Dates in Bangkok timezone, values match Aurora

# Or via E2E test
pytest tests/e2e/test_report_data_accuracy.py -v
```

---

## Migration Invariants

### Before Migration

- [ ] Current schema documented
- [ ] Data backup created (if destructive)
- [ ] Rollback script prepared
- [ ] Code not deployed yet (migrations run FIRST)

### Migration Execution

- [ ] Migration runs without errors
- [ ] Schema change verified (`DESCRIBE table`)
- [ ] Data integrity preserved
- [ ] Indexes recreated (if dropped)

### After Migration

- [ ] Code deployed (now matches new schema)
- [ ] Queries work with new schema
- [ ] No performance regression
- [ ] Migration file NOT edited

### Rollback Procedure
```bash
# If migration fails:
# 1. Do NOT edit migration file
# 2. Run rollback script (if prepared)
# 3. Create NEW migration to fix

# Example rollback
/dev "source" migrations/018_rollback_drop_ticker_info.sql

# Verify rollback
/dev "DESCRIBE ticker_info"
```

---

## Anti-Patterns (What Breaks Invariants)

| Anti-Pattern | Invariant Violated | Fix |
|--------------|-------------------|-----|
| Hardcoded table name | Level 4 (config) | Use `table_names.py` constants |
| `datetime.utcnow()` | Level 4 (timezone) | Use `datetime.now(bangkok_tz)` |
| Edit migration file | Level 2 (immutable) | Create new migration |
| Deploy code before migration | Level 2 (schema) | Always migrate FIRST |
| Missing NULL check | Level 2 (data) | Validate before insert |
| No transaction for related inserts | Level 1 (consistency) | Use atomic transactions |

---

## Common Migration Patterns

### Adding New Table
```sql
-- migrations/XXX_add_ticker_fundamentals.sql
CREATE TABLE IF NOT EXISTS ticker_fundamentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    pe_ratio DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES ticker_master(symbol)
) ENGINE=InnoDB;

CREATE INDEX idx_fundamentals_symbol ON ticker_fundamentals(symbol);
```

**Post-migration checklist**:
- [ ] Table in `table_names.py`
- [ ] `DESCRIBE` matches expected schema
- [ ] Foreign key valid
- [ ] Index created

### Adding Column
```sql
-- migrations/XXX_add_volume_column.sql
ALTER TABLE daily_prices
ADD COLUMN IF NOT EXISTS adjusted_volume BIGINT DEFAULT NULL;
```

**Post-migration checklist**:
- [ ] Column exists (`DESCRIBE`)
- [ ] Default value correct
- [ ] Existing rows have NULL (expected)

### Removing Table
```sql
-- migrations/XXX_drop_deprecated_cache.sql
DROP TABLE IF EXISTS deprecated_cache;
```

**Post-migration checklist**:
- [ ] Table removed from `table_names.py`
- [ ] No code references table
- [ ] `SHOW TABLES` confirms removal

---

## Claiming "Data Work Done"

```markdown
✅ Data work complete: {description}

**Type**: {schema change | data migration | query optimization}
**Migration**: {migration file number, if applicable}

**Invariants Verified**:
- [x] Level 4: Table constants updated, timezone correct
- [x] Level 3: Aurora connectivity confirmed
- [x] Level 2: Schema matches, data intact, no orphans
- [x] Level 1: Queries work, performance acceptable
- [x] Level 0: User sees correct data

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {DESCRIBE output, query results, user test}
```

---

*Domain: data*
*Last updated: 2026-01-12*
