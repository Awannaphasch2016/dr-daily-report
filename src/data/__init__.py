"""Data layer - Data fetching and storage

Lazy imports to avoid loading heavy dependencies (yfinance) when not needed.
This allows fund_data_sync Lambda to import from src.data.etl without requiring yfinance.

All imports are lazy via __getattr__ to prevent eager loading of yfinance.
"""

# NO module-level imports - all imports are lazy via __getattr__
# This prevents yfinance from being required when importing src.data.etl

def __getattr__(name):
    """Lazy import for data layer modules.
    
    Only imports modules when they are actually accessed, preventing
    yfinance dependency from being loaded for fund_data_sync Lambda.
    """
    if name == 'DataFetcher':
        from .data_fetcher import DataFetcher
        return DataFetcher
    elif name == 'NewsFetcher':
        from .news_fetcher import NewsFetcher
        return NewsFetcher
    elif name == 'S3Cache':
        from .s3_cache import S3Cache
        return S3Cache
    elif name == 'TickerMatcher':
        from .ticker_matcher import TickerMatcher
        return TickerMatcher
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'DataFetcher',
    'NewsFetcher',
    'S3Cache',
    'TickerMatcher',
]
