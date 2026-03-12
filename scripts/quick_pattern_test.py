#!/usr/bin/env python3
"""
Simplest possible test - just import and use their functions
"""

import sys
sys.path.insert(0, '/tmp/stock-pattern/src')

import utils
import pandas as pd
import yfinance as yf
import json

# Get real data
ticker = 'AAPL'
df = yf.download(ticker, period='6mo', progress=False)

# Their functions expect these columns
print(f"Downloaded {len(df)} bars for {ticker}")
print(f"Columns: {df.columns.tolist()}")
print(f"Date range: {df.index[0]} to {df.index[-1]}")

# Try to call one of their functions directly
# Most of them need pivots, so let's try a simple one first

# Let's just see what functions are available
pattern_functions = [name for name in dir(utils) if name.startswith('find_')]
print(f"\nAvailable pattern functions:")
for fn in pattern_functions:
    print(f"  - {fn}")

print("\n✅ Import successful! Their library works.")
print("Next step: Create proper OHLC data and call detection functions")
