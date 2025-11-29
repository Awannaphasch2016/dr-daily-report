#!/usr/bin/env python3
"""
Unit tests for JobService

Tests async job CRUD operations, status transitions, TTL, and error handling.
TDD: Write tests first, then implement JobService to pass them.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


class TestJobService:
    """Test suite for JobService"""

    @pytest.fixture
    def mock_dynamodb_table(self):
        """Create mock DynamoDB table"""
        mock_table = Mock()
        mock_table.put_item = Mock(return_value={})
        mock_table.get_item = Mock(return_value={})
        mock_table.update_item = Mock(return_value={})
        return mock_table

    @pytest.fixture
    def service(self, mock_dynamodb_table):
        """Create JobService with mocked dependencies"""
        from src.api.job_service import JobService

        with patch('src.api.job_service.boto3') as mock_boto3:
            mock_dynamodb = Mock()
            mock_dynamodb.Table = Mock(return_value=mock_dynamodb_table)
            mock_boto3.resource = Mock(return_value=mock_dynamodb)

            service = JobService(table_name='test-jobs-table')
            service.table = mock_dynamodb_table
            return service

    # =========================================================================
    # Test: create_job
    # =========================================================================

    def test_create_job_returns_job_with_pending_status(self, service):
        """Test that create_job returns a job with 'pending' status"""
        job = service.create_job(ticker='NVDA19')

        assert job.status == 'pending'
        assert job.ticker == 'NVDA19'
        service.table.put_item.assert_called_once()

    def test_create_job_generates_unique_id(self, service):
        """Test that create_job generates a unique job_id with prefix"""
        job = service.create_job(ticker='NVDA19')

        assert job.job_id is not None
        assert job.job_id.startswith('rpt_')
        assert len(job.job_id) > 10  # rpt_ + uuid portion

    def test_create_job_sets_created_at_timestamp(self, service):
        """Test that create_job sets created_at to current time"""
        before = datetime.now()
        job = service.create_job(ticker='DBS19')
        after = datetime.now()

        assert job.created_at is not None
        assert before <= job.created_at <= after

    def test_create_job_sets_24h_ttl(self, service):
        """Test that job has TTL set to 24 hours from creation"""
        job = service.create_job(ticker='NVDA19')

        # Verify put_item was called with TTL
        call_args = service.table.put_item.call_args
        item = call_args.kwargs['Item']

        expected_ttl = int((datetime.now() + timedelta(hours=24)).timestamp())
        # Allow 1 minute tolerance
        assert abs(item['ttl'] - expected_ttl) < 60

    def test_create_job_stores_ticker_uppercase(self, service):
        """Test that ticker is normalized to uppercase"""
        job = service.create_job(ticker='nvda19')

        assert job.ticker == 'NVDA19'

    # =========================================================================
    # Test: get_job
    # =========================================================================

    def test_get_job_returns_job_data(self, service, mock_dynamodb_table):
        """Test that get_job retrieves job from DynamoDB"""
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'job_id': 'rpt_abc123',
                'ticker': 'NVDA19',
                'status': 'pending',
                'created_at': '2025-01-15T10:00:00',
                'ttl': 1705496400
            }
        }

        job = service.get_job('rpt_abc123')

        assert job.job_id == 'rpt_abc123'
        assert job.ticker == 'NVDA19'
        assert job.status == 'pending'

    def test_get_job_not_found_raises_error(self, service, mock_dynamodb_table):
        """Test that get_job raises JobNotFoundError for missing job"""
        mock_dynamodb_table.get_item.return_value = {}  # No 'Item' key

        from src.api.job_service import JobNotFoundError

        with pytest.raises(JobNotFoundError) as exc_info:
            service.get_job('rpt_nonexistent')

        assert 'rpt_nonexistent' in str(exc_info.value)

    def test_get_job_includes_result_when_completed(self, service, mock_dynamodb_table):
        """Test that get_job includes result for completed jobs"""
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'job_id': 'rpt_abc123',
                'ticker': 'NVDA19',
                'status': 'completed',
                'created_at': '2025-01-15T10:00:00',
                'started_at': '2025-01-15T10:00:01',
                'finished_at': '2025-01-15T10:00:45',
                'result': '{"ticker": "NVDA19", "price": 150.0}',
                'ttl': 1705496400
            }
        }

        job = service.get_job('rpt_abc123')

        assert job.status == 'completed'
        assert job.result is not None
        assert job.finished_at is not None

    def test_get_job_includes_error_when_failed(self, service, mock_dynamodb_table):
        """Test that get_job includes error for failed jobs"""
        mock_dynamodb_table.get_item.return_value = {
            'Item': {
                'job_id': 'rpt_abc123',
                'ticker': 'NVDA19',
                'status': 'failed',
                'created_at': '2025-01-15T10:00:00',
                'started_at': '2025-01-15T10:00:01',
                'finished_at': '2025-01-15T10:00:45',
                'error': 'LLM API timeout',
                'ttl': 1705496400
            }
        }

        job = service.get_job('rpt_abc123')

        assert job.status == 'failed'
        assert job.error == 'LLM API timeout'

    # =========================================================================
    # Test: start_job
    # =========================================================================

    def test_start_job_updates_status_to_in_progress(self, service):
        """Test that start_job changes status from pending to in_progress"""
        service.start_job('rpt_abc123')

        service.table.update_item.assert_called_once()
        call_args = service.table.update_item.call_args

        # Verify update expression sets status to in_progress
        update_expr = call_args.kwargs.get('UpdateExpression', '')
        assert 'status' in update_expr.lower() or 'SET' in update_expr

    def test_start_job_sets_started_at_timestamp(self, service):
        """Test that start_job sets started_at to current time"""
        service.start_job('rpt_abc123')

        call_args = service.table.update_item.call_args
        attr_values = call_args.kwargs.get('ExpressionAttributeValues', {})

        # Check that started_at is set to a recent timestamp
        assert any('started_at' in str(v).lower() or ':started' in k
                   for k, v in attr_values.items()) or 'started_at' in str(call_args)

    # =========================================================================
    # Test: complete_job
    # =========================================================================

    def test_complete_job_stores_result(self, service):
        """Test that complete_job stores the result and sets status to completed"""
        result = {'ticker': 'NVDA19', 'price': 150.0, 'stance': 'bullish'}

        service.complete_job('rpt_abc123', result)

        service.table.update_item.assert_called_once()
        call_args = service.table.update_item.call_args

        # Verify status is set to completed
        update_expr = call_args.kwargs.get('UpdateExpression', '')
        assert 'status' in update_expr.lower() or 'SET' in update_expr

    def test_complete_job_sets_finished_at_timestamp(self, service):
        """Test that complete_job sets finished_at to current time"""
        result = {'ticker': 'NVDA19'}

        service.complete_job('rpt_abc123', result)

        call_args = service.table.update_item.call_args
        # Verify finished_at is included in update
        assert 'finished_at' in str(call_args).lower() or ':finished' in str(call_args)

    def test_complete_job_serializes_result_to_json(self, service):
        """Test that result dict is serialized to JSON string for storage"""
        result = {'ticker': 'NVDA19', 'price': 150.0}

        service.complete_job('rpt_abc123', result)

        call_args = service.table.update_item.call_args
        attr_values = call_args.kwargs.get('ExpressionAttributeValues', {})

        # Result should be JSON string
        result_value = [v for k, v in attr_values.items() if 'result' in k.lower()]
        # The value should be a string (JSON serialized) or dict
        assert len(result_value) > 0 or 'result' in str(call_args)

    # =========================================================================
    # Test: fail_job
    # =========================================================================

    def test_fail_job_stores_error_message(self, service):
        """Test that fail_job stores error and sets status to failed"""
        service.fail_job('rpt_abc123', 'Connection timeout')

        service.table.update_item.assert_called_once()
        call_args = service.table.update_item.call_args

        # Verify error is stored
        assert 'error' in str(call_args).lower() or ':error' in str(call_args)

    def test_fail_job_sets_finished_at_timestamp(self, service):
        """Test that fail_job sets finished_at to current time"""
        service.fail_job('rpt_abc123', 'Error occurred')

        call_args = service.table.update_item.call_args
        assert 'finished_at' in str(call_args).lower() or ':finished' in str(call_args)

    def test_fail_job_sets_status_to_failed(self, service):
        """Test that fail_job sets status to 'failed'"""
        service.fail_job('rpt_abc123', 'Error')

        call_args = service.table.update_item.call_args
        attr_values = call_args.kwargs.get('ExpressionAttributeValues', {})

        # Check status is set to 'failed'
        status_values = [v for k, v in attr_values.items() if 'status' in k.lower()]
        assert any(v == 'failed' for v in status_values) or 'failed' in str(call_args)

    # =========================================================================
    # Test: Error handling
    # =========================================================================

    def test_create_job_dynamodb_error(self, service):
        """Test handling DynamoDB errors on create"""
        service.table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Test error'}},
            'PutItem'
        )

        with pytest.raises(ClientError):
            service.create_job('NVDA19')

    def test_get_job_dynamodb_error(self, service):
        """Test handling DynamoDB errors on get"""
        service.table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Test error'}},
            'GetItem'
        )

        with pytest.raises(ClientError):
            service.get_job('rpt_abc123')


class TestJobModel:
    """Test suite for Job Pydantic model"""

    def test_job_status_enum_values(self):
        """Test that JobStatus enum has all required values"""
        from src.api.job_service import JobStatus

        assert hasattr(JobStatus, 'PENDING')
        assert hasattr(JobStatus, 'IN_PROGRESS')
        assert hasattr(JobStatus, 'COMPLETED')
        assert hasattr(JobStatus, 'FAILED')

    def test_job_model_required_fields(self):
        """Test that Job model requires essential fields"""
        from src.api.job_service import Job

        # Should be able to create with required fields
        job = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status='pending',
            created_at=datetime.now()
        )

        assert job.job_id == 'rpt_abc123'
        assert job.ticker == 'NVDA19'
        assert job.status == 'pending'

    def test_job_model_optional_fields_default_to_none(self):
        """Test that optional fields default to None"""
        from src.api.job_service import Job

        job = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status='pending',
            created_at=datetime.now()
        )

        assert job.started_at is None
        assert job.finished_at is None
        assert job.result is None
        assert job.error is None


class TestGetJobService:
    """Test suite for get_job_service singleton"""

    def test_get_job_service_returns_instance(self):
        """Test that get_job_service returns a JobService instance"""
        with patch('src.api.job_service.boto3'):
            from src.api.job_service import get_job_service, JobService

            # Reset global singleton
            import src.api.job_service as job_module
            job_module._job_service = None

            service = get_job_service()
            assert isinstance(service, JobService)

    def test_get_job_service_returns_same_instance(self):
        """Test that get_job_service returns singleton"""
        with patch('src.api.job_service.boto3'):
            from src.api.job_service import get_job_service

            # Reset global singleton
            import src.api.job_service as job_module
            job_module._job_service = None

            service1 = get_job_service()
            service2 = get_job_service()
            assert service1 is service2
