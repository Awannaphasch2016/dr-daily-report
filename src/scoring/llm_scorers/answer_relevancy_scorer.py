# -*- coding: utf-8 -*-
"""
Answer Relevancy Scorer (Ranking Tier)

Uses RAGAS library to evaluate how relevant the report is to the query.
This is a RANKING scorer - used to compare quality of good reports.

RAGAS answer_relevancy measures if the answer addresses the question.
"""

import logging
from typing import Optional

from src.scoring.types import ScoreResult, LLMScoringContext
from src.scoring.adapters import RAGASAdapter

logger = logging.getLogger(__name__)


class AnswerRelevancyScorer:
    """
    Evaluate answer relevancy using RAGAS library.

    Ranking Tier: Continuous 0-1 score for comparing reports.
    Higher = more relevant to the user's query.
    """

    def __init__(
        self,
        adapter: Optional[RAGASAdapter] = None,
    ):
        """
        Initialize answer relevancy scorer.

        Args:
            adapter: RAGASAdapter instance (creates new if not provided)
        """
        self._adapter = adapter or RAGASAdapter()

    async def score(self, context: LLMScoringContext) -> ScoreResult:
        """
        Score report answer relevancy.

        Args:
            context: LLMScoringContext with report, query, and contexts

        Returns:
            ScoreResult with answer_relevancy score (0=irrelevant, 1=highly relevant)
        """
        # Get query and contexts for RAGAS
        query = context.get_query()
        contexts = context.get_contexts_list()

        # Run RAGAS evaluation
        result = await self._adapter.evaluate_answer_relevancy(
            question=query,
            answer=context.report_text,
            contexts=contexts,
        )

        logger.info(f"Answer relevancy score for {context.ticker}: {result.value:.2f}")

        return result

    def format_score_report(self, result: ScoreResult) -> str:
        """Format answer relevancy score as human-readable report."""
        quality = (
            "Highly Relevant" if result.value >= 0.8
            else "Relevant" if result.value >= 0.6
            else "Somewhat Relevant" if result.value >= 0.4
            else "Not Relevant"
        )

        lines = [
            "=" * 60,
            "ANSWER RELEVANCY SCORE (Ranking Tier - RAGAS)",
            "=" * 60,
            "",
            f"Score: {result.value:.2f}/1.0 ({quality})",
            "",
        ]

        if result.metadata:
            lines.extend([
                f"Metric: {result.metadata.get('metric', 'answer_relevancy')}",
                f"RAGAS Version: {result.metadata.get('ragas_version', 'unknown')}",
                f"Latency: {result.latency_ms:.0f}ms",
                f"Cost: ${result.cost_usd:.4f}",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)
