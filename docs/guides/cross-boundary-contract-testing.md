# Cross-Boundary Contract Testing Guide

**Principle**: Principle #19 in CLAUDE.md
**Category**: Testing, Integration, Defensive Programming
**Abstraction**: [architecture-2026-01-03-cross-boundary-contract-testing.md](../../.claude/abstractions/architecture-2026-01-03-cross-boundary-contract-testing.md)

---

## Overview

Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary. Tests that verify logic in isolation (unit tests) or deployed systems (integration tests) miss contract violations that appear at **boundary crossings** where assumptions, configurations, or type systems change.

**Core insight**: Boundaries are where contracts break. Each boundary crossing represents a discontinuity where assumptions, configurations, or type systems change—and these transitions need explicit testing.

---

## Boundary Types

### 1. Phase Boundaries (Temporal)

**Definition**: Transitions between different execution phases or lifecycle stages.

**Examples**:
- **Build → Runtime**: Dockerfile expects build args, container expects runtime env vars
- **Development → Production**: Dev uses admin IAM, production uses least-privilege IAM
- **Container Startup → Running**: Lambda cold start validation vs. warm invocation
- **Deployment → First Invocation**: Terraform applies vs. Lambda actually receives env vars
- **Cache Warm → Cache Cold**: Cached responses vs. fresh database queries

**Common contract violations**:
- Missing environment variables (deployed but not configured)
- IAM permissions that work in dev but fail in production
- Initialization code that runs once vs. per-invocation code
- Configuration applied during deployment but not loaded at runtime

**Why integration tests miss this**: Tests against deployed systems don't catch fresh deployment reality. Tests in dev miss production constraints.

---

### 2. Service Boundaries (Spatial)

**Definition**: Transitions between different services, components, or systems.

**Examples**:
- **API Gateway → Lambda**: Event structure transformation, payload encoding
- **Lambda → Aurora**: SQL query construction, connection pooling
- **Lambda → SQS**: Message serialization, batch size limits
- **External API → Internal Model**: Response parsing, schema validation
- **Scheduler → Lambda**: Cron syntax vs. actual invocation time

**Common contract violations**:
- Event structure mismatches (API Gateway integration event vs. unit test mock)
- SQL injection via unparameterized queries
- Message size exceeding SQS limits (256 KB)
- Schema drift between external API and internal expectations
- Timezone confusion (UTC cron but Bangkok business logic)

**Why unit tests miss this**: Unit tests mock service interfaces. Integration tests test deployed services (already working).

---

### 3. Data Boundaries (Semantic)

**Definition**: Transitions where data transforms between different type systems or formats.

**Examples**:
- **Python types → JSON**: float('nan') → JSON (JSON spec rejects NaN)
- **NumPy → MySQL**: ndarray → JSON column (serialization format)
- **User input → Database**: Raw strings → parameterized queries (SQL injection prevention)
- **DateTime objects → String**: Timezone-aware → ISO 8601 string

**Common contract violations**:
- Special values handled differently (NaN, Infinity, null vs None)
- Precision loss during serialization (float → JSON → float)
- Character encoding issues (UTF-8 in Python vs. database charset)
- Type coercion mismatches (string "123" vs. integer 123)

**Why this matters**: Type mismatches cause silent failures. Data looks correct in one system but corrupts crossing boundary.

---

### 4. Time Boundaries (Temporal State)

**Definition**: Transitions where time-sensitive operations cross temporal state changes.

**Examples**:
- **Date boundaries**: 23:59:59 Bangkok → 00:00:00 (cache key changes)
- **Timezone transitions**: UTC → Bangkok (date shifts by +7 hours)
- **Cache TTL expiration**: Cached data → Fresh query (performance degradation)
- **Scheduled events**: Cron trigger → Lambda execution (actual vs. expected time)

**Common contract violations**:
- Cache key includes date, misses after midnight
- Timezone-naive datetime compared with timezone-aware
- TTL expiration causes thundering herd (all caches expire simultaneously)
- Scheduler timezone mismatch (UTC cron but Bangkok business logic)

**Why this matters**: Time-based bugs are non-deterministic and hard to reproduce. Only appear at specific times.

---

## Test Pattern Template

```python
def test_<source>_to_<target>_boundary():
    """<Boundary type>: <Source> → <Target>

    Tests that <contract> is upheld when crossing boundary.
    Simulates: <Real scenario exposing this boundary>
    """
    # 1. Set up boundary conditions (remove mocks, use real constraints)
    # 2. Invoke the transition (call handler, serialize data, etc.)
    # 3. Verify contract upheld (or exception raised if broken)
    # 4. Clean up (restore environment)
```

---

## Comprehensive Examples

### Example 1: Phase Boundary (Docker Container Import Validation)

**Scenario**: Local imports work, but Lambda container fails

**Real incident**: LINE bot 7-day outage (ImportError in Lambda, not local)

```python
def test_handler_imports_in_docker():
    """Phase boundary: Development → Lambda Runtime

    Tests Lambda handler imports in actual Lambda container environment.
    Simulates: Fresh Lambda deployment with new code.
    """
    import_script = "import src.scheduler.query_tool_handler"

    # Run import test inside Lambda Python 3.11 container
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "python3",
         "dr-lambda-test", "-c", import_script],
        capture_output=True
    )

    assert result.returncode == 0, (
        f"Import failed in Lambda container: {result.stderr}\n"
        f"Local import passed but Lambda import failed.\n"
        f"This is a phase boundary violation."
    )
```

**Why this test matters**:
- Local Python environment ≠ Lambda Python environment
- File paths differ (`/var/task` in Lambda vs. project root locally)
- Dependencies might be missing in Lambda layer
- Python version might differ (local 3.11.7 vs. Lambda 3.11.6)

---

### Example 2: Phase Boundary (Lambda Startup Validation)

**Scenario**: Missing environment variables only surface on first cold start

```python
def test_handler_startup_without_environment():
    """Phase boundary: Deployment → First Invocation

    Tests Lambda fails fast when environment variables missing.
    Simulates: Fresh deployment where Terraform forgot env vars.
    """
    original_tz = os.environ.pop('TZ', None)
    try:
        from src.scheduler.handler import lambda_handler
        with pytest.raises(RuntimeError) as exc:
            lambda_handler({}, MagicMock())
        assert 'TZ' in str(exc.value)
    finally:
        if original_tz:
            os.environ['TZ'] = original_tz
```

**Why this test matters**:
- Integration tests against deployed Lambda don't catch this (env vars already set)
- Only appears on fresh deployment (cold start)
- Missing env vars cause runtime errors, not import errors

---

### Example 3: Service Boundary (API Gateway Event Structure)

**Scenario**: Lambda works with test event, fails with real API Gateway event

```python
def test_lambda_with_actual_api_gateway_event():
    """Service boundary: API Gateway → Lambda

    Tests that Lambda correctly parses REAL API Gateway event structure.
    """
    # Load actual API Gateway proxy event (not mocked test event)
    with open('fixtures/api_gateway_proxy_event.json') as f:
        event = json.load(f)

    from src.api_handler import lambda_handler
    result = lambda_handler(event, MagicMock())

    assert result['statusCode'] == 200
    assert 'body' in result  # API Gateway requires body
    assert isinstance(result['body'], str)  # Must be string, not dict
```

**Why this test matters**:
- Unit tests mock event structure (might not match reality)
- API Gateway sends `body` as string, test mocks might send dict
- Real event has `requestContext`, `headers`, `queryStringParameters` (test mock might omit)

---

### Example 4: Data Boundary (Python → MySQL JSON)

**Scenario**: Python dict with NaN serializes to JSON, MySQL rejects

```python
def test_json_with_nan_rejects_in_mysql():
    """Data boundary: Python float('nan') → MySQL JSON

    Tests that MySQL JSON column rejects NaN (per RFC 8259).
    """
    import json
    import math

    # Python allows NaN in dict
    data = {'value': float('nan')}

    # JSON spec rejects NaN
    with pytest.raises(ValueError) as exc:
        json.dumps(data)  # Fails: Out of range float values are not JSON compliant

    # Must sanitize before MySQL insert
    sanitized = {'value': None if math.isnan(data['value']) else data['value']}
    json_str = json.dumps(sanitized)  # Now works

    # Verify MySQL accepts sanitized version
    cursor.execute(
        "INSERT INTO test_table (json_col) VALUES (%s)",
        (json_str,)
    )
    assert cursor.rowcount == 1
```

**Why this test matters**:
- Python's `float('nan')` is valid in Python, invalid in JSON
- MySQL JSON columns enforce JSON spec (RFC 8259)
- Silent failure: Insert succeeds but data corrupted

---

### Example 5: Time Boundary (Date Boundary Cache Key)

**Scenario**: Cache key includes date, misses after midnight

```python
def test_cache_key_consistency_across_date_boundary():
    """Time boundary: 23:59 Bangkok → 00:01 Bangkok

    Tests cache key remains consistent across date boundary.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    bangkok_tz = ZoneInfo("Asia/Bangkok")

    # Simulate request at 23:59 Bangkok (Dec 31)
    time_before_midnight = datetime(2025, 12, 31, 23, 59, 0, tzinfo=bangkok_tz)

    with freeze_time(time_before_midnight):
        cache_key_before = generate_cache_key('AAPL')
        assert 'AAPL:2025-12-31' in cache_key_before

    # Simulate request at 00:01 Bangkok (Jan 1)
    time_after_midnight = datetime(2026, 1, 1, 0, 1, 0, tzinfo=bangkok_tz)

    with freeze_time(time_after_midnight):
        cache_key_after = generate_cache_key('AAPL')
        assert 'AAPL:2026-01-01' in cache_key_after

    # Verify different cache keys (expected behavior)
    assert cache_key_before != cache_key_after

    # Verify cache invalidation logic handles this correctly
    # (date change should trigger cache refresh, not cache miss error)
```

**Why this test matters**:
- Date boundary bugs only appear at midnight
- Cache key includes date (design decision)
- Must verify cache invalidation handles date change gracefully

---

## Boundary Identification Heuristic

**Step-by-step process** for finding boundaries in your system:

1. **Map system components and their interactions**
   - Draw architecture diagram
   - Each arrow = potential service boundary
   - Example: API Gateway → Lambda → Aurora → S3

2. **List lifecycle phases for each component**
   - Deployment, Startup, Running, Shutdown
   - Each transition = potential phase boundary
   - Example: Lambda Deployment → Cold Start → Warm Execution

3. **Trace data transformations through system**
   - User input → JSON → Database
   - Each conversion = potential data boundary
   - Example: Python dict → JSON string → MySQL JSON column

4. **Identify time-sensitive operations**
   - Caching, scheduling, TTL, date-based logic
   - Each state change = potential time boundary
   - Example: Cache key with date, changes at midnight

5. **For each boundary, ask**:
   - What assumptions does each side make?
   - Do tests verify this contract?
   - What happens if contract violated?

---

## Anti-Patterns

### ❌ Testing Only Within Boundaries

**Problem**: Mocked environment, isolated logic

**Example**:
```python
# Bad: Mocking environment variables in test
def test_handler_with_mocked_env(monkeypatch):
    monkeypatch.setenv('TZ', 'Asia/Bangkok')
    # Test passes, but doesn't verify Lambda actually receives TZ
```

**Solution**: Test without mocks (remove env var, verify failure)

---

### ❌ Testing Deployed Systems Only

**Problem**: Doesn't catch fresh deployment gaps

**Example**:
```python
# Bad: Integration test against deployed Lambda
def test_deployed_lambda():
    response = lambda_client.invoke(FunctionName='my-function')
    # Passes because Lambda already has env vars, doesn't test fresh deployment
```

**Solution**: Docker container test (simulates fresh deployment)

---

### ❌ Assuming Mocks Match Reality

**Problem**: Real API Gateway sends body as string, test mock sends dict

**Example**:
```python
# Bad: Mock doesn't match real API Gateway event
event = {'body': {'key': 'value'}}  # Dict (wrong)
# Real API Gateway: {'body': '{"key": "value"}'}  # String (correct)
```

**Solution**: Use actual API Gateway event fixtures

---

### ❌ No Negative Boundary Tests

**Problem**: Only testing success paths, not failure modes

**Example**:
```python
# Bad: Only tests when env var present
def test_handler_success():
    os.environ['TZ'] = 'Asia/Bangkok'
    # Test passes, but doesn't verify failure when TZ missing
```

**Solution**: Test boundary violation (missing env var raises exception)

---

## Integration with Other Principles

**Principle #1 (Defensive Programming)**:
- Validation at boundaries (startup validation, input validation)

**Principle #2 (Progressive Evidence Strengthening)**:
- Verify transitions through evidence layers (status → payload → logs → ground truth)

**Principle #4 (Type System Integration)**:
- Research type compatibility at data boundaries

**Principle #15 (Infrastructure-Application Contract)**:
- Phase boundaries (deployment → first invocation)

**Principle #16 (Timezone Discipline)**:
- Time boundaries (UTC → Bangkok, date boundaries)

---

## When to Apply

✅ **Before deployment** (phase boundaries)
- Test Docker container imports
- Test Lambda cold start without env vars
- Test fresh deployment scenario

✅ **When integrating services** (service boundaries)
- Test with real API Gateway events
- Test actual Aurora schema (not mock)
- Test real SQS message structure

✅ **When handling user input** (data boundaries)
- Test type conversions (Python → JSON → MySQL)
- Test special values (NaN, null, infinity)
- Test character encoding (UTF-8 → database charset)

✅ **When dealing with time-sensitive operations** (time boundaries)
- Test cache key consistency across midnight
- Test timezone transitions (UTC → Bangkok)
- Test TTL expiration handling

---

## Rationale

**Why boundary testing matters**:

Integration tests against deployed systems **pass** because those systems already have correct configuration.

Gap appears when crossing boundaries:
- Deploying to **NEW** environment (fresh Lambda, missing env vars)
- Integrating with **DIFFERENT** service (real API Gateway vs. test mock)
- Handling **UNEXPECTED** data (NaN in Python, invalid in JSON)
- Crossing **TIME**-based state changes (cache key changes at midnight)

**Boundary tests explicitly verify these transitions.**

---

## Real-World Impact

**LINE Bot 7-Day Outage** (Dec 2025):
- **Cause**: ImportError in Lambda container (worked locally)
- **Gap**: No Docker container import validation
- **Fix**: Added `test_handler_imports_in_docker()` to CI/CD
- **Prevented**: query_tool_handler deployment blocker (Jan 2026)

**PDF Generation Schema Bug** (Jan 2026):
- **Cause**: Missing column in Aurora (code expected column)
- **Gap**: No schema validation test before deployment
- **Fix**: Principle #15 (Infrastructure-Application Contract)

---

## See Also

- **Abstraction**: [Cross-Boundary Contract Testing](.claude/abstractions/architecture-2026-01-03-cross-boundary-contract-testing.md) - Complete boundary taxonomy
- **Checklist**: [Execution Boundary Checklist](.claude/checklists/execution-boundaries.md) - Systematic verification workflow
- **Skill**: [testing-workflow](.claude/skills/testing-workflow/) - Test patterns and anti-patterns
- **Checklist**: [lambda-deployment](.claude/checklists/lambda-deployment.md) - Deployment verification workflow

---

*Guide version: 2026-01-04*
*Principle: #19 in CLAUDE.md*
*Status: Graduated from abstraction to principle to implementation guide*
