# -*- coding: utf-8 -*-
"""
Unit tests for ChartPatternDataRepository (Principle #19: Cross-Boundary Testing)

Tests follow defensive programming principles from CLAUDE.md:
- Test outcomes, not execution
- Explicit failure detection
- Defensive validation
- Type system integration (numpy → primitives)
- Implementation provenance tracking
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.data.aurora.chart_pattern_repository import (
    ChartPatternDataRepository,
    ALLOWED_PATTERN_TYPES,
    ALLOWED_IMPLEMENTATIONS,
    get_chart_pattern_repository,
)


class TestChartPatternDataRepositoryValidation:
    """Tests for defensive validation (Principle #1)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.repo = ChartPatternDataRepository(client=self.mock_client)

        # Sample valid pattern
        self.valid_pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'confidence': 'high',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 1, 10),
            'pattern_data': {
                'points': {
                    'A': {'date': '2026-01-01', 'price': 150.25},
                    'B': {'date': '2026-01-05', 'price': 155.50},
                }
            }
        }

    # =========================================================================
    # Required Fields Validation
    # =========================================================================

    def test_upsert_raises_on_missing_required_fields(self):
        """GIVEN pattern missing required fields
        WHEN upsert called
        THEN raises ValueError with missing field names

        Principle: Fail fast with visibility
        """
        invalid_pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            # Missing: pattern_date, pattern_type, pattern_code,
            #          implementation, impl_version, pattern_data
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert(invalid_pattern)

    def test_upsert_identifies_specific_missing_fields(self):
        """GIVEN pattern with some fields missing
        WHEN validation fails
        THEN error message includes exact missing field names
        """
        partial_pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            # Missing: pattern_code, implementation, impl_version, pattern_data
        }

        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert(partial_pattern)

        error_msg = str(exc_info.value)
        assert 'pattern_code' in error_msg
        assert 'implementation' in error_msg
        assert 'impl_version' in error_msg
        assert 'pattern_data' in error_msg

    # =========================================================================
    # Pattern Type Validation
    # =========================================================================

    def test_upsert_rejects_invalid_pattern_type(self):
        """GIVEN pattern with invalid pattern_type
        WHEN upsert called
        THEN raises ValueError with allowed types

        Principle: Defensive programming - whitelist validation
        """
        invalid_pattern = {**self.valid_pattern, 'pattern_type': 'invalid_pattern'}

        with pytest.raises(ValueError, match="Invalid pattern_type"):
            self.repo.upsert(invalid_pattern)

    def test_upsert_accepts_all_allowed_pattern_types(self):
        """GIVEN each allowed pattern type
        WHEN upsert called
        THEN validation passes (no ValueError)
        """
        self.mock_client.execute.return_value = 1

        for pattern_type in ALLOWED_PATTERN_TYPES:
            test_pattern = {**self.valid_pattern, 'pattern_type': pattern_type}
            # Should not raise
            self.repo.upsert(test_pattern)

    # =========================================================================
    # Implementation Validation
    # =========================================================================

    def test_upsert_rejects_invalid_implementation(self):
        """GIVEN pattern with invalid implementation
        WHEN upsert called
        THEN raises ValueError with allowed implementations
        """
        invalid_pattern = {**self.valid_pattern, 'implementation': 'unknown_detector'}

        with pytest.raises(ValueError, match="Invalid implementation"):
            self.repo.upsert(invalid_pattern)

    def test_upsert_accepts_all_allowed_implementations(self):
        """GIVEN each allowed implementation
        WHEN upsert called
        THEN validation passes
        """
        self.mock_client.execute.return_value = 1

        for implementation in ALLOWED_IMPLEMENTATIONS:
            test_pattern = {**self.valid_pattern, 'implementation': implementation}
            # Should not raise
            self.repo.upsert(test_pattern)


class TestChartPatternDataRepositoryTypeConversion:
    """Tests for type system integration (Principle #4)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.repo = ChartPatternDataRepository(client=self.mock_client)
        self.mock_client.execute.return_value = 1

    def test_upsert_converts_numpy_int64_to_primitive(self):
        """GIVEN pattern_data containing numpy.int64
        WHEN upsert serializes to JSON
        THEN numpy types converted to Python int

        Principle: Type boundary conversion prevents MySQL Error 3140
        """
        pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {
                'points': {'A': {'index': np.int64(42)}}
            }
        }

        self.repo.upsert(pattern)

        # Verify execute was called with JSON that doesn't contain numpy
        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]  # Second arg is params tuple
        json_param = params[10]  # pattern_data is 11th param (0-indexed: 10)

        # Should be valid JSON (no numpy)
        parsed = json.loads(json_param)
        assert parsed['points']['A']['index'] == 42
        assert isinstance(parsed['points']['A']['index'], int)

    def test_upsert_converts_numpy_float64_to_primitive(self):
        """GIVEN pattern_data containing numpy.float64
        WHEN upsert serializes to JSON
        THEN numpy floats converted to Python float
        """
        pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {
                'price': np.float64(150.25),
                'measurements': {'height': np.float64(10.5)}
            }
        }

        self.repo.upsert(pattern)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        json_param = params[10]

        parsed = json.loads(json_param)
        assert parsed['price'] == 150.25
        assert isinstance(parsed['price'], float)

    def test_upsert_converts_numpy_nan_to_null(self):
        """GIVEN pattern_data containing numpy.nan
        WHEN upsert serializes to JSON
        THEN NaN converted to None (JSON null)
        """
        pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {
                'nullable_value': np.nan,
                'inf_value': np.inf
            }
        }

        self.repo.upsert(pattern)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        json_param = params[10]

        parsed = json.loads(json_param)
        assert parsed['nullable_value'] is None
        assert parsed['inf_value'] is None

    def test_upsert_converts_numpy_array_to_list(self):
        """GIVEN pattern_data containing numpy.ndarray
        WHEN upsert serializes to JSON
        THEN array converted to Python list
        """
        pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {
                'prices': np.array([100.0, 101.0, 102.0])
            }
        }

        self.repo.upsert(pattern)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        json_param = params[10]

        parsed = json.loads(json_param)
        assert parsed['prices'] == [100.0, 101.0, 102.0]
        assert isinstance(parsed['prices'], list)


class TestChartPatternDataRepositoryUpsert:
    """Tests for upsert operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.repo = ChartPatternDataRepository(client=self.mock_client)

        self.valid_pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {'points': {}}
        }

    def test_upsert_returns_rowcount_not_boolean(self):
        """GIVEN valid pattern
        WHEN upsert executes
        THEN returns actual rowcount (not boolean/None)

        Principle: Test outcomes (rowcount) not execution
        """
        self.mock_client.execute.return_value = 1

        rowcount = self.repo.upsert(self.valid_pattern)

        assert isinstance(rowcount, int)
        assert rowcount == 1

    def test_upsert_returns_2_on_duplicate_key_update(self):
        """GIVEN duplicate pattern (same unique key)
        WHEN ON DUPLICATE KEY UPDATE executes
        THEN rowcount = 2 (MySQL behavior)
        """
        self.mock_client.execute.return_value = 2  # ON DUPLICATE KEY UPDATE

        rowcount = self.repo.upsert(self.valid_pattern)

        assert rowcount == 2

    def test_upsert_defaults_confidence_to_medium(self):
        """GIVEN pattern without confidence
        WHEN upsert executes
        THEN defaults to 'medium'
        """
        self.mock_client.execute.return_value = 1
        pattern_no_confidence = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {'points': {}}
            # Note: confidence NOT included - should default to 'medium'
        }

        self.repo.upsert(pattern_no_confidence)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        confidence_param = params[7]  # confidence is 8th param
        assert confidence_param == 'medium'


class TestChartPatternDataRepositoryBatchUpsert:
    """Tests for batch upsert operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.repo = ChartPatternDataRepository(client=self.mock_client)

        self.valid_pattern = {
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'pattern_data': {'points': {}}
        }

    def test_batch_upsert_raises_on_empty_list(self):
        """GIVEN empty patterns list
        WHEN batch_upsert called
        THEN raises ValueError (not silent return 0)

        Principle: Explicit failure
        """
        with pytest.raises(ValueError, match="Cannot upsert empty patterns list"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total_rowcount(self):
        """GIVEN multiple patterns
        WHEN batch_upsert executes
        THEN returns sum of all rowcounts
        """
        self.mock_client.execute.return_value = 1  # Each insert = 1

        patterns = [
            {**self.valid_pattern, 'pattern_type': 'bullish_flag'},
            {**self.valid_pattern, 'pattern_type': 'head_shoulders'},
            {**self.valid_pattern, 'pattern_type': 'ascending_wedge'},
        ]

        total = self.repo.batch_upsert(patterns)

        assert total == 3


class TestChartPatternDataRepositoryQuery:
    """Tests for query operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.repo = ChartPatternDataRepository(client=self.mock_client)

    def test_get_patterns_parses_json_pattern_data(self):
        """GIVEN patterns stored with JSON pattern_data
        WHEN fetched
        THEN pattern_data parsed back to dict
        """
        mock_row = {
            'id': 1,
            'ticker_id': 1,
            'symbol': 'AAPL',
            'pattern_date': date(2026, 1, 14),
            'pattern_type': 'bullish_flag',
            'pattern_code': 'FLAGU',
            'implementation': 'custom',
            'impl_version': '1.0.0',
            'confidence': 'high',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 1, 10),
            'pattern_data': '{"points": {"A": {"price": 150.25}}}',  # JSON string
            'detected_at': datetime(2026, 1, 14, 10, 0, 0),
            'created_at': datetime(2026, 1, 14, 10, 0, 0),
            'updated_at': datetime(2026, 1, 14, 10, 0, 0),
        }
        self.mock_client.fetch_all.return_value = [mock_row]

        patterns = self.repo.get_patterns_for_symbol('AAPL', pattern_date=date(2026, 1, 14))

        assert len(patterns) == 1
        assert isinstance(patterns[0]['pattern_data'], dict)
        assert patterns[0]['pattern_data']['points']['A']['price'] == 150.25

    def test_get_patterns_rejects_invalid_implementation_filter(self):
        """GIVEN invalid implementation filter
        WHEN get_patterns_for_symbol called
        THEN raises ValueError
        """
        with pytest.raises(ValueError, match="Invalid implementation"):
            self.repo.get_patterns_for_symbol('AAPL', implementation='unknown')

    def test_get_patterns_rejects_invalid_pattern_type_filter(self):
        """GIVEN invalid pattern_type filter
        WHEN get_patterns_for_symbol called
        THEN raises ValueError
        """
        with pytest.raises(ValueError, match="Invalid pattern_type"):
            self.repo.get_patterns_for_symbol('AAPL', pattern_type='invalid')


class TestChartPatternDataRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        """GIVEN singleton accessor called twice
        WHEN get_chart_pattern_repository called
        THEN returns same instance
        """
        with patch('src.data.aurora.chart_pattern_repository.get_aurora_client'):
            # Reset singleton for test
            import src.data.aurora.chart_pattern_repository as module
            module._repository_instance = None

            repo1 = get_chart_pattern_repository()
            repo2 = get_chart_pattern_repository()

            assert repo1 is repo2


class TestAllowedValuesCompleteness:
    """Meta-tests for allowed values completeness."""

    def test_allowed_pattern_types_includes_common_patterns(self):
        """Verify ALLOWED_PATTERN_TYPES includes expected patterns."""
        expected = {
            'bullish_flag', 'bearish_flag',
            'head_shoulders', 'inverse_head_shoulders',
            'double_top', 'double_bottom',
        }
        assert expected.issubset(ALLOWED_PATTERN_TYPES)

    def test_allowed_implementations_includes_known_detectors(self):
        """Verify ALLOWED_IMPLEMENTATIONS includes project detectors."""
        assert 'stock_pattern' in ALLOWED_IMPLEMENTATIONS
        assert 'custom' in ALLOWED_IMPLEMENTATIONS
