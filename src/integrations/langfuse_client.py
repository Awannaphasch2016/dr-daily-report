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
from typing import Optional
from functools import wraps

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
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
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


def set_observation_level(level: str):
    """Set observation level for current trace.

    Used to mark degraded operations (WARNING) or failures (ERROR).
    """
    global _observation_level
    _observation_level = level
    logger.debug(f"Observation level set to: {level}")


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
