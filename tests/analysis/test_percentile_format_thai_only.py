"""
Test percentile formatting for Thai-only reports.

Since we removed English report support, format_percentile_analysis()
should always return empty string regardless of input.
"""

import pytest
from src.analysis.technical_analysis import TechnicalAnalyzer


class TestPercentileFormatThaiOnly:
    """Test that percentile formatting always returns empty for Thai reports"""

    def setup_method(self):
        """Initialize TechnicalAnalyzer before each test"""
        self.analyzer = TechnicalAnalyzer()

    def test_format_percentile_analysis_returns_empty_with_data(self):
        """Test that percentile analysis returns empty string even with valid data"""
        percentiles = {
            'rsi': {
                'current_value': 65.3,
                'percentile': 75.2,
                'mean': 50.0,
                'frequency_above_70': 15.0
            },
            'macd': {
                'current_value': 0.0234,
                'percentile': 60.0,
                'mean': 0.0,
                'frequency_positive': 55.0
            }
        }

        result = self.analyzer.format_percentile_analysis(percentiles)

        assert result == "", "Thai reports should not show percentile section"

    def test_format_percentile_analysis_returns_empty_with_english_language(self):
        """Test that percentile analysis always returns empty (no language parameter)"""
        percentiles = {
            'rsi': {
                'current_value': 65.3,
                'percentile': 75.2
            }
        }

        result = self.analyzer.format_percentile_analysis(percentiles)

        assert result == "", "Percentile section not shown in reports"

    def test_format_percentile_analysis_returns_empty_with_none(self):
        """Test that passing None returns empty string"""
        result = self.analyzer.format_percentile_analysis(None)

        assert result == "", "Should return empty when percentiles is None"

    def test_format_percentile_analysis_returns_empty_with_empty_dict(self):
        """Test that passing empty dict returns empty string"""
        result = self.analyzer.format_percentile_analysis({})

        assert result == "", "Should return empty when percentiles is empty dict"

    def test_format_percentile_analysis_default_parameters(self):
        """Test that default parameters work (both optional)"""
        result = self.analyzer.format_percentile_analysis()

        assert result == "", "Should work with default parameters"
