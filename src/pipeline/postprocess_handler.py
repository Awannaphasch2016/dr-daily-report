"""PostProcess Lambda Handler — Number injection, scoring, and storage phase.

Reads raw data from S3, applies number injection to the generated report,
computes quality scores, pushes to Langfuse, stores trace in Aurora,
and optionally caches report for Telegram API.

Input event (from Step Functions):
    {s3_key, report_text, strategy_performance, ticker, dr_symbol, yahoo_symbol,
     experiment?, job_id?, source, api_costs, generation_mode, model?, execution_id}

Output:
    {status, quality_scores, placeholder_compliance, timing_ms, report_length}
"""

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)


def _validate_required_config() -> None:
    """Validate required environment variables. Fail fast."""
    required_vars = {
        'DATA_LAKE_BUCKET': 'S3 intermediate payload read',
        'AURORA_HOST': 'Aurora database (trace storage, report caching)',
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"All {len(required_vars)} required env vars present")


def handler(event: dict, context: Any) -> dict:
    """PostProcess Lambda handler — inject numbers, score, store.

    Args:
        event: {s3_key, report_text, strategy_performance, ticker, dr_symbol,
                yahoo_symbol, experiment?, job_id?, source, api_costs,
                generation_mode, model?, execution_id}
        context: Lambda context

    Returns:
        {status, quality_scores, placeholder_compliance, timing_ms, report_length}
    """
    start_time = time.perf_counter()
    ticker = event.get('ticker', 'UNKNOWN')
    dr_symbol = event.get('dr_symbol', ticker)
    yahoo_symbol = event.get('yahoo_symbol', ticker)
    s3_key = event.get('s3_key')
    report_text = event.get('report_text', '')
    is_experiment = event.get('experiment', False)
    job_id = event.get('job_id')
    source = event.get('source', 'unknown')
    api_costs = event.get('api_costs', {})
    generation_mode = event.get('generation_mode', 'single_pass')
    model = event.get('model', os.getenv('LLM_MODEL', 'openai/gpt-4o'))
    strategy_performance = event.get('strategy_performance', {})

    if not s3_key:
        raise ValueError("Missing 's3_key' field in event")
    if not report_text:
        raise ValueError("Missing 'report_text' field in event")

    logger.info(
        f"PostProcess handler invoked | ticker={ticker} | "
        f"source={source} | s3_key={s3_key}"
    )

    _validate_required_config()

    # Read raw data from S3
    from src.pipeline.s3_payload import read_payload
    raw_data = read_payload(s3_key)

    # Lazy imports
    from src.analysis.market_analyzer import MarketAnalyzer
    from src.analysis.technical_analysis import TechnicalAnalyzer
    from src.data.news_fetcher import NewsFetcher
    from src.report.number_injector import NumberInjector
    from src.report.prompt_builder import PromptBuilder
    from src.report.context_builder import ContextBuilder
    from src.scoring.scoring_service import ScoringService
    from src.formatters import DataFormatter

    market_analyzer = MarketAnalyzer()
    technical_analyzer = TechnicalAnalyzer()
    data_formatter = DataFormatter()
    context_builder = ContextBuilder(market_analyzer, data_formatter, technical_analyzer)
    prompt_builder = PromptBuilder(context_builder=context_builder)
    news_fetcher = NewsFetcher()
    number_injector = NumberInjector()
    scoring_service = ScoringService(enable_llm_scoring=False)

    # Step 1: Number injection + news references + transparency footer
    from src.pipeline.postprocess import inject_and_finalize
    finalized_report = inject_and_finalize(
        report_text=report_text,
        raw_data=raw_data,
        number_injector=number_injector,
        market_analyzer=market_analyzer,
        news_fetcher=news_fetcher,
        strategy_performance=strategy_performance or None,
    )

    # Step 2: Quality scoring + Langfuse + Aurora trace
    from src.pipeline.postprocess import compute_scores_and_store
    score_result = compute_scores_and_store(
        report_text=finalized_report,
        raw_data=raw_data,
        scoring_service=scoring_service,
        number_injector=number_injector,
        market_analyzer=market_analyzer,
        prompt_builder=prompt_builder,
        ticker_map={},  # Not needed for trace storage
        llm_model_name=model,
        api_costs=api_costs,
        is_experiment=is_experiment,
    )

    # Step 3: If NOT experiment, cache report in Aurora + update DynamoDB job
    if not is_experiment:
        _cache_and_complete(
            finalized_report=finalized_report,
            raw_data=raw_data,
            dr_symbol=dr_symbol,
            yahoo_symbol=yahoo_symbol,
            job_id=job_id,
            score_result=score_result,
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        f"PostProcess complete | ticker={ticker} | "
        f"report_length={len(finalized_report)} | timing={elapsed_ms:.0f}ms"
    )

    return {
        'status': 'success',
        'ticker': ticker,
        'quality_scores': score_result.get('quality_scores', {}),
        'placeholder_compliance': score_result.get('placeholder_compliance', 0),
        'placeholder_metrics': score_result.get('placeholder_metrics', {}),
        'timing_ms': round(elapsed_ms, 1),
        'report_length': len(finalized_report),
        'generation_mode': generation_mode,
    }


def _cache_and_complete(
    finalized_report: str,
    raw_data: dict,
    dr_symbol: str,
    yahoo_symbol: str,
    job_id: str = None,
    score_result: dict = None,
) -> None:
    """Cache report in Aurora and complete DynamoDB job if applicable."""
    # Transform to API format and cache
    try:
        from src.api.ticker_service import get_ticker_service
        from src.api.transformer import get_transformer
        from src.data.aurora.precompute_service import PrecomputeService
        import asyncio

        # Reconstruct a minimal state dict for the transformer
        state = dict(raw_data)
        state['report'] = finalized_report
        state['quality_scores'] = score_result.get('quality_scores', {}) if score_result else {}

        ticker_service = get_ticker_service()
        ticker_info = ticker_service.get_ticker_info(dr_symbol)
        transformer = get_transformer()
        response = asyncio.get_event_loop().run_until_complete(
            transformer.transform_report(state, ticker_info)
        )
        api_result = response.model_dump()

        # Cache in Aurora
        ps = PrecomputeService()
        success = ps.store_report_from_api(
            symbol=yahoo_symbol,
            report_text=api_result.get('narrative_report', ''),
            report_json=api_result,
            chart_base64=raw_data.get('chart_base64', ''),
        )
        if success:
            logger.info(f"Cached report for {yahoo_symbol}")
        else:
            logger.error(f"Failed to cache report for {yahoo_symbol}")

        # Complete DynamoDB job if job_id present
        if job_id:
            from src.api.job_service import get_job_service
            job_service = get_job_service()
            job_service.complete_job(job_id, api_result)
            logger.info(f"Completed job {job_id}")

    except Exception as e:
        logger.error(f"Cache/complete failed for {dr_symbol}: {e}", exc_info=True)
        # If job_id present, mark as failed
        if job_id:
            try:
                from src.api.job_service import get_job_service
                get_job_service().fail_job(job_id, str(e))
            except Exception:
                pass
