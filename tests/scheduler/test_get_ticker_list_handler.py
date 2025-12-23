# -*- coding: utf-8 -*-
"""
Unit tests for get_ticker_list_handler.py

Tests the Lambda handler that queries ticker_master for active DR symbols.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestGetTickerListHandler:
    """Test suite for get_ticker_list Lambda handler"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_env = {
            'AURORA_HOST': 'test-aurora.cluster.rds.amazonaws.com',
            'AURORA_USERNAME': 'test_user',
            'AURORA_PASSWORD': 'test_password',
            'AURORA_DATABASE': 'ticker_data',
            'AURORA_PORT': '3306'
        }

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db'
    })
    def test_returns_ticker_list_successfully(self, mock_connect):
        """Test successful ticker list retrieval"""
        from src.scheduler.get_ticker_list_handler import lambda_handler

        # Mock database query result
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('NVDA19',),
            ('DBS19',),
            ('AAPL19',),
            ('TSLA19',)
        ]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Call handler
        result = lambda_handler({}, None)

        # Verify result structure
        assert isinstance(result, dict), "Result should be a dict"
        assert 'tickers' in result, "Result must have 'tickers' field"
        assert 'count' in result, "Result must have 'count' field"

        # Verify ticker list content
        assert result['count'] == 4, f"Expected 4 tickers, got {result['count']}"
        assert 'NVDA19' in result['tickers']
        assert 'DBS19' in result['tickers']
        assert 'AAPL19' in result['tickers']
        assert 'TSLA19' in result['tickers']

        # Verify database interaction
        mock_connect.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()

        # Verify SQL query structure
        executed_query = mock_cursor.execute.call_args[0][0]
        assert 'ticker_master' in executed_query.lower()
        assert 'ticker_aliases' in executed_query.lower()
        assert 'is_active = true' in executed_query.lower()
        assert "symbol_type = 'dr'" in executed_query.lower()

        # Verify connection cleanup
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db'
    })
    def test_returns_empty_list_when_no_tickers(self, mock_connect):
        """Test handling of empty ticker list"""
        from src.scheduler.get_ticker_list_handler import lambda_handler

        # Mock empty result
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Call handler
        result = lambda_handler({}, None)

        # Verify empty list handling
        assert result['count'] == 0
        assert result['tickers'] == []

    @patch.dict('os.environ', {}, clear=True)
    def test_fails_when_missing_env_vars(self):
        """Test failure when required environment variables are missing"""
        from src.scheduler.get_ticker_list_handler import lambda_handler

        # Call handler without env vars - should raise KeyError
        with pytest.raises(KeyError):
            lambda_handler({}, None)

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db'
    })
    def test_handles_database_connection_error(self, mock_connect):
        """Test handling of database connection errors"""
        from src.scheduler.get_ticker_list_handler import lambda_handler
        import pymysql

        # Mock connection error
        mock_connect.side_effect = pymysql.Error("Connection failed")

        # Call handler - should raise exception
        with pytest.raises(pymysql.Error):
            lambda_handler({}, None)

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db'
    })
    def test_handles_query_execution_error(self, mock_connect):
        """Test handling of SQL query execution errors"""
        from src.scheduler.get_ticker_list_handler import lambda_handler
        import pymysql

        # Mock query execution error
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = pymysql.Error("Query execution failed")

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Call handler - should raise exception
        with pytest.raises(pymysql.Error):
            lambda_handler({}, None)

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db',
        'AURORA_PORT': '3307'  # Custom port
    })
    def test_uses_custom_port_from_env(self, mock_connect):
        """Test that custom Aurora port is used if specified"""
        from src.scheduler.get_ticker_list_handler import lambda_handler

        # Mock successful connection
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('NVDA19',)]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Call handler
        lambda_handler({}, None)

        # Verify port parameter
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['port'] == 3307

    @patch('src.scheduler.get_ticker_list_handler.pymysql.connect')
    @patch.dict('os.environ', {
        'AURORA_HOST': 'test-host',
        'AURORA_USERNAME': 'test-user',
        'AURORA_PASSWORD': 'test-pass',
        'AURORA_DATABASE': 'test-db'
    })
    def test_output_schema_matches_step_functions_expectation(self, mock_connect):
        """Test that output schema matches what Step Functions expects"""
        from src.scheduler.get_ticker_list_handler import lambda_handler

        # Mock result
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('NVDA19',), ('DBS19',)
        ]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Call handler
        result = lambda_handler({}, None)

        # Verify Step Functions contract
        # Step Functions expects: $.ticker_list.tickers
        assert 'tickers' in result, "Must have 'tickers' field for Step Functions"
        assert isinstance(result['tickers'], list), "tickers must be a list"
        assert all(isinstance(t, str) for t in result['tickers']), "All tickers must be strings"

        # Verify count field (helpful for logging/monitoring)
        assert 'count' in result
        assert result['count'] == len(result['tickers'])

        # Verify JSON serializability (Lambda requirement)
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed == result
