# -*- coding: utf-8 -*-
"""
Pattern Detectors Module - Core Analysis

Reusable pattern detection for chart patterns, candlestick patterns,
and support/resistance levels.

Following architecture principle: Core analysis (reusable) vs Protocol adapter (MCP/API-specific).

Usage:
    from src.analysis.pattern_detectors import (
        ChartPatternDetector,
        CandlestickPatternDetector,
        SupportResistanceDetector
    )

    # Detect chart patterns
    chart_detector = ChartPatternDetector()
    chart_patterns = chart_detector.detect(ohlc_df)

    # Detect candlestick patterns
    candle_detector = CandlestickPatternDetector()
    candle_patterns = candle_detector.detect(ohlc_df)

    # Calculate support/resistance
    sr_detector = SupportResistanceDetector()
    levels = sr_detector.calculate_levels(ohlc_df, num_levels=5)
"""

from .base_detector import BasePatternDetector
from .chart_patterns import ChartPatternDetector
from .candlestick_patterns import CandlestickPatternDetector
from .support_resistance import SupportResistanceDetector

__all__ = [
    'BasePatternDetector',
    'ChartPatternDetector',
    'CandlestickPatternDetector',
    'SupportResistanceDetector',
]
