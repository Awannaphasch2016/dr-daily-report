#!/usr/bin/env python3
"""
Check what's actually in the database
"""
import sqlite3
import json

db_path = 'data/ticker_reports.db'

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check ticker_reports table
cursor.execute("SELECT COUNT(*) FROM ticker_reports")
total_reports = cursor.fetchone()[0]
print(f"Total reports in ticker_reports: {total_reports}")

# Check for DBS19 specifically
cursor.execute("""
    SELECT ticker, report_date, indicators_json, recommendation
    FROM ticker_reports
    WHERE ticker = 'DBS19'
    LIMIT 1
""")
dbs19 = cursor.fetchone()

if dbs19:
    print(f"\nDBS19 record found:")
    print(f"  Ticker: {dbs19['ticker']}")
    print(f"  Date: {dbs19['report_date']}")
    print(f"  Recommendation: {dbs19['recommendation']}")
    print(f"  Indicators JSON: {dbs19['indicators_json'][:200] if dbs19['indicators_json'] else 'NULL'}...")
    
    if dbs19['indicators_json']:
        try:
            indicators = json.loads(dbs19['indicators_json'])
            print(f"\nParsed indicators:")
            print(f"  Keys: {list(indicators.keys())[:10]}")
            if 'current_price' in indicators:
                print(f"  current_price: {indicators['current_price']}")
            else:
                print(f"  current_price: NOT FOUND")
                print(f"  Available keys: {list(indicators.keys())}")
        except Exception as e:
            print(f"  Error parsing JSON: {e}")
else:
    print("\nNo DBS19 record in ticker_reports table")

# Check pdf_archive
cursor.execute("SELECT COUNT(*) FROM pdf_archive")
total_pdf = cursor.fetchone()[0]
print(f"\nTotal reports in pdf_archive: {total_pdf}")

conn.close()
