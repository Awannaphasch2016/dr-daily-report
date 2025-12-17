"""
Test JSON serialization utility for converting numpy/pandas types.

This utility is extracted from workflow_nodes.py to eliminate code duplication.
It handles conversion of non-JSON-serializable types (numpy int64, pandas Timestamp, etc.)
to JSON-compatible types.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime


class TestSerializationUtility:
    """Test make_json_serializable() function"""

    def test_numpy_integer_converts_to_float(self):
        """Test that numpy integers convert to Python float"""
        from src.utils.serialization import make_json_serializable

        value = np.int64(42)
        result = make_json_serializable(value)

        assert isinstance(result, float)
        assert result == 42.0

    def test_numpy_floating_converts_to_float(self):
        """Test that numpy floats convert to Python float"""
        from src.utils.serialization import make_json_serializable

        value = np.float64(3.14)
        result = make_json_serializable(value)

        assert isinstance(result, float)
        assert result == 3.14

    def test_numpy_array_converts_to_list(self):
        """Test that numpy arrays convert to Python list"""
        from src.utils.serialization import make_json_serializable

        value = np.array([1, 2, 3])
        result = make_json_serializable(value)

        assert isinstance(result, list)
        assert result == [1, 2, 3]

    def test_pandas_timestamp_converts_to_iso_string(self):
        """Test that pandas Timestamp converts to ISO format string"""
        from src.utils.serialization import make_json_serializable

        value = pd.Timestamp('2025-12-17 10:30:00')
        result = make_json_serializable(value)

        assert isinstance(result, str)
        assert '2025-12-17' in result
        assert 'T' in result  # ISO format separator

    def test_datetime_converts_to_iso_string(self):
        """Test that datetime objects convert to ISO format string"""
        from src.utils.serialization import make_json_serializable

        value = datetime(2025, 12, 17, 10, 30, 0)
        result = make_json_serializable(value)

        assert isinstance(result, str)
        assert '2025-12-17' in result

    def test_dict_with_numpy_values_recursively_converts(self):
        """Test that dicts with numpy values are converted recursively"""
        from src.utils.serialization import make_json_serializable

        value = {
            'count': np.int64(42),
            'price': np.float64(123.45),
            'nested': {
                'value': np.int64(10)
            }
        }
        result = make_json_serializable(value)

        assert isinstance(result['count'], float)
        assert isinstance(result['price'], float)
        assert isinstance(result['nested']['value'], float)
        assert result['count'] == 42.0
        assert result['price'] == 123.45

    def test_list_with_numpy_values_recursively_converts(self):
        """Test that lists with numpy values are converted recursively"""
        from src.utils.serialization import make_json_serializable

        value = [np.int64(1), np.float64(2.5), np.int64(3)]
        result = make_json_serializable(value)

        assert all(isinstance(x, float) for x in result)
        assert result == [1.0, 2.5, 3.0]

    def test_pandas_na_converts_to_none(self):
        """Test that pandas NA/NaT converts to None"""
        from src.utils.serialization import make_json_serializable

        value = pd.NA
        result = make_json_serializable(value)

        assert result is None

    def test_regular_python_types_passthrough(self):
        """Test that regular Python types pass through unchanged"""
        from src.utils.serialization import make_json_serializable

        # String
        assert make_json_serializable("hello") == "hello"

        # Int
        assert make_json_serializable(42) == 42

        # Float
        assert make_json_serializable(3.14) == 3.14

        # Bool
        assert make_json_serializable(True) is True

        # None
        assert make_json_serializable(None) is None

    def test_complex_nested_structure(self):
        """Test conversion of complex nested structure"""
        from src.utils.serialization import make_json_serializable

        value = {
            'ticker': 'DBS19',
            'indicators': {
                'rsi': np.float64(65.3),
                'current_price': np.float64(123.45)
            },
            'history': [
                {'date': pd.Timestamp('2025-12-17'), 'close': np.float64(120.0)},
                {'date': pd.Timestamp('2025-12-16'), 'close': np.float64(119.5)}
            ],
            'count': np.int64(253)
        }

        result = make_json_serializable(value)

        # Verify all numpy types converted
        assert isinstance(result['indicators']['rsi'], float)
        assert isinstance(result['indicators']['current_price'], float)
        assert isinstance(result['count'], float)
        assert isinstance(result['history'][0]['date'], str)
        assert isinstance(result['history'][0]['close'], float)

        # Verify regular types unchanged
        assert result['ticker'] == 'DBS19'
