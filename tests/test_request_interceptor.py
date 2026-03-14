"""Tests for Lambda Request Interceptor.

Validates the interceptor wrapper without AWS calls.
Uses mock handlers and monkeypatched env vars.
"""

import json
import logging
import pytest
from unittest.mock import MagicMock

from src.request_interceptor import (
    _detect_platform,
    _parse_event,
    _parse_line_event,
    _parse_report_worker_event,
    _parse_telegram_event,
    handler,
    PLATFORM_LINE,
    PLATFORM_REPORT_WORKER,
    PLATFORM_TELEGRAM,
    PLATFORM_UNKNOWN,
)
import src.request_interceptor as interceptor_module


# ─── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_interceptor_state(monkeypatch):
    """Reset module-level state between tests."""
    interceptor_module._is_cold_start = True
    interceptor_module._original_handler = None
    monkeypatch.delenv("ORIGINAL_HANDLER", raising=False)
    monkeypatch.delenv("INTERCEPTOR_DISABLED", raising=False)


def _mock_context(request_id="test-request-123"):
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


def _line_webhook_event(user_id="U123456789abcdef", text="DBS19"):
    return {
        "body": json.dumps({
            "events": [{
                "type": "message",
                "source": {"userId": user_id, "type": "user"},
                "message": {"type": "text", "id": "325708", "text": text},
                "replyToken": "mock_reply_token",
            }]
        }),
        "headers": {"x-line-signature": "mock_signature"},
    }


def _telegram_api_event(path="/api/v1/report/DBS19", user_id="12345", method="POST"):
    return {
        "requestContext": {"http": {"method": method, "path": path}},
        "headers": {"x-telegram-user-id": user_id},
    }


def _report_worker_event(ticker="DBS19", source="telegram_api"):
    return {"job_id": "rpt_abc123", "ticker": ticker, "source": source}


# ─── Section B: Parser Tests ──────────────────────────────────────────

class TestLineEventParsing:
    def test_extracts_user_id_and_ticker(self):
        result = _parse_line_event(_line_webhook_event())
        assert result["platform"] == PLATFORM_LINE
        assert result["user_id"] == "U123456789abcdef"
        assert result["ticker"] == "DBS19"

    def test_empty_body(self):
        result = _parse_line_event({"body": ""})
        assert result["user_id"] is None
        assert result["ticker"] is None

    def test_no_events(self):
        result = _parse_line_event({"body": json.dumps({"events": []})})
        assert result["user_id"] is None
        assert result["ticker"] is None

    def test_non_text_message(self):
        event = {
            "body": json.dumps({
                "events": [{
                    "type": "message",
                    "source": {"userId": "U999"},
                    "message": {"type": "image", "id": "123"},
                }]
            })
        }
        result = _parse_line_event(event)
        assert result["user_id"] == "U999"
        assert result["ticker"] is None

    def test_follow_event(self):
        event = {
            "body": json.dumps({
                "events": [{
                    "type": "follow",
                    "source": {"userId": "U999"},
                }]
            })
        }
        result = _parse_line_event(event)
        assert result["user_id"] == "U999"
        assert result["ticker"] is None


class TestTelegramEventParsing:
    def test_extracts_ticker_from_path(self):
        result = _parse_telegram_event(_telegram_api_event())
        assert result["platform"] == PLATFORM_TELEGRAM
        assert result["ticker"] == "DBS19"
        assert result["user_id"] == "12345"
        assert result["method"] == "POST"

    def test_non_report_path(self):
        result = _parse_telegram_event(_telegram_api_event(path="/api/v1/health"))
        assert result["ticker"] is None
        assert result["path"] == "/api/v1/health"

    def test_missing_user_header(self):
        event = {
            "requestContext": {"http": {"method": "GET", "path": "/api/v1/report/NVDA19"}},
            "headers": {},
        }
        result = _parse_telegram_event(event)
        assert result["user_id"] is None
        assert result["ticker"] == "NVDA19"

    def test_ticker_with_query_params(self):
        result = _parse_telegram_event(
            _telegram_api_event(path="/api/v1/report/DBS19?force_refresh=true")
        )
        assert result["ticker"] == "DBS19"


class TestReportWorkerEventParsing:
    def test_direct_invocation(self):
        result = _parse_report_worker_event(_report_worker_event())
        assert result["platform"] == PLATFORM_REPORT_WORKER
        assert result["ticker"] == "DBS19"
        assert result["user_id"] == "telegram_api"

    def test_sqs_record(self):
        event = {
            "Records": [{
                "body": json.dumps({"job_id": "rpt_123", "ticker": "NVDA19", "source": "precompute"})
            }]
        }
        result = _parse_report_worker_event(event)
        assert result["ticker"] == "NVDA19"
        assert result["user_id"] == "precompute"

    def test_malformed_sqs_record(self):
        event = {"Records": [{"body": "not json"}]}
        result = _parse_report_worker_event(event)
        assert result["ticker"] is None


# ─── Section C: Platform Detection ────────────────────────────────────

class TestPlatformDetection:
    def test_detects_line_from_env(self, monkeypatch):
        monkeypatch.setenv("ORIGINAL_HANDLER", "lambda_handler.lambda_handler")
        assert _detect_platform({}) == PLATFORM_LINE

    def test_detects_telegram_from_env(self, monkeypatch):
        monkeypatch.setenv("ORIGINAL_HANDLER", "telegram_lambda_handler.handler")
        assert _detect_platform({}) == PLATFORM_TELEGRAM

    def test_detects_worker_from_env(self, monkeypatch):
        monkeypatch.setenv("ORIGINAL_HANDLER", "report_worker_handler.handler")
        assert _detect_platform({}) == PLATFORM_REPORT_WORKER

    def test_fallback_line_from_headers(self):
        event = {"headers": {"x-line-signature": "abc"}, "body": "{}"}
        assert _detect_platform(event) == PLATFORM_LINE

    def test_fallback_telegram_from_request_context(self):
        event = {"requestContext": {"http": {"method": "GET", "path": "/health"}}, "headers": {}}
        assert _detect_platform(event) == PLATFORM_TELEGRAM

    def test_fallback_worker_from_event_shape(self):
        event = {"job_id": "rpt_123", "ticker": "DBS19"}
        assert _detect_platform(event) == PLATFORM_REPORT_WORKER

    def test_unknown_event(self):
        assert _detect_platform({"random": "data"}) == PLATFORM_UNKNOWN


# ─── Section E: Main Handler Tests ────────────────────────────────────

class TestHandler:
    def test_delegates_to_original_handler(self, monkeypatch):
        mock_handler = MagicMock(return_value={"statusCode": 200, "body": "ok"})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "some.handler")

        event = _telegram_api_event()
        context = _mock_context()
        response = handler(event, context)

        mock_handler.assert_called_once_with(event, context)
        assert response["statusCode"] == 200

    def test_cold_start_tracking(self, monkeypatch):
        mock_handler = MagicMock(return_value={"statusCode": 200})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "some.handler")

        assert interceptor_module._is_cold_start is True

        handler(_telegram_api_event(), _mock_context())
        assert interceptor_module._is_cold_start is False

        handler(_telegram_api_event(), _mock_context())
        assert interceptor_module._is_cold_start is False

    def test_escape_hatch(self, monkeypatch):
        mock_handler = MagicMock(return_value={"statusCode": 200})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "some.handler")
        monkeypatch.setenv("INTERCEPTOR_DISABLED", "true")

        handler(_telegram_api_event(), _mock_context())
        mock_handler.assert_called_once()

    def test_error_passthrough(self, monkeypatch):
        mock_handler = MagicMock(side_effect=RuntimeError("boom"))
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "some.handler")

        with pytest.raises(RuntimeError, match="boom"):
            handler(_telegram_api_event(), _mock_context())

    def test_logs_user_request(self, monkeypatch, caplog):
        mock_handler = MagicMock(return_value={"statusCode": 200})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "lambda_handler.lambda_handler")

        with caplog.at_level(logging.INFO, logger="request_interceptor"):
            handler(_line_webhook_event(), _mock_context())

        request_logs = [r for r in caplog.records if "USER_REQUEST" in r.message]
        assert len(request_logs) == 1
        assert "platform=line" in request_logs[0].message
        assert "user_id=U123456789abcdef" in request_logs[0].message
        assert "ticker=DBS19" in request_logs[0].message

    def test_logs_user_response(self, monkeypatch, caplog):
        mock_handler = MagicMock(return_value={"statusCode": 200})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "telegram_lambda_handler.handler")

        with caplog.at_level(logging.INFO, logger="request_interceptor"):
            handler(_telegram_api_event(), _mock_context())

        response_logs = [r for r in caplog.records if "USER_RESPONSE" in r.message]
        assert len(response_logs) == 1
        assert "duration_ms=" in response_logs[0].message
        assert "status=200" in response_logs[0].message

    def test_missing_original_handler_env(self):
        with pytest.raises(ValueError, match="ORIGINAL_HANDLER"):
            handler(_telegram_api_event(), _mock_context())

    def test_parse_failure_does_not_break_handler(self, monkeypatch):
        """Even if event parsing crashes, original handler still runs."""
        mock_handler = MagicMock(return_value={"statusCode": 200})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "lambda_handler.lambda_handler")

        # LINE platform detected but body is not valid JSON
        event = {"body": "not-json", "headers": {"x-line-signature": "abc"}}
        response = handler(event, _mock_context())

        mock_handler.assert_called_once()
        assert response["statusCode"] == 200

    def test_passes_response_body_to_aurora(self, monkeypatch):
        """Interceptor extracts response body and passes to _record_to_aurora."""
        from unittest.mock import patch, call
        body_json = json.dumps({"message": "OK", "responses": ["Report text"]})
        mock_handler = MagicMock(return_value={"statusCode": 200, "body": body_json})
        interceptor_module._original_handler = mock_handler
        monkeypatch.setenv("ORIGINAL_HANDLER", "lambda_handler.lambda_handler")

        with patch.object(interceptor_module, "_record_to_aurora") as mock_record:
            handler(_line_webhook_event(), _mock_context())

        mock_record.assert_called_once()
        kwargs = mock_record.call_args
        assert kwargs[1]["response_body"] == body_json
