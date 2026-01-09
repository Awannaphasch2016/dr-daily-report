"""FastAPI application for Telegram Mini App backend

Version: 1.0.1 - CI/CD pipeline verification
"""

from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime
import logging
import os
import json
import boto3

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models import (
    SearchResponse,
    ReportResponse,
    RankingsResponse,
    RankedTicker,
    WatchlistResponse,
    WatchlistAddRequest,
    WatchlistOperationResponse,
    JobSubmitResponse,
    JobStatusResponse
)
from .errors import (
    APIError,
    InvalidRequestError,
    TickerNotSupportedError,
    api_exception_handler
)
from .ticker_service import get_ticker_service
from .watchlist_service import get_watchlist_service
from .rankings_service import get_rankings_service
from .job_service import get_job_service, JobNotFoundError
from .telegram_auth import get_telegram_auth, TelegramAuthError

# Configure logging
# NOTE: In Lambda, basicConfig() is a no-op because Lambda pre-configures the root logger.
# Instead, get the logger and explicitly set its level.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Also ensure the root logger level allows INFO through (Lambda default may be WARNING)
logging.getLogger().setLevel(logging.INFO)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Financial Securities AI Report API",
    description="API for Telegram Mini App",
    version="1.0.0"
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware for Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Telegram origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
app.add_exception_handler(APIError, api_exception_handler)


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_id_from_header(
    x_telegram_init_data: str | None = None,
    x_telegram_user_id: str | None = None
) -> str:
    """Extract and validate user ID from Telegram WebApp headers

    Supports two authentication modes:
    1. Production: X-Telegram-Init-Data header with HMAC validation
    2. Development: X-Telegram-User-Id header for testing

    Args:
        x_telegram_init_data: Full initData string from Telegram WebApp (production)
        x_telegram_user_id: Simple user ID for testing (development)

    Returns:
        Validated user ID string

    Raises:
        InvalidRequestError: If authentication fails
    """
    # Try production auth first (initData with HMAC validation)
    if x_telegram_init_data:
        try:
            auth = get_telegram_auth()
            user_id = auth.get_user_id(x_telegram_init_data)
            logger.info(f"✅ Authenticated user via initData: {user_id}")
            return user_id
        except TelegramAuthError as e:
            logger.warning(f"initData validation failed: {e}")
            raise InvalidRequestError(f"Telegram authentication failed: {e}")

    # Fallback to simple header for development/testing
    if x_telegram_user_id:
        logger.info(f"⚠️ Using development auth for user: {x_telegram_user_id}")
        return x_telegram_user_id

    raise InvalidRequestError(
        "Missing user authentication. Provide X-Telegram-Init-Data (production) "
        "or X-Telegram-User-Id (development) header."
    )


def invoke_report_worker(job_id: str, ticker: str) -> None:
    """Invoke report worker Lambda directly for async processing

    Uses direct Lambda invocation with Event invocation type (async)
    to maintain request-response decoupling for long-running report generation.

    Args:
        job_id: Unique job identifier
        ticker: Ticker symbol to analyze

    Raises:
        ValueError: If REPORT_WORKER_FUNCTION_NAME environment variable not set
        ClientError: If Lambda invocation fails (permission denied, function not found, etc.)

    Example:
        >>> invoke_report_worker('job-123', 'NVDA19')
        # Logs: "✅ Invoked report worker for job job-123 (ticker: NVDA19)"
    """
    import boto3
    import json

    lambda_client = boto3.client('lambda')

    function_name = os.getenv('REPORT_WORKER_FUNCTION_NAME')
    if not function_name:
        raise ValueError(
            "REPORT_WORKER_FUNCTION_NAME environment variable not set. "
            "Cannot invoke report worker Lambda. "
            "Check Terraform configuration."
        )

    try:
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # Async invocation (fire-and-forget)
            Payload=json.dumps({
                'job_id': job_id,
                'ticker': ticker,
                'source': 'telegram_api'  # For tracing in CloudWatch logs
            })
        )

        logger.info(f"✅ Invoked report worker for job {job_id} (ticker: {ticker})")

    except Exception as e:
        logger.error(f"❌ Failed to invoke report worker: {e}")
        raise


# Custom error handler for JobNotFoundError
class JobNotFoundAPIError(APIError):
    """Job not found error"""
    def __init__(self, job_id: str):
        super().__init__(
            code="JOB_NOT_FOUND",
            message=f"Job not found: {job_id}",
            status_code=404
        )


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/search", response_model=SearchResponse)
@limiter.limit("60/minute")  # 60 search requests per minute per IP
async def search_tickers(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (ticker or company name)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """Search for tickers by query string

    Args:
        q: Partial ticker or company name (min 1 char)
        limit: Maximum results (default 10, max 50)

    Returns:
        SearchResponse with list of matching tickers
    """
    try:
        ticker_service = get_ticker_service()
        results = ticker_service.search(q, limit)

        logger.info(f"Search query='{q}' returned {len(results)} results")

        return SearchResponse(results=results)

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise InvalidRequestError(f"Search failed: {str(e)}")


@app.get("/api/v1/report/{ticker}", response_model=ReportResponse)
@limiter.limit("10/minute")  # 10 report requests per minute per IP (expensive LLM calls)
async def get_report(
    request: Request,
    ticker: str,
    force_refresh: bool = Query(False, description="Force report regeneration"),
    lang: str | None = Query(None, description="Language code (future use)")
):
    """Get full AI report for a ticker

    Args:
        ticker: Ticker symbol (e.g., NVDA19)
        force_refresh: If true, regenerate report (ignore cache)
        lang: Language code (optional, for future localization)

    Returns:
        ReportResponse with full ticker analysis
    """
    try:
        from src.agent import TickerAnalysisAgent
        from src.types import AgentState
        from .transformer import get_transformer

        ticker_service = get_ticker_service()
        ticker_upper = ticker.upper()

        # Validate ticker is supported
        if not ticker_service.is_supported(ticker_upper):
            raise TickerNotSupportedError(ticker)

        # Get ticker info
        ticker_info = ticker_service.get_ticker_info(ticker_upper)

        # Check for cached report in Aurora (unless force_refresh)
        if not force_refresh:
            try:
                from src.data.aurora.precompute_service import PrecomputeService
                import time

                cache_start = time.time()
                precompute_service = PrecomputeService()
                # Use yahoo_ticker (e.g., NVDA) instead of symbol (e.g., NVDA19) for cache lookup
                yahoo_ticker = ticker_info.get('yahoo_ticker', ticker_upper)
                cached_report = precompute_service.get_cached_report(yahoo_ticker)

                if cached_report and cached_report.get('report_text'):
                    cache_duration = time.time() - cache_start
                    logger.info(f"✅ Cache HIT for {ticker_upper} ({cache_duration:.3f}s)")

                    # Transform cached report to API response
                    transformer = get_transformer()
                    response = await transformer.transform_cached_report(
                        cached_report,
                        ticker_info
                    )
                    return response
                else:
                    logger.info(f"Cache MISS for {ticker_upper} - generating on-demand")

            except Exception as e:
                logger.warning(f"Cache check failed for {ticker_upper}: {e} - falling back to on-demand")

        logger.info(f"Generating report for {ticker_upper}")

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
        }

        # Run analysis
        final_state = agent.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            logger.error(f"Agent error for {ticker}: {final_state['error']}")
            raise HTTPException(
                status_code=400,
                detail=f"Analysis failed: {final_state['error']}"
            )

        # Transform to API response format
        transformer = get_transformer()
        response = await transformer.transform_report(final_state, ticker_info)

        logger.info(f"Successfully generated report for {ticker}")

        return response

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Report error for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Async Report Endpoints
# ============================================================================

@app.post("/api/v1/report/{ticker}", response_model=JobSubmitResponse)
@limiter.limit("20/minute")  # 20 async job submissions per minute per IP
async def submit_report_async(
    request: Request,
    ticker: str,
    force_refresh: bool = Query(False, description="Force report regeneration (ignore cache)")
):
    """Submit async report generation job

    First checks Aurora cache for an existing precomputed report. If found,
    returns immediately with a "cached" job_id (prefixed with "cached_").
    Otherwise, creates a job for async report generation and sends it to SQS queue.

    This cache-first approach enables <500ms response times for precomputed reports.

    Args:
        ticker: Ticker symbol (e.g., NVDA19)
        force_refresh: If true, skip cache and always generate new report

    Returns:
        JobSubmitResponse with job_id and status
    """
    try:
        import time

        ticker_upper = ticker.upper()
        ticker_service = get_ticker_service()

        # Validate ticker is supported
        if not ticker_service.is_supported(ticker_upper):
            raise TickerNotSupportedError(ticker)

        # ================================================================
        # CACHE-FIRST: Check Aurora precomputed_reports before creating job
        # ================================================================
        if not force_refresh:
            try:
                from src.data.aurora.precompute_service import PrecomputeService

                cache_start = time.time()
                precompute_service = PrecomputeService()

                # Get ticker info to resolve yahoo_ticker
                ticker_info = ticker_service.get_ticker_info(ticker_upper)
                yahoo_ticker = ticker_info.get('yahoo_ticker', ticker_upper)

                # Check cache using ticker_master_id (works with any symbol format)
                cached_report = precompute_service.get_cached_report(yahoo_ticker)

                if cached_report and cached_report.get('report_text'):
                    cache_duration = time.time() - cache_start
                    logger.info(
                        f"✅ CACHE HIT for {ticker_upper} (yahoo={yahoo_ticker}) "
                        f"in {cache_duration:.3f}s - returning cached job_id"
                    )

                    # Return a special "cached" job_id that status endpoint recognizes
                    # This allows clients to poll normally but get instant results
                    cached_job_id = f"cached_{yahoo_ticker}_{cached_report.get('id', 'unknown')}"

                    return JobSubmitResponse(
                        job_id=cached_job_id,
                        status="completed"  # Already completed (cached)
                    )
                else:
                    logger.info(f"Cache MISS for {ticker_upper} - creating async job")

            except Exception as e:
                logger.warning(f"Cache check failed for {ticker_upper}: {e} - falling back to async job")

        # ================================================================
        # CACHE MISS: Create async job as before
        # ================================================================

        # Create job in DynamoDB
        job_service = get_job_service()
        job = job_service.create_job(ticker=ticker_upper)

        # Invoke report worker Lambda directly for async processing
        invoke_report_worker(job.job_id, ticker_upper)

        logger.info(f"Submitted async report job {job.job_id} for {ticker_upper}")

        return JobSubmitResponse(
            job_id=job.job_id,
            status="pending"
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to submit report job for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/report/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of async report job

    Polls job status from DynamoDB. Returns result when completed.

    Special handling for cached job_ids (prefixed with "cached_"):
    - These are returned when a precomputed report exists
    - Fetches the report directly from Aurora cache
    - Returns immediately with completed status and result

    Args:
        job_id: Job identifier from submit_report_async

    Returns:
        JobStatusResponse with current status and result (if completed)
    """
    try:
        # ================================================================
        # Handle cached job_ids (from precomputed reports)
        # ================================================================
        if job_id.startswith("cached_"):
            # Extract ticker from cached_job_id format: "cached_{yahoo_ticker}_{id}"
            parts = job_id.split("_", 2)  # ["cached", yahoo_ticker, id]
            if len(parts) >= 2:
                yahoo_ticker = parts[1]

                try:
                    from src.data.aurora.precompute_service import PrecomputeService
                    from .transformer import get_transformer

                    precompute_service = PrecomputeService()
                    cached_report = precompute_service.get_cached_report(yahoo_ticker)

                    if cached_report and cached_report.get('report_text'):
                        # Get ticker info for transformation
                        ticker_service = get_ticker_service()

                        # Try to find matching ticker in service
                        # Note: cached reports use yahoo_ticker (e.g., NVDA), not DR symbol (e.g., NVDA19)
                        ticker_info = None
                        try:
                            # Search for ticker to get full info
                            search_results = ticker_service.search(yahoo_ticker, limit=1)
                            if search_results:
                                ticker_info = ticker_service.get_ticker_info(search_results[0].ticker)
                        except Exception:
                            pass

                        if ticker_info is None:
                            ticker_info = {
                                'ticker': yahoo_ticker,
                                'yahoo_ticker': yahoo_ticker,
                                'name': cached_report.get('symbol', yahoo_ticker)
                            }

                        # Transform cached report to API response
                        transformer = get_transformer()
                        result = await transformer.transform_cached_report(
                            cached_report,
                            ticker_info
                        )

                        logger.info(f"✅ Returning cached report for {yahoo_ticker}")

                        return JobStatusResponse(
                            job_id=job_id,
                            ticker=yahoo_ticker,
                            status="completed",
                            created_at=cached_report.get('report_generated_at') or cached_report.get('computed_at'),
                            started_at=cached_report.get('report_generated_at') or cached_report.get('computed_at'),
                            finished_at=cached_report.get('report_generated_at') or cached_report.get('computed_at'),
                            result=result.model_dump() if hasattr(result, 'model_dump') else result,
                            error=None
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch cached report for {job_id}: {e}")
                    # Fall through to regular job lookup (will raise JobNotFoundError)

        # ================================================================
        # Regular job lookup from DynamoDB
        # ================================================================
        job_service = get_job_service()
        job = job_service.get_job(job_id)

        return JobStatusResponse(
            job_id=job.job_id,
            ticker=job.ticker,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            result=job.result,
            error=job.error
        )

    except JobNotFoundError:
        raise JobNotFoundAPIError(job_id)
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/rankings", response_model=RankingsResponse)
@limiter.limit("60/minute")  # 60 ranking requests per minute per IP
async def get_rankings(
    request: Request,
    category: Literal["top_gainers", "top_losers", "volume_surge", "trending"] = Query(..., description="Ranking category"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Get market movers / ranked tickers

    Fetches real-time market data for all 47 supported tickers and returns ranked results
    based on the selected category. Results are cached for 5 minutes to reduce API calls.

    Args:
        category: Ranking type (top_gainers, top_losers, volume_surge, trending)
        limit: Maximum results (default 10, max 50)

    Returns:
        RankingsResponse with ranked tickers

    Example:
        GET /api/v1/rankings?category=top_gainers&limit=10
    """
    try:
        rankings_service = get_rankings_service()
        ranking_items = await rankings_service.get_rankings(category, limit=limit)

        logger.info(f"Rankings {category}: {len(ranking_items)} results")

        # Transform dict to RankedTicker (includes chart_data and key_scores from cache)
        tickers = [
            RankedTicker(
                ticker=item['ticker'],
                company_name=item['company_name'],
                price=item['price'],
                price_change_pct=item['price_change_pct'],
                currency=item['currency'],
                stance=None,  # Not available for rankings
                estimated_upside_pct=None,  # Not available for rankings
                risk_level=None,  # Not available for rankings
                chart_data=item.get('chart_data'),  # From Aurora cache
                key_scores=item.get('key_scores')   # From Aurora cache
            )
            for item in ranking_items
        ]

        return RankingsResponse(
            category=category,
            as_of=datetime.now(),
            tickers=tickers
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Rankings error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    x_telegram_user_id: str | None = Header(None, alias="X-Telegram-User-Id")
):
    """Get user's watchlist

    Args:
        x_telegram_init_data: Full initData from Telegram WebApp (production auth)
        x_telegram_user_id: Simple user ID (development auth)

    Returns:
        WatchlistResponse with list of watched tickers
    """
    try:
        user_id = get_user_id_from_header(x_telegram_init_data, x_telegram_user_id)
        watchlist_service = get_watchlist_service()

        tickers = watchlist_service.get_watchlist(user_id)

        logger.info(f"Retrieved watchlist for user {user_id}: {len(tickers)} items")

        return WatchlistResponse(tickers=tickers)

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Watchlist GET error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/watchlist", response_model=WatchlistOperationResponse)
async def add_to_watchlist(
    request: WatchlistAddRequest,
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    x_telegram_user_id: str | None = Header(None, alias="X-Telegram-User-Id")
):
    """Add ticker to watchlist

    Args:
        request: Ticker to add
        x_telegram_init_data: Full initData from Telegram WebApp (production auth)
        x_telegram_user_id: Simple user ID (development auth)

    Returns:
        WatchlistOperationResponse confirming addition
    """
    try:
        user_id = get_user_id_from_header(x_telegram_init_data, x_telegram_user_id)
        ticker_service = get_ticker_service()
        watchlist_service = get_watchlist_service()

        # Validate ticker is supported
        if not ticker_service.is_supported(request.ticker):
            raise TickerNotSupportedError(request.ticker)

        # Add to watchlist
        result = watchlist_service.add_ticker(user_id, request.ticker)

        logger.info(f"Added {request.ticker} to watchlist for user {user_id}")

        return WatchlistOperationResponse(
            status="ok",
            ticker=result['ticker']
        )

    except APIError:
        raise
    except ValueError as e:
        raise TickerNotSupportedError(str(e))
    except Exception as e:
        logger.error(f"Watchlist POST error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/watchlist/{ticker}", response_model=WatchlistOperationResponse)
async def remove_from_watchlist(
    ticker: str,
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    x_telegram_user_id: str | None = Header(None, alias="X-Telegram-User-Id")
):
    """Remove ticker from watchlist

    Args:
        ticker: Ticker symbol to remove
        x_telegram_init_data: Full initData from Telegram WebApp (production auth)
        x_telegram_user_id: Simple user ID (development auth)

    Returns:
        WatchlistOperationResponse confirming removal
    """
    try:
        user_id = get_user_id_from_header(x_telegram_init_data, x_telegram_user_id)
        watchlist_service = get_watchlist_service()

        # Remove from watchlist
        result = watchlist_service.remove_ticker(user_id, ticker)

        logger.info(f"Removed {ticker} from watchlist for user {user_id}")

        return WatchlistOperationResponse(
            status="ok",
            ticker=result['ticker']
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Watchlist DELETE error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Development Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
