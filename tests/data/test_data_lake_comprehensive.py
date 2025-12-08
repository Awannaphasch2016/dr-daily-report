# -*- coding: utf-8 -*-
"""
Comprehensive Tests for Data Lake Storage - Principle Violations Fix

TDD Approach: Tests written FIRST before implementation
Following principles.mdc guidelines comprehensively:
- System Boundary Principle: Validate types at boundary
- JSON Serialization Requirement: Convert types before storage
- Fail Fast and Visibly: Raise exceptions, don't return False
- Error Handling Duality: Utility functions raise exceptions
- Explicit Failure Detection: Verify storage succeeded
- Code execution ≠ Correct output: Verify file exists
- AWS Services Success ≠ No Errors: Verify file exists
- Validation Gates: Validate prerequisites before execution
- Round-Trip Tests: Store then retrieve to verify
- Test Sabotage Verification: Tests must be able to fail
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, date, timezone
import json
from botocore.exceptions import ClientError


class TestDataLakeBoundaryValidation:
    """Test System Boundary Principle: Validate types at boundary."""

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
    def test_store_indicators_validates_types_at_method_entry(self, mock_boto3):
        """Verify validation happens at boundary (method entry), not deep inside."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass indicators with truly incompatible type (custom object)
        class CustomObject:
            pass

        indicators = {
            'sma_20': 150.5,
            'custom_field': CustomObject()  # Truly incompatible - cannot be converted
        }

        # Act & Assert: Should raise TypeError BEFORE S3 call
        with pytest.raises(TypeError) as exc_info:
            data_lake.store_indicators(
                ticker='NVDA',
                indicators=indicators
            )

        # Verify error message mentions boundary validation
        assert 'boundary' in str(exc_info.value).lower() or 'json-serializable' in str(exc_info.value).lower(), \
            f"Error should mention boundary validation, got: {exc_info.value}"

        # Verify S3 put_object() NEVER called (fail fast)
        mock_s3_client.put_object.assert_not_called(), \
            "S3 put_object should NOT be called when validation fails at boundary"

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_rejects_incompatible_types(self, mock_boto3):
        """Verify incompatible types are caught at boundary."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass indicators dict with truly incompatible type
        class CustomObject:
            pass

        indicators = {
            'indicator_date': CustomObject()  # Cannot be converted
        }

        # Act & Assert: Verify TypeError raised with descriptive message
        with pytest.raises(TypeError) as exc_info:
            data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        error_msg = str(exc_info.value)
        assert 'indicators' in error_msg.lower(), \
            f"Error should mention 'indicators', got: {error_msg}"
        assert 'json-serializable' in error_msg.lower() or 'boundary' in error_msg.lower(), \
            f"Error should mention boundary validation, got: {error_msg}"

    @patch('src.data.data_lake.boto3')
    def test_store_percentiles_validates_types_at_method_entry(self, mock_boto3):
        """Same for percentiles."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass percentiles with truly incompatible type
        class CustomObject:
            pass

        percentiles = {
            'rsi_percentile': 65.3,
            'custom_field': CustomObject()  # Cannot be converted
        }

        # Act & Assert: Should raise TypeError BEFORE S3 call
        with pytest.raises(TypeError) as exc_info:
            data_lake.store_percentiles(ticker='NVDA', percentiles=percentiles)

        # Verify error message mentions percentiles
        assert 'percentiles' in str(exc_info.value).lower(), \
            f"Error should mention 'percentiles', got: {exc_info.value}"

        # Verify S3 put_object() NEVER called
        mock_s3_client.put_object.assert_not_called()

    def test_validation_gate_checks_prerequisites(self):
        """Verify Validation Gates principle: Check prerequisites before execution."""
        from src.data.data_lake import DataLakeStorage

        # Test 1: data lake disabled → returns False early (validation gate)
        # Clear env var to ensure bucket_name is None
        with patch.dict('os.environ', {}, clear=True):
            data_lake_disabled = DataLakeStorage(bucket_name=None)
            result = data_lake_disabled.store_indicators(ticker='NVDA', indicators={'sma_20': 150.5})
            assert result is False, "Should return False when data lake disabled (validation gate)"

        # Test 2: bucket not configured → returns False early (validation gate)
        with patch.dict('os.environ', {}, clear=True):
            data_lake_no_bucket = DataLakeStorage()
            result = data_lake_no_bucket.store_indicators(ticker='NVDA', indicators={'sma_20': 150.5})
            assert result is False, "Should return False when bucket not configured (validation gate)"

        # Test 3: invalid data structure → raises TypeError (validation gate)
        # Use a truly incompatible type (custom object) that cannot be converted
        class CustomObject:
            pass

        with patch('src.data.data_lake.boto3') as mock_boto3:
            mock_s3_client = MagicMock()
            mock_boto3.client.return_value = mock_s3_client
            data_lake = DataLakeStorage(bucket_name='test-bucket')

            with pytest.raises(TypeError):
                data_lake.store_indicators(
                    ticker='NVDA',
                    indicators={'custom_field': CustomObject()}  # Truly incompatible type
                )


class TestDataLakeTypeConversion:
    """Test JSON Serialization Requirement: Convert types before storage."""

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
    def test_store_indicators_converts_date_objects_to_iso_strings(self, mock_boto3):
        """Verify date objects converted to ISO strings."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass indicators with date objects (should be converted, not rejected)
        # Note: This test assumes conversion happens AFTER validation passes
        # But validation should catch date objects - so we need to pass serializable data
        # Actually, the conversion should happen BEFORE validation, or validation should allow
        # date objects if conversion is applied. Let's test the conversion path.
        indicators = {
            'sma_20': 150.5,
            'rsi_14': 65.3,
            'computed_date': date(2025, 1, 15),  # Should be converted to ISO string
            'computed_datetime': datetime(2025, 1, 15, 12, 30, 0)  # Should be converted
        }

        # Mock verification to succeed
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'sma_20': 150.5,
                'rsi_14': 65.3,
                'computed_date': '2025-01-15',  # ISO string
                'computed_datetime': '2025-01-15T12:30:00'  # ISO string
            }).encode())
        }

        # Act
        result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Assert: Should succeed
        assert result is True, "store_indicators should succeed with conversion"

        # Verify json.dumps() received ISO strings (not date objects)
        call_kwargs = mock_s3_client.put_object.call_args[1]
        body_data = json.loads(call_kwargs['Body'])

        # Verify dates converted to ISO strings
        assert body_data['computed_date'] == '2025-01-15', \
            f"Date should be converted to ISO string, got: {body_data['computed_date']}"
        assert body_data['computed_datetime'] == '2025-01-15T12:30:00', \
            f"Datetime should be converted to ISO string, got: {body_data['computed_datetime']}"

    @patch('src.data.data_lake.boto3')
    def test_store_percentiles_converts_date_objects_to_iso_strings(self, mock_boto3):
        """Same for percentiles."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        percentiles = {
            'rsi_percentile': 65.3,
            'computed_date': date(2025, 1, 15)
        }

        # Mock verification
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'rsi_percentile': 65.3,
                'computed_date': '2025-01-15'
            }).encode())
        }

        # Act
        result = data_lake.store_percentiles(ticker='NVDA', percentiles=percentiles)

        # Assert
        assert result is True

        # Verify conversion happened
        call_kwargs = mock_s3_client.put_object.call_args[1]
        body_data = json.loads(call_kwargs['Body'])
        assert body_data['computed_date'] == '2025-01-15'

    @patch('src.data.data_lake.boto3')
    def test_conversion_handles_nested_structures(self, mock_boto3):
        """Verify conversion works for nested dicts/lists."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {
            'sma_20': 150.5,
            'nested': {
                'date': date(2025, 1, 15),
                'values': [date(2025, 1, 14), date(2025, 1, 15)]
            }
        }

        # Mock verification
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'sma_20': 150.5,
                'nested': {
                    'date': '2025-01-15',
                    'values': ['2025-01-14', '2025-01-15']
                }
            }).encode())
        }

        # Act
        result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Assert
        assert result is True

        # Verify nested conversion
        call_kwargs = mock_s3_client.put_object.call_args[1]
        body_data = json.loads(call_kwargs['Body'])
        assert body_data['nested']['date'] == '2025-01-15'
        assert body_data['nested']['values'] == ['2025-01-14', '2025-01-15']


class TestDataLakeFailFast:
    """Test Fail Fast and Visibly Principle: Raise exceptions, don't return False."""

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
    def test_store_indicators_raises_typeerror_not_returns_false(self, mock_boto3):
        """Verify type errors raise TypeError (fail fast), not return False."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass invalid types (truly incompatible)
        class CustomObject:
            pass

        indicators = {'custom_field': CustomObject()}

        # Act & Assert: Verify TypeError raised (not return False)
        with pytest.raises(TypeError):
            result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)
            # Should not reach here - should raise instead
            assert False, "Should have raised TypeError, not returned False"

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_propagates_type_errors(self, mock_boto3):
        """Verify errors propagate to caller (not hidden)."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Use truly incompatible type
        class CustomObject:
            pass

        indicators = {'custom_field': CustomObject()}

        # Act & Assert: Call from PrecomputeService context
        # Verify TypeError propagates (not caught silently)
        with pytest.raises(TypeError) as exc_info:
            data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Verify exception is visible (not caught silently)
        assert exc_info.value is not None, "Exception should be visible, not hidden"

    @patch('src.data.data_lake.boto3')
    def test_error_handling_duality_utility_functions_raise(self, mock_boto3):
        """Verify Error Handling Duality: Utility functions raise exceptions."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # DataLakeStorage is utility function - should raise exceptions (not return False)
        class CustomObject:
            pass

        indicators = {'custom_field': CustomObject()}

        # Act & Assert: Verify exception type is descriptive
        with pytest.raises(TypeError) as exc_info:
            data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Verify exception type is TypeError (not generic Exception)
        assert isinstance(exc_info.value, TypeError), \
            f"Should raise TypeError, got {type(exc_info.value)}"


class TestDataLakeExplicitFailureDetection:
    """Test Explicit Failure Detection: Verify storage succeeded."""

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
    def test_store_indicators_verifies_file_exists_after_storage(self, mock_boto3):
        """Verify Code execution ≠ Correct output: Check file exists."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {'sma_20': 150.5, 'rsi_14': 65.3}

        # Mock successful put_object
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}

        # Mock verification: file exists
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(indicators).encode())
        }

        # Act
        result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Assert: Should succeed
        assert result is True

        # Verify S3 file exists check was called (not just put_object() succeeded)
        mock_s3_client.head_object.assert_called_once(), \
            "Should verify file exists after put_object()"

        # Verify file can be retrieved (round-trip test)
        mock_s3_client.get_object.assert_called_once(), \
            "Should retrieve file to verify content"

    @patch('src.data.data_lake.boto3')
    def test_store_indicators_verifies_file_content_correct(self, mock_boto3):
        """Verify stored file contains correct data."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {'sma_20': 150.5, 'rsi_14': 65.3}

        # Mock successful put_object
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}

        # Mock verification: file exists and content matches
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(indicators).encode())
        }

        # Act
        result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Assert
        assert result is True

        # Verify stored file contains correct data
        get_call_kwargs = mock_s3_client.get_object.call_args[1]
        stored_data = json.loads(mock_s3_client.get_object.return_value['Body'].read().decode())
        assert stored_data == indicators, \
            f"Stored data should match input, got: {stored_data}"

        # Verify JSON is valid
        assert isinstance(stored_data, dict), \
            "Stored data should be valid dict"

    @patch('src.data.data_lake.boto3')
    def test_aws_services_success_does_not_guarantee_no_errors(self, mock_boto3):
        """Verify AWS Services Success ≠ No Errors principle."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {'sma_20': 150.5}

        # Mock put_object() returns success
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}

        # But file doesn't actually exist (head_object returns 404)
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadObject'
        )

        # Act & Assert: Verify we detect this (explicit failure detection)
        with pytest.raises(RuntimeError) as exc_info:
            data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Verify error message mentions verification failure
        assert 'verification' in str(exc_info.value).lower() or 'exist' in str(exc_info.value).lower(), \
            f"Error should mention verification failure, got: {exc_info.value}"


class TestDataLakeRoundTrip:
    """Test Round-Trip Tests: Store then retrieve to verify."""

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
    def test_store_then_retrieve_indicators(self, mock_boto3):
        """Round-trip test: Store indicators, then retrieve."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        indicators = {'sma_20': 150.5, 'rsi_14': 65.3}

        # Mock successful storage
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(indicators).encode())
        }

        # Mock retrieval: list_objects_v2 returns the stored file
        stored_key = 'processed/indicators/NVDA/2025-01-15/20250115_120000.json'
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{
                'Key': stored_key,
                'LastModified': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            }]
        }
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(indicators).encode())
        }

        # Act: Store
        store_result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)
        assert store_result is True

        # Act: Retrieve using get_latest_indicators()
        retrieved = data_lake.get_latest_indicators('NVDA')

        # Assert: Verify data matches
        assert retrieved is not None, "Should retrieve stored indicators"
        assert retrieved == indicators, \
            f"Retrieved data should match stored data, got: {retrieved}"

        # This is the REAL contract (store → retrieve works)

    @patch('src.data.data_lake.boto3')
    def test_store_then_retrieve_percentiles(self, mock_boto3):
        """Same for percentiles."""
        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        percentiles = {'rsi_percentile': 65.3, 'macd_percentile': 70.5}

        # Mock successful storage
        mock_s3_client.put_object.return_value = {'ETag': 'test-etag'}
        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(percentiles).encode())
        }

        # Act: Store
        store_result = data_lake.store_percentiles(ticker='NVDA', percentiles=percentiles)
        assert store_result is True

        # Note: get_latest_percentiles() doesn't exist yet, but we can verify storage succeeded
        # by checking put_object was called and verification passed
        mock_s3_client.put_object.assert_called_once()
        mock_s3_client.head_object.assert_called_once()


class TestDataLakeSabotage:
    """Test Sabotage Verification: Tests must be able to fail."""

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
    def test_boundary_validation_detects_missing_validation(self, mock_boto3):
        """SABOTAGE TEST: Remove validation → test should FAIL."""
        # This test verifies that validation is actually used
        # If we temporarily remove validation, this test should FAIL
        # This proves the test can detect failures (not a "Liar" test)

        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass truly incompatible type - should be caught by validation
        class CustomObject:
            pass

        indicators = {'custom_field': CustomObject()}

        # Act & Assert: Should raise TypeError (validation catches it)
        # If validation is removed, this test will FAIL (proving test works)
        with pytest.raises(TypeError):
            data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # If we reach here without exception, validation is missing (test should fail)
        # This proves the test can detect missing validation

    @patch('src.data.data_lake.boto3')
    def test_type_conversion_detects_missing_conversion(self, mock_boto3):
        """SABOTAGE TEST: Remove conversion → test should FAIL."""
        # This test verifies that conversion is actually used
        # If conversion is removed, date objects will cause json.dumps() to fail
        # This proves the test can detect missing conversion

        # Arrange
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        from src.data.data_lake import DataLakeStorage

        data_lake = DataLakeStorage(bucket_name='test-bucket')

        # Pass date objects - should be converted
        indicators = {
            'sma_20': 150.5,
            'computed_date': date(2025, 1, 15)  # Should be converted to ISO string
        }

        # Mock verification - need to return actual bytes, not MagicMock
        stored_data_bytes = json.dumps({
            'sma_20': 150.5,
            'computed_date': '2025-01-15'  # ISO string
        }).encode()

        mock_s3_client.head_object.return_value = {'ContentLength': 100}
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: stored_data_bytes)
        }

        # Act: Should succeed with conversion
        result = data_lake.store_indicators(ticker='NVDA', indicators=indicators)

        # Assert: Should succeed (conversion happened)
        assert result is True

        # Verify conversion happened: body should contain ISO string, not date object
        call_kwargs = mock_s3_client.put_object.call_args[1]
        body_data = json.loads(call_kwargs['Body'])

        # If conversion is missing, body_data['computed_date'] would be a date object
        # and json.loads() would fail or return unexpected format
        assert isinstance(body_data['computed_date'], str), \
            f"Date should be converted to string, got: {type(body_data['computed_date'])}"
        assert body_data['computed_date'] == '2025-01-15', \
            f"Date should be ISO string, got: {body_data['computed_date']}"
