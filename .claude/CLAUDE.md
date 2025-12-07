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

### Overview
**IMPORTANT:** This project now supports TWO separate applications:

1. **LINE Bot** (Original, Production): Chat-based Thai financial reports via LINE Messaging API
2. **Telegram Mini App** (New, Phase 3): Web-based dashboard with REST API for richer interactions

**Shared Infrastructure:** Both apps use the same core agent/workflow, data layer, and analysis services. Resources are separated via AWS tags (`App = line-bot | telegram-api | shared`).

LINE bot generates comprehensive Thai language financial reports for day traders and investors. Uses hierarchical LLM architecture (specialist mini-reports → synthesis) for balanced data category representation.

### Core Components
- **Agent**: LangGraph workflow orchestration (`src/agent.py`)
- **Workflow**: State-based nodes for data fetching, analysis, report generation (`src/workflow/`)
- **Report Generation**: Single-stage or multi-stage LLM strategies (`src/report/`)
- **Data Layer**: YFinance, SQLite caching, S3 storage (`src/data/`)
- **Scoring**: Faithfulness, completeness, reasoning quality, QoS (`src/scoring/`)
- **CLI**: Two-layer design (Justfile + dr CLI) (`dr_cli/`, `justfile`)

### Key Technologies
- **LangGraph**: Workflow state management with AgentState TypedDict
- **OpenRouter**: LLM API (GPT-4o) with cost tracking
- **LangSmith**: Optional tracing (controlled via `--trace/--no-trace`)
- **Doppler**: Environment variable/secrets management
- **AWS Lambda**: Serverless deployment target

### AWS Permissions
**IMPORTANT:** The user has full AWS IAM permissions and can create/modify IAM policies. When encountering AWS permission errors:
1. **Do NOT ask** if the user wants to fix permissions - just fix them
2. Create the necessary IAM policy with required permissions
3. Attach the policy to the appropriate IAM user/role
4. Re-run the failed operation

Common permission patterns:
```bash
# Create IAM policy for missing permissions
aws iam create-policy --policy-name <name> --policy-document file://policy.json

# Attach to user
aws iam attach-user-policy --user-name <user> --policy-arn <arn>
```

### ⚠️ MAIN BRANCH PROTECTION - CRITICAL

**DO NOT touch the `main` branch.** The project is temporarily using environment-based branches:

| Branch | Environment | Deploys To |
|--------|-------------|------------|
| `telegram` | Dev | Auto-deploy on push |
| `telegram-staging` | Staging | Auto-deploy on push |
| `telegram-prod` | Production | Auto-deploy on push |

**NEVER do any of the following:**
- ❌ `git checkout main` followed by changes
- ❌ `git merge <anything> main`
- ❌ `git push origin main`
- ❌ Create PRs targeting `main`
- ❌ Deploy from `main` branch
- ❌ Reference `main` in GitHub Actions workflows

**Why:** Main branch contains legacy/unclean code. All Telegram Mini App development happens on `telegram` branch. Main will be cleaned up in the future when ready to follow standard CI/CD conventions.

**Future migration path:** When main is ready, `telegram-prod` → `main`

**If asked to use main branch:** REFUSE and explain this policy. Suggest using `telegram`, `telegram-staging`, or `telegram-prod` instead.

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

## Defensive Programming

### Core Principle: Fail-Fast vs Silent Failure

**The fundamental rule: When something goes wrong, fail immediately and visibly.**

Silent failures (fallbacks that hide problems) violate CI/CD principles where each stage must validate before the next executes. A deployment pipeline that silently falls back to production when test infrastructure is missing defeats the entire purpose of testing.

### Configuration Validation Pattern

**Principle:** Validate required configuration on startup, not on first use.

Missing secrets or environment variables should cause immediate, loud failures with actionable error messages. This prevents cascading failures and misdiagnosis.

**Why this matters:**
- Missing `CLOUDFRONT_TEST_DISTRIBUTION_ID` → Silent fallback to APP CloudFront → Tests run against production → Wrong conclusions about bugs
- Missing `DATABASE_URL` → Application starts → First request fails → Users see errors
- Missing `API_KEY` → Silently degrades → Partial data returned → Data integrity issues

**Implementation locations (all complementary):**

| Layer | When to Validate | Example |
|-------|------------------|---------|
| CI/CD | Before deploying | GitHub Actions job fails if secrets missing |
| Application Startup | On import/initialization | `config.py` validates env vars, raises on missing |
| Test Setup | In pytest fixtures | `conftest.py` validates test env, skips if unavailable |
| Infrastructure | Terraform apply | Preconditions check outputs exist before use |

### Anti-Pattern: Silent Fallback

**Never use fallback logic that hides configuration errors in production paths.**

```yaml
# BAD: Silent fallback (from deploy.yml issue)
if [ -n "${TEST_DIST_ID}" ]; then
    # Invalidate TEST CloudFront
else
    echo "⚠️ TEST CloudFront not configured, using APP CloudFront"  # Silent warning
    # Falls back to APP ❌ Users see untested code!
fi

# GOOD: Fail-fast
if [ -z "${TEST_DIST_ID}" ]; then
    echo "❌ FATAL: CLOUDFRONT_TEST_DISTRIBUTION_ID not configured"
    echo "Cannot deploy without TEST CloudFront for E2E validation"
    exit 1  # Explicit failure
fi
```

**Why fallbacks are dangerous:**
- Production path (APP CloudFront) gets tested instead of new code (TEST CloudFront)
- Violates "TEST → Validate → Promote" pattern
- Creates false confidence: CI passes but tested wrong thing
- Debugging becomes harder: symptoms don't match actual problem

### When Fallbacks ARE Appropriate

**Fail-safe (graceful degradation) for expected failures users can tolerate:**

```python
# GOOD: Graceful degradation for external API timeout
def fetch_news(ticker: str) -> List[dict]:
    """Fetch news with timeout fallback"""
    try:
        return news_api.fetch(ticker, timeout=5)
    except TimeoutError:
        logger.warning(f"News API timeout for {ticker}, returning cached data")
        return cache.get_news(ticker) or []  # Stale data > no data

# BAD: Silent failure for critical system component
def fetch_user_portfolio(user_id: str) -> dict:
    """Fetch user portfolio"""
    try:
        return database.query(user_id)
    except DatabaseError:
        logger.warning("Database error, returning empty portfolio")  # ❌ Silent data loss!
        return {}  # User thinks they have no holdings
```

**Decision matrix:**

| Scenario | Strategy | Why |
|----------|----------|-----|
| Missing required config | Fail-Fast | Configuration errors should never reach production |
| External API timeout | Fail-Safe | Users tolerate stale data better than no data |
| Invalid user input | Fail-Fast | User needs to know input is rejected |
| Optional feature unavailable | Fail-Safe | Core functionality still works |

### Design by Contract

**Define preconditions explicitly and check them at system boundaries.**

**Trust Boundaries:** Everything outside is dangerous (validate), everything inside is safe (trust).

```python
# System boundary: API endpoint
def generate_report(ticker: str, user_id: str) -> dict:
    """
    Generate report for ticker.

    Preconditions:
        - ticker must be in supported ticker list
        - user_id must be authenticated

    Postconditions:
        - Returns dict with 'report' key
        - Never returns None (raises exception on failure)
    """
    # Validate at boundary
    if not is_ticker_supported(ticker):
        raise TickerNotSupportedError(ticker)  # Explicit failure

    if not is_authenticated(user_id):
        raise Unauthorized(user_id)  # Explicit failure

    # Inside boundary: trust inputs
    report = _generate_report_internal(ticker)  # No validation needed

    # Postcondition check
    assert 'report' in report, "Postcondition violated: missing 'report' key"
    return report

# Internal function: trusts caller
def _generate_report_internal(ticker: str) -> dict:
    """Internal: assumes ticker is valid (caller validated)"""
    # NO validation - waste of cycles, creates false confidence
```

**Why this works:**
- Validation cost paid once at boundary, not repeatedly
- Internal functions stay simple and fast
- Bugs caught at point of entry, not deep in call stack
- Clear contract: public functions validate, private functions trust

### Configuration Validation Examples

**GitHub Actions (validate-secrets job):**
```yaml
validate-secrets:
  name: Validate Required Secrets
  runs-on: ubuntu-latest
  steps:
    - name: Check required secrets
      run: |
        MISSING=()

        [ -z "${{ secrets.CLOUDFRONT_TEST_DISTRIBUTION_ID }}" ] && MISSING+=("CLOUDFRONT_TEST_DISTRIBUTION_ID")
        [ -z "${{ secrets.TELEGRAM_API_URL }}" ] && MISSING+=("TELEGRAM_API_URL")
        [ -z "${{ secrets.AWS_ACCESS_KEY_ID }}" ] && MISSING+=("AWS_ACCESS_KEY_ID")

        if [ ${#MISSING[@]} -gt 0 ]; then
          echo "❌ Missing required secrets:"
          printf '  - %s\n' "${MISSING[@]}"
          exit 1
        fi

        echo "✅ All required secrets configured"

deploy-frontend:
  needs: validate-secrets  # Won't run if secrets missing
```

**Python Application (config.py):**
```python
# src/config.py
import os
from typing import Optional

class ConfigurationError(Exception):
    """Raised when required configuration is missing"""
    pass

class Config:
    """Application configuration with validation"""

    def __init__(self):
        # Validate on initialization (fail-fast)
        self.openrouter_api_key = self._require("OPENROUTER_API_KEY")
        self.database_url = self._require("DATABASE_URL")

        # Optional configs with defaults
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_tracing = os.getenv("LANGSMITH_TRACING_V2", "false") == "true"

    def _require(self, var_name: str) -> str:
        """Get required environment variable or fail"""
        value = os.getenv(var_name)
        if not value:
            raise ConfigurationError(
                f"Missing required environment variable: {var_name}\n"
                f"Set it in .env or via Doppler: doppler secrets set {var_name}=<value>"
            )
        return value

# Module-level singleton (fails on import if misconfigured)
config = Config()  # ❌ Immediate failure if env vars missing
```

**Pytest Fixtures (conftest.py):**
```python
# tests/conftest.py
import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def validate_test_environment():
    """Validate test environment before running any tests"""
    required_vars = ["DATABASE_URL", "OPENROUTER_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        pytest.fail(
            f"Missing required test environment variables: {', '.join(missing)}\n"
            f"Run: doppler run -- pytest"
        )

@pytest.fixture
def skip_if_no_aurora():
    """Skip test if Aurora not configured (CI environment)"""
    if not os.getenv("AURORA_HOST"):
        pytest.skip("Aurora not configured - requires live database")
```

**Terraform Preconditions:**
```hcl
# terraform/frontend.tf
resource "aws_cloudfront_distribution" "webapp_test" {
  # ... configuration

  lifecycle {
    precondition {
      condition     = var.telegram_webapp_test_url != ""
      error_message = "telegram_webapp_test_url must be set in terraform.tfvars"
    }
  }
}

output "test_distribution_id" {
  description = "TEST CloudFront distribution ID for E2E testing"
  value       = aws_cloudfront_distribution.webapp_test.id

  precondition {
    condition     = aws_cloudfront_distribution.webapp_test.enabled
    error_message = "TEST CloudFront distribution must be enabled"
  }
}
```

### Defensive Checks in Code

**NASA's Power of Ten Rules (adapted):**
- Minimum 2 assertions per function (precondition + postcondition)
- Never ignore return values (check rowcount, API responses, subprocess exit codes)
- Limit nesting to 3 levels (deep nesting hides control flow)
- No recursion (for production critical paths - stack overflow risk)

**Example: Database operation with defensive checks:**
```python
def store_report(self, symbol: str, report_text: str) -> bool:
    """
    Store report in database.

    Returns:
        True if stored successfully, False otherwise

    Defensive checks:
        - Validates inputs (precondition)
        - Checks rowcount (MySQL FK/ENUM failures are silent)
        - Explicit return value (never undefined behavior)
    """
    # Precondition
    assert symbol and report_text, "symbol and report_text cannot be empty"

    # Execute
    try:
        cursor = self.client.execute(
            "INSERT INTO reports (symbol, text) VALUES (%s, %s)",
            (symbol, report_text)
        )
        rowcount = cursor.rowcount
    except Exception as e:
        logger.error(f"Database error storing {symbol}: {e}")
        return False  # Explicit failure

    # Postcondition check
    if rowcount == 0:
        logger.warning(f"INSERT affected 0 rows for {symbol} - FK constraint or ENUM mismatch?")
        return False  # Catch silent failures

    logger.info(f"✅ Stored report for {symbol}")
    return True  # Explicit success
```

### Observability: Empty States vs Conditional Rendering

**Principle:** Components should always render (with empty state), not disappear when data is missing.

**Why:**
- Observability: User sees component exists, knows data is missing (not a UI bug)
- Debugging: Can inspect DOM, check testid attributes
- UX: Better to show "No data available" than blank screen

```typescript
// GOOD: Always renders
export function MiniChart({ data }: ChartProps) {
  if (!data || data.length === 0) {
    return (
      <div data-testid="mini-chart" className="mini-chart--empty">
        <div className="empty-state">
          <div className="empty-state__icon">📊</div>
          <div className="empty-state__text">No chart data available</div>
        </div>
      </div>
    );
  }

  return <div data-testid="mini-chart">{/* chart rendering */}</div>;
}

// BAD: Conditional rendering (disappears from DOM)
export function MiniChart({ data }: ChartProps) {
  if (!data || data.length === 0) return null;  // ❌ Component vanishes
  return <div data-testid="mini-chart">{/* chart */}</div>;
}
```

### Input Validation (OWASP)

**Validate at system boundaries:**
- User input (API requests, form submissions)
- External APIs (third-party responses)
- File uploads
- Database queries (prevent SQL injection)

**Allowlist > Denylist:**
```python
# GOOD: Allowlist
ALLOWED_CATEGORIES = {'top_gainers', 'top_losers', 'volume_surge', 'trending'}

def get_rankings(category: str):
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")  # Explicit rejection
    return _fetch_rankings(category)

# BAD: Denylist (always incomplete)
BLOCKED_CATEGORIES = {'admin', 'internal'}

def get_rankings(category: str):
    if category in BLOCKED_CATEGORIES:  # What about future bad categories?
        raise ValueError(f"Blocked category: {category}")
    return _fetch_rankings(category)  # ❌ Allows unknown categories
```

### When to Use Assertions vs Exceptions

| Use Case | Tool | Example |
|----------|------|---------|
| Developer mistakes (bugs) | `assert` | `assert len(data) > 0, "data cannot be empty"` |
| User/external errors | `raise Exception` | `raise ValueError("Invalid ticker symbol")` |
| Preconditions (internal) | `assert` | `assert is_authenticated(user)` |
| Postconditions (verify correctness) | `assert` | `assert result['status'] == 'success'` |
| Production invariants | `if not ... raise` | `if rowcount == 0: raise DatabaseError(...)` |

**Why both:**
- Assertions disabled with `python -O` (production optimization)
- Exceptions always active (catch production issues)
- Assertions document assumptions (checked in development)
- Exceptions handle runtime conditions (checked always)

### Summary: Defensive Programming Checklist

**Configuration:**
- [ ] Validate required secrets in CI before deployment
- [ ] Validate env vars on application startup (fail-fast)
- [ ] Provide actionable error messages (how to fix)

**Error Handling:**
- [ ] No silent fallbacks for required components
- [ ] Explicit return values (never undefined behavior)
- [ ] Check database rowcount (MySQL fails silently)
- [ ] Log warnings before degrading (observability)

**Boundaries:**
- [ ] Validate all external inputs (user, API, files)
- [ ] Use allowlisting over denylisting
- [ ] Trust internal functions (validate once at boundary)

**Observability:**
- [ ] Components render empty states (don't disappear)
- [ ] Log configuration at startup
- [ ] Return detailed error responses (not generic "500 Internal Error")

**Testing:**
- [ ] Test both success and failure paths
- [ ] Verify tests can detect failures (test sabotage)
- [ ] Skip tests gracefully when infrastructure unavailable (not silent failure)

### References

- [Fail-Fast (Martin Fowler)](https://martinfowler.com/ieeeSoftware/failFast.pdf)
- [Design by Contract (Bertrand Meyer)](https://en.wikipedia.org/wiki/Design_by_contract)
- [NASA's Power of Ten Rules](https://en.wikipedia.org/wiki/The_Power_of_10:_Rules_for_Developing_Safety-Critical_Code)
- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Let It Crash Philosophy (Erlang)](http://verraes.net/2014/12/erlang-let-it-crash/)
- [Microsoft SDL](https://www.microsoft.com/en-us/securityengineering/sdl/practices)

---

## Code Organization

### Directory Structure
```
src/
├── agent.py              # Main LangGraph agent
├── types.py              # TypedDict definitions (AgentState)
├── config.py             # Configuration constants
├── data/                 # Data fetching, caching, database
├── analysis/             # Technical, comparative, strategy analysis
├── report/               # Report generation (prompts, context, generators)
│   ├── prompt_templates/ # LLM prompt templates (.txt files)
│   ├── mini_report_generator.py
│   └── synthesis_generator.py
├── workflow/             # LangGraph workflow nodes
├── scoring/              # Quality scoring (faithfulness, completeness, etc.)
├── integrations/         # LINE bot, Lambda handler
├── evaluation/           # LangSmith integration
├── formatters/           # Data formatting, PDF generation
└── utils/                # Utilities (vector store, strategy, etc.)

dr_cli/
├── main.py               # CLI entry point
└── commands/             # Command groups (dev, test, build, deploy, utils)

tests/
├── test_<module>.py      # Unit tests mirroring src/ structure
└── test_cli/             # CLI-specific tests
```

### Telegram Mini App Structure (Phase 3)
**New in Phase 3** - REST API layer for Telegram WebApp:

```
src/api/                        # Telegram API layer (FastAPI)
├── app.py                     # FastAPI application, CORS, endpoints
├── models.py                   # Pydantic request/response models
├── errors.py                   # Custom exceptions, error handlers
├── ticker_service.py          # Ticker search/validation (singleton)
├── rankings_service.py        # Market movers (4 categories, singleton)
├── peer_selector.py           # Peer comparison (correlation-based, singleton)
├── watchlist_service.py       # User watchlists (DynamoDB, singleton)
└── transformer.py             # Data transformation (AgentState → API models)
```

**Service Singleton Pattern:**
```python
# All services use this pattern for resource efficiency
_service_instance: Optional[ServiceClass] = None

def get_service_name() -> ServiceClass:
    global _service_instance
    if _service_instance is None:
        _service_instance = ServiceClass()
    return _service_instance
```

**Async/Sync Conventions:**
- **Async** for I/O operations (yfinance fetching, DynamoDB, external APIs)
- **Sync** for LangGraph nodes (required by framework)
- Pattern: `method_async()` for I/O, `method()` for pre-computed data

**Endpoints:**
- `GET /api/v1/search?q=NVDA` - Ticker search with autocomplete
- `POST /api/v1/report/{ticker}` - Start async report generation (returns job_id)
- `GET /api/v1/report/status/{job_id}` - Poll for report completion
- `GET /api/v1/rankings?category=top_gainers` - Market movers (4 categories)
- `GET /api/v1/watchlist/{user_id}` - User watchlist CRUD

**⚠️ Sync Report Endpoint Limitation:**
The sync `GET /api/v1/report/{ticker}` endpoint **will timeout** in production because:
- Report generation takes ~50-60s
- API Gateway HTTP API max timeout is 30s (AWS hard limit)
- Lambda timeout is 120s but API Gateway cuts connection at 30s

**Always use the async pattern:**
```bash
# 1. Start report generation (returns immediately)
curl -X POST "https://api.../api/v1/report/DBS19"
# → {"job_id": "rpt_xxx", "status": "pending"}

# 2. Poll for completion (every 5-10s)
curl "https://api.../api/v1/report/status/rpt_xxx"
# → {"status": "completed", "result": {...}}
```

**Running Telegram API:**
```bash
just dev-api                          # FastAPI server on :8001
dr --doppler dev api-server           # With Doppler secrets
curl http://localhost:8001/api/v1/health
```

### Telegram API Architecture Patterns

#### Service Singleton Pattern
All API services use module-level global singletons for resource efficiency:

```python
# Pattern used in ticker_service.py, rankings_service.py, peer_selector.py, watchlist_service.py
_service_instance: Optional[ServiceClass] = None

def get_service_name() -> ServiceClass:
    """Get or create global service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ServiceClass()
    return _service_instance
```

**Why:** Avoids expensive operations on every request:
- CSV file reloads (2000+ tickers)
- DynamoDB connection initialization
- yfinance ticker object creation

**Trade-offs:**
- ✅ Faster: Persists across Lambda invocations (cold start optimization)
- ✅ Simpler: No dependency injection container needed
- ❌ Less testable: Requires patching in tests

**When to use:**
- Services with expensive initialization (DB connections, file I/O)
- Lambda functions (container reuse optimization)
- Read-heavy services with cacheable state

#### Async/Sync Dual Architecture

Services provide both sync and async methods to handle LangGraph (sync) + FastAPI (async):

```python
# Pattern: Async for I/O-bound operations
async def get_rankings(self, category: str) -> List[RankingItem]:
    """Async version for FastAPI endpoints"""
    # Parallel fetching with asyncio.gather()
    tasks = [self._fetch_ticker_data(t) for t in tickers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return self._calculate_ranking(results)

# Pattern: Sync wrapper for LangGraph nodes
def get_rankings_sync(self, category: str) -> List[RankingItem]:
    """Sync version for LangGraph workflows"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(self.get_rankings(category))
```

**Executor Bridging Pattern** (for blocking I/O in async context):
```python
# Used in peer_selector.py, rankings_service.py
async def fetch_data_async(self, ticker: str):
    """Run blocking yfinance call in executor to avoid blocking event loop"""
    loop = asyncio.get_event_loop()
    # yfinance.download() is blocking - run in thread pool
    df = await loop.run_in_executor(None, yf.download, ticker, start, end)
    return df
```

**Why this pattern:**
- LangGraph nodes must be synchronous (framework requirement)
- FastAPI endpoints are async-first (better concurrency)
- yfinance/DynamoDB calls block - need executor bridge

#### Error Handling Hierarchy

Custom exception classes that create consistent API error responses:

```python
# src/api/errors.py - Base class
class APIError(Exception):
    """Base exception for all API errors"""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# Domain-specific errors
class TickerNotSupportedError(APIError):
    def __init__(self, ticker: str):
        super().__init__(
            "TICKER_NOT_SUPPORTED",
            f"Ticker '{ticker}' is not supported",
            400
        )

# FastAPI exception handler registration
@app.exception_handler(APIError)
async def api_exception_handler(request: Request, exc: APIError):
    envelope = ErrorEnvelope(
        error=ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=getattr(exc, 'details', None)
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump()
    )
```

**Benefits:**
- Consistent error format across all endpoints
- Type-safe error responses (Pydantic validation)
- Centralized error logging

#### Pydantic Model Conventions

Use `Field()` with descriptions for auto-generated OpenAPI documentation:

```python
# src/api/models.py patterns
class ReportResponse(BaseModel):
    # Field descriptions appear in OpenAPI/Swagger docs
    ticker: str = Field(..., description="Ticker symbol (e.g., NVDA19)")
    company_name: str = Field(..., description="Company name")

    # Use Literal for string unions (not Enum)
    stance: Literal["bullish", "bearish", "neutral"] = Field(
        ..., description="Market stance based on technical analysis"
    )

    # Use default_factory for mutable defaults
    peers: list[Peer] = Field(default_factory=list, description="Correlated peer companies")

    # Nested models for complex structures
    summary_sections: SummarySections
    technical_metrics: list[TechnicalMetric]
    fundamentals: Fundamentals
```

**Conventions:**
- ✅ Use `Field(..., description="")` for all public API fields
- ✅ Use `Literal["a", "b"]` for fixed string sets (not Enum)
- ✅ Use `default_factory=list` for mutable defaults (avoid `[]`)
- ✅ Use `Optional[Type]` + `Field(None, ...)` for nullable fields
- ✅ Nest models for logical grouping (SummarySections, TechnicalMetric)

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `MiniReportGenerator`)
- **Functions/Methods**: `snake_case()` (e.g., `generate_technical_mini_report()`)
- **Private Methods**: `_snake_case()` (e.g., `_format_technical_data()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `LOOKBACK_DAYS = 365`)
- **Type Definitions**: `PascalCase` TypedDict (e.g., `AgentState`)

### Module Organization Pattern
```python
# -*- coding: utf-8 -*-  # For files with Thai content
"""
Module description.

Detailed explanation of module purpose and key components.
"""

import standard_library
import third_party
from langchain_module import Component

from src.types import AgentState
from src.module import LocalComponent


class MainClass:
    """Class description."""

    def __init__(self, dependencies):
        """Initialize with dependencies."""
        self.dependency = dependencies

    def public_method(self, param: Type) -> ReturnType:
        """Public method with full docstring."""
        pass

    def _private_method(self, param: Type) -> ReturnType:
        """Private helper method (brief docstring)."""
        pass
```

### Data Layer & Caching Patterns

#### Three-Tier Caching Strategy

Multi-level caching with increasing persistence for optimal performance and cost:

```
Request → Tier 1: In-Memory (5-min TTL)
            ↓ miss
          Tier 2: SQLite (Local DB)
            ↓ miss
          Tier 3: S3 (Persistent Storage)
            ↓ miss
          Source: yfinance API / LLM generation
```

**Tier 1: In-Memory Cache** (`RankingsService._cache`)
```python
# src/api/rankings_service.py
class RankingsService:
    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache: Dict[str, List[RankingItem]] = {}
        self._cache_timestamp: Optional[datetime] = None

    async def get_rankings(self, category: str) -> List[RankingItem]:
        # Check cache freshness
        if self._is_cache_valid():
            return self._cache.get(category, [])
        # Fetch and cache
        results = await self._fetch_rankings(category)
        self._cache[category] = results
        self._cache_timestamp = datetime.now()
        return results
```

**Tier 2: SQLite Local Database** (`src/data/database.py`)
```python
# Lambda: /tmp/ticker_data.db (ephemeral, per-container)
# Local: data/ticker_data.db (persistent)
class TickerDatabase:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Auto-detect environment
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                db_path = "/tmp/ticker_data.db"  # Lambda ephemeral storage
            else:
                db_path = "data/ticker_data.db"  # Local persistent
```

**Tier 3: S3 Persistent Cache** (`src/data/s3_cache.py`)
```python
# Cache key structure: cache/{type}/{ticker}/{date}/{file}
# Example: cache/reports/NVDA19/2025-01-15/report.json
class S3Cache:
    def check_exists(self, cache_type: str, ticker: str, date: str) -> bool:
        """Fast HEAD request (no data transfer) with metadata check"""
        key = f"cache/{cache_type}/{ticker}/{date}/data.json"
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            # Check TTL in metadata
            metadata = response.get('Metadata', {})
            expires_at = metadata.get('expires_at')
            if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                return False  # Expired
            return True
        except ClientError:
            return False
```

**DynamoDB for User Data** (`src/api/watchlist_service.py`)
```python
# Persistent user preferences (watchlists)
# TTL: 365 days auto-expiration
class WatchlistService:
    def add_ticker(self, user_id: str, ticker: str) -> dict:
        item = {
            'user_id': user_id,           # Partition key
            'ticker': ticker,              # Sort key
            'added_at': datetime.now().isoformat(),
            'ttl': int((datetime.now() + timedelta(days=365)).timestamp())
        }
        self.table.put_item(Item=item)
```

**When to use each tier:**
- **In-Memory**: Frequently accessed data, short TTL (rankings, market data)
- **SQLite**: Historical ticker data, session cache, Lambda container reuse
- **S3**: Generated reports, long-lived cache, cross-invocation persistence
- **DynamoDB**: User state, watchlists, requires strong consistency

#### System Boundary Principle

**When crossing system boundaries (API ↔ Database), verify data type compatibility explicitly.**

Strict types like MySQL ENUMs fail silently on mismatch - no exception, data just doesn't persist. Always validate that values passed between systems match the expected type constraints on both sides.

#### Retry/Fallback Pattern

Data fetcher with three-level fallback for reliability:

```python
# src/data/data_fetcher.py
def fetch_ticker_data(self, ticker: str, period: str = "1y"):
    """Fetch with automatic fallback chain"""

    # Level 1: yfinance.history() with retries
    for attempt in range(3):
        try:
            hist = stock.history(period=period)
            if not hist.empty:
                logger.info(f"✅ Fetched {ticker} via yfinance (attempt {attempt+1})")
                return hist
        except Exception as e:
            logger.warning(f"⚠️ yfinance attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff

    # Level 2: Direct Yahoo Finance API
    try:
        hist = self._fetch_via_direct_api(ticker, period)
        if hist is not None:
            logger.info(f"✅ Fetched {ticker} via direct API")
            return hist
    except Exception as e:
        logger.warning(f"⚠️ Direct API failed: {e}")

    # Level 3: Database cache (stale data better than no data)
    try:
        hist = self.db.load_cached_data(ticker)
        if hist is not None:
            logger.info(f"✅ Using cached data for {ticker}")
            return hist
    except Exception as e:
        logger.error(f"❌ All fallbacks failed for {ticker}: {e}")

    return None  # All attempts failed
```

**Why this pattern:**
- External APIs are unreliable (rate limits, network issues)
- Graceful degradation: stale data > no data
- Exponential backoff prevents hammering services

---

## CLI Usage

### Two-Layer Design
**Justfile** (Intent layer - WHEN/WHY to run commands)
```bash
just dev          # Start local development server
just test-changes # Run tests before committing
just build        # Build deployment package
```

**dr CLI** (Implementation layer - HOW commands work)
```bash
dr --doppler dev server
dr test
dr build
```

### Universal dr CLI Patterns
```bash
# Global flags (before command)
dr --doppler <command>         # Run with Doppler env vars
dr --trace <command>           # Enable LangSmith tracing
dr --no-trace <command>        # Disable LangSmith tracing

# Command structure
dr <group> <command> [options]

# Examples
dr dev server                           # Start Flask dev server
dr test file test_agent.py             # Run specific test
dr util report DBS19 --strategy multi-stage  # Generate report
dr --doppler langsmith list-runs       # List LangSmith traces
dr build --minimal                      # Build minimal Lambda package
```

### Common Workflows
```bash
# Daily development
just daily                # Pull, setup, test

# Pre-commit
just pre-commit          # Syntax check + tests

# Testing
dr test                  # All tests
dr test file <file>      # Specific test
dr test integration DBS19 # Integration test

# Report generation
dr --doppler util report <TICKER>                    # Single-stage
dr --doppler util report <TICKER> --strategy multi-stage  # Multi-stage

# Build & deploy
just build               # Build Lambda package
just ship-it            # Build + deploy to AWS
```

---

## Code Style & Principles

### Docstring Style (Google Format)
```python
def analyze_ticker(self, ticker: str, strategy: str = "single-stage") -> str:
    """
    Main entry point to analyze ticker

    Args:
        ticker: Ticker symbol to analyze
        strategy: Report generation strategy - 'single-stage' or 'multi-stage' (default: 'single-stage')

    Returns:
        Generated report text in Thai

    Raises:
        ValueError: If ticker is invalid

    Example:
        >>> agent = TickerAnalysisAgent()
        >>> report = agent.analyze_ticker('DBS19', strategy='multi-stage')
    """
```

### Type Hints
```python
from typing import Dict, Any, List, Optional
from src.types import AgentState

def process_data(
    indicators: Dict[str, Any],
    percentiles: Dict[str, Any],
    news: List[Dict[str, Any]]
) -> Optional[str]:
    """Process data with full type hints"""
    pass
```

### Workflow State Management Patterns

#### TypedDict with Operator.add for Message Accumulation

LangGraph workflows use `TypedDict` with `Annotated` types for auto-merging:

```python
# src/types.py
from typing import TypedDict, Annotated, Sequence
from operator import add
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """Type-safe state dictionary for LangGraph workflow"""

    # Auto-append pattern: messages are concatenated, not replaced
    messages: Annotated[Sequence[BaseMessage], add]

    # Regular fields (replaced on update)
    ticker: str
    ticker_data: dict
    indicators: dict
    percentiles: dict
    news: list
    comparative_data: dict
    report: str
    strategy: str  # 'single-stage' or 'multi-stage'
    error: str     # Error propagation field
```

**How `operator.add` works:**
```python
# Without operator.add:
state["messages"] = [msg1]  # First node
state["messages"] = [msg2]  # Second node overwrites → [msg2]

# With Annotated[Sequence[BaseMessage], add]:
state["messages"] = [msg1]  # First node
state["messages"] = [msg2]  # Second node → [msg1, msg2] (concatenated)
```

#### Error Propagation Pattern

Workflow nodes accumulate errors in `state["error"]` instead of raising exceptions:

```python
# src/workflow/workflow_nodes.py
def fetch_data(self, state: AgentState) -> AgentState:
    """Always return state, even on error"""
    try:
        ticker = state["ticker"]
        data = self.data_fetcher.fetch_ticker_data(ticker)
        state["ticker_data"] = data
        logger.info(f"✅ Fetched data for {ticker}")
    except Exception as e:
        error_msg = f"Failed to fetch data: {e}"
        state["error"] = error_msg  # Set error, don't raise
        logger.error(f"❌ {error_msg}")

    return state  # Always return state

def generate_report(self, state: AgentState) -> AgentState:
    """Check for upstream errors before processing"""
    if state.get("error"):
        logger.warning("⚠️ Skipping report generation due to upstream error")
        return state  # Pass through error

    # Normal processing...
    report = self._generate(state)
    state["report"] = report
    return state
```

**Why this pattern:**
- Enables workflow to complete (collect all errors)
- Supports resumable workflows (can restart from failed node)
- Better observability (see full error chain in LangSmith traces)

#### State Evolution Through Workflow Nodes

Field ownership by workflow node:

```
Initial State:
  {ticker: "NVDA19", strategy: "multi-stage"}

↓ fetch_data()
  + ticker_data: {info, history, financials}

↓ analyze_technical()
  + indicators: {sma, rsi, macd, ...}
  + percentiles: {current_percentile, ...}

↓ fetch_news()
  + news: [{title, url, source}, ...]

↓ fetch_comparative_data()
  + comparative_data: {peers, sector, correlations}

↓ analyze_comparative_insights()
  + comparative_insights: {peer_analysis, sector_position}

↓ generate_chart()
  + chart_base64: "data:image/png;base64,..."

↓ generate_report()
  + report: "📊 วิเคราะห์หุ้น NVDA..."
  + mini_reports: {technical, fundamental, ...}  # If multi-stage

↓ score_report()
  + faithfulness_score: {score: 85, feedback: "..."}
  + completeness_score: {score: 90, feedback: "..."}

Final State:
  {all above fields + scores}
```

**Key Principles:**
- Each node owns specific fields (don't modify others' fields)
- Nodes are pure functions: `(state) -> state`
- State is immutable between nodes (create new dict if modifying)

#### LangSmith State Filtering

Remove non-serializable objects before tracing:

```python
# src/workflow/workflow_nodes.py
def _filter_state_for_langsmith(state: dict) -> dict:
    """
    Remove DataFrames with Timestamp indices (not JSON-serializable)

    LangSmith Error:
      "keys must be str, int, float, bool or None, not Timestamp"
    """
    cleaned = state.copy()

    # Remove DataFrame fields
    if "ticker_data" in cleaned and isinstance(cleaned.get("ticker_data"), dict):
        ticker_data_clean = {
            k: v for k, v in cleaned["ticker_data"].items()
            if k != "history"  # Remove pd.DataFrame
        }
        cleaned["ticker_data"] = ticker_data_clean

    # Remove comparative DataFrames
    if "comparative_data" in cleaned:
        cleaned["comparative_data"] = "<removed for tracing>"

    return cleaned

# Usage with @traceable decorator
from langsmith import traceable

@traceable(
    name="analyze_technical",
    process_inputs=_filter_state_for_langsmith,
    process_outputs=_filter_state_for_langsmith
)
def analyze_technical(self, state: AgentState) -> AgentState:
    # Node implementation
    return state
```

**Why filtering needed:**
- pandas DataFrames with `Timestamp` indices fail JSON serialization
- LangSmith traces require JSON-serializable state
- Filter only affects tracing, not actual workflow state

### Error Handling Pattern
**Workflow Nodes**: Use state-based error propagation
```python
def fetch_data(self, state: AgentState) -> AgentState:
    """Fetch ticker data"""
    try:
        data = self.fetcher.fetch(state["ticker"])
        state["ticker_data"] = data
    except Exception as e:
        error_msg = f"Failed to fetch data: {e}"
        state["error"] = error_msg
        logger.error(error_msg)
    return state
```

**Utility Functions**: Raise exceptions with descriptive messages
```python
def load_template(path: str) -> str:
    """Load prompt template"""
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding='utf-8')
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Usage
logger.info(f"   📝 Generating report for {ticker}")
logger.warning(f"   ⚠️  Failed to fetch news: {e}")
logger.error(f"   ❌ Error in workflow: {error}")
```

### JSON Serialization (numpy/pandas)
```python
def _make_json_serializable(self, obj):
    """Convert numpy/pandas/datetime objects to JSON-serializable types"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: self._make_json_serializable(v) for k, v in obj.items()}
    return obj
```

---

## Deployment

### Build Process
```bash
# Quick build
just build

# Minimal build (faster cold starts)
dr build --minimal

# Clean before build
just clean
just build
```

### Deployment Target
- **Platform**: AWS Lambda
- **Runtime**: Python 3.11
- **Architecture**: Serverless with API Gateway
- **Secrets**: Managed via Doppler

### Deployment Workflow
```bash
# 1. Pre-deployment checks
just pre-deploy         # Test + build

# 2. Deploy
just deploy-prod        # Deploy to Lambda

# 3. Setup webhook (if needed)
just setup-webhook      # Configure LINE webhook
```

### Lambda/Production Patterns

#### NumPy/Pandas JSON Serialization

Lambda responses must be JSON-serializable. Convert NumPy/Pandas types:

```python
# Pattern used in: mini_report_generator.py, transformer.py, all Lambda handlers
from datetime import datetime, date
import numpy as np
import pandas as pd

def _make_json_serializable(obj):
    """Convert numpy/pandas/datetime objects to JSON-serializable types"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # "2025-01-15T10:30:00"
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, np.integer):
        return int(obj)  # np.int64 → int
    elif isinstance(obj, np.floating):
        return float(obj)  # np.float64 → float
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # array → list
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    return obj

# Usage before JSON serialization
data = {
    'price': np.float64(150.5),
    'volume': np.int64(1000000),
    'date': pd.Timestamp('2025-01-15')
}
cleaned = _make_json_serializable(data)
json_str = json.dumps(cleaned)  # No serialization error
```

**Common Serialization Errors:**
```
❌ Object of type int64 is not JSON serializable
❌ Object of type float64 is not JSON serializable
❌ Object of type Timestamp is not JSON serializable
❌ Object of type ndarray is not JSON serializable
```

#### Cold Start Optimization

Optimize Lambda cold starts with module-level initialization:

```python
# src/agent.py - Module-level initialization
import logging
logger = logging.getLogger(__name__)

# Heavy imports at module level (loaded once per container)
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

# Service singletons (persist across invocations)
_agent_instance: Optional[TickerAnalysisAgent] = None

def get_agent() -> TickerAnalysisAgent:
    """Get or create agent singleton (cold start optimization)"""
    global _agent_instance
    if _agent_instance is None:
        logger.info("🚀 Cold start: Initializing agent...")
        _agent_instance = TickerAnalysisAgent()
        logger.info("✅ Agent initialized")
    return _agent_instance

# Lambda handler
def lambda_handler(event, context):
    agent = get_agent()  # Reuses existing instance if warm
    return agent.process(event)
```

**Cold Start Timeline:**
```
First invocation (cold):
  Container creation: ~2s
  Python runtime: ~500ms
  Import packages: ~3s
  Initialize services: ~2s
  Total: ~7.5s

Subsequent invocations (warm):
  Container reuse: 0s
  Singleton reuse: 0s
  Total: ~200ms (37x faster)
```

**Best Practices:**
- Import heavy libraries at module level (pandas, numpy, langchain)
- Use service singletons (CSV data, DB connections)
- Avoid re-reading static files (tickers.csv loaded once)
- Pre-compile regex patterns at module level

#### Environment Detection Pattern

Detect Lambda vs local environment for path/config decisions:

```python
# src/data/database.py
import os

def __init__(self, db_path: Optional[str] = None):
    if db_path is None:
        # Auto-detect environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            # Lambda: Use ephemeral /tmp storage
            db_path = "/tmp/ticker_data.db"
            logger.info("📦 Lambda environment: Using /tmp/ticker_data.db")
        else:
            # Local: Use persistent data directory
            db_path = "data/ticker_data.db"
            logger.info("💻 Local environment: Using data/ticker_data.db")

    self.db_path = db_path
```

**Lambda /tmp Limitations:**
- 512 MB max size
- Ephemeral (cleared on container recycle)
- Not shared across concurrent invocations
- Good for: SQLite cache, temp files, downloads
- Bad for: Persistent user data (use S3/DynamoDB)

#### Response Transformer Pattern

Convert internal workflow state to API response format:

```python
# src/api/transformer.py
class ResponseTransformer:
    """Transform AgentState (LangGraph) → Pydantic models (API)"""

    async def transform_report(
        self,
        state: AgentState,
        ticker_info: dict
    ) -> ReportResponse:
        """Extract structured data from workflow state"""

        # Extract stance from multiple sources
        stance_info = self._extract_stance(
            report_text=state["report"],
            indicators=state.get("indicators", {}),
            percentiles=state.get("percentiles", {})
        )

        # Parse Thai report text into structured sections
        summary_sections = self._extract_summary_sections(state["report"])

        # Build technical metrics from indicators
        technical_metrics = self._build_technical_metrics(
            state.get("indicators", {}),
            state.get("percentiles", {})
        )

        # Async peer lookup (correlation-based)
        peer_selector = get_peer_selector()
        peer_tickers = await peer_selector.find_peers_async(
            ticker=ticker_info['symbol'],
            max_peers=5
        )

        # Return structured Pydantic response
        return ReportResponse(
            ticker=ticker_info['symbol'],
            company_name=ticker_info['name'],
            stance=stance_info['stance'],
            summary_sections=summary_sections,
            technical_metrics=technical_metrics,
            peers=peer_tickers,
            generation_metadata=self._build_metadata(state)
        )

    def _extract_stance(self, report_text: str, indicators: dict, percentiles: dict) -> dict:
        """Multi-source stance extraction with fallback"""
        # Priority 1: Parse from Thai report text
        # Priority 2: Infer from technical indicators
        # Priority 3: Default to 'neutral'
```

**Pattern Benefits:**
- Separates internal representation (AgentState) from API contract (Pydantic)
- Async enrichment (peer lookup) without blocking workflow
- Multi-source data extraction with fallbacks
- Type-safe transformation (Pydantic validation)

### Environment Variables (via Doppler)
```bash
OPENAI_API_KEY          # OpenRouter API key
LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET
LANGSMITH_TRACING_V2    # 'true' or 'false'
LANGSMITH_API_KEY
```

### Production-Grade Deployment Conventions

#### Mental Model: Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                    TERRAFORM                                     │
│                 "State Management"                               │
├─────────────────────────────────────────────────────────────────┤
│ Declares WHAT infrastructure should exist:                       │
│   • ECR repository, Lambda function, API Gateway, DynamoDB      │
│ Idempotent: run 10 times → same result                          │
│ Question answered: "Does this infrastructure exist?"             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER PUSH                                   │
│                 "Code Availability"                              │
├─────────────────────────────────────────────────────────────────┤
│ Puts code somewhere it CAN be used (image in ECR with tag)      │
│ Question answered: "Is this code available to deploy?"           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DEPLOY SCRIPT                                   │
│                "Pointer Management"                              │
├─────────────────────────────────────────────────────────────────┤
│ Controls WHICH code is active:                                   │
│   1. update-function-code → moves $LATEST pointer               │
│   2. smoke test → validates new code works                       │
│   3. publish-version → creates immutable snapshot                │
│   4. update-alias → moves "live" pointer (users see new code)   │
│ Question answered: "Which code should users get?"                │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle:** "Not moving pointer = no conflict"
- The `live` alias is the contract with API Gateway
- Until you move that pointer, users get the old code
- New code can exist in $LATEST without affecting production

#### Lambda Versioning & Alias Strategy

```
$LATEST (mutable)          ← New code lands here first
    │
    │ test passes?
    ▼
Version N (immutable)      ← Snapshot created via publish-version
    │
    ▼
"live" alias               ← API Gateway invokes this
```

**Why this matters:**
- `$LATEST` is a staging area for testing
- Versions are immutable snapshots (can't be changed)
- Alias is the pointer that controls production traffic
- Terraform uses `ignore_changes = [function_version]` to let deploy scripts control the alias

#### Deployment Methods

**Primary: GitHub Actions** (`.github/workflows/deploy.yml`)
- Triggered automatically on push to `telegram` branch
- Implements zero-downtime pattern inline (~300 lines)
- Tests $LATEST via `aws lambda invoke` before promoting

**Backup: Manual Script** (`scripts/deploy-backend.sh`)
- For manual deployments outside CI/CD
- Same zero-downtime pattern
- Usage: `ENV=dev ./scripts/deploy-backend.sh`

**Why CI/CD doesn't call the script:**
The script was created for manual use. GitHub Actions implements the same
pattern inline for better error handling and step visibility in the UI.

#### CI/CD Strategy: Auto-Progressive Deployment

**Single branch triggers deployment to ALL environments:**

```yaml
on:
  push:
    branches:
      - telegram  # Only trigger - auto-chains dev → staging → prod
    paths:
      - 'src/**'
      - 'frontend/telegram-webapp/**'
      - 'Dockerfile*'
      - 'requirements*.txt'
      - 'terraform/**'
```

**⚠️ Path Filter Implications - What Does NOT Trigger Deployment:**

| File Change | Triggers Deploy? | Why |
|-------------|------------------|-----|
| `tests/*.py` | ❌ No | Tests don't affect production code |
| `docs/*.md` | ❌ No | Documentation is git-only |
| `.claude/CLAUDE.md` | ❌ No | Dev instructions, not runtime |
| `.github/workflows/*.yml` | ❌ No | CI config (but runs on next trigger) |

**Consequence:** If you ONLY change test files and want CI to run, you must:
1. Include a trivial change to a path-filtered file (e.g., comment in `src/`)
2. Or manually trigger the workflow: `gh workflow run deploy.yml`

**Pipeline Flow:**
```
git push to telegram
       ↓
┌──────────────────┐
│   Quality Gates  │  Unit tests, syntax check, security audit
└────────┬─────────┘
         ↓
┌──────────────────┐
│   Build Image    │  Docker build → ECR (one image for all envs)
└────────┬─────────┘
         ↓
┌──────────────────┐
│   Deploy Dev     │  update-function-code → smoke test → promote
└────────┬─────────┘
         ↓ (only if dev succeeds)
┌──────────────────┐
│  Deploy Staging  │  update-function-code → smoke test → promote
└────────┬─────────┘
         ↓ (only if staging succeeds)
┌──────────────────┐
│   Deploy Prod    │  update-function-code → smoke test → promote
└──────────────────┘
```

**Key Points:**
- NO terraform in CI/CD (infrastructure assumed to exist)
- Same Docker image promoted through all environments
- Zero-downtime: test $LATEST before updating "live" alias
- Auto-progressive: no manual gates between environments

#### Rollback Strategy

```bash
# Instant rollback - just move the alias pointer
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-dev \
  --name live \
  --function-version <previous-version-number>
```

No rebuild needed - previous versions are immutable snapshots.

#### When to Deploy vs When NOT to Deploy

**Critical Rule: Match the action to the change type.**

There are THREE separate concerns that should NEVER be conflated:

| Concern | Trigger | Action | What Changes |
|---------|---------|--------|--------------|
| **Code/Test/Doc** | `tests/*.py`, `docs/*.md` | `git commit` only | Git history |
| **Infrastructure** | `terraform/*.tf` | `terraform apply` | AWS resources |
| **Application** | `src/*.py`, `frontend/*.js` | Deploy script | Running code |

**Decision Matrix:**

| If You Changed... | You Should... | You Should NOT... |
|-------------------|---------------|-------------------|
| `tests/*.py` | `git commit` | terraform apply, deploy script |
| `docs/*.md` | `git commit` | terraform apply, deploy script |
| `requirements*.txt` | `git commit` + rebuild image + deploy | terraform apply |
| `src/*.py` | `git commit` + deploy script | terraform apply (unless new AWS resources) |
| `terraform/*.tf` | `terraform plan/apply` | deploy script (unless code also changed) |
| `frontend/*.js` | `git commit` + `deploy-frontend.sh` | terraform apply |

**Anti-Pattern (Workflow Smell):**
```bash
# WRONG: Running terraform after editing tests
vim tests/test_e2e_frontend.py   # Only edited test file
terraform apply                   # Why? Tests don't affect infrastructure!
```

**Correct Pattern:**
```bash
# RIGHT: Just commit test changes
vim tests/test_e2e_frontend.py
git add tests/
git commit -m "Add E2E frontend tests"
# Done. No deployment needed.
```

**Why This Matters:**
- **Speed**: Don't wait for terraform apply when only tests changed
- **Safety**: Unnecessary deployments risk production incidents
- **Clarity**: Each action should have clear intent
- **Auditability**: Git history shows code changes, Terraform state shows infra changes

#### Deployment Monitoring Discipline

**CRITICAL: Never use `sleep X` to wait for deployments.**

Time-based waiting leads to incorrect conclusions:
- Too short: Conclude "bug exists" when deployment isn't done yet
- Too long: Waste time waiting for already-completed operations
- Variable: Same operation takes different time based on load/complexity

**Anti-Pattern (What causes misdiagnosis):**
```bash
# WRONG: Time-based waiting
./deploy.sh && sleep 60 && curl $API_URL  # ❌ Might not be ready
gh run list && sleep 120 && gh run view   # ❌ Guessing completion time

# WRONG: Checking "status: completed" without "conclusion: success"
gh run view 12345 --json status
# {"status": "completed"}  ← This does NOT mean success!
```

**Correct Pattern - Use Blocking Waiters:**

| Operation | Waiter Command | What It Does |
|-----------|----------------|--------------|
| Lambda code update | `aws lambda wait function-updated --function-name X` | Blocks until $LATEST is updated |
| CloudFront invalidation | `aws cloudfront wait invalidation-completed --distribution-id X --id Y` | Blocks until cache is purged |
| GitHub Actions run | `gh run watch <run-id> --exit-status` | Blocks AND returns proper exit code |
| Lambda publish version | `aws lambda wait function-active --function-name X` | Blocks until version is ready |

**AWS CLI Waiter Pattern:**
```bash
# Correct: Use AWS waiters (block until actual completion)
aws lambda update-function-code --function-name $FUNC --image-uri $IMAGE
aws lambda wait function-updated --function-name $FUNC  # ← Blocks until done
echo "Now Lambda is ACTUALLY updated"

# CloudFront invalidation
INVALIDATION_ID=$(aws cloudfront create-invalidation ... --query 'Invalidation.Id' --output text)
aws cloudfront wait invalidation-completed \
  --distribution-id $DIST_ID \
  --id $INVALIDATION_ID  # ← Blocks until cache is purged
```

**GitHub Actions Waiter Pattern:**
```bash
# Correct: Use --exit-status to get proper return code
gh run watch 12345 --exit-status  # Blocks AND exits non-zero on failure

# Or if you need JSON output after completion:
gh run watch 12345 --exit-status && gh run view 12345 --json conclusion

# ALWAYS check conclusion, not just status
gh run view 12345 --json status,conclusion --jq '{status, conclusion}'
# {"status": "completed", "conclusion": "success"}  ← Both matter!
```

**Completion vs Success - The Critical Distinction:**
```
status: completed  = "The workflow finished running"
conclusion: success = "The workflow achieved its goal"

A workflow can be:
- completed + success  → ✅ Deploy succeeded
- completed + failure  → ❌ Deploy failed (tests failed, build error, etc.)
- completed + cancelled → ⚠️ Someone cancelled it

NEVER assume completed = success!
```

**On Failure - Read Logs Before Concluding "Bug":**
```bash
# When something fails, check logs FIRST
gh run view 12345 --log-failed  # Shows only failed step logs

# For Lambda failures
aws logs tail /aws/lambda/$FUNCTION_NAME --since 5m

# For CloudWatch insights
aws logs filter-log-events \
  --log-group-name /aws/lambda/$FUNCTION_NAME \
  --filter-pattern "ERROR"
```

**Why This Discipline Matters:**
- **Accuracy**: Know when deployment is ACTUALLY done, not guessing
- **Debugging**: Don't chase phantom bugs that are just timing issues
- **Efficiency**: No wasted time on arbitrary sleep durations
- **Reliability**: CI/CD scripts fail properly when deployments fail

### AWS Infrastructure & Tagging Strategy

**Multi-App Resource Organization:**
Both LINE Bot and Telegram Mini App share AWS infrastructure with resources separated via tags:

**Tag Schema (All Resources):**
- `Project`: dr-daily-report
- `ManagedBy`: Terraform
- `Environment`: dev | staging | prod
- `Owner`: data-team
- `CostCenter`: engineering
- `App`: line-bot | telegram-api | shared
- `Component`: webhook-handler, rest-api, watchlist-storage, cache-storage, etc.

**Deployed Resources (Dev Environment):**
```bash
# Telegram Mini App (DynamoDB)
dr-daily-report-telegram-watchlist-dev  # User watchlists
dr-daily-report-telegram-cache-dev      # API response cache
dr-daily-report-dynamodb-access-dev     # IAM policy

# Shared Resources
line-bot-pdf-reports-*                  # S3 bucket for PDF storage (shared)

# LINE Bot (Production)
line-bot-ticker-report                  # Lambda function
line-bot-ticker-report-role             # IAM role
```

**Terraform Workflow (Layered):**
```bash
# Navigate to specific layer
cd terraform/layers/01-data          # or 02-platform, 03-apps/telegram-api, etc.

# Standard workflow
terraform init && terraform plan && terraform apply

# Check deployed resources by tag
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=App,Values=telegram-api
```

**Cost Tracking:**
Use AWS Cost Explorer with tag filters:
- `App = telegram-api` - Telegram Mini App costs
- `App = line-bot` - LINE Bot costs
- `App = shared` - Shared infrastructure costs
- `Component = *-storage` - All storage costs

See `terraform/TAGGING_POLICY.md` for complete documentation.

#### Multi-Environment CORS Configuration

API Gateway CORS is configured to allow multiple CloudFront origins for dev/staging/prod:

```hcl
# terraform/api_gateway.tf
cors_configuration {
  allow_origins = distinct(compact(concat(
    ["https://web.telegram.org", "https://t.me"],
    var.telegram_webapp_url != "" ? [var.telegram_webapp_url] : [],
    var.telegram_webapp_urls  # List of CloudFront URLs
  )))
}

# terraform/variables.tf
variable "telegram_webapp_urls" {
  description = "List of Telegram Mini App WebApp URLs (for CORS)"
  type        = list(string)
  default     = []
}

# terraform/terraform.dev.tfvars (and staging, prod)
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net",   # dev
  "https://d3uuexs20crp9s.cloudfront.net"   # staging
]
```

**Why:** Single `telegram_webapp_url` couldn't support multiple environments. The list
pattern allows staging frontend to call dev API during cross-environment testing.

#### Two-CloudFront Pattern for Zero-Risk Frontend Deployment

**Problem:** CloudFront cache invalidation is immediate - once you invalidate, users see
the new files. If the new frontend has bugs, users see broken UI before E2E tests can catch it.

**Solution:** Two CloudFront distributions per environment, both pointing to same S3 bucket:

```
                    S3 Bucket (single source)
                           │
          ┌────────────────┴────────────────┐
          │                                 │
    TEST CloudFront                   APP CloudFront
    (E2E testing)                     (User-facing)
          │                                 │
          ▼                                 ▼
   Invalidated FIRST              Invalidated ONLY after
   E2E tests run here              E2E tests pass
```

**Deployment Flow:**
```
1. S3 sync (files uploaded)
   ↓
2. Invalidate TEST CloudFront
   ↓
3. E2E tests run against TEST URL
   ↓
4. Tests pass? → Invalidate APP CloudFront
   Tests fail? → APP CloudFront unchanged (users see old version)
```

**Terraform Resources:**
```hcl
# terraform/frontend.tf
resource "aws_cloudfront_distribution" "webapp" {
  comment = "Telegram Mini App - ${var.environment}"  # User-facing
  # ... cache behaviors
}

resource "aws_cloudfront_distribution" "webapp_test" {
  comment = "Telegram Mini App TEST - ${var.environment} (E2E testing)"
  # Same S3 origin, same cache behaviors
  tags = { Purpose = "e2e-testing" }
}
```

**Outputs:**
- `webapp_url` - User-facing CloudFront URL
- `webapp_test_url` - E2E testing CloudFront URL
- `cloudfront_distribution_id` - APP CloudFront ID (for promotion)
- `cloudfront_test_distribution_id` - TEST CloudFront ID (for E2E)

**Deploy Script Usage:**
```bash
# Full deploy (S3 + both CloudFronts) - NOT recommended for CI
./scripts/deploy-frontend.sh dev

# CI/CD pattern (safe):
./scripts/deploy-frontend.sh dev --test-only  # S3 + TEST CloudFront
# ... run E2E tests ...
./scripts/deploy-frontend.sh dev --app-only   # APP CloudFront (after tests pass)
```

**GitHub Secrets Required (per environment):**
- `CLOUDFRONT_DISTRIBUTION_ID` - APP CloudFront ID
- `CLOUDFRONT_TEST_DISTRIBUTION_ID` - TEST CloudFront ID
- `CLOUDFRONT_DOMAIN` - APP CloudFront domain (for fallback)
- `CLOUDFRONT_TEST_DOMAIN` - TEST CloudFront domain (for E2E URL)

**Why This Pattern:**
- ✅ **Zero-Risk**: Users never see untested frontend code
- ✅ **Fast Rollback**: Don't invalidate APP = instant "rollback"
- ✅ **Mirrors Lambda Pattern**: TEST CloudFront = $LATEST, APP CloudFront = "live" alias
- ✅ **Same Infrastructure**: Both CloudFronts use same S3 bucket (no duplication)

**Trade-offs:**
- ❌ **Cost**: 2x CloudFront distributions per environment
- ❌ **Complexity**: More secrets, more invalidation steps
- ✅ **Overall**: Safety > cost for production deployments

### Infrastructure TDD Workflow - MANDATORY

**CRITICAL:** When modifying ANY terraform files (`terraform/*.tf`), you MUST follow this workflow. Do NOT skip steps.

```
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE TDD FLOW                       │
│                                                                  │
│  1. terraform plan        →  Generate plan                      │
│  2. conftest test         →  OPA policy validation (GATE)       │
│  3. terraform apply       →  Only if OPA passes                 │
│  4. go test (Terratest)   →  Verify infra works                 │
└─────────────────────────────────────────────────────────────────┘
```

**Step-by-Step Commands:**
```bash
cd terraform

# 1. Generate terraform plan
doppler run -- terraform plan -out=tfplan.binary -var-file=envs/dev/terraform.tfvars

# 2. OPA Policy Validation (MUST PASS before apply)
terraform show -json tfplan.binary > tfplan.json
conftest test tfplan.json -p policies/

# 3. Apply ONLY if OPA passes
doppler run -- terraform apply tfplan.binary

# 4. Post-apply verification with Terratest
cd tests && go test -v -timeout 10m
```

**What Each Step Catches:**

| Step | Tool | Catches |
|------|------|---------|
| Pre-apply | OPA/Conftest | IAM overpermission, missing tags, security misconfig |
| Post-apply | Terratest | Lambda doesn't start, API Gateway misconfigured, wrong schedule |

**When to Skip (NEVER for production changes):**
- ❌ NEVER skip OPA for production (`terraform/envs/prod/`)
- ⚠️ May skip Terratest locally if CI will run it
- ✅ Can skip for pure documentation changes in terraform/

**Justfile Recipes:**
```bash
just opa-validate dev      # Run OPA against dev plan
just terratest             # Run Terratest integration tests
just infra-tdd dev         # Full cycle: plan → OPA → apply → Terratest
```

**Anti-Pattern (What NOT to Do):**
```bash
# WRONG: Skipping OPA validation
terraform plan -var-file=envs/dev/terraform.tfvars
terraform apply -auto-approve  # ❌ No OPA check!

# WRONG: Reactive error fixing without re-validating
terraform apply  # fails
# fix error manually
terraform apply  # ❌ Should re-run OPA on new plan!
```

---

### Terraform Architecture

```
terraform/
├── *.tf                    # All resources (~10 files, ~1,800 lines)
├── envs/                   # Environment-specific config
│   ├── dev/
│   │   ├── backend.hcl     # S3 state: telegram-api/dev/terraform.tfstate
│   │   └── terraform.tfvars # memory=512, environment="dev"
│   ├── staging/
│   │   ├── backend.hcl
│   │   └── terraform.tfvars
│   └── prod/
│       ├── backend.hcl
│       └── terraform.tfvars
└── layers/                 # DEPRECATED - was used for initial bootstrap
```

**Deployment Workflow:**
```bash
# From terraform/ directory
terraform init -backend-config=envs/dev/backend.hcl
terraform plan -var-file=envs/dev/terraform.tfvars
terraform apply -var-file=envs/dev/terraform.tfvars

# Switch environments (must reconfigure backend)
terraform init -backend-config=envs/staging/backend.hcl -reconfigure
terraform apply -var-file=envs/staging/terraform.tfvars
```

**Key Principle:** Same .tf code for all environments, different tfvars values.

**Why no layers?** Layered terraform is premature optimization at <100 resources.
Current scale (~50 resources) doesn't justify the complexity of cross-layer state references.

### Multi-Environment Deployment

#### How It Works

```
Same Code + Different Variables = Different Environments

terraform/*.tf (SHARED)          envs/{env}/terraform.tfvars (DIFFERENT)
─────────────────────────        ─────────────────────────────────────
resource "aws_lambda" {          # dev
  memory = var.lambda_memory  →  lambda_memory = 512
}                                environment = "dev"

                                 # staging
                                 lambda_memory = 1024
                                 environment = "staging"

                                 # prod
                                 lambda_memory = 1024
                                 environment = "prod"
```

#### State Isolation

Each environment has its own state file (prevents cross-env accidents):
- `s3://dr-daily-report-tf-state/telegram-api/dev/terraform.tfstate`
- `s3://dr-daily-report-tf-state/telegram-api/staging/terraform.tfstate`
- `s3://dr-daily-report-tf-state/telegram-api/prod/terraform.tfstate`

#### When to Run Terraform vs CI/CD

| Change Type | Tool | Example |
|-------------|------|---------|
| Code only | CI/CD auto-deploys | Fix bug in rankings_service.py |
| Infra change | Manual `terraform apply` | Increase Lambda memory |
| New resource | `terraform apply` → then CI/CD | Add new DynamoDB table |

**Drift Prevention:** After applying to dev, remember to apply to staging and prod too.

#### Environment Configuration Differences

| Config | Dev | Staging | Prod |
|--------|-----|---------|------|
| Lambda Memory | 512 MB | 1024 MB | 1024 MB |
| Log Retention | 7 days | 14 days | 30 days |
| API Throttling | 10 req/s | 50 req/s | 100 req/s |

#### Deployment Commands

```bash
# Apply to dev
cd terraform
terraform init -backend-config=envs/dev/backend.hcl
terraform apply -var-file=envs/dev/terraform.tfvars

# Apply to staging (reconfigure backend first)
terraform init -backend-config=envs/staging/backend.hcl -reconfigure
terraform apply -var-file=envs/staging/terraform.tfvars

# Apply to prod
terraform init -backend-config=envs/prod/backend.hcl -reconfigure
terraform apply -var-file=envs/prod/terraform.tfvars
```

#### ⚠️ Terraform State Lock Discipline - CRITICAL

**The state lock protects Terraform state from concurrent modifications. Respect it.**

**What the lock means:**
- A `terraform apply` or `terraform import` is **actively running**
- It's making changes to remote state in S3
- Interrupting it can corrupt state

**NEVER do these:**
- ❌ Run `terraform force-unlock` because an operation is "taking too long"
- ❌ Start a new `terraform apply` while another is running
- ❌ Run multiple terraform commands in parallel (background jobs)
- ❌ Assume a slow operation has "stalled" - Lambda permissions can take 5+ minutes

**When is force-unlock appropriate?**
- ✅ The terraform process crashed (kill -9, network disconnect, machine reboot)
- ✅ The process that acquired the lock no longer exists (verify with `ps aux | grep terraform`)
- ✅ The lock is orphaned (AWS console shows no active operations)

**Correct workflow:**
```bash
# 1. Start apply (FOREGROUND, not background)
doppler run -- terraform apply -var-file=envs/dev/terraform.tfvars

# 2. WAIT for it to complete (even if it takes 10+ minutes)
# Some resources like Lambda permissions take a long time

# 3. Only then start another operation
doppler run -- terraform import ...
```

**If you hit a lock error:**
```bash
# FIRST: Check if terraform is still running
ps aux | grep terraform

# If process exists: WAIT for it to finish
# If process is dead: THEN force-unlock
terraform force-unlock <lock-id>
```

**Why this matters:**
- Force-unlocking an active operation can corrupt state
- Corrupted state requires manual recovery (terraform state rm/import)
- State corruption can cause resources to be orphaned or recreated

#### Infrastructure TDD Workflow

**Tests are the source of truth for infrastructure verification.**

When you need to verify infrastructure state (e.g., "is the SQS → Lambda trigger connected?"), first look at the Terratest tests. If tests don't answer the question, that's a TDD opportunity to expand coverage.

**Core Principle:**
> "If you can't find the answer by looking at the test, it means test coverage has room to improve and that's a good time to do TDD to expand the coverage."

**Workflow:**
```
1. Tests define expected infrastructure state
         ↓
2. Run tests → see failures (RED)
         ↓
3. terraform plan → OPA/Conftest validation
         ↓
4. terraform apply → make infrastructure changes
         ↓
5. Run tests → verify fixes (GREEN)
```

**Directory Structure:**
```
terraform/
├── tests/
│   ├── sqs_worker_test.go      # SQS → Lambda integration
│   ├── api_gateway_test.go     # API Gateway endpoints
│   └── iam_test.go             # IAM policies/roles
├── policies/
│   └── terraform.rego          # OPA policies for plan validation
└── *.tf                        # Terraform configurations
```

**Example: Testing SQS → Lambda Trigger:**
```go
// terraform/tests/sqs_worker_test.go
func TestSQSLambdaTrigger(t *testing.T) {
    // Verify event source mapping exists
    mappings := aws.LambdaListEventSourceMappings(t, region, functionName)
    assert.NotEmpty(t, mappings, "No event source mappings found")

    // Verify correct queue is connected
    for _, m := range mappings {
        if strings.Contains(*m.EventSourceArn, queueName) {
            assert.Equal(t, "Enabled", *m.State)
            return
        }
    }
    t.Errorf("Queue %s not found in event source mappings", queueName)
}
```

**Running Infrastructure Tests:**
```bash
# Run all infrastructure tests
cd terraform && go test -v ./tests/...

# Run specific test
go test -v -run TestSQSLambdaTrigger ./tests/...

# With timeout (infrastructure tests can be slow)
go test -v -timeout 5m ./tests/...
```

**Anti-Patterns:**
- ❌ Using `aws CLI` commands to manually verify infrastructure state
- ❌ Checking AWS Console for verification
- ❌ Running ad-hoc queries instead of adding test coverage
- ✅ Writing a test that verifies the expected state
- ✅ Using tests as living documentation of infrastructure contracts

**When Tests Fail:**
1. Read the error message carefully
2. Check if resource exists but isn't in Terraform state → `terraform import`
3. Check if resource needs to be created → update `.tf` files
4. Apply changes: `doppler run -- terraform apply -var-file=envs/dev/terraform.tfvars`
5. Re-run tests to verify fix

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

### Why Layered Terraform Architecture

**Decision:** Use layered architecture with S3 remote state instead of flat structure.

```
terraform/layers/
├── 00-bootstrap/    # State bucket, DynamoDB locks (manual bootstrap)
├── 01-data/         # DynamoDB tables, data policies
├── 02-platform/     # ECR, S3 buckets, shared infra
└── 03-apps/         # Application-specific resources
    ├── telegram-api/    # Lambda + API Gateway
    └── line-bot/        # Lambda + Function URL
```

**Rationale:**
- ✅ **Independent Deployability**: Update apps without touching data layer
- ✅ **Blast Radius Isolation**: Failed apply in one layer doesn't affect others
- ✅ **Team Collaboration**: Different teams can own different layers
- ✅ **Clear Dependencies**: Explicit layer order (data → platform → apps)
- ✅ **State Size**: Smaller state files = faster plans, less lock contention

**Trade-offs:**
- ❌ **More Files**: ~4x more .tf files than flat structure
- ❌ **Cross-Layer Complexity**: Must use `terraform_remote_state` for dependencies
- ❌ **Deploy Order**: Must deploy in dependency order (can't parallelize)
- ✅ **Overall**: Safety + isolation > fewer files

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

## Reference Examples

### Example: Adding a New Scorer
```python
# 1. Create tests/test_new_scorer.py
class TestNewScorer:
    def test_score_calculation(self):
        scorer = NewScorer()
        result = scorer.score(report="test", context={})
        assert 0 <= result['score'] <= 100

# 2. Implement src/scoring/new_scorer.py
class NewScorer:
    """New scoring metric"""

    def score(self, report: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate new score

        Args:
            report: Generated report text
            context: Analysis context

        Returns:
            Score dict with 'score', 'feedback', 'passed'
        """
        score = self._calculate(report, context)
        return {
            'score': score,
            'feedback': f"Score: {score}/100",
            'passed': score >= 70
        }

# 3. Integrate into workflow_nodes.py
self.new_scorer = new_scorer
score = self.new_scorer.score(state["report"], context)
state["new_score"] = score

# 4. Add to AgentState in src/types.py
class AgentState(TypedDict):
    # ... existing fields
    new_score: dict
```

### Example: Adding CLI Command
```python
# dr_cli/commands/utils.py
@utils.command()
@click.argument('ticker')
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
@click.pass_context
def analyze(ctx, ticker, format):
    """Analyze ticker with custom format

    Examples:
      dr util analyze DBS19
      dr util analyze DBS19 --format json
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = [
        sys.executable, "-c",
        f"from src.agent import TickerAnalysisAgent; "
        f"agent = TickerAnalysisAgent(); "
        f"print(agent.analyze_ticker('{ticker}', format='{format}'))"
    ]
    # ... execute command
```

### Example: Adding to Justfile
```bash
# justfile
# Analyze ticker with custom options
analyze TICKER FORMAT="text":
    @echo "📊 Analyzing {{TICKER}} with format {{FORMAT}}..."
    dr --doppler util analyze {{TICKER}} --format {{FORMAT}}
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start dev server | `just dev` or `dr --doppler dev server` |
| Run all tests | `just test-changes` or `dr test` |
| Run specific test | `dr test file <filename>` |
| Generate report | `dr --doppler util report <TICKER>` |
| Build Lambda package | `just build` or `dr build` |
| Check syntax | `just check` |
| Clean artifacts | `just clean` |
| View project structure | `just tree` |
| LangSmith traces | `dr --doppler langsmith list-runs` |
| Deploy code | `git push origin telegram` (CI/CD auto-deploys to all envs) |
| Deploy infra to dev | `cd terraform && terraform init -backend-config=envs/dev/backend.hcl && terraform apply -var-file=envs/dev/terraform.tfvars` |
| Deploy infra to staging | `terraform init -backend-config=envs/staging/backend.hcl -reconfigure && terraform apply -var-file=envs/staging/terraform.tfvars` |
| Deploy infra to prod | `terraform init -backend-config=envs/prod/backend.hcl -reconfigure && terraform apply -var-file=envs/prod/terraform.tfvars` |
| Check TF state | `terraform state list` |
| Rollback Lambda | `./scripts/rollback.sh <env> <version>` (e.g., `./scripts/rollback.sh dev 5`) |
| OPA validate | `just opa-validate dev` |
| Run Terratest | `just terratest` |
| Full infra TDD | `just infra-tdd dev` (OPA → apply → Terratest) |

**Key Files to Know:**
- `src/agent.py` - Main LangGraph agent
- `src/workflow/workflow_nodes.py` - Workflow implementation
- `src/types.py` - TypedDict state definitions
- `justfile` - Intent-based command recipes
- `dr_cli/main.py` - CLI entry point
