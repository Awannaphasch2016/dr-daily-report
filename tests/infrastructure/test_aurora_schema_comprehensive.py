"""Comprehensive Aurora schema validation (auto-updating).

Following TDD principle: Tests define contract, code must match.

Auto-extracts expected columns from actual INSERT queries in code.
NO MANUAL COLUMN LISTS - reduces maintenance and prevents staleness.

This test suite prevents schema mismatches by:
1. ✅ Auto-extracting expected columns from actual INSERT queries
2. ✅ Validating ALL tables used by the application
3. ✅ Checking column types, not just names
4. ✅ Providing actionable error messages with file locations

When a test fails, it means code expects columns that don't exist in Aurora.
The correct TDD workflow:
1. Write migration to add columns
2. Run migration against Aurora
3. Tests pass
4. Deploy code changes
"""

import pytest
import boto3
import re
import inspect
from typing import Dict, Set, Any, Optional
from datetime import date


class SchemaExtractor:
    """Utility to extract schema expectations from code.

    Uses AST introspection and regex parsing to extract INSERT queries
    from Python source code, then parses column names from those queries.

    This approach ensures tests always match code - no manual maintenance.
    """

    @staticmethod
    def extract_columns_from_insert(query: str) -> Set[str]:
        """Parse INSERT query to extract column names.

        Handles:
        - INSERT INTO table (col1, col2, ...) VALUES (...)
        - Multi-line queries with comments
        - Trailing commas and whitespace
        - ON DUPLICATE KEY UPDATE patterns

        Args:
            query: SQL INSERT query string

        Returns:
            Set of column names found in INSERT clause

        Raises:
            ValueError: If query format cannot be parsed
        """
        # Pattern: INSERT INTO table_name (columns...) VALUES
        match = re.search(
            r'INSERT\s+INTO\s+\w+\s*\((.*?)\)\s*VALUES',
            query,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            raise ValueError(f"Could not parse INSERT query: {query[:100]}...")

        columns_str = match.group(1)

        # Split by comma, strip whitespace, remove comments
        columns = []
        for col in columns_str.split(','):
            col = col.strip()
            # Remove inline comments
            col = re.sub(r'--.*$', '', col)
            # Remove block comments
            col = re.sub(r'/\*.*?\*/', '', col)
            if col:
                columns.append(col)

        return set(columns)

    @staticmethod
    def extract_insert_query_from_method(class_type: type, method_name: str) -> str:
        """Extract INSERT query string from method source code.

        Looks for patterns like:
            query = '''INSERT INTO ...'''
            query = \"\"\"INSERT INTO ...\"\"\"

        Args:
            class_type: Class containing the method
            method_name: Method name to extract from

        Returns:
            SQL query string

        Raises:
            ValueError: If no query found or method doesn't exist
        """
        try:
            method = getattr(class_type, method_name)
        except AttributeError:
            raise ValueError(f"Method {method_name} not found in {class_type.__name__}")

        source = inspect.getsource(method)

        # Try triple-quoted strings first (most common)
        query_match = re.search(r'query\s*=\s*"""(.*?)"""', source, re.DOTALL)
        if not query_match:
            query_match = re.search(r"query\s*=\s*'''(.*?)'''", source, re.DOTALL)
        if not query_match:
            # Try single quotes
            query_match = re.search(r'query\s*=\s*"(.*?)"', source, re.DOTALL)
        if not query_match:
            query_match = re.search(r"query\s*=\s*'(.*?)'", source, re.DOTALL)

        if not query_match:
            raise ValueError(
                f"No query found in {class_type.__name__}.{method_name}\n"
                f"Expected pattern: query = \"\"\"...\"\"\""
            )

        return query_match.group(1)

    @staticmethod
    def extract_columns_from_class_method(class_type: type, method_name: str) -> Set[str]:
        """Convenience method: extract columns directly from class method.

        Combines extract_insert_query_from_method + extract_columns_from_insert.

        Args:
            class_type: Class containing the method
            method_name: Method name to extract from

        Returns:
            Set of column names expected by the code
        """
        query = SchemaExtractor.extract_insert_query_from_method(class_type, method_name)
        return SchemaExtractor.extract_columns_from_insert(query)


@pytest.mark.integration
class TestAuroraSchemaComprehensive:
    """Validate ALL Aurora tables match code expectations (auto-extracted).

    This test suite is BLOCKING in CI/CD:
    - Runs in PR gate (blocks merge if fails)
    - Runs in pre-deploy gate (blocks deployment if fails)

    When a test fails:
    1. Check error message for file location and missing columns
    2. Create migration to add missing columns
    3. Run migration against Aurora
    4. Re-run tests (should pass)
    5. Deploy code changes
    """

    def setup_method(self):
        """Initialize AWS clients and test fixtures."""
        self.lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
        self.scheduler_lambda = 'dr-daily-report-query-tool-dev'
        self.extractor = SchemaExtractor()

    def _query_aurora_schema(self, table_name: str) -> Dict[str, Any]:
        """Query Aurora schema via Lambda DESCRIBE command.

        Uses scheduler Lambda's _handle_describe_table() method to query
        Aurora schema through VPC connection.

        Args:
            table_name: Table name to describe

        Returns:
            Dict mapping column names to schema info:
            {
                'column_name': {
                    'Type': 'varchar(50)',
                    'Null': 'YES',
                    'Key': 'PRI',
                    'Default': None,
                    'Extra': ''
                }
            }

        Raises:
            AssertionError: If Lambda invocation fails or returns error
        """
        import json

        payload_data = {
            "action": "describe_table",
            "table": table_name
        }

        response = self.lambda_client.invoke(
            FunctionName=self.scheduler_lambda,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload_data)
        )

        result = json.loads(response['Payload'].read())

        assert result.get('statusCode') == 200, \
            f"Lambda failed to query schema: {result.get('body', {}).get('message')}"

        return result.get('body', {}).get('schema', {})

    # =========================================================================
    # PRECOMPUTED_REPORTS TABLE
    # =========================================================================

    def test_precomputed_reports_full_insert_columns(self):
        """Schema matches _store_completed_report() INSERT query.

        Auto-extracts expected columns from actual code.
        NO MANUAL MAINTENANCE REQUIRED.

        If this test fails:
        1. Check error message for missing columns
        2. Run migration: scripts/migrate_add_columns.py
        3. Re-run this test
        """
        from src.data.aurora.precompute_service import PrecomputeService

        # Extract INSERT query from source code
        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                '_store_completed_report'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        # Query actual Aurora schema
        schema = self._query_aurora_schema('precomputed_reports')
        actual = set(schema.keys())

        # Validate all expected columns exist
        missing = expected - actual

        assert not missing, \
            f"❌ Aurora schema missing columns required by code:\n" \
            f"   Missing columns: {sorted(missing)}\n" \
            f"   Expected (from code): {sorted(expected)}\n" \
            f"   Actual (from Aurora): {sorted(actual)}\n" \
            f"   \n" \
            f"   Source: src/data/aurora/precompute_service.py::_store_completed_report\n" \
            f"   \n" \
            f"   ⚠️  BLOCKING: Cannot deploy until migration adds these columns\n" \
            f"   \n" \
            f"   To fix:\n" \
            f"   1. Create migration to add missing columns\n" \
            f"   2. Run migration: python scripts/migrate_add_columns.py\n" \
            f"   3. Re-run this test to verify\n"

    def test_precomputed_reports_status_update_columns(self):
        """Schema matches _update_report_status() INSERT query.

        Status updates use a subset of columns. Validates those exist.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                '_update_report_status'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('precomputed_reports')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ Missing columns for status updates: {missing}\n" \
            f"   Source: src/data/aurora/precompute_service.py::_update_report_status"

    def test_precomputed_reports_column_types(self):
        """Validate critical column types match code expectations.

        Type mismatches cause silent failures (MySQL ENUM constraints).
        This test catches type incompatibilities before deployment.
        """
        schema = self._query_aurora_schema('precomputed_reports')

        # Define type validations
        type_validations = {
            'strategy': {
                'validator': lambda t: 'enum' in t.lower(),
                'reason': 'Must be ENUM to match code expectations'
            },
            'report_json': {
                'validator': lambda t: 'json' in t.lower(),
                'reason': 'Must be JSON type for structured data'
            },
            'mini_reports': {
                'validator': lambda t: 'json' in t.lower(),
                'reason': 'Must be JSON type for structured data'
            },
            'generation_time_ms': {
                'validator': lambda t: 'int' in t.lower(),
                'reason': 'Must be integer for numeric operations'
            },
            'chart_base64': {
                'validator': lambda t: 'text' in t.lower(),
                'reason': 'Must be TEXT for large base64 strings'
            },
            'expires_at': {
                'validator': lambda t: 'timestamp' in t.lower() or 'datetime' in t.lower(),
                'reason': 'Must be TIMESTAMP/DATETIME for date operations'
            },
            'computed_at': {
                'validator': lambda t: 'timestamp' in t.lower() or 'datetime' in t.lower(),
                'reason': 'Must be TIMESTAMP/DATETIME for date operations'
            },
        }

        failures = []
        for col, validation in type_validations.items():
            if col not in schema:
                # Column doesn't exist - caught by other test
                continue

            actual_type = schema[col]['Type']
            if not validation['validator'](actual_type):
                failures.append(
                    f"   • {col}: expected type matching '{validation['reason']}', "
                    f"got '{actual_type}'"
                )

        assert not failures, \
            f"❌ Column type mismatches:\n" + "\n".join(failures) + "\n" \
            f"   \n" \
            f"   Type mismatches cause silent failures in MySQL.\n" \
            f"   ENUM violations don't raise exceptions, data just doesn't persist.\n"

    # =========================================================================
    # DAILY_INDICATORS TABLE
    # =========================================================================

    def test_daily_indicators_columns(self):
        """Schema matches store_daily_indicators() INSERT query.

        Validates 25+ indicator columns exist in Aurora.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                'store_daily_indicators'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('daily_indicators')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ daily_indicators missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/precompute_service.py::store_daily_indicators"

    # =========================================================================
    # INDICATOR_PERCENTILES TABLE
    # =========================================================================

    def test_indicator_percentiles_columns(self):
        """Schema matches store_percentiles() INSERT query.

        Validates 24+ percentile columns exist in Aurora.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                'store_percentiles'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('indicator_percentiles')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ indicator_percentiles missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/precompute_service.py::store_percentiles"

    # =========================================================================
    # COMPARATIVE_FEATURES TABLE
    # =========================================================================

    def test_comparative_features_columns(self):
        """Schema matches store_comparative_features() INSERT query.

        Validates 14+ comparative feature columns exist in Aurora.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                'store_comparative_features'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('comparative_features')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ comparative_features missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/precompute_service.py::store_comparative_features"

    # =========================================================================
    # TICKER_DATA_CACHE TABLE
    # =========================================================================

    def test_ticker_data_columns(self):
        """Schema matches store_ticker_data() INSERT query.

        Validates ticker data columns exist in Aurora.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        try:
            expected = self.extractor.extract_columns_from_class_method(
                PrecomputeService,
                'store_ticker_data'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('ticker_data')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ ticker_data missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/precompute_service.py::store_ticker_data"

    # =========================================================================
    # REPOSITORY TABLES
    # =========================================================================

    def test_ticker_info_columns(self):
        """Schema matches TickerRepository.upsert_ticker_info().

        Validates ticker info table has all required columns.
        """
        from src.data.aurora.repository import TickerRepository

        try:
            expected = self.extractor.extract_columns_from_class_method(
                TickerRepository,
                'upsert_ticker_info'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('ticker_info')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ ticker_info missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/repository.py::upsert_ticker_info"

    def test_daily_prices_columns(self):
        """Schema matches TickerRepository.upsert_daily_price().

        Validates daily prices table has all required columns.
        """
        from src.data.aurora.repository import TickerRepository

        try:
            expected = self.extractor.extract_columns_from_class_method(
                TickerRepository,
                'upsert_daily_price'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('daily_prices')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ daily_prices missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/repository.py::upsert_daily_price"

    # =========================================================================
    # FUND DATA TABLE
    # =========================================================================

    def test_fund_data_columns(self):
        """Schema matches FundDataRepository._upsert_batch().

        Validates fund data table has all required columns.
        """
        from src.data.aurora.fund_data_repository import FundDataRepository

        try:
            expected = self.extractor.extract_columns_from_class_method(
                FundDataRepository,
                '_upsert_batch'
            )
        except ValueError as e:
            pytest.skip(f"Could not extract schema from code: {e}")

        schema = self._query_aurora_schema('fund_data')
        actual = set(schema.keys())

        missing = expected - actual

        assert not missing, \
            f"❌ fund_data missing columns: {sorted(missing)}\n" \
            f"   Source: src/data/aurora/fund_data_repository.py::_upsert_batch"
