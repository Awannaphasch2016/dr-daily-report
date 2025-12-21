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

# Configure logging for Lambda
# Note: basicConfig() doesn't work in Lambda (runtime pre-configures logging)
# Must set logger level directly on root logger
root_logger = logging.getLogger()
if root_logger.handlers:  # Lambda runtime already configured
    root_logger.setLevel(logging.INFO)
else:  # Local development
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


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
