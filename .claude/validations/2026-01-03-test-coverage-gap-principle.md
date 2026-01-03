---
title: Test Coverage Gap - Cross-Boundary Contract Testing
validation_type: test-coverage-analysis
date: 2026-01-03
updated: 2026-01-03
status: generalized
confidence: High
principle: 19
---

# Validation: Test Coverage Gap for Cross-Boundary Contract Testing

**Note**: This validation originally focused on handler startup validation (phase boundary: Deployment → First Invocation). It has been generalized to **Principle #19: Cross-Boundary Contract Testing**, which applies the same pattern to all boundary types (phase, service, data, time).

See [Cross-Boundary Contract Testing](.claude/abstractions/architecture-2026-01-03-cross-boundary-contract-testing.md) for comprehensive boundary taxonomy and testing patterns.

## Original Problem Statement (Handler Startup Validation)

**Concrete instance**: Tests passed but production Lambda failed silently due to missing TZ environment variable.

**Boundary type**: Phase boundary (Deployment → First Invocation)

**Symptom**:
- Handler has startup validation: `_validate_required_config()` at line 35-60 in precompute_controller_handler.py
- Validation raises RuntimeError BEFORE logging configured (line 58)
- CloudWatch only shows START/END logs, no application logs
- Production completely broken but ALL tests passed

**Why existing principles didn't catch it**:
1. **Principle #1 (Defensive Programming)** - Handler DID validate at startup, but tests never invoked this validation
2. **Principle #10 (Testing Anti-Patterns)** - Tests verified outcomes, but only of DEPLOYED Lambdas (not fresh deployments)
3. **Principle #15 (Infrastructure-Application Contract)** - Validation script exists but doesn't verify handler startup
4. **Principle #16 (Timezone Discipline)** - Documents TZ requirement but doesn't enforce it in tests

---

## Evidence of Gap

### Handler Code (src/scheduler/precompute_controller_handler.py)

```python
def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup."""
    required_vars = {
        'PRECOMPUTE_STATE_MACHINE_ARN': 'Step Functions state machine ARN',
        'TZ': 'Bangkok timezone for date handling'  # ⚠️ REQUIRED
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        error_msg += "\nLambda cannot start precompute workflow without these variables."
        logger.error(error_msg)
        raise RuntimeError(error_msg)  # ⚠️ FAILS AT STARTUP

def lambda_handler(event, context):
    _validate_required_config()  # ⚠️ CALLED FIRST (line 80)
    # ... rest of handler logic
```

### Infrastructure Gap (terraform/precompute_workflow.tf)

```hcl
resource "aws_lambda_function" "precompute_controller" {
  # ... configuration ...

  environment {
    variables = {
      ENVIRONMENT                    = var.environment
      LOG_LEVEL                      = "INFO"
      PRECOMPUTE_STATE_MACHINE_ARN  = aws_sfn_state_machine.precompute_workflow.arn
      # ❌ MISSING: TZ = "Asia/Bangkok"
    }
  }
}
```

**Comparison - Report Worker (CORRECT)**:

```hcl
resource "aws_lambda_function" "report_worker" {
  environment {
    variables = {
      # Timezone (Principle #16: Timezone Discipline)
      TZ = "Asia/Bangkok"  # ✅ PRESENT
      # ... other vars ...
    }
  }
}
```

### Test Coverage Analysis

#### 1. Unit Tests (tests/scheduler/test_parallel_precompute.py)

**What they test**:
- Test SCHEDULER handler (`ticker_fetcher_handler`) - NOT precompute_controller
- Mock all environment variables
- Never invoke handler startup validation

**Example**:
```python
@patch('src.scheduler.handler.boto3')
@patch('src.api.job_service.get_job_service')
def test_parallel_precompute_sends_sqs_messages(mock_get_job_service, mock_boto3):
    # ❌ Mocks hide missing TZ env var
    # ❌ Tests wrong handler (scheduler, not precompute_controller)
    from src.scheduler.handler import lambda_handler
    event = {'action': 'parallel_precompute'}
    result = lambda_handler(event, None)
```

**Why they didn't catch it**: Wrong handler tested, environment fully mocked

---

#### 2. Integration Tests (tests/integration/test_precompute_trigger_integration.py)

**What they test**:
- Test DEPLOYED Lambdas (already have TZ set in test environment)
- Pass because deployed config is correct
- Don't catch Terraform configuration gaps

**Example**:
```python
@pytest.mark.integration
def test_scheduler_triggers_precompute_on_successful_fetch(self):
    # ✅ Tests deployed Lambda (already has TZ in dev environment)
    # ❌ Doesn't test fresh deployment or Terraform config
    response = self.lambda_client.invoke(
        FunctionName=self.scheduler_function,  # Already deployed with TZ
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
```

**Why they didn't catch it**: Test environment already has correct config (deployed previously)

---

#### 3. Infrastructure Tests (tests/infrastructure/test_handler_imports.py)

**What they test**:
- Test that modules can be IMPORTED
- Don't invoke lambda_handler() to trigger startup validation
- Test report_worker's `_validate_required_config()` but NOT precompute_controller's

**Example**:
```python
@pytest.mark.parametrize("handler_module", [
    "src.report_worker_handler",
    "src.scheduler.precompute_controller_handler",  # ✅ Imports successfully
])
def test_handler_module_exists(self, handler_module):
    mod = importlib.import_module(handler_module)  # ❌ Import ≠ Invoke
    assert mod is not None

def test_report_worker_handler_structure(self):
    from src.report_worker_handler import _validate_required_config
    # ✅ Tests report_worker validation exists
    # ❌ Doesn't TEST precompute_controller validation
    assert callable(_validate_required_config)
```

**Why they didn't catch it**: Import succeeds, but never INVOKE handler to trigger validation

---

## Root Cause

**Test environment ≠ Production reality**:
- Tests mock env vars OR test deployed Lambdas with correct config
- Gap appears when deploying NEW environment or updating Terraform
- No test validates Infrastructure-Application Contract for FRESH deployments

**Timeline of failure**:
1. ✅ Unit tests pass (mocked environment)
2. ✅ Integration tests pass (deployed Lambda already has TZ)
3. ✅ Infrastructure tests pass (import succeeds)
4. ✅ CI/CD deploys successfully
5. ❌ **PRODUCTION FAILS** - Lambda container crashes at startup (RuntimeError)
6. ❌ CloudWatch shows only START/END logs (no application logs)
7. ❌ Silent failure - Step Functions waits forever

---

## Concrete Test That Would Have Caught This

### Handler Startup Validation Test (Tier 0 - Fast)

**What it tests**: Handler startup validation WITHOUT mocking environment

```python
# tests/infrastructure/test_handler_startup_validation.py
"""Test that all Lambda handlers validate configuration at startup.

This test layer catches missing environment variables BEFORE deployment.
Complements import tests by actually INVOKING handlers.

Tier 0 test - runs in PR checks (~5 seconds, zero AWS calls)
"""

import pytest
import os
from unittest.mock import MagicMock

class TestHandlerStartupValidation:
    """Validate that handlers fail fast when configuration is missing."""

    def test_precompute_controller_validates_tz_at_startup(self):
        """
        GIVEN missing TZ environment variable
        WHEN precompute_controller handler invoked
        THEN should raise RuntimeError with clear error message
        """
        # Remove TZ env var (simulates fresh deployment)
        original_tz = os.environ.pop('TZ', None)

        # Set required vars (except TZ)
        os.environ['PRECOMPUTE_STATE_MACHINE_ARN'] = 'arn:aws:states:test:123:stateMachine:test'

        try:
            from src.scheduler.precompute_controller_handler import lambda_handler

            # Invoke handler - should fail at startup validation
            event = {}
            context = MagicMock()

            with pytest.raises(RuntimeError) as exc_info:
                lambda_handler(event, context)

            # Verify error message is descriptive
            error_msg = str(exc_info.value)
            assert 'TZ' in error_msg, "Error should mention missing TZ"
            assert 'Bangkok timezone' in error_msg, "Error should explain purpose"

        finally:
            # Restore TZ env var
            if original_tz:
                os.environ['TZ'] = original_tz
            else:
                os.environ.pop('TZ', None)

    @pytest.mark.parametrize("handler_module,handler_name,required_vars", [
        (
            "src.scheduler.precompute_controller_handler",
            "lambda_handler",
            ['PRECOMPUTE_STATE_MACHINE_ARN', 'TZ']
        ),
        (
            "src.report_worker_handler",
            "handler",
            ['OPENROUTER_API_KEY', 'AURORA_HOST', 'PDF_BUCKET_NAME', 'JOBS_TABLE_NAME']
        ),
        (
            "src.scheduler.ticker_fetcher_handler",
            "lambda_handler",
            ['AURORA_HOST', 'AURORA_DATABASE', 'AURORA_USER', 'AURORA_PASSWORD']
        ),
    ])
    def test_handler_validates_all_required_vars(self, handler_module, handler_name, required_vars):
        """
        GIVEN handler with required environment variables
        WHEN any required variable is missing
        THEN handler should fail fast with descriptive error
        """
        # Save original env vars
        original_vars = {var: os.environ.pop(var, None) for var in required_vars}

        try:
            # Import handler
            mod = importlib.import_module(handler_module)
            handler = getattr(mod, handler_name)

            # Test each missing variable
            for missing_var in required_vars:
                # Set all vars except one
                for var in required_vars:
                    if var != missing_var:
                        os.environ[var] = 'test-value'
                    else:
                        os.environ.pop(var, None)  # Ensure missing

                # Invoke handler - should fail
                event = {}
                context = MagicMock()

                with pytest.raises((ValueError, RuntimeError)) as exc_info:
                    handler(event, context)

                # Verify error message mentions the missing variable
                error_msg = str(exc_info.value)
                assert missing_var in error_msg, \
                    f"Error should mention missing {missing_var}"

        finally:
            # Restore all original env vars
            for var, value in original_vars.items():
                if value:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)
```

---

## Integration with Existing Principles

### Principle #1 (Defensive Programming)
**Current**: "Validate configuration at startup, not on first use"

**Gap**: No test enforces this validation happens BEFORE first use

**Integration**: New principle adds TEST requirement for startup validation

---

### Principle #10 (Testing Anti-Patterns)
**Current**: "Test outcomes, not execution"

**Gap**: Doesn't specify testing FAILURE modes (missing config)

**Integration**: New principle emphasizes testing handler startup failures

---

### Principle #15 (Infrastructure-Application Contract)
**Current**: "Update Terraform env vars for ALL affected Lambdas"

**Gap**: No verification that Terraform matches handler requirements

**Integration**: New principle adds automated verification via tests

---

### Principle #16 (Timezone Discipline)
**Current**: "Lambda functions: TZ = 'Asia/Bangkok' (environment variable)"

**Gap**: Documents requirement but doesn't enforce it

**Integration**: New principle enforces via handler startup tests

---

## Comparison: What Caught vs What Should Have Caught

### What Actually Caught It

**Method**: Production monitoring (CloudWatch Logs)

**Timeline**: AFTER deployment (production broken for hours)

**Evidence**: START/END logs only, no application logs

**Cost**: High (production outage, manual investigation, emergency fix)

---

### What Should Have Caught It

**Method**: Handler startup validation test (Tier 0)

**Timeline**: BEFORE deployment (in PR checks)

**Evidence**: Test fails with clear error message

**Cost**: Zero (caught in development, never reaches production)

---

## Lessons Learned

1. **Import ≠ Invoke** - Testing that a module imports successfully doesn't verify it works
2. **Mock ≠ Reality** - Mocking all environment variables hides missing configuration
3. **Deployed ≠ Fresh** - Integration tests against deployed Lambdas don't catch Terraform gaps
4. **Defensive Code ≠ Defensive Tests** - Code validates config, but tests never verify validation happens

---

## Recommended Testing Tiers

### Tier 0: Handler Startup Validation (NEW)
- **Purpose**: Verify handlers fail fast when configuration missing
- **Method**: Invoke handler without mocking environment
- **Runtime**: 5 seconds
- **Catches**: Missing env vars, startup validation gaps

### Tier 1: Unit Tests (EXISTING)
- **Purpose**: Verify business logic
- **Method**: Mock environment, test isolated functions
- **Runtime**: 10 seconds
- **Catches**: Logic bugs, edge cases

### Tier 2: Integration Tests (EXISTING)
- **Purpose**: Verify deployed system behavior
- **Method**: Test against deployed Lambdas
- **Runtime**: 30-60 seconds
- **Catches**: Integration bugs, API contract violations

### Tier 3: Infrastructure Tests (EXISTING)
- **Purpose**: Verify module imports
- **Method**: Import all handler modules
- **Runtime**: 5 seconds
- **Catches**: Import errors, missing dependencies

---

## Generalization to Cross-Boundary Contract Testing

This validation document identified a **phase boundary** testing gap. The pattern has been generalized to cover all boundary types:

### Boundary Types Taxonomy

1. **Phase Boundaries** (this document's focus):
   - Build → Runtime
   - Development → Production
   - Container Startup → Container Running
   - Deployment → First Invocation

2. **Service Boundaries**:
   - API Gateway → Lambda
   - Lambda → Aurora
   - Lambda → SQS
   - External API → Internal Model

3. **Data Boundaries**:
   - Python types → JSON
   - NumPy → MySQL
   - Pandas → DynamoDB
   - User Input → Database

4. **Time Boundaries**:
   - Date boundaries (23:59 → 00:00)
   - Timezone transitions (UTC → Bangkok)
   - Cache TTL expiration
   - Rate limit resets

### General Test Pattern

All boundary tests follow the same structure:

```python
def test_<source>_to_<target>_boundary():
    """<Boundary type>: <Source> → <Target>

    Tests that <contract> is upheld when crossing boundary.
    Simulates: <Real-world scenario exposing this boundary>
    """
    # 1. Set up boundary conditions (remove mocks, use real constraints)
    # 2. Invoke the transition (call handler, serialize data, etc.)
    # 3. Verify contract upheld (or exception raised if broken)
    # 4. Clean up (restore environment)
```

**Handler startup validation** is the canonical example of this pattern applied to phase boundaries.

---

## Related Documentation

### Original Concrete Instance (Phase Boundary)
- Handler code: `src/scheduler/precompute_controller_handler.py:35-60`
- Infrastructure: `terraform/precompute_workflow.tf:147-154`
- Bug hunt report: `.claude/bug-hunts/2026-01-03-pdf-code-not-executing-lambda-container-cache.md`

### Generalized Pattern
- **Principle #19**: [Cross-Boundary Contract Testing](../CLAUDE.md#19-cross-boundary-contract-testing)
- **Architecture document**: [Cross-Boundary Contract Testing](.claude/abstractions/architecture-2026-01-03-cross-boundary-contract-testing.md)
- **Related principles**:
  - Principle #1: Defensive Programming (validation at boundaries)
  - Principle #2: Progressive Evidence Strengthening (verify transitions)
  - Principle #4: Type System Integration Research (data boundaries)
  - Principle #15: Infrastructure-Application Contract (phase boundaries)
  - Principle #16: Timezone Discipline (time boundaries)
