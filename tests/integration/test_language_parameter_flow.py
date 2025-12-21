"""
Simplified integration tests for language parameter flow.

Tests verify that language parameter flows correctly through the system
by testing the key integration points, not the entire workflow.

Approach:
- Test PromptBuilder + ContextBuilder with actual templates (not mocks)
- Verify template loading works for both languages
- Verify backward compatibility (Thai default)
"""

import pytest
from src.report.prompt_builder import PromptBuilder
from src.report.context_builder import ContextBuilder
from unittest.mock import Mock


class TestLanguageParameterIntegration:
    """Integration tests for language parameter flow through services"""

    def test_prompt_builder_loads_thai_template(self):
        """Verify PromptBuilder loads Thai template successfully"""
        builder = PromptBuilder(language='th')
        assert builder.language == 'th'
        assert len(builder.main_prompt_template) > 0, "Thai template should be loaded"
        # Verify it's Thai template (check for "Write in Thai" instruction or Thai examples)
        assert 'Write in Thai' in builder.main_prompt_template or 'เปอร์เซ็นไทล์' in builder.main_prompt_template, \
            "Template should be Thai version (contains 'Write in Thai' or Thai examples)"

    def test_prompt_builder_loads_english_template(self):
        """Verify PromptBuilder loads English template successfully"""
        builder = PromptBuilder(language='en')
        assert builder.language == 'en'
        assert len(builder.main_prompt_template) > 0, "English template should be loaded"
        # Verify it's English content
        assert 'should' in builder.main_prompt_template.lower() or 'analysis' in builder.main_prompt_template.lower(), \
            "Template should contain English text"

    def test_prompt_builder_defaults_to_thai(self):
        """Verify PromptBuilder defaults to Thai for backward compatibility"""
        builder = PromptBuilder()  # No language specified
        assert builder.language == 'th', "Should default to Thai"
        assert len(builder.main_prompt_template) > 0

    def test_prompt_builder_invalid_language_raises_error(self):
        """Verify invalid language raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Main prompt template not found"):
            PromptBuilder(language='invalid')

    def test_context_builder_uses_thai_labels(self):
        """Verify ContextBuilder uses Thai labels"""
        mock_market_analyzer = Mock()
        mock_data_formatter = Mock()
        mock_technical_analyzer = Mock()

        builder = ContextBuilder(
            mock_market_analyzer,
            mock_data_formatter,
            mock_technical_analyzer,
            language='th'
        )
        assert builder.language == 'th'
        assert builder.labels['symbol'] == 'สัญลักษณ์', "Should use Thai label"
        assert builder.labels['company'] == 'บริษัท', "Should use Thai label"

    def test_context_builder_uses_english_labels(self):
        """Verify ContextBuilder uses English labels"""
        mock_market_analyzer = Mock()
        mock_data_formatter = Mock()
        mock_technical_analyzer = Mock()

        builder = ContextBuilder(
            mock_market_analyzer,
            mock_data_formatter,
            mock_technical_analyzer,
            language='en'
        )
        assert builder.language == 'en'
        assert builder.labels['symbol'] == 'Symbol', "Should use English label"
        assert builder.labels['company'] == 'Company', "Should use English label"

    def test_context_builder_defaults_to_thai(self):
        """Verify ContextBuilder defaults to Thai for backward compatibility"""
        mock_market_analyzer = Mock()
        mock_data_formatter = Mock()
        mock_technical_analyzer = Mock()

        builder = ContextBuilder(
            mock_market_analyzer,
            mock_data_formatter,
            mock_technical_analyzer
            # No language specified
        )
        assert builder.language == 'th', "Should default to Thai"
        assert builder.labels['symbol'] == 'สัญลักษณ์'

    def test_context_builder_invalid_language_raises_keyerror(self):
        """Verify invalid language raises KeyError for unsupported language"""
        mock_market_analyzer = Mock()
        mock_data_formatter = Mock()
        mock_technical_analyzer = Mock()

        with pytest.raises(KeyError):
            ContextBuilder(
                mock_market_analyzer,
                mock_data_formatter,
                mock_technical_analyzer,
                language='invalid'
            )
