# -*- coding: utf-8 -*-
"""
Projection Calculator - Linear Regression Forecasting

Calculates 7-day forward projections with confidence bands based on historical price trends.

Ported from: frontend/twinbar/src/utils/projectionCalculator.ts

Algorithm:
1. Calculate historical returns from entry point
2. Fit linear trend line (slope × day_index + intercept)
3. Calculate volatility (standard deviation)
4. Project 7 days forward with widening confidence bands
"""
import logging
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProjectionCalculator:
    """Calculate linear regression projections with confidence bands"""

    def __init__(self, initial_investment: float = 1000.0):
        """
        Initialize projection calculator

        Args:
            initial_investment: Starting portfolio value (default: $1000)
        """
        self.initial_investment = initial_investment

    def calculate_historical_returns(self, close_prices: List[float]) -> np.ndarray:
        """
        Calculate cumulative returns from first price (entry point)

        Args:
            close_prices: List of closing prices

        Returns:
            NumPy array of returns (%) from first price
        """
        if not close_prices:
            return np.array([])

        entry_price = close_prices[0]
        returns = []

        for price in close_prices:
            return_pct = ((price - entry_price) / entry_price) * 100
            returns.append(return_pct)

        return np.array(returns)

    def calculate_linear_trend(self, returns: np.ndarray) -> Dict[str, Any]:
        """
        Fit linear trend line to returns

        Args:
            returns: NumPy array of return percentages

        Returns:
            Dict with 'slope' and 'intercept'
        """
        if len(returns) == 0:
            return {'slope': 0.0, 'intercept': 0.0}

        # Edge case: single data point (can't fit line)
        if len(returns) == 1:
            return {'slope': 0.0, 'intercept': float(returns[0])}

        # Create x-axis: day indices
        x = np.arange(len(returns))

        # Use numpy polyfit for linear regression (degree 1)
        coefficients = np.polyfit(x, returns, 1)
        slope = coefficients[0]
        intercept = coefficients[1]

        return {
            'slope': float(slope),
            'intercept': float(intercept)
        }

    def calculate_standard_deviation(self, returns: np.ndarray) -> float:
        """
        Calculate standard deviation of returns (volatility measure)

        Args:
            returns: NumPy array of return percentages

        Returns:
            Standard deviation
        """
        if len(returns) == 0:
            return 0.0

        return float(np.std(returns))

    def calculate_projections(
        self,
        close_prices: List[float],
        dates: List[str],
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Calculate 7-day forward projections with confidence bands

        Algorithm:
        1. Calculate historical returns
        2. Fit linear trend
        3. Calculate volatility (std dev)
        4. Project forward with widening confidence bands

        Args:
            close_prices: List of historical closing prices
            dates: List of date strings (YYYY-MM-DD format)
            days_ahead: Number of days to project (default: 7)

        Returns:
            List of projection dicts with expected/best/worst case scenarios
        """
        if not close_prices or len(close_prices) == 0:
            return []

        # Calculate historical returns
        returns = self.calculate_historical_returns(close_prices)

        # Fit linear trend
        trend = self.calculate_linear_trend(returns)
        slope = trend['slope']
        intercept = trend['intercept']

        # Calculate volatility
        std_dev = self.calculate_standard_deviation(returns)

        # Last historical date
        # Handle both date strings and numeric indices
        last_date_str = dates[-1]

        # Check if it's a numeric string (e.g., "246" from RangeIndex)
        is_numeric = False
        if isinstance(last_date_str, (int, float)):
            is_numeric = True
        elif isinstance(last_date_str, str):
            try:
                float(last_date_str)
                is_numeric = True
            except ValueError:
                pass

        if is_numeric:
            # Numeric index - use today's date as fallback
            last_date = datetime.now()
            logger.warning(f"DataFrame has numeric index ({last_date_str}), using current date as projection start")
        else:
            last_date = datetime.strptime(str(last_date_str), '%Y-%m-%d')
        last_day_index = len(returns) - 1

        # Generate projections
        projections = []
        for future_day in range(1, days_ahead + 1):
            day_index = last_day_index + future_day
            projection_date = last_date + timedelta(days=future_day)

            # Expected return (linear trend)
            expected_return = slope * day_index + intercept

            # Confidence bands (widening factor based on how far into future)
            # Formula: day / days_ahead (day 7 = 100% widening, day 1 = 14% widening)
            widening_factor = future_day / days_ahead

            # Best/worst case = expected ± (std_dev × widening_factor)
            best_case_return = expected_return + (std_dev * widening_factor)
            worst_case_return = expected_return - (std_dev * widening_factor)

            # Convert returns to portfolio NAV
            expected_nav = self.initial_investment * (1 + expected_return / 100)
            best_case_nav = self.initial_investment * (1 + best_case_return / 100)
            worst_case_nav = self.initial_investment * (1 + worst_case_return / 100)

            projections.append({
                'date': projection_date.strftime('%Y-%m-%d'),
                'expected_return': round(expected_return, 2),
                'best_case_return': round(best_case_return, 2),
                'worst_case_return': round(worst_case_return, 2),
                'expected_nav': round(expected_nav, 2),
                'best_case_nav': round(best_case_nav, 2),
                'worst_case_nav': round(worst_case_nav, 2),
            })

        return projections

    def enhance_historical_data(self, ohlcv_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add return_pct and portfolio_nav to historical OHLCV data

        Args:
            ohlcv_data: List of dicts with date, open, high, low, close, volume

        Returns:
            Enhanced list with return_pct and portfolio_nav fields
        """
        if not ohlcv_data:
            return []

        # Extract close prices
        close_prices = [point['close'] for point in ohlcv_data]

        # Calculate returns
        returns = self.calculate_historical_returns(close_prices)

        # Enhance data
        enhanced = []
        for i, point in enumerate(ohlcv_data):
            return_pct = returns[i] if i < len(returns) else 0.0
            portfolio_nav = self.initial_investment * (1 + return_pct / 100)

            enhanced_point = {
                **point,  # Preserve original fields
                'return_pct': round(return_pct, 2),
                'portfolio_nav': round(portfolio_nav, 2),
            }
            enhanced.append(enhanced_point)

        logger.info(f"✅ Enhanced {len(enhanced)} historical data points with portfolio metrics")
        return enhanced
