"""SMA Crossover strategy powered by VectorBT Pro"""

import logging

import pandas as pd

from src.backtesting.strategies.base import BaseStrategy
from src.backtesting.types import BacktestResult, SignalFrame
from src.backtesting.metrics import extract_metrics

logger = logging.getLogger(__name__)

_vbt = None


def _lazy_import_vbt():
    """Import vectorbtpro on first use to avoid cold-start penalty."""
    global _vbt
    if _vbt is None:
        import vectorbtpro as vbt
        _vbt = vbt
    return _vbt


class SMACrossoverStrategy(BaseStrategy):
    """SMA crossover: buy when fast SMA crosses above slow SMA, sell on cross below."""

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def name(self) -> str:
        return f"SMA({self.fast_period}/{self.slow_period})"

    def detect_signals(self, hist_data: pd.DataFrame) -> SignalFrame:
        """Detect SMA crossover signals.

        Returns SignalFrame with columns:
            Close, SMA_Fast, SMA_Slow, Buy_Signal, Sell_Signal
        """
        vbt = _lazy_import_vbt()
        close = hist_data['Close']

        fast_ma = vbt.MA.run(close, window=self.fast_period).ma
        slow_ma = vbt.MA.run(close, window=self.slow_period).ma

        # Crossover: fast crosses above slow → buy; fast crosses below slow → sell
        buy_signal = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
        sell_signal = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))

        df = pd.DataFrame({
            'Close': close,
            'SMA_Fast': fast_ma,
            'SMA_Slow': slow_ma,
            'Buy_Signal': buy_signal.fillna(False),
            'Sell_Signal': sell_signal.fillna(False),
        }, index=hist_data.index)

        return SignalFrame(
            df=df,
            strategy_name=self.name,
            indicator_columns=['SMA_Fast', 'SMA_Slow'],
        )

    def backtest(self, hist_data: pd.DataFrame, direction: str) -> BacktestResult:
        """Run SMA crossover backtest.

        Args:
            direction: 'buy_only' (entries on buy signals only) or
                       'sell_only' (entries on sell signals only)
        """
        vbt = _lazy_import_vbt()
        signals = self.detect_signals(hist_data)
        close = hist_data['Close']

        if direction == "buy_only":
            entries = signals.df['Buy_Signal']
            exits = signals.df['Sell_Signal']
        elif direction == "sell_only":
            entries = signals.df['Sell_Signal']
            exits = signals.df['Buy_Signal']
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy_only' or 'sell_only'.")

        portfolio = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            init_cash=100_000,
            fees=0.001,
        )

        return extract_metrics(portfolio)
