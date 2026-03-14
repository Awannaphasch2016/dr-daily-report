"""Data types for the backtesting module"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

import pandas as pd


class StrategyType(Enum):
    """Supported backtesting strategy types"""
    SMA_CROSSOVER = "sma_crossover"
    RSI_THRESHOLD = "rsi_threshold"
    MACD_CROSSOVER = "macd_crossover"
    BOLLINGER_BAND = "bollinger_band"


@dataclass
class BacktestResult:
    """Standardized backtest result from any strategy"""
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    max_drawdown_pct: float = 0.0
    num_signals: int = 0
    total_trades: int = 0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    avg_trade_duration_days: float = 0.0
    raw_metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialization (excludes raw_metrics)"""
        d = asdict(self)
        d.pop('raw_metrics', None)
        return d


@dataclass
class SignalFrame:
    """Wraps a signal DataFrame with metadata"""
    df: pd.DataFrame
    strategy_name: str
    indicator_columns: list = field(default_factory=list)
