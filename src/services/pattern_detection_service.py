"""
Chart Pattern Detection Service

Uses registry pattern to support multiple pattern detection implementations:
- stock-pattern library (https://github.com/BennyThadikaran/stock-pattern)
- Custom internal detectors (src/analysis/pattern_detectors/)

The registry enables:
- Runtime selection between implementations
- Priority-based fallback (stock-pattern preferred, custom as fallback)
- Easy addition of new implementations (TA-Lib, custom ML models, etc.)

Patterns detected:
- Bullish/Bearish Flags
- Triangles (Ascending, Descending, Symmetric)
- Double Tops/Bottoms
- Head & Shoulders
- VCP (Volatility Contraction Pattern)
- Wedges (Rising, Falling)
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from src.data.aurora.repository import TickerRepository
from src.analysis.pattern_detectors import (
    get_pattern_registry,
    StockPatternAdapter,
    CustomPatternAdapter,
)

logger = logging.getLogger(__name__)


class PatternDetectionService:
    """
    Service for detecting chart patterns using pluggable implementations.

    Uses registry pattern to support multiple detection backends:
    - StockPatternAdapter: External stock-pattern library (priority=10)
    - CustomPatternAdapter: Internal detectors (priority=5, fallback)

    The registry automatically falls back to custom implementation when
    stock-pattern library is unavailable (e.g., in Lambda environment).
    """

    def __init__(self, impl_name: Optional[str] = None):
        """
        Initialize pattern detection service.

        Args:
            impl_name: Force specific implementation ('stock_pattern' or 'custom').
                       If None, uses priority-based selection with fallback.
        """
        self.repo = TickerRepository()
        self.config = {
            'FLAG_MAX_BARS': 7,
            'VCP_MAX_BARS': 10,
        }
        self.impl_name = impl_name

        # Initialize registry with adapters
        self._registry = get_pattern_registry()
        self._init_registry()

    def _init_registry(self) -> None:
        """Initialize registry with available pattern detector adapters."""
        # Register stock-pattern adapter (preferred, priority=10)
        stock_adapter = StockPatternAdapter()
        if stock_adapter.is_available():
            self._registry.register_detector(stock_adapter, priority=10)
            logger.info("Registered stock-pattern adapter (priority=10)")
        else:
            logger.debug("stock-pattern library not available, skipping registration")

        # Register custom adapter (fallback, priority=5)
        custom_adapter = CustomPatternAdapter()
        self._registry.register_detector(custom_adapter, priority=5)
        logger.info("Registered custom pattern adapter (priority=5)")

        # Log registry stats
        stats = self._registry.get_stats()
        logger.info(
            f"Pattern registry initialized: {stats['pattern_types']} pattern types, "
            f"{stats['available_implementations']} available implementations"
        )

    def detect_patterns(
        self,
        ticker: str,
        days: int = 180,
        pattern_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect chart patterns for a ticker.

        Uses registry to select between implementations with automatic fallback.

        Args:
            ticker: Stock ticker symbol
            days: Number of days of historical data to analyze
            pattern_types: List of pattern types to detect (None = all)

        Returns:
            {
                'ticker': str,
                'data_range': {'start': str, 'end': str},
                'patterns': [
                    {
                        'type': str,
                        'pattern': str,
                        'points': {...},
                        'confidence': str,
                        'implementation': str  # Which detector found it
                    }
                ]
            }
        """
        logger.info(f"Detecting patterns for {ticker} (last {days} days)")

        try:
            # Fetch OHLC data
            df = self._fetch_ohlc_data(ticker, days)

            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {ticker}: {len(df)} bars")
                return self._empty_result(ticker)

            # Find pivot points
            pivots = self._find_pivots(df)

            if len(pivots) < 5:
                logger.warning(f"Insufficient pivots for {ticker}: {len(pivots)} pivots")
                return self._empty_result(ticker)

            # Detect patterns using registry
            patterns = self._detect_all_patterns(ticker, df, pivots, pattern_types)

            logger.info(f"✅ {ticker}: {len(patterns)} pattern(s) detected")

            # Handle data_range for both date-indexed and numeric-indexed DataFrames
            # DatetimeIndex has strftime, RangeIndex (from precomputed fallback) does not
            if hasattr(df.index[0], 'strftime'):
                data_range = {
                    'start': df.index[0].strftime('%Y-%m-%d'),
                    'end': df.index[-1].strftime('%Y-%m-%d')
                }
            else:
                # Numeric index from precomputed_reports fallback
                data_range = {
                    'start': f"bar_{df.index[0]}",
                    'end': f"bar_{df.index[-1]}"
                }

            return {
                'ticker': ticker,
                'data_range': data_range,
                'bars': len(df),
                'pivots': len(pivots),
                'patterns': patterns
            }

        except Exception as e:
            logger.error(f"Error detecting patterns for {ticker}: {e}", exc_info=True)
            return self._empty_result(ticker, error=str(e))

    def _fetch_ohlc_data(self, ticker: str, days: int) -> pd.DataFrame:
        """Fetch OHLC data from Aurora.

        Tries daily_prices table first, then falls back to precomputed_reports
        which contains price_history embedded in report_json.

        Args:
            ticker: Ticker symbol (DR format like 'NVDA19' or Yahoo like 'NVDA')
            days: Number of days of historical data to fetch

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Try daily_prices table first (primary source)
        df = self.repo.get_prices_as_dataframe(
            symbol=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=days + 30  # Buffer for weekends/holidays
        )

        if not df.empty:
            return df

        # Fallback: Extract price_history from precomputed_reports
        # This supports dev environment where daily_prices table may be empty
        logger.debug(f"daily_prices empty for {ticker}, trying precomputed_reports fallback")
        df = self._fetch_ohlc_from_precomputed(ticker)

        return df

    def _fetch_ohlc_from_precomputed(self, ticker: str) -> pd.DataFrame:
        """Extract OHLC data from precomputed_reports.report_json.price_history.

        The price_history in precomputed reports contains OHLCV data with
        indexed dates (0, 1, 2, ...). We convert this to a DataFrame suitable
        for pattern detection.

        Args:
            ticker: Ticker symbol

        Returns:
            DataFrame with numeric index and OHLCV columns, or empty DataFrame
        """
        try:
            from src.data.aurora.precompute_service import PrecomputeService

            precompute = PrecomputeService()
            cached = precompute.get_cached_report(ticker)

            if not cached:
                logger.debug(f"No cached report for {ticker}")
                return pd.DataFrame()

            report_json = cached.get('report_json')
            if not report_json:
                logger.debug(f"No report_json in cached report for {ticker}")
                return pd.DataFrame()

            # Parse JSON if string
            if isinstance(report_json, str):
                import json
                report_json = json.loads(report_json)

            price_history = report_json.get('price_history', [])
            if not price_history:
                logger.debug(f"No price_history in report for {ticker}")
                return pd.DataFrame()

            # Filter to actual price data (exclude projections)
            actual_prices = [p for p in price_history if not p.get('is_projection', False)]

            if len(actual_prices) < 50:
                logger.debug(f"Insufficient price_history for {ticker}: {len(actual_prices)} bars")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(actual_prices)

            # Rename columns to match expected format
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)

            # Create a date-like index based on position
            # Pattern detection uses index position, not actual dates
            df.index = pd.RangeIndex(len(df))

            # Ensure numeric types
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            logger.info(f"✅ Loaded {len(df)} bars from precomputed_reports for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching from precomputed_reports: {e}")
            return pd.DataFrame()

    def _find_pivots(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Find pivot points (local highs and lows)

        Args:
            df: OHLC DataFrame
            window: Window size for pivot detection

        Returns:
            DataFrame with pivot points (columns: P, type)
        """
        pivots_data = []

        for i in range(window, len(df) - window):
            window_slice = slice(i - window, i + window + 1)

            # Local high
            if df['High'].iloc[i] == df['High'].iloc[window_slice].max():
                pivots_data.append({
                    'date': df.index[i],
                    'P': df['High'].iloc[i],
                    'type': 'high'
                })
            # Local low
            elif df['Low'].iloc[i] == df['Low'].iloc[window_slice].min():
                pivots_data.append({
                    'date': df.index[i],
                    'P': df['Low'].iloc[i],
                    'type': 'low'
                })

        if not pivots_data:
            return pd.DataFrame(columns=['P', 'type'])

        pivots_df = pd.DataFrame(pivots_data)
        pivots_df.set_index('date', inplace=True)

        return pivots_df

    def _detect_all_patterns(
        self,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        pattern_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run pattern detection using registry with fallback.

        Uses registry to select implementations automatically:
        - Tries highest priority implementation first (stock-pattern if available)
        - Falls back to lower priority implementations on failure
        - Each pattern type is detected independently

        Args:
            ticker: Ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            pattern_types: List of pattern types to detect (None = all)

        Returns:
            List of detected patterns with 'implementation' field
        """
        patterns = []

        # Default pattern types to detect
        all_pattern_types = [
            'bullish_flag', 'bearish_flag',
            'triangle',
            'double_bottom', 'double_top',
            'bullish_vcp', 'bearish_vcp',
            'head_shoulders', 'reverse_head_shoulders',
        ]

        # Filter if specific types requested
        types_to_detect = pattern_types or all_pattern_types

        # Run each pattern type through registry
        for pattern_type in types_to_detect:
            try:
                # Use registry with automatic fallback
                result = self._registry.detect_with_fallback(
                    pattern_type=pattern_type,
                    ticker=ticker,
                    df=df,
                    pivots=pivots,
                    config=self.config
                )

                if result:
                    patterns.append(result)
                    impl = result.get('implementation', 'unknown')
                    logger.info(f"  ✅ {pattern_type.replace('_', ' ').title()} [{impl}]")

            except Exception as e:
                logger.debug(f"  ⏭️  {pattern_type}: {str(e)[:50]}")
                continue

        return patterns

    def get_available_implementations(self, pattern_type: str) -> List[tuple]:
        """
        Get available implementations for a pattern type.

        Args:
            pattern_type: Pattern type to query

        Returns:
            List of (impl_name, priority, is_available) tuples
        """
        return self._registry.list_implementations(pattern_type)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the pattern detector registry."""
        return self._registry.get_stats()

    def _empty_result(self, ticker: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty result structure"""
        result = {
            'ticker': ticker,
            'data_range': None,
            'bars': 0,
            'pivots': 0,
            'patterns': []
        }

        if error:
            result['error'] = error

        return result


# Singleton instance
_pattern_service: Optional[PatternDetectionService] = None


def get_pattern_service() -> PatternDetectionService:
    """Get or create singleton pattern detection service"""
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternDetectionService()
    return _pattern_service
