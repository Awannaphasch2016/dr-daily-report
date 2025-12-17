#!/usr/bin/env python3
"""Test Aurora adapter - fetch ticker data."""

import sys
from src.workflow.aurora_data_adapter import fetch_ticker_data_from_aurora

def main():
    if len(sys.argv) < 2:
        print("Usage: test_aurora_ticker.py SYMBOL")
        sys.exit(1)

    symbol = sys.argv[1]

    try:
        data = fetch_ticker_data_from_aurora(symbol)

        print('✅ SUCCESS - Fetched data from Aurora!')
        print('\n📊 Company Information:')
        print(f'   Company: {data["company_name"]}')
        print(f'   Sector: {data.get("sector") or "N/A"}')
        print(f'   Industry: {data.get("industry") or "N/A"}')

        print('\n💰 Fundamentals:')
        if data.get('market_cap'):
            print(f'   Market Cap: ${data["market_cap"]:,.0f}')
        if data.get('pe_ratio'):
            print(f'   P/E Ratio: {data["pe_ratio"]:.2f}')
        if data.get('eps'):
            print(f'   EPS: ${data["eps"]:.2f}')
        if data.get('dividend_yield'):
            print(f'   Dividend Yield: {data["dividend_yield"]:.2f}%')

        print('\n📈 Latest Price:')
        print(f'   Close: ${data["close"]:.2f}')
        print(f'   Volume: {data["volume"]:,}')

        print('\n📉 Historical Data:')
        print(f'   Total days: {len(data["history"])}')
        print(f'   DataFrame shape: {data["history"].shape}')

    except Exception as e:
        print(f'❌ ERROR: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
