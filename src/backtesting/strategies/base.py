"""Abstract base class for backtesting strategies"""

from abc import ABC, abstractmethod

import pandas as pd

from src.backtesting.types import BacktestResult, SignalFrame


class BaseStrategy(ABC):
    """All strategies must implement signal detection and backtesting."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name"""

    @abstractmethod
    def detect_signals(self, hist_data: pd.DataFrame) -> SignalFrame:
        """Detect entry/exit signals from historical OHLCV data.

        Args:
            hist_data: DataFrame with at least a 'Close' column and DatetimeIndex

        Returns:
            SignalFrame with Buy_Signal and Sell_Signal boolean columns
        """

    @abstractmethod
    def backtest(self, hist_data: pd.DataFrame, direction: str) -> BacktestResult:
        """Run backtest for a given direction.

        Args:
            hist_data: DataFrame with OHLCV data
            direction: 'buy_only' or 'sell_only'

        Returns:
            BacktestResult with standardized metrics
        """
