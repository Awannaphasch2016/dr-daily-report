# -*- coding: utf-8 -*-
"""
Data Acquisitions Repository

Data access layer for the shared acquisition provenance table.
Tracks WHO (tool identity), WHAT (code version in S3), WHERE (endpoint),
and HOW IT WENT (run metrics) for every data acquisition.

Architecture:
    Any data pipeline → this repository → Aurora data_acquisitions table

Design Principles:
    1. Run lifecycle: start_run → (pipeline work) → complete_run / fail_run
    2. Defensive Programming: Validate source_type enum
    3. Idempotent queries: Safe to call multiple times
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import DATA_ACQUISITIONS

logger = logging.getLogger(__name__)

ALLOWED_SOURCE_TYPES = {'script', 'service', 'export', 'manual'}
ALLOWED_STATUSES = {'running', 'success', 'partial', 'failed'}


class DataAcquisitionsRepository:
    """Repository for data acquisition provenance tracking.

    Provides lifecycle management for acquisition runs:
    start_run → (pipeline populates target table) → complete_run / fail_run

    Example:
        >>> repo = DataAcquisitionsRepository()
        >>> acq_id = repo.start_run(
        ...     source_table='sgx_filings',
        ...     source_type='script',
        ...     source_name='sgx_financial_reports_scraper',
        ...     source_version='v2_2026-03-20',
        ...     artifact_s3_key='scripts/data-acquisition/sgx-financial-reports/v2.py',
        ...     endpoint_url='https://api.sgx.com/financialreports/v1.0',
        ...     endpoint_version='v1.0',
        ...     description='Backfill all DR ticker financial reports',
        ...     parameters={'pagesize': 250, 'companies': ['DBS', 'OCBC']}
        ... )
        >>> # ... do pipeline work ...
        >>> repo.complete_run(acq_id, records_fetched=12670, records_upserted=47)
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    def start_run(
        self,
        source_table: str,
        source_type: str,
        source_name: str,
        source_version: Optional[str] = None,
        artifact_s3_key: Optional[str] = None,
        artifact_checksum: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        endpoint_version: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Start a new acquisition run.

        Args:
            source_table: Target table being populated (e.g. 'sgx_filings')
            source_type: Tool type ('script', 'service', 'export', 'manual')
            source_name: Tool identity (e.g. 'sgx_financial_reports_scraper')
            source_version: Tool version tag (e.g. 'v2_2026-03-20')
            artifact_s3_key: S3 key to the script/code artifact
            artifact_checksum: SHA256 of the artifact file
            endpoint_url: API endpoint or data source URL
            endpoint_version: API version (e.g. 'v1.0')
            description: Human-readable description
            parameters: Request parameters / config used

        Returns:
            acquisition_id (BIGINT) for the new run

        Raises:
            ValueError: If source_type is not allowed
        """
        if source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source_type '{source_type}'. "
                f"Allowed: {sorted(ALLOWED_SOURCE_TYPES)}"
            )

        params_json = json.dumps(parameters) if parameters else None

        query = f"""
            INSERT INTO {DATA_ACQUISITIONS} (
                source_table, source_type, source_name, source_version,
                artifact_s3_key, artifact_checksum,
                endpoint_url, endpoint_version,
                description, parameters,
                status, started_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                'running', NOW()
            )
        """
        params = (
            source_table, source_type, source_name, source_version,
            artifact_s3_key, artifact_checksum,
            endpoint_url, endpoint_version,
            description, params_json,
        )

        self.client.execute(query, params, commit=True)

        result = self.client.fetch_one("SELECT LAST_INSERT_ID() AS id")
        acquisition_id = result['id']

        logger.info(
            f"Started acquisition run {acquisition_id}: "
            f"source={source_type}:{source_name}:{source_version}, "
            f"target={source_table}"
        )
        return acquisition_id

    def complete_run(
        self,
        acquisition_id: int,
        records_fetched: int,
        records_upserted: int,
        status: str = 'success',
    ) -> None:
        """Complete an acquisition run with metrics.

        Args:
            acquisition_id: Run ID from start_run()
            records_fetched: Total records obtained from source
            records_upserted: Records written to target table
            status: Final status ('success' or 'partial')

        Raises:
            ValueError: If status is not 'success' or 'partial'
        """
        if status not in ('success', 'partial'):
            raise ValueError(
                f"complete_run status must be 'success' or 'partial', got '{status}'"
            )

        query = f"""
            UPDATE {DATA_ACQUISITIONS}
            SET records_fetched = %s,
                records_upserted = %s,
                status = %s,
                completed_at = NOW()
            WHERE id = %s
        """
        rowcount = self.client.execute(
            query, (records_fetched, records_upserted, status, acquisition_id),
            commit=True,
        )

        if rowcount == 0:
            raise ValueError(f"Acquisition run {acquisition_id} not found")

        logger.info(
            f"Completed acquisition run {acquisition_id}: "
            f"fetched={records_fetched}, upserted={records_upserted}, status={status}"
        )

    def fail_run(
        self,
        acquisition_id: int,
        error_message: str,
        records_fetched: int = 0,
        records_upserted: int = 0,
    ) -> None:
        """Mark an acquisition run as failed.

        Args:
            acquisition_id: Run ID from start_run()
            error_message: Error details
            records_fetched: Records obtained before failure
            records_upserted: Records written before failure
        """
        query = f"""
            UPDATE {DATA_ACQUISITIONS}
            SET status = 'failed',
                error_message = %s,
                records_fetched = %s,
                records_upserted = %s,
                completed_at = NOW()
            WHERE id = %s
        """
        rowcount = self.client.execute(
            query, (error_message, records_fetched, records_upserted, acquisition_id),
            commit=True,
        )

        if rowcount == 0:
            raise ValueError(f"Acquisition run {acquisition_id} not found")

        logger.warning(
            f"Failed acquisition run {acquisition_id}: {error_message}"
        )

    def get_runs(
        self,
        source_table: Optional[str] = None,
        source_type: Optional[str] = None,
        source_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query acquisition runs with optional filters.

        Args:
            source_table: Filter by target table
            source_type: Filter by tool type
            source_name: Filter by tool name
            status: Filter by run status
            limit: Max rows to return

        Returns:
            List of acquisition run dicts, newest first
        """
        conditions = []
        params: List[Any] = []

        if source_table:
            conditions.append("source_table = %s")
            params.append(source_table)
        if source_type:
            if source_type not in ALLOWED_SOURCE_TYPES:
                raise ValueError(f"Invalid source_type: {source_type}")
            conditions.append("source_type = %s")
            params.append(source_type)
        if source_name:
            conditions.append("source_name = %s")
            params.append(source_name)
        if status:
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"Invalid status: {status}")
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, source_table,
                   source_type, source_name, source_version,
                   artifact_s3_key, artifact_checksum,
                   endpoint_url, endpoint_version,
                   description, parameters,
                   records_fetched, records_upserted,
                   status, error_message,
                   started_at, completed_at, created_at
            FROM {DATA_ACQUISITIONS}
            {where_clause}
            ORDER BY started_at DESC
            LIMIT %s
        """
        params.append(limit)

        rows = self.client.fetch_all(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON."""
        result = dict(row)

        if 'parameters' in result and isinstance(result['parameters'], str):
            result['parameters'] = json.loads(result['parameters'])

        for ts_field in ('started_at', 'completed_at', 'created_at'):
            if ts_field in result and isinstance(result[ts_field], datetime):
                result[ts_field] = result[ts_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[DataAcquisitionsRepository] = None


def get_data_acquisitions_repository() -> DataAcquisitionsRepository:
    """Get singleton DataAcquisitionsRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = DataAcquisitionsRepository()
    return _repository_instance
