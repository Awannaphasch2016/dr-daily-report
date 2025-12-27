---
title: Nightly CI/CD Build with Comprehensive Tests
focus: workflow
date: 2025-12-24
status: draft
schedule: 1 AM daily (18:00 UTC / Bangkok timezone)
tags: [ci-cd, testing, nightly-build, infrastructure, integration-tests]
---

# Workflow Specification: Nightly CI/CD Build with Comprehensive Tests

## Goal

**What does this workflow accomplish?**

Run a comprehensive nightly build at 1 AM Bangkok time (18:00 UTC previous day) that validates deployed infrastructure and code through long-running integration, smoke, and end-to-end tests that are too slow for PR checks or deploy pipelines.

**Purpose**:
- Verify deployed infrastructure works correctly (Aurora, Lambda, EventBridge, SQS, S3)
- Catch configuration drift between environments
- Validate end-to-end workflows with real AWS services
- Run expensive tests (full ticker precompute, multi-ticker backtests)
- Detect silent failures that unit tests miss

**Target environments**: dev, staging (production runs on-demand manually)

---

## Workflow Diagram

```
[Scheduled Trigger 1 AM]
        ↓
[Setup & Prepare] → [Tier 2: Integration Tests] → [Tier 3: Smoke Tests]
        ↓                      ↓                           ↓
   [Report]           [Infrastructure Tests]     [End-to-End Tests]
        ↓                      ↓                           ↓
   [Notify]            [Aurora Schema Tests]      [Full Workflow Tests]
                               ↓                           ↓
                    [EventBridge Schedule Tests]  [Multi-Ticker Tests]
                               ↓                           ↓
                        [Success/Failure] ←───────────────┘
                               ↓
                        [Send Notification]
                               ↓
                        [Archive Results]
```

---

## Test Execution Strategy

### Test Tier Breakdown

Based on existing test markers and project structure:

| Tier | Tests | Duration | Current CI Usage | Nightly Build |
|------|-------|----------|------------------|---------------|
| 0 | Unit only | ~30s | Local dev | ❌ Skip (too fast) |
| 1 | Unit + mocked | ~2min | Deploy gate | ❌ Skip (covered by PR/deploy) |
| 2 | + Integration | ~10-15min | None | ✅ **Primary focus** |
| 3 | + Smoke | ~5-10min | Post-deploy only | ✅ **Secondary focus** |
| 4 | + E2E | ~20-30min | Manual only | ✅ **Tertiary focus** |

**Nightly build runs**: Tier 2 + Tier 3 + Tier 4 (integration + smoke + e2e)

### Current Test Coverage Analysis

From proof analysis, you have **141 integration/smoke/e2e tests** across:
- `tests/infrastructure/` - AWS resource verification
- `tests/integration/` - Service integration tests
- `tests/data/` - Data layer integration tests
- `tests/scheduler/` - Scheduler integration tests
- `tests/telegram/` - Telegram API integration tests
- `tests/e2e/` - End-to-end workflow tests

---

## Workflow Nodes

### Node 1: Setup & Environment Preparation

**Purpose**: Prepare test environment and validate prerequisites

**Actions**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies (requirements.txt + test dependencies)
4. Configure AWS credentials for dev/staging
5. Verify environment variables (Doppler secrets)
6. Check AWS resource availability (Aurora, Lambda, SQS)

**Output**:
```yaml
environment_ready: true
aws_region: "ap-southeast-1"
test_environment: "dev"  # or "staging"
resources_validated: true
```

**Duration**: ~2-3 minutes

**Error conditions**:
- Missing AWS credentials → Fail immediately (notification sent)
- Aurora unreachable → Fail immediately (infrastructure issue)
- Missing environment variables → Fail with detailed list

---

### Node 2: Tier 2 Integration Tests

**Purpose**: Run integration tests that require real AWS services but don't deploy code

**Test categories**:

#### 2.1 Aurora Integration Tests
```bash
pytest tests/infrastructure/test_aurora_*.py \
       tests/data/test_*_integration.py \
       -m integration \
       --tb=short \
       -v
```

**Tests**:
- Aurora schema matches code expectations
- Precompute service writes/reads correctly
- Cache roundtrip tests (write → read → verify)
- Fund data repository integration
- Data lake S3 integration

**Expected duration**: 5-8 minutes

---

#### 2.2 Infrastructure Validation Tests
```bash
pytest tests/infrastructure/ \
       -m integration \
       --tb=short \
       -v
```

**Tests**:
- EventBridge scheduler exists and is enabled
- Lambda functions deployed with correct configuration
- SQS queues configured correctly
- Security groups allow Aurora access
- Lambda VPC configuration correct

**Expected duration**: 3-5 minutes

---

#### 2.3 Scheduler Integration Tests
```bash
pytest tests/scheduler/ \
       tests/integration/test_precompute_trigger_integration.py \
       -m integration \
       --tb=short \
       -v
```

**Tests**:
- Parallel precompute SQS fan-out
- Symbol format contract (Yahoo → DR conversion)
- Scheduler-to-precompute trigger flow
- Job creation and status tracking

**Expected duration**: 4-6 minutes

---

#### 2.4 Telegram API Integration Tests
```bash
pytest tests/telegram/ \
       -m integration \
       --tb=short \
       -v
```

**Tests**:
- Rankings cache integration
- Report retrieval from Aurora
- API endpoint contracts
- Data serialization (NumPy → JSON)

**Expected duration**: 2-3 minutes

---

### Node 3: Tier 3 Smoke Tests

**Purpose**: Verify deployed Lambda functions work with live invocation

**Test categories**:

#### 3.1 Scheduler Lambda Smoke Test
```bash
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action":"health"}' \
  /tmp/scheduler-health.json

# Verify response
cat /tmp/scheduler-health.json | jq '.statusCode == 200'
```

**Validation**:
- Lambda responds without import errors
- Aurora connection succeeds
- Environment variables loaded correctly

**Expected duration**: 30-60 seconds

---

#### 3.2 Precompute Smoke Test (Single Ticker)
```bash
aws lambda invoke \
  --function-name dr-daily-report-ticker-scheduler-dev \
  --payload '{"action":"precompute","symbol":"NVDA","include_report":true}' \
  /tmp/precompute-smoke.json

# Verify success
cat /tmp/precompute-smoke.json | jq '.body.success > 0'
```

**Validation**:
- Precompute completes without schema errors
- Data written to Aurora successfully
- Report generation works

**Expected duration**: 2-3 minutes (includes LLM call)

---

#### 3.3 Report Worker Smoke Test (via SQS)
```bash
# Send test message to SQS queue
aws sqs send-message \
  --queue-url $REPORT_JOBS_QUEUE_URL \
  --message-body '{"job_id":"nightly_test","ticker":"DBS19"}'

# Wait for processing (poll job status)
# Verify job completed successfully
```

**Validation**:
- SQS message triggers Lambda
- Report worker processes ticker
- Job status updates to "completed"
- Report cached in Aurora

**Expected duration**: 3-5 minutes

---

### Node 4: Tier 4 End-to-End Tests

**Purpose**: Run full workflow tests that simulate real user scenarios

**Test categories**:

#### 4.1 Full Scheduler Workflow (Multi-Ticker)
```bash
pytest tests/integration/test_precompute_trigger_integration.py::test_end_to_end_scheduler_to_step_functions \
       -m e2e \
       --tb=short \
       -v
```

**What it tests**:
1. Scheduler invoked with multiple tickers
2. Step Functions execution starts
3. All tickers processed in parallel
4. Results stored in Aurora
5. Cache populated correctly

**Expected duration**: 5-10 minutes (waits for Step Functions)

---

#### 4.2 Telegram API End-to-End
```bash
pytest tests/e2e/test_twinbar_dr_api_integration.py \
       -m e2e \
       --tb=short \
       -v
```

**What it tests**:
- Telegram Mini App API requests
- Rankings retrieval from cache
- Report generation from Aurora
- Chart data formatting
- Error handling

**Expected duration**: 3-5 minutes

---

#### 4.3 Parallel Precompute (All Tickers) - OPTIONAL
```bash
# This is expensive - run weekly instead of nightly
pytest tests/scheduler/test_parallel_precompute.py \
       -m "integration and not ratelimited" \
       --tb=short \
       -v
```

**What it tests**:
- Full 46-ticker precompute
- SQS fan-out at scale
- Lambda concurrency handling
- Aurora write throughput

**Expected duration**: 15-20 minutes

**Frequency**: Weekly (Sunday 1 AM) instead of nightly (too expensive)

---

### Node 5: Results Collection & Analysis

**Purpose**: Aggregate test results, generate report, analyze failures

**Actions**:
1. Collect pytest JSON report
2. Count passes/failures/skips by tier
3. Extract failure details (traceback, logs)
4. Query CloudWatch logs for Lambda errors during tests
5. Generate summary report (Markdown)

**Output**:
```yaml
total_tests: 141
passed: 135
failed: 3
skipped: 3
duration_minutes: 28
failure_details:
  - test: "test_aurora_schema_comprehensive"
    error: "Column 'new_field' not found"
    file: "tests/infrastructure/test_aurora_schema_comprehensive.py:45"
    logs: "https://cloudwatch.link/..."
```

**Duration**: 1-2 minutes

---

### Node 6: Notification

**Purpose**: Send test results to team

**Notification channels**:
- **GitHub Actions summary** (always)
- **Slack webhook** (on failure only)
- **Email** (on failure only, optional)

**Notification format**:

**On Success**:
```markdown
✅ Nightly Build PASSED (2025-12-24 01:00 Bangkok)

Environment: dev
Duration: 28 minutes
Tests: 135 passed, 3 skipped

Coverage:
  - Tier 2 (Integration): ✅ 98 passed
  - Tier 3 (Smoke): ✅ 25 passed
  - Tier 4 (E2E): ✅ 12 passed

Infrastructure:
  - Aurora: ✅ Healthy
  - Lambda: ✅ All functions responding
  - EventBridge: ✅ Schedule active

Next nightly build: 2025-12-25 01:00
```

**On Failure**:
```markdown
❌ Nightly Build FAILED (2025-12-24 01:00 Bangkok)

Environment: dev
Duration: 18 minutes (stopped early)
Tests: 120 passed, 3 failed, 18 skipped

❌ FAILURES:
1. test_aurora_schema_comprehensive
   Error: Column 'user_facing_scores' not found in ticker_data
   File: tests/infrastructure/test_aurora_schema_comprehensive.py:45
   Logs: https://cloudwatch.link/...

2. test_scheduler_lambda_invocation
   Error: Lambda timeout after 30s
   File: tests/infrastructure/test_scheduler_lambda.py:78
   Logs: https://cloudwatch.link/...

3. test_precompute_trigger_integration
   Error: SQS message not received within 5 minutes
   File: tests/integration/test_precompute_trigger_integration.py:120
   Logs: https://cloudwatch.link/...

🔧 Recommended Actions:
  - Check Aurora schema migration status
  - Verify Lambda timeout configuration
  - Investigate SQS queue visibility timeout

Full report: https://github.com/actions/runs/...
```

**Duration**: 30 seconds

---

## GitHub Actions Workflow Structure

### File: `.github/workflows/nightly-build.yml`

```yaml
name: Nightly Build - Comprehensive Tests

on:
  schedule:
    # 1 AM Bangkok (UTC+7) = 18:00 UTC previous day
    - cron: '0 18 * * *'  # Daily at 6 PM UTC (1 AM Bangkok)

  workflow_dispatch:  # Manual trigger for testing
    inputs:
      environment:
        description: 'Environment to test'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - staging
      test_tier:
        description: 'Test tier to run'
        required: false
        default: 'all'
        type: choice
        options:
          - all
          - integration-only
          - smoke-only
          - e2e-only

env:
  PYTHON_VERSION: '3.11'
  AWS_REGION: ap-southeast-1
  TEST_ENVIRONMENT: ${{ github.event.inputs.environment || 'dev' }}

jobs:
  ###############################################################################
  # Job 1: Setup & Environment Validation
  ###############################################################################
  setup:
    name: Setup & Validate Environment
    runs-on: ubuntu-latest
    outputs:
      environment_ready: ${{ steps.validate.outputs.ready }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-json-report boto3 pymysql

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Validate AWS Resources
        id: validate
        run: |
          echo "🔍 Validating AWS resources for ${{ env.TEST_ENVIRONMENT }} environment..."

          # Check Aurora accessibility
          AURORA_HOST=$(doppler secrets get AURORA_HOST --plain || echo "")
          if [ -z "$AURORA_HOST" ]; then
            echo "❌ Aurora host not configured"
            exit 1
          fi
          echo "✅ Aurora configured: $AURORA_HOST"

          # Check Lambda functions exist
          aws lambda get-function --function-name dr-daily-report-ticker-scheduler-${{ env.TEST_ENVIRONMENT }} > /dev/null
          echo "✅ Scheduler Lambda exists"

          # Check EventBridge rule
          aws events describe-rule --name dr-daily-report-daily-ticker-fetch-${{ env.TEST_ENVIRONMENT }} > /dev/null
          echo "✅ EventBridge rule exists"

          # Check SQS queue
          QUEUE_URL=$(doppler secrets get REPORT_JOBS_QUEUE_URL --plain || echo "")
          if [ -z "$QUEUE_URL" ]; then
            echo "❌ SQS queue URL not configured"
            exit 1
          fi
          echo "✅ SQS queue configured"

          echo "ready=true" >> $GITHUB_OUTPUT

  ###############################################################################
  # Job 2: Tier 2 - Integration Tests
  ###############################################################################
  integration-tests:
    name: Tier 2 - Integration Tests
    runs-on: ubuntu-latest
    needs: setup
    if: |
      needs.setup.outputs.environment_ready == 'true' &&
      (github.event.inputs.test_tier == 'all' ||
       github.event.inputs.test_tier == 'integration-only' ||
       github.event.inputs.test_tier == '')

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-json-report boto3 pymysql

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Run Integration Tests
        id: tests
        run: |
          echo "🧪 Running Tier 2 integration tests..."

          pytest tests/ \
            -m "integration and not e2e and not legacy" \
            --json-report \
            --json-report-file=integration-results.json \
            --tb=short \
            -v \
            --maxfail=10 \
            2>&1 | tee integration-test-output.txt

          TEST_EXIT_CODE=${PIPESTATUS[0]}

          echo "exit_code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: integration-test-results
          path: |
            integration-results.json
            integration-test-output.txt
          retention-days: 30

  ###############################################################################
  # Job 3: Tier 3 - Smoke Tests
  ###############################################################################
  smoke-tests:
    name: Tier 3 - Smoke Tests
    runs-on: ubuntu-latest
    needs: [setup, integration-tests]
    if: |
      needs.setup.outputs.environment_ready == 'true' &&
      (github.event.inputs.test_tier == 'all' ||
       github.event.inputs.test_tier == 'smoke-only' ||
       github.event.inputs.test_tier == '')

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Smoke Test - Scheduler Lambda Health
        run: |
          echo "🧪 Testing scheduler Lambda health..."

          aws lambda invoke \
            --function-name dr-daily-report-ticker-scheduler-${{ env.TEST_ENVIRONMENT }} \
            --payload '{"action":"health"}' \
            /tmp/scheduler-health.json

          cat /tmp/scheduler-health.json

          if grep -q "error\|Error" /tmp/scheduler-health.json; then
            echo "❌ Scheduler health check failed"
            exit 1
          fi

          echo "✅ Scheduler health check passed"

      - name: Smoke Test - Precompute Single Ticker
        run: |
          echo "🧪 Testing precompute with single ticker (NVDA)..."

          echo '{"action":"precompute","symbol":"NVDA","include_report":true}' > /tmp/payload.json

          aws lambda invoke \
            --function-name dr-daily-report-ticker-scheduler-${{ env.TEST_ENVIRONMENT }} \
            --payload fileb:///tmp/payload.json \
            /tmp/precompute-smoke.json

          cat /tmp/precompute-smoke.json

          # Check for errors
          if grep -q "error\|Error" /tmp/precompute-smoke.json; then
            echo "❌ Precompute smoke test failed"
            exit 1
          fi

          # Check success count
          SUCCESS=$(cat /tmp/precompute-smoke.json | jq -r '.body.success // 0')
          if [ "$SUCCESS" -eq 0 ]; then
            echo "❌ Precompute reported 0 successes"
            exit 1
          fi

          echo "✅ Precompute smoke test passed"

      - name: Smoke Test - EventBridge Schedule
        run: |
          echo "🧪 Verifying EventBridge scheduler configuration..."

          RULE_NAME="dr-daily-report-daily-ticker-fetch-${{ env.TEST_ENVIRONMENT }}"

          # Check rule exists and is enabled
          RULE_STATE=$(aws events describe-rule --name $RULE_NAME | jq -r '.State')

          if [ "$RULE_STATE" != "ENABLED" ]; then
            echo "❌ EventBridge rule is not enabled (state: $RULE_STATE)"
            exit 1
          fi

          # Verify schedule expression (should be 1 AM Bangkok = 18:00 UTC previous day)
          SCHEDULE=$(aws events describe-rule --name $RULE_NAME | jq -r '.ScheduleExpression')
          EXPECTED="cron(0 1 * * ? *)"

          if [ "$SCHEDULE" != "$EXPECTED" ]; then
            echo "❌ Schedule mismatch: expected '$EXPECTED', got '$SCHEDULE'"
            exit 1
          fi

          echo "✅ EventBridge schedule verified"

  ###############################################################################
  # Job 4: Tier 4 - End-to-End Tests
  ###############################################################################
  e2e-tests:
    name: Tier 4 - End-to-End Tests
    runs-on: ubuntu-latest
    needs: [setup, integration-tests, smoke-tests]
    if: |
      needs.setup.outputs.environment_ready == 'true' &&
      (github.event.inputs.test_tier == 'all' ||
       github.event.inputs.test_tier == 'e2e-only' ||
       github.event.inputs.test_tier == '')

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-json-report boto3 pymysql

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Run E2E Tests
        id: tests
        run: |
          echo "🧪 Running Tier 4 end-to-end tests..."

          pytest tests/ \
            -m "e2e and not legacy" \
            --json-report \
            --json-report-file=e2e-results.json \
            --tb=short \
            -v \
            --maxfail=5 \
            2>&1 | tee e2e-test-output.txt

          TEST_EXIT_CODE=${PIPESTATUS[0]}

          echo "exit_code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-test-results
          path: |
            e2e-results.json
            e2e-test-output.txt
          retention-days: 30

  ###############################################################################
  # Job 5: Report & Notify
  ###############################################################################
  report:
    name: Generate Report & Notify
    runs-on: ubuntu-latest
    needs: [setup, integration-tests, smoke-tests, e2e-tests]
    if: always()

    steps:
      - name: Download all test results
        uses: actions/download-artifact@v4
        with:
          path: test-results/

      - name: Generate summary report
        run: |
          echo "## 🌙 Nightly Build Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Date**: $(date +'%Y-%m-%d %H:%M %Z')" >> $GITHUB_STEP_SUMMARY
          echo "**Environment**: ${{ env.TEST_ENVIRONMENT }}" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY

          # Integration tests
          if [ -f "test-results/integration-test-results/integration-results.json" ]; then
            PASSED=$(cat test-results/integration-test-results/integration-results.json | jq -r '.summary.passed // 0')
            FAILED=$(cat test-results/integration-test-results/integration-results.json | jq -r '.summary.failed // 0')

            if [ "$FAILED" -eq 0 ]; then
              echo "### ✅ Tier 2: Integration Tests" >> $GITHUB_STEP_SUMMARY
            else
              echo "### ❌ Tier 2: Integration Tests" >> $GITHUB_STEP_SUMMARY
            fi
            echo "- Passed: $PASSED" >> $GITHUB_STEP_SUMMARY
            echo "- Failed: $FAILED" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
          fi

          # Smoke tests
          if [ "${{ needs.smoke-tests.result }}" == "success" ]; then
            echo "### ✅ Tier 3: Smoke Tests" >> $GITHUB_STEP_SUMMARY
          else
            echo "### ❌ Tier 3: Smoke Tests" >> $GITHUB_STEP_SUMMARY
          fi
          echo "- Scheduler Lambda: ${{ needs.smoke-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- Precompute: ${{ needs.smoke-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "- EventBridge: ${{ needs.smoke-tests.result }}" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY

          # E2E tests
          if [ -f "test-results/e2e-test-results/e2e-results.json" ]; then
            PASSED=$(cat test-results/e2e-test-results/e2e-results.json | jq -r '.summary.passed // 0')
            FAILED=$(cat test-results/e2e-test-results/e2e-results.json | jq -r '.summary.failed // 0')

            if [ "$FAILED" -eq 0 ]; then
              echo "### ✅ Tier 4: End-to-End Tests" >> $GITHUB_STEP_SUMMARY
            else
              echo "### ❌ Tier 4: End-to-End Tests" >> $GITHUB_STEP_SUMMARY
            fi
            echo "- Passed: $PASSED" >> $GITHUB_STEP_SUMMARY
            echo "- Failed: $FAILED" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
          fi

          echo "---" >> $GITHUB_STEP_SUMMARY
          echo "Next nightly build: Tomorrow 1 AM Bangkok" >> $GITHUB_STEP_SUMMARY

      - name: Notify on failure (Slack webhook - optional)
        if: failure()
        run: |
          # TODO: Add Slack webhook notification
          echo "Would send Slack notification on failure"
          # curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
          #   -H 'Content-Type: application/json' \
          #   -d '{"text":"❌ Nightly build failed for ${{ env.TEST_ENVIRONMENT }}"}'
```

---

## State Management

**State structure** (GitHub Actions outputs):
```yaml
WorkflowState:
  setup:
    environment_ready: boolean
    aws_resources_validated: boolean

  integration_tests:
    passed: integer
    failed: integer
    skipped: integer
    exit_code: integer

  smoke_tests:
    scheduler_health: "success" | "failure"
    precompute_health: "success" | "failure"
    eventbridge_validated: boolean

  e2e_tests:
    passed: integer
    failed: integer
    duration_seconds: integer

  overall_status: "success" | "failure" | "partial"
```

---

## Performance Expectations

**Total duration breakdown**:
- Setup: ~2-3 minutes
- Integration tests: ~15-20 minutes
- Smoke tests: ~5-8 minutes
- E2E tests: ~10-15 minutes
- Report generation: ~1-2 minutes

**Total**: 33-48 minutes per nightly build

**Resource usage**:
- AWS Lambda invocations: ~50-100 (smoke tests)
- Aurora queries: ~500-1000 (integration tests)
- SQS messages: ~10-20 (smoke tests)

**Cost estimate**: ~$0.50-1.00 per nightly build

---

## Error Handling

### Error Categories

**1. Environment setup failures**
- Missing AWS credentials → Fail fast, notify immediately
- Aurora unreachable → Fail fast, investigate infrastructure
- Missing secrets → Fail fast, check Doppler configuration

**2. Integration test failures**
- Schema mismatch → Create GitHub issue, notify team
- Aurora connectivity issues → Check security groups, VPC config
- Lambda import errors → Check Docker image, rebuild

**3. Smoke test failures**
- Lambda timeout → Check Lambda configuration, logs
- Precompute errors → Check CloudWatch logs, schema
- EventBridge misconfiguration → Verify Terraform state

**4. E2E test failures**
- Workflow timeout → Investigate Step Functions logs
- Data inconsistency → Check Aurora schema, cache state
- Rate limiting → Review test design, add throttling

### Retry Strategy

**No automatic retries** - nightly builds run once per day

**On failure**:
- Notify team immediately (Slack/email)
- Archive test results for investigation
- Create GitHub issue for persistent failures
- Team investigates and fixes before next nightly build

---

## Monitoring & Observability

### Success Metrics

**Track over time**:
- Test pass rate (target: >95%)
- Duration trend (detect performance regressions)
- Failure categories (infrastructure vs code)
- Resource usage (cost optimization)

### Alerts

**Immediate notification** (Slack/email) on:
- 3+ test failures in integration tier
- Any smoke test failure (critical)
- E2E test timeout (Step Functions issue)
- Total duration >60 minutes (performance regression)

### CloudWatch Integration

**Custom metrics**:
```
NightlyBuild/TestsPassed
NightlyBuild/TestsFailed
NightlyBuild/DurationMinutes
NightlyBuild/ResourceUsage
```

**Dashboards**:
- Nightly build trends (7-day, 30-day)
- Failure analysis (by category)
- Performance trends (duration over time)

---

## Open Questions

- [ ] Should we run nightly builds on **both dev and staging** or just dev?
  - Recommendation: Start with dev only, add staging after validation

- [ ] Do we need Slack/email notifications or is GitHub Actions summary sufficient?
  - Recommendation: Start with GitHub only, add Slack on repeated failures

- [ ] Should expensive E2E tests (46-ticker precompute) run nightly or weekly?
  - Recommendation: Weekly (Sunday 1 AM) to reduce cost

- [ ] Do we need to archive test results in S3 for long-term analysis?
  - Recommendation: GitHub artifacts (30-day retention) sufficient for now

- [ ] Should we fail fast (stop on first failure) or continue to collect all failures?
  - Recommendation: Continue (use `--maxfail=10`) to get full picture

---

## Next Steps

- [ ] Review workflow specification
- [ ] Decide on dev-only vs dev+staging
- [ ] Choose notification strategy (GitHub vs Slack)
- [ ] Determine weekly vs nightly for expensive tests
- [ ] If approved, implement `.github/workflows/nightly-build.yml`
- [ ] Test with manual trigger (`workflow_dispatch`)
- [ ] Monitor first week of nightly builds
- [ ] Adjust timing/scope based on results

---

## Related Documentation

- `.github/workflows/deploy-scheduler-dev.yml` - Existing scheduler deployment
- `.github/workflows/pr-check.yml` - PR validation workflow
- `.claude/CLAUDE.md` - Testing guidelines and tier definitions
- `tests/infrastructure/` - Infrastructure tests to run
- `tests/integration/` - Integration tests to run

---

*Specification created: 2025-12-24*
*Status: Draft - awaiting review*
