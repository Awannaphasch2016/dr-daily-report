# -*- coding: utf-8 -*-
"""
Aurora MySQL Setup Script

DEPRECATED: This script is deprecated after ticker_info table removal (migration 018).
The historical price storage system (ticker_info + daily_prices) has been removed.
Use database migrations (db/migrations/) for schema changes instead.

If Aurora historical storage is needed, refactor to use ticker_master instead of ticker_info.

Run this from Lambda or a VPC-connected environment to:
1. Create database tables
2. Import ticker data from S3 to Aurora

Usage (from Lambda):
    from scripts.aurora_setup import setup_aurora
    result = setup_aurora()
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# SQL for table creation
CREATE_TABLES_SQL = """
-- Table: ticker_info
CREATE TABLE IF NOT EXISTS ticker_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    company_name VARCHAR(255),
    exchange VARCHAR(50),
    market VARCHAR(50),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_fetched_at TIMESTAMP NULL,
    INDEX idx_ticker_info_market (market),
    INDEX idx_ticker_info_sector (sector),
    INDEX idx_ticker_info_exchange (exchange),
    INDEX idx_ticker_info_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: daily_prices
CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open DECIMAL(18, 6),
    high DECIMAL(18, 6),
    low DECIMAL(18, 6),
    close DECIMAL(18, 6),
    adj_close DECIMAL(18, 6),
    volume BIGINT,
    daily_return DECIMAL(10, 6),
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, price_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,
    INDEX idx_daily_prices_symbol (symbol),
    INDEX idx_daily_prices_date (price_date),
    INDEX idx_daily_prices_symbol_date (symbol, price_date DESC),
    INDEX idx_daily_prices_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: ticker_cache_metadata
CREATE TABLE IF NOT EXISTS ticker_cache_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,
    s3_key VARCHAR(500),
    s3_etag VARCHAR(100),
    status ENUM('pending', 'cached', 'expired', 'error') DEFAULT 'pending',
    error_message TEXT,
    rows_in_s3 INT DEFAULT 0,
    rows_in_aurora INT DEFAULT 0,
    cached_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_cache_date (symbol, cache_date),
    INDEX idx_cache_status (status),
    INDEX idx_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def get_aurora_client():
    """Get Aurora client (import here to avoid circular imports)."""
    from src.data.aurora.client import get_aurora_client as _get_aurora_client
    return _get_aurora_client()


def create_tables() -> Dict[str, Any]:
    """Create Aurora tables if they don't exist.

    Returns:
        Dict with status and message
    """
    client = get_aurora_client()

    # Split into individual statements
    statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]

    results = []
    for stmt in statements:
        # Remove leading comments and whitespace
        lines = stmt.strip().split('\n')
        clean_lines = [l for l in lines if not l.strip().startswith('--')]
        clean_stmt = '\n'.join(clean_lines).strip()

        if not clean_stmt:
            continue

        try:
            client.execute(clean_stmt + ';', commit=True)
            results.append({'statement': clean_stmt[:50] + '...', 'status': 'success'})
            logger.info(f"Executed: {clean_stmt[:50]}...")
        except Exception as e:
            results.append({'statement': clean_stmt[:50] + '...', 'status': 'error', 'error': str(e)})
            logger.error(f"Failed to execute: {clean_stmt[:50]}... Error: {e}")

    return {
        'status': 'completed',
        'tables_created': ['ticker_info', 'daily_prices', 'ticker_cache_metadata'],
        'results': results
    }


def list_s3_ticker_data(bucket: str, prefix: str = 'cache/ticker_data/') -> List[Dict[str, str]]:
    """List all ticker data files in S3.

    Args:
        bucket: S3 bucket name
        prefix: S3 key prefix

    Returns:
        List of dicts with ticker, date, s3_key
    """
    s3 = boto3.client('s3')
    ticker_files = []

    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            # Parse: cache/ticker_data/{ticker}/{date}/data.json
            parts = key.split('/')
            if len(parts) >= 5 and parts[-1] == 'data.json':
                ticker = parts[2]
                date = parts[3]
                ticker_files.append({
                    'ticker': ticker,
                    'date': date,
                    's3_key': key
                })

    return ticker_files


def import_ticker_from_s3(bucket: str, ticker: str, date: str, s3_key: str) -> Dict[str, Any]:
    """Import a single ticker's data from S3 to Aurora.

    Args:
        bucket: S3 bucket name
        ticker: Ticker symbol
        date: Date string (YYYY-MM-DD)
        s3_key: Full S3 key path

    Returns:
        Dict with import status
    """
    s3 = boto3.client('s3')

    try:
        # Fetch from S3
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        data = json.loads(response['Body'].read().decode('utf-8'))

        # Get Aurora repository
        from src.data.aurora.repository import TickerRepository
        repo = TickerRepository()

        # Upsert ticker info
        info = data.get('info', {})
        repo.upsert_ticker_info(
            symbol=ticker,
            display_name=info.get('shortName', ticker),
            company_name=info.get('longName'),
            exchange=info.get('exchange'),
            market=info.get('market'),
            currency=info.get('currency'),
            sector=info.get('sector'),
            industry=info.get('industry'),
            quote_type=info.get('quoteType'),
        )

        # Import history if available
        history = data.get('history', [])
        rows_imported = 0

        if history and isinstance(history, list):
            import pandas as pd
            df = pd.DataFrame(history)
            if not df.empty:
                rows_imported = repo.bulk_upsert_from_dataframe(ticker, df)

        return {
            'ticker': ticker,
            'date': date,
            'status': 'success',
            'rows_imported': rows_imported
        }

    except Exception as e:
        logger.error(f"Failed to import {ticker} from {s3_key}: {e}")
        return {
            'ticker': ticker,
            'date': date,
            'status': 'error',
            'error': str(e)
        }


def import_all_from_s3(bucket: str = None, limit: int = None) -> Dict[str, Any]:
    """Import all ticker data from S3 to Aurora.

    Args:
        bucket: S3 bucket name (defaults to PDF_BUCKET_NAME env)
        limit: Max number of tickers to import (for testing)

    Returns:
        Dict with import summary
    """
    bucket = bucket or os.environ.get('PDF_BUCKET_NAME', 'line-bot-pdf-reports-755283537543')

    logger.info(f"Listing ticker data in s3://{bucket}/cache/ticker_data/")
    ticker_files = list_s3_ticker_data(bucket)

    if limit:
        ticker_files = ticker_files[:limit]

    logger.info(f"Found {len(ticker_files)} ticker files to import")

    results = {
        'total': len(ticker_files),
        'success': 0,
        'failed': 0,
        'errors': []
    }

    for file_info in ticker_files:
        result = import_ticker_from_s3(
            bucket=bucket,
            ticker=file_info['ticker'],
            date=file_info['date'],
            s3_key=file_info['s3_key']
        )

        if result['status'] == 'success':
            results['success'] += 1
            logger.info(f"Imported {result['ticker']}: {result['rows_imported']} rows")
        else:
            results['failed'] += 1
            results['errors'].append(result)
            logger.error(f"Failed {result['ticker']}: {result.get('error')}")

    return results


def cleanup_prices() -> Dict[str, Any]:
    """Delete all price data (but keep ticker_info) for reimport.

    Returns:
        Dict with cleanup status
    """
    client = get_aurora_client()

    try:
        # Delete all daily prices
        result = client.execute("DELETE FROM daily_prices", commit=True)
        logger.info(f"Deleted {result} price rows")

        return {
            'status': 'success',
            'rows_deleted': result
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def setup_aurora(create_tables_only: bool = False, import_limit: int = None, cleanup_first: bool = False) -> Dict[str, Any]:
    """Full Aurora setup: create tables and import data.

    Args:
        create_tables_only: Only create tables, skip import
        import_limit: Limit number of tickers to import (for testing)
        cleanup_first: Delete all prices before reimporting (fixes bad data)

    Returns:
        Dict with setup summary
    """
    logger.info("Starting Aurora setup...")

    # Step 1: Create tables
    logger.info("Creating tables...")
    table_result = create_tables()
    logger.info(f"Tables created: {table_result['tables_created']}")

    if create_tables_only:
        return {
            'status': 'completed',
            'tables': table_result,
            'import': None
        }

    # Step 1.5: Cleanup if requested
    cleanup_result = None
    if cleanup_first:
        logger.info("Cleaning up old price data...")
        cleanup_result = cleanup_prices()
        logger.info(f"Cleanup: {cleanup_result}")

    # Step 2: Import data from S3
    logger.info("Importing data from S3...")
    import_result = import_all_from_s3(limit=import_limit)

    return {
        'status': 'completed',
        'tables': table_result,
        'cleanup': cleanup_result,
        'import': import_result
    }


def lambda_handler(event, context):
    """Lambda entry point for Aurora setup.

    Event params:
        create_tables_only: bool - Only create tables
        import_limit: int - Limit number of tickers to import
        cleanup_first: bool - Delete all prices before reimporting
    """
    create_tables_only = event.get('create_tables_only', False)
    import_limit = event.get('import_limit')
    cleanup_first = event.get('cleanup_first', False)

    result = setup_aurora(
        create_tables_only=create_tables_only,
        import_limit=import_limit,
        cleanup_first=cleanup_first
    )

    return {
        'statusCode': 200,
        'body': json.dumps(result, default=str)
    }


if __name__ == '__main__':
    # For local testing with Doppler
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--tables-only':
        result = setup_aurora(create_tables_only=True)
    elif len(sys.argv) > 1 and sys.argv[1] == '--test':
        result = setup_aurora(import_limit=5)
    else:
        result = setup_aurora()

    print(json.dumps(result, indent=2, default=str))
