# -*- coding: utf-8 -*-
"""
Get Active Ticker List Lambda

Query ticker_master + ticker_aliases for active DR symbols.
Used by Step Functions to get dynamic ticker list.

Single Responsibility: Query Aurora for active tickers

Triggered by: Step Functions PrepareTickerList state

Returns: {
    "tickers": ["NVDA19", "DBS19", ...],
    "count": 47
}
"""

import json
import logging
import os
from typing import Any, Dict
import pymysql

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Query Aurora for active DR ticker symbols.

    This Lambda is called by Step Functions to get the current list of
    active tickers from ticker_master table. This ensures precompute
    workflow is independent of scheduler fetch errors - it processes
    ALL tickers that should be active, not just those that were
    successfully fetched today.

    Args:
        event: Lambda event (unused, but required by Step Functions)
        context: Lambda context

    Returns:
        Dict with:
            - tickers: List[str] - Active DR symbols (e.g., ["NVDA19", "DBS19"])
            - count: int - Number of active tickers

    Raises:
        Exception: If database query fails
    """
    try:
        logger.info("Querying ticker_master for active DR symbols")

        # Connect to Aurora
        conn = pymysql.connect(
            host=os.environ['AURORA_HOST'],
            user=os.environ['AURORA_USERNAME'],
            password=os.environ['AURORA_PASSWORD'],
            database=os.environ['AURORA_DATABASE'],
            port=int(os.environ.get('AURORA_PORT', 3306))
        )

        cursor = conn.cursor()

        # Query for active DR symbols
        # Uses normalized schema:
        #   ticker_master (company info) + ticker_aliases (symbol mappings)
        from src.data.aurora.table_names import TICKER_MASTER, TICKER_ALIASES

        query = f"""
            SELECT DISTINCT a.symbol
            FROM {TICKER_MASTER} m
            JOIN {TICKER_ALIASES} a ON m.id = a.ticker_id
            WHERE m.is_active = TRUE
              AND a.symbol_type = 'dr'
            ORDER BY a.symbol
        """

        cursor.execute(query)
        tickers = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        logger.info(f"✅ Retrieved {len(tickers)} active tickers from ticker_master")
        logger.info(f"Tickers: {', '.join(tickers[:5])}... (showing first 5)")

        return {
            "tickers": tickers,
            "count": len(tickers)
        }

    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        logger.error("Required: AURORA_HOST, AURORA_USERNAME, AURORA_PASSWORD, AURORA_DATABASE")
        raise

    except pymysql.Error as e:
        logger.error(f"Database error: {e}")
        logger.error("Check Aurora connection, VPC config, and security groups")
        raise

    except Exception as e:
        logger.error(f"Failed to get ticker list: {e}")
        raise


# For local testing
if __name__ == '__main__':
    # Mock event
    test_event = {}
    test_context = None

    # NOTE: Requires environment variables:
    #   AURORA_HOST, AURORA_USERNAME, AURORA_PASSWORD, AURORA_DATABASE
    # Set these via: ENV=dev doppler run -- python src/scheduler/get_ticker_list_handler.py

    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2))
