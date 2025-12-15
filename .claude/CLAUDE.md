# Daily Report LINE Bot - Development Guide

**Project**: AI-powered Thai language financial ticker analysis bot
**Stack**: Python 3.11+, LangGraph, OpenRouter, AWS Lambda, LINE Messaging API
**Architecture**: Serverless LangGraph agent with multi-stage LLM generation

---

## About This Document

**CLAUDE.md is the ground truth contract for how we work.** All developers (human and AI) must follow these principles.

### What Belongs in CLAUDE.md

Maintain the **"Goldilocks Zone" of abstraction** - not too abstract, not too specific:

| Level | Example | Problem |
|-------|---------|---------|
| Too Abstract | "Use good practices for data" | No guidance - 100 ways to interpret |
| Too Specific | "Use Aurora with this exact SQL query" | Constant updates, implementation lock-in |
| **Just Right** | "Verify data type compatibility at system boundaries - MySQL ENUMs fail silently" | Guides behavior, explains WHY, survives implementation changes |

**A principle belongs here if it:**
- Guides behavior (tells you WHAT to do)
- Explains WHY (so you can adapt to new situations)
- Doesn't require updates when implementation details change
- Would cause bugs/confusion if not followed

**Code examples are appropriate when they:**
- Illustrate the principle (show what "right" looks like)
- Demonstrate anti-patterns (show what NOT to do)
- Reference stable interfaces (AWS CLI, gh commands) unlikely to change
- Help discoverability (flags like `--exit-status` people may not know)

**A principle does NOT belong here if it:**
- Is pure implementation without underlying principle
- References specific file paths that may change
- Is standard engineering practice (no need to document "write tests")
- Is a one-time decision already made (document in ADR or commit message)

---

## Project Context

**Multi-App Architecture:** This project supports two separate UX layers sharing a common backend:
- **LINE Bot**: Chat-based Thai financial reports (production)
- **Telegram Mini App**: Web-based dashboard with REST API (phase 3)

**Shared Infrastructure Principle:** Both apps use identical core agent/workflow/data layers. Resources are separated via AWS tags (`App = line-bot | telegram-api | shared`). See [Architecture Overview](docs/README.md).

**AWS Permissions Philosophy:** The user has full AWS IAM permissions. When encountering permission errors, create the necessary IAM policy and attach it—don't ask for permission. Common pattern:
```bash
aws iam create-policy --policy-name <name> --policy-document file://policy.json
aws iam attach-user-policy --user-name <user> --policy-arn <arn>
```
See [AWS Setup Guide](docs/AWS_SETUP.md) for complete IAM configuration.

**⚠️ Branch Protection:** DO NOT touch `main` branch. Use environment branches: `telegram` (dev), `telegram-staging`, `telegram-prod`. Main contains legacy code. See [Deployment Runbook](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md).

For complete component inventory, technology stack, and directory structure, see [Documentation Index](docs/README.md).

---

## Testing Guidelines

### Test Structure
```
tests/
├── conftest.py         # Shared fixtures ONLY
├── shared/             # Agent, workflow, data tests
├── telegram/           # Telegram API tests
├── line_bot/           # LINE Bot tests (mark: legacy)
├── e2e/                # Playwright browser tests
├── integration/        # External API tests
└── infrastructure/     # S3, DynamoDB tests
```

### Test Tiers

| Tier | Command | Includes | Use Case |
|------|---------|----------|----------|
| 0 | `pytest --tier=0` | Unit only | Fast local |
| 1 | `pytest` (default) | Unit + mocked | Deploy gate |
| 2 | `pytest --tier=2` | + integration | Nightly |
| 3 | `pytest --tier=3` | + smoke | Pre-deploy |
| 4 | `pytest --tier=4` | + e2e | Release |

### Rules (DO / DON'T)

| DO | DON'T |
|----|-------|
| `class TestComponent:` | `def test_foo()` at module level |
| `assert x == expected` | `return True/False` (pytest ignores!) |
| `assert isinstance(r, dict)` | `assert r is not None` (weak) |
| Define mocks in `conftest.py` | Duplicate mocks per file |
| Patch where USED: `@patch('src.api.module.lib')` | Patch where defined: `@patch('lib')` |
| `AsyncMock` for async methods | `Mock` for async (breaks await) |

### Canonical Test Pattern
```python
class TestComponent:
    def setup_method(self):
        self.component = Component()

    def test_success(self, mock_ticker_data):  # Use fixture from conftest
        result = self.component.process({'ticker': 'NVDA19'})
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result['ticker'] == 'NVDA19'

    def test_error(self):
        with pytest.raises(ValueError, match="Invalid"):
            self.component.process({'ticker': ''})

    @pytest.mark.asyncio
    async def test_async(self):
        with patch.object(svc, 'fetch', new_callable=AsyncMock) as m:
            m.return_value = {'data': 1}
            result = await svc.get_data()
        assert result == {'data': 1}
```

### Markers
```python
@pytest.mark.integration   # External APIs (LLM, yfinance)
@pytest.mark.smoke         # Requires live server
@pytest.mark.e2e           # Requires browser
@pytest.mark.legacy        # LINE bot (skip in Telegram CI)
@pytest.mark.ratelimited   # API rate limited (--run-ratelimited to include)
pytestmark = pytest.mark.legacy  # Mark entire file
```

### Quick Reference
```bash
just test-deploy                    # Deploy gate
pytest --tier=2 tests/telegram      # Integration + Telegram only
pytest -m "not legacy and not e2e"  # Skip LINE bot and browser tests
pytest --run-ratelimited            # Include rate-limited tests
```

### Defensive Programming Principles

**Core Principle:** Fail fast and visibly when something is wrong. Silent failures hide bugs.

**Key patterns:**
- **Validate configuration at startup**, not on first use (prevents production surprises)
- **Explicit failure detection**: Check operation outcomes (rowcount, status codes), not just absence of exceptions
- **No silent fallbacks**: Default values should be explicit, not hidden error recovery
- **Test failure modes**: After writing a test, intentionally break the code to verify the test catches it
- **NEVER assume data exists without validating first**: Always verify cache/database state before operations that depend on it. Assumptions about populated data lead to silent failures in production.
- **NEVER assume configuration is correct without validating first**: Always verify environment variables, secrets, and configuration values are set appropriately before operations. Run validation tests as gates to distinguish config failures from logic failures.
- **NEVER assume code produces expected output without verifying the actual result**: Code that executes without exceptions doesn't guarantee correct output. Workflow nodes can succeed but return empty data structures. Always validate the actual output content, not just execution success. Empty dicts `{}` pass `if result:` checks but fail `if result['key']:` checks.

**System boundary rule:** When crossing boundaries (API ↔ Database, Service ↔ External API), verify data type compatibility explicitly. Strict types like MySQL ENUMs fail silently on mismatch.

**Code execution ≠ Correct output:** A function returning without raising an exception doesn't mean it produced the expected data. Always verify output content, not just successful execution.

**AWS Services Success ≠ No Errors:** AWS services returning successful HTTP status codes (200, 202) does not guarantee error-free execution. Always validate CloudWatch logs, response payloads, and operation outcomes before concluding success.

**Log validation pattern:**
```python
# BAD: Assumes 200 = success
response = lambda_client.invoke(FunctionName='worker', Payload='{}')
assert response['StatusCode'] == 200  # ✗ Weak validation

# GOOD: Validates logs + payload
response = lambda_client.invoke(FunctionName='worker', Payload='{}')
assert response['StatusCode'] == 200

# Check CloudWatch logs for errors
logs = cloudwatch_client.filter_log_events(
    logGroupName=f'/aws/lambda/worker',
    startTime=int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000),
    filterPattern='ERROR'
)
assert len(logs['events']) == 0, f"Found {len(logs['events'])} errors in logs"

# Validate response payload
payload = json.loads(response['Payload'].read())
assert 'errorMessage' not in payload, f"Lambda error: {payload.get('errorMessage')}"
assert payload.get('jobs_failed', 0) == 0, f"{payload['jobs_failed']} jobs failed"
```

**Infrastructure test pattern:**
```python
@pytest.mark.integration
def test_worker_lambda_executes_without_errors(self):
    """Verify Lambda not only succeeds but has no errors in logs"""
    # Invoke Lambda
    response = self.lambda_client.invoke(
        FunctionName=self.worker_lambda_name,
        Payload=json.dumps({'ticker': 'NVDA19'})
    )

    # Level 1: Status code (weak)
    assert response['StatusCode'] == 200

    # Level 2: Response payload (stronger)
    payload = json.loads(response['Payload'].read())
    assert 'errorMessage' not in payload

    # Level 3: CloudWatch logs (strongest)
    logs_client = boto3.client('logs')
    log_events = logs_client.filter_log_events(
        logGroupName=f'/aws/lambda/{self.worker_lambda_name}',
        startTime=int((datetime.now() - timedelta(minutes=1)).timestamp() * 1000),
        filterPattern='ERROR'
    )

    assert len(log_events['events']) == 0, \
        f"Found errors in Lambda logs:\n" + \
        "\n".join(event['message'] for event in log_events['events'])
```

**CI/CD pattern:**
```yaml
# .github/workflows/deploy.yml
- name: Deploy Lambda
  run: |
    aws lambda update-function-code --function-name worker --image-uri $IMAGE_URI
    aws lambda wait function-updated --function-name worker

- name: Smoke Test with Log Validation
  run: |
    # Invoke Lambda
    aws lambda invoke --function-name worker --payload '{}' /tmp/response.json

    # Check response
    if grep -q "errorMessage" /tmp/response.json; then
      echo "❌ Lambda returned error"
      cat /tmp/response.json
      exit 1
    fi

    # Check CloudWatch logs for errors (last 2 minutes)
    START_TIME=$(($(date +%s) - 120))000
    ERROR_COUNT=$(aws logs filter-log-events \
      --log-group-name /aws/lambda/worker \
      --start-time $START_TIME \
      --filter-pattern "ERROR" \
      --query 'length(events)' \
      --output text)

    if [ "$ERROR_COUNT" -gt 0 ]; then
      echo "❌ Found $ERROR_COUNT errors in CloudWatch logs"
      aws logs filter-log-events \
        --log-group-name /aws/lambda/worker \
        --start-time $START_TIME \
        --filter-pattern "ERROR"
      exit 1
    fi

    echo "✅ Lambda executed without errors (validated: status code + payload + logs)"
```

**Data existence validation pattern:**
```python
# BAD: Assumes cache is populated
def trigger_ui_refresh():
    # Assumes 46 tickers in cache - may fail silently
    invalidate_cloudfront()

# GOOD: Validates data exists first
def trigger_ui_refresh():
    cache_count = check_cache_population()
    if cache_count == 0:
        raise ValueError("Cache is empty - populate before refreshing UI")
    invalidate_cloudfront()
```

**Configuration validation pattern:**
```python
# BAD: Assumes env vars are set
def populate_cache():
    # Assumes AURORA_HOST, API keys exist - may fail deep in execution
    lambda_client.invoke(FunctionName=SCHEDULER_LAMBDA, Payload={...})

# GOOD: Validates config before operations
def populate_cache():
    # Run validation gate first
    validation_result = subprocess.run(['scripts/validate_deployment_ready.sh'])
    if validation_result.returncode != 0:
        raise ValueError("Configuration validation failed - fix env vars before populating cache")

    # Now safe to proceed - failures are logic/data issues, not config
    lambda_client.invoke(FunctionName=SCHEDULER_LAMBDA, Payload={...})
```

**Output verification pattern:**
```python
# BAD: Assumes workflow produces expected data
def store_user_scores(agent_result):
    # Code exists to populate user_facing_scores, so we assume it worked
    precompute_service.store_report(
        report_json=agent_result  # Might be empty dict!
    )

# GOOD: Validates actual output content before using it
def store_user_scores(agent_result):
    # Verify output content, not just execution
    if 'user_facing_scores' not in agent_result:
        logger.error("Agent workflow did not produce user_facing_scores")
        raise ValueError("Missing required field: user_facing_scores")

    if not agent_result['user_facing_scores']:
        logger.error(f"user_facing_scores is empty: {agent_result['user_facing_scores']}")
        raise ValueError("user_facing_scores must not be empty")

    # Now safe - we know the data exists and is non-empty
    precompute_service.store_report(report_json=agent_result)
```

**The Truthy Trap:**
```python
# BAD: Empty dict is truthy but has no content
result = {'indicators': {}, 'ticker_data': {}, 'percentiles': {}}
if result['indicators']:  # ✓ Passes (dict exists)
    process(result)       # ✗ Fails (dict is empty)

# GOOD: Check for actual content
if result.get('indicators') and len(result['indicators']) > 0:
    process(result)
else:
    logger.warning(f"Indicators dict is empty: {result.get('indicators')}")
    # Handle empty data appropriately
```

**Silent None Propagation Anti-Pattern:**
```python
# BAD: Returns None hides failures
def fetch_ticker_data(ticker: str):
    hist = yf.download(ticker, period='1y')
    if hist is None or hist.empty:
        logger.warning(f"No data for {ticker}")
        return None  # ✗ Caller doesn't know WHY it failed

def process_ticker(ticker: str):
    data = fetch_ticker_data(ticker)
    if not data:  # Silent failure - logged as warning, workflow continues
        return {'ticker': ticker, 'indicators': {}}  # Empty dict propagates
    # ... rest of processing

# GOOD: Raise explicit exceptions
def fetch_ticker_data(ticker: str):
    hist = yf.download(ticker, period='1y')
    if hist is None or hist.empty:
        error_msg = f"No historical data returned for {ticker}"
        logger.error(error_msg)
        raise ValueError(error_msg)  # ✓ Caller MUST handle this

def process_ticker(ticker: str):
    try:
        data = fetch_ticker_data(ticker)
        # ... processing
    except ValueError as e:
        logger.error(f"Failed to process {ticker}: {e}")
        # Explicit error handling - set state['error'] or re-raise
        raise  # Fail fast with visibility
```

**Workflow Validation Gates:**
```python
# BAD: Assumes upstream nodes succeeded
def analyze_technical(state: AgentState) -> AgentState:
    # No validation - assumes ticker_data is populated
    result = analyzer.calculate_indicators(state['ticker_data'])
    state['indicators'] = result  # Might be {} if ticker_data was empty!
    return state

# GOOD: Validate prerequisites before execution
def analyze_technical(state: AgentState) -> AgentState:
    # VALIDATION GATE - check prerequisite data
    if not state.get('ticker_data') or len(state['ticker_data']) == 0:
        error_msg = f"Cannot analyze technical: ticker_data is empty for {state['ticker']}"
        logger.error(error_msg)
        state['error'] = error_msg
        return state  # Skip execution, preserve error state

    # Safe to proceed - prerequisite validated
    try:
        result = analyzer.calculate_indicators(state['ticker_data'])
        state['indicators'] = result
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        state['error'] = str(e)

    return state
```

### Principles of Error Investigation

**Core Principle:** Execution completion ≠ Operational success. Verify actual outcomes across multiple layers, not just the absence of exceptions.

#### Principle 1: Multi-Layer Verification

Errors surface at different layers. Check all layers to distinguish between "service executed" and "service succeeded":

**Verification Layers:**
1. **Exit Code/Status**: Did the process complete? (weakest signal)
2. **Logs**: What errors were logged? At what level? (ERROR vs WARNING vs INFO)
3. **Data State**: What actually changed in databases/files/external systems? (strongest signal)

**Pattern:** Always verify the layer that matters for your operation. For data storage, check the database; for API calls, check response payload; for background jobs, check both logs and side effects.

**Why this matters:** Services can complete successfully (exit code 0, status "completed") while critical operations fail internally (logged at ERROR level but caught by try-catch).

#### Principle 2: Log Level Determines Discoverability

Log levels are not just severity indicators—they determine whether failures are discoverable by monitoring systems:

- **ERROR/CRITICAL**: Monitored, triggers alerts, visible in dashboards
- **WARNING**: Logged but not alerted, requires manual log review
- **INFO/DEBUG**: Invisible to standard monitoring, requires active search

**Investigation Pattern:**
- Filter logs by ERROR level first to find actual failures
- If no ERROR logs but operation failed → possible silent failure (logged at wrong level or not logged)
- Check both application logs and service logs (e.g., Lambda + CloudWatch, database query logs + application logs)

**Why this matters:** An error logged at WARNING level is invisible to monitoring, making it a "discoverable but not discovered" failure.

#### Principle 3: Status Must Reflect Critical Operation Outcomes

When operations have multiple steps, overall status must reflect ALL critical steps, not just final step:

**Decision framework:**
- Is this operation critical to correctness? → Failure must propagate to overall status
- Is this operation optional/best-effort? → Log warning, continue, status remains success

**Example:** If job writes to primary storage (critical) and cache (optional):
- Primary fails → Job status: "failed"
- Cache fails, primary succeeds → Job status: "completed" + WARNING log

**Why this matters:** Misleading status creates false confidence. Users see "completed" and assume all operations succeeded.

#### Principle 4: Iterative Fix-and-Verify Cycle

Multi-component systems often have layered failures. Fixing one issue reveals the next:

**Pattern:**
1. Fix identified issue
2. Re-run operation
3. Check logs for NEW errors (may uncover next layer)
4. Verify actual outcome (data state, not just status)
5. Repeat until clean execution AND verified outcome

**Why this matters:** Schema mismatches, missing columns, FK constraints often surface sequentially—each fix reveals the next missing piece.

**Example from investigation:** Fixed FK constraint type mismatch → revealed missing columns → revealed wrong log level → revealed schema still incomplete.

### Remote Service Investigation Principles

**Core Principle:** When debugging remote AWS services, identify the PRECISE error layer before attempting fixes. Guessing wastes time and creates false hypotheses.

**Error Layer Framework:**

When a remote service fails, systematically identify which layer has the issue:

| Layer | How to Detect | Example Errors |
|-------|---------------|----------------|
| **Client/Code** | API returns structured error | Invalid parameter, malformed request |
| **Permission** | HTTP 403, AccessDeniedException | IAM policy missing, trust policy incorrect |
| **Network (client)** | Timeout, connection refused | WSL2 NAT, firewall, DNS |
| **Network (AWS)** | Timeout after security group check | Security group blocks, no Internet Gateway |
| **Instance/Service** | HTTP 400, TargetNotConnected | Agent not running, credential cache stale |

**Key Patterns:**

1. **HTTP Response ≠ Network Issue:** If you get an HTTP response (even an error), network to that endpoint is working. The issue MAY NOT be connectivity, but could be a different network layer or path.

2. **AWS Service Registration ≠ Working:** API accepts request (200 OK) doesn't mean service is functioning. Must verify agent running, registered with AWS, credentials valid, no errors in logs.

3. **Credential Cache Temporal Coupling:** Services cache credential state at startup. Attaching IAM role to running instance → agent has cached "no credentials". Solution: Restart service to force credential refresh from IMDS.

4. **Environment-Specific Access Path:** Establish ONE reliable access path for your environment and master it. Don't switch methods when debugging—each has different failure modes and you lose diagnostic context.
   - **WSL2 + AWS:** SSM Session Manager (works via HTTPS, bypasses WSL2 NAT)
   - **Corporate Network:** VPN + bastion pattern
   - **Local Development:** Direct SSH with proper key management

   When your chosen path fails, debug THAT path systematically through all layers.

5. **SSM Document Permissions Are Granular:** Having `ssm:StartSession` permission doesn't mean you can use ALL SSM documents. Each document type (interactive shell, port forwarding, SSH tunneling) requires explicit permission. Common failure: Can start interactive sessions but port forwarding fails with AccessDeniedException.
   - `SSM-SessionManagerRunShell` → Interactive shell access
   - `AWS-StartPortForwardingSessionToRemoteHost` → Port forwarding to remote hosts
   - `AWS-StartSSHSession` → SSH protocol tunneling
   - Solution: Update IAM policy to include all document ARNs you need

**Example - SSM Session Manager debugging checklist:**
```bash
# Layer 1: Client/Code - Verify AWS CLI working
aws sts get-caller-identity

# Layer 2: Permission - Verify IAM policies
aws iam list-attached-user-policies --user-name <username>
aws ec2 describe-iam-instance-profile-associations --filters "Name=instance-id,Values=<instance-id>"

# Layer 3: Network (client) - Verify HTTPS connectivity
curl -I https://ssm.ap-southeast-1.amazonaws.com

# Layer 4: Network (AWS) - Verify security groups, VPC
aws ec2 describe-instances --instance-ids <instance-id> --query 'Reservations[0].Instances[0].SecurityGroups'

# Layer 5: Instance/Service - Verify agent status
aws ssm describe-instance-information --filters "Key=InstanceIds,Values=<instance-id>"
```

For concise commands to interact with AWS services (EC2, Aurora, Lambda), see [AWS Operations Guide](docs/AWS_OPERATIONS.md).

### Testing Anti-Patterns to Avoid

These patterns create false confidence—tests that pass but don't catch bugs.

#### Anti-Pattern 1: The Liar (Tests That Can't Fail)

A test that passes regardless of whether the code works. Often written after implementation without verifying it can fail.

```python
# BAD: "The Liar" - this test always passes
def test_store_report(self):
    mock_client = MagicMock()  # MagicMock() is truthy by default
    service.store_report('NVDA19', 'report text')
    mock_client.execute.assert_called()  # Only checks "was it called?"
    # Missing: What if execute() returned 0 rows? Test still passes!

# GOOD: Test can actually fail when code is broken
def test_store_report_detects_failure(self):
    mock_client = MagicMock()
    mock_client.execute.return_value = 0  # Simulate FK constraint failure
    result = service.store_report('NVDA19', 'report text')
    assert result is False, "Should return False when INSERT affects 0 rows"
```

**Detection**: After writing a test, intentionally break the code. If the test still passes, it's a Liar.

#### Anti-Pattern 2: Happy Path Only

Testing only success scenarios, never failures.

```python
# BAD: Only tests success
def test_fetch_ticker(self):
    mock_yf.download.return_value = sample_dataframe
    result = service.fetch('NVDA')
    assert result is not None

# GOOD: Tests both success AND failure paths
def test_fetch_ticker_success(self):
    mock_yf.download.return_value = sample_dataframe
    result = service.fetch('NVDA')
    assert len(result) > 0

def test_fetch_ticker_returns_none_on_empty(self):
    mock_yf.download.return_value = pd.DataFrame()  # Empty result
    result = service.fetch('INVALID')
    assert result is None

def test_fetch_ticker_handles_timeout(self):
    mock_yf.download.side_effect = TimeoutError()
    result = service.fetch('NVDA')
    assert result is None  # Graceful degradation
```

#### Anti-Pattern 3: Testing Implementation, Not Behavior

Testing *how* code does something rather than *what* it achieves.

```python
# BAD: Tests implementation details (brittle)
def test_cache_stores_correctly(self):
    service.store_report('NVDA19', 'report')
    # Asserts exact SQL string - breaks on any query change
    mock_client.execute.assert_called_with(
        "INSERT INTO reports (symbol, text) VALUES (%s, %s)",
        ('NVDA19', 'report')
    )

# GOOD: Tests behavior (survives refactoring)
def test_stored_report_can_be_retrieved(self):
    service.store_report('NVDA19', 'report text')
    result = service.get_report('NVDA19')
    assert result['text'] == 'report text'  # The actual contract
```

**Kent Beck's Rule**: "Tests should be sensitive to behavior changes and insensitive to structure changes."

#### Anti-Pattern 4: Mock Overload (The Mockery)

So many mocks that you're testing the mocks, not the code.

```python
# BAD: Testing mocks, not behavior
@patch('service.db_client')
@patch('service.cache')
@patch('service.logger')
@patch('service.metrics')
@patch('service.validator')
def test_process(self, mock_validator, mock_metrics, mock_logger, mock_cache, mock_db):
    mock_validator.validate.return_value = True
    mock_cache.get.return_value = None
    mock_db.query.return_value = [{'id': 1}]
    # ... 20 more lines of mock setup
    # What are we even testing at this point?

# GOOD: Mock only external boundaries
@patch('service.external_api')  # Only mock what crosses system boundary
def test_process(self, mock_api):
    mock_api.fetch.return_value = {'data': 'value'}
    result = service.process('input')
    assert result['status'] == 'success'
```

**Rule**: If test setup is longer than the test itself, the code needs refactoring, not more mocks.

### Testing Principles (FIRST + Behavior)

#### Principle 1: Test Outcomes, Not Execution

```python
# Execution test: "Did it run?"
mock_client.execute.assert_called_once()  # ✗ Weak

# Outcome test: "Did it work?"
assert result is True  # Success case
assert result is False  # When rowcount=0
```

#### Principle 2: Explicit Failure Mocking

MagicMock defaults are truthy. Always explicitly mock failure states:

```python
# These failures must be explicitly simulated:
mock_client.execute.return_value = 0           # No rows affected
mock_client.execute.side_effect = IntegrityError("FK violation")
mock_client.fetch_one.return_value = None      # Not found
mock_api.call.side_effect = TimeoutError()     # Timeout
```

#### Principle 3: Round-Trip Tests for Persistence

The real contract for storage is "data can be retrieved after storing."

```python
def test_cache_roundtrip(self):
    """Store then retrieve - the actual user contract"""
    # Store
    service.store_report(
        symbol='MWG19',
        report_text='Analysis report',
        report_json={'key': 'value'}
    )

    # Retrieve (the behavior that matters)
    result = service.get_cached_report('MWG19')

    # Assert the contract
    assert result is not None, "Stored report should be retrievable"
    assert result['report_text'] == 'Analysis report'
```

#### Principle 4: Schema Testing at System Boundaries

**The Litmus Test:** "If changing this breaks consumers, it's a contract (test it). If changing this doesn't affect consumers, it's implementation (don't test it)."

**Kent Beck's Rule Clarified:**
> "Tests should be sensitive to behavior changes and insensitive to structure changes."

This appears to conflict with testing data schemas. The resolution:

- **Within a service boundary**: Schema is implementation (SQL table structure, internal class shapes)
- **Across service boundaries**: Schema IS the behavior (the interface contract)

**When Schema Testing IS Appropriate:**
- Producer/consumer architectures (scheduler writes data, UI reads it)
- Event-driven systems (event shape is the contract)
- API versioning (request/response structure is public contract)
- Shared data stores accessed by multiple services

**When Schema Testing is an Anti-Pattern:**
- Internal database table structures (implementation detail)
- Private class attributes (encapsulation)
- Function parameters within same codebase (refactoring breaks tests)

**Example - The Distinction:**

```python
# ❌ ANTI-PATTERN: Testing internal structure
def test_database_columns(self):
    """Don't: SQL schema can change without breaking behavior"""
    cursor.execute("DESCRIBE reports")
    assert 'created_at' in columns  # Breaks on column rename

# ✅ PATTERN: Testing cross-service contract
def test_api_response_schema(self):
    """Do: API contract must remain stable for consumers"""
    response = api.get_report('NVDA19')
    assert 'created_at' in response  # External contract
    assert isinstance(response['price_history'], list)
    assert len(response['price_history']) >= 30
```

**Why This Matters:**
When services communicate through shared data, changing the data format in one service can silently break others—even when each service's tests pass in isolation. Schema contract tests catch integration failures that unit tests miss.

#### Principle 5: Silent Failure Detection

Database operations often fail without exceptions:

| Failure Mode | Raises Exception? | How to Detect |
|--------------|-------------------|---------------|
| FK constraint (MySQL) | Sometimes | Check rowcount |
| ENUM value mismatch | No | Check rowcount |
| Duplicate key (IGNORE) | No | Check rowcount |
| Write to wrong table | No | Round-trip test |

```python
# Code must check rowcount, not just absence of exception
def store_report(self, symbol: str, text: str) -> bool:
    rowcount = self.client.execute(insert_query, params)
    if rowcount == 0:
        logger.warning(f"INSERT affected 0 rows for {symbol}")
        return False  # Explicit failure signal
    return True
```

#### Principle 5: Test Sabotage Verification

After writing a test, verify it can detect failures:

```python
# Step 1: Write the test
def test_store_returns_false_on_failure(self):
    mock_client.execute.return_value = 0
    result = service.store_report('NVDA19', 'text')
    assert result is False

# Step 2: Sabotage - temporarily break the code
def store_report(self, symbol, text):
    self.client.execute(query, params)
    return True  # BUG: Always returns True

# Step 3: Run test - it should FAIL
# If test passes despite sabotage, the test is worthless (The Liar)
```

### References

- [Software Testing Anti-patterns (Codepipes)](https://blog.codepipes.com/testing/software-testing-antipatterns.html)
- [Unit Testing Anti-Patterns (Yegor Bugayenko)](https://www.yegor256.com/2018/12/11/unit-testing-anti-patterns.html)
- [Learn Go with Tests: Anti-patterns](https://quii.gitbook.io/learn-go-with-tests/meta/anti-patterns)
- [Database Integration Testing (Three Dots Labs)](https://threedots.tech/post/database-integration-testing/)
- [FIRST Principles (Uncle Bob Martin)](https://medium.com/pragmatic-programmers/unit-tests-are-first-fast-isolated-repeatable-self-verifying-and-timely-a83e8070698e)

---

## Code Organization

**Domain-Driven Structure Philosophy:** Organize by functionality (agent, data, workflow, api), not technical layer (models, services, controllers). Each module encapsulates a business domain with clear boundaries. Avoids God objects and cross-cutting concerns.

**Three-Tier Caching Strategy:** In-Memory (5-min TTL) → SQLite (local persistence) → S3 (cross-invocation) → Source (API/LLM). Choose tier based on access frequency and consistency requirements. See [Data Layer Patterns](docs/CODE_STYLE.md#data-layer--caching-patterns).

**System Boundary Principle:** Verify data type compatibility explicitly when crossing service boundaries. Strict types (MySQL ENUMs) fail silently on mismatch—no exception, data just doesn't persist. Always validate constraints on both sides.

**Necessary Condition Principle:** When an entity (value, variable, resource) is a necessary condition for an operation (function, query, infrastructure), the absence of that entity cannot have a fallback plan. If X is required for operation Y to produce correct results, then operation Y must fail explicitly when X is absent—it cannot silently fall back to an alternative. Fallback patterns imply "the operation can succeed without the primary entity," but if the entity is actually necessary, the fallback creates silent incorrectness where the operation appears to succeed but produces wrong results. Valid fallbacks provide the same outcome through different means (cache miss → fetch from source, primary server → backup server). Invalid fallbacks change the nature of the operation itself (missing user ID → use default user, missing primary key → search by name instead). Make necessary conditions explicit and enforced: mark as NOT NULL in schemas, make parameters required, validate at operation entry point, fail fast with clear error messages. Detection pattern: if X is required for correctness AND code has fallback logic (try X, else use Y), this reveals a design inconsistency—either X isn't actually required, or the fallback is hiding failures.

**Type System Integration Principle:** Research type compatibility BEFORE integrating systems (APIs, databases, message queues). Type system mismatches cause silent failures. Answer: (1) What types does target accept? (2) What types does source produce? (3) How does target handle invalid types? Apply defense in depth: convert types → handle special values → validate schema → serialize strict → verify outcome. See [Type System Integration Guide](docs/TYPE_SYSTEM_INTEGRATION.md).

**Heterogeneous Type System Compatibility Principle:** When integrating heterogeneous systems (libraries, services, programs, databases, APIs), each system has independent type requirements that cannot be inferred from similar systems. Type mismatches at system boundaries cause runtime errors, data corruption, or silent failures that may not surface until production. Explicit type conversion at boundaries (before crossing into the foreign system) prevents these failures. Pattern: (1) Read target system's type requirements, (2) Convert data to required format at boundary, (3) Verify with minimal test case, (4) Never assume patterns from similar systems apply. Common boundary mismatches: structured data (Python dicts vs JSON strings vs Protocol Buffers), numeric types (NumPy int64 vs native Python int vs JSON number), temporal types (datetime objects vs ISO strings vs Unix timestamps vs database-specific formats), path representations (Path objects vs strings vs URLs).

**Examples across heterogeneous systems:**

| System Type | Example | Similar System | Type Mismatch | Fix |
|-------------|---------|----------------|---------------|-----|
| **Database Driver** | PyMySQL | mysql-connector-python | PyMySQL rejects dicts for JSON columns | `json.dumps(data)` before passing |
| **HTTP Client** | httpx | requests | httpx stricter about URL types | Convert to `str()` explicitly |
| **Cloud SDK** | boto3 | AWS CLI | boto3 needs native Python types, not NumPy | Convert `np.int64` → `int()` |
| **REST API** | FastAPI | Flask | FastAPI Pydantic expects ISO strings for datetime | Use `.isoformat()` before serializing |
| **Message Queue** | Kafka producer | RabbitMQ | Kafka requires bytes, not strings | `str.encode('utf-8')` |
| **CLI Tool** | subprocess | shell script | subprocess needs strings for env vars | Convert `Path` → `str()` |
| **Dataframe Library** | polars | pandas | Different datetime handling | Convert to `pd.Timestamp()` or `.dt.timestamp()` |

**Detection pattern:**
```
If switching from library A to library B:
  AND code worked with library A
  AND library B raises TypeError/ValueError
  → Check library B's type requirements, don't assume library A's patterns apply
```

**Research Before Iteration Principle:** When same bug persists after 2 fix attempts, STOP iterating and START researching. Invest 30-60 minutes understanding root cause (read specs, inspect real data, reproduce locally) instead of deploying more guesses. Research has upfront cost but prevents 3+ failed deployment cycles. Pattern: iteration for first hypotheses, research when hypotheses fail repeatedly.

**Retry/Fallback Pattern:** Multi-level fallback for reliability (yfinance with exponential backoff → direct API → stale cache). Graceful degradation: stale data better than no data. See [Data Layer Patterns](docs/CODE_STYLE.md#retryfallback-pattern).

**Service Design Patterns:** Singleton pattern for Lambda cold start optimization. Async/Sync dual methods for LangGraph (sync) + FastAPI (async). Custom exception hierarchy with centralized error handlers. See [API Architecture](docs/CODE_STYLE.md#telegram-api-architecture-patterns).

**Database Migration Principles:** Migration files are immutable once committed to version control—never edit them, always create new migrations for schema changes. This ensures reproducibility across environments and preserves schema evolution history. Use reconciliation migrations when database state is unknown or partially migrated. Reconciliation migrations use idempotent operations (CREATE TABLE IF NOT EXISTS, ALTER TABLE ADD COLUMN IF NOT EXISTS) to safely transition from any intermediate state to the desired schema without destructive operations. This pattern prevents migration conflicts, duplicate numbering issues, and unclear execution states. Unlike traditional sequential migrations that assume clean state, reconciliation migrations validate current schema and apply only missing changes. **Critical gotchas:** (1) `CREATE TABLE IF NOT EXISTS` skips entirely if table exists with different schema—use `ALTER TABLE` to fix existing tables. (2) `ALTER TABLE MODIFY COLUMN` changes column TYPE but not existing DATA—old rows retain their original values even if incompatible with new type. Always verify migrations changed what you expected with `DESCRIBE table_name` after applying. See [Database Migrations Guide](docs/DATABASE_MIGRATIONS.md) for detailed patterns, MySQL-specific considerations, and migration tracking strategies.

**Aurora VPC Access Pattern:** Aurora databases are deployed in private VPC subnets and CANNOT be accessed directly from outside the VPC. Use AWS SSM Session Manager port forwarding through a bastion host to establish secure tunnels. Pattern: (1) Find SSM-managed instance: `aws ssm describe-instance-information`, (2) Start port forwarding: `aws ssm start-session --target <instance-id> --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters '{"host":["<aurora-endpoint>"],"portNumber":["3306"],"localPortNumber":["3307"]}'`, (3) Connect to `localhost:3307` as if it were the Aurora endpoint. Scripts that access Aurora must expect SSM tunnel to be active (check with `ss -ltn | grep 3307`). Never attempt direct connections to Aurora endpoints—they will timeout. See `~/aurora-vd.sh` for reference implementation.

For complete directory tree and file organization, run `just tree` or see [Code Style Guide](docs/CODE_STYLE.md#naming-conventions).

---

## CLI Usage

The project uses a two-layer CLI design: **Justfile** (intent-based recipes describing WHEN/WHY) and **dr CLI** (explicit syntax for HOW).

**For complete command reference**, see [docs/cli.md](docs/cli.md).

**For common workflows**, see `justfile` or run `just --list`.

---

## Code Style & Principles

**Documentation Convention:** Google-style docstrings with Args/Returns/Raises sections. All public functions fully documented, private methods briefly documented. See [Code Style Guide](docs/CODE_STYLE.md#docstring-style).

**Type Safety:** Comprehensive type hints throughout (`Dict[str, Any]`, `Optional[Type]`, `TypedDict` for state). Type-safe state management with `AgentState` TypedDict enables IDE autocomplete and static analysis. See [Type Hints](docs/CODE_STYLE.md#type-hints).

**Workflow State Management Philosophy:** LangGraph workflows use `TypedDict` with `Annotated[Sequence[T], operator.add]` for auto-merging message lists. State is immutable between nodes—each node returns new state dict. Errors propagate via `state["error"]` field (never raise exceptions in workflow nodes). See [Workflow Patterns](docs/CODE_STYLE.md#workflow-state-management-patterns).

**Error Handling Duality:** Workflow nodes use state-based error propagation (collect all errors, enable resumable workflows). Utility functions raise descriptive exceptions (fail fast). Never mix these patterns. See [Error Handling](docs/CODE_STYLE.md#error-handling-patterns).

**Silent None Propagation Anti-Pattern:** Functions that return `None` on failure create cascading silent failures in workflows. Prefer explicit exceptions in utility functions so workflow orchestrators can catch and handle them appropriately. `return None` hides failures; exceptions make them visible and catchable.

**Workflow Validation Gates:** Before executing a workflow node, validate that all prerequisite data exists and is non-empty. Don't assume upstream nodes succeeded—check explicitly. Example: Before analyzing technical indicators, verify `ticker_data` is populated and non-empty.

**JSON Serialization Requirement:** NumPy/Pandas types must be converted before JSON encoding (`np.int64` → `int`, `pd.Timestamp` → ISO string). Lambda responses, API endpoints, and LangSmith tracing all require JSON-serializable state. See [JSON Serialization](docs/CODE_STYLE.md#json-serialization).

**Naming Conventions:** Files `snake_case.py`, classes `PascalCase`, functions `snake_case()`, constants `UPPER_SNAKE_CASE`, private methods `_snake_case()`. See [Naming Guide](docs/CODE_STYLE.md#naming-conventions).

## UI/Frontend Principles

**Normalized State Philosophy:** Store entity IDs instead of object copies; derive data from single source of truth via selectors. This eliminates entire class of stale copy bugs and enables automatic updates when source data changes. Example: `selectedTicker: string | null` derives market from `markets` array via `getSelectedMarket()` selector. See [UI Principles](docs/frontend/UI_PRINCIPLES.md#normalized-state-pattern).

**Stale-While-Revalidate Pattern:** Show cached data immediately for instant UI feedback while fetching fresh data in background. Upgrade UI seamlessly when fresh data arrives. Handles slow APIs gracefully without blocking user interaction. Example: Display 30-day cached chart from rankings API while fetching full 365-day report in background. See [UI Principles](docs/frontend/UI_PRINCIPLES.md#stale-while-revalidate-pattern).

**Monotonic Data Invariants:** Data structures that only grow or stay same, never shrink. Enforce via intelligent merge logic: only replace cached data if new data is demonstrably better (non-empty AND larger). Prevents data loss from partial API responses or race conditions. Example: `price_history.length` never decreases after being populated. See [UI Principles](docs/frontend/UI_PRINCIPLES.md#monotonic-data-invariants).

**Property-Based Testing:** Use generative testing tools (fast-check) to generate 1000+ random test cases that verify invariants always hold. Define properties that must be true regardless of input, let tool find counterexamples. Catches edge cases manual tests miss. See [UI Principles](docs/frontend/UI_PRINCIPLES.md#property-based-testing) for component patterns, state management, and testing strategies.

**TypeScript Component Patterns:** React components use strict TypeScript prop interfaces for type safety. Composition over inheritance. Props for configuration, children for content. Avoid prop drilling beyond 2-3 levels. See [UI Principles](docs/frontend/UI_PRINCIPLES.md#reacttypescript-patterns).

---

## Deployment

**Deployment Philosophy:** Serverless AWS Lambda with immutable container images, zero-downtime promotion via versioning.

**Zero-Downtime Pattern:** `$LATEST` (mutable staging) → `Version N` (immutable snapshot) → `live` alias (production pointer). Test in $LATEST before promoting alias. See [Lambda Versioning Strategy](docs/deployment/LAMBDA_VERSIONING.md).

**Environment Strategy:** Single branch auto-deploys through environments: `telegram` → dev → staging → prod. Progressive deployment with smoke tests between stages. See [CI/CD Architecture](docs/deployment/CI_CD.md) and [Multi-Environment Guide](docs/deployment/MULTI_ENV.md).

**NumPy/Pandas Serialization Requirement:** Lambda responses must be JSON-serializable. Convert NumPy types before JSON encoding (`np.int64` → `int`, `pd.Timestamp` → `str`). See [Lambda Best Practices](docs/deployment/LAMBDA_BEST_PRACTICES.md).

**Cold Start Optimization:** Module-level initialization for heavy imports and service singletons. Container reuse optimization critical for Lambda performance (cold: ~7.5s, warm: ~200ms). See [Performance Patterns](docs/deployment/PERFORMANCE.md).

**Deployment Monitoring Discipline:** Use AWS CLI waiters (`aws lambda wait function-updated`), never `sleep X`. Use GitHub Actions `gh run watch --exit-status` for proper exit codes. See [Monitoring Guide](docs/deployment/MONITORING.md).

**Artifact Promotion Principle:** Build once, promote same immutable image through all environments. What you test in staging is exactly what deploys to prod. See [Deployment Workflow](docs/deployment/WORKFLOW.md).

**Environment Variables:** Managed via Doppler. See `docs/deployment/WORKFLOW.md` for required secrets per environment.

**Secret Management Principle: Separation by Consumer**

Secrets are stored in two separate systems based on **who** consumes them:

**Doppler (Runtime Secrets)**
- Consumer: Application code (Lambda functions)
- When: During request/response execution
- Examples: `AURORA_HOST`, `OPENROUTER_API_KEY`, `PDF_BUCKET_NAME`
- Injection: Doppler → Terraform → Lambda environment variables
- Pattern: `ENV=dev doppler run -- python app.py`

**GitHub Secrets (Deployment Secrets)**
- Consumer: CI/CD pipeline (GitHub Actions)
- When: During deployment automation
- Examples: `CLOUDFRONT_DISTRIBUTION_ID`, `AWS_ACCESS_KEY_ID`
- Access: `${{ secrets.SECRET_NAME }}` in workflows
- Pattern: Used by deployment scripts, NOT application code

**The Deciding Question**: "Does the Lambda function running in production need to know this value?"
- YES → Store in Doppler (runtime secret)
- NO → Store in GitHub Secrets (deployment secret)

**Why This Separation:**
- Least privilege: Lambda never sees deployment credentials
- Clear boundaries: Doppler = app needs, GitHub = CI/CD needs
- Security: Compromised Lambda doesn't expose deployment access

**Infrastructure-Deployment Contract Validation**

Before every deployment, validate that GitHub secrets match actual AWS infrastructure state. This catches configuration drift and prevents deployment failures.

**Pattern: Query Reality, Validate Secrets**

The first job in every deployment pipeline queries AWS for actual infrastructure IDs, then validates GitHub secrets match reality:

```yaml
jobs:
  validate-deployment-config:
    name: Validate Infrastructure & Secrets
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-1

      - name: Validate CloudFront Distributions
        env:
          GITHUB_TEST_DIST: ${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }}
          GITHUB_APP_DIST: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}
        run: |
          # Query actual infrastructure from AWS
          ACTUAL_TEST=$(aws cloudfront list-distributions \
            --query 'DistributionList.Items[?Comment==`dr-daily-report TEST CloudFront - dev`].Id' \
            --output text)

          ACTUAL_APP=$(aws cloudfront list-distributions \
            --query 'DistributionList.Items[?Comment==`dr-daily-report APP CloudFront - dev`].Id' \
            --output text)

          # Validate secrets match reality
          if [ "$ACTUAL_TEST" != "$GITHUB_TEST_DIST" ]; then
            echo "❌ Mismatch: CLOUDFRONT_TEST_DISTRIBUTION_ID"
            echo "   AWS:    $ACTUAL_TEST"
            echo "   GitHub: $GITHUB_TEST_DIST"
            exit 1  # Fail fast - blocks entire pipeline
          fi

          if [ "$ACTUAL_APP" != "$GITHUB_APP_DIST" ]; then
            echo "❌ Mismatch: CLOUDFRONT_DISTRIBUTION_ID"
            exit 1
          fi

          echo "✅ All secrets match actual infrastructure"

  build:
    needs: validate-deployment-config  # Won't run if validation fails
    # ... rest of pipeline
```

**Why This Works:**
- ✅ Self-healing: Automatically detects when secrets are stale
- ✅ No manual checklist: Code queries AWS, compares to secrets
- ✅ Catches drift: Even if someone changed AWS console manually
- ✅ Single source of truth: AWS infrastructure is reality
- ✅ Fail fast: First job, blocks deployment if secrets wrong (< 30 seconds)

**When to Use:**
- Resources that CI/CD operates on (CloudFront invalidation, S3 sync, Lambda updates)
- First job in deployment pipeline (before build/deploy)
- Every deployment (not just after Terraform changes)

**Resources to Validate:**
- CloudFront distribution IDs (for cache invalidation)
- S3 bucket names (for file sync)
- Lambda function names (if not in Terraform variables)
- Any AWS resource ID referenced in deployment scripts

For complete deployment runbook, commands, and troubleshooting, see [Telegram Deployment Runbook](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md).

---

## Development Workflow

### Common Commands
```bash
# Setup
just setup              # Install dependencies

# Development
just dev                # Start local server
just shell              # Python REPL with imports

# Testing
just test-changes       # Quick test
just pre-commit         # Full pre-commit checks

# Code quality
just check              # Syntax check
just format             # Format with black
just lint               # Lint check

# Utilities
just tree               # Show project structure
just stats              # Code statistics
just report DBS19       # Generate ticker report
```

### Key Principles
1. **Two-layer CLI**: Justfile for intent, dr CLI for implementation
2. **State management**: TypedDict (AgentState) for type safety
3. **Error propagation**: state["error"] pattern in workflows
4. **Tracing control**: `--trace/--no-trace` for LangSmith
5. **Secrets management**: Always use Doppler, never hardcode
6. **Type hints**: Use throughout for better IDE support
7. **Docstrings**: Google format with Args/Returns/Example
8. **Testing**: Class-based pytest with descriptive test names

### When Adding New Features
1. Check if TypedDict (AgentState) needs new fields → Update `src/types.py`
2. Create tests first → `tests/test_<component>.py`
3. Implement with type hints and docstrings
4. Add CLI command if user-facing → `dr_cli/commands/<group>.py`
5. Add justfile recipe for common workflows → `justfile`
6. Update transparency footnote if new data source → `src/report/transparency_footer.py`

### Multi-Stage Report Generation
```python
# Single-stage (default)
dr util report DBS19

# Multi-stage (6 mini-reports → synthesis)
dr util report DBS19 --strategy multi-stage
```

Strategy implementation:
- Check `state["strategy"]` in `workflow_nodes.py:generate_report()`
- Delegates to `_generate_report_singlestage()` or `_generate_report_multistage()`
- Transparency footer shows which strategy was used

---

## Important Architectural Decisions

This section documents **WHY** certain technologies and patterns were chosen (not just WHAT they are).

### Why OpenRouter Instead of Direct OpenAI API

**Decision:** Use OpenRouter as LLM proxy instead of direct OpenAI API.

```python
# src/agent.py
self.llm = ChatOpenAI(
    model="openai/gpt-4o",
    base_url="https://openrouter.ai/api/v1",  # OpenRouter proxy
    api_key=os.getenv("OPENROUTER_API_KEY")  # Not OPENAI_API_KEY
)
```

**Rationale:**
- ✅ **Cost Tracking**: OpenRouter dashboard shows per-request costs, model usage
- ✅ **Usage Monitoring**: Track token consumption across all models
- ✅ **API Key Rotation**: Easier key management (no OpenAI account needed)
- ✅ **Multi-Model Support**: Easy to switch models (GPT-4o, Claude, Gemini) without code changes
- ✅ **Rate Limit Management**: OpenRouter handles rate limiting across providers

**Trade-offs:**
- ❌ Slight latency overhead (~50ms proxy hop)
- ❌ Additional service dependency
- ✅ Overall: Monitoring benefits > latency cost

**Historical Context:** Migrated from direct OpenAI in Sprint 1 after encountering cost tracking issues.

### Why Multi-Stage Report Generation

**Decision:** Support two strategies: single-stage (fast) and multi-stage (balanced).

**Single-Stage:**
```python
# One LLM call with all context
def _generate_report_singlestage(state):
    context = build_full_context(state)  # All data at once
    report = llm.generate(prompt, context)
    return report
```

**Multi-Stage:**
```python
# 6 specialist mini-reports → synthesis
def _generate_report_multistage(state):
    mini_reports = {
        'technical': generate_technical_mini_report(state),
        'fundamental': generate_fundamental_mini_report(state),
        'market_conditions': generate_market_mini_report(state),
        'news': generate_news_mini_report(state),
        'comparative': generate_comparative_mini_report(state),
        'strategy': generate_strategy_mini_report(state)
    }
    # Synthesis LLM combines mini-reports
    report = synthesis_generator.synthesize(mini_reports, state)
    return report
```

**Rationale:**
- ❌ **Problem**: Single-stage reports often over-emphasized technical analysis (60%+ of content)
- ✅ **Solution**: Multi-stage ensures equal representation (each category ~16% of final report)
- ✅ **Quality**: Specialist prompts for each category → better depth
- ✅ **Flexibility**: Easy to add/remove categories without rewriting main prompt

**Trade-offs:**
- ❌ Cost: 7 LLM calls vs 1 (7x token cost)
- ❌ Latency: ~15s vs ~5s generation time
- ✅ Quality: More balanced, comprehensive reports

**When to use:**
- Single-stage: Quick analysis, cost-sensitive, simple tickers
- Multi-stage: Important decisions, complex tickers, comprehensive analysis

### Why Service Singletons vs Dependency Injection

**Decision:** Use module-level global singletons for API services.

```python
# Pattern chosen:
_service: Optional[TickerService] = None

def get_ticker_service() -> TickerService:
    global _service
    if _service is None:
        _service = TickerService()
    return _service

# NOT dependency injection:
# class FastAPIApp:
#     def __init__(self, ticker_service: TickerService):
#         self.ticker_service = ticker_service
```

**Rationale:**
- ✅ **Lambda Cold Starts**: Container reuse preserves singletons (no re-init)
- ✅ **Simplicity**: No DI container framework needed
- ✅ **Performance**: CSV data loaded once per container (~2000 tickers)
- ✅ **Memory**: Single service instance vs multiple per request

**Trade-offs:**
- ❌ **Testing**: Requires patching globals (harder to mock)
- ❌ **Flexibility**: Can't easily swap implementations
- ✅ **Overall**: Lambda performance > testability concerns

**Why not DI:**
- DI containers (e.g., dependency-injector, punq) add complexity
- Lambda environment optimizes for speed over flexibility
- Service interfaces are stable (rarely need swapping)

### Why LangGraph TypedDict State

**Decision:** Use LangGraph with TypedDict state instead of custom orchestration.

```python
# src/types.py
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    ticker: str
    indicators: dict
    # ... all workflow state
```

**Rationale:**
- ✅ **Type Safety**: IDE autocomplete, type checking for state fields
- ✅ **LangSmith Integration**: Automatic tracing of workflow execution
- ✅ **Error Recovery**: state["error"] pattern enables resumable workflows
- ✅ **Observability**: See state evolution through each node in traces
- ✅ **LangChain Ecosystem**: Integrates with LangChain tools, agents, memory

**Trade-offs:**
- ❌ **Learning Curve**: LangGraph concepts (nodes, edges, StateGraph)
- ❌ **Framework Lock-in**: Tied to LangChain ecosystem
- ✅ **Overall**: Observability + tracing > framework independence

**Alternatives considered:**
- Custom orchestration (too much boilerplate, no tracing)
- Apache Airflow (overkill for single workflow, requires infrastructure)
- Prefect (good but no LLM-specific features)

### Why Correlation-Based Peer Comparison

**Decision:** Use historical price correlation for finding peer companies.

```python
# src/api/peer_selector.py
def find_peers(self, ticker: str, max_peers: int = 5) -> List[str]:
    """Find peers using 1-year price correlation (Pearson)"""
    target_data = yf.download(ticker, period='1y')['Close']

    correlations = []
    for candidate in all_tickers:
        candidate_data = yf.download(candidate, period='1y')['Close']
        correlation = target_data.corr(candidate_data)  # Pearson coefficient
        if correlation > 0.5:  # Threshold
            correlations.append((candidate, correlation))

    return sorted(correlations, reverse=True)[:max_peers]
```

**Rationale:**
- ✅ **No External APIs**: Uses yfinance data already fetched
- ✅ **Simple & Explainable**: Correlation coefficient easy to understand
- ✅ **Fast**: pandas.corr() is efficient (~1s for 2000 tickers)
- ✅ **Historical Data**: Based on actual price movements, not subjective classification

**Alternatives considered:**
- ❌ **Industry Classification**: Requires external data, not always accurate
- ❌ **Fundamental Similarity**: Complex, requires financials for all tickers
- ❌ **ML Clustering**: Overkill, requires training data, harder to explain
- ❌ **Manual Tagging**: Doesn't scale, requires maintenance

**Trade-offs:**
- ❌ **Limitation**: Correlation ≠ causation (may find spurious peers)
- ❌ **Market Bias**: Correlated during bull markets, not fundamentally similar
- ✅ **Overall**: Simplicity + speed > perfect accuracy

### Why Two Separate Apps (LINE Bot + Telegram Mini App)

**Decision:** Build Telegram Mini App as separate FastAPI app instead of extending LINE Bot.

**Rationale:**
- ✅ **LINE Limitations**: No rich UI, limited message types, no web views
- ✅ **Telegram Capabilities**: Mini Apps support full HTML/CSS/JS, charts, interactive UI
- ✅ **Different UX**: Chat-based (LINE) vs dashboard (Telegram)
- ✅ **Shared Backend**: Both use same agent/workflow, just different interfaces

**Architecture:**
```
Core Backend (Shared):
  - src/agent.py
  - src/workflow/
  - src/data/
  - src/analysis/

LINE Bot Interface:
  - src/integrations/line_bot.py
  - Lambda Function URL
  - Chat-based UX

Telegram Mini App Interface:
  - src/api/ (FastAPI)
  - API Gateway / Lambda
  - Web-based dashboard UX
```

**Why not extend LINE Bot:**
- LINE Messaging API doesn't support rich UI components
- Can't embed charts, interactive elements in LINE messages
- LINE Flex Messages limited compared to full HTML/CSS

**Trade-offs:**
- ❌ **Maintenance**: Two interfaces to maintain
- ✅ **User Experience**: Each platform optimized for its strengths
- ✅ **Overall**: Better UX > maintenance simplicity

### Why Single Root Terraform Architecture (Historical Note)

**Current Architecture (Dec 2024):** All infrastructure managed by root terraform in single state file.

```
terraform/
├── main.tf              # LINE bot Lambda
├── telegram_api.tf      # Telegram Lambda
├── ecr.tf               # ECR repositories
├── dynamodb.tf          # DynamoDB tables
├── aurora.tf            # Aurora database
├── frontend.tf          # CloudFront distributions
└── layers/
    └── 00-bootstrap/    # State bucket, DynamoDB locks (local state)
```

**Historical Context (Pre-Dec 2024):**
A layered terraform architecture was planned (01-data, 02-platform, 03-apps layers) but never fully implemented. The layer directories existed with terraform code but never managed actual resources (no S3 state files). All resources were created and managed by root terraform from the start.

**Dec 2024 Cleanup:**
Removed unused layer directories (01-data, 02-platform, 03-apps) after confirming:
- No S3 state files existed for these layers
- All resources tracked in root terraform state
- ~2GB of .terraform cache removed

**Why Keep 00-bootstrap Layer:**
Bootstrap layer uses LOCAL state (terraform.tfstate in its directory) to manage the S3 bucket and DynamoDB table that root terraform uses for remote state. This is the chicken-and-egg infrastructure - can't use remote state that doesn't exist yet.

**Rationale for Single Root:**
- ✅ **Simplicity**: Single terraform state, single apply
- ✅ **No Cross-Layer Complexity**: All resources in same state, direct references
- ✅ **Faster Development**: No need to coordinate layer dependencies
- ✅ **Sufficient for Project Scale**: ~100 resources manageable in single state

**Trade-offs:**
- ❌ **Blast Radius**: Failed apply affects entire infrastructure
- ❌ **State Lock Contention**: Single lock for all changes
- ✅ **Overall**: Simplicity > theoretical benefits of layering for this project size

**Why import blocks over CLI imports:**
```hcl
# Terraform 1.5+ import blocks (version-controlled, reviewable)
import {
  to = aws_lambda_function.telegram_api
  id = "telegram-api-ticker-report"
}

# vs CLI imports (ephemeral, not tracked in git)
# terraform import aws_lambda_function.telegram_api telegram-api-ticker-report
```

**Historical Context:** Migrated from flat structure after hitting state lock contention with 40+ resources in single state file.

### Why Directory Structure Over Terraform Workspaces

**Decision:** Use environment directories (`envs/dev/`, `envs/staging/`, `envs/prod/`) instead of Terraform workspaces.

| Workspaces | Directory Structure |
|------------|---------------------|
| `terraform workspace select prod` accidents | Explicit `cd envs/prod` |
| Same backend, easy cross-contamination | Separate backends per env |
| Can't require PR for prod only | Different directories = different PRs |
| Must share provider versions | Can differ per env |
| Good for: ephemeral/identical envs | Good for: long-lived envs with different configs |

**Rationale:**
- ✅ **Safety**: Can't accidentally destroy prod from dev terminal
- ✅ **Code Review**: prod changes get separate PRs with different reviewers
- ✅ **Flexibility**: Each env can have different resource sizes, retention, etc.
- ✅ **State Isolation**: Separate S3 keys prevent cross-env state corruption

**Trade-offs:**
- ❌ More files: 3x directory duplication
- ❌ Module updates: Must update all envs (use shared modules to minimize)
- ✅ Overall: Safety > DRY for infrastructure

**Historical Context:** Chose directories after evaluating workspace accidents in other projects where `terraform destroy` in wrong workspace deleted production.

### Why Artifact Promotion Over Per-Env Builds

**Decision:** Build container images once, promote same image through environments.

```
Build Once:  sha-abc123-20251127  (IMMUTABLE)
     │
     ├──▶  DEV:     lambda_image_uri = "sha-abc123-20251127"
     │              (auto on merge to main)
     │
     ├──▶  STAGING: lambda_image_uri = "sha-abc123-20251127"
     │              (same image, promoted after dev tests pass)
     │
     └──▶  PROD:    lambda_image_uri = "sha-abc123-20251127"
                    (same image, promoted after staging + approval)
```

**Rationale:**
- ✅ **Reproducibility**: What you test in staging is exactly what deploys to prod
- ✅ **Speed**: No rebuild per environment (save 5-10 min per deploy)
- ✅ **Rollback**: Can instantly revert to any previous image tag
- ✅ **Audit Trail**: SHA-based tags link deployments to exact commits

**Implementation:**
```hcl
# envs/dev/main.tf
variable "lambda_image_uri" {
  description = "ECR image URI from CI build step"
}

module "telegram_api" {
  source           = "../../modules/telegram-api"
  lambda_image_uri = var.lambda_image_uri  # Passed from CI
}
```

**CI Pattern:**
```yaml
# CI passes same image to each environment
terraform apply -var="lambda_image_uri=${{ needs.build.outputs.image_uri }}"
```

**Trade-offs:**
- ❌ Requires immutable tags (can't use `latest`)
- ❌ More complex CI (must pass image URI between jobs)
- ✅ Overall: Reproducibility > simplicity

### Why Infrastructure TDD with OPA + Terratest

**Decision:** Use OPA for pre-apply policy validation and Terratest for post-apply integration testing.

**TDD Flow:**
```
terraform plan → OPA validation → terraform apply → Terratest verification
     ↓                ↓                  ↓                   ↓
  Generate JSON    Check policies    Create infra    Verify infra works
```

**Pre-Apply: OPA Policy Validation**
```bash
# Convert plan to JSON, validate against policies
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test tfplan.json --policy policies/
```

**Post-Apply: Terratest Integration Tests**
```go
// terraform/tests/lambda_test.go
func TestTelegramAPIHealthCheck(t *testing.T) {
    client := getLambdaClient(t)
    result, err := client.Invoke(&lambda.InvokeInput{
        FunctionName: aws.String("dr-daily-report-telegram-api-dev"),
        Payload:      []byte(`{"httpMethod": "GET", "path": "/api/v1/health"}`),
    })
    require.NoError(t, err)
    // Assert response
}
```

**Rationale:**
- ✅ **Shift-Left Security**: Catch IAM/S3/encryption issues before they deploy
- ✅ **Policy-as-Code**: Version-controlled, reviewable security rules
- ✅ **Integration Confidence**: Terratest verifies infra actually works
- ✅ **CI/CD Integration**: OPA blocks PRs, Terratest runs on merge

**Trade-offs:**
- ❌ Learning curve: Rego language for OPA policies
- ❌ Test maintenance: Terratest needs updates when infra changes
- ✅ Overall: Early detection > deployment rollbacks

**Directory Structure:**
```
terraform/
├── policies/                    # OPA policies (Rego)
│   ├── main.rego               # Entry point
│   ├── security/               # Security policies
│   │   ├── iam.rego            # IAM least privilege
│   │   ├── s3.rego             # S3 security
│   │   ├── dynamodb.rego       # DynamoDB best practices
│   │   └── encryption.rego     # Encryption requirements
│   └── tagging/
│       └── required_tags.rego  # Tag enforcement
├── tests/                       # Terratest (Go)
│   ├── go.mod
│   ├── lambda_test.go
│   ├── dynamodb_test.go
│   └── api_gateway_test.go
└── envs/                        # Environment configs
```

**CI/CD Integration:**
```yaml
# .github/workflows/terraform-test.yml
jobs:
  opa-validate:     # Runs on PRs - blocks on policy violations
  terratest:        # Runs on push to telegram/staging - verifies deployment
```

**Justfile Recipes:**
```bash
just opa-validate dev    # Run OPA policies against dev plan
just terratest           # Run Terratest integration tests
just infra-tdd dev       # Full cycle: OPA → apply → Terratest
```

### Why Two CloudFront Distributions Per Environment

**Decision:** Create TEST and APP CloudFront distributions for zero-risk frontend deployment.

**Problem:**
CloudFront cache invalidation is atomic - once invalidated, users immediately see new files.
If E2E tests run AFTER invalidation and fail, users have already seen the broken frontend.

**Solution:**
```
Same S3 Bucket
     │
     ├── TEST CloudFront → Invalidated first, E2E tests run here
     │
     └── APP CloudFront  → Invalidated ONLY after E2E tests pass
```

**Rationale:**
- ✅ **Zero-Risk**: Users never see untested frontend code
- ✅ **Mirrors Backend Pattern**: Like Lambda's $LATEST (TEST) vs "live" alias (APP)
- ✅ **Instant Rollback**: Simply don't invalidate APP = users see old working version
- ✅ **No S3 Duplication**: Both CloudFronts serve same bucket, just different cache timing

**Alternatives considered:**
- ❌ **Separate S3 buckets**: Doubles storage costs, requires sync logic
- ❌ **S3 versioning + rollback**: Complex, doesn't prevent initial exposure
- ❌ **Feature flags**: Adds code complexity, still deploys broken code
- ❌ **Canary releases**: Overkill for static frontend, CloudFront doesn't support natively

**Trade-offs:**
- ❌ 2x CloudFront distributions = higher cost (~$1-5/month per distribution)
- ❌ More GitHub secrets to manage per environment
- ❌ Longer deployment pipeline (test → promote)
- ✅ Overall: Safety > cost for production frontends

**Historical Context:** Implemented after realizing CloudFront doesn't honor client-side
`Cache-Control: no-cache` headers - there's no way to "test before users see" with
a single distribution. This pattern mirrors the Lambda alias pattern that solved
the same problem for backend deployments.

---

## When Adding New Features

**Extension Points Philosophy:** The codebase has four primary extension points, each with specific integration requirements:

1. **Adding Scoring Metrics:** Create scorer class → integrate into workflow_nodes.py → extend AgentState TypedDict → run validation tests. Scorers must return dict with 'score', 'feedback', 'passed' fields. See [Code Style](docs/CODE_STYLE.md#module-organization-pattern) for module structure.

2. **Adding CLI Commands:** Use Click decorators in dr_cli/commands/ → add Justfile recipe for intent layer → test with `--help` flag. Follow two-layer design: Justfile for WHEN/WHY, dr CLI for HOW. See [CLI Architecture](#cli-usage).

3. **Extending State:** Update AgentState TypedDict in src/types.py → add workflow node that populates field → filter from LangSmith if non-serializable. All state fields must be JSON-serializable or filtered before tracing.

4. **Adding API Endpoints:** Create service singleton → define Pydantic models → add FastAPI route → write integration tests. Follow async/sync dual method pattern for LangGraph compatibility.
