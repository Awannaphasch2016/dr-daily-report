#!/usr/bin/env python3
"""
List all tickers from ticker_master table in Aurora.

Usage:
    ENV=dev doppler run --config dev_local -- python scripts/list_ticker_master.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.aurora.client import get_aurora_client


def main():
    print("🔌 Connecting to Aurora...")
    client = get_aurora_client()

    print("📋 Querying ticker_master table...")
    query = """
        SELECT symbol, company_name, market, sector, industry
        FROM ticker_master
        ORDER BY symbol
    """

    results = client.fetch_all(query, ())

    print(f"\n✅ Found {len(results)} tickers in ticker_master:\n")
    print(f"{'Symbol':<12} {'Company Name':<50} {'Market':<8} {'Sector':<30}")
    print("=" * 120)

    for row in results:
        symbol = row.get('symbol', '')
        company = row.get('company_name', '')[:48]
        market = row.get('market', '')
        sector = row.get('sector', '')[:28] if row.get('sector') else ''
        print(f"{symbol:<12} {company:<50} {market:<8} {sector:<30}")

    print(f"\n📊 Total: {len(results)} tickers")


if __name__ == "__main__":
    main()
