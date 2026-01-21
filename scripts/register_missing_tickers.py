#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time script to register missing tickers from fund_data.

Finds tickers in fund_data table that don't exist in ticker_master and
registers them with metadata inferred from the ticker format.

Usage:
    # Dry-run (report only, no changes)
    python scripts/register_missing_tickers.py --dry-run

    # Execute registration
    python scripts/register_missing_tickers.py

    # With specific environment
    ENV=dev python scripts/register_missing_tickers.py
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import FUND_DATA, TICKER_MASTER, TICKER_ALIASES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_missing_tickers() -> list[dict]:
    """Find tickers in fund_data that don't exist in ticker_master.

    Returns:
        List of dicts with ticker info: {ticker, stock, sample_date}
    """
    client = get_aurora_client()

    query = f"""
        SELECT DISTINCT
            f.ticker,
            f.stock,
            MAX(f.d_trade) as latest_date
        FROM {FUND_DATA} f
        LEFT JOIN {TICKER_ALIASES} ta ON UPPER(f.ticker) = UPPER(ta.symbol)
        WHERE ta.id IS NULL
        GROUP BY f.ticker, f.stock
        ORDER BY f.ticker
    """

    rows = client.fetch_all(query)
    return [
        {
            'ticker': row['ticker'],
            'stock': row['stock'],
            'latest_date': row['latest_date']
        }
        for row in rows
    ]


def infer_ticker_metadata(ticker: str, stock: str) -> dict:
    """Infer ticker metadata from ticker format.

    Args:
        ticker: Ticker symbol (e.g., 'NVDA19', 'D05.SI')
        stock: Stock name from fund_data

    Returns:
        Dict with inferred metadata
    """
    # Exchange and currency inference based on suffix
    exchange_map = {
        '.SI': ('SGX', 'SGD'),
        '.T': ('TSE', 'JPY'),
        '.HK': ('HKEX', 'HKD'),
        '.VN': ('HOSE', 'VND'),
        '.TW': ('TWSE', 'TWD'),
        '.BK': ('SET', 'THB'),
    }

    ticker_upper = ticker.upper()
    exchange = 'NASDAQ'  # Default
    currency = 'USD'

    for suffix, (exch, curr) in exchange_map.items():
        if ticker_upper.endswith(suffix):
            exchange = exch
            currency = curr
            break

    # Check if it's a DR symbol (ends with digits like '19')
    is_dr = ticker_upper[-2:].isdigit() and len(ticker) > 2
    symbol_type = 'dr' if is_dr else 'yahoo'

    # Derive company name from stock field or ticker
    company_name = stock if stock else ticker.replace('19', '').replace('.SI', '').replace('.HK', '')

    return {
        'company_name': company_name,
        'exchange': exchange,
        'currency': currency,
        'sector': None,
        'industry': None,
        'quote_type': 'equity',
        'symbol_type': symbol_type,
    }


def register_ticker(ticker: str, metadata: dict, dry_run: bool = False) -> int:
    """Register a single ticker in ticker_master and ticker_aliases.

    Args:
        ticker: Ticker symbol
        metadata: Ticker metadata from infer_ticker_metadata
        dry_run: If True, don't make changes

    Returns:
        ticker_id of the new ticker
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would register: {ticker} -> {metadata}")
        return -1

    client = get_aurora_client()

    # Insert into ticker_master
    insert_master = f"""
        INSERT INTO {TICKER_MASTER}
            (company_name, exchange, currency, sector, industry, quote_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    client.execute(
        insert_master,
        (
            metadata['company_name'],
            metadata['exchange'],
            metadata['currency'],
            metadata['sector'],
            metadata['industry'],
            metadata['quote_type']
        ),
        commit=True
    )

    # Get the inserted ID
    result = client.fetch_one("SELECT LAST_INSERT_ID() as id")
    ticker_id = result['id']

    # Insert alias
    insert_alias = f"""
        INSERT INTO {TICKER_ALIASES}
            (ticker_id, symbol, symbol_type, is_primary)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE ticker_id = VALUES(ticker_id)
    """
    client.execute(
        insert_alias,
        (ticker_id, ticker, metadata['symbol_type'], True),
        commit=True
    )

    logger.info(f"Registered: {ticker} (id={ticker_id}, type={metadata['symbol_type']})")
    return ticker_id


def main():
    parser = argparse.ArgumentParser(
        description='Register missing tickers from fund_data into ticker_master'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report missing tickers without making changes'
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Finding missing tickers in fund_data...")
    logger.info("=" * 60)

    missing = find_missing_tickers()

    if not missing:
        logger.info("No missing tickers found. All fund_data tickers are registered.")
        return 0

    logger.info(f"Found {len(missing)} missing tickers:")
    for item in missing:
        logger.info(f"  - {item['ticker']} (stock={item['stock']}, latest={item['latest_date']})")

    if args.dry_run:
        logger.info("\n[DRY-RUN] Would register the following tickers:")

    registered_count = 0
    for item in missing:
        metadata = infer_ticker_metadata(item['ticker'], item['stock'])
        ticker_id = register_ticker(item['ticker'], metadata, dry_run=args.dry_run)
        if ticker_id > 0:
            registered_count += 1

    logger.info("=" * 60)
    if args.dry_run:
        logger.info(f"[DRY-RUN] Would register {len(missing)} tickers")
    else:
        logger.info(f"Successfully registered {registered_count} tickers")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
