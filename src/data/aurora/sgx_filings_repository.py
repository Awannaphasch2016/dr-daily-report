# -*- coding: utf-8 -*-
"""
SGX Filings Repository

Data access layer for SGX exchange announcements/filings.
Supports upsert via ann_id (SGX's unique announcement ID) and
links each row to a shared acquisition provenance record.

Architecture:
    SGX data pipeline → this repository → Aurora sgx_filings table
                                        → Aurora data_acquisitions table (FK)

Design Principles:
    1. Idempotency: ON DUPLICATE KEY UPDATE on ann_id prevents duplicates
    2. Defensive Programming: Validate required fields before storage
    3. Provenance: Every row links to an acquisition run via acquisition_id
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import SGX_FILINGS

logger = logging.getLogger(__name__)


class SgxFilingsRepository:
    """Repository for SGX filings data operations.

    Provides CRUD operations for SGX exchange announcements with
    acquisition provenance tracking.

    Example:
        >>> repo = SgxFilingsRepository()
        >>> filing = {
        ...     'ticker_id': 1,
        ...     'symbol': 'DBS19',
        ...     'ann_id': 'ABC123',
        ...     'broadcast_date_time': '2026-03-14 08:30:00',
        ...     'category_code': 'ANNC',
        ...     'subcategory_code': 'ANNC09',
        ...     'title': 'Quarterly Results',
        ...     'raw_data': {'full': 'response'},
        ... }
        >>> repo.upsert(filing)
    """

    REQUIRED_FIELDS = {
        'ann_id', 'broadcast_date_time',
        'title', 'raw_data',
    }

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    # =========================================================================
    # Validation (Principle #1: Defensive Programming)
    # =========================================================================

    def _validate_filing(self, filing: Dict[str, Any]) -> None:
        """Validate filing data before storage.

        Raises:
            ValueError: If required fields are missing
        """
        missing = self.REQUIRED_FIELDS - set(filing.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    # =========================================================================
    # Upsert Operations
    # =========================================================================

    def upsert(self, filing: Dict[str, Any]) -> int:
        """Upsert a single SGX filing.

        Uses INSERT ... ON DUPLICATE KEY UPDATE on ann_id for idempotency.

        Args:
            filing: Filing data dict with required fields:
                - ticker_id, symbol, ann_id, broadcast_date_time
                - category_code, subcategory_code, title, raw_data
            Optional fields:
                - subcategory_name, issuer_name, stock_code
                - attachment_url, sgx_url, acquisition_id

        Returns:
            Number of affected rows (1 for insert, 2 for update)

        Raises:
            ValueError: If validation fails
        """
        self._validate_filing(filing)

        raw_data_json = json.dumps(filing['raw_data']) if isinstance(filing['raw_data'], dict) else filing['raw_data']

        query = f"""
            INSERT INTO {SGX_FILINGS} (
                ticker_id, symbol, ann_id, broadcast_date_time,
                category_code, subcategory_code, subcategory_name,
                title, issuer_name, stock_code,
                attachment_url, attachment_s3_key, sgx_url,
                raw_data, acquisition_id, fetched_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                ticker_id = VALUES(ticker_id),
                symbol = VALUES(symbol),
                broadcast_date_time = VALUES(broadcast_date_time),
                category_code = VALUES(category_code),
                subcategory_code = VALUES(subcategory_code),
                subcategory_name = VALUES(subcategory_name),
                title = VALUES(title),
                issuer_name = VALUES(issuer_name),
                stock_code = VALUES(stock_code),
                attachment_url = VALUES(attachment_url),
                attachment_s3_key = VALUES(attachment_s3_key),
                sgx_url = VALUES(sgx_url),
                raw_data = VALUES(raw_data),
                acquisition_id = VALUES(acquisition_id)
        """

        params = (
            filing.get('ticker_id'),
            filing.get('symbol'),
            filing['ann_id'],
            filing['broadcast_date_time'],
            filing.get('category_code'),
            filing.get('subcategory_code'),
            filing.get('subcategory_name'),
            filing['title'],
            filing.get('issuer_name'),
            filing.get('stock_code'),
            filing.get('attachment_url'),
            filing.get('attachment_s3_key'),
            filing.get('sgx_url'),
            raw_data_json,
            filing.get('acquisition_id'),
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted filing: {filing.get('symbol', 'N/A')} ann_id={filing['ann_id']} "
            f"- {rowcount} rows affected"
        )
        return rowcount

    def batch_upsert(
        self,
        filings: List[Dict[str, Any]],
        acquisition_id: Optional[int] = None,
        batch_size: int = 100,
    ) -> int:
        """Batch upsert multiple SGX filings.

        Args:
            filings: List of filing dicts
            acquisition_id: Stamp each row with this acquisition run ID
            batch_size: Records per batch (default: 100)

        Returns:
            Total number of affected rows

        Raises:
            ValueError: If filings list is empty
        """
        if not filings:
            raise ValueError("Cannot upsert empty filings list")

        total_affected = 0
        for i in range(0, len(filings), batch_size):
            batch = filings[i:i + batch_size]
            for filing in batch:
                if acquisition_id is not None:
                    filing['acquisition_id'] = acquisition_id
                affected = self.upsert(filing)
                total_affected += affected

            logger.info(
                f"Batch upsert: processed {len(batch)} filings "
                f"(batch {i // batch_size + 1})"
            )

        logger.info(
            f"Batch upsert complete: {len(filings)} filings, "
            f"{total_affected} total rows affected"
        )
        return total_affected

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_filings_for_symbol(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        subcategory_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get filings for a symbol with optional filters.

        Args:
            symbol: DR ticker symbol (e.g. 'DBS19')
            date_from: Start date filter (ISO format)
            date_to: End date filter (ISO format)
            subcategory_code: SGX subcategory filter (e.g. 'ANNC09')

        Returns:
            List of filing dicts, newest first
        """
        conditions = ["symbol = %s"]
        params: List[Any] = [symbol]

        if date_from:
            conditions.append("broadcast_date_time >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("broadcast_date_time <= %s")
            params.append(date_to)
        if subcategory_code:
            conditions.append("subcategory_code = %s")
            params.append(subcategory_code)

        query = f"""
            SELECT
                id, ticker_id, symbol, ann_id, broadcast_date_time,
                category_code, subcategory_code, subcategory_name,
                title, issuer_name, stock_code,
                attachment_url, sgx_url,
                raw_data, acquisition_id,
                fetched_at, created_at, updated_at
            FROM {SGX_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY broadcast_date_time DESC
        """

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_latest_filings(
        self,
        symbol: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get recent filings for a symbol.

        Args:
            symbol: DR ticker symbol
            days: Number of days to look back

        Returns:
            List of filing dicts, newest first
        """
        query = f"""
            SELECT
                id, ticker_id, symbol, ann_id, broadcast_date_time,
                category_code, subcategory_code, subcategory_name,
                title, issuer_name, stock_code,
                attachment_url, sgx_url,
                raw_data, acquisition_id,
                fetched_at, created_at, updated_at
            FROM {SGX_FILINGS}
            WHERE symbol = %s
              AND broadcast_date_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY broadcast_date_time DESC
        """

        rows = self.client.fetch_all(query, (symbol, days))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_by_acquisition(
        self,
        acquisition_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all filings from a specific acquisition run.

        Args:
            acquisition_id: FK to data_acquisitions table

        Returns:
            List of filing dicts from that run
        """
        query = f"""
            SELECT
                id, ticker_id, symbol, ann_id, broadcast_date_time,
                category_code, subcategory_code, subcategory_name,
                title, issuer_name, stock_code,
                attachment_url, sgx_url,
                raw_data, acquisition_id,
                fetched_at, created_at, updated_at
            FROM {SGX_FILINGS}
            WHERE acquisition_id = %s
            ORDER BY broadcast_date_time DESC
        """

        rows = self.client.fetch_all(query, (acquisition_id,))
        return [self._row_to_dict(row) for row in rows]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON and normalized dates."""
        result = dict(row)

        # Parse raw_data JSON
        if 'raw_data' in result and isinstance(result['raw_data'], str):
            result['raw_data'] = json.loads(result['raw_data'])

        # Convert datetimes to ISO strings for JSON serialization
        for dt_field in ('broadcast_date_time', 'fetched_at', 'created_at', 'updated_at'):
            if dt_field in result and isinstance(result[dt_field], (date, datetime)):
                result[dt_field] = result[dt_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[SgxFilingsRepository] = None


def get_sgx_filings_repository() -> SgxFilingsRepository:
    """Get singleton SgxFilingsRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = SgxFilingsRepository()
    return _repository_instance
