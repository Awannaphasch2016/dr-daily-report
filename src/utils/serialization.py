"""JSON serialization utilities for LangSmith tracing and API responses.

Handles conversion of non-JSON-serializable types (numpy, pandas) to JSON-compatible types.
Extracted from workflow_nodes.py to eliminate code duplication.
"""

from typing import Any
import numpy as np
import pandas as pd
from datetime import datetime


def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert non-JSON types to JSON-serializable format.

    Handles:
    - numpy types (int64, float64, etc.)
    - pandas DataFrame
    - pandas Timestamp
    - datetime objects
    - nested dicts and lists

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable version of obj
    """
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        # Convert DataFrame to list of records (handles timestamp indexes)
        df_copy = obj.reset_index(drop=False)
        return make_json_serializable(df_copy.to_dict('records'))
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj
