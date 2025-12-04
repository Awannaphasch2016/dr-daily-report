# -*- coding: utf-8 -*-
"""TDD tests for parallel precompute scheduler.

These tests verify the fan-out pattern for parallel report generation:
1. Scheduler gets list of all tickers
2. Scheduler sends one SQS message per ticker
3. Report Worker processes in parallel (auto-scales)

RED: Write tests first, expect failures
GREEN: Implement until tests pass
"""
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime


class TestParallelPrecomputeHandler:
    """Test the parallel precompute action in scheduler handler."""

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_sends_sqs_messages_for_each_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """Scheduler should send one SQS message per ticker for parallel processing.

        This is the core behavior: fan-out to SQS for parallel Lambda execution.
        """
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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_creates_job_for_each_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """Scheduler should create a DynamoDB job for each ticker."""
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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_returns_job_count(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """Response should include count of jobs submitted."""
        # Setup
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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_uses_correct_queue_url(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """SQS messages should be sent to the correct queue URL from env."""
        import os

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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_handles_sqs_failure_gracefully(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """If SQS fails for one ticker, continue with others and report failures."""
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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_parallel_precompute_respects_limit_parameter(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """Limit parameter should restrict number of tickers processed."""
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

    @patch('src.scheduler.handler.boto3')
    @patch('src.api.job_service.get_job_service')
    @patch('src.data.aurora.precompute_service.PrecomputeService')
    def test_sqs_message_contains_job_id_and_ticker(
        self, mock_precompute_class, mock_get_job_service, mock_boto3
    ):
        """SQS message body should contain job_id and ticker (Report Worker format)."""
        import json

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
