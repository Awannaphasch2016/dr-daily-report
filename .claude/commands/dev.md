---
name: dev
description: Execute operations targeting the dev environment without switching worktrees
accepts_args: true
arg_schema:
  - name: operation
    required: true
    description: "What to do in dev environment (logs, queries, deploy, compare, etc.)"
---

# Dev Environment Command

**Purpose**: Execute ANY operation targeting the dev environment from any worktree

**Core Philosophy**: "Target environment, not location" - Claude can execute commands against remote AWS resources regardless of which worktree/branch is currently active.

**When to use**:
- Check dev Lambda logs without switching worktrees
- Query dev Aurora database
- Deploy to dev environment
- Compare dev resources with other environments
- Any operation targeting dev AWS resources

---

## Resource Resolution

All resources automatically resolve to dev environment:

| Resource Type | Resolution |
|---------------|------------|
| Lambda | `dr-daily-report-{component}-dev` |
| Log Group | `/aws/lambda/dr-daily-report-{component}-dev` |
| S3 Bucket | `dr-daily-report-data-lake-dev` |
| Aurora | `dr-daily-report-dev` cluster |
| ECR | `dr-daily-report-lambda-dev` |
| Doppler | `dev` config |

---

## Quick Reference

```bash
# Check logs
/dev "show telegram-api errors in last 30 min"
/dev "count errors by type in last 1h"

# Query Aurora
/dev "SELECT COUNT(*) FROM daily_prices"
/dev "DESCRIBE ticker_master"

# Lambda operations
/dev "get current image digest for telegram-api"
/dev "list all Lambda functions"

# Deployment
/dev deploy
/dev "update telegram-api to sha256:abc123"

# Comparison
/dev "compare Lambda config with staging"
```

---

## Safety Level: UNRESTRICTED

Dev environment is safe for experimentation:
- No confirmation required for any operation
- Full read/write access
- Deploy freely

---

## Operation Categories

### Read Operations
- Query CloudWatch logs
- Describe Lambda functions
- Query Aurora (SELECT)
- List S3 objects
- Check deployment status
- Get metrics

### Write Operations
- Update Lambda code
- Insert/Update Aurora data
- Upload to S3
- Deploy artifacts

---

## Execution Flow

### Step 1: Parse Operation Request

Extract what the user wants to do:
- Log inspection
- Database query
- Lambda operation
- Deployment
- Comparison

### Step 2: Resolve Resources

Apply dev suffix to all resource names:
```
{component} → dr-daily-report-{component}-dev
{log_group} → /aws/lambda/dr-daily-report-{component}-dev
{bucket} → dr-daily-report-data-lake-dev
{cluster} → dr-daily-report-dev
```

### Step 3: Execute Operation

Use appropriate AWS CLI, MCP tools, or other methods:

**For logs** (use CloudWatch MCP):
```python
mcp__cloudwatch__execute_log_insights_query(
    log_group_names=["/aws/lambda/dr-daily-report-telegram-api-dev"],
    query_string="fields @timestamp, @message | filter @message like /ERROR/",
    ...
)
```

**For Aurora** (use Bash with mysql client or Aurora Data API):
```bash
aws rds-data execute-statement \
  --resource-arn "arn:aws:rds:ap-southeast-1:...:cluster:dr-daily-report-dev" \
  --secret-arn "..." \
  --sql "SELECT COUNT(*) FROM daily_prices"
```

**For Lambda** (use AWS CLI):
```bash
aws lambda get-function --function-name dr-daily-report-telegram-api-dev
```

**For deployment**:
Delegate to `/deploy dev` workflow

### Step 4: Report Results

Present results clearly with environment context:
```markdown
## Dev Environment: {operation}

{Results}

**Environment**: dev
**Resources queried**: {list}
**Timestamp**: {Bangkok time}
```

---

## Examples

### Example 1: Check Logs

```bash
/dev "show telegram-api errors in last 30 min"
```

**Execution**:
1. Resolve log group: `/aws/lambda/dr-daily-report-telegram-api-dev`
2. Query CloudWatch Logs Insights
3. Return formatted results

### Example 2: Query Aurora

```bash
/dev "count records in daily_prices"
```

**Execution**:
1. Resolve cluster: `dr-daily-report-dev`
2. Execute: `SELECT COUNT(*) FROM daily_prices`
3. Return count with timestamp

### Example 3: Compare with Staging

```bash
/dev "compare Lambda image digest with staging"
```

**Execution**:
1. Get dev image: `aws lambda get-function --function-name dr-daily-report-telegram-api-dev`
2. Get staging image: `aws lambda get-function --function-name dr-daily-report-telegram-api-staging`
3. Compare digests
4. Report match/mismatch

---

## Integration with Other Commands

**Deployment**:
```bash
/dev deploy  # Equivalent to /deploy dev
```

**Comparison workflow**:
```bash
/dev "get current state"
# Make changes
/dev "verify changes applied"
```

---

## See Also

- `/stg` - Staging environment operations
- `/prd` - Production environment operations (read-only default)
- `/deploy` - Full deployment workflow

---

## Prompt Template

You are executing the `/dev` command targeting the **dev environment**.

**Operation requested**: $ARGUMENTS

---

### Execution Steps

1. **Parse operation type**: Determine if this is logs, query, Lambda, deployment, or comparison

2. **Resolve resources**: Apply dev suffix to all resource names:
   - Lambda: `dr-daily-report-{component}-dev`
   - Log groups: `/aws/lambda/dr-daily-report-{component}-dev`
   - S3: `dr-daily-report-data-lake-dev`
   - Aurora cluster: `dr-daily-report-dev`
   - Doppler config: `dev`

3. **Execute operation**: Use appropriate tools:
   - Logs: CloudWatch MCP tools
   - Lambda: AWS CLI
   - Aurora: AWS CLI or direct query
   - Deploy: Delegate to deployment workflow

4. **Report results**: Include environment context in output

**Safety**: Dev environment - no confirmation required for any operation.

**Output format**:
```markdown
## Dev Environment: {operation_summary}

{results}

---
**Environment**: dev
**Timestamp**: {Bangkok time}
```
