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

from src.data.etl.fund_data_parser import (
    FundDataParser,
    get_fund_data_parser,
)

__all__ = [
    'FundDataParser',
    'get_fund_data_parser',
]
