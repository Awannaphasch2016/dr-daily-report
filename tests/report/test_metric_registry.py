# -*- coding: utf-8 -*-
"""Tests for MetricRegistry — the central metric management system."""

import pytest
from src.report.metric_registry import (
    MetricRegistry, MetricStatus, MetricDefinition,
    _METRIC_CAPABILITIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_ready_statuses():
    """Build db_statuses with ALL metrics set to 'ready'."""
    return {cap.id: 'ready' for cap in _METRIC_CAPABILITIES}


def _production_statuses():
    """Build db_statuses matching the migration seed (uncertainty=deprecated)."""
    statuses = _all_ready_statuses()
    statuses['uncertainty'] = 'deprecated'
    statuses['uncertainty_percentile'] = 'deprecated'
    return statuses


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestRegistryInit:
    def test_loads_all_ready_metrics(self):
        registry = MetricRegistry(_all_ready_statuses())
        ready = registry.get_ready_metrics()
        assert len(ready) == len(_METRIC_CAPABILITIES)

    def test_excludes_metrics_not_in_db(self):
        # Only provide 2 metrics in DB
        registry = MetricRegistry({'atr_pct': 'ready', 'rsi': 'ready'})
        all_metrics = list(registry._metrics.keys())
        assert set(all_metrics) == {'atr_pct', 'rsi'}

    def test_excludes_unknown_status(self):
        registry = MetricRegistry({'atr_pct': 'invalid_status'})
        assert registry.get_metric('atr_pct') is None

    def test_empty_db_produces_empty_registry(self):
        registry = MetricRegistry({})
        assert len(registry.get_ready_metrics()) == 0


# ---------------------------------------------------------------------------
# Status filtering
# ---------------------------------------------------------------------------

class TestStatusFiltering:
    def test_deprecated_excluded_from_ready(self):
        registry = MetricRegistry(_production_statuses())
        ready_ids = {m.id for m in registry.get_ready_metrics()}
        assert 'uncertainty' not in ready_ids
        assert 'uncertainty_percentile' not in ready_ids

    def test_deprecated_still_accessible_via_get_metric(self):
        registry = MetricRegistry(_production_statuses())
        m = registry.get_metric('uncertainty')
        assert m is not None
        assert m.status == MetricStatus.DEPRECATED

    def test_is_ready(self):
        registry = MetricRegistry(_production_statuses())
        assert registry.is_ready('atr_pct') is True
        assert registry.is_ready('uncertainty') is False
        assert registry.is_ready('nonexistent') is False

    def test_category_filter(self):
        registry = MetricRegistry(_production_statuses())
        risk = registry.get_ready_metrics(category='risk_metrics')
        risk_ids = {m.id for m in risk}
        assert 'atr_pct' in risk_ids
        assert 'uncertainty' not in risk_ids
        # RSI should NOT be in risk_metrics
        assert 'rsi' not in risk_ids

    def test_computing_status_excluded_from_ready(self):
        statuses = _all_ready_statuses()
        statuses['rsi'] = 'computing'
        registry = MetricRegistry(statuses)
        assert registry.is_ready('rsi') is False
        assert registry.get_metric('rsi').status == MetricStatus.COMPUTING


# ---------------------------------------------------------------------------
# get_placeholder_definitions (backward compat)
# ---------------------------------------------------------------------------

class TestPlaceholderDefinitions:
    def test_structure_matches_old_format(self):
        """Output should be dict of category -> list of (placeholder, suffix) tuples."""
        registry = MetricRegistry(_all_ready_statuses())
        defs = registry.get_placeholder_definitions()
        assert isinstance(defs, dict)
        for category, items in defs.items():
            assert isinstance(items, list)
            for item in items:
                assert isinstance(item, tuple)
                assert len(item) == 2

    def test_uncertainty_excluded_when_deprecated(self):
        registry = MetricRegistry(_production_statuses())
        defs = registry.get_placeholder_definitions()
        all_placeholders = []
        for items in defs.values():
            all_placeholders.extend(p[0] for p in items)
        assert 'UNCERTAINTY' not in all_placeholders
        assert 'UNCERTAINTY_PERCENTILE' not in all_placeholders

    def test_all_ready_categories_present(self):
        registry = MetricRegistry(_all_ready_statuses())
        defs = registry.get_placeholder_definitions()
        expected_categories = {
            'risk_metrics', 'momentum_indicators', 'trend_indicators',
            'volatility_indicators', 'volume_indicators', 'fundamentals',
            'comparative', 'strategy', 'percentiles',
        }
        assert set(defs.keys()) == expected_categories


# ---------------------------------------------------------------------------
# build_replacement_dict
# ---------------------------------------------------------------------------

class TestBuildReplacementDict:
    def setup_method(self):
        self.registry = MetricRegistry(_production_statuses())
        self.ground_truth = {
            'uncertainty_score': 35.0,
            'atr_pct': 1.82,
            'vwap_pct': 3.5,
            'volume_ratio': 1.45,
        }
        self.indicators = {
            'rsi': 55.0, 'macd': 0.02, 'macd_signal': 0.01,
            'current_price': 14.5,
            'sma_20': 14.0, 'sma_50': 13.5, 'sma_200': 12.0,
            'ema_12': 14.2, 'ema_26': 13.8,
            'atr': 0.26, 'bollinger_upper': 15.0,
            'bollinger_lower': 13.0, 'bollinger_middle': 14.0,
            'vwap': 14.3,
        }

    def test_uncertainty_not_in_replacements(self):
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, {}, {}, {}
        )
        assert '{UNCERTAINTY}' not in replacements

    def test_atr_pct_in_replacements(self):
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, {}, {}, {}
        )
        assert '{ATR_PCT}' in replacements
        assert replacements['{ATR_PCT}'] == '1.82'

    def test_vwap_pct_uses_abs(self):
        self.ground_truth['vwap_pct'] = -2.5
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, {}, {}, {}
        )
        assert replacements['{VWAP_PCT}'] == '2.50'

    def test_fundamental_formatting(self):
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, {},
            ticker_data={'pe_ratio': 8.5, 'market_cap': 2_500_000_000},
            comparative_insights={},
        )
        assert replacements['{PE_RATIO}'] == '8.5'
        assert replacements['{MARKET_CAP}'] == '2.50B'

    def test_strategy_nested_keys(self):
        strategy = {
            'best_supporting': {
                'buy_only': {
                    'total_return_pct': 15.5,
                    'sharpe_ratio': 1.2,
                    'win_rate': 65.0,
                    'max_drawdown_pct': -8.3,
                },
            },
        }
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, {}, {}, {},
            strategy_performance=strategy,
        )
        assert replacements['{STRATEGY_BUY_RETURN}'] == '15.50'
        assert replacements['{STRATEGY_BUY_DRAWDOWN}'] == '8.30'

    def test_percentile_replacements(self):
        percentiles = {
            'rsi': {'percentile': 62.5, 'mean': 50},
            'atr_percent': {'percentile': 30.1},
        }
        replacements = self.registry.build_replacement_dict(
            self.ground_truth, self.indicators, percentiles, {}, {}
        )
        assert replacements['{RSI_PERCENTILE}'] == '62.5'
        assert replacements['{ATR_PCT_PERCENTILE}'] == '30.1'


# ---------------------------------------------------------------------------
# has_value
# ---------------------------------------------------------------------------

class TestHasValue:
    def setup_method(self):
        self.registry = MetricRegistry(_production_statuses())

    def test_deprecated_metric_returns_false(self):
        assert self.registry.has_value(
            'uncertainty',
            ground_truth={'uncertainty_score': 50},
            indicators={}, percentiles={}, ticker_data={},
            comparative_insights={},
        ) is False

    def test_ready_metric_with_data_returns_true(self):
        assert self.registry.has_value(
            'atr_pct',
            ground_truth={'atr_pct': 1.5},
            indicators={}, percentiles={}, ticker_data={},
            comparative_insights={},
        ) is True

    def test_ready_metric_with_zero_returns_false_for_ground_truth(self):
        assert self.registry.has_value(
            'atr_pct',
            ground_truth={'atr_pct': 0},
            indicators={}, percentiles={}, ticker_data={},
            comparative_insights={},
        ) is False

    def test_price_metric_zero_returns_false(self):
        assert self.registry.has_value(
            'current_price',
            ground_truth={},
            indicators={'current_price': 0},
            percentiles={}, ticker_data={}, comparative_insights={},
        ) is False

    def test_fundamental_na_returns_false(self):
        assert self.registry.has_value(
            'pe_ratio',
            ground_truth={}, indicators={}, percentiles={},
            ticker_data={'pe_ratio': 'N/A'},
            comparative_insights={},
        ) is False

    def test_nonexistent_metric_returns_false(self):
        assert self.registry.has_value(
            'nonexistent',
            ground_truth={}, indicators={}, percentiles={},
            ticker_data={}, comparative_insights={},
        ) is False
