"""Post-processing pipeline for generated reports.

Extracted from WorkflowNodes._post_process_report_workflow() and the scoring/trace
section of _generate_report_singlestage(). Used by both the old monolithic path
and the new PostProcess Lambda.

Steps:
1. Number injection (replace {PLACEHOLDERS} with ground truth values)
2. News references
3. Transparency footer
4. Quality scoring + Langfuse push
5. Trace storage in Aurora
"""

import logging
import os
import time

logger = logging.getLogger(__name__)


def inject_and_finalize(
    report_text: str,
    raw_data: dict,
    number_injector,
    market_analyzer,
    news_fetcher,
    strategy_performance: dict = None,
) -> str:
    """Apply number injection, news references, and transparency footer.

    This is the "text transformation" half of post-processing. It modifies
    the report text but does not perform scoring or storage.

    Args:
        report_text: LLM-generated report with {PLACEHOLDERS}
        raw_data: Dict with RAW_DATA_FIELDS
        number_injector: NumberInjector instance
        market_analyzer: MarketAnalyzer instance
        news_fetcher: NewsFetcher instance
        strategy_performance: Optional filtered strategy data (overrides raw_data)

    Returns:
        Finalized report text with numbers injected and appendices added
    """
    indicators = raw_data.get('indicators', {})
    ticker_data = raw_data.get('ticker_data', {})
    percentiles = raw_data.get('percentiles', {})
    comparative_insights = raw_data.get('comparative_insights', {})
    news = raw_data.get('news', [])

    if strategy_performance is None:
        strategy_performance = raw_data.get('strategy_performance', {})

    # Step 1: Calculate ground truth
    conditions = market_analyzer.calculate_market_conditions(indicators)
    ground_truth = {
        'uncertainty_score': indicators.get('uncertainty_score', 0),
        'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                   if indicators.get('current_price', 0) > 0 else 0,
        'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
        'volume_ratio': conditions.get('volume_ratio', 0),
    }

    # Step 2: Replace {PLACEHOLDERS} with exact values
    report_text = number_injector.inject_deterministic_numbers(
        report_text,
        ground_truth,
        indicators,
        percentiles,
        ticker_data,
        comparative_insights,
        strategy_performance=strategy_performance,
    )

    # Step 3: Add news references
    if news:
        news_references = news_fetcher.get_news_references(news)
        report_text += f"\n\n{news_references}"

    # Step 4: Add transparency footer
    from src.report import TransparencyFooter
    transparency = TransparencyFooter()
    footnote = transparency.generate_data_usage_footnote(raw_data)
    report_text += footnote

    return report_text


def compute_scores_and_store(
    report_text: str,
    raw_data: dict,
    scoring_service,
    number_injector,
    market_analyzer,
    prompt_builder,
    ticker_map: dict,
    llm_model_name: str,
    api_costs: dict,
    is_experiment: bool = False,
) -> dict:
    """Compute quality scores, push to Langfuse, and store trace in Aurora.

    Args:
        report_text: Finalized report text (post number injection)
        raw_data: Dict with RAW_DATA_FIELDS
        scoring_service: ScoringService instance
        number_injector: NumberInjector instance (has last_metrics after injection)
        market_analyzer: MarketAnalyzer instance
        prompt_builder: PromptBuilder instance
        ticker_map: DR symbol → Yahoo ticker mapping
        llm_model_name: Model ID string for trace storage
        api_costs: Dict with input_tokens, output_tokens, llm_estimated
        is_experiment: If True, skip Aurora trace storage

    Returns:
        {
            'quality_scores': dict,  # {scorer_name: overall_score}
            'placeholder_compliance': float,  # 0-100
            'placeholder_metrics': dict,
        }
    """
    from src.utils.serialization import make_json_serializable
    from src.scoring.scoring_service import ScoringContext

    ticker = raw_data.get('ticker', '')
    indicators = raw_data.get('indicators', {})
    percentiles = raw_data.get('percentiles', {})
    news = raw_data.get('news', [])
    ticker_data = raw_data.get('ticker_data', {})

    # Build scoring context
    conditions = market_analyzer.calculate_market_conditions(indicators)
    scoring_context = ScoringContext(
        indicators=make_json_serializable(indicators),
        percentiles=make_json_serializable(percentiles),
        news=make_json_serializable(news),
        ticker_data=make_json_serializable(ticker_data),
        market_conditions={
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                       if indicators.get('current_price', 0) > 0 else 0,
            'price_vs_vwap_pct': conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': conditions.get('volume_ratio', 0),
        },
        comparative_insights=make_json_serializable(raw_data.get('comparative_insights', {})),
        injected_replacements=getattr(number_injector, 'last_replacements', None),
    )

    result = {
        'quality_scores': {},
        'placeholder_compliance': 0.0,
        'placeholder_metrics': {},
    }

    try:
        # Compute rule-based quality scores
        quality_scores = scoring_service.compute_all_quality_scores(
            report_text=report_text,
            context=scoring_context,
        )

        # Build langfuse scores dict
        langfuse_scores = {}
        for score_name, score_result in quality_scores.items():
            if hasattr(score_result, 'overall_score'):
                overall = score_result.overall_score
                comment = None
                sub = getattr(score_result, 'dimension_scores', None) or getattr(score_result, 'metric_scores', None)
                if sub:
                    sub_details = [f"{k}={v:.1f}" for k, v in sub.items()]
                    comment = ", ".join(sub_details)
                langfuse_scores[score_name] = (overall, comment)

        result['quality_scores'] = {
            name: r.overall_score if hasattr(r, 'overall_score') else 0
            for name, r in quality_scores.items()
        }

        score_summary = ", ".join([
            f"{name}={r.overall_score:.1f}"
            for name, r in quality_scores.items()
            if hasattr(r, 'overall_score')
        ])
        logger.info(f"Rule-based scores: {score_summary}")

        # Placeholder compliance
        last_metrics = getattr(number_injector, 'last_metrics', {}) or {}
        total = last_metrics.get('injected_count', 0) + last_metrics.get('unresolved_count', 0)
        compliance_pct = (last_metrics['injected_count'] / total * 100) if total > 0 else 100
        langfuse_scores['placeholder_compliance'] = (
            compliance_pct,
            f"injected={last_metrics.get('injected_count', 0)}, "
            f"unresolved={last_metrics.get('unresolved_count', 0)}, "
            f"orphan={last_metrics.get('orphan_suffix_count', 0)}"
        )
        result['placeholder_compliance'] = round(compliance_pct, 1)
        result['placeholder_metrics'] = last_metrics

        # Push scores to Langfuse
        try:
            from src.integrations.langfuse_client import score_trace_batch
            scores_pushed = score_trace_batch(langfuse_scores)
            if scores_pushed > 0:
                logger.info(f"Pushed {scores_pushed} scores to Langfuse")
        except Exception as e:
            logger.warning(f"Langfuse score push failed (non-blocking): {e}")

        # Store trace in Aurora (skip for experiments)
        if not is_experiment:
            _store_trace(
                ticker=ticker,
                raw_data=raw_data,
                llm_model_name=llm_model_name,
                prompt_builder=prompt_builder,
                api_costs=api_costs,
                langfuse_scores=langfuse_scores,
                quality_scores=quality_scores,
                number_injector=number_injector,
            )

    except Exception as e:
        logger.warning(f"Quality scoring failed (non-blocking): {e}")

    return result


def _store_trace(
    ticker: str,
    raw_data: dict,
    llm_model_name: str,
    prompt_builder,
    api_costs: dict,
    langfuse_scores: dict,
    quality_scores: dict,
    number_injector,
) -> None:
    """Store generation trace in Aurora with scores."""
    try:
        from src.data.aurora.trace_repository import get_trace_repository
        from src.integrations.langfuse_client import get_current_trace_id
        from src.scoring import (
            FaithfulnessScorer, CompletenessScorer, ReasoningQualityScorer,
            ComplianceScorer, ConsistencyScorer, CostScorer, QoSScorer,
        )

        scorer_versions = {
            'faithfulness': FaithfulnessScorer.VERSION,
            'completeness': CompletenessScorer.VERSION,
            'reasoning_quality': ReasoningQualityScorer.VERSION,
            'compliance': ComplianceScorer.VERSION,
            'consistency': ConsistencyScorer.VERSION,
            'cost_efficiency': CostScorer.VERSION,
            'qos': QoSScorer.VERSION,
            'placeholder_compliance': '1.0',
        }

        trace_repo = get_trace_repository()
        trace_data = {
            'trace_type': 'report_generation',
            'model_id': llm_model_name,
            'prompt_version': prompt_builder.get_prompt_metadata().get('prompt_version'),
            'agent_type': 'single-stage',
            'release': os.environ.get('LANGFUSE_RELEASE') or os.environ.get('AWS_LAMBDA_FUNCTION_VERSION'),
            'trace_provider': 'langfuse' if os.environ.get('LANGFUSE_PUBLIC_KEY') else None,
            'trace_external_id': get_current_trace_id(),
            'input_tokens': api_costs.get('input_tokens'),
            'output_tokens': api_costs.get('output_tokens'),
            'cost_usd': api_costs.get('llm_estimated'),
            'calc_version': 'v1',
            'context': {'symbol': ticker, 'report_date': str(raw_data.get('data_date', ''))},
            'status': 'completed',
            'error_message': None,
        }

        trace_scores = {}
        for name, (value, comment) in langfuse_scores.items():
            score_entry = {
                'value': value,
                'comment': comment,
                'scorer_type': 'rule',
                'scorer_version': scorer_versions.get(name, '1.0'),
                'sub_scores': None,
                'config': None,
            }
            if name in quality_scores:
                result = quality_scores[name]
                sub = getattr(result, 'dimension_scores', None) or getattr(result, 'metric_scores', None)
                if sub:
                    score_entry['sub_scores'] = dict(sub)
            if name == 'placeholder_compliance':
                score_entry['scorer_type'] = 'computed'
                score_entry['sub_scores'] = getattr(number_injector, 'last_metrics', None)
            trace_scores[name] = score_entry

        trace_repo.insert_trace_with_scores(trace_data, trace_scores)
        logger.info(f"Stored trace with {len(trace_scores)} scores to Aurora")

    except Exception as e:
        logger.warning(f"Trace storage failed (non-blocking): {e}")
