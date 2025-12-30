# Fund Data Sync Pipeline - Deployment Guide

**Purpose**: Event-driven ETL pipeline for syncing fund data from on-premises SQL Server to AWS Aurora MySQL
**Architecture**: S3 → SQS → Lambda → Aurora
**Implementation Date**: 2025-12-09
**Status**: ✅ Implementation Complete, Ready for Deployment

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Components Implemented](#components-implemented)
3. [Testing Strategy](#testing-strategy)
4. [Pre-Deployment Checklist](#pre-deployment-checklist)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment Validation](#post-deployment-validation)
7. [Operational Procedures](#operational-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring & Alerts](#monitoring--alerts)

---

## Architecture Overview

### Data Flow

```
On-Premises SQL Server
    ↓ (Daily CSV Export)
S3 Data Lake (raw/sql_server/fund_data/)
    ↓ (S3 ObjectCreated Event)
SQS Queue (fund-data-sync-dev)
    ↓ (Lambda Event Source Mapping)
Lambda Function (dr-daily-report-fund-data-sync-dev)
    ↓ (CSV Parse + Batch Upsert)
Aurora MySQL (fund_data table)
```

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Idempotency** | Composite unique key (d_trade, stock, ticker, col_code) with ON DUPLICATE KEY UPDATE |
| **Fault Isolation** | Dead Letter Queue (DLQ) after 3 retries |
| **Observability** | CloudWatch Logs, X-Ray tracing, CloudWatch alarms |
| **Security** | VPC isolation, least privilege IAM, SSE-SQS encryption |
| **Data Lineage** | s3_source_key tracks origin of every record |

### Timezone Configuration

**System timezone**: Asia/Bangkok (UTC+7)

**Components**:
- **On-premise export**: Bangkok time (04:00 AM daily)
- **S3 uploads**: Bangkok timestamps (04:11 AM pattern)
- **Lambda processing**: Bangkok time (TZ env var)
- **Aurora storage**: Bangkok time (parameter group)

**Migration date**: 2025-12-30

**Historical data**:
- Pre-2025-12-30: `synced_at` in UTC
- Post-2025-12-30: `synced_at` in Bangkok time
- Both are acceptable - no conversion needed

**Verification**:
```sql
SELECT @@global.time_zone, NOW(), UTC_TIMESTAMP();
-- Expected: Asia/Bangkok, <Bangkok time>, <UTC 7 hours behind>
```

---

## Components Implemented

### Phase 1: Foundation (Database & ETL Components)

#### 1. Database Schema
**File**: `db/migrations/003_fund_data_schema.sql`
**Purpose**: Aurora MySQL table with idempotency constraints

**Key Features**:
- Composite unique key: `(d_trade, stock, ticker, col_code)`
- Flexible value storage: `value_numeric` (DECIMAL) + `value_text` (TEXT)
- Data lineage: `s3_source_key` tracks S3 origin
- Indexes for query performance

**Deployment**:
```bash
# Run migration
mysql -h ${AURORA_HOST} -u ${AURORA_USER} -p${AURORA_PASSWORD} ${AURORA_DATABASE} < db/migrations/003_fund_data_schema.sql
```

#### 2. CSV Parser
**File**: `src/data/etl/fund_data_parser.py` (382 lines)
**Purpose**: Parse CSV bytes with encoding detection and type conversion

**Key Features**:
- Automatic encoding detection (Windows-1252, UTF-8) using chardet
- Type conversion at system boundary (CSV strings → Python types)
- Date format support: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, YYYYMMDD
- Decimal precision for financial data (avoids float precision loss)
- Schema validation (required fields: d_trade, stock, ticker, col_code)

#### 3. Aurora Repository
**File**: `src/data/aurora/fund_data_repository.py` (410 lines)
**Purpose**: Data access layer with batch upsert

**Key Features**:
- Batch upsert with `ON DUPLICATE KEY UPDATE`
- Batch size: 1000 records (optimal throughput)
- Defensive rowcount check (detects silent failures)
- Query methods: `get_by_ticker()`, `get_by_s3_source()`

#### 4. ETL Service Orchestration
**File**: `src/data/etl/fund_data_sync.py` (280 lines)
**Purpose**: Orchestrate complete ETL pipeline

**Key Features**:
- Module-level singleton for Lambda cold start optimization
- Process SQS messages containing S3 events
- Download CSV from S3 → Parse → Batch upsert to Aurora
- Comprehensive error handling with structured responses

#### 5. Lambda Handler
**File**: `src/lambda_handlers/fund_data_sync_handler.py` (174 lines)
**Purpose**: SQS-triggered Lambda entry point

**Key Features**:
- Process SQS message batches (up to 10 messages per invocation)
- Partial batch response (batchItemFailures for SQS)
- Continue processing remaining messages even if one fails
- Detailed logging for observability

### Phase 2: Testing (TDD Implementation)

#### 1. Parser Unit Tests
**File**: `tests/data/test_fund_data_parser.py` (406 lines)
**Coverage**: 15 tests demonstrating 6 defensive programming principles

**Run Tests**:
```bash
pytest tests/data/test_fund_data_parser.py -v
```

#### 2. Repository Unit Tests
**File**: `tests/data/test_fund_data_repository.py` (547 lines)
**Coverage**: 18 tests including idempotency, MySQL-specific behavior

**Run Tests**:
```bash
ENV=dev doppler run -- pytest tests/data/test_fund_data_repository.py -v --tier=2
```

#### 3. Integration Tests
**File**: `tests/data/test_fund_data_integration.py` (501 lines)
**Coverage**: 14 tests for end-to-end pipeline validation

**Run Tests**:
```bash
ENV=dev doppler run -- pytest tests/data/test_fund_data_integration.py -v --tier=2
```

#### 4. Lambda Handler Tests
**File**: `tests/lambda_handlers/test_fund_data_sync_handler.py` (437 lines)
**Coverage**: 17 tests for Lambda behavior, SQS integration, error handling

**Run Tests**:
```bash
pytest tests/lambda_handlers/test_fund_data_sync_handler.py -v
```

### Phase 3: Infrastructure (Terraform + OPA + Terratest)

#### 1. SQS Queue Module
**Files**:
- `terraform/modules/sqs-etl-queue/main.tf` (256 lines)
- `terraform/modules/sqs-etl-queue/variables.tf` (267 lines)
- `terraform/modules/sqs-etl-queue/outputs.tf` (80 lines)

**Features**:
- Main queue + Dead Letter Queue
- CloudWatch alarms: DLQ messages, queue depth, message age
- Long polling (reduce API calls by 95%)
- SSE-SQS encryption

#### 2. OPA Security Policies
**File**: `terraform/policies/sqs/fund_data_queue.rego` (242 lines)

**Policies Enforced**:
- DENY: Queue without Dead Letter Queue
- DENY: Visibility timeout < 60s
- DENY: Encryption not enabled
- DENY: Missing environment suffix (-dev, -staging, -prod)
- WARN: maxReceiveCount not in range 3-5
- WARN: Message retention < 1 day

**Run Validation**:
```bash
cd terraform
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test tfplan.json --policy policies/
```

#### 3. Terratest Integration Tests
**File**: `terraform/tests/sqs_etl_queue_test.go` (435 lines)

**Tests**:
- Queue creation
- Redrive policy configuration
- Encryption enabled
- Message flow (send → receive → delete)
- DLQ behavior (poison message moves to DLQ)

**Run Tests**:
```bash
cd terraform/tests
go test -v -timeout 30m
```

#### 4. Lambda Infrastructure
**File**: `terraform/fund_data_sync.tf` (348 lines)

**Resources Created**:
- ECR Repository: `dr-daily-report-fund-data-sync`
- Lambda Function: `dr-daily-report-fund-data-sync-dev`
- Lambda Event Source Mapping (SQS → Lambda)
- IAM Role + Policies (S3 read, SQS receive/delete, Aurora write)
- Security Group (Lambda → Aurora, Lambda → S3)
- CloudWatch Log Group (7-day retention)

#### 5. S3 Event Notification
**File**: `terraform/s3_fund_data_events.tf` (69 lines)

**Configuration**:
- Trigger: S3 ObjectCreated events
- Filter: `raw/sql_server/fund_data/*.csv`
- Destination: SQS queue

#### 6. Dockerfile
**File**: `Dockerfile.fund-data-sync` (33 lines)

**Base Image**: `public.ecr.aws/lambda/python:3.11`
**Handler**: `src.lambda_handlers.fund_data_sync_handler.lambda_handler`

---

## Testing Strategy

### TDD Methodology Applied

**RED Phase** (Tests First):
- Write failing tests that define requirements
- Tests specify expected behavior before implementation exists

**GREEN Phase** (Implementation):
- Write minimal code to make tests pass
- Focus on correctness, not optimization

**REFACTOR Phase** (Cleanup):
- Improve code quality without changing behavior
- Verify tests still pass

### Test Tiers

| Tier | Command | Tests |
|------|---------|-------|
| Tier 0 | `pytest --tier=0 tests/data/test_fund_data_parser.py` | Unit tests only (fast) |
| Tier 1 | `pytest tests/data/test_fund_data_parser.py` | Unit + mocked tests |
| Tier 2 | `ENV=dev doppler run -- pytest tests/data/ --tier=2` | + Integration (requires Aurora) |

### Defensive Programming Principles Tested

1. **Test Outcomes, Not Execution**: Verify data types, not just function calls
2. **Explicit Failure Mocking**: Mock failure states (rowcount=0, exceptions)
3. **Round-Trip Validation**: Store → Retrieve → Verify unchanged
4. **Schema Contract Testing**: Validate types at system boundaries
5. **Silent Failure Detection**: Check rowcount, not just absence of exceptions
6. **Test Sabotage Verification**: Verify tests detect failures

---

## Pre-Deployment Checklist

### Environment Variables

Ensure these are set in Doppler:

| Variable | Purpose | Example |
|----------|---------|---------|
| `AURORA_HOST` | Aurora cluster endpoint | `dr-daily-report-dev.cluster-xxx.ap-southeast-1.rds.amazonaws.com` |
| `AURORA_USER` | Database user | `admin` |
| `AURORA_PASSWORD` | Database password | (secret) |
| `AURORA_DATABASE` | Database name | `ticker_data` |
| `DATA_LAKE_BUCKET` | S3 bucket name | `dr-daily-report-data-lake-dev` |

### Required AWS Resources

- ✅ S3 Data Lake bucket (module.s3_data_lake)
- ✅ Aurora MySQL cluster (with fund_data table)
- ✅ VPC with private subnets (for Lambda)
- ✅ Aurora security group (to allow Lambda ingress)

### Testing Validation

Run all tests before deployment:

```bash
# Phase 1: Unit Tests
pytest tests/data/test_fund_data_parser.py -v
pytest tests/data/test_fund_data_repository.py -v --tier=0

# Phase 2: Integration Tests (requires Aurora)
ENV=dev doppler run -- pytest tests/data/ --tier=2 -v

# Phase 3: Lambda Handler Tests
pytest tests/lambda_handlers/test_fund_data_sync_handler.py -v

# Phase 4: Infrastructure Tests
cd terraform/tests
go test -v
```

**Expected**: All tests pass (no failures)

---

## Deployment Steps

### Step 1: Database Migration

```bash
# Connect to Aurora
ENV=dev doppler run -- mysql -h ${AURORA_HOST} -u ${AURORA_USER} -p${AURORA_PASSWORD} ${AURORA_DATABASE}

# Run migration
source db/migrations/003_fund_data_schema.sql

# Verify table created
DESCRIBE fund_data;
SHOW INDEXES FROM fund_data;
```

**Verification**:
```sql
SELECT COUNT(*) FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ticker_data' AND TABLE_NAME = 'fund_data';
-- Expected: 1
```

### Step 2: Infrastructure Deployment (Terraform)

```bash
cd terraform

# Step 2a: OPA Policy Validation
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test tfplan.json --policy policies/

# Expected: 0 DENY violations

# Step 2b: Terraform Apply
terraform apply

# Review plan, type 'yes' to confirm

# Step 2c: Verify Outputs
terraform output fund_data_sync_lambda_arn
terraform output fund_data_sync_queue_url
terraform output fund_data_sync_ecr_repository_url
```

**Resources Created**:
- SQS Queue: `fund-data-sync-dev`
- SQS DLQ: `fund-data-sync-dev-dlq`
- Lambda Function: `dr-daily-report-fund-data-sync-dev`
- ECR Repository: `dr-daily-report-fund-data-sync`
- CloudWatch Alarms: 3 alarms (DLQ messages, queue depth, message age)

### Step 3: Build and Push Docker Image

```bash
# Get ECR repository URL from Terraform output
ECR_REPO=$(terraform output -raw fund_data_sync_ecr_repository_url)
echo "ECR Repository: $ECR_REPO"

# AWS ECR Login
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build Docker image
docker build -f Dockerfile.fund-data-sync -t fund-data-sync:latest .

# Tag image
docker tag fund-data-sync:latest $ECR_REPO:latest

# Push image
docker push $ECR_REPO:latest

# Update Lambda function to use new image
aws lambda update-function-code \
  --function-name dr-daily-report-fund-data-sync-dev \
  --image-uri $ECR_REPO:latest

# Wait for update to complete
aws lambda wait function-updated \
  --function-name dr-daily-report-fund-data-sync-dev
```

**Verification**:
```bash
aws lambda get-function \
  --function-name dr-daily-report-fund-data-sync-dev \
  --query 'Configuration.[State,LastUpdateStatus]'

# Expected: ["Active", "Successful"]
```

### Step 4: Configure S3 Event Notification

Already handled by Terraform (`terraform/s3_fund_data_events.tf`).

**Verify Configuration**:
```bash
aws s3api get-bucket-notification-configuration \
  --bucket dr-daily-report-data-lake-dev | \
  jq '.QueueConfigurations[] | select(.Id == "fund-data-csv-upload")'
```

**Expected Output**:
```json
{
  "Id": "fund-data-csv-upload",
  "QueueArn": "arn:aws:sqs:ap-southeast-1:...:fund-data-sync-dev",
  "Events": ["s3:ObjectCreated:*"],
  "Filter": {
    "Key": {
      "FilterRules": [
        {"Name": "prefix", "Value": "raw/sql_server/fund_data/"},
        {"Name": "suffix", "Value": ".csv"}
      ]
    }
  }
}
```

---

## Post-Deployment Validation

### 1. Upload Test CSV

```bash
# Create test CSV
cat > /tmp/test_fund_data.csv <<'CSV'
d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1234567
2025-12-09,MWG,MWG19,CLOSE,28.30
CSV

# Upload to S3
aws s3 cp /tmp/test_fund_data.csv \
  s3://dr-daily-report-data-lake-dev/raw/sql_server/fund_data/2025-12-09/test.csv
```

### 2. Monitor SQS Queue

```bash
# Check message count
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw fund_data_sync_queue_url) \
  --attribute-names ApproximateNumberOfMessages \
  | jq -r '.Attributes.ApproximateNumberOfMessages'

# Expected: 0 (message processed quickly)
```

### 3. Check Lambda Logs

```bash
# View recent logs
aws logs tail /aws/lambda/dr-daily-report-fund-data-sync-dev \
  --since 5m --follow
```

**Expected Log Messages**:
```
START RequestId: abc123...
[INFO] Starting Fund Data Sync Lambda handler
[INFO] Processing 1 SQS messages
[INFO] Processing message abc-123-def
[INFO] Downloaded 150 bytes from S3
[INFO] Parsed 3 records from CSV
[INFO] Upserted 3 records, affected 3 rows
[INFO] Successfully processed message abc-123-def: 3 records
[INFO] Batch processing complete: 1 succeeded, 0 failed
END RequestId: abc123...
```

### 4. Verify Data in Aurora

```bash
# Connect to Aurora
ENV=dev doppler run -- mysql -h ${AURORA_HOST} -u ${AURORA_USER} -p${AURORA_PASSWORD} ${AURORA_DATABASE}

# Query inserted data
SELECT * FROM fund_data
WHERE s3_source_key = 'raw/sql_server/fund_data/2025-12-09/test.csv';
```

**Expected**: 3 rows returned (DBS19 CLOSE, DBS19 VOLUME, MWG19 CLOSE)

### 5. Test Idempotency

```bash
# Re-upload same CSV (simulate duplicate S3 event)
aws s3 cp /tmp/test_fund_data.csv \
  s3://dr-daily-report-data-lake-dev/raw/sql_server/fund_data/2025-12-09/test2.csv

# Wait for processing
sleep 10

# Verify only 3 rows in database (no duplicates)
SELECT COUNT(*) FROM fund_data;
# Expected: 3 (not 6)
```

---

## Operational Procedures

### Manual Test (End-to-End)

```bash
# 1. Upload CSV
aws s3 cp /path/to/fund_data.csv \
  s3://dr-daily-report-data-lake-dev/raw/sql_server/fund_data/$(date +%Y-%m-%d)/export.csv

# 2. Monitor processing
aws logs tail /aws/lambda/dr-daily-report-fund-data-sync-dev --follow

# 3. Verify in database
ENV=dev doppler run -- mysql -h ${AURORA_HOST} -u ${AURORA_USER} -p${AURORA_DATABASE} \
  -e "SELECT COUNT(*) FROM fund_data WHERE DATE(synced_at) = CURDATE();"
```

### Check Dead Letter Queue

```bash
# Check DLQ message count
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw fund_data_sync_dlq_url) \
  --attribute-names ApproximateNumberOfMessages
```

**If DLQ has messages** → Processing failures detected. Investigate.

### Replay DLQ Messages

```bash
# Receive message from DLQ
aws sqs receive-message \
  --queue-url $(terraform output -raw fund_data_sync_dlq_url) \
  --max-number-of-messages 1

# Copy message body, fix issue, re-send to main queue
aws sqs send-message \
  --queue-url $(terraform output -raw fund_data_sync_queue_url) \
  --message-body '<COPIED_BODY>'
```

### Query by S3 Source

```sql
-- Find all records from specific S3 file
SELECT * FROM fund_data
WHERE s3_source_key = 'raw/sql_server/fund_data/2025-12-09/export.csv';

-- Count records by S3 source
SELECT s3_source_key, COUNT(*)
FROM fund_data
GROUP BY s3_source_key
ORDER BY synced_at DESC;
```

---

## Troubleshooting

### Issue 1: CSV Encoding Errors

**Symptom**: `UnicodeDecodeError` in Lambda logs

**Cause**: CSV file not in expected encoding (Windows-1252 or UTF-8)

**Solution**:
1. Check file encoding:
   ```bash
   file -b --mime-encoding /path/to/file.csv
   ```
2. If different encoding, convert:
   ```bash
   iconv -f WINDOWS-1252 -t UTF-8 /path/to/input.csv > /path/to/output.csv
   ```

### Issue 2: Lambda VPC Timeout

**Symptom**: Lambda timeout after 120s, no database connection

**Cause**: Lambda cannot reach Aurora (security group issue)

**Solution**:
1. Verify Lambda security group allows egress to Aurora:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids <LAMBDA_SG_ID> \
     --query 'SecurityGroups[0].IpPermissionsEgress'
   ```
   **Expected**: Egress rule to Aurora security group on port 3306

2. Verify Aurora security group allows ingress from Lambda:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids <AURORA_SG_ID> \
     --query 'SecurityGroups[0].IpPermissions'
   ```
   **Expected**: Ingress rule from Lambda security group on port 3306

### Issue 3: Duplicate Key Constraint Violations

**Symptom**: `IntegrityError: (1062, "Duplicate entry '...' for key 'uk_fund_data_composite'")`

**Cause**: Race condition (multiple Lambdas processing same S3 file)

**Solution**:
- This is expected behavior (idempotency working)
- ON DUPLICATE KEY UPDATE handles this gracefully
- Check rowcount in logs to verify update occurred

### Issue 4: SQS Messages Stuck in Queue

**Symptom**: `ApproximateAgeOfOldestMessage` alarm firing

**Cause**: Lambda not processing messages (dead code, permission issue)

**Debug**:
1. Check Lambda event source mapping:
   ```bash
   aws lambda list-event-source-mappings \
     --function-name dr-daily-report-fund-data-sync-dev
   ```
   **State** should be `Enabled`

2. Check Lambda CloudWatch Logs for errors

3. Manually invoke Lambda with test event:
   ```bash
   aws lambda invoke \
     --function-name dr-daily-report-fund-data-sync-dev \
     --payload file://test_event.json \
     /tmp/response.json
   ```

---

## Monitoring & Alerts

### CloudWatch Alarms

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| **DLQ Messages** | ApproximateNumberOfMessagesVisible | > 1 | Investigate processing failures |
| **Queue Depth** | ApproximateNumberOfMessagesVisible | > 100 | Scale Lambda concurrency or fix processing |
| **Message Age** | ApproximateAgeOfOldestMessage | > 3600s (1 hour) | Check Lambda is processing |

**View Alarms**:
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "fund-data-sync-dev"
```

### CloudWatch Metrics

**Lambda**:
- `Invocations` - Number of Lambda invocations
- `Errors` - Number of errors
- `Duration` - Execution time
- `ConcurrentExecutions` - Number of concurrent executions

**SQS**:
- `NumberOfMessagesSent` - Messages added to queue
- `NumberOfMessagesReceived` - Messages read from queue
- `NumberOfMessagesDeleted` - Messages successfully processed
- `ApproximateAgeOfOldestMessage` - Queue processing lag

**Query Metrics**:
```bash
# Lambda error rate (last 1 hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=dr-daily-report-fund-data-sync-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# SQS message age (current)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateAgeOfOldestMessage \
  --dimensions Name=QueueName,Value=fund-data-sync-dev \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum
```

### X-Ray Tracing

Lambda has X-Ray tracing enabled. View traces in AWS Console:

```
AWS Console → X-Ray → Traces
Filter: service("dr-daily-report-fund-data-sync-dev")
```

**Trace Segments**:
- S3 GetObject (download CSV)
- SQS ReceiveMessage (read from queue)
- Aurora MySQL (batch upsert)

---

## Summary

### Implementation Complete ✅

**Phase 1 - Foundation**: Database schema, CSV parser, Aurora repository, ETL service, Lambda handler
**Phase 2 - Testing**: 64 tests (unit + integration) demonstrating TDD methodology
**Phase 3 - Infrastructure**: Terraform + OPA policies + Terratest for infrastructure validation
**Phase 4 - Deployment**: Dockerfile, deployment scripts, comprehensive documentation

### Files Created (20 total)

| Category | Files | Lines |
|----------|-------|-------|
| Application Code | 5 files | 1,644 lines |
| Tests (Python) | 4 files | 1,891 lines |
| Infrastructure (Terraform) | 5 files | 1,226 lines |
| Infrastructure (OPA + Terratest) | 2 files | 677 lines |
| Documentation + Docker | 3 files | 600+ lines |
| **Total** | **20 files** | **6,038+ lines** |

### Next Steps

1. **Deploy to Dev Environment**:
   - Run database migration
   - Deploy Terraform infrastructure
   - Build and push Docker image

2. **End-to-End Testing**:
   - Upload test CSV to S3
   - Monitor SQS queue processing
   - Verify data in Aurora

3. **Monitor Production**:
   - Set up CloudWatch dashboard
   - Configure SNS alerts for CloudWatch alarms
   - Review Lambda logs daily

4. **Production Deployment**:
   - Repeat deployment steps for staging environment
   - Run load testing (multiple CSV uploads)
   - Deploy to production after validation

---

**Last Updated**: 2025-12-09
**Implementation Status**: ✅ Complete
**Deployment Status**: ⏳ Ready for Deployment
