# -*- coding: utf-8 -*-
"""TDD tests for parallel precompute scheduler.

These tests verify the fan-out pattern for parallel report generation:
1. Scheduler gets list of all tickers
2. Scheduler sends one SQS message per ticker
3. Report Worker processes in parallel (auto-scales)

RED: Write tests first, expect failures
GREEN: Implement until tests pass

Symbol Format Contract:
    - DB stores: Yahoo symbols (D05.SI, NVDA, C6L.SI)
    - Worker expects: DR symbols (DBS19, NVDA19, SIA19)
    - Scheduler MUST convert Yahoo → DR at boundary
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime


def _create_identity_resolver_mock():
    """Create a resolver mock that returns the same symbol (identity mapping).

    Use this for tests that don't care about symbol conversion.
    """
    resolver = MagicMock()
    resolver.to_dr.side_effect = lambda s: s  # Identity: NVDA → NVDA
    return resolver


def _create_realistic_resolver_mock():
    """Create a resolver mock with realistic Yahoo → DR mappings.

    Use this for tests that verify symbol conversion behavior.
    """
    resolver = MagicMock()
    mappings = {
        'NVDA': 'NVDA19',
        'D05.SI': 'DBS19',
        'DBS19': 'DBS19',  # Already DR
        'MWG19': 'MWG19',  # Already DR
        'MWG.VN': 'MWG19',
        'C6L.SI': 'SIA19',
    }
    resolver.to_dr.side_effect = lambda s: mappings.get(s)
    return resolver


class TestParallelPrecomputeHandler:
    """Test the parallel precompute action in scheduler handler."""

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_sends_sqs_messages_for_each_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """Scheduler should send one SQS message per ticker for parallel processing.

        This is the core behavior: fan-out to SQS for parallel Lambda execution.
        """
        # Setup: Mock resolver (identity mapping for simplicity)
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        # Setup: Mock repository to return 3 test tickers
        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'DBS19'},
            {'symbol': 'MWG19'},
        ]
        mock_precompute_class.return_value = mock_service

        # Setup: Mock job service
        mock_job_service = MagicMock()
        mock_job_service.create_job.side_effect = [
            MagicMock(job_id='rpt_001', ticker='NVDA'),
            MagicMock(job_id='rpt_002', ticker='DBS19'),
            MagicMock(job_id='rpt_003', ticker='MWG19'),
        ]
        mock_get_job_service.return_value = mock_job_service

        # Setup: Mock SQS client
        mock_sqs = MagicMock()
        mock_boto3.client.return_value = mock_sqs

        # Import and call handler with parallel_precompute action
        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: SQS messages sent for each ticker
        assert mock_sqs.send_message.call_count == 3, \
            f"Expected 3 SQS messages (one per ticker), got {mock_sqs.send_message.call_count}"

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_creates_job_for_each_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """Scheduler should create a DynamoDB job for each ticker."""
        # Setup: Mock resolver (identity mapping)
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        # Setup: Mock repository
        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'DBS19'},
        ]
        mock_precompute_class.return_value = mock_service

        # Setup: Mock job service
        mock_job_service = MagicMock()
        mock_job_service.create_job.side_effect = [
            MagicMock(job_id='rpt_001', ticker='NVDA'),
            MagicMock(job_id='rpt_002', ticker='DBS19'),
        ]
        mock_get_job_service.return_value = mock_job_service

        # Setup: Mock SQS
        mock_boto3.client.return_value = MagicMock()

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: Jobs created for each ticker
        assert mock_job_service.create_job.call_count == 2
        mock_job_service.create_job.assert_any_call(ticker='NVDA')
        mock_job_service.create_job.assert_any_call(ticker='DBS19')

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_returns_job_count(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """Response should include count of jobs submitted."""
        # Setup: Mock resolver
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'DBS19'},
            {'symbol': 'MWG19'},
        ]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.side_effect = [
            MagicMock(job_id=f'rpt_{i}', ticker=t) for i, t in enumerate(['NVDA', 'DBS19', 'MWG19'])
        ]
        mock_get_job_service.return_value = mock_job_service
        mock_boto3.client.return_value = MagicMock()

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: Response includes job count
        assert result['statusCode'] == 200
        assert result['body']['jobs_submitted'] == 3
        assert result['body']['message'] == 'Parallel precompute initiated'

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_uses_correct_queue_url(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """SQS messages should be sent to the correct queue URL from env."""
        import os

        # Setup: Mock resolver
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        # Setup: Set queue URL env var
        test_queue_url = 'https://sqs.ap-southeast-1.amazonaws.com/123/test-queue'

        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [{'symbol': 'NVDA'}]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.return_value = MagicMock(job_id='rpt_001', ticker='NVDA')
        mock_get_job_service.return_value = mock_job_service

        mock_sqs = MagicMock()
        mock_boto3.client.return_value = mock_sqs

        # Patch os.environ.get to return our test queue URL
        with patch.dict(os.environ, {'REPORT_JOBS_QUEUE_URL': test_queue_url}):
            from src.scheduler.handler import lambda_handler
            event = {'action': 'parallel_precompute'}
            result = lambda_handler(event, None)

        # Assert: Correct queue URL used
        call_args = mock_sqs.send_message.call_args
        assert call_args is not None, "send_message was not called"
        assert call_args.kwargs.get('QueueUrl') == test_queue_url or \
               (len(call_args) > 1 and call_args[1].get('QueueUrl') == test_queue_url)

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_handles_sqs_failure_gracefully(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """If SQS fails for one ticker, continue with others and report failures."""
        # Setup: Mock resolver
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        # Setup: 3 tickers, SQS fails on second
        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'DBS19'},
            {'symbol': 'MWG19'},
        ]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.side_effect = [
            MagicMock(job_id='rpt_001', ticker='NVDA'),
            MagicMock(job_id='rpt_002', ticker='DBS19'),
            MagicMock(job_id='rpt_003', ticker='MWG19'),
        ]
        mock_get_job_service.return_value = mock_job_service

        # SQS fails on second message
        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = [
            None,  # NVDA: success
            Exception("SQS error"),  # DBS19: fail
            None,  # MWG19: success
        ]
        mock_boto3.client.return_value = mock_sqs

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: Partial success reported
        assert result['statusCode'] == 200
        assert result['body']['jobs_submitted'] == 2  # 2 succeeded
        assert result['body']['jobs_failed'] == 1     # 1 failed
        assert 'DBS19' in result['body']['failed_tickers']

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_respects_limit_parameter(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """Limit parameter should restrict number of tickers processed."""
        # Setup: Mock resolver (identity - TICKER0 stays TICKER0)
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        # Setup: 5 tickers available
        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': f'TICKER{i}'} for i in range(5)
        ]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.side_effect = [
            MagicMock(job_id=f'rpt_{i}', ticker=f'TICKER{i}') for i in range(5)
        ]
        mock_get_job_service.return_value = mock_job_service
        mock_boto3.client.return_value = MagicMock()

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute', 'limit': 2}
        result = lambda_handler(event, None)

        # Assert: Only 2 jobs submitted
        assert result['body']['jobs_submitted'] == 2
        assert mock_job_service.create_job.call_count == 2


class TestSQSMessageFormat:
    """Test that SQS messages have correct format for Report Worker."""

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_sqs_message_contains_job_id_and_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """SQS message body should contain job_id and ticker (Report Worker format)."""
        # Setup: Mock resolver (identity mapping)
        mock_get_resolver.return_value = _create_identity_resolver_mock()

        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [{'symbol': 'NVDA'}]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.return_value = MagicMock(job_id='rpt_abc123', ticker='NVDA')
        mock_get_job_service.return_value = mock_job_service

        mock_sqs = MagicMock()
        mock_boto3.client.return_value = mock_sqs

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        lambda_handler(event, None)

        # Assert: Message body has correct format
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs.get('MessageBody') or call_args[1].get('MessageBody'))

        assert 'job_id' in message_body, "Message body must contain job_id"
        assert 'ticker' in message_body, "Message body must contain ticker"
        assert message_body['job_id'] == 'rpt_abc123'
        assert message_body['ticker'] == 'NVDA'


class TestSymbolFormatContract:
    """
    CRITICAL: Verify scheduler sends DR symbols to worker, not Yahoo symbols.

    This test class exists because we discovered a bug where the scheduler was
    sending Yahoo symbols (D05.SI, NVDA) from the DB but the worker expected
    DR symbols (DBS19, NVDA19).

    Symbol format contract:
        - DB stores: Yahoo symbols (D05.SI, NVDA, C6L.SI)
        - Worker expects: DR symbols (DBS19, NVDA19, SIA19)
        - Scheduler MUST convert at boundary
    """

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_scheduler_converts_yahoo_to_dr_symbols(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """
        CRITICAL: Scheduler must convert Yahoo symbols from DB to DR symbols for worker.

        Bug that this catches:
            Scheduler sends D05.SI (Yahoo) instead of DBS19 (DR) to worker.
            Worker then fails with "ticker not found" error.
        """
        import json

        # Setup: Mock resolver with realistic Yahoo → DR mappings
        mock_get_resolver.return_value = _create_realistic_resolver_mock()

        # Setup: Repo returns REALISTIC Yahoo symbols (what DB actually stores)
        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'D05.SI'},   # Yahoo format - NOT DBS19!
            {'symbol': 'NVDA'},     # Yahoo format - NOT NVDA19!
            {'symbol': 'C6L.SI'},   # Yahoo format - NOT SIA19!
        ]
        mock_precompute_class.return_value = mock_service

        # Setup: Mock job service to capture what ticker is passed
        mock_job_service = MagicMock()
        created_tickers = []
        def capture_ticker(ticker):
            created_tickers.append(ticker)
            return MagicMock(job_id=f'rpt_{ticker}', ticker=ticker)
        mock_job_service.create_job.side_effect = capture_ticker
        mock_get_job_service.return_value = mock_job_service

        # Setup: Mock SQS to capture message bodies
        mock_sqs = MagicMock()
        sqs_messages = []
        def capture_sqs(**kwargs):
            sqs_messages.append(json.loads(kwargs['MessageBody']))
        mock_sqs.send_message.side_effect = capture_sqs
        mock_boto3.client.return_value = mock_sqs

        # Execute
        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: Job service received DR symbols (not Yahoo)
        assert 'DBS19' in created_tickers, \
            f"Expected DR symbol DBS19, but job service received: {created_tickers}"
        assert 'NVDA19' in created_tickers, \
            f"Expected DR symbol NVDA19, but job service received: {created_tickers}"
        assert 'SIA19' in created_tickers, \
            f"Expected DR symbol SIA19, but job service received: {created_tickers}"

        # Assert: Yahoo symbols should NOT be in created jobs
        assert 'D05.SI' not in created_tickers, \
            f"Yahoo symbol D05.SI leaked to worker! Jobs: {created_tickers}"
        assert 'C6L.SI' not in created_tickers, \
            f"Yahoo symbol C6L.SI leaked to worker! Jobs: {created_tickers}"

        # Assert: SQS messages contain DR symbols
        sqs_tickers = [msg['ticker'] for msg in sqs_messages]
        assert 'DBS19' in sqs_tickers, \
            f"SQS message should contain DR symbol DBS19, got: {sqs_tickers}"
        assert 'D05.SI' not in sqs_tickers, \
            f"Yahoo symbol leaked to SQS! Messages: {sqs_tickers}"

    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_scheduler_handles_unresolvable_symbols_gracefully(
        self, mock_precompute_class, mock_get_job_service, mock_boto3, mock_get_resolver
    ):
        """Scheduler should skip symbols that can't be resolved, not crash."""
        # Setup: Mock resolver - one symbol can't be resolved
        resolver = MagicMock()
        resolver.to_dr.side_effect = lambda s: {
            'NVDA': 'NVDA19',
            'UNKNOWN.XX': None,  # Can't resolve
        }.get(s)
        mock_get_resolver.return_value = resolver

        mock_service = MagicMock()
        mock_service.repo.get_all_tickers.return_value = [
            {'symbol': 'NVDA'},
            {'symbol': 'UNKNOWN.XX'},  # Invalid symbol
        ]
        mock_precompute_class.return_value = mock_service

        mock_job_service = MagicMock()
        mock_job_service.create_job.return_value = MagicMock(job_id='rpt_001', ticker='NVDA19')
        mock_get_job_service.return_value = mock_job_service
        mock_boto3.client.return_value = MagicMock()

        from src.scheduler.handler import lambda_handler
        event = {'action': 'parallel_precompute'}
        result = lambda_handler(event, None)

        # Assert: Only resolvable symbols processed
        assert result['statusCode'] == 200
        assert result['body']['jobs_submitted'] == 1  # Only NVDA succeeded
        assert result['body']['jobs_failed'] == 1     # UNKNOWN failed
        assert 'UNKNOWN.XX' in result['body']['failed_tickers']
