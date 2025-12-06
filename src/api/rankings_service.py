"""
Market Movers Rankings Service

Fetches real-time market data for all 47 supported tickers and calculates rankings
across different categories: top gainers, top losers, volume surge, and trending.

Features:
- Parallel async fetching using yfinance
- In-memory caching with configurable TTL
- Four ranking categories based on price changes and volume
"""

import asyncio
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Literal
from pathlib import Path

import yfinance as yf
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RankingItem(BaseModel):
    """Single ticker in a ranking"""
    ticker: str = Field(..., description="Ticker symbol (e.g., 'NVDA19')")
    company_name: str = Field(..., description="Company name in Thai")
    price: float = Field(..., description="Current market price")
    price_change_pct: float = Field(..., description="Price change percentage from previous close")
    currency: str = Field(..., description="Currency code (e.g., 'USD')")
    volume_ratio: float = Field(..., description="Current volume / average volume ratio")


RankingCategory = Literal['top_gainers', 'top_losers', 'volume_surge', 'trending']


class RankingsService:
    """
    Service for calculating market movers rankings

    This service fetches data for all 47 tickers in parallel and calculates rankings
    for four categories. Results are cached in memory to reduce API calls.
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize rankings service

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, List[RankingItem]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._ticker_map: Dict[str, str] = {}  # Symbol -> Yahoo ticker mapping
        self._load_tickers()

        logger.info(f"RankingsService initialized with {len(self._ticker_map)} tickers, "
                   f"cache TTL: {cache_ttl_seconds}s")

    def _load_tickers(self) -> None:
        """Load ticker symbol to Yahoo ticker mapping from tickers.csv"""
        try:
            tickers_file = Path(__file__).parent.parent.parent / 'data' / 'tickers.csv'

            if not tickers_file.exists():
                logger.warning(f"tickers.csv not found at {tickers_file}")
                return

            with open(tickers_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row['Symbol'].strip()
                    yahoo_ticker = row['Ticker'].strip()

                    if not symbol or not yahoo_ticker:
                        continue

                    # Map user-friendly symbol (SIA19) to Yahoo ticker (C6L.SI)
                    self._ticker_map[symbol] = yahoo_ticker

            logger.info(f"Loaded {len(self._ticker_map)} ticker mappings from CSV")

        except Exception as e:
            logger.error(f"Error loading tickers: {e}", exc_info=True)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False

        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self.cache_ttl_seconds

    async def _fetch_from_cache(self, symbol: str) -> Optional[Dict]:
        """
        Query Aurora cache for precomputed report data.

        Returns lightweight chart and score data from cached reports,
        or None if cache miss.

        Args:
            symbol: User-friendly symbol (e.g., 'NVDA19', 'SIA19')

        Returns:
            Dict with 'chart_data' and 'key_scores' or None on cache miss
        """
        from src.data.aurora.precompute_service import PrecomputeService
        from datetime import date as date_class

        try:
            service = PrecomputeService()
            cached = service.get_cached_report(symbol, date_class.today())

            if cached and cached.get('report_json'):
                report_json = cached['report_json']

                # Parse JSON if stored as string
                if isinstance(report_json, str):
                    import json
                    report_json = json.loads(report_json)

                # Extract chart data
                chart_data = None
                if any(k in report_json for k in ['price_history', 'projections', 'initial_investment']):
                    chart_data = {
                        'price_history': report_json.get('price_history', []),
                        'projections': report_json.get('projections', []),
                        'initial_investment': report_json.get('initial_investment', 1000.0),
                    }

                # Extract top 3 scores
                key_scores = None
                user_facing_scores = report_json.get('user_facing_scores')
                if user_facing_scores:
                    # user_facing_scores is a dict like {'Technical': {...}, 'Fundamental': {...}}
                    # Convert to list and take top 3
                    if isinstance(user_facing_scores, dict):
                        scores_list = list(user_facing_scores.values())[:3]
                        key_scores = scores_list
                    elif isinstance(user_facing_scores, list):
                        key_scores = user_facing_scores[:3]

                logger.info(f"✅ Cache hit for {symbol}: chart_data={chart_data is not None}, key_scores={key_scores is not None}")

                return {
                    'chart_data': chart_data,
                    'key_scores': key_scores
                }

        except Exception as e:
            logger.warning(f"⚠️ Cache miss for {symbol}: {e}")

        return None

    async def _fetch_ticker_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch real-time data for a single ticker with cached report data

        Args:
            symbol: User-friendly symbol (e.g., 'NVDA19', 'SIA19')

        Returns:
            Dict with ticker data, chart_data, and key_scores (or None if fetch fails)
        """
        try:
            # Get Yahoo ticker from mapping
            yahoo_ticker = self._ticker_map.get(symbol)
            if not yahoo_ticker:
                logger.warning(f"No Yahoo ticker found for symbol: {symbol}")
                return None

            # Run yfinance in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yahoo_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)

            # Extract required fields
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
            volume = info.get('regularMarketVolume') or info.get('volume')
            avg_volume = info.get('averageVolume') or info.get('averageDailyVolume10Day')
            company_name = info.get('shortName') or info.get('longName') or symbol
            currency = info.get('currency') or 'USD'  # Default to USD if not found

            # Validate required fields
            if not all([price, prev_close, volume, avg_volume]):
                logger.warning(f"Missing data for {symbol} ({yahoo_ticker}): price={price}, prev_close={prev_close}, "
                             f"volume={volume}, avg_volume={avg_volume}")
                return None

            # Calculate metrics
            price_change_pct = ((price - prev_close) / prev_close) * 100
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0

            # Fetch cached report data (chart + scores)
            cached_data = await self._fetch_from_cache(symbol)

            result = {
                'ticker': symbol,  # Return user-friendly symbol (NVDA19, not NVDA)
                'company_name': company_name,
                'price': float(price),
                'price_change_pct': round(price_change_pct, 2),
                'currency': currency,
                'volume_ratio': round(volume_ratio, 2),
            }

            # Add cached data if available
            if cached_data:
                if cached_data.get('chart_data'):
                    result['chart_data'] = cached_data['chart_data']
                if cached_data.get('key_scores'):
                    result['key_scores'] = cached_data['key_scores']

            return result

        except Exception as e:
            logger.error(f"Error fetching {symbol} ({yahoo_ticker}): {e}")
            return None

    async def _fetch_all_tickers(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch data for all tickers in parallel

        Args:
            symbols: List of user-friendly symbols (uses all symbols from mapping if None)

        Returns:
            List of ticker data dicts (failed fetches are excluded)
        """
        if symbols is None:
            symbols = list(self._ticker_map.keys())

        if not symbols:
            logger.warning("No symbols to fetch")
            return []

        logger.info(f"Fetching data for {len(symbols)} tickers in parallel...")
        start_time = datetime.now()

        # Fetch all tickers concurrently
        tasks = [self._fetch_ticker_data(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Fetched {len(valid_results)}/{len(symbols)} tickers in {duration:.2f}s")

        return valid_results

    def _calculate_top_gainers(self, ticker_data: List[Dict], limit: Optional[int] = None) -> List[Dict]:
        """
        Calculate top gainers by price change percentage

        Args:
            ticker_data: List of ticker data dicts
            limit: Number of results to return (None = all)

        Returns:
            Sorted list of ticker data dicts by highest price change
        """
        # Filter only positive changes
        gainers = [t for t in ticker_data if t['price_change_pct'] > 0]

        # Sort by price_change_pct descending
        gainers.sort(key=lambda x: x['price_change_pct'], reverse=True)

        # Apply limit
        if limit is not None:
            gainers = gainers[:limit]
        return gainers

    def _calculate_top_losers(self, ticker_data: List[Dict], limit: Optional[int] = None) -> List[Dict]:
        """
        Calculate top losers by price change percentage

        Args:
            ticker_data: List of ticker data dicts
            limit: Number of results to return (None = all)

        Returns:
            Sorted list of ticker data dicts by lowest price change
        """
        # Filter only negative changes
        losers = [t for t in ticker_data if t['price_change_pct'] < 0]

        # Sort by price_change_pct ascending (most negative first)
        losers.sort(key=lambda x: x['price_change_pct'])

        # Apply limit
        if limit is not None:
            losers = losers[:limit]
        return losers

    def _calculate_volume_surge(self, ticker_data: List[Dict], limit: Optional[int] = None) -> List[Dict]:
        """
        Calculate volume surge by volume ratio

        Args:
            ticker_data: List of ticker data dicts
            limit: Number of results to return (None = all)

        Returns:
            Sorted list of ticker data dicts by highest volume ratio
        """
        # Filter tickers with volume ratio > 1.5 (50% above average)
        volume_surge = [t for t in ticker_data if t['volume_ratio'] > 1.5]

        # Sort by volume_ratio descending
        volume_surge.sort(key=lambda x: x['volume_ratio'], reverse=True)

        # Apply limit
        if limit is not None:
            volume_surge = volume_surge[:limit]
        return volume_surge

    def _calculate_trending(self, ticker_data: List[Dict], limit: Optional[int] = None) -> List[Dict]:
        """
        Calculate trending tickers by momentum score

        Momentum score = price_change_pct + volume_ratio
        This captures both price movement and volume activity

        Args:
            ticker_data: List of ticker data dicts
            limit: Number of results to return (None = all)

        Returns:
            Sorted list of ticker data dicts by highest momentum score
        """
        # Calculate momentum score for each ticker (create copies to avoid mutating original)
        trending_data = []
        for ticker in ticker_data:
            t_copy = ticker.copy()
            t_copy['momentum_score'] = ticker['price_change_pct'] + ticker['volume_ratio']
            trending_data.append(t_copy)

        # Sort by momentum_score descending
        trending_data.sort(key=lambda x: x['momentum_score'], reverse=True)

        # Apply limit and remove momentum_score (internal metric)
        items = trending_data if limit is None else trending_data[:limit]
        return [{k: v for k, v in t.items() if k != 'momentum_score'} for t in items]

    async def get_rankings(
        self,
        category: RankingCategory,
        limit: int = 10,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Get market rankings for a specific category

        Args:
            category: Ranking category ('top_gainers', 'top_losers', 'volume_surge', 'trending')
            limit: Maximum number of results to return
            force_refresh: Force refresh even if cache is valid

        Returns:
            List of ticker data dicts sorted by category criteria (includes chart_data and key_scores if cached)

        Raises:
            ValueError: If category is invalid
        """
        valid_categories = ['top_gainers', 'top_losers', 'volume_surge', 'trending']
        if category not in valid_categories:
            raise ValueError(f"Invalid category: {category}. Must be one of {valid_categories}")

        # Check cache
        if not force_refresh and self._is_cache_valid() and category in self._cache:
            logger.info(f"Using cached data for {category}")
            return self._cache[category][:limit]

        # Fetch fresh data
        logger.info(f"Fetching fresh data for {category}")
        ticker_data = await self._fetch_all_tickers()

        if not ticker_data:
            logger.warning("No ticker data available")
            return []

        # Calculate all rankings and update cache (no limit, cache everything)
        self._cache = {
            'top_gainers': self._calculate_top_gainers(ticker_data, limit=None),
            'top_losers': self._calculate_top_losers(ticker_data, limit=None),
            'volume_surge': self._calculate_volume_surge(ticker_data, limit=None),
            'trending': self._calculate_trending(ticker_data, limit=None),
        }
        self._cache_timestamp = datetime.now()

        logger.info(f"Cache updated at {self._cache_timestamp}")

        # Apply limit when returning
        return self._cache[category][:limit]

    async def get_all_rankings(self, limit: int = 10) -> Dict[str, List[RankingItem]]:
        """
        Get rankings for all categories at once

        Args:
            limit: Maximum number of results per category

        Returns:
            Dict mapping category name to list of RankingItem
        """
        # This will populate all categories in cache
        await self.get_rankings('top_gainers', limit=limit)

        # Return all from cache
        return {
            category: items[:limit]
            for category, items in self._cache.items()
        }

    def clear_cache(self):
        """Clear the rankings cache"""
        self._cache = {}
        self._cache_timestamp = None
        logger.info("Cache cleared")


# Singleton instance
_rankings_service: Optional[RankingsService] = None


def get_rankings_service() -> RankingsService:
    """Get or create singleton RankingsService instance"""
    global _rankings_service
    if _rankings_service is None:
        _rankings_service = RankingsService(cache_ttl_seconds=300)  # 5 minutes
    return _rankings_service
