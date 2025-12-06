# -*- coding: utf-8 -*-
"""
Canonical schema for cached report data.

This is the CONTRACT between:
- Scheduler (writes to Aurora via precompute_service)
- UI (reads from Aurora via rankings_service)

Any changes to this schema MUST be coordinated across both sides.
"""

from typing import TypedDict, List, Literal, Dict, Any


class PricePoint(TypedDict):
    """OHLCV price data point with portfolio metrics"""
    date: str  # ISO format: "2025-12-07"
    open: float
    high: float
    low: float
    close: float
    volume: int
    # Portfolio metrics (added by ProjectionCalculator)
    cumulative_value: float
    returns_pct: float


class ProjectionBand(TypedDict):
    """7-day forecast projection band"""
    date: str  # ISO format: "2025-12-14"
    lower: float
    middle: float
    upper: float


class ScoringMetric(TypedDict):
    """Investment scoring metric"""
    label: str  # "Fundamental", "Technical", etc.
    score: int  # 0-100
    color: Literal["green", "yellow", "red"]


class CachedReportData(TypedDict):
    """
    Complete schema for cached report data in Aurora.

    This is what scheduler WRITES and UI READS.
    """
    # Core identification
    ticker: str
    report_date: str  # ISO format

    # Chart data (REQUIRED for UI charts)
    price_history: List[PricePoint]  # Min 30 points for 1-month chart
    projections: List[ProjectionBand]  # Exactly 7 points (7-day forecast)
    initial_investment: float  # Default: 1000.0

    # Investment analysis (REQUIRED for UI scoring panel)
    user_facing_scores: Dict[str, Any]  # Dict with 6 categories
    stance: Literal["bullish", "bearish", "neutral"]

    # Report metadata
    report_text: str  # Full Thai language report
    strategy: Literal["single-stage", "multi-stage"]
    created_at: str  # ISO timestamp


def validate_cached_report(data: dict) -> tuple[bool, list[str]]:
    """
    Validate that cached report data matches schema contract.

    Args:
        data: Report data dict from Aurora or API response

    Returns:
        (is_valid, error_messages)

    Example:
        >>> is_valid, errors = validate_cached_report(cached_data)
        >>> if not is_valid:
        >>>     raise ValueError(f"Schema violation: {errors}")
    """
    errors = []

    # Required fields
    required_fields = [
        'ticker', 'report_date', 'price_history', 'projections',
        'initial_investment', 'user_facing_scores', 'stance'
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Type validations
    if not isinstance(data['price_history'], list):
        errors.append("price_history must be list")
    elif len(data['price_history']) < 30:
        errors.append(f"price_history must have >=30 points (got {len(data['price_history'])})")

    if not isinstance(data['projections'], list):
        errors.append("projections must be list")
    elif len(data['projections']) != 7:
        errors.append(f"projections must have exactly 7 points (got {len(data['projections'])})")

    # user_facing_scores validation - should be dict with 6 categories
    if not isinstance(data.get('user_facing_scores'), dict):
        errors.append("user_facing_scores must be dict")
    elif len(data.get('user_facing_scores', {})) < 6:
        errors.append(f"user_facing_scores must have at least 6 categories (got {len(data.get('user_facing_scores', {}))})")

    if data.get('stance') not in ['bullish', 'bearish', 'neutral']:
        errors.append(f"stance must be bullish/bearish/neutral (got {data.get('stance')})")

    # Nested structure validations
    if isinstance(data.get('price_history'), list) and len(data['price_history']) > 0:
        first_point = data['price_history'][0]
        required_point_fields = ['date', 'open', 'high', 'low', 'close', 'volume']
        for field in required_point_fields:
            if field not in first_point:
                errors.append(f"price_history[0] missing field: {field}")

    if isinstance(data.get('user_facing_scores'), dict) and len(data['user_facing_scores']) > 0:
        # Check first category has required structure
        first_category = list(data['user_facing_scores'].keys())[0]
        first_score = data['user_facing_scores'][first_category]
        if isinstance(first_score, dict):
            required_score_fields = ['category', 'score']
            for field in required_score_fields:
                if field not in first_score:
                    errors.append(f"user_facing_scores['{first_category}'] missing field: {field}")

    return len(errors) == 0, errors
