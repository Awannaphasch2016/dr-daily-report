# -*- coding: utf-8 -*-
"""
Fund Data Repository

Data access layer for fund data synced from on-premises SQL Server.
Provides batch upsert operations with idempotency and data lineage tracking.

Architecture:
    S3 raw/sql_server/fund_data/*.csv → Lambda → this repository → Aurora fund_data table

Design Principles:
    1. Idempotency: ON DUPLICATE KEY UPDATE prevents duplicate inserts
    2. Batch Operations: INSERT ... VALUES (...), (...), ... for performance
    3. Data Lineage: s3_source_key tracks exact S3 object origin
    4. Defensive Programming: Explicit rowcount validation
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client

logger = logging.getLogger(__name__)


class FundDataRepository:
    """Repository for fund data operations.

    Provides batch upsert operations for fund data synced from on-premises SQL Server.

    Example:
        >>> repo = FundDataRepository()
        >>> records = [
        ...     {
        ...         'd_trade': '2025-12-09',
        ...         'stock': 'DBS',
        ...         'ticker': 'DBS19',
        ...         'col_code': 'CLOSE',
        ...         'value_numeric': 38.50,
        ...         'value_text': None,
        ...         's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_20251209_083829.csv'
        ...     }
        ... ]
        >>> rowcount = repo.batch_upsert(records)
        >>> print(f"Inserted/updated {rowcount} rows")
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        """Initialize repository.

        Args:
            client: AuroraClient instance (uses singleton if not provided)
        """
        self.client = client or get_aurora_client()

    # =========================================================================
    # Batch Upsert Operations
    # =========================================================================

    def batch_upsert(
        self,
        records: List[Dict[str, Any]],
        batch_size: int = 1000,
    ) -> int:
        """Batch upsert fund data records with idempotency.

        Uses INSERT ... ON DUPLICATE KEY UPDATE to prevent duplicates.
        Composite unique key: (d_trade, stock, ticker, col_code)

        Args:
            records: List of fund data records. Each record must have:
                - d_trade: Trading date (str YYYY-MM-DD or date object)
                - stock: Stock identifier from source system (str)
                - ticker: Ticker symbol in DR or Yahoo format (str)
                - col_code: Column code identifying data type (str)
                - value_numeric: Numeric value (float/Decimal) or None
                - value_text: Text value (str) or None
                - s3_source_key: S3 object key for data lineage (str)
            batch_size: Number of records per batch (default: 1000)

        Returns:
            Total number of affected rows (1 for insert, 2 for update per row)

        Raises:
            ValueError: If records list is empty or invalid
            RuntimeError: If batch upsert affects 0 rows (defensive check)

        Example:
            >>> records = [
            ...     {
            ...         'd_trade': date(2025, 12, 9),
            ...         'stock': 'DBS',
            ...         'ticker': 'DBS19',
            ...         'col_code': 'CLOSE',
            ...         'value_numeric': Decimal('38.50'),
            ...         'value_text': None,
            ...         's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_20251209_083829.csv'
            ...     },
            ...     {
            ...         'd_trade': '2025-12-09',
            ...         'stock': 'DBS',
            ...         'ticker': 'DBS19',
            ...         'col_code': 'STATUS',
            ...         'value_numeric': None,
            ...         'value_text': 'ACTIVE',
            ...         's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_20251209_083829.csv'
            ...     }
            ... ]
            >>> rowcount = repo.batch_upsert(records)
            >>> # rowcount = 2 (both inserted) or 4 (both updated)
        """
        if not records:
            raise ValueError("Cannot upsert empty records list")

        # Validate required fields
        required_fields = {'d_trade', 'stock', 'ticker', 'col_code', 's3_source_key'}
        for i, record in enumerate(records):
            missing = required_fields - set(record.keys())
            if missing:
                raise ValueError(
                    f"Record {i} missing required fields: {missing}. "
                    f"Required: {required_fields}"
                )

        total_affected = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            affected = self._upsert_batch(batch)
            total_affected += affected
            logger.info(
                f"Batch upsert: processed {len(batch)} records, "
                f"affected {affected} rows (batch {i // batch_size + 1})"
            )

        logger.info(
            f"Batch upsert complete: {len(records)} records, "
            f"{total_affected} total rows affected"
        )
        return total_affected

    def _upsert_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Execute single batch upsert.

        Args:
            batch: List of fund data records (max batch_size)

        Returns:
            Number of affected rows

        Raises:
            RuntimeError: If batch affects 0 rows (defensive check)
        """
        # Build INSERT query with multiple VALUES clauses
        query = """
            INSERT INTO fund_data (
                d_trade, stock, ticker, col_code,
                value_numeric, value_text,
                source, s3_source_key,
                synced_at
            ) VALUES
        """

        # Add VALUES clause for each record
        values_clauses = []
        params = []
        for record in batch:
            values_clauses.append("(%s, %s, %s, %s, %s, %s, %s, %s, NOW())")
            params.extend([
                self._normalize_date(record['d_trade']),
                record['stock'],
                record['ticker'],
                record['col_code'],
                self._normalize_numeric(record.get('value_numeric')),
                record.get('value_text'),
                record.get('source', 'sql_server'),
                record['s3_source_key']
            ])

        query += ", ".join(values_clauses)

        # ON DUPLICATE KEY UPDATE (idempotency)
        query += """
            ON DUPLICATE KEY UPDATE
                value_numeric = VALUES(value_numeric),
                value_text = VALUES(value_text),
                s3_source_key = VALUES(s3_source_key),
                synced_at = NOW()
        """

        # Execute batch insert
        rowcount = self.client.execute(query, tuple(params))

        # Defensive programming: verify operation succeeded
        if rowcount == 0:
            raise RuntimeError(
                f"Batch upsert affected 0 rows for {len(batch)} records. "
                "This should never happen - check unique constraint or data validity."
            )

        return rowcount

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_latest_by_ticker(
        self,
        ticker: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get latest fund data for a ticker.

        Args:
            ticker: Ticker symbol (DR or Yahoo format)
            days: Number of days to look back (default: 30)

        Returns:
            List of fund data records sorted by d_trade DESC, col_code

        Example:
            >>> data = repo.get_latest_by_ticker('DBS19', days=7)
            >>> for record in data:
            ...     print(f"{record['d_trade']} {record['col_code']}: {record['value_numeric']}")
        """
        query = """
            SELECT
                id, d_trade, stock, ticker, col_code,
                value_numeric, value_text,
                source, s3_source_key,
                synced_at, updated_at
            FROM fund_data
            WHERE ticker = %s
              AND d_trade >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY d_trade DESC, col_code
        """
        rows = self.client.fetch_all(query, (ticker, days))
        return [self._row_to_dict(row) for row in rows]

    def get_by_date_range(
        self,
        ticker: str,
        start_date: date,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get fund data for date range.

        Args:
            ticker: Ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive). If None, uses today.

        Returns:
            List of fund data records

        Example:
            >>> from datetime import date
            >>> data = repo.get_by_date_range(
            ...     'DBS19',
            ...     start_date=date(2025, 12, 1),
            ...     end_date=date(2025, 12, 9)
            ... )
        """
        # TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
        end = end_date or datetime.utcnow().date()
        query = """
            SELECT
                id, d_trade, stock, ticker, col_code,
                value_numeric, value_text,
                source, s3_source_key,
                synced_at, updated_at
            FROM fund_data
            WHERE ticker = %s
              AND d_trade BETWEEN %s AND %s
            ORDER BY d_trade DESC, col_code
        """
        rows = self.client.fetch_all(query, (ticker, start_date, end))
        return [self._row_to_dict(row) for row in rows]

    def get_by_s3_source(self, s3_source_key: str) -> List[Dict[str, Any]]:
        """Get all records from specific S3 source (data lineage query).

        Args:
            s3_source_key: S3 object key

        Returns:
            List of fund data records from this S3 source

        Example:
            >>> data = repo.get_by_s3_source(
            ...     'raw/sql_server/fund_data/2025-12-09/fund_data_20251209_083829.csv'
            ... )
            >>> print(f"Loaded {len(data)} records from S3")
        """
        query = """
            SELECT
                id, d_trade, stock, ticker, col_code,
                value_numeric, value_text,
                source, s3_source_key,
                synced_at, updated_at
            FROM fund_data
            WHERE s3_source_key = %s
            ORDER BY d_trade DESC, ticker, col_code
        """
        rows = self.client.fetch_all(query, (s3_source_key,))
        return [self._row_to_dict(row) for row in rows]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_date(self, value: Any) -> str:
        """Normalize date value to MySQL DATE format.

        Args:
            value: Date as string (YYYY-MM-DD) or date object

        Returns:
            Date string in YYYY-MM-DD format

        Raises:
            ValueError: If value cannot be converted to date
        """
        if isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, str):
            # Validate format by parsing
            try:
                parsed = datetime.strptime(value, '%Y-%m-%d').date()
                return parsed.isoformat()
            except ValueError as e:
                raise ValueError(f"Invalid date format '{value}': {e}")
        else:
            raise ValueError(
                f"Expected date or str, got {type(value).__name__}: {value}"
            )

    def _normalize_numeric(self, value: Any) -> Optional[Decimal]:
        """Normalize numeric value to Decimal.

        Args:
            value: Numeric value (int, float, Decimal, str) or None

        Returns:
            Decimal or None

        Raises:
            ValueError: If value cannot be converted to Decimal
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value)
            except Exception as e:
                raise ValueError(f"Cannot convert '{value}' to Decimal: {e}")
        raise ValueError(
            f"Expected numeric type, got {type(value).__name__}: {value}"
        )

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert database row tuple to dictionary.

        Args:
            row: Database row as tuple

        Returns:
            Dictionary with column names as keys
        """
        return {
            'id': row[0],
            'd_trade': row[1],
            'stock': row[2],
            'ticker': row[3],
            'col_code': row[4],
            'value_numeric': row[5],
            'value_text': row[6],
            'source': row[7],
            's3_source_key': row[8],
            'synced_at': row[9],
            'updated_at': row[10],
        }


# ============================================================================
# Singleton Pattern (Module-Level)
# ============================================================================

_repository: Optional[FundDataRepository] = None


def get_fund_data_repository() -> FundDataRepository:
    """Get or create fund data repository singleton.

    Returns:
        FundDataRepository instance (shared across Lambda invocations)

    Example:
        >>> repo = get_fund_data_repository()
        >>> repo.batch_upsert(records)
    """
    global _repository
    if _repository is None:
        _repository = FundDataRepository()
    return _repository
