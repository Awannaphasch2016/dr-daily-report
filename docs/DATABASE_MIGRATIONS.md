# Database Migrations Guide

**Purpose:** Comprehensive guide for database schema migrations with focus on reconciliation patterns for unknown database states.

**When to Use This Guide:**
- Creating new tables or columns in Aurora
- Reconciling unknown/partially-migrated database state
- Migrating production databases with zero downtime
- Understanding MySQL-specific migration gotchas

**Note (2025-12-30):** Examples reference `ticker_info` table (removed in migration 018). Principles remain valid - examples show historical patterns. For current migrations, see `db/migrations/018_drop_ticker_info_table.sql` as reference.

---

## Table of Contents

1. [Migration Philosophy](#migration-philosophy)
2. [Reconciliation Migrations](#reconciliation-migrations)
3. [Traditional vs Reconciliation Approach](#traditional-vs-reconciliation-approach)
4. [Migration File Structure](#migration-file-structure)
5. [MySQL-Specific Considerations](#mysql-specific-considerations)
6. [Idempotent Operations Reference](#idempotent-operations-reference)
7. [Common Patterns](#common-patterns)
8. [Migration Tracking](#migration-tracking)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Testing Migrations](#testing-migrations)

---

## Migration Philosophy

**Core Principles:**

1. **Idempotent**: Migrations can be run multiple times safely
2. **Additive**: Prefer adding columns over modifying existing schema
3. **Backwards Compatible**: Old code continues working during migration
4. **Explicit Failures**: Check rowcount, log errors, fail visibly
5. **No Data in Schema Migrations**: Separate schema changes from data backfills

**The Golden Rule:**

> "A migration should be safe to run against any intermediate state of the database and produce the desired final state."

This means:
- ✅ Can run against empty database (creates everything)
- ✅ Can run against partially migrated database (creates only missing pieces)
- ✅ Can run against fully migrated database (changes nothing, no errors)
- ✅ Can run multiple times (idempotent, no duplicate key errors)

---

## Reconciliation Migrations

**When to Use Reconciliation Migrations:**

- **Unknown database state**: Production database may have been manually altered
- **Partial migrations**: Some migration files executed, others not
- **Duplicate numbering**: Multiple `001_*.sql`, `002_*.sql` files with conflicts
- **Migration history lost**: No tracking of which migrations were applied
- **Fresh start needed**: Too many conflicting migrations to reconcile sequentially

**Reconciliation Migration Pattern:**

Instead of tracking which migrations have been applied, write a single migration that describes the **desired end state** using idempotent operations.

### Example: Traditional Sequential Migrations

```sql
-- 001_create_users.sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50)
);

-- 002_add_email.sql
ALTER TABLE users ADD COLUMN email VARCHAR(100);

-- 003_add_created_at.sql
ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

**Problems:**
- Must run in exact order
- Fails if 001 already executed but 002/003 missing
- No way to know which migrations were applied
- Can't re-run without errors

### Example: Reconciliation Migration

```sql
-- 001_reconcile_users_schema.sql
-- Purpose: Reconcile users table to desired schema
-- Safe to run: Against empty DB, partial migrations, or complete schema
-- Idempotent: Can run multiple times without errors

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add columns if they don't exist (MySQL 8.0.12+)
-- Note: MySQL < 8.0.12 doesn't support IF NOT EXISTS for ALTER TABLE
-- For older MySQL, check INFORMATION_SCHEMA first or use stored procedures
```

**Benefits:**
- ✅ Works regardless of current database state
- ✅ Creates table if missing
- ✅ Safe to re-run (IF NOT EXISTS)
- ✅ Single source of truth for desired schema
- ✅ No migration tracking needed

---

## Traditional vs Reconciliation Approach

| Aspect | Traditional Sequential | Reconciliation |
|--------|----------------------|----------------|
| **Assumption** | Clean slate or known state | Unknown/partial state |
| **Tracking** | Requires migration table | Optional (idempotency handles it) |
| **Execution** | Must run in strict order | Any order, any state |
| **Re-runnable** | No (fails on duplicates) | Yes (idempotent) |
| **Best For** | Greenfield projects | Legacy/production databases |
| **Rollback** | Requires down-migrations | N/A (additive only) |
| **Team Collaboration** | Merge conflicts on numbers | Single file, easier merges |

**When to Use Traditional:**
- Greenfield project with full control
- Migration tracking infrastructure exists
- Team discipline on sequential numbering
- Need to track exact migration history

**When to Use Reconciliation:**
- Production database with unknown changes
- Lost migration history
- Multiple conflicting migration files
- Need to support any intermediate state

---

## Migration File Structure

### Reconciliation Migration Header Template

```sql
-- ============================================================================
-- Migration: 001_complete_schema.sql
-- Type: Reconciliation Migration
-- Purpose: Reconcile Aurora schema to match application requirements
-- Created: 2025-12-12
-- ============================================================================
--
-- CHARACTERISTICS:
-- - Idempotent: Can run multiple times safely (uses IF NOT EXISTS)
-- - Additive: Only creates missing tables/columns (no DROP, no destructive ops)
-- - No data changes: Schema only (data backfills go in separate migrations)
--
-- SAFETY:
-- - Risk Level: LOW (only creates missing tables, no data changes)
-- - Locking: None (CREATE TABLE IF NOT EXISTS doesn't lock existing tables)
-- - Expected Runtime: <30 seconds (11 tables, all IF NOT EXISTS checks)
--
-- PRE-CONDITIONS:
-- - Aurora may have 0-11 tables already created
-- - Some tables may have partial schema (missing columns)
-- - No assumption about which prior migrations were executed
--
-- POST-CONDITIONS:
-- - All 11 tables exist with correct schema
-- - Existing data preserved (no DROP operations)
-- - Application INSERT queries will succeed
--
-- VERIFICATION:
-- Run these queries after migration to verify success:
--
-- -- Check table count
-- SELECT COUNT(*) as table_count
-- FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_SCHEMA = DATABASE();
-- -- Expected: 11
--
-- -- Check specific tables exist
-- SELECT TABLE_NAME
-- FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_SCHEMA = DATABASE()
-- AND TABLE_NAME IN (
--   'ticker_info', 'daily_prices', 'ticker_cache_metadata',
--   'precomputed_reports', 'ticker_data_cache', 'fund_data',
--   'daily_indicators', 'indicator_percentiles', 'comparative_features',
--   'ticker_master', 'ticker_aliases'
-- );
-- -- Expected: 11 rows
--
-- ROLLBACK:
-- Not needed - migration is additive only (safe to leave in place)
-- If absolutely necessary: DROP TABLE statements (data loss!)
--
-- ============================================================================

-- Your migration SQL here
CREATE TABLE IF NOT EXISTS ticker_info (...);
```

### Migration File Naming Conventions

**Reconciliation Migrations:**
```
db/migrations/
└── 001_complete_schema.sql           # Describes desired end state
```

**Traditional Sequential Migrations:**
```
db/migrations/
├── 001_initial_schema.sql
├── 002_add_user_columns.sql
├── 003_create_reports_table.sql
└── 004_add_indexes.sql
```

**Versioned Migrations (with timestamps):**
```
db/migrations/
├── 20251212_001_complete_schema.sql
├── 20251213_002_add_indexes.sql
└── 20251214_003_backfill_data.sql
```

---

## MySQL-Specific Considerations

### DDL Characteristics

**MySQL DDL Auto-Commits:**
```sql
-- WARNING: This auto-commits the transaction!
START TRANSACTION;
INSERT INTO users VALUES (1, 'alice');
ALTER TABLE users ADD COLUMN email VARCHAR(100);  -- Auto-commits!
-- Previous INSERT is now committed (can't rollback)
```

**Implication:** Can't rollback schema changes. Must design migrations to be additive and safe.

### IF NOT EXISTS Support

**CREATE TABLE (all MySQL versions):**
```sql
CREATE TABLE IF NOT EXISTS users (...);  -- ✅ Supported
```

**ALTER TABLE (MySQL 8.0.12+ only):**
```sql
-- MySQL 8.0.12+
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS email VARCHAR(100);  -- ✅ Supported

-- MySQL < 8.0.12
-- ❌ Not supported - must check INFORMATION_SCHEMA first
```

**Workaround for MySQL < 8.0.12:**
```sql
-- Check if column exists before adding
SET @column_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'email'
);

SET @sql = IF(
  @column_exists = 0,
  'ALTER TABLE users ADD COLUMN email VARCHAR(100)',
  'SELECT "Column already exists" AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

### ALGORITHM=INSTANT (MySQL 8.0.12+)

**Online DDL without table rebuild:**
```sql
-- Add column without locking table
ALTER TABLE users
  ADD COLUMN email VARCHAR(100),
  ALGORITHM=INSTANT;
```

**When INSTANT works:**
- ✅ Adding columns at end of table
- ✅ Adding/dropping virtual generated columns
- ✅ Adding/dropping column default values
- ✅ Modifying ENUM/SET definition (appending values)

**When INSTANT doesn't work (falls back to INPLACE/COPY):**
- ❌ Adding columns in middle of table
- ❌ Changing column type
- ❌ Adding indexes
- ❌ Changing NOT NULL constraints

**Best Practice:**
```sql
-- Explicitly specify ALGORITHM to fail fast if INSTANT not possible
ALTER TABLE users
  ADD COLUMN email VARCHAR(100),
  ALGORITHM=INSTANT;  -- Fails immediately if not possible

-- Or allow fallback
ALTER TABLE users
  ADD COLUMN email VARCHAR(100),
  ALGORITHM=INPLACE;  -- Tries INSTANT, falls back to INPLACE if needed
```

### ENUM Type Considerations

**Silent Failures:**
```sql
CREATE TABLE users (
    status ENUM('active', 'inactive')
);

-- Code tries to insert 'pending' - FAILS SILENTLY (becomes empty string!)
INSERT INTO users (status) VALUES ('pending');  -- ✗ No error, wrong data

-- Query returns 0 rows affected
SELECT ROW_COUNT();  -- Returns 1 (misleading!)
SELECT * FROM users WHERE status = 'pending';  -- Returns 0 rows
SELECT * FROM users WHERE status = '';  -- Returns the "pending" row!
```

**Best Practice:**
```sql
-- Prefer VARCHAR with CHECK constraint (MySQL 8.0.16+)
CREATE TABLE users (
    status VARCHAR(20) CHECK (status IN ('active', 'inactive', 'pending'))
);

-- Or validate in application code before INSERT
-- Or add column comment documenting valid values
```

### Foreign Key Behavior

**FK Constraint Failure (Sometimes Silent):**
```sql
-- Parent table
CREATE TABLE users (id INT PRIMARY KEY);

-- Child table with FK
CREATE TABLE posts (
    id INT PRIMARY KEY,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Try to insert post with non-existent user
INSERT INTO posts (id, user_id) VALUES (1, 999);
-- MySQL 5.7: Raises error immediately
-- MySQL 8.0: Raises error immediately
-- But: If FK constraint is DEFERRED or ON DELETE SET NULL...
-- May succeed with NULL or delayed check!
```

**Best Practice:**
```python
# Always check rowcount after INSERT
rowcount = cursor.execute(insert_query, params)
if rowcount == 0:
    logger.error(f"INSERT affected 0 rows - FK constraint or ENUM mismatch?")
    return False
return True
```

---

## Idempotent Operations Reference

### Safe Idempotent DDL

```sql
-- ✅ CREATE TABLE
CREATE TABLE IF NOT EXISTS users (...);

-- ✅ CREATE INDEX (MySQL 5.7.4+)
CREATE INDEX IF NOT EXISTS idx_username ON users(username);

-- ✅ DROP TABLE (safe if table might not exist)
DROP TABLE IF EXISTS old_table;

-- ✅ DROP INDEX (MySQL 5.7.4+)
DROP INDEX IF EXISTS idx_old ON users;
```

### Conditional ALTER TABLE (MySQL 8.0.12+)

```sql
-- ✅ Add column if not exists
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS email VARCHAR(100);

-- ✅ Drop column if exists
ALTER TABLE users
  DROP COLUMN IF EXISTS old_column;

-- ✅ Add index if not exists
ALTER TABLE users
  ADD INDEX IF NOT EXISTS idx_email (email);
```

### Checking Before Altering (MySQL < 8.0.12)

```sql
-- Check if column exists
SELECT COUNT(*) INTO @col_exists
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME = 'email';

-- Conditionally add column
SET @sql = IF(
  @col_exists = 0,
  'ALTER TABLE users ADD COLUMN email VARCHAR(100)',
  'SELECT "Column exists" AS msg'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

---

## Common Patterns

### Pattern 1: Reconcile Complete Schema

**Use Case:** Unknown database state, need to ensure all tables exist.

```sql
-- Creates all missing tables without touching existing ones
CREATE TABLE IF NOT EXISTS ticker_info (...);
CREATE TABLE IF NOT EXISTS daily_prices (...);
CREATE TABLE IF NOT EXISTS precomputed_reports (...);
-- ... all tables
```

**Benefits:**
- Works on empty database
- Works on partial database
- Works on complete database
- No errors, no duplicate tables

### Pattern 2: Add Missing Columns (Expand Pattern)

**Use Case:** Application needs new columns, but some production databases may already have them.

```sql
-- MySQL 8.0.12+
ALTER TABLE precomputed_reports
  ADD COLUMN IF NOT EXISTS strategy VARCHAR(50),
  ADD COLUMN IF NOT EXISTS generation_time_ms INT,
  ALGORITHM=INSTANT;  -- No table lock

-- Verification
SELECT COUNT(*) as new_columns
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'precomputed_reports'
  AND COLUMN_NAME IN ('strategy', 'generation_time_ms');
-- Expected: 2
```

### Pattern 3: Chunked Data Backfill

**Use Case:** Populate new column with computed values (millions of rows).

**BAD (locks table for hours):**
```sql
-- ❌ Don't do this
UPDATE precomputed_reports
SET strategy = 'singlestage';  -- Locks entire table!
```

**GOOD (chunked, resumable):**
```sql
-- Create tracking table
CREATE TABLE IF NOT EXISTS migration_checkpoints (
    migration_name VARCHAR(100) PRIMARY KEY,
    last_id BIGINT,
    completed_at TIMESTAMP NULL
);

-- Backfill in chunks (run multiple times until done)
SET @batch_size = 10000;
SET @last_id = COALESCE(
  (SELECT last_id FROM migration_checkpoints WHERE migration_name = 'backfill_strategy'),
  0
);

UPDATE precomputed_reports
SET strategy = 'singlestage'
WHERE id > @last_id
  AND strategy IS NULL
ORDER BY id
LIMIT @batch_size;

-- Update checkpoint
INSERT INTO migration_checkpoints (migration_name, last_id)
VALUES ('backfill_strategy', @last_id + @batch_size)
ON DUPLICATE KEY UPDATE last_id = VALUES(last_id);

-- Check progress
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN strategy IS NULL THEN 1 ELSE 0 END) as remaining
FROM precomputed_reports;
```

**Benefits:**
- Small locks (10k rows at a time)
- Resumable (checkpoint tracking)
- Monitorable (progress queries)
- Low impact on live traffic

### Pattern 4: Expand → Migrate → Contract

**Use Case:** Rename column without downtime.

**Phase 1: Expand (add new column)**
```sql
-- Migration 1: Add new column
ALTER TABLE users
  ADD COLUMN email_address VARCHAR(100),  -- New name
  ALGORITHM=INSTANT;

-- Deploy code that writes to BOTH columns
-- Old code: writes `email`
-- New code: writes both `email` and `email_address`
```

**Phase 2: Migrate (backfill data)**
```sql
-- Migration 2: Copy data in chunks
UPDATE users
SET email_address = email
WHERE email_address IS NULL
LIMIT 10000;
-- Run until all rows migrated
```

**Phase 3: Contract (remove old column)**
```sql
-- Migration 3: After all code deployed and data migrated
ALTER TABLE users DROP COLUMN email;  -- Remove old column

-- Deploy code that only uses `email_address`
```

**Benefits:**
- Zero downtime
- Rollback possible at each phase
- Old code keeps working during migration

---

## Migration Tracking

### Option 1: No Tracking (Reconciliation Pattern)

**When:** Using idempotent reconciliation migrations.

**How:** Migrations validate current schema and apply only missing changes.

**Pros:**
- ✅ Simple - no tracking table needed
- ✅ Works with unknown state
- ✅ Can re-run anytime

**Cons:**
- ❌ No audit history
- ❌ Can't tell which migrations ran
- ❌ Hard to debug "what changed when"

### Option 2: Migration Version Table (Traditional)

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,
    applied_by VARCHAR(100),
    INDEX idx_applied_at (applied_at DESC)
) ENGINE=InnoDB;
```

**Usage:**
```sql
-- Before running migration
SELECT version FROM schema_migrations WHERE version = '001_complete_schema';
-- If exists: skip
-- If not exists: run migration, then insert record

INSERT INTO schema_migrations (version, description, execution_time_ms, applied_by)
VALUES ('001_complete_schema', 'Complete Aurora schema reconciliation', 850, 'lambda:scheduler');
```

**Benefits:**
- ✅ Audit trail
- ✅ Know exactly what ran when
- ✅ Can query migration history

**Drawbacks:**
- ❌ More complex (need tracking logic)
- ❌ Can get out of sync with reality

### Option 3: Lambda Environment Variable

**Pattern:**
```python
# Lambda handler
def execute_migration(event):
    migration_file = event['migration_file']

    # Check if already executed
    executed_migrations = os.getenv('EXECUTED_MIGRATIONS', '').split(',')
    if migration_file in executed_migrations:
        return {'statusCode': 200, 'message': 'Already executed'}

    # Run migration
    run_sql_file(migration_file)

    # Update environment variable
    # (requires Lambda function update - external process)
```

**Pros:**
- ✅ No database table needed
- ✅ Version-controlled (in Terraform/CloudFormation)

**Cons:**
- ❌ Can't update from Lambda (need external process)
- ❌ Not queryable
- ❌ Limited to 4KB total env vars

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Destructive Migrations

**Bad:**
```sql
-- Destroys existing data!
DROP TABLE users;
CREATE TABLE users (...);
```

**Good:**
```sql
-- Preserves existing data
CREATE TABLE IF NOT EXISTS users (...);
```

### ❌ Anti-Pattern 2: Schema + Data in Same Migration

**Bad:**
```sql
-- Mixing schema and data
CREATE TABLE users (...);
INSERT INTO users VALUES (1, 'admin');  -- Fails on re-run (duplicate key)
```

**Good:**
```sql
-- Separate files
-- 001_schema.sql
CREATE TABLE IF NOT EXISTS users (...);

-- 002_seed_data.sql (optional, idempotent)
INSERT INTO users (id, username)
VALUES (1, 'admin')
ON DUPLICATE KEY UPDATE username = VALUES(username);
```

### ❌ Anti-Pattern 3: Assuming Migration Order

**Bad:**
```sql
-- 003_add_foreign_key.sql
-- Assumes 001 and 002 ran successfully
ALTER TABLE posts
  ADD FOREIGN KEY (user_id) REFERENCES users(id);  -- Fails if users table missing!
```

**Good:**
```sql
-- Check prerequisite exists
SELECT COUNT(*) INTO @users_exists
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users';

SET @sql = IF(
  @users_exists > 0,
  'ALTER TABLE posts ADD FOREIGN KEY (user_id) REFERENCES users(id)',
  'SELECT "Prerequisite users table missing" AS error'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
```

### ❌ Anti-Pattern 4: Silent Failures

**Bad:**
```python
# Assumes success if no exception
cursor.execute(insert_query, params)
return True  # But what if 0 rows affected?
```

**Good:**
```python
rowcount = cursor.execute(insert_query, params)
if rowcount == 0:
    logger.error(f"INSERT affected 0 rows for {params}")
    return False
return True
```

### ❌ Anti-Pattern 5: No Verification Queries

**Bad:**
```sql
-- Run migration, hope it worked
CREATE TABLE IF NOT EXISTS users (...);
-- Did it work? Who knows!
```

**Good:**
```sql
-- Migration includes verification
CREATE TABLE IF NOT EXISTS users (...);

-- Verify table exists
SELECT COUNT(*) INTO @table_exists
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users';

SELECT IF(@table_exists = 1, 'SUCCESS', 'FAILED') AS migration_status;
```

### ❌ Anti-Pattern 6: Editing Existing Migration Files

**The Migration Immutability Principle:**
> Once a migration file is committed to version control, it is immutable. Never edit it - create a new migration instead.

**Why Immutability Matters:**
- **Reproducibility**: Git history shows what schema changes were made when
- **Auditability**: Can trace schema evolution through migration file sequence
- **Team Coordination**: Other developers may have applied the old version
- **Environment Divergence**: Editing creates different schemas in different environments

**Bad:**
```sql
-- 001_create_users.sql (edited after commit)
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100)  -- ← Added this line after initial commit
);
```

**What happens:**
- Dev A applies 001 before edit (no email column)
- Dev B applies 001 after edit (has email column)
- Production applied 001 before edit (no email column)
- Result: Schema divergence across environments

**Good:**
```sql
-- 001_create_users.sql (never edited after commit)
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50)
);

-- 002_add_email.sql (new migration)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(100);
```

**Exception: Uncommitted Migrations**
- Migration files NOT YET committed to version control CAN be edited
- Once committed (`git commit`), they're immutable
- If you catch a mistake before committing, edit freely
- After commit, create a new migration file

**Recovery from Edited Migrations:**

If you accidentally edited a migration that was already applied:

1. **Revert the edit** (restore original file)
2. **Create new migration** with the intended change
3. **Document in commit message** what happened and why

Example:
```bash
# Revert bad edit
git checkout HEAD~1 -- db/migrations/001_complete_schema.sql

# Create new migration
vim db/migrations/008_fix_ticker_id_type.sql

# Commit with explanation
git commit -m "fix: Revert 001 edit, create 008 for ticker_id type change

- Accidentally edited 001_complete_schema.sql after it was applied
- Restored original 001 to maintain migration history integrity
- Created 008_fix_ticker_id_type.sql with intended change"
```

---

## Testing Migrations

### Pre-Deployment Testing

**1. Test Against Empty Database**
```bash
# Create fresh database
mysql -e "CREATE DATABASE test_migration;"

# Run migration
mysql test_migration < db/migrations/001_complete_schema.sql

# Verify table count
mysql -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='test_migration';"
# Expected: 11
```

**2. Test Idempotency (Re-run)**
```bash
# Run migration again
mysql test_migration < db/migrations/001_complete_schema.sql

# Should succeed with no errors
# Verify table count unchanged
mysql -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='test_migration';"
# Expected: 11 (not 22!)
```

**3. Test Against Partial State**
```bash
# Create database with some tables
mysql -e "CREATE DATABASE partial_migration;"
mysql partial_migration -e "CREATE TABLE ticker_info (id INT);"
mysql partial_migration -e "CREATE TABLE daily_prices (id INT);"

# Run full migration
mysql partial_migration < db/migrations/001_complete_schema.sql

# Should create missing 9 tables, leave existing 2 alone
mysql -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='partial_migration';"
# Expected: 11
```

### Integration Testing

**Python Test Pattern:**
```python
import pytest
import boto3
import pymysql
from datetime import datetime, timedelta

class TestMigration:
    def setup_method(self):
        self.lambda_client = boto3.client('lambda')
        self.logs_client = boto3.client('logs')
        self.db = pymysql.connect(
            host=os.getenv('AURORA_HOST'),
            user=os.getenv('AURORA_USER'),
            password=os.getenv('AURORA_PASSWORD'),
            database=os.getenv('AURORA_DATABASE')
        )

    def test_migration_creates_all_tables(self):
        """Verify migration creates all 11 required tables"""
        # Invoke Lambda migration
        response = self.lambda_client.invoke(
            FunctionName='dr-daily-report-scheduler-dev',
            Payload=json.dumps({
                'action': 'execute_migration',
                'migration_file': 'db/migrations/001_complete_schema.sql'
            })
        )

        # Check Lambda succeeded
        assert response['StatusCode'] == 200
        payload = json.loads(response['Payload'].read())
        assert 'errorMessage' not in payload

        # Check CloudWatch logs for errors
        log_events = self.logs_client.filter_log_events(
            logGroupName='/aws/lambda/dr-daily-report-scheduler-dev',
            startTime=int((datetime.now() - timedelta(minutes=2)).timestamp() * 1000),
            filterPattern='ERROR'
        )
        assert len(log_events['events']) == 0

        # Verify tables exist in Aurora
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT COUNT(*) as table_count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
        """)
        result = cursor.fetchone()
        assert result[0] == 11, f"Expected 11 tables, found {result[0]}"

    def test_migration_is_idempotent(self):
        """Verify migration can run multiple times safely"""
        # Run migration twice
        for i in range(2):
            response = self.lambda_client.invoke(
                FunctionName='dr-daily-report-scheduler-dev',
                Payload=json.dumps({
                    'action': 'execute_migration',
                    'migration_file': 'db/migrations/001_complete_schema.sql'
                })
            )
            assert response['StatusCode'] == 200

        # Verify still only 11 tables (not 22!)
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
        """)
        result = cursor.fetchone()
        assert result[0] == 11
```

### Schema Validation Tests

**Test Schema Matches Application Requirements:**
```python
def test_precomputed_reports_has_all_columns(self):
    """Verify precomputed_reports has all columns needed by INSERT queries"""
    cursor = self.db.cursor()
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'precomputed_reports'
        ORDER BY COLUMN_NAME
    """)

    columns = [row[0] for row in cursor.fetchall()]

    # Columns required by INSERT queries in precompute_service.py
    required = [
        'id', 'ticker_id', 'symbol', 'report_date',
        'report_text', 'report_json',
        'strategy', 'generation_time_ms', 'mini_reports', 'chart_base64',
        'status', 'error_message',
        'computed_at', 'expires_at', 'created_at', 'updated_at'
    ]

    for col in required:
        assert col in columns, f"Missing column: {col}"
```

---

## Quick Reference

### Migration Checklist

Before deploying a migration:

- [ ] Migration header complete with purpose, safety, pre/post conditions
- [ ] Uses idempotent operations (IF NOT EXISTS)
- [ ] No destructive operations (DROP TABLE, TRUNCATE)
- [ ] No data changes (schema only)
- [ ] Includes verification queries in header
- [ ] Tested against empty database
- [ ] Tested for idempotency (re-run)
- [ ] Tested against partial state
- [ ] Schema validation tests pass
- [ ] CloudWatch logs checked for errors

### Common Commands

```bash
# Execute migration via Lambda
aws lambda invoke \
  --function-name dr-daily-report-scheduler-dev \
  --payload '{"action":"execute_migration","migration_file":"db/migrations/001_complete_schema.sql"}' \
  /tmp/migration-result.json

# Check result
cat /tmp/migration-result.json | jq

# Verify table count
mysql -h $AURORA_HOST -u $AURORA_USER -p$AURORA_PASSWORD -e \
  "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='ticker_data';"

# Run schema validation tests
pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v
```

---

## Aurora as Source of Truth

The `precomputed_reports` table is the **primary data store** for report generation, not a cache layer.

### Schema

```sql
CREATE TABLE precomputed_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    report_text TEXT,              -- Final Thai report
    report_json JSON,              -- Complete AgentState (all data sources)
    strategy ENUM('single-stage', 'multi-stage'),
    generation_time_ms INT,
    chart_base64 LONGTEXT,
    status VARCHAR(20),
    expires_at DATETIME,           -- 24-hour TTL
    computed_at TIMESTAMP,
    UNIQUE KEY unique_report (ticker_id, report_date)
);
```

### Population Flow

1. **Scheduler Lambda** runs nightly (Step Function)
2. Fetches data from **yfinance, NewsService** for all 46 tickers
3. Generates **LLM reports** (5-15s per ticker)
4. Stores complete `report_json` with all collected data
5. **User APIs** read from this table (no external API calls)

### Fail-Fast Pattern

If `report_json` is missing or `status != 'completed'`, APIs return error instead of regenerating report.

**User-facing behavior:**
- ✅ Report exists → Return instantly (< 1 sec)
- ❌ Report missing → Return 404 "Report not available. Please try again later."
- ⚠️ NO fallback to external APIs during user requests

This ensures:
- Predictable latency (< 1 sec vs 5-15 sec for external APIs)
- Cost control (no unexpected LLM calls)
- Separation of concerns (write path = scheduler, read path = APIs)

---

## References

### External Resources

- [Liquibase Best Practices](https://www.liquibase.org/get-started/best-practices)
- [Flyway Migrations](https://flywaydb.org/documentation/concepts/migrations)
- [MySQL Online DDL](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl.html)
- [Expand/Contract Pattern](https://openpracticelibrary.com/practice/expand-and-contract-pattern/)
- [Database Reliability Engineering (book)](https://www.oreilly.com/library/view/database-reliability-engineering/9781491925935/)

### Internal Documentation

- [Type System Integration](TYPE_SYSTEM_INTEGRATION.md) - Related to silent ENUM failures
- [Defensive Programming Principles](.claude/CLAUDE.md#defensive-programming-principles)
- [Infrastructure Testing](../tests/infrastructure/) - Schema validation tests

---

**Last Updated:** 2025-12-12
**Maintainer:** Development Team
**Questions?** See [CLAUDE.md](.claude/CLAUDE.md) for contact info
