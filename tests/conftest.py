# -*- coding: utf-8 -*-
"""
Pytest Configuration and Shared Fixtures

This file configures pytest for the test suite, including:
- pytest-asyncio configuration for async tests
- Custom markers (unit, integration, smoke, slow)
- Shared fixtures for mocking services
"""

import os
import sys
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


###############################################################################
# pytest-asyncio Configuration
###############################################################################

# Configure pytest-asyncio to use auto mode (automatically detect async tests)
pytest_plugins = ['pytest_asyncio']


def pytest_addoption(parser):
    """Add custom CLI options"""
    parser.addoption(
        "--run-ratelimited",
        action="store_true",
        default=False,
        help="Run tests that are paused due to API rate limits"
    )
    parser.addoption(
        "--tier",
        action="store",
        default=None,
        type=int,
        choices=[0, 1, 2, 3, 4],
        help="Test tier: 0=unit, 1=mocked (default), 2=+integration, 3=+smoke, 4=+e2e"
    )


def pytest_configure(config):
    """Configure custom markers, handle --tier override, and log environment.

    Markers defined here are for documentation only (actual markers defined in pytest.ini).
    The main purpose is to handle --tier flag which needs to override addopts marker filter.
    """
    # ============================================================
    # ENVIRONMENT LOGGING
    # ============================================================
    # Log critical environment variables at test start to make
    # configuration issues obvious (no more guessing what's set)
    print("\n" + "="*60)
    print("TEST ENVIRONMENT")
    print("="*60)

    # API Configuration (critical for smoke tests)
    api_url = os.environ.get("TELEGRAM_API_URL", "http://localhost:8001")
    source = "env var" if "TELEGRAM_API_URL" in os.environ else "DEFAULT (localhost)"
    print(f"TELEGRAM_API_URL: {api_url}")
    print(f"  Source: {source}")

    # Doppler Detection
    doppler_config = os.environ.get("DOPPLER_CONFIG", "NOT SET")
    doppler_env = os.environ.get("DOPPLER_ENVIRONMENT", "NOT SET")
    print(f"DOPPLER_CONFIG: {doppler_config}")
    print(f"DOPPLER_ENVIRONMENT: {doppler_env}")

    # Other critical vars (mask sensitive keys)
    for var in ["AWS_REGION", "LANGSMITH_TRACING_V2", "OPENROUTER_API_KEY"]:
        value = os.environ.get(var, "NOT SET")
        if var.endswith("_KEY") and value != "NOT SET":
            value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        print(f"{var}: {value}")

    print("="*60 + "\n")

    # ============================================================
    # TIER HANDLING
    # ============================================================
    # If --tier is provided, override the marker filter from addopts
    tier_opt = config.getoption("--tier", default=None)
    if tier_opt is not None:
        # Clear the marker expression set by addopts
        # This allows --tier to take full control
        config.option.markexpr = ""


def pytest_collection_modifyitems(config, items):
    """Handle --run-ratelimited and --tier flags.

    Tier System (Layer 2 - Compositions of markers):
    - Tier 0: Unit tests only (no external dependencies)
    - Tier 1: Unit + mocked tests (default, same as addopts)
    - Tier 2: + integration tests (real APIs)
    - Tier 3: + smoke tests (requires live server)
    - Tier 4: + e2e tests (requires browser)
    """
    # Handle --run-ratelimited (existing behavior)
    if not config.getoption("--run-ratelimited"):
        skip_ratelimited = pytest.mark.skip(
            reason="Skipped: API rate limit (use --run-ratelimited to run)"
        )
        for item in items:
            if "ratelimited" in item.keywords:
                item.add_marker(skip_ratelimited)

    # Handle --tier flag
    tier_opt = config.getoption("--tier")
    if tier_opt is None:
        return  # Use addopts default behavior (pytest.ini)

    # Tier determines which markers to INCLUDE
    # Each tier builds on the previous (cumulative)
    tier_includes = {
        0: set(),                           # Unit only
        1: set(),                           # + mocked (same as 0)
        2: {'integration'},                 # + real APIs
        3: {'integration', 'smoke'},        # + live server
        4: {'integration', 'smoke', 'e2e'}, # + browser
    }

    included_markers = tier_includes.get(tier_opt, set())

    for item in items:
        item_markers = {m.name for m in item.iter_markers()}

        # Skip if test has markers not included in this tier
        excluded = {'integration', 'smoke', 'e2e'} - included_markers
        markers_to_skip = item_markers & excluded
        if markers_to_skip:
            item.add_marker(pytest.mark.skip(
                reason=f"Tier {tier_opt} excludes markers: {markers_to_skip}"
            ))


###############################################################################
# Mock Fixtures for API Services
###############################################################################

@pytest.fixture
def mock_yfinance_ticker():
    """Create a mock yfinance Ticker object"""
    mock_ticker = Mock()
    mock_ticker.info = {
        'symbol': 'NVDA',
        'shortName': 'NVIDIA Corporation',
        'regularMarketPrice': 150.0,
        'regularMarketChange': 5.0,
        'regularMarketChangePercent': 3.45,
        'regularMarketVolume': 50000000,
        'marketCap': 500000000000,
        'sector': 'Technology',
        'industry': 'Semiconductors'
    }
    mock_ticker.history = Mock(return_value=_create_mock_history())
    return mock_ticker


@pytest.fixture
def mock_yfinance_download():
    """Mock yfinance.download() for price data fetching"""
    import pandas as pd
    import numpy as np

    def mock_download(ticker, start=None, end=None, period=None, **kwargs):
        dates = pd.date_range(start='2024-01-01', periods=252, freq='D')
        prices = 100 + np.cumsum(np.random.randn(252) * 2)
        return pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Adj Close': prices,
            'Volume': np.random.randint(1000000, 10000000, 252)
        }, index=dates)

    with patch('yfinance.download', side_effect=mock_download) as mock:
        yield mock


@pytest.fixture
def mock_ticker_service():
    """Create a mock TickerService"""
    mock_service = Mock()
    mock_service.search = Mock(return_value=[
        {'symbol': 'NVDA19', 'name': 'NVIDIA Corporation', 'market': 'SET'},
        {'symbol': 'AMD19', 'name': 'Advanced Micro Devices', 'market': 'SET'}
    ])
    mock_service.validate = Mock(return_value=True)
    mock_service.get_ticker_info = Mock(return_value={
        'symbol': 'NVDA19',
        'name': 'NVIDIA Corporation',
        'market': 'SET'
    })
    return mock_service


@pytest.fixture
def mock_rankings_service():
    """Create a mock RankingsService"""
    mock_service = Mock()

    # Create async mock for get_rankings
    async def mock_get_rankings(category: str, limit: int = 10):
        return [
            {'ticker': 'NVDA19', 'change_percent': 5.5, 'price': 150.0},
            {'ticker': 'AMD19', 'change_percent': 3.2, 'price': 85.0},
        ][:limit]

    mock_service.get_rankings = AsyncMock(side_effect=mock_get_rankings)
    return mock_service


@pytest.fixture
def mock_peer_selector():
    """Create a mock PeerSelector"""
    mock_selector = Mock()

    async def mock_find_peers(ticker: str, max_peers: int = 5):
        return [
            {'ticker': 'AMD19', 'correlation': 0.85},
            {'ticker': 'INTC19', 'correlation': 0.78},
        ][:max_peers]

    mock_selector.find_peers_async = AsyncMock(side_effect=mock_find_peers)
    mock_selector.find_peers = Mock(return_value=[
        {'ticker': 'AMD19', 'correlation': 0.85},
        {'ticker': 'INTC19', 'correlation': 0.78},
    ])
    return mock_selector


@pytest.fixture
def mock_watchlist_service():
    """Create a mock WatchlistService"""
    mock_service = Mock()
    mock_service.get_watchlist = Mock(return_value=[
        {'ticker': 'NVDA19', 'added_at': '2025-01-01T00:00:00'},
        {'ticker': 'AMD19', 'added_at': '2025-01-02T00:00:00'},
    ])
    mock_service.add_ticker = Mock(return_value={'success': True})
    mock_service.remove_ticker = Mock(return_value={'success': True})
    return mock_service


@pytest.fixture
def mock_job_service():
    """Create a mock JobService"""
    mock_service = Mock()
    mock_service.create_job = Mock(return_value={
        'job_id': 'rpt_test123',
        'status': 'pending',
        'ticker': 'NVDA19'
    })
    mock_service.get_job = Mock(return_value={
        'job_id': 'rpt_test123',
        'status': 'completed',
        'ticker': 'NVDA19',
        'result': {'report': 'Test report content'}
    })
    return mock_service


###############################################################################
# Mock Fixtures for LangGraph Workflow
###############################################################################

@pytest.fixture
def mock_agent_state() -> Dict[str, Any]:
    """Create a sample AgentState for testing"""
    return {
        'ticker': 'NVDA19',
        'ticker_data': {
            'info': {'shortName': 'NVIDIA', 'sector': 'Technology'},
            'history': _create_mock_history()
        },
        'indicators': {
            'sma_20': 145.0,
            'sma_50': 140.0,
            'rsi_14': 55.0,
            'macd': 2.5
        },
        'percentiles': {
            'current_percentile': 75.0,
            'sma_percentile': 65.0
        },
        'news': [
            {'title': 'NVIDIA announces new GPU', 'url': 'https://example.com'},
            {'title': 'AI chip demand grows', 'url': 'https://example.com'}
        ],
        'comparative_data': {},
        'report': '',
        'strategy': 'single-stage',
        'error': '',
        'messages': []
    }


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing"""
    mock = Mock()
    mock.invoke = Mock(return_value=Mock(content="Mock LLM response"))
    return mock


###############################################################################
# Helper Functions
###############################################################################

def _create_mock_history():
    """Create mock price history DataFrame"""
    import pandas as pd
    import numpy as np

    dates = pd.date_range(start='2024-01-01', periods=252, freq='D')
    prices = 100 + np.cumsum(np.random.randn(252) * 2)

    return pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, 252)
    }, index=dates)


###############################################################################
# Event Loop Handling for Async Tests
###############################################################################

@pytest.fixture(scope='function')
def event_loop():
    """
    Create a new event loop for each test function.

    This avoids the "Cannot close a running event loop" error when tests
    use asyncio.run() (e.g., report_worker_handler tests) alongside
    pytest-asyncio tests.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


###############################################################################
# Singleton Reset Fixtures (Test Isolation)
###############################################################################

@pytest.fixture(autouse=True, scope='function')
def reset_api_singletons():
    """
    Reset module-level singleton instances before each test.

    This ensures test isolation by preventing singleton state from
    leaking between tests. Without this, tests may fail when run
    as a suite but pass when run individually.
    """
    # Store original values
    import importlib

    modules_to_reset = [
        ('src.api.rankings_service', '_rankings_service'),
        ('src.api.peer_selector', '_peer_selector_service'),
        ('src.api.watchlist_service', '_watchlist_service'),
        ('src.api.job_service', '_job_service'),
        ('src.api.ticker_service', '_ticker_service'),
        ('src.api.transformer', '_transformer'),
        ('src.api.transformer', '_pdf_storage'),
        ('src.api.telegram_auth', '_auth_instance'),
    ]

    original_values = {}

    for module_name, attr_name in modules_to_reset:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, attr_name):
                original_values[(module_name, attr_name)] = getattr(module, attr_name)
                setattr(module, attr_name, None)
        except ImportError:
            # Module not available, skip
            pass

    yield

    # Restore original values after test
    for (module_name, attr_name), original_value in original_values.items():
        try:
            module = importlib.import_module(module_name)
            setattr(module, attr_name, original_value)
        except ImportError:
            pass


###############################################################################
# Requirement Fixtures (Layer 0 - Runtime Dependency Checks)
###############################################################################

@pytest.fixture
def requires_llm():
    """Skip if OPENROUTER_API_KEY not available.

    Use this fixture for integration tests that make real LLM API calls.

    Example:
        def test_llm_generation(self, requires_llm):
            # This test will skip if no API key
            result = agent.generate_report(ticker)
    """
    if not os.environ.get('OPENROUTER_API_KEY'):
        pytest.skip("Requires OPENROUTER_API_KEY")


@pytest.fixture
def requires_live_server():
    """Skip if API server not responding.

    Use this fixture for smoke tests that need a running API server.

    Example:
        def test_health_endpoint(self, requires_live_server):
            # This test will skip if server not running
            response = requests.get(f"{API_URL}/health")
    """
    import requests
    api_url = os.environ.get('API_URL', 'http://localhost:8001')
    try:
        requests.get(f"{api_url}/api/v1/health", timeout=2)
    except Exception:
        pytest.skip(f"Requires running API server at {api_url}")


@pytest.fixture
def requires_browser():
    """Skip if Playwright not installed.

    Use this fixture for e2e browser tests.

    Example:
        def test_ui_interaction(self, requires_browser):
            # This test will skip if Playwright not available
            with sync_playwright() as p:
                browser = p.chromium.launch()
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        pytest.skip("Requires Playwright: pip install playwright && playwright install")


@pytest.fixture
def requires_langsmith():
    """Skip if LANGCHAIN_API_KEY not available.

    Use this fixture for tests that interact with LangSmith.

    Example:
        def test_langsmith_logging(self, requires_langsmith):
            # This test will skip if no LangSmith API key
            client = get_langsmith_client()
    """
    if not os.environ.get('LANGCHAIN_API_KEY'):
        pytest.skip("Requires LANGCHAIN_API_KEY for LangSmith")


###############################################################################
# Environment Fixtures
###############################################################################

@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables for testing"""
    env_vars = {
        'OPENAI_API_KEY': 'test-api-key',
        'PDF_BUCKET_NAME': 'test-bucket',
        'DYNAMODB_WATCHLIST_TABLE': 'test-watchlist-table',
        'DYNAMODB_CACHE_TABLE': 'test-cache-table',
        'JOBS_TABLE_NAME': 'test-jobs-table',
        'REPORT_JOBS_QUEUE_URL': 'https://sqs.test.amazonaws.com/test-queue',
        'ENVIRONMENT': 'test'
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_aws_clients():
    """Mock AWS service clients (DynamoDB, SQS, S3)"""
    with patch('boto3.resource') as mock_resource, \
         patch('boto3.client') as mock_client:

        # Mock DynamoDB Table
        mock_table = Mock()
        mock_table.get_item = Mock(return_value={'Item': {}})
        mock_table.put_item = Mock(return_value={})
        mock_table.query = Mock(return_value={'Items': []})

        mock_dynamodb = Mock()
        mock_dynamodb.Table = Mock(return_value=mock_table)
        mock_resource.return_value = mock_dynamodb

        # Mock SQS
        mock_sqs = Mock()
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-msg-id'})
        mock_client.return_value = mock_sqs

        yield {
            'dynamodb': mock_dynamodb,
            'sqs': mock_sqs,
            'table': mock_table
        }
