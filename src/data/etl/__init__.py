# -*- coding: utf-8 -*-
"""
ETL (Extract-Transform-Load) Module

Provides data pipeline components for loading external data sources into Aurora MySQL.

Current Pipelines:
    - Fund Data Sync: S3 CSV → Parser → Repository → Aurora

Modules:
    - fund_data_parser: CSV parsing with encoding detection
    - fund_data_sync: ETL service orchestration (TBD)
"""

# Lazy imports to avoid loading dependencies when not needed
# Import directly from modules, not via __init__ to prevent eager loading

def __getattr__(name):
    """Lazy import for ETL modules."""
    if name == 'FundDataParser':
        from .fund_data_parser import FundDataParser
        return FundDataParser
    elif name == 'get_fund_data_parser':
        from .fund_data_parser import get_fund_data_parser
        return get_fund_data_parser
    elif name == 'FundDataSyncService':
        from .fund_data_sync import FundDataSyncService
        return FundDataSyncService
    elif name == 'get_fund_data_sync_service':
        from .fund_data_sync import get_fund_data_sync_service
        return get_fund_data_sync_service
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'FundDataParser',
    'get_fund_data_parser',
    'FundDataSyncService',
    'get_fund_data_sync_service',
]
