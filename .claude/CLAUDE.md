# Daily Report LINE Bot - Development Guide

**Project**: AI-powered Thai language financial ticker analysis bot
**Stack**: Python 3.11+, LangGraph, OpenRouter, AWS Lambda, LINE Messaging API
**Architecture**: Serverless LangGraph agent with multi-stage LLM generation

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

---

## Testing Guidelines

### Test Organization
```
tests/
├── test_<component>.py      # Unit tests for src components
├── test_cli/                 # CLI command tests
├── test_line_*.py           # LINE bot integration tests
└── test_*_integration.py    # Integration/E2E tests
```

### Testing Framework
- **Framework**: pytest (no explicit config, using defaults)
- **Mocking**: `unittest.mock.Mock` for LLM responses, external APIs
- **Fixtures**: Use `@pytest.fixture` for reusable test setup
- **Assertions**: Prefer explicit checks over broad assertions

### Test Structure Pattern
```python
# -*- coding: utf-8 -*-
"""
Tests for <Component>

Brief description of what's being tested.
"""

import pytest
from unittest.mock import Mock
from src.module import Component


class TestComponent:
    """Test suite for Component"""

    @pytest.fixture
    def mock_dependency(self):
        """Create mock dependency"""
        dependency = Mock()
        dependency.method = Mock(return_value="expected")
        return dependency

    def test_<functionality>_<scenario>(self, mock_dependency):
        """Test that <functionality> works when <scenario>"""
        # Arrange
        component = Component(mock_dependency)
        input_data = {'key': 'value'}

        # Act
        result = component.method(input_data)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        mock_dependency.method.assert_called_once()
```

### Testing Scope
- **Unit Tests**: All src/ components (generators, analyzers, scorers)
- **Integration Tests**: Workflow nodes, end-to-end ticker analysis
- **CLI Tests**: Command parsing, flag handling
- **LINE Tests**: Message handling, follow/unfollow, fuzzy matching

### TDD Approach
1. Write test first for new functionality
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Add edge case tests

### Running Tests
```bash
# All tests
dr test
just test-changes

# Specific file
dr test file test_multistage_generation.py

# Specific test type
dr test line follow
dr test integration DBS19

# Pre-commit checks
just pre-commit
```

### Async Testing Patterns

For testing async services (Telegram API, rankings, peer selector):

#### pytest-asyncio Setup

```python
# tests/test_rankings_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

class TestRankingsService:
    """Test async rankings service"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return RankingsService(cache_ttl_seconds=300)

    @pytest.mark.asyncio  # Required for async tests
    async def test_fetch_rankings(self, service):
        """Test async ranking fetch"""
        # Arrange
        with patch('yfinance.Ticker') as mock_yf:
            mock_ticker = Mock()
            mock_ticker.info = {'regularMarketPrice': 150.0}
            mock_yf.return_value = mock_ticker

            # Act
            results = await service.get_rankings('top_gainers', limit=10)

            # Assert
            assert len(results) <= 10
            assert all(isinstance(r, RankingItem) for r in results)
```

#### Async Fixture Pattern

```python
@pytest.fixture
async def async_service():
    """Async fixture with setup/teardown"""
    service = WatchlistService(use_local=True)
    await service.initialize()  # Async setup

    yield service

    await service.cleanup()  # Async teardown
```

#### Mocking Async Functions

```python
# Pattern 1: Mock async method with AsyncMock
async def test_with_async_mock(service):
    with patch.object(service, 'fetch_data_async', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {'ticker': 'NVDA19', 'price': 150.0}

        result = await service.process_ticker('NVDA19')

        mock_fetch.assert_called_once_with('NVDA19')
        assert result['ticker'] == 'NVDA19'

# Pattern 2: Mock blocking I/O in executor
@patch('yfinance.download')
async def test_with_executor(mock_download, service):
    """Mock blocking yfinance call"""
    mock_download.return_value = pd.DataFrame({'Close': [100, 101, 102]})

    # Service uses loop.run_in_executor() internally
    result = await service.fetch_data_async('NVDA19')

    assert not result.empty
    mock_download.assert_called_once()
```

#### Testing asyncio.gather() Patterns

```python
@pytest.mark.asyncio
async def test_parallel_fetching(service):
    """Test parallel ticker fetching with gather()"""
    tickers = ['NVDA19', 'JPMUS19', 'DBS19']

    with patch.object(service, '_fetch_ticker_data', new_callable=AsyncMock) as mock_fetch:
        # Mock returns different values for each ticker
        mock_fetch.side_effect = [
            {'ticker': 'NVDA19', 'price': 150},
            {'ticker': 'JPMUS19', 'price': 50},
            {'ticker': 'DBS19', 'price': 25}
        ]

        # Service internally uses: await asyncio.gather(*tasks)
        results = await service.fetch_all(tickers)

        assert len(results) == 3
        assert mock_fetch.call_count == 3
```

**Key Patterns:**
- Use `@pytest.mark.asyncio` for all async test functions
- Use `AsyncMock` (not `Mock`) for async methods
- Use `new_callable=AsyncMock` in `patch()` for async patches
- Mock executor-based I/O at the blocking function level (e.g., `yf.download`)

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
- `GET /api/v1/report/{ticker}` - Full AI analysis report with peers
- `GET /api/v1/rankings?category=top_gainers` - Market movers (4 categories)
- `GET /api/v1/watchlist/{user_id}` - User watchlist CRUD

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

### Terraform Layered Architecture

**Layer Structure:** `terraform/layers/{00-bootstrap,01-data,02-platform,03-apps/*}`

**Key Pattern - Cross-Layer Dependencies:**
```hcl
# In app layer, reference outputs from lower layers via remote state
data "terraform_remote_state" "data" {
  backend = "s3"
  config = {
    bucket = "dr-daily-report-tf-state"
    key    = "layers/01-data/terraform.tfstate"  # State key path
    region = "ap-southeast-1"
  }
}

locals {
  # Consume outputs from lower layer
  dynamodb_policy_arn = data.terraform_remote_state.data.outputs.dynamodb_policy_arn
}
```

**Per-Layer Workflow:** `cd terraform/layers/XX-layer && terraform init && terraform plan && terraform apply`

**Deploy Order:** 01-data → 02-platform → 03-apps/* (respect dependencies)

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
| Deploy to AWS | `just ship-it` |
| Check syntax | `just check` |
| Clean artifacts | `just clean` |
| View project structure | `just tree` |
| LangSmith traces | `dr --doppler langsmith list-runs` |

**Key Files to Know:**
- `src/agent.py` - Main LangGraph agent
- `src/workflow/workflow_nodes.py` - Workflow implementation
- `src/types.py` - TypedDict state definitions
- `justfile` - Intent-based command recipes
- `dr_cli/main.py` - CLI entry point
