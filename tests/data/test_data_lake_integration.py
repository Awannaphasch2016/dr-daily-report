# -*- coding: utf-8 -*-
"""
Integration Tests for Data Lake Storage

End-to-end tests following principles.mdc:
- PrecomputeService → DataLakeStorage → S3 → Verification
- Fail-fast behavior for type errors
- Round-trip verification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timezone
import json
from botocore.exceptions import ClientError


class TestDataLakeIntegration:
    """Integration tests following principles.mdc."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict('os.environ', {
            'DATA_LAKE_BUCKET': 'test-data-lake-bucket'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Tear down test fixtures."""
        self.env_patcher.stop()

    @pytest.mark.integration
    @patch('src.data.data_lake.boto3')
    @patch('src.data.aurora.precompute_service.get_aurora_client')
    @patch('src.data.aurora.precompute_service.TickerRepository')
    @patch('src.data.aurora.precompute_service.TechnicalAnalyzer')
    def test_precompute_service_stores_with_all_principles(
        self,
        mock_analyzer_class,
        mock_repo_class,
        mock_aurora_client,
        mock_boto3
    ):
        """End-to-end test: PrecomputeService → DataLakeStorage → S3."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Aurora components
        mock_aurora = MagicMock()
        mock_aurora_client.return_value = mock_aurora

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_ticker_info.return_value = {'id': 1, 'symbol': 'DBS19'}
        mock_repo.get_prices_as_dataframe.return_value = MagicMock(empty=False)

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.calculate_historical_indicators.return_value = MagicMock(
            iloc=[MagicMock(get=lambda k: {'Open': 100, 'High': 110, 'Low': 95, 'Close': 105, 'Volume': 1000000, 'SMA_20': 100, 'SMA_50': 98, 'SMA_200': 95, 'RSI': 65, 'MACD': 2.5, 'MACD_Signal': 2.0, 'BB_Upper': 110, 'BB_Middle': 100, 'BB_Lower': 90, 'ATR': 5, 'VWAP': 100, 'Volume_SMA': 1000000, 'Volume_Ratio': 1.0, 'Uncertainty_Score': 0.5, 'Price_VWAP_Pct': 5.0})]
        )
        mock_analyzer.calculate_all_indicators_with_percentiles.return_value = {
            'indicators': {},
            'percentiles': {}
        }

        # Mock S3 storage verification
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({'sma_20': 100.0}).encode())
        }

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # Act: Call PrecomputeService.compute_for_ticker('DBS19')
        result = service.compute_for_ticker('DBS19', include_report=False)

        # Assert: Verify indicators stored in S3
        assert result.get('indicators') is True, "Indicators should be stored"

        # Verify S3 put_object was called (indicators stored)
        indicator_calls = [call for call in mock_s3_client.put_object.call_args_list
                          if 'indicators' in str(call)]
        assert len(indicator_calls) > 0, "Should store indicators to S3"

        # Verify files exist (Explicit Failure Detection)
        assert mock_s3_client.head_object.called, "Should verify file exists"

        # Verify files can be retrieved (Round-Trip Test)
        assert mock_s3_client.get_object.called, "Should retrieve file to verify"

    @pytest.mark.integration
    @patch('src.data.data_lake.boto3')
    @patch('src.data.aurora.precompute_service.get_aurora_client')
    @patch('src.data.aurora.precompute_service.TickerRepository')
    @patch('src.data.aurora.precompute_service.TechnicalAnalyzer')
    def test_precompute_service_fails_fast_on_type_errors(
        self,
        mock_analyzer_class,
        mock_repo_class,
        mock_aurora_client,
        mock_boto3
    ):
        """Verify fail-fast behavior for type errors."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Aurora components
        mock_aurora = MagicMock()
        mock_aurora_client.return_value = mock_aurora

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_ticker_info.return_value = {'id': 1, 'symbol': 'DBS19'}
        mock_repo.get_prices_as_dataframe.return_value = MagicMock(empty=False)

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.calculate_historical_indicators.return_value = MagicMock(
            iloc=[MagicMock(get=lambda k: {'Open': 100, 'High': 110, 'Low': 95, 'Close': 105, 'Volume': 1000000, 'SMA_20': 100, 'SMA_50': 98, 'SMA_200': 95, 'RSI': 65, 'MACD': 2.5, 'MACD_Signal': 2.0, 'BB_Upper': 110, 'BB_Middle': 100, 'BB_Lower': 90, 'ATR': 5, 'VWAP': 100, 'Volume_SMA': 1000000, 'Volume_Ratio': 1.0, 'Uncertainty_Score': 0.5, 'Price_VWAP_Pct': 5.0})]
        )

        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # Mock compute_daily_indicators to return indicators with date objects
        # This simulates a bug where date objects are passed instead of ISO strings
        original_compute = service.compute_daily_indicators

        def mock_compute_with_date_objects(symbol, hist_df, indicator_date=None):
            result = original_compute(symbol, hist_df, indicator_date)
            # Inject date object (simulating bug)
            result['buggy_date_field'] = date(2025, 1, 15)  # date object - should fail
            return result

        service.compute_daily_indicators = mock_compute_with_date_objects

        # Act & Assert: Verify TypeError raised (not caught silently)
        with pytest.raises(TypeError) as exc_info:
            service.compute_for_ticker('DBS19', include_report=False)

        # Verify error propagates to caller (not hidden)
        assert exc_info.value is not None, "TypeError should propagate, not be hidden"

        # Verify error mentions boundary validation or serialization
        error_msg = str(exc_info.value).lower()
        assert 'boundary' in error_msg or 'json-serializable' in error_msg or 'indicators' in error_msg, \
            f"Error should mention validation issue, got: {error_msg}"
