# -*- coding: utf-8 -*-
"""
Stock Pattern Library Adapter

Adapter wrapping the external stock-pattern library
(https://github.com/BennyThadikaran/stock-pattern) to conform to
PatternDetectorInterface.

This adapter makes the third-party library pluggable via the registry pattern,
allowing runtime selection between this and custom implementations.

Usage:
    adapter = StockPatternAdapter()
    if adapter.is_available():
        result = adapter.detect('bullish_flag', ticker, df, pivots, config)
"""

import sys
import logging
from typing import Dict, List, Optional, Any, Callable
import pandas as pd

from .registry import PatternDetectorInterface

logger = logging.getLogger(__name__)

# Try to load stock-pattern library (optional dependency)
stock_pattern_lib = None
STOCK_PATTERN_AVAILABLE = False

try:
    sys.path.insert(0, '/tmp/stock-pattern/src')
    import utils as stock_pattern_lib
    STOCK_PATTERN_AVAILABLE = True
    logger.info("stock-pattern library loaded successfully")
except ImportError:
    logger.debug("stock-pattern library not available (optional for Lambda)")


class StockPatternAdapter(PatternDetectorInterface):
    """
    Adapter for the stock-pattern library.

    Wraps external library functions to conform to PatternDetectorInterface,
    enabling registry-based selection and graceful fallback.

    Supported patterns:
    - bullish_flag, bearish_flag
    - triangle
    - double_bottom, double_top
    - head_shoulders, reverse_head_shoulders
    - bullish_vcp, bearish_vcp (Volatility Contraction Pattern)
    """

    # Map pattern types to stock-pattern library functions
    PATTERN_FUNCTIONS: Dict[str, str] = {
        'bullish_flag': 'find_bullish_flag',
        'bearish_flag': 'find_bearish_flag',
        'triangle': 'find_triangles',
        'double_bottom': 'find_double_bottom',
        'double_top': 'find_double_top',
        'head_shoulders': 'find_hns',
        'reverse_head_shoulders': 'find_reverse_hns',
        'bullish_vcp': 'find_bullish_vcp',
        'bearish_vcp': 'find_bearish_vcp',
    }

    @property
    def name(self) -> str:
        return 'stock_pattern'

    @property
    def supported_patterns(self) -> List[str]:
        return list(self.PATTERN_FUNCTIONS.keys())

    def is_available(self) -> bool:
        """Check if stock-pattern library is available."""
        return STOCK_PATTERN_AVAILABLE

    def detect(
        self,
        pattern_type: str,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect pattern using stock-pattern library.

        Args:
            pattern_type: Type of pattern to detect
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            config: Detection configuration

        Returns:
            Pattern data dict if detected, None otherwise

        Raises:
            RuntimeError: If library not available
            ValueError: If pattern type not supported
        """
        if not self.is_available():
            raise RuntimeError(
                "stock-pattern library not available. "
                "Install from: https://github.com/BennyThadikaran/stock-pattern"
            )

        if pattern_type not in self.PATTERN_FUNCTIONS:
            raise ValueError(
                f"Pattern type '{pattern_type}' not supported by stock-pattern adapter. "
                f"Supported: {self.supported_patterns}"
            )

        func_name = self.PATTERN_FUNCTIONS[pattern_type]
        detect_func = getattr(stock_pattern_lib, func_name, None)

        if detect_func is None:
            logger.error(f"Function '{func_name}' not found in stock-pattern library")
            return None

        try:
            result = detect_func(ticker, df, pivots, config)

            if not result:
                return None

            # Serialize result (convert Timestamps to strings)
            serialized = stock_pattern_lib.make_serializable(result)

            return {
                'type': pattern_type,
                'pattern': serialized.get('pattern', pattern_type.upper()),
                'points': serialized.get('points', {}),
                'start': serialized.get('start'),
                'end': serialized.get('end'),
                'confidence': self._assess_confidence(serialized),
                'source': 'stock_pattern_lib',
            }

        except Exception as e:
            logger.debug(f"stock-pattern detection failed for {pattern_type}: {e}")
            return None

    def _assess_confidence(self, pattern_data: Dict) -> str:
        """
        Assess pattern confidence.

        The stock-pattern library already applies strict validation,
        so any detected pattern is at least "medium" confidence.
        """
        # TODO: Add additional scoring logic based on pattern characteristics
        return 'medium'

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
            pivots: Pivot points DataFrame
            config: Detection configuration
            pattern_types: Specific patterns to detect (None = all)

        Returns:
            List of detected pattern dicts
        """
        if not self.is_available():
            logger.warning("stock-pattern library not available, returning empty results")
            return []

        types_to_detect = pattern_types or self.supported_patterns
        patterns = []

        for pattern_type in types_to_detect:
            if pattern_type not in self.PATTERN_FUNCTIONS:
                continue

            result = self.detect(pattern_type, ticker, df, pivots, config)
            if result:
                patterns.append(result)
                logger.info(f"  {pattern_type.replace('_', ' ').title()}")

        return patterns


# Convenience function for backward compatibility
def get_stock_pattern_adapter() -> Optional[StockPatternAdapter]:
    """Get StockPatternAdapter if available, None otherwise."""
    adapter = StockPatternAdapter()
    return adapter if adapter.is_available() else None
