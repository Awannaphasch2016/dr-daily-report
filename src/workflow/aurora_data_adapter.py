# -*- coding: utf-8 -*-
"""
Aurora Data Adapter

Adapter layer to translate Aurora database data into the exact format
expected by workflow nodes (matching yfinance data_fetcher structure).

Provides Aurora-only data sources for report generation with fail-fast
error handling when required data is missing.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from src.data.aurora.client import get_aurora_client
from src.data.aurora.repository import TickerRepository
from src.data.aurora.fund_data_fetcher import (
    fetch_fund_data_metrics,
    DataNotFoundError as FundDataNotFoundError
)

logger = logging.getLogger(__name__)


class DataNotFoundError(Exception):
    """Raised when required data not found in Aurora database.

    Aurora is the source of truth for report generation. This exception
    indicates that data has not been pre-populated by the nightly scheduler.
    The caller should fail fast and return an error to the user (no fallback
    to external APIs).

    User-facing APIs should display: "Report not available. Please try again later."
    Admin tools should prompt: "Run Step Function to populate Aurora."

    Example:
        >>> try:
        ...     data = fetch_ticker_data_from_aurora('DBS19')
        ... except DataNotFoundError as e:
        ...     logger.error(f"Aurora data missing: {e}")
        ...     raise  # Fail fast, no external API fallback
    """
    pass


def fetch_ticker_data_from_aurora(symbol: str) -> Dict[str, Any]:
    """Fetch ticker data from Aurora precomputed_reports table.

    Reads price_history and fundamentals from the most recent completed report's
    report_json field. This avoids Yahoo Finance calls by reusing cached data.

    Args:
        symbol: Ticker symbol (e.g., 'DBS19', 'D05.SI', 'NVDA')

    Returns:
        Dict matching data_fetcher.fetch_ticker_data() structure:
        {
            'date': '2025-01-15',
            'open': 100.5,
            'high': 102.3,
            'low': 99.8,
            'close': 101.2,
            'volume': 1500000,
            'market_cap': 1000000000,
            'pe_ratio': 25.5,
            'eps': 4.0,
            'dividend_yield': 0.02,
            'sector': 'Technology',
            'industry': 'Software',
            'company_name': 'Example Corp',
            'history': pd.DataFrame(...)  # Integer index, Date column as string
        }

    Raises:
        DataNotFoundError: If no precomputed report found for symbol

    Example:
        >>> data = fetch_ticker_data_from_aurora('D05.SI')
        >>> print(f"Fetched {len(data['history'])} days for {data['company_name']}")
        Fetched 365 days for DBS Group Holdings
    """
    client = get_aurora_client()

    logger.info(f"🔍 Fetching data from Aurora precomputed_reports for {symbol}")

    # Query most recent completed report
    query = """
        SELECT report_json, report_date, symbol
        FROM precomputed_reports
        WHERE symbol = %s
          AND status = 'completed'
        ORDER BY report_date DESC
        LIMIT 1
    """
    row = client.fetch_one(query, (symbol,))

    if not row:
        raise DataNotFoundError(
            f"No precomputed report found for {symbol}. "
            f"Generate report first or check symbol format (try both 'DBS19' and 'D05.SI')."
        )

    # Parse report_json
    try:
        report = json.loads(row['report_json'])
    except (json.JSONDecodeError, TypeError) as e:
        raise DataNotFoundError(
            f"Invalid report_json for {symbol}: {e}"
        )

    # Extract price_history from report
    price_history = report.get('price_history', [])
    if not price_history or len(price_history) == 0:
        raise DataNotFoundError(
            f"price_history is empty in precomputed report for {symbol}"
        )

    # Convert price_history to DataFrame (match yfinance format)
    # Aurora stores: [{date, open, high, low, close, volume, ...}, ...]
    df = pd.DataFrame(price_history)

    # Map Aurora column names to yfinance format (capitalized)
    column_mapping = {
        'date': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }

    # Rename columns if they exist in lowercase
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)

    # Validate required columns
    required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataNotFoundError(
            f"price_history missing required columns for {symbol}: {missing_cols}. "
            f"Available columns: {list(df.columns)}"
        )

    # Convert Date column to string format (yfinance uses strings, not datetime)
    # Handle both numeric dates ("0", "1", "2") and date strings
    if df['Date'].dtype in [int, float] or all(df['Date'].astype(str).str.isnumeric()):
        # Numeric dates - keep as strings representing index positions
        df['Date'] = df['Date'].astype(str)
    else:
        # Already date strings or datetime - ensure string format
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

    # Ensure integer index (not DatetimeIndex)
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index(drop=True)

    # Filter out projection rows (if is_projection field exists)
    if 'is_projection' in df.columns:
        df = df[df['is_projection'] == False].copy()
        df = df.reset_index(drop=True)

    # Get latest price (last row of actual data)
    if len(df) == 0:
        raise DataNotFoundError(f"No actual price data (all projections) for {symbol}")

    latest = df.iloc[-1]
    latest_date = latest['Date']

    # Extract fundamentals from report (nested structure)
    fundamentals = report.get('fundamentals', {})

    # Helper to extract value from nested fundamentals structure
    def extract_fundamental(category: str, name: str):
        """Extract value from fundamentals[category][name]"""
        items = fundamentals.get(category, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get('name') == name:
                    return item.get('value')
        return None

    # Extract specific fundamentals from nested structure
    pe_ratio = extract_fundamental('valuation', 'P/E Ratio')
    market_cap = extract_fundamental('valuation', 'Market Cap')
    eps = extract_fundamental('profitability', 'EPS')
    dividend_yield = extract_fundamental('profitability', 'Dividend Yield')

    # Build result dict (same structure as data_fetcher.fetch_ticker_data)
    result = {
        'date': latest_date,
        'open': float(latest['Open']),
        'high': float(latest['High']),
        'low': float(latest['Low']),
        'close': float(latest['Close']),
        'volume': int(latest['Volume']),
        'market_cap': market_cap,
        'pe_ratio': pe_ratio,
        'eps': eps,
        'dividend_yield': dividend_yield,
        'sector': report.get('sector'),  # May be None
        'industry': report.get('industry'),  # May be None
        'company_name': report.get('company_name', symbol),
        'history': df  # Full DataFrame with integer index, Date as string column
    }

    logger.info(f"✅ Fetched data from Aurora precomputed_reports for {symbol}")
    logger.info(f"   - Report date: {row['report_date']}")
    logger.info(f"   - Price history: {len(df)} days")
    logger.info(f"   - Company: {result['company_name']}")
    logger.info(f"   - Latest: {latest_date}, Close: {result['close']:.2f}")
    logger.info(f"   - Market Cap: {result.get('market_cap')}")
    logger.info(f"   - P/E Ratio: {result.get('pe_ratio')}")

    # NEW: Supplement with fund_data metrics (SQL Server source)
    try:
        fund_metrics = fetch_fund_data_metrics(symbol)

        # OVERRIDE precomputed_reports fundamentals with fund_data (Eikon source - more trustworthy)
        # Fund data is primary source of truth for fundamentals
        override_count = 0

        # Override P/E ratio if available
        if fund_metrics.get('P/E') is not None:
            old_pe = result.get('pe_ratio')
            result['pe_ratio'] = fund_metrics.get('P/E')
            if old_pe is not None and old_pe != result['pe_ratio']:
                logger.info(f"   ⚠️  Overriding P/E: {old_pe:.2f} (Yahoo) → {result['pe_ratio']:.2f} (Eikon)")
                override_count += 1

        # Override dividend yield if available
        if fund_metrics.get('FY1_DIV_YIELD') is not None:
            old_div = result.get('dividend_yield')
            result['dividend_yield'] = fund_metrics.get('FY1_DIV_YIELD')
            if old_div is not None and old_div != result['dividend_yield']:
                logger.info(f"   ⚠️  Overriding Dividend Yield: {old_div:.2f}% (Yahoo) → {result['dividend_yield']:.2f}% (Eikon)")
                override_count += 1

        # Add forward P/E (FY1_PE) as separate metric
        result['forward_pe'] = fund_metrics.get('FY1_PE')

        # Add other fund_data metrics (NEW fields)
        result['roe'] = fund_metrics.get('ROE')
        result['price_to_book'] = fund_metrics.get('P/BV')
        result['target_price'] = fund_metrics.get('TARGET_PRC')

        # Optional: Override sector if Eikon data more accurate
        if fund_metrics.get('SECTOR') is not None:
            old_sector = result.get('sector')
            result['sector'] = fund_metrics.get('SECTOR')
            if old_sector and old_sector != result['sector']:
                logger.info(f"   ⚠️  Overriding Sector: {old_sector} (Yahoo) → {result['sector']} (Eikon)")
                override_count += 1

        logger.info(f"✅ Supplemented with fund_data metrics for {symbol}")
        if override_count > 0:
            logger.info(f"   📊 Overrode {override_count} metrics with Eikon data (more trustworthy)")
        logger.info(f"   - P/E Ratio: {result.get('pe_ratio')}")
        logger.info(f"   - Forward P/E: {result.get('forward_pe')}")
        logger.info(f"   - Dividend Yield: {result.get('dividend_yield')}")
        logger.info(f"   - ROE: {result.get('roe')}")
        logger.info(f"   - P/B Ratio: {result.get('price_to_book')}")
        logger.info(f"   - Target Price: {result.get('target_price')}")

    except FundDataNotFoundError as e:
        # GRACEFUL DEGRADATION: fund_data missing, continue with Aurora data only
        logger.warning(f"⚠️ No fund_data found for {symbol}: {e}")
        logger.warning(f"   Continuing with Aurora precomputed_reports data only")
        # Set new metrics to None (they won't be in report)
        result['forward_pe'] = None
        result['roe'] = None
        result['price_to_book'] = None
        result['target_price'] = None

    return result


def fetch_peer_data_from_aurora(peer_symbols: List[str], days: int = 90) -> Dict[str, pd.DataFrame]:
    """Fetch historical price data for peer tickers from Aurora precomputed_reports.

    Reads price_history from each peer's most recent precomputed report.
    Truncates to requested number of days.

    Args:
        peer_symbols: List of peer ticker symbols
        days: Number of days of historical data (default: 90)

    Returns:
        Dict mapping symbol to DataFrame:
        {
            'NVDA': pd.DataFrame(...),  # 90 days OHLCV
            'D05.SI': pd.DataFrame(...)
        }

    Raises:
        DataNotFoundError: If no peer data found in Aurora

    Example:
        >>> peers = ['D05.SI', 'O39.SI']
        >>> peer_data = fetch_peer_data_from_aurora(peers, days=90)
        >>> print(f"Fetched {len(peer_data)} peers")
    """
    client = get_aurora_client()
    peer_data = {}

    logger.info(f"🔍 Fetching {days}-day history for {len(peer_symbols)} peers from Aurora")

    for symbol in peer_symbols:
        try:
            # Query most recent precomputed report
            query = """
                SELECT report_json
                FROM precomputed_reports
                WHERE symbol = %s
                  AND status = 'completed'
                ORDER BY report_date DESC
                LIMIT 1
            """
            row = client.fetch_one(query, (symbol,))

            if not row:
                logger.warning(f"⚠️ No precomputed report for peer {symbol}, skipping")
                continue

            # Parse report and extract price_history
            report = json.loads(row['report_json'])
            price_history = report.get('price_history', [])

            if not price_history:
                logger.warning(f"⚠️ Empty price_history for peer {symbol}, skipping")
                continue

            # Convert to DataFrame
            df = pd.DataFrame(price_history)

            # Map column names to yfinance format
            column_mapping = {
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)

            # Filter out projections
            if 'is_projection' in df.columns:
                df = df[df['is_projection'] == False].copy()

            # Ensure integer index
            df = df.reset_index(drop=True)

            # Truncate to requested number of days (take last N days)
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            # Convert Date to string format (handle numeric dates)
            if df['Date'].dtype in [int, float] or all(df['Date'].astype(str).str.isnumeric()):
                df['Date'] = df['Date'].astype(str)
            else:
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

            peer_data[symbol] = df
            logger.info(f"   ✅ Fetched {len(df)} days for {symbol}")

        except Exception as e:
            logger.warning(f"⚠️ Error fetching peer data for {symbol}: {e}, skipping")
            continue

    if not peer_data:
        raise DataNotFoundError(
            f"No peer data found in Aurora for any of: {peer_symbols}"
        )

    logger.info(f"✅ Fetched peer data for {len(peer_data)}/{len(peer_symbols)} tickers")
    return peer_data


def fetch_indicators_from_aurora(symbol: str, indicator_date: date) -> Dict[str, Any]:
    """Fetch precomputed technical indicators from Aurora.

    Reads from daily_indicators table which contains SMA, RSI, MACD, Bollinger Bands,
    ATR, VWAP, etc. that were precomputed by the Step Function.

    Args:
        symbol: Ticker symbol
        indicator_date: Date to fetch indicators for (usually today)

    Returns:
        Dict with technical indicators:
        {
            'rsi': 65.3,
            'macd': 1.5,
            'sma_20': 100.2,
            'bb_upper': 105.0,
            'bb_lower': 95.0,
            ...
        }

    Raises:
        DataNotFoundError: If no precomputed indicators found for date

    Example:
        >>> from datetime import date
        >>> indicators = fetch_indicators_from_aurora('DBS19', date.today())
        >>> print(f"RSI: {indicators['rsi']}")
    """
    client = get_aurora_client()

    query = """
        SELECT *
        FROM daily_indicators
        WHERE symbol = %s AND date = %s
        LIMIT 1
    """
    row = client.fetch_one(query, (symbol, indicator_date))

    if not row:
        raise DataNotFoundError(
            f"No precomputed indicators found for {symbol} on {indicator_date}"
        )

    # Remove non-indicator columns (symbol, date)
    indicators = {k: v for k, v in row.items() if k not in ('symbol', 'date')}

    logger.info(f"✅ Fetched precomputed indicators from Aurora for {symbol}")
    logger.info(f"   - Indicators: {len(indicators)} fields")

    return indicators


def fetch_percentiles_from_aurora(symbol: str, percentile_date: date) -> Dict[str, Any]:
    """Fetch indicator percentiles from Aurora.

    Reads from indicator_percentiles table which contains percentile rankings
    for various technical indicators (e.g., RSI percentile, volatility percentile).

    Args:
        symbol: Ticker symbol
        percentile_date: Date to fetch percentiles for

    Returns:
        Dict with percentile values:
        {
            'rsi_percentile': 75.0,
            'volatility_percentile': 60.0,
            ...
        }

    Raises:
        DataNotFoundError: If no percentiles found for date

    Example:
        >>> percentiles = fetch_percentiles_from_aurora('DBS19', date.today())
        >>> print(f"RSI is in {percentiles['rsi_percentile']}th percentile")
    """
    client = get_aurora_client()

    query = """
        SELECT *
        FROM indicator_percentiles
        WHERE symbol = %s AND date = %s
        LIMIT 1
    """
    row = client.fetch_one(query, (symbol, percentile_date))

    if not row:
        raise DataNotFoundError(
            f"No percentiles found for {symbol} on {percentile_date}"
        )

    # Remove non-percentile columns
    percentiles = {k: v for k, v in row.items() if k not in ('symbol', 'date')}

    logger.info(f"✅ Fetched percentiles from Aurora for {symbol}")

    return percentiles
