# -*- coding: utf-8 -*-
"""
Unit tests for ticker_fetcher_handler (Extract Layer).

Tests the new focused Lambda that ONLY fetches raw ticker data.
Part of scheduler redesign: splitting God Lambda into 4 focused Lambdas.

Sprint 1 Deliverable: Verify ticker-fetcher handler correctly:
- Fetches all tickers on empty event
- Fetches specific tickers when provided
- Handles configuration errors
- Returns proper response format
- Handles failures gracefully
"""
import json
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock


class TestTickerFetcherHandler:
    """Test ticker_fetcher_handler Lambda function."""

    def setup_method(self):
        """Set up test environment variables."""
        self.valid_env = {
            'PDF_BUCKET_NAME': 'test-pdf-bucket',
            'DATA_LAKE_BUCKET': 'test-data-lake-bucket',
            'ENVIRONMENT': 'test',
            'LOG_LEVEL': 'INFO',
            'AURORA_HOST': 'test-aurora.cluster.amazonaws.com',
            'AURORA_PORT': '3306',
            'AURORA_DATABASE': 'ticker_data',
            'AURORA_USER': 'admin',
            'AURORA_PASSWORD': 'test-password',
            'TZ': 'Asia/Bangkok'  # Required for timezone-aware date handling (Principle #16)
        }

        self.mock_fetch_results = {
            'success_count': 47,
            'failed_count': 0,
            'total': 47,
            'date': '2025-12-13',
            'success': [
                {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365},
                {'ticker': 'DBS19', 'yahoo_ticker': 'D05.SI', 'rows_written': 365}
            ],
            'failed': []
        }

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_fetch_all_tickers_on_empty_event(self, mock_fetcher_class):
        """GIVEN Lambda invoked with empty event
        WHEN handler processes event
        THEN it should fetch ALL tickers (default behavior)
        """
        # Setup mock
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.mock_fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            event = {}  # Empty event = fetch all
            context = MagicMock()

            result = lambda_handler(event, context)

            # Verify fetch_all_tickers was called (not fetch_tickers)
            mock_fetcher.fetch_all_tickers.assert_called_once()
            mock_fetcher.fetch_tickers.assert_not_called()

            # Verify response
            assert result['statusCode'] == 200
            assert result['body']['message'] == 'Ticker fetch completed'
            assert result['body']['success_count'] == 47
            assert result['body']['failed_count'] == 0

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_fetch_specific_tickers(self, mock_fetcher_class):
        """GIVEN Lambda invoked with specific tickers
        WHEN handler processes event
        THEN it should fetch ONLY those tickers
        """
        # Setup mock
        mock_fetcher = MagicMock()
        specific_results = {
            'success_count': 2,
            'failed_count': 0,
            'total': 2,
            'date': '2025-12-13',
            'success': [
                {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365},
                {'ticker': 'DBS19', 'yahoo_ticker': 'D05.SI', 'rows_written': 365}
            ],
            'failed': []
        }
        mock_fetcher.fetch_tickers.return_value = specific_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            event = {'tickers': ['NVDA', 'DBS19']}
            context = MagicMock()

            result = lambda_handler(event, context)

            # Verify fetch_tickers was called with correct tickers
            mock_fetcher.fetch_tickers.assert_called_once_with(['NVDA', 'DBS19'])
            mock_fetcher.fetch_all_tickers.assert_not_called()

            # Verify response
            assert result['statusCode'] == 200
            assert result['body']['success_count'] == 2

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_handler_initializes_fetcher_correctly(self, mock_fetcher_class):
        """GIVEN Lambda invocation
        WHEN TickerFetcher is instantiated
        THEN it should receive correct bucket names from env vars
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.mock_fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            lambda_handler({}, MagicMock())

            # Verify TickerFetcher was initialized with correct arguments
            mock_fetcher_class.assert_called_once_with(
                bucket_name='test-pdf-bucket',
                data_lake_bucket='test-data-lake-bucket'
            )

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_response_includes_duration(self, mock_fetcher_class):
        """GIVEN successful fetch
        WHEN handler completes
        THEN response should include duration_seconds
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.mock_fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Verify duration is present and reasonable
            assert 'duration_seconds' in result['body']
            duration = result['body']['duration_seconds']
            assert isinstance(duration, float)
            assert duration >= 0
            assert duration < 10  # Should be fast with mocked fetcher

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_response_includes_success_and_failed_lists(self, mock_fetcher_class):
        """GIVEN fetch results with some failures
        WHEN handler completes
        THEN response should include lists of successful and failed tickers
        """
        results_with_failures = {
            'success_count': 45,
            'failed_count': 2,
            'total': 47,
            'date': '2025-12-13',
            'success': [
                {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365}
            ],
            'failed': [
                {'ticker': 'INVALID', 'error': 'Ticker not found'}
            ]
        }
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = results_with_failures
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Verify response structure
            assert result['statusCode'] == 200
            assert 'success' in result['body']
            assert 'failed' in result['body']

            # Verify success list contains ticker names
            success_tickers = result['body']['success']
            assert 'NVDA' in success_tickers

            # Verify failed list is passed through
            assert result['body']['failed'] == [{'ticker': 'INVALID', 'error': 'Ticker not found'}]

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_handler_catches_fetcher_exceptions(self, mock_fetcher_class):
        """GIVEN TickerFetcher raises exception
        WHEN handler processes event
        THEN it should catch exception and return 500 error
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.side_effect = Exception("S3 connection failed")
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Verify error response
            assert result['statusCode'] == 500
            assert result['body']['message'] == 'Ticker fetch failed'
            assert 'S3 connection failed' in result['body']['error']

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_bucket_name_env_var(self):
        """GIVEN Lambda with missing PDF_BUCKET_NAME env var
        WHEN handler is invoked
        THEN it should raise RuntimeError (fail-fast validation)

        Note: Updated to expect validation failure per Defensive Programming principle.
        Handler now validates required env vars at startup.
        """
        incomplete_env = self.valid_env.copy()
        del incomplete_env['PDF_BUCKET_NAME']

        with patch.dict(os.environ, incomplete_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            with pytest.raises(RuntimeError) as exc_info:
                lambda_handler({}, MagicMock())

            # Verify error message mentions the missing var
            assert 'PDF_BUCKET_NAME' in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_handler_logs_event_and_results(self, mock_fetcher_class):
        """GIVEN Lambda invocation
        WHEN handler processes event
        THEN it should log event details and results
        """
        mock_results = {
            'success_count': 1,
            'failed_count': 0,
            'total': 1,
            'date': '2025-12-13',
            'success': [{'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365}],
            'failed': []
        }
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_tickers.return_value = mock_results  # Specific tickers path
        mock_fetcher.fetch_all_tickers.return_value = self.mock_fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            with patch('src.scheduler.ticker_fetcher_handler.logger') as mock_logger:
                from src.scheduler.ticker_fetcher_handler import lambda_handler

                event = {'tickers': ['NVDA']}
                lambda_handler(event, MagicMock())

                # Verify logging calls
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                log_messages = ' '.join(log_calls)

                # Should log invocation time
                assert 'Ticker Fetcher Lambda invoked' in log_messages

                # Should log event
                assert 'Event:' in log_messages

                # Should log completion with statistics
                completion_call = log_calls[-1]  # Last info log
                # Should show "1 success, 0 failed"
                assert '1 success' in completion_call and '0 failed' in completion_call

    def test_handler_can_be_tested_locally(self):
        """GIVEN handler __main__ block
        WHEN run locally
        THEN it should execute without errors
        """
        # This test verifies the __main__ block structure
        # In actual execution, we just verify the code path exists
        from src.scheduler.ticker_fetcher_handler import lambda_handler

        # The handler should be callable
        assert callable(lambda_handler)

        # The __name__ == '__main__' block should exist in the file
        with open('src/scheduler/ticker_fetcher_handler.py') as f:
            content = f.read()
            assert "if __name__ == '__main__':" in content
            assert "test_event = {'tickers': ['NVDA', 'D05.SI']}" in content


class TestTickerFetcherHandlerResponseFormat:
    """Test response format compliance with AWS Lambda standards."""

    def setup_method(self):
        """Set up environment."""
        self.valid_env = {
            'PDF_BUCKET_NAME': 'test-bucket',
            'DATA_LAKE_BUCKET': 'test-lake',
            'ENVIRONMENT': 'test',
            'LOG_LEVEL': 'INFO',
            'AURORA_HOST': 'test-aurora.cluster.amazonaws.com',
            'AURORA_PORT': '3306',
            'AURORA_DATABASE': 'ticker_data',
            'AURORA_USER': 'admin',
            'AURORA_PASSWORD': 'test-password',
            'TZ': 'Asia/Bangkok'  # Required for timezone-aware date handling (Principle #16)
        }

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_success_response_structure(self, mock_fetcher_class):
        """GIVEN successful fetch
        WHEN handler completes
        THEN response should have correct structure
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = {
            'success_count': 47,
            'failed_count': 0,
            'total': 47,
            'date': '2025-12-13',
            'success': [],
            'failed': []
        }
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Top-level keys
            assert 'statusCode' in result
            assert 'body' in result

            # Body keys
            body = result['body']
            assert 'message' in body
            assert 'success_count' in body
            assert 'failed_count' in body
            assert 'total' in body
            assert 'date' in body
            assert 'duration_seconds' in body
            assert 'success' in body
            assert 'failed' in body

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_error_response_structure(self, mock_fetcher_class):
        """GIVEN fetch failure
        WHEN handler catches exception
        THEN error response should have correct structure
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.side_effect = ValueError("Test error")
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Error response structure
            assert result['statusCode'] == 500
            assert 'body' in result
            assert 'message' in result['body']
            assert 'error' in result['body']
            assert result['body']['message'] == 'Ticker fetch failed'
            assert 'Test error' in result['body']['error']

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_response_body_is_dict_not_json_string(self, mock_fetcher_class):
        """GIVEN Lambda response
        WHEN handler returns
        THEN body should be dict, not JSON string (Lambda serializes it)
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = {
            'success_count': 47,
            'failed_count': 0,
            'total': 47,
            'date': '2025-12-13',
            'success': [],
            'failed': []
        }
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Body should be dict, not string
            assert isinstance(result['body'], dict)
            assert not isinstance(result['body'], str)


class TestPrecomputeTrigger:
    """Test _trigger_precompute() async Lambda invocation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_env = {
            'PDF_BUCKET_NAME': 'test-pdf-bucket',
            'DATA_LAKE_BUCKET': 'test-data-lake-bucket',
            'ENVIRONMENT': 'test',
            'LOG_LEVEL': 'INFO',
            'AURORA_HOST': 'test-aurora.cluster.amazonaws.com',
            'AURORA_PORT': '3306',
            'AURORA_DATABASE': 'ticker_data',
            'AURORA_USER': 'admin',
            'AURORA_PASSWORD': 'test-password',
            'TZ': 'Asia/Bangkok',  # Required for timezone-aware date handling (Principle #16)
            'PRECOMPUTE_CONTROLLER_ARN': 'arn:aws:lambda:region:account:function:precompute-controller'
        }

        self.fetch_results = {
            'success_count': 47,
            'failed_count': 0,
            'total': 47,
            'date': '2025-12-13',
            'success': [
                {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365},
                {'ticker': 'DBS19', 'yahoo_ticker': 'D05.SI', 'rows_written': 365}
            ],
            'failed': []
        }

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_triggers_precompute_on_successful_fetch(self, mock_fetcher_class, mock_boto_client):
        """GIVEN successful ticker fetch
        WHEN handler completes
        THEN it should trigger precompute Lambda asynchronously
        """
        # Setup fetch mock
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        # Setup Lambda client mock
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}  # Async accepted
        mock_boto_client.return_value = mock_lambda

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Verify Lambda invocation
            mock_boto_client.assert_called_once_with('lambda')
            mock_lambda.invoke.assert_called_once()

            # Verify invocation parameters
            invoke_args = mock_lambda.invoke.call_args
            assert invoke_args.kwargs['FunctionName'] == self.valid_env['PRECOMPUTE_CONTROLLER_ARN']
            assert invoke_args.kwargs['InvocationType'] == 'Event'  # Async fire-and-forget

            # Verify payload structure
            payload = json.loads(invoke_args.kwargs['Payload'])
            assert payload['triggered_by'] == 'scheduler'
            assert 'fetch_summary' in payload
            assert payload['fetch_summary']['success_count'] == 47
            assert payload['fetch_summary']['total'] == 47
            assert 'NVDA' in payload['fetch_summary']['success_tickers']
            assert 'DBS19' in payload['fetch_summary']['success_tickers']

            # Verify response indicates precompute was triggered
            assert result['body']['precompute_triggered'] is True

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_skips_precompute_when_no_successful_fetches(self, mock_fetcher_class, mock_boto_client):
        """GIVEN fetch with zero successes
        WHEN handler completes
        THEN it should NOT trigger precompute
        """
        # All fetches failed
        failed_results = {
            'success_count': 0,
            'failed_count': 47,
            'total': 47,
            'date': '2025-12-13',
            'success': [],
            'failed': [{'ticker': 'NVDA', 'error': 'Connection timeout'}]
        }

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = failed_results
        mock_fetcher_class.return_value = mock_fetcher

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Verify Lambda was NOT invoked
            mock_boto_client.assert_not_called()

            # Verify response indicates precompute was NOT triggered
            assert result['body']['precompute_triggered'] is False

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_skips_precompute_when_arn_not_configured(self, mock_fetcher_class, mock_boto_client):
        """GIVEN missing PRECOMPUTE_CONTROLLER_ARN env var
        WHEN handler completes
        THEN it should skip precompute trigger gracefully
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        # Environment without PRECOMPUTE_CONTROLLER_ARN (but with all required vars)
        env_without_arn = self.valid_env.copy()
        del env_without_arn['PRECOMPUTE_CONTROLLER_ARN']

        with patch.dict(os.environ, env_without_arn):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Should complete successfully without triggering
            assert result['statusCode'] == 200
            assert result['body']['precompute_triggered'] is False

            # Lambda client should not be created
            mock_boto_client.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_handles_lambda_invoke_failure_gracefully(self, mock_fetcher_class, mock_boto_client):
        """GIVEN Lambda invoke fails
        WHEN _trigger_precompute() is called
        THEN scheduler should still succeed (defensive error handling)
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        # Lambda invoke raises exception
        mock_lambda = MagicMock()
        mock_lambda.invoke.side_effect = Exception("Lambda service error")
        mock_boto_client.return_value = mock_lambda

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Scheduler should succeed despite precompute trigger failure
            assert result['statusCode'] == 200
            assert result['body']['success_count'] == 47

            # Precompute trigger failed
            assert result['body']['precompute_triggered'] is False

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_handles_unexpected_status_code(self, mock_fetcher_class, mock_boto_client):
        """GIVEN Lambda invoke returns unexpected status code
        WHEN _trigger_precompute() is called
        THEN it should handle gracefully
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        # Unexpected status code (not 202)
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 500}
        mock_boto_client.return_value = mock_lambda

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            result = lambda_handler({}, MagicMock())

            # Scheduler succeeds but precompute trigger failed
            assert result['statusCode'] == 200
            assert result['body']['precompute_triggered'] is False

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_precompute_payload_includes_timestamp(self, mock_fetcher_class, mock_boto_client):
        """GIVEN precompute trigger
        WHEN payload is constructed
        THEN it should include scheduler start timestamp
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = self.fetch_results
        mock_fetcher_class.return_value = mock_fetcher

        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            lambda_handler({}, MagicMock())

            # Extract payload
            payload = json.loads(mock_lambda.invoke.call_args.kwargs['Payload'])

            # Verify timestamp is present and valid ISO format
            assert 'timestamp' in payload
            from datetime import datetime
            # Should not raise exception
            timestamp = datetime.fromisoformat(payload['timestamp'])
            assert isinstance(timestamp, datetime)

    @patch.dict(os.environ, {}, clear=True)
    @patch('src.scheduler.ticker_fetcher_handler.boto3.client')
    @patch('src.scheduler.ticker_fetcher.TickerFetcher')
    def test_precompute_payload_includes_failed_tickers(self, mock_fetcher_class, mock_boto_client):
        """GIVEN fetch with some failures
        WHEN precompute is triggered
        THEN payload should include both success and failed ticker lists
        """
        # Results with failures
        mixed_results = {
            'success_count': 45,
            'failed_count': 2,
            'total': 47,
            'date': '2025-12-13',
            'success': [
                {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365}
            ],
            'failed': [
                {'ticker': 'INVALID1', 'error': 'Not found'},
                {'ticker': 'INVALID2', 'error': 'Timeout'}
            ]
        }

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all_tickers.return_value = mixed_results
        mock_fetcher_class.return_value = mock_fetcher

        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        with patch.dict(os.environ, self.valid_env):
            from src.scheduler.ticker_fetcher_handler import lambda_handler

            lambda_handler({}, MagicMock())

            # Extract payload
            payload = json.loads(mock_lambda.invoke.call_args.kwargs['Payload'])

            # Verify failed tickers are included
            assert payload['fetch_summary']['success_count'] == 45
            assert payload['fetch_summary']['failed_count'] == 2
            assert payload['fetch_summary']['failed_tickers'] == mixed_results['failed']
            assert 'NVDA' in payload['fetch_summary']['success_tickers']
