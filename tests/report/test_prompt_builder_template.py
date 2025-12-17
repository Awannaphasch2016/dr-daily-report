"""
Unit tests for PromptBuilder template loading functionality.

Verifies that PromptBuilder correctly loads prompts from template files
instead of using hardcoded strings.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.report.prompt_builder import PromptBuilder


class TestPromptBuilderTemplate:
    """Test suite for template loading in PromptBuilder"""

    def test_prompt_builder_loads_template_from_disk(self):
        """Verify PromptBuilder loads template file on initialization"""
        # Initialize with Thai language
        builder = PromptBuilder(language='th')

        # ASSERT: Template loaded from disk
        assert builder.main_prompt_template is not None
        assert len(builder.main_prompt_template) > 0
        assert isinstance(builder.main_prompt_template, str)

        # ASSERT: Template contains required placeholders
        assert "{CONTEXT}" in builder.main_prompt_template
        assert "{NARRATIVE_ELEMENTS}" in builder.main_prompt_template
        assert "{STRATEGY_SECTION}" in builder.main_prompt_template
        assert "{COMPARATIVE_SECTION}" in builder.main_prompt_template
        assert "{PROMPT_STRUCTURE}" in builder.main_prompt_template

    def test_prompt_builder_loads_english_template(self):
        """Verify PromptBuilder can load English template"""
        builder = PromptBuilder(language='en')

        # ASSERT: Template loaded successfully
        assert builder.main_prompt_template is not None
        assert len(builder.main_prompt_template) > 0

        # ASSERT: Contains required placeholders
        assert "{CONTEXT}" in builder.main_prompt_template
        assert "{NARRATIVE_ELEMENTS}" in builder.main_prompt_template

    def test_build_prompt_formats_template_correctly(self):
        """Verify build_prompt() replaces template variables"""
        builder = PromptBuilder(language='th')

        # Build prompt with test data
        prompt = builder.build_prompt(
            context="Test context data",
            uncertainty_score=50.0,
            strategy_performance=None
        )

        # ASSERT: Template variables were replaced
        assert "{CONTEXT}" not in prompt, "CONTEXT placeholder should be replaced"
        assert "Test context data" in prompt, "Context should be injected"
        assert "{NARRATIVE_ELEMENTS}" not in prompt, "NARRATIVE_ELEMENTS should be replaced"
        assert "{STRATEGY_SECTION}" not in prompt, "STRATEGY_SECTION should be replaced"
        assert "{COMPARATIVE_SECTION}" not in prompt, "COMPARATIVE_SECTION should be replaced"
        assert "{PROMPT_STRUCTURE}" not in prompt, "PROMPT_STRUCTURE should be replaced"

        # ASSERT: Final prompt is a valid string
        assert isinstance(prompt, str)
        assert len(prompt) > 1000, "Prompt should be substantial"

    def test_build_prompt_includes_strategy_when_provided(self):
        """Verify strategy section included when strategy_performance provided"""
        builder = PromptBuilder(language='th')

        # Build prompt WITH strategy
        prompt_with_strategy = builder.build_prompt(
            context="Test context",
            uncertainty_score=50.0,
            strategy_performance={'total_return': 10.5}
        )

        # Build prompt WITHOUT strategy
        prompt_without_strategy = builder.build_prompt(
            context="Test context",
            uncertainty_score=50.0,
            strategy_performance=None
        )

        # ASSERT: Strategy section included when provided
        # (Strategy section should add content, making prompt longer)
        assert len(prompt_with_strategy) >= len(prompt_without_strategy)

    def test_template_file_not_found_raises_error(self):
        """Verify FileNotFoundError raised when template missing"""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Main prompt template not found"):
                PromptBuilder(language='invalid_lang')

    def test_template_file_path_correct(self):
        """Verify template loaded from correct path"""
        builder = PromptBuilder(language='th')

        # Calculate expected path
        expected_dir = Path(__file__).parent.parent.parent / "src" / "report" / "prompt_templates" / "th"
        expected_file = expected_dir / "main_prompt.txt"

        # ASSERT: File exists at expected location
        assert expected_file.exists(), f"Template file should exist at {expected_file}"

        # ASSERT: Template matches file content
        with open(expected_file, 'r', encoding='utf-8') as f:
            file_content = f.read()

        assert builder.main_prompt_template == file_content

    def test_template_encoding_utf8(self):
        """Verify template loaded with UTF-8 encoding (for Thai characters)"""
        builder = PromptBuilder(language='th')

        # ASSERT: Thai characters present in template
        # (Thai templates should contain Thai text)
        assert any(ord(char) > 0x0E00 for char in builder.main_prompt_template), \
            "Thai template should contain Thai characters"

    def test_multiple_instances_load_independently(self):
        """Verify multiple PromptBuilder instances load templates independently"""
        builder_th = PromptBuilder(language='th')
        builder_en = PromptBuilder(language='en')

        # ASSERT: Both loaded successfully
        assert builder_th.main_prompt_template is not None
        assert builder_en.main_prompt_template is not None

        # ASSERT: Templates are different (language-specific)
        assert builder_th.main_prompt_template != builder_en.main_prompt_template

    def test_template_cache_in_instance(self):
        """Verify template cached in instance (not reloaded on each build_prompt)"""
        builder = PromptBuilder(language='th')

        # Get template reference
        template_ref_1 = builder.main_prompt_template

        # Build prompt (should not reload template)
        builder.build_prompt(context="test", uncertainty_score=50.0)

        # Get template reference again
        template_ref_2 = builder.main_prompt_template

        # ASSERT: Same template object (cached)
        assert template_ref_1 is template_ref_2, \
            "Template should be cached, not reloaded on each build_prompt()"
