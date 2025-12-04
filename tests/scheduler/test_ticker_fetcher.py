# -*- coding: utf-8 -*-
"""Tests for TickerFetcher"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import pandas as pd
import numpy as np


class TestTickerFetcher:
    """Test suite for TickerFetcher"""

    def setup_method(self):
        """Set up test fixtures"""
        # Mock environment
        self.env_patcher = patch.dict('os.environ', {
            'PDF_BUCKET_NAME': 'test-bucket'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Tear down test fixtures"""
        self.env_patcher.stop()

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_initialization(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test TickerFetcher initializes correctly"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {
            'NVDA19': 'NVDA',
            'DBS19': 'D05.SI'
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')

        # Assert
        assert isinstance(fetcher.tickers, list)
        assert len(fetcher.tickers) == 2
        assert 'NVDA' in fetcher.tickers
        assert 'D05.SI' in fetcher.tickers
        mock_data_fetcher.load_tickers.assert_called_once()

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_success(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test successful single ticker fetch"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA19': 'NVDA'}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 150.0,
            'company_name': 'NVIDIA Corporation',
            'history': pd.DataFrame({'Close': [150.0]})
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        result = fetcher.fetch_ticker('NVDA')

        # Assert
        assert result['status'] == 'success'
        assert result['ticker'] == 'NVDA'
        assert result['company_name'] == 'NVIDIA Corporation'
        mock_data_fetcher.fetch_ticker_data.assert_called_once_with('NVDA')
        mock_s3_cache.put_json.assert_called_once()

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_no_data(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test ticker fetch when no data returned"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'INVALID': 'INVALID'}
        mock_data_fetcher.fetch_ticker_data.return_value = None
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        result = fetcher.fetch_ticker('INVALID')

        # Assert
        assert result['status'] == 'failed'
        assert result['ticker'] == 'INVALID'
        assert 'error' in result
        mock_s3_cache.put_json.assert_not_called()

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_exception(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test ticker fetch handles exceptions"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA19': 'NVDA'}
        mock_data_fetcher.fetch_ticker_data.side_effect = Exception('API Error')
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        result = fetcher.fetch_ticker('NVDA')

        # Assert
        assert result['status'] == 'failed'
        assert result['ticker'] == 'NVDA'
        assert 'API Error' in result['error']

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_tickers_multiple(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test fetching multiple tickers"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {
            'NVDA19': 'NVDA',
            'DBS19': 'D05.SI'
        }
        mock_data_fetcher.fetch_ticker_data.side_effect = [
            {'close': 150.0, 'company_name': 'NVIDIA'},
            {'close': 25.0, 'company_name': 'DBS Bank'}
        ]
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        results = fetcher.fetch_tickers(['NVDA', 'D05.SI'])

        # Assert
        assert results['total'] == 2
        assert results['success_count'] == 2
        assert results['failed_count'] == 0
        assert len(results['success']) == 2

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_all_tickers(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test fetching all supported tickers"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {
            'NVDA19': 'NVDA',
            'DBS19': 'D05.SI',
            'UOB19': 'U11.SI'
        }
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 100.0,
            'company_name': 'Test Company'
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        results = fetcher.fetch_all_tickers()

        # Assert
        assert results['total'] == 3
        assert results['success_count'] == 3
        assert results['failed_count'] == 0
        assert mock_data_fetcher.fetch_ticker_data.call_count == 3

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_make_json_serializable(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test JSON serialization of numpy/pandas types"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {}
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')

        # Test various types
        test_data = {
            'int64': np.int64(42),
            'float64': np.float64(3.14),
            'date': date(2025, 1, 15),
            'array': np.array([1, 2, 3]),
            'nested': {'value': np.float64(1.5)}
        }

        # Act
        result = fetcher._make_json_serializable(test_data)

        # Assert
        assert result['int64'] == 42
        assert isinstance(result['int64'], int)
        assert result['float64'] == 3.14
        assert isinstance(result['float64'], float)
        assert result['date'] == '2025-01-15'
        assert result['array'] == [1, 2, 3]
        assert result['nested']['value'] == 1.5

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_get_cached_ticker_data(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test retrieving cached ticker data"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {}
        mock_data_fetcher_class.return_value = mock_data_fetcher

        cached_data = {'close': 150.0, 'company_name': 'NVIDIA'}
        mock_s3_cache = MagicMock()
        mock_s3_cache.get_json.return_value = cached_data
        mock_s3_cache_class.return_value = mock_s3_cache

        # Act
        from src.scheduler.ticker_fetcher import TickerFetcher
        fetcher = TickerFetcher(bucket_name='test-bucket')
        result = fetcher.get_cached_ticker_data('NVDA', '2025-01-15')

        # Assert
        assert result == cached_data
        mock_s3_cache.get_json.assert_called_once_with(
            cache_type='ticker_data',
            ticker='NVDA',
            date='2025-01-15',
            filename='data.json'
        )


class TestSchedulerHandler:
    """Test suite for scheduler Lambda handler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.env_patcher = patch.dict('os.environ', {
            'PDF_BUCKET_NAME': 'test-bucket'
        })
        self.env_patcher.start()

    def teardown_method(self):
        """Tear down test fixtures"""
        self.env_patcher.stop()

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_handler_fetch_all(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test handler fetches all tickers by default"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA19': 'NVDA'}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 150.0, 'company_name': 'NVIDIA'
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        from src.scheduler.handler import lambda_handler

        # Act
        result = lambda_handler({}, None)

        # Assert
        assert result['statusCode'] == 200
        assert result['body']['success_count'] == 1
        assert result['body']['failed_count'] == 0
        mock_data_fetcher.fetch_ticker_data.assert_called_once_with('NVDA')

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_handler_fetch_specific(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test handler fetches specific tickers when provided"""
        # Arrange
        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA19': 'NVDA', 'DBS19': 'DBS'}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'close': 150.0, 'company_name': 'Test'
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        from src.scheduler.handler import lambda_handler

        # Act
        result = lambda_handler({'tickers': ['NVDA', 'DBS']}, None)

        # Assert
        assert result['statusCode'] == 200
        assert result['body']['success_count'] == 2
        assert mock_data_fetcher.fetch_ticker_data.call_count == 2

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_handler_error_handling(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test handler handles exceptions gracefully"""
        # Arrange - make initialization fail
        mock_data_fetcher_class.side_effect = Exception('Initialization failed')

        from src.scheduler.handler import lambda_handler

        # Act
        result = lambda_handler({}, None)

        # Assert
        assert result['statusCode'] == 500
        assert 'error' in result['body']
        assert 'Initialization failed' in result['body']['error']
