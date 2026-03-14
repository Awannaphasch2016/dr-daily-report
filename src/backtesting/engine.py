"""BacktestEngine — orchestrator for running strategies"""

import logging
from typing import Any, Dict

import pandas as pd

from src.backtesting.strategies.base import BaseStrategy
from src.backtesting.types import BacktestResult

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Registry-based engine for running backtests across multiple strategies."""

    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}

    def register_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """Register a strategy by name."""
        self._strategies[name] = strategy

    @property
    def strategy_names(self) -> list:
        return list(self._strategies.keys())

    def run(self, name: str, hist_data: pd.DataFrame, direction: str) -> BacktestResult:
        """Run a single registered strategy.

        Args:
            name: Registered strategy name
            hist_data: OHLCV DataFrame
            direction: 'buy_only' or 'sell_only'

        Raises:
            KeyError: If strategy name not registered
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not registered. Available: {self.strategy_names}")
        return self._strategies[name].backtest(hist_data, direction)

    def run_all(self, hist_data: pd.DataFrame) -> Dict[str, Dict[str, BacktestResult]]:
        """Run all registered strategies in both directions.

        Returns:
            {strategy_name: {'buy_only': BacktestResult, 'sell_only': BacktestResult}}
        """
        results = {}
        for name, strategy in self._strategies.items():
            try:
                results[name] = {
                    'buy_only': strategy.backtest(hist_data, 'buy_only'),
                    'sell_only': strategy.backtest(hist_data, 'sell_only'),
                }
            except Exception as e:
                logger.warning(f"Strategy '{name}' failed: {e}")
                continue
        return results

    @staticmethod
    def summarize(
        results: Dict[str, Dict[str, BacktestResult]]
    ) -> Dict[str, Any]:
        """Convert run_all() output into per-strategy dicts.

        Pure conversion: BacktestResult → dict. No voting or interpretation.

        Args:
            results: Output of run_all()

        Returns:
            Dict with per_strategy key mapping strategy names to buy/sell dicts
        """
        if not results:
            return {'per_strategy': {}}

        per_strategy = {}

        for name, directions in results.items():
            buy_result = directions['buy_only']
            sell_result = directions['sell_only']

            buy_dict = buy_result.to_dict() if isinstance(buy_result, BacktestResult) else buy_result
            sell_dict = sell_result.to_dict() if isinstance(sell_result, BacktestResult) else sell_result

            per_strategy[name] = {
                'buy_only': buy_dict,
                'sell_only': sell_dict,
            }

        return {'per_strategy': per_strategy}
