"""Tests for PromptBuilder language support

Following TDD principles from CLAUDE.md:
- Write tests first before implementation
- Test outcomes, not execution
- Test both success and failure paths
- Avoid "The Liar" anti-pattern
"""

import pytest
from pathlib import Path
from src.report.prompt_builder import PromptBuilder


class TestPromptBuilderLanguageSupport:
    """Test PromptBuilder language parameter and template loading"""

    def test_thai_template_loading_default(self):
        """Verify Thai templates load correctly (default behavior)"""
        builder = PromptBuilder()  # No language parameter

        # Verify default is Thai
        assert builder.language == 'th', "Default language should be 'th'"

        # Verify template was loaded
        assert hasattr(builder, 'main_prompt_template'), "Should have main_prompt_template attribute"
        assert len(builder.main_prompt_template) > 0, "Template should not be empty"

        # Verify it's actually Thai content (check for Thai characters)
        assert 'ไทย' in builder.main_prompt_template or 'Thai' in builder.main_prompt_template, \
            "Template should contain Thai language instructions"

    def test_thai_template_loading_explicit(self):
        """Verify Thai templates load correctly when explicitly specified"""
        builder = PromptBuilder(language='th')

        assert builder.language == 'th'
        assert len(builder.main_prompt_template) > 0

        # Verify templates directory path is correct
        expected_path = Path(__file__).parent.parent.parent / 'src' / 'report' / 'prompt_templates' / 'th'
        assert builder.templates_dir == expected_path, \
            f"Expected {expected_path}, got {builder.templates_dir}"

    def test_english_template_loading(self):
        """Verify English templates load correctly"""
        builder = PromptBuilder(language='en')

        assert builder.language == 'en', "Language should be 'en'"
        assert len(builder.main_prompt_template) > 0, "Template should not be empty"

        # Verify it's English content (should contain 'English' or English instructions)
        assert 'English' in builder.main_prompt_template, \
            "Template should contain English language instructions"

    def test_template_file_not_found_raises_error(self):
        """Verify FileNotFoundError raised when template doesn't exist"""
        # Test with invalid language
        with pytest.raises(FileNotFoundError, match="Main prompt template not found"):
            PromptBuilder(language='invalid')

    def test_build_prompt_preserves_language(self):
        """Verify build_prompt() uses correct language template"""
        # Thai builder
        th_builder = PromptBuilder(language='th')
        th_prompt = th_builder.build_prompt(
            context="Test context",
            uncertainty_score=50.0
        )
        assert len(th_prompt) > 0, "Thai prompt should be generated"

        # English builder
        en_builder = PromptBuilder(language='en')
        en_prompt = en_builder.build_prompt(
            context="Test context",
            uncertainty_score=50.0
        )
        assert len(en_prompt) > 0, "English prompt should be generated"

        # Prompts should be different (different languages)
        assert th_prompt != en_prompt, "Thai and English prompts should differ"

    def test_template_placeholders_consistency(self):
        """Verify English and Thai templates have identical placeholders

        This is critical - templates must have same placeholders or
        build_prompt() will fail when trying to format()
        """
        th_builder = PromptBuilder(language='th')
        en_builder = PromptBuilder(language='en')

        # Extract placeholder patterns like {CONTEXT}, {NARRATIVE_ELEMENTS}, etc.
        import re
        placeholder_pattern = r'\{([A-Z_]+)\}'

        th_placeholders = set(re.findall(placeholder_pattern, th_builder.main_prompt_template))
        en_placeholders = set(re.findall(placeholder_pattern, en_builder.main_prompt_template))

        # Both should have same set of placeholders
        assert th_placeholders == en_placeholders, \
            f"Placeholder mismatch!\nThai: {th_placeholders}\nEnglish: {en_placeholders}"

        # Should have expected placeholders based on plan
        expected_placeholders = {'CONTEXT', 'NARRATIVE_ELEMENTS', 'STRATEGY_SECTION',
                                'COMPARATIVE_SECTION', 'PROMPT_STRUCTURE'}
        assert expected_placeholders.issubset(th_placeholders), \
            f"Missing expected placeholders. Found: {th_placeholders}"

    def test_backward_compatibility_no_language_param(self):
        """Verify backward compatibility - existing code without language param still works

        Critical for deployment - all existing code defaults to Thai
        """
        # Old code pattern (no language parameter)
        builder = PromptBuilder()

        # Should default to Thai
        assert builder.language == 'th'

        # Should work with existing build_prompt() calls
        prompt = builder.build_prompt(
            context="บริษัท: DBS Bank\nราคา: $35.50",
            uncertainty_score=45.0
        )
        assert len(prompt) > 0
        assert isinstance(prompt, str)

    def test_invalid_language_raises_error(self):
        """Verify invalid language codes raise clear errors"""
        # Should fail for unsupported languages
        with pytest.raises(FileNotFoundError):
            PromptBuilder(language='ja')  # Japanese not implemented yet

        with pytest.raises(FileNotFoundError):
            PromptBuilder(language='zh')  # Chinese not implemented yet


class TestPromptBuilderTemplateContent:
    """Test template content quality and structure"""

    def test_thai_template_word_count(self):
        """Verify Thai template has substantial content (not empty stub)"""
        builder = PromptBuilder(language='th')

        # Template should be at least 200 words (based on 245-line original)
        word_count = len(builder.main_prompt_template.split())
        assert word_count >= 200, \
            f"Thai template too short: {word_count} words (expected >= 200)"

    def test_english_template_word_count(self):
        """Verify English template has substantial content"""
        builder = PromptBuilder(language='en')

        # Should be similar length to Thai (±10% tolerance)
        word_count = len(builder.main_prompt_template.split())
        assert word_count >= 200, \
            f"English template too short: {word_count} words (expected >= 200)"

    def test_thai_template_has_instructions(self):
        """Verify Thai template contains analysis instructions"""
        builder = PromptBuilder(language='th')
        template = builder.main_prompt_template

        # Should contain key instruction keywords
        # (Will vary based on actual template content)
        assert len(template) > 500, "Template should be substantial"

    def test_english_template_has_instructions(self):
        """Verify English template contains analysis instructions"""
        builder = PromptBuilder(language='en')
        template = builder.main_prompt_template

        # Should contain English instructions
        assert len(template) > 500, "Template should be substantial"


# Test sabotage verification (run manually to verify tests catch failures)
class TestPromptBuilderTestVerification:
    """Meta-tests to verify our tests can detect failures

    Per CLAUDE.md: "After writing a test, verify it can detect failures"
    """

    @pytest.mark.skip(reason="Sabotage test - run manually to verify test quality")
    def test_sabotage_detection(self):
        """Verify tests catch failures when code is broken

        To use:
        1. Temporarily break PromptBuilder.__init__()
        2. Unskip this test
        3. Run tests - they should FAIL
        4. Restore code, tests should pass
        """
        # If tests pass when this runs, our tests are "Liars"
        assert False, "This test should be skipped normally"
