---
name: error-investigation
description: AWS error investigation with multi-layer verification, CloudWatch analysis, and Lambda logging patterns. Use when debugging AWS service failures, investigating production errors, or troubleshooting Lambda functions.
---

# Error Investigation Skill

**Tech Stack**: AWS CLI, CloudWatch Logs, Lambda, boto3, jq

**Source**: Extracted from CLAUDE.md error investigation principles and AWS diagnostic patterns.

---

## When to Use This Skill

Use the error-investigation skill when:
- ✓ AWS service returning errors
- ✓ Lambda function failing in production
- ✓ CloudWatch logs showing errors
- ✓ Service completed but operation failed
- ✓ Silent failures (no exception but wrong result)
- ✓ Investigating production incidents

**DO NOT use this skill for:**
- ✗ Local Python debugging (use debugger instead)
- ✗ Code refactoring (use refactor skill)
- ✗ Performance optimization (use different skill)

---

## Quick Investigation Decision Tree

```
What's failing?
├─ Lambda function?
│  ├─ Returns 200 but errors? → Check CloudWatch logs (Layer 3)
│  ├─ Timeout? → Check duration metrics + external dependencies
│  ├─ Permission denied? → Check IAM role policies
│  └─ Cold start slow? → Module-level initialization pattern
│
├─ AWS service operation?
│  ├─ DynamoDB write succeeded (200) but no data? → Check rowcount
│  ├─ S3 upload succeeded but file missing? → Check bucket policy
│  ├─ SQS message sent but not received? → Check DLQ
│  └─ Step Function succeeded but workflow incomplete? → Check state outputs
│
├─ External API call?
│  ├─ Timeout? → Check network path (security groups, VPC)
│  ├─ 403 Forbidden? → Check API key, rate limits
│  ├─ 500 Error? → Check API status page, retry logic
│  └─ Silent failure? → Inspect response payload
│
└─ Database query?
   ├─ INSERT affected 0 rows? → FK constraint, ENUM mismatch
   ├─ SELECT returns empty? → Check WHERE clause, data exists
   ├─ Connection timeout? → Security group, VPC routing
   └─ Query slow? → Missing index, full table scan
```

---

## Core Investigation Principles

### Principle 1: Execution Completion ≠ Operational Success

**From CLAUDE.md:**
> "Execution completion ≠ Operational success. Verify actual outcomes across multiple layers, not just the absence of exceptions."

**Why This Matters:**

```python
# ❌ WRONG: Assumes 200 = success
response = lambda_client.invoke(FunctionName='worker', Payload='{}')
assert response['StatusCode'] == 200  # ✗ Weak validation

# ✅ RIGHT: Multi-layer verification
response = lambda_client.invoke(FunctionName='worker', Payload='{}')

# Layer 1: Status code
assert response['StatusCode'] == 200

# Layer 2: Response payload
payload = json.loads(response['Payload'].read())
assert 'errorMessage' not in payload

# Layer 3: CloudWatch logs
logs = cloudwatch.filter_log_events(
    logGroupName='/aws/lambda/worker',
    filterPattern='ERROR'
)
assert len(logs['events']) == 0
```

### Principle 2: Multi-Layer Verification

**The Three Layers:**

| Layer | Signal Strength | What It Tells You | What It DOESN'T Tell You |
|-------|----------------|-------------------|--------------------------|
| **Status Code** | Weakest | Service responded | Whether it succeeded |
| **Response Payload** | Stronger | Function returned data | Whether logs show errors |
| **CloudWatch Logs** | Strongest | What actually happened | Future issues |

**Pattern:**

```bash
# Layer 1: Status code (weakest)
aws lambda invoke --function-name worker --payload '{}' /tmp/response.json
echo "Exit code: $?"  # 0 = AWS CLI succeeded

# Layer 2: Response payload (stronger)
if grep -q "errorMessage" /tmp/response.json; then
  echo "❌ Lambda returned error"
  exit 1
fi

# Layer 3: CloudWatch logs (strongest)
ERROR_COUNT=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --start-time $(($(date +%s) - 120))000 \
  --filter-pattern "ERROR" \
  --query 'length(events)' --output text)

if [ "$ERROR_COUNT" -gt 0 ]; then
  echo "❌ Found errors in CloudWatch logs"
  exit 1
fi

echo "✅ All 3 layers verified"
```

See [AWS-DIAGNOSTICS.md](AWS-DIAGNOSTICS.md) for AWS-specific diagnostic patterns.

### Principle 3: Log Level Determines Discoverability

**From CLAUDE.md:**
> "Log levels are not just severity indicators—they determine whether failures are discoverable by monitoring systems."

**Log Level Impact:**

| Log Level | Monitored? | Alerted? | Discoverable? |
|-----------|------------|----------|---------------|
| **ERROR** | ✅ Yes | ✅ Yes | ✅ Dashboards |
| **WARNING** | ✅ Yes | ❌ No | ⚠️  Manual review |
| **INFO** | ⚠️  Maybe | ❌ No | ❌ Active search |
| **DEBUG** | ❌ No | ❌ No | ❌ Hidden |

**Investigation Pattern:**

```bash
# Step 1: Check ERROR level first
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "ERROR"

# Step 2: If no ERRORs but operation failed → Check WARNING
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "WARNING"

# Step 3: Check both application AND service logs
# - Application logs: /aws/lambda/worker
# - Service logs: Lambda execution errors, timeouts
```

**Why This Matters:**

```python
# ❌ BAD: Error logged at WARNING (invisible to monitoring)
try:
    result = db.execute(query, params)
    if result == 0:
        logger.warning("INSERT failed")  # ⚠️  Not monitored!
except Exception as e:
    logger.warning(f"DB error: {e}")  # ⚠️  Not alerted!

# ✅ GOOD: Error logged at ERROR (visible to monitoring)
try:
    result = db.execute(query, params)
    if result == 0:
        logger.error("INSERT failed - 0 rows affected")  # ✅ Monitored
        raise ValueError("Insert operation failed")
except Exception as e:
    logger.error(f"DB error: {e}")  # ✅ Alerted
    raise
```

### Principle 4: Lambda Logging Configuration

**From CLAUDE.md:**
> "AWS Lambda pre-configures logging before your code runs. Never use `logging.basicConfig()` in Lambda handlers—it's a no-op."

**The Problem:**

```python
# ❌ This does NOTHING in Lambda
import logging

logging.basicConfig(level=logging.INFO)  # No-op!
logger = logging.getLogger(__name__)
logger.info("Invisible in CloudWatch")  # Filtered out
```

**Why It Fails:**
- Lambda runtime adds handlers to root logger BEFORE your code runs
- `basicConfig()` only works if root logger has NO handlers
- Result: INFO-level logs are invisible

**The Solution:**

```python
# ✅ Works in both Lambda and local dev
import logging

root_logger = logging.getLogger()

if root_logger.handlers:  # Lambda (already configured)
    root_logger.setLevel(logging.INFO)
else:  # Local dev (needs configuration)
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.info("Visible in CloudWatch")  # ✅ Works
```

See [LAMBDA-LOGGING.md](LAMBDA-LOGGING.md) for comprehensive Lambda logging patterns.

---

## Common Investigation Scenarios

### Scenario 1: Lambda Returns 200 But Has Errors

**Symptom:** Function completes, returns 200, but errors in logs.

**Investigation Steps:**

```bash
# 1. Invoke function
aws lambda invoke \
  --function-name worker \
  --payload '{"ticker": "NVDA19"}' \
  /tmp/response.json

# 2. Check response (Layer 2)
cat /tmp/response.json
# Output: {"result": {...}}  # Looks fine

# 3. Check CloudWatch logs (Layer 3)
aws logs tail /aws/lambda/worker --since 1m --filter-pattern "ERROR"

# Output:
# [ERROR] 2024-01-15 10:23:45 INSERT affected 0 rows for NVDA19
# [ERROR] 2024-01-15 10:23:46 FK constraint violation: symbol not found
```

**Root Cause:** Silent database failure (0 rowcount), logged at ERROR but caught exception.

**Fix:**

```python
# Before:
def store_report(symbol, report):
    try:
        self.db.execute(query, params)
        return True  # ❌ Always returns True
    except Exception as e:
        logger.error(f"DB error: {e}")
        return True  # ❌ Still returns True!

# After:
def store_report(symbol, report):
    rowcount = self.db.execute(query, params)
    if rowcount == 0:
        logger.error(f"INSERT affected 0 rows for {symbol}")
        return False  # ✅ Returns False on failure
    return True
```

### Scenario 2: INFO Logs Not Showing in CloudWatch

**Symptom:** `logger.info()` calls not appearing in CloudWatch.

**Investigation Steps:**

```bash
# 1. Check current log level
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --start-time $(($(date +%s) - 300))000 \
  --filter-pattern "INFO"

# No results (but INFO logs exist in code)

# 2. Check root logger configuration
# Add to Lambda handler:
import logging
print(f"Root logger level: {logging.getLogger().level}")
print(f"Root logger handlers: {logging.getLogger().handlers}")
```

**Root Cause:** Root logger set to WARNING, filters out INFO.

**Fix:**

```python
# handler.py (entry point)
import logging

# Configure logging at module level
root_logger = logging.getLogger()

if root_logger.handlers:  # Lambda environment
    root_logger.setLevel(logging.INFO)  # ✅ Set root logger level
else:  # Local development
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    logger.info("Handler invoked")  # Now visible
    # ...
```

See [LAMBDA-LOGGING.md#troubleshooting](LAMBDA-LOGGING.md#troubleshooting) for complete debugging guide.

### Scenario 3: DynamoDB PutItem Succeeds But No Data

**Symptom:** `put_item()` returns 200, but item not in table.

**Investigation Steps:**

```python
# 1. Check response
response = table.put_item(Item={'ticker': 'NVDA19', 'data': {...}})
print(f"HTTP Status: {response['ResponseMetadata']['HTTPStatusCode']}")
# Output: 200

# 2. Verify item exists
response = table.get_item(Key={'ticker': 'NVDA19'})
print(response.get('Item'))
# Output: None (no item!)

# 3. Check for conditional write
response = table.put_item(
    Item={'ticker': 'NVDA19', 'data': {...}},
    ConditionExpression='attribute_not_exists(ticker)'  # ← Condition failed?
)
```

**Root Cause:** Conditional expression failed silently.

**Fix:**

```python
# Before:
response = table.put_item(Item=item)  # ❌ No verification

# After:
try:
    response = table.put_item(Item=item)

    # Verify write
    verify = table.get_item(Key={'ticker': item['ticker']})
    if 'Item' not in verify:
        logger.error(f"Item not found after put_item: {item['ticker']}")
        raise ValueError("DynamoDB write verification failed")

except botocore.exceptions.ClientError as e:
    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        logger.warning(f"Conditional write failed: {item['ticker']}")
    else:
        logger.error(f"DynamoDB error: {e}")
        raise
```

---

## Investigation Workflow

### Step 1: Identify Error Layer (5 minutes)

```bash
# Check all three layers
aws lambda invoke --function-name worker --payload '{}' /tmp/response.json

# Layer 1: Exit code
echo "Exit code: $?"

# Layer 2: Response payload
cat /tmp/response.json | jq .

# Layer 3: CloudWatch logs
aws logs tail /aws/lambda/worker --since 5m --filter-pattern "ERROR"
```

**Questions:**
- Which layer shows the error?
- If Layer 1 OK but Layer 3 ERROR → Silent failure
- If all layers OK but wrong result → Logic error

### Step 2: Collect Error Context (10 minutes)

```bash
# Get full error details
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --start-time $(($(date +%s) - 3600))000 \
  --filter-pattern "ERROR" \
  --query 'events[*].[timestamp,message]' \
  --output table

# Get surrounding context (±5 lines)
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "ERROR" \
  | jq -r '.events[0].message' \
  | grep -C 5 "ERROR"
```

### Step 3: Check Recent Changes (5 minutes)

```bash
# When did errors start?
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "ERROR" \
  --query 'events[0].timestamp' \
  --output text

# What deployed around that time?
gh run list --limit 10

# What changed in code?
git log --since="2 hours ago" --oneline
```

### Step 4: Reproduce and Fix (variable)

See [AWS-DIAGNOSTICS.md](AWS-DIAGNOSTICS.md) for service-specific diagnostic patterns.

---

## Quick Reference

### Investigation Priority

1. **Check CloudWatch logs** (Layer 3 - strongest signal)
2. **Check response payload** (Layer 2 - structured errors)
3. **Check status code** (Layer 1 - weakest signal)
4. **Verify actual outcome** (database state, S3 files, etc.)

### Common Failure Modes

| Symptom | Likely Cause | Investigation |
|---------|--------------|---------------|
| **200 OK but errors in logs** | Silent failure | Check rowcount, verify writes |
| **INFO logs not showing** | Root logger level = WARNING | Set root logger to INFO |
| **Timeout** | Cold start, external API slow | Check duration metrics |
| **Permission denied** | IAM policy missing | Simulate permissions |
| **0 rows affected** | FK constraint, ENUM mismatch | Check constraints |

---

## File Organization

```
.claude/skills/error-investigation/
├── SKILL.md              # This file (entry point)
├── AWS-DIAGNOSTICS.md    # AWS-specific diagnostic patterns
└── LAMBDA-LOGGING.md     # Lambda logging configuration guide
```

---

## Next Steps

- **For AWS diagnostics**: See [AWS-DIAGNOSTICS.md](AWS-DIAGNOSTICS.md)
- **For Lambda logging**: See [LAMBDA-LOGGING.md](LAMBDA-LOGGING.md)
- **For general debugging**: See research skill

---

## References

- [AWS Lambda Troubleshooting](https://docs.aws.amazon.com/lambda/latest/dg/lambda-troubleshooting.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [AWS SDK Error Handling](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html)
