# -*- coding: utf-8 -*-
"""Model Catalog Repository — read/write access to model_catalog table.

Syncs model metadata from OpenRouter and provides pricing lookups
for cost scoring. Falls back to model_pricing table when catalog
doesn't have a match.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import MODEL_CATALOG, MODEL_PRICING

logger = logging.getLogger(__name__)


class ModelCatalogRepository:
    """Repository for model_catalog table with in-memory cache.

    Cache lives for the Lambda warm start. Cold start triggers fresh DB queries.
    """

    def __init__(self, client=None):
        self.client = client or get_aurora_client()
        self._pricing_cache: Optional[Dict[str, Tuple[Decimal, Decimal]]] = None

    def upsert_models(self, models: List[Dict]) -> int:
        """Bulk upsert model metadata from OpenRouter.

        Uses INSERT ... ON DUPLICATE KEY UPDATE for idempotent sync.

        Args:
            models: List of dicts with keys: model_id, name, context_length,
                    input_price_per_token, output_price_per_token, modality,
                    tokenizer, provider, is_free, created_at_source, raw_json

        Returns:
            Number of rows affected (inserted + updated).
        """
        if not models:
            return 0

        query = f"""
            INSERT INTO {MODEL_CATALOG} (
                model_id, name, context_length,
                input_price_per_token, output_price_per_token,
                modality, tokenizer, provider, is_free,
                created_at_source, raw_json, synced_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, NOW()
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                context_length = VALUES(context_length),
                input_price_per_token = VALUES(input_price_per_token),
                output_price_per_token = VALUES(output_price_per_token),
                modality = VALUES(modality),
                tokenizer = VALUES(tokenizer),
                provider = VALUES(provider),
                is_free = VALUES(is_free),
                created_at_source = VALUES(created_at_source),
                raw_json = VALUES(raw_json),
                synced_at = NOW()
        """

        affected = 0
        for model in models:
            raw_json = json.dumps(model.get('raw_json')) if model.get('raw_json') else None

            params = (
                model['model_id'],
                model.get('name'),
                model.get('context_length'),
                model.get('input_price_per_token'),
                model.get('output_price_per_token'),
                model.get('modality'),
                model.get('tokenizer'),
                model.get('provider'),
                model.get('is_free', False),
                model.get('created_at_source'),
                raw_json,
            )

            rowcount = self.client.execute(query, params, commit=True)
            affected += rowcount if rowcount else 0

        # Invalidate pricing cache after sync
        self._pricing_cache = None
        logger.info(f"Upserted {len(models)} models ({affected} rows affected)")
        return affected

    def get_model(self, model_id: str) -> Optional[Dict]:
        """Get a single model by ID.

        Args:
            model_id: OpenRouter model ID (e.g. 'openai/gpt-4o')

        Returns:
            Model dict or None if not found.
        """
        query = f"SELECT * FROM {MODEL_CATALOG} WHERE model_id = %s"
        return self.client.fetch_one(query, (model_id,))

    def get_pricing(self, model_id: str) -> Optional[Tuple[Decimal, Decimal]]:
        """Get per-token pricing for a model.

        Lookup chain: model_catalog → model_pricing table.

        Args:
            model_id: OpenRouter model ID

        Returns:
            (input_price_per_token, output_price_per_token) or None.
        """
        # Try catalog first
        query = f"""
            SELECT input_price_per_token, output_price_per_token
            FROM {MODEL_CATALOG}
            WHERE model_id = %s
              AND input_price_per_token IS NOT NULL
        """
        row = self.client.fetch_one(query, (model_id,))
        if row:
            return (
                Decimal(str(row['input_price_per_token'])),
                Decimal(str(row['output_price_per_token'])),
            )

        # Fallback to model_pricing table
        fallback_query = f"""
            SELECT input_price_per_token, output_price_per_token
            FROM {MODEL_PRICING}
            WHERE model_id = %s
        """
        row = self.client.fetch_one(fallback_query, (model_id,))
        if row:
            return (
                Decimal(str(row['input_price_per_token'])),
                Decimal(str(row['output_price_per_token'])),
            )

        return None

    def get_performance_summary(
        self, trace_type: Optional[str] = None, min_samples: int = 5
    ) -> List[Dict]:
        """Get model performance summary from the view.

        Args:
            trace_type: Filter by trace type (e.g. 'report_generation').
                        None returns all types.
            min_samples: Minimum sample count to include.

        Returns:
            List of performance summary dicts.
        """
        query = """
            SELECT * FROM v_model_performance_summary
            WHERE sample_count >= %s
        """
        params: list = [min_samples]

        if trace_type:
            query += " AND trace_type = %s"
            params.append(trace_type)

        query += " ORDER BY quality_per_dollar DESC"

        return self.client.fetch_all(query, tuple(params))

    def get_all_models(
        self, provider: Optional[str] = None, modality: Optional[str] = None
    ) -> List[Dict]:
        """Get all models with optional filters.

        Args:
            provider: Filter by provider (e.g. 'openai')
            modality: Filter by modality (e.g. 'text->text')

        Returns:
            List of model dicts.
        """
        query = f"SELECT * FROM {MODEL_CATALOG} WHERE 1=1"
        params: list = []

        if provider:
            query += " AND provider = %s"
            params.append(provider)
        if modality:
            query += " AND modality = %s"
            params.append(modality)

        query += " ORDER BY provider, model_id"

        return self.client.fetch_all(query, tuple(params))

    def clear_cache(self):
        """Clear the in-memory pricing cache."""
        self._pricing_cache = None


# Singleton
_instance: Optional[ModelCatalogRepository] = None


def get_model_catalog_repository() -> ModelCatalogRepository:
    """Get singleton ModelCatalogRepository instance."""
    global _instance
    if _instance is None:
        _instance = ModelCatalogRepository()
    return _instance
