# Infrastructure-Application Contract Guide

**Principle**: Principle #15 in CLAUDE.md
**Category**: Deployment, Configuration Management, Defensive Programming
**Abstraction**: [failure_mode-2026-01-02-missing-deployment-flags.md](../../.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md)

---

## Overview

When adding new features requiring infrastructure changes, maintain contract between application code, infrastructure configuration, and documented principles. Code deployed without matching infrastructure causes silent failures hours after deployment.

**Core problem**: Multi-file synchronization gap—application code (`src/`), infrastructure (`terraform/`), and principles (`.claude/CLAUDE.md`) must align, but no automated validation enforces this.

---

## Core Insight

**Infrastructure-Application Contract Violation**: When new application-level requirements (principles, features, configurations) are added to the codebase, but infrastructure deployment configurations (Terraform, Doppler, GitHub Actions) are not updated to satisfy those requirements.

**Result**: Code deploys successfully, tests pass, but feature not active or fails silently.

---

## Deployment Update Order

When adding new features requiring infrastructure changes:

### Step 1: Add Principle (if applicable)
Update `.claude/CLAUDE.md` with new principle

### Step 2: Update Application Code
Implement feature following principle

### Step 3: Update Database Schema (CRITICAL)
Create migration for ALL affected tables

**Migration file template**:
```sql
-- db/migrations/018_add_pdf_tracking.sql
-- Add PDF tracking to precomputed_reports table

ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) DEFAULT NULL
COMMENT 'S3 key for generated PDF report';
```

### Step 4: Update Terraform Environment Variables
Update env vars for ALL affected Lambdas

**Terraform template**:
```hcl
# terraform/lambda_config.tf
environment = {
  variables = {
    TZ = "Asia/Bangkok"  # Required by Principle #16
    AURORA_HOST = var.aurora_endpoint
    CACHE_TABLE_NAME = var.cache_table_name
    # Add new variables here
  }
}
```

### Step 5: Update Doppler Secrets (if sensitive)
Add API keys, credentials to Doppler

### Step 6: Run Pre-Deployment Validation
```bash
# Verify infrastructure matches code expectations
./scripts/validate_deployment_ready.sh
```

### Step 7: Deploy Schema Migration FIRST
```bash
# Apply migration to dev environment
mysql -h $AURORA_HOST -u $AURORA_USER -p < db/migrations/018_add_pdf_tracking.sql

# Verify migration applied
mysql -h $AURORA_HOST -u $AURORA_USER -p -e "DESCRIBE precomputed_reports"
```

### Step 8: THEN Deploy Code Changes
```bash
# Deploy Lambda handlers that use new column
git push origin dev  # Triggers CI/CD
```

### Step 9: Verify Ground Truth
```bash
# Check actual Aurora state matches code expectations
mysql -h $AURORA_HOST -u $AURORA_USER -p -e "
  SELECT pdf_s3_key FROM precomputed_reports
  WHERE symbol = 'DBS19' LIMIT 1
"
```

**Critical**: Missing Step 3 causes silent failures or data inconsistencies hours after deployment.

---

## Schema Migration Checklist

Before deploying code that depends on schema changes:

```markdown
- [ ] Created migration file (`db/migrations/0XX_*.sql`)
- [ ] Tested migration locally (forward and rollback)
- [ ] Ran schema validation tests (`pytest tests/infrastructure/test_aurora_schema_comprehensive.py`)
- [ ] Deployed migration to dev environment
- [ ] Verified migration applied (`DESCRIBE table_name`)
- [ ] THEN deploy code changes (handler updates)
- [ ] Verify ground truth (actual Aurora state matches code expectations)
```

---

## Multi-File Synchronization Pattern

Must maintain contract between three layers:

### Layer 1: Application Code (`src/`)
```python
# src/data/aurora/precompute_service.py
def store_report(symbol: str, report_json: dict, pdf_s3_key: str):
    query = """
        INSERT INTO precomputed_reports
        (symbol, report_date, report_json, pdf_s3_key)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (symbol, today, json.dumps(report_json), pdf_s3_key))
```

### Layer 2: Infrastructure (`terraform/`)
```hcl
# terraform/lambda_config.tf
resource "aws_lambda_function" "report_worker" {
  environment {
    variables = {
      TZ = "Asia/Bangkok"
      AURORA_HOST = var.aurora_endpoint
      # Must include all vars code expects
    }
  }
}
```

### Layer 3: Principles (`.claude/CLAUDE.md`)
```markdown
### 16. Timezone Discipline

Use Bangkok timezone consistently across all components.
Lambda functions must have TZ=Asia/Bangkok environment variable.
```

**Contract**: All three layers must align for correct behavior.

---

## Startup Validation Pattern

**Fail fast** when critical configuration missing:

```python
def _validate_configuration() -> None:
    """Validate required environment variables at Lambda startup.

    Fails fast if critical configuration is missing.
    Prevents silent failures hours after deployment.
    """
    required = [
        'AURORA_HOST',
        'AURORA_PORT',
        'AURORA_USER',
        'AURORA_PASSWORD',
        'TZ',  # Required by Principle #16
        'CACHE_TABLE_NAME',
        'JOBS_TABLE_NAME',
    ]

    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {missing}\n"
            f"Lambda cannot start without these variables.\n"
            f"Check Terraform configuration and Doppler secrets."
        )

def lambda_handler(event, context):
    _validate_configuration()  # Call FIRST, before any business logic
    # ... rest of handler logic
```

**Why this matters**:
- Fails immediately on cold start (not hours later on first use)
- Clear error message (lists missing vars)
- Prevents silent degradation (no fallback to defaults)

---

## Common Failure Patterns

### Failure 1: Missing Environment Variable

**Symptom**: Lambda returns 500, CloudWatch shows AttributeError

```python
# Code assumes CACHE_TABLE_NAME exists
cache_table = os.environ.get('CACHE_TABLE_NAME')  # Returns None
# ... later ...
cache_table.put_item(...)  # AttributeError: NoneType has no attribute 'put_item'
```

**Root cause**: Terraform missing env var

**Impact**: Jobs marked "completed" but cache never written (silent failure for 2+ hours)

**Fix**:
1. Add startup validation (fail fast)
2. Update Terraform to include CACHE_TABLE_NAME
3. Redeploy

---

### Failure 2: Schema Mismatch

**Symptom**: INSERT succeeds but column data not persisted

```python
# Code expects pdf_s3_key column
store_report(symbol='DBS19', report_json={...}, pdf_s3_key='s3://...')

# Inside function:
query = "INSERT INTO reports (symbol, report_json, pdf_s3_key) VALUES (%s, %s, %s)"
cursor.execute(query, (symbol, json.dumps(report_json), pdf_s3_key))
# ERROR: Unknown column 'pdf_s3_key'
```

**Root cause**: Migration not deployed before code

**Impact**: Data loss, silent failure

**Fix**:
1. Deploy migration FIRST
2. Verify schema updated (`DESCRIBE table_name`)
3. THEN deploy code

---

### Failure 3: Timezone Date Boundary Bug

**Symptom**: Cache misses despite data populated

```python
# Scheduler stores reports (Bangkok timezone)
today = datetime.now(ZoneInfo("Asia/Bangkok")).date()  # 2025-12-31 04:00 Bangkok
store_report(symbol='DBS19', report_date=today)  # Stored with date=2025-12-31

# LINE bot queries (UTC default, no TZ env var)
today = datetime.now().date()  # 2025-12-30 21:00 UTC
query = "SELECT * FROM reports WHERE symbol = %s AND report_date = %s"
cursor.execute(query, ('DBS19', today))  # Queries for 2025-12-30, not found!
```

**Root cause**: Terraform missing `TZ` environment variable

**Impact**: Cache miss, users see "รายงานยังไม่พร้อม" error despite data exists

**Fix**:
1. Add `TZ = "Asia/Bangkok"` to ALL Lambda env vars in Terraform
2. Redeploy all Lambdas
3. Verify ground truth (queries return expected data)

---

### Failure 4: Copy-Paste Inheritance

**Symptom**: New Lambda missing env vars that other Lambdas have

```hcl
# Old Lambda (has TZ)
resource "aws_lambda_function" "fund_data_sync" {
  environment {
    variables = {
      TZ = "Asia/Bangkok"
      AURORA_HOST = var.aurora_endpoint
    }
  }
}

# New Lambda (copied before TZ added, missing TZ)
resource "aws_lambda_function" "async_report" {
  environment {
    variables = {
      AURORA_HOST = var.aurora_endpoint
      # Missing TZ!
    }
  }
}
```

**Root cause**: Copy-paste from old config before principle added

**Impact**: New Lambda uses UTC default, causes date boundary bugs

**Fix**:
1. Compare env vars across all Lambdas
2. Identify missing vars
3. Add to all Lambdas
4. Redeploy

---

## Anti-Patterns

### ❌ Silent Fallbacks

**Problem**: Hides missing configuration

```python
# BAD: Silent fallback to UTC
tz = os.environ.get('TZ', 'UTC')  # Returns 'UTC' if TZ missing
# Code works but wrong behavior (UTC instead of Bangkok)

# GOOD: Fail fast
tz = os.environ['TZ']  # Raises KeyError if TZ missing
# OR
_validate_configuration()  # Validates at startup, raises RuntimeError
```

**Why silent fallbacks are dangerous**:
- Tests pass (code doesn't crash)
- Deployment succeeds (no errors)
- Feature not active or wrong behavior (hours later)
- Hard to debug (no clear error message)

---

### ❌ No Startup Validation

**Problem**: Fails on first use, not at startup

```python
# BAD: Validation on first use
def write_to_cache(data):
    cache_table = os.environ.get('CACHE_TABLE_NAME')  # None if missing
    cache_table.put_item(Item=data)  # Crashes here (hours after deployment)

# GOOD: Validation at startup
def lambda_handler(event, context):
    _validate_configuration()  # Crashes immediately if CACHE_TABLE_NAME missing
    write_to_cache(data)  # Only runs if config valid
```

---

### ❌ Infrastructure Updated After Deployment

**Problem**: Reactive, not proactive

```markdown
BAD workflow:
1. Deploy code (expects pdf_s3_key column)
2. Code fails (column doesn't exist)
3. Run migration (add column)
4. Redeploy code (now works)

GOOD workflow:
1. Run migration (add column)
2. Verify migration applied
3. Deploy code (expects pdf_s3_key column)
4. Code works immediately
```

---

### ❌ Copy-Paste Without Checking Requirements

**Problem**: Inherits old config, misses new requirements

```bash
# BAD: Copy existing Lambda config
cp terraform/fund_data_sync.tf terraform/new_lambda.tf
# Edit function name, but miss new env vars added since original created

# GOOD: Use template or checklist
cat terraform/lambda_template.tf | \
  sed "s/FUNCTION_NAME/new_lambda/" > terraform/new_lambda.tf
# Template includes ALL current requirements (TZ, etc.)
```

---

## Pre-Deployment Validation Script

Automate contract verification:

```bash
#!/bin/bash
# scripts/validate_deployment_ready.sh

set -euo pipefail

echo "======================================================"
echo "Pre-Deployment Validation"
echo "======================================================"

# 1. Check all Lambdas have required env vars
echo ""
echo "Checking Lambda environment variables..."

REQUIRED_VARS=("TZ" "AURORA_HOST" "AURORA_USER" "AURORA_PASSWORD")

for lambda in report-worker scheduler fund-data-sync; do
  echo "  Checking $lambda..."

  for var in "${REQUIRED_VARS[@]}"; do
    VALUE=$(aws lambda get-function-configuration \
      --function-name dr-daily-report-$lambda-dev \
      --query "Environment.Variables.$var" \
      --output text 2>/dev/null || echo "MISSING")

    if [ "$VALUE" = "MISSING" ] || [ "$VALUE" = "None" ]; then
      echo "    ❌ Missing: $var"
      exit 1
    else
      echo "    ✅ $var: $VALUE"
    fi
  done
done

# 2. Check Aurora schema matches code expectations
echo ""
echo "Checking Aurora schema..."

SCHEMA=$(mysql -h $AURORA_HOST -u $AURORA_USER -p$AURORA_PASSWORD \
  -e "DESCRIBE precomputed_reports" 2>/dev/null || echo "ERROR")

if echo "$SCHEMA" | grep -q "pdf_s3_key"; then
  echo "  ✅ pdf_s3_key column exists"
else
  echo "  ❌ pdf_s3_key column missing"
  echo "  Run migration: db/migrations/018_add_pdf_tracking.sql"
  exit 1
fi

# 3. Check Doppler secrets populated
echo ""
echo "Checking Doppler secrets..."

ENV=dev doppler secrets get LANGFUSE_PUBLIC_KEY >/dev/null 2>&1 && \
  echo "  ✅ Langfuse secrets configured" || \
  echo "  ⚠️  Langfuse secrets missing (optional)"

echo ""
echo "======================================================"
echo "✅ All pre-deployment checks passed"
echo "======================================================"
```

**Usage**:
```bash
# Run before deploying
./scripts/validate_deployment_ready.sh

# If passes, deploy
git push origin dev
```

---

## Integration with Other Principles

**Principle #1 (Defensive Programming)**:
- Validate configuration at startup (fail fast)
- No silent fallbacks (explicit failures)

**Principle #2 (Progressive Evidence Strengthening)**:
- Verify through ground truth (inspect Aurora schema, Lambda config)
- Don't assume Terraform applied correctly

**Principle #5 (Database Migrations Immutability)**:
- Migrations deployed before code
- Verify schema matches expectations

**Principle #20 (Execution Boundary Discipline)**:
- Verify WHERE code runs (Lambda)
- Verify WHAT it needs (env vars, schema)
- Verify HOW contract validated (startup validation, schema tests)

---

## When to Apply

✅ **Before every deployment**:
- Check all three layers aligned (code, infrastructure, principles)
- Run pre-deployment validation script
- Deploy schema migration FIRST, then code

✅ **When adding new principles**:
- Update CLAUDE.md
- Update code to follow principle
- Update Terraform to support principle
- Verify all Lambdas updated (not just new ones)

✅ **When adding new Lambda**:
- Use template with ALL current requirements
- Don't copy-paste old config (may be missing new vars)
- Run validation to verify env vars complete

✅ **When investigation "code looks correct but doesn't work"**:
- Check infrastructure matches code expectations
- Verify env vars, schema, permissions
- Use startup validation to catch missing config

---

## Rationale

**Why infrastructure-application contract matters**:

Code can be syntactically correct and tests can pass, but deployment fails silently because:
- Missing environment variable (Lambda uses default, wrong behavior)
- Schema not migrated (column doesn't exist, data loss)
- Secrets not configured (feature not active, graceful degradation)

**Multi-file synchronization is manual**:
- No compiler enforces alignment between code, Terraform, and principles
- No automated validation catches missing env vars or schema mismatches
- Only runtime or ground truth inspection reveals violations

**Benefits of systematic contract enforcement**:
- Catch issues before deployment (pre-deployment validation)
- Fail fast at startup (not hours later on first use)
- Clear deployment order (migration → code, not reversed)
- Prevent silent degradation (explicit failures, not fallbacks)

---

## See Also

- **Abstraction**: [Missing Deployment Flags Pattern](.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md) - Complete failure mode documentation with 4 real instances
- **Skill**: [deployment](.claude/skills/deployment/) - Deployment workflows and verification
- **Checklist**: [lambda-deployment](.claude/checklists/lambda-deployment.md) - Deployment verification workflow
- **Guide**: [Database Migration](database-migrations.md) - Migration patterns and Aurora-specific gotchas

---

*Guide version: 2026-01-04*
*Principle: #15 in CLAUDE.md*
*Status: Graduated from failure mode to principle to implementation guide*
