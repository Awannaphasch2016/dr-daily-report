# -*- coding: utf-8 -*-
"""
Conciseness Scorer (Ranking Tier)

Uses LLM-as-judge to evaluate report conciseness.
This is a RANKING scorer - used to compare quality of good reports.

Measures: Information density without unnecessary verbosity.
"""

import logging
from typing import Optional

from src.scoring.types import ScoreResult, LLMScoringContext
from src.scoring.adapters import LangfuseLLMAdapter

logger = logging.getLogger(__name__)


class ConcisenessScorer:
    """
    Evaluate report conciseness using LLM-as-judge.

    Ranking Tier: Continuous 0-1 score for comparing reports.
    Higher = more concise without losing important information.
    """

    def __init__(
        self,
        adapter: Optional[LangfuseLLMAdapter] = None,
        model: str = "openai/gpt-4o-mini",
    ):
        """
        Initialize conciseness scorer.

        Args:
            adapter: LangfuseLLMAdapter instance (creates new if not provided)
            model: Model to use for evaluation
        """
        self._adapter = adapter or LangfuseLLMAdapter(model=model)

    async def score(self, context: LLMScoringContext) -> ScoreResult:
        """
        Score report conciseness.

        Args:
            context: LLMScoringContext with report text

        Returns:
            ScoreResult with conciseness score (0=verbose, 1=perfectly concise)
        """
        # Run LLM evaluation
        result = await self._adapter.evaluate_conciseness(
            output=context.report_text,
        )

        logger.info(f"Conciseness score for {context.ticker}: {result.value:.2f}")

        return result

    def format_score_report(self, result: ScoreResult) -> str:
        """Format conciseness score as human-readable report."""
        quality = (
            "Excellent" if result.value >= 0.8
            else "Good" if result.value >= 0.6
            else "Fair" if result.value >= 0.4
            else "Verbose"
        )

        lines = [
            "=" * 60,
            "CONCISENESS SCORE (Ranking Tier)",
            "=" * 60,
            "",
            f"Score: {result.value:.2f}/1.0 ({quality})",
            "",
        ]

        if result.reasoning:
            lines.extend([
                "Reasoning:",
                f"  {result.reasoning}",
                "",
            ])

        if result.metadata:
            lines.extend([
                f"Model: {result.metadata.get('model', 'unknown')}",
                f"Latency: {result.latency_ms:.0f}ms",
                f"Cost: ${result.cost_usd:.4f}",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)
