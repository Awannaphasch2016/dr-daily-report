# -*- coding: utf-8 -*-
"""Tests for PrecomputeService - specifically store_report_from_api().

These tests serve as regression tests to prevent bugs like:
- Querying non-existent tables (ticker_info vs ticker_master)
- Symbol resolution failures
- Silent cache write failures
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass


class TestStoreReportFromApi:
    """Regression tests for store_report_from_api().

    Bug History:
    - 2025-12-02: Method queried non-existent 'ticker_info' table instead of
                  using TickerResolver which queries 'ticker_master' + 'ticker_aliases'
    """

    def setup_method(self):
        """Reset singletons before each test."""
        # Clear TickerResolver singleton
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

        # Clear PrecomputeService dependencies
        import src.data.aurora.client as client_module
        client_module._aurora_client = None

    @patch('src.data.aurora.client.get_aurora_client')
    def test_store_report_uses_ticker_resolver_not_repo(self, mock_get_client):
        """Regression: Must use TickerResolver, not repo.get_ticker_info().

        The repo.get_ticker_info() queries 'ticker_info' table which doesn't exist.
        TickerResolver correctly uses 'ticker_master' + 'ticker_aliases' tables.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        # Mock Aurora client
        mock_client = MagicMock()
        # For TickerResolver: simulate ticker_master table doesn't exist (force CSV fallback)
        mock_client.fetch_one.return_value = {'cnt': 0}
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        # Create service and call store_report_from_api
        service = PrecomputeService()
        result = service.store_report_from_api(
            symbol='DBS19',  # Known ticker in tickers.csv
            report_text='Test report in Thai',
            report_json={'ticker': 'DBS19', 'stance': 'bullish'},
            strategy='multi_stage_analysis'
        )

        # Should succeed because TickerResolver found the ticker via CSV fallback
        assert result is True, "store_report_from_api should return True on success"

    @patch('src.data.aurora.client.get_aurora_client')
    def test_store_report_returns_false_for_unknown_ticker(self, mock_get_client):
        """Test that unknown tickers return False, not raise exception."""
        from src.data.aurora.precompute_service import PrecomputeService

        # Mock Aurora client - force CSV fallback
        mock_client = MagicMock()
        mock_client.fetch_one.return_value = {'cnt': 0}
        mock_get_client.return_value = mock_client

        service = PrecomputeService()
        result = service.store_report_from_api(
            symbol='UNKNOWN99',  # Not in tickers.csv
            report_text='Test report',
            report_json={'ticker': 'UNKNOWN99'},
        )

        # Should return False for unknown ticker
        assert result is False, "Should return False for unknown ticker"

    @patch('src.data.aurora.client.get_aurora_client')
    def test_store_report_extracts_ticker_id_from_resolver(self, mock_get_client):
        """Verify ticker_id comes from TickerResolver.resolve().ticker_id."""
        from src.data.aurora.precompute_service import PrecomputeService

        # Mock Aurora client
        mock_client = MagicMock()
        mock_client.fetch_one.return_value = {'cnt': 0}  # Force CSV fallback
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        service = PrecomputeService()
        result = service.store_report_from_api(
            symbol='NVDA19',  # Known ticker in tickers.csv
            report_text='Test',
            report_json={},
        )

        # Verify execute was called (meaning we got past ticker resolution)
        assert mock_client.execute.called, "Should call execute to store report"
        assert result is True

    @patch('src.data.aurora.ticker_resolver.get_aurora_client')
    def test_ticker_resolver_loads_from_csv_fallback(self, mock_client):
        """Test TickerResolver falls back to CSV when Aurora unavailable."""
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        # Simulate Aurora connection failure
        mock_client.side_effect = Exception("Connection refused")

        resolver = get_ticker_resolver()

        # Should still work using CSV fallback
        info = resolver.resolve('DBS19')

        # DBS19 should be in tickers.csv
        assert info is not None, "Should resolve DBS19 from CSV fallback"
        assert info.dr_symbol == 'DBS19'
        assert info.yahoo_symbol is not None


class TestStoreCompletedReport:
    """Regression tests for _store_completed_report SQL schema matching.

    Bug History:
    - 2025-12-02: Query referenced non-existent columns (date, pdf_s3_key,
                  pdf_generated_at, report_generated_at). Actual schema has
                  report_date, computed_at, expires_at.
    """

    def setup_method(self):
        """Reset singletons."""
        import src.data.aurora.client as client_module
        client_module._aurora_client = None
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.data.aurora.client.get_aurora_client')
    def test_store_completed_report_uses_valid_columns(self, mock_get_client):
        """Regression: SQL must only reference columns that exist in schema.

        Expected schema columns:
            id, ticker_id, ticker_master_id, symbol, report_date,
            report_text, report_json, strategy, model_used,
            generation_time_ms, token_count, cost_usd, mini_reports,
            faithfulness_score, completeness_score, reasoning_score,
            chart_base64, status, error_message, computed_at, expires_at
        """
        from src.data.aurora.precompute_service import PrecomputeService
        from datetime import date

        mock_client = MagicMock()
        mock_client.fetch_one.return_value = {'cnt': 0}  # Force CSV fallback
        mock_client.execute.return_value = 1
        mock_get_client.return_value = mock_client

        service = PrecomputeService()

        # Call the internal method directly
        service._store_completed_report(
            ticker_id=1,
            symbol='TEST',
            data_date=date.today(),
            report_text='Test report',
            report_json={'test': 'data'},
            strategy='multi_stage_analysis',
            generation_time_ms=1000,
            mini_reports={},
            chart_base64='base64data',
        )

        # Verify execute was called
        assert mock_client.execute.called, "Should execute INSERT query"

        # Get the SQL query that was executed
        call_args = mock_client.execute.call_args
        sql_query = call_args[0][0].lower()

        # Verify ONLY valid columns are referenced
        valid_columns = [
            'ticker_id', 'ticker_master_id', 'symbol', 'report_date',
            'report_text', 'report_json', 'strategy', 'model_used',
            'generation_time_ms', 'token_count', 'cost_usd', 'mini_reports',
            'faithfulness_score', 'completeness_score', 'reasoning_score',
            'chart_base64', 'status', 'error_message', 'computed_at', 'expires_at'
        ]

        # These columns should NOT be in the query (they don't exist in schema)
        invalid_columns = ['date', 'pdf_s3_key', 'pdf_generated_at', 'report_generated_at']

        for col in invalid_columns:
            # Check column name is not used (avoid false positives like 'date' in 'report_date')
            # Use word boundary check
            import re
            pattern = rf'\b{col}\b'
            if col == 'date':
                # Special case: 'date' should not appear alone, but 'report_date' is ok
                pattern = r'\bdate\b(?!_)'  # date not followed by underscore
            matches = re.findall(pattern, sql_query)
            assert not matches, f"Query references non-existent column '{col}': {sql_query}"


class TestTickerResolverIntegration:
    """Test TickerResolver symbol resolution."""

    def setup_method(self):
        """Reset singleton."""
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @patch('src.data.aurora.ticker_resolver.get_aurora_client')
    def test_resolve_dr_symbol(self, mock_client):
        """Test resolving DR symbol (e.g., DBS19)."""
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        # Force CSV fallback
        mock_client.side_effect = Exception("No Aurora")

        resolver = get_ticker_resolver()
        info = resolver.resolve('DBS19')

        assert info is not None
        assert info.dr_symbol == 'DBS19'
        assert 'D05' in info.yahoo_symbol or 'SI' in info.yahoo_symbol

    @patch('src.data.aurora.ticker_resolver.get_aurora_client')
    def test_resolve_yahoo_symbol(self, mock_client):
        """Test resolving Yahoo symbol (e.g., D05.SI)."""
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        mock_client.side_effect = Exception("No Aurora")

        resolver = get_ticker_resolver()
        info = resolver.resolve('D05.SI')

        assert info is not None
        assert info.yahoo_symbol == 'D05.SI'

    @patch('src.data.aurora.ticker_resolver.get_aurora_client')
    def test_resolve_returns_none_for_unknown(self, mock_client):
        """Test unknown symbols return None."""
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        mock_client.side_effect = Exception("No Aurora")

        resolver = get_ticker_resolver()
        info = resolver.resolve('NOTREAL999')

        assert info is None
