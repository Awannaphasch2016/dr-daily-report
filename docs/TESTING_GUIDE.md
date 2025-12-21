# Testing Guide

**Comprehensive guide to testing patterns and practices for the Daily Report system.**

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Tiers](#test-tiers)
3. [Boundary Contract Testing](#boundary-contract-testing)
4. [Testing Patterns](#testing-patterns)
5. [Real-World Examples](#real-world-examples)

---

## Testing Philosophy

**Core Principle:** Tests should catch bugs before they reach production, especially silent failures at system boundaries.

**Key Insights:**
- Unit tests verify logic in isolation
- Integration tests verify components work together
- **Boundary tests verify data survives type conversions across system boundaries**

**Common Silent Failures:**
- Type mismatches (Python `date` → JSON)
- Encoding issues (NumPy `int64` → JSON `number`)
- Serialization errors (pandas `DataFrame` → JSON)
- Schema mismatches (Python `dict` → MySQL `JSON` column)

---

## Test Tiers

Located in `tests/conftest.py`, test tiers control which tests run:

| Tier | Command | Includes | Use Case |
|------|---------|----------|----------|
| 0 | `pytest --tier=0` | Unit only | Fast local dev |
| 1 | `pytest` (default) | Unit + mocked | Pre-commit / Deploy gate |
| 2 | `pytest --tier=2` | + integration | Nightly / Pre-deploy |
| 3 | `pytest --tier=3` | + smoke | Release validation |
| 4 | `pytest --tier=4` | + e2e | Full release |

**Markers:**
```python
@pytest.mark.integration   # External APIs (LLM, yfinance) - Tier 2
@pytest.mark.smoke         # Requires live server - Tier 3
@pytest.mark.e2e           # Requires browser - Tier 4
@pytest.mark.legacy        # LINE bot tests (skip in Telegram CI)
@pytest.mark.ratelimited   # API rate limited (explicit opt-in)
```

---

## Boundary Contract Testing

**Problem:** Type mismatches at system boundaries cause silent failures that unit tests miss.

**Solution:** Test that data survives serialization/deserialization across every boundary.

### System Boundaries in Our Architecture

```
┌─────────────┐  Python objects   ┌──────────┐  JSON     ┌────────┐
│   Workflow  │ ───────────────→  │  Lambda  │ ────────→ │  API   │
│    Nodes    │                   │ Response │           │ Client │
└─────────────┘                   └──────────┘           └────────┘
       ↓
   Python date,                       ↓
   np.int64,                      Must be JSON
   pd.Timestamp                   serializable
       ↓
┌─────────────┐  pymysql          ┌──────────┐
│   Aurora    │ ←───────────────  │ Python   │
│   MySQL     │                   │  Code    │
└─────────────┘                   └──────────┘
   DATE column                     date object
   JSON column                     dict/list
```

### Pattern 1: The Round-Trip Test

**Principle:** Data must survive a complete round-trip through the boundary.

```python
@pytest.mark.integration
class TestAuroraBoundary:
    """Verify data types cross Aurora boundary correctly."""

    def test_date_column_roundtrip(self):
        """Python date → MySQL DATE → Python date → JSON string."""
        from datetime import date
        import json

        # Step 1: Write Python date to Aurora
        test_date = date(2025, 12, 21)
        service.store_ticker_data(
            symbol='TEST',
            data_date=test_date  # Python date object
        )

        # Step 2: Read from Aurora (gets Python date back)
        result = service.get_ticker_data('TEST')
        assert isinstance(result['data_date'], date)

        # Step 3: CRITICAL - Must serialize to JSON (next boundary)
        try:
            json_str = json.dumps(result)
        except TypeError as e:
            pytest.fail(
                f"Aurora result cannot cross JSON boundary: {e}\n"
                f"Result contains non-JSON types: {result}"
            )

        # Step 4: Verify data integrity after round-trip
        roundtrip = json.loads(json_str)
        assert roundtrip['data_date'] == test_date.isoformat()
```

**Why This Works:**
- Catches issues at EVERY step of the data flow
- Tests actual boundaries (not just unit logic)
- Fails immediately when adding incompatible types

### Pattern 2: The Boundary Matrix

**Principle:** Test EVERY data type used in the system across ALL boundaries.

```python
# tests/boundaries/test_type_contracts.py
import pytest
from datetime import date, datetime
import json
import numpy as np
import pandas as pd

# Define all data types used in the system
BOUNDARY_TEST_CASES = [
    # (test_name, python_value, expected_json_type)
    ("python_date", date.today(), "string"),
    ("python_datetime", datetime.now(), "string"),
    ("numpy_int64", np.int64(42), "number"),
    ("numpy_float64", np.float64(3.14), "number"),
    ("pandas_timestamp", pd.Timestamp.now(), "string"),
    ("python_dict", {"key": "value"}, "object"),
    ("python_list", [1, 2, 3], "array"),
    ("python_none", None, "null"),
    ("python_bool", True, "boolean"),
]

@pytest.mark.parametrize("name,value,expected_json_type", BOUNDARY_TEST_CASES)
class TestLambdaResponseBoundary:
    """Verify all data types can cross Lambda → JSON boundary."""

    def test_json_serializable(self, name, value, expected_json_type):
        """All Lambda response data must be JSON serializable."""
        test_response = {"value": value}

        try:
            json_str = json.dumps(test_response)
        except (TypeError, ValueError) as e:
            pytest.fail(
                f"{name} ({type(value).__name__}) is not JSON serializable: {e}\n"
                f"Add converter in Lambda response handler"
            )

    def test_roundtrip_preserves_semantics(self, name, value, expected_json_type):
        """Data survives JSON round-trip with correct semantics."""
        # Serialize (with converter for non-JSON types)
        def json_converter(obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        serialized = json.dumps({"value": value}, default=json_converter)
        deserialized = json.loads(serialized)

        # Verify JSON type
        actual_type = type(deserialized['value']).__name__
        assert actual_type in [expected_json_type, "str" if expected_json_type == "string" else expected_json_type]

@pytest.mark.integration
class TestAuroraJSONColumnBoundary:
    """Verify data types cross Python → Aurora JSON column boundary."""

    @pytest.mark.parametrize("test_data", [
        {"price": 100.5, "volume": 1000},
        {"prices": [100.1, 100.2, 100.3]},
        {"metadata": {"exchange": "NYSE", "sector": "Tech"}},
        {"empty": {}},
        {"null_value": None},
    ])
    def test_json_column_accepts_python_structures(self, test_data):
        """Aurora JSON column must accept Python dicts/lists directly."""

        # Should NOT require json.dumps() before passing
        service.store_ticker_data(
            symbol='TEST',
            data_date=date.today(),
            company_info=test_data  # Pass dict directly
        )

        # Read back and verify
        result = service.get_ticker_data('TEST')
        assert result['company_info'] == test_data
```

### Pattern 3: Smoke Tests for Deployed Boundaries

**Principle:** Test actual deployed Lambdas to catch environment-specific issues.

```python
@pytest.mark.smoke
class TestDeployedLambdaBoundaries:
    """Test actual deployed Lambda can handle all data types."""

    def test_query_tool_handles_date_columns(self):
        """query_tool Lambda must serialize DATE columns to JSON.

        Real bug caught: query_tool returned 'Object of type date is not JSON serializable'
        """
        import boto3

        lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

        # Insert row with DATE column
        insert_response = lambda_client.invoke(
            FunctionName='dr-daily-report-query-tool-dev',
            Payload=json.dumps({
                'action': 'query',
                'sql': """
                    INSERT INTO ticker_data (symbol, date, price_history, row_count)
                    VALUES ('SMOKE_TEST', CURDATE(), '[]', 0)
                """
            })
        )

        insert_result = json.loads(insert_response['Payload'].read())
        assert insert_result['statusCode'] == 200, \
            f"Insert failed: {insert_result}"

        # SELECT date column (crosses Python → JSON boundary)
        select_response = lambda_client.invoke(
            FunctionName='dr-daily-report-query-tool-dev',
            Payload=json.dumps({
                'action': 'query',
                'sql': "SELECT date FROM ticker_data WHERE symbol = 'SMOKE_TEST'"
            })
        )

        # CRITICAL: Must not have serialization error
        payload = select_response['Payload'].read()

        try:
            result = json.loads(payload)
        except json.JSONDecodeError as e:
            pytest.fail(f"Lambda returned invalid JSON: {e}\nPayload: {payload}")

        # Check for runtime serialization errors
        if 'errorType' in result:
            if 'serializable' in result.get('errorMessage', '').lower():
                pytest.fail(
                    f"Lambda has JSON serialization bug:\n"
                    f"  Error: {result['errorMessage']}\n"
                    f"  Fix: Add date converter in query_tool response handler"
                )

        assert result['statusCode'] == 200, f"Query failed: {result}"
        assert len(result['body']['results']) > 0, "No results returned"

    def test_report_worker_handles_numpy_types(self):
        """report_worker Lambda must handle NumPy types from pandas/yfinance."""
        # Similar pattern for report_worker boundary
        pass
```

### Pattern 4: The Type Observatory

**Principle:** Instrument JSON serialization to detect non-JSON types during tests.

```python
# tests/conftest.py
import pytest
import json
from datetime import date, datetime
import numpy as np
import pandas as pd

@pytest.fixture(scope="session", autouse=True)
def type_observatory():
    """Log all non-JSON-native types encountered during JSON serialization.

    Helps identify boundary issues before they cause production failures.
    """
    original_json_dumps = json.dumps
    non_json_types_seen = set()

    def instrumented_dumps(obj, **kwargs):
        """Instrumented json.dumps that logs type conversions."""

        def check_types(o, path="root"):
            """Recursively check for non-JSON types."""
            if isinstance(o, (date, datetime)):
                non_json_types_seen.add(f"{path}: {type(o).__name__}")
            elif isinstance(o, (np.integer, np.floating)):
                non_json_types_seen.add(f"{path}: {type(o).__name__}")
            elif isinstance(o, pd.Timestamp):
                non_json_types_seen.add(f"{path}: Timestamp")
            elif isinstance(o, dict):
                for k, v in o.items():
                    check_types(v, f"{path}.{k}")
            elif isinstance(o, (list, tuple)):
                for i, v in enumerate(o):
                    check_types(v, f"{path}[{i}]")

        # Walk object tree
        check_types(obj)

        # Call original with any converters
        return original_json_dumps(obj, **kwargs)

    json.dumps = instrumented_dumps

    yield

    # Restore original
    json.dumps = original_json_dumps

    # Report findings
    if non_json_types_seen:
        print("\n⚠️  Type Observatory Report:")
        print("   Non-JSON types detected during tests:")
        for type_path in sorted(non_json_types_seen):
            print(f"     - {type_path}")
        print("   Add converters for these types at boundaries")
```

### Pattern 5: Pre-Deployment Boundary Validation

**Principle:** Run boundary contract tests before every deployment.

```yaml
# .github/workflows/deploy.yml
jobs:
  validate-boundaries:
    name: Validate Boundary Contracts
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Boundary Contract Tests
        run: |
          # Run tier 2 (integration) tests for boundaries
          pytest tests/boundaries/ --tier=2 -v --tb=short

          # Fail deployment if any boundary contract violated
        env:
          # Provide test database credentials
          AURORA_HOST: ${{ secrets.AURORA_HOST }}
          AURORA_USER: ${{ secrets.AURORA_USER }}
          AURORA_PASSWORD: ${{ secrets.AURORA_PASSWORD }}

  deploy:
    needs: validate-boundaries  # Won't run if boundaries fail
    # ... deployment steps
```

### Pattern 6: Canary Queries

**Principle:** After deployment, run queries that exercise all known data types.

```python
# scripts/canary_queries.py
"""
Post-deployment smoke tests that verify all boundaries work.

Run after deploying query_tool Lambda to catch serialization bugs.
"""

import boto3
import json
from typing import List, Tuple, Callable

def run_canary_queries(function_name: str) -> None:
    """Run canary queries that exercise all known data types."""

    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')

    # (query, validator_function, description)
    canary_queries: List[Tuple[str, Callable, str]] = [
        (
            "SELECT CURDATE() as today",
            lambda r: 'today' in r['body']['results'][0],
            "Test DATE column serialization"
        ),
        (
            "SELECT NOW() as current_time",
            lambda r: 'current_time' in r['body']['results'][0],
            "Test TIMESTAMP column serialization"
        ),
        (
            "SELECT price_history FROM ticker_data LIMIT 1",
            lambda r: isinstance(r['body']['results'][0].get('price_history'), list),
            "Test JSON column serialization"
        ),
        (
            "SELECT symbol, row_count FROM ticker_data LIMIT 1",
            lambda r: 'symbol' in r['body']['results'][0],
            "Test basic VARCHAR/INT serialization"
        ),
    ]

    failures = []

    for sql, validator, description in canary_queries:
        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps({'action': 'query', 'sql': sql})
            )

            result = json.loads(response['Payload'].read())

            # Check for serialization errors
            if 'errorType' in result:
                if 'serializable' in result.get('errorMessage', '').lower():
                    failures.append(
                        f"❌ {description}\n"
                        f"   SQL: {sql}\n"
                        f"   Error: {result['errorMessage']}"
                    )
                    continue

            # Validate result structure
            if result['statusCode'] != 200:
                failures.append(
                    f"❌ {description}\n"
                    f"   SQL: {sql}\n"
                    f"   Status: {result['statusCode']}\n"
                    f"   Error: {result.get('body', {}).get('message')}"
                )
                continue

            if not validator(result):
                failures.append(
                    f"❌ {description}\n"
                    f"   SQL: {sql}\n"
                    f"   Validation failed\n"
                    f"   Result: {result}"
                )
                continue

            print(f"✅ {description}")

        except Exception as e:
            failures.append(
                f"❌ {description}\n"
                f"   SQL: {sql}\n"
                f"   Exception: {e}"
            )

    if failures:
        print("\n" + "="*70)
        print("CANARY QUERY FAILURES:")
        print("="*70)
        for failure in failures:
            print(failure)
            print("-"*70)
        raise RuntimeError(f"{len(failures)} canary queries failed")

    print(f"\n✅ All {len(canary_queries)} canary queries passed")

if __name__ == '__main__':
    import sys
    function_name = sys.argv[1] if len(sys.argv) > 1 else 'dr-daily-report-query-tool-dev'
    run_canary_queries(function_name)
```

**Usage in CI/CD:**
```yaml
- name: Run Canary Queries
  run: |
    python scripts/canary_queries.py dr-daily-report-query-tool-dev
```

---

## Testing Patterns

### Pre-Integration Research Tests

**Principle:** Test library behavior BEFORE using it in production code.

```python
def test_pymysql_date_handling():
    """Research: How does pymysql handle DATE columns?

    BEFORE integrating pymysql, validate assumptions:
    - What Python type does it return for DATE columns?
    - Can that type serialize to JSON?
    - Do we need converters?
    """
    import pymysql
    from datetime import date
    import json

    # Connect and fetch a date
    conn = pymysql.connect(...)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT CURDATE() as test_date")
    result = cursor.fetchone()

    # Document actual type
    date_value = result['test_date']
    assert isinstance(date_value, date), \
        f"Expected Python date, got {type(date_value)}"

    # Can it serialize to JSON?
    try:
        json.dumps(result)
        pytest.fail(
            "date object WAS JSON serializable (unexpected!)\n"
            "Update documentation - no converter needed"
        )
    except TypeError:
        # Expected - date objects are not JSON serializable
        # Now we know we need a converter
        pass

    # Document the converter pattern
    converted = {'test_date': date_value.isoformat()}
    json_str = json.dumps(converted)  # This works
    assert '"test_date":' in json_str
```

### Test Sabotage Verification

**Principle:** After writing a test, verify it can detect failures.

```python
def test_store_returns_false_on_failure():
    """Verify store_ticker_data fails when INSERT affects 0 rows."""
    mock_client = MagicMock()
    mock_client.execute.return_value = 0  # Simulate FK constraint failure

    result = service.store_ticker_data('INVALID', date.today(), [], {})

    assert result is False, "Should return False when INSERT affects 0 rows"

# SABOTAGE TEST: Temporarily break the code
# def store_ticker_data(self, ...):
#     self.client.execute(query, params)
#     return True  # BUG: Always returns True (ignores rowcount)
#
# If test still passes with this bug, the test is worthless
```

---

## Real-World Examples

### Example 1: query_tool Date Serialization Bug

**Bug Discovered:** query_tool Lambda couldn't serialize MySQL DATE columns to JSON.

**Symptom:**
```
{
  "errorMessage": "Unable to marshal response: Object of type date is not JSON serializable",
  "errorType": "Runtime.MarshalError"
}
```

**Root Cause:** pymysql returns Python `date` objects, which are not JSON serializable.

**Test That Would Have Caught It:**

```python
@pytest.mark.smoke
def test_query_tool_date_serialization():
    """Verify query_tool can return DATE columns without errors."""
    import boto3

    lambda_client = boto3.client('lambda')

    response = lambda_client.invoke(
        FunctionName='dr-daily-report-query-tool-dev',
        Payload=json.dumps({
            'action': 'query',
            'sql': 'SELECT date FROM ticker_data LIMIT 1'
        })
    )

    payload = response['Payload'].read()
    result = json.loads(payload)  # Would fail here with MarshalError

    assert 'errorType' not in result
    assert result['statusCode'] == 200
```

**Fix:**
```python
# src/scheduler/query_tool_handler.py
def json_converter(obj):
    """Convert non-JSON types for Lambda response."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    raise TypeError(f"Type {type(obj)} not JSON serializable")

# In handler
return {
    'statusCode': 200,
    'body': json.loads(json.dumps(result, default=json_converter))
}
```

### Example 2: NumPy int64 in Lambda Response

**Bug:** NumPy `int64` from pandas calculations can't serialize to JSON.

**Test:**
```python
def test_lambda_response_handles_numpy_types():
    """Verify Lambda responses convert NumPy types."""
    import numpy as np

    # Simulate data from pandas/yfinance
    response_data = {
        'volume': np.int64(1000000),  # From pandas
        'price': np.float64(123.45)
    }

    # Lambda response handler must convert
    json_str = json.dumps(response_data, default=lambda x: x.item() if isinstance(x, (np.integer, np.floating)) else x)

    roundtrip = json.loads(json_str)
    assert isinstance(roundtrip['volume'], int)
    assert isinstance(roundtrip['price'], float)
```

---

## Quick Reference

### When to Use Each Pattern

| Pattern | When | Example |
|---------|------|---------|
| Round-trip test | Adding new data type to existing boundary | Testing Python date → Aurora → JSON |
| Boundary matrix | New boundary or major refactor | New Lambda handler, new database |
| Smoke test | After deployment | POST-deploy validation |
| Type observatory | Development/debugging | Finding hidden type issues |
| Canary queries | CI/CD pipeline | Automated deployment gate |
| Pre-integration | Evaluating new library | Before using new database driver |

### Common Boundary Checklist

When adding a new boundary, verify:
- [ ] Python → JSON (Lambda response)
- [ ] JSON → Python (API request)
- [ ] Python → Database (INSERT/UPDATE)
- [ ] Database → Python (SELECT)
- [ ] Python → S3 (JSON serialization)
- [ ] S3 → Python (JSON deserialization)

### Converter Patterns

```python
# Date/Datetime
obj.isoformat()

# NumPy types
obj.item()

# Pandas Timestamp
obj.isoformat()

# General converter
def json_converter(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not JSON serializable")

json.dumps(data, default=json_converter)
```

---

## See Also

- [CLAUDE.md Testing Guidelines](../.claude/CLAUDE.md#testing-guidelines) - Testing principles
- [Code Style Guide](CODE_STYLE.md) - Testing conventions
- [Type System Integration](TYPE_SYSTEM_INTEGRATION.md) - Type compatibility guide
