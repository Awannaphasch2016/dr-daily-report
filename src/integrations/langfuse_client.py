"""Langfuse observability integration.

Lightweight wrapper around Langfuse SDK for tracing LLM workflows.
Replaces LangSmith with free/self-hostable alternative.

Environment Variables:
    LANGFUSE_PUBLIC_KEY: Public API key
    LANGFUSE_SECRET_KEY: Secret API key
    LANGFUSE_HOST: Langfuse instance URL (default: https://cloud.langfuse.com)
"""

import os
import logging
from typing import Optional, Dict, Tuple
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global client instance (singleton pattern for Lambda cold start optimization)
_langfuse_client: Optional['Langfuse'] = None


def get_langfuse_client():
    """Get or create Langfuse client singleton.

    Returns:
        Langfuse client instance or None if not configured.
    """
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client

    # Check if Langfuse is configured
    public_key = os.environ.get('LANGFUSE_PUBLIC_KEY')
    secret_key = os.environ.get('LANGFUSE_SECRET_KEY')

    if not public_key or not secret_key:
        logger.info("Langfuse not configured (missing keys) - tracing disabled")
        return None

    try:
        from langfuse import Langfuse

        host = os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        release = os.environ.get('LANGFUSE_RELEASE')
        environment = os.environ.get('LANGFUSE_TRACING_ENVIRONMENT')
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            release=release,
            environment=environment,
        )

        logger.info(f"✅ Langfuse client initialized (host: {host})")
        return _langfuse_client

    except ImportError:
        logger.warning("Langfuse package not installed - tracing disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {e}")
        return None


def observe(name: Optional[str] = None):
    """Decorator for tracing functions with Langfuse.

    Lightweight alternative to LangSmith's @traceable decorator.

    Args:
        name: Optional trace name (defaults to function name)

    Example:
        @observe(name="fetch_ticker_data")
        def fetch_data(ticker: str):
            return yfinance.download(ticker)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = get_langfuse_client()

            # If Langfuse not configured, just run function normally
            if client is None:
                return func(*args, **kwargs)

            # Use Langfuse decorator if available
            try:
                from langfuse import observe as langfuse_observe

                trace_name = name or func.__name__
                traced_func = langfuse_observe(name=trace_name)(func)
                return traced_func(*args, **kwargs)

            except Exception as e:
                logger.warning(f"Langfuse tracing failed: {e} - executing without trace")
                return func(*args, **kwargs)

        return wrapper
    return decorator


def flush():
    """Flush any pending traces to Langfuse.

    Important for Lambda functions to ensure traces are sent before shutdown.
    """
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            logger.debug("Langfuse traces flushed")
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse traces: {e}")


# Observation level tracking (for degraded operations)
_observation_level = "INFO"


_VALID_LEVELS = {"DEBUG", "DEFAULT", "WARNING", "ERROR"}


def set_observation_level(level: str) -> bool:
    """Set observation level for current observation.

    Used to mark degraded operations (WARNING) or failures (ERROR).

    Returns:
        True if level was set successfully, False otherwise.
    """
    global _observation_level

    if level not in _VALID_LEVELS:
        logger.warning(f"Invalid observation level: {level}")
        return False

    client = get_langfuse_client()
    if client is None:
        return False

    try:
        client.update_current_observation(level=level)
        _observation_level = level
        logger.debug(f"Observation level set to: {level}")
        return True
    except Exception as e:
        logger.warning(f"Failed to set observation level: {e}")
        return False


def get_observation_level() -> str:
    """Get current observation level."""
    return _observation_level


def get_langchain_handler():
    """Get LangChain callback handler for Langfuse integration.

    Returns a handler that can be passed to LangChain's callback system
    for tracing LLM calls.

    Returns:
        LangChain callback handler or None if Langfuse not configured.
    """
    client = get_langfuse_client()
    if client is None:
        return None

    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler()
    except ImportError:
        logger.warning("Langfuse callback handler not available")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Langfuse callback handler: {e}")
        return None


def score_current_trace(name: str, value: float, comment: Optional[str] = None) -> bool:
    """Push a score to the current Langfuse trace.

    Normalizes values from 0-100 scale to 0-1 scale expected by Langfuse.
    Values already in 0-1 range are passed through unchanged.

    Args:
        name: Score name (e.g. "faithfulness", "completeness")
        value: Score value (0-100 scale normalized to 0-1, or 0-1 passed through)
        comment: Optional comment describing the score

    Returns:
        True if score was pushed successfully, False otherwise.
    """
    client = get_langfuse_client()
    if client is None:
        return False

    # Normalize: our API uses 0-100, Langfuse expects 0-1
    normalized = value / 100 if value > 1 else value

    try:
        client.score_current_trace(name=name, value=normalized, comment=comment)
        return True
    except Exception as e:
        logger.warning(f"Failed to push score '{name}' to Langfuse: {e}")
        return False


def score_trace_batch(scores: Dict[str, Tuple[float, Optional[str]]]) -> int:
    """Push multiple scores to the current Langfuse trace.

    Args:
        scores: Dict of {name: (value, comment)} pairs

    Returns:
        Count of successfully pushed scores.
    """
    count = 0
    for name, (value, comment) in scores.items():
        if score_current_trace(name, value, comment=comment):
            count += 1
    return count


def set_trace_level(level: str) -> bool:
    """Set level on the current trace.

    Args:
        level: One of DEBUG, DEFAULT, WARNING, ERROR

    Returns:
        True if level was set successfully, False otherwise.
    """
    if level not in _VALID_LEVELS:
        logger.warning(f"Invalid trace level: {level}")
        return False

    client = get_langfuse_client()
    if client is None:
        return False

    try:
        client.update_current_trace(level=level)
        return True
    except Exception as e:
        logger.warning(f"Failed to set trace level: {e}")
        return False


@contextmanager
def trace_context(user_id: Optional[str] = None, session_id: Optional[str] = None,
                  tags: Optional[list] = None, metadata: Optional[dict] = None):
    """Context manager to set trace attributes on the current Langfuse trace.

    Args:
        user_id: User identifier (truncated to 200 chars per Langfuse limit)
        session_id: Session grouping identifier
        tags: Filterable tags list
        metadata: Key-value metadata dict
    """
    client = get_langfuse_client()
    if client is None:
        yield
        return

    try:
        kwargs = {}
        if user_id is not None:
            kwargs['user_id'] = user_id[:200]
        if session_id is not None:
            kwargs['session_id'] = session_id
        if tags is not None:
            kwargs['tags'] = tags
        if metadata is not None:
            kwargs['metadata'] = metadata

        client.update_current_trace(**kwargs)
    except Exception as e:
        logger.warning(f"Failed to update trace context: {e}")

    yield
