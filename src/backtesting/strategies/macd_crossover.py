"""MACD Crossover strategy powered by VectorBT Pro"""

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


class MACDCrossoverStrategy(BaseStrategy):
    """MACD signal-line crossover: buy when MACD crosses above signal, sell on cross below."""

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def name(self) -> str:
        return f"MACD({self.fast_period}/{self.slow_period}/{self.signal_period})"

    def detect_signals(self, hist_data: pd.DataFrame) -> SignalFrame:
        vbt = _lazy_import_vbt()
        close = hist_data['Close']

        macd_ind = vbt.MACD.run(
            close,
            fast_window=self.fast_period,
            slow_window=self.slow_period,
            signal_window=self.signal_period,
        )
        macd_line = macd_ind.macd
        signal_line = macd_ind.signal

        # Buy when MACD crosses above signal; sell when MACD crosses below signal
        buy_signal = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        sell_signal = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))

        df = pd.DataFrame({
            'Close': close,
            'MACD': macd_line,
            'MACD_Signal': signal_line,
            'MACD_Histogram': macd_line - signal_line,
            'Buy_Signal': buy_signal.fillna(False),
            'Sell_Signal': sell_signal.fillna(False),
        }, index=hist_data.index)

        return SignalFrame(
            df=df,
            strategy_name=self.name,
            indicator_columns=['MACD', 'MACD_Signal', 'MACD_Histogram'],
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
