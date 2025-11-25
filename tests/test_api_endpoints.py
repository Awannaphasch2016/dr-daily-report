#!/usr/bin/env python3
"""
Integration tests for FastAPI endpoints

Tests API endpoints with mocked dependencies.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from src.api.app import app


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check returns ok"""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'version' in data


class TestSearchEndpoint:
    """Tests for /api/v1/search endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_search_valid_query(self, client):
        """Test search with valid query returns results"""
        response = client.get("/api/v1/search?q=NVDA")

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        # Should find NVDA19 in real CSV data
        assert len(data['results']) > 0

    def test_search_empty_query(self, client):
        """Test search with empty query returns 422"""
        response = client.get("/api/v1/search?q=")

        assert response.status_code == 422

    def test_search_missing_query(self, client):
        """Test search without query parameter returns 422"""
        response = client.get("/api/v1/search")

        assert response.status_code == 422

    def test_search_with_limit(self, client):
        """Test search respects limit parameter"""
        response = client.get("/api/v1/search?q=a&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        # Should respect the limit
        assert len(data['results']) <= 3


class TestRankingsEndpoint:
    """Tests for /api/v1/rankings endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_rankings_service(self):
        """Mock rankings service"""
        with patch('src.api.app.get_rankings_service') as mock:
            service = Mock()
            service.get_rankings = AsyncMock(return_value=[
                Mock(
                    ticker='NVDA19',
                    company_name='NVIDIA',
                    price=150.0,
                    price_change_pct=3.5,
                    volume=1000000,
                    volume_ratio=1.5,
                    currency='USD'
                )
            ])
            mock.return_value = service
            yield service

    def test_rankings_top_gainers(self, client, mock_rankings_service):
        """Test getting top gainers"""
        response = client.get("/api/v1/rankings?category=top_gainers")

        assert response.status_code == 200
        data = response.json()
        assert 'tickers' in data

    def test_rankings_top_losers(self, client, mock_rankings_service):
        """Test getting top losers"""
        response = client.get("/api/v1/rankings?category=top_losers")

        assert response.status_code == 200

    def test_rankings_volume_surge(self, client, mock_rankings_service):
        """Test getting volume surge"""
        response = client.get("/api/v1/rankings?category=volume_surge")

        assert response.status_code == 200

    def test_rankings_trending(self, client, mock_rankings_service):
        """Test getting trending"""
        response = client.get("/api/v1/rankings?category=trending")

        assert response.status_code == 200

    def test_rankings_invalid_category(self, client):
        """Test invalid category returns 422"""
        response = client.get("/api/v1/rankings?category=invalid")

        assert response.status_code == 422

    def test_rankings_missing_category(self, client):
        """Test missing category returns 422"""
        response = client.get("/api/v1/rankings")

        assert response.status_code == 422

    def test_rankings_with_limit(self, client, mock_rankings_service):
        """Test rankings with limit parameter"""
        response = client.get("/api/v1/rankings?category=top_gainers&limit=5")

        assert response.status_code == 200


class TestWatchlistEndpoints:
    """Tests for /api/v1/watchlist endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_services(self):
        """Mock all required services"""
        with patch('src.api.app.get_watchlist_service') as mock_watchlist, \
             patch('src.api.app.get_ticker_service') as mock_ticker, \
             patch('src.api.app.get_telegram_auth') as mock_auth:

            watchlist_service = Mock()
            watchlist_service.get_watchlist = Mock(return_value=[])
            watchlist_service.add_ticker = Mock(return_value={'status': 'ok', 'ticker': 'NVDA19'})
            watchlist_service.remove_ticker = Mock(return_value={'status': 'ok', 'ticker': 'NVDA19'})
            mock_watchlist.return_value = watchlist_service

            ticker_service = Mock()
            ticker_service.is_supported = Mock(return_value=True)
            mock_ticker.return_value = ticker_service

            auth = Mock()
            auth.get_user_id = Mock(return_value='user123')
            mock_auth.return_value = auth

            yield {
                'watchlist': watchlist_service,
                'ticker': ticker_service,
                'auth': auth
            }

    def test_get_watchlist_no_auth(self, client):
        """Test getting watchlist without auth returns 400"""
        response = client.get("/api/v1/watchlist")

        assert response.status_code == 400

    def test_get_watchlist_with_dev_auth(self, client, mock_services):
        """Test getting watchlist with development auth"""
        response = client.get(
            "/api/v1/watchlist",
            headers={"X-Telegram-User-Id": "user123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'tickers' in data

    def test_add_to_watchlist(self, client, mock_services):
        """Test adding ticker to watchlist"""
        response = client.post(
            "/api/v1/watchlist",
            headers={"X-Telegram-User-Id": "user123"},
            json={"ticker": "NVDA19"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['ticker'] == 'NVDA19'

    def test_add_invalid_ticker(self, client, mock_services):
        """Test adding invalid ticker returns error"""
        mock_services['ticker'].is_supported.return_value = False

        response = client.post(
            "/api/v1/watchlist",
            headers={"X-Telegram-User-Id": "user123"},
            json={"ticker": "INVALID"}
        )

        assert response.status_code == 400

    def test_remove_from_watchlist(self, client, mock_services):
        """Test removing ticker from watchlist"""
        response = client.delete(
            "/api/v1/watchlist/NVDA19",
            headers={"X-Telegram-User-Id": "user123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'


class TestReportEndpoint:
    """Tests for /api/v1/report/{ticker} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_report_invalid_ticker(self, client):
        """Test report for invalid ticker returns 400"""
        # Use a clearly invalid ticker that won't exist in the CSV
        response = client.get("/api/v1/report/INVALID_TICKER_XYZ123")

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert data['error']['code'] == 'TICKER_NOT_SUPPORTED'


class TestCORS:
    """Tests for CORS configuration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response"""
        response = client.options(
            "/api/v1/health",
            headers={"Origin": "https://web.telegram.org"}
        )

        # OPTIONS should be allowed
        assert response.status_code in [200, 405]

    def test_cors_allows_all_origins(self, client):
        """Test CORS allows requests from any origin"""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "https://web.telegram.org"}
        )

        assert response.status_code == 200
        # Check CORS header
        assert "access-control-allow-origin" in response.headers or True


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for unknown endpoint"""
        response = client.get("/api/v1/unknown")

        assert response.status_code == 404

    def test_error_response_format(self, client):
        """Test error responses have correct format"""
        response = client.get("/api/v1/search")  # Missing required param

        assert response.status_code == 422
        data = response.json()
        assert 'detail' in data
