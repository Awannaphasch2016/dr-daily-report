"""Lambda Request Interceptor (Handler Wrapper)

Sits between the Lambda Runtime and the original handler.
Intercepts every invocation for cross-cutting concerns:
- Structured request logging (user_id, ticker, platform)
- Cold start detection
- Request/response timing

Configuration:
    ORIGINAL_HANDLER: dotted path to real handler (e.g., "telegram_lambda_handler.handler")
    INTERCEPTOR_DISABLED: set to "true" to bypass (escape hatch)

This module must NEVER break the original handler.
All parsing/logging is wrapped in try/except with silent failure.
"""

import importlib
import json
import logging
import os
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("request_interceptor")
logger.setLevel(logging.INFO)

# Lambda pre-configures root logger at WARNING; ensure INFO passes through
logging.getLogger().setLevel(logging.INFO)

# ─── Cold Start Tracking ─────────────────────────────────────────────
_is_cold_start = True
_original_handler: Optional[Callable] = None

# ─── Platform Constants ──────────────────────────────────────────────
PLATFORM_LINE = "line"
PLATFORM_TELEGRAM = "telegram"
PLATFORM_REPORT_WORKER = "report_worker"
PLATFORM_UNKNOWN = "unknown"


# ─── Section A: Handler Resolution ───────────────────────────────────

def _resolve_handler() -> Callable:
    """Import and cache the original handler from ORIGINAL_HANDLER env var.

    Format: "module_path.function_name" (e.g., "telegram_lambda_handler.handler")
    """
    global _original_handler
    if _original_handler is not None:
        return _original_handler

    handler_path = os.environ.get("ORIGINAL_HANDLER")
    if not handler_path:
        raise ValueError(
            "ORIGINAL_HANDLER environment variable not set. "
            "Cannot determine which handler to delegate to."
        )

    module_path, _, func_name = handler_path.rpartition(".")
    if not module_path:
        raise ValueError(
            f"Invalid ORIGINAL_HANDLER format: '{handler_path}'. "
            "Expected 'module.function'."
        )

    module = importlib.import_module(module_path)
    _original_handler = getattr(module, func_name)
    logger.info(f"INTERCEPTOR_INIT handler={handler_path}")
    return _original_handler


# ─── Section B: Platform-Specific Parsers ─────────────────────────────

def _parse_line_event(event: dict) -> dict:
    """Parse LINE webhook event.

    Body contains: {"events": [{"source": {"userId": "U123"}, "message": {"text": "DBS19"}}]}
    """
    result = {"platform": PLATFORM_LINE, "user_id": None, "ticker": None, "path": None, "method": "POST"}
    body_str = event.get("body", "")
    if not body_str:
        return result
    body = json.loads(body_str)
    events = body.get("events", [])
    if events:
        first_event = events[0]
        result["user_id"] = first_event.get("source", {}).get("userId")
        msg = first_event.get("message", {})
        if msg.get("type") == "text":
            result["ticker"] = msg.get("text", "").strip()
    return result


def _parse_telegram_event(event: dict) -> dict:
    """Parse Telegram API Gateway HTTP API v2 event.

    Path: /api/v1/report/{ticker}, Header: x-telegram-user-id
    """
    result = {"platform": PLATFORM_TELEGRAM, "user_id": None, "ticker": None, "path": None, "method": None}
    rc = event.get("requestContext", {}).get("http", {})
    result["method"] = rc.get("method")
    result["path"] = rc.get("path")

    headers = event.get("headers", {})
    result["user_id"] = headers.get("x-telegram-user-id") or headers.get("x-telegram-init-data")

    path = result["path"] or ""
    if "/report/" in path:
        result["ticker"] = path.split("/report/")[-1].split("/")[0].split("?")[0]

    return result


def _parse_report_worker_event(event: dict) -> dict:
    """Parse Report Worker direct invocation event.

    Direct: {"job_id": "xxx", "ticker": "DBS19", "source": "telegram_api"}
    SQS: {"Records": [{"body": "{\"ticker\": ...}"}]}
    """
    result = {"platform": PLATFORM_REPORT_WORKER, "user_id": None, "ticker": None, "path": None, "method": None}

    if "ticker" in event:
        result["ticker"] = event["ticker"]
        result["user_id"] = event.get("source", "direct")
        return result

    records = event.get("Records", [])
    if records:
        try:
            body = json.loads(records[0].get("body", "{}"))
            result["ticker"] = body.get("ticker")
            result["user_id"] = body.get("source", "sqs")
        except (json.JSONDecodeError, IndexError):
            pass

    return result


# ─── Section C: Platform Detection ────────────────────────────────────

def _detect_platform(event: dict) -> str:
    """Detect platform from ORIGINAL_HANDLER env var, with event shape fallback."""
    handler_path = os.environ.get("ORIGINAL_HANDLER", "")

    if "lambda_handler.lambda_handler" in handler_path:
        return PLATFORM_LINE
    if "telegram_lambda_handler" in handler_path:
        return PLATFORM_TELEGRAM
    if "report_worker_handler" in handler_path:
        return PLATFORM_REPORT_WORKER

    # Fallback: detect from event shape
    headers = event.get("headers", {})
    if isinstance(headers, dict):
        if "x-line-signature" in headers or "X-Line-Signature" in headers:
            return PLATFORM_LINE
        if event.get("requestContext", {}).get("http"):
            return PLATFORM_TELEGRAM

    if "Records" in event or ("job_id" in event and "ticker" in event):
        return PLATFORM_REPORT_WORKER

    return PLATFORM_UNKNOWN


def _parse_event(event: dict) -> dict:
    """Route to correct parser based on detected platform."""
    platform = _detect_platform(event)
    parsers = {
        PLATFORM_LINE: _parse_line_event,
        PLATFORM_TELEGRAM: _parse_telegram_event,
        PLATFORM_REPORT_WORKER: _parse_report_worker_event,
    }
    parser = parsers.get(platform)
    if parser:
        return parser(event)
    return {"platform": PLATFORM_UNKNOWN, "user_id": None, "ticker": None, "path": None, "method": None}


# ─── Section D: Structured Logging ────────────────────────────────────

def _log_request(request_info: dict, request_id: str, is_cold_start: bool) -> None:
    """Emit structured USER_REQUEST log line for CloudWatch Insights."""
    parts = ["USER_REQUEST"]
    parts.append(f"platform={request_info.get('platform', 'unknown')}")
    parts.append(f"user_id={request_info.get('user_id') or 'N/A'}")
    parts.append(f"ticker={request_info.get('ticker') or 'N/A'}")
    if request_info.get("method"):
        parts.append(f"method={request_info['method']}")
    if request_info.get("path"):
        parts.append(f"path={request_info['path']}")
    parts.append(f"cold_start={is_cold_start}")
    parts.append(f"request_id={request_id}")
    logger.info(" ".join(parts))


def _log_response(request_info: dict, request_id: str, duration_ms: float,
                  status_code: int = 0, error: str = None) -> None:
    """Emit structured USER_RESPONSE log line."""
    parts = ["USER_RESPONSE"]
    parts.append(f"platform={request_info.get('platform', 'unknown')}")
    parts.append(f"ticker={request_info.get('ticker') or 'N/A'}")
    parts.append(f"duration_ms={duration_ms:.0f}")
    if status_code:
        parts.append(f"status={status_code}")
    if error:
        parts.append(f"error={error[:200]}")
    parts.append(f"request_id={request_id}")
    logger.info(" ".join(parts))


def _record_to_aurora(request_info: dict, request_id: str, duration_ms: float,
                      status_code: int = 0, error: str = None,
                      response_body: str = None) -> None:
    """Write user request to Aurora tables. Silent on failure."""
    platform = request_info.get("platform")
    user_id = request_info.get("user_id")
    ticker = request_info.get("ticker")

    # Skip if missing required fields
    if not platform or not user_id or platform == PLATFORM_UNKNOWN:
        return

    result = "error" if error else ("cache_hit" if status_code == 200 else "unknown")
    # For ticker-less requests (health checks, etc.), skip recording
    if not ticker:
        return

    from src.data.aurora.user_repository import UserRepository
    repo = UserRepository()
    uid = repo.upsert_user(platform, user_id)
    repo.record_request(uid, ticker, platform, result, duration_ms, request_id,
                        response_body=response_body)


# ─── Section E: Main Handler ──────────────────────────────────────────

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Interceptor entry point. Delegates to ORIGINAL_HANDLER after logging.

    Fail-safe: If ANY interceptor logic fails, it falls through to
    the original handler. The interceptor must NEVER prevent the
    original handler from executing.
    """
    global _is_cold_start

    # Escape hatch
    if os.environ.get("INTERCEPTOR_DISABLED", "").lower() == "true":
        return _resolve_handler()(event, context)

    # ── Pre-invocation ──
    request_id = getattr(context, "aws_request_id", "unknown")
    start_time = time.time()
    request_info = {}
    current_cold_start = _is_cold_start

    try:
        request_info = _parse_event(event)
        _log_request(request_info, request_id, current_cold_start)
    except Exception:
        logger.warning("INTERCEPTOR_PARSE_ERROR", exc_info=True)

    _is_cold_start = False

    # ── Invoke original handler ──
    try:
        response = _resolve_handler()(event, context)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        try:
            _log_response(request_info, request_id, duration_ms, error=str(e))
        except Exception:
            pass
        raise

    # ── Post-invocation ──
    duration_ms = (time.time() - start_time) * 1000
    try:
        status_code = response.get("statusCode", 0) if isinstance(response, dict) else 0
        _log_response(request_info, request_id, duration_ms, status_code=status_code)
    except Exception:
        pass

    # ── Record to Aurora (silent on failure) ──
    try:
        status_code = response.get("statusCode", 0) if isinstance(response, dict) else 0
        response_body = None
        if isinstance(response, dict):
            response_body = response.get("body")
        _record_to_aurora(request_info, request_id, duration_ms,
                          status_code=status_code, response_body=response_body)
    except Exception:
        logger.warning("INTERCEPTOR_DB_WRITE_ERROR", exc_info=True)

    return response
