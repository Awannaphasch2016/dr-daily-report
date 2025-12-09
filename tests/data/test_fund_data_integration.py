# -*- coding: utf-8 -*-
"""
Integration tests for Fund Data ETL pipeline (Parser + Repository)

Tests the complete data flow:
    CSV bytes → Parser → Repository → Aurora → Retrieval

Following defensive programming principles:
- Round-trip validation (store → retrieve → verify)
- Schema contract testing at system boundaries
- Explicit failure detection
- Data lineage tracking

Note: These tests require Aurora database connection (VPC access).
Run with: pytest -m integration
"""

import io
from datetime import date
from decimal import Decimal

import pytest

from src.data.etl.fund_data_parser import FundDataParser
from src.data.aurora.fund_data_repository import FundDataRepository
from src.data.aurora.client import get_aurora_client


@pytest.mark.integration
class TestFundDataETLIntegration:
    """Integration tests for complete ETL pipeline.

    Requires Aurora database connection - skipped in local environment.
    CI environment has VPC access via Lambda execution role.
    """

    def setup_method(self):
        """Set up integration test fixtures."""
        self.parser = FundDataParser()

        # Use actual Aurora client (requires VPC access)
        try:
            self.client = get_aurora_client()
            self.repo = FundDataRepository(client=self.client)
        except Exception as e:
            pytest.skip(f"Aurora connection not available: {e}")

        self.s3_key = "raw/sql_server/fund_data/2025-12-09/integration_test.csv"

    def teardown_method(self):
        """Clean up test data from Aurora."""
        # Delete test records by s3_source_key to avoid polluting database
        try:
            cleanup_query = "DELETE FROM fund_data WHERE s3_source_key = %s"
            self.client.execute(cleanup_query, (self.s3_key,))
        except:
            pass  # Best-effort cleanup

    # =========================================================================
    # Round-Trip Integration Tests
    # =========================================================================

    def test_complete_etl_pipeline_roundtrip(self):
        """GIVEN CSV bytes from S3
        WHEN parsed and upserted to Aurora
        THEN data can be retrieved unchanged

        Principle: Round-trip validation across full pipeline
        """
        # Step 1: Create CSV data (simulating S3 ObjectCreated event)
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1234567
2025-12-09,DBS,DBS19,STATUS,ACTIVE"""

        # Step 2: Parse CSV (ETL Extract)
        records = self.parser.parse(csv_data, self.s3_key)

        assert len(records) == 3, "Parser should extract 3 records"

        # Step 3: Batch upsert to Aurora (ETL Load)
        rowcount = self.repo.batch_upsert(records)

        assert rowcount >= 3, "Should insert at least 3 rows"

        # Step 4: Retrieve from Aurora
        results = self.repo.get_by_s3_source(self.s3_key)

        # Step 5: Round-trip validation
        assert len(results) == 3, "Should retrieve all 3 records"

        # Verify first record (numeric)
        close_record = next(r for r in results if r['col_code'] == 'CLOSE')
        assert close_record['ticker'] == 'DBS19'
        assert close_record['d_trade'] == date(2025, 12, 9)
        assert close_record['value_numeric'] == Decimal('38.50')
        assert close_record['value_text'] is None
        assert close_record['s3_source_key'] == self.s3_key

        # Verify second record (large numeric)
        volume_record = next(r for r in results if r['col_code'] == 'VOLUME')
        assert volume_record['value_numeric'] == Decimal('1234567')

        # Verify third record (text)
        status_record = next(r for r in results if r['col_code'] == 'STATUS')
        assert status_record['value_numeric'] is None
        assert status_record['value_text'] == 'ACTIVE'

    def test_windows1252_encoding_roundtrip(self):
        """GIVEN CSV with Windows-1252 encoding (SQL Server export)
        WHEN parsed and stored
        THEN encoding detected and data stored correctly

        Principle: Test real-world SQL Server export scenario
        """
        # SQL Server export with Windows-1252 encoding
        csv_content = "d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"
        csv_data = csv_content.encode('windows-1252')

        # Parse
        records = self.parser.parse(csv_data, self.s3_key)

        # Store
        rowcount = self.repo.batch_upsert(records)
        assert rowcount >= 1

        # Retrieve
        results = self.repo.get_by_s3_source(self.s3_key)

        # Verify
        assert len(results) == 1
        assert results[0]['ticker'] == 'DBS19'
        assert results[0]['value_numeric'] == Decimal('38.50')

    def test_idempotency_reprocessing_same_s3_file(self):
        """GIVEN CSV file already processed
        WHEN same file reprocessed (S3 event duplicate)
        THEN no duplicate rows created

        Principle: Idempotency via composite unique key
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        # First processing
        records = self.parser.parse(csv_data, self.s3_key)
        rowcount1 = self.repo.batch_upsert(records)
        assert rowcount1 == 1, "First insert should affect 1 row"

        # Second processing (duplicate S3 event)
        records = self.parser.parse(csv_data, self.s3_key)
        rowcount2 = self.repo.batch_upsert(records)
        assert rowcount2 == 2, "ON DUPLICATE KEY UPDATE should affect 2 rows"

        # Verify only 1 record exists
        results = self.repo.get_by_s3_source(self.s3_key)
        assert len(results) == 1, "Should have only 1 record (no duplicates)"

    def test_updated_value_overwrites_existing(self):
        """GIVEN record already in Aurora
        WHEN new CSV with updated value processed
        THEN value updated (not duplicated)

        Principle: Idempotency allows value updates
        """
        # Initial value
        csv_data_v1 = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"
        records = self.parser.parse(csv_data_v1, self.s3_key)
        self.repo.batch_upsert(records)

        # Updated value
        csv_data_v2 = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,39.00"
        records = self.parser.parse(csv_data_v2, self.s3_key)
        rowcount = self.repo.batch_upsert(records)

        assert rowcount == 2, "Update should affect 2 rows"

        # Verify updated value
        results = self.repo.get_by_s3_source(self.s3_key)
        assert len(results) == 1
        assert results[0]['value_numeric'] == Decimal('39.00'), "Value should be updated"

    # =========================================================================
    # Data Lineage Testing
    # =========================================================================

    def test_data_lineage_tracking_via_s3_key(self):
        """GIVEN multiple CSV files processed
        WHEN queried by s3_source_key
        THEN can trace exact origin

        Principle: Data lineage for audit trail
        """
        # File 1
        s3_key_1 = "raw/sql_server/fund_data/2025-12-09/file1.csv"
        csv_1 = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"
        records = self.parser.parse(csv_1, s3_key_1)
        self.repo.batch_upsert(records)

        # File 2
        s3_key_2 = "raw/sql_server/fund_data/2025-12-09/file2.csv"
        csv_2 = b"d_trade,stock,ticker,col_code,value\n2025-12-09,NVDA,NVDA19,CLOSE,150.25"
        records = self.parser.parse(csv_2, s3_key_2)
        self.repo.batch_upsert(records)

        # Query by lineage
        results_1 = self.repo.get_by_s3_source(s3_key_1)
        results_2 = self.repo.get_by_s3_source(s3_key_2)

        # Verify lineage separation
        assert len(results_1) == 1
        assert results_1[0]['ticker'] == 'DBS19'
        assert results_1[0]['s3_source_key'] == s3_key_1

        assert len(results_2) == 1
        assert results_2[0]['ticker'] == 'NVDA19'
        assert results_2[0]['s3_source_key'] == s3_key_2

        # Cleanup both files
        self.client.execute("DELETE FROM fund_data WHERE s3_source_key = %s", (s3_key_1,))
        self.client.execute("DELETE FROM fund_data WHERE s3_source_key = %s", (s3_key_2,))

    # =========================================================================
    # Query Integration Tests
    # =========================================================================

    def test_get_latest_by_ticker_retrieves_stored_data(self):
        """GIVEN records stored for ticker
        WHEN get_latest_by_ticker called
        THEN retrieves recent data

        Principle: Test query methods with actual database
        """
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
2025-12-09,DBS,DBS19,VOLUME,1000000"""

        records = self.parser.parse(csv_data, self.s3_key)
        self.repo.batch_upsert(records)

        # Query by ticker
        results = self.repo.get_latest_by_ticker('DBS19', days=30)

        # Verify
        assert len(results) >= 2, "Should retrieve both records"
        tickers = [r['ticker'] for r in results]
        assert all(t == 'DBS19' for t in tickers)

    def test_get_by_date_range_filters_correctly(self):
        """GIVEN records for date range
        WHEN get_by_date_range called
        THEN filters by dates

        Principle: Test date filtering with actual database
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,CLOSE,38.50"

        records = self.parser.parse(csv_data, self.s3_key)
        self.repo.batch_upsert(records)

        # Query date range
        results = self.repo.get_by_date_range(
            'DBS19',
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 31)
        )

        # Verify
        assert len(results) >= 1
        assert results[0]['d_trade'] == date(2025, 12, 9)

    # =========================================================================
    # Type Conversion Integration Tests
    # =========================================================================

    def test_decimal_precision_preserved_through_pipeline(self):
        """GIVEN high-precision decimal in CSV
        WHEN parsed and stored
        THEN precision preserved (not float rounding)

        Principle: Decimal type prevents precision loss
        """
        csv_data = b"d_trade,stock,ticker,col_code,value\n2025-12-09,DBS,DBS19,PRICE,38.123456"

        records = self.parser.parse(csv_data, self.s3_key)
        assert records[0]['value_numeric'] == Decimal('38.123456')

        self.repo.batch_upsert(records)

        results = self.repo.get_by_s3_source(self.s3_key)
        assert results[0]['value_numeric'] == Decimal('38.123456'), "Precision must be preserved"

    def test_date_format_handling_through_pipeline(self):
        """GIVEN various date formats in CSV
        WHEN parsed and stored
        THEN all formats normalized to date object

        Principle: Type conversion at system boundary
        """
        # Test multiple date formats
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
12/09/2025,DBS,DBS20,CLOSE,39.00
20251209,DBS,DBS21,CLOSE,40.00"""

        records = self.parser.parse(csv_data, self.s3_key)

        # All should parse to same date
        assert all(r['d_trade'] == date(2025, 12, 9) for r in records)

        self.repo.batch_upsert(records)

        results = self.repo.get_by_s3_source(self.s3_key)
        assert len(results) == 3
        assert all(r['d_trade'] == date(2025, 12, 9) for r in results)

    # =========================================================================
    # Batch Performance Tests
    # =========================================================================

    def test_batch_upsert_handles_large_csv(self):
        """GIVEN CSV with 100+ rows
        WHEN batch upserted
        THEN all rows stored efficiently

        Principle: Test batch performance at scale
        """
        # Generate large CSV
        rows = ["d_trade,stock,ticker,col_code,value"]
        for i in range(100):
            rows.append(f"2025-12-09,DBS,DBS{i},CLOSE,{38.50 + i}")

        csv_data = "\n".join(rows).encode('utf-8')

        # Parse and store
        records = self.parser.parse(csv_data, self.s3_key)
        assert len(records) == 100

        rowcount = self.repo.batch_upsert(records, batch_size=50)
        assert rowcount >= 100, "Should insert all 100 records"

        # Verify
        results = self.repo.get_by_s3_source(self.s3_key)
        assert len(results) == 100, "Should retrieve all 100 records"

    # =========================================================================
    # Error Handling Integration Tests
    # =========================================================================

    def test_parser_error_prevents_partial_insert(self):
        """GIVEN CSV with invalid row
        WHEN parsing fails
        THEN no partial data inserted to Aurora

        Principle: Fail fast prevents data corruption
        """
        # CSV with invalid date in row 2
        csv_data = b"""d_trade,stock,ticker,col_code,value
2025-12-09,DBS,DBS19,CLOSE,38.50
INVALID_DATE,DBS,DBS19,VOLUME,1000"""

        # Parser should raise ValueError
        with pytest.raises(ValueError, match="Failed to parse row"):
            records = self.parser.parse(csv_data, self.s3_key)

        # Verify no data inserted
        results = self.repo.get_by_s3_source(self.s3_key)
        assert len(results) == 0, "No partial data should be inserted on parse error"

    def test_repository_validation_prevents_incomplete_data(self):
        """GIVEN record missing required fields
        WHEN batch_upsert called
        THEN raises ValueError before database call

        Principle: Validate at system boundary
        """
        invalid_record = {
            'd_trade': date(2025, 12, 9),
            'ticker': 'DBS19',
            # Missing: stock, col_code, s3_source_key
        }

        with pytest.raises(ValueError, match="missing required fields"):
            self.repo.batch_upsert([invalid_record])

        # No database call should have been made


# =============================================================================
# Schema Contract Integration Tests
# =============================================================================

@pytest.mark.integration
class TestFundDataSchemaContract:
    """Schema contract tests - verify database schema matches expectations.

    Principle: Test cross-service boundary contracts
    """

    def setup_method(self):
        """Set up schema validation."""
        try:
            self.client = get_aurora_client()
        except Exception as e:
            pytest.skip(f"Aurora connection not available: {e}")

    def test_fund_data_table_exists(self):
        """GIVEN migration 003 deployed
        WHEN checking schema
        THEN fund_data table exists

        Principle: Verify infrastructure deployment
        """
        query = """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = 'ticker_data'
              AND TABLE_NAME = 'fund_data'
        """
        result = self.client.fetch_one(query)

        assert result is not None, "fund_data table must exist"
        assert result[0] == 'fund_data'

    def test_fund_data_composite_unique_key_exists(self):
        """GIVEN migration 003 deployed
        WHEN checking indexes
        THEN composite unique key exists

        Principle: Verify idempotency constraint
        """
        query = """
            SHOW INDEX FROM fund_data
            WHERE Key_name = 'uk_fund_data_composite'
        """
        results = self.client.fetch_all(query)

        assert len(results) == 4, "Composite key should have 4 columns"

        # Verify columns in order
        columns = [row[4] for row in results]  # Column_name is 5th field
        assert 'd_trade' in columns
        assert 'stock' in columns
        assert 'ticker' in columns
        assert 'col_code' in columns

    def test_fund_data_column_types_match_expectations(self):
        """GIVEN migration 003 deployed
        WHEN checking column definitions
        THEN types match Python type conversion

        Principle: Type compatibility at system boundary
        """
        query = "DESCRIBE fund_data"
        results = self.client.fetch_all(query)

        columns = {row[0]: row[1] for row in results}  # field: type

        # Verify critical types
        assert 'date' in columns['d_trade'].lower(), "d_trade must be DATE"
        assert 'decimal' in columns['value_numeric'].lower(), "value_numeric must be DECIMAL"
        assert 'text' in columns['value_text'].lower(), "value_text must be TEXT"
        assert 'varchar' in columns['s3_source_key'].lower(), "s3_source_key must be VARCHAR"

    def test_fund_data_indexes_for_query_performance(self):
        """GIVEN migration 003 deployed
        WHEN checking indexes
        THEN performance indexes exist

        Principle: Verify query optimization
        """
        query = "SHOW INDEX FROM fund_data"
        results = self.client.fetch_all(query)

        index_names = {row[2] for row in results}  # Key_name

        # Verify expected indexes
        assert 'PRIMARY' in index_names
        assert 'uk_fund_data_composite' in index_names
        assert 'idx_d_trade' in index_names
        assert 'idx_ticker' in index_names
        assert 'idx_s3_source' in index_names
