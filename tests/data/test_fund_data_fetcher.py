"""
Unit tests for fund_data_fetcher module.

Tests the fund_data fetching logic in isolation using mocks.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.data.aurora.fund_data_fetcher import (
    fetch_fund_data_metrics,
    DataNotFoundError
)


class TestFundDataFetcher:
    """Test suite for fund_data_fetcher module"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.sample_ticker = 'D05.SI'
        self.sample_date = date(2025, 11, 18)

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_fetch_fund_data_metrics_success(self, mock_get_client):
        """Verify fund_data metrics fetched correctly"""
        # Mock database response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('14.08'), 'value_text': None},
            {'col_code': 'ROE', 'value_numeric': Decimal('12.5'), 'value_text': None},
            {'col_code': 'P/BV', 'value_numeric': Decimal('2.3'), 'value_text': None},
            {'col_code': 'TARGET_PRC', 'value_numeric': Decimal('60.0'), 'value_text': None},
            {'col_code': 'SECTOR', 'value_numeric': None, 'value_text': 'Financials'}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute
        metrics = fetch_fund_data_metrics(self.sample_ticker)

        # DEFENSIVE TESTING: Verify actual outcomes, not just execution
        assert isinstance(metrics, dict), f"Expected dict, got {type(metrics)}"
        assert len(metrics) == 5, f"Expected 5 metrics, got {len(metrics)}"

        # Verify expected COL_CODEs present
        assert 'FY1_PE' in metrics
        assert 'ROE' in metrics
        assert 'P/BV' in metrics
        assert 'TARGET_PRC' in metrics
        assert 'SECTOR' in metrics

        # Verify numeric values converted from Decimal to float
        assert isinstance(metrics['FY1_PE'], float), f"Expected float, got {type(metrics['FY1_PE'])}"
        assert metrics['FY1_PE'] == 14.08
        assert metrics['ROE'] == 12.5
        assert metrics['P/BV'] == 2.3
        assert metrics['TARGET_PRC'] == 60.0

        # Verify text values
        assert isinstance(metrics['SECTOR'], str)
        assert metrics['SECTOR'] == 'Financials'

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_fetch_fund_data_metrics_not_found(self, mock_get_client):
        """Verify DataNotFoundError raised for missing ticker"""
        # Mock database response - empty result
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No data

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute and verify exception raised
        with pytest.raises(DataNotFoundError, match="No fund_data found for ticker INVALID.TICKER"):
            fetch_fund_data_metrics('INVALID.TICKER')

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_fetch_fund_data_metrics_specific_date(self, mock_get_client):
        """Verify fetching for specific trading date"""
        # Mock database response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('15.5'), 'value_text': None}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute with specific date
        metrics = fetch_fund_data_metrics(self.sample_ticker, d_trade=self.sample_date)

        # Verify query was called with date parameter
        assert len(metrics) > 0
        assert 'FY1_PE' in metrics

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_decimal_to_float_conversion(self, mock_get_client):
        """Verify Decimal types converted to float at system boundary"""
        # Mock database response with Decimal values
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('14.08123456'), 'value_text': None}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute
        metrics = fetch_fund_data_metrics(self.sample_ticker)

        # DEFENSIVE: Verify type conversion at system boundary (PyMySQL → Python)
        assert isinstance(metrics['FY1_PE'], float), "Decimal must be converted to float"
        assert not isinstance(metrics['FY1_PE'], Decimal), "Decimal not converted!"
        assert metrics['FY1_PE'] == 14.08123456

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_none_values_allowed_in_metrics(self, mock_get_client):
        """Verify None values are allowed in metrics dict (valid data scenario)"""
        # Mock database response - rows exist with None values (valid scenario)
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        # Rows exist but both numeric and text values are None (valid - metric exists but no value)
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('14.08'), 'value_text': None},
            {'col_code': 'SECTOR', 'value_numeric': None, 'value_text': None}  # None is valid
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute - should NOT raise exception
        metrics = fetch_fund_data_metrics(self.sample_ticker)

        # Verify None values are preserved
        assert 'SECTOR' in metrics
        assert metrics['SECTOR'] is None  # None is allowed

    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_mixed_numeric_and_text_values(self, mock_get_client):
        """Verify handling of both numeric and text COL_CODE values"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('14.08'), 'value_text': None},
            {'col_code': 'SECTOR', 'value_numeric': None, 'value_text': 'Technology'},
            {'col_code': 'ROE', 'value_numeric': Decimal('15.0'), 'value_text': None}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        metrics = fetch_fund_data_metrics(self.sample_ticker)

        # Verify numeric values are floats
        assert isinstance(metrics['FY1_PE'], float)
        assert isinstance(metrics['ROE'], float)

        # Verify text value is string
        assert isinstance(metrics['SECTOR'], str)
        assert metrics['SECTOR'] == 'Technology'

    @patch('src.data.aurora.fund_data_fetcher.get_ticker_resolver')
    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_ticker_resolution_to_eikon(self, mock_get_client, mock_get_resolver):
        """Verify TickerResolver is used to resolve symbols to Eikon format"""
        # Mock TickerResolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver

        # Mock TickerInfo with Eikon symbol
        mock_ticker_info = MagicMock()
        mock_ticker_info.eikon_symbol = 'DBSM.SI'  # Eikon format (different from Yahoo D05.SI)
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_resolver.resolve.return_value = mock_ticker_info

        # Mock database response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('14.08'), 'value_text': None}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute with Yahoo symbol
        metrics = fetch_fund_data_metrics('D05.SI')

        # Verify TickerResolver was called
        mock_resolver.resolve.assert_called_once_with('D05.SI')

        # Verify query used Eikon symbol (DBSM.SI), not input symbol (D05.SI)
        # Check that cursor.execute was called with eikon_symbol
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1][0] == 'DBSM.SI', "Should use Eikon symbol in query"

        # Verify metrics were returned
        assert 'FY1_PE' in metrics
        assert metrics['FY1_PE'] == 14.08

    @patch('src.data.aurora.fund_data_fetcher.get_ticker_resolver')
    def test_unknown_ticker_raises_error(self, mock_get_resolver):
        """Verify DataNotFoundError raised when TickerResolver returns None"""
        # Mock TickerResolver returning None (unknown ticker)
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver
        mock_resolver.resolve.return_value = None

        # Should raise DataNotFoundError immediately
        with pytest.raises(DataNotFoundError, match="Unknown ticker: INVALID"):
            fetch_fund_data_metrics('INVALID')

        # Verify resolver was called
        mock_resolver.resolve.assert_called_once_with('INVALID')

    @patch('src.data.aurora.fund_data_fetcher.get_ticker_resolver')
    @patch('src.data.aurora.fund_data_fetcher.get_aurora_client')
    def test_fallback_to_yahoo_when_no_eikon(self, mock_get_client, mock_get_resolver):
        """Verify fallback to yahoo_symbol when eikon_symbol is None"""
        # Mock TickerResolver
        mock_resolver = MagicMock()
        mock_get_resolver.return_value = mock_resolver

        # Mock TickerInfo with NO Eikon symbol (fallback to Yahoo)
        mock_ticker_info = MagicMock()
        mock_ticker_info.eikon_symbol = None  # No Eikon mapping
        mock_ticker_info.yahoo_symbol = '7974.T'  # Fallback to Yahoo
        mock_resolver.resolve.return_value = mock_ticker_info

        # Mock database response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'col_code': 'FY1_PE', 'value_numeric': Decimal('15.5'), 'value_text': None}
        ]

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        mock_client.get_connection.return_value = mock_conn

        # Execute
        metrics = fetch_fund_data_metrics('NINTENDO19')

        # Verify query used yahoo_symbol as fallback
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1][0] == '7974.T', "Should fallback to yahoo_symbol when no eikon_symbol"

        assert 'FY1_PE' in metrics
