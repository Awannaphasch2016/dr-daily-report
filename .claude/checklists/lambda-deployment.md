# Lambda Deployment Checklist

**Purpose**: Systematic verification before deploying Lambda functions to prevent phase boundary violations, environment mismatches, and runtime failures.

**When to use**: Before every Lambda deployment (dev → staging → prod)

**Evidence base**: query_tool_handler import error (Jan 2026), LINE bot 7-day outage (Dec 2025), TZ env var gap

---

## Phase Boundary: Development → Lambda Runtime

**What we're verifying**: Code works in Lambda container, not just local environment

### 1. Container Import Validation

**Why**: Local imports pass, Lambda container imports fail → production broken

- [ ] **Run Docker import tests**: `pytest tests/infrastructure/test_handler_imports_docker.py -v`
  - Tests handlers import in Lambda Python 3.11 container
  - Validates /var/task filesystem layout
  - Catches missing COPY directives in Dockerfile

**Evidence required**: All Docker tests green ✅

**If failed**:
- Check Dockerfile COPY directives include handler file
- Verify import paths relative to /var/task
- Run interactive: `docker run -it --entrypoint bash dr-lambda-test`
- Debug imports: `python3 -c "import module_name"`

**Prevents**: Dec 2025 LINE bot ImportError (7-day outage)

---

### 2. Local Import Validation

**Why**: Fast feedback - catches syntax errors before Docker build

- [ ] **Run local import tests**: `pytest tests/infrastructure/test_handler_imports.py -v`
  - Tests handler modules exist
  - Tests handler functions callable
  - Fast (5 seconds, no Docker)

**Evidence required**: All local tests green ✅

**If failed**:
- Check Python syntax: `python -m py_compile src/path/to/handler.py`
- Check import paths correct
- Check __init__.py files exist

**Prevents**: Syntax errors, missing files, broken imports

---

## Environment Boundary: Code → AWS Configuration

**What we're verifying**: Lambda has all required environment variables and permissions

### 3. Environment Variable Validation

**Why**: Missing env var → Lambda fails at startup → CloudWatch shows only START/END logs

- [ ] **Check Terraform env vars**: Compare code requirements vs Terraform config
  ```bash
  # Extract required vars from handler _validate_required_config()
  grep "required_vars\|REQUIRED_VARS" src/path/to/handler.py

  # Check Terraform has all required vars
  grep "environment" terraform/lambda_config.tf
  ```

**Evidence required**: All required vars present in Terraform ✅

**Common required vars** (handler-specific):
- `TZ = "Asia/Bangkok"` (Principle #16 - Timezone Discipline)
- `AURORA_HOST`, `AURORA_DATABASE`, `AURORA_USER`, `AURORA_PASSWORD`
- `OPENROUTER_API_KEY` (report_worker)
- `PDF_BUCKET_NAME` (report_worker)
- `PRECOMPUTE_STATE_MACHINE_ARN` (precompute_controller)

**If missing**:
- Update `terraform/<lambda>.tf` environment block
- Run pre-deployment validation: `scripts/validate_deployment_ready.sh`
- Deploy Terraform BEFORE deploying code

**Prevents**: Jan 2026 precompute_controller TZ gap (silent failure)

---

### 4. Startup Validation Test

**Why**: Handler validates config at startup but tests never invoke validation

- [ ] **Run startup validation tests**: Tests that handlers fail fast when env vars missing
  ```bash
  # Tests handler startup without environment
  pytest tests/infrastructure/test_handler_startup_validation.py -v
  ```

**Evidence required**: Tests verify handlers raise RuntimeError when config missing ✅

**If test missing**: Create test following Principle #19 pattern (Cross-Boundary Contract Testing)

**Prevents**: Silent failures when env vars missing in fresh deployments

---

## Service Boundary: Lambda → Aurora

**What we're verifying**: Lambda code matches Aurora schema

### 5. Schema Validation

**Why**: Code expects column, Aurora doesn't have it → silent data loss

- [ ] **Run schema validation tests**: `pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v -m integration`
  - Auto-extracts expected columns from code
  - Queries actual Aurora schema
  - Blocks deployment if mismatch

**Evidence required**: Schema tests green ✅

**If failed**:
1. Check test output for missing columns
2. Create migration: `db/migrations/0XX_add_columns.sql`
3. Test migration locally
4. Deploy migration to dev Aurora
5. Verify: `DESCRIBE table_name`
6. Re-run schema tests
7. THEN deploy code

**Prevents**: Jan 2026 PDF schema bug (pdf_s3_key parameter ignored)

---

### 6. Database Connectivity

**Why**: Lambda can't reach Aurora → timeout errors

- [ ] **Check VPC configuration**: Lambda in same VPC as Aurora
  ```bash
  # Check Lambda VPC config
  aws lambda get-function-configuration \
    --function-name LAMBDA_NAME \
    --query 'VpcConfig' --output json

  # Check Aurora VPC
  aws rds describe-db-instances \
    --db-instance-identifier AURORA_INSTANCE \
    --query 'DBInstances[0].DBSubnetGroup.VpcId'
  ```

**Evidence required**: Lambda and Aurora in same VPC ✅

**If different**:
- Update Terraform: `terraform/lambda_config.tf` vpc_config
- Deploy Terraform changes
- Verify connectivity with smoke test

**Prevents**: Lambda timeout (can't reach Aurora)

---

## Execution Boundary: Code → Runtime Behavior

**What we're verifying**: Code executes correctly in Lambda environment

### 7. Unit Tests

**Why**: Verify business logic before deployment

- [ ] **Run unit tests**: `pytest tests/ -m "not integration and not e2e" -v`
  - Tests core logic
  - Tests error handling
  - Fast (no AWS calls)

**Evidence required**: All unit tests green ✅

**If failed**: Fix logic bugs before deploying

---

### 8. Integration Tests

**Why**: Verify Lambda works with real AWS services

- [ ] **Run integration tests**: `pytest tests/ -m integration -v`
  - Tests against deployed dev environment
  - Tests Aurora queries work
  - Tests S3 uploads work
  - Tests Step Functions invocations work

**Evidence required**: Integration tests green ✅

**If failed**: Fix integration bugs before deploying

**Note**: Integration tests pass because deployed environment already has correct config. They don't catch fresh deployment gaps (that's why we need Docker tests).

---

## Data Boundary: Code → Aurora Types

**What we're verifying**: Data types compatible between Python and MySQL

### 9. Type System Validation

**Why**: Python types don't match MySQL → silent data corruption or query failures

- [ ] **Check type compatibility**: Review INSERT/UPDATE queries
  - Python `None` → MySQL `NULL` ✅
  - Python `str` → MySQL `VARCHAR/TEXT` ✅
  - Python `int` → MySQL `INT/BIGINT` ✅
  - Python `float` → MySQL `DECIMAL/DOUBLE` ✅
  - Python `datetime` → MySQL `TIMESTAMP/DATETIME` ✅
  - Python `bool` → MySQL `TINYINT(1)` ✅

**Special cases** (Principle #4 - Type System Integration):
- ❌ Python `float('nan')` → MySQL JSON (rejected per RFC 8259)
- ❌ Python `float('inf')` → MySQL JSON (rejected)
- ✅ Convert NaN/Inf to `None` before insertion

**Evidence required**: No NaN/Inf in data payloads ✅

**If incompatible**: Add type conversion in code or update schema

---

## Pre-Deployment Checklist

**Run BEFORE creating PR**:

- [ ] Local import tests pass (`test_handler_imports.py`)
- [ ] Docker import tests pass (`test_handler_imports_docker.py`)
- [ ] Unit tests pass
- [ ] Terraform env vars match code requirements
- [ ] Schema validation tests pass (if Aurora changes)
- [ ] Startup validation tests exist for new handlers

**Run BEFORE merging PR**:

- [ ] CI/CD pipeline green (PR checks passed)
- [ ] Docker validation step passed in workflow
- [ ] Schema validation step passed (if applicable)
- [ ] Code review approved

**Run BEFORE deploying to staging**:

- [ ] Integration tests pass against dev environment
- [ ] Smoke tests pass in dev environment
- [ ] CloudWatch logs show expected behavior
- [ ] Ground truth verified (database state matches expectations)

**Run BEFORE deploying to prod**:

- [ ] Staging deployment successful
- [ ] Staging smoke tests pass
- [ ] Staging monitoring shows no errors
- [ ] Rollback plan documented

---

## Post-Deployment Verification

**Progressive Evidence Strengthening** (Principle #2):

### Layer 1: Surface Signals
- [ ] **Deployment exit code**: `echo $?` → 0 ✅
- [ ] **AWS CLI response**: `aws lambda wait function-updated` succeeds ✅

**Evidence strength**: Weakest (only confirms process completed)

### Layer 2: Content Signals
- [ ] **Lambda configuration**: `aws lambda get-function` shows correct image URI ✅
- [ ] **Environment variables**: `aws lambda get-function-configuration` shows all required vars ✅

**Evidence strength**: Stronger (confirms configuration applied)

### Layer 3: Observability Signals
- [ ] **CloudWatch logs**: Application logs present (not just START/END) ✅
  ```bash
  aws logs filter-log-events \
    --log-group-name /aws/lambda/LAMBDA_NAME \
    --start-time $(date -u -d '5 minutes ago' +%s)000 \
    --filter-pattern "INFO"
  ```
- [ ] **No startup errors**: No RuntimeError in logs ✅
- [ ] **Expected log messages**: See handler-specific log patterns ✅

**Evidence strength**: Strong (reveals what actually happened)

### Layer 4: Ground Truth
- [ ] **Smoke test passes**: Invoke Lambda, check response ✅
  ```bash
  aws lambda invoke \
    --function-name LAMBDA_NAME \
    --payload '{"test": true}' \
    /tmp/response.json
  cat /tmp/response.json
  ```
- [ ] **Database state correct**: Query Aurora, verify data ✅
- [ ] **S3 objects exist**: Check S3 bucket for generated files ✅

**Evidence strength**: Strongest (confirms intent matched reality)

**Never stop at Layer 1** - exit code 0 doesn't mean deployment worked!

---

## Rollback Triggers

**When to rollback** (Principle #6 - Deployment Monitoring Discipline):

- ❌ **Post-deployment smoke test fails**: Lambda returns 500 or import errors
- ❌ **CloudWatch shows only START/END logs**: No application logs = startup crash
- ❌ **Error rate exceeds baseline**: >5% errors in first 5 minutes
- ❌ **Ground truth verification fails**: Database state doesn't match expectations

**Rollback execution**:
```bash
# Get previous known-good image digest
PREVIOUS_IMAGE=$(git log -2 --oneline | tail -1 | awk '{print $1}')

# Rollback Lambda to previous image
aws lambda update-function-code \
  --function-name LAMBDA_NAME \
  --image-uri REGISTRY/REPO:$PREVIOUS_IMAGE

# Wait for rollback to complete
aws lambda wait function-updated --function-name LAMBDA_NAME

# Verify rollback successful
aws lambda get-function --function-name LAMBDA_NAME \
  --query 'Code.ImageUri' --output text

# Re-run smoke tests
```

**Document rollback**:
- Why rollback triggered
- What evidence showed failure
- Rollback command used
- Post-rollback verification results
- Create incident report

---

## Common Deployment Failures

### 1. Import Error in Lambda
**Symptom**: CloudWatch shows "cannot import module 'handler_name'"

**Root cause**: Handler file missing from Docker COPY or import path wrong

**Fix**:
1. Check Dockerfile COPY directives
2. Run Docker import tests locally
3. Verify /var/task filesystem layout
4. Rebuild Docker image
5. Re-deploy

**Prevention**: Add Docker import tests to PR workflow

---

### 2. Missing Environment Variable
**Symptom**: CloudWatch shows only START/END logs, no application logs

**Root cause**: Lambda crashes at startup due to missing required env var

**Fix**:
1. Check handler _validate_required_config() for required vars
2. Update Terraform environment block
3. Deploy Terraform changes
4. Re-deploy Lambda
5. Verify env vars present

**Prevention**: Add startup validation tests to PR workflow

---

### 3. Schema Mismatch
**Symptom**: Parameters accepted but silently ignored, no database updates

**Root cause**: Code expects column, Aurora schema doesn't have it

**Fix**:
1. Run schema validation tests
2. Create migration to add missing columns
3. Deploy migration to Aurora
4. Verify schema with DESCRIBE table_name
5. Re-deploy Lambda code

**Prevention**: Run schema validation in PR workflow (already exists)

---

### 4. VPC Connectivity
**Symptom**: Lambda timeout errors when accessing Aurora

**Root cause**: Lambda not in same VPC as Aurora

**Fix**:
1. Check Lambda VPC config
2. Check Aurora VPC config
3. Update Terraform vpc_config
4. Deploy Terraform changes
5. Verify connectivity

**Prevention**: Integration tests catch this (but only after deployment)

---

## Integration with CLAUDE.md Principles

This checklist implements:

- **Principle #1** (Defensive Programming): Startup validation tests verify fail-fast behavior
- **Principle #2** (Progressive Evidence Strengthening): Post-deployment verification uses all 4 evidence layers
- **Principle #6** (Deployment Monitoring Discipline): Rollback triggers and verification steps
- **Principle #10** (Testing Anti-Patterns): Docker tests validate deployment artifacts, not just source
- **Principle #15** (Infrastructure-Application Contract): Terraform env var validation
- **Principle #16** (Timezone Discipline): TZ env var verification
- **Principle #19** (Cross-Boundary Contract Testing): Docker tests verify Development → Lambda Runtime boundary
- **Principle #20** (Execution Boundary Discipline): Systematic verification of WHERE code runs and WHAT it needs

---

## Quick Reference

**Before PR**:
```bash
# Local tests (fast)
pytest tests/infrastructure/test_handler_imports.py -v

# Docker tests (slow but comprehensive)
pytest tests/infrastructure/test_handler_imports_docker.py -v

# Unit tests
pytest tests/ -m "not integration" -v
```

**Before merge**:
- Wait for CI/CD pipeline green
- Check PR workflow Docker validation passed

**Before deploy**:
```bash
# Schema validation (if Aurora changes)
pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v -m integration

# Integration tests
pytest tests/ -m integration -v
```

**After deploy**:
```bash
# Smoke test
aws lambda invoke \
  --function-name LAMBDA_NAME \
  --payload '{"test": true}' \
  /tmp/response.json

# Check logs
aws logs tail /aws/lambda/LAMBDA_NAME --follow
```

---

**Checklist version**: 1.0
**Last updated**: 2026-01-03
**Owner**: Daily Report Engineering
**Related**: [Deployment Skill](.claude/skills/deployment/), [Testing Workflow](.claude/skills/testing-workflow/)
