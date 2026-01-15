# -*- coding: utf-8 -*-
"""
Ticker Repository

Data access layer for ticker data operations in Aurora MySQL.
Provides high-level methods for ticker info and price data.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import DAILY_PRICES, TICKER_CACHE_METADATA

logger = logging.getLogger(__name__)


class TickerRepository:
    """Repository for ticker data operations.

    Provides CRUD operations for:
    - ticker_data: Historical OHLCV data with company metadata
    - daily_indicators: Technical indicators

    Note: ticker_info table removed (migration 018) - use ticker_master + ticker_aliases instead

    Example:
        >>> repo = TickerRepository()
        >>> prices = repo.get_ticker_data('NVDA', start_date='2025-01-01')
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        """Initialize repository.

        Args:
            client: AuroraClient instance (uses singleton if not provided)
        """
        self.client = client or get_aurora_client()

    # =========================================================================
    # Ticker Lookup Operations
    # =========================================================================

    def get_ticker_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker info from ticker_master by symbol via ticker_aliases.

        Note: ticker_master doesn't have symbol column. Symbols are in ticker_aliases
        which references ticker_master.id via ticker_id.

        Args:
            symbol: Ticker symbol (e.g., 'NVDA19', 'D05.SI')

        Returns:
            Dict with id, symbol, company_name, etc. or None if not found
        """
        query = """
            SELECT
                m.id,
                a.symbol,
                m.company_name,
                m.sector,
                m.exchange,
                m.is_active,
                m.created_at,
                m.updated_at
            FROM ticker_aliases a
            JOIN ticker_master m ON a.ticker_id = m.id
            WHERE a.symbol = %s
            LIMIT 1
        """
        return self.client.fetch_one(query, (symbol,))

    # =========================================================================
    # Historical Price Query Operations (Read-only)
    # =========================================================================
    # Note: Write operations removed (migration 018) due to ticker_info dependency
    # If Aurora historical data storage is needed, refactor to use ticker_master

    def get_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365
    ) -> List[Dict[str, Any]]:
        """Get historical prices for a symbol.

        Args:
            symbol: Ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum rows to return

        Returns:
            List of price dicts ordered by date descending
        """
        conditions = ["symbol = %s"]
        params = [symbol]

        if start_date:
            conditions.append("price_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("price_date <= %s")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT * FROM {DAILY_PRICES}
            WHERE {where_clause}
            ORDER BY price_date DESC
            LIMIT %s
        """
        params.append(limit)

        return self.client.fetch_all(query, tuple(params))

    def get_prices_as_dataframe(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365
    ) -> pd.DataFrame:
        """Get historical prices as pandas DataFrame.

        Args:
            symbol: Ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum rows to return

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns
        """
        prices = self.get_prices(symbol, start_date, end_date, limit)

        if not prices:
            return pd.DataFrame()

        df = pd.DataFrame(prices)
        df['price_date'] = pd.to_datetime(df['price_date'])
        df.set_index('price_date', inplace=True)
        df.sort_index(inplace=True)

        # Rename columns to match yfinance format
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'adj_close': 'Adj Close',
            'volume': 'Volume'
        }, inplace=True)

        # Convert Decimal to float (MySQL returns Decimal, pandas expects float)
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]

    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the latest price for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Latest price dict or None
        """
        query = f"""
            SELECT * FROM {DAILY_PRICES}
            WHERE symbol = %s
            ORDER BY price_date DESC
            LIMIT 1
        """
        return self.client.fetch_one(query, (symbol,))

    @staticmethod
    def _to_float(value) -> Optional[float]:
        """Convert value to float, handling NaN and None."""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            import math
            if math.isnan(float(value)):
                return None
            return float(value)
        return None

    @staticmethod
    def _to_int(value) -> Optional[int]:
        """Convert value to int, handling NaN and None."""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            import math
            if math.isnan(float(value)):
                return None
            return int(value)
        return None

    # =========================================================================
    # Cache Metadata Operations
    # =========================================================================

    def update_cache_status(
        self,
        symbol: str,
        cache_date: date,
        status: str,
        s3_key: Optional[str] = None,
        rows_count: int = 0,
        error_message: Optional[str] = None
    ) -> int:
        """Update cache status for sync tracking.

        Args:
            symbol: Ticker symbol
            cache_date: Date of cached data
            status: Status ('pending', 'cached', 'expired', 'error')
            s3_key: S3 key path
            rows_count: Number of rows synced
            error_message: Error message if status is 'error'

        Returns:
            Number of affected rows
        """
        query = f"""
            INSERT INTO {TICKER_CACHE_METADATA} (
                symbol, cache_date, status, s3_key,
                rows_in_aurora, error_message, cached_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                s3_key = VALUES(s3_key),
                rows_in_aurora = VALUES(rows_in_aurora),
                error_message = VALUES(error_message),
                cached_at = NOW(),
                updated_at = NOW()
        """
        params = (symbol, cache_date, status, s3_key, rows_count, error_message)
        return self.client.execute(query, params)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with counts and date ranges
        """
        stats = {}

        # Ticker count (from ticker_master instead of removed ticker_info)
        result = self.client.fetch_one("SELECT COUNT(*) as count FROM ticker_master WHERE is_active = TRUE")
        stats['ticker_count'] = result['count'] if result else 0

        # Price row count
        result = self.client.fetch_one(f"SELECT COUNT(*) as count FROM {DAILY_PRICES}")
        stats['price_row_count'] = result['count'] if result else 0

        # Date range
        result = self.client.fetch_one(f"""
            SELECT MIN(price_date) as min_date, MAX(price_date) as max_date
            FROM {DAILY_PRICES}
        """)
        if result:
            stats['min_date'] = str(result['min_date']) if result['min_date'] else None
            stats['max_date'] = str(result['max_date']) if result['max_date'] else None

        return stats
