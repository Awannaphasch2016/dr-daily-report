#!/usr/bin/env python3
"""Test Aurora adapter - fetch peer data."""

import sys
from src.workflow.aurora_data_adapter import fetch_peer_data_from_aurora

def main():
    if len(sys.argv) < 2:
        print("Usage: test_aurora_peers.py PEER1,PEER2,PEER3")
        sys.exit(1)

    peers = sys.argv[1].split(',')

    try:
        peer_data = fetch_peer_data_from_aurora(peers, days=90)

        print(f'✅ SUCCESS - Fetched {len(peer_data)}/{len(peers)} peers from Aurora!\n')

        for symbol, df in peer_data.items():
            print(f'{symbol}:')
            print(f'  Days: {len(df)}')
            print(f'  Latest close: ${df.iloc[-1]["Close"]:.2f}')
            print()

    except Exception as e:
        print(f'❌ ERROR: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
