#!/usr/bin/env python3
"""
Standalone Bokeh Tiles Visualization Test
Generates an HTML file with the Bokeh visualization for manual validation
"""
import sys
import os
import sqlite3
import json
from pathlib import Path

# Add webapp to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))

# Import Flask app to get database connection logic
from flask import Flask
from app import app, get_db

# Import Bokeh visualization
from bokeh_tiles import create_tiles_visualization
from bokeh.resources import CDN
from bokeh.embed import file_html

def get_tiles_data():
    """Get tiles data directly from database"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Same query as in app.py
    cursor.execute("""
        SELECT 
            pa.ticker,
            pa.report_date as date,
            pa.pdf_filename,
            tr.indicators_json,
            tr.percentiles_json,
            tr.recommendation,
            tr.created_at
        FROM pdf_archive pa
        LEFT JOIN ticker_reports tr ON pa.ticker = tr.ticker AND pa.report_date = tr.report_date
        ORDER BY pa.report_date DESC, pa.ticker ASC
    """)
    
    reports = cursor.fetchall()
    
    # Process data similar to get_tiles_data() in app.py
    # For now, use simplified processing
    tiles_data = []
    
    # Try to get fundamental data from ticker_data.db
    ticker_data_conn = None
    try:
        possible_paths = [
            os.path.join(os.path.dirname(app.config['DATABASE']), 'ticker_data.db'),
            os.path.join(os.path.dirname(os.path.dirname(app.config['DATABASE'])), 'data', 'ticker_data.db'),
            'data/ticker_data.db',
            '../data/ticker_data.db'
        ]
        
        for ticker_data_path in possible_paths:
            if os.path.exists(ticker_data_path):
                ticker_data_conn = sqlite3.connect(ticker_data_path)
                ticker_data_conn.row_factory = sqlite3.Row
                break
    except Exception as e:
        print(f"Warning: Could not connect to ticker_data.db: {e}")
        pass
    
    conn.close()
    
    # Try to fetch live data using yfinance if available
    try:
        import yfinance as yf
        import pandas as pd
        yfinance_available = True
        
        # Load ticker mapping
        ticker_map = {}
        try:
            tickers_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tickers.csv')
            if os.path.exists(tickers_csv_path):
                df = pd.read_csv(tickers_csv_path)
                ticker_map = dict(zip(df['Symbol'], df['Ticker']))
        except:
            pass
    except ImportError:
        yfinance_available = False
        ticker_map = {}
    
    # Import helper functions from app
    from app import (
        calculate_52week_position,
        calculate_volatility_bucket,
        categorize_market_cap,
        get_sector_color
    )
    
    # Process each report
    for report in reports:
        ticker = report['ticker']
        ticker_data = {
            'ticker': ticker,
            'date': report['date'],
            'filename': report['pdf_filename'],
            'created_at': report['created_at'],
            'recommendation': report['recommendation'] or 'N/A'
        }
        
        # Get fundamental data from ticker_data.db
        sector = None
        market_cap = None
        week_52_high = None
        week_52_low = None
        beta = None
        price = None
        volume = None
        
        if ticker_data_conn:
            try:
                ticker_cursor = ticker_data_conn.cursor()
                ticker_cursor.execute("""
                    SELECT close, volume, market_cap, high, low
                    FROM ticker_data
                    WHERE ticker = ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (ticker,))
                price_data = ticker_cursor.fetchone()
                if price_data:
                    price = price_data['close']
                    volume = price_data['volume']
                    market_cap = price_data['market_cap']
                    
                    ticker_cursor.execute("""
                        SELECT MAX(high) as max_high, MIN(low) as min_low
                        FROM ticker_data
                        WHERE ticker = ? AND date >= date('now', '-365 days')
                    """, (ticker,))
                    year_data = ticker_cursor.fetchone()
                    if year_data and year_data['max_high']:
                        week_52_high = year_data['max_high']
                        week_52_low = year_data['min_low']
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                pass
        
        # Try yfinance if not in DB
        if yfinance_available and (not sector or not week_52_high or not price):
            try:
                yahoo_ticker = ticker_map.get(ticker, ticker)
                if yahoo_ticker == ticker:
                    yahoo_ticker = ticker.replace('19', '') if ticker.endswith('19') else ticker
                
                stock = yf.Ticker(yahoo_ticker)
                info = stock.info
                if info:
                    if not sector:
                        sector = info.get('sector')
                    if not market_cap:
                        market_cap = info.get('marketCap')
                    if not week_52_high:
                        week_52_high = info.get('fiftyTwoWeekHigh')
                    if not week_52_low:
                        week_52_low = info.get('fiftyTwoWeekLow')
                    if not price:
                        price = info.get('currentPrice') or info.get('regularMarketPrice')
                    if not beta:
                        beta = info.get('beta')
            except Exception as e:
                pass
        
        # Parse indicators if available
        if report['indicators_json']:
            try:
                indicators = json.loads(report['indicators_json'])
                if not price:
                    price = indicators.get('current_price')
                if not volume:
                    volume = indicators.get('volume')
                if not week_52_high:
                    week_52_high = indicators.get('fifty_two_week_high') or indicators.get('52w_high')
                if not week_52_low:
                    week_52_low = indicators.get('fifty_two_week_low') or indicators.get('52w_low')
                
                ticker_data.update({
                    'price': price,
                    'change': indicators.get('price_change', 0),
                    'changePercent': indicators.get('price_change_percent', 0),
                    'volume': volume,
                })
            except:
                pass
        
        if price and not ticker_data.get('price'):
            ticker_data['price'] = price
            if ticker_data_conn:
                try:
                    ticker_cursor = ticker_data_conn.cursor()
                    ticker_cursor.execute("""
                        SELECT close
                        FROM ticker_data
                        WHERE ticker = ? AND date < ?
                        ORDER BY date DESC
                        LIMIT 1
                    """, (ticker, report['date']))
                    prev_data = ticker_cursor.fetchone()
                    if prev_data and prev_data['close']:
                        prev_price = prev_data['close']
                        change = price - prev_price
                        change_percent = (change / prev_price) * 100 if prev_price else 0
                        ticker_data['change'] = change
                        ticker_data['changePercent'] = change_percent
                except:
                    pass
        
        if volume and not ticker_data.get('volume'):
            ticker_data['volume'] = volume
        
        # Calculate 52-week position
        if ticker_data.get('price') and week_52_high and week_52_low:
            week_52_position = calculate_52week_position(
                ticker_data['price'], week_52_high, week_52_low
            )
            ticker_data['week52Position'] = week_52_position
            ticker_data['week52High'] = week_52_high
            ticker_data['week52Low'] = week_52_low
        else:
            ticker_data['week52Position'] = None
        
        # Calculate volatility bucket
        volatility_bucket = calculate_volatility_bucket(
            ticker_data.get('atr'),
            ticker_data.get('price'),
            beta
        )
        ticker_data['volatilityBucket'] = volatility_bucket
        
        # Categorize market cap
        market_cap_category = categorize_market_cap(market_cap)
        ticker_data['marketCap'] = market_cap
        ticker_data['marketCapCategory'] = market_cap_category
        
        # Sector information
        ticker_data['sector'] = sector or 'Unknown'
        ticker_data['sectorColor'] = get_sector_color(sector) if sector else '#7f8c8d'
        
        tiles_data.append(ticker_data)
    
    if ticker_data_conn:
        ticker_data_conn.close()
    
    return tiles_data

def main():
    print("=" * 60)
    print("Bokeh Tiles Visualization Generator")
    print("=" * 60)
    
    # Get data
    print("\n1. Fetching data from database...")
    with app.app_context():
        tiles_data = get_tiles_data()
    
    print(f"   ✅ Got {len(tiles_data)} records")
    if len(tiles_data) > 0:
        print(f"   Sample tickers: {[d['ticker'] for d in tiles_data[:5]]}")
    
    if not tiles_data:
        print("\n❌ No data available. Cannot generate visualization.")
        return
    
    # Create visualization
    print("\n2. Creating Bokeh visualization...")
    try:
        script, div = create_tiles_visualization(tiles_data, container_width=1600)
        print(f"   ✅ Script length: {len(script)} characters")
        print(f"   ✅ Div length: {len(div)} characters")
        print(f"   ✅ Contains Bokeh: {'Bokeh' in script}")
    except Exception as e:
        print(f"   ❌ Error creating visualization: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create standalone HTML
    print("\n3. Generating standalone HTML file...")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bokeh Stock Tiles Visualization - Test</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f5f7fa;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .info {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            color: #555;
        }}
    </style>
    {script}
</head>
<body>
    <div class="container">
        <h1>📈 Stock Tiles Visualization - Bokeh Test</h1>
        <div class="info">
            <strong>Data:</strong> {len(tiles_data)} records | 
            <strong>Generated:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        {div}
    </div>
</body>
</html>"""
    
    # Save to file
    output_file = 'bokeh_tiles_test.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    abs_path = os.path.abspath(output_file)
    print(f"   ✅ Saved to: {abs_path}")
    print(f"\n📖 Open this file in your browser to view the visualization:")
    print(f"   file://{abs_path}")
    print(f"\n   Or run: open {output_file}")

if __name__ == '__main__':
    main()
