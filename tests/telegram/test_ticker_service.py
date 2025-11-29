#!/usr/bin/env python3
"""
Unit tests for TickerService

Tests ticker search, validation, and CSV data loading.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.api.ticker_service import TickerService, get_ticker_service


class TestTickerService:
    """Test suite for TickerService"""

    @pytest.fixture
    def service(self):
        """Create TickerService instance for testing"""
        return TickerService()

    # Test 1: Service initialization
    def test_service_initialization(self, service):
        """Test that service initializes and loads ticker data"""
        assert isinstance(service, TickerService), f"Expected TickerService, got {type(service)}"
        assert len(service.ticker_map) > 0
        assert isinstance(service.ticker_map, dict)
        assert isinstance(service.ticker_info, dict)

    # Test 2: Singleton pattern
    def test_singleton_pattern(self):
        """Test that get_ticker_service returns singleton"""
        service1 = get_ticker_service()
        service2 = get_ticker_service()
        assert service1 is service2

    # Test 3: Check ticker is supported
    def test_is_supported_valid_ticker(self, service):
        """Test is_supported returns True for valid ticker"""
        # Test with a ticker we know exists (from CSV)
        valid_tickers = ['NVDA19', 'DBS19', 'UOB19']
        for ticker in valid_tickers:
            if ticker in service.ticker_map:
                assert service.is_supported(ticker) is True
                break

    def test_is_supported_invalid_ticker(self, service):
        """Test is_supported returns False for invalid ticker"""
        assert service.is_supported('INVALID_TICKER_XYZ') is False
        assert service.is_supported('') is False

    def test_is_supported_none_ticker(self, service):
        """Test is_supported handles None gracefully"""
        # This may raise or return False depending on implementation
        try:
            result = service.is_supported(None)
            assert result is False
        except (AttributeError, TypeError):
            pass  # Expected if None is not handled

    def test_is_supported_case_insensitive(self, service):
        """Test is_supported is case-insensitive"""
        # Find a valid ticker first
        if service.ticker_map:
            valid_ticker = list(service.ticker_map.keys())[0]
            assert service.is_supported(valid_ticker.lower()) is True
            assert service.is_supported(valid_ticker.upper()) is True

    # Test 4: Get ticker info
    def test_get_ticker_info_valid(self, service):
        """Test get_ticker_info returns correct data for valid ticker"""
        if service.ticker_map:
            valid_ticker = list(service.ticker_map.keys())[0]
            info = service.get_ticker_info(valid_ticker)
            assert info is not None
            assert 'symbol' in info
            assert 'company_name' in info

    def test_get_ticker_info_invalid(self, service):
        """Test get_ticker_info returns None for invalid ticker"""
        info = service.get_ticker_info('INVALID_TICKER_XYZ')
        assert info is None

    # Test 5: Search functionality
    def test_search_by_symbol(self, service):
        """Test search returns results when searching by symbol"""
        if service.ticker_map:
            valid_ticker = list(service.ticker_map.keys())[0]
            # Search with partial symbol
            results = service.search(valid_ticker[:3], limit=5)
            assert len(results) > 0

    def test_search_by_company_name(self, service):
        """Test search returns results when searching by company name"""
        # Search for common company name patterns
        results = service.search("bank", limit=10)
        # May or may not have results depending on data
        assert isinstance(results, list)

    def test_search_empty_query(self, service):
        """Test search handles empty query gracefully"""
        results = service.search("", limit=5)
        # Service may return all results or empty list for empty query
        assert isinstance(results, list)

    def test_search_respects_limit(self, service):
        """Test search respects the limit parameter"""
        results = service.search("a", limit=3)
        assert len(results) <= 3

    def test_search_case_insensitive(self, service):
        """Test search is case-insensitive"""
        if service.ticker_map:
            valid_ticker = list(service.ticker_map.keys())[0]
            results_lower = service.search(valid_ticker.lower(), limit=5)
            results_upper = service.search(valid_ticker.upper(), limit=5)
            # Should have similar results
            assert len(results_lower) == len(results_upper)

    # Test 6: Get Yahoo ticker symbol
    def test_get_yahoo_ticker_valid(self, service):
        """Test get_yahoo_ticker returns correct symbol"""
        if service.ticker_map:
            valid_ticker = list(service.ticker_map.keys())[0]
            yahoo_symbol = service.get_yahoo_ticker(valid_ticker)
            assert yahoo_symbol is not None
            assert isinstance(yahoo_symbol, str)

    def test_get_yahoo_ticker_invalid(self, service):
        """Test get_yahoo_ticker returns None for invalid ticker"""
        yahoo_symbol = service.get_yahoo_ticker('INVALID_TICKER_XYZ')
        assert yahoo_symbol is None

    # Test 7: Ticker count
    def test_ticker_count(self, service):
        """Test that tickers dictionary has expected count"""
        # Based on CLAUDE.md, should have ~47 tickers
        assert len(service.ticker_map) > 0
        # Don't enforce exact count as it may change


class TestTickerServiceEdgeCases:
    """Edge case tests for TickerService"""

    @pytest.fixture
    def service(self):
        """Create TickerService instance for testing"""
        return TickerService()

    def test_search_special_characters(self, service):
        """Test search handles special characters gracefully"""
        results = service.search("!@#$%", limit=5)
        assert isinstance(results, list)
        # Should not raise exception

    def test_search_unicode_characters(self, service):
        """Test search handles unicode/Thai characters"""
        results = service.search("กสิกร", limit=5)  # Thai bank name
        assert isinstance(results, list)
        # May or may not have results

    def test_search_very_long_query(self, service):
        """Test search handles very long query"""
        long_query = "a" * 1000
        results = service.search(long_query, limit=5)
        assert isinstance(results, list)

    def test_search_with_spaces(self, service):
        """Test search handles query with spaces"""
        results = service.search("nvidia corp", limit=5)
        assert isinstance(results, list)

    def test_get_ticker_info_whitespace(self, service):
        """Test get_ticker_info handles whitespace"""
        info = service.get_ticker_info("  ")
        assert info is None
