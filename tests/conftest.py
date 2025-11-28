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


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "smoke: mark test as a smoke test (post-deployment)")
    config.addinivalue_line("markers", "slow: mark test as slow (may take >10 seconds)")
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end browser test (requires playwright)")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
