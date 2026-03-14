"""RSI Threshold strategy powered by VectorBT Pro"""

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


class RSIThresholdStrategy(BaseStrategy):
    """RSI overbought/oversold: buy when RSI < oversold, sell when RSI > overbought."""

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"RSI({self.period}, {self.oversold}/{self.overbought})"

    def detect_signals(self, hist_data: pd.DataFrame) -> SignalFrame:
        vbt = _lazy_import_vbt()
        close = hist_data['Close']

        rsi = vbt.RSI.run(close, window=self.period).rsi

        # Buy when RSI crosses below oversold; sell when crosses above overbought
        buy_signal = (rsi < self.oversold) & (rsi.shift(1) >= self.oversold)
        sell_signal = (rsi > self.overbought) & (rsi.shift(1) <= self.overbought)

        df = pd.DataFrame({
            'Close': close,
            'RSI': rsi,
            'Buy_Signal': buy_signal.fillna(False),
            'Sell_Signal': sell_signal.fillna(False),
        }, index=hist_data.index)

        return SignalFrame(
            df=df,
            strategy_name=self.name,
            indicator_columns=['RSI'],
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
