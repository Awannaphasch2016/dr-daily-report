"""
Unit tests for Fund Data Sync Lambda handler.

Tests the Lambda handler that processes SQS messages containing S3 events.

TDD Principles Applied:
1. Test outcomes (message processed successfully) not execution (function called)
2. Explicit failure mocking (S3 download fails, parsing fails, upsert fails)
3. Schema contract testing (Lambda response format)
4. Silent failure detection (verify failures are logged and returned)
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


class TestFundDataSyncHandler:
    """Test Lambda handler for SQS-triggered Fund Data Sync."""

    def setup_method(self):
        """Set up test fixtures."""
        # Sample SQS event (Lambda receives batches)
        self.sqs_event = {
            'Records': [
                {
                    'messageId': '059f36b4-87a3-44ab-83d2-661975830a7d',
                    'receiptHandle': 'AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...',
                    'body': json.dumps({
                        'Records': [
                            {
                                's3': {
                                    'bucket': {'name': 'dr-daily-report-data-lake-dev'},
                                    'object': {'key': 'raw/sql_server/fund_data/2025-12-09/export.csv'}
                                }
                            }
                        ]
                    }),
                    'attributes': {
                        'ApproximateReceiveCount': '1',
                        'SentTimestamp': '1523232000000'
                    }
                }
            ]
        }

        self.context = Mock()
        self.context.function_name = 'fund-data-sync-dev'
        self.context.request_id = 'test-request-123'

    # =========================================================================
    # Success Path Tests
    # =========================================================================

    def test_handler_processes_sqs_message_successfully(self):
        """Test handler processes SQS message and returns success response.

        Principle: Test outcomes (success response) not execution (function called).
        """
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': True,
                'records_processed': 150,
                'rows_affected': 150,
                's3_source': 's3://dr-daily-report-data-lake-dev/raw/sql_server/fund_data/2025-12-09/export.csv',
                'message': 'Successfully synced 150 records'
            }
            mock_get_service.return_value = mock_service

            # Execute handler
            response = lambda_handler(self.sqs_event, self.context)

            # Verify outcome: Lambda response format
            assert response['statusCode'] == 200
            assert 'body' in response
            body = json.loads(response['body'])
            assert body['batchItemFailures'] == [], "Should have no batch failures on success"
            assert body['successCount'] == 1
            assert body['failureCount'] == 0

    def test_handler_processes_multiple_sqs_messages(self):
        """Test handler processes batch of SQS messages."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        # Create batch of 3 messages
        multi_message_event = {
            'Records': [
                {
                    'messageId': f'message-{i}',
                    'receiptHandle': f'receipt-{i}',
                    'body': json.dumps({
                        'Records': [{
                            's3': {
                                'bucket': {'name': 'test-bucket'},
                                'object': {'key': f'file-{i}.csv'}
                            }
                        }]
                    })
                }
                for i in range(3)
            ]
        }

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': True,
                'records_processed': 100,
                'rows_affected': 100
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(multi_message_event, self.context)

            # Verify all messages processed
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['successCount'] == 3
            assert body['failureCount'] == 0
            assert len(body['batchItemFailures']) == 0

    def test_handler_logs_processing_details(self):
        """Test handler logs detailed processing information."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service, \
             patch('src.lambda_handlers.fund_data_sync_handler.logger') as mock_logger:

            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': True,
                'records_processed': 150,
                's3_source': 's3://bucket/file.csv'
            }
            mock_get_service.return_value = mock_service

            lambda_handler(self.sqs_event, self.context)

            # Verify logging
            assert mock_logger.info.call_count >= 2, "Should log start and success"
            mock_logger.info.assert_any_call('Starting Fund Data Sync Lambda handler')
            # Should log per-message success
            success_calls = [call for call in mock_logger.info.call_args_list
                           if 'Successfully processed' in str(call)]
            assert len(success_calls) >= 1

    # =========================================================================
    # Failure Path Tests (Explicit Failure Detection)
    # =========================================================================

    def test_handler_returns_batch_failures_on_processing_error(self):
        """Test handler returns batchItemFailures for failed messages.

        Principle: Explicit failure detection - failed messages must be reported.
        """
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            # Simulate processing failure
            mock_service.process_sqs_message.return_value = {
                'success': False,
                'error': 'S3 object not found',
                'records_processed': 0
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(self.sqs_event, self.context)

            # Verify failure reported
            assert response['statusCode'] == 200  # Lambda succeeded
            body = json.loads(response['body'])
            assert body['failureCount'] == 1
            assert body['successCount'] == 0
            # batchItemFailures tells SQS which messages to retry
            assert len(body['batchItemFailures']) == 1
            assert body['batchItemFailures'][0]['itemIdentifier'] == '059f36b4-87a3-44ab-83d2-661975830a7d'

    def test_handler_continues_processing_after_single_failure(self):
        """Test handler processes remaining messages after one fails."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        multi_message_event = {
            'Records': [
                {
                    'messageId': 'msg-1',
                    'receiptHandle': 'receipt-1',
                    'body': json.dumps({
                        'Records': [{
                            's3': {
                                'bucket': {'name': 'bucket'},
                                'object': {'key': 'file-1.csv'}
                            }
                        }]
                    })
                },
                {
                    'messageId': 'msg-2',
                    'receiptHandle': 'receipt-2',
                    'body': json.dumps({
                        'Records': [{
                            's3': {
                                'bucket': {'name': 'bucket'},
                                'object': {'key': 'file-2.csv'}
                            }
                        }]
                    })
                }
            ]
        }

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            # First message fails, second succeeds
            mock_service.process_sqs_message.side_effect = [
                {'success': False, 'error': 'Parse error', 'records_processed': 0},
                {'success': True, 'records_processed': 100, 'rows_affected': 100}
            ]
            mock_get_service.return_value = mock_service

            response = lambda_handler(multi_message_event, self.context)

            # Verify partial success
            body = json.loads(response['body'])
            assert body['successCount'] == 1
            assert body['failureCount'] == 1
            assert len(body['batchItemFailures']) == 1
            assert body['batchItemFailures'][0]['itemIdentifier'] == 'msg-1'

    def test_handler_logs_errors_for_failed_messages(self):
        """Test handler logs errors with full context."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service, \
             patch('src.lambda_handlers.fund_data_sync_handler.logger') as mock_logger:

            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': False,
                'error': 'Aurora connection timeout',
                'records_processed': 0,
                's3_source': 's3://bucket/file.csv'
            }
            mock_get_service.return_value = mock_service

            lambda_handler(self.sqs_event, self.context)

            # Verify error logging
            error_calls = [call for call in mock_logger.error.call_args_list
                          if 'Failed to process message' in str(call)]
            assert len(error_calls) >= 1, "Should log error with message ID"

    def test_handler_handles_exception_during_processing(self):
        """Test handler catches and reports exceptions during processing."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            # Simulate unexpected exception
            mock_service.process_sqs_message.side_effect = RuntimeError('Unexpected database error')
            mock_get_service.return_value = mock_service

            response = lambda_handler(self.sqs_event, self.context)

            # Verify exception handled gracefully
            body = json.loads(response['body'])
            assert body['failureCount'] == 1
            assert len(body['batchItemFailures']) == 1

    # =========================================================================
    # Schema Contract Tests
    # =========================================================================

    def test_handler_response_schema_contract(self):
        """Test handler returns expected response schema for Lambda.

        Principle: Schema contract testing - response structure must match Lambda expectations.
        """
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': True,
                'records_processed': 150
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(self.sqs_event, self.context)

            # Verify Lambda response schema
            assert isinstance(response, dict), "Response must be dict"
            assert 'statusCode' in response, "Must have statusCode"
            assert 'body' in response, "Must have body"
            assert isinstance(response['statusCode'], int), "statusCode must be int"

            # Verify body schema
            body = json.loads(response['body'])
            assert 'batchItemFailures' in body, "Must have batchItemFailures for SQS"
            assert 'successCount' in body
            assert 'failureCount' in body
            assert isinstance(body['batchItemFailures'], list)

    def test_batch_item_failures_schema(self):
        """Test batchItemFailures follows AWS SQS schema."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': False,
                'error': 'Test error'
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(self.sqs_event, self.context)

            body = json.loads(response['body'])
            failures = body['batchItemFailures']

            # Verify AWS SQS batchItemFailures schema
            assert len(failures) == 1
            assert 'itemIdentifier' in failures[0], "Must have itemIdentifier (messageId)"
            assert failures[0]['itemIdentifier'] == '059f36b4-87a3-44ab-83d2-661975830a7d'

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_handler_handles_empty_sqs_batch(self):
        """Test handler handles empty Records list."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        empty_event = {'Records': []}

        response = lambda_handler(empty_event, self.context)

        # Should succeed with no processing
        body = json.loads(response['body'])
        assert body['successCount'] == 0
        assert body['failureCount'] == 0
        assert len(body['batchItemFailures']) == 0

    def test_handler_handles_malformed_sqs_message_body(self):
        """Test handler handles invalid JSON in SQS message body."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        malformed_event = {
            'Records': [
                {
                    'messageId': 'malformed-msg',
                    'receiptHandle': 'receipt',
                    'body': 'INVALID JSON {{{',  # Invalid JSON
                }
            ]
        }

        response = lambda_handler(malformed_event, self.context)

        # Should report as failure
        body = json.loads(response['body'])
        assert body['failureCount'] == 1
        assert len(body['batchItemFailures']) == 1

    def test_handler_handles_missing_s3_info_in_message(self):
        """Test handler handles message without S3 event structure."""
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        missing_s3_event = {
            'Records': [
                {
                    'messageId': 'no-s3-msg',
                    'receiptHandle': 'receipt',
                    'body': json.dumps({
                        'Records': [{'eventName': 'TestEvent'}]  # No s3 key
                    })
                }
            ]
        }

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            mock_service.process_sqs_message.return_value = {
                'success': False,
                'error': 'Missing bucket or key in S3 event'
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(missing_s3_event, self.context)

            # Should report as failure
            body = json.loads(response['body'])
            assert body['failureCount'] == 1

    # =========================================================================
    # Sabotage Tests
    # =========================================================================

    def test_sabotage_handler_always_returns_empty_failures(self):
        """SABOTAGE TEST: Verify test detects when handler doesn't report failures.

        To verify this test works:
        1. Temporarily change handler to: return {'batchItemFailures': []}
        2. Run test - should FAIL
        3. Revert change - test should PASS
        """
        from src.lambda_handlers.fund_data_sync_handler import lambda_handler

        with patch('src.lambda_handlers.fund_data_sync_handler.get_fund_data_sync_service') as mock_get_service:
            mock_service = Mock()
            # Simulate failure
            mock_service.process_sqs_message.return_value = {
                'success': False,
                'error': 'Processing failed',
                'records_processed': 0
            }
            mock_get_service.return_value = mock_service

            response = lambda_handler(self.sqs_event, self.context)

            # This MUST report failure
            body = json.loads(response['body'])
            assert body['failureCount'] > 0, "SABOTAGE: Handler must report failures"
            assert len(body['batchItemFailures']) > 0, "SABOTAGE: Must return batchItemFailures for SQS"
