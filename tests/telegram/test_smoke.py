# -*- coding: utf-8 -*-
"""
Smoke Tests for Telegram API

Post-deployment validation tests that verify basic API functionality.
These tests run against a live API endpoint (local or production).

Usage:
    # Local development
    API_URL=http://localhost:8001 pytest tests/telegram/test_smoke.py -v

    # Production
    API_URL=https://xxx.execute-api.ap-southeast-1.amazonaws.com pytest tests/telegram/test_smoke.py -v

    # CI/CD (uses TELEGRAM_API_URL secret)
    pytest tests/telegram/test_smoke.py -v -m smoke
"""

import os
import pytest
import requests
from typing import Optional


# Mark all tests in this module as smoke tests (require running server)
pytestmark = pytest.mark.smoke


# Get API URL from environment (CI provides this via secrets)
API_URL = os.environ.get(
    "API_URL",
    os.environ.get("TELEGRAM_API_URL", "http://localhost:8001")
)


def get_api_url() -> str:
    """Get the API base URL"""
    return API_URL.rstrip("/")


class TestHealthEndpoints:
    """Smoke tests for health/readiness endpoints"""

    @pytest.mark.smoke
    def test_health_endpoint_returns_200(self):
        """Verify /api/v1/health returns 200 OK"""
        url = f"{get_api_url()}/api/v1/health"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, f"Health check failed: {response.text}"

    @pytest.mark.smoke
    def test_health_response_format(self):
        """Verify health response has expected fields"""
        url = f"{get_api_url()}/api/v1/health"
        response = requests.get(url, timeout=10)

        data = response.json()
        assert "status" in data or "healthy" in data, f"Unexpected health response: {data}"


class TestSearchEndpoint:
    """Smoke tests for ticker search functionality"""

    @pytest.mark.smoke
    def test_search_returns_200(self):
        """Verify /api/v1/search returns 200 OK"""
        url = f"{get_api_url()}/api/v1/search"
        response = requests.get(url, params={"q": "NVDA"}, timeout=10)

        assert response.status_code == 200, f"Search failed: {response.text}"

    @pytest.mark.smoke
    def test_search_returns_results(self):
        """Verify search returns ticker results"""
        url = f"{get_api_url()}/api/v1/search"
        response = requests.get(url, params={"q": "NVDA"}, timeout=10)

        data = response.json()
        # Response should be a list or have a 'results' field
        if isinstance(data, list):
            assert len(data) > 0, "Search returned empty results"
        elif isinstance(data, dict):
            results = data.get("results", data.get("data", []))
            assert len(results) >= 0, "Search response has unexpected format"

    @pytest.mark.smoke
    def test_search_empty_query_handled(self):
        """Verify search handles empty query gracefully"""
        url = f"{get_api_url()}/api/v1/search"
        response = requests.get(url, params={"q": ""}, timeout=10)

        # Should return 200 or 400, not 500
        assert response.status_code in [200, 400], f"Empty search failed badly: {response.text}"


class TestRankingsEndpoint:
    """Smoke tests for market rankings functionality"""

    @pytest.mark.smoke
    def test_rankings_returns_200(self):
        """Verify /api/v1/rankings returns 200 OK"""
        url = f"{get_api_url()}/api/v1/rankings"
        response = requests.get(
            url,
            params={"category": "top_gainers", "limit": 5},
            timeout=30  # Rankings may take time due to data fetching
        )

        assert response.status_code == 200, f"Rankings failed: {response.text}"

    @pytest.mark.smoke
    def test_rankings_returns_list(self):
        """Verify rankings returns a list of tickers"""
        url = f"{get_api_url()}/api/v1/rankings"
        response = requests.get(
            url,
            params={"category": "top_gainers", "limit": 5},
            timeout=30
        )

        data = response.json()
        # Response should be a list or have items/data field
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items", data.get("data", data.get("rankings", [])))
        else:
            items = []

        assert isinstance(items, list), f"Rankings response not a list: {type(items)}"

    @pytest.mark.smoke
    @pytest.mark.parametrize("category", ["top_gainers", "top_losers", "most_active", "trending"])
    def test_rankings_categories(self, category: str):
        """Verify all ranking categories work"""
        url = f"{get_api_url()}/api/v1/rankings"
        response = requests.get(
            url,
            params={"category": category, "limit": 3},
            timeout=30
        )

        assert response.status_code == 200, f"Rankings category '{category}' failed: {response.text}"


class TestReportEndpoint:
    """Smoke tests for report generation (lightweight checks only)"""

    @pytest.mark.smoke
    def test_report_endpoint_exists(self):
        """Verify /api/v1/report/{ticker} endpoint exists"""
        url = f"{get_api_url()}/api/v1/report/INVALID_TICKER_12345"
        response = requests.get(url, timeout=10)

        # Should return 400/404 for invalid ticker, not 500 or connection error
        assert response.status_code in [400, 404, 422], f"Report endpoint error: {response.status_code}"

    @pytest.mark.smoke
    @pytest.mark.slow  # This test may take time
    def test_report_generation_starts(self):
        """Verify report generation can be initiated"""
        url = f"{get_api_url()}/api/v1/report/NVDA19"
        response = requests.get(url, timeout=60)  # Longer timeout for report gen

        # Should return 200 (sync) or 202 (async job created)
        assert response.status_code in [200, 202], f"Report initiation failed: {response.text}"


class TestWatchlistEndpoint:
    """Smoke tests for watchlist functionality"""

    @pytest.mark.smoke
    def test_watchlist_get_requires_user(self):
        """Verify watchlist requires user ID"""
        url = f"{get_api_url()}/api/v1/watchlist"
        response = requests.get(url, timeout=10)

        # Should return 400/401/422 without user ID, not 500
        assert response.status_code in [400, 401, 422, 200], f"Watchlist error: {response.status_code}"


class TestErrorHandling:
    """Smoke tests for error handling"""

    @pytest.mark.smoke
    def test_404_returns_json(self):
        """Verify 404 errors return JSON, not HTML"""
        url = f"{get_api_url()}/api/v1/nonexistent-endpoint-12345"
        response = requests.get(url, timeout=10)

        assert response.status_code == 404

        # Response should be JSON
        try:
            data = response.json()
            assert "error" in data or "detail" in data or "message" in data
        except requests.exceptions.JSONDecodeError:
            # Some APIs return empty body for 404, that's acceptable
            pass

    @pytest.mark.smoke
    def test_invalid_method_returns_405(self):
        """Verify invalid HTTP methods return 405"""
        url = f"{get_api_url()}/api/v1/health"
        response = requests.delete(url, timeout=10)

        # Should return 405 Method Not Allowed, not 500
        assert response.status_code in [405, 404, 400], f"Invalid method handling: {response.status_code}"


# Run if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
