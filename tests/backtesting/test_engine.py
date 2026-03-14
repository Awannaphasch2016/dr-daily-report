"""Tests for BacktestEngine"""

import pytest

from src.backtesting.engine import BacktestEngine
from src.backtesting.strategies.sma_crossover import SMACrossoverStrategy
from src.backtesting.types import BacktestResult


@pytest.mark.tier0
class TestBacktestEngine:

    def test_register_and_list(self):
        engine = BacktestEngine()
        engine.register_strategy('sma', SMACrossoverStrategy())

        assert 'sma' in engine.strategy_names

    def test_run_registered_strategy(self, synthetic_ohlcv):
        engine = BacktestEngine()
        engine.register_strategy('sma', SMACrossoverStrategy(fast_period=10, slow_period=30))

        result = engine.run('sma', synthetic_ohlcv, 'buy_only')
        assert isinstance(result, BacktestResult)

    def test_run_unregistered_raises(self, synthetic_ohlcv):
        engine = BacktestEngine()

        with pytest.raises(KeyError, match="not registered"):
            engine.run('nonexistent', synthetic_ohlcv, 'buy_only')

    def test_run_all(self, synthetic_ohlcv):
        engine = BacktestEngine()
        engine.register_strategy('sma', SMACrossoverStrategy(fast_period=10, slow_period=30))

        results = engine.run_all(synthetic_ohlcv)

        assert 'sma' in results
        assert 'buy_only' in results['sma']
        assert 'sell_only' in results['sma']
        assert isinstance(results['sma']['buy_only'], BacktestResult)
