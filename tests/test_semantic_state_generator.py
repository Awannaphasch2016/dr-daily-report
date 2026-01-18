"""Unit tests for SemanticStateGenerator

Tests semantic state classification logic (Layer 1 → Layer 2 conversion).
Verifies threshold boundaries and state transitions.
"""

import pytest
from src.analysis.semantic_state_generator import (
    SemanticStateGenerator,
    RiskRegime,
    MomentumState,
    TrendState,
    MarketRegime,
    DivergenceSignal,
    SemanticStates
)


class TestRiskRegime:
    """Test risk regime classification"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_stable_market_low_volatility(self):
        """Verify stable + low volatility classification"""
        ground_truth = {
            'uncertainty_score': 20,
            'atr_pct': 0.5,
            'vwap_pct': 2.0,
            'volume_ratio': 1.2
        }
        regime = self.generator.generate_risk_regime(ground_truth)

        assert regime.uncertainty_state == "stable"
        assert regime.volatility_regime == "low"
        assert regime.pressure_direction == "buying"
        assert regime.volume_confidence == "normal"

    def test_extreme_uncertainty_high_volatility(self):
        """Verify extreme + high volatility classification"""
        ground_truth = {
            'uncertainty_score': 85,
            'atr_pct': 3.5,
            'vwap_pct': -6.0,
            'volume_ratio': 2.5
        }
        regime = self.generator.generate_risk_regime(ground_truth)

        assert regime.uncertainty_state == "extreme"
        assert regime.volatility_regime == "extreme"
        assert regime.pressure_direction == "strong_selling"
        assert regime.volume_confidence == "very_high"

    def test_moderate_uncertainty_moderate_volatility(self):
        """Verify moderate classification (mid-range values)"""
        ground_truth = {
            'uncertainty_score': 40,
            'atr_pct': 1.5,
            'vwap_pct': 0.5,
            'volume_ratio': 1.0
        }
        regime = self.generator.generate_risk_regime(ground_truth)

        assert regime.uncertainty_state == "moderate"
        assert regime.volatility_regime == "moderate"
        assert regime.pressure_direction == "neutral"
        assert regime.volume_confidence == "normal"

    def test_boundary_conditions_uncertainty(self):
        """Test boundary values for uncertainty state transitions"""
        # Exactly at 25 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 25, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.uncertainty_state == "moderate"

        # Just below 25 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 24.9, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.uncertainty_state == "stable"

        # Exactly at 50 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 50, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.uncertainty_state == "high_risk"

        # Exactly at 75 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 75, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.uncertainty_state == "extreme"

    def test_boundary_conditions_volatility(self):
        """Test boundary values for volatility regime transitions"""
        # Just below 1.0 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0.99, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.volatility_regime == "low"

        # Exactly at 1.0 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 1.0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.volatility_regime == "moderate"

        # Exactly at 2.0 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 2.0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.volatility_regime == "high"

        # Exactly at 3.0 threshold
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 3.0, 'vwap_pct': 0, 'volume_ratio': 1})
        assert regime.volatility_regime == "extreme"

    def test_pressure_direction_thresholds(self):
        """Test buy/sell pressure direction classification"""
        # Strong buying (>5%)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 6.0, 'volume_ratio': 1})
        assert regime.pressure_direction == "strong_buying"

        # Buying (1-5%)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 2.5, 'volume_ratio': 1})
        assert regime.pressure_direction == "buying"

        # Neutral (-1 to 1%)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0.5, 'volume_ratio': 1})
        assert regime.pressure_direction == "neutral"

        # Selling (-5 to -1%)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': -2.5, 'volume_ratio': 1})
        assert regime.pressure_direction == "selling"

        # Strong selling (<-5%)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': -6.0, 'volume_ratio': 1})
        assert regime.pressure_direction == "strong_selling"

    def test_volume_confidence_levels(self):
        """Test volume confidence classification"""
        # Very low (<0.5x)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 0.3})
        assert regime.volume_confidence == "very_low"

        # Low (0.5-0.8x)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 0.6})
        assert regime.volume_confidence == "low"

        # Normal (0.8-1.5x)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1.0})
        assert regime.volume_confidence == "normal"

        # High (1.5-2.0x)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 1.7})
        assert regime.volume_confidence == "high"

        # Very high (>2.0x)
        regime = self.generator.generate_risk_regime({'uncertainty_score': 0, 'atr_pct': 0, 'vwap_pct': 0, 'volume_ratio': 2.5})
        assert regime.volume_confidence == "very_high"

    def test_to_dict_conversion(self):
        """Verify RiskRegime converts to dict correctly"""
        regime = RiskRegime(
            uncertainty_state="moderate",
            volatility_regime="low",
            pressure_direction="buying",
            volume_confidence="high"
        )
        result = regime.to_dict()

        assert isinstance(result, dict)
        assert result['uncertainty_state'] == "moderate"
        assert result['volatility_regime'] == "low"
        assert result['pressure_direction'] == "buying"
        assert result['volume_confidence'] == "high"


class TestMomentumState:
    """Test momentum state classification"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_oversold_bearish_weakening(self):
        """Verify oversold + bearish momentum classification"""
        indicators = {
            'rsi': 25,
            'macd': -0.9,  # diff = -0.9 - (-0.3) = -0.6 < -0.5 → strong_bearish
            'macd_signal': -0.3
        }
        momentum = self.generator.generate_momentum_state(indicators)

        assert momentum.rsi_zone == "oversold"
        assert momentum.macd_signal == "strong_bearish"
        assert momentum.momentum_direction == "weakening"

    def test_overbought_bullish_strengthening(self):
        """Verify overbought + bullish momentum classification"""
        indicators = {
            'rsi': 75,
            'macd': 1.3,  # diff = 1.3 - 0.8 = 0.5 → bullish (0.5 < diff < 1.0)
            'macd_signal': 0.8
        }
        momentum = self.generator.generate_momentum_state(indicators)

        assert momentum.rsi_zone == "overbought"
        assert momentum.macd_signal == "bullish"
        assert momentum.momentum_direction == "strengthening"

    def test_neutral_rsi_stable_momentum(self):
        """Verify neutral RSI + stable momentum classification"""
        indicators = {
            'rsi': 50,
            'macd': -0.1,  # negative but above signal → stable (-0.1 > -0.3)
            'macd_signal': -0.3
        }
        momentum = self.generator.generate_momentum_state(indicators)

        assert momentum.rsi_zone == "neutral"
        assert momentum.macd_signal == "neutral"  # diff = -0.1 - (-0.3) = 0.2 (0 < 0.2 < 0.5)
        assert momentum.momentum_direction == "stable"

    def test_rsi_zone_boundaries(self):
        """Test RSI zone threshold boundaries"""
        # Oversold (<30)
        momentum = self.generator.generate_momentum_state({'rsi': 29, 'macd': 0, 'macd_signal': 0})
        assert momentum.rsi_zone == "oversold"

        # Approaching oversold (30-40)
        momentum = self.generator.generate_momentum_state({'rsi': 35, 'macd': 0, 'macd_signal': 0})
        assert momentum.rsi_zone == "approaching_oversold"

        # Neutral (40-60)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 0, 'macd_signal': 0})
        assert momentum.rsi_zone == "neutral"

        # Approaching overbought (60-70)
        momentum = self.generator.generate_momentum_state({'rsi': 65, 'macd': 0, 'macd_signal': 0})
        assert momentum.rsi_zone == "approaching_overbought"

        # Overbought (>70)
        momentum = self.generator.generate_momentum_state({'rsi': 75, 'macd': 0, 'macd_signal': 0})
        assert momentum.rsi_zone == "overbought"

    def test_macd_signal_thresholds(self):
        """Test MACD signal classification based on MACD - Signal differential"""
        # Strong bearish (diff < -0.5)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': -1.0, 'macd_signal': -0.4})
        assert momentum.macd_signal == "strong_bearish"

        # Bearish (-0.5 < diff < 0)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': -0.2, 'macd_signal': 0})
        assert momentum.macd_signal == "bearish"

        # Neutral (0 < diff < 0.5)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 0.3, 'macd_signal': 0.1})
        assert momentum.macd_signal == "neutral"

        # Bullish (0.5 < diff < 1.0)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 0.8, 'macd_signal': 0.2})
        assert momentum.macd_signal == "bullish"

        # Strong bullish (diff > 1.0)
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 1.5, 'macd_signal': 0.3})
        assert momentum.macd_signal == "strong_bullish"

    def test_momentum_direction_logic(self):
        """Test momentum direction derived from MACD trend"""
        # Strengthening: positive MACD above signal
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 0.5, 'macd_signal': 0.3})
        assert momentum.momentum_direction == "strengthening"

        # Weakening: negative MACD below signal
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': -0.5, 'macd_signal': -0.3})
        assert momentum.momentum_direction == "weakening"

        # Stable: positive MACD below signal
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': 0.3, 'macd_signal': 0.5})
        assert momentum.momentum_direction == "stable"

        # Stable: negative MACD above signal
        momentum = self.generator.generate_momentum_state({'rsi': 50, 'macd': -0.3, 'macd_signal': -0.5})
        assert momentum.momentum_direction == "stable"


class TestTrendState:
    """Test trend state classification"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_strong_uptrend_golden_cross(self):
        """Verify strong uptrend (SMA20 > SMA50 > SMA200)"""
        indicators = {
            'current_price': 55,
            'sma_20': 52,
            'sma_50': 50,
            'sma_200': 48
        }
        trend = self.generator.generate_trend_state(indicators)

        assert trend.sma_alignment == "strong_uptrend"
        assert trend.price_vs_sma == "far_above"  # (55-52)/52 = 5.77% > 5%

    def test_strong_downtrend_death_cross(self):
        """Verify strong downtrend (SMA20 < SMA50 < SMA200)"""
        indicators = {
            'current_price': 42,
            'sma_20': 45,
            'sma_50': 48,
            'sma_200': 50
        }
        trend = self.generator.generate_trend_state(indicators)

        assert trend.sma_alignment == "strong_downtrend"
        assert trend.price_vs_sma == "far_below"  # (42-45)/45 = -6.67% < -5%

    def test_uptrend_partial_golden_cross(self):
        """Verify uptrend (SMA20 > SMA50, but SMA50 < SMA200)"""
        indicators = {
            'current_price': 50,
            'sma_20': 52,
            'sma_50': 50,
            'sma_200': 55
        }
        trend = self.generator.generate_trend_state(indicators)

        assert trend.sma_alignment == "uptrend"

    def test_downtrend_partial_death_cross(self):
        """Verify downtrend (SMA20 < SMA50, but SMA50 > SMA200)"""
        indicators = {
            'current_price': 50,
            'sma_20': 48,
            'sma_50': 50,
            'sma_200': 45
        }
        trend = self.generator.generate_trend_state(indicators)

        assert trend.sma_alignment == "downtrend"

    def test_sideways_mixed_signals(self):
        """Verify sideways when SMAs are equal (no clear trend)"""
        indicators = {
            'current_price': 50,
            'sma_20': 50,  # All SMAs equal → sideways
            'sma_50': 50,
            'sma_200': 50
        }
        trend = self.generator.generate_trend_state(indicators)

        assert trend.sma_alignment == "sideways"

    def test_price_vs_sma_positions(self):
        """Test price positioning relative to SMA20"""
        # Far above (>5%)
        trend = self.generator.generate_trend_state({'current_price': 106, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90})
        assert trend.price_vs_sma == "far_above"

        # Above (1-5%)
        trend = self.generator.generate_trend_state({'current_price': 103, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90})
        assert trend.price_vs_sma == "above"

        # At (-1 to 1%)
        trend = self.generator.generate_trend_state({'current_price': 100.5, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90})
        assert trend.price_vs_sma == "at"

        # Below (-5 to -1%)
        trend = self.generator.generate_trend_state({'current_price': 97, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90})
        assert trend.price_vs_sma == "below"

        # Far below (<-5%)
        trend = self.generator.generate_trend_state({'current_price': 94, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90})
        assert trend.price_vs_sma == "far_below"

    def test_zero_sma_handling(self):
        """Test graceful handling when SMA20 is 0 or missing"""
        trend = self.generator.generate_trend_state({'current_price': 50, 'sma_20': 0, 'sma_50': 48, 'sma_200': 45})
        assert trend.price_vs_sma == "at"  # Safe default when SMA20 is 0

        trend = self.generator.generate_trend_state({'current_price': 50, 'sma_50': 48, 'sma_200': 45})
        assert trend.price_vs_sma == "at"  # Safe default when SMA20 is missing


class TestSemanticStatesIntegration:
    """Test complete semantic state generation pipeline"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_generate_all_states_complete(self):
        """Test generating all semantic states from complete data"""
        ground_truth = {
            'uncertainty_score': 35,
            'atr_pct': 1.2,
            'vwap_pct': 3.5,
            'volume_ratio': 1.8
        }
        indicators = {
            'rsi': 65,
            'macd': 0.45,
            'macd_signal': 0.3,
            'current_price': 55,
            'sma_20': 52,
            'sma_50': 50,
            'sma_200': 48
        }

        states = self.generator.generate_all_states(ground_truth, indicators)

        # Verify all states generated
        assert isinstance(states, SemanticStates)
        assert isinstance(states.risk, RiskRegime)
        assert isinstance(states.momentum, MomentumState)
        assert isinstance(states.trend, TrendState)
        assert isinstance(states.market_regime, MarketRegime)
        assert isinstance(states.divergence, DivergenceSignal)

        # Verify specific states
        assert states.risk.uncertainty_state == "moderate"
        assert states.momentum.rsi_zone == "approaching_overbought"
        assert states.trend.sma_alignment == "strong_uptrend"
        assert states.market_regime.regime == "bull"  # Uptrend + non-weakening momentum
        assert states.divergence.signal == "no_divergence"  # No history provided

    def test_semantic_states_to_dict(self):
        """Test conversion to nested dictionary for template injection"""
        ground_truth = {'uncertainty_score': 20, 'atr_pct': 0.8, 'vwap_pct': 2, 'volume_ratio': 1.1}
        indicators = {'rsi': 50, 'macd': 0.2, 'macd_signal': 0.15, 'current_price': 50, 'sma_20': 49, 'sma_50': 48, 'sma_200': 47}

        states = self.generator.generate_all_states(ground_truth, indicators)
        result = states.to_dict()

        # Verify structure
        assert isinstance(result, dict)
        assert 'risk' in result
        assert 'momentum' in result
        assert 'trend' in result
        assert 'market_regime' in result
        assert 'divergence' in result

        # Verify nested dicts
        assert isinstance(result['risk'], dict)
        assert 'uncertainty_state' in result['risk']
        assert result['risk']['uncertainty_state'] == "stable"

        assert isinstance(result['momentum'], dict)
        assert 'rsi_zone' in result['momentum']

        assert isinstance(result['trend'], dict)
        assert 'sma_alignment' in result['trend']

        assert isinstance(result['market_regime'], dict)
        assert 'regime' in result['market_regime']

        assert isinstance(result['divergence'], dict)
        assert 'signal' in result['divergence']

    def test_empty_data_handling(self):
        """Test graceful handling of missing/empty data"""
        states = self.generator.generate_all_states({}, {})

        # Should still create states with defaults (0 values)
        assert isinstance(states, SemanticStates)
        assert states.risk.uncertainty_state == "stable"  # 0 < 25
        assert states.risk.volatility_regime == "low"  # 0 < 1.0
        assert states.momentum.rsi_zone == "neutral"  # Default RSI = 50
        assert states.trend.price_vs_sma == "at"  # Division by zero protection
        assert states.market_regime.regime == "sideways"  # Default with no clear trend
        assert states.divergence.signal == "no_divergence"  # No history = no divergence


class TestRealWorldScenarios:
    """Test realistic market scenarios"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_bullish_momentum_scenario(self):
        """Test: Strong uptrend with buying pressure and high volume"""
        ground_truth = {
            'uncertainty_score': 15,  # Stable market
            'atr_pct': 0.8,  # Low volatility
            'vwap_pct': 4.5,  # Buying pressure
            'volume_ratio': 1.9  # High volume
        }
        indicators = {
            'rsi': 68,  # Approaching overbought
            'macd': 0.9,  # diff = 0.9 - 0.4 = 0.5 → bullish
            'macd_signal': 0.4,
            'current_price': 105,
            'sma_20': 102,  # Price above SMA
            'sma_50': 100,
            'sma_200': 95
        }

        states = self.generator.generate_all_states(ground_truth, indicators)

        # Expected: Bullish scenario
        assert states.risk.uncertainty_state == "stable"
        assert states.risk.volatility_regime == "low"
        assert states.risk.pressure_direction == "buying"
        assert states.risk.volume_confidence == "high"
        assert states.momentum.rsi_zone == "approaching_overbought"
        assert states.momentum.macd_signal == "bullish"
        assert states.trend.sma_alignment == "strong_uptrend"

    def test_bearish_momentum_scenario(self):
        """Test: Downtrend with selling pressure and low volume"""
        ground_truth = {
            'uncertainty_score': 65,  # High risk
            'atr_pct': 2.5,  # High volatility
            'vwap_pct': -4.5,  # Selling pressure
            'volume_ratio': 0.6  # Low volume
        }
        indicators = {
            'rsi': 32,  # Approaching oversold
            'macd': -0.8,  # diff = -0.8 - (-0.2) = -0.6 < -0.5 → strong_bearish
            'macd_signal': -0.2,
            'current_price': 92,
            'sma_20': 95,  # Price below SMA
            'sma_50': 97,
            'sma_200': 100
        }

        states = self.generator.generate_all_states(ground_truth, indicators)

        # Expected: Bearish scenario
        assert states.risk.uncertainty_state == "high_risk"
        assert states.risk.volatility_regime == "high"
        assert states.risk.pressure_direction == "selling"
        assert states.risk.volume_confidence == "low"
        assert states.momentum.rsi_zone == "approaching_oversold"
        assert states.momentum.macd_signal == "strong_bearish"
        assert states.trend.sma_alignment == "strong_downtrend"


class TestMarketRegime:
    """Test market regime classification (Tier-1 derived state)"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_bull_regime_strong_uptrend(self):
        """Test bull regime with strong uptrend and strengthening momentum"""
        indicators = {
            'rsi': 65,
            'macd': 0.5,
            'macd_signal': 0.3,  # Positive MACD above signal = strengthening
            'current_price': 55,
            'sma_20': 52,
            'sma_50': 50,
            'sma_200': 48  # Strong uptrend: SMA20 > SMA50 > SMA200
        }
        regime = self.generator.generate_market_regime(indicators)

        assert regime.regime == "bull"

    def test_bear_regime_strong_downtrend(self):
        """Test bear regime with strong downtrend and weakening momentum"""
        indicators = {
            'rsi': 35,
            'macd': -0.5,
            'macd_signal': -0.3,  # Negative MACD below signal = weakening
            'current_price': 40,
            'sma_20': 45,
            'sma_50': 48,
            'sma_200': 50  # Strong downtrend: SMA20 < SMA50 < SMA200
        }
        regime = self.generator.generate_market_regime(indicators)

        assert regime.regime == "bear"

    def test_sideways_mixed_signals(self):
        """Test sideways regime with mixed trend/momentum signals"""
        indicators = {
            'rsi': 50,
            'macd': 0.1,
            'macd_signal': 0.2,  # Positive but below signal = stable/not strengthening
            'current_price': 50,
            'sma_20': 50,
            'sma_50': 50,
            'sma_200': 50  # Sideways: SMAs equal
        }
        regime = self.generator.generate_market_regime(indicators)

        assert regime.regime == "sideways"

    def test_sideways_uptrend_with_weakening_momentum(self):
        """Test that uptrend with weakening momentum becomes sideways"""
        indicators = {
            'rsi': 55,
            'macd': -0.5,
            'macd_signal': -0.3,  # Negative MACD below signal = weakening
            'current_price': 55,
            'sma_20': 52,
            'sma_50': 50,
            'sma_200': 48  # Uptrend but momentum weakening
        }
        regime = self.generator.generate_market_regime(indicators)

        assert regime.regime == "sideways"  # Uptrend + weakening = sideways

    def test_sideways_downtrend_with_strengthening_momentum(self):
        """Test that downtrend with strengthening momentum becomes sideways"""
        indicators = {
            'rsi': 45,
            'macd': 0.5,
            'macd_signal': 0.3,  # Positive MACD above signal = strengthening
            'current_price': 45,
            'sma_20': 48,
            'sma_50': 50,
            'sma_200': 52  # Downtrend but momentum strengthening
        }
        regime = self.generator.generate_market_regime(indicators)

        assert regime.regime == "sideways"  # Downtrend + strengthening = sideways

    def test_market_regime_to_dict(self):
        """Verify MarketRegime converts to dict correctly"""
        regime = MarketRegime(regime="bull")
        result = regime.to_dict()

        assert isinstance(result, dict)
        assert result['regime'] == "bull"


class TestDivergenceSignal:
    """Test RSI-price divergence detection"""

    def setup_method(self):
        self.generator = SemanticStateGenerator()

    def test_bullish_divergence_price_down_rsi_up(self):
        """Test bullish divergence: price falling but RSI rising"""
        indicators = {'rsi': 45, 'macd': 0, 'macd_signal': 0, 'current_price': 92, 'sma_20': 95, 'sma_50': 98, 'sma_200': 100}
        price_history = [100, 98, 95, 92]  # Price falling
        rsi_history = [30, 35, 40, 45]     # RSI rising

        divergence = self.generator.generate_divergence_signal(indicators, price_history, rsi_history)

        assert divergence.signal == "bullish_divergence"

    def test_bearish_divergence_price_up_rsi_down(self):
        """Test bearish divergence: price rising but RSI falling"""
        indicators = {'rsi': 55, 'macd': 0, 'macd_signal': 0, 'current_price': 98, 'sma_20': 95, 'sma_50': 92, 'sma_200': 90}
        price_history = [90, 92, 95, 98]  # Price rising
        rsi_history = [70, 65, 60, 55]    # RSI falling

        divergence = self.generator.generate_divergence_signal(indicators, price_history, rsi_history)

        assert divergence.signal == "bearish_divergence"

    def test_no_divergence_both_rising(self):
        """Test no divergence when both price and RSI rising"""
        indicators = {'rsi': 65, 'macd': 0, 'macd_signal': 0, 'current_price': 105, 'sma_20': 100, 'sma_50': 95, 'sma_200': 90}
        price_history = [95, 98, 102, 105]  # Price rising
        rsi_history = [50, 55, 60, 65]      # RSI rising

        divergence = self.generator.generate_divergence_signal(indicators, price_history, rsi_history)

        assert divergence.signal == "no_divergence"

    def test_no_divergence_both_falling(self):
        """Test no divergence when both price and RSI falling"""
        indicators = {'rsi': 35, 'macd': 0, 'macd_signal': 0, 'current_price': 90, 'sma_20': 95, 'sma_50': 98, 'sma_200': 100}
        price_history = [105, 100, 95, 90]  # Price falling
        rsi_history = [65, 55, 45, 35]      # RSI falling

        divergence = self.generator.generate_divergence_signal(indicators, price_history, rsi_history)

        assert divergence.signal == "no_divergence"

    def test_no_history_defaults_to_no_divergence(self):
        """Test that missing history returns no_divergence (conservative default)"""
        indicators = {'rsi': 50, 'macd': 0, 'macd_signal': 0, 'current_price': 100}

        # No history provided
        divergence = self.generator.generate_divergence_signal(indicators)
        assert divergence.signal == "no_divergence"

        # Empty history
        divergence = self.generator.generate_divergence_signal(indicators, [], [])
        assert divergence.signal == "no_divergence"

        # Insufficient history (need at least 2)
        divergence = self.generator.generate_divergence_signal(indicators, [100], [50])
        assert divergence.signal == "no_divergence"

    def test_divergence_signal_to_dict(self):
        """Verify DivergenceSignal converts to dict correctly"""
        divergence = DivergenceSignal(signal="bullish_divergence")
        result = divergence.to_dict()

        assert isinstance(result, dict)
        assert result['signal'] == "bullish_divergence"
