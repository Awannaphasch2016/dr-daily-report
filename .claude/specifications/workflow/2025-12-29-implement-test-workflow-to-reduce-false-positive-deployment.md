---
title: Implement test workflow to reduce false positive deployment
focus: workflow
date: 2025-12-29
status: draft
tags: [testing, lambda, docker, ci-cd, deployment]
---

# Workflow Specification: Test Workflow to Reduce False Positive Deployments

## Goal

**What does this workflow accomplish?**

Prevent false positive deployments where tests pass locally/in CI but Lambda fails in production due to import errors, filesystem issues, or environment mismatches.

**Current problem**:
- LINE bot import error reached production (7-day outage)
- Root cause: Unit tests validated source code, not deployment package
- Gap: "Filesystem unaware" testing (tests run in dev environment, not Lambda runtime)

**Solution**:
- Implement Docker-based testing using official Lambda base image
- Test deployment package (what Lambda actually runs), not source code
- Catch import/deployment errors in CI/CD before production

---

## Workflow Diagram

```
[Code Change]
      ↓
[Unit Tests in Docker] ← Uses Lambda Python 3.11 container
      ↓ (Pass)
[Build Deployment Package]
      ↓
[Smoke Test in Docker] ← Validates deployment package
      ↓ (Pass)
[Deploy to Lambda]
      ↓
[Post-Deploy Smoke Test] ← Verify production Lambda
      ↓ (Pass)
[Production Ready] ✅
```

**Error path** (any test fails):
```
[Test Failure]
      ↓
[Block Deployment] ❌
      ↓
[Developer Notification]
      ↓
[Fix Code]
      ↓
[Retry Workflow]
```

---

## Workflow Nodes

### Node 1: Unit Tests in Docker

**Purpose**: Run all unit tests inside Lambda-identical Docker environment

**Input**:
```python
{
  "source_code": "src/",
  "test_files": "tests/line_bot/",
  "python_version": "3.11"
}
```

**Processing**:
```bash
# Run pytest inside Lambda container
docker run --rm \
  -v $(pwd):/var/task \
  -e PYTHONPATH=/var/task \
  public.ecr.aws/lambda/python:3.11 \
  bash -c "
    pip install -q pytest pytest-mock boto3 pymysql
    pytest tests/line_bot/ -v --tb=short
  "
```

**Output**:
```python
{
  "tests_passed": true,
  "tests_failed": 0,
  "import_errors": 0,
  "duration_seconds": 8.5
}
```

**Duration**: 5-10s (Docker image cached)

**Error conditions**:
- Import error: Test can't import module → **BLOCK DEPLOYMENT**
- Logic error: Test assertion fails → **BLOCK DEPLOYMENT**
- Timeout: Tests take >60s → **WARN** (but don't block)

**Why Docker for unit tests**:
- ✅ **2 birds 1 stone**: Tests logic AND validates Lambda environment
- ✅ **Filesystem aware**: Tests run in `/var/task` with Lambda Python build
- ✅ **Catches import errors**: If imports fail in test, they'll fail in Lambda
- ✅ **Runtime fidelity**: Exact Python version, dependencies, filesystem layout

---

### Node 2: Build Deployment Package

**Purpose**: Create Lambda deployment ZIP from source code

**Input**:
```python
{
  "source_code": "src/",
  "requirements": "requirements.txt",
  "build_script": "./build.sh"
}
```

**Processing**:
```bash
# Execute build script
./build.sh

# Verify ZIP created
ls -lh deployment_package.zip
```

**Output**:
```python
{
  "deployment_package": "deployment_package.zip",
  "package_size_mb": 15.2,
  "build_successful": true
}
```

**Duration**: 10-20s (depends on dependencies)

**Error conditions**:
- Build fails: `build.sh` exits non-zero → **BLOCK DEPLOYMENT**
- ZIP too large: >50MB uncompressed → **WARN** (Lambda limit is 250MB)
- Missing files: Required files not in ZIP → **BLOCK DEPLOYMENT**

---

### Node 3: Smoke Test Deployment Package

**Purpose**: Validate deployment package structure and imports in Lambda Docker

**Input**:
```python
{
  "deployment_package": "deployment_package.zip",
  "lambda_runtime": "python:3.11"
}
```

**Processing**:
```bash
# Test deployment package in Lambda container
docker run --rm \
  -v $(pwd)/deployment_package.zip:/tmp/package.zip \
  public.ecr.aws/lambda/python:3.11 \
  bash -c "
    cd /var/task
    unzip -q /tmp/package.zip

    # Test critical imports
    python -c 'from src.integrations.line_bot import handle_webhook; print(\"✅ handle_webhook\")'
    python -c 'from src.lambda_handler import lambda_handler; print(\"✅ lambda_handler\")'

    echo '✅ All imports validated'
  "
```

**Output**:
```python
{
  "imports_validated": true,
  "deployment_package_valid": true,
  "critical_functions_present": ["handle_webhook", "lambda_handler"]
}
```

**Duration**: 3-5s

**Error conditions**:
- Import error: Module not found in ZIP → **BLOCK DEPLOYMENT** ← **This would have caught LINE bot bug**
- File missing: Required file not in `/var/task` → **BLOCK DEPLOYMENT**
- Unzip fails: Corrupted ZIP → **BLOCK DEPLOYMENT**

**Why this catches production bugs**:
- ✅ Tests actual deployment artifact (ZIP), not source code
- ✅ Validates filesystem layout matches Lambda expectations
- ✅ Catches "file exists in source but missing in ZIP" errors
- ✅ Exact Lambda environment (official AWS Docker image)

---

### Node 4: Deploy to Lambda

**Purpose**: Upload deployment package to AWS Lambda

**Input**:
```python
{
  "deployment_package": "deployment_package.zip",
  "function_name": "line-bot-ticker-report",
  "environment": "dev"
}
```

**Processing**:
```bash
# Deploy to Lambda
ENV=dev doppler run -- aws lambda update-function-code \
  --function-name line-bot-ticker-report \
  --zip-file fileb://deployment_package.zip

# Wait for update to complete
aws lambda wait function-updated \
  --function-name line-bot-ticker-report
```

**Output**:
```python
{
  "deployment_successful": true,
  "lambda_version": "$LATEST",
  "last_modified": "2025-12-29T10:30:00Z",
  "code_sha256": "abc123..."
}
```

**Duration**: 10-30s (depends on package size)

**Error conditions**:
- Upload fails: Network error, auth failure → **RETRY** (transient)
- Lambda doesn't update: Stuck in pending → **ALERT** (manual intervention)
- Code SHA mismatch: Deployed code ≠ uploaded code → **ALERT** (corruption)

---

### Node 5: Post-Deploy Smoke Test

**Purpose**: Verify deployed Lambda actually works in production

**Input**:
```python
{
  "function_name": "line-bot-ticker-report",
  "test_payload": {"body": "test", "headers": {"x-line-signature": "test_signature"}}
}
```

**Processing**:
```bash
# Invoke Lambda with test payload
aws lambda invoke \
  --function-name line-bot-ticker-report \
  --payload '{"body":"test","headers":{"x-line-signature":"test_signature"}}' \
  --query 'StatusCode' \
  response.json

# Verify response
STATUS=$(cat response.json | jq -r '.statusCode')
if [ "$STATUS" != "200" ]; then
  echo "❌ Smoke test failed - Lambda returned $STATUS"
  exit 1
fi

# Check for import errors
if grep -q "IMPORT_ERROR" response.json; then
  echo "❌ Import error detected in Lambda response"
  exit 1
fi

echo "✅ Smoke test passed"
```

**Output**:
```python
{
  "smoke_test_passed": true,
  "lambda_status_code": 200,
  "no_import_errors": true,
  "response_time_ms": 1250
}
```

**Duration**: 2-3s

**Error conditions**:
- Lambda returns 500: Import error or runtime error → **ROLLBACK DEPLOYMENT**
- Lambda timeout: Exceeds 30s → **ALERT** (performance issue)
- Import error in response: "IMPORT_ERROR" found → **ROLLBACK DEPLOYMENT**

**Why this is critical**:
- ✅ Final validation in actual AWS environment
- ✅ Catches infrastructure issues (IAM, VPC, environment variables)
- ✅ Detects errors that Docker tests might miss
- ✅ Provides rollback trigger if deployment broken

---

## State Management

**State structure**:
```python
class DeploymentState(TypedDict):
    source_code_path: str
    unit_tests_passed: bool
    deployment_package_path: Optional[str]
    package_validated: bool
    lambda_deployed: bool
    smoke_test_passed: bool
    deployment_version: Optional[str]
    error: Optional[str]
    should_rollback: bool
```

**State transitions**:

```
Initial State:
{
  "unit_tests_passed": false,
  "deployment_package_path": null,
  "package_validated": false,
  "lambda_deployed": false,
  "smoke_test_passed": false,
  "error": null,
  "should_rollback": false
}

After Node 1 (Unit Tests):
{
  "unit_tests_passed": true,  # ← Changed
  ...
}

After Node 2 (Build):
{
  "unit_tests_passed": true,
  "deployment_package_path": "deployment_package.zip",  # ← Changed
  ...
}

After Node 3 (Package Validation):
{
  "unit_tests_passed": true,
  "deployment_package_path": "deployment_package.zip",
  "package_validated": true,  # ← Changed
  ...
}

After Node 4 (Deploy):
{
  ...
  "package_validated": true,
  "lambda_deployed": true,  # ← Changed
  "deployment_version": "$LATEST",
  ...
}

After Node 5 (Smoke Test):
{
  ...
  "lambda_deployed": true,
  "smoke_test_passed": true,  # ← Changed
  "error": null
}
```

**Error state** (any node fails):
```python
{
  ...
  "error": "Import error: cannot import handle_webhook",
  "should_rollback": false  # Don't deploy, so nothing to rollback
}
```

**Rollback state** (post-deploy smoke test fails):
```python
{
  ...
  "lambda_deployed": true,
  "smoke_test_passed": false,
  "error": "Smoke test failed: Lambda returned 500",
  "should_rollback": true  # ← Trigger rollback
}
```

---

## Error Handling

**Error propagation**:
- Each node returns `{"success": bool, "error": Optional[str]}`
- If `success == false`, workflow halts at that node
- Error message propagated to developer via GitHub Actions failure

**Retry logic**:

| Error Type | Node | Retry Strategy |
|------------|------|----------------|
| Import error | Unit Tests (1) | **NO RETRY** - Developer must fix code |
| Build failure | Build Package (2) | **NO RETRY** - Developer must fix build |
| Package validation | Smoke Test (3) | **NO RETRY** - Deployment package broken |
| Network error | Deploy (4) | **RETRY 3x** with exponential backoff |
| Lambda timeout | Smoke Test (5) | **RETRY 1x** then ALERT |

**Permanent errors** (no retry):
- Import errors (code bug)
- Build failures (build script bug)
- Package validation failures (deployment package bug)

**Transient errors** (retry allowed):
- Network failures (AWS API unreachable)
- Lambda throttling (temporary capacity issue)

---

## Performance

**Expected duration**:
- **Best case**: 25-35s (all tests pass, no retries)
  - Unit Tests: 8s
  - Build: 10s
  - Package Validation: 3s
  - Deploy: 10s
  - Smoke Test: 2s
  - Total: ~33s

- **Average case**: 30-40s (includes Docker image pull once)
  - First run: +10s (Docker image pull)
  - Subsequent runs: cached

- **Worst case**: 60-120s (includes retries)
  - Network error retry: +30s
  - Lambda update wait: +20s

**Bottlenecks**:
- Node 2 (Build Package): 10-20s
  - Why: `pip install` for dependencies
  - Optimization: Cache `requirements.txt` layers in Docker

- Node 4 (Deploy): 10-30s
  - Why: Large deployment package (15MB)
  - Optimization: Use Lambda layers for dependencies

**Performance vs Safety trade-off**:
- ✅ 30-40s CI/CD time is **acceptable** to prevent 7-day production outage
- ✅ Docker overhead (5-10s) is **worth it** for deployment fidelity
- ✅ Can run locally in same time (developer pre-commit validation)

---

## CI/CD Integration

**GitHub Actions workflow** (`.github/workflows/test-and-deploy.yml`):

```yaml
name: Test and Deploy Lambda

on:
  push:
    branches: [dev, main]
  pull_request:
    branches: [dev, main]

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      # Node 1: Unit Tests in Docker
      - name: Run unit tests in Lambda Docker
        run: |
          docker run --rm \
            -v $(pwd):/var/task \
            -e PYTHONPATH=/var/task \
            public.ecr.aws/lambda/python:3.11 \
            bash -c "
              pip install -q pytest pytest-mock boto3 pymysql
              pytest tests/line_bot/ -v --tb=short
            "

      # Node 2: Build Deployment Package
      - name: Build deployment package
        run: ./build.sh

      # Node 3: Smoke Test Package
      - name: Validate deployment package
        run: |
          docker run --rm \
            -v $(pwd)/deployment_package.zip:/tmp/package.zip \
            public.ecr.aws/lambda/python:3.11 \
            bash -c "
              cd /var/task
              unzip -q /tmp/package.zip
              python -c 'from src.integrations.line_bot import handle_webhook'
              python -c 'from src.lambda_handler import lambda_handler'
              echo '✅ Package validated'
            "

      # Node 4: Deploy (only on dev/main branch)
      - name: Deploy to Lambda
        if: github.ref == 'refs/heads/dev'
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN_DEV }}
        run: |
          ENV=dev doppler run -- aws lambda update-function-code \
            --function-name line-bot-ticker-report \
            --zip-file fileb://deployment_package.zip

          aws lambda wait function-updated \
            --function-name line-bot-ticker-report

      # Node 5: Post-Deploy Smoke Test
      - name: Smoke test deployed Lambda
        if: github.ref == 'refs/heads/dev'
        run: |
          aws lambda invoke \
            --function-name line-bot-ticker-report \
            --payload '{"body":"test","headers":{"x-line-signature":"test_signature"}}' \
            response.json

          STATUS=$(jq -r '.statusCode' response.json)
          if [ "$STATUS" != "200" ]; then
            echo "❌ Smoke test failed"
            exit 1
          fi

          if grep -q "IMPORT_ERROR" response.json; then
            echo "❌ Import error detected"
            exit 1
          fi

          echo "✅ Deployment successful"
```

---

## Local Development Workflow

**Developer pre-commit validation**:

```bash
#!/bin/bash
# scripts/test_lambda_local.sh

echo "🧪 Running Lambda tests locally..."

# Node 1: Unit Tests
echo ""
echo "1️⃣ Running unit tests in Docker..."
docker run --rm \
  -v $(pwd):/var/task \
  -e PYTHONPATH=/var/task \
  public.ecr.aws/lambda/python:3.11 \
  bash -c "
    pip install -q pytest pytest-mock boto3 pymysql
    pytest tests/line_bot/ -v --tb=short
  "

if [ $? -ne 0 ]; then
  echo "❌ Unit tests failed"
  exit 1
fi

# Node 2: Build
echo ""
echo "2️⃣ Building deployment package..."
./build.sh

if [ $? -ne 0 ]; then
  echo "❌ Build failed"
  exit 1
fi

# Node 3: Smoke Test Package
echo ""
echo "3️⃣ Validating deployment package..."
docker run --rm \
  -v $(pwd)/deployment_package.zip:/tmp/package.zip \
  public.ecr.aws/lambda/python:3.11 \
  bash -c "
    cd /var/task
    unzip -q /tmp/package.zip
    python -c 'from src.integrations.line_bot import handle_webhook'
    python -c 'from src.lambda_handler import lambda_handler'
    echo '✅ Package validated'
  "

if [ $? -ne 0 ]; then
  echo "❌ Package validation failed"
  exit 1
fi

echo ""
echo "✅ All local tests passed - ready to commit"
```

**Usage**:
```bash
# Before committing
./scripts/test_lambda_local.sh

# If passes, safe to commit and push
git add .
git commit -m "fix: ..."
git push
```

---

## Open Questions

- [x] Should we cache Docker images to speed up CI/CD? **YES** - GitHub Actions caches by default
- [x] Should we add pre-commit hooks for local validation? **OPTIONAL** - not required, but useful
- [ ] Should we test ALL Lambda functions or just LINE bot? **EXTEND LATER** - start with LINE bot, generalize pattern
- [ ] Should we add performance benchmarks (response time)? **FUTURE** - focus on correctness first
- [ ] Should we separate unit tests from integration tests? **NO** - Docker-based tests ARE unit tests for Lambda

---

## Success Criteria

**Workflow is successful if**:
- ✅ Import errors caught in CI/CD before deployment (Node 3)
- ✅ Tests run in <60s total (acceptable for CI/CD)
- ✅ Developers can run same tests locally (Docker installed)
- ✅ False positive deployments eliminated (tests pass = Lambda works)
- ✅ No additional infrastructure required (uses existing GitHub Actions + Docker)

**Metrics to track**:
- Deployment success rate (should increase to ~100%)
- CI/CD duration (should remain <60s)
- False positive rate (should drop to 0%)
- Time to detect deployment issues (should be <5min in CI/CD, not 7 days in production)

---

## Next Steps

- [ ] Create `scripts/test_lambda_local.sh` for local development
- [ ] Update `.github/workflows/test-and-deploy.yml` with new workflow
- [ ] Test workflow with LINE bot Lambda function
- [ ] Document in testing runbook (`.claude/skills/testing-workflow/`)
- [ ] Extend pattern to other Lambda functions (Telegram API, scheduler)
- [ ] Add to `CLAUDE.md` as testing principle (#10 update)

---

## Related Documentation

- **Research**: `.claude/research/2025-12-29-local-docker-testing-for-lambda.md` (tool evaluation)
- **Bug Hunt**: `.claude/bug-hunts/2025-12-28-linebot-import-error-custom-error-message.md` (motivating bug)
- **What-If**: Conversation about Docker-based testing vs import unit tests
- **CLAUDE.md**: Principle #10 (Testing Anti-Patterns) - will be updated with Docker-based testing pattern

---

*Specification created: 2025-12-29*
*Status: Ready for implementation (plan mode)*
*Priority: P0 (Prevents production outages)*
