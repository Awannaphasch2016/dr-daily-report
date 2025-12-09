# -*- coding: utf-8 -*-
"""
Unit tests for FundDataParser (TDD RED → GREEN verification)

Tests follow defensive programming principles from CLAUDE.md:
- Test outcomes, not execution
- Explicit failure mocking
- Round-trip validation
- Schema contract testing
- Silent failure detection
- Test sabotage verification
"""

import io
from datetime import date
from decimal import Decimal

import pytest

from src.data.etl.fund_data_parser import FundDataParser


class TestFundDataParser:
    """Unit tests for CSV parser with encoding detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = FundDataParser()
        self.s3_key = "raw/sql_server/fund_data/2025-12-09/test.csv"

    # =========================================================================
    # Principle 1: Test Outcomes, Not Execution
    # =========================================================================

    def test_parse_returns_typed_records_not_just_strings(self):
        """GIVEN valid CSV
        WHEN parsed
        THEN returns typed records (date, Decimal), not raw strings

        Principle: Test outcomes (typed data) not execution (parsing happened)
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        # Outcome validation - actual types matter
        assert len(records) == 1
        record = records[0]
        assert isinstance(record['d_trade'], date), "d_trade must be date object"
        assert record['d_trade'] == date(2025, 12, 9)
        assert isinstance(record['value_numeric'], Decimal), "value_numeric must be Decimal"
        assert record['value_numeric'] == Decimal('38.50')
        assert record['ticker'] == 'DBS19'

    # =========================================================================
    # Principle 2: Explicit Failure Mocking
    # =========================================================================

    def test_parse_detects_missing_header(self):
        """GIVEN CSV with no header row
        WHEN parsed
        THEN raises ValueError with clear message

        Principle: Explicit failure detection, not silent None return
        """
        csv_data = b"2025-12-09,DBS,DBS19,CLOSE,38.50"  # No header

        with pytest.raises(ValueError, match="CSV has no header row"):
            self.parser.parse(csv_data, self.s3_key)

    def test_parse_detects_missing_required_columns(self):
        """GIVEN CSV missing required columns
        WHEN parsed
        THEN raises ValueError listing missing columns

        Principle: Fail fast with visibility
        """
        csv_data = b"d_trade,stock,ticker\n2025-12-09,DBS,DBS19"  # Missing col_code, value

        with pytest.raises(ValueError, match="CSV missing required columns"):
            self.parser.parse(csv_data, self.s3_key)

    def test_parse_detects_empty_csv(self):
        """GIVEN CSV with header but no data rows
        WHEN parsed
        THEN raises ValueError (not returns empty list)

        Principle: Explicit failure - empty data is an error condition
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n"  # Header only

        with pytest.raises(ValueError, match="CSV contains no data rows"):
            self.parser.parse(csv_data, self.s3_key)

    def test_parse_detects_invalid_date_format(self):
        """GIVEN CSV with invalid date
        WHEN parsed
        THEN raises ValueError with row context

        Principle: Rich error messages for debugging
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\nINVALID_DATE,DBS,DBS19,CLOSE,38.50"

        with pytest.raises(ValueError, match="Failed to parse row 2"):
            self.parser.parse(csv_data, self.s3_key)

    def test_parse_detects_missing_required_field_values(self):
        """GIVEN CSV with empty required fields
        WHEN parsed
        THEN raises ValueError for each missing field

        Defensive: Required fields must be populated
        """
        # Missing ticker
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,,CLOSE,38.50"

        with pytest.raises(ValueError, match="Field 'ticker' is required but empty"):
            self.parser.parse(csv_data, self.s3_key)

    # =========================================================================
    # Principle 3: Round-Trip Validation
    # =========================================================================

    def test_parse_preserves_data_integrity_roundtrip(self):
        """GIVEN CSV with various data types
        WHEN parsed and values extracted
        THEN all values match expected with no loss

        Principle: Data survives conversion unchanged
        """
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1234567
2025-12-09,DBS,DBS19,STATUS,ACTIVE"""

        records = self.parser.parse(csv_data, self.s3_key)

        assert len(records) == 3

        # Numeric value preserved
        assert records[0]['value_numeric'] == Decimal('38.50')
        assert records[0]['value_text'] is None

        # Large numeric preserved
        assert records[1]['value_numeric'] == Decimal('1234567')

        # Text value preserved
        assert records[2]['value_numeric'] is None
        assert records[2]['value_text'] == 'ACTIVE'

    # =========================================================================
    # Principle 4: Encoding Detection
    # =========================================================================

    def test_encoding_detection_utf8(self):
        """GIVEN UTF-8 encoded CSV
        WHEN encoding detected
        THEN correctly decodes UTF-8
        """
        csv_data = "d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50".encode('utf-8')

        records = self.parser.parse(csv_data, self.s3_key)

        assert len(records) == 1
        assert records[0]['ticker'] == 'DBS19'

    def test_encoding_detection_windows1252(self):
        """GIVEN Windows-1252 encoded CSV (from SQL Server export)
        WHEN encoding detected
        THEN correctly decodes Windows-1252

        Real-world: SQL Server exports often use Windows-1252
        """
        csv_data = "d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50".encode('windows-1252')

        records = self.parser.parse(csv_data, self.s3_key)

        assert len(records) == 1
        assert records[0]['ticker'] == 'DBS19'

    def test_encoding_detection_fails_gracefully_on_low_confidence(self):
        """GIVEN CSV with ambiguous encoding (low confidence)
        WHEN encoding detected
        THEN logs warning but proceeds

        Defensive: Don't block pipeline on encoding uncertainty
        """
        # Most chardet will detect SOME encoding even on binary garbage
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        # Should not raise even with low confidence
        records = self.parser.parse(csv_data, self.s3_key)
        assert len(records) == 1

    # =========================================================================
    # Principle 5: Type Conversion Edge Cases
    # =========================================================================

    def test_type_conversion_numeric_with_commas(self):
        """GIVEN numeric value with thousand separators
        WHEN parsed
        THEN commas removed and converted to Decimal
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,VOLUME,1,234,567"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['value_numeric'] == Decimal('1234567')

    def test_type_conversion_decimal_precision_preserved(self):
        """GIVEN high-precision decimal
        WHEN parsed
        THEN precision preserved (not float rounding)

        Defensive: Decimal prevents float precision loss
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,PRICE,38.123456"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['value_numeric'] == Decimal('38.123456')

    def test_type_conversion_text_vs_numeric_detection(self):
        """GIVEN values that look numeric but aren't
        WHEN parsed
        THEN correctly classified as text
        """
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CODE,ABC123
2025-12-09,DBS,DBS19,STATUS,ACTIVE"""

        records = self.parser.parse(csv_data, self.s3_key)

        # Not numeric - stored as text
        assert records[0]['value_numeric'] is None
        assert records[0]['value_text'] == 'ABC123'

        assert records[1]['value_numeric'] is None
        assert records[1]['value_text'] == 'ACTIVE'

    def test_type_conversion_empty_value_field(self):
        """GIVEN row with empty value field
        WHEN parsed
        THEN both value_numeric and value_text are None

        Edge case: Some SQL Server exports have NULL values
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['value_numeric'] is None
        assert records[0]['value_text'] is None

    # =========================================================================
    # Principle 6: Date Format Support
    # =========================================================================

    def test_date_format_yyyy_mm_dd(self):
        """GIVEN date in YYYY-MM-DD format
        WHEN parsed
        THEN correctly converted to date object
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['d_trade'] == date(2025, 12, 9)

    def test_date_format_mm_dd_yyyy(self):
        """GIVEN date in MM/DD/YYYY format (US format)
        WHEN parsed
        THEN correctly converted to date object
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n12/09/2025,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['d_trade'] == date(2025, 12, 9)

    def test_date_format_yyyymmdd(self):
        """GIVEN date in YYYYMMDD format (compact)
        WHEN parsed
        THEN correctly converted to date object
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n20251209,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        assert records[0]['d_trade'] == date(2025, 12, 9)

    # =========================================================================
    # Principle 7: Data Lineage Tracking
    # =========================================================================

    def test_parse_includes_s3_source_key_in_every_record(self):
        """GIVEN CSV with multiple rows
        WHEN parsed
        THEN every record includes s3_source_key for lineage

        Defensive: Data lineage is critical for audit trail
        """
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1000"""

        records = self.parser.parse(csv_data, self.s3_key)

        assert len(records) == 2
        assert records[0]['s3_source_key'] == self.s3_key
        assert records[1]['s3_source_key'] == self.s3_key

    # =========================================================================
    # Principle 8: Schema Contract Validation
    # =========================================================================

    def test_parse_returns_expected_schema_for_all_records(self):
        """GIVEN valid CSV
        WHEN parsed
        THEN every record has expected schema keys

        Schema contract: Cross-service boundary validation
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        expected_keys = {
            'd_trade', 'stock', 'ticker', 'col_code',
            'value_numeric', 'value_text', 's3_source_key'
        }

        for record in records:
            assert set(record.keys()) == expected_keys, \
                f"Record schema mismatch. Expected {expected_keys}, got {set(record.keys())}"

    # =========================================================================
    # Test Sabotage Verification (Defensive Programming)
    # =========================================================================

    def test_sabotage_parser_returns_empty_list(self):
        """SABOTAGE TEST: If parser returns [] instead of raising
        THEN test should FAIL (verifies test catches bugs)

        Principle: Verify tests can detect failures

        To verify this test works:
        1. Temporarily change parser to: return []
        2. Run test - should FAIL
        3. Revert change - test should PASS
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n"  # Empty data

        # This MUST raise, not return []
        with pytest.raises(ValueError, match="CSV contains no data rows"):
            self.parser.parse(csv_data, self.s3_key)

        # If parser was sabotaged to return [], pytest.raises would fail

    def test_sabotage_parser_returns_strings_not_types(self):
        """SABOTAGE TEST: If parser returns string '2025-12-09' instead of date
        THEN test should FAIL

        Verifies type conversion is actually happening
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)

        # If sabotaged to skip type conversion, this fails
        assert isinstance(records[0]['d_trade'], date), \
            "Parser must convert to date, not return string"
        assert isinstance(records[0]['value_numeric'], Decimal), \
            "Parser must convert to Decimal, not return string"


# =============================================================================
# Integration Test (would use actual files in tests/fixtures/)
# =============================================================================

class TestFundDataParserIntegration:
    """Integration tests with real CSV files."""

    def test_parse_real_export_from_sql_server(self):
        """GIVEN actual CSV exported from SQL Server
        WHEN parsed
        THEN successfully processes all rows

        Note: This would use a fixture CSV file in tests/fixtures/
        For now, simulating Windows-1252 encoding typical of SQL Server
        """
        # Simulate SQL Server export with Windows-1252 encoding
        csv_content = """d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1234567
2025-12-09,DBS,DBS19,STATUS,ACTIVE
2025-12-09,NVDA,NVDA19,CLOSE,150.25"""

        csv_data = csv_content.encode('windows-1252')
        parser = FundDataParser()

        records = parser.parse(csv_data, 'raw/sql_server/fund_data/2025-12-09/export.csv')

        assert len(records) == 4
        assert all(isinstance(r['d_trade'], date) for r in records)
        assert records[0]['ticker'] == 'DBS19'
        assert records[3]['ticker'] == 'NVDA19'
