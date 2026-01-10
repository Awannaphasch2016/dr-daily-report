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

            return {
                'ticker': ticker,
                'data_range': {
                    'start': df.index[0].strftime('%Y-%m-%d'),
                    'end': df.index[-1].strftime('%Y-%m-%d')
                },
                'bars': len(df),
                'pivots': len(pivots),
                'patterns': patterns
            }

        except Exception as e:
            logger.error(f"Error detecting patterns for {ticker}: {e}", exc_info=True)
            return self._empty_result(ticker, error=str(e))

    def _fetch_ohlc_data(self, ticker: str, days: int) -> pd.DataFrame:
        """Fetch OHLC data from Aurora"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        df = self.repo.get_prices_as_dataframe(
            symbol=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=days + 30  # Buffer for weekends/holidays
        )

        return df

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
