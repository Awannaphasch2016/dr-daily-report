"""PreProcess Lambda Handler — Data pipeline phase.

Runs the data-only LangGraph (all data fetching, no report generation),
serializes raw data + chart to S3, and returns metadata for downstream phases.

Invoked by the Report Pipeline Step Functions state machine.

Input event:
    {ticker, data_date?, generation_strategy?, experiment?, job_id?, source, model?}

Output:
    {s3_key, ticker, dr_symbol, yahoo_symbol, generation_strategy,
     experiment, job_id, source, model, data_date, timing_ms}
"""

import json
import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)


def _validate_required_config() -> None:
    """Validate required environment variables. Fail fast."""
    required_vars = {
        'OPENROUTER_API_KEY': 'LLM initialization (even for data-only graph)',
        'AURORA_HOST': 'Aurora database (MetricRegistry, ticker resolution)',
        'DATA_LAKE_BUCKET': 'S3 intermediate payload storage',
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
    """PreProcess Lambda handler — run data pipeline, write state to S3.

    Args:
        event: {ticker, data_date?, generation_strategy?, experiment?,
                job_id?, source, model?}
        context: Lambda context

    Returns:
        {s3_key, ticker, dr_symbol, yahoo_symbol, generation_strategy,
         experiment, job_id, source, model, data_date, timing_ms}
    """
    start_time = time.perf_counter()
    ticker_raw = event.get('ticker')
    if not ticker_raw:
        raise ValueError("Missing 'ticker' field in event")

    logger.info(
        f"PreProcess handler invoked | ticker={ticker_raw} | "
        f"source={event.get('source', 'unknown')}"
    )

    _validate_required_config()

    # Init MetricRegistry (cached via singleton)
    try:
        from src.data.aurora.metric_config_repository import get_metric_config_repository
        from src.report.metric_registry import get_metric_registry
        db_statuses = get_metric_config_repository().get_all_statuses()
        get_metric_registry(db_statuses)
        logger.info(f"MetricRegistry initialized: {len(db_statuses)} metrics from DB")
    except Exception as e:
        logger.warning(f"Could not load metric_config from DB: {e}")

    # Resolve ticker
    from src.data.aurora.ticker_resolver import get_ticker_resolver
    resolver = get_ticker_resolver()
    resolved = resolver.resolve(ticker_raw)
    if not resolved:
        raise ValueError(f"Unknown ticker: {ticker_raw}")

    dr_symbol = resolved.dr_symbol
    yahoo_symbol = resolved.yahoo_symbol
    model = event.get('model')
    data_date = event.get('data_date', '')

    logger.info(f"Resolved: {ticker_raw} -> {dr_symbol} (DR) / {yahoo_symbol} (Yahoo)")

    # Run data-only pipeline
    from src.pipeline.data_pipeline import run_data_pipeline
    final_state = run_data_pipeline(
        ticker=dr_symbol.upper(),
        model=model,
        data_date=data_date,
    )

    # Serialize raw data + chart to S3
    from src.types import extract_raw_data_for_storage
    from src.pipeline.s3_payload import write_payload

    raw_data = extract_raw_data_for_storage(final_state)
    raw_data['chart_base64'] = final_state.get('chart_base64', '')
    raw_data['data_date'] = final_state.get('data_date', data_date)
    raw_data['timing_metrics'] = final_state.get('timing_metrics', {})
    raw_data['user_facing_scores'] = final_state.get('user_facing_scores', {})

    execution_id = event.get('execution_id') or str(uuid.uuid4())
    s3_key = write_payload(execution_id, raw_data)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    generation_strategy = event.get('generation_strategy', 'single_pass')

    logger.info(
        f"PreProcess complete | ticker={dr_symbol} | "
        f"s3_key={s3_key} | timing={elapsed_ms:.0f}ms"
    )

    return {
        's3_key': s3_key,
        'ticker': ticker_raw,
        'dr_symbol': dr_symbol,
        'yahoo_symbol': yahoo_symbol,
        'generation_strategy': generation_strategy,
        'experiment': event.get('experiment', False),
        'job_id': event.get('job_id'),
        'source': event.get('source', 'unknown'),
        'model': model or os.getenv('LLM_MODEL', 'openai/gpt-4o'),
        'data_date': data_date,
        'timing_ms': round(elapsed_ms, 1),
        'execution_id': execution_id,
    }
