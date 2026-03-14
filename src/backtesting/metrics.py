"""Extract standardized metrics from VectorBT Pro Portfolio objects"""

import math

from src.backtesting.types import BacktestResult


def _safe_float(value, default: float = 0.0) -> float:
    """Convert numpy/pandas scalar to Python float, handling NaN/Inf."""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """Convert numpy/pandas scalar to Python int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_metrics(portfolio) -> BacktestResult:
    """Extract BacktestResult from a VBT Portfolio object.

    Args:
        portfolio: vectorbtpro Portfolio object

    Returns:
        BacktestResult with all metrics populated
    """
    stats = portfolio.stats()

    # Map VBT stat names → BacktestResult fields
    total_return = _safe_float(stats.get('Total Return [%]', 0))
    sharpe = _safe_float(stats.get('Sharpe Ratio', 0))
    max_dd = _safe_float(stats.get('Max Drawdown [%]', 0))
    total_trades = _safe_int(stats.get('Total Trades', 0))
    win_rate = _safe_float(stats.get('Win Rate [%]', 0))

    # Derived metrics
    profit_factor = _safe_float(stats.get('Profit Factor', 0))
    calmar = _safe_float(stats.get('Calmar Ratio', 0))

    # Average trade duration
    avg_duration = stats.get('Avg Winning Trade Duration', None)
    avg_duration_days = 0.0
    if avg_duration is not None:
        try:
            avg_duration_days = _safe_float(avg_duration.total_seconds() / 86400)
        except AttributeError:
            pass

    # Count signals (entries)
    try:
        num_signals = _safe_int(portfolio.entries.sum())
    except Exception:
        num_signals = total_trades

    return BacktestResult(
        total_return_pct=total_return,
        sharpe_ratio=sharpe,
        win_rate=win_rate,
        max_drawdown_pct=max_dd,
        num_signals=num_signals,
        total_trades=total_trades,
        profit_factor=profit_factor,
        calmar_ratio=calmar,
        avg_trade_duration_days=avg_duration_days,
        raw_metrics=dict(stats),
    )
