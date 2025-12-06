# -*- coding: utf-8 -*-
"""
Tests for ProjectionCalculator - Linear regression projections

TDD: Write tests first, then implement projection logic

Ported from: frontend/twinbar/src/utils/projectionCalculator.ts
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from src.analysis.projection_calculator import ProjectionCalculator


class TestHistoricalReturns:
    """Test historical return calculation"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_calculates_returns_from_first_price(self):
        """Returns should be calculated from first price as entry point"""
        close_prices = [100, 105, 110, 105, 115]

        returns = self.calc.calculate_historical_returns(close_prices)

        assert len(returns) == 5, "Should have same length as input"
        assert returns[0] == 0.0, "First return should be 0% (entry point)"
        assert returns[1] == 5.0, "Second return: (105-100)/100 * 100 = 5%"
        assert returns[2] == 10.0, "Third return: (110-100)/100 * 100 = 10%"
        assert returns[3] == 5.0, "Fourth return: (105-100)/100 * 100 = 5%"
        assert returns[4] == 15.0, "Fifth return: (115-100)/100 * 100 = 15%"

    def test_handles_price_decline(self):
        """Should correctly calculate negative returns"""
        close_prices = [100, 95, 90]

        returns = self.calc.calculate_historical_returns(close_prices)

        assert returns[1] == -5.0, "Down 5%"
        assert returns[2] == -10.0, "Down 10%"

    def test_empty_prices_returns_empty(self):
        """Empty input should return empty array"""
        returns = self.calc.calculate_historical_returns([])
        assert len(returns) == 0


class TestLinearTrend:
    """Test linear regression trend calculation"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_fits_upward_trend(self):
        """Should detect positive slope for upward trend"""
        # Perfect upward trend: 0, 5, 10, 15, 20
        returns = np.array([0, 5, 10, 15, 20])

        trend = self.calc.calculate_linear_trend(returns)

        assert 'slope' in trend
        assert 'intercept' in trend
        assert trend['slope'] > 4.5, f"Should have positive slope ~5, got {trend['slope']}"
        assert trend['slope'] < 5.5

    def test_fits_downward_trend(self):
        """Should detect negative slope for downward trend"""
        returns = np.array([20, 15, 10, 5, 0])

        trend = self.calc.calculate_linear_trend(returns)

        assert trend['slope'] < -4.5, f"Should have negative slope ~-5, got {trend['slope']}"
        assert trend['slope'] > -5.5

    def test_flat_trend_has_zero_slope(self):
        """Flat returns should have slope near 0"""
        returns = np.array([5, 5, 5, 5, 5])

        trend = self.calc.calculate_linear_trend(returns)

        assert abs(trend['slope']) < 0.1, f"Flat trend should have slope ~0, got {trend['slope']}"


class TestStandardDeviation:
    """Test volatility calculation"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_high_volatility_data(self):
        """High volatility should return higher std dev"""
        volatile_returns = np.array([0, 10, -8, 15, -12, 20])
        stable_returns = np.array([0, 1, 2, 1, 2, 1])

        volatile_std = self.calc.calculate_standard_deviation(volatile_returns)
        stable_std = self.calc.calculate_standard_deviation(stable_returns)

        assert volatile_std > stable_std, "Volatile data should have higher std dev"
        assert volatile_std > 8, f"Volatile std dev should be >8, got {volatile_std}"

    def test_constant_returns_zero_std(self):
        """Constant returns should have std dev near 0"""
        returns = np.array([5, 5, 5, 5, 5])

        std = self.calc.calculate_standard_deviation(returns)

        assert std < 0.1, f"Constant returns should have std ~0, got {std}"


class TestProjections:
    """Test 7-day forward projections"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_generates_7_day_projections(self):
        """Should return 7 future data points"""
        close_prices = [100, 102, 104, 106, 108]
        dates = [
            (datetime.now() - timedelta(days=4-i)).strftime('%Y-%m-%d')
            for i in range(5)
        ]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        assert len(projections) == 7, f"Should generate 7 projections, got {len(projections)}"

    def test_projection_has_required_fields(self):
        """Each projection should have expected/best/worst fields"""
        close_prices = [100, 105, 110]
        dates = [(datetime.now() - timedelta(days=2-i)).strftime('%Y-%m-%d') for i in range(3)]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        first_proj = projections[0]
        assert 'date' in first_proj
        assert 'expected_return' in first_proj
        assert 'best_case_return' in first_proj
        assert 'worst_case_return' in first_proj
        assert 'expected_nav' in first_proj
        assert 'best_case_nav' in first_proj
        assert 'worst_case_nav' in first_proj

    def test_projection_dates_are_future(self):
        """Projection dates should be after last historical date"""
        close_prices = [100, 102, 104]
        last_date = datetime.now()
        dates = [
            (last_date - timedelta(days=2-i)).strftime('%Y-%m-%d')
            for i in range(3)
        ]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        last_hist_date = datetime.strptime(dates[-1], '%Y-%m-%d')
        for proj in projections:
            proj_date = datetime.strptime(proj['date'], '%Y-%m-%d')
            assert proj_date > last_hist_date, f"Projection date {proj['date']} should be after {dates[-1]}"

    def test_confidence_bands_widen_over_time(self):
        """Best/worst case should diverge more as days progress"""
        close_prices = [100, 105, 110, 115, 120]
        dates = [(datetime.now() - timedelta(days=4-i)).strftime('%Y-%m-%d') for i in range(5)]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        # Day 1 spread vs Day 7 spread
        day1_spread = projections[0]['best_case_return'] - projections[0]['worst_case_return']
        day7_spread = projections[6]['best_case_return'] - projections[6]['worst_case_return']

        assert day7_spread > day1_spread, \
            f"Day 7 spread ({day7_spread}) should be > Day 1 spread ({day1_spread})"

    def test_upward_trend_has_positive_expected_return(self):
        """Upward trending prices should project positive returns"""
        # Strong upward trend
        close_prices = [100, 105, 110, 115, 120, 125]
        dates = [(datetime.now() - timedelta(days=5-i)).strftime('%Y-%m-%d') for i in range(6)]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        # Expected return for day 7 should be positive
        day7_expected = projections[6]['expected_return']
        assert day7_expected > 0, f"Upward trend should have positive expected return, got {day7_expected}"

    def test_best_case_greater_than_expected_greater_than_worst(self):
        """Confidence bands should maintain order"""
        close_prices = [100, 102, 104, 106, 108]
        dates = [(datetime.now() - timedelta(days=4-i)).strftime('%Y-%m-%d') for i in range(5)]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        for i, proj in enumerate(projections):
            assert proj['best_case_return'] >= proj['expected_return'], \
                f"Day {i+1}: Best case should be >= Expected"
            assert proj['expected_return'] >= proj['worst_case_return'], \
                f"Day {i+1}: Expected should be >= Worst case"


class TestEnhanceHistoricalData:
    """Test adding portfolio metrics to historical OHLCV data"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_adds_return_pct_and_portfolio_nav(self):
        """Should add return_pct and portfolio_nav fields"""
        ohlcv_data = [
            {'date': '2025-01-01', 'open': 98, 'high': 102, 'low': 97, 'close': 100, 'volume': 1000000},
            {'date': '2025-01-02', 'open': 100, 'high': 107, 'low': 99, 'close': 105, 'volume': 1200000},
            {'date': '2025-01-03', 'open': 105, 'high': 112, 'low': 104, 'close': 110, 'volume': 1100000},
        ]

        enhanced = self.calc.enhance_historical_data(ohlcv_data)

        assert len(enhanced) == 3
        for point in enhanced:
            assert 'return_pct' in point, "Should have return_pct field"
            assert 'portfolio_nav' in point, "Should have portfolio_nav field"

    def test_return_pct_calculation(self):
        """Return % should be cumulative from first price"""
        ohlcv_data = [
            {'date': '2025-01-01', 'close': 100, 'open': 98, 'high': 102, 'low': 97, 'volume': 1000000},
            {'date': '2025-01-02', 'close': 110, 'open': 100, 'high': 112, 'low': 99, 'volume': 1000000},
        ]

        enhanced = self.calc.enhance_historical_data(ohlcv_data)

        assert enhanced[0]['return_pct'] == 0.0, "First day return should be 0%"
        assert enhanced[1]['return_pct'] == 10.0, "Second day: (110-100)/100 * 100 = 10%"

    def test_portfolio_nav_calculation(self):
        """NAV should be initial_investment * (1 + return_pct/100)"""
        ohlcv_data = [
            {'date': '2025-01-01', 'close': 100, 'open': 100, 'high': 100, 'low': 100, 'volume': 1000000},
            {'date': '2025-01-02', 'close': 110, 'open': 110, 'high': 110, 'low': 110, 'volume': 1000000},  # +10%
            {'date': '2025-01-03', 'close': 90, 'open': 90, 'high': 90, 'low': 90, 'volume': 1000000},   # -10%
        ]

        enhanced = self.calc.enhance_historical_data(ohlcv_data)

        # $1000 initial investment
        assert enhanced[0]['portfolio_nav'] == 1000.0, "Day 1: $1000"
        assert enhanced[1]['portfolio_nav'] == 1100.0, "Day 2: $1000 * 1.10 = $1100"
        assert enhanced[2]['portfolio_nav'] == 900.0, "Day 3: $1000 * 0.90 = $900"

    def test_preserves_original_ohlcv_fields(self):
        """Should keep original OHLCV fields intact"""
        ohlcv_data = [
            {'date': '2025-01-01', 'open': 100, 'high': 105, 'low': 99, 'close': 102, 'volume': 1000000}
        ]

        enhanced = self.calc.enhance_historical_data(ohlcv_data)

        assert enhanced[0]['open'] == 100
        assert enhanced[0]['high'] == 105
        assert enhanced[0]['low'] == 99
        assert enhanced[0]['close'] == 102
        assert enhanced[0]['volume'] == 1000000


class TestEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        self.calc = ProjectionCalculator(initial_investment=1000.0)

    def test_flat_prices_projects_flat(self):
        """Flat historical prices should project near-flat future"""
        close_prices = [100, 100, 100, 100, 100]
        dates = [(datetime.now() - timedelta(days=4-i)).strftime('%Y-%m-%d') for i in range(5)]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        # Expected return should be near 0%
        day7_expected = projections[6]['expected_return']
        assert abs(day7_expected) < 5, f"Flat prices should project near 0%, got {day7_expected}%"

    def test_single_price_point(self):
        """Should handle single data point gracefully"""
        close_prices = [100]
        dates = [datetime.now().strftime('%Y-%m-%d')]

        projections = self.calc.calculate_projections(close_prices, dates, days_ahead=7)

        # Should still generate 7 projections (may be flat)
        assert len(projections) == 7

    def test_high_volatility_wide_bands(self):
        """High volatility should create wider confidence bands"""
        # Highly volatile prices
        volatile_prices = [100, 120, 90, 130, 85, 125]
        dates = [(datetime.now() - timedelta(days=5-i)).strftime('%Y-%m-%d') for i in range(6)]

        projections = self.calc.calculate_projections(volatile_prices, dates, days_ahead=7)

        # Day 7 spread should be large
        day7_spread = projections[6]['best_case_return'] - projections[6]['worst_case_return']
        assert day7_spread > 20, f"High volatility should create wide bands (>20%), got {day7_spread}%"
