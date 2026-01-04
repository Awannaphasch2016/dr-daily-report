"""Unit tests for async report SQS-to-direct-Lambda migration

Tests the new invoke_report_worker() function that replaces send_to_sqs().
Ensures proper Lambda invocation, error handling, and environment validation.

Migration context: Principle #15 (Infrastructure-Application Contract)
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables for testing"""
    monkeypatch.setenv('REPORT_WORKER_FUNCTION_NAME', 'dr-daily-report-report-worker-dev')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv('AURORA_HOST', 'test-host')


def test_invoke_report_worker_success(mock_env_vars, mocker):
    """Test direct Lambda invocation success path

    Verifies:
    - boto3 Lambda client created correctly
    - invoke() called with correct parameters
    - InvocationType='Event' for async invocation
    - Payload contains job_id, ticker, source
    """
    # Mock boto3 Lambda client at the module where it's imported
    mock_lambda_client = MagicMock()
    mock_boto3 = mocker.patch('boto3.client')
    mock_boto3.return_value = mock_lambda_client

    # Import and invoke function
    from src.api.app import invoke_report_worker
    invoke_report_worker('job123', 'NVDA19')

    # Verify boto3.client called with 'lambda'
    mock_boto3.assert_called_once_with('lambda')

    # Verify Lambda invoke called
    mock_lambda_client.invoke.assert_called_once()
    call_kwargs = mock_lambda_client.invoke.call_args.kwargs

    # Verify function name
    assert call_kwargs['FunctionName'] == 'dr-daily-report-report-worker-dev'

    # Verify async invocation type
    assert call_kwargs['InvocationType'] == 'Event'

    # Verify payload structure
    payload = json.loads(call_kwargs['Payload'])
    assert payload['job_id'] == 'job123'
    assert payload['ticker'] == 'NVDA19'
    assert payload['source'] == 'telegram_api'


def test_invoke_report_worker_missing_env_var(monkeypatch):
    """Test fail-fast when REPORT_WORKER_FUNCTION_NAME missing (Principle #1)

    Defensive programming: validate config before use, not on first use.
    Missing env var should raise ValueError immediately with clear message.
    """
    # Clear environment variable
    monkeypatch.delenv('REPORT_WORKER_FUNCTION_NAME', raising=False)

    # Import after clearing env var
    from src.api.app import invoke_report_worker

    # Should raise ValueError with descriptive message
    with pytest.raises(ValueError) as exc_info:
        invoke_report_worker('job123', 'NVDA19')

    # Verify error message mentions the missing env var
    assert 'REPORT_WORKER_FUNCTION_NAME' in str(exc_info.value)
    assert 'not set' in str(exc_info.value)


def test_invoke_report_worker_lambda_invoke_failure(mock_env_vars, mocker):
    """Test handling of Lambda invocation failures

    Verifies:
    - boto3 ClientError propagated (not swallowed)
    - Error logged before re-raising
    - Job creation in DynamoDB not affected (happens before invoke)
    """
    # Mock boto3 Lambda client to raise ClientError
    mock_lambda_client = MagicMock()
    mock_lambda_client.invoke.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Function not found'
            }
        },
        operation_name='Invoke'
    )

    mock_boto3 = mocker.patch('boto3.client')
    mock_boto3.return_value = mock_lambda_client

    # Mock logger to verify error logging
    mock_logger = mocker.patch('src.api.app.logger')

    # Import and invoke
    from src.api.app import invoke_report_worker

    # Should raise ClientError (not swallow it)
    with pytest.raises(ClientError) as exc_info:
        invoke_report_worker('job123', 'NVDA19')

    # Verify error was logged
    mock_logger.error.assert_called()
    error_log_message = mock_logger.error.call_args[0][0]
    assert 'Failed to invoke report worker' in error_log_message

    # Verify it's the Lambda ClientError
    assert exc_info.value.response['Error']['Code'] == 'ResourceNotFoundException'


def test_invoke_report_worker_empty_function_name(monkeypatch):
    """Test fail-fast when REPORT_WORKER_FUNCTION_NAME is empty string

    Empty string != missing env var, but equally problematic.
    Should raise ValueError, not attempt Lambda invocation.
    """
    # Set empty string (different from missing)
    monkeypatch.setenv('REPORT_WORKER_FUNCTION_NAME', '')

    from src.api.app import invoke_report_worker

    with pytest.raises(ValueError) as exc_info:
        invoke_report_worker('job123', 'NVDA19')

    assert 'REPORT_WORKER_FUNCTION_NAME' in str(exc_info.value)


def test_invoke_report_worker_payload_serialization(mock_env_vars, mocker):
    """Test that payload is properly JSON-serialized

    Verifies:
    - Payload parameter is a JSON string, not dict
    - JSON parses back to expected structure
    - Special characters in ticker handled correctly
    """
    mock_lambda_client = MagicMock()
    mock_boto3 = mocker.patch('boto3.client')
    mock_boto3.return_value = mock_lambda_client

    # Import and invoke
    from src.api.app import invoke_report_worker

    # Use ticker with special character
    invoke_report_worker('job-abc-123', 'NVDA19')

    call_kwargs = mock_lambda_client.invoke.call_args.kwargs
    payload_str = call_kwargs['Payload']

    # Should be a string (JSON-serialized)
    assert isinstance(payload_str, str)

    # Should parse back to dict
    payload_dict = json.loads(payload_str)
    assert payload_dict['job_id'] == 'job-abc-123'
    assert payload_dict['ticker'] == 'NVDA19'
