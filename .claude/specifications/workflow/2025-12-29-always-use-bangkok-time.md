---
title: Always Use Bangkok Time
focus: workflow
date: 2025-12-29
status: draft
tags: [timezone, infrastructure, migration, bangkok]
---

# Workflow Specification: Always Use Bangkok Time

## Goal

**What does this workflow accomplish?**

Eliminate timezone confusion by standardizing the entire system on Bangkok time (Asia/Bangkok, UTC+7). Currently the system uses UTC in various places (database, scheduler, Python code), which causes confusion for a Bangkok-based user with no UTC requirements.

**Target state**: All timestamps, schedules, and datetime operations use Bangkok time consistently across infrastructure, database, application code, and logs.

---

## Problem Statement

**Current state**:
- Aurora MySQL defaults to UTC timezone
- EventBridge scheduler runs on UTC cron (22:00 UTC = 5 AM Bangkok)
- Python code uses `datetime.utcnow()` in 8+ locations
- Database migrations use `CURRENT_TIMESTAMP` (UTC)
- CloudWatch logs show UTC timestamps
- Code comments say "TIMEZONE FIX: Use UTC date to match Aurora"

**Pain points**:
- Constant UTC ↔ Bangkok mental conversion
- Date boundaries confusing (22:00 UTC is next day in Bangkok)
- Comments explicitly call out timezone mismatch as a "fix"
- User is Bangkok-based with no UTC requirements
- Unnecessary complexity for single-timezone use case

---

## Workflow Diagram

```
[Phase 1: Infrastructure] → [Phase 2: Database] → [Phase 3: Application Code] → [Phase 4: Verification]
                                                                                          ↓
                                                                                    [Success]
                                                                                          ↓
                                                                              [Phase 5: Documentation]
```

---

## Phase 1: Infrastructure Configuration

### Node 1.1: Aurora MySQL Timezone

**Purpose**: Configure Aurora to use Bangkok timezone for all `CURRENT_TIMESTAMP` and `NOW()` calls

**Input**: Current Aurora cluster with no timezone configuration (defaults to UTC)

**Processing**:
1. Create RDS parameter group with `time_zone = "Asia/Bangkok"`
2. Attach parameter group to Aurora cluster
3. Apply changes (triggers cluster restart)

**Implementation**:

```hcl
# File: terraform/aurora.tf (add after line 174)

# RDS Parameter Group for timezone configuration
resource "aws_rds_cluster_parameter_group" "aurora" {
  name        = "${var.project_name}-aurora-params-${var.environment}"
  family      = "aurora-mysql8.0"
  description = "Custom parameter group for Aurora with Bangkok timezone"

  parameter {
    name  = "time_zone"
    value = "Asia/Bangkok"
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-aurora-params"
    App       = "shared"
    Component = "aurora-parameter-group"
  })
}

# Update existing aws_rds_cluster resource (line 180)
resource "aws_rds_cluster" "aurora" {
  # ... existing config ...

  # ADD THIS LINE:
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name

  # ... rest of existing config ...
}
```

**Output**: Aurora cluster configured with Bangkok timezone

**Duration**: 5 minutes (includes cluster restart)

**Error conditions**:
- Cluster restart fails → Rollback to previous parameter group
- Parameter group validation fails → Check timezone name is valid

**Verification**:
```sql
SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();
-- Expected: Asia/Bangkok, Asia/Bangkok, <Bangkok time>, <UTC time 7 hours behind>
```

---

### Node 1.2: Lambda Environment Variables

**Purpose**: Set TZ environment variable so Python's `datetime.now()` returns Bangkok time

**Input**: Lambda functions with no TZ variable (default to UTC)

**Processing**:
1. Add `TZ = "Asia/Bangkok"` to all Lambda environment variables
2. Deploy updated Lambda configurations

**Implementation**:

```hcl
# File: terraform/scheduler.tf (line 28-61)
# File: terraform/precompute_workflow.tf (similar locations)
# File: terraform/ticker_fetcher.tf (similar locations)

environment {
  variables = {
    # ... existing variables ...

    # Timezone configuration (Bangkok = UTC+7)
    TZ = "Asia/Bangkok"

    # ... rest of variables ...
  }
}
```

**Lambda functions to update**:
1. `ticker_scheduler` (terraform/scheduler.tf)
2. `precompute_controller` (terraform/precompute_workflow.tf)
3. `telegram_api` (terraform/telegram.tf)
4. `report_worker` (if exists)
5. `query_tool` (if exists)

**Output**: All Lambda functions use Bangkok timezone by default

**Duration**: 2 minutes (terraform apply)

**Error conditions**:
- Invalid timezone name → Validation error (won't deploy)
- Lambda environment size limit → Use shorter env var names

**Verification**:
```bash
# Check Lambda configuration
aws lambda get-function-configuration \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --query "Environment.Variables.TZ"
# Expected: "Asia/Bangkok"

# Invoke Lambda and check logs
aws lambda invoke --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action": "test"}' /tmp/response.json
# Check CloudWatch logs for Bangkok timestamps
```

---

### Node 1.3: EventBridge Schedule Documentation

**Purpose**: Document that EventBridge cron stays in UTC (platform limitation)

**Input**: EventBridge rule with UTC cron expression

**Processing**:
1. Update comments to clarify UTC cron limitation
2. Verify cron expression still correct (22:00 UTC = 5 AM Bangkok)
3. Document in code and infrastructure comments

**Implementation**:

```hcl
# File: terraform/scheduler.tf (line 169-184)

resource "aws_cloudwatch_event_rule" "daily_ticker_fetch" {
  name                = "${var.project_name}-daily-ticker-fetch-${var.environment}"
  description         = "Fetch ticker data daily at 5 AM Bangkok time (Asia/Bangkok)"

  # EventBridge cron expressions ALWAYS run in UTC (platform limitation)
  # 22:00 UTC = 05:00 Bangkok next day (UTC+7)
  # This cron stays in UTC, but all application code uses Bangkok timezone
  schedule_expression = "cron(0 22 * * ? *)"

  state = "ENABLED"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-daily-ticker-fetch-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler-trigger"
    Schedule  = "daily-5am-bangkok"  # User-facing description
    CronNote  = "UTC cron: 22:00 UTC = 05:00 Bangkok"  # Technical note
  })
}
```

**Output**: EventBridge schedule unchanged but clearly documented

**Duration**: 1 minute (documentation only)

**Error conditions**: None (documentation only)

---

## Phase 2: Database Schema Updates

### Node 2.1: Update Migration Comments

**Purpose**: Document timezone context for existing `CURRENT_TIMESTAMP` columns

**Input**: Migration files with `CURRENT_TIMESTAMP DEFAULT` (20+ occurrences)

**Processing**:
1. Add comments to migrations documenting timezone change
2. Note that existing data remains in UTC
3. Document migration date (2025-12-29)

**Implementation**:

```sql
-- File: db/migrations/001_complete_schema.sql (example at line 37-38)

-- Timestamp columns (Bangkok timezone after 2025-12-29)
-- Pre-2025-12-29: UTC timestamps | Post-2025-12-29: Bangkok timestamps
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Created timestamp (Bangkok time after 2025-12-29)',
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Updated timestamp (Bangkok time after 2025-12-29)',
```

**Files to update**:
1. `db/migrations/001_complete_schema.sql` (20 occurrences)
2. `db/migrations/001_create_ticker_master.sql`
3. `db/migrations/002_create_ticker_aliases.sql`
4. `db/migrations/004_create_daily_prices.sql`
5. `db/migrations/005_create_ticker_data_cache.sql`
6. `db/migrations/016_add_semantic_comments.sql`

**Output**: Migration files document timezone context

**Duration**: 10 minutes (documentation only)

**Error conditions**: None (comments don't affect schema)

---

### Node 2.2: Optional Data Migration

**Purpose**: Convert existing UTC timestamps to Bangkok time (OPTIONAL)

**Input**: Tables with UTC timestamps in `fetched_at`, `computed_at`, `created_at` columns

**Processing**:
1. Backup database (safety)
2. Run CONVERT_TZ for each timestamp column
3. Verify conversion (spot check)

**Implementation**:

```sql
-- ⚠️ OPTIONAL: Only if you want historical data in Bangkok time
-- Test on staging first!

-- Backup first
-- mysqldump ticker_data > ticker_data_backup.sql

-- Convert ticker_data.fetched_at
UPDATE ticker_data
SET fetched_at = CONVERT_TZ(fetched_at, '+00:00', '+07:00')
WHERE fetched_at < '2025-12-29 00:00:00';

-- Convert precomputed_reports.computed_at
UPDATE precomputed_reports
SET computed_at = CONVERT_TZ(computed_at, '+00:00', '+07:00')
WHERE computed_at < '2025-12-29 00:00:00';

-- Verify conversion
SELECT
  MIN(fetched_at) as first_fetch,
  MAX(fetched_at) as last_fetch,
  COUNT(*) as total_records
FROM ticker_data;
-- Check that timestamps look correct (7 hours ahead of old values)
```

**⚠️ WARNING**:
- **Not required**: New timestamps will be Bangkok, old timestamps still work
- **Risky**: Large table updates can cause downtime
- **Test first**: Run on staging before production
- **Consider NOT doing this**: Mixed timezones are acceptable if documented

**Output**: All historical data in Bangkok time (OPTIONAL)

**Duration**: 10-60 minutes (depends on data volume)

**Error conditions**:
- Table lock timeout → Run during low-traffic window
- Conversion fails → Restore from backup

**Recommendation**: **Skip this step** unless you specifically need historical data converted. New data will be Bangkok time automatically.

---

## Phase 3: Application Code Updates

### Node 3.1: Replace datetime.utcnow() in Scheduler

**Purpose**: Replace all `datetime.utcnow()` calls with `datetime.now()` (uses TZ env var)

**Input**: Scheduler files with 8+ `datetime.utcnow()` calls

**Processing**:
1. Find all `datetime.utcnow()` calls in scheduler files
2. Replace with `datetime.now()` (automatically uses TZ env var)
3. Update comments from "Use UTC" to "Use Bangkok time"

**Implementation**:

```python
# File: src/scheduler/ticker_fetcher.py

# Line 154: BEFORE
today = datetime.utcnow().date().isoformat()

# Line 154: AFTER
today = datetime.now().date().isoformat()

# Line 175-178: BEFORE
# TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
self.precompute_service.store_ticker_data(
    symbol=symbol,
    data_date=datetime.utcnow().date(),
    # ...
)

# Line 175-178: AFTER
# Use Bangkok date to match Aurora timezone (Asia/Bangkok)
self.precompute_service.store_ticker_data(
    symbol=symbol,
    data_date=datetime.now().date(),
    # ...
)

# Line 312-317: BEFORE
'date': datetime.utcnow().date().isoformat()

# Line 312-317: AFTER
'date': datetime.now().date().isoformat()

# Line 359-361: Similar changes
```

**Files to update** (Priority: CRITICAL):
1. `src/scheduler/ticker_fetcher.py` (6 locations)
2. `src/scheduler/query_tool_handler.py` (1 location)

**Files already correct** (use `datetime.now()` already):
- `src/scheduler/ticker_fetcher_handler.py` ✅
- `src/scheduler/precompute_controller_handler.py` ✅
- `src/scheduler/schema_manager_handler.py` ✅

**Output**: Scheduler code uses Bangkok time consistently

**Duration**: 15 minutes (code changes)

**Error conditions**:
- Forgot to set TZ env var → Lambda uses UTC (caught in testing)
- Import statement missing → Add `from datetime import datetime`

---

### Node 3.2: Update Data Fetcher Files

**Purpose**: Review and update datetime usage in data fetcher files

**Input**: Data fetcher files with potential `datetime.utcnow()` calls

**Processing**:
1. Grep for `datetime.utcnow()` in data fetcher files
2. Replace with `datetime.now()` where found
3. Verify no timezone-aware datetime objects conflict

**Files to review** (Priority: HIGH):
- `src/data/data_fetcher.py`
- `src/data/data_lake.py`
- `src/data/s3_cache.py`
- `src/data/aurora/repository.py`
- `src/data/aurora/precompute_service.py`
- `src/data/aurora/fund_data_repository.py`

**Implementation**:
```bash
# Find all datetime.utcnow() usage
grep -rn "datetime.utcnow()" src/data/

# Replace each occurrence
sed -i 's/datetime\.utcnow()/datetime.now()/g' {file}
```

**Output**: Data fetcher files use Bangkok time

**Duration**: 20 minutes

**Error conditions**:
- Timezone-aware datetime conflicts → Use naive datetime (no tzinfo)

---

### Node 3.3: Update API Service Files

**Purpose**: Ensure API responses use Bangkok time consistently

**Input**: API service files with timestamp generation

**Processing**:
1. Review API response timestamps
2. Update any `datetime.utcnow()` to `datetime.now()`
3. Consider adding timezone indicator in API responses (optional)

**Files to review** (Priority: MEDIUM):
- `src/api/app.py`
- `src/api/transformer.py`
- `src/api/rankings_service.py`
- `src/api/watchlist_service.py`
- `src/api/job_service.py`
- `src/api/models.py` (Pydantic defaults)

**Optional enhancement**:
```python
# Add timezone indicator to API responses (optional)
{
  "data": {...},
  "timestamp": "2025-12-29T05:00:00+07:00",  # ISO 8601 with timezone
  "timezone": "Asia/Bangkok"
}
```

**Output**: API services use Bangkok time

**Duration**: 15 minutes

---

### Node 3.4: Update Workflow Files

**Purpose**: Ensure workflow execution timestamps use Bangkok time

**Input**: Workflow files with state timestamps

**Processing**:
1. Review workflow node timestamp generation
2. Update any `datetime.utcnow()` to `datetime.now()`
3. Verify workflow state serialization handles Bangkok time

**Files to update** (Priority: HIGH):
- `src/workflow/workflow_nodes.py`
- `src/workflow/aurora_data_adapter.py`
- `src/agent.py`

**Output**: Workflow timestamps use Bangkok time

**Duration**: 10 minutes

---

## Phase 4: Verification & Testing

### Node 4.1: Infrastructure Verification

**Purpose**: Verify Aurora and Lambda timezone configuration

**Processing**:

**Test 1: Aurora timezone**
```sql
SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();
-- Expected:
-- @@global.time_zone: Asia/Bangkok
-- @@session.time_zone: Asia/Bangkok
-- NOW(): Bangkok time (e.g., 2025-12-29 14:30:00)
-- UTC_TIMESTAMP(): UTC time (e.g., 2025-12-29 07:30:00) - 7 hours behind
```

**Test 2: Lambda TZ variable**
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --query "Environment.Variables.TZ"
# Expected: "Asia/Bangkok"
```

**Test 3: Lambda datetime.now() output**
```bash
# Invoke Lambda with test payload
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action": "test_timezone"}' \
  /tmp/response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/dr-daily-report-ticker-scheduler-dev --follow
# Look for log timestamps - should be Bangkok time
```

**Success criteria**:
- Aurora `@@global.time_zone` = Asia/Bangkok
- Lambda TZ env var = Asia/Bangkok
- Lambda logs show Bangkok timestamps

**Duration**: 5 minutes

---

### Node 4.2: Scheduler Timing Verification

**Purpose**: Verify scheduler runs at 5 AM Bangkok time

**Processing**:

**Test 1: Manual trigger with date check**
```bash
# Trigger scheduler manually
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{}' \
  /tmp/response.json

# Check generated data date
just --unstable aurora-query "
SELECT date, COUNT(*) as count
FROM ticker_data
ORDER BY date DESC
LIMIT 3
"
# Expected: Latest date should match Bangkok's current date (not UTC date)
```

**Test 2: Wait for scheduled run**
```bash
# EventBridge runs at 22:00 UTC = 5:00 AM Bangkok next day
# Check CloudWatch logs at 5:00-5:05 AM Bangkok time
aws logs tail /aws/lambda/dr-daily-report-ticker-scheduler-dev --follow --since 5m
```

**Success criteria**:
- Scheduler runs at 5:00 AM Bangkok time (verify in CloudWatch)
- Generated data has Bangkok date (not UTC date)
- No timezone-related errors in logs

**Duration**: 10 minutes (or wait for next scheduled run)

---

### Node 4.3: Database Write Verification

**Purpose**: Verify new database writes use Bangkok timestamps

**Processing**:

```sql
-- Insert test record
INSERT INTO ticker_data (
  ticker_master_id, symbol, date, price_history,
  company_info, financials_json, source
) VALUES (
  1, 'TEST', CURDATE(), '{}', '{}', '{}', 'test'
);

-- Check fetched_at timestamp
SELECT
  symbol, date, fetched_at,
  TIMESTAMPDIFF(HOUR, UTC_TIMESTAMP(), fetched_at) as hours_from_utc
FROM ticker_data
WHERE symbol = 'TEST'
ORDER BY id DESC
LIMIT 1;

-- Expected:
-- fetched_at: Bangkok time (e.g., 2025-12-29 14:30:00)
-- hours_from_utc: ~7 (Bangkok is UTC+7)

-- Clean up test record
DELETE FROM ticker_data WHERE symbol = 'TEST';
```

**Success criteria**:
- New records have Bangkok timestamps in `fetched_at`
- `TIMESTAMPDIFF` shows ~7 hour difference from UTC
- No timezone conversion errors

**Duration**: 5 minutes

---

### Node 4.4: Unit Test Updates

**Purpose**: Update test expectations for Bangkok timezone

**Processing**:
1. Run existing tests
2. Identify timezone-related test failures
3. Update test expectations to Bangkok time
4. Add timezone verification tests

**Files to update**:
- `tests/infrastructure/test_scheduler_lambda.py`
- `tests/infrastructure/test_eventbridge_scheduler.py`
- `tests/shared/test_data_fetcher.py`

**Example test update**:
```python
# BEFORE (expected UTC)
def test_ticker_fetch_date():
    result = ticker_fetcher.fetch_all()
    expected_date = datetime.utcnow().date()
    assert result['date'] == expected_date

# AFTER (expect Bangkok)
def test_ticker_fetch_date():
    result = ticker_fetcher.fetch_all()
    # Bangkok time (datetime.now() uses TZ env var)
    expected_date = datetime.now().date()
    assert result['date'] == expected_date
```

**Success criteria**:
- All tests pass with Bangkok timezone
- No hard-coded UTC expectations remain
- Tests verify TZ env var is set

**Duration**: 20 minutes

---

## Phase 5: Documentation Updates

### Node 5.1: Update Code Comments

**Purpose**: Replace all "UTC" references with "Bangkok" in comments

**Processing**:

```bash
# Find all comments mentioning UTC or timezone
grep -rn "UTC\|timezone\|utc" src/ | grep -i "comment\|#\|//"

# Update comments manually or with sed
sed -i 's/Use UTC date to match Aurora/Use Bangkok date to match Aurora/g' src/scheduler/*.py
sed -i 's/Aurora runs in UTC/Aurora runs in Bangkok time (Asia\/Bangkok)/g' src/scheduler/*.py
sed -i 's/TIMEZONE FIX: Use UTC/Use Bangkok time (Asia\/Bangkok)/g' src/scheduler/*.py
```

**Files with comments to update**:
1. `src/scheduler/ticker_fetcher.py:175,312,359`
2. `src/scheduler/query_tool_handler.py:380`
3. `terraform/scheduler.tf:4,172`
4. `terraform/aurora.tf:200`

**Success criteria**:
- No misleading "Use UTC" comments remain
- Comments accurately describe Bangkok timezone usage

**Duration**: 10 minutes

---

### Node 5.2: Update Deployment Runbooks

**Purpose**: Update runbooks to expect Bangkok timestamps

**Processing**:

```markdown
# File: docs/deployment/RUNBOOK_AURORA_DATA_VERIFICATION.md

## Verification Queries

### Check timestamp range (UPDATED for Bangkok timezone)

```sql
SELECT
  MIN(fetched_at) as first_fetch,
  MAX(fetched_at) as last_fetch,
  COUNT(*) as total_records
FROM ticker_data
WHERE date = CURDATE();

-- Expected:
-- first_fetch: Bangkok time (e.g., 05:01:00 local time)
-- last_fetch: Bangkok time (e.g., 05:05:00 local time)
-- NOTE: All timestamps in Bangkok timezone (Asia/Bangkok) after 2025-12-29
```
\`\`\`

**Success criteria**:
- Runbooks mention Bangkok timezone
- Example timestamps show Bangkok time
- No UTC expectations remain

**Duration**: 15 minutes

---

### Node 5.3: Update Project Documentation

**Purpose**: Document timezone configuration in README and project docs

**Processing**:

```markdown
# Add to README.md or docs/ARCHITECTURE.md

## Timezone Configuration

**System timezone**: Asia/Bangkok (UTC+7)

All timestamps, schedules, and datetime operations use Bangkok time:
- **Aurora MySQL**: Configured with `time_zone = "Asia/Bangkok"`
- **Lambda functions**: Environment variable `TZ = "Asia/Bangkok"`
- **EventBridge schedules**: UTC cron (platform limitation) but executes at Bangkok time equivalent
- **Python code**: `datetime.now()` returns Bangkok time automatically
- **Database columns**: `CURRENT_TIMESTAMP` returns Bangkok time

**Why Bangkok time?**
- User is Bangkok-based with no UTC requirements
- Eliminates timezone conversion confusion
- Simplifies date boundary logic (no next-day confusion)
- Single timezone reduces mental overhead

**EventBridge limitation**:
EventBridge cron expressions only support UTC. Our schedule:
- Cron: `cron(0 22 * * ? *)` (22:00 UTC)
- Executes: 5:00 AM Bangkok (next day)
- Application code uses Bangkok time despite UTC cron

**Historical data**:
- Pre-2025-12-29: UTC timestamps (not converted)
- Post-2025-12-29: Bangkok timestamps
- Both are acceptable - queries work correctly either way
```

**Success criteria**:
- README documents Bangkok timezone
- Architecture docs explain timezone design decision
- New contributors understand timezone configuration

**Duration**: 20 minutes

---

## State Management

**State structure**:
```python
class MigrationState(TypedDict):
    phase: str                    # Current phase (infrastructure/database/code/verification/docs)
    infrastructure_done: bool     # Aurora + Lambda configured
    database_done: bool           # Migrations updated, optional data migration
    code_done: bool               # All datetime.utcnow() replaced
    tests_passing: bool           # Tests updated and passing
    verification_done: bool       # All verification tests passed
    docs_done: bool               # Documentation updated
    errors: List[str]             # Any errors encountered
```

**State transitions**:
- Initial → After Phase 1: `infrastructure_done = True`
- After Phase 2: `database_done = True`
- After Phase 3: `code_done = True`
- After Phase 4: `verification_done = True, tests_passing = True`
- After Phase 5: `docs_done = True` → Migration complete

---

## Error Handling

**Error propagation**:
- Infrastructure errors: Rollback terraform, Aurora remains functional
- Code errors: Git revert, redeploy previous version
- Test failures: Fix code, don't proceed to next phase
- Verification failures: Investigate root cause, don't mark phase complete

**Retry logic**:
- Terraform apply: Automatic retry on transient errors
- Aurora parameter change: Automatic cluster restart
- Lambda deploy: Automatic rollback on health check failure
- No manual retries needed for infrastructure

**Rollback plan** (if migration fails):
1. **Revert Terraform changes**:
   ```bash
   git revert <commit>
   terraform plan -out=rollback.tfplan
   terraform apply rollback.tfplan
   ```

2. **Revert Python code**:
   ```bash
   git revert <commit>
   # CI/CD redeploys automatically
   ```

3. **Verify rollback**:
   ```sql
   SELECT @@global.time_zone;  -- Should return SYSTEM or UTC
   ```

**Recovery time**: 10-15 minutes (rollback is faster than migration)

---

## Performance

**Expected duration**:
- **Phase 1** (Infrastructure): 30 minutes (includes Aurora restart)
- **Phase 2** (Database): 20 minutes (documentation only, skip data migration)
- **Phase 3** (Code): 60 minutes (update 30+ files)
- **Phase 4** (Verification): 40 minutes (includes waiting for scheduler run)
- **Phase 5** (Documentation): 45 minutes
- **Total**: 3-4 hours (without data migration)

**With optional data migration**: +1-2 hours (depends on data volume)

**Bottlenecks**:
- Aurora cluster restart (5 minutes downtime)
- Terraform apply (waits for Lambda deployment)
- Manual testing (wait for next scheduled run)

**Optimization opportunities**:
- Run Phases 1-3 in parallel on different branches → merge together
- Skip optional data migration (not required)
- Automate test verification with CI/CD

---

## Success Criteria

✅ **Infrastructure**:
- [ ] Aurora parameter group shows `time_zone = Asia/Bangkok`
- [ ] Lambda environment variables include `TZ = Asia/Bangkok`
- [ ] EventBridge cron still scheduled at 22:00 UTC (platform limitation)

✅ **Database**:
- [ ] `SELECT NOW()` returns Bangkok time (7 hours ahead of UTC)
- [ ] New inserts have Bangkok timestamps
- [ ] Migration comments document timezone change

✅ **Code**:
- [ ] No `datetime.utcnow()` calls in src/ directory
- [ ] All `datetime.now()` calls use TZ env var (Bangkok)
- [ ] Comments updated from "UTC" to "Bangkok"

✅ **Tests**:
- [ ] All unit tests pass with Bangkok timezone
- [ ] Integration tests verify correct scheduler timing
- [ ] No hard-coded UTC expectations remain

✅ **Verification**:
- [ ] Scheduler runs at 5:00 AM Bangkok time (verified in CloudWatch)
- [ ] Generated data has Bangkok date (not UTC date)
- [ ] Database writes have Bangkok timestamps

✅ **Documentation**:
- [ ] README documents Bangkok timezone configuration
- [ ] Runbooks updated with Bangkok timestamp expectations
- [ ] Comments explain Bangkok timezone design decision

---

## Open Questions

- [ ] **Optional data migration**: Do we convert existing UTC timestamps to Bangkok? (Recommendation: NO - not worth the risk)
- [ ] **API timezone indicator**: Should API responses include timezone? (e.g., `"timezone": "Asia/Bangkok"`)
- [ ] **Backup window**: Keep Aurora backup at 02:00-03:00 UTC (09:00-10:00 Bangkok)? Or change to Bangkok time?
- [ ] **Log aggregation**: Do we need to configure CloudWatch Logs to show Bangkok time? (May require Lambda extension)

---

## Next Steps

**Immediate** (before implementation):
- [ ] Review this specification with user
- [ ] Answer open questions
- [ ] Get approval for migration approach
- [ ] Confirm: skip optional data migration? (recommended)

**Implementation** (if approved):
- [ ] Phase 1: Update terraform configuration (30 min)
- [ ] Phase 2: Update database migration comments (20 min)
- [ ] Phase 3: Update application code (60 min)
- [ ] Phase 4: Verify all changes work (40 min)
- [ ] Phase 5: Update documentation (45 min)

**Post-implementation**:
- [ ] Monitor first scheduled run (5 AM Bangkok)
- [ ] Verify no timezone-related errors in production
- [ ] Update `/locate` report with actual implementation results
- [ ] Journal lessons learned: `/journal architecture "Bangkok timezone migration"`

---

## Related Specifications

- `/locate` report: `.claude/locate/2025-12-29-utc-to-bangkok-timezone-migration.md`
  - Detailed file list (31 files)
  - Line-by-line code changes
  - Risk assessment
  - Testing strategy

**This specification** provides:
- High-level workflow (5 phases)
- Implementation approach (how to execute)
- Success criteria (what done looks like)
- Rollback plan (how to undo if fails)

**Use `/locate` for**: "Which files to change?"
**Use this spec for**: "How to change them?"

---

## Recommendations

**✅ DO**:
- Set Aurora timezone to Asia/Bangkok (parameter group)
- Add TZ env var to all Lambda functions
- Replace `datetime.utcnow()` with `datetime.now()` (uses TZ)
- Update documentation and comments
- Test thoroughly before deploying to production

**❌ DON'T**:
- Don't migrate existing UTC timestamps to Bangkok (risky, not necessary)
- Don't change EventBridge cron from UTC (platform doesn't support named timezones)
- Don't skip verification steps (timezone bugs are subtle)
- Don't forget to update tests (will fail with old UTC expectations)

**⚠️ IMPORTANT**:
- Aurora cluster will restart when parameter group applied (1-2 min downtime)
- EventBridge cron stays in UTC but executes at correct Bangkok time equivalent
- Historical data remains in UTC (acceptable - new data will be Bangkok)
- Test in dev environment first, then staging, then production

---

**Status**: Draft (awaiting review)
**Estimated effort**: 3-4 hours (without optional data migration)
**Risk level**: Medium (Aurora restart required, many files to update)
**Recommendation**: Proceed with migration - benefits outweigh risks for Bangkok-based user

---

*Generated by `/specify` command*
*Focus: Workflow design*
*Date: 2025-12-29*
