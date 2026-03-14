"""Backward-compatible adapter — drop-in replacement for the old stub.

This module exports SMAStrategyBacktester with the exact same interface
as src/utils/strategy.py so that agent.py, strategy_analyzer.py, and
workflow_nodes.py require only an import-path change.
"""

import logging
from typing import Optional

import pandas as pd

from src.backtesting.strategies.sma_crossover import SMACrossoverStrategy

logger = logging.getLogger(__name__)


class SMAStrategyBacktester:
    """Backward-compatible facade over SMACrossoverStrategy.

    Interface contract (must match old stub):
        __init__(fast_period=20, slow_period=50)
        detect_signals(hist_data) -> DataFrame | None
        backtest_buy_only(hist_data) -> dict | None
        backtest_sell_only(hist_data) -> dict | None
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._strategy = SMACrossoverStrategy(
            fast_period=fast_period,
            slow_period=slow_period,
        )

    def detect_signals(self, hist_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Detect buy/sell signals. Returns raw DataFrame (not SignalFrame).

        Returns DataFrame with columns: Close, SMA_Fast, SMA_Slow, Buy_Signal, Sell_Signal
        Returns None on failure.
        """
        try:
            signal_frame = self._strategy.detect_signals(hist_data)
            return signal_frame.df
        except Exception as e:
            logger.warning(f"detect_signals failed: {e}")
            return None

    def backtest_buy_only(self, hist_data: pd.DataFrame) -> Optional[dict]:
        """Run buy-only backtest. Returns plain dict or None on failure."""
        try:
            result = self._strategy.backtest(hist_data, direction="buy_only")
            return result.to_dict()
        except Exception as e:
            logger.warning(f"backtest_buy_only failed: {e}")
            return None

    def backtest_sell_only(self, hist_data: pd.DataFrame) -> Optional[dict]:
        """Run sell-only backtest. Returns plain dict or None on failure."""
        try:
            result = self._strategy.backtest(hist_data, direction="sell_only")
            return result.to_dict()
        except Exception as e:
            logger.warning(f"backtest_sell_only failed: {e}")
            return None
