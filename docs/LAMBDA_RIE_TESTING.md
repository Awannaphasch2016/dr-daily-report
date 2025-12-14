# Lambda RIE Testing Guide

## Overview

This project uses Lambda Runtime Interface Emulator (RIE) to test Lambda handlers locally before deployment. This catches import errors and handler configuration issues **before** they reach AWS.

**Problem solved:** The v116 import error that reached production would have been caught by these tests.

## Quick Start

### Option 1: Quick Import Check (Fastest)

```bash
just lambda-check
```

**What it does:**
- Builds Lambda container image
- Runs quick import test for all handlers
- Takes ~30 seconds
- **Use before:** Every git push / PR

**Example output:**
```
⚡ Quick Lambda import check...
✅ report_worker_handler.handler
✅ telegram_lambda_handler.handler
✅ lambda_handler.lambda_handler

✅ All handlers import successfully
```

### Option 2: Full RIE Testing (Most comprehensive)

```bash
# Start Lambda containers with RIE
just lambda-up

# In another terminal, run pytest tests
just test-lambda

# Stop containers
just lambda-down
```

**What it does:**
- Starts actual Lambda containers with RIE
- Runs pytest suite that invokes handlers via HTTP
- Tests handlers in exact Lambda runtime environment
- **Use before:** Deployment to dev/staging/prod

### Option 3: Full Automated Workflow

```bash
just test-lambda-full
```

**What it does:**
- Builds image → Starts RIE containers → Runs tests → Cleans up
- Complete end-to-end validation
- Takes ~2 minutes
- **Use in:** CI/CD pipeline

## Available Commands

| Command | Purpose | Time | When to Use |
|---------|---------|------|-------------|
| `just lambda-check` | Quick import validation | ~30s | Every commit/push |
| `just lambda-up` | Start RIE containers | ~10s | Interactive testing |
| `just lambda-down` | Stop RIE containers | ~2s | After testing |
| `just test-lambda` | Run RIE pytest tests | ~30s | Verify handlers work |
| `just test-lambda-full` | Build + test + cleanup | ~2min | CI/CD |

## What Gets Tested

### Layer 2 (RIE) Tests Catch:
- ✅ **Import errors** (missing modules, wrong paths)
- ✅ **Handler function exists** (handler vs lambda_handler)
- ✅ **Container-specific issues** (file permissions, paths)
- ✅ **Dependency problems** (missing packages in requirements.txt)
- ✅ **Environment variable handling**

### Example Failures Caught:
```python
# ❌ Would be caught:
from src.nonexistent_module import Foo  # Import error

# ❌ Would be caught:
def hander(event, context):  # Typo: 'hander' not 'handler'
    pass

# ❌ Would be caught:
from mangum import Mangum  # Missing in requirements.txt
```

## RIE Container Endpoints

When running `just lambda-up`:

| Handler | Endpoint | Event Type |
|---------|----------|------------|
| report-worker | http://localhost:9001 | SQS |
| telegram-api | http://localhost:9002 | API Gateway |
| line-bot | http://localhost:9003 | Function URL |

## Manual Testing with RIE

```bash
# Start containers
just lambda-up

# Test report-worker with SQS event
curl -X POST "http://localhost:9001/2015-03-31/functions/function/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "Records": [{
      "messageId": "test-123",
      "body": "{\"job_id\": \"rpt_test\", \"ticker\": \"DBS19\"}"
    }]
  }'

# Test telegram-api health endpoint
curl -X POST "http://localhost:9002/2015-03-31/functions/function/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "requestContext": {
      "http": {"method": "GET", "path": "/api/v1/health"}
    },
    "headers": {}
  }'

# Stop containers
just lambda-down
```

## CI/CD Integration

Add to `.github/workflows/deploy.yml` after Docker build:

```yaml
- name: Validate Lambda Handlers (RIE)
  run: just lambda-check
```

This catches import errors **before** pushing to ECR.

## Troubleshooting

### Containers won't start
```bash
# Check Docker is running
docker ps

# Check logs
docker-compose -f docker-compose.lambda.yml logs

# Rebuild image
docker-compose -f docker-compose.lambda.yml build
```

### Import errors in tests
```bash
# Verify handler files exist in container
docker run --rm --entrypoint ls lambda-quick-test -la /var/task/ | grep handler

# Check Python path
docker run --rm --entrypoint python3 lambda-quick-test -c "import sys; print(sys.path)"

# Test direct import
docker run --rm -e PYTHONPATH=/var/task --entrypoint python3 lambda-quick-test -c "import report_worker_handler; print('OK')"
```

### Tests timeout
- Increase timeout in pytest: `pytest --timeout=60`
- Check container logs: `docker logs <container_name>`
- Verify environment variables are set

## Architecture

```
┌─────────────────────────────────────────────┐
│  Developer Machine                          │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  just lambda-check                   │  │
│  │  ├─ docker build                     │  │
│  │  └─ docker run python test_imports  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  just test-lambda                    │  │
│  │  ├─ docker-compose up (RIE)          │  │
│  │  ├─ pytest (HTTP invoke Lambda)      │  │
│  │  └─ docker-compose down              │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ✅ All tests pass → Safe to deploy       │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  CI/CD (GitHub Actions)                     │
│                                             │
│  ├─ Build Docker image                     │
│  ├─ just lambda-check (fail fast)          │
│  ├─ Push to ECR                             │
│  └─ Deploy to Lambda                        │
└─────────────────────────────────────────────┘
```

## Files Created

- `docker-compose.lambda.yml` - RIE container configuration
- `tests/lambda_rie/test_handlers_rie.py` - pytest RIE tests
- `scripts/test_lambda_imports.py` - Quick import checker
- `justfile` - New `lambda-*` recipes

## See Also

- [Testing Strategy Plan](/home/anak/.claude/plans/goofy-dancing-wigderson.md)
- [Deployment Runbook](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md)
- [AWS Lambda RIE Documentation](https://docs.aws.amazon.com/lambda/latest/dg/images-test.html)
