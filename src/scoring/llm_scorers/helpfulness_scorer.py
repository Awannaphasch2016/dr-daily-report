# -*- coding: utf-8 -*-
"""
Helpfulness Scorer (Ranking Tier)

Uses LLM-as-judge to evaluate how helpful the report is for the user.
This is a RANKING scorer - used to compare quality of good reports.
"""

import logging
from typing import Optional

from src.scoring.types import ScoreResult, LLMScoringContext
from src.scoring.adapters import LangfuseLLMAdapter

logger = logging.getLogger(__name__)


class HelpfulnessScorer:
    """
    Evaluate report helpfulness using LLM-as-judge.

    Ranking Tier: Continuous 0-1 score for comparing reports.
    Higher = more helpful to user.
    """

    def __init__(
        self,
        adapter: Optional[LangfuseLLMAdapter] = None,
        model: str = "openai/gpt-4o-mini",
    ):
        """
        Initialize helpfulness scorer.

        Args:
            adapter: LangfuseLLMAdapter instance (creates new if not provided)
            model: Model to use for evaluation
        """
        self._adapter = adapter or LangfuseLLMAdapter(model=model)

    async def score(self, context: LLMScoringContext) -> ScoreResult:
        """
        Score report helpfulness.

        Args:
            context: LLMScoringContext with report and query info

        Returns:
            ScoreResult with helpfulness score (0=not helpful, 1=very helpful)
        """
        # Get the user query (or generate default)
        query = context.get_query()

        # Run LLM evaluation
        result = await self._adapter.evaluate_helpfulness(
            output=context.report_text,
            query=query,
        )

        logger.info(f"Helpfulness score for {context.ticker}: {result.value:.2f}")

        return result

    def format_score_report(self, result: ScoreResult) -> str:
        """Format helpfulness score as human-readable report."""
        quality = (
            "Excellent" if result.value >= 0.8
            else "Good" if result.value >= 0.6
            else "Fair" if result.value >= 0.4
            else "Poor"
        )

        lines = [
            "=" * 60,
            "HELPFULNESS SCORE (Ranking Tier)",
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
