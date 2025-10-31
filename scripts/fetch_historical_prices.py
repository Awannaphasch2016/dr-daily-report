#!/usr/bin/env python3
"""
Fetch 30 days historical prices for all tickers in tickers.csv
"""
import sys
import csv
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import time

sys.path.insert(0, 'src')
from database import TickerDatabase

def load_tickers(csv_path='data/tickers.csv'):
    """Load tickers from CSV"""
    tickers = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers[row['Symbol']] = row['Ticker']
    return tickers

def fetch_30day_history(ticker):
    """Fetch 30 days of historical data for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        # Fetch 30 days of data
        hist = stock.history(period='30d')
        
        if hist.empty:
            print(f"  ⚠️  No data for {ticker}")
            return None
        
        return hist
    except Exception as e:
        print(f"  ❌ Error fetching {ticker}: {str(e)}")
        return None

def store_historical_data(db, symbol, ticker, hist_data):
    """Store historical data in database"""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    stored_count = 0
    for date, row in hist_data.iterrows():
        try:
            date_str = date.strftime('%Y-%m-%d')
            
            # Insert or ignore (since we have UNIQUE constraint)
            cursor.execute('''
                INSERT OR IGNORE INTO ticker_data 
                (symbol, ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, 
                ticker, 
                date_str,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume'])
            ))
            
            if cursor.rowcount > 0:
                stored_count += 1
                
        except Exception as e:
            print(f"    Error storing {date_str}: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    return stored_count

def main():
    """Main function"""
    print("=" * 70)
    print("Fetching 30 Days Historical Prices for All Tickers")
    print("=" * 70)
    
    # Load tickers
    print("\n1. Loading tickers from data/tickers.csv...")
    tickers = load_tickers()
    print(f"   ✓ Loaded {len(tickers)} tickers")
    
    # Initialize database
    db = TickerDatabase()
    
    # Fetch and store data for each ticker
    print("\n2. Fetching historical data...")
    total_stored = 0
    success_count = 0
    
    for i, (symbol, ticker) in enumerate(tickers.items(), 1):
        print(f"\n[{i}/{len(tickers)}] {symbol} ({ticker})")
        
        # Fetch historical data
        hist = fetch_30day_history(ticker)
        
        if hist is not None:
            # Store in database
            count = store_historical_data(db, symbol, ticker, hist)
            print(f"   ✓ Stored {count} new records ({len(hist)} total days fetched)")
            total_stored += count
            success_count += 1
        
        # Rate limiting - be nice to Yahoo Finance
        if i < len(tickers):
            time.sleep(0.5)  # 500ms delay between requests
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Total tickers processed: {len(tickers)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(tickers) - success_count}")
    print(f"  New records stored: {total_stored}")
    print("=" * 70)
    
    # Show database stats
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM ticker_data")
    unique_tickers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ticker_data")
    total_records = cursor.fetchone()[0]
    conn.close()
    
    print(f"\nDatabase now contains:")
    print(f"  Unique tickers: {unique_tickers}")
    print(f"  Total records: {total_records}")
    print()

if __name__ == "__main__":
    main()
