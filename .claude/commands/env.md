---
name: env
description: Execute operations targeting feature branch environments (generic environment targeting)
accepts_args: true
arg_schema:
  - name: environment
    required: true
    description: "Feature branch environment name (e.g., 'feature-alerts', 'feature-backtest')"
  - name: operation
    required: true
    description: "What to do in the environment (logs, queries, deploy, compare, etc.)"
---

# Env Command (Generic Environment Targeting)

**Purpose**: Execute operations against feature branch environments from any worktree

**Core Philosophy**: "Target environment, not location" - same as `/dev`, `/stg`, `/prd` but for arbitrary feature branch environments.

**When to use**:
- When you have deployed a feature branch to its own isolated AWS environment
- Check feature branch Lambda logs
- Query feature branch Aurora database (if isolated)
- Deploy to feature branch environment
- Compare feature branch with dev/staging

**When NOT to use**:
- For standard environments → Use `/local`, `/dev`, `/stg`, `/prd` instead
- These fixed commands have explicit safety gates and are optimized for common paths

---

## Relationship to Fixed Environment Commands

| Command | Target | Safety Level | Use For |
|---------|--------|--------------|---------|
| `/local` | localhost + SSM tunnel | Unrestricted | Local development |
| `/dev` | `*-dev` resources | Unrestricted | Development testing |
| `/stg` | `*-staging` resources | Moderate | Pre-prod validation |
| `/prd` | `*-prod` resources | Restricted | Production (read-only default) |
| **`/env`** | `*-{branch}` resources | **Dev-equivalent** | Feature branches |

**Why both?**
- Fixed commands (`/dev`, `/prd`) provide explicit safety differentiation
- `/prd` being distinct has psychological safety value
- `/env` extends the pattern to arbitrary feature branches
- 90% of operations use fixed environments; `/env` handles the long tail

---

## Resource Resolution

Resources resolve using the environment name as suffix:

```
/env "feature-alerts" "operation"
  ↓
dr-daily-report-{component}-feature-alerts
```

| Resource Type | Pattern |
|---------------|---------|
| Lambda | `dr-daily-report-{component}-{env}` |
| Log Group | `/aws/lambda/dr-daily-report-{component}-{env}` |
| S3 Bucket | `dr-daily-report-data-lake-{env}` |
| Aurora | `dr-daily-report-{env}` cluster (if isolated) |
| ECR | `dr-daily-report-lambda-{env}` |
| Doppler | `{env}` config (if exists) |

**Note**: Feature branches may share some resources with dev:
- **Isolated**: Each feature branch has its own Lambda, logs
- **Shared**: Aurora may be shared with dev (depends on provisioning)

---

## Safety Level Mapping

Safety gates are determined by environment naming convention:

| Environment Pattern | Safety Level | Confirmation |
|---------------------|--------------|--------------|
| `feature-*` | Unrestricted (dev-like) | None |
| `experiment-*` | Unrestricted (dev-like) | None |
| `staging-*`, `stg-*` | Moderate | Writes only |
| `hotfix-*` | Restricted (prod-like) | All writes + deploys |
| `release-*` | Restricted (prod-like) | All writes + deploys |

**Default**: If pattern doesn't match, treat as dev-equivalent (unrestricted).

---

## Quick Reference

```bash
# Check logs for feature branch
/env "feature-alerts" "show errors in last 30 min"
/env "feature-backtest" "count errors by type"

# Query Aurora (if isolated or shared)
/env "feature-alerts" "SELECT COUNT(*) FROM alert_rules"
/env "feature-charts" "DESCRIBE chart_patterns"

# Lambda operations
/env "feature-alerts" "get current image digest"
/env "feature-alerts" "list environment variables"

# Deployment
/env "feature-alerts" deploy
/env "feature-backtest" "update to sha256:abc123"

# Comparison
/env "feature-alerts" "compare with dev"
/env "feature-alerts" "diff Lambda config vs staging"
```

---

## Discovery: List Available Environments

```bash
# List all deployed feature environments
/env --list
```

**How discovery works**:
1. Query Lambda functions with `dr-daily-report-*` prefix
2. Extract unique environment suffixes
3. Filter out standard environments (dev, staging, prod)
4. Return remaining feature branch environments

**Output**:
```markdown
## Available Feature Environments

| Environment | Components | Last Modified |
|-------------|------------|---------------|
| feature-alerts | telegram-api, line-bot | 2026-01-14 |
| feature-backtest | telegram-api | 2026-01-12 |
| experiment-charts | telegram-api | 2026-01-10 |

Use: /env "{environment}" "{operation}"
```

---

## Execution Flow

### Step 1: Parse Environment and Operation

```bash
/env "feature-alerts" "show errors in last 30 min"
       ↑                ↑
       ENV              OPERATION
```

- Extract environment name: `feature-alerts`
- Extract operation: `show errors in last 30 min`

### Step 2: Determine Safety Level

```python
if env.startswith(("feature-", "experiment-")):
    safety = "unrestricted"
elif env.startswith(("staging-", "stg-")):
    safety = "moderate"
elif env.startswith(("hotfix-", "release-")):
    safety = "restricted"
else:
    safety = "unrestricted"  # Default to dev-like
```

### Step 3: Resolve Resources

Apply environment suffix to all resource names:

```
{component} → dr-daily-report-{component}-{env}
{log_group} → /aws/lambda/dr-daily-report-{component}-{env}
{bucket} → dr-daily-report-data-lake-{env}
{cluster} → dr-daily-report-{env} (or shared with dev)
```

### Step 4: Execute Operation

Use appropriate AWS CLI, MCP tools, or other methods:

**For logs** (use CloudWatch MCP):
```python
mcp__cloudwatch__execute_log_insights_query(
    log_group_names=[f"/aws/lambda/dr-daily-report-telegram-api-{env}"],
    query_string="fields @timestamp, @message | filter @message like /ERROR/",
    ...
)
```

**For Lambda** (use AWS CLI):
```bash
aws lambda get-function --function-name dr-daily-report-telegram-api-{env}
```

**For deployment**:
Construct appropriate deployment commands for the feature branch.

### Step 5: Report Results

Present results clearly with environment context:

```markdown
## {Environment}: {operation}

{Results}

---
**Environment**: {env}
**Type**: Feature branch
**Safety**: {unrestricted | moderate | restricted}
**Timestamp**: {Bangkok time}
```

---

## Examples

### Example 1: Check Feature Branch Logs

```bash
/env "feature-alerts" "show telegram-api errors in last 30 min"
```

**Execution**:
1. Resolve log group: `/aws/lambda/dr-daily-report-telegram-api-feature-alerts`
2. Query CloudWatch Logs Insights
3. Return formatted results

**Output**:
```markdown
## feature-alerts: telegram-api errors (last 30 min)

Found 3 errors:

| Timestamp | Message |
|-----------|---------|
| 14:32:05 | ValidationError: Invalid ticker symbol |
| 14:28:12 | TimeoutError: Alert delivery timeout |
| 14:15:33 | KeyError: 'price' missing in response |

---
**Environment**: feature-alerts
**Type**: Feature branch
**Safety**: Unrestricted
**Timestamp**: 2026-01-14 14:45:00 (Bangkok)
```

### Example 2: Compare with Dev

```bash
/env "feature-alerts" "compare Lambda config with dev"
```

**Execution**:
1. Get feature branch config: `aws lambda get-function-configuration --function-name dr-daily-report-telegram-api-feature-alerts`
2. Get dev config: `aws lambda get-function-configuration --function-name dr-daily-report-telegram-api-dev`
3. Compare and highlight differences

**Output**:
```markdown
## feature-alerts vs dev: Lambda Configuration

| Setting | feature-alerts | dev | Match |
|---------|----------------|-----|-------|
| Memory | 512 MB | 512 MB | ✅ |
| Timeout | 30s | 30s | ✅ |
| Runtime | python3.11 | python3.11 | ✅ |
| Image Digest | sha256:abc... | sha256:xyz... | ❌ |
| ENV: ENABLE_ALERTS | true | false | ❌ |

**Differences**: 2
- Image digest differs (feature branch has newer code)
- ENABLE_ALERTS is enabled in feature branch
```

### Example 3: Deploy to Feature Branch

```bash
/env "feature-alerts" deploy
```

**Execution**:
1. Determine safety level: `unrestricted` (feature-* prefix)
2. No confirmation required
3. Execute deployment for feature-alerts environment
4. Report deployment status

### Example 4: List Available Environments

```bash
/env --list
```

**Output**:
```markdown
## Available Feature Environments

| Environment | Components | Status | Last Deploy |
|-------------|------------|--------|-------------|
| feature-alerts | telegram-api | Active | 2026-01-14 10:30 |
| feature-backtest | telegram-api, precompute | Active | 2026-01-12 15:45 |
| experiment-charts | telegram-api | Stale (7d) | 2026-01-07 09:00 |

**Total**: 3 feature environments

Use: `/env "{environment}" "{operation}"`
Example: `/env "feature-alerts" "show errors"`

**Cleanup suggestions**:
- `experiment-charts` - Last activity 7 days ago, consider cleanup
```

---

## Integration with Other Commands

### With Worktree Commands
```bash
# Create worktree for feature work
/wt-spin-off "alert-system"

# Work in worktree, deploy to feature environment
/env "feature-alerts" deploy

# Check logs from any location
/env "feature-alerts" "show errors"

# Merge when done
/wt-merge "alert-system"
```

### With Fixed Environment Commands
```bash
# Compare feature with dev
/env "feature-alerts" "compare with dev"

# Or equivalently
/dev "compare with feature-alerts"

# Promote to staging
/env "feature-alerts" "diff vs staging"
/stg deploy  # After feature verified
```

### Workflow Pattern
```bash
# 1. Provision feature environment
/provision-env "feature-alerts" from dev

# 2. Work on feature
# ... make changes ...

# 3. Deploy to feature environment
/env "feature-alerts" deploy

# 4. Verify
/env "feature-alerts" "run integration tests"
/env "feature-alerts" "show errors"

# 5. Compare with dev before merging
/env "feature-alerts" "compare with dev"

# 6. Merge feature branch
/wt-merge "feature-alerts"

# 7. Cleanup feature environment
/env "feature-alerts" cleanup
```

---

## When to Use /env vs Fixed Commands

| Scenario | Use | Why |
|----------|-----|-----|
| Check dev logs | `/dev` | Fixed command, optimized path |
| Deploy to prod | `/prd deploy` | Explicit safety, psychological barrier |
| Check feature branch | `/env "feature-X"` | Dynamic environment |
| Compare dev vs staging | `/dev` or `/stg` | Fixed environments |
| Compare feature vs dev | `/env "feature-X"` | Feature branch context |

**Rule of thumb**:
- **Known environment** (dev/stg/prd/local) → Use fixed command
- **Feature branch** → Use `/env`

---

## Prompt Template

You are executing the `/env` command targeting a **feature branch environment**.

**Environment**: $1
**Operation**: $2

---

### Execution Steps

1. **Validate environment name**: Ensure it's not a standard environment
   - If `dev`, `staging`, `prod`, `local` → Redirect to fixed command
   - Otherwise → Proceed with generic resolution

2. **Determine safety level**:
   - `feature-*`, `experiment-*` → Unrestricted
   - `staging-*`, `stg-*` → Moderate (confirm writes)
   - `hotfix-*`, `release-*` → Restricted (confirm all writes + deploys)
   - Default → Unrestricted

3. **Resolve resources**: Apply environment suffix:
   - Lambda: `dr-daily-report-{component}-{env}`
   - Log groups: `/aws/lambda/dr-daily-report-{component}-{env}`
   - S3: `dr-daily-report-data-lake-{env}`
   - Aurora: `dr-daily-report-{env}` (or shared with dev)

4. **Execute operation**: Use appropriate tools:
   - Logs: CloudWatch MCP tools
   - Lambda: AWS CLI
   - Aurora: AWS CLI or direct query
   - Deploy: Appropriate deployment workflow

5. **Report results**: Include environment context

**Output format**:
```markdown
## {Environment}: {operation_summary}

{results}

---
**Environment**: {env}
**Type**: Feature branch
**Safety**: {level}
**Timestamp**: {Bangkok time}
```

---

## See Also

- `/local` - Local development environment
- `/dev` - Dev environment operations (unrestricted)
- `/stg` - Staging environment operations (moderate gates)
- `/prd` - Production environment operations (restricted)
- `/provision-env` - Create new feature branch environment
- `/wt-spin-off` - Create worktree for parallel work
