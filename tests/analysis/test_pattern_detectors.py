# -*- coding: utf-8 -*-
"""
Pattern Detector Tests - Basic Verification

Verifies refactoring completed successfully:
- Pattern detectors can be imported
- Defensive validation works (fail fast on invalid data)
- Pattern detection returns expected structure
- Constants used (not hardcoded strings)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.analysis.pattern_detectors import (
    ChartPatternDetector,
    CandlestickPatternDetector,
    SupportResistanceDetector,
)
from src.analysis.pattern_types import (
    PATTERN_HEAD_AND_SHOULDERS,
    PATTERN_TRIANGLE,
    PATTERN_DOUBLE_TOP,
    PATTERN_DOUBLE_BOTTOM,
    PATTERN_FLAG_PENNANT,
    PATTERN_WEDGE_RISING,
    PATTERN_WEDGE_FALLING,
    PATTERN_DOJI,
    PATTERN_HAMMER,
    PATTERN_SHOOTING_STAR,
    PATTERN_ENGULFING_BULLISH,
    PATTERN_ENGULFING_BEARISH,
    PATTERN_THREE_LINE_STRIKE,
    PATTERN_TYPE_BULLISH,
    PATTERN_TYPE_BEARISH,
    PATTERN_TYPE_NEUTRAL,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)


@pytest.fixture
def sample_ohlc_data():
    """Create sample OHLC data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    np.random.seed(42)

    open_prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
    high_prices = open_prices + np.abs(np.random.randn(50) * 2)
    low_prices = open_prices - np.abs(np.random.randn(50) * 2)
    close_prices = open_prices + np.random.randn(50) * 1.5
    volumes = np.random.randint(1000000, 5000000, size=50)

    return pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volumes
    }, index=dates)


class TestChartPatternDetector:
    """Test chart pattern detection (head & shoulders, triangles, double tops/bottoms, flags/pennants)."""

    def test_detector_initialization(self):
        """Test detector can be instantiated."""
        detector = ChartPatternDetector()
        assert detector is not None

    def test_defensive_validation_empty_dataframe(self):
        """Test fail-fast on empty DataFrame (Principle #1)."""
        detector = ChartPatternDetector()
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Cannot detect patterns on empty DataFrame"):
            detector.detect(empty_df)

    def test_defensive_validation_missing_columns(self):
        """Test fail-fast on missing OHLC columns (Principle #1)."""
        detector = ChartPatternDetector()
        invalid_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'Close': [101, 102, 103]
            # Missing High, Low
        })

        with pytest.raises(ValueError, match="Missing required OHLC columns"):
            detector.detect(invalid_df)

    def test_detect_returns_list(self, sample_ohlc_data):
        """Test detect() returns list of patterns."""
        detector = ChartPatternDetector()
        patterns = detector.detect(sample_ohlc_data)

        assert isinstance(patterns, list)

    def test_pattern_structure_uses_constants(self, sample_ohlc_data):
        """Test patterns use constants from pattern_types.py (Principle #14)."""
        detector = ChartPatternDetector()
        patterns = detector.detect(sample_ohlc_data)

        if patterns:
            # Verify pattern dict structure
            pattern = patterns[0]
            assert 'pattern' in pattern
            assert 'type' in pattern
            assert 'confidence' in pattern

            # Verify using constants (not hardcoded strings)
            assert pattern['pattern'] in [
                PATTERN_HEAD_AND_SHOULDERS,
                PATTERN_TRIANGLE,
                PATTERN_DOUBLE_TOP,
                PATTERN_DOUBLE_BOTTOM,
                PATTERN_FLAG_PENNANT,
            ]

            assert pattern['type'] in [
                PATTERN_TYPE_BULLISH,
                PATTERN_TYPE_BEARISH,
                PATTERN_TYPE_NEUTRAL,
                'ascending_triangle',  # Triangle subtypes
                'descending_triangle',
                'symmetrical_triangle',
            ]

            assert pattern['confidence'] in [
                CONFIDENCE_HIGH,
                CONFIDENCE_MEDIUM,
                CONFIDENCE_LOW,
            ]


class TestCandlestickPatternDetector:
    """Test candlestick pattern detection (doji, hammer, engulfing, etc.)."""

    def test_detector_initialization(self):
        """Test detector can be instantiated."""
        detector = CandlestickPatternDetector()
        assert detector is not None

    def test_defensive_validation_insufficient_data(self):
        """Test fail-fast on insufficient data (need at least 2 rows)."""
        detector = CandlestickPatternDetector()
        single_row = pd.DataFrame({
            'Open': [100],
            'High': [102],
            'Low': [99],
            'Close': [101]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            detector.detect(single_row)

    def test_detect_returns_list(self, sample_ohlc_data):
        """Test detect() returns list of patterns."""
        detector = CandlestickPatternDetector()
        patterns = detector.detect(sample_ohlc_data)

        assert isinstance(patterns, list)
        assert len(patterns) <= 10  # Returns top 10

    def test_pattern_structure_uses_constants(self, sample_ohlc_data):
        """Test patterns use constants from pattern_types.py."""
        detector = CandlestickPatternDetector()
        patterns = detector.detect(sample_ohlc_data)

        if patterns:
            pattern = patterns[0]
            assert 'pattern' in pattern
            assert 'type' in pattern
            assert 'date' in pattern
            assert 'confidence' in pattern

            # Verify using constants
            assert pattern['pattern'] in [
                PATTERN_DOJI,
                PATTERN_HAMMER,
                PATTERN_SHOOTING_STAR,
                PATTERN_ENGULFING_BULLISH,
                PATTERN_ENGULFING_BEARISH,
                PATTERN_THREE_LINE_STRIKE,
            ]


class TestSupportResistanceDetector:
    """Test support/resistance level calculation."""

    def test_detector_initialization(self):
        """Test detector can be instantiated with custom window."""
        detector = SupportResistanceDetector(window=15)
        assert detector is not None
        assert detector.window == 15

    def test_calculate_levels_returns_dict(self, sample_ohlc_data):
        """Test calculate_levels() returns dict with expected structure."""
        detector = SupportResistanceDetector()
        levels = detector.calculate_levels(sample_ohlc_data, num_levels=3)

        assert isinstance(levels, dict)
        assert 'support' in levels
        assert 'resistance' in levels
        assert 'current_price' in levels

        # Verify support/resistance are lists of floats
        assert isinstance(levels['support'], list)
        assert isinstance(levels['resistance'], list)
        assert len(levels['support']) <= 3
        assert len(levels['resistance']) <= 3

        # Verify current price is float
        assert isinstance(levels['current_price'], float)

    def test_defensive_validation_insufficient_data(self):
        """Test fail-fast on insufficient data (need at least 20 rows)."""
        detector = SupportResistanceDetector()
        small_df = pd.DataFrame({
            'Open': [100, 101],
            'High': [102, 103],
            'Low': [99, 100],
            'Close': [101, 102]
        })

        with pytest.raises(ValueError, match="Insufficient data"):
            detector.calculate_levels(small_df)

    def test_levels_with_strength(self, sample_ohlc_data):
        """Test calculate_levels_with_strength() returns strength indicators."""
        detector = SupportResistanceDetector()
        levels = detector.calculate_levels_with_strength(sample_ohlc_data, num_levels=2)

        assert isinstance(levels, dict)
        assert 'support' in levels
        assert 'resistance' in levels

        # Verify support/resistance have strength information
        if levels['support']:
            support_level = levels['support'][0]
            assert 'level' in support_level
            assert 'strength' in support_level
            assert 'touches' in support_level
            assert support_level['strength'] in ['strong', 'medium', 'weak']


class TestWedgePatterns:
    """Test wedge pattern detection (rising and falling wedges)."""

    def test_detect_wedges_returns_list(self, sample_ohlc_data):
        """Test wedge detection returns list."""
        detector = ChartPatternDetector()
        wedges = detector.detect_wedges(sample_ohlc_data)

        assert isinstance(wedges, list)
        assert len(wedges) <= 5  # Returns top 5

    def test_wedge_pattern_structure(self, sample_ohlc_data):
        """Test wedge patterns use constants and have correct structure."""
        detector = ChartPatternDetector()
        wedges = detector.detect_wedges(sample_ohlc_data)

        if wedges:
            wedge = wedges[0]

            # Verify constants used (Principle #14)
            assert wedge['pattern'] in [
                PATTERN_WEDGE_RISING,
                PATTERN_WEDGE_FALLING
            ]

            assert wedge['type'] in [
                PATTERN_TYPE_BULLISH,  # Falling wedge
                PATTERN_TYPE_BEARISH   # Rising wedge
            ]

            # Verify wedge-specific fields
            assert 'resistance_slope' in wedge
            assert 'support_slope' in wedge
            assert 'convergence_ratio' in wedge
            assert 'start_spread' in wedge
            assert 'end_spread' in wedge
            assert 'start_date' in wedge
            assert 'end_date' in wedge
            assert 'confidence' in wedge

            # Verify slope relationship
            if wedge['pattern'] == PATTERN_WEDGE_RISING:
                # Rising wedge: both ascending, support steeper
                assert wedge['support_slope'] > wedge['resistance_slope']
                assert wedge['resistance_slope'] > 0
                assert wedge['support_slope'] > 0
                assert wedge['type'] == PATTERN_TYPE_BEARISH
            elif wedge['pattern'] == PATTERN_WEDGE_FALLING:
                # Falling wedge: both descending, resistance steeper
                assert wedge['resistance_slope'] < wedge['support_slope']
                assert wedge['resistance_slope'] < 0
                assert wedge['support_slope'] < 0
                assert wedge['type'] == PATTERN_TYPE_BULLISH

            # Verify convergence (lines getting closer)
            assert wedge['convergence_ratio'] < 1.0
            assert wedge['end_spread'] < wedge['start_spread']

    def test_wedge_minimum_data_validation(self):
        """Test wedge detection fails fast on insufficient data (Principle #1)."""
        detector = ChartPatternDetector()
        small_df = pd.DataFrame({
            'Open': [100] * 10,
            'High': [102] * 10,
            'Low': [99] * 10,
            'Close': [101] * 10
        }, index=pd.date_range('2024-01-01', periods=10))

        with pytest.raises(ValueError, match="Insufficient data for.*wedge"):
            detector.detect_wedges(small_df)

    def test_wedge_included_in_main_detect(self, sample_ohlc_data):
        """Test wedges included in main detect() method."""
        detector = ChartPatternDetector()
        all_patterns = detector.detect(sample_ohlc_data)

        # Verify wedges can be in results
        wedge_patterns = [
            p for p in all_patterns
            if p['pattern'] in [PATTERN_WEDGE_RISING, PATTERN_WEDGE_FALLING]
        ]

        # May or may not find wedges in random data, but shouldn't error
        assert isinstance(wedge_patterns, list)

    def test_wedge_defensive_checks(self):
        """Test wedge detection handles edge cases defensively."""
        detector = ChartPatternDetector()

        # Create data with zero slope (flat prices)
        flat_df = pd.DataFrame({
            'Open': [100] * 50,
            'High': [100] * 50,
            'Low': [100] * 50,
            'Close': [100] * 50
        }, index=pd.date_range('2024-01-01', periods=50))

        # Should not error, just return empty list
        wedges = detector.detect_wedges(flat_df)
        assert isinstance(wedges, list)
        assert len(wedges) == 0  # No wedges in flat data


class TestMCPServerIntegration:
    """Test MCP server can use refactored pattern detectors."""

    def test_import_mcp_handler(self):
        """Test MCP handler can be imported (verifies no circular imports)."""
        from src.mcp_servers.financial_markets_handler import FinancialMarketsAnalyzer

        analyzer = FinancialMarketsAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, 'chart_detector')
        assert hasattr(analyzer, 'candlestick_detector')
        assert hasattr(analyzer, 'sr_detector')

    def test_mcp_analyzer_pattern_detection(self, sample_ohlc_data):
        """Test MCP analyzer delegates to core modules."""
        from src.mcp_servers.financial_markets_handler import FinancialMarketsAnalyzer

        analyzer = FinancialMarketsAnalyzer()

        # Test chart patterns
        chart_patterns = analyzer.detect_head_and_shoulders(sample_ohlc_data)
        assert isinstance(chart_patterns, list)

        triangles = analyzer.detect_triangles(sample_ohlc_data)
        assert isinstance(triangles, list)

        double_tops = analyzer.detect_double_tops_bottoms(sample_ohlc_data)
        assert isinstance(double_tops, list)

        flags = analyzer.detect_flags_pennants(sample_ohlc_data)
        assert isinstance(flags, list)

        # Test candlestick patterns
        candle_patterns = analyzer.detect_candlestick_patterns(sample_ohlc_data)
        assert isinstance(candle_patterns, list)

        # Test support/resistance
        levels = analyzer.calculate_support_resistance(sample_ohlc_data, num_levels=3)
        assert isinstance(levels, dict)
        assert 'support' in levels
        assert 'resistance' in levels
