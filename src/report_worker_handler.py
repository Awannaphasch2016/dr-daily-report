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
    """Lambda handler for SQS report generation messages and migrations

    Two modes:
    1. SQS Mode (default): Processes SQS records for async report generation
    2. Migration Mode: Routes to migration_handler for database migrations

    Args:
        event: SQS event with Records array OR direct invocation with 'migration' key
        context: Lambda context (unused)

    Returns:
        Dict with processing status

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
        # STEP 4.5: Generate PDF (for scheduled workflows)
        # ========================================
        # Context: Workers are triggered by:
        #   1. Telegram API requests (user-initiated) - job_id exists, no PDF needed
        #   2. Scheduled workflows (Step Functions) - no job_id, PDF needed
        #
        # Strategy: Generate PDF if:
        #   - No job_id (scheduled workflow), OR
        #   - Message explicitly requests PDF (generate_pdf flag)
        #
        # Graceful degradation: If PDF fails, continue without it (report is still valid)

        pdf_s3_key = None
        pdf_generated_at = None

        # Determine if PDF should be generated:
        # 1. Scheduled workflows (Step Functions) have source="step_functions_precompute"
        # 2. API requests can explicitly request PDF with generate_pdf=true flag
        is_scheduled = message.get('source') == 'step_functions_precompute'
        explicitly_requested = message.get('generate_pdf', False)

        should_generate_pdf = is_scheduled or explicitly_requested

        if should_generate_pdf and final_state.get('report'):
            try:
                logger.info(f"📄 Generating PDF for {ticker}...")

                from datetime import datetime, date

                ps = PrecomputeService()

                # Generate and upload PDF using existing method
                pdf_s3_key = ps._generate_and_upload_pdf(
                    symbol=ticker,
                    data_date=date.today(),
                    report_text=final_state.get('report', ''),
                    chart_base64=final_state.get('chart_base64', '')
                )

                if pdf_s3_key:
                    pdf_generated_at = datetime.now()
                    logger.info(f"✅ Generated PDF: {pdf_s3_key}")
                else:
                    logger.warning(f"⚠️ PDF generation returned None for {ticker}")

            except Exception as e:
                logger.warning(f"⚠️ PDF generation failed for {ticker}: {e}")
                # Continue without PDF - report is still valid
                # Don't re-raise - graceful degradation

        else:
            if not final_state.get('report'):
                logger.info(f"ℹ️ Skipping PDF generation (no report text) for {ticker}")
            elif is_scheduled:
                logger.warning(f"⚠️ PDF generation disabled despite scheduled workflow for {ticker}")
            else:
                logger.info(f"ℹ️ Skipping PDF generation (API request) for {ticker}")

        # Store to Aurora cache for future cache hits (enables cache-first behavior)
        try:
            logger.info(f"Attempting to cache report in Aurora for {ticker}")
            precompute_service = PrecomputeService()
            # Store report (strategy field no longer needed - using Semantic Layer Architecture)
            cache_result = precompute_service.store_report_from_api(
                symbol=ticker,
                report_text=result.get('narrative_report', ''),
                report_json=result,
                chart_base64=final_state.get('chart_base64', ''),
                pdf_s3_key=pdf_s3_key,
                pdf_generated_at=pdf_generated_at,
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
