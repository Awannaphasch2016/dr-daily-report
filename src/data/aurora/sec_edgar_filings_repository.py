# -*- coding: utf-8 -*-
"""
SEC EDGAR Filings Repository

Data access layer for SEC EDGAR (US) corporate filings.
Supports upsert via accession_number (SEC's unique filing ID) and
links each row to a shared acquisition provenance record.

Architecture:
    SEC EDGAR data pipeline -> this repository -> Aurora sec_edgar_filings table
                                                -> Aurora data_acquisitions table (FK)

Design Principles:
    1. Idempotency: ON DUPLICATE KEY UPDATE on accession_number prevents duplicates
    2. Defensive Programming: Validate required fields before storage
    3. Provenance: Every row links to an acquisition run via acquisition_id
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import SEC_EDGAR_FILINGS

logger = logging.getLogger(__name__)


class SecEdgarFilingsRepository:
    """Repository for SEC EDGAR filings data operations.

    Example:
        >>> repo = SecEdgarFilingsRepository()
        >>> filing = {
        ...     'accession_number': '0000320193-24-000123',
        ...     'cik': '320193',
        ...     'filing_date': '2024-11-01',
        ...     'raw_data': {'full': 'response'},
        ... }
        >>> repo.upsert(filing)
    """

    REQUIRED_FIELDS = {
        'accession_number', 'cik', 'filing_date', 'raw_data',
    }

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    # =========================================================================
    # Validation (Principle #1: Defensive Programming)
    # =========================================================================

    def _validate_filing(self, filing: Dict[str, Any]) -> None:
        """Validate filing data before storage."""
        missing = self.REQUIRED_FIELDS - set(filing.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    # =========================================================================
    # Upsert Operations
    # =========================================================================

    def upsert(self, filing: Dict[str, Any]) -> int:
        """Upsert a single SEC EDGAR filing.

        Uses INSERT ... ON DUPLICATE KEY UPDATE on accession_number for idempotency.

        Returns:
            Number of affected rows (1 for insert, 2 for update)
        """
        self._validate_filing(filing)

        raw_data_json = json.dumps(filing['raw_data']) if isinstance(filing['raw_data'], dict) else filing['raw_data']

        query = f"""
            INSERT INTO {SEC_EDGAR_FILINGS} (
                ticker_id, symbol,
                accession_number, cik,
                form_type, filing_date, report_date, acceptance_datetime,
                company_name, title,
                primary_document, primary_doc_url, filing_index_url, pdf_s3_key,
                raw_data, acquisition_id, fetched_at
            ) VALUES (
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                ticker_id = VALUES(ticker_id),
                symbol = VALUES(symbol),
                cik = VALUES(cik),
                form_type = VALUES(form_type),
                filing_date = VALUES(filing_date),
                report_date = VALUES(report_date),
                acceptance_datetime = VALUES(acceptance_datetime),
                company_name = VALUES(company_name),
                title = VALUES(title),
                primary_document = VALUES(primary_document),
                primary_doc_url = VALUES(primary_doc_url),
                filing_index_url = VALUES(filing_index_url),
                pdf_s3_key = VALUES(pdf_s3_key),
                raw_data = VALUES(raw_data),
                acquisition_id = VALUES(acquisition_id)
        """

        params = (
            filing.get('ticker_id'),
            filing.get('symbol'),
            filing['accession_number'],
            filing['cik'],
            filing.get('form_type'),
            filing['filing_date'],
            filing.get('report_date'),
            filing.get('acceptance_datetime'),
            filing.get('company_name'),
            filing.get('title'),
            filing.get('primary_document'),
            filing.get('primary_doc_url'),
            filing.get('filing_index_url'),
            filing.get('pdf_s3_key'),
            raw_data_json,
            filing.get('acquisition_id'),
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted filing: {filing.get('symbol', 'N/A')} "
            f"accession={filing['accession_number']} - {rowcount} rows affected"
        )
        return rowcount

    def batch_upsert(
        self,
        filings: List[Dict[str, Any]],
        acquisition_id: Optional[int] = None,
        batch_size: int = 100,
    ) -> int:
        """Batch upsert multiple SEC EDGAR filings."""
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
        accession_number, cik,
        form_type, filing_date, report_date, acceptance_datetime,
        company_name, title,
        primary_document, primary_doc_url, filing_index_url, pdf_s3_key,
        raw_data, acquisition_id,
        fetched_at, created_at, updated_at
    """

    def get_filings_for_symbol(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        form_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get filings for a symbol with optional filters."""
        conditions = ["symbol = %s"]
        params: List[Any] = [symbol]

        if date_from:
            conditions.append("filing_date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("filing_date <= %s")
            params.append(date_to)
        if form_type:
            conditions.append("form_type = %s")
            params.append(form_type)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {SEC_EDGAR_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY filing_date DESC
        """

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_for_cik(
        self,
        cik: str,
        form_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get filings for a CIK with optional form type filter."""
        conditions = ["cik = %s"]
        params: List[Any] = [cik]

        if form_type:
            conditions.append("form_type = %s")
            params.append(form_type)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {SEC_EDGAR_FILINGS}
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
        """Get recent filings for a symbol."""
        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {SEC_EDGAR_FILINGS}
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
        """Get all filings from a specific acquisition run."""
        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {SEC_EDGAR_FILINGS}
            WHERE acquisition_id = %s
            ORDER BY filing_date DESC
        """

        rows = self.client.fetch_all(query, (acquisition_id,))
        return [self._row_to_dict(row) for row in rows]

    # =========================================================================
    # Document Operations
    # =========================================================================

    def get_filings_needing_docs(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Get filings that have documents but not yet archived to S3."""
        limit_clause = f"LIMIT {limit}" if limit > 0 else ""
        query = f"""
            SELECT accession_number, cik, primary_doc_url, company_name, filing_date
            FROM {SEC_EDGAR_FILINGS}
            WHERE primary_doc_url IS NOT NULL
              AND pdf_s3_key IS NULL
            ORDER BY filing_date DESC
            {limit_clause}
        """
        rows = self.client.fetch_all(query)
        return [dict(row) for row in rows]

    def update_pdf_s3_key(self, accession_number: str, s3_key: str) -> int:
        """Update the pdf_s3_key for a filing after archiving to S3."""
        query = f"""
            UPDATE {SEC_EDGAR_FILINGS}
            SET pdf_s3_key = %s
            WHERE accession_number = %s
        """
        rowcount = self.client.execute(query, (s3_key, accession_number), commit=True)
        if rowcount > 0:
            logger.debug(f"Updated pdf_s3_key for accession={accession_number}: {s3_key}")
        return rowcount

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON and normalized dates."""
        result = dict(row)

        if 'raw_data' in result and isinstance(result['raw_data'], str):
            result['raw_data'] = json.loads(result['raw_data'])

        for dt_field in (
            'filing_date', 'report_date', 'acceptance_datetime',
            'fetched_at', 'created_at', 'updated_at',
        ):
            if dt_field in result and isinstance(result[dt_field], (date, datetime)):
                result[dt_field] = result[dt_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[SecEdgarFilingsRepository] = None


def get_sec_edgar_filings_repository() -> SecEdgarFilingsRepository:
    """Get singleton SecEdgarFilingsRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = SecEdgarFilingsRepository()
    return _repository_instance
