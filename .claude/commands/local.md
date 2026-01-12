---
name: local
description: Execute operations targeting the local development environment (localhost with SSM tunnel to Aurora)
accepts_args: true
arg_schema:
  - name: operation
    required: true
    description: "What to do in local environment (start server, run tests, query Aurora via tunnel, etc.)"
---

# Local Environment Command

**Purpose**: Execute operations targeting the local development environment from any worktree

**Core Philosophy**: "Local development with remote data" - Local FastAPI server with SSM tunnel to dev Aurora. No AWS Lambda involved.

**When to use**:
- Start local development server
- Run local tests
- Query Aurora via SSM tunnel
- Debug locally before deploying
- Verify local setup

---

## Environment Characteristics

Unlike `/dev`, `/stg`, `/prd` which target AWS resources, `/local` targets:

| Component | Location |
|-----------|----------|
| API Server | `localhost:8000` (FastAPI via uvicorn) |
| Aurora | Dev cluster via SSM tunnel |
| DynamoDB | LocalStack (`localhost:4566`) |
| Secrets | Doppler `local_dev` config (inherits from `dev`) |

**No Lambda functions** - everything runs locally.

---

## Resource Resolution

| Resource Type | Resolution |
|---------------|------------|
| API | `http://localhost:8000` |
| Aurora | SSM tunnel → `dr-daily-report-dev` cluster |
| DynamoDB | LocalStack `localhost:4566` |
| Doppler | `local_dev` config |
| Logs | Local stdout/stderr |

---

## Quick Reference

```bash
# Start local server
/local "start API server"
/local "start with hot reload"

# Verify setup
/local "verify local setup"
/local "check SSM tunnel status"

# Run tests locally
/local "run unit tests"
/local "run integration tests against local"

# Query Aurora (via tunnel)
/local "SELECT COUNT(*) FROM daily_prices"
/local "check Aurora connection"

# LocalStack operations
/local "list DynamoDB tables"
/local "create local DynamoDB tables"

# Debug
/local "check what's running on port 8000"
/local "tail local logs"
```

---

## Safety Level: UNRESTRICTED

Local environment is completely safe:
- No confirmation required for any operation
- Cannot affect AWS resources directly (only via SSM tunnel to dev Aurora)
- Changes are local only

---

## Prerequisites

Before using `/local`, ensure:

1. **SSM tunnel running** (for Aurora access):
   ```bash
   # Start tunnel in background
   aws ssm start-session \
     --target <bastion-instance-id> \
     --document-name AWS-StartPortForwardingSessionToRemoteHost \
     --parameters '{"host":["dr-daily-report-dev.cluster-xxx.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["3306"]}'
   ```

2. **LocalStack running** (for DynamoDB):
   ```bash
   docker-compose up -d localstack
   ```

3. **Doppler configured**:
   ```bash
   doppler setup --config local_dev
   ```

---

## Execution Flow

### Step 1: Parse Operation Request

Determine operation type:
- Server management (start, stop, restart)
- Database operations (Aurora queries via tunnel)
- LocalStack operations (DynamoDB)
- Tests (unit, integration)
- Verification (setup check, health check)

### Step 2: Resolve Resources

Apply local environment configuration:
```
API → http://localhost:8000
Aurora → localhost:3306 (via SSM tunnel)
DynamoDB → localhost:4566 (LocalStack)
Doppler → local_dev
```

### Step 3: Execute Operation

**For server operations**:
```bash
# Start server
doppler run --config local_dev -- uvicorn src.api.main:app --reload --port 8000

# Or via scripts
./scripts/start_local_api.sh
```

**For Aurora queries** (via tunnel):
```bash
doppler run --config local_dev -- mysql -h 127.0.0.1 -P 3306 -u admin -p -e "SELECT COUNT(*) FROM daily_prices"
```

**For LocalStack operations**:
```bash
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

**For tests**:
```bash
doppler run --config local_dev -- pytest tests/ -v
```

### Step 4: Report Results

Present results with local context:
```markdown
## Local Environment: {operation}

{Results}

**Environment**: local (localhost + SSM tunnel)
**Doppler config**: local_dev
**Timestamp**: {Bangkok time}
```

---

## Examples

### Example 1: Start Local Server

```bash
/local "start API server"
```

**Execution**:
```bash
doppler run --config local_dev -- uvicorn src.api.main:app --reload --port 8000
```

**Output**:
```
✅ Local API server started
   URL: http://localhost:8000
   Docs: http://localhost:8000/docs
   Config: local_dev (inherits from dev)
```

### Example 2: Verify Local Setup

```bash
/local "verify local setup"
```

**Execution**:
```bash
./scripts/verify_local_setup.sh
```

**Checks**:
- ✅ Doppler configured for local_dev
- ✅ SSM tunnel active (port 3306)
- ✅ LocalStack running (port 4566)
- ✅ Aurora connection successful
- ✅ DynamoDB tables exist

### Example 3: Query Aurora Locally

```bash
/local "SELECT COUNT(*) FROM daily_prices"
```

**Execution**:
1. Verify SSM tunnel is running
2. Execute query via local MySQL connection
3. Return results

**Note**: Queries go to dev Aurora via tunnel, so data matches `/dev` environment.

### Example 4: Run Tests

```bash
/local "run integration tests"
```

**Execution**:
```bash
doppler run --config local_dev -- pytest tests/integration/ -v
```

---

## Common Workflows

### Local Development Cycle
```bash
/local "verify setup"           # Check prerequisites
/local "start server"           # Start FastAPI
# Make code changes
# Server auto-reloads (--reload flag)
/local "run tests"              # Verify changes
/dev deploy                     # Deploy to dev when ready
```

### Debugging Aurora Issues
```bash
/local "check SSM tunnel"       # Verify connection
/local "SELECT * FROM ..."      # Query locally
/dev "SELECT * FROM ..."        # Compare with direct dev query
```

---

## Doppler Config: local_dev

The `local_dev` config **inherits from dev** with local overrides:

| Secret | Source | Value |
|--------|--------|-------|
| `AURORA_HOST` | Override | `127.0.0.1` (tunnel) |
| `AURORA_PORT` | Override | `3306` (tunnel) |
| `DYNAMODB_ENDPOINT` | Override | `http://localhost:4566` |
| `API_BASE_URL` | Override | `http://localhost:8000` |
| `OPENROUTER_API_KEY` | Inherited | From dev |
| `TELEGRAM_BOT_TOKEN` | Inherited | From dev |
| ... | Inherited | From dev |

**Benefits**:
- 9 local overrides + inherited secrets = complete config
- When dev secrets update, local inherits automatically
- No secret duplication

---

## Integration with Other Commands

**Local → Dev promotion**:
```bash
/local "run all tests"          # Verify locally
/local "verify setup"           # Check everything works
/dev deploy                     # Deploy to dev
/dev "verify deployment"        # Confirm in dev
```

**Debugging workflow**:
```bash
/dev "show recent errors"       # Find issue in dev
/local "reproduce locally"      # Debug with local server
# Fix the issue
/local "verify fix"             # Test locally
/dev deploy                     # Deploy fix
```

---

## Troubleshooting

### SSM Tunnel Not Running
```
Error: Cannot connect to Aurora

Fix:
1. Start SSM tunnel: aws ssm start-session ...
2. Verify: nc -zv localhost 3306
```

### LocalStack Not Running
```
Error: Cannot connect to DynamoDB

Fix:
1. Start LocalStack: docker-compose up -d localstack
2. Create tables: python scripts/create_local_dynamodb_tables.py
```

### Doppler Not Configured
```
Error: Missing secrets

Fix:
1. Configure: doppler setup --config local_dev
2. Verify: doppler run -- printenv | head
```

---

## See Also

- `/dev` - Dev environment operations (AWS)
- `/stg` - Staging environment operations (AWS)
- `/prd` - Production environment operations (AWS)
- [Doppler Config Guide](../../docs/deployment/DOPPLER_CONFIG.md)
- [Shared Virtual Environment](../../docs/guides/shared-virtual-environment.md)

---

## Prompt Template

You are executing the `/local` command targeting the **local development environment**.

**Operation requested**: $ARGUMENTS

---

### Execution Steps

1. **Parse operation type**: Determine if this is server, database, test, or verification

2. **Resolve resources**: Apply local configuration:
   - API: `http://localhost:8000`
   - Aurora: `localhost:3306` (via SSM tunnel to dev)
   - DynamoDB: `localhost:4566` (LocalStack)
   - Doppler config: `local_dev`

3. **Check prerequisites** (if needed):
   - SSM tunnel running for Aurora operations
   - LocalStack running for DynamoDB operations
   - Doppler configured for any operation

4. **Execute operation**: Use appropriate tools:
   - Server: `doppler run --config local_dev -- uvicorn ...`
   - Aurora: `doppler run --config local_dev -- mysql ...`
   - DynamoDB: `aws --endpoint-url=http://localhost:4566 ...`
   - Tests: `doppler run --config local_dev -- pytest ...`

5. **Report results**: Include local context in output

**Safety**: Local environment - no confirmation required.

**Output format**:
```markdown
## Local Environment: {operation_summary}

{results}

---
**Environment**: local (localhost + SSM tunnel)
**Doppler config**: local_dev
**Timestamp**: {Bangkok time}
```
