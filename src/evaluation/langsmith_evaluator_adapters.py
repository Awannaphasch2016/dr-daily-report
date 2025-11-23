#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangSmith RunEvaluator Adapters for dr-daily-report Scorers

Wraps existing 7 scorers to be compatible with LangSmith's evaluate() function.
These adapters implement the RunEvaluator protocol, allowing scorers to be used
in offline evaluation with datasets.

Evaluation Framework:
- FaithfulnessScorer: Factual accuracy (are facts supported by data?)
- ConsistencyScorer: Logical consistency (do interpretations match data?)
- CompletenessScorer: Coverage (are all dimensions included?)
- ReasoningQualityScorer: Explanation quality (how well is it explained?)
- ComplianceScorer: Format/policy adherence
- QoSScorer: Performance metrics
- CostScorer: Operational costs

Usage:
    from langsmith import evaluate
    from src.evaluation.langsmith_evaluator_adapters import (
        faithfulness_evaluator,
        completeness_evaluator,
        reasoning_quality_evaluator,
        compliance_evaluator,
        consistency_evaluator,  # NEW: LLM-based logical consistency
        qos_evaluator,
        cost_evaluator
    )

    results = evaluate(
        target=my_report_generator,
        data="my-dataset",
        evaluators=[
            faithfulness_evaluator,
            completeness_evaluator,
            reasoning_quality_evaluator,
            compliance_evaluator,
            consistency_evaluator,
            qos_evaluator,
            cost_evaluator
        ]
    )
"""

from langsmith.evaluation import EvaluationResult, run_evaluator
from langsmith.schemas import Run, Example
from typing import Optional
from dataclasses import asdict
import logging

from .faithfulness_scorer import FaithfulnessScorer
from .completeness_scorer import CompletenessScorer
from .reasoning_quality_scorer import ReasoningQualityScorer
from .compliance_scorer import ComplianceScorer
from .qos_scorer import QoSScorer
from .cost_scorer import CostScorer
from .consistency_scorer import ConsistencyScorer

logger = logging.getLogger(__name__)


# ==============================================================================
# QUALITY SCORERS (Rule-Based)
# ==============================================================================

@run_evaluator
def faithfulness_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """
    LangSmith evaluator adapter for FaithfulnessScorer.

    Expected Run/Example structure:
        run.outputs: {"narrative": "..."}  or {"output": "..."}
        run.inputs or example.inputs: {
            "indicators": {...},
            "percentiles": {...},
            "market_conditions": {...},
            "news_data": [...] or "news": [...]
        }

    Note: ground_truth dict is constructed from indicators and market_conditions
    """
    try:
        # Extract data from Run/Example
        narrative = run.outputs.get("narrative") or run.outputs.get("output", "")

        # Get base data sources
        indicators = run.inputs.get("indicators") or (example.inputs.get("indicators") if example else {})
        percentiles = run.inputs.get("percentiles") or (example.inputs.get("percentiles") if example else {})
        news_data = run.inputs.get("news_data") or run.inputs.get("news") or (example.inputs.get("news_data") if example else []) or (example.inputs.get("news") if example else [])
        market_conditions = run.inputs.get("market_conditions") or (example.inputs.get("market_conditions") if example else {})
        ticker_data = run.inputs.get("ticker_data") or (example.inputs.get("ticker_data") if example else None)

        # Construct ground_truth dict (same as scoring_service.py)
        # This dict is needed by faithfulness_scorer but not stored as a single key in datasets
        ground_truth = {
            'uncertainty_score': (indicators or {}).get('uncertainty_score', 0) if indicators else 0,
            'atr_pct': (market_conditions or {}).get('atr_pct', 0) if market_conditions else 0,
            'vwap_pct': (market_conditions or {}).get('price_vs_vwap_pct', 0) if market_conditions else 0,
            'volume_ratio': (market_conditions or {}).get('volume_ratio', 0) if market_conditions else 0,
        }

        # Score using existing scorer
        scorer = FaithfulnessScorer()
        result = scorer.score_narrative(
            narrative=narrative,
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            news_data=news_data,
            ticker_data=ticker_data
        )

        # Format comment
        comment = (
            f"Numeric: {result.metric_scores['numeric_accuracy']:.1f}%, "
            f"Percentile: {result.metric_scores['percentile_accuracy']:.1f}%, "
            f"News: {result.metric_scores['news_citation_accuracy']:.1f}%, "
            f"Factual: {result.metric_scores['factual_correctness']:.1f}%, "
            f"Claims: {result.metric_scores['claim_support']:.1f}% | "
            f"Violations: {len(result.violations)}"
        )

        return EvaluationResult(
            key="faithfulness_score",
            score=result.overall_score / 100.0,  # Normalize to 0-1
            comment=comment,
            evaluator_info={"metric_scores": result.metric_scores},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Faithfulness evaluator error: {e}")
        return EvaluationResult(
            key="faithfulness_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


@run_evaluator
def completeness_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """LangSmith evaluator adapter for CompletenessScorer"""
    try:
        narrative = run.outputs.get("narrative") or run.outputs.get("output", "")
        ticker_data = run.inputs.get("ticker_data") or (example.inputs.get("ticker_data") if example else {})
        indicators = run.inputs.get("indicators") or (example.inputs.get("indicators") if example else {})
        percentiles = run.inputs.get("percentiles") or (example.inputs.get("percentiles") if example else {})
        news_data = run.inputs.get("news_data") or (example.inputs.get("news_data") if example else [])

        scorer = CompletenessScorer()
        result = scorer.score_narrative(
            narrative=narrative,
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news_data=news_data
        )

        comment = (
            f"Context: {result.dimension_scores['context_completeness']:.1f}%, "
            f"Analysis: {result.dimension_scores['analysis_dimensions']:.1f}%, "
            f"Temporal: {result.dimension_scores['temporal_completeness']:.1f}%, "
            f"Actionability: {result.dimension_scores['actionability']:.1f}% | "
            f"Missing: {len(result.missing_elements)}"
        )

        return EvaluationResult(
            key="completeness_score",
            score=result.overall_score / 100.0,
            comment=comment,
            evaluator_info={"dimension_scores": result.dimension_scores},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Completeness evaluator error: {e}")
        return EvaluationResult(
            key="completeness_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


@run_evaluator
def reasoning_quality_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """LangSmith evaluator adapter for ReasoningQualityScorer"""
    try:
        narrative = run.outputs.get("narrative") or run.outputs.get("output", "")
        indicators = run.inputs.get("indicators") or (example.inputs.get("indicators") if example else {})
        percentiles = run.inputs.get("percentiles") or (example.inputs.get("percentiles") if example else {})
        ticker_data = run.inputs.get("ticker_data") or (example.inputs.get("ticker_data") if example else {})

        scorer = ReasoningQualityScorer()
        result = scorer.score_narrative(
            narrative=narrative,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data
        )

        comment = (
            f"Clarity: {result.dimension_scores['clarity']:.1f}%, "
            f"Coverage: {result.dimension_scores['coverage']:.1f}%, "
            f"Specificity: {result.dimension_scores['specificity']:.1f}% | "
            f"Issues: {len(result.issues)}, Strengths: {len(result.strengths)}"
        )

        return EvaluationResult(
            key="reasoning_quality_score",
            score=result.overall_score / 100.0,
            comment=comment,
            evaluator_info={"dimension_scores": result.dimension_scores},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Reasoning quality evaluator error: {e}")
        return EvaluationResult(
            key="reasoning_quality_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


@run_evaluator
def compliance_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """LangSmith evaluator adapter for ComplianceScorer"""
    try:
        narrative = run.outputs.get("narrative") or run.outputs.get("output", "")
        indicators = run.inputs.get("indicators") or (example.inputs.get("indicators") if example else {})
        news_data = run.inputs.get("news_data") or (example.inputs.get("news_data") if example else [])

        scorer = ComplianceScorer()
        result = scorer.score_narrative(
            narrative=narrative,
            indicators=indicators,
            news_data=news_data
        )

        comment = (
            f"Structure: {result.dimension_scores['structure_compliance']:.1f}%, "
            f"Content: {result.dimension_scores['content_compliance']:.1f}%, "
            f"Format: {result.dimension_scores['format_compliance']:.1f}% | "
            f"Violations: {len(result.violations)}"
        )

        return EvaluationResult(
            key="compliance_score",
            score=result.overall_score / 100.0,
            comment=comment,
            evaluator_info={"dimension_scores": result.dimension_scores},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Compliance evaluator error: {e}")
        return EvaluationResult(
            key="compliance_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


# ==============================================================================
# PERFORMANCE SCORERS
# ==============================================================================

@run_evaluator
def qos_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """LangSmith evaluator adapter for QoSScorer"""
    try:
        # Performance metrics typically in run.metadata
        timing_metrics = run.metadata.get("timing_metrics", {})
        database_metrics = run.metadata.get("database_metrics", {})
        error_occurred = run.metadata.get("error_occurred", False)
        cache_hit = run.metadata.get("cache_hit", False)
        llm_calls = run.metadata.get("llm_calls", 0)

        scorer = QoSScorer()
        result = scorer.score_qos(
            timing_metrics=timing_metrics,
            database_metrics=database_metrics,
            error_occurred=error_occurred,
            cache_hit=cache_hit,
            llm_calls=llm_calls
        )

        comment = (
            f"Latency: {result.dimension_scores['latency']:.1f}%, "
            f"Reliability: {result.dimension_scores['reliability']:.1f}%, "
            f"Resource: {result.dimension_scores['resource_efficiency']:.1f}% | "
            f"Total: {timing_metrics.get('total_elapsed', 0):.2f}s"
        )

        return EvaluationResult(
            key="qos_score",
            score=result.overall_score / 100.0,
            comment=comment,
            evaluator_info={"dimension_scores": result.dimension_scores},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"QoS evaluator error: {e}")
        return EvaluationResult(
            key="qos_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


@run_evaluator
def cost_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """LangSmith evaluator adapter for CostScorer"""
    try:
        api_costs = run.metadata.get("api_costs", {})
        llm_calls = run.metadata.get("llm_calls", 0)
        database_metrics = run.metadata.get("database_metrics", {})
        cache_hit = run.metadata.get("cache_hit", False)

        scorer = CostScorer()
        result = scorer.score_cost(
            api_costs=api_costs,
            llm_calls=llm_calls,
            database_metrics=database_metrics,
            cache_hit=cache_hit
        )

        comment = (
            f"Cost: {result.overall_cost_thb:.4f} THB "
            f"(${result.cost_breakdown['llm_cost_usd']:.6f}) | "
            f"Tokens: {result.token_usage['total_tokens']:,}"
        )

        return EvaluationResult(
            key="cost_score",
            score=result.cost_efficiency_score / 100.0,
            comment=comment,
            evaluator_info={"cost_breakdown": result.cost_breakdown},
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Cost evaluator error: {e}")
        return EvaluationResult(
            key="cost_score",
            score=0.0,
            comment=f"Error: {str(e)}"
        )


# ==============================================================================
# CONSISTENCY EVALUATOR (LLM-based logical consistency)
# ==============================================================================

@run_evaluator
def consistency_evaluator(
    run: Run,
    example: Optional[Example] = None
) -> EvaluationResult:
    """
    LangSmith evaluator adapter for ConsistencyScorer (LLM-based consistency check).

    Evaluates logical consistency between interpretations and quantitative data.
    Does NOT re-validate numeric accuracy (FaithfulnessScorer handles that).

    Expected Run/Example structure:
        run.outputs: {"narrative": "..."}
        run.inputs or example.inputs: {
            "indicators": {...},
            "percentiles": {...},
            "market_conditions": {...},
            "ticker_data": {...}  # Optional
        }
    """
    try:
        narrative = run.outputs.get("narrative") or run.outputs.get("output", "")

        # Get base data sources
        indicators = run.inputs.get("indicators") or (example.inputs.get("indicators") if example else {})
        percentiles = run.inputs.get("percentiles") or (example.inputs.get("percentiles") if example else {})
        market_conditions = run.inputs.get("market_conditions") or (example.inputs.get("market_conditions") if example else {})
        ticker_data = run.inputs.get("ticker_data") or (example.inputs.get("ticker_data") if example else None)

        # Score using LLM-based consistency scorer
        scorer = ConsistencyScorer()
        result = scorer.score_narrative(
            narrative=narrative,
            indicators=indicators,
            percentiles=percentiles,
            market_conditions=market_conditions,
            ticker_data=ticker_data
        )

        comment = (
            f"Consistency: {result.overall_score:.1f}/100 "
            f"(confidence: {result.confidence:.1f}%) | "
            f"Inconsistencies: {len(result.inconsistencies)}, "
            f"Validated: {len(result.validated_alignments)}"
        )

        return EvaluationResult(
            key="consistency_score",
            score=result.overall_score / 100.0,
            comment=comment,
            evaluator_info={
                "confidence": result.confidence,
                "inconsistency_count": len(result.inconsistencies),
                "validated_count": len(result.validated_alignments)
            },
            extra=asdict(result)
        )

    except Exception as e:
        logger.error(f"Consistency evaluator error: {e}")
        return EvaluationResult(
            key="consistency_score",
            score=0.5,  # Conservative middle score on error
            comment=f"Error: {str(e)}"
        )


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_all_evaluators():
    """
    Get list of all 7 evaluators for convenience.

    Usage:
        from langsmith import evaluate
        from src.evaluation.langsmith_evaluator_adapters import get_all_evaluators

        results = evaluate(
            target=my_function,
            data="my-dataset",
            evaluators=get_all_evaluators()
        )
    """
    return [
        faithfulness_evaluator,
        completeness_evaluator,
        reasoning_quality_evaluator,
        compliance_evaluator,
        consistency_evaluator,
        qos_evaluator,
        cost_evaluator
    ]


def get_quality_evaluators():
    """Get only quality evaluators (5 total: 4 rule-based + 1 LLM-based)"""
    return [
        faithfulness_evaluator,
        completeness_evaluator,
        reasoning_quality_evaluator,
        compliance_evaluator,
        consistency_evaluator
    ]


def get_performance_evaluators():
    """Get only performance evaluators (2 total)"""
    return [
        qos_evaluator,
        cost_evaluator
    ]
