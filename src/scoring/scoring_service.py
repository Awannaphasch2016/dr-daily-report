"""
Scoring Service Layer

Provides a clean interface for computing all report scores, decoupled from report generation.
Enables rescoring of historical reports using stored context data.

Two-Tier Scoring:
- Gate Tier (binary pass/fail): hallucination
- Ranking Tier (0-1 continuous): faithfulness, completeness, reasoning_quality,
  compliance, consistency, helpfulness, conciseness, answer_relevancy
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

from src.scoring.faithfulness_scorer import FaithfulnessScorer
from src.scoring.completeness_scorer import CompletenessScorer
from src.scoring.reasoning_quality_scorer import ReasoningQualityScorer
from src.scoring.compliance_scorer import ComplianceScorer
from src.scoring.qos_scorer import QoSScorer
from src.scoring.cost_scorer import CostScorer
from src.scoring.consistency_scorer import ConsistencyScorer
from src.scoring.types import ScoreResult, LLMScoringContext, ScoringError

logger = logging.getLogger(__name__)


@dataclass
class ScoringContext:
    """
    Context data required for scoring a report.

    This dataclass encapsulates all the information needed to compute quality scores
    for a report. By storing this alongside the report_text, we can recompute scores
    exactly as they were originally calculated, even if external data changes.
    """
    indicators: dict
    percentiles: dict
    news: list
    ticker_data: dict
    market_conditions: dict
    comparative_insights: Optional[dict] = None

    def to_json(self) -> dict:
        """Convert to JSON-serializable dict"""
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> 'ScoringContext':
        """Create from JSON dict"""
        return cls(**data)


class ScoringService:
    """
    Service layer for computing report scores.

    This service provides a clean, reusable interface for scoring reports.
    It can be used by:
    - agent.py during report generation
    - score_reports.py for batch rescoring
    - Test suites for validation

    Two-Tier Scoring:
    - Gate Tier: hallucination (binary pass/fail)
    - Ranking Tier: quality scores (0-1 continuous)
    """

    def __init__(self, enable_llm_scoring: bool = True):
        """
        Initialize all scorers.

        Args:
            enable_llm_scoring: Whether to enable LLM-based scorers (default True).
                               Set to False for fast-path/testing scenarios.

        Scorers:
        - 4 rule-based quality scorers (fast, free)
        - 1 LLM-based consistency scorer
        - 2 performance scorers (QoS, Cost)
        - 4 LLM-as-judge scorers (if enabled)
        """
        # Rule-based scorers (fast, no API cost)
        self.faithfulness_scorer = FaithfulnessScorer()
        self.completeness_scorer = CompletenessScorer()
        self.reasoning_quality_scorer = ReasoningQualityScorer()
        self.compliance_scorer = ComplianceScorer()
        self.consistency_scorer = ConsistencyScorer()

        # Performance scorers
        self.qos_scorer = QoSScorer()
        self.cost_scorer = CostScorer()

        # LLM-as-judge scorers (lazy initialization to avoid import cost)
        self._enable_llm_scoring = enable_llm_scoring
        self._llm_scorers_initialized = False
        self._hallucination_scorer = None
        self._helpfulness_scorer = None
        self._conciseness_scorer = None
        self._answer_relevancy_scorer = None

    def _ensure_llm_scorers_initialized(self):
        """Lazy initialization of LLM scorers (Principle #1: Defensive Programming)."""
        if self._llm_scorers_initialized:
            return

        if not self._enable_llm_scoring:
            logger.info("LLM scoring disabled - skipping initialization")
            self._llm_scorers_initialized = True
            return

        try:
            from src.scoring.llm_scorers import (
                HallucinationScorer,
                HelpfulnessScorer,
                ConcisenessScorer,
                AnswerRelevancyScorer,
            )

            self._hallucination_scorer = HallucinationScorer()
            self._helpfulness_scorer = HelpfulnessScorer()
            self._conciseness_scorer = ConcisenessScorer()
            self._answer_relevancy_scorer = AnswerRelevancyScorer()
            self._llm_scorers_initialized = True

            logger.info("✅ LLM scorers initialized (4 scorers)")

        except ImportError as e:
            logger.warning(f"LLM scorers not available (missing dependencies): {e}")
            self._enable_llm_scoring = False
            self._llm_scorers_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize LLM scorers: {e}")
            self._enable_llm_scoring = False
            self._llm_scorers_initialized = True

    def compute_all_quality_scores(
        self,
        report_text: str,
        context: ScoringContext
    ) -> dict:
        """
        Compute all 5 quality scores for a report.

        Args:
            report_text: Generated report text (Thai narrative)
            context: ScoringContext with all required data

        Returns:
            Dictionary with faithfulness, completeness, reasoning_quality, compliance, consistency scores
        """
        # Calculate ground truth for faithfulness scorer
        ground_truth = {
            'uncertainty_score': context.indicators.get('uncertainty_score', 0),
            'atr_pct': context.market_conditions.get('atr_pct', 0),
            'vwap_pct': context.market_conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': context.market_conditions.get('volume_ratio', 0),
        }

        # Compute each quality score
        faithfulness_score = self.faithfulness_scorer.score_narrative(
            narrative=report_text,
            ground_truth=ground_truth,
            indicators=context.indicators,
            percentiles=context.percentiles,
            news_data=context.news,
            ticker_data=context.ticker_data
        )

        completeness_score = self.completeness_scorer.score_narrative(
            narrative=report_text,
            ticker_data=context.ticker_data,
            indicators=context.indicators,
            percentiles=context.percentiles,
            news_data=context.news
        )

        reasoning_quality_score = self.reasoning_quality_scorer.score_narrative(
            narrative=report_text,
            indicators=context.indicators,
            percentiles=context.percentiles,
            ticker_data=context.ticker_data
        )

        compliance_score = self.compliance_scorer.score_narrative(
            narrative=report_text,
            indicators=context.indicators,
            news_data=context.news
        )

        consistency_score = self.consistency_scorer.score_narrative(
            narrative=report_text,
            indicators=context.indicators,
            percentiles=context.percentiles,
            market_conditions=context.market_conditions,
            ticker_data=context.ticker_data
        )

        return {
            'faithfulness': faithfulness_score,
            'completeness': completeness_score,
            'reasoning_quality': reasoning_quality_score,
            'compliance': compliance_score,
            'consistency': consistency_score
        }

    def compute_performance_scores(
        self,
        timing_metrics: dict,
        api_costs: dict,
        database_metrics: dict,
        llm_calls: int,
        error_occurred: bool = False,
        cache_hit: bool = False,
        historical_data: Optional[dict] = None
    ) -> dict:
        """
        Compute QoS and Cost performance scores.

        Args:
            timing_metrics: Dict with component timing data
            api_costs: Dict with LLM API cost breakdown
            database_metrics: Dict with DB query count, cache info
            llm_calls: Number of LLM API calls
            error_occurred: Whether an error occurred during execution
            cache_hit: Whether cache was used
            historical_data: Historical QoS data for comparison

        Returns:
            Dictionary with qos and cost scores
        """
        qos_score = self.qos_scorer.score_qos(
            timing_metrics=timing_metrics,
            database_metrics=database_metrics,
            error_occurred=error_occurred,
            cache_hit=cache_hit,
            llm_calls=llm_calls,
            historical_data=historical_data
        )

        cost_score = self.cost_scorer.score_cost(
            api_costs=api_costs,
            llm_calls=llm_calls,
            database_metrics=database_metrics,
            cache_hit=cache_hit
        )

        return {
            'qos': qos_score,
            'cost': cost_score
        }

    def format_all_reports(self, scores: dict) -> str:
        """
        Format all score reports as human-readable text.

        Args:
            scores: Dictionary with all score objects

        Returns:
            Formatted report string
        """
        reports = []

        if 'faithfulness' in scores:
            reports.append(self.faithfulness_scorer.format_score_report(scores['faithfulness']))

        if 'completeness' in scores:
            reports.append(self.completeness_scorer.format_score_report(scores['completeness']))

        if 'reasoning_quality' in scores:
            reports.append(self.reasoning_quality_scorer.format_score_report(scores['reasoning_quality']))

        if 'compliance' in scores:
            reports.append(self.compliance_scorer.format_score_report(scores['compliance']))

        if 'qos' in scores:
            reports.append(self.qos_scorer.format_score_report(scores['qos']))

        if 'cost' in scores:
            reports.append(self.cost_scorer.format_score_report(scores['cost']))

        return "\n\n".join(reports)

    # =========================================================================
    # LLM-as-Judge Scoring (Two-Tier Framework)
    # =========================================================================

    def build_llm_scoring_context(
        self,
        report_text: str,
        ticker: str,
        context: ScoringContext,
        query: Optional[str] = None,
    ) -> LLMScoringContext:
        """
        Build LLMScoringContext from report and ScoringContext.

        Args:
            report_text: Generated report text
            ticker: Stock ticker symbol
            context: ScoringContext with indicators, news, etc.
            query: Optional user query (defaults to generic report request)

        Returns:
            LLMScoringContext for LLM-based evaluation
        """
        # Build input_data dict from indicators and market_conditions
        input_data = {}
        input_data.update(context.indicators)
        input_data.update(context.market_conditions)

        return LLMScoringContext(
            report_text=report_text,
            ticker=ticker,
            input_data=input_data,
            news_data=context.news,
            query=query,
        )

    async def compute_llm_scores_async(
        self,
        llm_context: LLMScoringContext,
        run_gate_only: bool = False,
    ) -> Dict[str, ScoreResult]:
        """
        Compute LLM-as-judge scores asynchronously.

        Two-tier scoring:
        - Gate Tier: hallucination (must pass to proceed)
        - Ranking Tier: helpfulness, conciseness, answer_relevancy

        Args:
            llm_context: LLMScoringContext with report and ground truth
            run_gate_only: If True, only run gate tier (for fast fail path)

        Returns:
            Dict mapping score name to ScoreResult

        Raises:
            ScoringError: If critical scoring fails
        """
        self._ensure_llm_scorers_initialized()

        if not self._enable_llm_scoring:
            logger.warning("LLM scoring disabled - returning empty scores")
            return {}

        results = {}

        # Gate Tier: Hallucination (must always run)
        try:
            if self._hallucination_scorer:
                hallucination_result = await self._hallucination_scorer.score(llm_context)
                results['hallucination'] = hallucination_result

                # Check gate: if failed, optionally skip ranking tier
                if not self._hallucination_scorer.passed_gate(hallucination_result):
                    logger.warning(
                        f"⚠️ Gate FAILED: hallucination score {hallucination_result.value:.2f} "
                        f"< threshold {self._hallucination_scorer.GATE_THRESHOLD}"
                    )
                    if run_gate_only:
                        return results

        except ScoringError as e:
            logger.error(f"Gate scoring failed (hallucination): {e}")
            # Continue with ranking tier even if gate fails

        if run_gate_only:
            return results

        # Ranking Tier: Run in parallel for efficiency
        ranking_tasks = []

        if self._helpfulness_scorer:
            ranking_tasks.append(('helpfulness', self._helpfulness_scorer.score(llm_context)))

        if self._conciseness_scorer:
            ranking_tasks.append(('conciseness', self._conciseness_scorer.score(llm_context)))

        if self._answer_relevancy_scorer:
            ranking_tasks.append(('answer_relevancy', self._answer_relevancy_scorer.score(llm_context)))

        # Execute ranking tasks concurrently
        if ranking_tasks:
            async_results = await asyncio.gather(
                *[task for _, task in ranking_tasks],
                return_exceptions=True
            )

            for (name, _), result in zip(ranking_tasks, async_results):
                if isinstance(result, Exception):
                    logger.warning(f"Ranking scorer {name} failed: {result}")
                else:
                    results[name] = result

        logger.info(
            f"📊 LLM scores computed: {', '.join(f'{k}={v.value:.2f}' for k, v in results.items())}"
        )

        return results

    def compute_llm_scores(
        self,
        llm_context: LLMScoringContext,
        run_gate_only: bool = False,
    ) -> Dict[str, ScoreResult]:
        """
        Synchronous wrapper for compute_llm_scores_async.

        Use this in synchronous contexts (e.g., LangGraph workflow nodes).

        Args:
            llm_context: LLMScoringContext with report and ground truth
            run_gate_only: If True, only run gate tier

        Returns:
            Dict mapping score name to ScoreResult
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.compute_llm_scores_async(llm_context, run_gate_only)
                    )
                    return future.result(timeout=60)  # 60s timeout
            else:
                return loop.run_until_complete(
                    self.compute_llm_scores_async(llm_context, run_gate_only)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(
                self.compute_llm_scores_async(llm_context, run_gate_only)
            )

    def format_llm_score_reports(self, scores: Dict[str, ScoreResult]) -> str:
        """
        Format LLM score results as human-readable text.

        Args:
            scores: Dict mapping score name to ScoreResult

        Returns:
            Formatted report string
        """
        if not scores:
            return "No LLM scores computed."

        reports = []

        # Gate tier first
        if 'hallucination' in scores:
            reports.append(self._hallucination_scorer.format_score_report(scores['hallucination']))

        # Ranking tier
        for name in ['helpfulness', 'conciseness', 'answer_relevancy']:
            if name in scores:
                scorer = getattr(self, f'_{name}_scorer', None)
                if scorer:
                    reports.append(scorer.format_score_report(scores[name]))

        return "\n\n".join(reports)

    def llm_scores_to_langfuse_format(
        self,
        scores: Dict[str, ScoreResult]
    ) -> Dict[str, tuple[float, Optional[str]]]:
        """
        Convert LLM scores to Langfuse score_trace_batch format.

        Args:
            scores: Dict mapping score name to ScoreResult

        Returns:
            Dict mapping score name to (value, comment) tuple.
            Value is already 0-1 normalized (Langfuse convention).
        """
        langfuse_scores = {}

        for name, result in scores.items():
            # Value is already 0-1 (ScoreResult enforces this)
            # Multiply by 100 for score_trace_batch which normalizes from 0-100
            langfuse_scores[name] = (result.value * 100, result.reasoning)

        return langfuse_scores
