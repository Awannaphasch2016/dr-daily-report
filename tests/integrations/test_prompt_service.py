# -*- coding: utf-8 -*-
"""Tests for PromptService - Langfuse prompt management integration.

Tests the Langfuse prompt fetch with file fallback per invariant requirements.
Follows Principle #10 (Testing Anti-Patterns): No external calls, deterministic data.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.integrations.prompt_service import (
    PromptService,
    PromptResult,
    get_prompt_service,
    PROMPT_FILE_MAPPING,
)


class TestPromptResult:
    """Tests for PromptResult dataclass."""

    def test_prompt_result_creation(self):
        """PromptResult can be created with all fields."""
        result = PromptResult(
            content="Test prompt",
            source="langfuse",
            name="test-prompt",
            version="1",
            variables=["ticker", "context"]
        )
        assert result.content == "Test prompt"
        assert result.source == "langfuse"
        assert result.name == "test-prompt"
        assert result.version == "1"
        assert result.variables == ["ticker", "context"]


class TestPromptServiceFileFallback:
    """Tests for PromptService file fallback behavior.

    Invariant: File fallback always works when Langfuse disabled.
    """

    @pytest.fixture
    def service_with_langfuse_disabled(self, tmp_path):
        """Create PromptService with Langfuse disabled and temp prompt file."""
        # Create temp prompt file
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "main_prompt_v4_minimal.txt"
        prompt_file.write_text("Test prompt for {TICKER}")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "false"}):
            service = PromptService(prompts_base_path=tmp_path)
            yield service

    def test_fallback_to_file_when_langfuse_disabled(self, service_with_langfuse_disabled):
        """When Langfuse disabled, loads from file."""
        result = service_with_langfuse_disabled.get_prompt("report-generation")
        assert result.source == "file"
        assert result.version == "file"
        assert "Test prompt" in result.content

    def test_file_fallback_returns_valid_content(self, service_with_langfuse_disabled):
        """File fallback returns prompt content."""
        result = service_with_langfuse_disabled.get_prompt("report-generation")
        assert len(result.content) > 0
        assert result.name == "report-generation"

    def test_unknown_prompt_raises_error(self, service_with_langfuse_disabled):
        """Unknown prompt name raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            service_with_langfuse_disabled.get_prompt("unknown-prompt")
        assert "Unknown prompt name" in str(exc_info.value)


class TestPromptServiceLangfuseIntegration:
    """Tests for PromptService Langfuse integration.

    Invariant: Langfuse fetch works when enabled and configured.
    """

    @pytest.fixture
    def mock_langfuse_client(self):
        """Mock Langfuse client for testing."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = "Langfuse prompt content"
        mock_prompt.version = 5
        mock_prompt.config = {"variables": ["ticker"]}

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        return mock_client, mock_prompt

    def test_fetches_from_langfuse_when_enabled(self, mock_langfuse_client, tmp_path):
        """When Langfuse enabled, fetches from Langfuse first."""
        mock_client, mock_prompt = mock_langfuse_client

        # Create fallback file
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Fallback")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true", "ENVIRONMENT": "dev"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                result = service.get_prompt("report-generation")

        assert result.source == "langfuse"
        assert result.version == "5"
        assert result.content == "Langfuse prompt content"

    def test_falls_back_to_file_when_langfuse_fails(self, tmp_path):
        """Falls back to file when Langfuse fetch fails."""
        # Create fallback file
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Fallback prompt")

        mock_client = MagicMock()
        mock_client.get_prompt.side_effect = Exception("Langfuse API error")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                result = service.get_prompt("report-generation")

        assert result.source == "file"
        assert result.content == "Fallback prompt"

    def test_falls_back_when_langfuse_not_configured(self, tmp_path):
        """Falls back to file when Langfuse client is None."""
        # Create fallback file
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Fallback")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=None):
                service = PromptService(prompts_base_path=tmp_path)
                result = service.get_prompt("report-generation")

        assert result.source == "file"


class TestPromptServiceVersionTracking:
    """Tests for prompt version tracking.

    Invariant: Version metadata available for all prompts.
    """

    def test_file_prompt_has_version_file(self, tmp_path):
        """File-based prompts have version='file'."""
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Test")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "false"}):
            service = PromptService(prompts_base_path=tmp_path)
            result = service.get_prompt("report-generation")

        assert result.version == "file"

    def test_langfuse_prompt_has_numeric_version(self, tmp_path):
        """Langfuse prompts have numeric version."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = "Content"
        mock_prompt.version = 42
        mock_prompt.config = {}

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        # Create fallback
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Fallback")

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                result = service.get_prompt("report-generation")

        assert result.version == "42"


class TestPromptServiceCompilation:
    """Tests for prompt compilation with variables."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create PromptService with test prompt."""
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text(
            "Report for {TICKER}\nContext: {CONTEXT}"
        )

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "false"}):
            return PromptService(prompts_base_path=tmp_path)

    def test_compile_substitutes_variables(self, service):
        """compile_prompt substitutes variables correctly."""
        result = service.get_prompt("report-generation")
        compiled, metadata = service.compile_prompt(
            result,
            TICKER="ADVANC",
            CONTEXT="Market data here"
        )

        assert "ADVANC" in compiled
        assert "Market data here" in compiled

    def test_compile_returns_metadata(self, service):
        """compile_prompt returns metadata for tracing."""
        result = service.get_prompt("report-generation")
        compiled, metadata = service.compile_prompt(result, TICKER="TEST", CONTEXT="ctx")

        assert "prompt_name" in metadata
        assert "prompt_version" in metadata
        assert "prompt_source" in metadata
        assert metadata["prompt_name"] == "report-generation"

    def test_compile_handles_missing_variable(self, service):
        """compile_prompt handles missing variables gracefully."""
        result = service.get_prompt("report-generation")
        # Missing CONTEXT variable
        compiled, metadata = service.compile_prompt(result, TICKER="TEST")

        # Should not crash, returns uncompiled content
        assert "prompt_name" in metadata


class TestPromptServiceEnvironmentMapping:
    """Tests for environment to Langfuse label mapping."""

    @pytest.fixture
    def mock_langfuse_setup(self, tmp_path):
        """Setup for testing environment mapping."""
        prompt_dir = tmp_path / "prompt_templates" / "th" / "single-stage"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "main_prompt_v4_minimal.txt").write_text("Test")

        mock_prompt = MagicMock()
        mock_prompt.prompt = "Content"
        mock_prompt.version = 1
        mock_prompt.config = {}

        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt

        return tmp_path, mock_client

    def test_dev_environment_uses_development_label(self, mock_langfuse_setup):
        """dev environment maps to 'development' label."""
        tmp_path, mock_client = mock_langfuse_setup

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true", "ENVIRONMENT": "dev"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                service.get_prompt("report-generation")

        mock_client.get_prompt.assert_called_once()
        call_kwargs = mock_client.get_prompt.call_args[1]
        assert call_kwargs["label"] == "development"

    def test_prod_environment_uses_production_label(self, mock_langfuse_setup):
        """prod environment maps to 'production' label."""
        tmp_path, mock_client = mock_langfuse_setup

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true", "ENVIRONMENT": "prod"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                service.get_prompt("report-generation")

        call_kwargs = mock_client.get_prompt.call_args[1]
        assert call_kwargs["label"] == "production"

    def test_staging_environment_uses_staging_label(self, mock_langfuse_setup):
        """staging environment maps to 'staging' label."""
        tmp_path, mock_client = mock_langfuse_setup

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "true", "ENVIRONMENT": "staging"}):
            with patch("src.integrations.prompt_service.get_langfuse_client", return_value=mock_client):
                service = PromptService(prompts_base_path=tmp_path)
                service.get_prompt("report-generation")

        call_kwargs = mock_client.get_prompt.call_args[1]
        assert call_kwargs["label"] == "staging"


class TestPromptServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_prompt_service_returns_same_instance(self):
        """get_prompt_service returns singleton."""
        # Clear singleton
        import src.integrations.prompt_service as ps
        ps._prompt_service = None

        with patch.dict("os.environ", {"LANGFUSE_PROMPTS_ENABLED": "false"}):
            service1 = get_prompt_service()
            service2 = get_prompt_service()

        assert service1 is service2


class TestPromptFileMappingConfig:
    """Tests for prompt file mapping configuration."""

    def test_report_generation_prompt_mapped(self):
        """report-generation prompt is mapped to file."""
        assert "report-generation" in PROMPT_FILE_MAPPING
        assert "main_prompt_v4_minimal.txt" in PROMPT_FILE_MAPPING["report-generation"]
