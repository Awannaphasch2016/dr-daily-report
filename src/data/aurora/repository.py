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

logger = logging.getLogger(__name__)


class TickerRepository:
    """Repository for ticker data operations.

    Provides CRUD operations for:
    - ticker_info: Company metadata
    - daily_prices: Historical OHLCV data

    Example:
        >>> repo = TickerRepository()
        >>> repo.upsert_ticker_info('NVDA', 'NVIDIA', market='us_market')
        >>> prices = repo.get_prices('NVDA', start_date='2025-01-01')
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        """Initialize repository.

        Args:
            client: AuroraClient instance (uses singleton if not provided)
        """
        self.client = client or get_aurora_client()

    # =========================================================================
    # Ticker Info Operations
    # =========================================================================

    def upsert_ticker_info(
        self,
        symbol: str,
        display_name: str,
        company_name: Optional[str] = None,
        exchange: Optional[str] = None,
        market: Optional[str] = None,
        currency: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        quote_type: Optional[str] = None,
    ) -> int:
        """Insert or update ticker info.

        Args:
            symbol: Ticker symbol (e.g., 'NVDA', 'DBS.SI')
            display_name: Display name
            company_name: Full company name
            exchange: Exchange code (e.g., 'NMS', 'SGX')
            market: Market classification
            currency: Trading currency
            sector: Business sector
            industry: Industry classification
            quote_type: Type (EQUITY, ETF, etc.)

        Returns:
            Number of affected rows (1 for insert, 2 for update)
        """
        query = """
            INSERT INTO ticker_info (
                symbol, display_name, company_name, exchange, market,
                currency, sector, industry, quote_type, last_fetched_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                display_name = VALUES(display_name),
                company_name = VALUES(company_name),
                exchange = VALUES(exchange),
                market = VALUES(market),
                currency = VALUES(currency),
                sector = VALUES(sector),
                industry = VALUES(industry),
                quote_type = VALUES(quote_type),
                last_fetched_at = NOW()
        """
        params = (
            symbol, display_name, company_name, exchange, market,
            currency, sector, industry, quote_type
        )
        return self.client.execute(query, params)

    def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker info by symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Dict with ticker info or None if not found
        """
        query = "SELECT * FROM ticker_info WHERE symbol = %s AND is_active = TRUE"
        return self.client.fetch_one(query, (symbol,))

    def get_all_tickers(self, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active tickers.

        Args:
            market: Optional market filter

        Returns:
            List of ticker info dicts
        """
        if market:
            query = "SELECT * FROM ticker_info WHERE is_active = TRUE AND market = %s ORDER BY symbol"
            return self.client.fetch_all(query, (market,))
        else:
            query = "SELECT * FROM ticker_info WHERE is_active = TRUE ORDER BY symbol"
            return self.client.fetch_all(query)

    def bulk_upsert_ticker_info(self, tickers: List[Dict[str, Any]]) -> int:
        """Bulk insert/update ticker info.

        Args:
            tickers: List of ticker info dicts with keys matching columns

        Returns:
            Number of affected rows
        """
        query = """
            INSERT INTO ticker_info (
                symbol, display_name, company_name, exchange, market,
                currency, sector, industry, quote_type, last_fetched_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                display_name = VALUES(display_name),
                company_name = VALUES(company_name),
                exchange = VALUES(exchange),
                market = VALUES(market),
                currency = VALUES(currency),
                sector = VALUES(sector),
                industry = VALUES(industry),
                quote_type = VALUES(quote_type),
                last_fetched_at = NOW()
        """
        params_list = [
            (
                t['symbol'],
                t.get('display_name', t['symbol']),
                t.get('company_name'),
                t.get('exchange'),
                t.get('market'),
                t.get('currency'),
                t.get('sector'),
                t.get('industry'),
                t.get('quote_type'),
            )
            for t in tickers
        ]
        return self.client.execute_many(query, params_list)

    # =========================================================================
    # Daily Prices Operations
    # =========================================================================

    def upsert_daily_price(
        self,
        symbol: str,
        price_date: date,
        open_price: float,
        high: float,
        low: float,
        close: float,
        adj_close: Optional[float] = None,
        volume: Optional[int] = None,
    ) -> int:
        """Insert or update a single daily price.

        Args:
            symbol: Ticker symbol
            price_date: Date of the price
            open_price: Opening price
            high: High price
            low: Low price
            close: Closing price
            adj_close: Adjusted close price
            volume: Trading volume

        Returns:
            Number of affected rows
        """
        # Get ticker_id
        ticker_info = self.get_ticker_info(symbol)
        if not ticker_info:
            raise ValueError(f"Ticker not found: {symbol}. Insert into ticker_info first.")

        ticker_id = ticker_info['id']

        # Calculate daily return
        prev_close = self._get_previous_close(symbol, price_date)
        daily_return = None
        if prev_close and prev_close != 0:
            daily_return = (close - prev_close) / prev_close

        query = """
            INSERT INTO daily_prices (
                ticker_id, symbol, price_date,
                open, high, low, close, adj_close, volume, daily_return
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                open = VALUES(open),
                high = VALUES(high),
                low = VALUES(low),
                close = VALUES(close),
                adj_close = VALUES(adj_close),
                volume = VALUES(volume),
                daily_return = VALUES(daily_return),
                fetched_at = NOW()
        """
        params = (
            ticker_id, symbol, price_date,
            open_price, high, low, close, adj_close, volume, daily_return
        )
        return self.client.execute(query, params)

    def bulk_upsert_daily_prices(
        self,
        symbol: str,
        prices: List[Dict[str, Any]]
    ) -> int:
        """Bulk insert/update daily prices for a symbol.

        Args:
            symbol: Ticker symbol
            prices: List of price dicts with keys: date, open, high, low, close, adj_close, volume

        Returns:
            Number of affected rows

        Example:
            >>> prices = [
            ...     {'date': '2025-01-01', 'open': 100, 'high': 105, 'low': 99, 'close': 104, 'volume': 1000000},
            ...     {'date': '2025-01-02', 'open': 104, 'high': 108, 'low': 103, 'close': 107, 'volume': 1200000},
            ... ]
            >>> repo.bulk_upsert_daily_prices('NVDA', prices)
        """
        # Get ticker_id
        ticker_info = self.get_ticker_info(symbol)
        if not ticker_info:
            raise ValueError(f"Ticker not found: {symbol}. Insert into ticker_info first.")

        ticker_id = ticker_info['id']

        query = """
            INSERT INTO daily_prices (
                ticker_id, symbol, price_date,
                open, high, low, close, adj_close, volume
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                open = VALUES(open),
                high = VALUES(high),
                low = VALUES(low),
                close = VALUES(close),
                adj_close = VALUES(adj_close),
                volume = VALUES(volume),
                fetched_at = NOW()
        """
        params_list = [
            (
                ticker_id,
                symbol,
                p.get('date') or p.get('price_date'),
                p.get('open'),
                p.get('high'),
                p.get('low'),
                p.get('close'),
                p.get('adj_close') or p.get('close'),
                p.get('volume'),
            )
            for p in prices
        ]
        return self.client.execute_many(query, params_list)

    def bulk_upsert_from_dataframe(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> int:
        """Bulk insert/update from pandas DataFrame (yfinance format).

        Args:
            symbol: Ticker symbol
            df: DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Adj Close, Volume

        Returns:
            Number of affected rows

        Example:
            >>> import yfinance as yf
            >>> ticker = yf.Ticker('NVDA')
            >>> hist = ticker.history(period='1y')
            >>> repo.bulk_upsert_from_dataframe('NVDA', hist)
        """
        if df.empty:
            logger.warning(f"Empty DataFrame for {symbol}, skipping insert")
            return 0

        # Get ticker_id
        ticker_info = self.get_ticker_info(symbol)
        if not ticker_info:
            raise ValueError(f"Ticker not found: {symbol}. Insert into ticker_info first.")

        ticker_id = ticker_info['id']

        # Convert DataFrame to list of tuples
        query = """
            INSERT INTO daily_prices (
                ticker_id, symbol, price_date,
                open, high, low, close, adj_close, volume
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                open = VALUES(open),
                high = VALUES(high),
                low = VALUES(low),
                close = VALUES(close),
                adj_close = VALUES(adj_close),
                volume = VALUES(volume),
                fetched_at = NOW()
        """

        params_list = []
        for idx, row in df.iterrows():
            # Handle various date formats
            price_date = None

            # First, check if index is a valid date
            if hasattr(idx, 'date'):
                price_date = idx.date()
            elif isinstance(idx, str) and len(idx) == 10 and '-' in idx:
                try:
                    price_date = datetime.strptime(idx, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # If index isn't a date, look for 'Date' column in the row
            if price_date is None:
                date_col = row.get('Date') or row.get('date')
                if date_col is not None:
                    if hasattr(date_col, 'date'):
                        price_date = date_col.date()
                    elif isinstance(date_col, str):
                        price_date = datetime.strptime(date_col, '%Y-%m-%d').date()
                    elif isinstance(date_col, date):
                        price_date = date_col

            # Skip row if no valid date found
            if price_date is None:
                logger.warning(f"Skipping row with invalid date: idx={idx}, row={dict(row)}")
                continue

            params_list.append((
                ticker_id,
                symbol,
                price_date,
                self._to_float(row.get('Open')),
                self._to_float(row.get('High')),
                self._to_float(row.get('Low')),
                self._to_float(row.get('Close')),
                self._to_float(row.get('Adj Close') or row.get('Close')),
                self._to_int(row.get('Volume')),
            ))

        return self.client.execute_many(query, params_list)

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
            SELECT * FROM daily_prices
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
        query = """
            SELECT * FROM daily_prices
            WHERE symbol = %s
            ORDER BY price_date DESC
            LIMIT 1
        """
        return self.client.fetch_one(query, (symbol,))

    def get_latest_prices_all(self) -> List[Dict[str, Any]]:
        """Get latest prices for all tickers.

        Returns:
            List of latest price dicts for all active tickers
        """
        query = """
            SELECT dp.*, ti.display_name, ti.company_name, ti.sector
            FROM daily_prices dp
            INNER JOIN ticker_info ti ON dp.symbol = ti.symbol
            WHERE dp.price_date = (
                SELECT MAX(price_date)
                FROM daily_prices
                WHERE symbol = dp.symbol
            )
            AND ti.is_active = TRUE
            ORDER BY dp.symbol
        """
        return self.client.fetch_all(query)

    def _get_previous_close(self, symbol: str, price_date: date) -> Optional[float]:
        """Get the previous day's close price."""
        query = """
            SELECT close FROM daily_prices
            WHERE symbol = %s AND price_date < %s
            ORDER BY price_date DESC
            LIMIT 1
        """
        result = self.client.fetch_one(query, (symbol, price_date))
        if result:
            return float(result['close']) if result['close'] else None
        return None

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
        query = """
            INSERT INTO ticker_cache_metadata (
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

        # Ticker count
        result = self.client.fetch_one("SELECT COUNT(*) as count FROM ticker_info WHERE is_active = TRUE")
        stats['ticker_count'] = result['count'] if result else 0

        # Price row count
        result = self.client.fetch_one("SELECT COUNT(*) as count FROM daily_prices")
        stats['price_row_count'] = result['count'] if result else 0

        # Date range
        result = self.client.fetch_one("""
            SELECT MIN(price_date) as min_date, MAX(price_date) as max_date
            FROM daily_prices
        """)
        if result:
            stats['min_date'] = str(result['min_date']) if result['min_date'] else None
            stats['max_date'] = str(result['max_date']) if result['max_date'] else None

        return stats
