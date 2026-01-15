# -*- coding: utf-8 -*-
"""
Chart Pattern Data Repository

Data access layer for detected chart patterns with implementation provenance tracking.
Supports multiple pattern detection implementations (stock_pattern, custom, talib).

Architecture:
    PatternDetectionService → this repository → Aurora chart_pattern_data table

Design Principles:
    1. Idempotency: ON DUPLICATE KEY UPDATE prevents duplicate patterns
    2. Type Safety: _convert_numpy_to_primitives at Aurora boundary
    3. Defensive Programming: Explicit validation of pattern types and implementations
    4. Implementation Provenance: Track which detector generated each pattern
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Set

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import CHART_PATTERN_DATA
from src.data.aurora.precompute_service import _convert_numpy_to_primitives

logger = logging.getLogger(__name__)


# =============================================================================
# Allowed Values (Principle #1: Defensive Programming)
# =============================================================================

ALLOWED_PATTERN_TYPES: Set[str] = {
    # Flag patterns
    'bullish_flag', 'bearish_flag',
    # Head and shoulders
    'head_shoulders', 'inverse_head_shoulders',
    # Wedges
    'ascending_wedge', 'descending_wedge',
    'rising_wedge', 'falling_wedge',  # Aliases
    # Double patterns
    'double_top', 'double_bottom',
    # Triangles
    'triangle',  # Generic triangle
    'ascending_triangle', 'descending_triangle', 'symmetrical_triangle',
    # VCP patterns
    'vcp', 'bullish_vcp', 'bearish_vcp',
    # Other patterns
    'cup_handle',
    # Generic (for custom patterns)
    'bullish', 'bearish', 'neutral',
}

ALLOWED_IMPLEMENTATIONS: Set[str] = {
    'stock_pattern',  # External stock-pattern library
    'custom',         # Our ChartPatternDetector
    'talib',          # TA-Lib (future)
    'ml_detector',    # ML-based detector (future)
}

ConfidenceLevel = Literal['high', 'medium', 'low']


class ChartPatternDataRepository:
    """Repository for chart pattern data operations.

    Provides CRUD operations for detected chart patterns with implementation
    provenance tracking. Supports multiple pattern detection implementations.

    Example:
        >>> repo = ChartPatternDataRepository()
        >>> pattern = {
        ...     'ticker_id': 1,
        ...     'symbol': 'AAPL',
        ...     'pattern_date': date(2026, 1, 14),
        ...     'pattern_type': 'bullish_flag',
        ...     'pattern_code': 'FLAGU',
        ...     'implementation': 'custom',
        ...     'impl_version': '1.0.0',
        ...     'confidence': 'high',
        ...     'start_date': date(2026, 1, 1),
        ...     'end_date': date(2026, 1, 10),
        ...     'pattern_data': {'points': {'A': {'date': '2026-01-01', 'price': 150.25}}}
        ... }
        >>> repo.upsert(pattern)
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        """Initialize repository.

        Args:
            client: AuroraClient instance (uses singleton if not provided)
        """
        self.client = client or get_aurora_client()

    # =========================================================================
    # Validation (Principle #1: Defensive Programming)
    # =========================================================================

    def _validate_pattern(self, pattern: Dict[str, Any]) -> None:
        """Validate pattern data before storage.

        Args:
            pattern: Pattern data dict

        Raises:
            ValueError: If required fields missing or invalid values
        """
        required_fields = {
            'ticker_id', 'symbol', 'pattern_date', 'pattern_type',
            'pattern_code', 'implementation', 'impl_version', 'pattern_data'
        }
        missing = required_fields - set(pattern.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        pattern_type = pattern['pattern_type']
        if pattern_type not in ALLOWED_PATTERN_TYPES:
            raise ValueError(
                f"Invalid pattern_type '{pattern_type}'. "
                f"Allowed: {sorted(ALLOWED_PATTERN_TYPES)}"
            )

        implementation = pattern['implementation']
        if implementation not in ALLOWED_IMPLEMENTATIONS:
            raise ValueError(
                f"Invalid implementation '{implementation}'. "
                f"Allowed: {sorted(ALLOWED_IMPLEMENTATIONS)}"
            )

    def _normalize_date(self, value: Any) -> Optional[str]:
        """Normalize date to string format.

        Args:
            value: Date as string, date object, or datetime

        Returns:
            Date string in YYYY-MM-DD format or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value
        raise ValueError(f"Cannot normalize date: {value} (type: {type(value)})")

    # =========================================================================
    # Upsert Operations
    # =========================================================================

    def upsert(self, pattern: Dict[str, Any]) -> int:
        """Upsert a single chart pattern.

        Uses INSERT ... ON DUPLICATE KEY UPDATE for idempotency.
        Unique key: (symbol, pattern_date, pattern_type, implementation)

        Args:
            pattern: Pattern data dict with required fields:
                - ticker_id: Foreign key to ticker_master
                - symbol: Ticker symbol
                - pattern_date: Date pattern was detected
                - pattern_type: Pattern category (bullish_flag, etc.)
                - pattern_code: Short code (FLAGU, etc.)
                - implementation: Detector name (stock_pattern, custom, etc.)
                - impl_version: Version string (1.0.0, etc.)
                - pattern_data: Dict with pattern-specific data
            Optional fields:
                - confidence: high/medium/low (default: medium)
                - start_date: Pattern start in price data
                - end_date: Pattern end in price data

        Returns:
            Number of affected rows (1 for insert, 2 for update)

        Raises:
            ValueError: If validation fails
        """
        self._validate_pattern(pattern)

        # Convert numpy types at Aurora boundary (Principle #4)
        pattern_data_clean = _convert_numpy_to_primitives(pattern['pattern_data'])
        pattern_data_json = json.dumps(pattern_data_clean)

        query = f"""
            INSERT INTO {CHART_PATTERN_DATA} (
                ticker_id, symbol, pattern_date,
                pattern_type, pattern_code,
                implementation, impl_version,
                confidence, start_date, end_date,
                pattern_data, detected_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                pattern_code = VALUES(pattern_code),
                impl_version = VALUES(impl_version),
                confidence = VALUES(confidence),
                start_date = VALUES(start_date),
                end_date = VALUES(end_date),
                pattern_data = VALUES(pattern_data),
                detected_at = NOW(),
                updated_at = NOW()
        """

        params = (
            pattern['ticker_id'],
            pattern['symbol'],
            self._normalize_date(pattern['pattern_date']),
            pattern['pattern_type'],
            pattern['pattern_code'],
            pattern['implementation'],
            pattern['impl_version'],
            pattern.get('confidence', 'medium'),
            self._normalize_date(pattern.get('start_date')),
            self._normalize_date(pattern.get('end_date')),
            pattern_data_json,
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted pattern: {pattern['symbol']} {pattern['pattern_type']} "
            f"({pattern['implementation']}) - {rowcount} rows affected"
        )
        return rowcount

    def batch_upsert(
        self,
        patterns: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """Batch upsert multiple chart patterns.

        Args:
            patterns: List of pattern dicts
            batch_size: Records per batch (default: 100)

        Returns:
            Total number of affected rows

        Raises:
            ValueError: If patterns list is empty
        """
        if not patterns:
            raise ValueError("Cannot upsert empty patterns list")

        total_affected = 0
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]
            for pattern in batch:
                affected = self.upsert(pattern)
                total_affected += affected

            logger.info(
                f"Batch upsert: processed {len(batch)} patterns "
                f"(batch {i // batch_size + 1})"
            )

        logger.info(
            f"Batch upsert complete: {len(patterns)} patterns, "
            f"{total_affected} total rows affected"
        )
        return total_affected

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_patterns_for_symbol(
        self,
        symbol: str,
        pattern_date: Optional[date] = None,
        implementation: Optional[str] = None,
        pattern_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get patterns for a symbol.

        Args:
            symbol: Ticker symbol
            pattern_date: Filter by specific date (default: today)
            implementation: Filter by implementation (optional)
            pattern_type: Filter by pattern type (optional)

        Returns:
            List of pattern records
        """
        conditions = ["symbol = %s"]
        params: List[Any] = [symbol]

        if pattern_date:
            conditions.append("pattern_date = %s")
            params.append(self._normalize_date(pattern_date))

        if implementation:
            if implementation not in ALLOWED_IMPLEMENTATIONS:
                raise ValueError(f"Invalid implementation: {implementation}")
            conditions.append("implementation = %s")
            params.append(implementation)

        if pattern_type:
            if pattern_type not in ALLOWED_PATTERN_TYPES:
                raise ValueError(f"Invalid pattern_type: {pattern_type}")
            conditions.append("pattern_type = %s")
            params.append(pattern_type)

        query = f"""
            SELECT
                id, ticker_id, symbol, pattern_date,
                pattern_type, pattern_code,
                implementation, impl_version,
                confidence, start_date, end_date,
                pattern_data,
                detected_at, created_at, updated_at
            FROM {CHART_PATTERN_DATA}
            WHERE {' AND '.join(conditions)}
            ORDER BY pattern_date DESC, confidence DESC
        """

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_latest_patterns(
        self,
        symbol: str,
        days: int = 30,
        implementation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get latest patterns for a symbol within date range.

        Args:
            symbol: Ticker symbol
            days: Number of days to look back
            implementation: Filter by implementation (optional)

        Returns:
            List of pattern records sorted by date DESC
        """
        conditions = [
            "symbol = %s",
            "pattern_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
        ]
        params: List[Any] = [symbol, days]

        if implementation:
            if implementation not in ALLOWED_IMPLEMENTATIONS:
                raise ValueError(f"Invalid implementation: {implementation}")
            conditions.append("implementation = %s")
            params.append(implementation)

        query = f"""
            SELECT
                id, ticker_id, symbol, pattern_date,
                pattern_type, pattern_code,
                implementation, impl_version,
                confidence, start_date, end_date,
                pattern_data,
                detected_at, created_at, updated_at
            FROM {CHART_PATTERN_DATA}
            WHERE {' AND '.join(conditions)}
            ORDER BY pattern_date DESC, confidence DESC
        """

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def delete_patterns(
        self,
        symbol: str,
        pattern_date: date,
        implementation: Optional[str] = None
    ) -> int:
        """Delete patterns for a symbol on a date.

        Useful for re-running detection with different parameters.

        Args:
            symbol: Ticker symbol
            pattern_date: Date of patterns to delete
            implementation: Delete only for specific implementation (optional)

        Returns:
            Number of deleted rows
        """
        conditions = ["symbol = %s", "pattern_date = %s"]
        params: List[Any] = [symbol, self._normalize_date(pattern_date)]

        if implementation:
            if implementation not in ALLOWED_IMPLEMENTATIONS:
                raise ValueError(f"Invalid implementation: {implementation}")
            conditions.append("implementation = %s")
            params.append(implementation)

        query = f"""
            DELETE FROM {CHART_PATTERN_DATA}
            WHERE {' AND '.join(conditions)}
        """

        rowcount = self.client.execute(query, tuple(params))
        logger.info(
            f"Deleted {rowcount} patterns for {symbol} on {pattern_date}"
            + (f" (implementation: {implementation})" if implementation else "")
        )
        return rowcount

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON.

        Args:
            row: Database row dict

        Returns:
            Dict with pattern_data parsed from JSON
        """
        result = dict(row)

        # Parse pattern_data JSON
        if 'pattern_data' in result and isinstance(result['pattern_data'], str):
            result['pattern_data'] = json.loads(result['pattern_data'])

        # Convert dates to ISO strings for JSON serialization
        for date_field in ['pattern_date', 'start_date', 'end_date']:
            if date_field in result and result[date_field] is not None:
                if isinstance(result[date_field], (date, datetime)):
                    result[date_field] = result[date_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[ChartPatternDataRepository] = None


def get_chart_pattern_repository() -> ChartPatternDataRepository:
    """Get singleton ChartPatternDataRepository instance.

    Returns:
        ChartPatternDataRepository instance
    """
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ChartPatternDataRepository()
    return _repository_instance
