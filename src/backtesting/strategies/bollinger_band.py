"""Bollinger Band Breakout strategy powered by VectorBT Pro"""

import logging

import pandas as pd

from src.backtesting.strategies.base import BaseStrategy
from src.backtesting.types import BacktestResult, SignalFrame
from src.backtesting.metrics import extract_metrics

logger = logging.getLogger(__name__)

_vbt = None


def _lazy_import_vbt():
    global _vbt
    if _vbt is None:
        import vectorbtpro as vbt
        _vbt = vbt
    return _vbt


class BollingerBandStrategy(BaseStrategy):
    """Bollinger Band: buy when price touches lower band, sell when touches upper band."""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    @property
    def name(self) -> str:
        return f"BB({self.period}, {self.std_dev})"

    def detect_signals(self, hist_data: pd.DataFrame) -> SignalFrame:
        vbt = _lazy_import_vbt()
        close = hist_data['Close']

        bb = vbt.BBANDS.run(close, window=self.period, alpha=self.std_dev)
        upper = bb.upper
        lower = bb.lower
        middle = bb.middle

        # Buy when close crosses below lower band; sell when crosses above upper band
        buy_signal = (close <= lower) & (close.shift(1) > lower.shift(1))
        sell_signal = (close >= upper) & (close.shift(1) < upper.shift(1))

        df = pd.DataFrame({
            'Close': close,
            'BB_Upper': upper,
            'BB_Middle': middle,
            'BB_Lower': lower,
            'Buy_Signal': buy_signal.fillna(False),
            'Sell_Signal': sell_signal.fillna(False),
        }, index=hist_data.index)

        return SignalFrame(
            df=df,
            strategy_name=self.name,
            indicator_columns=['BB_Upper', 'BB_Middle', 'BB_Lower'],
        )

    def backtest(self, hist_data: pd.DataFrame, direction: str) -> BacktestResult:
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
            raise ValueError(f"Invalid direction: {direction}")

        portfolio = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            init_cash=100_000,
            fees=0.001,
        )

        return extract_metrics(portfolio)
