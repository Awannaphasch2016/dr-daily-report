"""Tests for ContextBuilder language support

Following TDD principles from CLAUDE.md:
- Write tests first before implementation
- Test outcomes, not execution
- Test both success and failure paths
"""

import pytest
from unittest.mock import MagicMock
from src.report.context_builder import ContextBuilder


class TestContextBuilderLanguageSupport:
    """Test ContextBuilder language parameter and label translation"""

    def setup_method(self):
        """Setup mock dependencies"""
        self.mock_market_analyzer = MagicMock()
        self.mock_data_formatter = MagicMock()
        self.mock_technical_analyzer = MagicMock()

    def test_thai_labels_default(self):
        """Verify Thai labels are used by default"""
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer
        )

        # Should default to Thai
        assert builder.language == 'th', "Default language should be 'th'"
        assert hasattr(builder, 'labels'), "Should have labels attribute"

        # Verify Thai labels
        assert builder.labels['symbol'] == 'สัญลักษณ์', "Symbol label should be Thai"
        assert builder.labels['company'] == 'บริษัท', "Company label should be Thai"
        assert builder.labels['sector'] == 'ภาคธุรกิจ', "Sector label should be Thai"

    def test_thai_labels_explicit(self):
        """Verify Thai labels when explicitly specified"""
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='th'
        )

        assert builder.language == 'th'
        assert builder.labels['current_price'] == 'ราคาปัจจุบัน'
        assert builder.labels['market_cap'] == 'มูลค่าตลาด'

    def test_english_labels(self):
        """Verify English labels when language='en'"""
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='en'
        )

        assert builder.language == 'en', "Language should be 'en'"

        # Verify English labels
        assert builder.labels['symbol'] == 'Symbol', "Symbol label should be English"
        assert builder.labels['company'] == 'Company', "Company label should be English"
        assert builder.labels['sector'] == 'Sector', "Sector label should be English"
        assert builder.labels['current_price'] == 'Current Price'
        assert builder.labels['market_cap'] == 'Market Cap'

    def test_prepare_context_uses_correct_labels(self):
        """Verify prepare_context() uses correct language labels"""
        # Setup mock data
        ticker_data = {
            'company_name': 'DBS Bank',
            'sector': 'Financial Services',
            'industry': 'Banks',
            'current_price': 35.50
        }

        indicators = {
            'current_price': 35.50,
            'rsi': 65.5,
            'volume': 1000000,
            'volume_sma': 900000,
            'atr': 0.5,
            'vwap': 35.0
        }

        percentiles = {}
        news = []
        news_summary = {}

        # Setup mock return values
        self.mock_market_analyzer.calculate_market_conditions.return_value = {
            'current_price': 35.50,
            'uncertainty_score': 50,
            'atr': 0.5,
            'vwap': 35.0,
            'price_vs_vwap_pct': 1.4,
            'volume_ratio': 1.1
        }
        self.mock_market_analyzer.interpret_uncertainty_level.return_value = "Market is stable"
        self.mock_market_analyzer.interpret_volatility.return_value = "Low volatility"
        self.mock_market_analyzer.interpret_vwap_pressure.return_value = "Buying pressure"
        self.mock_market_analyzer.interpret_volume.return_value = "Normal volume"

        self.mock_data_formatter.format_percentile_context.return_value = ""
        self.mock_data_formatter.format_fundamental_section.return_value = ""
        self.mock_data_formatter.format_technical_section.return_value = ""
        self.mock_data_formatter.format_news_section.return_value = ""
        self.mock_data_formatter.format_comparative_insights.return_value = ""

        # Thai context
        th_builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='th'
        )

        th_context = th_builder.prepare_context(
            ticker='DBS19',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        # Should contain Thai labels
        assert 'สัญลักษณ์' in th_context or 'บริษัท' in th_context, \
            "Thai context should contain Thai labels"

        # English context
        en_builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='en'
        )

        en_context = en_builder.prepare_context(
            ticker='DBS19',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=news,
            news_summary=news_summary
        )

        # Should contain English labels
        assert 'Symbol' in en_context or 'Company' in en_context, \
            "English context should contain English labels"

        # Contexts should be different (different languages)
        assert th_context != en_context, "Thai and English contexts should differ"

    def test_label_consistency_across_languages(self):
        """Verify English and Thai have same label keys (just different translations)"""
        th_builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='th'
        )

        en_builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='en'
        )

        # Should have identical keys
        assert set(th_builder.labels.keys()) == set(en_builder.labels.keys()), \
            "Thai and English should have identical label keys"

    def test_backward_compatibility_no_language_param(self):
        """Verify backward compatibility - existing code without language param still works"""
        # Old code pattern (no language parameter)
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer
        )

        # Should default to Thai
        assert builder.language == 'th'
        assert builder.labels['symbol'] == 'สัญลักษณ์'

    def test_invalid_language_raises_error(self):
        """Verify invalid language codes raise clear errors"""
        # Should fail for unsupported languages
        with pytest.raises(KeyError):
            ContextBuilder(
                self.mock_market_analyzer,
                self.mock_data_formatter,
                self.mock_technical_analyzer,
                language='ja'  # Japanese not implemented yet
            )


class TestContextBuilderLabelContent:
    """Test label content quality and completeness"""

    def setup_method(self):
        """Setup mock dependencies"""
        self.mock_market_analyzer = MagicMock()
        self.mock_data_formatter = MagicMock()
        self.mock_technical_analyzer = MagicMock()

    def test_thai_labels_have_content(self):
        """Verify Thai labels are not empty"""
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='th'
        )

        # All labels should have content
        for key, value in builder.labels.items():
            assert len(value) > 0, f"Thai label '{key}' should not be empty"
            assert isinstance(value, str), f"Thai label '{key}' should be string"

    def test_english_labels_have_content(self):
        """Verify English labels are not empty"""
        builder = ContextBuilder(
            self.mock_market_analyzer,
            self.mock_data_formatter,
            self.mock_technical_analyzer,
            language='en'
        )

        # All labels should have content
        for key, value in builder.labels.items():
            assert len(value) > 0, f"English label '{key}' should not be empty"
            assert isinstance(value, str), f"English label '{key}' should be string"

    def test_required_labels_exist(self):
        """Verify all required labels exist for both languages"""
        required_labels = [
            'symbol', 'company', 'sector', 'industry',
            'market_cap', 'current_price', 'volume',
            'rsi', 'macd', 'uncertainty', 'volatility'
        ]

        for language in ['th', 'en']:
            builder = ContextBuilder(
                self.mock_market_analyzer,
                self.mock_data_formatter,
                self.mock_technical_analyzer,
                language=language
            )

            for label_key in required_labels:
                assert label_key in builder.labels, \
                    f"Required label '{label_key}' missing in {language} labels"
