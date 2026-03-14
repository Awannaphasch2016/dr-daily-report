"""Tests for SMA Crossover strategy"""

import pytest
import pandas as pd

from src.backtesting.strategies.sma_crossover import SMACrossoverStrategy
from src.backtesting.types import BacktestResult, SignalFrame


@pytest.mark.tier0
class TestSMACrossoverDetectSignals:
    """Signal detection tests"""

    def test_returns_signal_frame(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.detect_signals(synthetic_ohlcv)

        assert isinstance(result, SignalFrame)
        assert isinstance(result.df, pd.DataFrame)

    def test_signal_frame_has_required_columns(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.detect_signals(synthetic_ohlcv)

        required = {'Close', 'SMA_Fast', 'SMA_Slow', 'Buy_Signal', 'Sell_Signal'}
        assert required.issubset(set(result.df.columns))

    def test_signals_are_boolean(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        df = strategy.detect_signals(synthetic_ohlcv).df

        assert df['Buy_Signal'].dtype == bool
        assert df['Sell_Signal'].dtype == bool

    def test_produces_signals_on_sine_data(self, synthetic_ohlcv):
        """Sine wave data should produce at least some crossover signals."""
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        df = strategy.detect_signals(synthetic_ohlcv).df

        assert df['Buy_Signal'].sum() > 0
        assert df['Sell_Signal'].sum() > 0

    def test_same_length_as_input(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        df = strategy.detect_signals(synthetic_ohlcv).df

        assert len(df) == len(synthetic_ohlcv)

    def test_strategy_name(self):
        strategy = SMACrossoverStrategy(fast_period=20, slow_period=50)
        assert "20" in strategy.name
        assert "50" in strategy.name


@pytest.mark.tier0
class TestSMACrossoverBacktest:
    """Backtest execution tests"""

    def test_buy_only_returns_backtest_result(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.backtest(synthetic_ohlcv, 'buy_only')

        assert isinstance(result, BacktestResult)

    def test_sell_only_returns_backtest_result(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.backtest(synthetic_ohlcv, 'sell_only')

        assert isinstance(result, BacktestResult)

    def test_metrics_are_python_native_types(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.backtest(synthetic_ohlcv, 'buy_only')

        assert isinstance(result.total_return_pct, float)
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.win_rate, float)
        assert isinstance(result.max_drawdown_pct, float)
        assert isinstance(result.num_signals, int)

    def test_invalid_direction_raises(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)

        with pytest.raises(ValueError, match="Invalid direction"):
            strategy.backtest(synthetic_ohlcv, 'invalid')

    def test_to_dict_excludes_raw_metrics(self, synthetic_ohlcv):
        strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        result = strategy.backtest(synthetic_ohlcv, 'buy_only')
        d = result.to_dict()

        assert 'raw_metrics' not in d
        assert 'total_return_pct' in d
        assert 'sharpe_ratio' in d
        assert 'win_rate' in d
        assert 'max_drawdown_pct' in d
        assert 'num_signals' in d
