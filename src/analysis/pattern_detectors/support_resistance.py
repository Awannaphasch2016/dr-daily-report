# -*- coding: utf-8 -*-
"""
Support & Resistance Level Detector - Core Analysis Module

Calculates support and resistance levels from OHLC price data
following defensive programming patterns (Principle #1).

Support: Price level where buying interest strong enough to prevent further decline
Resistance: Price level where selling pressure strong enough to prevent further rise

Levels calculated using local extrema (rolling window peaks and troughs).

All level types use constants from pattern_types.py (Principle #14).
"""

from typing import List, Dict, Any
import pandas as pd
import logging

from .base_detector import BasePatternDetector
from ..pattern_types import (
    LEVEL_SUPPORT,
    LEVEL_RESISTANCE,
    LEVEL_SUPPORT_RESISTANCE,
)

logger = logging.getLogger(__name__)


class SupportResistanceDetector(BasePatternDetector):
    """
    Detects support and resistance levels in OHLC price data.

    Levels identified by finding local extrema:
    - Support: Local minima (price bounces off level from below)
    - Resistance: Local maxima (price bounces off level from above)

    Usage:
        detector = SupportResistanceDetector()
        levels = detector.detect(ohlc_df, num_levels=5)

        print(f"Support: {levels['support']}")
        print(f"Resistance: {levels['resistance']}")
        print(f"Current price: {levels['current_price']}")
    """

    def __init__(self, window: int = 10):
        """
        Initialize support/resistance detector.

        Args:
            window: Rolling window size for finding local extrema (default: 10)
                   Larger window = fewer, stronger levels
                   Smaller window = more, weaker levels
        """
        super().__init__()
        self.window = window

    def detect(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect support and resistance levels in OHLC data.

        This method is required by BasePatternDetector but returns
        a different format than chart/candlestick patterns.

        For support/resistance, use calculate_levels() instead.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            Empty list (use calculate_levels() for actual detection)

        See Also:
            calculate_levels(): Main method for support/resistance detection
        """
        # Support/resistance uses different return format than patterns
        # Redirect to calculate_levels()
        logger.info("Called detect() on SupportResistanceDetector - use calculate_levels() instead")
        return []

    def calculate_levels(
        self,
        data: pd.DataFrame,
        num_levels: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate support and resistance levels.

        Finds local minima (support) and maxima (resistance) using rolling windows.

        Args:
            data: DataFrame with High and Low prices
            num_levels: Number of levels to return for each type (default: 5)

        Returns:
            Dictionary with:
                - support: List of support price levels (sorted ascending)
                - resistance: List of resistance price levels (sorted descending)
                - current_price: Current Close price

        Raises:
            ValueError: If data invalid (no columns, empty, all-NaN)

        Examples:
            >>> detector = SupportResistanceDetector()
            >>> levels = detector.calculate_levels(df, num_levels=3)
            >>> print(levels)
            {
                'support': [145.0, 147.5, 149.0],
                'resistance': [155.0, 153.0, 151.5],
                'current_price': 150.0
            }
        """
        # Defensive validation (Principle #1)
        self._validate_ohlc_data(data)
        self._validate_minimum_data(data, min_rows=20, pattern_name="support_resistance")

        highs = data['High'].values
        lows = data['Low'].values

        # Find local maxima (resistance levels)
        resistance_levels = []
        for i in range(self.window, len(highs) - self.window):
            # Check if this is a local maximum
            window_highs = highs[i-self.window:i+self.window+1]
            if highs[i] == max(window_highs):
                resistance_levels.append(float(highs[i]))

        # Find local minima (support levels)
        support_levels = []
        for i in range(self.window, len(lows) - self.window):
            # Check if this is a local minimum
            window_lows = lows[i-self.window:i+self.window+1]
            if lows[i] == min(window_lows):
                support_levels.append(float(lows[i]))

        # Remove duplicates and sort
        # Resistance: highest first (descending)
        # Support: lowest first (ascending)
        resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
        support_levels = sorted(set(support_levels))[:num_levels]

        current_price = float(data['Close'].iloc[-1])

        logger.info(
            f"✅ Found {len(support_levels)} support levels "
            f"and {len(resistance_levels)} resistance levels "
            f"(current price: {current_price:.2f})"
        )

        return {
            'support': support_levels,
            'resistance': resistance_levels,
            'current_price': current_price
        }

    def calculate_levels_with_strength(
        self,
        data: pd.DataFrame,
        num_levels: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate support/resistance levels with strength indicators.

        Strength calculated by counting how many times price touched level.

        Args:
            data: DataFrame with OHLC columns
            num_levels: Number of levels to return for each type

        Returns:
            Dictionary with:
                - support: List of dicts with {level, strength, touches}
                - resistance: List of dicts with {level, strength, touches}
                - current_price: Current Close price

        Examples:
            >>> levels = detector.calculate_levels_with_strength(df)
            >>> print(levels['support'][0])
            {
                'level': 145.0,
                'strength': 'strong',
                'touches': 5
            }
        """
        # Get basic levels first
        basic_levels = self.calculate_levels(data, num_levels=num_levels * 2)

        # Count touches for each level (within 1% tolerance)
        support_with_strength = self._calculate_strength(
            basic_levels['support'],
            data['Low'].values,
            tolerance=0.01
        )[:num_levels]

        resistance_with_strength = self._calculate_strength(
            basic_levels['resistance'],
            data['High'].values,
            tolerance=0.01
        )[:num_levels]

        return {
            'support': support_with_strength,
            'resistance': resistance_with_strength,
            'current_price': basic_levels['current_price']
        }

    def _calculate_strength(
        self,
        levels: List[float],
        prices: List[float],
        tolerance: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Calculate strength of levels based on touch count.

        Args:
            levels: Price levels to analyze
            prices: Price series (High or Low)
            tolerance: % tolerance for considering a touch (default: 1%)

        Returns:
            List of dicts with {level, strength, touches}
        """
        levels_with_strength = []

        for level in levels:
            # Count how many times price touched this level
            touches = sum(
                1 for price in prices
                if abs(price - level) / level <= tolerance
            )

            # Classify strength
            if touches >= 5:
                strength = 'strong'
            elif touches >= 3:
                strength = 'medium'
            else:
                strength = 'weak'

            levels_with_strength.append({
                'level': level,
                'strength': strength,
                'touches': touches
            })

        # Sort by strength (strong first)
        strength_order = {'strong': 0, 'medium': 1, 'weak': 2}
        levels_with_strength.sort(key=lambda x: strength_order[x['strength']])

        return levels_with_strength
