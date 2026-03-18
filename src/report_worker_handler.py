"""Report Worker Lambda Handler

Ports & Adapters architecture:
- generate_report(): Pure core — resolve ticker, run agent, return state + metrics
- _handle_job_mode(): Adapter — job tracking (DynamoDB) + transform + cache (Aurora)
- _handle_experiment_mode(): Adapter — return raw metrics, no side effects
- _handle_step_functions_mode(): Adapter — transform + cache, no job tracking

Flow:
  handler() routes by event shape → adapter calls generate_report() → adapter applies side effects
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from src.agent import TickerAnalysisAgent
from src.types import create_initial_state
from src.api.job_service import get_job_service
from src.api.ticker_service import get_ticker_service
from src.api.transformer import get_transformer
from src.data.aurora.precompute_service import PrecomputeService
from src.data.aurora.ticker_resolver import get_ticker_resolver

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)


class AgentError(Exception):
    """Raised when agent returns error in state."""
    pass


# ============================================================================
# Configuration
# ============================================================================

def _validate_required_config() -> None:
    """Validate required environment variables at startup. Fail fast."""
    required_vars = {
        'OPENROUTER_API_KEY': 'LLM report generation',
        'AURORA_HOST': 'Aurora database caching',
        'PDF_BUCKET_NAME': 'PDF report storage',
        'JOBS_TABLE_NAME': 'Job status tracking'
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"✅ All {len(required_vars)} required environment variables present")


def _init_metric_registry() -> None:
    """Initialize MetricRegistry from DB. Cached via singleton for warm starts."""
    from src.data.aurora.metric_config_repository import get_metric_config_repository
    from src.report.metric_registry import get_metric_registry
    try:
        db_statuses = get_metric_config_repository().get_all_statuses()
        get_metric_registry(db_statuses)
        logger.info(f"MetricRegistry initialized: {len(db_statuses)} metrics from DB")
    except Exception as e:
        logger.warning(f"Could not load metric_config from DB: {e}. MetricRegistry may not be available.")


# ============================================================================
# Core: Pure report generation (no side effects beyond Langfuse tracing)
# ============================================================================

def generate_report(ticker_raw: str, model: str = None, tags: list = None, data_date: str = None) -> dict:
    """Core report generation. Resolve ticker, run agent, return state + metrics.

    Args:
        ticker_raw: Ticker symbol (DR or Yahoo format)
        model: Optional LLM model override
        tags: Optional Langfuse trace tags (e.g. ["experiment"], ["job", "report_generation"])
        data_date: Optional ISO date string (e.g. "2026-03-16"). Defaults to today if not provided.

    Returns:
        {'state': AgentState, 'dr_symbol': str, 'yahoo_symbol': str,
         'placeholder_metrics': dict, 'placeholder_compliance': float}

    Raises:
        ValueError: If ticker cannot be resolved
        AgentError: If agent returns error in state
    """
    from src.integrations.langfuse_client import trace_context

    # Resolve ticker
    resolver = get_ticker_resolver()
    resolved = resolver.resolve(ticker_raw)
    if not resolved:
        raise ValueError(f"Unknown ticker: {ticker_raw}")

    dr_symbol = resolved.dr_symbol
    yahoo_symbol = resolved.yahoo_symbol
    logger.info(f"Generating report: {ticker_raw} → {dr_symbol} (DR) / {yahoo_symbol} (Yahoo), model={model}")

    # Create agent and run
    agent = TickerAnalysisAgent(model=model)
    initial_state = create_initial_state(dr_symbol.upper(), data_date=data_date or "")

    with trace_context(tags=tags, metadata={'ticker': dr_symbol, 'model': model, 'data_date': data_date}):
        final_state = agent.graph.invoke(initial_state)

    # Check for agent errors
    if final_state.get("error"):
        raise AgentError(final_state["error"])

    # Extract placeholder metrics
    ni = agent.workflow_nodes.number_injector
    last_metrics = getattr(ni, 'last_metrics', {}) or {}
    total = last_metrics.get('injected_count', 0) + last_metrics.get('unresolved_count', 0)
    compliance = (last_metrics['injected_count'] / total * 100) if total > 0 else 0

    return {
        'state': final_state,
        'dr_symbol': dr_symbol,
        'yahoo_symbol': yahoo_symbol,
        'placeholder_metrics': last_metrics,
        'placeholder_compliance': round(compliance, 1),
    }


# ============================================================================
# Adapter: Job mode (DynamoDB tracking + transform + cache)
# ============================================================================

async def _handle_job_mode(job_id: str, ticker_raw: str, model: str = None, data_date: str = None) -> None:
    """Process a job: track in DynamoDB, generate report, transform, cache.

    Raises:
        AgentError: If agent returns error (job marked as failed)
        Exception: Any other error (job marked as failed, re-raised for DLQ)
    """
    job_service = get_job_service()

    # Create + start job in DynamoDB
    created_at = datetime.now()
    ttl = int((created_at + timedelta(hours=24)).timestamp())
    job_service.table.put_item(Item={
        'job_id': job_id,
        'ticker': ticker_raw.upper(),
        'status': 'pending',
        'created_at': created_at.isoformat(),
        'ttl': ttl,
    })
    job_service.start_job(job_id)
    logger.info(f"Job {job_id} started for {ticker_raw}")

    try:
        # Core
        result = generate_report(ticker_raw, model=model, tags=["job", "report_generation"], data_date=data_date)
        state = result['state']

        # Transform to API format
        ticker_service = get_ticker_service()
        ticker_info = ticker_service.get_ticker_info(result['dr_symbol'])
        transformer = get_transformer()
        response = await transformer.transform_report(state, ticker_info)
        api_result = response.model_dump()

        # Complete job
        job_service.complete_job(job_id, api_result)
        logger.info(f"✅ Job {job_id} completed for {result['yahoo_symbol']}")

        # Cache report in Aurora
        ps = PrecomputeService()
        success = ps.store_report_from_api(
            symbol=result['yahoo_symbol'],
            report_text=api_result.get('narrative_report', ''),
            report_json=api_result,
            chart_base64=state.get('chart_base64', ''),
        )
        if success:
            logger.info(f"✅ Cached report for {result['yahoo_symbol']}")
        else:
            logger.error(f"❌ Failed to cache report for {result['yahoo_symbol']}")

    except AgentError as e:
        job_service.fail_job(job_id, str(e))
        raise
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            job_service.fail_job(job_id, str(e))
        except Exception as fail_error:
            logger.error(f"Failed to mark job {job_id} as failed: {fail_error}")
        raise


# ============================================================================
# Adapter: Experiment mode (return metrics, no side effects)
# ============================================================================

def _handle_experiment_mode(event: dict) -> dict:
    """Run experiment: generate report, return raw metrics. No job tracking, no cache."""
    ticker_raw = event['ticker']
    model = event.get('model')

    try:
        result = generate_report(ticker_raw, model=model, tags=["experiment"], data_date=event.get('data_date'))
        state = result['state']

        response = {
            'status': 'success',
            'ticker': result['dr_symbol'],
            'model': model or os.getenv('LLM_MODEL', 'openai/gpt-4o'),
            'data_date': state.get('data_date', ''),
            'placeholder_compliance': result['placeholder_compliance'],
            'placeholder_metrics': result['placeholder_metrics'],
            'quality_scores': state.get('quality_scores', {}),
            'timing_metrics': state.get('timing_metrics', {}),
            'api_costs': state.get('api_costs', {}),
            'report_length': len(state.get('report', '')),
            'error': '',
        }

        # Include full report data when requested (for local re-scoring)
        if event.get('include_report_data'):
            from src.utils.serialization import make_json_serializable
            response['report_text'] = state.get('report', '')
            indicators = state.get('indicators', {})
            response['scoring_context'] = {
                'indicators': make_json_serializable(indicators),
                'percentiles': make_json_serializable(state.get('percentiles', {})),
                'news': make_json_serializable(state.get('news', [])),
                'ticker_data': make_json_serializable(state.get('ticker_data', {})),
                'market_conditions': {
                    'uncertainty_score': indicators.get('uncertainty_score', 0),
                    'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                    if indicators.get('current_price', 0) > 0 else 0,
                    'price_vs_vwap_pct': indicators.get('price_vs_vwap_pct', 0),
                    'volume_ratio': indicators.get('volume_ratio', 0),
                },
            }

        return response
    except Exception as e:
        logger.error(f"Experiment failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'ticker': ticker_raw,
            'model': model,
            'error': str(e),
        }


# ============================================================================
# Adapter: Step Functions mode (transform + cache, no job tracking)
# ============================================================================

async def _handle_step_functions_mode(event: dict) -> dict:
    """Step Functions invocation: generate report, transform, cache. No DynamoDB job."""
    ticker_raw = event.get('ticker')
    if not ticker_raw:
        raise ValueError("Missing 'ticker' field in Step Functions event")

    try:
        result = generate_report(ticker_raw, model=event.get('model'), tags=["precompute", "report_generation"], data_date=event.get('data_date'))
        state = result['state']

        # Transform to API format
        ticker_service = get_ticker_service()
        ticker_info = ticker_service.get_ticker_info(result['dr_symbol'])
        transformer = get_transformer()
        response = await transformer.transform_report(state, ticker_info)
        api_result = response.model_dump()

        # Cache report in Aurora
        ps = PrecomputeService()
        ps.store_report_from_api(
            symbol=result['yahoo_symbol'],
            report_text=api_result.get('narrative_report', ''),
            report_json=api_result,
            chart_base64=state.get('chart_base64', ''),
        )

        logger.info(f"✅ Step Functions: completed {ticker_raw}")
        return {'ticker': ticker_raw, 'status': 'success', 'error': ''}

    except Exception as e:
        logger.error(f"Step Functions failed for {ticker_raw}: {e}")
        return {'ticker': ticker_raw, 'status': 'failed', 'error': str(e)}


# ============================================================================
# Router: Lambda entry point
# ============================================================================

def handler(event: dict, context: Any) -> dict:
    """Lambda handler — routes to adapters by event shape.

    Modes:
    1. Migration:      {'migration': 'name'}
    2. Experiment:     {'experiment': true, 'ticker': 'X', 'model': '...'}
    3. Direct job:     {'job_id': 'xxx', 'ticker': 'X'}
    4. Step Functions: {'ticker': 'X', 'source': 'precompute'}
    5. SQS:            {'Records': [...]}
    """
    # Migration mode (priority: check first, no config validation needed)
    if 'migration' in event:
        logger.info(f"Detected migration request: {event.get('migration')}")
        from src.migration_handler import lambda_handler as migration_lambda_handler
        return migration_lambda_handler(event, context)

    # Validate config + init registry
    _validate_required_config()
    _init_metric_registry()

    # Experiment mode (no job tracking, no cache)
    if event.get('experiment') and 'ticker' in event:
        logger.info(f"🧪 Experiment mode: ticker={event['ticker']}, model={event.get('model', 'default')}")
        return _handle_experiment_mode(event)

    # Direct invocation with job tracking
    if 'job_id' in event and 'ticker' in event:
        logger.info(f"📋 Job mode: job_id={event['job_id']}, ticker={event['ticker']}")
        asyncio.run(_handle_job_mode(event['job_id'], event['ticker'], event.get('model'), event.get('data_date')))
        return {'statusCode': 200, 'ticker': event['ticker'], 'job_id': event['job_id']}

    # Step Functions invocation
    if 'ticker' in event and 'source' in event:
        logger.info(f"⚙️ Step Functions mode: ticker={event['ticker']}")
        return asyncio.run(_handle_step_functions_mode(event))

    # SQS mode (backward compatible)
    if 'Records' in event:
        records = event['Records']
        logger.info(f"📨 SQS mode: processing {len(records)} records")
        for record in records:
            message = json.loads(record.get('body', '{}'))
            asyncio.run(_handle_job_mode(message['job_id'], message['ticker'], message.get('model'), message.get('data_date')))
        return {'statusCode': 200, 'processed': len(records)}

    # Unknown event format
    logger.error(f"❌ Unknown event format: {json.dumps(event)}")
    raise ValueError(f"Unknown event format: {json.dumps(event)}")
