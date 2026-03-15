# -*- coding: utf-8 -*-
"""Metric Registry — single source of truth for metric capabilities.

Code defines WHAT each metric IS (placeholder, format, source mapping).
DB (metric_config table) defines WHETHER it's active.
Version: 1.0.1 (2026-03-16)

Usage:
    from src.data.aurora.metric_config_repository import get_metric_config_repository
    from src.report.metric_registry import MetricRegistry

    db_statuses = get_metric_config_repository().get_all_statuses()
    registry = MetricRegistry(db_statuses)

    # Get only active metrics for a category
    ready = registry.get_ready_metrics(category='risk_metrics')

    # Backward-compatible with NumberInjector
    defs = registry.get_placeholder_definitions()

    # Build replacement dict for NumberInjector
    replacements = registry.build_replacement_dict(ground_truth, indicators, ...)
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricStatus(str, Enum):
    DRAFT = 'draft'
    COMPUTING = 'computing'
    READY = 'ready'
    DEPRECATED = 'deprecated'


# ---------------------------------------------------------------------------
# Metric definition (code-side capability)
# ---------------------------------------------------------------------------

@dataclass
class MetricDefinition:
    """Defines a metric's capability — what it IS, not whether it's active.

    Status comes from DB at runtime, not from this dataclass.
    """
    id: str
    placeholder: str          # e.g. "ATR_PCT"
    suffix: str               # e.g. "%", "/100", "x", ""
    category: str             # e.g. "risk_metrics" — must match DB category
    source: str               # "ground_truth" | "indicators" | "ticker_data" | ...
    source_key: str           # key in the source dict, e.g. "atr_pct"
    format_fn: Callable[[Any], str]  # formats the raw value to string
    description: str          # human-readable, shown in LLM context
    status: MetricStatus = field(default=MetricStatus.DRAFT)  # set from DB at runtime


# ---------------------------------------------------------------------------
# Format helpers (reused by metric definitions)
# ---------------------------------------------------------------------------

def _fmt_1f(v): return f"{v:.1f}" if v is not None else "0.0"
def _fmt_2f(v): return f"{v:.2f}" if v is not None else "0.00"
def _fmt_4f(v): return f"{v:.4f}" if v is not None else "0.0000"
def _fmt_abs_2f(v): return f"{abs(v):.2f}" if v is not None else "0.00"
def _fmt_str(v): return f"{v}" if v is not None and v != '' else "N/A"
def _fmt_pct_1f(v): return f"{v:.1f}" if v is not None else "0.0"


def _fmt_large_number(value):
    """Format large numbers with K/M/B/T suffixes."""
    if value is None or value == 'N/A':
        return 'N/A'
    try:
        val = float(value)
        if val >= 1e12:
            return f"{val/1e12:.2f}T"
        elif val >= 1e9:
            return f"{val/1e9:.2f}B"
        elif val >= 1e6:
            return f"{val/1e6:.2f}M"
        else:
            return f"{val:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_percentage(value):
    """Format percentage values (handles both 0.05 and 5.0 formats)."""
    if value is None or value == 'N/A':
        return 'N/A'
    try:
        val = float(value)
        return f"{val*100:.2f}" if val < 1 else f"{val:.2f}"
    except (ValueError, TypeError):
        return str(value)


# ---------------------------------------------------------------------------
# All metric capability definitions (code-side)
# ---------------------------------------------------------------------------

_METRIC_CAPABILITIES: List[MetricDefinition] = [
    # ── Risk Metrics ──
    MetricDefinition(id='uncertainty', placeholder='UNCERTAINTY', suffix='/100',
                     category='risk_metrics', source='ground_truth', source_key='uncertainty_score',
                     format_fn=_fmt_1f, description='Market uncertainty composite (0=stable, 100=extreme)'),
    MetricDefinition(id='atr_pct', placeholder='ATR_PCT', suffix='%',
                     category='risk_metrics', source='ground_truth', source_key='atr_pct',
                     format_fn=_fmt_2f, description='Price volatility as % of price (<1%=low, 1-2%=moderate, >3%=high)'),
    MetricDefinition(id='vwap_pct', placeholder='VWAP_PCT', suffix='%',
                     category='risk_metrics', source='ground_truth', source_key='vwap_pct',
                     format_fn=_fmt_abs_2f, description='Buy/sell pressure vs VWAP (+positive=buyers winning, -negative=sellers winning)'),
    MetricDefinition(id='volume_ratio', placeholder='VOLUME_RATIO', suffix='x',
                     category='risk_metrics', source='ground_truth', source_key='volume_ratio',
                     format_fn=_fmt_2f, description='Trading volume vs 20-day average (>1.5x=high interest, <0.8x=low interest)'),
    MetricDefinition(id='current_price', placeholder='CURRENT_PRICE', suffix='',
                     category='risk_metrics', source='indicators', source_key='current_price',
                     format_fn=_fmt_2f, description='Current stock price'),

    # ── Momentum ──
    MetricDefinition(id='rsi', placeholder='RSI', suffix='',
                     category='momentum_indicators', source='indicators', source_key='rsi',
                     format_fn=_fmt_2f, description='Momentum indicator (0-30=oversold, 70-100=overbought)'),
    MetricDefinition(id='macd', placeholder='MACD', suffix='',
                     category='momentum_indicators', source='indicators', source_key='macd',
                     format_fn=_fmt_4f, description='Trend strength (positive=bullish, negative=bearish)'),
    MetricDefinition(id='macd_signal', placeholder='MACD_SIGNAL', suffix='',
                     category='momentum_indicators', source='indicators', source_key='macd_signal',
                     format_fn=_fmt_4f, description='MACD signal line'),

    # ── Trend ──
    MetricDefinition(id='sma_20', placeholder='SMA_20', suffix='',
                     category='trend_indicators', source='indicators', source_key='sma_20',
                     format_fn=_fmt_2f, description='20-day simple moving average'),
    MetricDefinition(id='sma_50', placeholder='SMA_50', suffix='',
                     category='trend_indicators', source='indicators', source_key='sma_50',
                     format_fn=_fmt_2f, description='50-day simple moving average'),
    MetricDefinition(id='sma_200', placeholder='SMA_200', suffix='',
                     category='trend_indicators', source='indicators', source_key='sma_200',
                     format_fn=_fmt_2f, description='200-day simple moving average'),
    MetricDefinition(id='ema_12', placeholder='EMA_12', suffix='',
                     category='trend_indicators', source='indicators', source_key='ema_12',
                     format_fn=_fmt_2f, description='12-day exponential moving average'),
    MetricDefinition(id='ema_26', placeholder='EMA_26', suffix='',
                     category='trend_indicators', source='indicators', source_key='ema_26',
                     format_fn=_fmt_2f, description='26-day exponential moving average'),

    # ── Volatility ──
    MetricDefinition(id='atr', placeholder='ATR', suffix='',
                     category='volatility_indicators', source='indicators', source_key='atr',
                     format_fn=_fmt_2f, description='Average True Range (raw volatility)'),
    MetricDefinition(id='bollinger_upper', placeholder='BOLLINGER_UPPER', suffix='',
                     category='volatility_indicators', source='indicators', source_key='bollinger_upper',
                     format_fn=_fmt_2f, description='Bollinger Band upper'),
    MetricDefinition(id='bollinger_lower', placeholder='BOLLINGER_LOWER', suffix='',
                     category='volatility_indicators', source='indicators', source_key='bollinger_lower',
                     format_fn=_fmt_2f, description='Bollinger Band lower'),
    MetricDefinition(id='bollinger_middle', placeholder='BOLLINGER_MIDDLE', suffix='',
                     category='volatility_indicators', source='indicators', source_key='bollinger_middle',
                     format_fn=_fmt_2f, description='Bollinger Band middle'),

    # ── Volume ──
    MetricDefinition(id='vwap', placeholder='VWAP', suffix='',
                     category='volume_indicators', source='indicators', source_key='vwap',
                     format_fn=_fmt_2f, description='Volume Weighted Average Price'),

    # ── Fundamentals ──
    MetricDefinition(id='pe_ratio', placeholder='PE_RATIO', suffix='',
                     category='fundamentals', source='ticker_data', source_key='pe_ratio',
                     format_fn=_fmt_str, description='Price-to-Earnings ratio'),
    MetricDefinition(id='eps', placeholder='EPS', suffix='',
                     category='fundamentals', source='ticker_data', source_key='eps',
                     format_fn=_fmt_str, description='Earnings Per Share'),
    MetricDefinition(id='market_cap', placeholder='MARKET_CAP', suffix='',
                     category='fundamentals', source='ticker_data', source_key='market_cap',
                     format_fn=_fmt_large_number, description='Market capitalization'),
    MetricDefinition(id='revenue_growth', placeholder='REVENUE_GROWTH', suffix='%',
                     category='fundamentals', source='ticker_data', source_key='revenue_growth',
                     format_fn=_fmt_percentage, description='Revenue growth rate'),
    MetricDefinition(id='profit_margin', placeholder='PROFIT_MARGIN', suffix='%',
                     category='fundamentals', source='ticker_data', source_key='profit_margin',
                     format_fn=_fmt_percentage, description='Profit margin'),
    MetricDefinition(id='dividend_yield', placeholder='DIVIDEND_YIELD', suffix='%',
                     category='fundamentals', source='ticker_data', source_key='dividend_yield',
                     format_fn=_fmt_percentage, description='Dividend yield'),
    MetricDefinition(id='roe', placeholder='ROE', suffix='%',
                     category='fundamentals', source='ticker_data', source_key='return_on_equity',
                     format_fn=_fmt_percentage, description='Return on Equity'),
    MetricDefinition(id='debt_to_equity', placeholder='DEBT_TO_EQUITY', suffix='',
                     category='fundamentals', source='ticker_data', source_key='debt_to_equity',
                     format_fn=_fmt_str, description='Debt-to-Equity ratio'),
    MetricDefinition(id='current_ratio', placeholder='CURRENT_RATIO', suffix='',
                     category='fundamentals', source='ticker_data', source_key='current_ratio',
                     format_fn=_fmt_str, description='Current ratio'),
    MetricDefinition(id='book_value', placeholder='BOOK_VALUE', suffix='',
                     category='fundamentals', source='ticker_data', source_key='book_value',
                     format_fn=_fmt_str, description='Book value per share'),
    MetricDefinition(id='52_week_high', placeholder='52_WEEK_HIGH', suffix='',
                     category='fundamentals', source='ticker_data', source_key='fifty_two_week_high',
                     format_fn=_fmt_str, description='52-week high price'),
    MetricDefinition(id='52_week_low', placeholder='52_WEEK_LOW', suffix='',
                     category='fundamentals', source='ticker_data', source_key='fifty_two_week_low',
                     format_fn=_fmt_str, description='52-week low price'),
    MetricDefinition(id='target_price', placeholder='TARGET_PRICE', suffix='',
                     category='fundamentals', source='ticker_data', source_key='target_mean_price',
                     format_fn=_fmt_str, description='Analyst target price (mean)'),
    MetricDefinition(id='beta', placeholder='BETA', suffix='',
                     category='fundamentals', source='ticker_data', source_key='beta',
                     format_fn=_fmt_str, description='Beta (market risk)'),

    # ── Comparative ──
    MetricDefinition(id='performance_advantage', placeholder='PERFORMANCE_ADVANTAGE', suffix='',
                     category='comparative', source='comparative_insights', source_key='performance_advantage',
                     format_fn=_fmt_str, description='Performance vs peers'),
    MetricDefinition(id='volatility_advantage', placeholder='VOLATILITY_ADVANTAGE', suffix='',
                     category='comparative', source='comparative_insights', source_key='volatility_advantage',
                     format_fn=_fmt_str, description='Volatility vs peers'),
    MetricDefinition(id='comparative_return', placeholder='COMPARATIVE_RETURN', suffix='',
                     category='comparative', source='comparative_insights', source_key='comparative_return',
                     format_fn=_fmt_str, description='Return vs peer average'),
    MetricDefinition(id='peer_count', placeholder='PEER_COUNT', suffix='',
                     category='comparative', source='comparative_insights', source_key='peer_count',
                     format_fn=_fmt_str, description='Number of peer stocks'),

    # ── Strategy ──
    MetricDefinition(id='strategy_buy_return', placeholder='STRATEGY_BUY_RETURN', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.buy_only.total_return_pct',
                     format_fn=_fmt_2f, description='Buy strategy total return'),
    MetricDefinition(id='strategy_buy_sharpe', placeholder='STRATEGY_BUY_SHARPE', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.buy_only.sharpe_ratio',
                     format_fn=_fmt_2f, description='Buy strategy Sharpe ratio'),
    MetricDefinition(id='strategy_buy_win_rate', placeholder='STRATEGY_BUY_WIN_RATE', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.buy_only.win_rate',
                     format_fn=_fmt_1f, description='Buy strategy win rate'),
    MetricDefinition(id='strategy_buy_drawdown', placeholder='STRATEGY_BUY_DRAWDOWN', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.buy_only.max_drawdown_pct',
                     format_fn=lambda v: _fmt_2f(abs(v)) if v is not None else "0.00",
                     description='Buy strategy max drawdown'),
    MetricDefinition(id='strategy_sell_return', placeholder='STRATEGY_SELL_RETURN', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.sell_only.total_return_pct',
                     format_fn=_fmt_2f, description='Sell strategy total return'),
    MetricDefinition(id='strategy_sell_sharpe', placeholder='STRATEGY_SELL_SHARPE', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.sell_only.sharpe_ratio',
                     format_fn=_fmt_2f, description='Sell strategy Sharpe ratio'),
    MetricDefinition(id='strategy_sell_win_rate', placeholder='STRATEGY_SELL_WIN_RATE', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.sell_only.win_rate',
                     format_fn=_fmt_1f, description='Sell strategy win rate'),
    MetricDefinition(id='strategy_sell_drawdown', placeholder='STRATEGY_SELL_DRAWDOWN', suffix='',
                     category='strategy', source='strategy_performance', source_key='best_supporting.sell_only.max_drawdown_pct',
                     format_fn=lambda v: _fmt_2f(abs(v)) if v is not None else "0.00",
                     description='Sell strategy max drawdown'),

    # ── Percentiles ──
    MetricDefinition(id='uncertainty_percentile', placeholder='UNCERTAINTY_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='uncertainty_score',
                     format_fn=_fmt_1f, description='Uncertainty percentile vs 1yr history'),
    MetricDefinition(id='atr_pct_percentile', placeholder='ATR_PCT_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='atr_percent',
                     format_fn=_fmt_1f, description='ATR% percentile vs 1yr history'),
    MetricDefinition(id='vwap_pct_percentile', placeholder='VWAP_PCT_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='vwap_pct',
                     format_fn=_fmt_1f, description='VWAP% percentile vs 1yr history'),
    MetricDefinition(id='volume_ratio_percentile', placeholder='VOLUME_RATIO_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='volume_ratio',
                     format_fn=_fmt_1f, description='Volume ratio percentile vs 1yr history'),
    MetricDefinition(id='rsi_percentile', placeholder='RSI_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='rsi',
                     format_fn=_fmt_1f, description='RSI percentile vs 1yr history'),
    MetricDefinition(id='macd_percentile', placeholder='MACD_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='macd',
                     format_fn=_fmt_1f, description='MACD percentile vs 1yr history'),
    MetricDefinition(id='macd_signal_percentile', placeholder='MACD_SIGNAL_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='macd_signal',
                     format_fn=_fmt_1f, description='MACD signal percentile vs 1yr history'),
    MetricDefinition(id='sma_20_percentile', placeholder='SMA_20_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='sma_20',
                     format_fn=_fmt_1f, description='SMA20 percentile vs 1yr history'),
    MetricDefinition(id='sma_50_percentile', placeholder='SMA_50_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='sma_50',
                     format_fn=_fmt_1f, description='SMA50 percentile vs 1yr history'),
    MetricDefinition(id='sma_200_percentile', placeholder='SMA_200_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='sma_200',
                     format_fn=_fmt_1f, description='SMA200 percentile vs 1yr history'),
    MetricDefinition(id='ema_12_percentile', placeholder='EMA_12_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='ema_12',
                     format_fn=_fmt_1f, description='EMA12 percentile vs 1yr history'),
    MetricDefinition(id='ema_26_percentile', placeholder='EMA_26_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='ema_26',
                     format_fn=_fmt_1f, description='EMA26 percentile vs 1yr history'),
    MetricDefinition(id='atr_percentile', placeholder='ATR_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='atr',
                     format_fn=_fmt_1f, description='ATR percentile vs 1yr history'),
    MetricDefinition(id='bollinger_upper_percentile', placeholder='BOLLINGER_UPPER_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='bollinger_upper',
                     format_fn=_fmt_1f, description='Bollinger upper percentile vs 1yr history'),
    MetricDefinition(id='bollinger_lower_percentile', placeholder='BOLLINGER_LOWER_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='bollinger_lower',
                     format_fn=_fmt_1f, description='Bollinger lower percentile vs 1yr history'),
    MetricDefinition(id='bollinger_middle_percentile', placeholder='BOLLINGER_MIDDLE_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='bollinger_middle',
                     format_fn=_fmt_1f, description='Bollinger middle percentile vs 1yr history'),
    MetricDefinition(id='vwap_percentile', placeholder='VWAP_PERCENTILE', suffix='%',
                     category='percentiles', source='percentiles', source_key='vwap',
                     format_fn=_fmt_1f, description='VWAP percentile vs 1yr history'),
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MetricRegistry:
    """Registry that merges code capabilities with DB status.

    Code defines WHAT each metric IS.
    DB defines WHETHER it's active.
    """

    def __init__(self, db_statuses: Dict[str, str]):
        """Initialize registry with DB statuses.

        Args:
            db_statuses: {metric_id: status} from metric_config table.
                         DB is the sole source of truth for status.
                         Metrics not in DB are excluded.
        """
        self._metrics: Dict[str, MetricDefinition] = {}
        self._by_category: Dict[str, List[MetricDefinition]] = {}

        for cap in _METRIC_CAPABILITIES:
            status_str = db_statuses.get(cap.id)
            if status_str is None:
                # Metric not in DB → excluded
                continue

            try:
                status = MetricStatus(status_str)
            except ValueError:
                logger.warning(f"Unknown status '{status_str}' for metric '{cap.id}', skipping")
                continue

            metric = MetricDefinition(
                id=cap.id,
                placeholder=cap.placeholder,
                suffix=cap.suffix,
                category=cap.category,
                source=cap.source,
                source_key=cap.source_key,
                format_fn=cap.format_fn,
                description=cap.description,
                status=status,
            )
            self._metrics[cap.id] = metric
            self._by_category.setdefault(cap.category, []).append(metric)

        logger.info(
            f"MetricRegistry loaded: {len(self._metrics)} metrics "
            f"({sum(1 for m in self._metrics.values() if m.status == MetricStatus.READY)} ready, "
            f"{sum(1 for m in self._metrics.values() if m.status == MetricStatus.DEPRECATED)} deprecated)"
        )

    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        """Get a metric definition by ID (any status)."""
        return self._metrics.get(metric_id)

    def get_ready_metrics(self, category: str = None) -> List[MetricDefinition]:
        """Get metrics with status=READY, optionally filtered by category."""
        if category:
            return [m for m in self._by_category.get(category, [])
                    if m.status == MetricStatus.READY]
        return [m for m in self._metrics.values() if m.status == MetricStatus.READY]

    def is_ready(self, metric_id: str) -> bool:
        """Check if a metric is READY."""
        m = self._metrics.get(metric_id)
        return m is not None and m.status == MetricStatus.READY

    # ------------------------------------------------------------------
    # Backward-compatible interface (replaces NumberInjector static method)
    # ------------------------------------------------------------------

    def get_placeholder_definitions(self) -> Dict[str, List[Tuple[str, str]]]:
        """Return placeholder definitions grouped by category.

        Only includes READY metrics. Output format matches
        NumberInjector.get_placeholder_definitions() exactly.
        """
        result: Dict[str, List[Tuple[str, str]]] = {}
        for metric in self.get_ready_metrics():
            result.setdefault(metric.category, []).append(
                (metric.placeholder, metric.suffix)
            )
        return result

    # ------------------------------------------------------------------
    # Replacement dict (replaces hardcoded dict in NumberInjector)
    # ------------------------------------------------------------------

    def build_replacement_dict(
        self,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict,
        comparative_insights: Dict,
        strategy_performance: Dict = None,
    ) -> Dict[str, str]:
        """Build {placeholder: formatted_value} dict for READY metrics only.

        This replaces the hardcoded replacement dict in
        NumberInjector.inject_deterministic_numbers().
        """
        source_map = {
            'ground_truth': ground_truth,
            'indicators': indicators,
            'ticker_data': ticker_data,
            'comparative_insights': comparative_insights,
            'strategy_performance': strategy_performance or {},
        }

        replacements: Dict[str, str] = {}

        for metric in self.get_ready_metrics():
            # Skip percentiles — handled separately below
            if metric.category == 'percentiles':
                continue

            value = self._resolve_value(metric, source_map)
            if value is not None:
                placeholder_key = f"{{{metric.placeholder}}}"
                replacements[placeholder_key] = metric.format_fn(value)

        # Percentile replacements (special: values are nested dicts)
        for metric in self.get_ready_metrics(category='percentiles'):
            pct_data = percentiles.get(metric.source_key)
            if pct_data is None:
                continue
            percentile_val = pct_data.get('percentile', 0) if isinstance(pct_data, dict) else pct_data
            placeholder_key = f"{{{metric.placeholder}}}"
            replacements[placeholder_key] = metric.format_fn(percentile_val)

        return replacements

    def _resolve_value(self, metric: MetricDefinition, source_map: Dict) -> Any:
        """Resolve a metric's value from the appropriate source dict."""
        source_dict = source_map.get(metric.source, {})
        if not source_dict:
            return None

        # Handle dotted keys for strategy (e.g., "best_supporting.buy_only.total_return_pct")
        if '.' in metric.source_key:
            parts = metric.source_key.split('.')
            current = source_dict
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
                if current is None:
                    return None
            return current

        return source_dict.get(metric.source_key)

    # ------------------------------------------------------------------
    # Has-value check (replaces PromptBuilder._has_value())
    # ------------------------------------------------------------------

    def has_value(
        self,
        metric_id: str,
        ground_truth: Dict,
        indicators: Dict,
        percentiles: Dict,
        ticker_data: Dict,
        comparative_insights: Dict,
        strategy_performance: Dict = None,
    ) -> bool:
        """Check if a metric has actual non-empty data available.

        Only returns True for READY metrics with non-None values.
        Replaces PromptBuilder._has_value().
        """
        metric = self._metrics.get(metric_id)
        if metric is None or metric.status != MetricStatus.READY:
            return False

        source_map = {
            'ground_truth': ground_truth,
            'indicators': indicators,
            'ticker_data': ticker_data,
            'comparative_insights': comparative_insights,
            'strategy_performance': strategy_performance or {},
        }

        # Percentiles: special handling
        if metric.category == 'percentiles':
            pct_data = percentiles.get(metric.source_key)
            if pct_data is None:
                return False
            if isinstance(pct_data, dict):
                return pct_data.get('percentile') is not None
            return pct_data is not None

        # Strategy: check if nested structure has data
        if metric.source == 'strategy_performance':
            value = self._resolve_value(metric, source_map)
            return value is not None

        value = self._resolve_value(metric, source_map)

        # For price-like values, 0 or negative means no data
        if metric.source_key in ('current_price', 'sma_20', 'sma_50', 'sma_200',
                                  'ema_12', 'ema_26', 'atr', 'bollinger_upper',
                                  'bollinger_lower', 'bollinger_middle', 'vwap'):
            return value is not None and value > 0

        # For fundamentals, N/A and empty string mean no data
        if metric.source == 'ticker_data':
            return value is not None and value != 'N/A' and value != ''

        # For comparative, N/A means no data
        if metric.source == 'comparative_insights':
            return value is not None and value != 'N/A'

        # For ground_truth risk metrics, 0 is valid for some but not for uncertainty
        if metric.source == 'ground_truth':
            return value is not None and value != 0

        # For indicators like RSI, MACD — None means no data, 0 is valid
        return value is not None


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_registry_instance: Optional[MetricRegistry] = None


def get_metric_registry(db_statuses: Dict[str, str] = None) -> MetricRegistry:
    """Get or create MetricRegistry singleton.

    Args:
        db_statuses: If provided, creates/recreates the registry.
                     If None and singleton exists, returns cached instance.
                     If None and no singleton, raises ValueError.
    """
    global _registry_instance
    if db_statuses is not None:
        _registry_instance = MetricRegistry(db_statuses)
    if _registry_instance is None:
        raise ValueError(
            "MetricRegistry not initialized. Call get_metric_registry(db_statuses) first, "
            "or ensure MetricConfigRepository.get_all_statuses() is called at Lambda startup."
        )
    return _registry_instance
