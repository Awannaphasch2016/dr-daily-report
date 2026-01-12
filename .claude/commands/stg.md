---
name: stg
description: Execute operations targeting the staging environment without switching worktrees
accepts_args: true
arg_schema:
  - name: operation
    required: true
    description: "What to do in staging environment (logs, queries, deploy, compare, etc.)"
---

# Staging Environment Command

**Purpose**: Execute ANY operation targeting the staging environment from any worktree

**Core Philosophy**: "Target environment, not location" - Claude can execute commands against remote AWS resources regardless of which worktree/branch is currently active.

**When to use**:
- Check staging Lambda logs without switching worktrees
- Query staging Aurora database
- Verify staging deployment
- Compare staging with dev or prod
- Pre-production validation

---

## Resource Resolution

All resources automatically resolve to staging environment:

| Resource Type | Resolution |
|---------------|------------|
| Lambda | `dr-daily-report-{component}-staging` |
| Log Group | `/aws/lambda/dr-daily-report-{component}-staging` |
| S3 Bucket | `dr-daily-report-data-lake-staging` |
| Aurora | `dr-daily-report-staging` cluster |
| ECR | `dr-daily-report-lambda-staging` |
| Doppler | `stg` config |

---

## Quick Reference

```bash
# Check logs
/stg "show telegram-api errors in last 30 min"
/stg "verify no errors after deployment"

# Query Aurora
/stg "SELECT COUNT(*) FROM daily_prices"
/stg "compare record count with dev"

# Lambda operations
/stg "get current image digest for telegram-api"
/stg "verify Lambda updated to latest"

# Deployment verification
/stg "run smoke tests"
/stg "compare Lambda config with dev"

# Pre-production check
/stg "verify all endpoints healthy"
```

---

## Safety Level: MODERATE

Staging is pre-production - some caution required:

| Operation | Confirmation |
|-----------|--------------|
| Read (logs, queries, describe) | No confirmation |
| Write (data changes) | Confirmation required |
| Deploy | Confirmation required |

---

## Operation Categories

### Read Operations (No Confirmation)
- Query CloudWatch logs
- Describe Lambda functions
- Query Aurora (SELECT)
- List S3 objects
- Check deployment status
- Get metrics
- Run smoke tests (read-only)

### Write Operations (Confirmation Required)
- Update Lambda code
- Insert/Update Aurora data
- Upload to S3
- Deploy artifacts

---

## Execution Flow

### Step 1: Parse Operation Request

Extract what the user wants to do and classify as READ or WRITE.

### Step 2: Resolve Resources

Apply staging suffix to all resource names:
```
{component} → dr-daily-report-{component}-staging
{log_group} → /aws/lambda/dr-daily-report-{component}-staging
{bucket} → dr-daily-report-data-lake-staging
{cluster} → dr-daily-report-staging
```

### Step 3: Check Safety Gate

**If WRITE operation**:
```
⚠️ WRITE operation on STAGING environment

Operation: {description}
Resources: {affected resources}

This will modify staging data/configuration.
Proceed? (y/n)
```

### Step 4: Execute Operation

Use appropriate AWS CLI, MCP tools, or other methods.

### Step 5: Report Results

Present results clearly with environment context:
```markdown
## Staging Environment: {operation}

{Results}

**Environment**: staging
**Resources queried**: {list}
**Timestamp**: {Bangkok time}
```

---

## Examples

### Example 1: Verify Deployment

```bash
/stg "verify deployment succeeded"
```

**Execution**:
1. Check Lambda image digest matches expected
2. Run health check against API
3. Check for errors in logs (last 5 min)
4. Report deployment status

### Example 2: Compare with Dev

```bash
/stg "compare Lambda image digest with dev"
```

**Execution**:
1. Get staging image: `aws lambda get-function --function-name dr-daily-report-telegram-api-staging`
2. Get dev image: `aws lambda get-function --function-name dr-daily-report-telegram-api-dev`
3. Compare digests
4. Report match/mismatch

### Example 3: Pre-Production Validation

```bash
/stg "run pre-production checklist"
```

**Execution**:
1. Health check all endpoints
2. Verify Aurora connectivity
3. Check for errors in logs
4. Validate configuration matches expected
5. Report overall status

---

## Common Use Cases

### After Dev Deployment
```bash
/dev deploy
# ... wait for dev deployment ...
/stg "verify staging has same image as dev"
```

### Before Production Promotion
```bash
/stg "run smoke tests"
/stg "check error rate in last 24h"
/stg "compare config with production"
```

### Debugging Staging Issues
```bash
/stg "show errors in last 1h"
/stg "query Aurora for suspicious data"
```

---

## Integration with Other Commands

**Deployment**:
```bash
/stg deploy  # Equivalent to /deploy staging (requires confirmation)
```

**Cross-environment comparison**:
```bash
/dev "get Lambda digest"
/stg "get Lambda digest"
# Compare outputs
```

---

## See Also

- `/dev` - Development environment operations (unrestricted)
- `/prd` - Production environment operations (read-only default)
- `/deploy` - Full deployment workflow

---

## Prompt Template

You are executing the `/stg` command targeting the **staging environment**.

**Operation requested**: $ARGUMENTS

---

### Execution Steps

1. **Parse operation type**: Determine if this is logs, query, Lambda, deployment, or comparison

2. **Classify as READ or WRITE**:
   - READ: logs, queries (SELECT), describe, list, health checks
   - WRITE: deploy, update, insert, delete, modify

3. **Resolve resources**: Apply staging suffix to all resource names:
   - Lambda: `dr-daily-report-{component}-staging`
   - Log groups: `/aws/lambda/dr-daily-report-{component}-staging`
   - S3: `dr-daily-report-data-lake-staging`
   - Aurora cluster: `dr-daily-report-staging`
   - Doppler config: `stg`

4. **Safety gate** (for WRITE operations):
   ```
   ⚠️ WRITE operation on STAGING environment

   Operation: {description}
   Resources: {affected resources}

   Proceed? (y/n)
   ```

5. **Execute operation**: Use appropriate tools

6. **Report results**: Include environment context in output

**Output format**:
```markdown
## Staging Environment: {operation_summary}

{results}

---
**Environment**: staging
**Timestamp**: {Bangkok time}
```
