# Type System Integration Guide

**Purpose**: Guidance for integrating systems with different type systems (APIs, databases, message queues, external services).

**Principle**: Research type compatibility BEFORE writing integration code. Type system mismatches cause silent failures that are expensive to debug.

---

## The Boundary Problem

When integrating two systems, each has its own type system with different rules:

```
System A (Producer)  →  Boundary  →  System B (Consumer)
Type System A              ???         Type System B
```

**Common Mismatches:**

| Source | Target | Problem |
|--------|--------|---------|
| Python `float('nan')` | MySQL JSON column | MySQL rejects NaN per RFC 8259 |
| NumPy `np.int64` | JSON encoder | Not JSON-serializable, raises TypeError |
| Python `datetime` | ISO 8601 string | Multiple format variations, timezone handling |
| Enum value `"active"` | MySQL `ENUM('ACTIVE')` | Case-sensitive, silent failure (0 rows affected) |
| Pandas `pd.Timestamp` | DynamoDB | boto3 doesn't auto-convert |
| Python `None` | PostgreSQL `NOT NULL` | Constraint violation |

---

## Research Questions to Answer

Before writing integration code, answer these questions:

### 1. What types does the target system accept?

- **Read official documentation** - Not blog posts or Stack Overflow first
- **Check specifications** - RFC, ISO standards, API contracts
- **Test edge cases** - NaN, Infinity, null, empty strings, large values, special characters

**Example Research:**
```markdown
Target: MySQL JSON column
Documentation: https://dev.mysql.com/doc/refman/8.0/en/json.html
Specification: RFC 8259 (JSON Specification)
Findings:
- Accepts: null, true, false, numbers, strings, arrays, objects
- Rejects: NaN, Infinity, -Infinity, undefined
- Error: 3140 "Invalid JSON text"
```

### 2. What types does the source system produce?

- **Inspect actual data** - Don't assume documentation is complete
- **Check for library-specific types** - NumPy, Pandas, Arrow, Polars
- **Test with real data** - Not just mocked examples

**Example Inspection:**
```python
# Don't assume - inspect!
response = yfinance_api.get_company_info('AAPL')
for key, value in response.items():
    print(f"{key}: {type(value)} = {value}")

# Findings:
# revenueGrowth: <class 'float'> = nan  # ⚠️ Python native float, not NumPy!
# profitMargins: <class 'float'> = 0.25
# marketCap: <class 'int'> = 2800000000000
```

### 3. How does the target system handle invalid types?

**Three failure modes:**

| Failure Mode | Behavior | Detection |
|--------------|----------|-----------|
| **Exception** | Raises error immediately | Easy to catch, explicit |
| **Silent Failure** | Appears successful, no data persisted | Check rowcount, verify outcome |
| **Coercion** | Converts to different type | May hide bugs, test edge cases |

**Examples:**

```python
# Exception (explicit)
json.dumps({'value': float('nan')}, allow_nan=False)
# ValueError: Out of range float values are not JSON compliant

# Silent Failure (dangerous)
cursor.execute("INSERT INTO users (status) VALUES (%s)", ("active",))
# MySQL ENUM('ACTIVE', 'INACTIVE') - case mismatch, 0 rows affected, NO EXCEPTION

# Coercion (may hide bugs)
dynamodb.put_item(Item={'count': '123'})  # String coerced to Number
dynamodb.put_item(Item={'count': 'abc'})  # Fails, inconsistent
```

### 4. Are there intermediate conversions?

**Check serialization layers:**
- JSON encoding (`json.dumps()`)
- MessagePack, Protocol Buffers
- HTTP encoding (form data, multipart)
- ORM abstractions (SQLAlchemy, Django ORM)
- SDK libraries (boto3, google-cloud, azure-sdk)

**Example:**
```
Python dict → json.dumps() → HTTP → API Gateway → Lambda
     ↓              ↓            ↓         ↓          ↓
  np.int64    Python allows  UTF-8    Enforces   Expects
  np.nan      NaN by default encoding JSON schema primitives
```

---

## Defense in Depth Pattern

Apply multiple validation layers when crossing boundaries:

```python
def send_to_external_system(data: Any) -> bool:
    """
    Send data across system boundary with defense in depth.

    Args:
        data: Raw data from source system

    Returns:
        True if successfully sent and verified
    """
    # Layer 1: Convert source types to neutral types
    converted = convert_library_types(data)
    # NumPy → Python primitives
    # Pandas → dicts/lists
    # datetime → ISO strings

    # Layer 2: Handle special values
    sanitized = handle_special_values(converted)
    # NaN → None
    # Infinity → None or max value
    # Empty strings → None (if not allowed)

    # Layer 3: Validate against target schema
    validated = validate_target_schema(sanitized)
    # Check required fields exist
    # Check types match expectations
    # Raise ValueError if invalid

    # Layer 4: Serialize with strict mode
    payload = serialize_strict(validated)
    # json.dumps(..., allow_nan=False)
    # Fail fast if any issues leak through

    # Layer 5: Send and verify outcome
    result = external_api.send(payload)

    # DON'T just check status code!
    if result.status_code == 200:
        # Verify actual outcome
        if not verify_data_persisted(result):
            raise IntegrationError("Data not persisted despite 200 OK")

    return True
```

### Layer 1: Type Conversion

Convert library-specific types to neutral Python primitives:

```python
def _convert_library_types(obj: Any) -> Any:
    """Convert NumPy/Pandas/Arrow types to Python primitives."""
    # NumPy scalar types
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)

    # Pandas types
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')

    # Python datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Recursive for nested structures
    if isinstance(obj, dict):
        return {k: _convert_library_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_library_types(item) for item in obj]

    return obj
```

### Layer 2: Special Value Handling

Handle values that are valid in source but invalid in target:

```python
def _handle_special_values(obj: Any) -> Any:
    """Handle NaN, Inf, and other special values."""
    # Python native float special values
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return None  # Or raise exception, depending on context
        return obj

    # Empty strings (if target doesn't allow)
    if isinstance(obj, str) and obj.strip() == '':
        return None  # Or keep empty string, depending on target

    # Large numbers (if target has limits)
    if isinstance(obj, int):
        MAX_INT = 2**31 - 1  # Example: PostgreSQL INT limit
        if obj > MAX_INT:
            return MAX_INT  # Or raise exception

    # Recursive traversal
    if isinstance(obj, dict):
        return {k: _handle_special_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_handle_special_values(item) for item in obj]

    return obj
```

### Layer 3: Schema Validation

Explicitly validate against target system's schema:

```python
def _validate_target_schema(data: dict, schema: dict) -> dict:
    """
    Validate data matches target schema.

    Args:
        data: Converted and sanitized data
        schema: Target system's schema definition

    Raises:
        ValueError: If data doesn't match schema
    """
    # Check required fields
    required = schema.get('required', [])
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
        if data[field] is None:
            raise ValueError(f"Required field cannot be null: {field}")

    # Check field types
    for field, expected_type in schema.get('types', {}).items():
        if field in data and data[field] is not None:
            actual_type = type(data[field])
            if not isinstance(data[field], expected_type):
                raise ValueError(
                    f"Field '{field}' type mismatch: "
                    f"expected {expected_type}, got {actual_type}"
                )

    # Check constraints (enums, ranges, patterns)
    for field, constraint in schema.get('constraints', {}).items():
        if field in data and data[field] is not None:
            if 'enum' in constraint:
                if data[field] not in constraint['enum']:
                    raise ValueError(
                        f"Field '{field}' value '{data[field]}' "
                        f"not in allowed values: {constraint['enum']}"
                    )
            if 'range' in constraint:
                min_val, max_val = constraint['range']
                if not (min_val <= data[field] <= max_val):
                    raise ValueError(
                        f"Field '{field}' value {data[field]} "
                        f"outside range [{min_val}, {max_val}]"
                    )

    return data
```

### Layer 4: Strict Serialization

Use strict modes to fail fast:

```python
def _serialize_strict(data: Any, format: str = 'json') -> str:
    """
    Serialize with strict validation.

    Args:
        data: Validated data
        format: 'json', 'msgpack', etc.

    Returns:
        Serialized string/bytes

    Raises:
        ValueError: If serialization fails (invalid data leaked through)
    """
    if format == 'json':
        # allow_nan=False: Fail fast if NaN/Inf exists
        # ensure_ascii=False: Support Unicode
        # separators: Compact output
        return json.dumps(
            data,
            allow_nan=False,
            ensure_ascii=False,
            separators=(',', ':')
        )

    elif format == 'msgpack':
        import msgpack
        return msgpack.packb(data, strict_types=True)

    else:
        raise ValueError(f"Unsupported format: {format}")
```

### Layer 5: Outcome Verification

Don't trust status codes alone:

```python
def _verify_outcome(result: Response) -> bool:
    """
    Verify data was actually persisted/processed.

    Args:
        result: API response

    Returns:
        True if verified successful
    """
    # Layer 1: Check status code
    if result.status_code not in (200, 201):
        return False

    # Layer 2: Check response payload
    try:
        payload = result.json()
    except json.JSONDecodeError:
        return False

    if 'error' in payload or 'errorMessage' in payload:
        logger.error(f"API returned error: {payload}")
        return False

    # Layer 3: Check operation outcome
    # Example: Database insert
    if 'rows_affected' in payload:
        if payload['rows_affected'] == 0:
            logger.warning("Operation returned 0 rows affected")
            return False

    # Example: Queue message
    if 'message_id' in payload:
        if not payload['message_id']:
            logger.warning("No message ID returned")
            return False

    return True
```

---

## Real-World Case Studies

### Case Study 1: Python → MySQL JSON Storage

**Integration**: Python workflow data → MySQL JSON column

**Research Findings:**
- **MySQL JSON**: Enforces RFC 8259 strictly, rejects NaN/Infinity
- **Python json.dumps()**: Allows NaN/Infinity by default (`allow_nan=True`)
- **yfinance API**: Returns Python native `float('nan')`, not NumPy `np.nan`
- **NumPy propagation**: `NaN * 20 = NaN`, infects all calculations

**Type Mismatch:**
```python
# Source produces:
{'score': float('nan')}

# json.dumps() produces (by default):
'{"score": NaN}'  # Not valid JSON per RFC 8259!

# MySQL rejects:
# Error 3140: Invalid JSON text: "Invalid value."
```

**Solution (3 layers)**:
```python
def safe_mysql_json(data: Any) -> str:
    # Layer 1: NumPy → Python
    # Layer 2: Python float NaN → None
    converted = _convert_numpy_to_primitives(data)

    # Layer 3: Strict JSON
    return json.dumps(converted, allow_nan=False)
```

**Cost of Late Discovery**: 3 deployment iterations, 60+ minutes debugging

**References**:
- [RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259)
- [MySQL JSON Docs](https://dev.mysql.com/doc/refman/8.0/en/json.html)
- [Python json.dumps()](https://docs.python.org/3/library/json.html)

---

### Case Study 2: Pandas → DynamoDB

**Integration**: Pandas DataFrame → DynamoDB table

**Research Findings:**
- **DynamoDB**: Accepts String (S), Number (N), Binary (B), Boolean (BOOL), Null (NULL)
- **boto3**: Does NOT auto-convert NumPy/Pandas types
- **Pandas**: Uses `np.int64`, `np.float64`, `pd.Timestamp` internally

**Type Mismatch:**
```python
df = pd.read_csv('data.csv')
# df['count'] is np.int64
# df['timestamp'] is pd.Timestamp

table.put_item(Item=df.iloc[0].to_dict())
# TypeError: Float types are not supported. Use Decimal types instead.
```

**Solution**:
```python
def df_to_dynamodb_items(df: pd.DataFrame) -> List[dict]:
    """Convert DataFrame to DynamoDB-compatible items."""
    items = []
    for _, row in df.iterrows():
        item = {}
        for col, value in row.items():
            # Convert types
            if pd.isna(value):
                item[col] = None  # DynamoDB NULL
            elif isinstance(value, (np.integer, np.int64)):
                item[col] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                if np.isnan(value) or np.isinf(value):
                    item[col] = None
                else:
                    from decimal import Decimal
                    item[col] = Decimal(str(value))  # DynamoDB requires Decimal
            elif isinstance(value, pd.Timestamp):
                item[col] = value.isoformat()
            else:
                item[col] = value
        items.append(item)
    return items
```

**References**:
- [DynamoDB Data Types](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html)
- [boto3 DynamoDB Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html)

---

## Integration Checklist

Use this checklist BEFORE writing integration code:

```markdown
## Integration Checklist: [System A] → [System B]

### Research Phase

#### Target System (Consumer)
- [ ] Read official documentation
- [ ] Identify accepted types (primitives, composite, special)
- [ ] Check specifications (RFC, ISO, API contract)
- [ ] Test edge cases (NaN, null, empty, large values)
- [ ] Understand failure modes (exception / silent / coercion)

#### Source System (Producer)
- [ ] Inspect actual output (don't assume docs are complete)
- [ ] Identify library-specific types (NumPy, Pandas, etc.)
- [ ] Test with real data (not just mocks)
- [ ] Check for special values (NaN, None, empty)

#### Boundary Analysis
- [ ] List type mismatches (source types target rejects)
- [ ] Identify intermediate conversions (serialization, network)
- [ ] Document silent failure modes
- [ ] Estimate cost of late discovery

### Implementation Phase

#### Conversion Function
- [ ] Layer 1: Library types → Python primitives
- [ ] Layer 2: Special value handling (NaN → None)
- [ ] Layer 3: Schema validation (explicit check)
- [ ] Layer 4: Strict serialization (fail fast)
- [ ] Layer 5: Outcome verification

#### Testing
- [ ] Unit test with edge cases (NaN, Inf, null, empty)
- [ ] Integration test with real target system
- [ ] Verify silent failure detection (check rowcount, outcome)
- [ ] Test failure scenarios (invalid types, constraints)

#### Documentation
- [ ] Document type contract in code comments
- [ ] Add reference to specifications (RFC, API docs)
- [ ] Explain WHY conversion is needed (for future maintainers)
- [ ] Include example of failure without conversion
```

---

## When to Research

### ✅ Research BEFORE Integration (Recommended)

| Scenario | Research Time | Benefit |
|----------|--------------|---------|
| New external API | 30-60 min | Avoid deployment failures |
| New database type | 20-40 min | Prevent silent data loss |
| New message format | 15-30 min | Catch serialization issues |
| Library upgrade | 10-20 min | Detect breaking changes |

**Cost**: 30 minutes upfront
**Benefit**: Avoid 2-4 hours of debugging + deployment cycles

### ❌ Research AFTER Problems (Reactive)

| Discovery Point | Cost |
|-----------------|------|
| Local testing | 2 hours debugging |
| CI/CD failure | 4 hours + blocked pipeline |
| Staging issues | 1 day + rollback |
| Production incident | Days + incident response |

**Pattern**: If same error persists after 2 fix attempts, STOP iterating and START researching.

---

## Common Type System Boundaries

| Boundary | Source Types | Target Types | Common Issues |
|----------|-------------|--------------|---------------|
| Python → MySQL | `float('nan')`, `np.int64` | RFC 8259 JSON | NaN rejection, NumPy types |
| Python → PostgreSQL | `datetime`, `dict` | TIMESTAMP, JSONB | Timezone handling, NaN |
| Python → DynamoDB | NumPy types, `float` | String, Number (Decimal) | No auto-convert, Decimal required |
| Python → S3 | Any | Bytes (serialized) | json.dumps() defaults |
| yfinance → NumPy | Python `float('nan')` | `np.float64` | Type mismatch assumptions |
| Pandas → JSON API | `pd.Timestamp`, `np.int64` | ISO 8601, numbers | Serialization failures |
| Python → gRPC | `datetime`, `dict` | protobuf Timestamp, Message | Proto compilation |
| Python → Redis | Any | String (serialized) | pickle vs json vs msgpack |

---

## References

### Specifications
- [RFC 8259 - JSON Specification](https://datatracker.ietf.org/doc/html/rfc8259)
- [ISO 8601 - Date and Time Format](https://www.iso.org/iso-8601-date-and-time-format.html)
- [IEEE 754 - Floating Point Arithmetic](https://standards.ieee.org/standard/754-2019.html)

### Database Documentation
- [MySQL JSON Data Type](https://dev.mysql.com/doc/refman/8.0/en/json.html)
- [PostgreSQL JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)
- [DynamoDB Data Types](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html)

### Python Libraries
- [Python json Module](https://docs.python.org/3/library/json.html)
- [NumPy Data Types](https://numpy.org/doc/stable/user/basics.types.html)
- [Pandas Data Types](https://pandas.pydata.org/docs/user_guide/basics.html#dtypes)

### AWS SDK
- [boto3 DynamoDB Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html)
- [boto3 Type Serialization](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html#valid-dynamodb-types)

### Articles
- [Python's Non-Standard JSON Encoding](https://evanhahn.com/pythons-nonstandard-json-encoding/)
- [MySQL Error 3140 Guide](https://www.getgalaxy.io/learn/common-errors/mysql-error-3140-erinvalidjsontext-invalid-json-text-how-to-fix-and-prevent)
- [Stack Overflow: Sending NaN in JSON](https://stackoverflow.com/questions/6601812/sending-nan-in-json)
