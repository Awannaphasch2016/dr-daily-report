"""
Scoring Service Layer

Provides a clean interface for computing all report scores, decoupled from report generation.
Enables rescoring of historical reports using stored context data.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from src.scoring.faithfulness_scorer import FaithfulnessScorer
from src.scoring.completeness_scorer import CompletenessScorer
from src.scoring.reasoning_quality_scorer import ReasoningQualityScorer
from src.scoring.compliance_scorer import ComplianceScorer
from src.scoring.qos_scorer import QoSScorer
from src.scoring.cost_scorer import CostScorer
from src.scoring.consistency_scorer import ConsistencyScorer


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
    """

    def __init__(self):
        """Initialize all scorers (4 rule-based quality + 1 LLM-based consistency + 2 performance)"""
        self.faithfulness_scorer = FaithfulnessScorer()
        self.completeness_scorer = CompletenessScorer()
        self.reasoning_quality_scorer = ReasoningQualityScorer()
        self.compliance_scorer = ComplianceScorer()
        self.consistency_scorer = ConsistencyScorer()
        self.qos_scorer = QoSScorer()
        self.cost_scorer = CostScorer()

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
