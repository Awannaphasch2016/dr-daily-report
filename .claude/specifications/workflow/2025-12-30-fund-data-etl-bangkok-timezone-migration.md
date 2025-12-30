---
title: Fund Data ETL Bangkok Timezone Migration
focus: workflow
date: 2025-12-30
status: draft
tags: [timezone, etl, fund-data, bangkok, migration]
---

# Workflow Specification: Fund Data ETL Bangkok Timezone Migration

## Goal

**What does this workflow accomplish?**

Complete the Bangkok timezone migration for the fund data ETL pipeline (on-premise → S3 → SQS → Lambda → Aurora). Currently, on-premise exports use Bangkok time (04:11 AM) but AWS components (Lambda, Aurora) use UTC, causing timezone mismatch in `synced_at` timestamps.

**Target state**: All components use Bangkok time consistently - on-premise export, S3 timestamps, Lambda processing, and Aurora storage.

**Why this matters**:
- Eliminates timezone confusion (no more UTC ↔ Bangkok mental conversion)
- Consistent log correlation (S3 logs and Aurora timestamps match)
- Aligns with project specification (.claude/specifications/workflow/2025-12-29-always-use-bangkok-time.md)
- Ticker scheduler already migrated (proven approach)

---

## Current State (MIXED Timezone)

**Evidence from validation** (.claude/validations/2025-12-30-fund-data-etl-timezone.md):

```
On-premise SQL Server Export → Bangkok Time (UTC+7)
   ↓ (04:11 AM Bangkok)
S3 Data Lake → Bangkok timestamps
   ↓ (S3 event)
Lambda Processing → UTC (no TZ env var)
   ↓ (writes synced_at = NOW())
Aurora MySQL → UTC (default timezone)
   ↓
Result: synced_at = 21:11:48 UTC (7 hours behind S3 upload)
```

**Timestamp correlation**:
- S3 upload: `04:11:16` Bangkok
- Aurora sync: `21:11:48` UTC
- Offset: 7 hours (Bangkok = UTC+7)
- Processing delta: 32 seconds

---

## Workflow Diagram

```
[Phase 1: Aurora Timezone] → [Phase 2: Lambda TZ Config] → [Phase 3: Verification] → [Phase 4: Documentation]
                                                                      ↓
                                                                [Success]
```

---

## Nodes

### Node 1: Configure Aurora Timezone (5 minutes)

**Purpose**: Set Aurora cluster to use Bangkok timezone for all `CURRENT_TIMESTAMP` and `NOW()` calls

**Input**: Aurora cluster with UTC default timezone

**Processing**:
1. Create RDS parameter group with `time_zone = "Asia/Bangkok"`
2. Attach parameter group to Aurora cluster (terraform apply)
3. Restart Aurora cluster (automatic, ~2 minutes downtime)

**Implementation**:

```hcl
# File: terraform/aurora.tf (add after existing parameter group or line 174)

# Bangkok timezone parameter group
resource "aws_rds_cluster_parameter_group" "aurora_bangkok" {
  name        = "${var.project_name}-aurora-params-${var.environment}"
  family      = "aurora-mysql8.0"
  description = "Aurora parameter group with Bangkok timezone (Asia/Bangkok)"

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

# Update existing aws_rds_cluster resource
resource "aws_rds_cluster" "aurora" {
  # ... existing config ...

  # ADD THIS LINE:
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora_bangkok.name

  # ... rest of existing config ...
}
```

**Output**: Aurora cluster configured with Bangkok timezone

**Duration**: 5 minutes (includes cluster restart)

**Error conditions**:
- Cluster restart fails → Rollback to previous parameter group (automatic)
- Parameter group validation fails → Check timezone name is valid

**Verification**:
```sql
SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();
-- Expected:
-- @@global.time_zone: Asia/Bangkok
-- @@session.time_zone: Asia/Bangkok
-- NOW(): <Bangkok time> (e.g., 2025-12-30 10:30:00)
-- UTC_TIMESTAMP(): <UTC time> (e.g., 2025-12-30 03:30:00) - 7 hours behind
```

---

### Node 2: Configure Lambda TZ Environment Variable (2 minutes)

**Purpose**: Set `TZ = "Asia/Bangkok"` env var so Python's `datetime.now()` returns Bangkok time

**Input**: Lambda function with no TZ variable (defaults to UTC)

**Processing**:
1. Add `TZ = "Asia/Bangkok"` to Lambda environment variables
2. Deploy updated Lambda configuration (terraform apply)

**Implementation**:

```hcl
# File: terraform/fund_data_sync.tf (line ~110-140, in aws_lambda_function.fund_data_sync)

resource "aws_lambda_function" "fund_data_sync" {
  # ... existing config ...

  environment {
    variables = {
      # Existing variables
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_USER     = var.aurora_username
      AURORA_PASSWORD = var.aurora_password
      AURORA_DATABASE = var.aurora_database
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id

      # ADD THIS LINE:
      TZ = "Asia/Bangkok"  # Bangkok timezone (UTC+7)

      # ... rest of existing variables ...
    }
  }

  # ... rest of existing config ...
}
```

**Output**: Lambda function uses Bangkok timezone by default

**Duration**: 2 minutes (terraform apply)

**Error conditions**:
- Invalid timezone name → Validation error (won't deploy)
- Lambda environment size limit → Use shorter env var names (unlikely)

**Verification**:
```bash
# Check Lambda configuration
ENV=dev doppler run -- aws lambda get-function-configuration \
  --function-name dr-daily-report-fund-data-sync-dev \
  --query "Environment.Variables.TZ"

# Expected: "Asia/Bangkok"
```

---

### Node 3: Update Code Comments (5 minutes)

**Purpose**: Document timezone semantics in code

**Input**: Repository code with UTC timezone comments/assumptions

**Processing**:
1. Update comments in fund_data_repository.py
2. Update database migration comments
3. Document timezone in FUND_DATA_SYNC_DEPLOYMENT.md

**Implementation**:

**File 1**: `src/data/aurora/fund_data_repository.py:169`

```python
# BEFORE:
synced_at = NOW()

# AFTER:
synced_at = NOW()  # Bangkok time (Asia/Bangkok) - matches on-premise export timezone
```

**File 2**: `db/migrations/003_fund_data_schema.sql` (add migration comment)

```sql
-- Timezone Migration (2025-12-30):
-- Pre-2025-12-30: synced_at stored in UTC
-- Post-2025-12-30: synced_at stored in Bangkok time (Asia/Bangkok)
-- Both are valid - no data migration required
```

**File 3**: `docs/FUND_DATA_SYNC_DEPLOYMENT.md` (update section 2.1.3 or add new section)

```markdown
### Timezone Configuration

**System timezone**: Asia/Bangkok (UTC+7)

**Components**:
- **On-premise export**: Bangkok time (04:00 AM daily)
- **S3 uploads**: Bangkok timestamps (04:11 AM pattern)
- **Lambda processing**: Bangkok time (TZ env var)
- **Aurora storage**: Bangkok time (parameter group)

**Migration date**: 2025-12-30

**Historical data**:
- Pre-2025-12-30: synced_at in UTC
- Post-2025-12-30: synced_at in Bangkok time
- Both are acceptable - no conversion needed

**Verification**:
```sql
SELECT @@global.time_zone, NOW(), UTC_TIMESTAMP();
-- Expected: Asia/Bangkok, <Bangkok>, <UTC 7h behind>
```
```

**Output**: Code and documentation reflect Bangkok timezone

**Duration**: 5 minutes (documentation updates)

---

### Node 4: Verification Testing (10 minutes)

**Purpose**: Verify Bangkok timezone configuration works end-to-end

**Input**: Configured Aurora + Lambda with Bangkok timezone

**Processing**:
1. Test Aurora timezone configuration
2. Test Lambda timezone
3. End-to-end test: Upload CSV → verify synced_at timestamp

**Test 1: Aurora Timezone**

```bash
# Connect to Aurora
just --unstable aurora tunnel  # Start tunnel in background
sleep 5

# Verify timezone
mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' ticker_data -e "
SELECT
  @@global.time_zone as global_tz,
  @@session.time_zone as session_tz,
  NOW() as bangkok_time,
  UTC_TIMESTAMP() as utc_time,
  TIMESTAMPDIFF(HOUR, UTC_TIMESTAMP(), NOW()) as hours_offset
"
```

**Expected**:
```
+-----------------+--------------------+---------------------+---------------------+--------------+
| global_tz       | session_tz         | bangkok_time        | utc_time            | hours_offset |
+-----------------+--------------------+---------------------+---------------------+--------------+
| Asia/Bangkok    | Asia/Bangkok       | 2025-12-30 10:30:00 | 2025-12-30 03:30:00 |            7 |
+-----------------+--------------------+---------------------+---------------------+--------------+
```

**Test 2: Lambda Timezone**

```bash
# Check Lambda configuration
ENV=dev doppler run -- aws lambda get-function-configuration \
  --function-name dr-daily-report-fund-data-sync-dev \
  --query "Environment.Variables.TZ"

# Expected: "Asia/Bangkok"
```

**Test 3: End-to-End Test**

```bash
# Create test CSV
cat > /tmp/test_fund_data_tz.csv <<'CSV'
d_trade,stock,ticker,col_code,value
2025-12-30,TEST,TEST19,CLOSE,99.99
CSV

# Upload to S3
ENV=dev doppler run -- aws s3 cp /tmp/test_fund_data_tz.csv \
  s3://dr-daily-report-data-lake-dev/raw/sql_server/fund_data/2025-12-30/test_timezone.csv

# Wait for processing
sleep 10

# Check synced_at timestamp in Aurora
mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' ticker_data -e "
SELECT
  ticker,
  synced_at as bangkok_synced_at,
  TIMESTAMPDIFF(HOUR, UTC_TIMESTAMP(), synced_at) as hours_from_utc,
  s3_source_key
FROM fund_data
WHERE s3_source_key LIKE '%test_timezone.csv%'
ORDER BY synced_at DESC
LIMIT 1;
"

# Clean up test record
mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' ticker_data -e "
DELETE FROM fund_data WHERE s3_source_key LIKE '%test_timezone.csv%';
"
```

**Expected**:
```
+--------+---------------------+----------------+------------------------------------------------+
| ticker | bangkok_synced_at   | hours_from_utc | s3_source_key                                  |
+--------+---------------------+----------------+------------------------------------------------+
| TEST19 | 2025-12-30 10:30:45 |              7 | raw/sql_server/fund_data/.../test_timezone.csv |
+--------+---------------------+----------------+------------------------------------------------+
```

**Success criteria**:
- ✅ Aurora `@@global.time_zone` = Asia/Bangkok
- ✅ Lambda TZ env var = Asia/Bangkok
- ✅ `synced_at` timestamp ~7 hours ahead of UTC
- ✅ Test CSV processed successfully

**Output**: Verification complete, Bangkok timezone working

**Duration**: 10 minutes

**Error conditions**:
- Aurora timezone not set → Check terraform apply succeeded
- Lambda TZ not set → Check terraform apply succeeded
- Test CSV processing fails → Check Lambda logs for errors

---

### Node 5: Update Justfile Recipe (5 minutes)

**Purpose**: Update `just verify-fund-data` recipe to reflect Bangkok timezone

**Input**: Recipe with "Last Sync (UTC)" label

**Processing**:
1. Update SQL query label from "(UTC)" to "(Bangkok)"
2. Update recipe comments

**Implementation**:

```bash
# File: justfile (verify-fund-data recipe, ~line 98)

# BEFORE:
DATE_FORMAT(MAX(synced_at), '%Y-%m-%d %H:%i:%s') as 'Last Sync (UTC)'

# AFTER:
DATE_FORMAT(MAX(synced_at), '%Y-%m-%d %H:%i:%s') as 'Last Sync (Bangkok)'
```

**Output**: Recipe reflects Bangkok timezone

**Duration**: 5 minutes

---

## State Management

**State structure**:
```python
class MigrationState(TypedDict):
    aurora_configured: bool       # Aurora parameter group applied
    lambda_configured: bool       # Lambda TZ env var set
    code_updated: bool           # Comments updated
    verification_passed: bool    # Tests passed
    documentation_updated: bool  # Docs reflect Bangkok timezone
    errors: List[str]            # Any errors encountered
```

**State transitions**:
- Initial → After Node 1: `aurora_configured = True`
- After Node 2: `lambda_configured = True`
- After Node 3: `code_updated = True`
- After Node 4: `verification_passed = True`
- After Node 5: `documentation_updated = True` → Migration complete

---

## Error Handling

**Error propagation**:
- Aurora parameter group error → Halt, rollback terraform
- Lambda config error → Halt, rollback terraform
- Verification failure → Investigate, don't proceed
- Documentation update → Low risk, can fix later

**Retry logic**:
- Terraform apply: Automatic retry on transient errors
- Aurora restart: Automatic (managed by AWS)
- Lambda config: Automatic rollback on failure

**Rollback plan**:

```bash
# Revert terraform changes
git revert <commit>
cd terraform
terraform plan -out=rollback.tfplan
terraform apply rollback.tfplan

# Verify rollback
mysql -h 127.0.0.1 -P 3307 -u admin -p'...' ticker_data -e "
SELECT @@global.time_zone;
-- Expected: SYSTEM or UTC (reverted)
"

ENV=dev doppler run -- aws lambda get-function-configuration \
  --function-name dr-daily-report-fund-data-sync-dev \
  --query "Environment.Variables.TZ"
# Expected: null (reverted)
```

**Recovery time**: 5 minutes (rollback faster than migration)

---

## Performance

**Expected duration**:
- **Node 1** (Aurora timezone): 5 minutes (includes restart)
- **Node 2** (Lambda TZ): 2 minutes
- **Node 3** (Code comments): 5 minutes
- **Node 4** (Verification): 10 minutes
- **Node 5** (Justfile update): 5 minutes
- **Total**: 27 minutes

**Downtime**:
- Aurora restart: 1-2 minutes (writes blocked)
- Lambda config: 0 minutes (no downtime)

**Optimization opportunities**:
- Run Nodes 2-3 in parallel (code updates while Aurora restarts)
- Skip optional data migration (historical timestamps stay UTC)

---

## Open Questions

- [x] Should historical synced_at timestamps be converted? **Answer: NO** - Not worth the risk, mixed timestamps are acceptable with documentation
- [x] Will Aurora restart affect production? **Answer: YES** - 1-2 min downtime, schedule during low-traffic window
- [x] Need to update on-premise export? **Answer: NO** - Already uses Bangkok time
- [ ] Should we add timezone indicator to API responses? (Optional enhancement)

---

## Success Criteria

✅ **Infrastructure**:
- [ ] Aurora parameter group shows `time_zone = Asia/Bangkok`
- [ ] Lambda environment variable `TZ = Asia/Bangkok`

✅ **Database**:
- [ ] `SELECT NOW()` returns Bangkok time (7 hours ahead of UTC)
- [ ] New inserts have Bangkok timestamps in `synced_at`

✅ **Code**:
- [ ] Comments updated from "UTC" to "Bangkok"
- [ ] FUND_DATA_SYNC_DEPLOYMENT.md documents timezone configuration

✅ **Verification**:
- [ ] Test CSV processed successfully
- [ ] `synced_at` timestamp ~7 hours ahead of UTC
- [ ] No timezone-related errors in Lambda logs

✅ **Documentation**:
- [ ] Justfile recipe reflects Bangkok timezone
- [ ] Database migration comments document timezone semantics

---

## Next Steps

**Immediate** (before implementation):
- [ ] Review this specification
- [ ] Answer remaining open questions
- [ ] Decide: Proceed with migration? (Recommended: YES)
- [ ] Schedule Aurora restart during low-traffic window

**Implementation** (if approved):
1. [ ] Node 1: Configure Aurora timezone (terraform apply)
2. [ ] Node 2: Configure Lambda TZ (terraform apply)
3. [ ] Node 3: Update code comments
4. [ ] Node 4: Run verification tests
5. [ ] Node 5: Update justfile recipe

**Post-implementation**:
- [ ] Monitor next fund data upload (verify Bangkok timestamps)
- [ ] Run `just verify-fund-data` to see Bangkok timestamps
- [ ] Journal: `/journal architecture "Fund data ETL Bangkok timezone migration"`
- [ ] Update validation report with results

---

## Related Specifications

- `.claude/specifications/workflow/2025-12-29-always-use-bangkok-time.md` - Original Bangkok timezone migration specification (comprehensive, covers all components)
- `.claude/validations/2025-12-30-fund-data-etl-timezone.md` - Validation report confirming mixed timezone usage
- `.claude/bug-hunts/2025-12-30-wrong-date-utc-instead-of-bangkok.md` - Bug hunt for ticker scheduler (already fixed)

**This specification** focuses on:
- Fund data ETL pipeline only (narrower scope than 2025-12-29 spec)
- Practical implementation steps (not just design)
- Quick migration (27 minutes total)

---

## Recommendations

**✅ DO**:
- Apply Aurora timezone parameter group (proven approach)
- Add Lambda TZ env var (no downtime)
- Document timezone in code comments
- Test thoroughly with end-to-end test

**❌ DON'T**:
- Don't migrate historical synced_at timestamps (risky, not needed)
- Don't skip verification step (timezone bugs are subtle)
- Don't forget to update documentation (future confusion)

**⚠️ IMPORTANT**:
- Aurora cluster will restart (~1-2 min downtime)
- Schedule during low-traffic window
- Monitor first production upload after migration

---

**Status**: Draft (ready for review)
**Estimated effort**: 27 minutes
**Risk level**: Low (ticker scheduler already migrated successfully)
**Recommendation**: Proceed with migration - aligns with project specification

---

*Generated by `/specify` command*
*Focus: Workflow design*
*Date: 2025-12-30*
