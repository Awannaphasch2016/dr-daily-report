#!/usr/bin/env python3
"""
Working demo: Use stock-pattern library and export results for visualization
"""

import sys
sys.path.insert(0, '/tmp/stock-pattern/src')

import utils as sp  # stock-pattern library
import pandas as pd
import yfinance as yf
import json
from pathlib import Path

def get_data(ticker, period='6mo'):
    """Fetch data from yfinance and format correctly"""
    df = yf.download(ticker, period=period, progress=False)

    # yfinance returns multi-index columns for single ticker
    # Flatten to simple column names
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # Keep only OHLCV
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    print(f"✅ {ticker}: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
    return df

def simple_pivots(df, window=5):
    """Dead simple pivot detection"""
    pivots = []

    for i in range(window, len(df) - window):
        window_high = df['High'].iloc[i-window:i+window+1]
        window_low = df['Low'].iloc[i-window:i+window+1]

        # Is this bar the highest in the window?
        if df['High'].iloc[i] == window_high.max():
            pivots.append({
                'date': df.index[i],
                'P': df['High'].iloc[i]
            })
        # Is this bar the lowest in the window?
        elif df['Low'].iloc[i] == window_low.min():
            pivots.append({
                'date': df.index[i],
                'P': df['Low'].iloc[i]
            })

    if not pivots:
        return pd.DataFrame(columns=['P'])

    piv_df = pd.DataFrame(pivots)
    piv_df.set_index('date', inplace=True)
    return piv_df

def detect_patterns(ticker, df):
    """Call all detection functions"""
    pivots = simple_pivots(df)

    if len(pivots) < 5:
        print(f"⚠️  Only {len(pivots)} pivots found, need at least 5")
        return []

    print(f"📍 {len(pivots)} pivot points found")

    # Configuration
    config = {'FLAG_MAX_BARS': 7}

    # Try each pattern
    patterns_found = []

    detectors = {
        'bullish_flag': sp.find_bullish_flag,
        'bearish_flag': sp.find_bearish_flag,
        'triangle': sp.find_triangles,
        'double_bottom': sp.find_double_bottom,
        'double_top': sp.find_double_top,
    }

    for name, detector in detectors.items():
        try:
            result = detector(ticker, df, pivots, config)
            if result:
                serialized = sp.make_serializable(result)
                patterns_found.append({
                    'type': name,
                    'pattern': serialized.get('pattern', name),
                    'points': serialized.get('points', {}),
                    'data': serialized
                })
                print(f"✅ {name.replace('_', ' ').title()} detected!")
        except Exception as e:
            # Silently skip patterns that error
            pass

    return patterns_found

def main():
    print("="*70)
    print("STOCK-PATTERN LIBRARY - WORKING DEMO")
    print("="*70)
    print()

    # Test with multiple tickers
    tickers = ['AAPL', 'TSLA', 'NVDA']
    all_results = {}

    for ticker in tickers:
        print(f"\n[{ticker}]")
        try:
            df = get_data(ticker, period='6mo')
            patterns = detect_patterns(ticker, df)

            all_results[ticker] = {
                'ticker': ticker,
                'bars': len(df),
                'date_range': {
                    'start': df.index[0].strftime('%Y-%m-%d'),
                    'end': df.index[-1].strftime('%Y-%m-%d')
                },
                'patterns': patterns,
                'ohlc': [
                    {
                        'x': int(date.timestamp() * 1000),  # milliseconds
                        'date': date.strftime('%Y-%m-%d'),
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                    }
                    for date, row in df.iterrows()
                ]
            }

            print(f"📊 Found {len(patterns)} pattern(s)")

        except Exception as e:
            print(f"❌ Error: {e}")
            all_results[ticker] = {'error': str(e)}

    # Save results
    output_file = Path(__file__).parent.parent / 'frontend' / 'pattern_detection_results.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "="*70)
    print(f"✅ Results saved to: {output_file}")
    print(f"📦 {len(all_results)} tickers processed")
    print()

    # Summary
    total_patterns = sum(len(r.get('patterns', [])) for r in all_results.values())
    print(f"📈 Total patterns detected: {total_patterns}")

    for ticker, data in all_results.items():
        if 'patterns' in data and data['patterns']:
            print(f"  {ticker}: {[p['type'] for p in data['patterns']]}")

if __name__ == '__main__':
    main()
