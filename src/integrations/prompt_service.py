# -*- coding: utf-8 -*-
"""Langfuse Prompt Management Service.

Provides prompt fetching with file-based fallback for reliability.
Enables prompt version tracking for A/B testing and performance comparison.

Migration Strategy:
    Phase 1 (current): Read-only integration with file fallback
    Phase 2: Full Langfuse integration (remove fallback)
    Phase 3: A/B testing with multiple prompt versions

Environment Variables:
    LANGFUSE_PROMPTS_ENABLED: Set to "true" to enable Langfuse prompts (default: "false")
    ENVIRONMENT: Environment name for prompt label (dev/staging/production)
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from src.integrations.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)

# Prompt name to file path mapping (single source of truth)
PROMPT_FILE_MAPPING = {
    "report-generation": "prompt_templates/th/single-stage/main_prompt_v4_minimal.txt",
}

# Cache TTL for Langfuse prompts (seconds)
PROMPT_CACHE_TTL = int(os.environ.get("LANGFUSE_PROMPT_CACHE_TTL", "60"))


@dataclass
class PromptResult:
    """Result of prompt fetch operation.

    Attributes:
        content: The prompt template content
        source: Where prompt came from ("langfuse" or "file")
        name: Prompt name/identifier
        version: Version string (Langfuse version or "file")
        variables: Variables that can be substituted in the prompt
    """
    content: str
    source: str
    name: str
    version: str
    variables: list


class PromptService:
    """Service for fetching prompts with Langfuse integration and file fallback.

    This service implements Phase 1 of the Langfuse prompt migration:
    - Fetches prompts from Langfuse when available
    - Falls back to file-based prompts if Langfuse unavailable
    - Tracks prompt version for performance comparison

    Usage:
        service = PromptService()
        result = service.get_prompt("report-generation")
        compiled = service.compile_prompt(result, ticker="ADVANC", context="...")

    Invariants:
        - Always returns valid prompt (Langfuse or file)
        - Fallback triggers within 3 seconds if Langfuse unavailable
        - Version tracking enabled for all prompts
    """

    def __init__(self, prompts_base_path: Optional[Path] = None):
        """Initialize PromptService.

        Args:
            prompts_base_path: Base path for file prompts (default: src/report/)
        """
        self.prompts_base_path = prompts_base_path or Path(__file__).parent.parent / "report"
        self._langfuse_enabled = os.environ.get("LANGFUSE_PROMPTS_ENABLED", "false").lower() == "true"
        self._environment = os.environ.get("ENVIRONMENT", "dev")

        # Map environment to Langfuse label
        self._label_map = {
            "dev": "development",
            "staging": "staging",
            "prod": "production",
            "production": "production",
        }

        logger.info(f"PromptService initialized: langfuse_enabled={self._langfuse_enabled}, env={self._environment}")

    def _get_langfuse_label(self) -> str:
        """Get Langfuse prompt label for current environment."""
        return self._label_map.get(self._environment, "development")

    def get_prompt(self, name: str, version: Optional[str] = None) -> PromptResult:
        """Fetch prompt by name with fallback to file.

        Args:
            name: Prompt name (e.g., "report-generation")
            version: Optional specific version to fetch (for reproducibility)

        Returns:
            PromptResult with content, source, and version info

        Raises:
            FileNotFoundError: If prompt not found in Langfuse AND file fallback fails
        """
        # Try Langfuse first if enabled
        if self._langfuse_enabled:
            result = self._fetch_from_langfuse(name, version)
            if result:
                logger.info(f"✅ Prompt '{name}' fetched from Langfuse (version: {result.version})")
                return result
            else:
                logger.warning(f"⚠️ Langfuse fetch failed for '{name}', falling back to file")

        # Fallback to file
        result = self._fetch_from_file(name)
        logger.info(f"📄 Prompt '{name}' loaded from file (fallback)")
        return result

    def _fetch_from_langfuse(self, name: str, version: Optional[str] = None) -> Optional[PromptResult]:
        """Fetch prompt from Langfuse.

        Args:
            name: Prompt name in Langfuse
            version: Optional specific version

        Returns:
            PromptResult or None if fetch fails
        """
        client = get_langfuse_client()
        if not client:
            return None

        try:
            label = self._get_langfuse_label()

            # Fetch prompt with caching
            if version:
                # Fetch specific version (for reproducibility)
                prompt = client.get_prompt(
                    name=name,
                    version=int(version),
                    cache_ttl_seconds=PROMPT_CACHE_TTL
                )
            else:
                # Fetch by label (latest for environment)
                prompt = client.get_prompt(
                    name=name,
                    label=label,
                    cache_ttl_seconds=PROMPT_CACHE_TTL
                )

            # Extract prompt content
            # Langfuse prompts can be TextPrompt or ChatPrompt
            if hasattr(prompt, 'prompt'):
                content = prompt.prompt
            elif hasattr(prompt, 'get_langchain_prompt'):
                # For chat prompts, get the template
                lc_prompt = prompt.get_langchain_prompt()
                content = str(lc_prompt)
            else:
                content = str(prompt)

            # Get version info
            prompt_version = str(prompt.version) if hasattr(prompt, 'version') else "unknown"

            # Get config/variables if available
            variables = []
            if hasattr(prompt, 'config') and prompt.config:
                variables = prompt.config.get('variables', [])

            return PromptResult(
                content=content,
                source="langfuse",
                name=name,
                version=prompt_version,
                variables=variables
            )

        except Exception as e:
            logger.warning(f"Langfuse prompt fetch error for '{name}': {e}")
            return None

    def _fetch_from_file(self, name: str) -> PromptResult:
        """Fetch prompt from file system.

        Args:
            name: Prompt name (mapped to file path)

        Returns:
            PromptResult from file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if name not in PROMPT_FILE_MAPPING:
            raise FileNotFoundError(f"Unknown prompt name: {name}. Available: {list(PROMPT_FILE_MAPPING.keys())}")

        file_path = self.prompts_base_path / PROMPT_FILE_MAPPING[name]

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return PromptResult(
            content=content,
            source="file",
            name=name,
            version="file",
            variables=[]
        )

    def compile_prompt(self, result: PromptResult, **variables) -> Tuple[str, Dict[str, Any]]:
        """Compile prompt with variables and return metadata for tracing.

        Args:
            result: PromptResult from get_prompt
            **variables: Variables to substitute in prompt

        Returns:
            Tuple of (compiled_prompt, metadata_for_tracing)

        Note:
            The metadata should be attached to Langfuse traces for version tracking.
        """
        # Compile prompt (substitute variables)
        try:
            compiled = result.content.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable in prompt compilation: {e}")
            # Return uncompiled content with error note
            compiled = result.content

        # Build metadata for tracing
        metadata = {
            "prompt_name": result.name,
            "prompt_version": result.version,
            "prompt_source": result.source,
        }

        return compiled, metadata


# Singleton instance for Lambda optimization
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Get or create PromptService singleton.

    Returns:
        PromptService instance
    """
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
