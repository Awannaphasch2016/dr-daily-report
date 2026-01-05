# -*- coding: utf-8 -*-
"""
Candlestick Pattern Detector - Core Analysis Module

Implements candlestick pattern detection (single and multi-candle patterns)
following defensive programming patterns (Principle #1).

Candlestick patterns reveal market psychology through OHLC relationships:
- Doji: Indecision (small body, long shadows)
- Hammer: Bullish reversal (small body at top, long lower shadow)
- Shooting Star: Bearish reversal (small body at bottom, long upper shadow)
- Engulfing: Strong reversal signal (current candle engulfs previous)
- Three Line Strike: Continuation pattern (three consecutive candles)

All patterns use constants from pattern_types.py (Principle #14).
"""

from typing import List, Dict, Any
import pandas as pd
import logging

from .base_detector import BasePatternDetector
from ..pattern_types import (
    # Single-candle patterns
    PATTERN_DOJI,
    PATTERN_HAMMER,
    PATTERN_INVERTED_HAMMER,
    PATTERN_HANGING_MAN,
    PATTERN_SHOOTING_STAR,

    # Multi-candle patterns
    PATTERN_ENGULFING_BULLISH,
    PATTERN_ENGULFING_BEARISH,
    PATTERN_THREE_LINE_STRIKE,

    # Classification constants
    PATTERN_TYPE_BULLISH,
    PATTERN_TYPE_BEARISH,
    PATTERN_TYPE_NEUTRAL,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)

logger = logging.getLogger(__name__)


class CandlestickPatternDetector(BasePatternDetector):
    """
    Detects candlestick patterns in OHLC price data.

    Patterns detected:
    - Doji (neutral - indecision)
    - Hammer (bullish reversal)
    - Shooting Star (bearish reversal)
    - Engulfing (bullish/bearish reversal)
    - Three Line Strike (continuation)

    Usage:
        detector = CandlestickPatternDetector()
        patterns = detector.detect(ohlc_df)

        for pattern in patterns:
            print(f"{pattern['pattern']}: {pattern['type']} ({pattern['date']})")
    """

    def __init__(self):
        """Initialize candlestick pattern detector."""
        super().__init__()

    def detect(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect all candlestick patterns in OHLC data.

        Args:
            data: DataFrame with OHLC columns and DatetimeIndex

        Returns:
            List of detected patterns, each containing:
                - pattern: Pattern type constant (from pattern_types.py)
                - type: bullish/bearish/neutral
                - date: When pattern occurred
                - open/close: Candle OHLC values
                - confidence: high/medium/low

        Raises:
            ValueError: If data invalid (no columns, empty, all-NaN)

        Examples:
            >>> detector = CandlestickPatternDetector()
            >>> patterns = detector.detect(df)
            >>> doji_patterns = [p for p in patterns if p['pattern'] == 'doji']
            >>> print(len(doji_patterns))
            3
        """
        # Defensive validation (Principle #1)
        self._validate_ohlc_data(data)
        self._validate_minimum_data(data, min_rows=2, pattern_name="candlestick_patterns")

        patterns = []

        for i in range(1, len(data)):
            open_price = data.iloc[i]['Open']
            high = data.iloc[i]['High']
            low = data.iloc[i]['Low']
            close = data.iloc[i]['Close']

            body = abs(close - open_price)
            upper_shadow = high - max(open_price, close)
            lower_shadow = min(open_price, close) - low
            total_range = high - low

            # Defensive check: skip if no price movement
            if total_range == 0:
                logger.debug(f"Skipping candle at {data.index[i]} - no price movement (total_range=0)")
                continue

            # Single-candle patterns
            patterns.extend(self._detect_doji(i, data, body, total_range, open_price, close))
            patterns.extend(self._detect_hammer(i, data, body, total_range, lower_shadow, upper_shadow, open_price, close))
            patterns.extend(self._detect_shooting_star(i, data, body, total_range, upper_shadow, lower_shadow, open_price, close))

            # Multi-candle patterns (require previous candle)
            patterns.extend(self._detect_engulfing(i, data, open_price, close))

            # Three-candle patterns
            if i >= 3:
                patterns.extend(self._detect_three_line_strike(i, data))

        logger.info(f"✅ Detected {len(patterns)} candlestick patterns")
        return patterns[:10]  # Return top 10

    def _detect_doji(
        self,
        i: int,
        data: pd.DataFrame,
        body: float,
        total_range: float,
        open_price: float,
        close: float
    ) -> List[Dict[str, Any]]:
        """
        Detect Doji pattern (neutral - indecision).

        Doji: Very small body relative to range, long shadows.
        Signals indecision - neither bulls nor bears in control.

        Returns:
            List with single doji pattern if detected, empty list otherwise
        """
        # Doji: Very small body relative to range
        if body / total_range < 0.1:
            return [{
                'pattern': PATTERN_DOJI,
                'type': PATTERN_TYPE_NEUTRAL,
                'date': self._format_date(data.index[i]),
                'open': float(open_price),
                'close': float(close),
                'confidence': CONFIDENCE_MEDIUM
            }]
        return []

    def _detect_hammer(
        self,
        i: int,
        data: pd.DataFrame,
        body: float,
        total_range: float,
        lower_shadow: float,
        upper_shadow: float,
        open_price: float,
        close: float
    ) -> List[Dict[str, Any]]:
        """
        Detect Hammer pattern (bullish reversal).

        Hammer: Small body at top, long lower shadow (>2x body), minimal upper shadow.
        Signals buyers stepping in after sellers pushed price down.

        Returns:
            List with single hammer pattern if detected, empty list otherwise
        """
        # Hammer: Small body at top, long lower shadow
        if body / total_range < 0.3 and lower_shadow > body * 2 and upper_shadow < body * 0.5:
            return [{
                'pattern': PATTERN_HAMMER,
                'type': PATTERN_TYPE_BULLISH,
                'date': self._format_date(data.index[i]),
                'open': float(open_price),
                'close': float(close),
                'confidence': CONFIDENCE_MEDIUM
            }]
        return []

    def _detect_shooting_star(
        self,
        i: int,
        data: pd.DataFrame,
        body: float,
        total_range: float,
        upper_shadow: float,
        lower_shadow: float,
        open_price: float,
        close: float
    ) -> List[Dict[str, Any]]:
        """
        Detect Shooting Star pattern (bearish reversal).

        Shooting Star: Small body at bottom, long upper shadow (>2x body), minimal lower shadow.
        Signals sellers stepping in after buyers pushed price up.

        Returns:
            List with single shooting star pattern if detected, empty list otherwise
        """
        # Shooting Star: Small body at bottom, long upper shadow
        if body / total_range < 0.3 and upper_shadow > body * 2 and lower_shadow < body * 0.5:
            return [{
                'pattern': PATTERN_SHOOTING_STAR,
                'type': PATTERN_TYPE_BEARISH,
                'date': self._format_date(data.index[i]),
                'open': float(open_price),
                'close': float(close),
                'confidence': CONFIDENCE_MEDIUM
            }]
        return []

    def _detect_engulfing(
        self,
        i: int,
        data: pd.DataFrame,
        open_price: float,
        close: float
    ) -> List[Dict[str, Any]]:
        """
        Detect Engulfing patterns (bullish/bearish reversal).

        Bullish engulfing: Current green candle completely engulfs previous red candle.
        Bearish engulfing: Current red candle completely engulfs previous green candle.

        Strong reversal signal (high confidence).

        Returns:
            List with single engulfing pattern if detected, empty list otherwise
        """
        patterns = []

        prev_open = data.iloc[i-1]['Open']
        prev_close = data.iloc[i-1]['Close']

        # Bullish engulfing: current candle completely engulfs previous
        if (close > open_price and prev_close < prev_open and
            open_price < prev_close and close > prev_open):
            patterns.append({
                'pattern': PATTERN_ENGULFING_BULLISH,
                'type': PATTERN_TYPE_BULLISH,
                'date': self._format_date(data.index[i]),
                'open': float(open_price),
                'close': float(close),
                'confidence': CONFIDENCE_HIGH
            })

        # Bearish engulfing
        if (close < open_price and prev_close > prev_open and
            open_price > prev_close and close < prev_open):
            patterns.append({
                'pattern': PATTERN_ENGULFING_BEARISH,
                'type': PATTERN_TYPE_BEARISH,
                'date': self._format_date(data.index[i]),
                'open': float(open_price),
                'close': float(close),
                'confidence': CONFIDENCE_HIGH
            })

        return patterns

    def _detect_three_line_strike(self, i: int, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Three Line Strike pattern (continuation).

        Three consecutive candles in same direction signals trend continuation.
        - Bullish: Three consecutive up candles (close > open)
        - Bearish: Three consecutive down candles (close < open)

        Returns:
            List with single three line strike pattern if detected, empty list otherwise
        """
        patterns = []

        candles = data.iloc[i-2:i+1]
        if len(candles) == 3:
            # Bullish: three consecutive up candles
            if all(candles['Close'] > candles['Open']):
                patterns.append({
                    'pattern': PATTERN_THREE_LINE_STRIKE,
                    'type': PATTERN_TYPE_BULLISH,
                    'date': self._format_date(data.index[i]),
                    'confidence': CONFIDENCE_MEDIUM
                })
            # Bearish: three consecutive down candles
            elif all(candles['Close'] < candles['Open']):
                patterns.append({
                    'pattern': PATTERN_THREE_LINE_STRIKE,
                    'type': PATTERN_TYPE_BEARISH,
                    'date': self._format_date(data.index[i]),
                    'confidence': CONFIDENCE_MEDIUM
                })

        return patterns
