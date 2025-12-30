"""Fetch fundamental metrics from fund_data table (SQL Server source)."""

import logging
from typing import Dict, Optional, Any
from datetime import date
from decimal import Decimal

from src.data.aurora.client import get_aurora_client
from src.data.aurora.ticker_resolver import get_ticker_resolver

logger = logging.getLogger(__name__)


class DataNotFoundError(Exception):
    """Raised when requested data is not found in fund_data table."""
    pass


def fetch_fund_data_metrics(
    ticker: str,
    d_trade: Optional[date] = None
) -> Dict[str, Any]:
    """
    Fetch fundamental metrics from fund_data table.

    Uses TickerResolver to translate any symbol format (DR, Yahoo, Eikon)
    to the Eikon format used by fund_data table. Follows the established
    pattern from precompute_service.py for consistency.

    Args:
        ticker: Ticker symbol in any format (e.g., 'D05.SI', 'DBS19', 'DBSM.SI')
        d_trade: Trading date to fetch (defaults to latest available)

    Returns:
        Dict mapping COL_CODE to value:
        {
            'FY1_PE': 14.08,
            'P/E': 15.2,
            'FY1_DIV_YIELD': 5.18,
            'ROE': 12.5,
            'P/BV': 2.3,
            'TARGET_PRC': 60.0,
            'SECTOR': 'Financials'
        }

    Raises:
        DataNotFoundError: If ticker not found

    Example:
        >>> metrics = fetch_fund_data_metrics('D05.SI')  # Yahoo symbol
        >>> print(metrics['FY1_PE'])  # 14.08
        >>> metrics = fetch_fund_data_metrics('DBS19')  # DR symbol also works
    """
    # RESOLVE SYMBOL using TickerResolver (follows precompute_service.py pattern)
    resolver = get_ticker_resolver()
    ticker_info = resolver.resolve(ticker)

    # DEFENSIVE: Validate ticker resolution succeeded
    if not ticker_info:
        raise DataNotFoundError(f"Unknown ticker: {ticker}")

    # Extract Eikon symbol (fund_data uses Eikon format)
    # Fallback to yahoo_symbol if no eikon_symbol mapping
    eikon_symbol = ticker_info.eikon_symbol or ticker_info.yahoo_symbol

    logger.debug(f"Resolved {ticker} → {eikon_symbol} (Eikon) for fund_data query")

    client = get_aurora_client()

    # Query fund_data for latest metrics using resolved Eikon symbol
    from src.data.aurora.table_names import FUND_DATA

    query = f"""
        SELECT col_code, value_numeric, value_text
        FROM {FUND_DATA}
        WHERE ticker = %s
        AND d_trade = COALESCE(%s, (
            SELECT MAX(d_trade)
            FROM {FUND_DATA}
            WHERE ticker = %s
        ))
        ORDER BY col_code
    """

    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (eikon_symbol, d_trade, eikon_symbol))
                rows = cursor.fetchall()

                # DEFENSIVE: Check rowcount explicitly (fail fast)
                if not rows or len(rows) == 0:
                    error_msg = f"No fund_data found for ticker {ticker} (resolved to Eikon: {eikon_symbol})"
                    if d_trade:
                        error_msg += f" on date {d_trade}"
                    logger.warning(error_msg)
                    raise DataNotFoundError(error_msg)

                logger.info(f"✅ Fetched {len(rows)} fund_data metrics for {ticker} (Eikon: {eikon_symbol})")

    except Exception as e:
        if isinstance(e, DataNotFoundError):
            raise  # Re-raise our custom exception
        logger.error(f"Database error fetching fund_data for {ticker} (Eikon: {eikon_symbol}): {e}")
        raise

    # Map COL_CODE to value
    metrics: Dict[str, Any] = {}

    for row in rows:
        col_code = row['col_code']

        # DEFENSIVE: System boundary type conversion
        # PyMySQL returns DECIMAL as Decimal objects - convert to float
        if row['value_numeric'] is not None:
            value = row['value_numeric']
            # Convert Decimal to float for JSON serialization compatibility
            if isinstance(value, Decimal):
                value = float(value)
            metrics[col_code] = value
        else:
            # Text value (e.g., SECTOR)
            metrics[col_code] = row['value_text']

    # DEFENSIVE: Validate we actually got content (truthy trap)
    if not metrics or len(metrics) == 0:
        raise DataNotFoundError(f"fund_data query returned rows but no metrics extracted for {ticker}")

    logger.debug(f"Extracted fund_data metrics: {list(metrics.keys())}")
    return metrics
