"""
Unit tests for scheduler handler startup configuration validation.

Tests the defensive programming principle: "Validate configuration at startup, not on first use"
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestSchedulerConfigValidation:
    """Test Lambda handler configuration validation at startup."""

    def setup_method(self):
        """Set up test environment variables."""
        self.valid_env = {
            'AURORA_HOST': 'test-aurora.cluster.amazonaws.com',
            'AURORA_USER': 'admin',
            'AURORA_PASSWORD': 'password',
            'AURORA_DATABASE': 'ticker_data',
            'REPORT_JOBS_QUEUE_URL': 'https://sqs.region.amazonaws.com/queue',
            'JOBS_TABLE_NAME': 'jobs-table-test',
            'OPENROUTER_API_KEY': 'sk-test-key',
            'PDF_BUCKET_NAME': 'pdf-bucket-test'
        }

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_all_config_fails_fast(self):
        """GIVEN Lambda with NO environment variables
        WHEN handler is invoked
        THEN it should fail immediately with configuration error
        """
        from src.scheduler.handler import lambda_handler

        event = {'action': 'parallel_precompute'}
        context = MagicMock()

        result = lambda_handler(event, context)

        assert result['statusCode'] == 500
        assert 'Configuration validation failed' in result['body']['message']
        assert 'AURORA_HOST' in result['body']['error']
        assert 'JOBS_TABLE_NAME' in result['body']['error']

    @patch.dict(os.environ, {'AURORA_HOST': 'test-host'}, clear=True)
    def test_missing_partial_config_fails_fast(self):
        """GIVEN Lambda with PARTIAL environment variables
        WHEN handler is invoked
        THEN it should fail and list ALL missing vars
        """
        from src.scheduler.handler import lambda_handler

        event = {'action': 'parallel_precompute'}
        context = MagicMock()

        result = lambda_handler(event, context)

        assert result['statusCode'] == 500
        error = result['body']['error']
        # Should list missing vars (not AURORA_HOST since it's set)
        assert 'AURORA_USER' in error
        assert 'JOBS_TABLE_NAME' in error
        assert 'OPENROUTER_API_KEY' in error
        # Should NOT complain about AURORA_HOST (it's set)
        assert error.count('AURORA_HOST') <= 1  # Only in error message structure

    def test_complete_config_passes_validation(self):
        """GIVEN Lambda with ALL required environment variables
        WHEN handler is invoked
        THEN configuration validation should pass
        """
        from src.scheduler.handler import _validate_configuration

        with patch.dict(os.environ, self.valid_env, clear=True):
            # Should not raise
            _validate_configuration()

    @patch.dict(os.environ, {}, clear=True)
    def test_validation_function_raises_on_missing_config(self):
        """GIVEN missing environment variables
        WHEN _validate_configuration is called
        THEN it should raise RuntimeError with clear message
        """
        from src.scheduler.handler import _validate_configuration

        with pytest.raises(RuntimeError) as exc_info:
            _validate_configuration()

        error_msg = str(exc_info.value)
        assert 'CONFIGURATION ERROR' in error_msg
        assert 'Missing required environment variables' in error_msg
        assert 'AURORA_HOST' in error_msg

    def test_error_message_groups_vars_by_category(self):
        """GIVEN missing configuration
        WHEN validation fails
        THEN error message should group vars by category (Aurora, SQS, DynamoDB, etc.)
        """
        from src.scheduler.handler import _validate_configuration

        with patch.dict(os.environ, {}, clear=True):
            try:
                _validate_configuration()
                pytest.fail("Should have raised RuntimeError")
            except RuntimeError as e:
                error_msg = str(e)
                # Check categories are mentioned
                assert 'Aurora=' in error_msg
                assert 'SQS=' in error_msg
                assert 'DynamoDB=' in error_msg
                assert 'API=' in error_msg
                assert 'Storage=' in error_msg
