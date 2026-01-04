"""Integration tests for async report workflow with direct Lambda invocation

Tests end-to-end async report flow after migration from SQS to direct invocation.

Boundary tested (Principle #19):
- API → Lambda.invoke() → Report Worker → DynamoDB

This replaces the old flow:
- API → SQS → Lambda Event Source → Report Worker → DynamoDB

Migration context: Validate that direct Lambda invocation maintains
same user-facing behavior as SQS-based pattern.
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch, ANY
import boto3
from moto import mock_aws


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables"""
    monkeypatch.setenv('REPORT_WORKER_FUNCTION_NAME', 'dr-daily-report-report-worker-test')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv('AURORA_HOST', 'test-aurora.cluster.amazonaws.com')
    monkeypatch.setenv('PDF_BUCKET_NAME', 'test-pdf-bucket')
    monkeypatch.setenv('JOBS_TABLE_NAME', 'test-jobs-table')
    monkeypatch.setenv('DYNAMODB_CACHE_TABLE', 'test-cache-table')
    monkeypatch.setenv('CACHE_BACKEND', 'dynamodb')


@pytest.mark.integration
def test_async_report_submit_invokes_lambda(mock_env_vars, mocker):
    """Test async report submission invokes Lambda directly (not SQS)

    Verifies:
    1. POST /api/v1/report/{ticker} creates job in DynamoDB
    2. API calls Lambda.invoke() with correct parameters
    3. InvocationType='Event' for async execution
    4. Response returns job_id immediately (non-blocking)

    Boundary: API endpoint → Lambda invoke (Service boundary)
    """
    from src.api.app import app
    from fastapi.testclient import TestClient

    # Mock DynamoDB job service
    mock_job_service = mocker.patch('src.api.app.get_job_service')
    mock_job = MagicMock()
    mock_job.job_id = 'test-job-123'
    mock_job_service.return_value.create_job.return_value = mock_job

    # Mock ticker service
    mock_ticker_service = mocker.patch('src.api.app.get_ticker_service')
    mock_ticker_service.return_value.is_supported.return_value = True

    # Mock PrecomputeService (cache check returns None for cache miss)
    with patch('src.api.app.PrecomputeService') as mock_precompute:
        mock_precompute.return_value.get_cached_report.return_value = None

        # Mock boto3 Lambda client
        mock_lambda_client = MagicMock()
        mock_boto3 = mocker.patch('src.api.app.boto3')
        mock_boto3.client.return_value = mock_lambda_client

        # Create test client
        client = TestClient(app)

        # Submit async report
        response = client.post('/api/v1/report/NVDA19')

        # Verify HTTP success
        assert response.status_code == 200
        result = response.json()

        # Verify job_id returned
        assert result['job_id'] == 'test-job-123'
        assert result['status'] == 'pending'

        # Verify Lambda.invoke() called (NOT SQS send_message)
        mock_boto3.client.assert_called_with('lambda')
        mock_lambda_client.invoke.assert_called_once()

        # Verify invoke parameters
        call_kwargs = mock_lambda_client.invoke.call_args.kwargs
        assert call_kwargs['FunctionName'] == 'dr-daily-report-report-worker-test'
        assert call_kwargs['InvocationType'] == 'Event'  # Async

        # Verify payload
        payload = json.loads(call_kwargs['Payload'])
        assert payload['job_id'] == 'test-job-123'
        assert payload['ticker'] == 'NVDA19'
        assert payload['source'] == 'telegram_api'


@pytest.mark.integration
def test_async_report_cache_hit_skips_lambda_invocation(mock_env_vars, mocker):
    """Test cached report skips Lambda invocation (optimization)

    When precomputed report exists in cache:
    1. API returns cached job_id immediately
    2. Status = 'completed' (not 'pending')
    3. Lambda.invoke() NOT called (no async processing needed)

    This behavior should remain unchanged after migration.
    """
    from src.api.app import app
    from fastapi.testclient import TestClient

    # Mock ticker service
    mock_ticker_service = mocker.patch('src.api.app.get_ticker_service')
    mock_ticker_service.return_value.is_supported.return_value = True
    mock_ticker_service.return_value.get_ticker_info.return_value = {
        'yahoo_ticker': 'NVDA'
    }

    # Mock PrecomputeService (cache HIT)
    with patch('src.api.app.PrecomputeService') as mock_precompute:
        mock_precompute.return_value.get_cached_report.return_value = {
            'id': 'cached-123',
            'report_text': 'Cached report content',
            'ticker': 'NVDA'
        }

        # Mock boto3 Lambda client (should NOT be called)
        mock_lambda_client = MagicMock()
        mock_boto3 = mocker.patch('src.api.app.boto3')
        mock_boto3.client.return_value = mock_lambda_client

        # Create test client
        client = TestClient(app)

        # Submit async report
        response = client.post('/api/v1/report/NVDA19')

        # Verify HTTP success
        assert response.status_code == 200
        result = response.json()

        # Verify cached job_id format
        assert result['job_id'].startswith('cached_')
        assert result['status'] == 'completed'  # Already completed

        # CRITICAL: Lambda.invoke() should NOT be called (cache hit)
        mock_lambda_client.invoke.assert_not_called()


@pytest.mark.integration
@mock_aws
def test_report_worker_processes_direct_invocation_event():
    """Test report worker Lambda processes direct invocation event

    Simulates Lambda receiving direct invoke payload:
    {
        "job_id": "job123",
        "ticker": "NVDA19",
        "source": "telegram_api"
    }

    Verifies:
    1. Handler detects direct mode (not SQS)
    2. Job processing succeeds
    3. DynamoDB job status updated

    Boundary: Lambda event format (Data boundary)
    """
    import os

    # Set up environment
    os.environ.update({
        'OPENROUTER_API_KEY': 'test-key',
        'AURORA_HOST': 'test-aurora.cluster.amazonaws.com',
        'PDF_BUCKET_NAME': 'test-pdf-bucket',
        'JOBS_TABLE_NAME': 'test-jobs-table',
        'AWS_DEFAULT_REGION': 'ap-southeast-1'
    })

    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
    table = dynamodb.create_table(
        TableName='test-jobs-table',
        KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )

    # Put initial job (status=pending)
    table.put_item(Item={
        'job_id': 'job123',
        'ticker': 'NVDA19',
        'status': 'pending',
        'created_at': '2026-01-04T00:00:00Z'
    })

    # Mock the agent to avoid actual LLM calls
    with patch('src.report_worker_handler.TickerAnalysisAgent') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        # Mock ainvoke to return successful state
        async def mock_ainvoke(state):
            return {
                'ticker': 'NVDA19',
                'report_text': 'Test report content',
                'error': None
            }

        mock_agent.ainvoke = mock_ainvoke

        # Import handler
        from src.report_worker_handler import handler

        # Direct invocation event (NEW format)
        event = {
            'job_id': 'job123',
            'ticker': 'NVDA19',
            'source': 'telegram_api'
        }

        # Invoke handler
        result = handler(event, None)

        # Verify handler returned success
        assert result['statusCode'] == 200
        assert result['ticker'] == 'NVDA19'

        # Verify job status updated in DynamoDB
        response = table.get_item(Key={'job_id': 'job123'})
        job = response['Item']

        assert job['status'] == 'completed'
        assert 'report_text' in job
        assert job['report_text'] == 'Test report content'


@pytest.mark.integration
def test_async_report_boundary_lambda_permission_denied(mock_env_vars, mocker):
    """Test graceful handling of Lambda invocation permission errors

    Simulates IAM permission denied (boundary violation).
    API should:
    1. Log error clearly
    2. Raise exception (not swallow)
    3. Job already created in DynamoDB (partial state)

    This tests error recovery at service boundary.
    """
    from src.api.app import app
    from fastapi.testclient import TestClient
    from botocore.exceptions import ClientError

    # Mock job service
    mock_job_service = mocker.patch('src.api.app.get_job_service')
    mock_job = MagicMock()
    mock_job.job_id = 'test-job-123'
    mock_job_service.return_value.create_job.return_value = mock_job

    # Mock ticker service
    mock_ticker_service = mocker.patch('src.api.app.get_ticker_service')
    mock_ticker_service.return_value.is_supported.return_value = True

    # Mock PrecomputeService (cache miss)
    with patch('src.api.app.PrecomputeService') as mock_precompute:
        mock_precompute.return_value.get_cached_report.return_value = None

        # Mock boto3 to raise permission error
        mock_lambda_client = MagicMock()
        mock_lambda_client.invoke.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User: arn:aws:... is not authorized to perform: lambda:InvokeFunction'
                }
            },
            operation_name='Invoke'
        )

        mock_boto3 = mocker.patch('src.api.app.boto3')
        mock_boto3.client.return_value = mock_lambda_client

        # Mock logger to verify error logged
        mock_logger = mocker.patch('src.api.app.logger')

        # Create test client
        client = TestClient(app)

        # Submit async report (should fail)
        response = client.post('/api/v1/report/NVDA19')

        # Verify HTTP 500 (internal server error)
        assert response.status_code == 500

        # Verify error logged
        mock_logger.error.assert_called()
        error_logs = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any('Failed to invoke report worker' in log for log in error_logs)

        # Job was created but Lambda invoke failed
        # This is expected partial state - job exists but stuck in pending


@pytest.mark.integration
def test_end_to_end_progressive_evidence_strengthening(mock_env_vars, mocker):
    """Test Principle #2: Progressive Evidence Strengthening

    Verifies async report workflow through all evidence layers:
    1. Surface signal: HTTP 200 status code
    2. Content signal: job_id in response payload
    3. Observability signal: Lambda.invoke() called (logged)
    4. Ground truth: Job created in DynamoDB

    This test validates the migration maintains evidence chain.
    """
    from src.api.app import app
    from fastapi.testclient import TestClient

    # Mock DynamoDB job service
    mock_job_service = mocker.patch('src.api.app.get_job_service')
    mock_job = MagicMock()
    mock_job.job_id = 'evidence-test-job'
    mock_job_service.return_value.create_job.return_value = mock_job

    # Mock ticker service
    mock_ticker_service = mocker.patch('src.api.app.get_ticker_service')
    mock_ticker_service.return_value.is_supported.return_value = True

    # Mock PrecomputeService (cache miss)
    with patch('src.api.app.PrecomputeService') as mock_precompute:
        mock_precompute.return_value.get_cached_report.return_value = None

        # Mock boto3 Lambda client
        mock_lambda_client = MagicMock()
        mock_boto3 = mocker.patch('src.api.app.boto3')
        mock_boto3.client.return_value = mock_lambda_client

        # Mock logger to capture observability signals
        mock_logger = mocker.patch('src.api.app.logger')

        # Create test client
        client = TestClient(app)

        # === Layer 1: Surface Signal ===
        response = client.post('/api/v1/report/NVDA19')
        assert response.status_code == 200  # ✓ Execution finished

        # === Layer 2: Content Signal ===
        result = response.json()
        assert 'job_id' in result  # ✓ Payload structure valid
        assert result['job_id'] == 'evidence-test-job'
        assert result['status'] == 'pending'  # ✓ Expected state

        # === Layer 3: Observability Signal ===
        # Verify Lambda invocation logged
        info_logs = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('Invoked report worker' in log for log in info_logs)  # ✓ Action logged

        # === Layer 4: Ground Truth ===
        # Verify job created (ground truth = DynamoDB state change)
        mock_job_service.return_value.create_job.assert_called_once_with(ticker='NVDA19')

        # Verify Lambda actually invoked (ground truth = AWS API called)
        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args.kwargs
        payload = json.loads(call_kwargs['Payload'])
        assert payload['job_id'] == 'evidence-test-job'  # ✓ Correct job dispatched

        # All 4 evidence layers verified ✓✓✓✓
