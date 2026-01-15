# -*- coding: utf-8 -*-
"""
Aurora Table Name Constants

Centralized table name definitions for Aurora MySQL database.

Why constants instead of dynamic lookup?
- Table names are stable (don't change across environments)
- Centralized modification point if schema evolves
- Zero runtime overhead (resolved at import time)
- Type-safe with IDE autocomplete

Usage:
    from src.data.aurora.table_names import TABLES

    query = f"SELECT * FROM {TABLES.DAILY_PRICES} WHERE symbol = %s"

    # Or individual imports:
    from src.data.aurora.table_names import DAILY_PRICES
    query = f"SELECT * FROM {DAILY_PRICES} WHERE symbol = %s"

If table names ever change:
    1. Update constants in this file
    2. No other code changes needed (constants propagate automatically)
    3. Run tests to verify no breakage
"""


# ============================================================================
# Core Tables (Active)
# ============================================================================

DAILY_PRICES = "daily_prices"
"""Historical OHLCV price data (open, high, low, close, volume)"""

TICKER_CACHE_METADATA = "ticker_cache_metadata"
"""S3 cache synchronization metadata for ticker data"""

PRECOMPUTED_REPORTS = "precomputed_reports"
"""Generated ticker analysis reports cache"""

TICKER_DATA = "ticker_data"
"""1-year price history + company info (precomputed cache)
Aliases: ticker_data_cache (schema name)"""

FUND_DATA = "fund_data"
"""Fund data synced from on-premises SQL Server source"""

DAILY_INDICATORS = "daily_indicators"
"""Technical indicators computed daily (RSI, MACD, SMA, etc.)"""

INDICATOR_PERCENTILES = "indicator_percentiles"
"""Percentile rankings for technical indicators"""

COMPARATIVE_FEATURES = "comparative_features"
"""Comparative peer analysis metrics"""

TICKER_MASTER = "ticker_master"
"""Master ticker registry (canonical ticker symbols)"""

TICKER_ALIASES = "ticker_aliases"
"""Ticker symbol aliases and mappings (DR format ↔ Yahoo format)"""

CHART_PATTERN_DATA = "chart_pattern_data"
"""Detected chart patterns with implementation provenance tracking"""


# ============================================================================
# Deprecated Tables (Scheduled for Removal)
# ============================================================================

# NOTE: ticker_info table removed - see migration 018_drop_ticker_info_table.sql
# TICKER_INFO = "ticker_info"  # ❌ REMOVED (empty table, never populated)


# ============================================================================
# Convenience: All Active Tables
# ============================================================================

class TABLES:
    """Namespace for all active Aurora table names.

    Usage:
        from src.data.aurora.table_names import TABLES
        query = f"SELECT * FROM {TABLES.DAILY_PRICES}"
    """
    DAILY_PRICES = DAILY_PRICES
    TICKER_CACHE_METADATA = TICKER_CACHE_METADATA
    PRECOMPUTED_REPORTS = PRECOMPUTED_REPORTS
    TICKER_DATA = TICKER_DATA
    FUND_DATA = FUND_DATA
    DAILY_INDICATORS = DAILY_INDICATORS
    INDICATOR_PERCENTILES = INDICATOR_PERCENTILES
    COMPARATIVE_FEATURES = COMPARATIVE_FEATURES
    TICKER_MASTER = TICKER_MASTER
    TICKER_ALIASES = TICKER_ALIASES
    CHART_PATTERN_DATA = CHART_PATTERN_DATA


# ============================================================================
# Schema Validation (Optional - for future use)
# ============================================================================

def validate_table_exists(client, table_name: str) -> bool:
    """Check if table exists in Aurora database.

    Args:
        client: AuroraClient instance
        table_name: Table name to check

    Returns:
        True if table exists, False otherwise

    Example:
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.table_names import DAILY_PRICES, validate_table_exists

        client = get_aurora_client()
        if not validate_table_exists(client, DAILY_PRICES):
            raise RuntimeError(f"Table {DAILY_PRICES} does not exist in Aurora")
    """
    query = """
        SELECT COUNT(*) as cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
    """
    result = client.fetch_one(query, (table_name,))
    return result and result.get('cnt', 0) > 0


__all__ = [
    # Module-level constants
    'DAILY_PRICES',
    'TICKER_CACHE_METADATA',
    'PRECOMPUTED_REPORTS',
    'TICKER_DATA',
    'FUND_DATA',
    'DAILY_INDICATORS',
    'INDICATOR_PERCENTILES',
    'COMPARATIVE_FEATURES',
    'TICKER_MASTER',
    'TICKER_ALIASES',
    'CHART_PATTERN_DATA',

    # Convenience namespace
    'TABLES',

    # Validation utility
    'validate_table_exists',
]
