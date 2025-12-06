# -*- coding: utf-8 -*-
"""
Tests for UserFacingScorer - Investment decision scores (0-10 scale)

TDD: Write tests first, then implement scoring logic
"""
import pytest
from src.scoring.user_facing_scorer import UserFacingScorer


class TestFundamentalScore:
    """Test fundamental score calculation (0-10 scale)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_perfect_fundamentals_scores_high(self):
        """Strong fundamentals should score 8-10"""
        ticker_data = {
            'info': {
                'trailingPE': 15.0,  # Good P/E
                'revenueGrowth': 0.50,  # 50% growth
                'profitMargins': 0.30,  # 30% margin
                'returnOnEquity': 0.20,  # 20% ROE
            }
        }
        percentiles = {'pe_percentile': 30}  # Low P/E percentile = good value

        result = self.scorer.calculate_fundamental_score(ticker_data, percentiles)

        assert isinstance(result, dict), "Should return dict"
        assert 'score' in result, "Should have score key"
        assert 'category' in result, "Should have category key"
        assert 'rationale' in result, "Should have rationale key"
        assert result['category'] == 'Fundamental'
        assert 8 <= result['score'] <= 10, f"Strong fundamentals should score 8-10, got {result['score']}"

    def test_poor_fundamentals_scores_low(self):
        """Weak fundamentals should score 0-3"""
        ticker_data = {
            'info': {
                'trailingPE': 50.0,  # High P/E (expensive)
                'revenueGrowth': -0.10,  # Negative growth
                'profitMargins': 0.05,  # 5% margin (weak)
                'returnOnEquity': 0.05,  # 5% ROE (weak)
            }
        }
        percentiles = {'pe_percentile': 90}  # High P/E percentile = expensive

        result = self.scorer.calculate_fundamental_score(ticker_data, percentiles)

        assert 0 <= result['score'] <= 3, f"Weak fundamentals should score 0-3, got {result['score']}"

    def test_missing_data_returns_neutral_score(self):
        """Missing fundamental data should return ~5 (neutral)"""
        ticker_data = {'info': {}}
        percentiles = {}

        result = self.scorer.calculate_fundamental_score(ticker_data, percentiles)

        assert 4 <= result['score'] <= 6, "Missing data should score neutral (~5)"
        assert 'insufficient' in result['rationale'].lower() or 'data' in result['rationale'].lower()

    def test_score_stays_within_bounds(self):
        """Score should never exceed 0-10 range"""
        # Extreme values
        ticker_data = {
            'info': {
                'trailingPE': 1.0,  # Extremely low
                'revenueGrowth': 2.0,  # 200% growth (extreme)
                'profitMargins': 0.80,  # 80% margin (extreme)
                'returnOnEquity': 0.50,  # 50% ROE (extreme)
            }
        }
        percentiles = {'pe_percentile': 1}

        result = self.scorer.calculate_fundamental_score(ticker_data, percentiles)

        assert 0 <= result['score'] <= 10, f"Score must be 0-10, got {result['score']}"


class TestTechnicalScore:
    """Test technical score calculation (0-10 scale)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_bullish_technicals_scores_high(self):
        """Bullish SMA alignment + strong momentum should score 8-10"""
        indicators = {
            'current_price': 150.0,
            'sma_20': 145.0,
            'sma_50': 140.0,
            'sma_200': 130.0,
            'rsi': 65.0,  # Healthy, not overbought
            'macd': 2.0,
            'macd_signal': 1.5,  # MACD > signal (bullish)
        }

        result = self.scorer.calculate_technical_score(indicators)

        assert result['category'] == 'Technical'
        assert 8 <= result['score'] <= 10, f"Bullish technicals should score 8-10, got {result['score']}"

    def test_bearish_technicals_scores_low(self):
        """Bearish SMA alignment + weak momentum should score 0-3"""
        indicators = {
            'current_price': 130.0,
            'sma_20': 140.0,
            'sma_50': 145.0,
            'sma_200': 150.0,
            'rsi': 25.0,  # Oversold
            'macd': -2.0,
            'macd_signal': -1.0,  # MACD < signal (bearish)
        }

        result = self.scorer.calculate_technical_score(indicators)

        assert 0 <= result['score'] <= 3, f"Bearish technicals should score 0-3, got {result['score']}"

    def test_rsi_overbought_penalty(self):
        """RSI > 70 should reduce score"""
        indicators_normal = {
            'current_price': 150.0,
            'sma_20': 145.0,
            'sma_50': 140.0,
            'sma_200': 130.0,
            'rsi': 65.0,
            'macd': 2.0,
            'macd_signal': 1.5,
        }

        indicators_overbought = indicators_normal.copy()
        indicators_overbought['rsi'] = 80.0  # Overbought

        score_normal = self.scorer.calculate_technical_score(indicators_normal)['score']
        score_overbought = self.scorer.calculate_technical_score(indicators_overbought)['score']

        assert score_overbought < score_normal, "Overbought RSI should reduce score"

    def test_rsi_oversold_bonus(self):
        """RSI < 30 should increase score (buying opportunity)"""
        indicators_normal = {
            'current_price': 150.0,
            'sma_20': 145.0,
            'sma_50': 140.0,
            'sma_200': 130.0,
            'rsi': 50.0,
            'macd': 1.0,
            'macd_signal': 0.5,
        }

        indicators_oversold = indicators_normal.copy()
        indicators_oversold['rsi'] = 25.0  # Oversold

        score_normal = self.scorer.calculate_technical_score(indicators_normal)['score']
        score_oversold = self.scorer.calculate_technical_score(indicators_oversold)['score']

        assert score_oversold > score_normal, "Oversold RSI should increase score (buying opportunity)"


class TestLiquidityScore:
    """Test liquidity score calculation (0-10 scale)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_high_volume_scores_high(self):
        """2x average volume should score ~10"""
        indicators = {
            'volume': 2000000,
            'volume_sma': 1000000,  # 2x volume ratio
        }
        percentiles = {'volume_percentile': 90}

        result = self.scorer.calculate_liquidity_score(indicators, percentiles)

        assert result['category'] == 'Liquidity'
        assert result['score'] >= 8, f"High volume should score >=8, got {result['score']}"

    def test_low_volume_scores_low(self):
        """<0.7x average volume should score <=3"""
        indicators = {
            'volume': 500000,
            'volume_sma': 1000000,  # 0.5x volume ratio
        }
        percentiles = {'volume_percentile': 10}

        result = self.scorer.calculate_liquidity_score(indicators, percentiles)

        assert result['score'] <= 3, f"Low volume should score <=3, got {result['score']}"


class TestValuationScore:
    """Test valuation score calculation (0-10 scale)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_undervalued_scores_high(self):
        """Low P/E, P/B percentiles should score high"""
        ticker_data = {
            'info': {
                'trailingPE': 10.0,
                'priceToBook': 1.5,
                'dividendYield': 0.04,  # 4% yield
            }
        }
        percentiles = {
            'pe_percentile': 20,  # Low = undervalued
            'pb_percentile': 25,
        }

        result = self.scorer.calculate_valuation_score(ticker_data, percentiles)

        assert result['category'] == 'Valuation'
        assert result['score'] >= 7, f"Undervalued should score >=7, got {result['score']}"

    def test_overvalued_scores_low(self):
        """High P/E, P/B percentiles should score low"""
        ticker_data = {
            'info': {
                'trailingPE': 50.0,
                'priceToBook': 10.0,
                'dividendYield': 0.0,
            }
        }
        percentiles = {
            'pe_percentile': 95,  # High = overvalued
            'pb_percentile': 90,
        }

        result = self.scorer.calculate_valuation_score(ticker_data, percentiles)

        assert result['score'] <= 3, f"Overvalued should score <=3, got {result['score']}"

    def test_dividend_yield_bonus(self):
        """High dividend yield should add bonus points"""
        ticker_data_no_div = {
            'info': {
                'trailingPE': 20.0,
                'priceToBook': 3.0,
                'dividendYield': 0.0,
            }
        }
        ticker_data_high_div = {
            'info': {
                'trailingPE': 20.0,
                'priceToBook': 3.0,
                'dividendYield': 0.06,  # 6% yield
            }
        }
        percentiles = {'pe_percentile': 50, 'pb_percentile': 50}

        score_no_div = self.scorer.calculate_valuation_score(ticker_data_no_div, percentiles)['score']
        score_high_div = self.scorer.calculate_valuation_score(ticker_data_high_div, percentiles)['score']

        assert score_high_div > score_no_div, "High dividend yield should increase score"


class TestSellingPressureScore:
    """Test selling pressure score using VWAP (0-10 scale)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_strong_buying_pressure_scores_high(self):
        """Price >3% above VWAP should score ~9"""
        indicators = {
            'current_price': 104.0,
            'vwap': 100.0,  # Price 4% above VWAP (>3% threshold)
        }

        result = self.scorer.calculate_selling_pressure_score(indicators)

        assert result['category'] == 'Selling Pressure'
        assert result['score'] >= 8, f"Strong buying pressure should score >=8, got {result['score']}"
        assert 'buying' in result['rationale'].lower() or 'demand' in result['rationale'].lower()

    def test_strong_selling_pressure_scores_low(self):
        """Price <-3% below VWAP should score ~1"""
        indicators = {
            'current_price': 97.0,
            'vwap': 100.0,  # Price 3% below VWAP
        }

        result = self.scorer.calculate_selling_pressure_score(indicators)

        assert result['score'] <= 2, f"Strong selling pressure should score <=2, got {result['score']}"
        assert 'selling' in result['rationale'].lower() or 'pressure' in result['rationale'].lower()

    def test_balanced_market_scores_neutral(self):
        """Price near VWAP should score ~5"""
        indicators = {
            'current_price': 100.5,
            'vwap': 100.0,  # Price 0.5% above VWAP
        }

        result = self.scorer.calculate_selling_pressure_score(indicators)

        assert 4 <= result['score'] <= 6, f"Balanced market should score ~5, got {result['score']}"


class TestUncertaintyScore:
    """Test uncertainty score conversion from 0-100 to 0-10 scale (INVERTED)"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_low_uncertainty_scores_high(self):
        """Low uncertainty (0-25) should score 8-10 (stable market)"""
        indicators = {'uncertainty_score': 20}

        result = self.scorer.calculate_uncertainty_score(indicators)

        assert result['category'] == 'Uncertainty'
        assert 8 <= result['score'] <= 10, f"Low uncertainty should score 8-10, got {result['score']}"
        assert 'stable' in result['rationale'].lower() or 'low' in result['rationale'].lower()

    def test_high_uncertainty_scores_low(self):
        """High uncertainty (75-100) should score 0-4 (volatile market)"""
        indicators = {'uncertainty_score': 85}

        result = self.scorer.calculate_uncertainty_score(indicators)

        assert 0 <= result['score'] <= 4, f"High uncertainty should score 0-4, got {result['score']}"
        assert 'volatile' in result['rationale'].lower() or 'unstable' in result['rationale'].lower()

    def test_uncertainty_inversion_formula(self):
        """Verify inverted scoring: higher uncertainty = lower score"""
        test_cases = [
            (0, 10),    # 0 uncertainty → 10 score
            (10, 9),    # 10 uncertainty → 9 score
            (50, 5),    # 50 uncertainty → 5 score
            (100, 0),   # 100 uncertainty → 0 score
        ]

        for uncertainty, expected_score in test_cases:
            indicators = {'uncertainty_score': uncertainty}
            result = self.scorer.calculate_uncertainty_score(indicators)
            assert abs(result['score'] - expected_score) <= 0.5, \
                f"Uncertainty {uncertainty} should score ~{expected_score}, got {result['score']}"

    def test_missing_uncertainty_returns_neutral(self):
        """Missing uncertainty score should return neutral ~5"""
        indicators = {}

        result = self.scorer.calculate_uncertainty_score(indicators)

        assert 4 <= result['score'] <= 6, "Missing uncertainty should score neutral (~5)"


class TestCalculateAllScores:
    """Test calculate_all_scores() integration"""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_returns_all_6_scores(self):
        """Should return dict with all 6 score types"""
        ticker_data = {
            'info': {
                'trailingPE': 20.0,
                'revenueGrowth': 0.15,
                'profitMargins': 0.20,
                'returnOnEquity': 0.15,
                'priceToBook': 3.0,
                'dividendYield': 0.02,
            }
        }
        indicators = {
            'current_price': 150.0,
            'sma_20': 145.0,
            'sma_50': 140.0,
            'sma_200': 135.0,
            'rsi': 60.0,
            'macd': 1.5,
            'macd_signal': 1.0,
            'volume': 1500000,
            'volume_sma': 1000000,
            'vwap': 148.0,
            'uncertainty_score': 40,
        }
        percentiles = {
            'pe_percentile': 50,
            'pb_percentile': 50,
            'volume_percentile': 70,
        }

        result = self.scorer.calculate_all_scores(ticker_data, indicators, percentiles)

        assert isinstance(result, dict), "Should return dict"
        assert len(result) == 6, f"Should have 6 scores, got {len(result)}"

        expected_categories = ['Fundamental', 'Technical', 'Liquidity', 'Valuation', 'Selling Pressure', 'Uncertainty']
        for category in expected_categories:
            assert category in result, f"Missing category: {category}"
            assert 'score' in result[category], f"{category} missing score"
            assert 'category' in result[category], f"{category} missing category field"
            assert 'rationale' in result[category], f"{category} missing rationale"
            assert 0 <= result[category]['score'] <= 10, f"{category} score out of bounds: {result[category]['score']}"

    def test_handles_partial_data(self):
        """Should handle missing data gracefully"""
        ticker_data = {'info': {}}
        indicators = {'current_price': 150.0}
        percentiles = {}

        result = self.scorer.calculate_all_scores(ticker_data, indicators, percentiles)

        assert len(result) == 6, "Should return all 6 scores even with partial data"
        for category, score_data in result.items():
            assert 0 <= score_data['score'] <= 10, f"{category} score out of bounds with partial data"
