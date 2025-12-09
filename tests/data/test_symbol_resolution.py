# -*- coding: utf-8 -*-
"""
Tests for Symbol Resolution - Symbol-Type Invariance

TDD Approach: Tests verify that all operations are symbol-type invariant.
Following principles.md guidelines:
- Class-based tests
- Test behavior (symbol resolution happens), not implementation
- Test both success AND failure paths
- Test outcomes (correct Yahoo symbol used), not execution (method called)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import pandas as pd


class TestDataFetcherSymbolResolution:
    """Test symbol resolution in DataFetcher (symbol-type invariant)."""

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.data.data_fetcher.get_ticker_resolver')
    @patch('src.data.data_fetcher.yf')
    def test_fetch_ticker_data_resolves_dr_symbol_to_yahoo(self, mock_yf, mock_get_resolver):
        """
        GIVEN DataFetcher receives DR symbol (DBS19)
        WHEN fetch_ticker_data is called
        THEN should resolve to Yahoo symbol (D05.SI) before Yahoo Finance API call
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        # Mock yfinance
        mock_stock = MagicMock()
        mock_stock.history.return_value = pd.DataFrame({
            'Open': [54.0],
            'High': [54.5],
            'Low': [53.5],
            'Close': [54.0],
            'Volume': [1000000]
        })
        mock_stock.info = {'longName': 'DBS Group Holdings Ltd'}
        mock_yf.Ticker.return_value = mock_stock

        # Mock direct API test
        from src.data.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        fetcher.test_yahoo_api_direct = MagicMock(return_value=(True, 252))

        # Act
        result = fetcher.fetch_ticker_data('DBS19')

        # Assert: Yahoo Finance API called with resolved Yahoo symbol
        mock_yf.Ticker.assert_called_once_with('D05.SI'), \
            "Should call yfinance with resolved Yahoo symbol, not DR symbol"
        assert result is not None, "Should return data successfully"
        assert result['company_name'] == 'DBS Group Holdings Ltd'

    @patch('src.data.data_fetcher.get_ticker_resolver')
    @patch('src.data.data_fetcher.yf')
    def test_fetch_ticker_data_handles_already_yahoo_symbol(self, mock_yf, mock_get_resolver):
        """
        GIVEN DataFetcher receives Yahoo symbol (D05.SI)
        WHEN fetch_ticker_data is called
        THEN should use symbol as-is (no resolution needed)
        """
        # Arrange: Mock resolver returns None (symbol not found, assume it's Yahoo)
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = None
        mock_get_resolver.return_value = mock_resolver

        # Mock yfinance
        mock_stock = MagicMock()
        mock_stock.history.return_value = pd.DataFrame({
            'Close': [54.0]
        })
        mock_stock.info = {}
        mock_yf.Ticker.return_value = mock_stock

        from src.data.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        fetcher.test_yahoo_api_direct = MagicMock(return_value=(True, 252))

        # Act
        result = fetcher.fetch_ticker_data('D05.SI')

        # Assert: Should use symbol as-is
        mock_yf.Ticker.assert_called_once_with('D05.SI'), \
            "Should use Yahoo symbol as-is when resolver returns None"

    @patch('src.data.data_fetcher.get_ticker_resolver')
    def test_resolve_to_yahoo_symbol_handles_resolver_failure(self, mock_get_resolver):
        """
        GIVEN resolver fails (exception)
        WHEN _resolve_to_yahoo_symbol is called
        THEN should fallback to using symbol as-is (graceful degradation)
        """
        # Arrange: Resolver raises exception
        mock_get_resolver.side_effect = Exception("Resolver error")

        from src.data.data_fetcher import DataFetcher
        fetcher = DataFetcher()

        # Act
        result = fetcher._resolve_to_yahoo_symbol('DBS19')

        # Assert: Should fallback to original symbol
        assert result == 'DBS19', "Should fallback to original symbol on resolver failure"


class TestPrecomputeServiceSymbolResolution:
    """Test symbol resolution in PrecomputeService (fixes Aurora query bug)."""

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None
        import src.data.aurora.client as client_module
        client_module._aurora_client = None

    @patch('src.data.aurora.precompute_service.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_resolves_dr_symbol_before_aurora_query(self, mock_get_client, mock_repo_class, mock_get_resolver):
        """
        GIVEN PrecomputeService receives DR symbol (DBS19)
        WHEN compute_for_ticker is called
        THEN should resolve to Yahoo symbol (D05.SI) before querying Aurora
        
        This test fixes the bug: "No price data for DBS19" when Aurora stores prices with Yahoo symbols.
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        # Mock Aurora client
        mock_client = MagicMock()
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        # Mock repository - CRITICAL: Should be called with Yahoo symbol
        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102],
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Volume': [1000, 1100, 1200]
        })
        mock_repo_class.return_value = mock_repo

        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        service.repo = mock_repo

        # Act: Call with DR symbol
        result = service.compute_for_ticker('DBS19', include_report=False)

        # Assert: Repository should be called with Yahoo symbol, not DR symbol
        mock_repo.get_prices_as_dataframe.assert_called_once()
        call_args = mock_repo.get_prices_as_dataframe.call_args
        yahoo_symbol_arg = call_args[0][0]  # First positional argument
        
        assert yahoo_symbol_arg == 'D05.SI', \
            f"Should query Aurora with Yahoo symbol (D05.SI), not DR symbol (DBS19). Got: {yahoo_symbol_arg}"
        assert result['indicators'] is True, "Should succeed when using correct Yahoo symbol"

    @patch('src.data.aurora.precompute_service.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_handles_empty_dataframe_with_error(self, mock_get_client, mock_repo_class, mock_get_resolver):
        """
        GIVEN Aurora query returns empty DataFrame
        WHEN compute_for_ticker is called
        THEN should set error in results (not return silently)
        
        Following defensive programming: validate data exists before proceeding.
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock repository returns empty DataFrame (no price data)
        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame()  # Empty!
        mock_repo_class.return_value = mock_repo

        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        service.repo = mock_repo

        # Act
        result = service.compute_for_ticker('DBS19', include_report=False)

        # Assert: Should set error, not return silently
        assert 'error' in result, "Should set error field when no price data found"
        assert result['error'] is not None, "Error message should not be None"
        assert 'D05.SI' in result['error'] or 'DBS19' in result['error'], \
            "Error message should mention the symbol"
        assert result['indicators'] is False, "Should not compute indicators without price data"

    @patch('src.data.aurora.precompute_service.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_uses_yahoo_symbol_for_data_lake_storage(self, mock_get_client, mock_repo_class, mock_get_resolver):
        """
        GIVEN indicators computed for DR symbol
        WHEN storing to data lake
        THEN should use Yahoo symbol for consistency with raw data storage
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        mock_client = MagicMock()
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102],
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Volume': [1000, 1100, 1200]
        })
        mock_repo_class.return_value = mock_repo

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_indicators.return_value = True

        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        service.repo = mock_repo
        service.data_lake = mock_data_lake

        # Act: Call with DR symbol
        result = service.compute_for_ticker('DBS19', include_report=False)

        # Assert: Data lake storage should use Yahoo symbol
        mock_data_lake.store_indicators.assert_called_once()
        call_kwargs = mock_data_lake.store_indicators.call_args[1]
        assert call_kwargs['ticker'] == 'D05.SI', \
            f"Should store to data lake with Yahoo symbol (D05.SI), not DR symbol. Got: {call_kwargs['ticker']}"


class TestTickerFetcherSymbolResolution:
    """Test symbol resolution in TickerFetcher (symbol-type invariant)."""

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.scheduler.ticker_fetcher.get_ticker_resolver')
    @patch('src.scheduler.ticker_fetcher.DataLakeStorage')
    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_resolves_dr_symbol_for_data_lake_storage(self, mock_data_fetcher_class, mock_s3_cache_class, mock_data_lake_class, mock_get_resolver):
        """
        GIVEN TickerFetcher receives DR symbol (DBS19)
        WHEN storing to data lake
        THEN should use Yahoo symbol (D05.SI) for consistency
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 54.0,
            'company_name': 'DBS Group Holdings',
            'history': pd.DataFrame({'Close': [54.0]})
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_raw_yfinance_data.return_value = True
        mock_data_lake_class.return_value = mock_data_lake

        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket', data_lake_bucket='test-data-lake')

        # Act: Call with DR symbol
        result = fetcher.fetch_ticker('DBS19')

        # Assert: Data lake storage should use Yahoo symbol
        mock_data_lake.store_raw_yfinance_data.assert_called_once()
        call_kwargs = mock_data_lake.store_raw_yfinance_data.call_args[1]
        assert call_kwargs['ticker'] == 'D05.SI', \
            f"Should store to data lake with Yahoo symbol (D05.SI), not DR symbol. Got: {call_kwargs['ticker']}"
        assert result['status'] == 'success'


class TestNewsFetcherSymbolResolution:
    """Test symbol resolution in NewsFetcher (symbol-type invariant)."""

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.data.news_fetcher.get_ticker_resolver')
    @patch('src.data.news_fetcher.yf')
    def test_fetch_news_resolves_dr_symbol_to_yahoo(self, mock_yf, mock_get_resolver):
        """
        GIVEN NewsFetcher receives DR symbol (DBS19)
        WHEN fetch_news is called
        THEN should resolve to Yahoo symbol (D05.SI) before Yahoo Finance API call
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver

        # Mock yfinance
        mock_stock = MagicMock()
        mock_stock.news = [
            {'title': 'DBS News', 'link': 'http://example.com'}
        ]
        mock_yf.Ticker.return_value = mock_stock

        from src.data.news_fetcher import NewsFetcher
        fetcher = NewsFetcher()

        # Act: Call with DR symbol
        result = fetcher.fetch_news('DBS19')

        # Assert: Yahoo Finance API called with resolved Yahoo symbol
        mock_yf.Ticker.assert_called_once_with('D05.SI'), \
            "Should call yfinance with resolved Yahoo symbol, not DR symbol"
        assert len(result) > 0, "Should return news successfully"
