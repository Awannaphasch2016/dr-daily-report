# -*- coding: utf-8 -*-
"""Tests for Aurora MySQL data layer."""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


class TestAuroraClient:
    """Test suite for AuroraClient."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear singleton
        import src.data.aurora.client as client_module
        client_module._aurora_client = None

    @patch('src.data.aurora.client.pymysql.connect')
    def test_client_creates_connection(self, mock_connect):
        """Test that client creates MySQL connection."""
        from src.data.aurora.client import AuroraClient

        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        client = AuroraClient(
            host='test-host',
            database='test_db',
            user='admin',
            password='secret'
        )

        with client.get_connection() as conn:
            assert conn is not None

        mock_connect.assert_called_once()

    @patch('src.data.aurora.client.pymysql.connect')
    def test_client_execute_runs_query(self, mock_connect):
        """Test that execute runs SQL query."""
        from src.data.aurora.client import AuroraClient

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_conn

        client = AuroraClient(
            host='test-host',
            database='test_db',
            user='admin',
            password='secret'
        )

        result = client.execute(
            "INSERT INTO ticker_info (symbol) VALUES (%s)",
            ('NVDA',)
        )

        assert result == 1
        mock_cursor.execute.assert_called_once()

    @patch('src.data.aurora.client.pymysql.connect')
    def test_client_fetch_one(self, mock_connect):
        """Test that fetch_one returns single row."""
        from src.data.aurora.client import AuroraClient

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'symbol': 'NVDA', 'display_name': 'NVIDIA'}
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_conn

        client = AuroraClient(
            host='test-host',
            database='test_db',
            user='admin',
            password='secret'
        )

        result = client.fetch_one("SELECT * FROM ticker_info WHERE symbol = %s", ('NVDA',))

        assert result['symbol'] == 'NVDA'
        assert result['display_name'] == 'NVIDIA'

    @patch('src.data.aurora.client.pymysql.connect')
    def test_client_health_check_healthy(self, mock_connect):
        """Test health check returns healthy status."""
        from src.data.aurora.client import AuroraClient

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'health': 1, 'server_time': '2025-01-01 00:00:00'}
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_connect.return_value = mock_conn

        client = AuroraClient(
            host='test-host',
            database='test_db',
            user='admin',
            password='secret'
        )

        result = client.health_check()

        assert result['status'] == 'healthy'
        assert result['host'] == 'test-host'

    def test_client_requires_host_or_secret(self):
        """Test that client raises error without host or secret ARN."""
        from src.data.aurora.client import AuroraClient

        client = AuroraClient()  # No config

        with pytest.raises(ValueError, match="Aurora host not configured"):
            with client.get_connection():
                pass


class TestTickerRepository:
    """Test suite for TickerRepository."""

    @patch('src.data.aurora.repository.get_aurora_client')
    def test_upsert_ticker_info(self, mock_get_client):
        """Test upserting ticker info."""
        from src.data.aurora.repository import TickerRepository

        mock_client = MagicMock()
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        repo = TickerRepository()
        result = repo.upsert_ticker_info(
            symbol='NVDA',
            display_name='NVIDIA',
            company_name='NVIDIA Corporation',
            sector='Technology'
        )

        assert result == 1
        mock_client.execute.assert_called_once()

    @patch('src.data.aurora.repository.get_aurora_client')
    def test_get_ticker_info(self, mock_get_client):
        """Test getting ticker info by symbol."""
        from src.data.aurora.repository import TickerRepository

        mock_client = MagicMock()
        mock_client.fetch_one.return_value = {
            'id': 1,
            'symbol': 'NVDA',
            'display_name': 'NVIDIA',
            'sector': 'Technology'
        }
        mock_get_client.return_value = mock_client

        repo = TickerRepository()
        result = repo.get_ticker_info('NVDA')

        assert result['symbol'] == 'NVDA'
        assert result['sector'] == 'Technology'

    @patch('src.data.aurora.repository.get_aurora_client')
    def test_bulk_upsert_from_dataframe(self, mock_get_client):
        """Test bulk upsert from pandas DataFrame."""
        from src.data.aurora.repository import TickerRepository

        mock_client = MagicMock()
        mock_client.fetch_one.return_value = {'id': 1, 'symbol': 'NVDA'}
        mock_client.execute_many.return_value = 5
        mock_get_client.return_value = mock_client

        # Create sample DataFrame (yfinance format)
        df = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [104.0, 105.0, 106.0],
            'Adj Close': [104.0, 105.0, 106.0],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2025-01-01', periods=3))

        repo = TickerRepository()
        result = repo.bulk_upsert_from_dataframe('NVDA', df)

        assert result == 5
        mock_client.execute_many.assert_called_once()

    @patch('src.data.aurora.repository.get_aurora_client')
    def test_get_prices_as_dataframe(self, mock_get_client):
        """Test getting prices as DataFrame."""
        from src.data.aurora.repository import TickerRepository

        mock_client = MagicMock()
        mock_client.fetch_all.return_value = [
            {
                'price_date': date(2025, 1, 1),
                'open': 100.0,
                'high': 105.0,
                'low': 99.0,
                'close': 104.0,
                'adj_close': 104.0,
                'volume': 1000000
            },
            {
                'price_date': date(2025, 1, 2),
                'open': 104.0,
                'high': 108.0,
                'low': 103.0,
                'close': 107.0,
                'adj_close': 107.0,
                'volume': 1100000
            }
        ]
        mock_get_client.return_value = mock_client

        repo = TickerRepository()
        df = repo.get_prices_as_dataframe('NVDA', start_date=date(2025, 1, 1))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'Open' in df.columns
        assert 'Close' in df.columns

    @patch('src.data.aurora.repository.get_aurora_client')
    def test_get_stats(self, mock_get_client):
        """Test getting database stats."""
        from src.data.aurora.repository import TickerRepository

        mock_client = MagicMock()
        mock_client.fetch_one.side_effect = [
            {'count': 46},  # ticker count
            {'count': 12000},  # price row count
            {'min_date': date(2024, 1, 1), 'max_date': date(2025, 1, 15)}  # date range
        ]
        mock_get_client.return_value = mock_client

        repo = TickerRepository()
        stats = repo.get_stats()

        assert stats['ticker_count'] == 46
        assert stats['price_row_count'] == 12000
        assert stats['min_date'] == '2024-01-01'


class TestTickerFetcherWithAurora:
    """Test TickerFetcher Aurora integration."""

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetcher_without_aurora(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test TickerFetcher works without Aurora enabled."""
        from src.scheduler.ticker_fetcher import TickerFetcher

        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA': 'NVDA'}
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        fetcher = TickerFetcher(enable_aurora=False)

        assert fetcher.enable_aurora is False
        assert fetcher._aurora_repo is None

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    @patch('src.data.aurora.TickerRepository')
    def test_fetcher_with_aurora_enabled(self, mock_repo_class, mock_data_fetcher_class, mock_s3_cache_class):
        """Test TickerFetcher initializes Aurora when enabled."""
        from src.scheduler.ticker_fetcher import TickerFetcher

        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA': 'NVDA'}
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache_class.return_value = mock_s3_cache

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        fetcher = TickerFetcher(enable_aurora=True)

        assert fetcher.enable_aurora is True

    @patch('src.scheduler.ticker_fetcher.S3Cache')
    @patch('src.scheduler.ticker_fetcher.DataFetcher')
    def test_fetch_ticker_returns_aurora_rows(self, mock_data_fetcher_class, mock_s3_cache_class):
        """Test fetch_ticker returns aurora_rows count."""
        from src.scheduler.ticker_fetcher import TickerFetcher

        mock_data_fetcher = MagicMock()
        mock_data_fetcher.load_tickers.return_value = {'NVDA': 'NVDA'}
        mock_data_fetcher.fetch_ticker_data.return_value = {
            'company_name': 'NVIDIA',
            'info': {'shortName': 'NVIDIA'},
            'history': pd.DataFrame()
        }
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_s3_cache = MagicMock()
        mock_s3_cache.put_json.return_value = True
        mock_s3_cache_class.return_value = mock_s3_cache

        fetcher = TickerFetcher(enable_aurora=False)
        result = fetcher.fetch_ticker('NVDA')

        assert result['status'] == 'success'
        assert result['aurora_rows'] == 0  # Aurora disabled
