# -*- coding: utf-8 -*-
"""
TDD Tests: Symbol-Type Invariance

Tests written BEFORE implementation to verify symbol resolution works correctly.
Following principles.md testing guidelines:
- Class-based tests
- Test outcomes, not execution
- Test both success AND failure paths
- Explicit failure mocking
- Test sabotage verification (tests that can actually fail)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import pandas as pd


class TestDataFetcherSymbolResolution:
    """Test DataFetcher symbol-type invariance.
    
    CRITICAL: These tests verify that DataFetcher resolves symbols BEFORE
    making Yahoo Finance API calls, making all operations symbol-type invariant.
    """

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    def test_resolve_to_yahoo_symbol_resolves_dr_to_yahoo(self):
        """
        GIVEN DataFetcher._resolve_to_yahoo_symbol receives DR symbol (DBS19)
        WHEN called
        THEN should return Yahoo symbol (D05.SI)
        
        Test Outcome: Verify resolution works correctly
        """
        # Arrange: Mock resolver (patch where imported)
        with patch('src.data.aurora.ticker_resolver.get_ticker_resolver') as mock_get_resolver:
            mock_resolver = MagicMock()
            mock_ticker_info = MagicMock()
            mock_ticker_info.yahoo_symbol = 'D05.SI'
            mock_resolver.resolve.return_value = mock_ticker_info
            mock_get_resolver.return_value = mock_resolver
            
            # Act
            from src.data.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            result = fetcher._resolve_to_yahoo_symbol('DBS19')
            
            # Assert: Returns resolved Yahoo symbol
            assert result == 'D05.SI', \
                f"Should resolve DBS19 to D05.SI, got {result}"
            mock_resolver.resolve.assert_called_once_with('DBS19')

    def test_resolve_to_yahoo_symbol_handles_yahoo_symbol_directly(self):
        """
        GIVEN DataFetcher._resolve_to_yahoo_symbol receives Yahoo symbol (D05.SI)
        WHEN called
        THEN should return same symbol (already Yahoo format)
        
        Test Outcome: Verify Yahoo symbols pass through unchanged
        """
        # Arrange: Mock resolver returns same symbol
        with patch('src.data.aurora.ticker_resolver.get_ticker_resolver') as mock_get_resolver:
            mock_resolver = MagicMock()
            mock_ticker_info = MagicMock()
            mock_ticker_info.yahoo_symbol = 'D05.SI'
            mock_resolver.resolve.return_value = mock_ticker_info
            mock_get_resolver.return_value = mock_resolver
            
            # Act
            from src.data.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            result = fetcher._resolve_to_yahoo_symbol('D05.SI')
            
            # Assert: Returns same symbol (already Yahoo format)
            assert result == 'D05.SI', \
                f"Should return Yahoo symbol as-is, got {result}"
            mock_resolver.resolve.assert_called_once_with('D05.SI')

    def test_resolve_to_yahoo_symbol_handles_none_resolution(self):
        """
        GIVEN resolver returns None (unknown symbol)
        WHEN _resolve_to_yahoo_symbol is called
        THEN should fallback to original symbol
        
        Test Outcome: Graceful fallback when resolution fails
        """
        # Arrange: Mock resolver returns None
        with patch('src.data.aurora.ticker_resolver.get_ticker_resolver') as mock_get_resolver:
            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = None  # Unknown symbol
            mock_get_resolver.return_value = mock_resolver
            
            # Act
            from src.data.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            result = fetcher._resolve_to_yahoo_symbol('UNKNOWN99')
            
            # Assert: Falls back to original symbol
            assert result == 'UNKNOWN99', \
                "Should fallback to original symbol when resolution returns None"

    def test_resolve_to_yahoo_symbol_handles_resolver_failure(self):
        """
        GIVEN resolver fails or returns None
        WHEN _resolve_to_yahoo_symbol is called
        THEN should fallback to using symbol as-is (graceful degradation)
        
        Test Outcome: Returns original symbol when resolution fails
        """
        # Arrange: Mock resolver to fail (patch where imported)
        with patch('src.data.aurora.ticker_resolver.get_ticker_resolver') as mock_get_resolver:
            mock_resolver = MagicMock()
            mock_resolver.resolve.side_effect = Exception("Resolver failed")
            mock_get_resolver.return_value = mock_resolver
            
            # Act
            from src.data.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            result = fetcher._resolve_to_yahoo_symbol('UNKNOWN99')
            
            # Assert: Falls back to original symbol
            assert result == 'UNKNOWN99', \
                "Should fallback to original symbol when resolution fails"


class TestPrecomputeServiceSymbolResolution:
    """Test PrecomputeService symbol-type invariance.
    
    CRITICAL: These tests verify that PrecomputeService resolves symbols BEFORE
    querying Aurora, fixing the "No price data for DBS19" bug.
    """

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None
        import src.data.aurora.client as client_module
        client_module._aurora_client = None

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_resolves_dr_symbol_before_aurora_query(
        self, mock_get_client, mock_repo_class, mock_get_resolver
    ):
        """
        GIVEN PrecomputeService receives DR symbol (DBS19)
        WHEN compute_for_ticker is called
        THEN should resolve to Yahoo symbol (D05.SI) BEFORE querying Aurora
        
        Test Outcome: Aurora query uses resolved Yahoo symbol, not DR symbol
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
            'Close': [50.0, 51.0, 52.0] * 100,
            'Open': [49.0, 50.0, 51.0] * 100,
            'High': [51.0, 52.0, 53.0] * 100,
            'Low': [48.0, 49.0, 50.0] * 100,
            'Volume': [1000, 1100, 1200] * 100
        })
        mock_repo_class.return_value = mock_repo
        
        # Act
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        result = service.compute_for_ticker('DBS19', include_report=False)
        
        # Assert: Repository called with RESOLVED Yahoo symbol
        mock_repo.get_prices_as_dataframe.assert_called_once()
        call_args = mock_repo.get_prices_as_dataframe.call_args
        assert call_args[0][0] == 'D05.SI', \
            f"Should query Aurora with Yahoo symbol 'D05.SI', got '{call_args[0][0]}'"
        
        # Assert: Computation succeeded
        assert result['indicators'] is True, "Indicators should be computed successfully"
        assert result['percentiles'] is True, "Percentiles should be computed successfully"

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_handles_empty_aurora_data_gracefully(
        self, mock_get_client, mock_repo_class, mock_get_resolver
    ):
        """
        GIVEN Aurora returns empty DataFrame (no price data)
        WHEN compute_for_ticker is called
        THEN should set error in results and return early (validation gate)
        
        Test Outcome: Error set in results, not silent failure
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver
        
        # Mock Aurora client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock repository returns EMPTY DataFrame (simulates no price data)
        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame()  # Empty!
        mock_repo_class.return_value = mock_repo
        
        # Act
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        result = service.compute_for_ticker('DBS19', include_report=False)
        
        # Assert: Error set in results (validation gate)
        assert 'error' in result, "Should set error field when no price data"
        assert result['error'] is not None, "Error message should be set"
        assert 'D05.SI' in result['error'], "Error should mention resolved symbol"
        
        # Assert: All flags False (early return)
        assert result['indicators'] is False, "Should not compute indicators without data"
        assert result['percentiles'] is False, "Should not compute percentiles without data"

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_uses_yahoo_symbol_for_data_lake_storage(
        self, mock_get_client, mock_repo_class, mock_get_resolver
    ):
        """
        GIVEN indicators computed successfully
        WHEN storing to data lake
        THEN should use Yahoo symbol for storage (consistent with raw data format)
        
        Test Outcome: Data lake storage uses Yahoo symbol
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver
        
        # Mock Aurora
        mock_client = MagicMock()
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client
        
        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [50.0] * 300,
            'Open': [49.0] * 300,
            'High': [51.0] * 300,
            'Low': [48.0] * 300,
            'Volume': [1000] * 300
        })
        mock_repo_class.return_value = mock_repo
        
        # Mock data lake
        from src.data.data_lake import DataLakeStorage
        with patch.object(DataLakeStorage, 'is_enabled', return_value=True), \
             patch.object(DataLakeStorage, 'store_indicators', return_value=True) as mock_store:
            
            # Act
            from src.data.aurora.precompute_service import PrecomputeService
            service = PrecomputeService()
            result = service.compute_for_ticker('DBS19', include_report=False)
            
            # Assert: Data lake storage called with Yahoo symbol
            assert mock_store.called, "Should store indicators to data lake"
            call_kwargs = mock_store.call_args[1]
            assert call_kwargs['ticker'] == 'D05.SI', \
                f"Should store with Yahoo symbol 'D05.SI', got '{call_kwargs['ticker']}'"


class TestTickerFetcherSymbolResolution:
    """Test TickerFetcher symbol-type invariance."""

    def setup_method(self):
        """Reset singletons before each test."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.ticker_fetcher.DataLakeStorage')
    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_resolves_symbol_for_data_lake_storage(
        self, mock_data_fetcher_class, mock_s3_cache_class, mock_data_lake_class, mock_get_resolver
    ):
        """
        GIVEN TickerFetcher receives DR symbol (DBS19)
        WHEN fetch_ticker is called
        THEN should resolve to Yahoo symbol before data lake storage
        
        Test Outcome: Data lake storage uses Yahoo symbol
        """
        # Arrange: Mock resolver
        mock_resolver = MagicMock()
        mock_ticker_info = MagicMock()
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info
        mock_get_resolver.return_value = mock_resolver
        
        # Mock DataFetcher
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'DBS19': 'D05.SI'}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 50.0,
            'company_name': 'DBS Group Holdings',
            'history': pd.DataFrame({'Close': [50.0]})
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher
        
        # Mock S3 cache
        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache
        
        # Mock data lake
        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_raw_yfinance_data.return_value = True
        mock_data_lake_class.return_value = mock_data_lake
        
        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket', data_lake_bucket='test-data-lake')
        result = fetcher.fetch_ticker('DBS19')
        
        # Assert: Data lake storage called with Yahoo symbol
        mock_data_lake.store_raw_yfinance_data.assert_called_once()
        call_kwargs = mock_data_lake.store_raw_yfinance_data.call_args[1]
        assert call_kwargs['ticker'] == 'D05.SI', \
            f"Should store with Yahoo symbol 'D05.SI', got '{call_kwargs['ticker']}'"
        
        # Assert: Success
        assert result['status'] == 'success'


class TestSymbolResolutionSabotage:
    """Test sabotage verification - ensure tests can actually fail.
    
    Following principles.md: "After writing a test, intentionally break the code.
    If the test still passes, it's a Liar."
    """

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_fails_when_resolution_missing(
        self, mock_get_client, mock_repo_class, mock_get_resolver
    ):
        """
        SABOTAGE TEST: This test verifies that symbol resolution is actually used.
        
        If we remove symbol resolution from compute_for_ticker, this test should FAIL
        because Aurora will be queried with DR symbol instead of Yahoo symbol.
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
        
        # Mock repository - returns data ONLY for Yahoo symbol query
        mock_repo = MagicMock()
        def get_prices_side_effect(symbol, **kwargs):
            if symbol == 'D05.SI':
                return pd.DataFrame({
                    'Close': [50.0] * 300,
                    'Open': [49.0] * 300,
                    'High': [51.0] * 300,
                    'Low': [48.0] * 300,
                    'Volume': [1000] * 300
                })
            else:
                return pd.DataFrame()  # Empty for DR symbol
        
        mock_repo.get_prices_as_dataframe.side_effect = get_prices_side_effect
        mock_repo_class.return_value = mock_repo
        
        # Act
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        result = service.compute_for_ticker('DBS19', include_report=False)
        
        # Assert: Should succeed because Yahoo symbol was used
        assert result['indicators'] is True, \
            "Should succeed when Yahoo symbol used for Aurora query"
        
        # Verify repository was called with Yahoo symbol (not DR symbol)
        calls = mock_repo.get_prices_as_dataframe.call_args_list
        assert len(calls) > 0, "Repository should be called"
        assert calls[0][0][0] == 'D05.SI', \
            "SABOTAGE CHECK: If this fails, symbol resolution is not working!"
