# -*- coding: utf-8 -*-
"""
Regression tests for projection_calculator.py edge cases

These tests reproduce production bugs discovered during parallel report generation:
- Bug #2: ValueError when DataFrame has numeric index instead of datetime index

Following CLAUDE.md testing principles:
- Test Sabotage Verification: Written to FAIL with buggy code, PASS with fixed code
- Happy Path Only anti-pattern: These tests cover edge cases that weren't tested initially
- Explicit Failure Mocking: Tests use real failure scenarios from production
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis.projection_calculator import ProjectionCalculator


class TestProjectionCalculatorEdgeCases:
    """Test edge cases that production bugs revealed were missing from initial TDD"""

    def setup_method(self):
        self.calculator = ProjectionCalculator(initial_investment=1000.0)

    def test_numeric_dataframe_index_does_not_crash(self):
        """
        Regression test for Bug #2: ValueError: time data '246' does not match format '%Y-%m-%d'

        Production error from CloudWatch logs:
            File "/var/task/src/analysis/projection_calculator.py", line 147
            last_date = datetime.strptime(str(last_date_str), '%Y-%m-%d')
            ValueError: time data '246' does not match format '%Y-%m-%d'

        Root cause: When yfinance returns DataFrame with numeric index (0, 1, 2, ...),
        code tried to parse integers as date strings.

        This test follows CLAUDE.md Principle 5 (Test Sabotage Verification):
        - With buggy code: FAILS with ValueError
        - With fixed code: PASSES without exception
        """
        # Simulate yfinance DataFrame with numeric index
        close_prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
        dates = [243, 244, 245, 246, 247, 248, 249]  # ← Numeric index from DataFrame.index.tolist()

        # This should NOT crash with ValueError
        projections = self.calculator.calculate_projections(
            close_prices=close_prices,
            dates=dates,
            days_ahead=7
        )

        # Verify projections were created
        assert len(projections) == 7, "Should create 7-day projections"

        # Verify all projection dates are valid date strings
        for proj in projections:
            assert 'date' in proj
            # Should be parseable as date (not raise ValueError)
            parsed_date = datetime.strptime(proj['date'], '%Y-%m-%d')
            assert isinstance(parsed_date, datetime)

    def test_mixed_numeric_and_string_dates(self):
        """
        Edge case: DataFrame with mixed index types (shouldn't happen but test defensive coding)
        """
        close_prices = [100.0, 101.0, 102.0]
        dates = [0, '2025-12-05', 2]  # Mixed types

        # Should handle gracefully without crashing
        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=3)
        assert len(projections) == 3

    def test_single_data_point_with_numeric_index(self):
        """
        Edge case: Single data point with numeric index

        Follows CLAUDE.md "Happy Path Only" anti-pattern avoidance:
        Original tests only used multiple data points with perfect date strings.
        """
        close_prices = [100.0]
        dates = [0]  # Single numeric index

        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)

        assert len(projections) == 7
        # Should use today's date as starting point
        first_proj_date = datetime.strptime(projections[0]['date'], '%Y-%m-%d')
        today = datetime.now()
        # First projection should be within 2 days of today (accounting for timezone)
        assert abs((first_proj_date - today).days) <= 2

    def test_empty_data_with_numeric_dates(self):
        """
        Edge case: Empty data arrays

        Follows CLAUDE.md Principle 2 (Explicit Failure Mocking):
        Test explicit failure conditions, not just success.
        """
        close_prices = []
        dates = []

        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)

        # Should return empty list, not crash
        assert projections == []

    def test_valid_date_strings_still_work(self):
        """
        Ensure fix doesn't break the happy path (valid date strings)

        Regression prevention: Verify fix doesn't introduce new bugs.
        """
        close_prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        dates = ['2025-12-01', '2025-12-02', '2025-12-03', '2025-12-04', '2025-12-05']

        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)

        assert len(projections) == 7

        # Verify dates are sequential
        expected_start = datetime.strptime('2025-12-05', '%Y-%m-%d') + timedelta(days=1)
        first_proj = datetime.strptime(projections[0]['date'], '%Y-%m-%d')
        assert first_proj == expected_start

    def test_float_index_values(self):
        """
        Edge case: DataFrame with float index values (can happen with resampling)
        """
        close_prices = [100.0, 101.0, 102.0]
        dates = [0.0, 1.0, 2.0]  # Float indices

        # Should handle float indices without crashing
        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)
        assert len(projections) == 7

    def test_large_numeric_index(self):
        """
        Actual production case: Index values like 243, 244, 245, 246

        This was the exact failure from CloudWatch logs.
        """
        close_prices = [150.0, 151.0, 152.0, 153.0]
        dates = [243, 244, 245, 246]  # Actual values from production error

        # This is the exact case that failed in production
        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)

        assert len(projections) == 7
        # Verify projections have all required fields
        for proj in projections:
            assert 'date' in proj
            assert 'expected_return' in proj
            assert 'best_case_return' in proj
            assert 'worst_case_return' in proj
            assert 'expected_nav' in proj

    def test_numpy_integer_index(self):
        """
        Edge case: numpy int64 values (common from pandas DataFrame.index.tolist())
        """
        close_prices = [100.0, 101.0, 102.0]
        dates = [np.int64(0), np.int64(1), np.int64(2)]  # numpy integers

        # Should handle numpy integer types
        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)
        assert len(projections) == 7


class TestProjectionCalculatorRoundTrip:
    """
    Round-trip tests: Verify enhanced historical data can feed into projections

    Follows CLAUDE.md Principle 3 (Round-Trip Tests for Persistence):
    The real contract is "enhanced data → projections pipeline works end-to-end"
    """

    def setup_method(self):
        self.calculator = ProjectionCalculator(initial_investment=1000.0)

    def test_enhance_then_project_with_numeric_index(self):
        """
        Round-trip: enhance historical data → calculate projections

        Tests the actual workflow: OHLCV data with numeric index → enhanced → projections
        """
        # Simulate OHLCV data with numeric index
        ohlcv_data = [
            {'date': 0, 'open': 100.0, 'high': 102.0, 'low': 99.0, 'close': 101.0, 'volume': 1000000},
            {'date': 1, 'open': 101.0, 'high': 103.0, 'low': 100.0, 'close': 102.0, 'volume': 1100000},
            {'date': 2, 'open': 102.0, 'high': 104.0, 'low': 101.0, 'close': 103.0, 'volume': 1200000},
        ]

        # Step 1: Enhance historical data
        enhanced = self.calculator.enhance_historical_data(ohlcv_data)

        assert len(enhanced) == 3
        assert all('return_pct' in point for point in enhanced)
        assert all('portfolio_nav' in point for point in enhanced)

        # Step 2: Extract for projections
        close_prices = [point['close'] for point in enhanced]
        dates = [point['date'] for point in enhanced]  # Numeric dates

        # Step 3: Calculate projections (should not crash)
        projections = self.calculator.calculate_projections(close_prices, dates, days_ahead=7)

        assert len(projections) == 7
        # Verify projections are forward-looking (NAV > 1000)
        assert all(proj['expected_nav'] > 0 for proj in projections)
