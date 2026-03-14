"""Judge agents — FastJudge (rule-based scoring) + DeepJudge (LLM feedback).

FastJudge: Wraps existing ScoringService for fast, free quality scoring (~100ms).
DeepJudge: Uses a cost-efficient LLM to produce actionable revision feedback (~3s).
"""

import json
import logging
import time
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.scoring.scoring_service import ScoringService, ScoringContext
from src.quant_agent.context_buffer import JudgeVerdict

logger = logging.getLogger(__name__)


# Score weights for aggregation
SCORE_WEIGHTS = {
    "faithfulness": 0.30,
    "completeness": 0.20,
    "reasoning_quality": 0.20,
    "compliance": 0.15,
    "consistency": 0.15,
}

DEEP_JUDGE_PROMPT = """\
You are a quality reviewer for Thai-language financial stock reports.

REPORT TO REVIEW:
{report}

MARKET DATA SUMMARY:
{data_summary}

RULE-BASED QUALITY SCORES (0-1 scale):
{fast_scores}

Your task: Identify 1-3 specific weaknesses and provide concrete revision instructions.
Focus on: faithfulness to data, logical consistency, completeness of analysis, actionable recommendation.

Respond in JSON only:
{{"weaknesses": ["weakness 1", "weakness 2"], "revision_instructions": ["fix 1", "fix 2"]}}"""


class FastJudge:
    """Rule-based quality scoring. Reuses ScoringService directly.

    ~100ms, free. Returns aggregate score (0-100) and per-dimension scores.
    """

    def __init__(self, scoring_service: ScoringService):
        self.scoring_service = scoring_service

    def score(self, report: str, scoring_ctx: ScoringContext) -> tuple[float, dict]:
        """Score the report using rule-based scorers.

        Args:
            report: Post-processed report text.
            scoring_ctx: ScoringContext with indicators, news, etc.

        Returns:
            Tuple of (aggregate_score_0_100, raw_scores_dict).
        """
        start = time.perf_counter()

        scores = self.scoring_service.compute_all_quality_scores(report, scoring_ctx)

        # Weighted aggregate (scorers return overall_score in 0-100 range)
        aggregate = 0.0
        for name, weight in SCORE_WEIGHTS.items():
            if name in scores and hasattr(scores[name], "overall_score"):
                aggregate += scores[name].overall_score * weight

        aggregate_100 = aggregate

        elapsed = time.perf_counter() - start
        score_summary = ", ".join(
            f"{k}={v.overall_score:.2f}"
            for k, v in scores.items()
            if hasattr(v, "overall_score")
        )
        logger.info(
            f"   FastJudge: {aggregate_100:.1f}/100 ({score_summary}) [{elapsed*1000:.0f}ms]"
        )

        return aggregate_100, scores


class DeepJudge:
    """LLM-as-judge for textual revision feedback.

    Uses a cost-efficient model (gpt-4o-mini by default) to provide
    actionable feedback that the Writer can use on the next iteration.
    ~3s per call.
    """

    def __init__(self, model: str = "openai/gpt-4o-mini", api_key: Optional[str] = None,
                 base_url: str = "https://openrouter.ai/api/v1"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.3,
            base_url=base_url,
            api_key=api_key,
        )

    def review(
        self, report: str, state_data: dict, fast_scores: dict
    ) -> JudgeVerdict:
        """Produce actionable feedback for the Writer.

        Args:
            report: The report text to review.
            state_data: Raw data dict for context.
            fast_scores: Scores from FastJudge for context.

        Returns:
            JudgeVerdict with weaknesses and revision instructions.
        """
        start = time.perf_counter()

        # Build compact data summary for the judge
        data_summary = self._build_data_summary(state_data)

        # Format fast scores
        score_lines = []
        for name, result in fast_scores.items():
            if hasattr(result, "overall_score"):
                score_lines.append(f"  {name}: {result.overall_score:.2f}")
        scores_str = "\n".join(score_lines)

        prompt = DEEP_JUDGE_PROMPT.format(
            report=report[:2000],  # Truncate to control token usage
            data_summary=data_summary[:1000],
            fast_scores=scores_str,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            verdict = self._parse_verdict(response.content)
        except Exception as e:
            logger.warning(f"   DeepJudge: LLM call failed ({e}), returning generic feedback")
            verdict = JudgeVerdict(
                weaknesses=["Could not evaluate report quality"],
                revision_instructions=["Try to improve overall narrative coherence"],
            )

        elapsed = time.perf_counter() - start
        logger.info(
            f"   DeepJudge: {len(verdict.weaknesses)} weaknesses identified [{elapsed:.1f}s]"
        )

        return verdict

    def _build_data_summary(self, state_data: dict) -> str:
        """Build a compact data summary for the judge prompt."""
        indicators = state_data.get("indicators", {})
        ticker_data = state_data.get("ticker_data", {})

        lines = [f"Ticker: {state_data.get('ticker', 'N/A')}"]

        # Key indicators
        for key in ["current_price", "rsi", "macd", "uncertainty_score", "atr"]:
            val = indicators.get(key)
            if val is not None:
                lines.append(f"  {key}: {val}")

        # Company info
        company = ticker_data.get("company_info", {})
        if isinstance(company, dict):
            for key in ["sector", "industry", "pe_ratio", "market_cap"]:
                val = company.get(key)
                if val is not None:
                    lines.append(f"  {key}: {val}")

        return "\n".join(lines)

    def _parse_verdict(self, response_text: str) -> JudgeVerdict:
        """Parse LLM response into JudgeVerdict."""
        try:
            # Try to extract JSON from response
            text = response_text.strip()
            # Handle markdown code blocks
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            data = json.loads(text)
            return JudgeVerdict(
                weaknesses=data.get("weaknesses", ["No weaknesses identified"]),
                revision_instructions=data.get(
                    "revision_instructions", ["Improve overall quality"]
                ),
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"   DeepJudge: Failed to parse JSON ({e}), extracting manually")
            return JudgeVerdict(
                weaknesses=[response_text[:200]],
                revision_instructions=["Address the issues noted above"],
            )
