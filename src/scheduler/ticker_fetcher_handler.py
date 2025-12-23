# -*- coding: utf-8 -*-
"""
Lambda handler for scheduled ticker data fetching (Extract Layer).

Single Responsibility: Fetch raw ticker data from yfinance and store to S3/Aurora/Data Lake.

Triggered by: EventBridge (daily at 8 AM Bangkok time)
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict
import boto3

# Configure logging for Lambda
# Note: basicConfig() doesn't work in Lambda (runtime pre-configures logging)
# Must set logger level directly on root logger
root_logger = logging.getLogger()
if root_logger.handlers:  # Lambda runtime already configured
    root_logger.setLevel(logging.INFO)
else:  # Local development
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def _trigger_precompute(fetch_results: Dict[str, Any], start_time: datetime) -> bool:
    """
    Trigger precompute workflow asynchronously after successful fetch.

    This invokes the precompute controller Lambda with Event invocation type
    (fire-and-forget). The scheduler returns immediately without waiting for
    precompute to complete (~15-20 min).

    Args:
        fetch_results: Results from ticker fetch operation
        start_time: Scheduler start timestamp

    Returns:
        True if precompute was triggered, False otherwise
    """
    # Only trigger if at least one ticker succeeded
    if fetch_results['success_count'] == 0:
        logger.warning("No successful fetches, skipping precompute trigger")
        return False

    precompute_arn = os.environ.get('PRECOMPUTE_CONTROLLER_ARN')

    if not precompute_arn:
        logger.warning("PRECOMPUTE_CONTROLLER_ARN not set, skipping precompute trigger")
        logger.warning("Set this env var in terraform/scheduler.tf to enable automatic precompute")
        return False

    try:
        logger.info(f"✨ Triggering precompute for {fetch_results['total']} tickers")

        lambda_client = boto3.client('lambda')

        # Prepare payload with fetch summary
        payload = {
            'triggered_by': 'scheduler',
            'fetch_summary': {
                'success_count': fetch_results['success_count'],
                'failed_count': fetch_results['failed_count'],
                'total': fetch_results['total'],
                'date': fetch_results['date'],
                'success_tickers': [r['ticker'] for r in fetch_results['success']],
                'failed_tickers': fetch_results['failed']
            },
            'timestamp': start_time.isoformat()
        }

        # Async invocation (fire-and-forget)
        response = lambda_client.invoke(
            FunctionName=precompute_arn,
            InvocationType='Event',  # Async - don't wait for response
            Payload=json.dumps(payload)
        )

        status_code = response['StatusCode']
        logger.info(f"✅ Precompute controller invoked (async): HTTP {status_code}")

        if status_code == 202:  # Accepted for async processing
            return True
        else:
            logger.warning(f"Unexpected status code from Lambda invoke: {status_code}")
            return False

    except Exception as e:
        # Don't fail scheduler if precompute trigger fails
        logger.error(f"⚠️ Failed to trigger precompute: {e}")
        logger.error("Scheduler completed successfully, but precompute was NOT triggered")
        logger.error("You may need to trigger precompute manually")
        return False


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Fetch ticker data and store to S3/Aurora/Data Lake.

    Event formats:
        - {} or {"fetch_all": true}  -> Fetch all supported tickers
        - {"tickers": ["NVDA", "DBS19"]} -> Fetch specific tickers

    Args:
        event: Lambda event (from EventBridge or manual invocation)
        context: Lambda context

    Returns:
        Response dict with fetch results
    """
    start_time = datetime.now()
    logger.info(f"Ticker Fetcher Lambda invoked at {start_time.isoformat()}")
    logger.info(f"Event: {json.dumps(event)}")

    # Lazy import to avoid cold start overhead
    from src.scheduler.ticker_fetcher import TickerFetcher

    try:
        # Initialize fetcher with S3 and data lake buckets
        bucket_name = os.environ.get('PDF_BUCKET_NAME')
        data_lake_bucket = os.environ.get('DATA_LAKE_BUCKET')
        fetcher = TickerFetcher(
            bucket_name=bucket_name,
            data_lake_bucket=data_lake_bucket
        )

        # Determine what to fetch
        if event.get('tickers'):
            # Fetch specific tickers (for testing or manual runs)
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

        # Trigger precompute workflow (async, fire-and-forget)
        precompute_triggered = _trigger_precompute(results, start_time)

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
                'failed': results['failed'],
                'precompute_triggered': precompute_triggered
            }
        }

        logger.info(
            f"Fetch completed in {duration_seconds:.1f}s: "
            f"{results['success_count']} success, {results['failed_count']} failed"
        )

        return response

    except Exception as e:
        logger.error(f"Ticker fetch failed: {e}")
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
