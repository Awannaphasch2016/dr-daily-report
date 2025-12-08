"""
Unit test: _calculate_single_percentile() MUST return primitives only.

Following CLAUDE.md:
- Defensive Programming: Validate data types at creation
- System Boundary: TechnicalAnalyzer._calculate_single_percentile() → workflow → Aurora cache
- Contract: All return values must be Python primitives (int, float, str, bool, None, list, dict)

ROOT CAUSE IDENTIFICATION:
This test targets the EXACT method that returns NumPy types: _calculate_single_percentile():183-196

The method returns dict with:
- 'percentile': np.float64 (from np.sum() and len())
- 'mean': np.float64 (from pandas.mean())
- 'std': np.float64 (from pandas.std())
- 'min': np.float64 (from pandas.min())
- 'max': np.float64 (from pandas.max())
"""
import pytest
import json
import numpy as np
import pandas as pd
from src.analysis.technical_analysis import TechnicalAnalyzer


class TestPercentilePrimitivesOnly:
    """Test _calculate_single_percentile() returns primitives only."""

    def setup_method(self):
        self.analyzer = TechnicalAnalyzer()

    def test_calculate_single_percentile_returns_only_primitives(self):
        """GIVEN _calculate_single_percentile with pandas Series (production reality)
        WHEN method is called
        THEN ALL return values must be Python primitives

        This is the ROOT CAUSE of JSON serialization bug.
        """
        # Create pandas Series (matches production data from yfinance)
        historical_values = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0])
        current_value = np.float64(75.0)  # NumPy type from calculations

        # Call the EXACT method that causes the bug
        result = self.analyzer._calculate_single_percentile(historical_values, current_value)

        assert result is not None

        # CONTRACT: All values in result dict must be primitives
        for key, value in result.items():
            assert isinstance(value, (int, float, str, bool, type(None))), \
                f"result[{key}] is {type(value).__name__} (value: {value})\n" \
                f"Expected: int, float, str, bool, or None\n" \
                f"Got: {type(value).__module__}.{type(value).__name__}\n" \
                f"SOURCE: technical_analysis.py:183-196 _calculate_single_percentile()\n" \
                f"RETURNS NumPy types from pandas calculations (.mean(), .std(), .min(), .max())"

    def test_calculate_single_percentile_result_is_json_serializable(self):
        """GIVEN percentile calculation result
        WHEN json.dumps() is called
        THEN it must succeed (no TypeError)

        This is the ultimate test - if it JSON-serializes, it's safe for Aurora.
        """
        # Realistic data
        historical_values = pd.Series(np.random.rand(100) * 100)
        current_value = np.float64(50.0)

        result = self.analyzer._calculate_single_percentile(historical_values, current_value)

        # Must not raise TypeError
        try:
            json_str = json.dumps(result)
            deserialized = json.loads(json_str)
            assert deserialized is not None
            assert 'percentile' in deserialized
            assert 'mean' in deserialized
        except TypeError as e:
            pytest.fail(
                f"_calculate_single_percentile result not JSON-serializable: {e}\n"
                f"Source: technical_analysis.py:183-196\n"
                f"Returns NumPy types from pandas (.mean(), .std(), .min(), .max())\n"
                f"FIX: Convert to Python primitives before returning:\n"
                f"  'mean': float(historical_values.mean())\n"
                f"  'percentile': float(percentile)"
            )

    def test_specific_fields_are_primitives(self):
        """GIVEN percentile result
        WHEN inspecting specific fields
        THEN percentile, mean, std, min, max must be primitives

        This test verifies the EXACT fields that cause JSON serialization failure.
        """
        historical_values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        current_value = 3.0

        result = self.analyzer._calculate_single_percentile(historical_values, current_value)

        # These are the fields that contain NumPy types
        fields_to_check = ['percentile', 'mean', 'std', 'min', 'max']

        for field in fields_to_check:
            assert field in result, f"Missing field: {field}"
            value = result[field]

            # Check if it's a NumPy type (THIS WILL FAIL - that's the bug!)
            is_numpy = isinstance(value, (np.integer, np.floating, np.ndarray))
            is_primitive = isinstance(value, (int, float))

            assert is_primitive and not is_numpy, \
                f"Field '{field}' is NumPy type {type(value).__name__}, not Python primitive\n" \
                f"Value: {value}\n" \
                f"Type module: {type(value).__module__}\n" \
                f"PROOF: This is the bug that causes MySQL Error 3140"

    def test_with_frequency_functions_also_returns_primitives(self):
        """GIVEN percentile calculation with frequency functions
        WHEN method is called
        THEN additional frequency fields must also be primitives

        Frequency functions add more fields to result dict (also NumPy types).
        """
        historical_values = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        current_value = 75.0

        # With frequency functions (like RSI > 70, RSI < 30)
        freq_funcs = {
            'frequency_above_70': lambda x: x > 70,
            'frequency_below_30': lambda x: x < 30
        }

        result = self.analyzer._calculate_single_percentile(
            historical_values,
            current_value,
            frequency_functions=freq_funcs
        )

        # ALL values must be primitives, including frequency percentages
        for key, value in result.items():
            assert isinstance(value, (int, float, str, bool, type(None))), \
                f"result[{key}] is {type(value).__name__}, expected primitive"
