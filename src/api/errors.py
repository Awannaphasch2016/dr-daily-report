"""Standardized error handling for API"""

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from .models import ErrorEnvelope, ErrorResponse, ErrorDetail


class APIError(Exception):
    """Base API error"""
    def __init__(self, code: str, message: str, status_code: int = 400, details: ErrorDetail | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# Error codes from spec
class InvalidRequestError(APIError):
    """400 - Invalid request parameters"""
    def __init__(self, message: str, details: ErrorDetail | None = None):
        super().__init__("INVALID_REQUEST", message, 400, details)


class TickerNotSupportedError(APIError):
    """400 - Ticker not in supported list"""
    def __init__(self, ticker: str):
        super().__init__(
            "TICKER_NOT_SUPPORTED",
            f"Ticker '{ticker}' is not supported",
            400,
            ErrorDetail(ticker=ticker)
        )


class ReportNotFoundError(APIError):
    """404 - Report not found"""
    def __init__(self, ticker: str):
        super().__init__(
            "REPORT_NOT_FOUND",
            f"No report found for ticker '{ticker}'",
            404,
            ErrorDetail(ticker=ticker)
        )


class InternalError(APIError):
    """500 - Internal server error"""
    def __init__(self, message: str = "Internal server error"):
        super().__init__("INTERNAL_ERROR", message, 500)


class UpstreamTimeoutError(APIError):
    """504 - Upstream analysis timeout"""
    def __init__(self, message: str = "Analysis service timed out"):
        super().__init__("UPSTREAM_TIMEOUT", message, 504)


class RateLimitedError(APIError):
    """429 - Rate limited"""
    def __init__(self, message: str = "Too many requests"):
        super().__init__("RATE_LIMITED", message, 429)


def create_error_response(error: APIError) -> JSONResponse:
    """Create standardized error response"""
    envelope = ErrorEnvelope(
        error=ErrorResponse(
            code=error.code,
            message=error.message,
            details=error.details
        )
    )

    return JSONResponse(
        status_code=error.status_code,
        content=envelope.model_dump(exclude_none=True)
    )


def api_exception_handler(request, exc: APIError) -> JSONResponse:
    """FastAPI exception handler for APIError"""
    return create_error_response(exc)
