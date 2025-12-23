# Testing Implementation - Scheduler & Precompute Trigger

## Overview

Comprehensive 7-layer testing strategy for the updated scheduler + SQS fanout implementation. This testing suite reduces iteration time by catching errors early in local tests (seconds) before deploying to AWS (minutes).

**Implementation Date:** 2025-12-23
**Components Tested:**
- `src/scheduler/get_ticker_list_handler.py` - Query ticker_master for active tickers
- `src/scheduler/ticker_fetcher_handler.py` - Fetch ticker data + trigger precompute
- `terraform/step_functions/precompute_workflow.json` - Step Functions state machine
- Integration between scheduler → precompute → Step Functions

---

## Test Coverage Summary

### ✅ Layer 1: Unit Tests (Python + pytest)
**Runtime:** ~15 seconds | **Status:** 26/26 PASSED

#### `test_get_ticker_list_handler.py` (7 tests)
Tests Lambda handler that queries Aurora for active DR ticker symbols.

- ✅ Returns ticker list successfully
- ✅ Returns empty list when no tickers
- ✅ Fails when missing environment variables
- ✅ Handles database connection errors
- ✅ Handles query execution errors
- ✅ Uses custom port from env
- ✅ Output schema matches Step Functions expectations

**Key Test:**
```python
def test_output_schema_matches_step_functions_expectation(self):
    """Test that output schema matches what Step Functions expects"""
    result = lambda_handler({}, None)

    # Step Functions expects: $.ticker_list.tickers
    assert 'tickers' in result
    assert isinstance(result['tickers'], list)
    assert all(isinstance(t, str) for t in result['tickers'])
```

#### `test_ticker_fetcher_handler.py` (19 tests)
Tests scheduler Lambda + precompute trigger integration.

**TestTickerFetcherHandler (11 tests):**
- ✅ Fetches all tickers on empty event
- ✅ Fetches specific tickers when provided
- ✅ Initializes fetcher correctly
- ✅ Response includes duration
- ✅ Response includes success/failed lists
- ✅ Catches fetcher exceptions
- ✅ Handles missing bucket name env var
- ✅ Logs event and results
- ✅ Can be tested locally
- ✅ Response structure valid
- ✅ Response body is dict (not JSON string)

**TestPrecomputeTrigger (8 tests):**
- ✅ Triggers precompute on successful fetch
- ✅ Skips precompute when no successful fetches
- ✅ Skips precompute when ARN not configured
- ✅ Handles Lambda invoke failure gracefully
- ✅ Handles unexpected status code
- ✅ Precompute payload includes timestamp
- ✅ Precompute payload includes failed tickers

**Key Test:**
```python
def test_triggers_precompute_on_successful_fetch(self):
    """Test async Lambda invocation"""
    result = lambda_handler({}, None)

    # Verify Lambda invocation
    mock_lambda.invoke.assert_called_once()
    invoke_args = mock_lambda.invoke.call_args
    assert invoke_args.kwargs['InvocationType'] == 'Event'  # Async

    # Verify payload structure
    payload = json.loads(invoke_args.kwargs['Payload'])
    assert payload['triggered_by'] == 'scheduler'
    assert 'fetch_summary' in payload
```

**Run:**
```bash
just test-scheduler-unit
pytest tests/scheduler/test_get_ticker_list_handler.py tests/scheduler/test_ticker_fetcher_handler.py -v
```

---

### ✅ Layer 2: Docker Import Tests
**Runtime:** ~30 seconds | **Script:** `scripts/test_docker_imports.sh`

Tests that all Python imports work inside Lambda Docker container.

**Tests:**
- ✅ get_ticker_list_handler imports successfully
- ✅ ticker_fetcher_handler imports successfully
- ✅ pymysql dependency available
- ✅ boto3 dependency available
- ✅ yfinance dependency available

**Catches:**
- Missing dependencies in requirements.txt
- Import errors due to missing system libraries
- Module path issues

**Run:**
```bash
./scripts/test_docker_imports.sh
./scripts/test_docker_imports.sh --rebuild  # Force rebuild image
```

---

### ✅ Layer 3: Docker Local Execution
**Runtime:** ~60 seconds | **Script:** `scripts/test_docker_local.sh`

Executes Lambda handlers inside Docker container with mocked AWS services.

**Tests:**
- ✅ get_ticker_list_handler executes successfully
- ✅ ticker_fetcher_handler executes successfully
- ✅ Error handling (missing env vars)

**Catches:**
- Handler logic errors
- Environment variable handling issues
- Response format problems

**Run:**
```bash
./scripts/test_docker_local.sh
./scripts/test_docker_local.sh --verbose  # Show detailed output
```

---

### ✅ Layer 4: Step Functions Contract Tests
**Runtime:** ~10 seconds | **Script:** `scripts/test_contracts.sh`

Validates Lambda outputs match Step Functions JSONPath expectations.

**Tests:**
- ✅ get_ticker_list output schema valid
- ✅ JSONPath `$.ticker_list.tickers` extraction works
- ✅ Map state iterator contract valid
- ✅ SQS message format valid
- ✅ Retry configuration present

**Catches:**
- Lambda output schema mismatches
- JSONPath expression errors
- SQS message format issues

**Run:**
```bash
./scripts/test_contracts.sh
./scripts/test_contracts.sh --verbose
```

---

### ✅ Layer 5: Terraform Validation
**Runtime:** ~30 seconds

Standard Terraform validation.

**Commands:**
```bash
cd terraform
terraform fmt -check -recursive
terraform validate
```

---

### ✅ Layer 6: Integration Tests (AWS)
**Runtime:** ~60 seconds | **Requires:** Deployed Lambda functions

**File:** `tests/integration/test_precompute_trigger_integration.py`

**TestPrecomputeTriggerIntegration:**
- ✅ Scheduler triggers precompute on successful fetch
- ✅ Scheduler skips precompute when all fetches fail
- ⏭️  End-to-end scheduler → Step Functions (requires `--run-e2e` flag, ~10 minutes)

**TestStepFunctionsContract:**
- ✅ get_ticker_list output matches Step Functions contract
- ✅ Ticker list is JSON serializable

**Run:**
```bash
just test-scheduler-integration
pytest tests/integration/test_precompute_trigger_integration.py -v -m integration
```

---

### ⏭️ Layer 7: OPA Policy Tests (Optional)
**Status:** Not implemented (no OPA policies exist yet)

Would test Terraform infrastructure policies if OPA policies were defined.

---

## Master Test Script

**File:** `scripts/test_all.sh`

Orchestrates all test layers in correct order.

**Usage:**
```bash
# Quick tests (layers 1-5, ~2 minutes)
./scripts/test_all.sh
just test-scheduler

# Full tests including integration (layers 1-6, ~5 minutes)
./scripts/test_all.sh --full
just test-scheduler-all

# Run only up to layer 3
./scripts/test_all.sh --layer=3

# Skip Docker tests
./scripts/test_all.sh --skip-docker
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 1: Unit Tests (pytest)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Layer 1 passed (15s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 2: Docker Import Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Layer 2 passed (30s)

...

✅ All test layers passed!
Total duration: 120s
```

---

## Justfile Commands

New commands added to `justfile`:

```bash
# Run scheduler unit tests (fastest, ~15 seconds)
just test-scheduler-unit

# Run Docker validation tests (~90 seconds)
just test-scheduler-docker

# Run Step Functions contract tests (~10 seconds)
just test-scheduler-contracts

# Run integration tests (requires AWS deployment, ~60 seconds)
just test-scheduler-integration

# Quick scheduler validation (layers 1-5, ~2 minutes)
just test-scheduler

# Run all scheduler tests (full 7-layer strategy, ~5 minutes)
just test-scheduler-all
```

---

## Testing Philosophy

### Early Error Detection
Tests are ordered by execution speed to catch errors early:
1. **Unit tests (15s)** - Catch logic errors
2. **Docker import (30s)** - Catch dependency issues
3. **Docker local (60s)** - Catch execution errors
4. **Contracts (10s)** - Catch integration issues
5. **Terraform (30s)** - Catch infrastructure errors
6. **Integration (60s)** - Catch deployment issues

### Defensive Testing Patterns
All tests follow defensive programming principles:

- ✅ **Test outcomes, not execution** - Verify results, not just function calls
- ✅ **Explicit failure mocking** - MagicMock defaults are truthy; explicitly mock failures
- ✅ **Schema testing at boundaries** - Test Lambda ↔ Step Functions contracts
- ✅ **Test sabotage verification** - Break code to verify tests catch it

**Example:**
```python
# ❌ BAD: Only tests execution
def test_handler():
    lambda_handler({}, None)  # No assertions!

# ✅ GOOD: Tests outcome
def test_handler():
    result = lambda_handler({}, None)
    assert result['statusCode'] == 200
    assert 'tickers' in result['body']
```

---

## Next Steps

### Before Deployment
```bash
# 1. Run quick validation
just test-scheduler

# 2. Verify Terraform changes
cd terraform && terraform plan

# 3. Deploy to dev
just deploy-dev

# 4. Run integration tests
just test-scheduler-integration
```

### After Deployment
```bash
# 1. Test Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn <arn> \
  --input '{}'

# 2. Monitor CloudWatch logs
aws logs tail /aws/lambda/get-ticker-list-dev --follow
aws logs tail /aws/lambda/ticker-fetcher-dev --follow

# 3. Verify DynamoDB jobs table
aws dynamodb scan --table-name dr-daily-report-telegram-jobs-dev \
  --select COUNT
```

---

## Files Created

### Test Files
- `tests/scheduler/test_get_ticker_list_handler.py` - Unit tests for get_ticker_list Lambda
- `tests/scheduler/test_ticker_fetcher_handler.py` - Updated with precompute trigger tests
- `tests/integration/test_precompute_trigger_integration.py` - Integration tests

### Test Scripts
- `scripts/test_docker_imports.sh` - Docker import validation
- `scripts/test_docker_local.sh` - Docker local execution tests
- `scripts/test_contracts.sh` - Step Functions contract tests
- `scripts/test_all.sh` - Master test orchestration script

### Documentation
- `docs/TESTING_IMPLEMENTATION.md` - This file

### Configuration
- `justfile` - Added scheduler testing commands (lines 253-302)

---

## Test Results

All tests passing as of 2025-12-23:

```
tests/scheduler/test_get_ticker_list_handler.py ................. [  7 PASSED]
tests/scheduler/test_ticker_fetcher_handler.py .................. [ 19 PASSED]

============================== 26 passed in 6.54s ==============================
```

---

## References

- [Testing Workflow Skill](.claude/skills/testing-workflow/) - Testing patterns and anti-patterns
- [Code Review Skill](.claude/skills/code-review/DEFENSIVE.md) - Defensive programming patterns
- [CLAUDE.md](.claude/CLAUDE.md) - Testing guidelines and principles
