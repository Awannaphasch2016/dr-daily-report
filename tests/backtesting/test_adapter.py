"""Tests for backward-compatible adapter — verifies exact dict shape for downstream consumers"""

import pytest
import pandas as pd

from src.backtesting.adapters import SMAStrategyBacktester


# The exact keys downstream code expects
REQUIRED_BACKTEST_KEYS = {'total_return_pct', 'sharpe_ratio', 'win_rate', 'max_drawdown_pct', 'num_signals'}


@pytest.mark.tier0
class TestAdapterBackwardCompat:
    """Ensure adapter output matches what workflow_nodes.py and section_formatters.py expect."""

    def test_constructor_matches_old_signature(self):
        """Must accept fast_period and slow_period kwargs."""
        bt = SMAStrategyBacktester(fast_period=20, slow_period=50)
        assert bt.fast_period == 20
        assert bt.slow_period == 50

    def test_constructor_defaults(self):
        bt = SMAStrategyBacktester()
        assert bt.fast_period == 20
        assert bt.slow_period == 50

    def test_detect_signals_returns_dataframe_or_none(self, synthetic_ohlcv):
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)
        result = bt.detect_signals(synthetic_ohlcv)

        assert result is None or isinstance(result, pd.DataFrame)

    def test_detect_signals_has_required_columns(self, synthetic_ohlcv):
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)
        df = bt.detect_signals(synthetic_ohlcv)

        assert df is not None
        required = {'Close', 'SMA_Fast', 'SMA_Slow', 'Buy_Signal', 'Sell_Signal'}
        assert required.issubset(set(df.columns))

    def test_backtest_buy_only_returns_dict_with_required_keys(self, synthetic_ohlcv):
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)
        result = bt.backtest_buy_only(synthetic_ohlcv)

        assert isinstance(result, dict)
        assert REQUIRED_BACKTEST_KEYS.issubset(set(result.keys()))

    def test_backtest_sell_only_returns_dict_with_required_keys(self, synthetic_ohlcv):
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)
        result = bt.backtest_sell_only(synthetic_ohlcv)

        assert isinstance(result, dict)
        assert REQUIRED_BACKTEST_KEYS.issubset(set(result.keys()))

    def test_backtest_values_are_json_serializable(self, synthetic_ohlcv):
        """All values must be plain Python types for Lambda JSON responses."""
        import json

        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)
        result = bt.backtest_buy_only(synthetic_ohlcv)

        # This will raise if any numpy types sneak through
        json.dumps(result)

    def test_workflow_integration_shape(self, synthetic_ohlcv):
        """Simulate what workflow_nodes.py does — the full strategy_performance dict shape."""
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)

        buy_results = bt.backtest_buy_only(synthetic_ohlcv)
        sell_results = bt.backtest_sell_only(synthetic_ohlcv)

        assert buy_results is not None
        assert sell_results is not None

        # This is the exact shape workflow_nodes.py builds
        strategy_performance = {
            'buy_only': buy_results,
            'sell_only': sell_results,
        }

        # Verify what section_formatters.py accesses
        assert isinstance(strategy_performance['buy_only']['total_return_pct'], float)
        assert isinstance(strategy_performance['buy_only']['sharpe_ratio'], float)
        assert isinstance(strategy_performance['buy_only']['win_rate'], float)
        assert isinstance(strategy_performance['buy_only']['max_drawdown_pct'], float)
        assert isinstance(strategy_performance['buy_only']['num_signals'], int)

    def test_graceful_failure_returns_none(self):
        """On bad input, adapter returns None instead of raising."""
        bt = SMAStrategyBacktester(fast_period=10, slow_period=30)

        empty_df = pd.DataFrame()
        assert bt.detect_signals(empty_df) is None
        assert bt.backtest_buy_only(empty_df) is None
        assert bt.backtest_sell_only(empty_df) is None
