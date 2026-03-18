# -*- coding: utf-8 -*-
"""
Ingestion Methods Repository

Registry of HOW data gets fetched — tracks the infrastructure and
tooling used for each data acquisition approach.

Architecture:
    ingestion_methods table ← data_acquisitions.ingestion_method_id FK

Design Principles:
    1. Idempotency: get_or_create prevents duplicates on method_name
    2. Defensive Programming: Validate runtime_type before storage
    3. Provenance: Links methods to acquisition runs for full traceability
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import INGESTION_METHODS

logger = logging.getLogger(__name__)

ALLOWED_RUNTIME_TYPES = {
    'ecs_fargate', 'lambda', 'local', 'step_functions', 'github_actions',
}


class IngestionMethodsRepository:
    """Repository for ingestion method registry.

    Provides CRUD operations for the ingestion methods table,
    which tracks different approaches used to fetch data.

    Example:
        >>> repo = IngestionMethodsRepository()
        >>> method_id = repo.get_or_create(
        ...     method_name='edinet-ecs-fargate-backfill',
        ...     runtime_type='ecs_fargate',
        ...     script_path='scripts/ingest_edinet_filings.py',
        ... )
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    def create(
        self,
        method_name: str,
        runtime_type: str,
        script_path: Optional[str] = None,
        container_image: Optional[str] = None,
        description: Optional[str] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new ingestion method.

        Args:
            method_name: Unique name (e.g. 'edinet-ecs-fargate-backfill')
            runtime_type: One of: ecs_fargate, lambda, local, step_functions, github_actions
            script_path: Path to script in repo
            container_image: Full Docker image URI with tag
            description: Human-readable explanation
            config_snapshot: Infrastructure config (cpu, memory, cluster, etc.)

        Returns:
            id of the created method

        Raises:
            ValueError: If runtime_type is invalid
        """
        if runtime_type not in ALLOWED_RUNTIME_TYPES:
            raise ValueError(
                f"Invalid runtime_type '{runtime_type}'. "
                f"Allowed: {sorted(ALLOWED_RUNTIME_TYPES)}"
            )

        config_json = json.dumps(config_snapshot) if config_snapshot else None

        query = f"""
            INSERT INTO {INGESTION_METHODS} (
                method_name, runtime_type, script_path,
                container_image, description, config_snapshot
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            method_name, runtime_type, script_path,
            container_image, description, config_json,
        )

        self.client.execute(query, params, commit=True)
        result = self.client.fetch_one("SELECT LAST_INSERT_ID() AS id")
        method_id = result['id']

        logger.info(f"Created ingestion method {method_id}: {method_name} ({runtime_type})")
        return method_id

    def get_by_name(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get an ingestion method by name.

        Args:
            method_name: Unique method name

        Returns:
            Method dict or None if not found
        """
        query = f"""
            SELECT id, method_name, runtime_type, script_path,
                   container_image, description, config_snapshot,
                   is_active, created_at, updated_at
            FROM {INGESTION_METHODS}
            WHERE method_name = %s
        """
        row = self.client.fetch_one(query, (method_name,))
        return self._row_to_dict(row) if row else None

    def get_or_create(
        self,
        method_name: str,
        runtime_type: str,
        script_path: Optional[str] = None,
        container_image: Optional[str] = None,
        description: Optional[str] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get existing method or create new one. Idempotent on method_name.

        Returns:
            Method dict (existing or newly created)
        """
        existing = self.get_by_name(method_name)
        if existing:
            return existing

        method_id = self.create(
            method_name=method_name,
            runtime_type=runtime_type,
            script_path=script_path,
            container_image=container_image,
            description=description,
            config_snapshot=config_snapshot,
        )
        return self.get_by_name(method_name)

    def list_active(self) -> List[Dict[str, Any]]:
        """List all active ingestion methods.

        Returns:
            List of method dicts, newest first
        """
        query = f"""
            SELECT id, method_name, runtime_type, script_path,
                   container_image, description, config_snapshot,
                   is_active, created_at, updated_at
            FROM {INGESTION_METHODS}
            WHERE is_active = TRUE
            ORDER BY created_at DESC
        """
        rows = self.client.fetch_all(query)
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dict with parsed JSON."""
        result = dict(row)

        if 'config_snapshot' in result and isinstance(result['config_snapshot'], str):
            result['config_snapshot'] = json.loads(result['config_snapshot'])

        for ts_field in ('created_at', 'updated_at'):
            if ts_field in result and isinstance(result[ts_field], datetime):
                result[ts_field] = result[ts_field].isoformat()

        return result


# =============================================================================
# Module-level singleton (lazy initialization)
# =============================================================================

_repository_instance: Optional[IngestionMethodsRepository] = None


def get_ingestion_methods_repository() -> IngestionMethodsRepository:
    """Get singleton IngestionMethodsRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = IngestionMethodsRepository()
    return _repository_instance
