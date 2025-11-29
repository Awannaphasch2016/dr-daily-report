# -*- coding: utf-8 -*-
"""
Tests for S3 Cache Functionality

Tests the S3 cache layer for report caching, chart caching,
and news caching with mocked AWS services.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date


class TestS3Cache:
    """Unit tests for S3Cache with mocked boto3"""

    @pytest.fixture
    def cache_with_mock(self):
        """Create S3Cache instance with mocked client, returns both"""
        mock_client = MagicMock()
        with patch('boto3.client', return_value=mock_client):
            from src.data.s3_cache import S3Cache
            cache = S3Cache(bucket_name='test-bucket', ttl_hours=24)
            # Replace the s3_client with our mock
            cache.s3_client = mock_client
            return cache, mock_client

    @pytest.fixture
    def s3_cache(self, cache_with_mock):
        """Get just the cache from the fixture"""
        return cache_with_mock[0]

    @pytest.fixture
    def mock_s3_client(self, cache_with_mock):
        """Get the mock client from the fixture"""
        return cache_with_mock[1]

    def _create_s3_response(self, body_content: bytes, metadata: dict = None):
        """Helper to create mock S3 get_object response with valid expiration"""
        from datetime import datetime, timedelta

        mock_body = MagicMock()
        mock_body.read.return_value = body_content

        # Default to non-expired metadata
        if metadata is None:
            # Set expires-at to 1 hour from now (not expired)
            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            metadata = {'expires-at': expires_at}

        return {
            'Body': mock_body,
            'Metadata': metadata
        }

    def test_init_creates_client(self):
        """Test that S3Cache initializes boto3 client"""
        with patch('boto3.client') as mock_boto3:
            from src.data.s3_cache import S3Cache
            cache = S3Cache(bucket_name='test-bucket')

            mock_boto3.assert_called_once_with('s3')
            assert cache.bucket_name == 'test-bucket'

    def test_get_cached_report_miss(self, s3_cache, mock_s3_client):
        """Test cache miss returns None"""
        from botocore.exceptions import ClientError

        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'GetObject'
        )

        result = s3_cache.get_cached_report('TEST', '2024-01-01')

        assert result is None

    def test_get_cached_report_hit(self, s3_cache, mock_s3_client):
        """Test cache hit returns cached data"""
        cached_data = {
            'report_text': 'Test report',
            'context_json': '{"test": "data"}'
        }

        mock_s3_client.get_object.return_value = self._create_s3_response(
            json.dumps(cached_data).encode('utf-8')
        )

        result = s3_cache.get_cached_report('TEST', '2024-01-01')

        assert result is not None, "Expected cached data, got None"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result['report_text'] == 'Test report'

    def test_save_report_success(self, s3_cache, mock_s3_client):
        """Test saving report to cache"""
        report_data = {
            'report_text': 'Test report',
            'context_json': '{"test": "data"}'
        }

        s3_cache.save_report_cache('TEST', '2024-01-01', report_data)

        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert 'TEST' in call_args[1]['Key']

    def test_save_chart_cache(self, s3_cache, mock_s3_client):
        """Test saving chart to cache"""
        chart_base64 = 'iVBORw0KGgoAAAANSUhEUg=='

        s3_cache.save_chart_cache('TEST', '2024-01-01', chart_base64)

        mock_s3_client.put_object.assert_called_once()

    def test_get_cached_chart_hit(self, s3_cache, mock_s3_client):
        """Test retrieving cached chart"""
        chart_base64 = 'iVBORw0KGgoAAAANSUhEUg=='

        mock_s3_client.get_object.return_value = self._create_s3_response(
            chart_base64.encode('utf-8')
        )

        result = s3_cache.get_cached_chart('TEST', '2024-01-01')

        assert result is not None, "Expected chart data, got None"
        assert result == chart_base64

    def test_save_news_cache(self, s3_cache, mock_s3_client):
        """Test saving news to cache"""
        news = [
            {'title': 'News 1', 'score': 80},
            {'title': 'News 2', 'score': 70}
        ]

        s3_cache.save_news_cache('TEST', '2024-01-01', news)

        mock_s3_client.put_object.assert_called_once()

    def test_get_cached_news_hit(self, s3_cache, mock_s3_client):
        """Test retrieving cached news"""
        news = [
            {'title': 'News 1', 'score': 80},
            {'title': 'News 2', 'score': 70}
        ]

        mock_s3_client.get_object.return_value = self._create_s3_response(
            json.dumps(news).encode('utf-8')
        )

        result = s3_cache.get_cached_news('TEST', '2024-01-01')

        assert result is not None, "Expected news data, got None"
        assert result == news
        assert len(result) == 2

    def test_get_pdf_url_returns_presigned_url(self, s3_cache, mock_s3_client):
        """Test getting presigned URL for PDF"""
        mock_s3_client.generate_presigned_url.return_value = 'https://s3.amazonaws.com/test-bucket/test.pdf?signature=xxx'

        # First check if PDF exists
        mock_s3_client.head_object.return_value = {}

        result = s3_cache.get_pdf_url('TEST', '2024-01-01')

        assert result is not None
        assert 'https://' in result

    def test_get_pdf_url_returns_none_if_not_exists(self, s3_cache, mock_s3_client):
        """Test PDF URL returns None if file doesn't exist"""
        from botocore.exceptions import ClientError

        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}},
            'HeadObject'
        )

        result = s3_cache.get_pdf_url('TEST', '2024-01-01')

        assert result is None


class TestS3CacheKeyGeneration:
    """Tests for S3 cache key generation"""

    @pytest.fixture
    def s3_cache(self):
        """Create S3Cache with mocked client"""
        with patch('boto3.client'):
            from src.data.s3_cache import S3Cache
            return S3Cache(bucket_name='test-bucket')

    def test_report_cache_key_format(self, s3_cache):
        """Test report cache key follows expected format"""
        # Use the public _get_cache_key method
        key = s3_cache._get_cache_key('reports', 'TEST', '2024-01-01', 'report.json')

        assert 'TEST' in key
        assert '2024-01-01' in key
        assert 'report' in key.lower()

    def test_chart_cache_key_format(self, s3_cache):
        """Test chart cache key follows expected format"""
        # Use the public _get_cache_key method
        key = s3_cache._get_cache_key('reports', 'TEST', '2024-01-01', 'chart.b64')

        assert 'TEST' in key
        assert '2024-01-01' in key
        assert 'chart' in key.lower()


@pytest.mark.integration
class TestS3CacheIntegration:
    """Integration tests requiring actual S3 access"""

    @pytest.fixture
    def real_s3_cache(self):
        """Create real S3Cache if bucket is configured"""
        bucket_name = os.getenv('PDF_BUCKET_NAME')
        if not bucket_name:
            pytest.skip("PDF_BUCKET_NAME not set")

        from src.data.s3_cache import S3Cache
        return S3Cache(bucket_name=bucket_name)

    def test_round_trip_report_cache(self, real_s3_cache):
        """Test saving and retrieving report from S3"""
        test_ticker = 'TEST_INTEGRATION'
        test_date = date.today().isoformat()

        report_data = {
            'report_text': 'Integration test report',
            'context_json': '{"integration": "test"}'
        }

        # Save
        real_s3_cache.save_report_cache(test_ticker, test_date, report_data)

        # Retrieve
        result = real_s3_cache.get_cached_report(test_ticker, test_date)

        assert result is not None
        assert result['report_text'] == 'Integration test report'
