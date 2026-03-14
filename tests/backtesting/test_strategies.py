"""Parametrized tests across all strategy types"""

import pytest

from src.backtesting.types import StrategyType, BacktestResult, SignalFrame
from src.backtesting.strategies import get_strategy


STRATEGY_CONFIGS = [
    (StrategyType.SMA_CROSSOVER, {'fast_period': 10, 'slow_period': 30}),
    (StrategyType.RSI_THRESHOLD, {}),
    (StrategyType.MACD_CROSSOVER, {}),
    (StrategyType.BOLLINGER_BAND, {}),
]


@pytest.mark.tier0
class TestAllStrategies:

    @pytest.mark.parametrize("strategy_type,kwargs", STRATEGY_CONFIGS,
                             ids=[s[0].value for s in STRATEGY_CONFIGS])
    def test_detect_signals_returns_signal_frame(self, synthetic_ohlcv, strategy_type, kwargs):
        strategy = get_strategy(strategy_type, **kwargs)
        result = strategy.detect_signals(synthetic_ohlcv)

        assert isinstance(result, SignalFrame)
        assert 'Buy_Signal' in result.df.columns
        assert 'Sell_Signal' in result.df.columns
        assert 'Close' in result.df.columns

    @pytest.mark.parametrize("strategy_type,kwargs", STRATEGY_CONFIGS,
                             ids=[s[0].value for s in STRATEGY_CONFIGS])
    def test_backtest_buy_only(self, synthetic_ohlcv, strategy_type, kwargs):
        strategy = get_strategy(strategy_type, **kwargs)
        result = strategy.backtest(synthetic_ohlcv, 'buy_only')

        assert isinstance(result, BacktestResult)
        assert isinstance(result.total_return_pct, float)
        assert isinstance(result.num_signals, int)

    @pytest.mark.parametrize("strategy_type,kwargs", STRATEGY_CONFIGS,
                             ids=[s[0].value for s in STRATEGY_CONFIGS])
    def test_backtest_sell_only(self, synthetic_ohlcv, strategy_type, kwargs):
        strategy = get_strategy(strategy_type, **kwargs)
        result = strategy.backtest(synthetic_ohlcv, 'sell_only')

        assert isinstance(result, BacktestResult)

    @pytest.mark.parametrize("strategy_type,kwargs", STRATEGY_CONFIGS,
                             ids=[s[0].value for s in STRATEGY_CONFIGS])
    def test_has_name(self, strategy_type, kwargs):
        strategy = get_strategy(strategy_type, **kwargs)
        assert isinstance(strategy.name, str)
        assert len(strategy.name) > 0

    @pytest.mark.parametrize("strategy_type,kwargs", STRATEGY_CONFIGS,
                             ids=[s[0].value for s in STRATEGY_CONFIGS])
    def test_invalid_direction_raises(self, synthetic_ohlcv, strategy_type, kwargs):
        strategy = get_strategy(strategy_type, **kwargs)

        with pytest.raises(ValueError):
            strategy.backtest(synthetic_ohlcv, 'invalid')
