# -*- coding: utf-8 -*-
"""
Hallucination Scorer (Gate Tier)

Uses LLM-as-judge to detect fabricated information in reports.
This is a GATE scorer - reports with hallucinations should be rejected.

Threshold: 0.7 (below this = likely hallucination = FAIL)
"""

import logging
from typing import Optional

from src.scoring.types import ScoreResult, ScoreTier, LLMScoringContext
from src.scoring.adapters import LangfuseLLMAdapter

logger = logging.getLogger(__name__)


class HallucinationScorer:
    """
    Detect hallucinations using LLM-as-judge evaluation.

    Gate Tier: Binary pass/fail based on threshold.
    Score >= 0.7: PASS (no hallucinations)
    Score < 0.7: FAIL (hallucinations detected)
    """

    # Gate threshold - below this is FAIL
    GATE_THRESHOLD = 0.7

    def __init__(
        self,
        adapter: Optional[LangfuseLLMAdapter] = None,
        model: str = "openai/gpt-4o-mini",
    ):
        """
        Initialize hallucination scorer.

        Args:
            adapter: LangfuseLLMAdapter instance (creates new if not provided)
            model: Model to use for evaluation
        """
        self._adapter = adapter or LangfuseLLMAdapter(model=model)

    async def score(self, context: LLMScoringContext) -> ScoreResult:
        """
        Score report for hallucinations.

        Args:
            context: LLMScoringContext with report and ground truth data

        Returns:
            ScoreResult with hallucination score (0=hallucinated, 1=grounded)
        """
        # Format context for LLM evaluation
        ground_truth_context = context.format_context_for_llm()

        # Run LLM evaluation
        result = await self._adapter.evaluate_hallucination(
            output=context.report_text,
            context=ground_truth_context,
        )

        # Override tier to GATE (adapter defaults to RANKING)
        result.tier = ScoreTier.GATE

        logger.info(
            f"Hallucination score for {context.ticker}: {result.value:.2f} "
            f"({'PASS' if result.passed_gate(self.GATE_THRESHOLD) else 'FAIL'})"
        )

        return result

    def passed_gate(self, result: ScoreResult) -> bool:
        """Check if hallucination check passed (no hallucinations)."""
        return result.passed_gate(self.GATE_THRESHOLD)

    def format_score_report(self, result: ScoreResult) -> str:
        """Format hallucination score as human-readable report."""
        passed = self.passed_gate(result)
        status = "PASS (No hallucinations)" if passed else "FAIL (Hallucinations detected)"

        lines = [
            "=" * 60,
            "HALLUCINATION SCORE (Gate Tier)",
            "=" * 60,
            "",
            f"Score: {result.value:.2f}/1.0 ({status})",
            f"Threshold: {self.GATE_THRESHOLD}",
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
