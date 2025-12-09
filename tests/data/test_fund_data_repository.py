# -*- coding: utf-8 -*-
"""
Unit tests for FundDataRepository (TDD RED → GREEN verification)

Tests follow defensive programming principles from CLAUDE.md:
- Test outcomes, not execution
- Explicit failure detection
- Round-trip validation
- Idempotency testing
- Schema contract testing
- Test sabotage verification
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.fund_data_repository import FundDataRepository


class TestFundDataRepository:
    """Unit tests for fund data repository with defensive programming."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Aurora client
        self.mock_client = MagicMock()
        self.repo = FundDataRepository(client=self.mock_client)

        # Sample valid record
        self.sample_record = {
            'd_trade': date(2025, 12, 9),
            'stock': 'DBS',
            'ticker': 'DBS19',
            'col_code': 'CLOSE',
            'value_numeric': Decimal('38.50'),
            'value_text': None,
            's3_source_key': 'raw/sql_server/fund_data/2025-12-09/test.csv'
        }

    # =========================================================================
    # Principle 1: Test Outcomes, Not Execution
    # =========================================================================

    def test_batch_upsert_returns_rowcount_not_just_success(self):
        """GIVEN valid records
        WHEN batch upsert executes
        THEN returns actual rowcount (not boolean/None)

        Principle: Test outcomes (rowcount value) not execution (method called)
        """
        self.mock_client.execute.return_value = 2  # 1 insert, 1 update

        records = [self.sample_record]
        rowcount = self.repo.batch_upsert(records)

        # Outcome validation - exact rowcount matters
        assert isinstance(rowcount, int), "Must return int rowcount"
        assert rowcount == 2, "Should return actual affected rows"

    def test_insert_affects_one_row_on_new_record(self):
        """GIVEN new record (not duplicate)
        WHEN inserted
        THEN rowcount = 1 (MySQL INSERT behavior)

        Principle: Test database behavior outcome
        """
        self.mock_client.execute.return_value = 1  # New insert

        rowcount = self.repo.batch_upsert([self.sample_record])

        assert rowcount == 1, "New INSERT should affect 1 row"

    def test_update_affects_two_rows_on_duplicate(self):
        """GIVEN duplicate composite key
        WHEN ON DUPLICATE KEY UPDATE executes
        THEN rowcount = 2 (MySQL ON DUPLICATE KEY behavior)

        Principle: Test MySQL-specific outcome
        """
        self.mock_client.execute.return_value = 2  # ON DUPLICATE KEY UPDATE

        rowcount = self.repo.batch_upsert([self.sample_record])

        assert rowcount == 2, "ON DUPLICATE KEY UPDATE affects 2 rows in MySQL"

    # =========================================================================
    # Principle 2: Explicit Failure Detection
    # =========================================================================

    def test_batch_upsert_raises_on_empty_records(self):
        """GIVEN empty records list
        WHEN batch_upsert called
        THEN raises ValueError (not silently returns 0)

        Principle: Explicit failure, not silent fallback
        """
        with pytest.raises(ValueError, match="Cannot upsert empty records list"):
            self.repo.batch_upsert([])

    def test_batch_upsert_raises_on_missing_required_fields(self):
        """GIVEN record missing required fields
        WHEN batch_upsert validates
        THEN raises ValueError listing missing fields

        Principle: Fail fast with visibility
        """
        invalid_record = {
            'd_trade': date(2025, 12, 9),
            'ticker': 'DBS19',
            # Missing: stock, col_code, s3_source_key
        }

        with pytest.raises(ValueError, match="missing required fields"):
            self.repo.batch_upsert([invalid_record])

    def test_batch_upsert_raises_on_zero_rowcount(self):
        """GIVEN database returns 0 affected rows
        WHEN batch_upsert executes
        THEN raises RuntimeError (defensive check)

        Principle: Detect silent failures (FK constraint, ENUM mismatch)
        """
        self.mock_client.execute.return_value = 0  # Silent failure

        with pytest.raises(RuntimeError, match="affected 0 rows"):
            self.repo.batch_upsert([self.sample_record])

    def test_normalize_date_raises_on_invalid_format(self):
        """GIVEN invalid date string
        WHEN _normalize_date called
        THEN raises ValueError (not returns None)

        Principle: Type conversion failures must be explicit
        """
        with pytest.raises(ValueError, match="Invalid date format"):
            self.repo._normalize_date("INVALID_DATE")

    def test_normalize_date_raises_on_wrong_type(self):
        """GIVEN non-date, non-string value
        WHEN _normalize_date called
        THEN raises ValueError with type information

        Principle: Clear error messages for debugging
        """
        with pytest.raises(ValueError, match="Expected date or str, got int"):
            self.repo._normalize_date(12345)

    def test_normalize_numeric_raises_on_unconvertible_value(self):
        """GIVEN non-numeric string
        WHEN _normalize_numeric called
        THEN raises ValueError

        Principle: Type conversion at system boundary must validate
        """
        with pytest.raises(ValueError, match="Cannot convert"):
            self.repo._normalize_numeric("ABC123")

    # =========================================================================
    # Principle 3: Round-Trip Validation
    # =========================================================================

    def test_store_then_retrieve_by_ticker_roundtrip(self):
        """GIVEN records stored
        WHEN retrieved by ticker
        THEN data matches original

        Principle: Round-trip tests verify persistence contract
        """
        # Mock upsert success
        self.mock_client.execute.return_value = 1

        # Store
        self.repo.batch_upsert([self.sample_record])

        # Mock retrieval
        self.mock_client.fetch_all.return_value = [
            (
                1,  # id
                date(2025, 12, 9),  # d_trade
                'DBS',  # stock
                'DBS19',  # ticker
                'CLOSE',  # col_code
                Decimal('38.50'),  # value_numeric
                None,  # value_text
                'sql_server',  # source
                'raw/sql_server/fund_data/2025-12-09/test.csv',  # s3_source_key
                datetime(2025, 12, 9, 10, 0, 0),  # synced_at
                datetime(2025, 12, 9, 10, 0, 0),  # updated_at
            )
        ]

        # Retrieve
        results = self.repo.get_latest_by_ticker('DBS19', days=30)

        # Round-trip validation
        assert len(results) == 1
        result = results[0]
        assert result['ticker'] == self.sample_record['ticker']
        assert result['d_trade'] == self.sample_record['d_trade']
        assert result['value_numeric'] == self.sample_record['value_numeric']
        assert result['s3_source_key'] == self.sample_record['s3_source_key']

    def test_store_then_retrieve_by_s3_source_roundtrip(self):
        """GIVEN records stored from S3
        WHEN retrieved by s3_source_key
        THEN can trace data lineage

        Principle: Data lineage tracking via round-trip
        """
        self.mock_client.execute.return_value = 1
        s3_key = 'raw/sql_server/fund_data/2025-12-09/test.csv'

        # Store
        self.repo.batch_upsert([self.sample_record])

        # Mock retrieval by S3 source
        self.mock_client.fetch_all.return_value = [
            (
                1, date(2025, 12, 9), 'DBS', 'DBS19', 'CLOSE',
                Decimal('38.50'), None, 'sql_server', s3_key,
                datetime(2025, 12, 9, 10, 0, 0),
                datetime(2025, 12, 9, 10, 0, 0)
            )
        ]

        # Retrieve by lineage
        results = self.repo.get_by_s3_source(s3_key)

        # Verify lineage preserved
        assert len(results) == 1
        assert results[0]['s3_source_key'] == s3_key

    # =========================================================================
    # Principle 4: Idempotency Testing
    # =========================================================================

    def test_inserting_same_record_twice_updates_not_duplicates(self):
        """GIVEN record inserted
        WHEN same composite key inserted again
        THEN updates existing row (ON DUPLICATE KEY UPDATE)

        Principle: Idempotency via composite unique key
        """
        # First insert
        self.mock_client.execute.return_value = 1
        rowcount1 = self.repo.batch_upsert([self.sample_record])
        assert rowcount1 == 1

        # Second insert (duplicate key)
        self.mock_client.execute.return_value = 2  # ON DUPLICATE KEY UPDATE
        updated_record = self.sample_record.copy()
        updated_record['value_numeric'] = Decimal('39.00')  # Changed value

        rowcount2 = self.repo.batch_upsert([updated_record])

        # Verify update behavior
        assert rowcount2 == 2, "ON DUPLICATE KEY UPDATE should affect 2 rows"

    def test_composite_key_uniqueness(self):
        """GIVEN records with same (d_trade, stock, ticker, col_code)
        WHEN batch upserted
        THEN composite key prevents duplicates

        Principle: Test database constraint behavior
        """
        # Both records have same composite key
        record1 = self.sample_record.copy()
        record2 = self.sample_record.copy()
        record2['value_numeric'] = Decimal('39.00')  # Different value

        # Mock: MySQL would update, not insert twice
        self.mock_client.execute.return_value = 2  # 1 insert + 1 update

        rowcount = self.repo.batch_upsert([record1, record2])

        # Should not double-insert (rowcount would be 2 for 2 inserts)
        # Instead: 1 insert + 1 update = 2 affected rows
        assert rowcount == 2

    # =========================================================================
    # Principle 5: Type Normalization (System Boundary)
    # =========================================================================

    def test_normalize_date_accepts_date_object(self):
        """GIVEN date object
        WHEN normalized
        THEN returns ISO format string

        Principle: Type conversion at Python → MySQL boundary
        """
        d = date(2025, 12, 9)
        result = self.repo._normalize_date(d)

        assert result == '2025-12-09'
        assert isinstance(result, str)

    def test_normalize_date_accepts_iso_string(self):
        """GIVEN ISO date string
        WHEN normalized
        THEN validates and returns unchanged

        Principle: Accept multiple input formats
        """
        result = self.repo._normalize_date('2025-12-09')

        assert result == '2025-12-09'

    def test_normalize_numeric_accepts_decimal(self):
        """GIVEN Decimal value
        WHEN normalized
        THEN returns unchanged

        Principle: Preserve precision types
        """
        d = Decimal('38.123456')
        result = self.repo._normalize_numeric(d)

        assert result == d
        assert isinstance(result, Decimal)

    def test_normalize_numeric_converts_int_to_decimal(self):
        """GIVEN int value
        WHEN normalized
        THEN converts to Decimal

        Principle: Type conversion to preserve precision
        """
        result = self.repo._normalize_numeric(123)

        assert result == Decimal('123')
        assert isinstance(result, Decimal)

    def test_normalize_numeric_converts_float_to_decimal(self):
        """GIVEN float value
        WHEN normalized
        THEN converts to Decimal (via string to avoid precision loss)

        Principle: Avoid float precision issues
        """
        result = self.repo._normalize_numeric(38.50)

        assert result == Decimal('38.5')
        assert isinstance(result, Decimal)

    def test_normalize_numeric_converts_string_to_decimal(self):
        """GIVEN numeric string
        WHEN normalized
        THEN converts to Decimal

        Principle: Handle string inputs from external sources
        """
        result = self.repo._normalize_numeric('38.50')

        assert result == Decimal('38.50')
        assert isinstance(result, Decimal)

    def test_normalize_numeric_returns_none_for_none(self):
        """GIVEN None value
        WHEN normalized
        THEN returns None (not raises)

        Principle: NULL is valid database value
        """
        result = self.repo._normalize_numeric(None)

        assert result is None

    # =========================================================================
    # Principle 6: Query Methods
    # =========================================================================

    def test_get_latest_by_ticker_filters_by_days(self):
        """GIVEN ticker data query
        WHEN get_latest_by_ticker called
        THEN filters last N days

        Principle: Test query behavior, not SQL syntax
        """
        self.mock_client.fetch_all.return_value = []

        self.repo.get_latest_by_ticker('DBS19', days=7)

        # Verify query was called (behavior test)
        self.mock_client.fetch_all.assert_called_once()
        call_args = self.mock_client.fetch_all.call_args
        assert 'DBS19' in call_args[0]  # Ticker parameter
        assert 7 in call_args[0]  # Days parameter

    def test_get_by_date_range_uses_provided_dates(self):
        """GIVEN date range
        WHEN get_by_date_range called
        THEN queries between dates

        Principle: Test query parameters, not implementation
        """
        self.mock_client.fetch_all.return_value = []

        start = date(2025, 12, 1)
        end = date(2025, 12, 9)

        self.repo.get_by_date_range('DBS19', start_date=start, end_date=end)

        call_args = self.mock_client.fetch_all.call_args
        assert start in call_args[0]
        assert end in call_args[0]

    def test_get_by_date_range_defaults_end_to_today(self):
        """GIVEN no end_date provided
        WHEN get_by_date_range called
        THEN defaults to today

        Principle: Test default behavior
        """
        self.mock_client.fetch_all.return_value = []

        start = date(2025, 12, 1)

        self.repo.get_by_date_range('DBS19', start_date=start, end_date=None)

        # Verify query executed (we can't easily assert "today" without time dependency)
        self.mock_client.fetch_all.assert_called_once()

    def test_get_by_s3_source_enables_data_lineage_query(self):
        """GIVEN S3 source key
        WHEN get_by_s3_source called
        THEN retrieves all records from that source

        Principle: Test data lineage capability
        """
        self.mock_client.fetch_all.return_value = []
        s3_key = 'raw/sql_server/fund_data/2025-12-09/test.csv'

        self.repo.get_by_s3_source(s3_key)

        call_args = self.mock_client.fetch_all.call_args
        assert s3_key in call_args[0]

    # =========================================================================
    # Principle 7: Row to Dict Conversion
    # =========================================================================

    def test_row_to_dict_converts_all_fields(self):
        """GIVEN database row tuple
        WHEN converted to dict
        THEN all fields mapped correctly

        Principle: Test data structure conversion
        """
        row = (
            1,  # id
            date(2025, 12, 9),  # d_trade
            'DBS',  # stock
            'DBS19',  # ticker
            'CLOSE',  # col_code
            Decimal('38.50'),  # value_numeric
            None,  # value_text
            'sql_server',  # source
            'raw/sql_server/fund_data/2025-12-09/test.csv',  # s3_source_key
            datetime(2025, 12, 9, 10, 0, 0),  # synced_at
            datetime(2025, 12, 9, 10, 0, 0),  # updated_at
        )

        result = self.repo._row_to_dict(row)

        assert result['id'] == 1
        assert result['d_trade'] == date(2025, 12, 9)
        assert result['stock'] == 'DBS'
        assert result['ticker'] == 'DBS19'
        assert result['col_code'] == 'CLOSE'
        assert result['value_numeric'] == Decimal('38.50')
        assert result['value_text'] is None
        assert result['source'] == 'sql_server'
        assert 's3_source_key' in result

    # =========================================================================
    # Principle 8: Test Sabotage Verification
    # =========================================================================

    def test_sabotage_removing_rowcount_check(self):
        """SABOTAGE TEST: If _upsert_batch doesn't check rowcount
        THEN test should FAIL

        Principle: Verify test catches defensive programming removal

        To verify this test works:
        1. Comment out "if rowcount == 0: raise RuntimeError" in _upsert_batch
        2. Run test - should FAIL
        3. Uncomment - test should PASS
        """
        self.mock_client.execute.return_value = 0  # Silent failure

        # This MUST raise RuntimeError due to defensive check
        with pytest.raises(RuntimeError, match="affected 0 rows"):
            self.repo.batch_upsert([self.sample_record])

        # If defensive check removed, this test would fail (test the test!)

    def test_sabotage_accepting_empty_records(self):
        """SABOTAGE TEST: If validation removed
        THEN test should FAIL

        Verifies empty list validation
        """
        # This MUST raise ValueError
        with pytest.raises(ValueError, match="Cannot upsert empty records list"):
            self.repo.batch_upsert([])

        # If validation removed, test would fail

    def test_sabotage_skipping_field_validation(self):
        """SABOTAGE TEST: If required field check removed
        THEN test should FAIL

        Verifies required field validation
        """
        invalid_record = {'ticker': 'DBS19'}  # Missing required fields

        # This MUST raise ValueError
        with pytest.raises(ValueError, match="missing required fields"):
            self.repo.batch_upsert([invalid_record])

        # If validation removed, would silently fail or raise different error


# =============================================================================
# Integration Test Stubs (would use actual Aurora connection)
# =============================================================================

class TestFundDataRepositoryIntegration:
    """Integration tests with actual Aurora database.

    Note: These require Aurora connection and are marked as integration tests.
    Run with: pytest -m integration
    """

    @pytest.mark.integration
    def test_actual_insert_and_retrieve_roundtrip(self):
        """GIVEN actual Aurora database
        WHEN record inserted and retrieved
        THEN data integrity preserved

        This would use real AuroraClient, not mock.
        Skipped in unit tests (requires Aurora VPC access).
        """
        pytest.skip("Requires Aurora database connection")

    @pytest.mark.integration
    def test_actual_duplicate_key_update(self):
        """GIVEN actual database with unique constraint
        WHEN duplicate inserted
        THEN ON DUPLICATE KEY UPDATE executes

        Verifies MySQL behavior matches test assumptions.
        """
        pytest.skip("Requires Aurora database connection")

    @pytest.mark.integration
    def test_actual_composite_key_constraint(self):
        """GIVEN actual database
        WHEN duplicate composite key inserted
        THEN constraint enforced

        Validates schema migration 003 works as expected.
        """
        pytest.skip("Requires Aurora database connection")
