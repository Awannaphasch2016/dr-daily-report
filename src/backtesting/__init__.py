"""Backtesting module — VectorBT Pro-powered strategy backtesting"""

from src.backtesting.adapters import SMAStrategyBacktester
from src.backtesting.engine import BacktestEngine
from src.backtesting.types import BacktestResult, SignalFrame, StrategyType
from src.backtesting.strategies import get_strategy

__all__ = [
    'SMAStrategyBacktester',
    'BacktestEngine',
    'BacktestResult',
    'SignalFrame',
    'StrategyType',
    'get_strategy',
]
