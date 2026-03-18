# -*- coding: utf-8 -*-
"""
HKEX Filings Repository

Data access layer for HKEX (Hong Kong Exchange) corporate filings.
Supports upsert via news_id (HKEXnews unique identifier) and
links each row to a shared acquisition provenance record.
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import HKEX_FILINGS

logger = logging.getLogger(__name__)


class HkexFilingsRepository:
    """Repository for HKEX filings data operations."""

    REQUIRED_FIELDS = {
        'news_id', 'stock_code', 'filing_date', 'raw_data',
    }

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    def _validate_filing(self, filing: Dict[str, Any]) -> None:
        missing = self.REQUIRED_FIELDS - set(filing.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    def upsert(self, filing: Dict[str, Any]) -> int:
        """Upsert a single HKEX filing via INSERT ... ON DUPLICATE KEY UPDATE on news_id."""
        self._validate_filing(filing)

        raw_data_json = json.dumps(filing['raw_data']) if isinstance(filing['raw_data'], dict) else filing['raw_data']

        query = f"""
            INSERT INTO {HKEX_FILINGS} (
                ticker_id, symbol,
                news_id, stock_code,
                filing_date, date_time, category_code, subcategory_code,
                stock_name, title, long_text,
                file_link, file_url, file_type, pdf_s3_key,
                raw_data, acquisition_id, fetched_at
            ) VALUES (
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                ticker_id = VALUES(ticker_id),
                symbol = VALUES(symbol),
                stock_code = VALUES(stock_code),
                filing_date = VALUES(filing_date),
                date_time = VALUES(date_time),
                category_code = VALUES(category_code),
                subcategory_code = VALUES(subcategory_code),
                stock_name = VALUES(stock_name),
                title = VALUES(title),
                long_text = VALUES(long_text),
                file_link = VALUES(file_link),
                file_url = VALUES(file_url),
                file_type = VALUES(file_type),
                pdf_s3_key = VALUES(pdf_s3_key),
                raw_data = VALUES(raw_data),
                acquisition_id = VALUES(acquisition_id)
        """

        params = (
            filing.get('ticker_id'),
            filing.get('symbol'),
            filing['news_id'],
            filing['stock_code'],
            filing['filing_date'],
            filing.get('date_time'),
            filing.get('category_code'),
            filing.get('subcategory_code'),
            filing.get('stock_name'),
            filing.get('title'),
            filing.get('long_text'),
            filing.get('file_link'),
            filing.get('file_url'),
            filing.get('file_type'),
            filing.get('pdf_s3_key'),
            raw_data_json,
            filing.get('acquisition_id'),
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted filing: {filing.get('symbol', 'N/A')} "
            f"news_id={filing['news_id']} - {rowcount} rows affected"
        )
        return rowcount

    def batch_upsert(
        self,
        filings: List[Dict[str, Any]],
        acquisition_id: Optional[int] = None,
        batch_size: int = 100,
    ) -> int:
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

    _SELECT_COLUMNS = """
        id, ticker_id, symbol,
        news_id, stock_code,
        filing_date, date_time, category_code, subcategory_code,
        stock_name, title, long_text,
        file_link, file_url, file_type, pdf_s3_key,
        raw_data, acquisition_id,
        fetched_at, created_at, updated_at
    """

    def get_filings_for_symbol(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        subcategory_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conditions = ["symbol = %s"]
        params: List[Any] = [symbol]

        if date_from:
            conditions.append("filing_date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("filing_date <= %s")
            params.append(date_to)
        if subcategory_code:
            conditions.append("subcategory_code = %s")
            params.append(subcategory_code)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {HKEX_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY filing_date DESC
        """
        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_for_stock_code(
        self,
        stock_code: str,
        subcategory_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conditions = ["stock_code = %s"]
        params: List[Any] = [stock_code]

        if subcategory_code:
            conditions.append("subcategory_code = %s")
            params.append(subcategory_code)

        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {HKEX_FILINGS}
            WHERE {' AND '.join(conditions)}
            ORDER BY filing_date DESC
        """
        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_latest_filings(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {HKEX_FILINGS}
            WHERE symbol = %s
              AND filing_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY filing_date DESC
        """
        rows = self.client.fetch_all(query, (symbol, days))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_by_acquisition(self, acquisition_id: int) -> List[Dict[str, Any]]:
        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM {HKEX_FILINGS}
            WHERE acquisition_id = %s
            ORDER BY filing_date DESC
        """
        rows = self.client.fetch_all(query, (acquisition_id,))
        return [self._row_to_dict(row) for row in rows]

    def get_filings_needing_docs(self, limit: int = 0) -> List[Dict[str, Any]]:
        limit_clause = f"LIMIT {limit}" if limit > 0 else ""
        query = f"""
            SELECT news_id, stock_code, file_url, stock_name, filing_date
            FROM {HKEX_FILINGS}
            WHERE file_url IS NOT NULL
              AND pdf_s3_key IS NULL
            ORDER BY filing_date DESC
            {limit_clause}
        """
        rows = self.client.fetch_all(query)
        return [dict(row) for row in rows]

    def update_pdf_s3_key(self, news_id: str, s3_key: str) -> int:
        query = f"UPDATE {HKEX_FILINGS} SET pdf_s3_key = %s WHERE news_id = %s"
        rowcount = self.client.execute(query, (s3_key, news_id), commit=True)
        if rowcount > 0:
            logger.debug(f"Updated pdf_s3_key for news_id={news_id}: {s3_key}")
        return rowcount

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(row)

        if 'raw_data' in result and isinstance(result['raw_data'], str):
            result['raw_data'] = json.loads(result['raw_data'])

        for dt_field in ('filing_date', 'fetched_at', 'created_at', 'updated_at'):
            if dt_field in result and isinstance(result[dt_field], (date, datetime)):
                result[dt_field] = result[dt_field].isoformat()

        return result


_repository_instance: Optional[HkexFilingsRepository] = None


def get_hkex_filings_repository() -> HkexFilingsRepository:
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = HkexFilingsRepository()
    return _repository_instance
