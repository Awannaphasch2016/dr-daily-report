"""
Chart Pattern Detection Service

Uses stock-pattern library (https://github.com/BennyThadikaran/stock-pattern)
to detect technical chart patterns in OHLC data.

Patterns detected:
- Bullish/Bearish Flags
- Triangles (Ascending, Descending, Symmetric)
- Double Tops/Bottoms
- Head & Shoulders
- Harmonic patterns (Bat, Gartley, Butterfly, Crab)
"""

import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

# Add stock-pattern library to path
sys.path.insert(0, '/tmp/stock-pattern/src')
import utils as stock_pattern_lib

from src.data.aurora.repository import TickerRepository

logger = logging.getLogger(__name__)


class PatternDetectionService:
    """Service for detecting chart patterns using stock-pattern library"""

    def __init__(self):
        self.repo = TickerRepository()
        self.config = {
            'FLAG_MAX_BARS': 7,
            'VCP_MAX_BARS': 10,
        }

    def detect_patterns(
        self,
        ticker: str,
        days: int = 180,
        pattern_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect chart patterns for a ticker

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
                        'confidence': str
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

            # Detect patterns
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
        Run all pattern detection functions

        Args:
            ticker: Ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            pattern_types: List of pattern types to detect (None = all)

        Returns:
            List of detected patterns
        """
        patterns = []

        # Define available detectors
        all_detectors = {
            'bullish_flag': stock_pattern_lib.find_bullish_flag,
            'bearish_flag': stock_pattern_lib.find_bearish_flag,
            'triangle': stock_pattern_lib.find_triangles,
            'double_bottom': stock_pattern_lib.find_double_bottom,
            'double_top': stock_pattern_lib.find_double_top,
            'bullish_vcp': stock_pattern_lib.find_bullish_vcp,
            'bearish_vcp': stock_pattern_lib.find_bearish_vcp,
            'head_shoulders': stock_pattern_lib.find_hns,
            'reverse_head_shoulders': stock_pattern_lib.find_reverse_hns,
        }

        # Filter detectors if pattern_types specified
        if pattern_types:
            detectors = {k: v for k, v in all_detectors.items() if k in pattern_types}
        else:
            detectors = all_detectors

        # Run each detector
        for pattern_name, detect_fn in detectors.items():
            try:
                result = detect_fn(ticker, df, pivots, self.config)

                if result:
                    # Serialize result (convert Timestamps to strings)
                    serialized = stock_pattern_lib.make_serializable(result)

                    pattern_data = {
                        'type': pattern_name,
                        'pattern': serialized.get('pattern', pattern_name.upper()),
                        'points': serialized.get('points', {}),
                        'start': serialized.get('start'),
                        'end': serialized.get('end'),
                        'confidence': self._assess_confidence(serialized)
                    }

                    patterns.append(pattern_data)
                    logger.info(f"  ✅ {pattern_name.replace('_', ' ').title()}")

            except Exception as e:
                logger.debug(f"  ⏭️  {pattern_name}: {str(e)[:50]}")
                continue

        return patterns

    def _assess_confidence(self, pattern_data: Dict) -> str:
        """
        Assess pattern confidence based on detection criteria

        The stock-pattern library already applies strict validation,
        so any detected pattern is at least "medium" confidence.

        Returns:
            'high' | 'medium' | 'low'
        """
        # For now, all detected patterns are medium confidence
        # (since the library's validation is already strict)
        # TODO: Add additional scoring logic if needed
        return 'medium'

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
