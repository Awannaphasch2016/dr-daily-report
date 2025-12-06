# -*- coding: utf-8 -*-
"""
User-Facing Investment Scorer

Calculates 6 investment decision scores (0-10 scale) for non-technical users:
1. Fundamental Score - Company financial health
2. Technical Score - Price momentum and trends
3. Liquidity Score - Trading volume activity
4. Valuation Score - Price vs intrinsic value
5. Selling Pressure Score - Market buying/selling dynamics (VWAP-based)
6. Uncertainty Score - Market stability/volatility (inverted)
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class UserFacingScorer:
    """Calculate user-facing investment scores (0-10 scale)"""

    def calculate_fundamental_score(
        self,
        ticker_data: Dict[str, Any],
        percentiles: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate fundamental score based on company financials

        Weights: Valuation 30% + Growth 30% + Profitability 40%

        Args:
            ticker_data: Dict with 'info' key containing financial data
            percentiles: Dict with 'pe_percentile' key

        Returns:
            Dict with score, category, rationale
        """
        info = ticker_data.get('info', {})

        # Extract metrics with defaults
        pe = info.get('trailingPE', None)
        pe_percentile = percentiles.get('pe_percentile', 50)
        revenue_growth = info.get('revenueGrowth', None)
        profit_margin = info.get('profitMargins', None)
        roe = info.get('returnOnEquity', None)

        # Check for missing data
        if all(v is None for v in [pe, revenue_growth, profit_margin, roe]):
            return {
                'score': 5.0,
                'category': 'Fundamental',
                'rationale': 'Insufficient fundamental data available'
            }

        # Calculate component scores
        # Valuation: Lower P/E percentile = better value
        valuation_score = (100 - pe_percentile) / 10 if pe_percentile is not None else 5.0

        # Growth: 50% revenue growth = 10/10
        if revenue_growth is not None:
            growth_score = min(max(revenue_growth * 20, 0), 10)  # Scale: 0.5 (50%) → 10
        else:
            growth_score = 5.0

        # Profit Margin: 30% margin = 10/10
        if profit_margin is not None:
            margin_score = min(max(profit_margin * 33.33, 0), 10)  # Scale: 0.3 (30%) → 10
        else:
            margin_score = 5.0

        # ROE: 20% ROE = 10/10
        if roe is not None:
            roe_score = min(max(roe * 50, 0), 10)  # Scale: 0.2 (20%) → 10
        else:
            roe_score = 5.0

        # Weighted average
        profitability_score = (margin_score + roe_score) / 2
        final_score = (valuation_score * 0.3) + (growth_score * 0.3) + (profitability_score * 0.4)

        # Clamp to 0-10
        final_score = max(0, min(10, final_score))

        # Generate rationale
        if final_score >= 7:
            rationale = f"Strong fundamentals: {int(revenue_growth * 100) if revenue_growth else 'N/A'}% growth, {int(profit_margin * 100) if profit_margin else 'N/A'}% margin"
        elif final_score >= 4:
            rationale = "Moderate fundamental strength"
        else:
            rationale = "Weak fundamentals: low growth or margins"

        return {
            'score': round(final_score, 1),
            'category': 'Fundamental',
            'rationale': rationale
        }

    def calculate_technical_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate technical score based on price trends and momentum

        Weights: Trend 50% + Momentum 30% + MACD 20%

        Args:
            indicators: Dict with price, SMA, RSI, MACD data

        Returns:
            Dict with score, category, rationale
        """
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        sma_200 = indicators.get('sma_200', 0)
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)

        # Trend Score (50%): Check SMA alignment
        trend_score = 0
        if current_price > sma_20 > sma_50 > sma_200:
            trend_score = 10  # Perfect bullish alignment
        elif current_price > sma_20 > sma_50:
            trend_score = 7  # Strong bullish
        elif current_price > sma_20:
            trend_score = 5  # Moderate bullish
        elif current_price < sma_20 < sma_50 < sma_200:
            trend_score = 0  # Perfect bearish alignment
        elif current_price < sma_20 < sma_50:
            trend_score = 3  # Strong bearish
        else:
            trend_score = 5  # Mixed/neutral

        # Momentum Score (30%): RSI-based
        if rsi < 30:
            momentum_score = 8  # Oversold = buying opportunity
        elif 30 <= rsi < 40:
            momentum_score = 6
        elif 40 <= rsi <= 60:
            momentum_score = 5  # Neutral
        elif 60 < rsi <= 70:
            momentum_score = 6
        elif rsi > 70:
            momentum_score = 3  # Overbought = caution
        else:
            momentum_score = 5

        # MACD Score (20%)
        if macd > macd_signal and macd > 0:
            macd_score = 8  # Bullish crossover
        elif macd > macd_signal:
            macd_score = 6  # Bullish but negative
        elif macd < macd_signal and macd < 0:
            macd_score = 2  # Bearish crossover
        else:
            macd_score = 5  # Neutral

        # Weighted average
        final_score = (trend_score * 0.5) + (momentum_score * 0.3) + (macd_score * 0.2)

        # Clamp to 0-10
        final_score = max(0, min(10, final_score))

        # Generate rationale
        if final_score >= 7:
            rationale = "Bullish technical signals: uptrend with strong momentum"
        elif final_score >= 4:
            rationale = "Mixed technical signals"
        else:
            rationale = "Bearish technical signals: downtrend or weak momentum"

        return {
            'score': round(final_score, 1),
            'category': 'Technical',
            'rationale': rationale
        }

    def calculate_liquidity_score(
        self,
        indicators: Dict[str, Any],
        percentiles: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate liquidity score based on trading volume

        Weights: Recent ratio 60% + Historical percentile 40%

        Args:
            indicators: Dict with volume, volume_sma
            percentiles: Dict with volume_percentile

        Returns:
            Dict with score, category, rationale
        """
        volume = indicators.get('volume', 0)
        volume_sma = indicators.get('volume_sma', 1)  # Avoid division by zero
        volume_percentile = percentiles.get('volume_percentile', 50)

        # Calculate volume ratio
        volume_ratio = volume / volume_sma if volume_sma > 0 else 1.0

        # Ratio score: 2x volume = 10/10, 0.7x = 2/10
        if volume_ratio >= 2.0:
            ratio_score = 10
        elif volume_ratio >= 1.5:
            ratio_score = 8
        elif volume_ratio >= 1.0:
            ratio_score = 6
        elif volume_ratio >= 0.7:
            ratio_score = 4
        else:
            ratio_score = 2

        # Percentile score
        percentile_score = volume_percentile / 10  # 90th percentile = 9/10

        # Weighted average
        final_score = (ratio_score * 0.6) + (percentile_score * 0.4)

        # Clamp to 0-10
        final_score = max(0, min(10, final_score))

        # Generate rationale
        if final_score >= 7:
            rationale = f"High liquidity: {volume_ratio:.1f}x average volume"
        elif final_score >= 4:
            rationale = "Normal trading volume"
        else:
            rationale = f"Low liquidity: {volume_ratio:.1f}x average volume"

        return {
            'score': round(final_score, 1),
            'category': 'Liquidity',
            'rationale': rationale
        }

    def calculate_valuation_score(
        self,
        ticker_data: Dict[str, Any],
        percentiles: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate valuation score based on price multiples

        Weights: P/E 40% + P/B 30% + EV/EBITDA 30% + Dividend bonus (+2 max)

        Args:
            ticker_data: Dict with 'info' containing P/E, P/B, dividend data
            percentiles: Dict with pe_percentile, pb_percentile

        Returns:
            Dict with score, category, rationale
        """
        info = ticker_data.get('info', {})
        pe_percentile = percentiles.get('pe_percentile', 50)
        pb_percentile = percentiles.get('pb_percentile', 50)
        dividend_yield = info.get('dividendYield', 0.0)

        # Lower percentiles = better value = higher score
        pe_score = (100 - pe_percentile) / 10 if pe_percentile is not None else 5.0
        pb_score = (100 - pb_percentile) / 10 if pb_percentile is not None else 5.0

        # Weighted average (simplified: P/E 40%, P/B 30%, assume EV/EBITDA = P/B for now)
        base_score = (pe_score * 0.4) + (pb_score * 0.6)

        # Dividend bonus: 0-6% yield → 0-2 bonus points
        dividend_bonus = min((dividend_yield or 0) * 33.33, 2)  # 6% yield = 2 bonus

        final_score = base_score + dividend_bonus

        # Clamp to 0-10
        final_score = max(0, min(10, final_score))

        # Generate rationale
        if final_score >= 7:
            rationale = f"Undervalued: low multiples{', high dividend' if dividend_yield and dividend_yield > 0.03 else ''}"
        elif final_score >= 4:
            rationale = "Fair valuation"
        else:
            rationale = "Overvalued: high multiples"

        return {
            'score': round(final_score, 1),
            'category': 'Valuation',
            'rationale': rationale
        }

    def calculate_selling_pressure_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate selling pressure score using VWAP

        Uses existing MarketAnalyzer VWAP logic from src/analysis/market_analyzer.py:57

        Args:
            indicators: Dict with current_price, vwap

        Returns:
            Dict with score, category, rationale
        """
        current_price = indicators.get('current_price', 0)
        vwap = indicators.get('vwap', current_price)  # Default to current price if missing

        if vwap == 0:
            return {
                'score': 5.0,
                'category': 'Selling Pressure',
                'rationale': 'VWAP data unavailable'
            }

        # Calculate price vs VWAP percentage
        price_vs_vwap_pct = ((current_price - vwap) / vwap) * 100

        # Score based on VWAP position (from plan)
        if price_vs_vwap_pct > 3:
            score = 9  # Strong buying
            rationale = f"Strong buying pressure: price {price_vs_vwap_pct:.1f}% above VWAP"
        elif price_vs_vwap_pct > 1:
            score = 7  # Moderate buying
            rationale = f"Moderate buying pressure: price {price_vs_vwap_pct:.1f}% above VWAP"
        elif price_vs_vwap_pct > -1:
            score = 5  # Balanced
            rationale = "Balanced market: price near VWAP"
        elif price_vs_vwap_pct > -3:
            score = 3  # Moderate selling
            rationale = f"Moderate selling pressure: price {abs(price_vs_vwap_pct):.1f}% below VWAP"
        else:
            score = 1  # Strong selling
            rationale = f"Strong selling pressure: price {abs(price_vs_vwap_pct):.1f}% below VWAP"

        return {
            'score': float(score),
            'category': 'Selling Pressure',
            'rationale': rationale
        }

    def calculate_uncertainty_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate uncertainty score from existing uncertainty_score (0-100)

        Converts to 0-10 scale with INVERSION: low uncertainty = high score

        Source: src/analysis/technical_analysis.py - combines ATR volatility + VWAP variance

        Args:
            indicators: Dict with uncertainty_score (0-100)

        Returns:
            Dict with score, category, rationale
        """
        uncertainty_score = indicators.get('uncertainty_score', None)

        if uncertainty_score is None:
            return {
                'score': 5.0,
                'category': 'Uncertainty',
                'rationale': 'Uncertainty data unavailable'
            }

        # Convert 0-100 to 0-10 scale (INVERTED)
        # Formula: score = 10 - (uncertainty_score / 10)
        # 0 uncertainty → 10 score, 100 uncertainty → 0 score
        converted_score = 10 - (uncertainty_score / 10)

        # Clamp to 0-10
        converted_score = max(0, min(10, converted_score))

        # Generate rationale based on uncertainty levels
        if uncertainty_score < 25:
            rationale = f"Very stable market (uncertainty: {uncertainty_score:.0f}/100)"
        elif uncertainty_score < 50:
            rationale = f"Moderately stable market (uncertainty: {uncertainty_score:.0f}/100)"
        elif uncertainty_score < 75:
            rationale = f"Volatile market (uncertainty: {uncertainty_score:.0f}/100)"
        else:
            rationale = f"Extremely volatile/unstable market (uncertainty: {uncertainty_score:.0f}/100)"

        return {
            'score': round(converted_score, 1),
            'category': 'Uncertainty',
            'rationale': rationale
        }

    def calculate_all_scores(
        self,
        ticker_data: Dict[str, Any],
        indicators: Dict[str, Any],
        percentiles: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate all 6 user-facing investment scores

        Args:
            ticker_data: Dict with ticker info (from yfinance)
            indicators: Dict with technical indicators
            percentiles: Dict with percentile rankings

        Returns:
            Dict mapping category name to score dict
            {
                'Fundamental': {'score': 7.5, 'category': 'Fundamental', 'rationale': '...'},
                'Technical': {...},
                ...
            }
        """
        scores = {}

        try:
            scores['Fundamental'] = self.calculate_fundamental_score(ticker_data, percentiles)
        except Exception as e:
            logger.warning(f"Failed to calculate fundamental score: {e}")
            scores['Fundamental'] = {'score': 5.0, 'category': 'Fundamental', 'rationale': 'Calculation error'}

        try:
            scores['Technical'] = self.calculate_technical_score(indicators)
        except Exception as e:
            logger.warning(f"Failed to calculate technical score: {e}")
            scores['Technical'] = {'score': 5.0, 'category': 'Technical', 'rationale': 'Calculation error'}

        try:
            scores['Liquidity'] = self.calculate_liquidity_score(indicators, percentiles)
        except Exception as e:
            logger.warning(f"Failed to calculate liquidity score: {e}")
            scores['Liquidity'] = {'score': 5.0, 'category': 'Liquidity', 'rationale': 'Calculation error'}

        try:
            scores['Valuation'] = self.calculate_valuation_score(ticker_data, percentiles)
        except Exception as e:
            logger.warning(f"Failed to calculate valuation score: {e}")
            scores['Valuation'] = {'score': 5.0, 'category': 'Valuation', 'rationale': 'Calculation error'}

        try:
            scores['Selling Pressure'] = self.calculate_selling_pressure_score(indicators)
        except Exception as e:
            logger.warning(f"Failed to calculate selling pressure score: {e}")
            scores['Selling Pressure'] = {'score': 5.0, 'category': 'Selling Pressure', 'rationale': 'Calculation error'}

        try:
            scores['Uncertainty'] = self.calculate_uncertainty_score(indicators)
        except Exception as e:
            logger.warning(f"Failed to calculate uncertainty score: {e}")
            scores['Uncertainty'] = {'score': 5.0, 'category': 'Uncertainty', 'rationale': 'Calculation error'}

        logger.info(f"✅ Calculated all 6 user-facing scores")
        return scores
