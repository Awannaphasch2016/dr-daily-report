#!/usr/bin/env python3
"""
Demo: Use stock-pattern library functions directly

Just import their functions, feed them data, get results.
No API, no Aurora connection needed - keep it simple!
"""

import sys
sys.path.insert(0, '/tmp/stock-pattern/src')

import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Import their detection functions directly
import utils as stock_pattern

def create_sample_data_with_flag():
    """Create OHLC data with clear bullish flag pattern"""
    import numpy as np
    np.random.seed(42)

    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    prices = []

    # Phase 1: Strong uptrend (flagpole) - 20 days
    for i in range(20):
        prices.append(100 + i * 2)

    # Phase 2: Consolidation (flag) - 15 days
    consolidation_start = prices[-1]
    for i in range(15):
        prices.append(consolidation_start - i * 0.3 + np.random.randn() * 0.5)

    # Phase 3: Continuation - 65 days
    continuation_start = prices[-1]
    for i in range(65):
        prices.append(continuation_start + i * 0.5)

    # Create OHLC
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        data.append({
            'Date': date,
            'Open': price + np.random.randn() * 0.3,
            'High': price + abs(np.random.randn()) * 0.5,
            'Low': price - abs(np.random.randn()) * 0.5,
            'Close': price + np.random.randn() * 0.3,
            'Volume': int(1000000 + np.random.randn() * 100000)
        })

    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df

def fetch_real_data(ticker='AAPL', days=90):
    """Fetch real OHLC data from yfinance"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    df = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    # yfinance already provides correctly named columns
    # Just ensure we have the required columns
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Got: {df.columns.tolist()}")

    return df[required_cols]

def find_pivots(df, window=3):
    """Simple pivot detection (smaller window for more sensitivity)"""
    pivots_data = []

    for i in range(window, len(df) - window):
        # Local high
        if df['High'].iloc[i] >= df['High'].iloc[i-window:i+window+1].max():
            pivots_data.append({
                'date': df.index[i],
                'P': df['High'].iloc[i],
                'type': 'high'
            })
        # Local low
        if df['Low'].iloc[i] <= df['Low'].iloc[i-window:i+window+1].min():
            pivots_data.append({
                'date': df.index[i],
                'P': df['Low'].iloc[i],
                'type': 'low'
            })

    if not pivots_data:
        return pd.DataFrame(columns=['P', 'type'])

    pivots_df = pd.DataFrame(pivots_data)
    pivots_df.set_index('date', inplace=True)
    return pivots_df

def detect_all_patterns(ticker, df):
    """Run their detection functions"""
    patterns = []
    pivots = find_pivots(df)

    print(f"\n{'='*70}")
    print(f"Pattern Detection for {ticker}")
    print(f"{'='*70}")
    print(f"Data: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Pivots: {len(pivots)} found\n")

    if len(pivots) < 3:
        print("⚠️  Insufficient pivot points for detection")
        return patterns

    config = {'FLAG_MAX_BARS': 5}

    # Try each pattern type
    detection_functions = [
        ('Bullish Flag', stock_pattern.find_bullish_flag),
        ('Bearish Flag', stock_pattern.find_bearish_flag),
        ('Triangle', stock_pattern.find_triangles),
    ]

    for pattern_name, detect_fn in detection_functions:
        try:
            result = detect_fn(ticker, df, pivots, config)
            if result:
                serialized = stock_pattern.make_serializable(result)
                patterns.append({
                    'type': pattern_name,
                    'data': serialized
                })
                print(f"✅ {pattern_name} detected!")
                print(f"   Points: {list(serialized.get('points', {}).keys())}")
        except Exception as e:
            print(f"❌ {pattern_name}: {str(e)[:50]}")

    return patterns

def main():
    """Run pattern detection demo"""
    print("\n" + "="*70)
    print("STOCK-PATTERN LIBRARY DEMO")
    print("="*70)

    # Test 1: Sample data with known flag pattern
    print("\n[TEST 1] Sample data (designed to have bullish flag)")
    sample_df = create_sample_data_with_flag()
    sample_patterns = detect_all_patterns('SAMPLE', sample_df)

    # Test 2: Real data
    print("\n[TEST 2] Real data from yfinance")
    for ticker in ['AAPL', 'TSLA']:
        try:
            real_df = fetch_real_data(ticker, days=90)
            real_patterns = detect_all_patterns(ticker, real_df)
        except Exception as e:
            print(f"❌ {ticker}: {str(e)}")

    # Output results as JSON for frontend
    print("\n" + "="*70)
    print("JSON OUTPUT (for frontend visualization)")
    print("="*70)

    output = {
        'sample_data': {
            'ticker': 'SAMPLE',
            'patterns': sample_patterns,
            'ohlc': [
                {
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                }
                for date, row in sample_df.iterrows()
            ]
        }
    }

    # Save to file
    output_file = '/tmp/pattern_detection_results.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print(f"\nPatterns found: {len(sample_patterns)}")

    if sample_patterns:
        print("\nPattern details:")
        for p in sample_patterns:
            print(json.dumps(p, indent=2))

if __name__ == '__main__':
    main()
