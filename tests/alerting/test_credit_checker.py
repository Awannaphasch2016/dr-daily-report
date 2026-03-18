"""Tests for OpenRouter credit checker Lambda handler.

Tests the credit balance checking, Langfuse cost querying, CloudWatch metric
publishing, and Slack alerting pipeline.
Follows Principle #10 (Testing Anti-Patterns): No external calls, deterministic data.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
from urllib.error import HTTPError, URLError


# Set required env vars before import
@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key-123")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test-123")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test-456")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ESTIMATED_DAILY_COST", "2.5")
    monkeypatch.setenv("GRAFANA_DASHBOARD_URL", "https://grafana.example.com/d/pipeline-health")
    monkeypatch.setenv("COST_MARGIN", "1.5")
    # Reload module-level constants
    import importlib
    import src.alerting.credit_checker as mod
    importlib.reload(mod)


# Import after env vars are set
from src.alerting.credit_checker import (
    _validate_config,
    _check_credit_balance,
    _get_actual_daily_cost,
    _push_cloudwatch_metrics,
    _format_credit_alert,
    _send_slack_alert,
    lambda_handler,
)


class TestValidateConfig:
    """Tests for _validate_config function."""

    def test_valid_config_passes(self):
        """All required vars present — no exception."""
        _validate_config()  # Should not raise

    def test_missing_openrouter_key_raises(self, monkeypatch):
        """Missing OPENROUTER_API_KEY raises RuntimeError."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "OPENROUTER_API_KEY", "")
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            mod._validate_config()

    def test_missing_slack_url_raises(self, monkeypatch):
        """Missing SLACK_WEBHOOK_URL raises RuntimeError."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "SLACK_WEBHOOK_URL", "")
        with pytest.raises(RuntimeError, match="SLACK_WEBHOOK_URL"):
            mod._validate_config()

    def test_missing_langfuse_keys_raises(self, monkeypatch):
        """Missing Langfuse keys raises RuntimeError."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "LANGFUSE_PUBLIC_KEY", "")
        monkeypatch.setattr(mod, "LANGFUSE_SECRET_KEY", "")
        with pytest.raises(RuntimeError, match="LANGFUSE_PUBLIC_KEY"):
            mod._validate_config()

    def test_multiple_missing_vars_listed(self, monkeypatch):
        """All missing vars are listed in error message."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "OPENROUTER_API_KEY", "")
        monkeypatch.setattr(mod, "SLACK_WEBHOOK_URL", "")
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY.*SLACK_WEBHOOK_URL"):
            mod._validate_config()


class TestCheckCreditBalance:
    """Tests for _check_credit_balance function."""

    def _mock_response(self, data: dict, status=200):
        """Create mock urllib response."""
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode("utf-8")
        response.status = status
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_successful_balance_check(self, mock_urlopen):
        """Successful API call returns correct balance calculation."""
        mock_urlopen.return_value = self._mock_response({
            "data": {"usage": 94.5, "limit": 100.0, "label": "dr-prod"}
        })

        result = _check_credit_balance("sk-test")
        assert result["usage"] == 94.5
        assert result["limit"] == 100.0
        assert result["balance"] == 5.5
        assert result["label"] == "dr-prod"

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_zero_limit_returns_negative_usage(self, mock_urlopen):
        """When limit is 0 (unlimited), balance is negative usage."""
        mock_urlopen.return_value = self._mock_response({
            "data": {"usage": 50.0, "limit": 0, "label": "free-tier"}
        })

        result = _check_credit_balance("sk-test")
        assert result["balance"] == -50.0

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_http_401_raises(self, mock_urlopen):
        """HTTP 401 (invalid key) raises HTTPError."""
        mock_urlopen.side_effect = HTTPError(
            "https://openrouter.ai", 401, "Unauthorized", {}, BytesIO(b"")
        )
        with pytest.raises(HTTPError):
            _check_credit_balance("sk-invalid")

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_connection_error_raises(self, mock_urlopen):
        """Connection timeout raises URLError."""
        mock_urlopen.side_effect = URLError("Connection timed out")
        with pytest.raises(URLError):
            _check_credit_balance("sk-test")


class TestGetActualDailyCost:
    """Tests for _get_actual_daily_cost function."""

    def _mock_response(self, data: dict):
        """Create mock urllib response."""
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode("utf-8")
        response.status = 200
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_calculates_daily_cost_from_traces(self, mock_urlopen):
        """Sums trace costs and divides by distinct days."""
        mock_urlopen.return_value = self._mock_response({
            "data": [
                {"totalCost": 1.5, "timestamp": "2026-03-17T05:00:00Z"},
                {"totalCost": 1.6, "timestamp": "2026-03-16T05:00:00Z"},
                {"totalCost": 1.4, "timestamp": "2026-03-15T05:00:00Z"},
            ]
        })

        result = _get_actual_daily_cost()
        assert result is not None
        # total=4.5, 3 distinct days, daily=1.5
        assert result == 1.5

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_empty_traces_returns_none(self, mock_urlopen):
        """No traces found returns None (triggers fallback)."""
        mock_urlopen.return_value = self._mock_response({"data": []})

        result = _get_actual_daily_cost()
        assert result is None

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_traces_without_cost_returns_none(self, mock_urlopen):
        """Traces with null/zero costs returns None."""
        mock_urlopen.return_value = self._mock_response({
            "data": [
                {"totalCost": None, "timestamp": "2026-03-17T05:00:00Z"},
                {"totalCost": 0, "timestamp": "2026-03-16T05:00:00Z"},
            ]
        })

        result = _get_actual_daily_cost()
        assert result is None

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_langfuse_api_error_returns_none(self, mock_urlopen):
        """Langfuse API failure returns None gracefully."""
        mock_urlopen.side_effect = HTTPError(
            "https://cloud.langfuse.com", 500, "Server Error", {}, BytesIO(b"")
        )

        result = _get_actual_daily_cost()
        assert result is None

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_langfuse_connection_error_returns_none(self, mock_urlopen):
        """Connection failure returns None gracefully."""
        mock_urlopen.side_effect = URLError("Connection refused")

        result = _get_actual_daily_cost()
        assert result is None

    def test_missing_langfuse_credentials_returns_none(self, monkeypatch):
        """Missing Langfuse credentials returns None without API call."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "LANGFUSE_PUBLIC_KEY", "")
        monkeypatch.setattr(mod, "LANGFUSE_SECRET_KEY", "")

        result = mod._get_actual_daily_cost()
        assert result is None


class TestPushCloudwatchMetrics:
    """Tests for _push_cloudwatch_metrics function."""

    @patch("src.alerting.credit_checker.boto3.client")
    def test_pushes_three_metrics(self, mock_boto3_client):
        """Pushes CreditBalance, ActualDailyCost, DaysRemaining metrics."""
        mock_cw = MagicMock()
        mock_boto3_client.return_value = mock_cw

        _push_cloudwatch_metrics(balance=5.50, daily_cost=1.55, days_remaining=3.5)

        mock_cw.put_metric_data.assert_called_once()
        call_args = mock_cw.put_metric_data.call_args
        assert call_args.kwargs["Namespace"] == "DR/OpenRouter"

        metric_names = [m["MetricName"] for m in call_args.kwargs["MetricData"]]
        assert "CreditBalance" in metric_names
        assert "ActualDailyCost" in metric_names
        assert "DaysRemaining" in metric_names

    @patch("src.alerting.credit_checker.boto3.client")
    def test_metrics_have_environment_dimension(self, mock_boto3_client):
        """All metrics include Environment dimension."""
        mock_cw = MagicMock()
        mock_boto3_client.return_value = mock_cw

        _push_cloudwatch_metrics(balance=5.50, daily_cost=1.55, days_remaining=3.5)

        call_args = mock_cw.put_metric_data.call_args
        for metric in call_args.kwargs["MetricData"]:
            dims = {d["Name"]: d["Value"] for d in metric["Dimensions"]}
            assert "Environment" in dims


class TestFormatCreditAlert:
    """Tests for _format_credit_alert function."""

    def test_critical_alert_has_danger_color(self):
        """Balance < 1 day remaining gets danger color."""
        msg = _format_credit_alert(
            balance=1.0, limit=100.0, daily_cost=1.55,
            days_remaining=0.6, cost_source="Langfuse traces (7d)",
        )
        assert msg["attachments"][0]["color"] == "danger"
        assert "CRITICAL" in msg["attachments"][0]["pretext"]

    def test_warning_alert_has_warning_color(self):
        """Balance > 1 day but below threshold gets warning color."""
        msg = _format_credit_alert(
            balance=2.0, limit=100.0, daily_cost=1.55,
            days_remaining=1.3, cost_source="Langfuse traces (7d)",
        )
        assert msg["attachments"][0]["color"] == "warning"

    def test_alert_contains_topup_link(self):
        """Alert message contains OpenRouter top-up link."""
        msg = _format_credit_alert(
            balance=1.0, limit=100.0, daily_cost=1.55,
            days_remaining=0.6, cost_source="Langfuse traces (7d)",
        )
        text = msg["attachments"][0]["text"]
        assert "openrouter.ai/settings/credits" in text

    def test_alert_contains_balance_and_cost(self):
        """Alert fields contain balance and daily cost."""
        msg = _format_credit_alert(
            balance=2.50, limit=100.0, daily_cost=1.55,
            days_remaining=1.6, cost_source="Langfuse traces (7d)",
        )
        fields = {f["title"]: f["value"] for f in msg["attachments"][0]["fields"]}
        assert "$2.50" in fields["Balance"]
        assert "$1.55" in fields["Daily Report Cost"]
        assert "1.6" in fields["Days Remaining"]


class TestSendSlackAlert:
    """Tests for _send_slack_alert function."""

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_successful_send(self, mock_urlopen):
        """Successful Slack webhook call returns True."""
        response = MagicMock()
        response.status = 200
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        result = _send_slack_alert({"text": "test"})
        assert result is True

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_failed_send_returns_false(self, mock_urlopen):
        """URL error returns False without raising."""
        mock_urlopen.side_effect = URLError("Connection refused")

        result = _send_slack_alert({"text": "test"})
        assert result is False


class TestLambdaHandler:
    """Integration tests for lambda_handler."""

    def _mock_urlopen_side_effect(self, openrouter_data, langfuse_data):
        """Create side_effect that routes by URL."""
        def side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            response = MagicMock()
            response.__enter__ = lambda s: s
            response.__exit__ = MagicMock(return_value=False)
            response.status = 200

            if "openrouter.ai" in url:
                response.read.return_value = json.dumps(openrouter_data).encode()
            elif "langfuse.com" in url:
                response.read.return_value = json.dumps(langfuse_data).encode()
            else:
                # Slack webhook
                response.read.return_value = b"ok"

            return response
        return side_effect

    @patch("src.alerting.credit_checker.boto3.client")
    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_happy_path_sufficient_balance(self, mock_urlopen, mock_boto3):
        """Sufficient balance → no alert, metrics pushed."""
        mock_boto3.return_value = MagicMock()
        mock_urlopen.side_effect = self._mock_urlopen_side_effect(
            openrouter_data={"data": {"usage": 90.0, "limit": 100.0, "label": "prod"}},
            langfuse_data={"data": [
                {"totalCost": 1.5, "timestamp": "2026-03-17T05:00:00Z"},
            ]},
        )

        result = lambda_handler({"source": "test"}, None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["balance"] == 10.0
        assert body["alert_sent"] is False

    @patch("src.alerting.credit_checker.boto3.client")
    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_alert_path_insufficient_balance(self, mock_urlopen, mock_boto3):
        """Insufficient balance → alert sent."""
        mock_boto3.return_value = MagicMock()
        mock_urlopen.side_effect = self._mock_urlopen_side_effect(
            openrouter_data={"data": {"usage": 99.0, "limit": 100.0, "label": "prod"}},
            langfuse_data={"data": [
                {"totalCost": 1.5, "timestamp": "2026-03-17T05:00:00Z"},
            ]},
        )

        result = lambda_handler({"source": "test"}, None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["balance"] == 1.0
        assert body["alert_sent"] is True

    @patch("src.alerting.credit_checker.boto3.client")
    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_langfuse_down_uses_fallback(self, mock_urlopen, mock_boto3):
        """Langfuse unavailable → uses ESTIMATED_DAILY_COST fallback."""
        mock_boto3.return_value = MagicMock()

        call_count = 0
        def side_effect(req, timeout=None):
            nonlocal call_count
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            response = MagicMock()
            response.__enter__ = lambda s: s
            response.__exit__ = MagicMock(return_value=False)
            response.status = 200

            if "openrouter.ai" in url:
                response.read.return_value = json.dumps({
                    "data": {"usage": 95.0, "limit": 100.0, "label": "prod"}
                }).encode()
            elif "langfuse.com" in url:
                raise URLError("Connection refused")
            else:
                response.read.return_value = b"ok"

            return response

        mock_urlopen.side_effect = side_effect

        result = lambda_handler({"source": "test"}, None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["cost_source"] == "Fallback estimate ($2.5)"

    @patch("src.alerting.credit_checker.urllib.request.urlopen")
    def test_openrouter_down_returns_502(self, mock_urlopen):
        """OpenRouter API failure returns 502."""
        mock_urlopen.side_effect = URLError("Connection timed out")

        result = lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 502

    def test_missing_config_returns_500(self, monkeypatch):
        """Missing configuration returns 500."""
        import src.alerting.credit_checker as mod
        monkeypatch.setattr(mod, "OPENROUTER_API_KEY", "")

        result = mod.lambda_handler({"source": "test"}, None)
        assert result["statusCode"] == 500
