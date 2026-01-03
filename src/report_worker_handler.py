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
import os
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


def _validate_required_config() -> None:
    """Validate required environment variables at startup

    Defensive programming principle from CLAUDE.md:
    'Validate configuration at startup, not on first use (prevents production surprises)'

    This catches missing/empty environment variables immediately, preventing wasted
    compute on jobs that will inevitably fail during workflow execution.

    Raises:
        ValueError: If any required environment variable is missing or empty
    """
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
        error_msg += "\nThis Lambda cannot process jobs without these environment variables."
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"✅ All {len(required_vars)} required environment variables present")


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for SQS report generation messages, Step Functions, and migrations

    Three modes:
    1. SQS Mode (default): Processes SQS records for async report generation
    2. Direct Mode: Step Functions invocation for precompute workflow
    3. Migration Mode: Routes to migration_handler for database migrations

    Args:
        event: SQS event with Records array OR
               Step Functions event with ticker/source OR
               direct invocation with 'migration' key
        context: Lambda context (unused)

    Returns:
        Dict with processing status (SQS/migration) or
        Dict with ticker result (Step Functions direct mode)

    Raises:
        ValueError: If required environment variables are missing
        Exception: Re-raised after marking job as failed (for DLQ)
    """
    # Check if this is a migration request (direct invocation)
    if 'migration' in event:
        logger.info(f"Detected migration request: {event.get('migration')}")
        from src.migration_handler import lambda_handler as migration_lambda_handler
        return migration_lambda_handler(event, context)

    # Validate configuration at startup - fail fast!
    # Defensive programming: catch missing env vars before wasting compute
    _validate_required_config()

    # Direct Step Functions invocation mode
    if 'ticker' in event and 'source' in event:
        logger.info(f"Direct Step Functions invocation: {event.get('ticker')}")
        result = asyncio.run(process_ticker_direct(event))
        return result

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

        # Use Yahoo symbol for Aurora data queries
        # ticker_data is stored with Yahoo symbols (D05.SI, NVDA, 1378.HK)
        # Workers receive DR symbols from SQS but must query Aurora with Yahoo symbols
        ticker = resolved.yahoo_symbol
        dr_symbol = resolved.dr_symbol  # Keep for reference
        logger.info(f"Processing job {job_id} for ticker {ticker_raw} → {ticker} (Yahoo) / {dr_symbol} (DR)")

        # Get services
        job_service = get_job_service()
        ticker_service = get_ticker_service()
        transformer = get_transformer()

        # Mark job as in_progress
        job_service.start_job(job_id)

        # Get ticker info (ticker_service expects DR symbol, not Yahoo symbol)
        ticker_info = ticker_service.get_ticker_info(dr_symbol)

        # Initialize agent
        agent = TickerAnalysisAgent()

        # Create initial state
        # NOTE: state['ticker'] must be DR symbol (workflow nodes expect it for their ticker_map lookups)
        initial_state: AgentState = {
            "messages": [],
            "ticker": dr_symbol.upper(),
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

        # ========================================
        # STEP 4.5: Store Report (PDF generated separately)
        # ========================================
        # Note: PDF generation moved to separate Step Function workflow
        # This worker ONLY generates and stores the report

        try:
            logger.info(f"====== Storing Report ======")
            ps = PrecomputeService()

            # Store report WITHOUT PDF (PDF workflow handles it)
            success = ps.store_report_from_api(
                symbol=ticker,
                report_text=result.get('narrative_report', ''),
                report_json=result,
                chart_base64=final_state.get('chart_base64', ''),
                pdf_s3_key=None,           # PDF generated in separate workflow
                pdf_generated_at=None,
            )

            if not success:
                logger.error(f"❌ Failed to store report for {ticker}")
                raise ValueError(f"Failed to store report for {ticker}")

            logger.info(f"✅ Stored report for {ticker}")

        except Exception as e:
            logger.error(f"❌ Failed to store report for {ticker}: {e}", exc_info=True)
            raise  # Re-raise to fail job (SQS will retry or DLQ)

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


async def process_ticker_direct(event: dict) -> dict:
    """Process single ticker from direct Step Functions invocation.

    Args:
        event: {"ticker": "DBS19", "execution_id": "exec_123", "source": "step_functions_precompute"}

    Returns:
        {"ticker": "DBS19", "status": "success"|"failed", "pdf_s3_key": "...", "error": ""}

    Raises:
        ValueError: If 'ticker' field is missing
    """
    ticker_raw = event.get('ticker')
    execution_id = event.get('execution_id', 'unknown')

    if not ticker_raw:
        raise ValueError("Missing 'ticker' field in direct invocation event")

    try:
        # Create synthetic SQS message to reuse process_record() logic
        synthetic_body = json.dumps({
            'job_id': f'sfn_{execution_id}_{ticker_raw}',
            'ticker': ticker_raw,
            'source': event.get('source'),
            'generate_pdf': True
        })

        synthetic_record = {
            'messageId': f'direct_{execution_id}',
            'body': synthetic_body
        }

        # Reuse existing processing logic
        await process_record(synthetic_record)

        # Get result from DynamoDB
        job_service = get_job_service()
        job_status = job_service.get_job_status(f'sfn_{execution_id}_{ticker_raw}')

        if job_status.get('status') == 'completed':
            return {
                'ticker': ticker_raw,
                'status': 'success',
                'pdf_s3_key': job_status.get('result', {}).get('pdf_s3_key'),
                'error': ''
            }
        else:
            return {
                'ticker': ticker_raw,
                'status': 'failed',
                'pdf_s3_key': None,
                'error': job_status.get('error', 'Unknown error')
            }

    except Exception as e:
        logger.error(f"Failed to process {ticker_raw}: {e}")
        return {
            'ticker': ticker_raw,
            'status': 'failed',
            'pdf_s3_key': None,
            'error': str(e)
        }
