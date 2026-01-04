"""Unit tests for report worker handler migration to dual-mode

Tests the updated handler that supports both:
1. Direct Lambda invocation (new)
2. SQS event processing (backward compatible)
3. Migration mode (existing)

Migration context: Principle #19 (Cross-Boundary Contract Testing)
Tests data boundary: Event format transition (SQS → Direct)
"""

import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables for handler validation"""
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv('AURORA_HOST', 'test-aurora.cluster.amazonaws.com')
    monkeypatch.setenv('PDF_BUCKET_NAME', 'test-pdf-bucket')
    monkeypatch.setenv('JOBS_TABLE_NAME', 'test-jobs-table')


@pytest.fixture
def mock_process_job():
    """Mock _process_single_job to isolate handler event routing logic"""
    with patch('src.report_worker_handler._process_single_job') as mock:
        mock.return_value = {'statusCode': 200, 'ticker': 'NVDA19'}
        yield mock


def test_handler_direct_invocation_mode(mock_env_vars, mock_process_job):
    """Test handler processes direct Lambda invocation (NEW mode)

    Event format:
    {
        "job_id": "job123",
        "ticker": "NVDA19",
        "source": "telegram_api"
    }

    Verifies:
    - Handler detects direct invocation mode (presence of job_id + ticker)
    - Calls _process_single_job with correct parameters
    - Returns job processing result
    """
    from src.report_worker_handler import handler

    # Direct invocation event (NEW format)
    event = {
        'job_id': 'job123',
        'ticker': 'NVDA19',
        'source': 'telegram_api'
    }

    result = handler(event, None)

    # Verify _process_single_job called with extracted values
    mock_process_job.assert_called_once_with('job123', 'NVDA19')

    # Verify result returned
    assert result['statusCode'] == 200
    assert result['ticker'] == 'NVDA19'


def test_handler_backward_compatible_sqs_mode(mock_env_vars, mock_process_job, mocker):
    """Test handler still supports SQS events (backward compatibility)

    Event format:
    {
        "Records": [
            {
                "body": "{\"job_id\": \"job123\", \"ticker\": \"NVDA19\"}"
            }
        ]
    }

    Verifies:
    - Handler detects SQS mode (presence of Records array)
    - Parses SQS record body JSON
    - Calls process_record for each record
    - Returns processing summary
    """
    # Mock process_record to avoid actual job processing
    mock_process_record = mocker.patch('src.report_worker_handler.process_record')
    mock_process_record.return_value = None  # Async function returns None

    from src.report_worker_handler import handler

    # SQS event format (EXISTING format for backward compatibility)
    event = {
        'Records': [
            {
                'body': json.dumps({
                    'job_id': 'job123',
                    'ticker': 'NVDA19'
                })
            }
        ]
    }

    result = handler(event, None)

    # Verify process_record called (via asyncio.run)
    mock_process_record.assert_called_once()

    # Verify SQS processing summary returned
    assert result['statusCode'] == 200
    assert result['processed'] == 1


def test_handler_sqs_mode_multiple_records(mock_env_vars, mock_process_job, mocker):
    """Test handler processes multiple SQS records in batch

    SQS can send up to 10 records per Lambda invocation.
    Handler should process each record sequentially.
    """
    # Mock process_record to avoid actual job processing
    mock_process_record = mocker.patch('src.report_worker_handler.process_record')
    mock_process_record.return_value = None

    from src.report_worker_handler import handler

    # SQS event with 3 records
    event = {
        'Records': [
            {'body': json.dumps({'job_id': 'job1', 'ticker': 'NVDA19'})},
            {'body': json.dumps({'job_id': 'job2', 'ticker': 'AAPL'})},
            {'body': json.dumps({'job_id': 'job3', 'ticker': 'TSLA'})}
        ]
    }

    result = handler(event, None)

    # Verify all 3 records processed
    assert mock_process_record.call_count == 3
    assert result['processed'] == 3


def test_handler_migration_mode_unchanged(mock_env_vars):
    """Test handler still routes to migration_handler (existing mode)

    Migration mode should remain unchanged.
    Event format: {"migration": "migration_name"}
    """
    from src.report_worker_handler import handler

    # Mock the migration_lambda_handler imported from src.migration_handler
    with patch('src.migration_handler.lambda_handler') as mock_migration:
        mock_migration.return_value = {'migration': 'success'}

        # Migration event
        event = {'migration': 'add_user_facing_scores_to_precomputed_reports'}

        result = handler(event, None)

        # Verify migration handler called
        mock_migration.assert_called_once()
        assert result['migration'] == 'success'


def test_handler_unknown_event_format_raises_error(mock_env_vars):
    """Test handler raises ValueError for unknown event formats

    Defensive programming: fail-fast on unexpected input.
    Should NOT silently ignore unknown event structures.
    """
    from src.report_worker_handler import handler

    # Unknown event format (missing job_id, Records, and migration)
    event = {
        'unknown_key': 'unknown_value',
        'some_data': 123
    }

    # Should raise ValueError with descriptive message
    with pytest.raises(ValueError) as exc_info:
        handler(event, None)

    error_message = str(exc_info.value)
    assert 'Unknown event format' in error_message

    # Error message should list expected formats
    assert 'migration' in error_message
    assert 'job_id' in error_message
    assert 'Records' in error_message


def test_handler_validates_config_before_processing(monkeypatch):
    """Test handler validates required env vars at startup (Principle #1)

    Missing OPENROUTER_API_KEY should fail before attempting job processing.
    This prevents wasted Lambda execution time.
    """
    from src.report_worker_handler import handler

    # Clear required env var
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

    # Set other required vars
    monkeypatch.setenv('AURORA_HOST', 'test-host')
    monkeypatch.setenv('PDF_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('JOBS_TABLE_NAME', 'test-table')

    # Direct invocation event
    event = {'job_id': 'job123', 'ticker': 'NVDA19'}

    # Should raise ValueError from _validate_required_config()
    with pytest.raises(ValueError) as exc_info:
        handler(event, None)

    # Verify it mentions the missing env var
    assert 'OPENROUTER_API_KEY' in str(exc_info.value)


def test_handler_direct_mode_missing_ticker_field():
    """Test handler detects incomplete direct invocation event

    Event with job_id but missing ticker should be treated as unknown format.
    Both fields required for direct invocation mode.
    """
    from src.report_worker_handler import handler

    # Set minimal env vars to get past validation
    import os
    os.environ.update({
        'OPENROUTER_API_KEY': 'test',
        'AURORA_HOST': 'test',
        'PDF_BUCKET_NAME': 'test',
        'JOBS_TABLE_NAME': 'test'
    })

    # Incomplete direct invocation (missing ticker)
    event = {'job_id': 'job123'}

    # Should raise ValueError (unknown format)
    with pytest.raises(ValueError) as exc_info:
        handler(event, None)

    assert 'Unknown event format' in str(exc_info.value)


def test_handler_direct_mode_logs_source_field(mock_env_vars, mock_process_job, mocker):
    """Test handler logs the 'source' field for tracing

    Direct invocation includes 'source' field for debugging.
    Handler should log this for correlation.
    """
    from src.report_worker_handler import handler

    # Mock logger
    mock_logger = mocker.patch('src.report_worker_handler.logger')

    event = {
        'job_id': 'job123',
        'ticker': 'NVDA19',
        'source': 'telegram_api'
    }

    handler(event, None)

    # Verify logger.info called with source info
    mock_logger.info.assert_called()
    log_message = mock_logger.info.call_args[0][0]

    # Should mention direct invocation mode and source
    assert 'Direct invocation' in log_message or 'direct' in log_message.lower()
    assert 'telegram_api' in log_message or event['source'] in log_message
