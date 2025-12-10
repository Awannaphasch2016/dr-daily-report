# -*- coding: utf-8 -*-
"""
Aurora MySQL Data Layer

Provides database access for ticker data storage in Aurora MySQL Serverless v2.

Lazy imports to avoid loading pandas when not needed (for fund_data_sync Lambda).
"""

# Lazy imports via __getattr__ to prevent pandas from being required
# when importing fund_data_repository (which only needs client)

def __getattr__(name):
    """Lazy import for Aurora modules.
    
    Only imports modules when actually accessed, preventing pandas
    from being required for fund_data_sync Lambda.
    """
    if name == 'AuroraClient':
        from .client import AuroraClient
        return AuroraClient
    elif name == 'get_aurora_client':
        from .client import get_aurora_client
        return get_aurora_client
    elif name == 'TickerRepository':
        from .repository import TickerRepository
        return TickerRepository
    elif name == 'TickerResolver':
        from .ticker_resolver import TickerResolver
        return TickerResolver
    elif name == 'TickerInfo':
        from .ticker_resolver import TickerInfo
        return TickerInfo
    elif name == 'get_ticker_resolver':
        from .ticker_resolver import get_ticker_resolver
        return get_ticker_resolver
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'AuroraClient',
    'get_aurora_client',
    'TickerRepository',
    'TickerResolver',
    'TickerInfo',
    'get_ticker_resolver',
]
