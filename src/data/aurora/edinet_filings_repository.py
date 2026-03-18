# -*- coding: utf-8 -*-
"""
EDINET Filings Repository

Data access layer for EDINET (Japan FSA) corporate filings.
Supports upsert via doc_id (EDINET's unique document ID) and
links each row to a shared acquisition provenance record.

Architecture:
    EDINET data pipeline -> this repository -> Aurora edinet_filings table
                                             -> Aurora data_acquisitions table (FK)

Design Principles:
    1. Idempotency: ON DUPLICATE KEY UPDATE on doc_id prevents duplicates
    2. Defensive Programming: Validate required fields before storage
    3. Provenance: Every row links to an acquisition run via acquisition_id
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import EDINET_FILINGS

logger = logging.getLogger(__name__)


class EdinetFilingsRepository:
    """Repository for EDINET filings data operations.

    Provides CRUD operations for EDINET corporate filings with
    acquisition provenance tracking.

    Example:
        >>> repo = EdinetFilingsRepository()
        >>> filing = {
        ...     'doc_id': 'S100ABC1',
        ...     'filing_date': '2026-03-15',
        ...     'filer_name': 'Nintendo',
        ...     'doc_type_code': '120',
        ...     'raw_data': {'full': 'response'},
        ... }
        >>> repo.upsert(filing)
    """

    REQUIRED_FIELDS = {
        'doc_id', 'filing_date', 'raw_data',
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
        """Upsert a single EDINET filing.

        Uses INSERT ... ON DUPLICATE KEY UPDATE on doc_id for idempotency.

        Args:
            filing: Filing data dict with required fields:
                - doc_id, filing_date, raw_data
            Optional fields:
                - ticker_id, symbol, edinet_code, sec_code
                - submit_date_time, doc_type_code, doc_description
                - filer_name, title, period_start, period_end
                - xbrl_flag, pdf_flag, english_doc_flag
                - pdf_url, pdf_s3_key, acquisition_id

        Returns:
            Number of affected rows (1 for insert, 2 for update)

        Raises:
            ValueError: If validation fails
        """
        self._validate_filing(filing)

        raw_data_json = json.dumps(filing['raw_data']) if isinstance(filing['raw_data'], dict) else filing['raw_data']

        query = f"""
            INSERT INTO {EDINET_FILINGS} (
                ticker_id, symbol,
                doc_id, edinet_code, sec_code,
                filing_date, submit_date_time,
                doc_type_code, doc_description,
                filer_name, title,
                period_start, period_end,
                xbrl_flag, pdf_flag, english_doc_flag,
                pdf_url, pdf_s3_key,
                raw_data, acquisition_id, fetched_at
            ) VALUES (
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                ticker_id = VALUES(ticker_id),
                symbol = VALUES(symbol),
                edinet_code = VALUES(edinet_code),
                sec_code = VALUES(sec_code),
                filing_date = VALUES(filing_date),
                submit_date_time = VALUES(submit_date_time),
                doc_type_code = VALUES(doc_type_code),
                doc_description = VALUES(doc_description),
                filer_name = VALUES(filer_name),
                title = VALUES(title),
                period_start = VALUES(period_start),
                period_end = VALUES(period_end),
                xbrl_flag = VALUES(xbrl_flag),
                pdf_flag = VALUES(pdf_flag),
                english_doc_flag = VALUES(english_doc_flag),
                pdf_url = VALUES(pdf_url),
                pdf_s3_key = VALUES(pdf_s3_key),
                raw_data = VALUES(raw_data),
                acquisition_id = VALUES(acquisition_id)
        """

        params = (
            filing.get('ticker_id'),
            filing.get('symbol'),
            filing['doc_id'],
            filing.get('edinet_code'),
            filing.get('sec_code'),
            filing['filing_date'],
            filing.get('submit_date_time'),
            filing.get('doc_type_code'),
            filing.get('doc_description'),
            filing.get('filer_name'),
            filing.get('title'),
            filing.get('period_start'),
            filing.get('period_end'),
            filing.get('xbrl_flag', False),
            filing.get('pdf_flag', False),
            filing.get('english_doc_flag', False),
            filing.get('pdf_url'),
            filing.get('pdf_s3_key'),
            raw_data_json,
            filing.get('acquisition_id'),
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted filing: {filing.get('symbol', 'N/A')} doc_id={filing['doc_id']} "
            f"- {rowcount} rows affected"
        )
        return rowcount

    def batch_upsert(
        self,
        filings: List[Dict[str, Any]],
        acquisition_id: Optional[int] = None,
        batch_size: int = 100,
    ) -> int:
        """Batch upsert multiple EDINET filings.

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

    _SELECT_COLUMNS = """
        id, ticker_id, symbol,
        doc_id, edinet_code, sec_code,
        filing_date, submit_date_time,
        doc_type_code, doc_description,
        filer_name, title,
        period_start, period_end,
        xbrl_flag, pdf_flag, english_doc_flag,
        pdf_url, pdf_s3_key,
        raw_data, acquisition_id,
        fetched_at, created_at, updated_at
    """

    def get_filings_for_date(
        self,
        filing_date: str,
        doc_type_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all filings for a specific date.

        Args:
            filing_date: Date string (ISO format, e.g. '2026-03-15')
            doc_type_code: Optional EDINET doc type filter (e.g. '120')

        Returns:
            List of filing dicts
        """
        conditions = ["filing_date = %s"]
        params: List[Any] = [filing_date]

        if doc_type_code:
            conditions.append("doc_type_code = %s")
            params.append(doc_type_code)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {EDINET_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY submit_date_time DESC
        """

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_for_symbol(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        doc_type_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get filings for a symbol with optional filters.

        Args:
            symbol: DR ticker symbol (e.g. 'NINTENDO19')
            date_from: Start date filter (ISO format)
            date_to: End date filter (ISO format)
            doc_type_code: EDINET doc type filter (e.g. '120')

        Returns:
            List of filing dicts, newest first
        """
        conditions = ["symbol = %s"]
        params: List[Any] = [symbol]

        if date_from:
            conditions.append("filing_date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("filing_date <= %s")
            params.append(date_to)
        if doc_type_code:
            conditions.append("doc_type_code = %s")
            params.append(doc_type_code)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {EDINET_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY filing_date DESC
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
            SELECT {self._SELECT_COLUMNS}
            FROM {EDINET_FILINGS}
            WHERE symbol = %s
              AND filing_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY filing_date DESC
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
            SELECT {self._SELECT_COLUMNS}
            FROM {EDINET_FILINGS}
            WHERE acquisition_id = %s
            ORDER BY filing_date DESC
        """

        rows = self.client.fetch_all(query, (acquisition_id,))
        return [self._row_to_dict(row) for row in rows]

    # =========================================================================
    # PDF Operations
    # =========================================================================

    def get_filings_needing_pdfs(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Get filings that have PDFs available but not yet archived to S3.

        Returns:
            List of dicts with doc_id and pdf_url, newest first
        """
        limit_clause = f"LIMIT {limit}" if limit > 0 else ""
        query = f"""
            SELECT doc_id, pdf_url, edinet_code, filer_name, filing_date
            FROM {EDINET_FILINGS}
            WHERE pdf_flag = TRUE
              AND pdf_s3_key IS NULL
              AND pdf_url IS NOT NULL
            ORDER BY filing_date DESC
            {limit_clause}
        """
        rows = self.client.fetch_all(query)
        return [dict(row) for row in rows]

    def update_pdf_s3_key(self, doc_id: str, s3_key: str) -> int:
        """Update the pdf_s3_key for a filing after archiving to S3.

        Args:
            doc_id: EDINET document ID
            s3_key: S3 key where PDF was archived

        Returns:
            Number of rows affected (1 if found, 0 if not)
        """
        query = f"""
            UPDATE {EDINET_FILINGS}
            SET pdf_s3_key = %s
            WHERE doc_id = %s
        """
        rowcount = self.client.execute(query, (s3_key, doc_id), commit=True)
        if rowcount > 0:
            logger.debug(f"Updated pdf_s3_key for doc_id={doc_id}: {s3_key}")
        return rowcount

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON and normalized dates."""
        result = dict(row)

        # Parse raw_data JSON
        if 'raw_data' in result and isinstance(result['raw_data'], str):
            result['raw_data'] = json.loads(result['raw_data'])

        # Convert datetimes/dates to ISO strings for JSON serialization
        for dt_field in (
            'filing_date', 'submit_date_time',
            'period_start', 'period_end',
            'fetched_at', 'created_at', 'updated_at',
        ):
            if dt_field in result and isinstance(result[dt_field], (date, datetime)):
                result[dt_field] = result[dt_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[EdinetFilingsRepository] = None


def get_edinet_filings_repository() -> EdinetFilingsRepository:
    """Get singleton EdinetFilingsRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = EdinetFilingsRepository()
    return _repository_instance
