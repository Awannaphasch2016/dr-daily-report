# -*- coding: utf-8 -*-
"""
Tests for S3 Data Lake Phase 2: Processed Data Storage

TDD Approach: Tests written BEFORE implementation
Following principles.md guidelines:
- Class-based tests
- Test behavior, not implementation
- Test both success AND failure paths
- Verify tests can actually fail (test sabotage)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json


class TestDataLakeStoragePhase2:
    """Test suite for Phase 2 processed data storage methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict('os.environ', {
            'DATA_LAKE_BUCKET': 'test-data-lake-bucket'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Tear down test fixtures."""
        self.env_patcher.stop()

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_success(self, mock_boto3):
        """
        GIVEN computed indicators for a ticker
        WHEN storing to data lake with source raw data link
        THEN should store with correct key structure, tags, and metadata
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        ticker = 'NVDA'
        indicators = {
            'sma_20': 150.5,
            'sma_50': 145.2,
            'rsi_14': 65.3,
            'macd': 2.5,
            'bb_upper': 155.0,
            'bb_lower': 145.0
        }
        source_raw_data_key = 'raw/yfinance/NVDA/2025-01-15/20250115_120000.json'
        computed_at = datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)

        # Act
        result = data_lake.store_indicators(
            ticker=ticker,
            indicators=indicators,
            source_raw_data_key=source_raw_data_key,
            computed_at=computed_at
        )

        # Assert: Should succeed
        assert result is True, "store_indicators should return True on success"

        # Assert: S3 put_object called with correct parameters
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]

        # Verify key structure: processed/indicators/{ticker}/{date}/{timestamp}.json
        s3_key = call_kwargs['Key']
        assert s3_key.startswith('processed/indicators/NVDA/2025-01-15/'), \
            f"Key should start with processed/indicators/NVDA/2025-01-15/, got {s3_key}"
        assert s3_key.endswith('.json'), \
            f"Key should end with .json, got {s3_key}"

        # Verify bucket
        assert call_kwargs['Bucket'] == 'test-bucket', \
            "Bucket should match"

        # Verify content type
        assert call_kwargs['ContentType'] == 'application/json', \
            "Content type should be application/json"

        # Verify body contains indicators
        body_data = json.loads(call_kwargs['Body'])
        assert body_data == indicators, \
            "Body should contain indicators data"

        # Verify tags contain source raw data link
        tags = call_kwargs['Tagging']
        assert 'source=computed' in tags, \
            "Tags should contain source=computed"
        assert 'ticker=NVDA' in tags, \
            "Tags should contain ticker=NVDA"
        assert 'computed_at=2025-01-15' in tags, \
            "Tags should contain computed_at date"
        assert f'source_raw_data={source_raw_data_key}' in tags.replace('&', '&'), \
            "Tags should contain source_raw_data key"

        # Verify metadata
        metadata = call_kwargs['Metadata']
        assert metadata['source'] == 'indicators_computation', \
            "Metadata should contain source=indicators_computation"
        assert metadata['ticker'] == 'NVDA', \
            "Metadata should contain ticker"
        assert metadata['source_raw_data_key'] == source_raw_data_key, \
            "Metadata should contain source_raw_data_key"
        assert 'computation_version' in metadata, \
            "Metadata should contain computation_version"

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_without_source_key(self, mock_boto3):
        """
        GIVEN indicators without source raw data key
        WHEN storing to data lake
        THEN should still succeed (source_key is optional for backward compatibility)
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {'sma_20': 150.5, 'rsi_14': 65.3}

        # Act
        result = data_lake.store_indicators(
            ticker='NVDA',
            indicators=indicators,
            source_raw_data_key=None  # Optional
        )

        # Assert: Should succeed even without source key
        assert result is True, "store_indicators should succeed without source key"

        # Verify tags don't contain source_raw_data when None
        call_kwargs = mock_s3_client.put_object.call_args[1]
        tags = call_kwargs['Tagging']
        assert 'source_raw_data=' not in tags, \
            "Tags should not contain source_raw_data when None"

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_s3_failure(self, mock_boto3):
        """
        GIVEN S3 put_object fails
        WHEN storing indicators
        THEN should return False and log error (non-blocking)
        """
        # Arrange
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'PutObject'
        )
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.store_indicators(
            ticker='NVDA',
            indicators={'sma_20': 150.5}
        )

        # Assert: Should return False on failure
        assert result is False, "store_indicators should return False on S3 failure"

    @patch('src.data.data_lake.boto3')
    def test_store_percentiles_success(self, mock_boto3):
        """
        GIVEN computed percentiles for a ticker
        WHEN storing to data lake with source raw data link
        THEN should store with correct key structure, tags, and metadata
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        ticker = 'DBS19'
        percentiles = {
            'current_price_percentile': 75.5,
            'rsi_percentile': 68.2,
            'macd_percentile': 55.0,
            'uncertainty_percentile': 42.3
        }
        source_raw_data_key = 'raw/yfinance/DBS19/2025-01-15/20250115_120000.json'
        computed_at = datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)

        # Act
        result = data_lake.store_percentiles(
            ticker=ticker,
            percentiles=percentiles,
            source_raw_data_key=source_raw_data_key,
            computed_at=computed_at
        )

        # Assert: Should succeed
        assert result is True, "store_percentiles should return True on success"

        # Assert: Key structure: processed/percentiles/{ticker}/{date}/{timestamp}.json
        call_kwargs = mock_s3_client.put_object.call_args[1]
        s3_key = call_kwargs['Key']
        assert s3_key.startswith('processed/percentiles/DBS19/2025-01-15/'), \
            f"Key should start with processed/percentiles/DBS19/2025-01-15/, got {s3_key}"

        # Verify metadata source
        metadata = call_kwargs['Metadata']
        assert metadata['source'] == 'percentiles_computation', \
            "Metadata should contain source=percentiles_computation"

    @patch('src.data.data_lake.boto3')
    def test_store_percentiles_s3_failure(self, mock_boto3):
        """
        GIVEN S3 put_object fails
        WHEN storing percentiles
        THEN should return False (non-blocking)
        """
        # Arrange
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}},
            'PutObject'
        )
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.store_percentiles(
            ticker='NVDA',
            percentiles={'rsi_percentile': 65.0}
        )

        # Assert: Should return False on failure
        assert result is False, "store_percentiles should return False on S3 failure"

    @patch('src.data.data_lake.boto3')
    @patch.dict('os.environ', {}, clear=True)
    def test_store_indicators_data_lake_disabled(self, mock_boto3):
        """
        GIVEN data lake bucket not configured
        WHEN storing indicators
        THEN should return False gracefully
        """
        # Arrange
        import os
        # Ensure no DATA_LAKE_BUCKET in environment
        os.environ.pop('DATA_LAKE_BUCKET', None)

        from src.data.data_lake import DataLakeStorage

        # Create with no bucket (disabled) - will read from env which is now empty
        data_lake = DataLakeStorage(bucket_name=None)

        # Act
        result = data_lake.store_indicators(
            ticker='NVDA',
            indicators={'sma_20': 150.5}
        )

        # Assert: Should return False when disabled
        assert result is False, "store_indicators should return False when data lake disabled"
        assert not data_lake.is_enabled(), "Data lake should be disabled when no bucket configured"
        mock_boto3.client.assert_not_called()

    def test_store_indicators_timestamp_format(self):
        """
        GIVEN indicators stored at specific time
        WHEN checking S3 key timestamp format
        THEN should use YYYYMMDD_HHMMSS format (matches Phase 1)
        """
        # Arrange
        with patch('src.data.data_lake.boto3') as mock_boto3:
            mock_s3_client = MagicMock()
            mock_boto3.client.return_value = mock_s3_client

            from src.data.data_lake import DataLakeStorage

            data_lake = DataLakeStorage(bucket_name='test-bucket')

            computed_at = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

            # Act
            data_lake.store_indicators(
                ticker='NVDA',
                indicators={'sma_20': 150.5},
                computed_at=computed_at
            )

            # Assert: Timestamp format matches Phase 1
            call_kwargs = mock_s3_client.put_object.call_args[1]
            s3_key = call_kwargs['Key']
            # Should contain timestamp like 20250115_123045
            assert '20250115_123045' in s3_key, \
                f"Key should contain timestamp 20250115_123045, got {s3_key}"
