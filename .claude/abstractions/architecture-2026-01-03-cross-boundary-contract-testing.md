---
pattern_type: architecture
confidence: high
created: 2026-01-03
generalized_from: principle-19-handler-startup-validation
tags: [testing, boundaries, contracts, integration, defensive-programming]
---

# Architecture Pattern: Cross-Boundary Contract Testing

## Pattern Summary

**Core Insight**: Tests that verify behavior within a single boundary (unit tests, integration tests of deployed systems) miss contract violations that appear at **boundary crossings**. Each boundary represents a discontinuity where assumptions, configurations, or type systems change—and these transitions need explicit testing.

**Definition**: Cross-boundary contract testing validates that implicit contracts are upheld when crossing from one execution phase, system component, or data domain to another. It tests the **transition itself**, not just the states before and after.

---

## Boundary Taxonomy

### 1. Phase Boundaries (Temporal)

**Definition**: Transitions between different execution phases or lifecycle stages.

**Examples**:
- **Build → Runtime**: Dockerfile expects build args, container expects runtime env vars
- **Development → Production**: Dev uses admin IAM, production uses least-privilege IAM
- **Container Startup → Container Running**: Lambda cold start validation vs. warm invocation
- **Deployment → First Invocation**: Terraform applies vs. Lambda actually receives env vars
- **Cache Warm → Cache Cold**: Cached responses vs. fresh database queries

**Contract violations**:
- Missing environment variables (deployed but not configured)
- IAM permissions that work in dev but fail in production
- Initialization code that runs once vs. per-invocation code
- Configuration applied during deployment but not loaded at runtime

**Testing gap**: Tests against deployed systems miss fresh deployment reality. Tests in dev miss production constraints.

**Example test**:
```python
def test_lambda_startup_without_environment():
    """Phase boundary: Deployment → First Invocation

    Tests what happens when Lambda container starts fresh
    (simulates deployment without environment variables).
    """
    original_tz = os.environ.pop('TZ', None)
    try:
        from src.handler import lambda_handler
        with pytest.raises(RuntimeError) as exc:
            lambda_handler({}, MagicMock())
        assert 'TZ' in str(exc.value)
    finally:
        if original_tz: os.environ['TZ'] = original_tz
```

---

### 2. Service Boundaries (Spatial)

**Definition**: Transitions between different services, components, or systems.

**Examples**:
- **API Gateway → Lambda**: Event structure transformation, payload encoding
- **Lambda → Aurora**: SQL query construction, connection pooling
- **Lambda → SQS**: Message serialization, batch size limits
- **External API → Internal Model**: Response parsing, schema validation
- **Scheduler → Lambda**: Cron syntax vs. actual invocation time

**Contract violations**:
- Event structure mismatches (API Gateway integration event vs. unit test mock)
- SQL injection via unparameterized queries
- Message size exceeding SQS limits (256 KB)
- Schema drift between external API and internal expectations
- Timezone confusion (UTC cron but Bangkok business logic)

**Testing gap**: Unit tests mock service interfaces. Integration tests test deployed services (already working).

**Example test**:
```python
def test_lambda_with_actual_api_gateway_event():
    """Service boundary: API Gateway → Lambda

    Tests that Lambda correctly parses REAL API Gateway event structure
    (not mocked test event).
    """
    # Load actual API Gateway proxy event
    with open('fixtures/api_gateway_proxy_event.json') as f:
        event = json.load(f)

    from src.api_handler import lambda_handler
    result = lambda_handler(event, MagicMock())

    assert result['statusCode'] == 200
    assert 'body' in result  # API Gateway requires body
    assert isinstance(result['body'], str)  # Must be string, not dict
```

---

### 3. Data Boundaries (Type System)

**Definition**: Transitions between different data representations or type systems.

**Examples**:
- **Python → JSON**: `float('nan')` → JSON (NaN not in JSON spec)
- **NumPy → MySQL**: `np.int64` → MySQL INT (type conversion)
- **Pandas → DynamoDB**: `pd.Timestamp` → ISO string (boto3 doesn't auto-convert)
- **User Input → Database**: Unsanitized strings → SQL injection
- **External API → Pydantic**: Unexpected null values → validation errors

**Contract violations**:
- NaN/Infinity values rejected by JSON spec (MySQL ERROR 3140)
- Library-specific types (NumPy, Pandas) not JSON-serializable
- Timezone-aware vs. timezone-naive datetime objects
- Enum case sensitivity (`"active"` vs. `ENUM('ACTIVE')`)
- Null constraint violations (Python `None` → PostgreSQL `NOT NULL`)

**Testing gap**: Tests use clean mock data. Production data has NaN, null, edge cases.

**Example test**:
```python
def test_price_history_with_nan_values():
    """Data boundary: Python float (NaN) → MySQL JSON

    Tests that NaN values are handled BEFORE database write
    (MySQL JSON rejects NaN per RFC 8259).
    """
    from src.data.aurora.client import AuroraClient

    price_data = {
        'prices': [100.0, float('nan'), 105.0],  # NaN in data
        'dates': ['2024-01-01', '2024-01-02', '2024-01-03']
    }

    client = AuroraClient()

    # Should sanitize NaN before writing
    client.write_price_history('AAPL', price_data)

    # Verify NaN was converted to null
    result = client.read_price_history('AAPL')
    assert result['prices'][1] is None  # Not NaN
```

**Related**: See [Type System Integration Guide](../../docs/TYPE_SYSTEM_INTEGRATION.md) for comprehensive type boundary patterns.

---

### 4. Time Boundaries (State Change)

**Definition**: Transitions across time-sensitive state changes or temporal constraints.

**Examples**:
- **Date Boundaries**: 23:59:59 → 00:00:00 (date changes, affects caching)
- **Timezone Transitions**: UTC → Bangkok (affects business date calculation)
- **Rate Limits**: Request N vs. Request N+1 (quota exceeded)
- **TTL Expiration**: Cache hit → Cache miss (TTL expired)
- **Scheduler Drift**: Expected time vs. Actual execution time

**Contract violations**:
- Cache keys using different timezones (scheduler uses Bangkok, API uses UTC)
- Date boundary bugs (21:00 UTC Dec 30 ≠ 04:00 Bangkok Dec 31)
- Race conditions (concurrent requests exceed rate limit)
- Stale data served after TTL (no revalidation logic)
- Scheduler executes later than expected (affects SLA)

**Testing gap**: Tests use fixed timestamps. Production crosses date boundaries.

**Example test**:
```python
def test_cache_key_timezone_consistency():
    """Time boundary: UTC → Bangkok timezone

    Tests that cache keys use CONSISTENT timezone
    (scheduler writes Bangkok date, API reads same date).
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime
    from src.data.cache import build_cache_key

    # Simulate 21:00 UTC Dec 30 (= 04:00 Bangkok Dec 31)
    utc_time = datetime(2025, 12, 30, 21, 0, tzinfo=ZoneInfo("UTC"))
    bangkok_time = utc_time.astimezone(ZoneInfo("Asia/Bangkok"))

    # Cache keys should use Bangkok date (Principle #16)
    scheduler_key = build_cache_key('AAPL', bangkok_time.date())
    api_key = build_cache_key('AAPL', bangkok_time.date())

    assert scheduler_key == api_key, "Timezone mismatch in cache keys"
```

---

## Boundary Identification Heuristic

**How to find untested boundaries in your system:**

### Step 1: Map System Components

Draw a diagram of your system components and their interactions:

```
┌─────────────┐     ┌─────────┐     ┌─────────┐
│ API Gateway │────▶│ Lambda  │────▶│ Aurora  │
└─────────────┘     └─────────┘     └─────────┘
                         │
                         ▼
                    ┌─────────┐
                    │   SQS   │
                    └─────────┘
```

**Each arrow is a service boundary.**

---

### Step 2: Identify Lifecycle Phases

List the execution phases for each component:

**Lambda lifecycle**:
1. Docker build (build args required)
2. Image push (registry authentication)
3. Terraform apply (infrastructure created)
4. Container cold start (env vars loaded, _validate_configuration() runs)
5. First invocation (handler called)
6. Warm invocations (reuses container)
7. Container shutdown (cleanup)

**Each transition is a phase boundary.**

---

### Step 3: Enumerate Data Transformations

Trace a data element through the system:

```
User Input (string)
  → API validation (Pydantic model)
  → Lambda processing (Python dict)
  → Database write (MySQL JSON)
  → Cache storage (Redis string)
  → API response (JSON string)
  → Client display (React component)
```

**Each transformation is a data boundary.**

---

### Step 4: Check for Temporal Dependencies

Identify time-sensitive operations:

- Caching (TTL expiration)
- Rate limiting (quota resets)
- Scheduling (cron execution)
- Date calculations (timezone conversions)
- Session management (token expiration)

**Each time-based state change is a time boundary.**

---

### Step 5: Ask "What Can Go Wrong at This Transition?"

For each boundary, ask:

1. **What assumptions does Side A make?**
   - Lambda assumes `TZ` env var is set
   - Scheduler assumes Aurora uses Bangkok timezone

2. **What assumptions does Side B make?**
   - Aurora expects valid JSON (no NaN)
   - SQS expects messages < 256 KB

3. **What happens if assumptions conflict?**
   - Lambda uses UTC (no TZ), Aurora uses Bangkok → Date mismatch
   - Python produces NaN, MySQL rejects → ERROR 3140

4. **Do we have tests for this conflict scenario?**
   - ❌ No test for missing TZ env var
   - ❌ No test for NaN in price data

**If no test exists, you found an untested boundary.**

---

## Testing Pattern Template

### Structure of Cross-Boundary Test

```python
def test_<source>_to_<target>_<scenario>():
    """<Boundary type>: <Source> → <Target>

    Tests that <specific contract> is upheld when crossing boundary.

    Simulates: <Real-world scenario that exposes this boundary>
    """
    # 1. Set up boundary conditions (remove mocks, use real constraints)

    # 2. Invoke the transition (call handler, serialize data, etc.)

    # 3. Verify contract upheld (or exception raised if contract broken)

    # 4. Clean up (restore environment, close connections)
```

### Example: Phase Boundary Test

```python
def test_handler_startup_without_aurora_credentials():
    """Phase boundary: Deployment → First Invocation

    Tests that Lambda fails fast when Aurora credentials missing.

    Simulates: Fresh deployment where Terraform forgot to set AURORA_HOST.
    """
    # 1. Remove env vars (simulate fresh deployment)
    original = {
        'AURORA_HOST': os.environ.pop('AURORA_HOST', None),
        'AURORA_USER': os.environ.pop('AURORA_USER', None),
    }

    try:
        # 2. Import handler (triggers _validate_configuration)
        from src.scheduler.handler import lambda_handler

        # 3. Verify fails fast with clear error
        with pytest.raises(RuntimeError) as exc:
            lambda_handler({}, MagicMock())

        assert 'AURORA_HOST' in str(exc.value)
        assert 'AURORA_USER' in str(exc.value)

    finally:
        # 4. Restore environment
        for key, value in original.items():
            if value: os.environ[key] = value
```

### Example: Service Boundary Test

```python
def test_sqs_message_size_limit():
    """Service boundary: Lambda → SQS

    Tests that messages are chunked BEFORE sending to SQS.

    Simulates: Large report payload exceeding 256 KB SQS limit.
    """
    from src.messaging.sqs_sender import send_report_message

    # 1. Create large payload (300 KB)
    large_report = {
        'ticker': 'AAPL',
        'analysis': 'x' * 300_000,  # Exceeds SQS 256 KB limit
    }

    # 2. Send message (should chunk automatically)
    send_report_message(large_report)

    # 3. Verify message was chunked
    messages = receive_all_messages_from_queue()
    assert len(messages) > 1, "Large payload should be chunked"
    assert all(len(m) < 256_000 for m in messages), "Each chunk < 256 KB"
```

### Example: Data Boundary Test

```python
def test_numpy_int64_json_serialization():
    """Data boundary: NumPy → JSON

    Tests that NumPy types are converted BEFORE JSON encoding.

    Simulates: External API returns NumPy array, we return JSON response.
    """
    import numpy as np
    from src.api.serializer import to_json_safe

    # 1. Create data with NumPy types
    data = {
        'prices': np.array([100, 105, 110], dtype=np.int64),
        'volume': np.int64(1000000),
    }

    # 2. Convert to JSON-safe types
    safe_data = to_json_safe(data)

    # 3. Verify JSON serialization works
    json_str = json.dumps(safe_data)  # Should not raise
    assert isinstance(safe_data['volume'], int)  # Python int, not np.int64
```

### Example: Time Boundary Test

```python
def test_date_boundary_cache_consistency():
    """Time boundary: Date change (23:59 → 00:00)

    Tests that cache keys remain consistent across date boundary.

    Simulates: Scheduler runs at 23:59 Bangkok, API called at 00:01.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from src.data.cache import build_cache_key

    bangkok_tz = ZoneInfo("Asia/Bangkok")

    # 1. Simulate scheduler at 23:59 Dec 30
    scheduler_time = datetime(2025, 12, 30, 23, 59, tzinfo=bangkok_tz)
    scheduler_key = build_cache_key('AAPL', scheduler_time.date())

    # 2. Simulate API call at 00:01 Dec 31
    api_time = scheduler_time + timedelta(minutes=2)
    api_key = build_cache_key('AAPL', api_time.date())

    # 3. Keys should be DIFFERENT (different business dates)
    assert scheduler_key != api_key, "Date boundary should change cache key"
    assert '2025-12-30' in scheduler_key
    assert '2025-12-31' in api_key
```

---

## Integration with Existing Principles

### Principle #1: Defensive Programming

**Current**: "Validate configuration at startup, not on first use"

**Cross-boundary extension**: Startup validation is **phase boundary testing** (Deployment → First Invocation). Apply same principle to ALL boundaries:

- **Service boundaries**: Validate API event structure before processing
- **Data boundaries**: Validate types before database writes
- **Time boundaries**: Validate timezone consistency before cache operations

**Pattern**: `validate_before_crossing(boundary_type, data)`

---

### Principle #2: Progressive Evidence Strengthening

**Current**: Trust but verify through increasingly strong evidence sources.

**Cross-boundary application**: Each boundary crossing requires **evidence of successful transition**:

- **Phase boundary**: Env vars present (not just deployment succeeded)
- **Service boundary**: Response schema matches (not just 200 OK)
- **Data boundary**: No type errors (not just query executed)
- **Time boundary**: Correct business date (not just timestamp exists)

**Pattern**: Verify contract at each boundary, don't assume transition succeeded.

---

### Principle #4: Type System Integration Research

**Current**: Research type compatibility BEFORE integrating systems.

**Cross-boundary realization**: Type system integration IS data boundary testing. The principle already exists—Cross-Boundary Contract Testing generalizes it to all boundary types.

**Pattern**: Replace "research first" with "test the boundary explicitly"

---

### Principle #10: Testing Anti-Patterns Awareness

**Current**: Test outcomes, not execution. Verify results, not just that functions were called.

**Cross-boundary addition**: Test **transitions**, not just endpoints. Common anti-pattern:

```python
# ❌ Tests endpoint A and endpoint B separately
def test_lambda_works():
    assert lambda_handler({}, None) == {'statusCode': 200}

def test_aurora_works():
    assert aurora_client.query("SELECT 1") == [(1,)]

# ✅ Tests boundary crossing
def test_lambda_to_aurora_boundary():
    """Verifies Lambda can actually connect to Aurora (not mocked)"""
    result = lambda_handler({'action': 'test_db'}, None)
    # Evidence: Lambda received env vars + connected + queried successfully
    assert result['statusCode'] == 200
    assert 'database_version' in result['body']
```

---

### Principle #15: Infrastructure-Application Contract

**Current**: Update Terraform env vars when adding new principles.

**Cross-boundary realization**: This IS phase boundary testing (Application code → Infrastructure config → Deployed Lambda). The pattern template is:

1. **Boundary**: Development (local code) → Deployment (Lambda runtime)
2. **Contract**: Lambda expects env vars that Terraform must provide
3. **Test**: Handler startup validation (Principle #19 before generalization)

**Pattern**: Every Infrastructure-Application change is a boundary crossing that needs testing.

---

### Principle #16: Timezone Discipline

**Current**: Use Bangkok timezone consistently across all components.

**Cross-boundary realization**: This IS time boundary testing. The discipline exists to prevent boundary violations:

- **Scheduler (Bangkok) → Cache key (Bangkok)** - Same timezone
- **Cache key (Bangkok) → API query (Bangkok)** - Same timezone
- **Lambda (Bangkok TZ env var) → Python code (Bangkok ZoneInfo)** - Consistent

**Pattern**: Timezone consistency tests ARE time boundary tests.

---

## When to Apply Cross-Boundary Testing

### High Priority (Required)

Apply when boundaries have:

1. **Different ownership**: API Gateway (AWS) → Lambda (your code)
2. **Different type systems**: Python → MySQL JSON
3. **Different execution phases**: Build time → Runtime
4. **Different failure modes**: Graceful degradation → Fail fast
5. **Historical failures**: Previous bugs at this boundary

**Example**: Lambda startup validation (historical TZ bug, ownership boundary)

---

### Medium Priority (Recommended)

Apply when boundaries have:

1. **Complex transformations**: Multi-step data conversions
2. **External dependencies**: Third-party APIs, libraries
3. **Time sensitivity**: Caching, scheduling, rate limits
4. **Security implications**: Input validation, SQL injection
5. **Performance constraints**: Message size limits, batch processing

**Example**: SQS message chunking (size constraint, external AWS service)

---

### Low Priority (Optional)

Apply when boundaries have:

1. **Simple pass-through**: No transformation or validation
2. **Same type system**: Python → Python
3. **Well-tested libraries**: boto3, requests, pandas
4. **Low change frequency**: Stable APIs, established patterns
5. **Comprehensive mocking**: Existing unit tests cover edge cases

**Example**: Internal function calls within same module

---

## Anti-Patterns

### ❌ Testing Only Within Boundaries

```python
# Tests Lambda logic in isolation (mocked environment)
def test_process_report():
    with patch('os.environ', {'TZ': 'Asia/Bangkok'}):
        result = process_report('AAPL')
        assert result['status'] == 'success'

# Tests Aurora query in isolation (mocked connection)
def test_save_report():
    with patch('src.data.aurora.client.AuroraClient'):
        save_report({'ticker': 'AAPL'})
```

**Problem**: Never tests if Lambda can actually connect to Aurora (boundary untested).

---

### ❌ Testing Deployed Systems Only

```python
@pytest.mark.integration
def test_deployed_lambda_works():
    """Tests deployed Lambda (already has correct env vars)"""
    response = lambda_client.invoke(FunctionName='my-lambda-dev', ...)
    assert response['StatusCode'] == 200
```

**Problem**: Doesn't catch Terraform configuration gaps (deployment already succeeded).

---

### ❌ Assuming Mocks Match Reality

```python
def test_api_gateway_event():
    event = {
        'body': {'ticker': 'AAPL'},  # ❌ Mock assumes dict
        'headers': {'Content-Type': 'application/json'}
    }
    result = lambda_handler(event, None)
```

**Problem**: Real API Gateway sends `body` as **string**, not dict. Test passes, production fails.

---

### ❌ No Negative Boundary Tests

```python
def test_handler_with_valid_config():
    """Only tests success path"""
    os.environ['TZ'] = 'Asia/Bangkok'
    result = lambda_handler({}, None)
    assert result['statusCode'] == 200
```

**Problem**: Never tests what happens when crossing boundary with invalid state (missing TZ).

---

## Boundary Test Checklist

When adding a new integration, component, or feature:

- [ ] **Identify boundaries**: Map phase/service/data/time transitions
- [ ] **Define contracts**: What assumptions does each side make?
- [ ] **Test success crossing**: Verify contract upheld in normal case
- [ ] **Test failure crossing**: Verify graceful failure when contract broken
- [ ] **Test edge cases**: NaN, null, empty, max size, date boundaries
- [ ] **Verify evidence**: Check ground truth, not just status codes
- [ ] **Document boundary**: Note in code where boundary exists and why tested

---

## Real-World Examples from This Project

### Example 1: Lambda Container Startup (Phase Boundary)

**Boundary**: Terraform deployment → Lambda cold start

**Contract**: Lambda expects `TZ`, `AURORA_HOST`, etc. environment variables

**Test**: Handler startup validation (tests/scheduler/test_handler_config_validation.py)

**Historical failure**: PDF generation silently failed for 2+ hours (missing TZ)

**Prevention**: Tier 0 tests invoke handlers without mocking environment

---

### Example 2: Python float(NaN) → MySQL JSON (Data Boundary)

**Boundary**: Python type system → MySQL JSON column

**Contract**: MySQL JSON follows RFC 8259 (no NaN, no Infinity)

**Test**: tests/data/test_price_history_nan_handling.py (would catch this)

**Historical failure**: ERROR 3140 "Invalid JSON text" when writing price data

**Prevention**: Sanitize NaN before database write, verify in tests

---

### Example 3: Scheduler (Bangkok) → API (UTC) Cache Keys (Time Boundary)

**Boundary**: Scheduler timezone → API timezone

**Contract**: Both use Bangkok date for cache keys

**Test**: tests/data/test_cache_key_timezone.py (would catch this)

**Historical failure**: Cache misses despite data present (date mismatch)

**Prevention**: Timezone discipline (Principle #16) + explicit tests

---

### Example 4: API Gateway → Lambda Event Structure (Service Boundary)

**Boundary**: API Gateway integration → Lambda handler

**Contract**: Event has `body` (string), `headers` (dict), `pathParameters` (dict)

**Test**: tests/api/test_api_gateway_integration.py (uses real event fixtures)

**Historical failure**: None (caught early via fixtures)

**Prevention**: Load actual API Gateway proxy event JSON from fixtures/

---

## Related Documentation

- [Type System Integration Guide](../../docs/TYPE_SYSTEM_INTEGRATION.md) - Data boundary patterns
- [Infrastructure-Application Contract](.claude/abstractions/failure_mode-2026-01-02-missing-deployment-flags.md) - Phase boundary failures
- [Timezone Discipline](.claude/validations/2025-12-30-etl-bangkok-timezone-verification.md) - Time boundary validation
- [Defensive Programming](../CLAUDE.md#1-defensive-programming) - Startup validation
- [Progressive Evidence Strengthening](../CLAUDE.md#2-progressive-evidence-strengthening) - Verification across boundaries

---

## Metadata

**Pattern Type**: Architecture (testing strategy)

**Confidence**: High (generalized from multiple concrete instances)

**Created**: 2026-01-03

**Generalized From**: Principle #19 (Handler Startup Validation Testing)

**Related Principles**: #1 (Defensive), #2 (Evidence), #4 (Type Systems), #10 (Testing), #15 (Infra-App), #16 (Timezone)

**Impact**: Prevents silent failures at boundary crossings (hours of debugging saved)
