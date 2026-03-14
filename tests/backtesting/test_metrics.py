"""Tests for VBT metric extraction"""

import math
import json
import pytest

from src.backtesting.metrics import _safe_float, _safe_int, extract_metrics
from src.backtesting.types import BacktestResult


@pytest.mark.tier0
class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float(1.5) == 1.5

    def test_nan_returns_default(self):
        assert _safe_float(float('nan')) == 0.0

    def test_inf_returns_default(self):
        assert _safe_float(float('inf')) == 0.0

    def test_neg_inf_returns_default(self):
        assert _safe_float(float('-inf')) == 0.0

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_custom_default(self):
        assert _safe_float(None, default=-1.0) == -1.0

    def test_numpy_float(self):
        import numpy as np
        result = _safe_float(np.float64(3.14))
        assert isinstance(result, float)
        assert abs(result - 3.14) < 1e-10


@pytest.mark.tier0
class TestSafeInt:
    def test_normal_int(self):
        assert _safe_int(5) == 5

    def test_float_to_int(self):
        assert _safe_int(5.7) == 5

    def test_none_returns_default(self):
        assert _safe_int(None) == 0

    def test_numpy_int(self):
        import numpy as np
        result = _safe_int(np.int64(42))
        assert isinstance(result, int)
        assert result == 42


@pytest.mark.tier0
class TestExtractMetrics:
    def test_returns_backtest_result(self, synthetic_ohlcv):
        """Integration: run a real VBT portfolio and extract metrics."""
        import vectorbtpro as vbt

        close = synthetic_ohlcv['Close']
        entries = close > close.shift(1)
        exits = close < close.shift(1)

        portfolio = vbt.Portfolio.from_signals(
            close=close, entries=entries, exits=exits, init_cash=100_000
        )
        result = extract_metrics(portfolio)

        assert isinstance(result, BacktestResult)
        assert isinstance(result.total_return_pct, float)
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.num_signals, int)

    def test_result_is_json_serializable(self, synthetic_ohlcv):
        import vectorbtpro as vbt

        close = synthetic_ohlcv['Close']
        entries = close > close.shift(1)
        exits = close < close.shift(1)

        portfolio = vbt.Portfolio.from_signals(
            close=close, entries=entries, exits=exits, init_cash=100_000
        )
        result = extract_metrics(portfolio)

        # to_dict() must produce JSON-safe values
        json.dumps(result.to_dict())
