# -*- coding: utf-8 -*-
"""
Pattern Detectors Module - Core Analysis

Reusable pattern detection for chart patterns, candlestick patterns,
and support/resistance levels.

Following architecture principle: Core analysis (reusable) vs Protocol adapter (MCP/API-specific).

Registry Pattern:
    The registry allows multiple implementations per pattern type, enabling
    runtime selection between external libraries (stock-pattern) and custom
    implementations.

Usage:
    # Basic usage (individual detectors)
    from src.analysis.pattern_detectors import (
        ChartPatternDetector,
        CandlestickPatternDetector,
        SupportResistanceDetector
    )

    chart_detector = ChartPatternDetector()
    chart_patterns = chart_detector.detect(ohlc_df)

    # Registry-based usage (pluggable implementations)
    from src.analysis.pattern_detectors import (
        get_pattern_registry,
        StockPatternAdapter,
        CustomPatternAdapter,
    )

    registry = get_pattern_registry()
    registry.register_detector(StockPatternAdapter(), priority=10)
    registry.register_detector(CustomPatternAdapter(), priority=5)

    # Detect with automatic fallback
    result = registry.detect_with_fallback('bullish_flag', ticker, df, pivots, config)
"""

from .base_detector import BasePatternDetector
from .chart_patterns import ChartPatternDetector
from .candlestick_patterns import CandlestickPatternDetector
from .support_resistance import SupportResistanceDetector

# Registry pattern exports
from .registry import (
    PatternDetectorInterface,
    PatternDetectorRegistry,
    get_pattern_registry,
)
from .stock_pattern_adapter import StockPatternAdapter, get_stock_pattern_adapter
from .custom_adapter import CustomPatternAdapter, get_custom_adapter

__all__ = [
    # Base classes
    'BasePatternDetector',
    'PatternDetectorInterface',

    # Detectors
    'ChartPatternDetector',
    'CandlestickPatternDetector',
    'SupportResistanceDetector',

    # Registry
    'PatternDetectorRegistry',
    'get_pattern_registry',

    # Adapters
    'StockPatternAdapter',
    'CustomPatternAdapter',
    'get_stock_pattern_adapter',
    'get_custom_adapter',
]
