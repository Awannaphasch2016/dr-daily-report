"""Semantic state generator: Converts numeric indicators to semantic tokens

This implements Layer 2 of the three-layer architecture:
  Layer 1 (Code): Numeric calculations, ground truth
  Layer 2 (Code): Semantic state classification ← THIS MODULE
  Layer 3 (LLM): Narrative synthesis constrained by states

Research basis:
- https://arxiv.org/html/2512.13040 (FinFRE-RAG semantic serialization)
- https://www.moduleq.com/blog/how-new-prompting-techniques-increase-llm-accuracy-in-financial-applications
- https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms

Core principle: Code decides what numbers MEAN, LLM decides how meanings COMBINE.
"""

from typing import Dict, Literal, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class RiskRegime:
    """Risk assessment semantic state

    Represents market risk conditions using categorical labels instead of numeric thresholds.
    These states constrain LLM narrative generation.
    """
    uncertainty_state: Literal["stable", "moderate", "high_risk", "extreme"]
    volatility_regime: Literal["low", "moderate", "high", "extreme"]
    pressure_direction: Literal["strong_buying", "buying", "neutral", "selling", "strong_selling"]
    volume_confidence: Literal["very_low", "low", "normal", "high", "very_high"]

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for template injection"""
        return asdict(self)


@dataclass
class MomentumState:
    """Momentum indicator semantic state

    Captures directional signals and zones without exposing raw numeric values to LLM.
    """
    rsi_zone: Literal["oversold", "approaching_oversold", "neutral", "approaching_overbought", "overbought"]
    macd_signal: Literal["strong_bearish", "bearish", "neutral", "bullish", "strong_bullish"]
    momentum_direction: Literal["strengthening", "stable", "weakening"]

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for template injection"""
        return asdict(self)


@dataclass
class TrendState:
    """Trend indicator semantic state

    Represents trend alignment and price positioning relative to moving averages.
    """
    sma_alignment: Literal["strong_uptrend", "uptrend", "sideways", "downtrend", "strong_downtrend"]
    price_vs_sma: Literal["far_above", "above", "at", "below", "far_below"]

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for template injection"""
        return asdict(self)


@dataclass
class MarketRegime:
    """Top-level market regime classification

    Derived from SMA alignment + momentum direction for clearer LLM guidance.
    Simplifies LLM's interpretive burden by providing explicit regime label.

    States:
    - bull: Sustained uptrend with supporting momentum
    - bear: Sustained downtrend with confirming momentum
    - sideways: Mixed signals, range-bound market
    """
    regime: Literal["bull", "bear", "sideways"]

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for template injection"""
        return asdict(self)


@dataclass
class DivergenceSignal:
    """RSI-Price divergence detection

    Divergence is a leading indicator where price and RSI move in opposite directions.
    - Bullish divergence: Price makes lower lows, RSI makes higher lows (hidden strength)
    - Bearish divergence: Price makes higher highs, RSI makes lower highs (hidden weakness)
    - No divergence: Price and RSI moving in same direction
    """
    signal: Literal["bullish_divergence", "bearish_divergence", "no_divergence"]

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for template injection"""
        return asdict(self)


@dataclass
class SemanticStates:
    """Container for all semantic states

    Aggregates all Layer 2 semantic classifications for a ticker.
    """
    risk: RiskRegime
    momentum: MomentumState
    trend: TrendState
    market_regime: MarketRegime
    divergence: DivergenceSignal

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """Convert to nested dictionary for template injection"""
        return {
            'risk': self.risk.to_dict(),
            'momentum': self.momentum.to_dict(),
            'trend': self.trend.to_dict(),
            'market_regime': self.market_regime.to_dict(),
            'divergence': self.divergence.to_dict()
        }


class SemanticStateGenerator:
    """Converts numeric indicators to semantic states (Layer 1 → Layer 2)

    Design principle: Code decides what numbers MEAN, LLM decides how meanings COMBINE

    This class implements the semantic layer architecture where:
    - Numeric thresholds are encapsulated in code (deterministic, testable)
    - LLM receives only semantic labels (no number leakage)
    - State transitions are explicit and documented

    Research shows semantic layers improve LLM accuracy by 300% in financial applications
    by pre-computing business logic and preventing numeric hallucinations.
    """

    def generate_all_states(
        self,
        ground_truth: Dict,
        indicators: Dict,
        price_history: list = None,
        rsi_history: list = None
    ) -> SemanticStates:
        """Generate all semantic states from numeric data

        Args:
            ground_truth: Calculated market conditions (uncertainty, atr_pct, vwap_pct, volume_ratio)
            indicators: Technical indicators (rsi, macd, sma, etc.)
            price_history: Optional list of recent prices for divergence detection
            rsi_history: Optional list of recent RSI values for divergence detection

        Returns:
            SemanticStates: Complete semantic state classification

        Example:
            >>> generator = SemanticStateGenerator()
            >>> states = generator.generate_all_states(
            ...     ground_truth={'uncertainty_score': 35, 'atr_pct': 1.2, 'vwap_pct': 3.5, 'volume_ratio': 1.8},
            ...     indicators={'rsi': 65, 'macd': 0.45, 'macd_signal': 0.3, 'current_price': 50, 'sma_20': 48, 'sma_50': 45, 'sma_200': 42}
            ... )
            >>> states.risk.uncertainty_state
            'moderate'
            >>> states.momentum.rsi_zone
            'approaching_overbought'
            >>> states.market_regime.regime
            'bull'
        """
        risk = self.generate_risk_regime(ground_truth)
        momentum = self.generate_momentum_state(indicators)
        trend = self.generate_trend_state(indicators)
        market_regime = self.generate_market_regime(indicators)
        divergence = self.generate_divergence_signal(indicators, price_history, rsi_history)

        return SemanticStates(
            risk=risk,
            momentum=momentum,
            trend=trend,
            market_regime=market_regime,
            divergence=divergence
        )

    def generate_risk_regime(self, ground_truth: Dict) -> RiskRegime:
        """Convert risk metrics to semantic states

        Research basis: Directional constraints instead of numeric constraints

        Thresholds are based on percentile analysis of historical data:
        - uncertainty_score: 0-100 scale (MarketAnalyzer calculation)
        - atr_pct: Percentage volatility (<1% low, >3% high)
        - vwap_pct: Price vs VWAP percentage (±5% strong zones)
        - volume_ratio: Volume vs 20-day average (1.5x+ high, 0.5x- low)

        Args:
            ground_truth: Dict with keys: uncertainty_score, atr_pct, vwap_pct, volume_ratio

        Returns:
            RiskRegime: Categorical risk assessment
        """
        uncertainty = ground_truth.get('uncertainty_score', 0)
        atr_pct = ground_truth.get('atr_pct', 0)
        vwap_pct = ground_truth.get('vwap_pct', 0)
        volume_ratio = ground_truth.get('volume_ratio', 0)

        # Uncertainty state (0-100 scale)
        # Based on percentile thresholds: 25th, 50th, 75th percentiles
        if uncertainty < 25:
            uncertainty_state = "stable"
        elif uncertainty < 50:
            uncertainty_state = "moderate"
        elif uncertainty < 75:
            uncertainty_state = "high_risk"
        else:
            uncertainty_state = "extreme"

        # Volatility regime (ATR as % of price)
        # Thresholds based on SET market volatility distribution
        if atr_pct < 1.0:
            volatility_regime = "low"
        elif atr_pct < 2.0:
            volatility_regime = "moderate"
        elif atr_pct < 3.0:
            volatility_regime = "high"
        else:
            volatility_regime = "extreme"

        # Pressure direction (price vs VWAP)
        # ±1% = noise, ±5% = significant pressure
        if vwap_pct > 5:
            pressure_direction = "strong_buying"
        elif vwap_pct > 1:
            pressure_direction = "buying"
        elif vwap_pct > -1:
            pressure_direction = "neutral"
        elif vwap_pct > -5:
            pressure_direction = "selling"
        else:
            pressure_direction = "strong_selling"

        # Volume confidence (volume ratio vs 20-day average)
        # <0.5x = very low interest, >2x = very high interest
        if volume_ratio < 0.5:
            volume_confidence = "very_low"
        elif volume_ratio < 0.8:
            volume_confidence = "low"
        elif volume_ratio < 1.5:
            volume_confidence = "normal"
        elif volume_ratio < 2.0:
            volume_confidence = "high"
        else:
            volume_confidence = "very_high"

        return RiskRegime(
            uncertainty_state=uncertainty_state,
            volatility_regime=volatility_regime,
            pressure_direction=pressure_direction,
            volume_confidence=volume_confidence
        )

    def generate_momentum_state(self, indicators: Dict) -> MomentumState:
        """Convert momentum indicators to semantic states

        Momentum is classified into zones and directional signals:
        - RSI zones: Standard 30/70 oversold/overbought with 40/60 approach zones
        - MACD signal: MACD vs Signal line differential
        - Direction: Derived from MACD trend

        Args:
            indicators: Dict with keys: rsi, macd, macd_signal

        Returns:
            MomentumState: Categorical momentum assessment
        """
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)

        # RSI zone (standard technical analysis zones)
        # 30/70 = oversold/overbought, 40/60 = approaching zones
        if rsi < 30:
            rsi_zone = "oversold"
        elif rsi < 40:
            rsi_zone = "approaching_oversold"
        elif rsi < 60:
            rsi_zone = "neutral"
        elif rsi < 70:
            rsi_zone = "approaching_overbought"
        else:
            rsi_zone = "overbought"

        # MACD signal (MACD vs Signal line)
        # Positive differential = bullish, negative = bearish
        macd_diff = macd - macd_signal
        if macd_diff < -0.5:
            macd_signal_state = "strong_bearish"
        elif macd_diff < 0:
            macd_signal_state = "bearish"
        elif macd_diff < 0.5:
            macd_signal_state = "neutral"
        elif macd_diff < 1.0:
            macd_signal_state = "bullish"
        else:
            macd_signal_state = "strong_bullish"

        # Momentum direction (derived from MACD trend)
        # Positive MACD above signal = strengthening
        # Negative MACD below signal = weakening
        if macd > 0 and macd > macd_signal:
            momentum_direction = "strengthening"
        elif macd < 0 and macd < macd_signal:
            momentum_direction = "weakening"
        else:
            momentum_direction = "stable"

        return MomentumState(
            rsi_zone=rsi_zone,
            macd_signal=macd_signal_state,
            momentum_direction=momentum_direction
        )

    def generate_trend_state(self, indicators: Dict) -> TrendState:
        """Convert trend indicators to semantic states

        Trend is determined by SMA alignment (golden cross/death cross patterns)
        and price positioning relative to key moving averages.

        SMA Alignment Rules:
        - strong_uptrend: SMA20 > SMA50 > SMA200 (classic golden cross)
        - uptrend: SMA20 > SMA50 (partial golden cross)
        - strong_downtrend: SMA20 < SMA50 < SMA200 (classic death cross)
        - downtrend: SMA20 < SMA50 (partial death cross)
        - sideways: Mixed signals

        Args:
            indicators: Dict with keys: current_price, sma_20, sma_50, sma_200

        Returns:
            TrendState: Categorical trend assessment
        """
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        sma_200 = indicators.get('sma_200', 0)

        # SMA alignment (golden cross / death cross detection)
        # Strong trends require all three SMAs aligned
        if sma_20 > sma_50 > sma_200:
            sma_alignment = "strong_uptrend"
        elif sma_20 > sma_50:
            sma_alignment = "uptrend"
        elif sma_20 < sma_50 < sma_200:
            sma_alignment = "strong_downtrend"
        elif sma_20 < sma_50:
            sma_alignment = "downtrend"
        else:
            sma_alignment = "sideways"

        # Price vs SMA 20 (short-term trend reference)
        # ±1% = at SMA, ±5% = far from SMA
        if not sma_20 or sma_20 == 0:
            price_vs_sma = "at"
        else:
            diff_pct = ((current_price - sma_20) / sma_20) * 100
            if diff_pct > 5:
                price_vs_sma = "far_above"
            elif diff_pct > 1:
                price_vs_sma = "above"
            elif diff_pct > -1:
                price_vs_sma = "at"
            elif diff_pct > -5:
                price_vs_sma = "below"
            else:
                price_vs_sma = "far_below"

        return TrendState(
            sma_alignment=sma_alignment,
            price_vs_sma=price_vs_sma
        )

    def generate_market_regime(self, indicators: Dict) -> MarketRegime:
        """Top-level market regime classification

        Derives from SMA alignment + momentum direction for clearer LLM guidance.
        This is a higher-order semantic state that simplifies regime identification.

        Classification Rules:
        - bull: Uptrend alignment + non-weakening momentum
        - bear: Downtrend alignment + non-strengthening momentum
        - sideways: Mixed signals or transitional state

        Args:
            indicators: Dict with SMA and momentum data

        Returns:
            MarketRegime: Single regime classification
        """
        # Get component states
        trend = self.generate_trend_state(indicators)
        momentum = self.generate_momentum_state(indicators)

        # Derive regime from components
        if trend.sma_alignment in ("strong_uptrend", "uptrend") and momentum.momentum_direction != "weakening":
            regime = "bull"
        elif trend.sma_alignment in ("strong_downtrend", "downtrend") and momentum.momentum_direction != "strengthening":
            regime = "bear"
        else:
            regime = "sideways"

        return MarketRegime(regime=regime)

    def generate_divergence_signal(
        self,
        indicators: Dict,
        price_history: list = None,
        rsi_history: list = None
    ) -> DivergenceSignal:
        """Detect RSI-price divergence patterns

        Divergence detection requires historical data to compare trends.
        If history not available, returns no_divergence (conservative default).

        Divergence Types:
        - Bullish divergence: Price down, RSI up (hidden strength)
        - Bearish divergence: Price up, RSI down (hidden weakness)
        - No divergence: Price and RSI moving in same direction

        Args:
            indicators: Dict with current rsi and price
            price_history: Last N prices (optional, at least 2 needed)
            rsi_history: Last N RSI values (optional, at least 2 needed)

        Returns:
            DivergenceSignal: Divergence classification
        """
        # Default to no divergence if history not available
        if not price_history or not rsi_history or len(price_history) < 2 or len(rsi_history) < 2:
            return DivergenceSignal(signal="no_divergence")

        # Compare recent trends (last 2 data points)
        price_rising = price_history[-1] > price_history[-2]
        rsi_rising = rsi_history[-1] > rsi_history[-2]

        # Divergence detection
        if price_rising and not rsi_rising:
            # Price up, RSI down = bearish divergence (weakness)
            signal = "bearish_divergence"
        elif not price_rising and rsi_rising:
            # Price down, RSI up = bullish divergence (hidden strength)
            signal = "bullish_divergence"
        else:
            signal = "no_divergence"

        return DivergenceSignal(signal=signal)
