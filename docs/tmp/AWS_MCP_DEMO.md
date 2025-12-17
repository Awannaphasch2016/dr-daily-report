# AWS MCP Advantage Demonstration

## Scenario: "Check if my telegram-api Lambda is healthy and show me any recent errors"

---

## ❌ WITHOUT AWS MCP (Manual Approach)

### Step 1: You need to know the exact Lambda function name
```bash
# First, figure out the naming convention by reading Terraform files
grep -r "function_name" terraform/
# Result: "${var.project_name}-telegram-api-${var.environment}"

# Then check tfvars to get actual values
cat terraform/envs/dev/terraform.tfvars
# Result: project_name = "dr-daily-report", environment = "dev"
# So function name is: dr-daily-report-telegram-api-dev
```

### Step 2: Get Lambda function status
```bash
aws lambda get-function \
  --function-name dr-daily-report-telegram-api-dev \
  --region ap-southeast-1 \
  --query 'Configuration.[FunctionName,State,LastUpdateStatus,Runtime,MemorySize,Timeout]' \
  --output table
```

### Step 3: Get recent CloudWatch logs
```bash
# Find the log group name (need to know the naming convention)
LOG_GROUP="/aws/lambda/dr-daily-report-telegram-api-dev"

# Get recent log streams
aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --region ap-southeast-1 \
  --query 'logStreams[*].[logStreamName,lastEventTime]' \
  --output table

# Get recent error logs (need to know log stream name from above)
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region ap-southeast-1 \
  --query 'events[*].[timestamp,message]' \
  --output table
```

### Step 4: Check CloudWatch metrics for errors
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region ap-southeast-1 \
  --output table
```

### Step 5: Interpret results manually
- Compare error counts
- Read through log messages
- Check if errors are increasing
- Determine if action is needed

**Time Required:** 5-10 minutes  
**Commands Needed:** 4-5 different AWS CLI commands  
**Knowledge Required:** 
- Lambda naming conventions
- CloudWatch log group naming
- AWS CLI query syntax
- Date/time formatting for filters
- Metric names and dimensions

---

## ✅ WITH AWS MCP (AI-Assisted Approach)

### You simply ask Cursor:

```
Check if my telegram-api Lambda is healthy and show me any recent errors
```

### What happens automatically:

1. **Context Understanding**: Cursor understands:
   - You're asking about a Lambda function
   - "telegram-api" refers to the function in your project
   - "healthy" means checking status, errors, and recent activity
   - "recent errors" means CloudWatch logs with ERROR level

2. **Intelligent Discovery**: Cursor can:
   - Search your codebase to find the exact function name
   - Understand Terraform naming patterns
   - Know which environment you're working with

3. **Automated Execution**: Cursor uses AWS MCP to:
   - Query Lambda function status
   - Retrieve CloudWatch logs
   - Filter for errors automatically
   - Present results in readable format

4. **Smart Analysis**: Cursor can:
   - Identify error patterns
   - Suggest fixes based on error messages
   - Compare with previous states
   - Provide actionable insights

**Time Required:** 10-30 seconds  
**Commands Needed:** 0 (just ask)  
**Knowledge Required:** None (natural language)

---

## Real Example Output Comparison

### WITHOUT AWS MCP Output:
```
$ aws lambda get-function --function-name dr-daily-report-telegram-api-dev --region ap-southeast-1
{
    "Configuration": {
        "FunctionName": "dr-daily-report-telegram-api-dev",
        "State": "Active",
        "LastUpdateStatus": "Successful",
        ...
    }
}

$ aws logs filter-log-events --log-group-name "/aws/lambda/dr-daily-report-telegram-api-dev" --filter-pattern "ERROR" ...
[Raw JSON output - need to parse manually]
```

### WITH AWS MCP Output:
```
✅ Lambda Function Status: dr-daily-report-telegram-api-dev

📊 Current Status:
   • State: Active ✅
   • Last Update: Successful ✅
   • Runtime: Provided (Container Image)
   • Memory: 512 MB
   • Timeout: 120 seconds

🔍 Recent Errors (Last Hour):
   • Found 3 errors in the last hour
   • Error Pattern: "Connection timeout to Aurora"
   • Most Recent: 2025-01-XX 14:23:15 UTC
   • Frequency: Increasing (1 error/hour → 3 errors/hour)

⚠️  Recommendation:
   The errors suggest Aurora connection timeouts. This might be due to:
   1. VPC configuration issues
   2. Security group rules blocking connections
   3. Aurora cluster scaling down too aggressively

   Would you like me to:
   - Check VPC configuration?
   - Review security group rules?
   - Check Aurora cluster status?
```

---

## Key Advantages Summary

| Aspect | WITHOUT AWS MCP | WITH AWS MCP |
|--------|----------------|--------------|
| **Time** | 5-10 minutes | 10-30 seconds |
| **Commands** | 4-5 CLI commands | Natural language query |
| **Knowledge** | AWS CLI syntax, naming conventions | Just describe what you need |
| **Context** | Manual discovery | Automatic from codebase |
| **Analysis** | Manual interpretation | AI-powered insights |
| **Error Handling** | Manual troubleshooting | Suggested fixes |
| **Learning Curve** | High (AWS expertise needed) | Low (just ask questions) |

---

## Additional Use Cases Where AWS MCP Shines

### 1. **Complex Multi-Service Queries**
**Without MCP:**
```bash
# Need to run 5+ commands across Lambda, API Gateway, CloudWatch, DynamoDB
aws lambda get-function ...
aws apigatewayv2 get-api ...
aws dynamodb describe-table ...
aws cloudwatch get-metric-statistics ...
# Then manually correlate results
```

**With MCP:**
```
Show me the complete health status of my telegram-api including Lambda, API Gateway, and DynamoDB
```

### 2. **Intelligent Troubleshooting**
**Without MCP:**
- Read error logs manually
- Search documentation
- Try different AWS CLI commands
- Hope you find the right metric

**With MCP:**
```
My telegram-api is slow. What's causing the performance issue?
```
→ Cursor analyzes: Lambda duration, memory usage, cold starts, downstream service latency, etc.

### 3. **Code-Aware Operations**
**Without MCP:**
- Need to know exact resource names
- Manual lookups in Terraform files
- Risk of typos or wrong environment

**With MCP:**
```
Deploy the latest code to telegram-api
```
→ Cursor knows:
- Which Lambda function (from codebase)
- Which ECR image to use (from CI/CD)
- Which environment (from context)
- How to safely deploy (from Terraform patterns)

---

## Conclusion

AWS MCP transforms AWS operations from:
- **Manual CLI commands** → **Natural language queries**
- **Time-consuming lookups** → **Instant context-aware results**
- **Raw data dumps** → **Intelligent analysis and recommendations**
- **Expert knowledge required** → **Anyone can ask questions**

This is especially powerful for:
- **Faster debugging** - Get answers in seconds, not minutes
- **Better insights** - AI correlates data across services
- **Reduced errors** - No typos in resource names or commands
- **Learning** - Understand AWS better through AI explanations
