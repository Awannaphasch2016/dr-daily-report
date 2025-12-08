# -*- coding: utf-8 -*-
"""
Lambda handler for scheduled ticker data fetching.

Triggered by EventBridge (daily at 8 AM Bangkok time) or manual invocation.

Supports parallel precompute via SQS fan-out for fast cache population.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _handle_describe_table(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Query Aurora table schema for CI/CD schema validation (NO MOCKING).

    Following CLAUDE.md Principle 4: Schema Testing at System Boundaries
    - System boundary: Python code → Aurora MySQL
    - Contract: Table schema must match code expectations
    - This handler enables real schema queries from CI/CD pipelines

    Args:
        event: Lambda event with required param:
            - table: Table name to describe (e.g., "precomputed_reports")
        start_time: When the Lambda was invoked

    Returns:
        Response dict with schema info:
        {
            'statusCode': 200,
            'body': {
                'schema': {
                    'column_name': {'Type': 'varchar(255)', 'Null': 'NO', 'Key': 'PRI'},
                    ...
                }
            }
        }

    Example usage (from CI/CD):
        aws lambda invoke \\
          --function-name dr-daily-report-ticker-scheduler-dev \\
          --payload '{"action":"describe_table","table":"precomputed_reports"}' \\
          /tmp/schema.json
    """
    import traceback

    try:
        from src.data.aurora.client import get_aurora_client

        table_name = event.get('table')
        if not table_name:
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Missing required parameter: table',
                    'error': 'Must provide table name to describe'
                }
            }

        client = get_aurora_client()

        # Query table schema using DESCRIBE (MySQL DDL command)
        query = f"DESCRIBE {table_name}"
        logger.info(f"Querying schema for table: {table_name}")

        result = client.fetch_all(query, ())

        # Transform to dict: {column_name: {Type, Null, Key, ...}}
        schema = {}
        for row in result:
            col_name = row['Field']
            schema[col_name] = {
                'Type': row['Type'],
                'Null': row['Null'],
                'Key': row.get('Key', ''),
                'Default': row.get('Default'),
                'Extra': row.get('Extra', '')
            }

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(f"Schema query completed: {len(schema)} columns in {table_name}")

        return {
            'statusCode': 200,
            'body': {
                'message': f'Schema retrieved for {table_name}',
                'table': table_name,
                'column_count': len(schema),
                'schema': schema,
                'duration_seconds': duration_seconds
            }
        }

    except Exception as e:
        logger.error(f"Schema query failed for table {event.get('table')}: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': f"Failed to describe table {event.get('table')}",
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_debug_cache(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Debug action to query precomputed_reports table in Aurora.

    Args:
        event: Lambda event with optional params:
            - symbol: Check specific symbol's cached report
            - date: Date to check (default: today)
            - limit: Max reports to return (default: 10)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with cached reports info
    """
    import traceback
    from datetime import date

    try:
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.precompute_service import PrecomputeService

        client = get_aurora_client()
        service = PrecomputeService()

        symbol = event.get('symbol')
        check_date = event.get('date', str(date.today()))
        limit = event.get('limit', 10)

        if symbol:
            # Check specific symbol's cached report
            cached = service.get_cached_report(symbol, date.fromisoformat(check_date))
            if cached:
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f'Cache HIT for {symbol}',
                        'symbol': symbol,
                        'date': check_date,
                        'report_id': cached.get('id'),
                        'ticker_master_id': cached.get('ticker_master_id'),
                        'status': cached.get('status'),
                        'report_text_length': len(cached.get('report_text', '')),
                        'has_chart': bool(cached.get('chart_base64')),
                        'generated_at': str(cached.get('report_generated_at')),
                    }
                }
            else:
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f'Cache MISS for {symbol}',
                        'symbol': symbol,
                        'date': check_date,
                    }
                }
        else:
            # First, get table schema to understand column names
            schema_query = "DESCRIBE precomputed_reports"
            try:
                schema = client.fetch_all(schema_query, ())
                schema_info = [{'field': r['Field'], 'type': r['Type']} for r in schema]
            except Exception as schema_err:
                schema_info = str(schema_err)

            # List all cached reports for the date (use SELECT * to be schema-agnostic)
            query = """
                SELECT * FROM precomputed_reports
                WHERE report_date = %s
                ORDER BY id DESC
                LIMIT %s
            """
            reports = client.fetch_all(query, (check_date, limit))

            # Build report summary dynamically based on available columns
            report_summaries = []
            for r in reports:
                summary = {
                    'id': r.get('id'),
                    'symbol': r.get('symbol'),
                    'report_date': str(r.get('report_date')) if r.get('report_date') else None,
                    'status': r.get('status'),
                    'has_report_text': bool(r.get('report_text')),
                    'report_text_len': len(r.get('report_text', '') or ''),
                }
                # Add optional columns if they exist
                if 'ticker_master_id' in r:
                    summary['ticker_master_id'] = r['ticker_master_id']
                if 'ticker_id' in r:
                    summary['ticker_id'] = r['ticker_id']
                if 'created_at' in r:
                    summary['created_at'] = str(r['created_at'])
                if 'updated_at' in r:
                    summary['updated_at'] = str(r['updated_at'])
                report_summaries.append(summary)

            return {
                'statusCode': 200,
                'body': {
                    'message': f'Found {len(reports)} cached reports',
                    'date': check_date,
                    'count': len(reports),
                    'schema': schema_info,
                    'reports': report_summaries
                }
            }

    except Exception as e:
        logger.error(f"Debug cache failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'message': 'Debug cache failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_precompute(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle precomputation of indicators, percentiles, and reports.

    Args:
        event: Lambda event with optional params:
            - symbol: Single ticker to process
            - include_report: Whether to generate LLM reports (default: False)
            - limit: Max number of tickers to process
        start_time: When the Lambda was invoked

    Returns:
        Response dict with precomputation results
    """
    logger.info("Starting precomputation...")

    try:
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        symbol = event.get('symbol')
        include_report = event.get('include_report', False)
        limit = event.get('limit')

        if symbol:
            # Process single ticker
            result = service.compute_for_ticker(symbol, include_report=include_report)
            results = {'total': 1, 'success': 1 if not result.get('error') else 0, 'details': [result]}
        else:
            # Process all tickers
            results = service.compute_all(include_report=include_report, limit=limit)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Precomputation completed',
                'duration_seconds': duration_seconds,
                **results
            }
        }

    except Exception as e:
        logger.error(f"Precomputation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Precomputation failed',
                'error': str(e)
            }
        }


def _handle_precompute_migration(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle precomputation tables migration.

    Args:
        event: Lambda event
        start_time: When the Lambda was invoked

    Returns:
        Response dict with migration results
    """
    logger.info("Starting precomputation tables migration...")

    try:
        from scripts.aurora_precompute_migration import run_migration

        result = run_migration()

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Precomputation migration completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Precomputation migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Precomputation migration failed',
                'error': str(e)
            }
        }


def _handle_aurora_setup(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle Aurora database setup: create tables and import data from S3.

    Args:
        event: Lambda event with optional create_tables_only, import_limit, cleanup_first params
        start_time: When the Lambda was invoked

    Returns:
        Response dict with setup results
    """
    logger.info("Starting Aurora setup...")

    try:
        from scripts.aurora_setup import setup_aurora

        create_tables_only = event.get('create_tables_only', False)
        import_limit = event.get('import_limit')
        cleanup_first = event.get('cleanup_first', False)

        result = setup_aurora(
            create_tables_only=create_tables_only,
            import_limit=import_limit,
            cleanup_first=cleanup_first
        )

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Aurora setup completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Aurora setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Aurora setup failed',
                'error': str(e)
            }
        }


def _handle_setup_ticker_mapping(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Setup ticker mapping tables and populate from tickers.csv.

    Creates ticker_master and ticker_aliases tables if they don't exist,
    then populates them from tickers.csv for centralized symbol resolution.

    Args:
        event: Lambda event with optional 'populate' param (default: True)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with setup results
    """
    logger.info("Starting ticker mapping setup...")

    try:
        from src.data.aurora.ticker_resolver import TickerResolver

        resolver = TickerResolver()

        # Create tables
        resolver.create_tables()
        logger.info("Created ticker_master and ticker_aliases tables")

        # Populate from CSV unless explicitly disabled
        populate = event.get('populate', True)
        count = 0

        if populate:
            count = resolver.populate_from_csv()
            logger.info(f"Populated {count} tickers from CSV")

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        # Test resolution
        test_results = {}
        for test_symbol in ['NVDA19', 'NVDA', 'DBS19', 'D05.SI']:
            info = resolver.resolve(test_symbol)
            if info:
                test_results[test_symbol] = {
                    'resolved': True,
                    'yahoo': info.yahoo_symbol,
                    'dr': info.dr_symbol,
                    'company': info.company_name
                }
            else:
                test_results[test_symbol] = {'resolved': False}

        return {
            'statusCode': 200,
            'body': {
                'message': 'Ticker mapping setup completed',
                'duration_seconds': duration_seconds,
                'tables_created': True,
                'tickers_populated': count,
                'test_resolution': test_results
            }
        }

    except Exception as e:
        logger.error(f"Ticker mapping setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Ticker mapping setup failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_ticker_unification(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle ticker unification migration (Phase 4).

    Migrates data tables to use ticker_master.id as the canonical identifier
    instead of raw symbol strings.

    Args:
        event: Lambda event with params:
            - phase: Migration phase ("4.1", "4.2", "4.4", "verify")
            - dry_run: If True, only show what would be done (optional)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with migration results
    """
    logger.info("Starting ticker unification migration...")

    try:
        from scripts.aurora_ticker_unification_migration import run_migration

        phase = event.get('phase', 'verify')
        dry_run = event.get('dry_run', False)

        result = run_migration(phase=phase, dry_run=dry_run)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': f'Ticker unification migration phase {phase} completed',
                'duration_seconds': duration_seconds,
                **result
            }
        }

    except Exception as e:
        logger.error(f"Ticker unification migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Ticker unification migration failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_parallel_precompute(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Handle parallel precomputation via fan-out to SQS.

    Instead of processing tickers sequentially (which takes ~47 minutes for 47 tickers),
    this sends one SQS message per ticker, allowing Report Worker Lambda to process
    them in parallel (auto-scales to handle concurrent invocations).

    Architecture:
        Scheduler Lambda → SQS (47 messages) → Report Worker Lambda ×47 (parallel)

    Benefits:
        - Total time ≈ slowest ticker (~60s) instead of sum (~47 min)
        - Uses existing SQS + Report Worker infrastructure
        - Auto-scales, fault-tolerant

    Args:
        event: Lambda event with optional params:
            - limit: Max number of tickers to process (for testing)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with job submission results
    """
    logger.info("Starting parallel precompute (fan-out to SQS)...")

    try:
        from src.data.aurora.precompute_service import PrecomputeService
        from src.api.job_service import get_job_service
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        service = PrecomputeService()
        job_service = get_job_service()
        resolver = get_ticker_resolver()

        # Get all tickers from Aurora
        tickers = service.repo.get_all_tickers()
        limit = event.get('limit')
        if limit:
            tickers = tickers[:limit]

        logger.info(f"Submitting {len(tickers)} tickers for parallel processing...")

        # Get SQS queue URL
        queue_url = os.environ.get(
            "REPORT_JOBS_QUEUE_URL",
            "https://sqs.ap-southeast-1.amazonaws.com/755283537543/dr-daily-report-telegram-queue-dev"
        )

        sqs = boto3.client('sqs')

        jobs_submitted = 0
        jobs_failed = 0
        failed_tickers = []
        submitted_jobs = []

        for ticker_info in tickers:
            yahoo_symbol = ticker_info['symbol']  # DB stores Yahoo format

            # Convert Yahoo symbol to DR symbol for worker
            # Worker expects DR format (DBS19, NVDA19) not Yahoo format (D05.SI, NVDA)
            dr_symbol = resolver.to_dr(yahoo_symbol)
            if not dr_symbol:
                logger.warning(f"Cannot resolve {yahoo_symbol} to DR format, skipping")
                jobs_failed += 1
                failed_tickers.append(yahoo_symbol)
                continue

            try:
                # Create job in DynamoDB with DR symbol
                job = job_service.create_job(ticker=dr_symbol)

                # Send to SQS for async processing with DR symbol
                message_body = json.dumps({
                    'job_id': job.job_id,
                    'ticker': dr_symbol
                })

                sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=message_body
                )

                jobs_submitted += 1
                submitted_jobs.append({
                    'job_id': job.job_id,
                    'ticker': dr_symbol
                })

                logger.debug(f"Submitted job {job.job_id} for {dr_symbol} (from {yahoo_symbol})")

            except Exception as e:
                logger.error(f"Failed to submit job for {dr_symbol} ({yahoo_symbol}): {e}")
                jobs_failed += 1
                failed_tickers.append(dr_symbol)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            f"Parallel precompute initiated: {jobs_submitted} jobs submitted, "
            f"{jobs_failed} failed in {duration_seconds:.1f}s"
        )

        return {
            'statusCode': 200,
            'body': {
                'message': 'Parallel precompute initiated',
                'jobs_submitted': jobs_submitted,
                'jobs_failed': jobs_failed,
                'total_tickers': len(tickers),
                'duration_seconds': duration_seconds,
                'failed_tickers': failed_tickers,
                'submitted_jobs': submitted_jobs[:10]  # First 10 for brevity
            }
        }

    except Exception as e:
        logger.error(f"Parallel precompute failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Parallel precompute failed',
                'error': str(e)
            }
        }


def _handle_debug_prices(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Debug action to inspect price data in Aurora.

    Args:
        event: Lambda event with optional 'symbol' param
        start_time: When the Lambda was invoked

    Returns:
        Response dict with debug info
    """
    logger.info("Starting debug prices...")

    try:
        from src.data.aurora.repository import TickerRepository

        repo = TickerRepository()
        symbol = event.get('symbol', 'D05.SI')

        # Get raw prices
        prices = repo.get_prices(symbol, limit=3)

        # Get as DataFrame
        df = repo.get_prices_as_dataframe(symbol, limit=3)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': 'Debug prices completed',
                'duration_seconds': duration_seconds,
                'symbol': symbol,
                'raw_prices_count': len(prices) if prices else 0,
                'raw_prices_sample': [
                    {k: str(v) for k, v in p.items()} for p in (prices[:2] if prices else [])
                ],
                'df_shape': list(df.shape) if not df.empty else [0, 0],
                'df_columns': list(df.columns) if not df.empty else [],
                'df_index_type': str(type(df.index)) if not df.empty else 'N/A',
                'df_head': df.head(2).to_dict() if not df.empty else {}
            }
        }

    except Exception as e:
        logger.error(f"Debug prices failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Debug prices failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _validate_configuration() -> None:
    """
    Validate required environment variables at Lambda startup.

    Fails fast if critical configuration is missing, following defensive programming principle:
    "Validate configuration at startup, not on first use"

    Raises:
        RuntimeError: If required environment variables are missing
    """
    # Aurora connection (required for all operations)
    aurora_vars = ['AURORA_HOST', 'AURORA_USER', 'AURORA_PASSWORD', 'AURORA_DATABASE']

    # SQS queue (required for parallel_precompute action)
    queue_vars = ['REPORT_JOBS_QUEUE_URL']

    # DynamoDB tables (required for job tracking)
    dynamo_vars = ['JOBS_TABLE_NAME']

    # API keys (required for LLM report generation)
    api_vars = ['OPENROUTER_API_KEY']

    # Storage (required for PDF generation)
    storage_vars = ['PDF_BUCKET_NAME']

    # Collect ALL required vars
    all_required_vars = aurora_vars + queue_vars + dynamo_vars + api_vars + storage_vars

    missing_vars = [var for var in all_required_vars if not os.environ.get(var)]

    if missing_vars:
        error_msg = (
            f"❌ CONFIGURATION ERROR: Missing required environment variables: {missing_vars}\n"
            f"Lambda cannot start without these variables.\n"
            f"Required vars: Aurora={aurora_vars}, SQS={queue_vars}, "
            f"DynamoDB={dynamo_vars}, API={api_vars}, Storage={storage_vars}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Log successful validation
    logger.info("✅ Configuration validation passed - all required environment variables present")
    logger.info(f"Aurora: {os.environ.get('AURORA_HOST')}")
    logger.info(f"Jobs table: {os.environ.get('JOBS_TABLE_NAME')}")
    logger.info(f"Queue: {os.environ.get('REPORT_JOBS_QUEUE_URL')}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for ticker data fetching and Aurora setup.

    Event formats:
        - {} or {"refresh_all": true}  -> Fetch all supported tickers
        - {"tickers": ["NVDA", "DBS19"]} -> Fetch specific tickers
        - {"action": "aurora_setup"}     -> Create Aurora tables and import data
        - {"action": "aurora_setup", "create_tables_only": true} -> Only create tables
        - {"action": "aurora_setup", "import_limit": 5} -> Import limited tickers (for testing)
        - {"action": "debug_prices"}     -> Debug price data in Aurora

    Args:
        event: Lambda event (from EventBridge or manual invocation)
        context: Lambda context

    Returns:
        Response dict with status and results
    """
    start_time = datetime.now()
    logger.info(f"Scheduler Lambda invoked at {start_time.isoformat()}")
    logger.info(f"Event: {json.dumps(event)}")

    # Validate configuration at startup (fail-fast principle)
    try:
        _validate_configuration()
    except RuntimeError as e:
        return {
            'statusCode': 500,
            'body': {
                'message': 'Configuration validation failed',
                'error': str(e)
            }
        }

    # Handle debug prices action
    if event.get('action') == 'debug_prices':
        return _handle_debug_prices(event, start_time)

    # Handle debug cache action (query precomputed_reports table)
    if event.get('action') == 'debug_cache':
        return _handle_debug_cache(event, start_time)

    # Handle describe table action (for schema contract testing - NO MOCKING)
    if event.get('action') == 'describe_table':
        return _handle_describe_table(event, start_time)

    # Handle ticker unification migration (Phase 4)
    if event.get('action') == 'ticker_unification':
        return _handle_ticker_unification(event, start_time)

    # Handle ticker mapping setup
    if event.get('action') == 'setup_ticker_mapping':
        return _handle_setup_ticker_mapping(event, start_time)

    # Handle Aurora setup action
    if event.get('action') == 'aurora_setup':
        return _handle_aurora_setup(event, start_time)

    # Handle precomputation migration
    if event.get('action') == 'precompute_migration':
        return _handle_precompute_migration(event, start_time)

    # Handle precomputation (backfill indicators/percentiles)
    if event.get('action') == 'precompute':
        return _handle_precompute(event, start_time)

    # Handle parallel precomputation (fan-out to SQS for parallel processing)
    if event.get('action') == 'parallel_precompute':
        return _handle_parallel_precompute(event, start_time)

    # Import here to avoid cold start issues if module import fails
    from src.scheduler.ticker_fetcher import TickerFetcher

    try:
        # Initialize fetcher with data lake bucket (if configured)
        bucket_name = os.environ.get('PDF_BUCKET_NAME')
        data_lake_bucket = os.environ.get('DATA_LAKE_BUCKET')
        fetcher = TickerFetcher(
            bucket_name=bucket_name,
            data_lake_bucket=data_lake_bucket
        )

        # Determine what to fetch
        if event.get('tickers'):
            # Fetch specific tickers
            tickers = event['tickers']
            logger.info(f"Fetching specific tickers: {tickers}")
            results = fetcher.fetch_tickers(tickers)
        else:
            # Fetch all tickers (default for EventBridge schedule)
            logger.info("Fetching all supported tickers")
            results = fetcher.fetch_all_tickers()

        # Calculate duration
        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        response = {
            'statusCode': 200,
            'body': {
                'message': 'Ticker fetch completed',
                'success_count': results['success_count'],
                'failed_count': results['failed_count'],
                'total': results['total'],
                'date': results['date'],
                'duration_seconds': duration_seconds,
                'success': [r['ticker'] for r in results['success']],
                'failed': results['failed']
            }
        }

        logger.info(
            f"Fetch completed in {duration_seconds:.1f}s: "
            f"{results['success_count']} success, {results['failed_count']} failed"
        )

        return response

    except Exception as e:
        logger.error(f"Scheduler Lambda failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Ticker fetch failed',
                'error': str(e)
            }
        }


# For local testing
if __name__ == '__main__':
    # Test with specific tickers
    test_event = {'tickers': ['NVDA', 'D05.SI']}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
