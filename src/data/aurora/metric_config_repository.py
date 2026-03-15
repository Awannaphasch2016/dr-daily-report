# -*- coding: utf-8 -*-
"""Metric Config Repository — read-only access to metric_config table.

The metric_config table is the sole source of truth for which metrics
are active in reports. All Lambda versions read from the same table,
ensuring consistency across deploys and rebuilds.
"""

import logging
from typing import Dict, Optional

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import METRIC_CONFIG

logger = logging.getLogger(__name__)


class MetricConfigRepository:
    """Read-only repository for metric configuration.

    Caches results for the lifetime of the singleton (Lambda warm start).
    Cold start triggers a fresh DB query.
    """

    def __init__(self, client=None):
        self.client = client or get_aurora_client()
        self._cache: Optional[Dict[str, str]] = None

    def get_all_statuses(self) -> Dict[str, str]:
        """Get {metric_id: status} for all metrics.

        Returns:
            Dict mapping metric_id to status string.
            Cached after first call (cleared on cold start).

        Example:
            >>> repo = MetricConfigRepository()
            >>> statuses = repo.get_all_statuses()
            >>> statuses['uncertainty']
            'deprecated'
            >>> statuses['rsi']
            'ready'
        """
        if self._cache is not None:
            return self._cache

        query = f"SELECT metric_id, status FROM {METRIC_CONFIG}"
        rows = self.client.fetch_all(query)
        self._cache = {row['metric_id']: row['status'] for row in rows}
        logger.info(f"Loaded {len(self._cache)} metric configs from DB")
        return self._cache

    def get_status(self, metric_id: str) -> Optional[str]:
        """Get status for a single metric.

        Args:
            metric_id: The metric identifier.

        Returns:
            Status string or None if not found.
        """
        return self.get_all_statuses().get(metric_id)

    def clear_cache(self):
        """Clear the in-memory cache (for testing or forced refresh)."""
        self._cache = None


# Singleton
_instance: Optional[MetricConfigRepository] = None


def get_metric_config_repository() -> MetricConfigRepository:
    """Get singleton MetricConfigRepository instance."""
    global _instance
    if _instance is None:
        _instance = MetricConfigRepository()
    return _instance
