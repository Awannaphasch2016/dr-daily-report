"""Report Worker Lambda Handler

Processes SQS messages for async report generation.
Each message contains job_id and ticker to analyze.

Flow:
1. Parse SQS message (job_id, ticker)
2. Mark job as in_progress
3. Run TickerAnalysisAgent
4. Transform result to API format
5. Mark job as completed (or failed)
"""

import asyncio
import json
import logging
from typing import Any

from src.agent import TickerAnalysisAgent
from src.types import AgentState
from src.api.job_service import get_job_service
from src.api.ticker_service import get_ticker_service
from src.api.transformer import get_transformer
from src.data.aurora.precompute_service import PrecomputeService
from src.data.aurora.ticker_resolver import get_ticker_resolver

# Configure logging
# NOTE: In Lambda, basicConfig() is a no-op because Lambda pre-configures the root logger.
# Instead, get the logger and explicitly set its level.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Also ensure the root logger level allows INFO through (Lambda default may be WARNING)
logging.getLogger().setLevel(logging.INFO)


class AgentError(Exception):
    """Raised when agent returns error in state (already marked as failed)"""
    pass


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for SQS report generation messages

    Processes each SQS record:
    1. Parse job_id and ticker from message body
    2. Mark job as in_progress
    3. Run analysis agent
    4. Transform and store result
    5. Mark job as completed/failed

    Args:
        event: SQS event with Records array
        context: Lambda context (unused)

    Returns:
        Dict with processing status

    Raises:
        Exception: Re-raised after marking job as failed (for DLQ)
    """
    records = event.get('Records', [])
    logger.info(f"Processing {len(records)} SQS records")

    for record in records:
        # Use asyncio.run() for async transformer.transform_report()
        asyncio.run(process_record(record))

    return {'statusCode': 200, 'body': f'Processed {len(records)} records'}


async def process_record(record: dict) -> None:
    """Process a single SQS record

    Args:
        record: SQS record with messageId and body

    Raises:
        Exception: Re-raised after marking job as failed
    """
    message_id = record.get('messageId', 'unknown')
    body = record.get('body', '')

    job_id = None
    ticker = None

    try:
        # Parse message body
        message = json.loads(body)
        job_id = message['job_id']
        ticker_raw = message['ticker']

        # Defensive validation: Resolve ticker to canonical form
        # This handles both DR symbols (DBS19) and Yahoo symbols (D05.SI)
        resolver = get_ticker_resolver()
        resolved = resolver.resolve(ticker_raw)

        if not resolved:
            error_msg = f"Unknown ticker: {ticker_raw}"
            logger.error(f"Job {job_id}: {error_msg}")
            job_service = get_job_service()
            job_service.fail_job(job_id, error_msg)
            raise ValueError(error_msg)

        # Use DR symbol for consistency
        ticker = resolved.dr_symbol
        logger.info(f"Processing job {job_id} for ticker {ticker} (resolved from {ticker_raw})")

        # Get services
        job_service = get_job_service()
        ticker_service = get_ticker_service()
        transformer = get_transformer()

        # Mark job as in_progress
        job_service.start_job(job_id)

        # Get ticker info
        ticker_info = ticker_service.get_ticker_info(ticker)

        # Initialize agent
        agent = TickerAnalysisAgent()

        # Create initial state
        initial_state: AgentState = {
            "messages": [],
            "ticker": ticker.upper(),
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "error": "",
            "strategy": "multi_stage_analysis"
        }

        # Run analysis
        final_state = agent.graph.invoke(initial_state)

        # Check for agent errors
        if final_state.get("error"):
            error_msg = final_state["error"]
            logger.error(f"Agent error for {ticker}: {error_msg}")
            job_service.fail_job(job_id, error_msg)
            # Raise with special marker to avoid double fail_job call
            raise AgentError(error_msg)

        # Transform to API response format (async method)
        response = await transformer.transform_report(final_state, ticker_info)
        result = response.model_dump()

        # Mark job as completed in DynamoDB
        job_service.complete_job(job_id, result)
        logger.info(f"Completed job {job_id} for ticker {ticker}")

        # Store to Aurora cache for future cache hits (enables cache-first behavior)
        try:
            logger.info(f"Attempting to cache report in Aurora for {ticker}")
            precompute_service = PrecomputeService()
            # Map API strategy name to MySQL ENUM value
            api_strategy = result.get('generation_metadata', {}).get('strategy', 'multi_stage_analysis')
            db_strategy = 'multi-stage' if 'multi' in api_strategy.lower() else 'single-stage'
            cache_result = precompute_service.store_report_from_api(
                symbol=ticker,
                report_text=result.get('narrative_report', ''),
                report_json=result,
                strategy=db_strategy,
                chart_base64=final_state.get('chart_base64', ''),
            )
            if cache_result:
                logger.info(f"✅ Cached report in Aurora for {ticker}")
            else:
                logger.warning(f"⚠️ store_report_from_api returned False for {ticker}")
        except Exception as cache_error:
            # Log but don't fail the job - DynamoDB result is the primary store
            logger.error(f"❌ Failed to cache report in Aurora for {ticker}: {cache_error}", exc_info=True)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in message body: {e}"
        logger.error(f"Message {message_id}: {error_msg}")
        raise Exception(error_msg)

    except KeyError as e:
        error_msg = f"Missing required field in message: {e}"
        logger.error(f"Message {message_id}: {error_msg}")
        raise Exception(error_msg)

    except AgentError:
        # Job already marked as failed, just re-raise for SQS DLQ
        raise

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process job {job_id}: {error_msg}")

        # Mark job as failed if we have job_id
        if job_id:
            try:
                job_service = get_job_service()
                job_service.fail_job(job_id, error_msg)
            except Exception as fail_error:
                logger.error(f"Failed to mark job {job_id} as failed: {fail_error}")

        # Re-raise for SQS retry/DLQ
        raise
