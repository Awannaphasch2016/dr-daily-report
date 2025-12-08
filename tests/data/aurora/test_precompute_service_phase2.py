# -*- coding: utf-8 -*-
"""
Tests for PrecomputeService Phase 2 integration with Data Lake

TDD Approach: Tests written BEFORE full integration
Following principles.md guidelines:
- Class-based tests
- Test behavior (data lake storage happens), not implementation
- Test both success AND failure paths
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import pandas as pd


class TestPrecomputeServicePhase2:
    """Test suite for Phase 2 data lake integration in PrecomputeService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict('os.environ', {
            'DATA_LAKE_BUCKET': 'test-data-lake-bucket'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Tear down test fixtures."""
        self.env_patcher.stop()

    @patch('src.data.data_lake.DataLakeStorage')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_stores_indicators_to_data_lake(self, mock_get_client, mock_repo_class, mock_data_lake_class):
        """
        GIVEN indicators computed for a ticker
        WHEN compute_for_ticker is called
        THEN should store indicators to data lake after Aurora storage
        """
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102],
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Volume': [1000, 1100, 1200]
        })
        mock_repo.get_ticker_info.return_value = {'id': 1}
        mock_repo_class.return_value = mock_repo

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_indicators.return_value = True
        mock_data_lake_class.return_value = mock_data_lake

        # Mock Aurora execute (store_daily_indicators)
        mock_client.execute.return_value = 1

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()
        # Replace the data_lake instance with our mock
        service.data_lake = mock_data_lake

        # Act
        result = service.compute_for_ticker('NVDA', include_report=False)

        # Assert: Indicators should be stored to data lake
        assert result['indicators'] is True, "Indicators computation should succeed"
        mock_data_lake.store_indicators.assert_called_once()
        
        # Verify call arguments
        call_kwargs = mock_data_lake.store_indicators.call_args[1]
        assert call_kwargs['ticker'] == 'NVDA', "Should store indicators for correct ticker"
        assert 'indicators' in call_kwargs, "Should pass indicators dict"

    @patch('src.data.data_lake.DataLakeStorage')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_compute_for_ticker_stores_percentiles_to_data_lake(self, mock_get_client, mock_repo_class, mock_data_lake_class):
        """
        GIVEN percentiles computed for a ticker
        WHEN compute_for_ticker is called
        THEN should store percentiles to data lake after Aurora storage
        """
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102] * 100,  # Need enough data for percentiles
            'Open': [99, 100, 101] * 100,
            'High': [101, 102, 103] * 100,
            'Low': [98, 99, 100] * 100,
            'Volume': [1000, 1100, 1200] * 100
        })
        mock_repo.get_ticker_info.return_value = {'id': 1}
        mock_repo_class.return_value = mock_repo

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_percentiles.return_value = True
        mock_data_lake_class.return_value = mock_data_lake

        # Mock Aurora execute (store_percentiles)
        mock_client.execute.return_value = 1

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()
        # Replace the data_lake instance with our mock
        service.data_lake = mock_data_lake

        # Act
        result = service.compute_for_ticker('NVDA', include_report=False)

        # Assert: Percentiles should be stored to data lake
        assert result['percentiles'] is True, "Percentiles computation should succeed"
        mock_data_lake.store_percentiles.assert_called_once()
        
        # Verify call arguments
        call_kwargs = mock_data_lake.store_percentiles.call_args[1]
        assert call_kwargs['ticker'] == 'NVDA', "Should store percentiles for correct ticker"
        assert 'percentiles' in call_kwargs, "Should pass percentiles dict"

    @patch('src.data.data_lake.DataLakeStorage')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_data_lake_storage_failure_non_blocking(self, mock_get_client, mock_repo_class, mock_data_lake_class):
        """
        GIVEN data lake storage fails
        WHEN compute_for_ticker is called
        THEN Aurora storage should still succeed (non-blocking)
        """
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102],
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Volume': [1000, 1100, 1200]
        })
        mock_repo.get_ticker_info.return_value = {'id': 1}
        mock_repo_class.return_value = mock_repo

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = True
        mock_data_lake.store_indicators.side_effect = Exception('Data lake error')
        mock_data_lake_class.return_value = mock_data_lake

        # Mock Aurora execute (should succeed)
        mock_client.execute.return_value = 1

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()
        # Replace the data_lake instance with our mock
        service.data_lake = mock_data_lake

        # Act
        result = service.compute_for_ticker('NVDA', include_report=False)

        # Assert: Aurora storage should succeed even if data lake fails
        assert result['indicators'] is True, "Aurora storage should succeed despite data lake failure"
        assert mock_client.execute.called, "Aurora storage should be called"

    @patch('src.data.data_lake.DataLakeStorage')
    @patch('src.data.aurora.repository.TickerRepository')
    @patch('src.data.aurora.client.get_aurora_client')
    def test_data_lake_disabled_does_not_store(self, mock_get_client, mock_repo_class, mock_data_lake_class):
        """
        GIVEN data lake is disabled
        WHEN compute_for_ticker is called
        THEN should skip data lake storage but still store to Aurora
        """
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.get_prices_as_dataframe.return_value = pd.DataFrame({
            'Close': [100, 101, 102],
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Volume': [1000, 1100, 1200]
        })
        mock_repo.get_ticker_info.return_value = {'id': 1}
        mock_repo_class.return_value = mock_repo

        mock_data_lake = MagicMock()
        mock_data_lake.is_enabled.return_value = False  # Disabled
        mock_data_lake_class.return_value = mock_data_lake

        mock_client.execute.return_value = 1

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()
        # Replace the data_lake instance with our mock
        service.data_lake = mock_data_lake

        # Act
        result = service.compute_for_ticker('NVDA', include_report=False)

        # Assert: Should succeed but not call data lake storage
        assert result['indicators'] is True, "Aurora storage should succeed"
        mock_data_lake.store_indicators.assert_not_called(), \
            "Data lake storage should not be called when disabled"
