# Execution Boundary Verification Checklist

**Purpose**: Systematically identify and validate execution boundaries BEFORE concluding "code is correct"

**When to use**:
- ✓ Analyzing distributed systems (Lambda, Step Functions, Aurora, S3, SQS)
- ✓ Validating multi-service workflows
- ✓ Investigating "code looks correct but doesn't work" bugs
- ✓ Reviewing deployment configurations
- ✓ Adding new service integrations

**When NOT to use**:
- ✗ Pure computation (no external dependencies)
- ✗ Single-process systems (no service boundaries)
- ✗ Well-tested stable code (boundaries already validated)

---

## Quick Start

Before analyzing code correctness, ask:

1. **WHERE does this code run?** (Lambda, EC2, local, Docker?)
2. **WHAT environment does it need?** (env vars, files, network?)
3. **WHAT services does it call?** (Aurora, S3, SQS, external APIs?)
4. **WHAT contracts must hold?** (schemas, payloads, permissions?)

If you can't answer all 4 questions, you're missing execution boundaries.

---

## Detailed Checklist

### Phase 1: Identify Execution Context

**WHERE does this code execute?**

- [ ] Execution environment identified:
  - [ ] Local development (laptop, venv, manual invocation)
  - [ ] Lambda function (which function: `dr-daily-report-{name}-{env}`)
  - [ ] EC2 instance (which instance ID, what role)
  - [ ] Container (Docker, ECS, Fargate)
  - [ ] Step Functions (state machine, which state)
  - [ ] Other: _______________

- [ ] Runtime characteristics documented:
  - [ ] Language/runtime version (Python 3.12, Node.js 20, etc.)
  - [ ] Memory allocation (Lambda: 128MB-10GB)
  - [ ] Timeout limit (Lambda: 15 min max, Step Functions: 1 year max)
  - [ ] Execution model (synchronous, async, event-driven)

**Example**:
```markdown
WHERE: Lambda function `dr-daily-report-report-worker-dev`
RUNTIME: Python 3.12, 1024MB memory, 180s timeout
MODEL: Async (SQS-triggered)
```

---

### Phase 2: Validate Environment Contracts

**WHAT environment does this code need?**

#### Environment Variables

- [ ] All environment variables identified:
  ```python
  # From code inspection
  os.environ.get('TZ')                    # Required: timezone
  os.environ.get('AURORA_HOST')           # Required: database host
  os.environ.get('AURORA_PORT')           # Required: database port
  os.environ.get('AURORA_USER')           # Required: database user
  os.environ.get('AURORA_PASSWORD')       # Required: database password
  os.environ.get('AURORA_DATABASE')       # Required: database name
  os.environ.get('S3_BUCKET')             # Required: S3 bucket name
  os.environ.get('CACHE_TABLE_NAME')      # Required: DynamoDB table
  ```

- [ ] Environment variables verified in infrastructure:
  - [ ] Terraform configuration checked (`terraform/*.tf`)
  - [ ] CloudFormation template checked (if used)
  - [ ] Doppler secrets checked (`doppler secrets`)
  - [ ] GitHub secrets checked (`gh secret list`)

- [ ] Startup validation exists:
  ```python
  # Does code validate env vars at startup?
  def _validate_configuration():
      required = ['TZ', 'AURORA_HOST', ...]
      missing = [var for var in required if not os.environ.get(var)]
      if missing:
          raise RuntimeError(f"Missing env vars: {missing}")
  ```

**Example verification**:
```bash
# Check Terraform
rg "TZ" terraform/lambda_worker.tf
# Found: environment { TZ = "Asia/Bangkok" } ✅

# Check actual deployed value
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'Environment.Variables.TZ' --output text
# Returns: Asia/Bangkok ✅
```

#### Filesystem Access

- [ ] Filesystem requirements identified:
  - [ ] Read access needed? (config files, certificates, etc.)
  - [ ] Write access needed? (logs, temp files, cache)
  - [ ] Writable directories identified (`/tmp` in Lambda)
  - [ ] File size limits known (512MB `/tmp` in Lambda)

- [ ] Filesystem access verified:
  ```python
  # Does code assume files exist?
  with open('/etc/app/config.json') as f:  # ❌ Won't exist in Lambda
      config = json.load(f)

  # Lambda-safe alternative
  config = json.loads(os.environ.get('CONFIG_JSON'))  # ✅ From env var
  ```

#### Network Access

- [ ] Network requirements identified:
  - [ ] Internet access needed? (external APIs)
  - [ ] VPC access needed? (Aurora, RDS, private resources)
  - [ ] Security groups configured? (ingress/egress rules)
  - [ ] NAT Gateway available? (for VPC Lambda → internet)

- [ ] Network access verified:
  ```bash
  # Check Lambda VPC configuration
  aws lambda get-function-configuration \
    --function-name dr-daily-report-report-worker-dev \
    --query 'VpcConfig'

  # Check security groups allow Aurora access
  aws ec2 describe-security-groups \
    --group-ids sg-12345678 \
    --query 'SecurityGroups[0].IpPermissions'
  ```

---

### Phase 3: Validate Service Integrations

**WHAT services does this code call?**

#### Aurora MySQL Database

- [ ] Database connection requirements:
  - [ ] Host/port reachable from execution environment?
  - [ ] VPC/security group allows connection?
  - [ ] Database user has required permissions?
  - [ ] Connection timeout configured appropriately?

- [ ] Database schema matches code expectations:
  ```sql
  -- Verify table exists
  SHOW TABLES LIKE 'precomputed_reports';

  -- Verify columns match code
  SHOW COLUMNS FROM precomputed_reports;

  -- Check for missing columns
  -- If code INSERT uses pdf_s3_key, verify column exists:
  SELECT COLUMN_NAME
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = 'ticker_data'
    AND TABLE_NAME = 'precomputed_reports'
    AND COLUMN_NAME = 'pdf_s3_key';
  -- Returns: Empty set → COLUMN MISSING ❌
  ```

- [ ] Data types match code expectations:
  ```python
  # Code sends dict
  cursor.execute("INSERT INTO tbl (json_col) VALUES (%s)", ({'key': 'val'},))

  # Does Aurora accept dict or require JSON string?
  # PyMySQL: Requires json.dumps() ← VERIFY THIS
  ```

- [ ] Schema migration status checked:
  ```bash
  # Check latest migration applied
  ls -la db/migrations/ | tail -5
  # Latest: 018_drop_ticker_info_table.sql

  # Does code depend on migration 019+ features?
  # If yes → migration must be applied BEFORE deployment
  ```

#### S3 Buckets

- [ ] S3 access requirements:
  - [ ] Bucket exists in target AWS account/region?
  - [ ] Lambda IAM role has s3:PutObject permission?
  - [ ] Bucket policy allows Lambda role?
  - [ ] Bucket encryption compatible with code?

- [ ] S3 access verified:
  ```bash
  # Check bucket exists
  aws s3 ls s3://dr-daily-report-dev-storage/

  # Check Lambda role permissions
  aws iam get-role-policy \
    --role-name dr-daily-report-worker-role-dev \
    --policy-name S3Access \
    --query 'PolicyDocument.Statement'

  # Test write access (from Lambda or local with same role)
  echo "test" | aws s3 cp - s3://dr-daily-report-dev-storage/test.txt
  ```

- [ ] S3 key format matches code expectations:
  ```python
  # Code generates key
  pdf_s3_key = f"reports/{symbol}/{date}/{symbol}_report_{date}_{timestamp}.pdf"

  # Verify key doesn't exceed limits (1024 chars max)
  # Verify no special characters that need encoding
  # Verify bucket prefix/suffix rules followed
  ```

#### SQS Queues

- [ ] SQS access requirements:
  - [ ] Queue exists in target AWS account/region?
  - [ ] Lambda has sqs:SendMessage permission (producer)?
  - [ ] Lambda has sqs:ReceiveMessage permission (consumer)?
  - [ ] Dead letter queue configured?

- [ ] SQS message format verified:
  ```python
  # What does sender send?
  message_body = json.dumps({
      'ticker': 'DBS19',
      'source': 'step_functions_precompute'
  })

  # What does receiver expect?
  message = json.loads(event['Records'][0]['body'])
  ticker = message['ticker']  # Must match sender format
  ```

- [ ] SQS limits checked:
  - [ ] Message size < 256 KB?
  - [ ] Visibility timeout > Lambda timeout?
  - [ ] Batch size appropriate for processing time?

#### External APIs

- [ ] API access requirements:
  - [ ] Endpoint reachable from Lambda (internet or VPN)?
  - [ ] API key/authentication configured?
  - [ ] Rate limits known and respected?
  - [ ] Timeout configured appropriately?

- [ ] API contract verified:
  ```bash
  # Test API request format
  curl -X POST https://api.example.com/v1/reports \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"symbol": "DBS19"}'

  # Verify response format matches code expectations
  # Code expects: {"report": {...}}
  # API returns: {"data": {"report": {...}}} ← MISMATCH
  ```

#### Service Integration Boundaries (NEW)

**Purpose**: Verify AWS service-to-service payload contracts (Step Functions → Lambda, EventBridge → Step Functions, etc.)

**When to check**:
- ✅ Adding new service integration
- ✅ Debugging "works in isolation but fails end-to-end"
- ✅ After infrastructure changes
- ✅ Zero-gradient debugging pattern (2+ attempts, same outcome)

**Step Functions → Lambda**:

- [ ] Payload passthrough configured correctly:
  ```json
  // ❌ WRONG: Hardcoded empty payload
  "Parameters": {
    "FunctionName": "arn:...:function:my-lambda",
    "Payload": {}
  }

  // ✅ CORRECT: JsonPath reference passes input
  "Parameters": {
    "FunctionName": "arn:...:function:my-lambda",
    "Payload.$": "$"  // Pass entire input
  }
  ```

- [ ] Lambda receives expected event structure:
  ```python
  # Lambda expects
  def lambda_handler(event, context):
      report_date = event['report_date']  # Must exist in event

  # Verify Step Functions passes it
  # Check execution history:
  aws stepfunctions get-execution-history --execution-arn "$ARN" > history.json
  jq '.events[2].taskScheduledEventDetails.parameters' history.json
  # Look for: "Payload": {"report_date": "2026-01-04"} ✅
  ```

- [ ] Payload format matches Lambda expectations:
  ```bash
  # Direct Lambda test (isolate service boundary)
  aws lambda invoke \
    --function-name my-lambda \
    --cli-binary-format raw-in-base64-out \
    --payload '{"report_date":"2026-01-04"}' \
    response.json

  # If direct invocation works but Step Functions doesn't:
  # → Payload passthrough bug in Step Functions definition
  ```

**EventBridge → Step Functions**:

- [ ] Event pattern matches source events:
  ```json
  // EventBridge rule
  {
    "source": ["aws.states"],
    "detail-type": ["Step Functions Execution Status Change"],
    "detail": {
      "status": ["SUCCEEDED"],
      "stateMachineArn": ["arn:...:stateMachine:precompute-workflow-dev"]
    }
  }

  // Verify pattern matches actual events
  aws events test-event-pattern \
    --event-pattern file://pattern.json \
    --event file://sample-event.json
  ```

- [ ] Input transformer configured (if used):
  ```json
  // Transform EventBridge event → Step Functions input
  "InputTransformer": {
    "InputPathsMap": {
      "executionId": "$.detail.name"
    },
    "InputTemplate": "{\"execution_id\": \"<executionId>\"}"
  }
  ```

**SQS → Lambda (Event Source Mapping)**:

- [ ] Message body format matches Lambda expectations:
  ```python
  # Lambda expects
  def lambda_handler(event, context):
      for record in event['Records']:
          body = json.loads(record['body'])  # SQS wraps in Records

  # Verify SQS sender matches
  # Sender must: json.dumps(message) before sqs.send_message()
  ```

- [ ] Batch size appropriate:
  ```bash
  # Check event source mapping
  aws lambda get-event-source-mapping --uuid $UUID \
    --query 'BatchSize'

  # Ensure: BatchSize * processing_time < Lambda timeout
  ```

**API Gateway → Lambda**:

- [ ] Integration type matches Lambda expectations:
  ```json
  // Lambda integration (raw event)
  "IntegrationType": "AWS"  // Lambda gets API Gateway event structure

  // Lambda proxy integration (simplified)
  "IntegrationType": "AWS_PROXY"  // Lambda gets HTTP request structure
  ```

- [ ] Request/response transformation configured:
  ```bash
  # Check API Gateway integration
  aws apigatewayv2 get-integration --api-id $API_ID --integration-id $INT_ID \
    --query '{Type:IntegrationType,PayloadFormat:PayloadFormatVersion}'
  ```

**Debugging Protocol** (4-Layer Evidence):

When service integration fails:

1. **Layer 1 (Surface)**: Check final status
   ```bash
   aws stepfunctions describe-execution --execution-arn "$ARN" --query 'status'
   ```

2. **Layer 3 (Observability)**: Check execution history FIRST (not logs)
   ```bash
   # What payload was actually sent?
   aws stepfunctions get-execution-history --execution-arn "$ARN" > history.json
   jq '.events[] | select(.type=="TaskScheduled")' history.json
   ```

3. **Layer 4 (Ground Truth)**: Invoke target service directly
   ```bash
   # Does Lambda work when invoked directly?
   aws lambda invoke --function-name my-lambda --payload '{"test":"data"}' out.json
   ```

4. **Layer 2 (Content)**: Check logs for confirmation
   ```bash
   # What event did Lambda receive?
   aws logs tail /aws/lambda/my-lambda --since 5m
   ```

**Optimal debugging order**: 1 → 3 → 4 → 2 (execution history reveals integration bugs fastest)

**Integration test checklist**:

- [ ] Test written for service boundary:
  ```python
  def test_step_functions_passes_payload_to_lambda():
      """Verify Step Functions → Lambda payload passthrough"""
      # Prevents configuration regressions
  ```

- [ ] Test runs in CI/CD:
  ```yaml
  # .github/workflows/test.yml
  - name: Test service integrations
    run: pytest tests/integration/test_step_functions_integration.py
  ```

- [ ] Terraform changes trigger integration tests:
  ```bash
  # Before deploying Step Functions changes
  terraform plan && pytest tests/integration/
  ```

**See**: [Service Integration Verification Pattern](.claude/patterns/service-integration-verification.md) for complete debugging protocol

---

### Phase 4: Validate Cross-Boundary Contracts

**WHAT contracts must hold between layers?**

#### Code → Runtime Contract

- [ ] Python version matches deployment:
  ```python
  # Code uses walrus operator (Python 3.8+)
  if (result := fetch_data()):  # Requires Python 3.8+
      process(result)

  # Check Lambda runtime
  # Terraform: runtime = "python3.12" ✅
  ```

- [ ] Dependencies available in runtime:
  ```python
  # Code imports library
  import pandas as pd  # Does Lambda layer include pandas?

  # Check Lambda layers
  aws lambda get-function-configuration \
    --function-name dr-daily-report-report-worker-dev \
    --query 'Layers[*].Arn'
  ```

- [ ] File paths valid for runtime:
  ```python
  # Local development
  LOG_FILE = '/home/user/app.log'  # ❌ Won't work in Lambda

  # Lambda-compatible
  LOG_FILE = '/tmp/app.log'  # ✅ /tmp is writable in Lambda
  ```

#### Code → Infrastructure Contract

- [ ] Code assumptions match Terraform reality:
  ```python
  # Code assumes
  aurora_host = os.environ['AURORA_HOST']  # Expects env var

  # Terraform must provide
  environment_variables = {
    AURORA_HOST = aws_rds_cluster.aurora.endpoint  # ✅ Provided
  }
  ```

- [ ] Infrastructure changes deployed BEFORE code changes:
  ```markdown
  # Correct order:
  1. Terraform apply (add AURORA_HOST env var)
  2. Wait for Lambda update
  3. Deploy code (uses AURORA_HOST)

  # Wrong order (will fail):
  1. Deploy code (expects AURORA_HOST)
  2. Terraform apply (adds AURORA_HOST) ← Too late!
  ```

#### Code → Database Contract

- [ ] INSERT query columns match table schema:
  ```python
  # Code INSERT
  INSERT INTO precomputed_reports (
    symbol, report_date, report_text, pdf_s3_key  # ← Code expects
  ) VALUES (%s, %s, %s, %s)

  # Aurora schema
  mysql> SHOW COLUMNS FROM precomputed_reports;
  # Missing: pdf_s3_key ❌

  # CONTRACT VIOLATED → Silent failure or error
  ```

- [ ] Data types match:
  ```python
  # Code sends
  report_json = {'key': 'value'}  # Python dict

  # Aurora expects
  # JSON column type ← Requires JSON string, not dict

  # Fix
  json.dumps(report_json)  # Convert to string
  ```

- [ ] Foreign key constraints satisfied:
  ```sql
  -- Aurora schema
  ALTER TABLE precomputed_reports
  ADD CONSTRAINT fk_ticker
  FOREIGN KEY (ticker_id) REFERENCES ticker_master(id);

  -- Code must ensure ticker_id exists in ticker_master first
  # Otherwise: IntegrityError: foreign key constraint fails
  ```

#### Service A → Service B Contract

- [ ] Payload format matches:
  ```python
  # Step Functions sends
  {
    "ticker": "DBS19",
    "source": "step_functions_precompute"
  }

  # Lambda expects
  message = event['Records'][0]['body']  # SQS wraps payload
  data = json.loads(message)
  ticker = data['ticker']  # ✅ Format matches
  ```

- [ ] Authentication/authorization works:
  ```bash
  # Lambda calls Step Functions
  aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:...

  # Verify Lambda role has stepfunctions:StartExecution permission
  aws iam get-role-policy \
    --role-name dr-daily-report-worker-role-dev \
    --policy-name StepFunctionsAccess
  ```

---

## Boundary Type Reference

### 1. Process Boundary (Code → Runtime)

**What to verify**:
- Environment variables exist and have correct values
- Filesystem paths valid for runtime environment
- Dependencies (libraries, layers) available
- Runtime version matches code requirements

**Common failures**:
- Missing env var → `KeyError: 'AURORA_HOST'`
- Wrong Python version → `SyntaxError: invalid syntax`
- Missing dependency → `ModuleNotFoundError: No module named 'pandas'`

---

### 2. Network Boundary (Service → Service)

**What to verify**:
- Network connectivity (VPC, security groups, NAT)
- DNS resolution (service endpoints reachable)
- Firewall rules (ingress/egress allowed)
- Timeout configuration (connection, read, write)

**Common failures**:
- VPC Lambda can't reach internet → `ConnectionError: [Errno 110] Connection timed out`
- Security group blocks Aurora → `OperationalError: (2003, "Can't connect to MySQL server")`

---

### 3. Data Boundary (Code → Storage)

**What to verify**:
- Database schema matches code expectations (tables, columns, types)
- API response format matches code parsing logic
- Message queue payload format matches code deserialization
- File format matches code reading logic

**Common failures**:
- Missing column → Silent ignore or `Unknown column 'pdf_s3_key'`
- Type mismatch → `TypeError: Object of type dict is not JSON serializable`
- Format mismatch → `KeyError: 'data'` (code expects different structure)

---

## Entity Identification Guide

**Purpose**: Identify the "physical what" (specific entities with ARNs, IDs, names) rather than just "conceptual what" (Lambda → Aurora boundary type)

**Why this matters**: Boundary verification requires knowing WHICH Lambda function, WHICH Aurora cluster, WHICH S3 bucket—not just the boundary types.

### Step 1: Identify Code Entity

**What to find**:
- Exact file path where code executes (e.g., `src/report_worker_handler.py`)
- Function/class name that contains logic
- Entry point (Lambda handler, CLI command, API endpoint)

**How to verify**:
```bash
# Find Lambda handler function
rg "def lambda_handler" src/

# Find specific function
rg "def store_report" src/

# Identify execution flow
cat src/report_worker_handler.py | grep -A 10 "lambda_handler"
```

**Document**:
- Code entity: `src/report_worker_handler.py::lambda_handler()`
- Purpose: Processes SQS messages to generate reports
- Trigger: SQS queue message arrival

### Step 2: Identify Runtime Entity

**What to find**:
- AWS Lambda function name (e.g., `dr-daily-report-report-worker-dev`)
- Lambda ARN for exact identity
- Runtime configuration (Python version, memory, timeout)

**How to verify**:
```bash
# Find Lambda function
aws lambda list-functions --query 'Functions[?contains(FunctionName, `report-worker`)].FunctionName'

# Get complete configuration
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --output json

# Extract critical properties
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query '{Name:FunctionName, Timeout:Timeout, Memory:MemorySize, Runtime:Runtime}'
```

**Document**:
- Runtime entity: `dr-daily-report-report-worker-dev`
- ARN: `arn:aws:lambda:ap-southeast-1:123456789012:function:dr-daily-report-report-worker-dev`
- Configuration: Python 3.12, 512 MB memory, 300s timeout

### Step 3: Identify Infrastructure Entity

**What to find**:
- Terraform resource that creates Lambda
- Module and variable references
- Resource dependencies

**How to verify**:
```bash
# Find Terraform resource
rg "resource \"aws_lambda_function\"" terraform/

# Find Lambda definition
cat terraform/lambdas.tf | grep -A 20 "report-worker"

# Check Terraform state
terraform state list | grep lambda
terraform state show 'aws_lambda_function.report_worker'
```

**Document**:
- Infrastructure entity: `aws_lambda_function.report_worker` (Terraform)
- File: `terraform/lambdas.tf:45-78`
- Dependencies: IAM role, VPC, security groups, environment variables

### Step 4: Identify Storage Entity

**What to find**:
- Aurora cluster name (e.g., `dr-daily-report-aurora-dev`)
- Database name, table names
- Connection endpoints

**How to verify**:
```bash
# Find Aurora cluster
aws rds describe-db-clusters --query 'DBClusters[?contains(DBClusterIdentifier, `daily-report`)].DBClusterIdentifier'

# Get cluster details
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{Endpoint:Endpoint, Port:Port, Engine:Engine, Status:Status}'

# Verify table schema
mysql -h <endpoint> -u admin -p << 'SQL'
SHOW TABLES;
DESCRIBE precomputed_reports;
SQL
```

**Document**:
- Storage entity: Aurora cluster `dr-daily-report-aurora-dev`
- Endpoint: `dr-daily-report-aurora-dev.cluster-xyz.ap-southeast-1.rds.amazonaws.com:3306`
- Tables: `precomputed_reports`, `ticker_master`, `daily_prices`

### Step 5: Identify Permission Entity

**What to find**:
- IAM role attached to Lambda
- Inline policies and managed policies
- Resource policies on target services

**How to verify**:
```bash
# Find Lambda role
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'Role'

# Get role policies
aws iam list-attached-role-policies --role-name dr-daily-report-worker-role-dev
aws iam list-role-policies --role-name dr-daily-report-worker-role-dev

# Get policy details
aws iam get-policy-version \
  --policy-arn arn:aws:iam::123456789012:policy/lambda-aurora-access \
  --version-id v1 \
  --query 'PolicyVersion.Document'
```

**Document**:
- Permission entity: IAM role `dr-daily-report-worker-role-dev`
- Attached policies: `lambda-aurora-access`, `AWSLambdaVPCAccessExecutionRole`
- Permissions: Aurora connection, S3 write, CloudWatch logs

### Entity Mapping Table

Create a mapping table showing relationships:

| Boundary | Source Entity | Target Entity | Contract |
|----------|---------------|---------------|----------|
| Code → Runtime | `report_worker_handler.py::lambda_handler()` | Lambda `dr-daily-report-report-worker-dev` | Expects `event` dict with SQS records |
| Runtime → Storage | Lambda `dr-daily-report-report-worker-dev` | Aurora `dr-daily-report-aurora-dev` | Requires VPC access + IAM auth |
| Code → Storage | `precompute_service.py::store_report()` | Aurora table `precomputed_reports` | INSERT requires `pdf_s3_key` column |
| Runtime → Permission | Lambda `dr-daily-report-report-worker-dev` | IAM role `dr-daily-report-worker-role-dev` | Role allows S3 write, Aurora connect |

**Benefits**:
- Clear traceability (code file → AWS resource → infrastructure config)
- Enables verification (check EXACT Lambda has EXACT permission to EXACT Aurora cluster)
- Prevents "works in dev, fails in prod" (different entity configurations)

---

## Entity Configuration Verification

**Purpose**: Verify entity configuration matches code requirements (Layer 4: Configuration Correctness)

**Pattern**: Code requirements → Entity configuration → MATCH or MISMATCH

### Lambda Configuration Verification

#### Timeout Configuration

**Code requirement analysis**:
```python
# Code makes external API call
response = requests.get(external_api_url, timeout=60)  # 60s timeout

# Code waits for database query
result = cursor.execute(slow_query)  # Might take 45s

# Total execution time: 60s + 45s + overhead = ~120s
```

**Lambda configuration check**:
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query '{Name:FunctionName, Timeout:Timeout}'

# Output: {"Name": "...", "Timeout": 30}
```

**Verification**:
- Code requires: ~120s
- Lambda configured: 30s
- **MISMATCH ❌**: Lambda will timeout before code completes

**Fix**:
```hcl
# terraform/lambdas.tf
resource "aws_lambda_function" "report_worker" {
  timeout = 180  # Increase to 180s (120s + 60s buffer)
}
```

#### Memory Configuration

**Code requirement analysis**:
```python
# Code loads large dataset
import pandas as pd
df = pd.read_csv('large_file.csv')  # 200 MB CSV

# Code processes data in memory
processed = df.groupby('ticker').apply(complex_transform)  # ~300 MB peak
```

**Lambda configuration check**:
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'MemorySize'

# Output: 128
```

**Verification**:
- Code requires: ~300 MB peak memory
- Lambda configured: 128 MB
- **MISMATCH ❌**: Lambda will OOM (Out of Memory)

**Fix**:
```hcl
resource "aws_lambda_function" "report_worker" {
  memory_size = 512  # Increase to 512 MB (300 MB + buffer)
}
```

#### Concurrency Configuration

**Code requirement analysis**:
```python
# SQS queue receives 100 messages/minute
# Each message takes 30s to process
# Required concurrency: (100 messages/60s) * 30s = 50 concurrent executions
```

**Lambda configuration check**:
```bash
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'ReservedConcurrentExecutions'

# Output: null (default: account limit, usually 1000)
```

**Verification**:
- Code requires: 50 concurrent executions
- Lambda configured: null (unreserved, shares account limit)
- **MATCH ✅**: Sufficient concurrency (but might want to reserve to prevent throttling)

**Optional improvement**:
```hcl
resource "aws_lambda_function" "report_worker" {
  reserved_concurrent_executions = 50  # Reserve capacity
}
```

### Aurora Configuration Verification

#### Connection Limit Configuration

**Code requirement analysis**:
```python
# Lambda has 50 concurrent executions
# Each Lambda creates 1 Aurora connection
# Required: 50 connections minimum
```

**Aurora configuration check**:
```bash
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].{Class:DBInstanceClass, Connections:MaxAllocatedStorage}'

# Check parameter group
aws rds describe-db-cluster-parameters \
  --db-cluster-parameter-group-name default.aurora-mysql8.0 \
  --query 'Parameters[?ParameterName==`max_connections`].ParameterValue'
```

**Verification**:
- Code requires: 50 connections
- Aurora configured: max_connections = 100
- **MATCH ✅**: Sufficient connection capacity

#### Storage Configuration

**Code requirement analysis**:
```python
# Precompute stores 46 tickers * 365 days * 100 KB/report = ~1.7 GB/year
# Add historical data: ~10 GB total
```

**Aurora configuration check**:
```bash
aws rds describe-db-clusters \
  --db-cluster-identifier dr-daily-report-aurora-dev \
  --query 'DBClusters[0].AllocatedStorage'
```

**Verification**:
- Code requires: ~10 GB
- Aurora configured: 20 GB
- **MATCH ✅**: Sufficient storage (2x buffer)

### S3 Configuration Verification

#### Storage Class Configuration

**Code requirement analysis**:
```python
# Code generates PDFs: ~500 KB each
# Access pattern: Frequent reads in first 30 days, rare after
# Ideal: S3 Standard (0-30 days) → S3 IA (30+ days)
```

**S3 configuration check**:
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket dr-daily-report-dev-storage

# Check default storage class
aws s3api get-bucket-location --bucket dr-daily-report-dev-storage
```

**Verification**:
- Code requires: Lifecycle transition after 30 days
- S3 configured: No lifecycle policy
- **MISMATCH ⚠️**: Works but not cost-optimized

**Improvement**:
```hcl
resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  rule {
    id     = "transition-old-reports"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}
```

### Entity Configuration Checklist

- [ ] **Lambda timeout** matches code execution time (measured + buffer)
- [ ] **Lambda memory** matches code peak usage (profiled + buffer)
- [ ] **Lambda concurrency** matches workload rate (messages/sec * processing time)
- [ ] **Aurora max_connections** ≥ Lambda concurrency (prevent connection exhaustion)
- [ ] **Aurora storage** ≥ projected data growth (1-2 year projection)
- [ ] **S3 storage class** matches access pattern (frequent vs infrequent)
- [ ] **VPC subnet** has sufficient IP addresses (ENI per Lambda concurrent execution)

---

## Entity Intention Verification

**Purpose**: Verify entity usage matches its designed purpose (Layer 5: Intentional Correctness)

**Pattern**: How is entity being used? → What was entity designed for? → MATCH or VIOLATION

### Understanding Entity Intention

**Sources of intention**:
1. **AWS Service Documentation**: Intended use cases for Lambda, Aurora, S3
2. **Terraform Comments**: Why was this resource created? (inline documentation)
3. **Architecture Decisions**: ADRs documenting technology choices
4. **Resource Tags**: `Purpose`, `Workload` tags describing intent
5. **Git History**: Original commit message creating the resource

**Example - Discovering Lambda Intention**:
```bash
# Check Terraform comments
cat terraform/lambdas.tf | grep -B 5 -A 20 "report-worker"

# Check resource tags
aws lambda list-tags --resource arn:aws:lambda:...:function:report-worker-dev

# Check git history
git log --follow -p terraform/lambdas.tf | grep -A 10 "report-worker"

# Expected findings:
# - Terraform comment: "Async worker for long-running report generation"
# - Tag: Purpose=background-processing
# - Commit: "Add async Lambda for PDF generation (not API-facing)"
```

### Intention Verification Examples

#### Example 1: Synchronous API Using Async Lambda

**Entity**: Lambda function `api-handler-dev`

**Discovered intention**:
```hcl
# terraform/lambdas.tf
# API Gateway integration - Synchronous request/response
resource "aws_lambda_function" "api_handler" {
  function_name = "api-handler-dev"
  # Tag: Purpose=synchronous-api
}
```

**Actual usage**:
```python
# src/api_handler.py
def lambda_handler(event, context):
    # Long-running operation
    result = generate_report(ticker)  # Takes 60s
    return {"statusCode": 200, "body": json.dumps(result)}
```

**Verification**:
- **Designed for**: Synchronous API (< 30s response time)
- **Used for**: Long-running operation (60s)
- **VIOLATION ⚠️**: Using sync Lambda for async workload

**Why this is wrong**:
- API Gateway has 30s timeout → Lambda will always timeout
- Client waits 60s blocking UI → poor UX
- Wastes Lambda execution time (client might have disconnected)

**Correct pattern**:
```python
# API should return immediately with job ID
def lambda_handler(event, context):
    job_id = str(uuid.uuid4())
    sqs.send_message(QueueUrl=WORKER_QUEUE, MessageBody=json.dumps({
        'job_id': job_id,
        'ticker': ticker
    }))
    return {"statusCode": 202, "body": json.dumps({"job_id": job_id})}

# Separate worker Lambda processes job asynchronously
```

#### Example 2: Lambda Layer for Development Dependencies

**Entity**: Lambda layer `dev-dependencies`

**Discovered intention**:
```bash
# Check layer name and git history
aws lambda list-layers | grep dev-dependencies

git log --all --grep="dev-dependencies"
# Commit: "Add layer for pytest, black, mypy (development only)"
```

**Actual usage**:
```python
# Production Lambda using dev layer
import pytest  # ❌ Production code importing test framework

def lambda_handler(event, context):
    # ... uses pytest fixtures in production ...
```

**Verification**:
- **Designed for**: Development/testing tools (not production)
- **Used for**: Production Lambda runtime
- **VIOLATION ❌**: Development dependencies in production

**Why this is wrong**:
- Bloated Lambda package (100 MB layer for unused tools)
- Security risk (test tools might have vulnerabilities)
- Confusing signal (pytest in production implies testing, not execution)

**Correct pattern**:
```hcl
# Separate layers for dev and prod
resource "aws_lambda_layer_version" "prod_dependencies" {
  layer_name = "prod-dependencies"
  # Only: pandas, requests, boto3
}

resource "aws_lambda_layer_version" "dev_dependencies" {
  layer_name = "dev-dependencies"
  # Only attached to dev/test Lambdas
}
```

#### Example 3: Aurora Serverless for Predictable Workload

**Entity**: Aurora Serverless cluster `reports-db-dev`

**Discovered intention**:
```bash
# Check Aurora engine mode
aws rds describe-db-clusters \
  --db-cluster-identifier reports-db-dev \
  --query 'DBClusters[0].EngineMode'
# Output: "serverless"

# Check Terraform
cat terraform/aurora.tf | grep -A 10 "serverless"
# Comment: "Serverless for unpredictable dev workload"
```

**Actual usage**:
- EventBridge scheduler runs 46 jobs nightly at 01:00 (predictable spike)
- Daytime: Minimal traffic (5-10 queries/hour)
- Pattern: Highly predictable, not bursty

**Verification**:
- **Designed for**: Unpredictable bursty workload (serverless scales on demand)
- **Used for**: Predictable scheduled workload (nightly batch)
- **VIOLATION ⚠️**: Using serverless for predictable workload (waste of cost)

**Why this is wrong**:
- Serverless charges per ACU-hour, expensive for sustained load
- Cold start delays when scheduler triggers 46 jobs simultaneously
- Provisioned Aurora would be cheaper and faster (always warm)

**Correct pattern**:
```hcl
# Use provisioned Aurora for predictable scheduled workload
resource "aws_rds_cluster" "reports_db" {
  engine_mode = "provisioned"
  # Right-size based on measured peak load
}
```

### Intention Verification Checklist

- [ ] **Lambda invocation type** matches workload (sync API = RequestResponse, async job = Event)
- [ ] **Lambda layers** contain only production dependencies (no dev/test tools)
- [ ] **Aurora engine mode** matches workload (serverless = unpredictable, provisioned = predictable)
- [ ] **S3 bucket** used for intended data type (reports bucket only for reports, not logs)
- [ ] **SQS queue** used for intended message type (standard vs FIFO matches ordering requirements)
- [ ] **Step Functions** used for coordination, not data processing (don't pass large payloads through states)
- [ ] **EventBridge rule** schedule matches intended frequency (cron correct for timezone)

### How to Document Intention

**When creating infrastructure, add intention comments**:

```hcl
# Terraform
resource "aws_lambda_function" "report_worker" {
  function_name = "report-worker-dev"

  # INTENTION: Async background worker for long-running report generation (60-120s)
  # Triggered by: SQS messages from Step Functions
  # NOT for: Synchronous API requests (use api-handler for that)
  timeout     = 180
  memory_size = 512

  tags = {
    Purpose  = "background-processing"
    Workload = "async-reports"
  }
}
```

**Benefits**:
- Future developers know WHY resource exists
- Prevents misuse (intention violation)
- Enables correct architecture decisions

---

### 4. Permission Boundary (Principal → Resource)

**What to verify**:
- IAM role has required permissions (s3:PutObject, dynamodb:Query, etc.)
- Resource policy allows principal (bucket policy, SQS policy)
- Cross-account access configured (if accessing resources in different account)
- Service-linked role exists (for AWS-managed integrations)

**Common failures**:
- Missing permission → `AccessDenied: User is not authorized to perform: s3:PutObject`
- Resource policy blocks → `403 Forbidden`

---

### 5. Deployment Boundary (Local → AWS)

**What to verify**:
- Environment parity (local dev matches AWS deployment)
- Configuration parity (Doppler dev_local vs Doppler dev)
- Dependency parity (local venv vs Lambda layer)
- Behavior parity (works locally → should work in AWS)

**Common failures**:
- Works locally, fails in Lambda → Missing env var in Terraform
- Different behavior → Local uses mock, Lambda uses real service

---

## Progressive Evidence Strengthening

Verify boundaries using increasingly strong evidence:

### Layer 1: Surface Signals (Code Inspection)
```python
# Read code
def store_report(pdf_s3_key: Optional[str] = None):
    ...

# Conclusion: "Code accepts pdf_s3_key parameter" ✅
# Confidence: LOW (code compiles, but does it work?)
```

### Layer 2: Configuration Inspection
```hcl
# Read Terraform
resource "aws_lambda_function" "worker" {
  environment {
    variables = {
      TZ = "Asia/Bangkok"
    }
  }
}

# Conclusion: "Terraform provides TZ env var" ✅
# Confidence: MEDIUM (config exists, but is it deployed?)
```

### Layer 3: Runtime Inspection
```bash
# Query deployed Lambda
aws lambda get-function-configuration \
  --function-name dr-daily-report-report-worker-dev \
  --query 'Environment.Variables.TZ'

# Returns: "Asia/Bangkok"
# Conclusion: "Lambda has TZ env var" ✅
# Confidence: HIGH (runtime confirmed)
```

### Layer 4: Ground Truth Verification
```bash
# Invoke Lambda and check logs
aws lambda invoke --function-name worker /tmp/response.json

# Check CloudWatch logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "TZ="

# Log shows: "Using timezone: Asia/Bangkok"
# Conclusion: "Code correctly uses TZ env var" ✅
# Confidence: HIGHEST (execution verified)
```

**Never stop at Layer 1** - Always verify through Layer 3 (runtime) or Layer 4 (ground truth).

---

## Real-World Example: PDF Schema Bug

### Without Boundary Analysis (What Happened)

```markdown
Step 1: Read code
✅ Code passes pdf_s3_key parameter
✅ Function signature accepts pdf_s3_key
Conclusion: "Code supports PDF tracking"

Step 2: Deploy code
❌ Parameters silently ignored
❌ PDFs not linked in Aurora

Step 3: User reports bug
⏰ 3 days later: "Can't find PDFs from Aurora"

Root cause: Aurora schema missing pdf_s3_key column
Time wasted: 3 deployment cycles, 3 days debugging
```

### With Boundary Analysis (What Should Happen)

```markdown
Step 1: Identify boundaries
WHERE: Lambda → Aurora
WHAT: Code writes pdf_s3_key to Aurora

Step 2: Validate data boundary
Code expects: INSERT INTO reports (..., pdf_s3_key) VALUES (...)
Aurora has: SHOW COLUMNS FROM reports
Result: ❌ pdf_s3_key column missing

Root cause: Schema mismatch
Time: 5 minutes pre-deployment verification

Step 3: Fix boundary (before deployment)
Create migration: ALTER TABLE reports ADD COLUMN pdf_s3_key VARCHAR(255)
Apply migration: mysql < 019_add_pdf_tracking.sql
Verify: SHOW COLUMNS FROM reports → pdf_s3_key ✅

Step 4: Deploy code
✅ Schema ready, code works correctly

Time saved: 3 deployment cycles + 3 days debugging
```

---

## Integration with CLAUDE.md Principles

This checklist implements:

- **Principle #1** (Defensive Programming): Validate initial conditions before execution
- **Principle #2** (Progressive Evidence Strengthening): Verify through all 4 layers
- **Principle #4** (Type System Integration): Research boundaries before integrating
- **Principle #15** (Infrastructure-Application Contract): Sync code and infrastructure
- **Principle #20** (Execution Boundary Discipline): Systematically identify boundaries and verify entity properties

---

## Quick Reference Card

**Before concluding "code is correct":**

1. ✅ WHERE does this run? → Identified execution environment (Lambda, EC2, local)
2. ✅ WHAT env needed? → Verified environment variables, filesystem, network
3. ✅ WHAT services called? → Verified Aurora schema, S3 permissions, SQS format
4. ✅ WHAT are entity properties? → Verified timeout/memory config, intended usage
5. ✅ WHAT contracts hold? → Verified code-infra, code-data, service-service boundaries

**If you can't check all 5 boxes, you're missing execution boundaries.**

---

## Related Resources

- **Abstraction**: `.claude/abstractions/failure_mode-2026-01-03-missing-execution-boundary-analysis.md`
- **CLAUDE.md Principle #20**: Execution Boundary Discipline
- **Skills**: `.claude/skills/research/`, `.claude/skills/code-review/`
- **Framework Evolution**: `.claude/evolution/2026-01-03-boundary-verification-framework.md`
