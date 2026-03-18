# -*- coding: utf-8 -*-
"""Tests for ModelCatalogRepository."""

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.data.aurora.model_catalog_repository import ModelCatalogRepository


class TestModelCatalogRepository:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = ModelCatalogRepository(client=self.mock_client)

    # ---- upsert_models ----

    def test_upsert_models_executes_per_model(self):
        self.mock_client.execute.return_value = 1

        models = [
            {"model_id": "openai/gpt-4o", "name": "GPT-4o"},
            {"model_id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
        ]

        affected = self.repo.upsert_models(models)

        assert self.mock_client.execute.call_count == 2
        assert affected == 2

    def test_upsert_models_empty_list_returns_zero(self):
        affected = self.repo.upsert_models([])
        assert affected == 0
        self.mock_client.execute.assert_not_called()

    def test_upsert_models_serializes_raw_json(self):
        self.mock_client.execute.return_value = 1

        raw = {"id": "openai/gpt-4o", "pricing": {"prompt": "0.0025"}}
        models = [{"model_id": "openai/gpt-4o", "raw_json": raw}]

        self.repo.upsert_models(models)

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        # raw_json is the last param (index 10)
        assert params[10] == json.dumps(raw)

    def test_upsert_models_handles_null_raw_json(self):
        self.mock_client.execute.return_value = 1

        models = [{"model_id": "test/model", "raw_json": None}]
        self.repo.upsert_models(models)

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        assert params[10] is None

    def test_upsert_models_invalidates_pricing_cache(self):
        self.mock_client.execute.return_value = 1
        self.repo._pricing_cache = {"cached": "data"}

        self.repo.upsert_models([{"model_id": "test/model"}])

        assert self.repo._pricing_cache is None

    def test_upsert_models_passes_all_fields(self):
        self.mock_client.execute.return_value = 1

        model = {
            "model_id": "openai/gpt-4o",
            "name": "GPT-4o",
            "context_length": 128000,
            "input_price_per_token": Decimal("0.0000025"),
            "output_price_per_token": Decimal("0.00001"),
            "modality": "text+image->text",
            "tokenizer": "o200k_base",
            "provider": "openai",
            "is_free": False,
            "created_at_source": "2024-05-13 00:00:00",
            "raw_json": {"id": "openai/gpt-4o"},
        }

        self.repo.upsert_models([model])

        params = self.mock_client.execute.call_args[0][1]
        assert params[0] == "openai/gpt-4o"
        assert params[1] == "GPT-4o"
        assert params[2] == 128000
        assert params[3] == Decimal("0.0000025")
        assert params[4] == Decimal("0.00001")
        assert params[5] == "text+image->text"
        assert params[6] == "o200k_base"
        assert params[7] == "openai"
        assert params[8] is False

    # ---- get_model ----

    def test_get_model_returns_row(self):
        self.mock_client.fetch_one.return_value = {
            "model_id": "openai/gpt-4o",
            "name": "GPT-4o",
        }

        result = self.repo.get_model("openai/gpt-4o")

        assert result["model_id"] == "openai/gpt-4o"
        self.mock_client.fetch_one.assert_called_once()

    def test_get_model_returns_none_for_missing(self):
        self.mock_client.fetch_one.return_value = None

        result = self.repo.get_model("nonexistent/model")
        assert result is None

    # ---- get_pricing ----

    def test_get_pricing_from_catalog(self):
        self.mock_client.fetch_one.return_value = {
            "input_price_per_token": "0.0000025",
            "output_price_per_token": "0.00001",
        }

        result = self.repo.get_pricing("openai/gpt-4o")

        assert result == (Decimal("0.0000025"), Decimal("0.00001"))

    def test_get_pricing_fallback_to_model_pricing(self):
        # First call (catalog) returns None, second call (model_pricing) returns data
        self.mock_client.fetch_one.side_effect = [
            None,
            {
                "input_price_per_token": "0.000003",
                "output_price_per_token": "0.000012",
            },
        ]

        result = self.repo.get_pricing("openai/gpt-4o")

        assert result == (Decimal("0.000003"), Decimal("0.000012"))
        assert self.mock_client.fetch_one.call_count == 2

    def test_get_pricing_returns_none_when_not_found(self):
        self.mock_client.fetch_one.return_value = None

        result = self.repo.get_pricing("unknown/model")
        assert result is None

    # ---- get_performance_summary ----

    def test_get_performance_summary_queries_view(self):
        self.mock_client.fetch_all.return_value = [
            {
                "model_id": "openai/gpt-4o",
                "trace_type": "report_generation",
                "sample_count": 50,
                "quality_per_dollar": 42.5,
            }
        ]

        result = self.repo.get_performance_summary(
            trace_type="report_generation", min_samples=5
        )

        assert len(result) == 1
        assert result[0]["quality_per_dollar"] == 42.5

    def test_get_performance_summary_without_trace_type(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.get_performance_summary(min_samples=10)

        query = self.mock_client.fetch_all.call_args[0][0]
        assert "trace_type" not in query.split("WHERE")[1].split("ORDER")[0]

    def test_get_performance_summary_with_trace_type_filter(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.get_performance_summary(trace_type="report_generation")

        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert "trace_type = %s" in query
        assert "report_generation" in params

    # ---- get_all_models ----

    def test_get_all_models_no_filter(self):
        self.mock_client.fetch_all.return_value = [
            {"model_id": "openai/gpt-4o"},
            {"model_id": "anthropic/claude-3.5-sonnet"},
        ]

        result = self.repo.get_all_models()
        assert len(result) == 2

    def test_get_all_models_with_provider_filter(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.get_all_models(provider="openai")

        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert "provider = %s" in query
        assert "openai" in params

    def test_get_all_models_with_modality_filter(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.get_all_models(modality="text->text")

        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert "modality = %s" in query
        assert "text->text" in params

    def test_get_all_models_with_both_filters(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.get_all_models(provider="openai", modality="text+image->text")

        params = self.mock_client.fetch_all.call_args[0][1]
        assert params == ("openai", "text+image->text")

    # ---- clear_cache ----

    def test_clear_cache(self):
        self.repo._pricing_cache = {"some": "data"}
        self.repo.clear_cache()
        assert self.repo._pricing_cache is None


class TestGetModelCatalogRepository:
    def test_singleton_returns_same_instance(self):
        from src.data.aurora import model_catalog_repository as mod

        # Reset singleton
        mod._instance = None

        mock_client = MagicMock()
        repo1 = ModelCatalogRepository(client=mock_client)
        mod._instance = repo1

        repo2 = mod.get_model_catalog_repository()
        assert repo2 is repo1

        # Clean up
        mod._instance = None
