---
name: prd
description: Execute operations targeting the production environment without switching worktrees (read-only default)
accepts_args: true
arg_schema:
  - name: operation
    required: true
    description: "What to do in production environment (logs, queries, status checks - write operations require explicit confirmation)"
---

# Production Environment Command

**Purpose**: Execute operations targeting the production environment from any worktree

**Core Philosophy**: "Observe production, don't touch it" - Production operations are read-only by default. Write operations require explicit confirmation.

**When to use**:
- Check production Lambda logs
- Query production Aurora (read-only)
- Verify production deployment status
- Compare production with staging
- Monitor production health

**When NOT to use**:
- Direct production deployments (use `/deploy prod` with full workflow)
- Emergency fixes (use proper incident response)

---

## Resource Resolution

All resources automatically resolve to production environment:

| Resource Type | Resolution |
|---------------|------------|
| Lambda | `dr-daily-report-{component}-prod` |
| Log Group | `/aws/lambda/dr-daily-report-{component}-prod` |
| S3 Bucket | `dr-daily-report-data-lake-prod` |
| Aurora | `dr-daily-report-prod` cluster |
| ECR | `dr-daily-report-lambda-prod` |
| Doppler | `prd` config |

---

## Quick Reference

```bash
# Check logs (safe)
/prd "show telegram-api errors in last 1h"
/prd "count errors by type today"

# Query Aurora (read-only)
/prd "SELECT COUNT(*) FROM daily_prices"
/prd "SELECT MAX(date) FROM daily_prices"

# Status checks (safe)
/prd "get current image digest for telegram-api"
/prd "check all Lambda health"

# Comparisons (safe)
/prd "compare Lambda image with staging"
/prd "verify config matches staging"

# Monitoring (safe)
/prd "check error rate in last 24h"
/prd "get CloudWatch metrics summary"
```

---

## Safety Level: RESTRICTED

Production requires maximum caution:

| Operation | Permission | Confirmation |
|-----------|------------|--------------|
| Read (logs, SELECT, describe) | Allowed | None |
| Write (data changes) | Blocked by default | Double confirmation |
| Deploy | Redirect to /deploy prod | Full workflow |

---

## Operation Categories

### Read Operations (Always Allowed)
- Query CloudWatch logs
- Describe Lambda functions
- Query Aurora (SELECT only)
- List S3 objects
- Check deployment status
- Get metrics
- Health checks

### Write Operations (Double Confirmation Required)

**Before any write operation**:
```
🔒 PRODUCTION WRITE OPERATION BLOCKED

Operation: {description}
Resources: {affected resources}

This is a PRODUCTION environment. Write operations require explicit confirmation.

To proceed, you must:
1. Confirm this is intentional
2. Confirm you understand the impact

Type "CONFIRM PRODUCTION WRITE" to proceed, or cancel.
```

### Deploy Operations (Redirect)

Production deployments use full workflow:
```
/prd deploy → Redirects to /deploy prod

This ensures:
- Pre-deployment validation
- Staging verification
- Full deployment workflow
- Post-deployment validation
```

---

## Execution Flow

### Step 1: Parse Operation Request

Extract what the user wants to do and classify:
- READ: Allowed
- WRITE: Requires double confirmation
- DEPLOY: Redirect to /deploy prod

### Step 2: Resolve Resources

Apply prod suffix to all resource names:
```
{component} → dr-daily-report-{component}-prod
{log_group} → /aws/lambda/dr-daily-report-{component}-prod
{bucket} → dr-daily-report-data-lake-prod
{cluster} → dr-daily-report-prod
```

### Step 3: Safety Gate

**If READ operation**: Proceed directly

**If WRITE operation**:
```
🔒 PRODUCTION WRITE OPERATION

⚠️ WARNING: This will modify PRODUCTION data/configuration

Operation: {description}
Resources: {affected resources}
Impact: {potential impact}

This action cannot be easily undone.

Type "CONFIRM PRODUCTION WRITE" to proceed.
```

**If DEPLOY operation**:
```
🔄 Production deployments use full workflow

Redirecting to: /deploy prod

This ensures proper validation, verification, and rollback capability.
```

### Step 4: Execute Operation

Use appropriate AWS CLI, MCP tools, or other methods.

### Step 5: Report Results

Present results clearly with environment context:
```markdown
## Production Environment: {operation}

{Results}

**Environment**: PRODUCTION
**Resources queried**: {list}
**Timestamp**: {Bangkok time}
**Operation type**: READ (safe)
```

---

## Examples

### Example 1: Check Production Errors

```bash
/prd "show errors in last 1 hour"
```

**Execution**:
1. Classify: READ operation (allowed)
2. Resolve: `/aws/lambda/dr-daily-report-telegram-api-prod`
3. Query CloudWatch Logs
4. Return formatted results with PRODUCTION label

### Example 2: Verify Deployment Matches Staging

```bash
/prd "compare Lambda image with staging"
```

**Execution**:
1. Classify: READ operation (allowed)
2. Get prod image digest
3. Get staging image digest
4. Compare and report match/mismatch

### Example 3: Production Query (Read-Only)

```bash
/prd "count active users today"
```

**Execution**:
1. Classify: READ operation (SELECT query)
2. Resolve: `dr-daily-report-prod` cluster
3. Execute: `SELECT COUNT(*) FROM users WHERE last_active >= CURDATE()`
4. Return count

### Example 4: Write Operation (Blocked)

```bash
/prd "update user settings"
```

**Response**:
```
🔒 PRODUCTION WRITE OPERATION BLOCKED

Operation: UPDATE user settings
Resources: dr-daily-report-prod Aurora cluster

This is a PRODUCTION environment. Write operations require explicit confirmation.

To proceed, type "CONFIRM PRODUCTION WRITE"

Recommended: Make this change in dev/staging first, then deploy.
```

---

## Common Use Cases

### Post-Deployment Monitoring
```bash
/prd "check error rate in last 30 min"
/prd "verify all endpoints responding"
/prd "compare metrics with pre-deployment baseline"
```

### Incident Investigation
```bash
/prd "show all errors in last 1h"
/prd "query Aurora for affected records"
/prd "get Lambda cold start metrics"
```

### Capacity Planning
```bash
/prd "get daily request volume"
/prd "check Aurora connection count"
/prd "get Lambda concurrent execution metrics"
```

---

## Anti-Patterns

### Don't Do This
```bash
# Don't use /prd for deployments
/prd deploy  # → Use /deploy prod instead

# Don't do data fixes directly
/prd "UPDATE users SET ..."  # → Fix in dev, deploy properly

# Don't bypass safety gates
# → They exist to protect production
```

### Do This Instead
```bash
# Use proper deployment workflow
/deploy prod

# Test in lower environments first
/dev "UPDATE users SET ..."  # Test fix
/stg "UPDATE users SET ..."  # Verify in staging
# Then deploy migration

# Respect safety gates
# They prevent incidents
```

---

## Integration with Other Commands

**Deployment**:
```bash
/prd deploy  # Redirects to /deploy prod
```

**Cross-environment verification**:
```bash
/stg "get Lambda digest"
/prd "get Lambda digest"
# Verify they match before considering deployment complete
```

**Incident response**:
```bash
/prd "show recent errors"
# Investigate, fix in dev
/dev "apply fix"
# Verify in staging
/stg "verify fix"
# Deploy to prod via proper workflow
/deploy prod
```

---

## See Also

- `/dev` - Development environment operations (unrestricted)
- `/stg` - Staging environment operations (moderate gates)
- `/deploy` - Full deployment workflow (required for prod deploys)

---

## Prompt Template

You are executing the `/prd` command targeting the **PRODUCTION environment**.

**Operation requested**: $ARGUMENTS

---

### Execution Steps

1. **Parse operation type**: Determine if this is logs, query, Lambda, deployment, or comparison

2. **Classify operation**:
   - **READ**: logs, queries (SELECT), describe, list, health checks, metrics → ALLOWED
   - **WRITE**: update, insert, delete, modify → REQUIRES DOUBLE CONFIRMATION
   - **DEPLOY**: any deployment → REDIRECT TO /deploy prod

3. **Resolve resources**: Apply prod suffix to all resource names:
   - Lambda: `dr-daily-report-{component}-prod`
   - Log groups: `/aws/lambda/dr-daily-report-{component}-prod`
   - S3: `dr-daily-report-data-lake-prod`
   - Aurora cluster: `dr-daily-report-prod`
   - Doppler config: `prd`

4. **Safety gate**:

   **For READ**: Proceed directly

   **For WRITE**:
   ```
   🔒 PRODUCTION WRITE OPERATION

   ⚠️ WARNING: This will modify PRODUCTION

   Operation: {description}
   Resources: {affected resources}

   Type "CONFIRM PRODUCTION WRITE" to proceed.
   ```

   **For DEPLOY**:
   ```
   🔄 Redirecting to /deploy prod for full deployment workflow
   ```

5. **Execute operation**: Use appropriate tools (only after safety gate passes)

6. **Report results**: Include PRODUCTION label prominently

**Output format**:
```markdown
## PRODUCTION Environment: {operation_summary}

{results}

---
**Environment**: 🔴 PRODUCTION
**Operation type**: {READ | WRITE (confirmed)}
**Timestamp**: {Bangkok time}
```
