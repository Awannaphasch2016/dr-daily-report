# -*- coding: utf-8 -*-
"""
Tests for S3 Data Lake Phase 3: Retrieval Methods

TDD Approach: Tests written BEFORE implementation
Following principles.md guidelines:
- Class-based tests
- Test behavior, not implementation
- Test both success AND failure paths
- Verify tests can actually fail (test sabotage)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timezone
import json


class TestDataLakeStoragePhase3Retrieval:
    """Test suite for Phase 3 retrieval methods."""

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
    def test_get_latest_indicators_success(self, mock_boto3):
        """
        GIVEN multiple indicator files stored for a ticker
        WHEN retrieving latest indicators
        THEN should return the most recent indicators based on timestamp
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock list_objects_v2 to return multiple indicator files
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_120000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_123000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_110000.json',
                    'LastModified': datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }

        # Mock get_object to return latest indicators data
        latest_indicators = {
            'sma_20': 150.5,
            'sma_50': 145.2,
            'rsi_14': 65.3
        }
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(latest_indicators).encode('utf-8'))
        }

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_latest_indicators('NVDA')

        # Assert: Should return latest indicators
        assert result is not None, "get_latest_indicators should return data"
        assert isinstance(result, dict), "Result should be a dict"
        assert result['sma_20'] == 150.5, "Should return latest indicators data"

        # Verify list_objects_v2 was called with correct prefix
        mock_s3_client.list_objects_v2.assert_called_once()
        call_kwargs = mock_s3_client.list_objects_v2.call_args[1]
        assert call_kwargs['Bucket'] == 'test-bucket', "Should query correct bucket"
        assert call_kwargs['Prefix'] == 'processed/indicators/NVDA/', \
            "Should use correct prefix for ticker"

        # Verify get_object was called with latest key
        mock_s3_client.get_object.assert_called_once()
        get_call_kwargs = mock_s3_client.get_object.call_args[1]
        assert get_call_kwargs['Key'] == 'processed/indicators/NVDA/2025-01-15/20250115_123000.json', \
            "Should retrieve latest file based on timestamp"

    @patch('src.data.data_lake.boto3')
    def test_get_latest_indicators_no_data(self, mock_boto3):
        """
        GIVEN no indicator files exist for a ticker
        WHEN retrieving latest indicators
        THEN should return None
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock empty list (no files found)
        mock_s3_client.list_objects_v2.return_value = {'Contents': []}

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_latest_indicators('UNKNOWN')

        # Assert: Should return None when no data exists
        assert result is None, "get_latest_indicators should return None when no data exists"

    @patch('src.data.data_lake.boto3')
    def test_get_latest_indicators_s3_error(self, mock_boto3):
        """
        GIVEN S3 list_objects_v2 fails
        WHEN retrieving latest indicators
        THEN should return None and log error
        """
        # Arrange
        from botocore.exceptions import ClientError

        mock_s3_client = MagicMock()
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'ListObjectsV2'
        )
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_latest_indicators('NVDA')

        # Assert: Should return None on error
        assert result is None, "get_latest_indicators should return None on S3 error"

    @patch('src.data.data_lake.boto3')
    def test_get_indicators_by_date_success(self, mock_boto3):
        """
        GIVEN indicator files stored for a specific date
        WHEN retrieving indicators by date
        THEN should return indicators for that date (latest if multiple)
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        target_date = date(2025, 1, 15)

        # Mock list_objects_v2 to return files for specific date
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': f'processed/indicators/NVDA/{target_date.isoformat()}/20250115_120000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': f'processed/indicators/NVDA/{target_date.isoformat()}/20250115_123000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
                }
            ]
        }

        indicators_data = {'sma_20': 150.5, 'rsi_14': 65.3}
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(indicators_data).encode('utf-8'))
        }

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_indicators_by_date('NVDA', target_date)

        # Assert: Should return indicators for the date
        assert result is not None, "get_indicators_by_date should return data"
        assert result['sma_20'] == 150.5, "Should return correct indicators"

        # Verify prefix includes date
        call_kwargs = mock_s3_client.list_objects_v2.call_args[1]
        assert call_kwargs['Prefix'] == f'processed/indicators/NVDA/{target_date.isoformat()}/', \
            "Should use date-specific prefix"

    @patch('src.data.data_lake.boto3')
    def test_get_indicators_by_date_not_found(self, mock_boto3):
        """
        GIVEN no indicators exist for a specific date
        WHEN retrieving indicators by date
        THEN should return None
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        mock_s3_client.list_objects_v2.return_value = {'Contents': []}

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_indicators_by_date('NVDA', date(2025, 1, 20))

        # Assert: Should return None when no data for date
        assert result is None, "get_indicators_by_date should return None when no data exists"

    @patch('src.data.data_lake.boto3')
    def test_get_percentiles_by_date_success(self, mock_boto3):
        """
        GIVEN percentile files stored for a specific date
        WHEN retrieving percentiles by date
        THEN should return percentiles for that date (latest if multiple)
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        target_date = date(2025, 1, 15)

        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': f'processed/percentiles/NVDA/{target_date.isoformat()}/20250115_123000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
                }
            ]
        }

        percentiles_data = {
            'current_price_percentile': 75.5,
            'rsi_percentile': 68.2
        }
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(percentiles_data).encode('utf-8'))
        }

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_percentiles_by_date('NVDA', target_date)

        # Assert: Should return percentiles for the date
        assert result is not None, "get_percentiles_by_date should return data"
        assert result['current_price_percentile'] == 75.5, "Should return correct percentiles"

        # Verify prefix uses percentiles path
        call_kwargs = mock_s3_client.list_objects_v2.call_args[1]
        assert call_kwargs['Prefix'] == f'processed/percentiles/NVDA/{target_date.isoformat()}/', \
            "Should use percentiles prefix"

    @patch('src.data.data_lake.boto3')
    def test_get_latest_indicators_data_lake_disabled(self, mock_boto3):
        """
        GIVEN data lake is disabled
        WHEN retrieving latest indicators
        THEN should return None gracefully
        """
        # Arrange
        import os
        os.environ.pop('DATA_LAKE_BUCKET', None)

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name=None)

        # Act
        result = data_lake.get_latest_indicators('NVDA')

        # Assert: Should return None when disabled
        assert result is None, "get_latest_indicators should return None when data lake disabled"
        mock_boto3.client.assert_not_called()

    @patch('src.data.data_lake.boto3')
    def test_get_latest_indicators_sorts_by_timestamp_correctly(self, mock_boto3):
        """
        GIVEN multiple indicator files with different timestamps
        WHEN retrieving latest indicators
        THEN should select the file with the latest LastModified timestamp
        """
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Files with timestamps in non-chronological order (test sorting)
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_120000.json',
                    'LastModified': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_150000.json',  # Latest
                    'LastModified': datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed/indicators/NVDA/2025-01-15/20250115_110000.json',
                    'LastModified': datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }

        latest_indicators = {'sma_20': 155.0}  # Different value for latest
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(latest_indicators).encode('utf-8'))
        }

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Act
        result = data_lake.get_latest_indicators('NVDA')

        # Assert: Should retrieve the latest file (15:00:00)
        assert result is not None, "Should return data"
        assert result['sma_20'] == 155.0, "Should return latest indicators"

        # Verify get_object called with latest key
        get_call_kwargs = mock_s3_client.get_object.call_args[1]
        assert get_call_kwargs['Key'] == 'processed/indicators/NVDA/2025-01-15/20250115_150000.json', \
            "Should select file with latest LastModified timestamp"
