# -*- coding: utf-8 -*-
"""
Custom Pattern Detector Adapter

Adapter wrapping the internal ChartPatternDetector to conform to
PatternDetectorInterface.

This provides a fallback when external libraries (stock-pattern) are unavailable,
ensuring pattern detection works in all environments (including Lambda).

Usage:
    adapter = CustomPatternAdapter()
    result = adapter.detect('head_shoulders', ticker, df, pivots, config)
"""

import logging
from typing import Dict, List, Optional, Any
import pandas as pd

from .registry import PatternDetectorInterface
from .chart_patterns import ChartPatternDetector
from .candlestick_patterns import CandlestickPatternDetector
from ..pattern_types import (
    PATTERN_HEAD_AND_SHOULDERS,
    PATTERN_INVERSE_HEAD_AND_SHOULDERS,
    PATTERN_DOUBLE_TOP,
    PATTERN_DOUBLE_BOTTOM,
    PATTERN_TRIANGLE,
    PATTERN_FLAG_PENNANT,
    PATTERN_WEDGE_RISING,
    PATTERN_WEDGE_FALLING,
)

logger = logging.getLogger(__name__)


class CustomPatternAdapter(PatternDetectorInterface):
    """
    Adapter for internal custom pattern detectors.

    Wraps ChartPatternDetector and CandlestickPatternDetector to conform to
    PatternDetectorInterface, enabling registry-based selection.

    Always available (no external dependencies), serves as fallback.

    Supported patterns:
    - head_shoulders, reverse_head_shoulders
    - double_bottom, double_top
    - triangle
    - flag_pennant
    - wedge_rising, wedge_falling
    """

    # Map pattern types to detector methods
    PATTERN_METHODS: Dict[str, str] = {
        'head_shoulders': 'detect_head_and_shoulders',
        'reverse_head_shoulders': 'detect_head_and_shoulders',  # Same method, different filter
        'double_bottom': 'detect_double_tops_bottoms',
        'double_top': 'detect_double_tops_bottoms',
        'triangle': 'detect_triangles',
        'flag_pennant': 'detect_flags_pennants',
        'bullish_flag': 'detect_flags_pennants',
        'bearish_flag': 'detect_flags_pennants',
        'wedge_rising': 'detect_wedges',
        'wedge_falling': 'detect_wedges',
        'bullish_vcp': 'detect_wedges',  # VCP is similar to wedge
        'bearish_vcp': 'detect_wedges',
    }

    # Map stock-pattern types to internal pattern type constants
    PATTERN_TYPE_MAP: Dict[str, str] = {
        'head_shoulders': PATTERN_HEAD_AND_SHOULDERS,
        'reverse_head_shoulders': PATTERN_INVERSE_HEAD_AND_SHOULDERS,
        'double_bottom': PATTERN_DOUBLE_BOTTOM,
        'double_top': PATTERN_DOUBLE_TOP,
        'triangle': PATTERN_TRIANGLE,
        'flag_pennant': PATTERN_FLAG_PENNANT,
        'bullish_flag': PATTERN_FLAG_PENNANT,
        'bearish_flag': PATTERN_FLAG_PENNANT,
        'wedge_rising': PATTERN_WEDGE_RISING,
        'wedge_falling': PATTERN_WEDGE_FALLING,
        'bullish_vcp': PATTERN_WEDGE_RISING,
        'bearish_vcp': PATTERN_WEDGE_FALLING,
    }

    def __init__(self):
        self._chart_detector = ChartPatternDetector()
        self._candlestick_detector = CandlestickPatternDetector()

    @property
    def name(self) -> str:
        return 'custom'

    @property
    def supported_patterns(self) -> List[str]:
        return list(self.PATTERN_METHODS.keys())

    def is_available(self) -> bool:
        """Custom detector is always available (no external dependencies)."""
        return True

    def detect(
        self,
        pattern_type: str,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect pattern using custom internal detector.

        Args:
            pattern_type: Type of pattern to detect
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame (not used by custom detector)
            config: Detection configuration (not used by custom detector)

        Returns:
            Pattern data dict if detected, None otherwise
        """
        if pattern_type not in self.PATTERN_METHODS:
            logger.warning(f"Pattern type '{pattern_type}' not supported by custom adapter")
            return None

        method_name = self.PATTERN_METHODS[pattern_type]
        detect_method = getattr(self._chart_detector, method_name, None)

        if detect_method is None:
            logger.error(f"Method '{method_name}' not found in ChartPatternDetector")
            return None

        try:
            # Custom detector works on DataFrame directly
            results = detect_method(df)

            if not results:
                return None

            # Filter results to match requested pattern type
            target_pattern = self.PATTERN_TYPE_MAP.get(pattern_type, pattern_type)
            matching = [r for r in results if r.get('pattern') == target_pattern]

            if not matching:
                # For some patterns, we need to filter by type (bullish/bearish)
                if pattern_type in ('head_shoulders', 'double_top', 'bearish_flag', 'bearish_vcp'):
                    matching = [r for r in results if r.get('type') == 'bearish']
                elif pattern_type in ('reverse_head_shoulders', 'double_bottom', 'bullish_flag', 'bullish_vcp'):
                    matching = [r for r in results if r.get('type') == 'bullish']
                else:
                    matching = results

            if not matching:
                return None

            # Return first matching pattern
            result = matching[0]

            # Normalize to standard format
            return self._normalize_result(pattern_type, result)

        except Exception as e:
            logger.debug(f"Custom detection failed for {pattern_type}: {e}")
            return None

    def _normalize_result(self, pattern_type: str, result: Dict) -> Dict[str, Any]:
        """
        Normalize custom detector result to standard format.

        Args:
            pattern_type: Requested pattern type
            result: Raw detector result

        Returns:
            Normalized pattern dict
        """
        return {
            'type': pattern_type,
            'pattern': result.get('pattern', pattern_type.upper()),
            'points': self._extract_points(result),
            'start': result.get('start_date') or result.get('date'),
            'end': result.get('end_date') or result.get('date'),
            'confidence': result.get('confidence', 'medium'),
            'source': 'custom_detector',
            # Preserve additional fields
            'sentiment': result.get('type'),  # bullish/bearish
            **{k: v for k, v in result.items() if k not in (
                'pattern', 'type', 'date', 'start_date', 'end_date', 'confidence'
            )}
        }

    def _extract_points(self, result: Dict) -> Dict[str, Any]:
        """Extract pattern points from result.

        Coordinate points for visualization are expected in format:
        { 'A': (timestamp, price), 'B': (timestamp, price), ... }

        If 'points' key exists with coordinate data, use it directly.
        Otherwise, fall back to extracting metadata fields (legacy).
        """
        # New format: coordinate points for line drawing
        if 'points' in result and isinstance(result['points'], dict):
            points = result['points']
            # Validate at least one point has correct tuple format
            for key, value in points.items():
                if isinstance(value, (tuple, list)) and len(value) == 2:
                    return points  # Valid coordinate points, use directly

        # Legacy format: extract metadata fields (won't render lines, but preserves data)
        points = {}
        price_fields = [
            'left_shoulder_price', 'head_price', 'right_shoulder_price', 'neckline',
            'peak1_price', 'peak2_price', 'valley_price',
            'bottom1_price', 'bottom2_price', 'peak_price',
            'resistance_level', 'support_level',
            'resistance_slope', 'support_slope', 'convergence_ratio',
        ]

        for field in price_fields:
            if field in result:
                points[field] = result[field]

        return points

    def detect_all(
        self,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any],
        pattern_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect all supported patterns.

        Args:
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame (unused)
            config: Detection configuration (unused)
            pattern_types: Specific patterns to detect (None = all)

        Returns:
            List of detected pattern dicts
        """
        types_to_detect = pattern_types or [
            'head_shoulders', 'double_bottom', 'double_top',
            'triangle', 'flag_pennant', 'wedge_rising', 'wedge_falling'
        ]

        patterns = []
        seen_methods = set()

        for pattern_type in types_to_detect:
            if pattern_type not in self.PATTERN_METHODS:
                continue

            # Avoid calling same method multiple times
            method_name = self.PATTERN_METHODS[pattern_type]
            if method_name in seen_methods:
                continue
            seen_methods.add(method_name)

            result = self.detect(pattern_type, ticker, df, pivots, config)
            if result:
                patterns.append(result)
                logger.info(f"  {pattern_type.replace('_', ' ').title()}")

        return patterns


# Convenience function
def get_custom_adapter() -> CustomPatternAdapter:
    """Get CustomPatternAdapter instance."""
    return CustomPatternAdapter()
