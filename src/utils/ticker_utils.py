"""Ticker utility functions for workflow routing decisions"""

import os
from typing import Dict


def is_us_ticker(yahoo_ticker: str) -> bool:
    """
    Determine if a ticker is US-listed.

    Args:
        yahoo_ticker: Yahoo Finance ticker symbol (e.g., "AAPL", "D05.SI", "700.HK")

    Returns:
        True if ticker is US-listed, False otherwise

    Examples:
        >>> is_us_ticker("AAPL")
        True
        >>> is_us_ticker("NVDA.US")
        True
        >>> is_us_ticker("D05.SI")  # Singapore
        False
        >>> is_us_ticker("700.HK")  # Hong Kong
        False
    """
    if not yahoo_ticker:
        return False

    # US tickers either have no suffix or end with .US
    non_us_suffixes = ['.SI', '.HK', '.T', '.TW', '.L', '.AX']

    # Check if ticker has any non-US suffix
    if any(yahoo_ticker.upper().endswith(suffix) for suffix in non_us_suffixes):
        return False

    # US ticker if no non-US suffix
    return True


def has_mcp_server(server_name: str) -> bool:
    """
    Check if an MCP server is configured via environment variables.

    Args:
        server_name: Name of MCP server ('alpaca', 'financial_markets', 'portfolio_manager')

    Returns:
        True if server is configured, False otherwise

    Examples:
        >>> has_mcp_server('alpaca')  # Checks MCP_ALPACA_URL
        False
        >>> has_mcp_server('financial_markets')  # Checks MCP_FINANCIAL_MARKETS_URL
        False
    """
    # Map server names to environment variable names
    server_env_vars = {
        'alpaca': 'MCP_ALPACA_URL',
        'financial_markets': 'MCP_FINANCIAL_MARKETS_URL',
        'financial-markets': 'MCP_FINANCIAL_MARKETS_URL',  # Handle both formats
        'portfolio_manager': 'MCP_PORTFOLIO_MANAGER_URL',
        'portfolio-manager': 'MCP_PORTFOLIO_MANAGER_URL',
    }

    env_var = server_env_vars.get(server_name.lower())
    if not env_var:
        return False

    url = os.getenv(env_var)
    return bool(url and url.strip())


def get_ticker_market(yahoo_ticker: str) -> str:
    """
    Get the market/exchange for a ticker.

    Args:
        yahoo_ticker: Yahoo Finance ticker symbol

    Returns:
        Market code ('US', 'SG', 'HK', 'TW', 'JP', 'UK', 'AU', or 'UNKNOWN')

    Examples:
        >>> get_ticker_market("AAPL")
        'US'
        >>> get_ticker_market("D05.SI")
        'SG'
        >>> get_ticker_market("700.HK")
        'HK'
    """
    if not yahoo_ticker:
        return 'UNKNOWN'

    ticker_upper = yahoo_ticker.upper()

    # Map suffixes to markets
    suffix_market_map = {
        '.SI': 'SG',  # Singapore
        '.HK': 'HK',  # Hong Kong
        '.T': 'JP',   # Tokyo
        '.TW': 'TW',  # Taiwan
        '.L': 'UK',   # London
        '.AX': 'AU',  # Australia
    }

    for suffix, market in suffix_market_map.items():
        if ticker_upper.endswith(suffix):
            return market

    # Default to US if no recognized suffix
    return 'US'
