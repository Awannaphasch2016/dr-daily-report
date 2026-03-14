"""Strategy registry and factory"""

from src.backtesting.types import StrategyType

# Lazy strategy registry — avoids importing VBT Pro at module level
_STRATEGY_MAP = {
    StrategyType.SMA_CROSSOVER: "src.backtesting.strategies.sma_crossover.SMACrossoverStrategy",
    StrategyType.RSI_THRESHOLD: "src.backtesting.strategies.rsi_threshold.RSIThresholdStrategy",
    StrategyType.MACD_CROSSOVER: "src.backtesting.strategies.macd_crossover.MACDCrossoverStrategy",
    StrategyType.BOLLINGER_BAND: "src.backtesting.strategies.bollinger_band.BollingerBandStrategy",
}


def get_strategy(strategy_type: StrategyType, **kwargs):
    """Factory: instantiate a strategy by type with lazy import.

    Args:
        strategy_type: Which strategy to create
        **kwargs: Strategy-specific parameters (e.g. fast_period=20)

    Returns:
        Strategy instance
    """
    import importlib

    fqn = _STRATEGY_MAP[strategy_type]
    module_path, class_name = fqn.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(**kwargs)
