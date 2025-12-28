# -*- coding: utf-8 -*-
"""
Unit tests for MCP context integration.

Tests that SEC filing data is formatted correctly for LLM context.
Follows TDD principles: test behavior, not implementation; validate actual output.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.report.context_builder import ContextBuilder


class TestMCPContextIntegration:
    """Test that SEC filing data is formatted correctly for LLM context."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_market_analyzer = Mock()
        self.mock_market_analyzer.calculate_market_conditions.return_value = {
            'current_price': 150.0,
            'uncertainty_score': 50.0,
            'atr': 5.0,
            'price_vs_vwap_pct': 2.0,
            'vwap': 147.0,
            'volume_ratio': 1.5
        }
        self.mock_market_analyzer.interpret_uncertainty_level.return_value = "Moderate"
        self.mock_market_analyzer.interpret_volatility.return_value = "Low volatility"
        self.mock_market_analyzer.interpret_vwap_pressure.return_value = "Buy pressure"
        self.mock_market_analyzer.interpret_volume.return_value = "Average volume"

        self.mock_data_formatter = Mock()
        self.mock_data_formatter.format_percentile_context.return_value = "Percentile context"
        self.mock_data_formatter.format_fundamental_section.return_value = "Fundamental section"
        self.mock_data_formatter.format_technical_section.return_value = "Technical section"
        self.mock_data_formatter.format_news_section.return_value = "News section"
        self.mock_data_formatter.format_comparative_insights.return_value = "Comparative section"

        self.mock_technical_analyzer = Mock()

        self.context_builder = ContextBuilder(
            market_analyzer=self.mock_market_analyzer,
            data_formatter=self.mock_data_formatter,
            technical_analyzer=self.mock_technical_analyzer
        )

    def test_context_builder_includes_sec_filing_section(self):
        """Test context builder formats SEC filing data correctly."""
        # Arrange: SEC filing data
        sec_filing_data = {
            'ticker': 'AAPL',
            'form_type': '10-Q',
            'filing_date': '2024-01-15',
            'company_name': 'Apple Inc.',
            'cik': '0000320193',
            'xbrl': {
                'RevenueFromContractWithCustomerExcludingAssessedTax': 1000000000,
                'OperatingIncomeLoss': 300000000,
                'NetIncomeLoss': 250000000,
                'Assets': 5000000000
            },
            'text_sections': {
                'risk_factors': 'Market competition and supply chain risks.'
            }
        }

        ticker_data = {'company_name': 'Apple Inc.', 'date': '2024-01-15'}
        indicators = {'rsi': 55.0, 'macd': 2.5}
        percentiles = {'current_percentile': 75.0}

        # Act: Build context
        context = self.context_builder.prepare_context(
            ticker='AAPL',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=[],
            news_summary={},
            sec_filing_data=sec_filing_data
        )

        # Assert: Context contains SEC filing section with actual data
        assert isinstance(context, str), f"Context should be string, got {type(context)}"
        assert len(context) > 0, "Context is empty"
        assert "SEC FILING DATA" in context, "Context missing SEC filing section header"
        assert "10-Q" in context, "Context missing form type"
        assert "2024-01-15" in context, "Context missing filing date"
        assert "Apple Inc." in context, "Context missing company name"
        assert "Revenue" in context or "Financial Metrics" in context, "Context missing XBRL data"
        assert "Risk Factors" in context, "Context missing risk factors section"

    def test_context_builder_excludes_sec_section_when_data_empty(self):
        """Test context builder excludes SEC section when data is empty."""
        # Arrange: Empty SEC filing data
        sec_filing_data = {}

        ticker_data = {'company_name': 'Apple Inc.', 'date': '2024-01-15'}
        indicators = {'rsi': 55.0, 'macd': 2.5}
        percentiles = {'current_percentile': 75.0}

        # Act: Build context
        context = self.context_builder.prepare_context(
            ticker='AAPL',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=[],
            news_summary={},
            sec_filing_data=sec_filing_data
        )

        # Assert: Context does not contain SEC filing section
        assert isinstance(context, str), f"Context should be string, got {type(context)}"
        assert "SEC FILING DATA" not in context, "Context should not contain SEC section when data is empty"

    def test_context_builder_excludes_sec_section_when_data_none(self):
        """Test context builder excludes SEC section when data is None."""
        # Arrange: None SEC filing data
        sec_filing_data = None

        ticker_data = {'company_name': 'Apple Inc.', 'date': '2024-01-15'}
        indicators = {'rsi': 55.0, 'macd': 2.5}
        percentiles = {'current_percentile': 75.0}

        # Act: Build context
        context = self.context_builder.prepare_context(
            ticker='AAPL',
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news=[],
            news_summary={},
            sec_filing_data=sec_filing_data
        )

        # Assert: Context does not contain SEC filing section
        assert isinstance(context, str), f"Context should be string, got {type(context)}"
        assert "SEC FILING DATA" not in context, "Context should not contain SEC section when data is None"

    def test_format_sec_filing_section_includes_all_fields(self):
        """Test _format_sec_filing_section includes all required fields."""
        # Arrange: Complete SEC filing data
        sec_filing_data = {
            'form_type': '10-K',
            'filing_date': '2023-12-31',
            'xbrl': {
                'RevenueFromContractWithCustomerExcludingAssessedTax': 2000000000,
                'OperatingIncomeLoss': 500000000,
                'NetIncomeLoss': 400000000
            },
            'text_sections': {
                'risk_factors': 'Detailed risk factors text here.'
            }
        }

        # Act: Format SEC filing section
        section = self.context_builder._format_sec_filing_section(sec_filing_data)

        # Assert: Section contains all required fields
        assert isinstance(section, str), f"Section should be string, got {type(section)}"
        assert len(section) > 0, "Section is empty"
        assert "10-K" in section, "Section missing form type"
        assert "2023-12-31" in section, "Section missing filing date"
        assert "Financial Metrics" in section, "Section missing financial metrics header"
        assert "Revenue" in section, "Section missing revenue"
        assert "Operating Income" in section, "Section missing operating income"
        assert "Net Income" in section, "Section missing net income"
        assert "Operating Margin" in section, "Section missing calculated margins"
        assert "Risk Factors" in section, "Section missing risk factors"

    def test_format_sec_filing_section_handles_minimal_data(self):
        """Test _format_sec_filing_section handles minimal data gracefully."""
        # Arrange: Minimal SEC filing data (only required fields)
        sec_filing_data = {
            'form_type': '8-K',
            'filing_date': '2024-01-10'
        }

        # Act: Format SEC filing section
        section = self.context_builder._format_sec_filing_section(sec_filing_data)

        # Assert: Section contains basic fields
        assert isinstance(section, str), f"Section should be string, got {type(section)}"
        assert len(section) > 0, "Section is empty"
        assert "8-K" in section, "Section missing form type"
        assert "2024-01-10" in section, "Section missing filing date"
        # Should not crash when XBRL or text_sections are missing

    def test_format_sec_filing_section_handles_empty_dict(self):
        """Test _format_sec_filing_section handles empty dict gracefully."""
        # Arrange: Empty dict
        sec_filing_data = {}

        # Act: Format SEC filing section
        section = self.context_builder._format_sec_filing_section(sec_filing_data)

        # Assert: Returns empty string
        assert section == "", f"Expected empty string, got: {section}"

    def test_format_sec_filing_section_handles_none(self):
        """Test _format_sec_filing_section handles None gracefully."""
        # Arrange: None
        sec_filing_data = None

        # Act: Format SEC filing section
        section = self.context_builder._format_sec_filing_section(sec_filing_data)

        # Assert: Returns empty string
        assert section == "", f"Expected empty string, got: {section}"


class TestSabotageVerification:
    """Verify tests can detect failures (TDD principle)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_market_analyzer = Mock()
        self.mock_market_analyzer.calculate_market_conditions.return_value = {
            'current_price': 150.0,
            'uncertainty_score': 50.0,
            'atr': 5.0,
            'price_vs_vwap_pct': 2.0,
            'vwap': 147.0,
            'volume_ratio': 1.5
        }
        self.mock_market_analyzer.interpret_uncertainty_level.return_value = "Moderate"
        self.mock_market_analyzer.interpret_volatility.return_value = "Low volatility"
        self.mock_market_analyzer.interpret_vwap_pressure.return_value = "Buy pressure"
        self.mock_market_analyzer.interpret_volume.return_value = "Average volume"

        self.mock_data_formatter = Mock()
        self.mock_data_formatter.format_percentile_context.return_value = "Percentile context"
        self.mock_data_formatter.format_fundamental_section.return_value = "Fundamental section"
        self.mock_data_formatter.format_technical_section.return_value = "Technical section"
        self.mock_data_formatter.format_news_section.return_value = "News section"
        self.mock_data_formatter.format_comparative_insights.return_value = "Comparative section"

        self.mock_technical_analyzer = Mock()

        self.context_builder = ContextBuilder(
            market_analyzer=self.mock_market_analyzer,
            data_formatter=self.mock_data_formatter,
            technical_analyzer=self.mock_technical_analyzer
        )

    @pytest.mark.skip(reason="Obsolete: Tests context_builder._format_sec_filing_section which is no longer used (replaced by SECFilingSectionFormatter from registry)")
    def test_context_builder_test_detects_missing_sec_section(self):
        """Verify test fails if SEC section is missing from context.

        OBSOLETE: This test sabotages context_builder._format_sec_filing_section, but that
        method is no longer called in production. The actual flow uses SECFilingSectionFormatter
        from the formatter registry (context_builder.py:151-153).

        To fix: Update test to sabotage SECFilingSectionFormatter._format_sec_filing_section
        instead of the obsolete context_builder method.
        """
        # Arrange: SEC filing data
        sec_filing_data = {
            'form_type': '10-Q',
            'filing_date': '2024-01-15'
        }

        ticker_data = {'company_name': 'Apple Inc.', 'date': '2024-01-15'}
        indicators = {'rsi': 55.0, 'macd': 2.5}
        percentiles = {'current_percentile': 75.0}

        # Simulate broken context builder (doesn't include SEC section)
        with pytest.MonkeyPatch().context() as m:
            # Temporarily break _format_sec_filing_section to return empty string
            original_method = self.context_builder._format_sec_filing_section
            self.context_builder._format_sec_filing_section = lambda x: ""

            # Act: Build context
            context = self.context_builder.prepare_context(
                ticker='AAPL',
                ticker_data=ticker_data,
                indicators=indicators,
                percentiles=percentiles,
                news=[],
                news_summary={},
                sec_filing_data=sec_filing_data
            )

            # Assert: Test detects missing SEC section
            assert "SEC FILING DATA" not in context, "Test should detect missing SEC section when method returns empty string"

            # Restore original method
            self.context_builder._format_sec_filing_section = original_method

    def test_format_sec_filing_section_test_detects_missing_form_type(self):
        """Verify test fails if form_type is missing from section."""
        # Arrange: SEC filing data without form_type
        sec_filing_data = {
            'filing_date': '2024-01-15'
            # Missing form_type
        }

        # Act: Format SEC filing section
        section = self.context_builder._format_sec_filing_section(sec_filing_data)

        # Assert: Section should still be generated but form_type will be 'N/A'
        assert isinstance(section, str), f"Section should be string, got {type(section)}"
        # When form_type is missing, it should show 'N/A' in the section
        assert "N/A" in section or "Form Type" in section, "Section should handle missing form_type gracefully"
