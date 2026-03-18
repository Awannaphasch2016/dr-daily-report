"""Tests for model catalog sync Lambda handler.

Tests the OpenRouter API fetching, model transformation, and database
upsert pipeline.
Follows Principle #10 (Testing Anti-Patterns): No external calls, deterministic data.
"""

import json
import os

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO
from urllib.error import HTTPError, URLError


# Set required env vars before import
@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv("AURORA_HOST", "test-aurora-host")
    monkeypatch.setenv("AURORA_PORT", "3306")
    monkeypatch.setenv("AURORA_DATABASE", "test_db")
    monkeypatch.setenv("AURORA_USER", "test_user")
    monkeypatch.setenv("AURORA_PASSWORD", "test_pass")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    # Reload module-level constants
    import importlib
    import src.alerting.model_catalog_sync as mod
    importlib.reload(mod)


from src.alerting.model_catalog_sync import (
    _validate_config,
    _fetch_openrouter_models,
    _parse_price,
    _extract_provider,
    _parse_created_at,
    _transform_models,
    lambda_handler,
)


class TestValidateConfig:
    def test_valid_config_passes(self):
        _validate_config()  # Should not raise

    def test_missing_aurora_host_raises(self, monkeypatch):
        monkeypatch.delenv("AURORA_HOST")
        import importlib
        import src.alerting.model_catalog_sync as mod
        importlib.reload(mod)
        with pytest.raises(RuntimeError, match="AURORA_HOST"):
            mod._validate_config()

    def test_missing_multiple_vars_listed(self, monkeypatch):
        monkeypatch.delenv("AURORA_HOST")
        monkeypatch.delenv("AURORA_DATABASE")
        import importlib
        import src.alerting.model_catalog_sync as mod
        importlib.reload(mod)
        with pytest.raises(RuntimeError, match="AURORA_HOST.*AURORA_DATABASE"):
            mod._validate_config()


class TestFetchOpenrouterModels:
    def _mock_response(self, data: dict):
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode("utf-8")
        response.status = 200
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_returns_model_list(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({
            "data": [
                {"id": "openai/gpt-4o", "name": "GPT-4o"},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            ]
        })

        models = _fetch_openrouter_models()
        assert len(models) == 2
        assert models[0]["id"] == "openai/gpt-4o"

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_empty_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({"data": []})

        with pytest.raises(ValueError, match="empty model list"):
            _fetch_openrouter_models()

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_connection_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection timed out")

        with pytest.raises(URLError):
            _fetch_openrouter_models()

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_http_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            "https://openrouter.ai", 500, "Server Error", {}, BytesIO(b"")
        )

        with pytest.raises(HTTPError):
            _fetch_openrouter_models()


class TestParsePrice:
    def test_valid_price_string(self):
        assert _parse_price("0.0000025") == Decimal("0.0000025")

    def test_zero_price(self):
        assert _parse_price("0") == Decimal("0")

    def test_none_returns_none(self):
        assert _parse_price(None) is None

    def test_invalid_string_returns_none(self):
        assert _parse_price("free") is None


class TestExtractProvider:
    def test_standard_model_id(self):
        assert _extract_provider("openai/gpt-4o") == "openai"

    def test_nested_model_id(self):
        assert _extract_provider("meta-llama/llama-3-70b") == "meta-llama"

    def test_no_slash_returns_none(self):
        assert _extract_provider("gpt-4o") is None


class TestParseCreatedAt:
    def test_valid_timestamp(self):
        # 2024-05-13T00:00:00Z = 1715558400
        result = _parse_created_at(1715558400)
        assert result == "2024-05-13 00:00:00"

    def test_none_returns_none(self):
        assert _parse_created_at(None) is None

    def test_invalid_timestamp_returns_none(self):
        assert _parse_created_at("not-a-timestamp") is None


class TestTransformModels:
    def test_transforms_full_model(self):
        raw = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "architecture": {"modality": "text+image->text", "tokenizer": "o200k_base"},
                "created": 1715558400,
            }
        ]

        result = _transform_models(raw)

        assert len(result) == 1
        m = result[0]
        assert m["model_id"] == "openai/gpt-4o"
        assert m["name"] == "GPT-4o"
        assert m["context_length"] == 128000
        assert m["input_price_per_token"] == Decimal("0.0000025")
        assert m["output_price_per_token"] == Decimal("0.00001")
        assert m["modality"] == "text+image->text"
        assert m["tokenizer"] == "o200k_base"
        assert m["provider"] == "openai"
        assert m["is_free"] is False

    def test_skips_models_without_id(self):
        raw = [
            {"name": "No ID Model"},
            {"id": "valid/model", "name": "Valid"},
        ]

        result = _transform_models(raw)
        assert len(result) == 1
        assert result[0]["model_id"] == "valid/model"

    def test_free_model_detected(self):
        raw = [
            {
                "id": "free/model",
                "pricing": {"prompt": "0", "completion": "0"},
            }
        ]

        result = _transform_models(raw)
        assert result[0]["is_free"] is True

    def test_missing_pricing_handled(self):
        raw = [{"id": "test/model"}]

        result = _transform_models(raw)
        assert result[0]["input_price_per_token"] is None
        assert result[0]["output_price_per_token"] is None

    def test_missing_architecture_handled(self):
        raw = [{"id": "test/model"}]

        result = _transform_models(raw)
        assert result[0]["modality"] is None
        assert result[0]["tokenizer"] is None

    def test_raw_json_preserved(self):
        raw_entry = {"id": "test/model", "extra_field": "value"}
        result = _transform_models([raw_entry])
        assert result[0]["raw_json"] == raw_entry


class TestLambdaHandler:
    def _mock_response(self, data: dict):
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode("utf-8")
        response.status = 200
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch("src.data.aurora.model_catalog_repository.get_model_catalog_repository")
    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_happy_path(self, mock_urlopen, mock_get_repo):
        mock_urlopen.return_value = self._mock_response({
            "data": [
                {"id": "openai/gpt-4o", "name": "GPT-4o", "pricing": {"prompt": "0.0025", "completion": "0.01"}},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5", "pricing": {"prompt": "0.003", "completion": "0.015"}},
            ]
        })

        mock_repo = MagicMock()
        mock_repo.upsert_models.return_value = 4
        mock_get_repo.return_value = mock_repo

        result = lambda_handler({"source": "test"}, None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["fetched"] == 2
        assert body["transformed"] == 2
        assert body["db_affected"] == 4

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_openrouter_down_returns_502(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection timed out")

        result = lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 502

    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_empty_response_returns_502(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({"data": []})

        result = lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 502

    @patch("src.data.aurora.model_catalog_repository.get_model_catalog_repository")
    @patch("src.alerting.model_catalog_sync.urllib.request.urlopen")
    def test_db_error_returns_500(self, mock_urlopen, mock_get_repo):
        mock_urlopen.return_value = self._mock_response({
            "data": [{"id": "test/model"}]
        })

        mock_repo = MagicMock()
        mock_repo.upsert_models.side_effect = Exception("Connection refused")
        mock_get_repo.return_value = mock_repo

        result = lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 500

    def test_missing_config_returns_500(self, monkeypatch):
        monkeypatch.delenv("AURORA_HOST")
        import importlib
        import src.alerting.model_catalog_sync as mod
        importlib.reload(mod)

        result = mod.lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 500
