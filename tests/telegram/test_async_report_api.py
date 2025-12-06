#!/usr/bin/env python3
"""
Tests for async report API endpoints

TDD: Tests for POST /report/{ticker} and GET /report/status/{job_id}
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from src.api.app import app
from src.api.job_service import Job, JobStatus, JobNotFoundError


class TestSubmitReportEndpoint:
    """Tests for POST /api/v1/report/{ticker} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_services(self):
        """Mock job and ticker services"""
        with patch('src.api.app.get_job_service') as mock_job, \
             patch('src.api.app.get_ticker_service') as mock_ticker, \
             patch('src.api.app.send_to_sqs') as mock_sqs:

            job_service = Mock()
            job_service.create_job = Mock(return_value=Job(
                job_id='rpt_abc123',
                ticker='NVDA19',
                status=JobStatus.PENDING.value,
                created_at=datetime.now()
            ))
            mock_job.return_value = job_service

            ticker_service = Mock()
            ticker_service.is_supported = Mock(return_value=True)
            mock_ticker.return_value = ticker_service

            mock_sqs.return_value = None  # Fire and forget

            yield {
                'job': job_service,
                'ticker': ticker_service,
                'sqs': mock_sqs
            }

    def test_post_report_returns_job_id(self, client, mock_services):
        """Test that POST /report/{ticker} returns job_id"""
        response = client.post("/api/v1/report/NVDA19")

        assert response.status_code == 200
        data = response.json()
        assert 'job_id' in data
        assert data['job_id'] == 'rpt_abc123'
        assert data['status'] == 'pending'

    def test_post_report_creates_job(self, client, mock_services):
        """Test that POST creates a job in DynamoDB"""
        client.post("/api/v1/report/NVDA19")

        mock_services['job'].create_job.assert_called_once_with(ticker='NVDA19')

    def test_post_report_sends_to_sqs(self, client, mock_services):
        """Test that POST sends message to SQS queue"""
        client.post("/api/v1/report/NVDA19")

        mock_services['sqs'].assert_called_once()
        call_args = mock_services['sqs'].call_args
        # Should include job_id and ticker
        assert 'rpt_abc123' in str(call_args) or call_args[0][0] == 'rpt_abc123'

    def test_post_report_invalid_ticker_returns_400(self, client, mock_services):
        """Test that invalid ticker returns 400 error"""
        mock_services['ticker'].is_supported.return_value = False

        response = client.post("/api/v1/report/INVALID123")

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert data['error']['code'] == 'TICKER_NOT_SUPPORTED'

    def test_post_report_normalizes_ticker_uppercase(self, client, mock_services):
        """Test that ticker is normalized to uppercase"""
        client.post("/api/v1/report/nvda19")

        # Ticker service should be called with uppercase
        mock_services['ticker'].is_supported.assert_called()
        call_args = mock_services['ticker'].is_supported.call_args
        assert call_args[0][0] == 'NVDA19' or 'NVDA19' in str(call_args)


class TestJobStatusEndpoint:
    """Tests for GET /api/v1/report/status/{job_id} endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_job_service(self):
        """Mock job service"""
        with patch('src.api.app.get_job_service') as mock:
            service = Mock()
            mock.return_value = service
            yield service

    def test_get_status_pending_job(self, client, mock_job_service):
        """Test getting status of pending job"""
        mock_job_service.get_job.return_value = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status=JobStatus.PENDING.value,
            created_at=datetime.now()
        )

        response = client.get("/api/v1/report/status/rpt_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data['job_id'] == 'rpt_abc123'
        assert data['status'] == 'pending'
        assert data['ticker'] == 'NVDA19'
        assert data.get('result') is None

    def test_get_status_in_progress_job(self, client, mock_job_service):
        """Test getting status of in_progress job"""
        mock_job_service.get_job.return_value = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status=JobStatus.IN_PROGRESS.value,
            created_at=datetime.now(),
            started_at=datetime.now()
        )

        response = client.get("/api/v1/report/status/rpt_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'in_progress'
        assert data['started_at'] is not None

    def test_get_status_completed_job_includes_result(self, client, mock_job_service):
        """Test that completed job includes full result"""
        mock_job_service.get_job.return_value = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status=JobStatus.COMPLETED.value,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=datetime.now(),
            result={'ticker': 'NVDA19', 'price': 150.0, 'stance': 'bullish'}
        )

        response = client.get("/api/v1/report/status/rpt_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'completed'
        assert data['result'] is not None
        assert data['result']['ticker'] == 'NVDA19'
        assert data['finished_at'] is not None

    def test_get_status_failed_job_includes_error(self, client, mock_job_service):
        """Test that failed job includes error message"""
        mock_job_service.get_job.return_value = Job(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status=JobStatus.FAILED.value,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=datetime.now(),
            error='LLM API timeout'
        )

        response = client.get("/api/v1/report/status/rpt_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'failed'
        assert data['error'] == 'LLM API timeout'

    def test_get_status_not_found_returns_404(self, client, mock_job_service):
        """Test that non-existent job returns 404"""
        mock_job_service.get_job.side_effect = JobNotFoundError('rpt_nonexistent')

        response = client.get("/api/v1/report/status/rpt_nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert data['error']['code'] == 'JOB_NOT_FOUND'


class TestCacheFirstBehavior:
    """Tests for cache-first behavior in POST /api/v1/report/{ticker}

    TDD: These tests verify that the API checks Aurora cache before creating async jobs.
    Cache HIT → return immediately with cached_* job_id and status='completed'
    Cache MISS → create async job as before
    """

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_services_with_cache(self):
        """Mock all services including PrecomputeService for cache testing"""
        with patch('src.api.app.get_job_service') as mock_job, \
             patch('src.api.app.get_ticker_service') as mock_ticker, \
             patch('src.api.app.send_to_sqs') as mock_sqs:

            job_service = Mock()
            job_service.create_job = Mock(return_value=Job(
                job_id='rpt_abc123',
                ticker='DBS19',
                status=JobStatus.PENDING.value,
                created_at=datetime.now()
            ))
            mock_job.return_value = job_service

            ticker_service = Mock()
            ticker_service.is_supported = Mock(return_value=True)
            ticker_service.get_ticker_info = Mock(return_value={
                'ticker': 'DBS19',
                'yahoo_ticker': 'D05.SI',
                'name': 'DBS Group Holdings'
            })
            mock_ticker.return_value = ticker_service

            mock_sqs.return_value = None

            yield {
                'job': job_service,
                'ticker': ticker_service,
                'sqs': mock_sqs
            }

    def test_cache_hit_returns_completed_immediately(self, client, mock_services_with_cache):
        """When cache HIT, should return status='completed' with cached_* job_id"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.return_value = {
                'id': 123,
                'symbol': 'D05.SI',
                'report_text': 'Thai report content...',
                'report_json': {'ticker': 'DBS19', 'stance': 'bullish'},
                'status': 'completed'
            }
            mock_precompute_class.return_value = mock_precompute

            response = client.post("/api/v1/report/DBS19")

            assert response.status_code == 200
            data = response.json()
            # Should return cached job_id pattern
            assert data['job_id'].startswith('cached_'), f"Expected cached_* job_id, got {data['job_id']}"
            assert data['status'] == 'completed', f"Expected 'completed', got {data['status']}"
            # Should NOT create async job
            mock_services_with_cache['job'].create_job.assert_not_called()
            mock_services_with_cache['sqs'].assert_not_called()

    def test_cache_hit_uses_yahoo_ticker_for_lookup(self, client, mock_services_with_cache):
        """Cache lookup should use yahoo_ticker (D05.SI), not DR symbol (DBS19)"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.return_value = {
                'id': 123,
                'symbol': 'D05.SI',
                'report_text': 'Thai report content...',
                'report_json': {},
                'status': 'completed'
            }
            mock_precompute_class.return_value = mock_precompute

            client.post("/api/v1/report/DBS19")

            # Verify cache lookup used yahoo_ticker
            mock_precompute.get_cached_report.assert_called_once()
            call_args = mock_precompute.get_cached_report.call_args
            lookup_symbol = call_args[0][0] if call_args[0] else call_args[1].get('symbol')
            assert lookup_symbol == 'D05.SI', f"Expected lookup with 'D05.SI', got '{lookup_symbol}'"

    def test_cache_miss_creates_async_job(self, client, mock_services_with_cache):
        """When cache MISS (no report), should create async job as before"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.return_value = None  # Cache MISS
            mock_precompute_class.return_value = mock_precompute

            response = client.post("/api/v1/report/DBS19")

            assert response.status_code == 200
            data = response.json()
            # Should return regular job_id (not cached_*)
            assert data['job_id'] == 'rpt_abc123'
            assert data['status'] == 'pending'
            # Should create async job
            mock_services_with_cache['job'].create_job.assert_called_once()
            mock_services_with_cache['sqs'].assert_called_once()

    def test_cache_miss_when_report_text_empty(self, client, mock_services_with_cache):
        """Cache with empty report_text should be treated as MISS"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.return_value = {
                'id': 123,
                'symbol': 'D05.SI',
                'report_text': '',  # Empty = MISS
                'report_json': {},
                'status': 'completed'
            }
            mock_precompute_class.return_value = mock_precompute

            response = client.post("/api/v1/report/DBS19")

            assert response.status_code == 200
            data = response.json()
            # Should fall through to async job
            assert data['status'] == 'pending'
            mock_services_with_cache['job'].create_job.assert_called_once()

    def test_cache_error_falls_back_to_async_job(self, client, mock_services_with_cache):
        """If cache lookup fails with exception, should fall back to async job"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.side_effect = Exception("Aurora connection failed")
            mock_precompute_class.return_value = mock_precompute

            response = client.post("/api/v1/report/DBS19")

            assert response.status_code == 200
            data = response.json()
            # Should fall back to async job gracefully
            assert data['status'] == 'pending'
            mock_services_with_cache['job'].create_job.assert_called_once()

    def test_force_refresh_skips_cache(self, client, mock_services_with_cache):
        """force_refresh=true should skip cache and always create async job"""
        with patch('src.data.aurora.precompute_service.PrecomputeService') as mock_precompute_class:
            mock_precompute = Mock()
            mock_precompute.get_cached_report.return_value = {
                'id': 123,
                'symbol': 'D05.SI',
                'report_text': 'Thai report content...',
                'report_json': {},
                'status': 'completed'
            }
            mock_precompute_class.return_value = mock_precompute

            response = client.post("/api/v1/report/DBS19?force_refresh=true")

            assert response.status_code == 200
            data = response.json()
            # Should skip cache and create async job
            assert data['status'] == 'pending'
            # PrecomputeService should not be called at all
            mock_precompute.get_cached_report.assert_not_called()


class TestAsyncReportModels:
    """Tests for Pydantic models used in async report endpoints"""

    def test_job_submit_response_model(self):
        """Test JobSubmitResponse model structure"""
        from src.api.models import JobSubmitResponse

        response = JobSubmitResponse(job_id='rpt_abc123')
        assert response.job_id == 'rpt_abc123'
        assert response.status == 'pending'

    def test_job_status_response_model(self):
        """Test JobStatusResponse model structure"""
        from src.api.models import JobStatusResponse

        response = JobStatusResponse(
            job_id='rpt_abc123',
            ticker='NVDA19',
            status='completed',
            created_at=datetime.now(),
            finished_at=datetime.now(),
            result={'ticker': 'NVDA19'}
        )
        assert response.job_id == 'rpt_abc123'
        assert response.status == 'completed'
        assert response.result is not None
