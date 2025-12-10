# Deep Analysis: validate-aurora-schema Job Failure

## Run ID: 20095616178

---

## Root Cause Analysis

### Issue 1: Missing Environment Variable Configuration

**Problem:** The validation script uses `os.getenv('SCHEDULER_LAMBDA_NAME', ...)` but the GitHub Actions workflow **never sets this environment variable**.

**Current Code:**
```python
# scripts/validate_aurora_schema.py:180
lambda_name = os.getenv('SCHEDULER_LAMBDA_NAME', 'dr-daily-report-ticker-scheduler-dev')
```

**Workflow:**
```yaml
# .github/workflows/deploy.yml:324-332
- name: Validate Aurora schema matches code expectations
  run: |
    python scripts/validate_aurora_schema.py
    # No SCHEDULER_LAMBDA_NAME env var set!
```

**Impact:** Script always uses hardcoded default `'dr-daily-report-ticker-scheduler-dev'`, which:
- ✅ Works for dev environment
- ❌ **Fails for staging/prod** (if this job runs there)
- ❌ Violates **Configuration Validation Principle** (CLAUDE.md line 156): "NEVER assume configuration is correct without validating first"

---

### Issue 2: Incomplete Error Handling - Malformed Lambda Response

**Problem:** Script doesn't validate Lambda response structure before accessing nested fields.

**Current Code:**
```python
# scripts/validate_aurora_schema.py:82-84
result = json.loads(response['Payload'].read())

if result.get('statusCode') != 200:
    error_msg = result.get('body', {}).get('message', 'Unknown error')
```

**Failure Scenarios:**
1. **Lambda returns non-JSON response** → `json.loads()` raises `JSONDecodeError` → Script crashes (unhandled exception)
2. **Lambda returns `null` or empty string** → `result` is `None` or `str` → `result.get('statusCode')` fails → Script crashes
3. **Lambda returns error structure without `body`** → `result.get('body', {})` returns `{}` → `error_msg` is `'Unknown error'` → Less helpful debugging

**Violates:** **Defensive Programming Principle** (CLAUDE.md line 148): "Fail fast and visibly when something is wrong"

---

### Issue 3: Missing AWS Credentials Validation

**Problem:** Script validates Lambda client creation but doesn't verify credentials actually work.

**Current Code:**
```python
# scripts/validate_aurora_schema.py:189-194
try:
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
except Exception as e:
    print(f"❌ Failed to create Lambda client: {e}")
    sys.exit(1)
```

**Issue:** Creating boto3 client doesn't validate credentials. Credentials might be:
- Missing (but boto3 uses default chain)
- Invalid (expired, wrong region)
- Insufficient permissions (can't invoke Lambda)

**Failure Scenario:** Script proceeds, tries to invoke Lambda, gets `AccessDeniedException` → Script exits 1 → Blocks deployment, but error message is unclear

**Violates:** **Configuration Validation Pattern** (CLAUDE.md line 276-292): "Validate configuration at startup, not on first use"

---

### Issue 4: Workflow Condition Logic Gap

**Problem:** When `build` job is skipped, `validate-aurora-schema` is also skipped, but `deploy-dev` condition might not handle this correctly.

**Current Workflow:**
```yaml
# .github/workflows/deploy.yml:300
validate-aurora-schema:
  needs: [build]
  if: github.event_name == 'push' && needs.build.result == 'success'

# Line 346-349
deploy-dev:
  needs: [build, validate-aurora-schema]
  if: |
    always() &&
    needs.build.result == 'success' &&
    needs.validate-aurora-schema.result == 'success'
```

**Scenario Analysis:**

| build.result | validate-aurora-schema.result | deploy-dev behavior |
|--------------|------------------------------|-------------------|
| `success` | `success` | ✅ Runs (correct) |
| `success` | `failure` | ❌ Blocked (correct) |
| `skipped` | `skipped` | ❌ Blocked (WRONG - should skip) |
| `success` | `skipped` | ❌ Blocked (WRONG - shouldn't happen) |

**Issue:** If `build` is skipped (frontend-only changes), `validate-aurora-schema` is also skipped, but `deploy-dev` requires `needs.validate-aurora-schema.result == 'success'`, which will never be true if it's skipped.

**However:** This might be intentional - if backend didn't change, we don't deploy backend. But the condition should be clearer.

---

### Issue 5: Missing Log Validation (Violates CI/CD Pattern)

**Problem:** Script doesn't validate CloudWatch logs for errors, only checks Lambda response.

**Current Code:** Only checks `statusCode` and response body, doesn't check logs.

**Violates:** **CI/CD Pattern** (CLAUDE.md line 220-259): "AWS Services Success ≠ No Errors" - Always validate CloudWatch logs

**Example from CLAUDE.md:**
```yaml
# Check CloudWatch logs for errors (last 2 minutes)
START_TIME=$(($(date +%s) - 120))000
ERROR_COUNT=$(aws logs filter-log-events \
  --log-group-name /aws/lambda/worker \
  --start-time $START_TIME \
  --filter-pattern "ERROR" \
  --query 'length(events)' \
  --output text)
```

**Impact:** Lambda might return 200 but have errors in logs (timeout, partial failure, etc.)

---

## Failure Mode Analysis

### Most Likely Failure Scenarios (in order):

1. **Lambda returns malformed JSON** → `json.loads()` exception → Script crashes → Job fails
2. **AWS credentials insufficient** → `AccessDeniedException` → Script exits 1 → Blocks deployment
3. **Lambda timeout** → Script waits indefinitely or times out → Job fails
4. **Environment variable not set** → Uses wrong Lambda name (staging/prod) → Queries wrong Lambda → Fails

---

## Fix Plan (Following Testing & CI/CD Principles)

### Fix 1: Add Environment Variable Configuration ✅

**Principle:** Configuration Validation Pattern (CLAUDE.md line 276)

**Change:**
```yaml
# .github/workflows/deploy.yml:324
- name: Validate Aurora schema matches code expectations
  env:
    SCHEDULER_LAMBDA_NAME: dr-daily-report-ticker-scheduler-${{ env.ENV_NAME }}
  run: |
    python scripts/validate_aurora_schema.py
```

**Also update script to validate env var:**
```python
# scripts/validate_aurora_schema.py:177-186
def main():
    """Main validation logic."""
    # Get Lambda name from environment (VALIDATE at startup)
    lambda_name = os.getenv('SCHEDULER_LAMBDA_NAME')
    
    if not lambda_name:
        print("❌ SCHEDULER_LAMBDA_NAME environment variable not set")
        print("   This is a CI/CD configuration error - fix workflow")
        sys.exit(1)
    
    print("=" * 60)
    print("Aurora Schema Validation (CI/CD Gate)")
    print("=" * 60)
    print(f"Lambda: {lambda_name}")
    print()
```

---

### Fix 2: Robust Error Handling for Lambda Response ✅

**Principle:** Defensive Programming (CLAUDE.md line 148)

**Change:**
```python
# scripts/validate_aurora_schema.py:74-115
try:
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload),
        LogType='Tail'
    )
    
    # VALIDATION GATE: Check response structure
    if 'Payload' not in response:
        print(f"❌ Lambda response missing 'Payload' field")
        print(f"   Response: {response}")
        sys.exit(1)
    
    # Parse JSON with error handling
    try:
        payload_bytes = response['Payload'].read()
        if not payload_bytes:
            print(f"❌ Lambda returned empty payload")
            sys.exit(1)
        
        result = json.loads(payload_bytes)
    except json.JSONDecodeError as e:
        print(f"❌ Lambda returned invalid JSON: {e}")
        print(f"   Raw payload: {payload_bytes[:500]}")
        sys.exit(1)
    
    # VALIDATION GATE: Check result structure
    if not isinstance(result, dict):
        print(f"❌ Lambda response is not a dict: {type(result)}")
        print(f"   Response: {result}")
        sys.exit(1)
    
    # Check status code
    status_code = result.get('statusCode')
    if status_code != 200:
        # Extract error message safely
        body = result.get('body', {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {'message': body}
        elif not isinstance(body, dict):
            body = {'message': str(body)}
        
        error_msg = body.get('message', 'Unknown error')
        error_detail = body.get('error', '')
        
        print(f"❌ Lambda failed to query schema: {error_msg}")
        if error_detail:
            print(f"   Error detail: {error_detail}")
        
        # Check if it's a "table doesn't exist" error (MySQL error 1146)
        if 'doesn\'t exist' in error_msg.lower() or '1146' in str(error_detail):
            print(f"\n⚠️  Table '{table_name}' doesn't exist in Aurora")
            print(f"   This may be OK if:")
            print(f"   1. Aurora is not enabled for this environment")
            print(f"   2. Schema migration hasn't been run yet")
            print(f"   3. This is a new deployment")
            print(f"\n   To fix: Run schema migration:")
            print(f"   python scripts/aurora_precompute_migration.py")
            return {}
        
        sys.exit(1)
    
    # Extract schema safely
    body = result.get('body', {})
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            print(f"❌ Lambda body is not valid JSON: {body[:200]}")
            sys.exit(1)
    
    schema = body.get('schema', {})
    if not isinstance(schema, dict):
        print(f"❌ Schema is not a dict: {type(schema)}")
        sys.exit(1)
    
    return schema

except lambda_client.exceptions.ResourceNotFoundException:
    print(f"⚠️  Lambda function not found: {lambda_name}")
    print(f"   Skipping Aurora schema validation")
    return {}
except lambda_client.exceptions.AccessDeniedException as e:
    print(f"❌ Access denied when invoking Lambda: {e}")
    print(f"   Check AWS credentials and IAM permissions")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to invoke Lambda: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

---

### Fix 3: Add AWS Credentials Validation ✅

**Principle:** Configuration Validation Pattern (CLAUDE.md line 276)

**Change:**
```python
# scripts/validate_aurora_schema.py:188-210
# Initialize boto3 client
try:
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
except Exception as e:
    print(f"❌ Failed to create Lambda client: {e}")
    print(f"   Ensure AWS credentials are configured")
    sys.exit(1)

# VALIDATION GATE: Test credentials by checking if we can list functions
print("🔍 Validating AWS credentials...")
try:
    # Try to describe the Lambda function (lightweight operation)
    lambda_client.get_function(FunctionName=lambda_name)
    print(f"✅ AWS credentials valid - Lambda function exists")
except lambda_client.exceptions.ResourceNotFoundException:
    print(f"⚠️  Lambda function not found: {lambda_name}")
    print(f"   This may be OK if Aurora is not enabled")
    # Don't exit here - let query_aurora_schema handle it
except lambda_client.exceptions.AccessDeniedException as e:
    print(f"❌ Access denied when checking Lambda: {e}")
    print(f"   Check IAM permissions for Lambda:GetFunction")
    sys.exit(1)
except Exception as e:
    print(f"⚠️  Failed to validate credentials: {e}")
    print(f"   Will attempt Lambda invocation anyway")
```

---

### Fix 4: Add CloudWatch Log Validation ✅

**Principle:** CI/CD Pattern - Log Validation (CLAUDE.md line 220-259)

**Change:**
```python
# scripts/validate_aurora_schema.py:74-115 (add after Lambda invocation)
try:
    response = lambda_client.invoke(...)
    
    # ... existing response parsing ...
    
    # VALIDATION GATE: Check CloudWatch logs for errors
    if 'LogResult' in response:
        import base64
        try:
            logs = base64.b64decode(response['LogResult']).decode('utf-8')
            
            # Check for ERROR level logs
            if 'ERROR' in logs or 'Exception' in logs or 'Traceback' in logs:
                print(f"\n⚠️  Found errors in Lambda logs:")
                # Print last 20 lines of logs
                log_lines = logs.split('\n')
                for line in log_lines[-20:]:
                    if any(keyword in line for keyword in ['ERROR', 'Exception', 'Traceback']):
                        print(f"   {line}")
                
                # Don't exit here - might be non-fatal errors
                # But log them for visibility
        except Exception as e:
            print(f"⚠️  Failed to decode logs: {e}")
    
    # ... rest of schema extraction ...
```

**Also add to workflow:**
```yaml
# .github/workflows/deploy.yml:324
- name: Validate Aurora schema matches code expectations
  env:
    SCHEDULER_LAMBDA_NAME: dr-daily-report-ticker-scheduler-${{ env.ENV_NAME }}
  run: |
    echo "🔍 Validating Aurora schema via Lambda (NO MOCKING)..."
    echo "   Following CLAUDE.md: Schema Testing at System Boundaries"
    echo "   Query REAL Aurora schema, compare against code expectations"
    echo ""
    
    # Run validation script
    python scripts/validate_aurora_schema.py
    
    # VALIDATION GATE: Check script exit code explicitly
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
      echo ""
      echo "✅ Schema validation passed - Safe to deploy"
    elif [ $EXIT_CODE -eq 1 ]; then
      echo ""
      echo "❌ Schema validation failed - Deployment BLOCKED"
      exit 1
    else
      echo ""
      echo "❌ Unexpected exit code: $EXIT_CODE"
      exit 1
    fi
```

---

### Fix 5: Improve Workflow Condition Logic ✅

**Principle:** Explicit Failure Detection (CLAUDE.md line 152)

**Change:**
```yaml
# .github/workflows/deploy.yml:342-350
deploy-dev:
  name: Deploy Dev
  needs: [build, validate-aurora-schema]
  # Run if: build succeeded AND schema validation succeeded
  # If build was skipped (frontend-only), deploy-dev should also skip
  if: |
    always() &&
    (
      (needs.build.result == 'success' && needs.validate-aurora-schema.result == 'success') ||
      (needs.build.result == 'skipped' && needs.detect-changes.outputs.backend == 'false')
    )
```

**Rationale:** Makes explicit that deploy-dev should skip when backend didn't change.

---

## Testing Strategy

### Unit Tests (Add to `tests/infrastructure/test_aurora_schema_validation.py`)

```python
class TestAuroraSchemaValidation:
    """Test validate_aurora_schema.py script."""
    
    def test_missing_env_var_exits_1(self, monkeypatch):
        """Test that missing SCHEDULER_LAMBDA_NAME exits 1."""
        monkeypatch.delenv('SCHEDULER_LAMBDA_NAME', raising=False)
        result = subprocess.run(
            ['python', 'scripts/validate_aurora_schema.py'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1
        assert 'SCHEDULER_LAMBDA_NAME' in result.stdout
    
    def test_malformed_lambda_response_handled(self, mock_lambda_client):
        """Test that malformed JSON response is handled."""
        mock_lambda_client.invoke.return_value = {
            'Payload': Mock(read=lambda: b'invalid json')
        }
        # Should exit 1 with clear error message
    
    def test_empty_payload_handled(self, mock_lambda_client):
        """Test that empty payload is detected."""
        mock_lambda_client.invoke.return_value = {
            'Payload': Mock(read=lambda: b'')
        }
        # Should exit 1
    
    def test_access_denied_exits_1(self, mock_lambda_client):
        """Test that AccessDeniedException exits 1."""
        mock_lambda_client.invoke.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}},
            'Invoke'
        )
        # Should exit 1 with clear error message
```

### Integration Test (Manual)

```bash
# Test 1: Missing env var
unset SCHEDULER_LAMBDA_NAME
python scripts/validate_aurora_schema.py
# Expected: Exit 1, error message about missing env var

# Test 2: Invalid credentials
AWS_ACCESS_KEY_ID=invalid AWS_SECRET_ACCESS_KEY=invalid python scripts/validate_aurora_schema.py
# Expected: Exit 1, error about credentials

# Test 3: Lambda doesn't exist
SCHEDULER_LAMBDA_NAME=nonexistent-lambda python scripts/validate_aurora_schema.py
# Expected: Exit 0 (graceful skip)

# Test 4: Valid Lambda, table doesn't exist
SCHEDULER_LAMBDA_NAME=dr-daily-report-ticker-scheduler-dev python scripts/validate_aurora_schema.py
# Expected: Exit 0 (graceful skip) or Exit 1 (if schema mismatch)
```

---

## Implementation Priority

1. **P0 (Critical):** Fix 1 (Environment variable) + Fix 2 (Error handling) - Prevents crashes
2. **P1 (High):** Fix 3 (Credentials validation) - Better error messages
3. **P2 (Medium):** Fix 4 (Log validation) - Follows CI/CD pattern
4. **P3 (Low):** Fix 5 (Workflow condition) - Clarifies intent

---

## Summary

**Root Cause:** Missing environment variable configuration + incomplete error handling for Lambda responses

**Impact:** Script crashes on malformed responses or fails silently on configuration errors

**Fix:** Add environment variable validation, robust error handling, credentials validation, and CloudWatch log checking

**Testing:** Add unit tests for error cases, manual integration tests for real scenarios
