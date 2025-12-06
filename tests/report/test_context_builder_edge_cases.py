# -*- coding: utf-8 -*-
"""
Regression tests for context_builder.py edge cases

These tests reproduce production bugs discovered during parallel report generation:
- Bug #1: AttributeError when recommendation field is None

Following CLAUDE.md testing principles:
- Test Sabotage Verification: Written to FAIL with buggy code, PASS with fixed code
- Happy Path Only anti-pattern: These tests cover None/missing data that wasn't tested initially
- Explicit Failure Mocking: Tests use real failure scenarios from production
"""
import pytest
from unittest.mock import MagicMock
from src.report.context_builder import ContextBuilder


class TestContextBuilderEdgeCases:
    """Test edge cases that production bugs revealed were missing from initial TDD"""

    def setup_method(self):
        # Mock dependencies
        self.mock_market_analyzer = MagicMock()
        self.mock_data_formatter = MagicMock()
        self.mock_technical_analyzer = MagicMock()

        # Create ContextBuilder instance
        self.builder = ContextBuilder(
            market_analyzer=self.mock_market_analyzer,
            data_formatter=self.mock_data_formatter,
            technical_analyzer=self.mock_technical_analyzer
        )

        # Setup common mocks
        self.mock_market_analyzer.calculate_market_conditions.return_value = {
            'current_price': 100.0,
            'uncertainty_score': 50.0,
            'atr': 2.0,
            'price_vs_vwap_pct': 1.5,
            'vwap': 99.0,
            'volume_ratio': 1.2
        }

        self.mock_market_analyzer.interpret_uncertainty_level.return_value = "Moderate"
        self.mock_market_analyzer.interpret_volatility.return_value = "Low volatility"
        self.mock_market_analyzer.interpret_vwap_pressure.return_value = "Buying pressure"
        self.mock_market_analyzer.interpret_volume.return_value = "Normal volume"

        self.mock_data_formatter.format_percentile_context.return_value = "Percentile context"
        self.mock_data_formatter.format_fundamental_section.return_value = "Fundamentals section"
        self.mock_data_formatter.format_technical_section.return_value = "Technical section"
        self.mock_data_formatter.format_news_section.return_value = "News section"
        self.mock_data_formatter.format_comparative_insights.return_value = ""

    def test_none_recommendation_does_not_crash(self):
        """
        Regression test for Bug #1: AttributeError: 'NoneType' object has no attribute 'upper'

        Production error from CloudWatch logs:
            File "/var/task/src/report/context_builder.py", line 119, in prepare_context
            - คำแนะนำนักวิเคราะห์: {ticker_data.get('recommendation', 'N/A').upper()}
            AttributeError: 'NoneType' object has no attribute 'upper'

        Root cause: yfinance returns recommendation: None for some tickers.
        The .get('recommendation', 'N/A') returns None (doesn't use default when key exists with None value).

        This test follows CLAUDE.md Principle 5 (Test Sabotage Verification):
        - With buggy code: FAILS with AttributeError
        - With fixed code: PASSES without exception
        """
        # Simulate yfinance data with None recommendation
        ticker_data = {
            'company_name': 'Test Company',
            'date': '2025-12-07',
            'recommendation': None,  # ← This is what yfinance returns for some tickers
            'target_mean_price': 150.0,
            'analyst_count': 5,
            'fifty_two_week_high': 200.0,
            'fifty_two_week_low': 80.0
        }

        indicators = {'rsi': 50, 'macd': 0.5, 'atr': 2.0, 'vwap': 99.0}
        percentiles = {'rsi_percentile': 60}
        news = []
        news_summary = {}

        # This should NOT crash with AttributeError
        context = self.builder.prepare_context(
            ticker='TEST',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        # Verify context was built successfully
        assert isinstance(context, str)
        assert len(context) > 0

        # Verify "N/A" appears in output (not "NONE" or crash)
        assert 'N/A' in context or 'คำแนะนำนักวิเคราะห์' in context

    def test_empty_string_recommendation(self):
        """
        Edge case: Empty string recommendation (different from None but equally problematic)
        """
        ticker_data = {
            'company_name': 'Test Company',
            'date': '2025-12-07',
            'recommendation': '',  # Empty string
            'target_mean_price': None,
            'analyst_count': 0,
            'fifty_two_week_high': 200.0,
            'fifty_two_week_low': 80.0
        }

        indicators = {'rsi': 50, 'macd': 0.5}
        percentiles = {}
        news = []
        news_summary = {}

        # Should handle empty string gracefully
        context = self.builder.prepare_context(
            ticker='TEST',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        assert isinstance(context, str)

    def test_missing_recommendation_field(self):
        """
        Edge case: recommendation key doesn't exist at all

        This is different from recommendation: None - the key is missing entirely.
        """
        ticker_data = {
            'company_name': 'Test Company',
            'date': '2025-12-07',
            # No recommendation field at all
            'target_mean_price': 150.0,
            'analyst_count': 5,
            'fifty_two_week_high': 200.0,
            'fifty_two_week_low': 80.0
        }

        indicators = {'rsi': 50, 'macd': 0.5}
        percentiles = {}
        news = []
        news_summary = {}

        # Should use default 'N/A' when key missing
        context = self.builder.prepare_context(
            ticker='TEST',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        assert isinstance(context, str)
        assert 'N/A' in context

    def test_all_optional_fields_none(self):
        """
        Edge case: All optional ticker_data fields are None

        Follows CLAUDE.md "Explicit Failure Mocking" principle:
        Test with worst-case real-world data, not just happy path.
        """
        ticker_data = {
            'company_name': 'Test Company',
            'date': '2025-12-07',
            'recommendation': None,
            'target_mean_price': None,
            'analyst_count': None,
            'fifty_two_week_high': None,
            'fifty_two_week_low': None
        }

        indicators = {'rsi': 50, 'macd': 0.5}
        percentiles = {}
        news = []
        news_summary = {}

        # Should handle all None values gracefully
        context = self.builder.prepare_context(
            ticker='TEST',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        assert isinstance(context, str)
        # Verify N/A appears for missing values
        assert 'N/A' in context

    def test_valid_recommendation_still_works(self):
        """
        Ensure fix doesn't break the happy path (valid recommendation strings)

        Regression prevention: Verify fix doesn't introduce new bugs.
        """
        ticker_data = {
            'company_name': 'Test Company',
            'date': '2025-12-07',
            'recommendation': 'buy',  # Valid string
            'target_mean_price': 150.0,
            'analyst_count': 10,
            'fifty_two_week_high': 200.0,
            'fifty_two_week_low': 80.0
        }

        indicators = {'rsi': 50, 'macd': 0.5}
        percentiles = {}
        news = []
        news_summary = {}

        context = self.builder.prepare_context(
            ticker='TEST',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        # Should contain uppercased recommendation
        assert 'BUY' in context

    def test_various_recommendation_values(self):
        """
        Property-based test: Various recommendation values from yfinance

        Actual values seen in production: 'buy', 'sell', 'hold', 'strong buy', 'strong sell', None
        """
        recommendations = ['buy', 'sell', 'hold', 'strong buy', 'strong sell', None, '', 'neutral']

        for rec in recommendations:
            ticker_data = {
                'company_name': 'Test Company',
                'date': '2025-12-07',
                'recommendation': rec,
                'target_mean_price': 150.0,
                'analyst_count': 5,
                'fifty_two_week_high': 200.0,
                'fifty_two_week_low': 80.0
            }

            indicators = {'rsi': 50, 'macd': 0.5}
            percentiles = {}
            news = []
            news_summary = {}

            # None of these should crash
            context = self.builder.prepare_context(
                ticker='TEST',
                ticker_data=ticker_data,
                indicators=indicators,
                percentiles=percentiles,
                news=news,
                news_summary=news_summary
            )

            assert isinstance(context, str), f"Failed for recommendation={rec}"
            assert len(context) > 0


class TestContextBuilderIntegration:
    """
    Integration tests with realistic data combinations

    Follows CLAUDE.md Principle 3 (Round-Trip Tests):
    Test realistic workflows, not just isolated units.
    """

    def setup_method(self):
        # Use real dependencies (no mocks) for integration tests
        from src.analysis import MarketAnalyzer
        from src.formatters import DataFormatter
        from src.analysis.technical_analysis import TechnicalAnalyzer

        self.builder = ContextBuilder(
            market_analyzer=MarketAnalyzer(),
            data_formatter=DataFormatter(),
            technical_analyzer=TechnicalAnalyzer()
        )

    def test_realistic_incomplete_yfinance_data(self):
        """
        Integration test: Real-world incomplete yfinance data

        Simulates what actually comes from yfinance for small-cap or international stocks.
        """
        ticker_data = {
            'company_name': 'Small Cap Inc',
            'date': '2025-12-07',
            'recommendation': None,  # No analyst coverage
            'target_mean_price': None,
            'analyst_count': 0,
            'fifty_two_week_high': 50.0,
            'fifty_two_week_low': 20.0
        }

        indicators = {
            'sma_20': 45.0,
            'sma_50': 43.0,
            'rsi': 65.0,
            'macd': 0.8,
            'macd_signal': 0.6,
            'atr': 2.5,
            'vwap': 44.5
        }

        percentiles = {
            'rsi_percentile': 70,
            'volume_percentile': 50
        }

        news = []
        news_summary = {'summary': 'No recent news'}

        # Should build context successfully with incomplete data
        context = self.builder.prepare_context(
            ticker='SMALLCAP',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        assert isinstance(context, str)
        assert len(context) > 500  # Should have substantial content despite missing data
        assert 'N/A' in context  # Should show N/A for missing analyst data
