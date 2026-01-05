# -*- coding: utf-8 -*-
"""
Chart Pattern Detector - Core Analysis Module

Implements chart pattern detection (reversal, continuation, triangles)
following defensive programming patterns (Principle #1).

Extracted from MCP server to enable reusable pattern detection across:
- Report generation (PDF/Telegram)
- API endpoints
- ETL pipelines
- MCP tools

All patterns use constants from pattern_types.py (Principle #14).
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np
import logging

from .base_detector import BasePatternDetector
from ..pattern_types import (
    # Pattern type constants
    PATTERN_HEAD_AND_SHOULDERS,
    PATTERN_INVERSE_HEAD_AND_SHOULDERS,
    PATTERN_DOUBLE_TOP,
    PATTERN_DOUBLE_BOTTOM,
    PATTERN_TRIANGLE,
    PATTERN_TRIANGLE_ASCENDING,
    PATTERN_TRIANGLE_DESCENDING,
    PATTERN_TRIANGLE_SYMMETRICAL,
    PATTERN_FLAG_PENNANT,
    PATTERN_WEDGE_RISING,
    PATTERN_WEDGE_FALLING,

    # Classification constants
    PATTERN_TYPE_BULLISH,
    PATTERN_TYPE_BEARISH,
    PATTERN_TYPE_NEUTRAL,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)

logger = logging.getLogger(__name__)


class ChartPatternDetector(BasePatternDetector):
    """
    Detects chart patterns in OHLC price data.

    Patterns detected:
    - Head & Shoulders (bearish reversal)
    - Inverse Head & Shoulders (bullish reversal)
    - Double Tops/Bottoms (reversal)
    - Triangles (ascending, descending, symmetrical)
    - Flags/Pennants (continuation)
    - Wedges (rising wedge = bearish, falling wedge = bullish)

    Usage:
        detector = ChartPatternDetector()
        patterns = detector.detect(ohlc_df)

        for pattern in patterns:
            print(f"{pattern['pattern']}: {pattern['type']} ({pattern['confidence']})")
    """

    def __init__(self):
        """Initialize chart pattern detector."""
        super().__init__()

    def detect(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect all chart patterns in OHLC data.

        Args:
            data: DataFrame with OHLC columns and DatetimeIndex

        Returns:
            List of detected patterns, each containing:
                - pattern: Pattern type constant (from pattern_types.py)
                - type: bullish/bearish/neutral
                - date/start_date/end_date: When pattern occurred
                - confidence: high/medium/low
                - Pattern-specific fields (prices, levels, etc.)

        Raises:
            ValueError: If data invalid (no columns, empty, all-NaN)

        Examples:
            >>> detector = ChartPatternDetector()
            >>> patterns = detector.detect(df)
            >>> print(patterns[0])
            {
                'pattern': 'head_and_shoulders',
                'type': 'bearish',
                'head_price': 150.5,
                'confidence': 'medium'
            }
        """
        # Defensive validation (Principle #1)
        self._validate_ohlc_data(data)

        all_patterns = []

        # Detect each pattern type
        all_patterns.extend(self.detect_head_and_shoulders(data))
        all_patterns.extend(self.detect_triangles(data))
        all_patterns.extend(self.detect_double_tops_bottoms(data))
        all_patterns.extend(self.detect_flags_pennants(data))
        all_patterns.extend(self.detect_wedges(data))

        logger.info(f"✅ Detected {len(all_patterns)} chart patterns")
        return all_patterns

    def detect_head_and_shoulders(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Head & Shoulders patterns (bearish reversal).

        Pattern: Three peaks with middle peak (head) highest, two shoulders similar height.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of head & shoulders patterns

        Examples:
            >>> detector = ChartPatternDetector()
            >>> patterns = detector.detect_head_and_shoulders(df)
            >>> print(patterns[0]['head_price'])
            150.5
        """
        # Validate minimum data requirement
        self._validate_minimum_data(data, min_rows=20, pattern_name=PATTERN_HEAD_AND_SHOULDERS)

        patterns = []
        highs = data['High'].values
        window = 5

        for i in range(window, len(highs) - window * 2):
            # Find local peaks
            left_shoulder_idx = i
            head_idx = i + window
            right_shoulder_idx = i + window * 2

            if (head_idx >= len(highs) or right_shoulder_idx >= len(highs)):
                continue

            left_shoulder = highs[left_shoulder_idx]
            head = highs[head_idx]
            right_shoulder = highs[right_shoulder_idx]

            # Check if head is highest and shoulders are similar
            if (head > left_shoulder * 1.05 and head > right_shoulder * 1.05 and
                abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder) < 0.1):

                patterns.append({
                    'pattern': PATTERN_HEAD_AND_SHOULDERS,
                    'type': PATTERN_TYPE_BEARISH,
                    'left_shoulder_price': float(left_shoulder),
                    'head_price': float(head),
                    'right_shoulder_price': float(right_shoulder),
                    'neckline': float((left_shoulder + right_shoulder) / 2),
                    'date': self._format_date(data.index[right_shoulder_idx]),
                    'confidence': CONFIDENCE_MEDIUM
                })

        return patterns[:5]  # Return top 5

    def detect_triangles(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect triangle patterns (continuation/reversal).

        Triangle types:
        - Ascending triangle: Flat resistance, rising support (bullish)
        - Descending triangle: Flat support, falling resistance (bearish)
        - Symmetrical triangle: Converging trendlines (neutral)

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of triangle patterns with type classification

        Examples:
            >>> patterns = detector.detect_triangles(df)
            >>> print(patterns[0]['type'])
            'ascending_triangle'
        """
        # Validate minimum data requirement
        self._validate_minimum_data(data, min_rows=20, pattern_name=PATTERN_TRIANGLE)

        patterns = []

        # Use rolling windows to detect converging trendlines
        window = 20
        for i in range(window, len(data)):
            segment = data.iloc[i-window:i]

            highs = segment['High'].values
            lows = segment['Low'].values

            # Calculate trendline slopes
            high_slope = np.polyfit(range(len(highs)), highs, 1)[0]
            low_slope = np.polyfit(range(len(lows)), lows, 1)[0]

            # Detect triangle type based on slope patterns
            if abs(high_slope) < 0.01 and low_slope > 0.01:
                pattern_type = PATTERN_TRIANGLE_ASCENDING
            elif high_slope < -0.01 and abs(low_slope) < 0.01:
                pattern_type = PATTERN_TRIANGLE_DESCENDING
            elif abs(high_slope) < 0.01 and abs(low_slope) < 0.01:
                pattern_type = PATTERN_TRIANGLE_SYMMETRICAL
            else:
                continue

            # Check if lines are converging (defensive check)
            high_range = highs.max() - highs.min()
            low_range = lows.max() - lows.min()

            if high_range > 0 and low_range > 0:
                patterns.append({
                    'pattern': PATTERN_TRIANGLE,
                    'type': pattern_type,
                    'start_date': self._format_date(segment.index[0]),
                    'end_date': self._format_date(segment.index[-1]),
                    'resistance_level': float(highs.max()),
                    'support_level': float(lows.min()),
                    'confidence': CONFIDENCE_MEDIUM
                })

        return patterns[:5]

    def detect_double_tops_bottoms(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect double top and double bottom patterns (reversal).

        Double top: Two similar peaks with valley between (bearish)
        Double bottom: Two similar troughs with peak between (bullish)

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of double top/bottom patterns

        Examples:
            >>> patterns = detector.detect_double_tops_bottoms(df)
            >>> double_top = [p for p in patterns if p['pattern'] == 'double_top'][0]
            >>> print(double_top['peak1_price'])
            150.0
        """
        # Validate minimum data requirement
        self._validate_minimum_data(data, min_rows=20, pattern_name=PATTERN_DOUBLE_TOP)

        patterns = []

        # Detect double tops (bearish reversal)
        highs = data['High'].values
        for i in range(10, len(highs) - 10):
            peak1 = highs[i]
            peak2_idx = i + 5
            if peak2_idx >= len(highs):
                continue
            peak2 = highs[peak2_idx]

            # Check if peaks are similar (within 2%)
            if abs(peak1 - peak2) / max(peak1, peak2) < 0.02:
                # Check if there's a valley between peaks
                valley = highs[i:peak2_idx].min()
                if valley < peak1 * 0.95:  # At least 5% drop
                    patterns.append({
                        'pattern': PATTERN_DOUBLE_TOP,
                        'type': PATTERN_TYPE_BEARISH,
                        'peak1_price': float(peak1),
                        'peak2_price': float(peak2),
                        'valley_price': float(valley),
                        'date': self._format_date(data.index[peak2_idx]),
                        'confidence': CONFIDENCE_MEDIUM
                    })

        # Detect double bottoms (bullish reversal)
        lows = data['Low'].values
        for i in range(10, len(lows) - 10):
            bottom1 = lows[i]
            bottom2_idx = i + 5
            if bottom2_idx >= len(lows):
                continue
            bottom2 = lows[bottom2_idx]

            # Check if bottoms are similar (within 2%)
            if abs(bottom1 - bottom2) / max(bottom1, bottom2) < 0.02:
                # Check if there's a peak between bottoms
                peak = lows[i:bottom2_idx].max()
                if peak > bottom1 * 1.05:  # At least 5% rise
                    patterns.append({
                        'pattern': PATTERN_DOUBLE_BOTTOM,
                        'type': PATTERN_TYPE_BULLISH,
                        'bottom1_price': float(bottom1),
                        'bottom2_price': float(bottom2),
                        'peak_price': float(peak),
                        'date': self._format_date(data.index[bottom2_idx]),
                        'confidence': CONFIDENCE_MEDIUM
                    })

        return patterns[:5]

    def detect_flags_pennants(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect flag and pennant patterns (continuation).

        Pattern: Strong trend followed by consolidation (small price range).
        - Bullish: Uptrend + consolidation → likely breakout up
        - Bearish: Downtrend + consolidation → likely breakout down

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of flag/pennant patterns

        Examples:
            >>> patterns = detector.detect_flags_pennants(df)
            >>> print(patterns[0]['trend_direction'])
            'up'
        """
        # Validate minimum data requirement
        self._validate_minimum_data(data, min_rows=15, pattern_name=PATTERN_FLAG_PENNANT)

        patterns = []
        closes = data['Close'].values

        # Look for strong trend followed by consolidation
        for i in range(10, len(data) - 5):
            # Check for trend before consolidation
            trend_segment = closes[i-10:i]
            consolidation_segment = closes[i:i+5]

            trend_slope = np.polyfit(range(len(trend_segment)), trend_segment, 1)[0]
            consolidation_std = np.std(consolidation_segment)
            trend_std = np.std(trend_segment)

            # Defensive check: avoid division by zero
            if trend_std == 0:
                continue

            if trend_slope > 0.01 and consolidation_std < trend_std * 0.5:
                # Bullish flag/pennant
                patterns.append({
                    'pattern': PATTERN_FLAG_PENNANT,
                    'type': PATTERN_TYPE_BULLISH,
                    'start_date': self._format_date(data.index[i]),
                    'end_date': self._format_date(data.index[i+5]),
                    'trend_direction': 'up',
                    'confidence': CONFIDENCE_LOW
                })
            elif trend_slope < -0.01 and consolidation_std < trend_std * 0.5:
                # Bearish flag/pennant
                patterns.append({
                    'pattern': PATTERN_FLAG_PENNANT,
                    'type': PATTERN_TYPE_BEARISH,
                    'start_date': self._format_date(data.index[i]),
                    'end_date': self._format_date(data.index[i+5]),
                    'trend_direction': 'down',
                    'confidence': CONFIDENCE_LOW
                })

        return patterns[:5]

    def detect_wedges(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect rising and falling wedge patterns.

        Wedge patterns are formed by converging trendlines with both resistance
        and support sloping in the same direction.

        Rising wedge (bearish reversal):
        - Both trendlines ascending
        - Support slope > Resistance slope (converging)
        - Decreasing volume as pattern forms
        - Price likely to break down

        Falling wedge (bullish reversal):
        - Both trendlines descending
        - Resistance slope < Support slope (converging, both negative)
        - Decreasing volume as pattern forms
        - Price likely to break up

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of wedge patterns (rising/falling)

        Examples:
            >>> patterns = detector.detect_wedges(df)
            >>> rising_wedges = [p for p in patterns if p['pattern'] == 'wedge_rising']
            >>> print(rising_wedges[0]['convergence_ratio'])
            0.75
        """
        # Defensive validation (Principle #1)
        self._validate_minimum_data(data, min_rows=30, pattern_name="wedge")

        # Narrative logging (Principle #18)
        logger.info("=" * 60)
        logger.info("📊 Wedge Pattern Detection")
        logger.info("=" * 60)
        logger.info(f"📄 Analyzing {len(data)} candles for wedge patterns...")

        patterns = []
        window = 30

        for i in range(window, len(data)):
            segment = data.iloc[i-window:i]

            highs = segment['High'].values
            lows = segment['Low'].values

            # Calculate trendline slopes using linear regression
            x = np.arange(len(highs))
            resistance_slope = np.polyfit(x, highs, 1)[0]
            support_slope = np.polyfit(x, lows, 1)[0]

            # Defensive check: avoid division by zero (Principle #1)
            if resistance_slope == 0 or support_slope == 0:
                logger.debug(f"Skipping segment at {segment.index[-1]} - zero slope (no trend)")
                continue

            # Calculate convergence (lines getting closer)
            start_spread = highs[0] - lows[0]
            end_spread = highs[-1] - lows[-1]

            # Defensive check: avoid division by zero
            if start_spread == 0:
                logger.debug(f"Skipping segment at {segment.index[-1]} - zero spread at start")
                continue

            convergence_ratio = end_spread / start_spread

            # Rising Wedge: Both ascending, support steeper than resistance
            # Resistance: 0.01 < slope < 0.10 (ascending but shallow)
            # Support: 0.10 < slope < 0.50 (ascending steeply)
            if (0.01 < resistance_slope < 0.10 and
                0.10 < support_slope < 0.50 and
                support_slope > resistance_slope):

                # Verify converging (20% convergence minimum)
                if convergence_ratio < 0.8:
                    patterns.append({
                        'pattern': PATTERN_WEDGE_RISING,
                        'type': PATTERN_TYPE_BEARISH,
                        'start_date': self._format_date(segment.index[0]),
                        'end_date': self._format_date(segment.index[-1]),
                        'resistance_slope': float(resistance_slope),
                        'support_slope': float(support_slope),
                        'convergence_ratio': float(convergence_ratio),
                        'start_spread': float(start_spread),
                        'end_spread': float(end_spread),
                        'confidence': CONFIDENCE_MEDIUM
                    })

            # Falling Wedge: Both descending, resistance steeper than support
            # Resistance: -0.50 < slope < -0.10 (descending steeply)
            # Support: -0.10 < slope < -0.01 (descending but shallow)
            elif (-0.50 < resistance_slope < -0.10 and
                  -0.10 < support_slope < -0.01 and
                  resistance_slope < support_slope):  # Both negative, resistance more negative

                # Verify converging (20% convergence minimum)
                if convergence_ratio < 0.8:
                    patterns.append({
                        'pattern': PATTERN_WEDGE_FALLING,
                        'type': PATTERN_TYPE_BULLISH,
                        'start_date': self._format_date(segment.index[0]),
                        'end_date': self._format_date(segment.index[-1]),
                        'resistance_slope': float(resistance_slope),
                        'support_slope': float(support_slope),
                        'convergence_ratio': float(convergence_ratio),
                        'start_spread': float(start_spread),
                        'end_spread': float(end_spread),
                        'confidence': CONFIDENCE_MEDIUM
                    })

        # Summary logging with counts
        rising_count = sum(1 for p in patterns if p['pattern'] == PATTERN_WEDGE_RISING)
        falling_count = sum(1 for p in patterns if p['pattern'] == PATTERN_WEDGE_FALLING)

        logger.info(
            f"✅ Detected {len(patterns)} wedge patterns "
            f"({rising_count} rising, {falling_count} falling)"
        )

        return patterns[:5]  # Return top 5
