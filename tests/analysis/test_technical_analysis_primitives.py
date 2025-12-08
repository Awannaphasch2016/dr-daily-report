"""
Contract test: TechnicalAnalyzer MUST return primitives only.

Following CLAUDE.md:
- Defensive Programming: Validate data types at creation
- System Boundary: TechnicalAnalyzer → Workflow → UserFacingScorer → Aurora cache
- Contract: All return values must be Python primitives (int, float, str, bool, None, list, dict)
- Test Fixtures Must Match Production Reality: Use real pandas DataFrames

ROOT CAUSE: _calculate_single_percentile() returns NumPy types from pandas calculations
"""
import pytest
import json
import numpy as np
import pandas as pd
import yfinance as yf
from src.analysis.technical_analysis import TechnicalAnalyzer


class TestTechnicalAnalyzerPrimitivesOnly:
    """Enforce contract: TechnicalAnalyzer returns primitives only."""

    def setup_method(self):
        self.analyzer = TechnicalAnalyzer()

    def test_calculate_all_indicators_with_percentiles_returns_only_primitives(self):
        """GIVEN TechnicalAnalyzer with REAL pandas DataFrame (production data)
        WHEN calculate_all_indicators_with_percentiles is called
        THEN ALL return values must be Python primitives

        Contract: Never return NumPy/Pandas types. Convert at source.

        This test uses REAL yfinance data to match production reality.
        """
        # Fetch real ticker data (matches production!)
        ticker_data = yf.download('AAPL', period='1y', progress=False)

        if ticker_data.empty:
            pytest.skip("Could not fetch ticker data (network issue)")

        # Call real method (not mocked!)
        result = self.analyzer.calculate_all_indicators_with_percentiles(ticker_data)

        assert result is not None, "Analyzer returned None"

        # CONTRACT: Recursively verify ALL values are primitives
        def assert_primitives_only(obj, path="root"):
            """Fail test if any non-primitive type found."""
            primitive_types = (int, float, str, bool, type(None))

            if isinstance(obj, dict):
                for key, value in obj.items():
                    assert_primitives_only(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    assert_primitives_only(item, f"{path}[{i}]")
            else:
                # The actual check
                assert isinstance(obj, primitive_types), \
                    f"Non-primitive type at {path}: {type(obj).__name__} = {obj}\n" \
                    f"Expected: int, float, str, bool, or None\n" \
                    f"Got: {type(obj).__module__}.{type(obj).__name__}\n" \
                    f"HINT: This is likely from _calculate_single_percentile() returning NumPy types"

        assert_primitives_only(result)

    def test_calculate_all_indicators_with_percentiles_is_json_serializable(self):
        """GIVEN analyzer output with REAL pandas data
        WHEN json.dumps() is called
        THEN it must succeed (no TypeError)

        This is the ultimate contract: if it's JSON-serializable, it's safe.

        Following CLAUDE.md Principle 3.5: Integration tests must exercise
        critical transformations - don't mock json.dumps()!
        """
        # Fetch real data
        ticker_data = yf.download('NVDA', period='6mo', progress=False)

        if ticker_data.empty:
            pytest.skip("Could not fetch ticker data (network issue)")

        result = self.analyzer.calculate_all_indicators_with_percentiles(ticker_data)

        # Must not raise TypeError - let json.dumps() execute for real!
        try:
            json_str = json.dumps(result)
            # Round-trip verification (CLAUDE.md Principle 3)
            deserialized = json.loads(json_str)
            assert deserialized is not None
            assert 'indicators' in deserialized
            assert 'percentiles' in deserialized
        except TypeError as e:
            pytest.fail(
                f"TechnicalAnalyzer output not JSON-serializable: {e}\n"
                f"This means NumPy/Pandas types are being returned.\n"
                f"Contract violation: All return values must be Python primitives.\n"
                f"Check _calculate_single_percentile() - likely source of NumPy types."
            )

    def test_percentiles_structure_has_primitive_values(self):
        """GIVEN percentiles output from analyzer
        WHEN inspecting percentile dicts
        THEN all statistical values (mean, std, min, max, percentile) must be primitives

        This specifically targets _calculate_single_percentile() which is the
        ROOT CAUSE of NumPy types in production.
        """
        ticker_data = yf.download('MSFT', period='3mo', progress=False)

        if ticker_data.empty:
            pytest.skip("Could not fetch ticker data (network issue)")

        result = self.analyzer.calculate_all_indicators_with_percentiles(ticker_data)

        assert result is not None
        assert 'percentiles' in result

        percentiles = result['percentiles']

        # Check each percentile dict
        for indicator_name, percentile_data in percentiles.items():
            if percentile_data is None:
                continue  # Some indicators may be None

            # These fields come from pandas and will be NumPy types if not converted
            for field in ['current_value', 'percentile', 'mean', 'std', 'min', 'max']:
                if field in percentile_data:
                    value = percentile_data[field]
                    assert isinstance(value, (int, float, type(None))), \
                        f"percentiles[{indicator_name}][{field}] is {type(value).__name__}, " \
                        f"expected int/float/None. " \
                        f"This is from _calculate_single_percentile():183-196 returning NumPy types."

    def test_indicators_structure_has_primitive_values(self):
        """GIVEN indicators output from analyzer
        WHEN inspecting indicator values
        THEN all values must be primitives

        This tests calculate_all_indicators() which extracts current values.
        """
        ticker_data = yf.download('TSLA', period='3mo', progress=False)

        if ticker_data.empty:
            pytest.skip("Could not fetch ticker data (network issue)")

        result = self.analyzer.calculate_all_indicators_with_percentiles(ticker_data)

        assert result is not None
        assert 'indicators' in result

        indicators = result['indicators']

        # All indicator values should be primitives
        for indicator_name, value in indicators.items():
            if value is None:
                continue  # None is acceptable

            assert isinstance(value, (int, float, bool)), \
                f"indicators[{indicator_name}] is {type(value).__name__}, expected int/float/bool"
