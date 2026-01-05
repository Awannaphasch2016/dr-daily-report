# Infrastructure Debugging Guide

**Purpose**: Pattern catalog for debugging infrastructure-related failures in distributed AWS systems.

**When to use**: Lambda timeouts, network failures, VPC issues, deterministic failure patterns.

---

## Pattern Catalog

### Pattern 1: NAT Gateway Connection Saturation

**Symptom:**
- Deterministic failure pattern: First N operations succeed, last M timeout
- Long execution times (10+ minutes)
- Connection timeout errors in logs
- Multiple concurrent Lambda invocations

**Example Timeline:**
```
23:35:22-23 - All 10 Lambdas start (within 1 second)
23:35:30-31 - All 10 operations complete processing (within 1 second)
23:35:32-33 - First 5 network operations succeed (2-3 seconds)
23:45:39-57 - Last 5 network operations fail (~10 minutes timeout)
```

**Evidence:**
```bash
# Check for connection timeout errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "ConnectTimeoutError" \
  --query 'events[*].message'

# Analyze timing pattern
aws logs tail /aws/lambda/worker --since 30m | \
  grep -E "START RequestId|✅ completed|❌ failed" | \
  awk '{print $1, $2, $NF}' | sort
```

**Root Cause:**
- NAT Gateway has limited concurrent connection establishment rate
- When N concurrent operations attempt network calls simultaneously:
  - First batch establishes connections → SUCCESS
  - Remaining operations queue and eventually timeout → FAILURE
- Pattern is deterministic (not random) because connection slots are allocated first-come-first-served

**Solution:**
Add VPC Gateway Endpoint to bypass NAT Gateway for AWS services (S3, DynamoDB):

```hcl
# terraform/s3_vpc_endpoint.tf
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = data.aws_route_tables.vpc_route_tables.ids

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:*"
      Resource  = "*"
    }]
  })
}
```

**Verification:**
```bash
# 1. Verify endpoint exists and is available
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<vpc-id>" \
            "Name=service-name,Values=com.amazonaws.<region>.s3" \
  --query 'VpcEndpoints[0].State'
# Expected: "available"

# 2. Verify route table attachment
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<vpc-id>" \
  --query 'VpcEndpoints[0].RouteTableIds'
# Expected: List of route table IDs including Lambda subnet route tables

# 3. Test with concurrent operations
# Expected: 100% success rate, 2-3s per operation (vs 50% failure, 10min timeout)
```

**Benefits:**
- **FREE**: Gateway endpoints have no hourly charge
- **Faster**: Direct AWS network path (no NAT hop)
- **Reliable**: No connection establishment limits
- **Secure**: Traffic never leaves AWS network

**Real-world example:** [Bug Hunt: PDF S3 Upload Timeout](../../.claude/bug-hunts/2026-01-05-pdf-s3-upload-timeout.md)

---

### Pattern 2: VPC Endpoint Missing or Misconfigured

**Symptom:**
- All network operations to AWS service fail (100% failure rate)
- Connection timeout or "host unreachable" errors
- Works in some environments but not others

**Evidence:**
```bash
# Check if VPC endpoint exists
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<vpc-id>" \
            "Name=service-name,Values=com.amazonaws.<region>.<service>"

# If empty → No endpoint exists
# If exists → Check state and route table attachment
```

**Root Cause:**
- Lambda in VPC without internet access (no NAT Gateway, no VPC endpoints)
- VPC endpoint exists but not attached to correct route tables
- VPC endpoint policy denies required actions

**Solution:**
```bash
# Option 1: Add VPC endpoint (if missing)
# See Pattern 1 for Terraform configuration

# Option 2: Verify route table attachment
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id <endpoint-id> \
  --add-route-table-ids <route-table-id>

# Option 3: Update endpoint policy (if too restrictive)
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id <endpoint-id> \
  --policy-document file://endpoint-policy.json
```

---

### Pattern 3: Execution Time ≠ Hang Location

**Symptom:**
- Lambda execution time is very long (10+ minutes)
- Logs don't show where code is "hanging"
- Adding detailed logging doesn't reveal hang point

**Critical Insight:**
**Execution time shows WHAT system waits for, not WHERE code hangs.**

**Example:**
```
Lambda execution time: 600s
Logs show:
  [23:35:30] 📄 Generating PDF...
  [23:45:57] ❌ ValueError: S3 upload failed
```

**Wrong conclusion:** "Code hangs during PDF generation for 10 minutes"

**Correct conclusion:** "Code completes PDF generation quickly, then waits 10 minutes for S3 connection timeout"

**How to identify actual hang point:**

1. **Check stack traces** (Layer 3 evidence):
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "Traceback" \
  --query 'events[*].message'
```

Stack trace shows:
```
File "formatters/pdf_storage.py", line 84, in upload_to_s3
  response = s3_client.put_object(...)
File "botocore/client.py", line 391, in _make_request
  raise ConnectTimeoutError(endpoint_url=request.url)
```

**Conclusion:** Code hangs at S3 connection establishment, not PDF generation.

2. **Use boundary logging** (survives Lambda failures):
```python
# WRONG: Logging at depth (lost when Lambda fails)
def generate_pdf():
    logger.info("Building PDF...")  # Lost if S3 upload fails
    doc.build(story)
    logger.info("PDF built")  # Lost if S3 upload fails

    upload_to_s3(pdf_bytes)  # Fails here, logs above never flush

# RIGHT: Logging at boundaries (survives failures)
def handler():
    logger.info("Starting PDF generation")  # Survives
    pdf_bytes = generate_pdf()
    logger.info("✅ PDF generation completed")  # Survives

    logger.info("Starting S3 upload")  # Survives
    upload_to_s3(pdf_bytes)  # Fails here
    # Error logged in exception handler → Survives
```

3. **Analyze duration distribution** (pattern recognition):
```bash
# Get all durations
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "Duration:" \
  | grep -o "Duration: [0-9]*" \
  | sort -n

# Output:
# Duration: 2340ms   ← First request (success)
# Duration: 2456ms   ← Second request (success)
# Duration: 616000ms ← Third request (timeout)
# Duration: 626000ms ← Fourth request (timeout)
```

**Pattern:** Bimodal distribution (2-3s OR 600s+) → Network timeout, not gradual slowdown

---

## Timeline Analysis

**Purpose:** Identify infrastructure bottlenecks vs performance issues

**Pattern: Deterministic Failure**
```
Request 1: Started 10:00:00 → Completed 10:00:02 (2s)
Request 2: Started 10:00:00 → Completed 10:00:02 (2s)
Request 3: Started 10:00:00 → Completed 10:00:03 (3s)
Request 4: Started 10:00:00 → Completed 10:00:03 (3s)
Request 5: Started 10:00:00 → Completed 10:00:03 (3s)
Request 6: Started 10:00:00 → Failed 10:10:39 (639s)
Request 7: Started 10:00:00 → Failed 10:10:40 (640s)
Request 8: Started 10:00:00 → Failed 10:10:49 (649s)
Request 9: Started 10:00:00 → Failed 10:10:57 (657s)
Request 10: Started 10:00:00 → Failed 10:10:57 (657s)
```

**Conclusion:** Infrastructure bottleneck (first N succeed, last M fail)

**Pattern: Random Failure**
```
Request 1: Started 10:00:00 → Completed 10:00:02 (2s)
Request 2: Started 10:00:00 → Failed 10:00:15 (15s)
Request 3: Started 10:00:00 → Completed 10:00:03 (3s)
Request 4: Started 10:00:00 → Failed 10:00:12 (12s)
Request 5: Started 10:00:00 → Completed 10:00:02 (2s)
```

**Conclusion:** Performance issue (scattered failures, varying durations)

**Timeline Analysis Script:**
```bash
#!/bin/bash
# Analyze Lambda execution timeline

LOG_GROUP="/aws/lambda/worker"
SINCE="30m"

echo "=== Timeline Analysis ==="
echo ""

# Get all Lambda invocations with outcomes
aws logs tail $LOG_GROUP --since $SINCE 2>&1 | \
  grep -E "START RequestId:|✅|❌|Duration:" | \
  awk '
    /START RequestId:/ {
      time=$1;
      reqid=$NF;
      start[reqid]=time;
    }
    /✅/ {
      time=$1;
      for(r in start) if($0 ~ r) { success[r]=time; }
    }
    /❌/ {
      time=$1;
      for(r in start) if($0 ~ r) { failed[r]=time; }
    }
    /Duration:/ {
      duration=$NF;
      for(r in start) if($0 ~ r) { dur[r]=duration; }
    }
    END {
      print "Request | Start | End | Duration | Status"
      print "--------|-------|-----|----------|-------"
      n=0;
      for(r in start) {
        n++;
        status = (r in success) ? "✅ SUCCESS" : "❌ FAILED";
        printf "%7d | %s | %s | %8s | %s\n",
          n, start[r], (r in success ? success[r] : failed[r]), dur[r], status;
      }
    }
  '
```

---

## Stack Trace Interpretation

**Purpose:** Find actual failure point from CloudWatch logs

**Pattern: Connection Timeout**
```python
Traceback (most recent call last):
  File "/var/task/src/pdf_worker_handler.py", line 112, in lambda_handler
    result = _generate_and_upload_pdf(ticker, report_date)
  File "/var/task/src/pdf_worker_handler.py", line 156, in _generate_and_upload_pdf
    pdf_s3_key = pdf_storage.upload_to_s3(pdf_bytes, ticker, report_date)
  File "/var/task/src/formatters/pdf_storage.py", line 84, in upload_to_s3
    response = s3_client.put_object(Bucket=bucket, Key=s3_key, Body=pdf_bytes)
  File "/var/runtime/botocore/client.py", line 391, in _make_request
    raise ConnectTimeoutError(endpoint_url=request.url)
botocore.exceptions.ConnectTimeoutError: Connect timeout on endpoint URL:
"https://bucket.s3.region.amazonaws.com/reports/TICKER/2026-01-05.pdf"
```

**Read stack trace bottom-up:**
1. Line 391 in botocore: Connection establishment failed
2. Line 84 in pdf_storage: S3 put_object() call
3. Line 156 in pdf_worker_handler: upload_to_s3() call
4. Line 112 in lambda_handler: Entry point

**Conclusion:** Failure occurs during S3 connection establishment, NOT during PDF generation (which completed successfully before upload).

**Extraction Script:**
```bash
# Get most recent stack trace
aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --filter-pattern "Traceback" \
  --query 'events[0].message' \
  --output text \
  | python -c "
import sys
stack = sys.stdin.read()

# Extract exception type
if 'ConnectTimeoutError' in stack:
    print('❌ Connection Timeout → Network/VPC issue')
elif 'PermissionError' in stack:
    print('❌ Permission Denied → IAM policy issue')
elif 'KeyError' in stack:
    print('❌ Missing Key → Configuration issue')
else:
    print('⚠️  Other exception → Check stack trace')

# Extract failure point (last line before exception)
lines = stack.split('\n')
for i, line in enumerate(lines):
    if 'File' in line and i < len(lines) - 1:
        print(f'  {line.strip()}')
        print(f'    {lines[i+1].strip()}')
"
```

---

## Verification Checklist

### VPC Endpoint Verification

```bash
# 1. Check endpoint exists
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<vpc-id>" \
            "Name=service-name,Values=com.amazonaws.<region>.s3" \
  --query 'VpcEndpoints[0].{ID:VpcEndpointId, State:State, Service:ServiceName}'

# Expected output:
# {
#   "ID": "vpce-xxx",
#   "State": "available",
#   "Service": "com.amazonaws.region.s3"
# }

# 2. Verify route table attachment
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids <endpoint-id> \
  --query 'VpcEndpoints[0].RouteTableIds'

# Expected: List includes Lambda subnet route tables

# 3. Check endpoint policy
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids <endpoint-id> \
  --query 'VpcEndpoints[0].PolicyDocument' \
  | jq .

# Expected: Policy allows required S3 actions

# 4. Test network path from Lambda
aws lambda invoke \
  --function-name worker \
  --payload '{"test": "s3_connection"}' \
  /tmp/response.json

aws logs tail /aws/lambda/worker --since 1m --filter-pattern "✅ S3"
# Expected: "✅ S3 upload completed in 2-3s"
```

### NAT Gateway Verification

```bash
# 1. Check NAT Gateway exists
aws ec2 describe-nat-gateways \
  --filters "Name=vpc-id,Values=<vpc-id>" \
  --query 'NatGateways[*].{ID:NatGatewayId, State:State, Subnet:SubnetId}'

# 2. Check route table routing
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=<vpc-id>" \
  --query 'RouteTables[*].Routes[?GatewayId!=`local`]'

# Look for: 0.0.0.0/0 → nat-xxx (NAT Gateway)
# vs:       pl-xxx → vpce-xxx (VPC Endpoint prefix list)

# 3. Check CloudWatch metrics for NAT Gateway
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name ActiveConnectionCount \
  --dimensions Name=NatGatewayId,Value=<nat-id> \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Maximum

# High connection count = potential saturation
```

---

## Real-World Examples

### Case Study: PDF S3 Upload Timeout

**Context:** Nightly PDF generation workflow processes 46 tickers concurrently using Step Functions → SQS → Lambda.

**Symptom:**
- 50% of PDFs fail to upload to S3 (22/46 failures)
- Execution time: 600s+ (vs 2-3s expected)
- Pattern: First 5 succeed, last 5 timeout (deterministic)

**Initial Hypothesis:** PDF generation hangs in ReportLab library
- Added detailed logging to pdf_generator.py
- Increased Lambda timeout from 600s to 900s
- Deployed and tested

**Discovery:** Logging never appeared in CloudWatch!
- Logs at depth are lost when Lambda fails before buffer flush
- Only boundary logs survive (handler entry/exit)

**Root Cause Analysis:**
```bash
# Check for actual error message
aws logs filter-log-events \
  --log-group-name /aws/lambda/pdf-worker-dev \
  --filter-pattern "ConnectTimeoutError"

# Output:
botocore.exceptions.ConnectTimeoutError: Connect timeout on endpoint URL:
"https://line-bot-pdf-reports-755283537543.s3.ap-southeast-1.amazonaws.com/..."
```

**Network Path Analysis:**
```bash
# Check VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-0fb04b10ef8c3d18b" \
            "Name=service-name,Values=com.amazonaws.ap-southeast-1.s3"
# Result: Empty (no S3 VPC endpoint)

# Check routing
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-0fb04b10ef8c3d18b"
# Result: 0.0.0.0/0 → nat-0ddc2f2ba2848e433 (NAT Gateway)
```

**Root Cause:** NAT Gateway connection saturation
- 10 concurrent Lambdas attempt S3 upload simultaneously
- NAT Gateway limited to ~5 concurrent connection establishments
- First 5 establish connections → SUCCESS (2-3s)
- Last 5 queue and timeout → FAILURE (600s)

**Solution:** Add S3 VPC Gateway Endpoint
```bash
cd terraform
ENV=dev doppler run -- terraform apply -var-file=terraform.dev.tfvars
```

**Result:**
- Before: 50% failure rate, 10min execution time for failures
- After: 100% success rate, 30s total workflow time
- Cost: FREE (Gateway endpoints have no hourly charge)

**Full Report:** [Bug Hunt: PDF S3 Upload Timeout](../../.claude/bug-hunts/2026-01-05-pdf-s3-upload-timeout.md)

---

## References

- [CLAUDE.md Principle #2: Progressive Evidence Strengthening](../../.claude/CLAUDE.md#2-progressive-evidence-strengthening)
- [CLAUDE.md Principle #15: Infrastructure-Application Contract](../../.claude/CLAUDE.md#15-infrastructure-application-contract)
- [CLAUDE.md Principle #18: Logging Discipline](../../.claude/CLAUDE.md#18-logging-discipline-storytelling-pattern)
- [Error Investigation Skill](../../.claude/skills/error-investigation/)
- [AWS VPC Endpoints Documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [AWS NAT Gateway Troubleshooting](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html)
