# Execution Boundary Discipline Guide

**Principle**: Principle #20 in CLAUDE.md
**Category**: Defensive Programming, System Integration, Verification
**Abstraction**: [failure_mode-2026-01-03-missing-execution-boundary-analysis.md](../../.claude/abstractions/failure_mode-2026-01-03-missing-execution-boundary-analysis.md)

---

## Overview

**Reading code ≠ Verifying code works.** In distributed systems, code correctness depends on WHERE it executes and WHAT initial conditions hold. Before concluding "code is correct", systematically identify execution boundaries (code → runtime, code → database, service → service) and verify contracts at each boundary match reality.

**Core problem**: Analysts validate code logic (Layer 1) but skip infrastructure contracts (Layers 2-4), leading to "code looks correct but doesn't work" bugs that only surface in production.

---

## Core Insight

Code can be syntactically correct but fail in production because:
- Missing environment variable causes runtime error
- Schema mismatch causes silent data loss
- Permission denied blocks service access
- Network misconfiguration prevents connectivity

**These failures are invisible from code inspection alone—must verify WHERE code runs and WHAT it needs.**

---

## Five Critical Verification Questions

Before concluding "code is correct", answer these questions systematically:

### 1. WHERE does this code run?
- Lambda function? (which function, what runtime)
- EC2 instance? (which instance, what OS)
- Docker container? (local, ECS, Fargate)
- Local development? (laptop, venv)

### 2. WHAT environment does it require?
- Environment variables? (TZ, AURORA_HOST, API_KEY, ...)
- Filesystem access? (read /tmp, write logs, ...)
- Network access? (VPC, security groups, internet access)
- Permissions? (IAM role, resource policies)

### 3. WHAT external systems does it call?
- Aurora database? (verify schema matches code)
- S3 buckets? (verify bucket exists, permissions)
- SQS queues? (verify queue exists, message format)
- External APIs? (verify endpoint reachable, auth works)

### 4. WHAT are entity properties?
- Lambda timeout/memory? (does workload fit constraints)
- Aurora connection limits? (will concurrent connections exceed pool)
- S3 bucket policies? (does IAM role have access)
- Intended usage? (sync Lambda not for async work)

### 5. HOW do I verify the contract?
- Terraform config? (check environment variable definitions)
- SHOW COLUMNS? (verify database schema)
- Test access? (aws lambda invoke, mysql connection)
- Ground truth? (inspect actual runtime state)

---

## Five Layers of Correctness

Progressive verification from weakest to strongest:

### Layer 1: Syntactic (Code Compiles)
```python
# Python syntax valid
def store_report(symbol: str, pdf_s3_key: Optional[str] = None):
    pass
```
**Verification**: Code runs without syntax errors
**Limitation**: Doesn't verify code does what it claims

### Layer 2: Semantic (Code Does What It Claims)
```python
def store_report(symbol: str, pdf_s3_key: Optional[str] = None):
    query = "INSERT INTO reports (symbol, pdf_s3_key) VALUES (%s, %s)"
    cursor.execute(query, (symbol, pdf_s3_key))
```
**Verification**: Logic correct, function implements intended behavior
**Limitation**: Doesn't verify code can reach what it needs

### Layer 3: Boundary (Code Can Reach What It Needs)
```bash
# Verify Lambda has network access to Aurora
aws lambda get-function-configuration \
  --function-name report-worker \
  --query 'VpcConfig'

# Verify IAM role has Aurora permissions
aws iam get-role-policy \
  --role-name lambda-execution-role \
  --policy-name aurora-access
```
**Verification**: Network connectivity, permissions, configuration exist
**Limitation**: Doesn't verify entity configuration matches requirements

### Layer 4: Configuration (Entity Config Matches Requirements)
```bash
# Verify Lambda timeout sufficient for workload
aws lambda get-function-configuration \
  --function-name report-worker \
  --query 'Timeout'  # Should be >= expected runtime

# Verify Aurora schema has required columns
mysql> SHOW COLUMNS FROM reports;
# Must include: symbol, pdf_s3_key
```
**Verification**: Database schema, Lambda config, resource properties match code expectations
**Limitation**: Doesn't verify intended usage matches design

### Layer 5: Intentional (Usage Matches Designed Purpose)
```python
# Anti-pattern: Using synchronous Lambda for async workload
# Lambda configured for: API Gateway sync response (30s timeout)
# Actual usage: Long-running PDF generation (60s runtime)
# Result: Lambda times out, PDF incomplete

# Correct: Use async Lambda with appropriate timeout
# Lambda configured for: SQS async processing (900s timeout)
# Usage: PDF generation triggered by SQS message
```
**Verification**: Code usage matches entity's designed purpose and constraints
**Strongest verification**: All layers pass = high confidence code will work

---

## Concrete Verification Methods

### 1. Docker Container Testing (Development → Lambda Runtime)

**Problem**: Local imports work, but Lambda container fails

**Solution**: Test imports in actual Lambda container environment

```bash
# Build Lambda container (same base image as AWS)
docker build -t dr-lambda-test -f Dockerfile .

# Test imports in container (catches missing dependencies)
docker run --rm --entrypoint python3 dr-lambda-test \
  -c "import src.scheduler.query_tool_handler"

# Expected: Exit code 0 (success)
# If ImportError: Lambda will fail too (fix before deploying)

# Interactive debugging (explore container environment)
docker run -it --entrypoint bash dr-lambda-test

# Inside container:
# - Verify file paths (/var/task vs local project root)
# - Test imports interactively
# - Check Python version (3.11 in Lambda vs local)
```

**Why this matters**:
- Local Python environment ≠ Lambda Python environment
- File paths differ (`/var/task` in Lambda vs. project root locally)
- Dependencies might be missing in Lambda layer
- Python version might differ (local 3.11.7 vs. Lambda 3.11.6)

**Real incident**: LINE bot 7-day outage (ImportError in Lambda, not local)

---

### 2. Terraform Environment Verification (Code → Infrastructure)

**Problem**: Code requires env var, but Terraform forgot to set it

**Solution**: Verify Terraform config matches code requirements

```bash
# Step 1: Extract required vars from code
grep "required_vars\|REQUIRED_VARS" src/handler.py
# Output: REQUIRED_VARS = ['TZ', 'AURORA_HOST', 'CACHE_TABLE_NAME']

# Step 2: Check Terraform has all vars
grep -A 20 "environment" terraform/lambda_config.tf
# Should see:
#   environment = {
#     variables = {
#       TZ = "Asia/Bangkok"
#       AURORA_HOST = var.aurora_endpoint
#       CACHE_TABLE_NAME = var.cache_table_name
#     }
#   }

# Step 3: Verify deployed Lambda has vars (ground truth)
aws lambda get-function-configuration \
  --function-name report-worker \
  --query 'Environment.Variables'

# Should match Terraform config exactly
```

**Why this matters**:
- Terraform applies config ≠ Lambda receives config (verify both)
- Missing env var causes runtime error, not deployment error
- Only appears on fresh deployment (cold start)
- Integration tests against deployed Lambda don't catch this (env vars already set)

---

### 3. Aurora Schema Verification (Code → Database)

**Problem**: Code INSERT expects column, but Aurora schema doesn't have it

**Solution**: Verify Aurora schema matches code expectations

```bash
# Automated verification (run in CI/CD)
pytest tests/infrastructure/test_aurora_schema_comprehensive.py -v

# Manual verification (inspect actual schema)
mysql -h $AURORA_HOST -u $AURORA_USER -p$AURORA_PASSWORD \
  -e "DESCRIBE precomputed_reports"

# Expected output should include:
# Field          | Type         | Null | Key | Default | Extra
# --------------------------------------------------------------
# id             | int          | NO   | PRI | NULL    | auto_increment
# symbol         | varchar(20)  | NO   |     | NULL    |
# report_date    | date         | NO   |     | NULL    |
# pdf_s3_key     | varchar(255) | YES  |     | NULL    |  <- Must exist!

# If pdf_s3_key missing:
# - Code will compile (Python doesn't check schema)
# - INSERT will fail silently (parameter ignored)
# - Data lost (pdf_s3_key not persisted)
```

**Schema validation test pattern**:
```python
def test_aurora_schema_matches_code_expectations():
    """Verify Aurora schema has all columns code expects to write."""

    cursor.execute("SHOW COLUMNS FROM precomputed_reports")
    actual_columns = {row['Field'] for row in cursor.fetchall()}

    # Columns code expects (from INSERT query)
    expected_columns = {
        'id', 'symbol', 'report_date', 'report_json',
        'pdf_s3_key',  # New column for PDF tracking
        'created_at', 'updated_at'
    }

    missing = expected_columns - actual_columns
    assert not missing, (
        f"Aurora schema missing columns: {missing}\n"
        f"Code expects these columns but database doesn't have them.\n"
        f"Run migration first: db/migrations/0XX_add_pdf_s3_key.sql"
    )
```

**Why this matters**:
- PyMySQL doesn't validate schema before INSERT (silent failure)
- Missing column causes data loss, not error
- Schema drift between environments (dev has column, staging doesn't)

**Real incident**: PDF generation schema bug (2026-01-03) - Code passed `pdf_s3_key` parameter, Aurora silently ignored it

---

## Boundary Types

### 1. Process Boundary (Code → Runtime Environment)

**Definition**: Transition from source code to executing process

**Contract**: Code assumes environment provides:
- Environment variables (TZ, AURORA_HOST, ...)
- Filesystem paths (/tmp writable, /var/task readable)
- Python packages (dependencies installed)
- Permissions (IAM role attached, resource policies)

**Verification**:
```bash
# Check Lambda has env vars
aws lambda get-function-configuration --function-name LAMBDA_NAME

# Check Lambda has correct IAM role
aws lambda get-function --function-name LAMBDA_NAME \
  --query 'Configuration.Role'

# Test Lambda can execute (smoke test)
aws lambda invoke --function-name LAMBDA_NAME /tmp/response.json
```

**Common failures**:
- Missing environment variable (Lambda defaults to None/empty)
- Wrong IAM role attached (permissions denied)
- Dependencies missing from Lambda layer (ImportError)

---

### 2. Network Boundary (Service A → Service B)

**Definition**: Transition across network (Lambda → Aurora, Lambda → S3)

**Contract**: Services assume:
- Network connectivity (VPC, security groups, routing tables)
- Authentication (IAM role, credentials, API keys)
- Quotas (connection limits, rate limits, concurrent requests)

**Verification**:
```bash
# Check Lambda in correct VPC/subnets (same as Aurora)
aws lambda get-function-configuration --function-name LAMBDA_NAME \
  --query 'VpcConfig'

# Check security group allows Aurora access (port 3306)
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Test actual connectivity (from Lambda)
aws lambda invoke \
  --function-name LAMBDA_NAME \
  --payload '{"action": "test_aurora_connection"}' \
  /tmp/response.json
```

**Common failures**:
- Lambda not in VPC (can't reach Aurora in VPC)
- Security group blocks port 3306 (connection timeout)
- Aurora max_connections exceeded (too many concurrent Lambdas)

---

### 3. Data Boundary (Code → Storage)

**Definition**: Transition where data persists across system restart

**Contract**: Code and storage assume:
- Schema match (columns exist, types compatible)
- Constraints satisfied (NOT NULL, UNIQUE, FOREIGN KEY)
- Type compatibility (Python dict → JSON string)

**Verification**:
```sql
-- Verify schema matches code expectations
DESCRIBE table_name;

-- Verify constraints
SHOW CREATE TABLE table_name;

-- Test INSERT actually works
INSERT INTO table_name (col1, col2) VALUES ('test', 'data');
SELECT * FROM table_name WHERE col1 = 'test';
DELETE FROM table_name WHERE col1 = 'test';
```

**Common failures**:
- Missing column (code expects `pdf_s3_key`, Aurora doesn't have it)
- Type mismatch (Python dict → MySQL JSON requires `json.dumps()`)
- Constraint violation (NOT NULL column, code passes None)

---

### 4. Deployment Boundary (Local → AWS)

**Definition**: Transition from development to production environment

**Contract**: Environments assume:
- Configuration parity (same env vars, same dependencies)
- Service availability (Aurora reachable, S3 accessible)
- Resource limits (Lambda timeout/memory, Aurora connection pool)

**Verification**:
```bash
# Compare local vs deployed configuration
# Local:
cat .env

# Deployed:
aws lambda get-function-configuration --function-name LAMBDA_NAME

# Verify deployed Lambda can execute
aws lambda invoke --function-name LAMBDA_NAME /tmp/response.json
cat /tmp/response.json

# Check CloudWatch logs for errors
aws logs tail /aws/lambda/LAMBDA_NAME --follow
```

**Common failures**:
- Local uses .env, Lambda missing env vars (Terraform forgot to set)
- Local uses admin IAM, Lambda uses least-privilege IAM (permission denied)
- Local has unlimited timeout, Lambda timeout=30s (workload incomplete)

---

## Progressive Verification Workflow

Apply Principle #2 (Progressive Evidence Strengthening) to boundary verification:

### Step 1: Surface Signals (Weakest Evidence)
- Terraform apply exit code = 0 (deployment succeeded)
- Lambda invoke status code = 200 (execution completed)

**Limitation**: Doesn't verify correctness, only that process finished

### Step 2: Content Signals (Stronger Evidence)
- Lambda response payload contains expected fields
- Aurora query returns expected rows

**Limitation**: Doesn't verify execution path or side effects

### Step 3: Observability Signals (Stronger Still)
- CloudWatch logs show execution trace
- Lambda logs show "✅ Inserted 1 row into Aurora"

**Limitation**: Logs can lie (defensive logging might be missing)

### Step 4: Ground Truth (Strongest Evidence)
- Aurora table inspection shows data actually persisted
- S3 bucket contains uploaded file
- SQS queue has expected message

**Verification**: Directly inspect system state, don't trust status codes

---

## Common Boundary Failures

### Failure 1: Missing Environment Variable

**Symptom**: Lambda returns 500, CloudWatch shows KeyError

```python
# Code assumes TZ environment variable exists
tz = os.environ['TZ']  # KeyError if TZ not set
```

**Boundary**: Code → Runtime environment

**Verification**:
```bash
# Check Terraform has TZ
grep -A 10 "environment" terraform/lambda_config.tf | grep TZ

# Verify deployed Lambda has TZ
aws lambda get-function-configuration \
  --function-name LAMBDA_NAME \
  --query 'Environment.Variables.TZ'
```

**Fix**: Add TZ to Terraform, redeploy

---

### Failure 2: Schema Mismatch

**Symptom**: INSERT succeeds but data not persisted (silent failure)

```python
# Code passes pdf_s3_key parameter
store_report(symbol='DBS19', pdf_s3_key='s3://...')

# Function builds INSERT query
query = "INSERT INTO reports (symbol, ...) VALUES (%s, ...)"
# NOTE: Query doesn't include pdf_s3_key! Parameter silently ignored
```

**Boundary**: Code → Aurora schema

**Verification**:
```sql
-- Check schema has pdf_s3_key column
DESCRIBE precomputed_reports;

-- If missing, run migration first
ALTER TABLE precomputed_reports ADD COLUMN pdf_s3_key VARCHAR(255);
```

**Fix**: Run migration before deploying code

---

### Failure 3: Permission Denied

**Symptom**: Lambda returns error, CloudWatch shows AccessDenied

```python
# Code tries to write to S3
s3_client.put_object(Bucket='reports', Key='report.pdf', Body=pdf_data)
# Error: Access Denied (IAM role doesn't have s3:PutObject)
```

**Boundary**: Lambda IAM role → S3 bucket policy

**Verification**:
```bash
# Check Lambda IAM role has S3 permissions
aws iam get-role-policy \
  --role-name lambda-execution-role \
  --policy-name s3-access

# Check S3 bucket policy allows Lambda role
aws s3api get-bucket-policy --bucket reports
```

**Fix**: Add s3:PutObject permission to IAM role, attach to Lambda

---

### Failure 4: Network Blocked

**Symptom**: Lambda timeout, CloudWatch shows connection timeout

```python
# Code tries to connect to Aurora
connection = pymysql.connect(host=AURORA_HOST, ...)
# Error: Connection timeout (security group blocks port 3306)
```

**Boundary**: Lambda VPC → Aurora VPC (network access)

**Verification**:
```bash
# Check Lambda in correct VPC/subnets
aws lambda get-function-configuration --function-name LAMBDA_NAME \
  --query 'VpcConfig'

# Check security group allows port 3306
aws ec2 describe-security-groups --group-ids sg-xxxxx \
  --query 'SecurityGroups[0].IpPermissions'
```

**Fix**: Add inbound rule to security group (port 3306 from Lambda security group)

---

## Anti-Patterns

### ❌ Assuming Code Works Because Python Syntax is Valid

**Problem**: Code compiles but fails at runtime

```python
# Code looks correct
def handler(event, context):
    tz = os.environ['TZ']  # Assumes TZ exists
    # ... rest of logic
```

**Why it fails**: TZ environment variable missing in Lambda (not set in Terraform)

**Solution**: Verify Terraform config, test in Docker container

---

### ❌ Assuming Environment Variables Exist

**Problem**: Works locally (.env file), fails in Lambda

```python
# Local development
# .env file has: TZ=Asia/Bangkok
# Code works fine

# Lambda deployment
# No .env file, TZ not in Terraform
# Code crashes: KeyError 'TZ'
```

**Solution**: Verify Terraform/Doppler has ALL env vars code needs

---

### ❌ Assuming Database Schema Matches Code

**Problem**: Code INSERT expects column, Aurora doesn't have it

```python
# Code expects pdf_s3_key column
query = "INSERT INTO reports (symbol, pdf_s3_key) VALUES (%s, %s)"

# Aurora schema:
# reports table has: id, symbol, report_date
# Missing: pdf_s3_key
```

**Solution**: Run `SHOW COLUMNS FROM reports` before deploying code

---

### ❌ Stopping at Code Inspection

**Problem**: Reading code and concluding "this should work"

```python
# Analyst reads code:
def store_report(symbol, pdf_s3_key):
    query = "INSERT INTO reports (symbol, pdf_s3_key) VALUES (%s, %s)"
    cursor.execute(query, (symbol, pdf_s3_key))

# Analyst concludes: "Code looks correct" ✅

# Analyst SHOULD verify:
# - WHERE: Lambda (check Terraform)
# - WHAT env: TZ, AURORA_HOST (check Terraform)
# - WHAT schema: pdf_s3_key column (check Aurora)
# - WHAT contract: INSERT matches schema (test query)
```

**Solution**: Apply 5-question checklist, verify through ground truth

---

### ❌ Testing Locally Only

**Problem**: Local environment ≠ Lambda environment

```python
# Local testing
# - Python 3.11.7
# - All dependencies installed
# - Admin AWS credentials
# - .env file with all variables
# Test passes ✅

# Lambda runtime
# - Python 3.11.6 (might have different behavior)
# - Only dependencies in Lambda layer (might be missing some)
# - Least-privilege IAM role (permission denied)
# - Only env vars in Terraform (might be missing some)
# Production fails ❌
```

**Solution**: Test in Docker container (Lambda base image), verify deployed Lambda

---

## Real-World Impact

### Without Boundary Analysis

**Scenario**: Deploy code without verifying execution boundaries

```
Iteration 1: "Code looks correct, deploy"
  - Deploy (8 min)
  - Lambda returns 500
  - CloudWatch: Silent failure (pdf_s3_key parameter ignored)

Iteration 2: "Add logging, deploy"
  - Deploy (8 min)
  - Same failure
  - Logs show INSERT succeeded but data missing

Iteration 3: "Check Aurora schema... oh no column!"
  - SHOW COLUMNS FROM reports
  - pdf_s3_key column missing!
  - Root cause found

Total: 32 minutes + 3 deployments
```

### With Boundary Analysis

**Scenario**: Verify execution boundaries before deploying

```
Pre-deployment boundary analysis:
1. WHERE: Lambda (verified Terraform config)
2. WHAT env: TZ=Asia/Bangkok (verified Terraform)
3. WHAT services: Aurora (checked schema)
4. WHAT contract: INSERT needs pdf_s3_key column
   → SHOW COLUMNS FROM reports
   → pdf_s3_key NOT FOUND! ❌

Root cause found: 5 minutes, 0 deployments

Fix workflow:
1. Create migration: ALTER TABLE reports ADD COLUMN pdf_s3_key
2. Deploy migration (5 min)
3. Verify column exists (1 min)
4. Deploy code (8 min)

Total: 19 minutes + 2 deployments (1 migration + 1 code)
Savings: 13 minutes, 1 failed deployment avoided
```

**Benefits**:
- Faster root cause identification (5 min vs 24 min)
- Fewer deployments (1 vs 3 failed attempts)
- Higher confidence (verified all boundaries before deploying)
- Correct fix sequence (migration first, then code)

---

## Execution Boundary Checklist

Use this checklist when analyzing code in distributed systems:

### Pre-Analysis Boundary Identification

**1. Identify WHERE code executes**
- [ ] Local development? (laptop, venv)
- [ ] Lambda function? (which function, what runtime)
- [ ] Docker container? (local, ECS, Fargate)
- [ ] EC2 instance? (which instance, what OS)

**2. Identify WHAT environment code needs**
- [ ] Environment variables? (list all: TZ, AURORA_HOST, ...)
- [ ] Filesystem access? (read /tmp, write logs, ...)
- [ ] Network access? (VPC, security groups, internet)
- [ ] Permissions? (IAM role, resource policies)

**3. Identify WHAT services code calls**
- [ ] Aurora database? (verify schema matches code)
- [ ] S3 buckets? (verify bucket exists, permissions)
- [ ] SQS queues? (verify queue exists, message format)
- [ ] External APIs? (verify endpoint reachable, auth works)

**4. Identify WHAT entity properties apply**
- [ ] Lambda timeout/memory? (does workload fit)
- [ ] Aurora connection limits? (concurrent connections)
- [ ] S3 bucket policies? (IAM role access)
- [ ] Intended usage? (sync vs async design)

**5. Identify WHAT contracts must hold**
- [ ] Code → Database: INSERT columns match schema
- [ ] Code → API: Request format matches API spec
- [ ] Service A → Service B: Payload format matches
- [ ] Local → Deployed: Environment parity verified

### Boundary Verification Methods

**Process boundary (Code → Runtime)**:
- [ ] Terraform has all required env vars
- [ ] Lambda IAM role has necessary permissions
- [ ] Dependencies installed (Lambda layer or package)
- [ ] Test imports in Docker container (Lambda base image)

**Network boundary (Service A → Service B)**:
- [ ] Lambda in correct VPC (same as Aurora)
- [ ] Security groups allow required ports (3306 for Aurora)
- [ ] Network ACLs don't block traffic
- [ ] Test actual connectivity (Lambda invoke with connection test)

**Data boundary (Code → Storage)**:
- [ ] Aurora schema has all columns code expects
- [ ] Types match (Python dict → JSON string via json.dumps)
- [ ] Constraints satisfied (NOT NULL, UNIQUE)
- [ ] Test INSERT query manually

**Deployment boundary (Local → AWS)**:
- [ ] Terraform config matches code requirements
- [ ] Deployed Lambda has same env vars as Terraform
- [ ] CloudWatch logs show expected execution trace
- [ ] Ground truth verification (inspect Aurora/S3 directly)

---

## Integration with Other Principles

**Principle #1 (Defensive Programming)**:
- Validate initial conditions at startup (fail fast if boundary contract violated)
- Example: Check TZ env var exists before using datetime.now()

**Principle #2 (Progressive Evidence Strengthening)**:
- Verify through increasingly strong evidence sources
- Example: Terraform config → Lambda config → CloudWatch logs → Aurora state

**Principle #4 (Type System Integration)**:
- Research type compatibility at data boundaries
- Example: PyMySQL accepts JSON string, not Python dict

**Principle #15 (Infrastructure-Application Contract)**:
- Sync code and infrastructure before deploying
- Example: Run migration before deploying code that expects new column

**Principle #19 (Cross-Boundary Contract Testing)**:
- Test transitions at boundaries, not just within boundaries
- Example: Test Lambda startup without TZ env var (deployment → first invocation)

---

## When to Apply

✅ **Before concluding "code is correct"**
- Systematically verify WHERE code runs and WHAT it needs
- Don't skip boundary verification just because code looks right

✅ **Before deploying to production**
- Verify all execution boundaries match reality
- Test in Docker container (Lambda runtime environment)

✅ **When investigating "code works locally but fails in Lambda"**
- Identify deployment boundary (local → AWS)
- Verify environment parity (env vars, dependencies, permissions)

✅ **When adding new service dependencies**
- Identify network boundary (Lambda → new service)
- Verify connectivity, permissions, schema/API compatibility

✅ **After 2 failed deployment attempts**
- Switch from iteration to investigation
- Apply boundary checklist systematically

---

## Rationale

**Why boundary discipline matters**:

Code can be syntactically correct but fail in production because execution boundaries aren't verified. These failures are invisible from code inspection alone—must verify WHERE code runs and WHAT it needs.

**Common root causes**:
- Missing environment variable (Lambda vs local)
- Schema mismatch (code INSERT vs Aurora columns)
- Permission denied (IAM role vs resource policy)
- Network blocked (VPC vs internet)
- Configuration mismatch (Lambda timeout vs workload duration)
- Intentional mismatch (sync Lambda used for async work)

**Benefits of systematic boundary verification**:
- Catch issues before deployment (faster feedback)
- Fewer failed deployments (higher confidence)
- Correct fix sequence (infrastructure first, then code)
- Better incident analysis (identify which boundary violated)

---

## See Also

- **Abstraction**: [Missing Execution Boundary Analysis](.claude/abstractions/failure_mode-2026-01-03-missing-execution-boundary-analysis.md) - Complete failure mode documentation
- **Checklist**: [Execution Boundary Checklist](.claude/checklists/execution-boundaries.md) - Systematic verification workflow
- **Skill**: [research](.claude/skills/research/) - Investigation methodology with boundary analysis
- **Skill**: [error-investigation](.claude/skills/error-investigation/) - AWS-specific debugging patterns

---

*Guide version: 2026-01-04*
*Principle: #20 in CLAUDE.md*
*Status: Graduated from failure mode to principle to implementation guide*
