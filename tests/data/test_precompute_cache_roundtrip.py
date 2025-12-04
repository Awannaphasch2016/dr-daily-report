"""Unit tests for cache store→lookup round-trip behavior.

These tests use mocks (no live Aurora) to verify code correctness.
Tests the bug where INSERT uses `ticker_id` but SELECT uses `ticker_master_id`.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date


class TestCacheRoundtripBehavior:
    """Verify that reports stored can be looked up successfully."""

    @patch('src.data.aurora.client.get_aurora_client')
    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    def test_get_cached_report_query_uses_valid_columns(
        self, mock_resolver_fn, mock_get_client
    ):
        """SELECT query should NOT reference non-existent ticker_master_id column.

        The table schema has 'ticker_id', not 'ticker_master_id'.
        This test catches the column name mismatch bug.
        """
        # Setup mock resolver
        mock_ticker_info = MagicMock()
        mock_ticker_info.ticker_id = 123
        mock_ticker_info.yahoo_symbol = 'MWG.VN'
        mock_ticker_info.dr_symbol = 'MWG19'
        mock_resolver_fn.return_value.resolve.return_value = mock_ticker_info

        # Setup mock client
        mock_client = MagicMock()
        mock_client.fetch_one.return_value = None
        mock_get_client.return_value = mock_client

        # Import and call
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        service.get_cached_report('MWG.VN')

        # Get the SQL query that was executed
        query = mock_client.fetch_one.call_args[0][0]

        # ASSERTION: Query should NOT reference ticker_master_id
        # (This column doesn't exist in the schema!)
        assert 'ticker_master_id' not in query, \
            f"Query references 'ticker_master_id' which doesn't exist in schema. " \
            f"Should use 'ticker_id' instead. Query: {query}"

    @patch('src.data.aurora.client.get_aurora_client')
    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    def test_get_cached_report_uses_ticker_id_for_fallback_lookup(
        self, mock_resolver_fn, mock_get_client
    ):
        """SELECT query should use ticker_id (not ticker_master_id) for ID-based lookup."""
        # Setup mock resolver
        mock_ticker_info = MagicMock()
        mock_ticker_info.ticker_id = 123
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_ticker_info.dr_symbol = 'DBS19'
        mock_resolver_fn.return_value.resolve.return_value = mock_ticker_info

        # Setup mock client
        mock_client = MagicMock()
        mock_client.fetch_one.return_value = None
        mock_get_client.return_value = mock_client

        # Import and call
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        service.get_cached_report('DBS19')

        # Get the SQL query that was executed
        query = mock_client.fetch_one.call_args[0][0]

        # The query should have ticker_id for the ID-based fallback lookup
        # (symbol IN (...) OR (ticker_id IS NOT NULL AND ticker_id = %s))
        if 'ticker_id IS NOT NULL' in query or 'ticker_id =' in query:
            # Good - using the correct column name
            pass
        elif 'ticker_master_id' in query:
            pytest.fail(
                f"Query uses 'ticker_master_id' which doesn't exist in schema!\n"
                f"The INSERT uses 'ticker_id', so SELECT should too.\n"
                f"Query: {query}"
            )

    @patch('src.data.aurora.client.get_aurora_client')
    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    def test_store_and_lookup_use_consistent_columns(
        self, mock_resolver_fn, mock_get_client
    ):
        """INSERT and SELECT should reference the same column for ticker ID."""
        # Setup
        mock_ticker_info = MagicMock()
        mock_ticker_info.ticker_id = 123
        mock_ticker_info.yahoo_symbol = 'MWG.VN'
        mock_ticker_info.dr_symbol = 'MWG19'
        mock_resolver_fn.return_value.resolve.return_value = mock_ticker_info

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()

        # Store
        service.store_report_from_api(
            symbol='MWG19',
            report_text='Test report',
            report_json={'test': True}
        )
        insert_query = mock_client.execute.call_args[0][0]

        # Lookup
        service.get_cached_report('MWG.VN')
        select_query = mock_client.fetch_one.call_args[0][0]

        # Both should use 'ticker_id' (the actual column name)
        assert 'ticker_id' in insert_query, "INSERT should use ticker_id"

        # SELECT should NOT have ticker_master_id
        if 'ticker_master_id' in select_query:
            pytest.fail(
                f"Column name mismatch!\n"
                f"INSERT uses: ticker_id\n"
                f"SELECT uses: ticker_master_id (WRONG!)\n"
                f"This causes cache lookup to fail even when report was stored."
            )


class TestStoreReportReturnValue:
    """Test that store_report_from_api correctly reports success/failure.

    Bug 2: INSERT may fail due to FK constraint (ticker_id not in ticker_info),
    but code logs "✅ Cached" anyway because it doesn't check rowcount.
    """

    @patch('src.data.aurora.client.get_aurora_client')
    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    def test_store_returns_false_when_insert_affects_zero_rows(
        self, mock_resolver_fn, mock_get_client
    ):
        """store_report_from_api should return False when INSERT affects 0 rows.

        This catches the silent FK failure bug where ticker_id doesn't exist
        in ticker_info table but code still reports success.
        """
        # Setup mock resolver - returns a ticker_id
        mock_ticker_info = MagicMock()
        mock_ticker_info.ticker_id = 999  # ID that doesn't exist in ticker_info
        mock_ticker_info.yahoo_symbol = 'MWG.VN'
        mock_ticker_info.dr_symbol = 'MWG19'
        mock_resolver_fn.return_value.resolve.return_value = mock_ticker_info

        # Setup mock client - execute returns 0 (no rows affected = FK failure)
        mock_client = MagicMock()
        mock_client.execute.return_value = 0  # Simulates FK constraint failure
        mock_get_client.return_value = mock_client

        # Import and call
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        result = service.store_report_from_api(
            symbol='MWG19',
            report_text='Test report',
            report_json={'test': True}
        )

        # ASSERTION: Should return False when INSERT affected 0 rows
        assert result is False, (
            "store_report_from_api returned True but INSERT affected 0 rows!\n"
            "This means FK constraint failed (ticker_id not in ticker_info) "
            "but code didn't detect the failure.\n"
            "The code should check execute() rowcount and return False on failure."
        )

    @patch('src.data.aurora.client.get_aurora_client')
    @patch('src.data.aurora.ticker_resolver.get_ticker_resolver')
    def test_store_returns_true_when_insert_succeeds(
        self, mock_resolver_fn, mock_get_client
    ):
        """store_report_from_api should return True when INSERT succeeds."""
        # Setup mock resolver
        mock_ticker_info = MagicMock()
        mock_ticker_info.ticker_id = 1
        mock_ticker_info.yahoo_symbol = 'D05.SI'
        mock_ticker_info.dr_symbol = 'DBS19'
        mock_resolver_fn.return_value.resolve.return_value = mock_ticker_info

        # Setup mock client - execute returns 1 (one row inserted)
        mock_client = MagicMock()
        mock_client.execute.return_value = 1  # Success
        mock_get_client.return_value = mock_client

        # Import and call
        from src.data.aurora.precompute_service import PrecomputeService
        service = PrecomputeService()
        result = service.store_report_from_api(
            symbol='DBS19',
            report_text='Test report',
            report_json={'test': True}
        )

        # ASSERTION: Should return True when INSERT succeeds
        assert result is True, (
            "store_report_from_api returned False but INSERT succeeded (rowcount=1)!"
        )
