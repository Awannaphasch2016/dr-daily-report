# -*- coding: utf-8 -*-
"""
Base Pattern Detector - Abstract Base Class

Implements defensive programming patterns (Principle #1):
- Input validation (fail fast on invalid data)
- Clear error messages (explain what's wrong and why)
- Type safety (enforce correct data structures)

All pattern detectors inherit from this base class to ensure
consistent validation and error handling.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BasePatternDetector(ABC):
    """
    Abstract base class for all pattern detectors.

    Enforces:
    - Defensive validation before analysis
    - Consistent error messages
    - Type-safe pattern detection

    Subclasses must implement:
    - detect(): Main pattern detection method
    """

    def __init__(self):
        """Initialize base pattern detector."""
        pass

    def _validate_ohlc_data(self, data: pd.DataFrame) -> None:
        """
        Validate OHLC DataFrame has required structure.

        Checks:
        1. DataFrame is not empty
        2. Has required OHLC columns (Open, High, Low, Close)
        3. Has DatetimeIndex (for date formatting)
        4. No all-NaN columns

        Args:
            data: DataFrame to validate

        Raises:
            ValueError: If data structure invalid
            TypeError: If data types invalid

        Examples:
            >>> detector._validate_ohlc_data(df)  # Passes
            >>> detector._validate_ohlc_data(empty_df)  # Raises ValueError
        """
        # Check data exists
        if data is None:
            raise ValueError(
                "Cannot detect patterns on None DataFrame.\n"
                "Provide valid OHLC data with columns: Open, High, Low, Close"
            )

        # Check not empty
        if len(data) == 0:
            raise ValueError(
                "Cannot detect patterns on empty DataFrame.\n"
                "Provide DataFrame with at least 1 row of OHLC data."
            )

        # Check required columns
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing = [col for col in required_cols if col not in data.columns]

        if missing:
            raise ValueError(
                f"Missing required OHLC columns: {missing}\n"
                f"Pattern detection requires columns: {required_cols}\n"
                f"Available columns: {list(data.columns)}"
            )

        # Check for all-NaN columns
        for col in required_cols:
            if data[col].isna().all():
                raise ValueError(
                    f"Column '{col}' contains only NaN values.\n"
                    f"Pattern detection requires valid price data."
                )

        # Check datetime index (needed for date formatting)
        if not isinstance(data.index, pd.DatetimeIndex):
            logger.warning(
                f"Expected DatetimeIndex for date formatting, got {type(data.index)}.\n"
                f"Pattern dates will use str(index) instead of strftime()."
            )

    def _validate_minimum_data(
        self,
        data: pd.DataFrame,
        min_rows: int,
        pattern_name: str
    ) -> None:
        """
        Validate DataFrame has minimum rows for pattern detection.

        Different patterns require different minimum data:
        - Simple patterns (doji, hammer): 1-2 rows
        - Medium patterns (triangles, double tops): 20-30 rows
        - Complex patterns (head & shoulders): 30-50 rows

        Args:
            data: DataFrame to validate
            min_rows: Minimum rows required
            pattern_name: Pattern being detected (for error message)

        Raises:
            ValueError: If insufficient data

        Examples:
            >>> detector._validate_minimum_data(df, 20, "head_and_shoulders")
            >>> # Raises if len(df) < 20
        """
        if len(data) < min_rows:
            raise ValueError(
                f"Insufficient data for {pattern_name} detection: "
                f"{len(data)} rows provided, {min_rows} rows required.\n"
                f"Pattern detection needs more historical data."
            )

    def _format_date(self, timestamp) -> str:
        """
        Format timestamp to YYYY-MM-DD string.

        Handles both DatetimeIndex and other index types gracefully.

        Args:
            timestamp: pandas Timestamp or any index value

        Returns:
            Formatted date string (YYYY-MM-DD format)

        Examples:
            >>> detector._format_date(pd.Timestamp('2024-01-15'))
            '2024-01-15'
            >>> detector._format_date("2024-01-15")  # Fallback
            '2024-01-15'
        """
        if hasattr(timestamp, 'strftime'):
            return timestamp.strftime('%Y-%m-%d')
        else:
            return str(timestamp)

    @abstractmethod
    def detect(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect patterns in OHLC data.

        This is the main entry point for pattern detection.
        Subclasses must implement this method.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected patterns, each as dict with:
                - pattern: Pattern type (from pattern_types.py)
                - type: bullish/bearish/neutral
                - date/start_date/end_date: When pattern occurred
                - confidence: high/medium/low
                - Additional pattern-specific fields

        Raises:
            NotImplementedError: If subclass doesn't implement

        Examples:
            >>> patterns = detector.detect(df)
            >>> print(patterns[0])
            {
                'pattern': 'head_and_shoulders',
                'type': 'bearish',
                'head_date': '2024-01-15',
                'confidence': 'high'
            }
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement detect() method"
        )
