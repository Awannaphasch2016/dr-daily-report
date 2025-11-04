"""
Flask web application for storing and viewing ticker reports
Groups reports by date and allows filtering by ticker
"""

from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, date
import sqlite3
import json
import os
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
# Use webapp/data/ticker_reports.db if it exists, otherwise fall back to data/ticker_reports.db
if os.path.exists('webapp/data/ticker_reports.db'):
    app.config['DATABASE'] = os.getenv('DATABASE_PATH', 'webapp/data/ticker_reports.db')
else:
    app.config['DATABASE'] = os.getenv('DATABASE_PATH', 'data/ticker_reports.db')

# Ensure data directory exists
os.makedirs('data', exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)


def init_db():
    """Initialize database with reports and pdf_archive tables"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Table for storing ticker reports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticker_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL,
            report_text TEXT NOT NULL,
            chart_base64 TEXT,
            audio_base64 TEXT,
            audio_english_base64 TEXT,
            indicators_json TEXT,
            percentiles_json TEXT,
            news_json TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, report_date)
        )
    """)

    # Index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_report_date ON ticker_reports(report_date DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker ON ticker_reports(ticker)
    """)

    # Table for PDF archive (minimalist design)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL,
            pdf_filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, report_date)
        )
    """)

    # Index for PDF archive queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pdf_ticker ON pdf_archive(ticker)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pdf_report_date ON pdf_archive(report_date DESC)
    """)

    conn.commit()
    conn.close()


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main page - PDF archive listing"""
    ticker_filter = request.args.get('ticker', '').strip()
    date_filter = request.args.get('date', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    # Build query with filters
    query = "SELECT ticker, report_date, pdf_filename, created_at FROM pdf_archive WHERE 1=1"
    params = []

    if ticker_filter:
        query += " AND ticker = ?"
        params.append(ticker_filter.upper())

    if date_filter:
        query += " AND report_date = ?"
        params.append(date_filter)

    query += " ORDER BY report_date DESC, ticker ASC"

    cursor.execute(query, params)
    reports = [dict(row) for row in cursor.fetchall()]

    # Get list of all available tickers for filter dropdown
    cursor.execute("SELECT DISTINCT ticker FROM pdf_archive ORDER BY ticker")
    available_tickers = [row['ticker'] for row in cursor.fetchall()]

    # Get list of all available dates for filter dropdown
    cursor.execute("SELECT DISTINCT report_date FROM pdf_archive ORDER BY report_date DESC")
    available_dates = [row['report_date'] for row in cursor.fetchall()]

    conn.close()

    return render_template('archive.html',
                         reports=reports,
                         ticker_filter=ticker_filter,
                         date_filter=date_filter,
                         available_tickers=available_tickers,
                         available_dates=available_dates)


@app.route('/reports/<filename>')
def serve_pdf(filename):
    """Serve PDF file from reports directory"""
    reports_dir = Path(__file__).parent.parent / 'reports'
    pdf_path = reports_dir / filename

    if not pdf_path.exists():
        return "PDF file not found", 404

    return send_file(
        pdf_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=filename
    )


@app.route('/tiles')
def tiles_view():
    """Stock tiles visualization page"""
    return render_template('tiles.html')


def calculate_52week_position(current_price, week_52_high, week_52_low):
    """Calculate position in 52-week range (0-100%)"""
    if not all([current_price, week_52_high, week_52_low]) or week_52_high == week_52_low:
        return None
    if current_price < week_52_low:
        return 0
    if current_price > week_52_high:
        return 100
    return ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100

def calculate_volatility_bucket(atr, current_price, beta=None):
    """Categorize volatility into low/medium/high buckets"""
    if atr and current_price:
        atr_percent = (atr / current_price) * 100
        if atr_percent < 1.5:
            return 'low'
        elif atr_percent < 3.5:
            return 'medium'
        else:
            return 'high'
    elif beta:
        if beta < 0.8:
            return 'low'
        elif beta < 1.3:
            return 'medium'
        else:
            return 'high'
    return None

def categorize_market_cap(market_cap):
    """Categorize market cap into small/mid/large"""
    if not market_cap:
        return None
    if market_cap >= 10e12:  # >= $10T
        return 'mega'
    elif market_cap >= 200e9:  # >= $200B
        return 'large'
    elif market_cap >= 2e9:  # >= $2B
        return 'mid'
    else:
        return 'small'

def get_sector_color(sector):
    """Get color for sector"""
    sector_colors = {
        'Technology': '#3498db',
        'Healthcare': '#e74c3c',
        'Financial Services': '#f39c12',
        'Consumer Cyclical': '#9b59b6',
        'Communication Services': '#1abc9c',
        'Industrials': '#34495e',
        'Consumer Defensive': '#e67e22',
        'Energy': '#f1c40f',
        'Utilities': '#16a085',
        'Real Estate': '#c0392b',
        'Basic Materials': '#95a5a6',
    }
    return sector_colors.get(sector, '#7f8c8d')

@app.route('/api/tiles-data')
def get_tiles_data():
    """Get data for D3.js stock tiles visualization with enhanced metrics"""
    conn = get_db()
    cursor = conn.cursor()

    # Join with ticker_reports to get financial metrics
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
    
    # Also try to get fundamental data from ticker_data.db if available
    ticker_data_conn = None
    technical_indicators_conn = None
    try:
        # Try multiple possible paths for ticker_data.db
        possible_paths = [
            os.path.join(os.path.dirname(app.config['DATABASE']), 'ticker_data.db'),
            os.path.join(os.path.dirname(os.path.dirname(app.config['DATABASE'])), 'data', 'ticker_data.db'),
            'data/ticker_data.db'
        ]
        
        for ticker_data_path in possible_paths:
            if os.path.exists(ticker_data_path):
                ticker_data_conn = sqlite3.connect(ticker_data_path)
                ticker_data_conn.row_factory = sqlite3.Row
                technical_indicators_conn = ticker_data_conn  # Same DB
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

    # Convert to list of dicts for JSON with parsed financial data
    tiles_data = []
    for report in reports:
        ticker = report['ticker']
        ticker_data = {
            'ticker': ticker,
            'date': report['date'],
            'filename': report['pdf_filename'],
            'created_at': report['created_at'],
            'recommendation': report['recommendation'] or 'N/A'
        }
        
        # Try to get fundamental data from ticker_data.db
        sector = None
        market_cap = None
        week_52_high = None
        week_52_low = None
        beta = None
        price = None
        volume = None
        atr = None
        
        # Get price and volume from ticker_data table
        if ticker_data_conn:
            try:
                ticker_cursor = ticker_data_conn.cursor()
                # Get latest price data
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
                    
                    # Try to get 52-week high/low from historical data
                    ticker_cursor.execute("""
                        SELECT MAX(high) as max_high, MIN(low) as min_low
                        FROM ticker_data
                        WHERE ticker = ? AND date >= date('now', '-365 days')
                    """, (ticker,))
                    year_data = ticker_cursor.fetchone()
                    if year_data and year_data['max_high']:
                        week_52_high = year_data['max_high']
                        week_52_low = year_data['min_low']
                
                # Get ATR from technical_indicators table
                ticker_cursor.execute("""
                    SELECT rsi, macd, sma_20, sma_50, sma_200
                    FROM technical_indicators
                    WHERE ticker = ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (ticker,))
                tech_data = ticker_cursor.fetchone()
                # Note: ATR not stored in technical_indicators, we'll calculate from price data
                
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                pass
        
        # Try to fetch sector and 52-week data from yfinance if not in DB
        if yfinance_available and (not sector or not week_52_high or not price):
            try:
                # Map ticker to Yahoo Finance symbol using tickers.csv
                yahoo_ticker = ticker_map.get(ticker, ticker)
                
                # If not in map, try common patterns
                if yahoo_ticker == ticker:
                    # Try stripping '19' suffix
                    yahoo_ticker = ticker.replace('19', '') if ticker.endswith('19') else ticker
                
                # Try the mapped ticker first, then fallback options
                possible_tickers = [yahoo_ticker]
                if yahoo_ticker != ticker:
                    possible_tickers.append(ticker)  # Also try original
                
                stock_info = None
                for yt in possible_tickers:
                    try:
                        stock = yf.Ticker(yt)
                        info = stock.info
                        if info and (info.get('sector') or info.get('currentPrice') or info.get('regularMarketPrice')):
                            stock_info = info
                            break
                    except Exception as e:
                        continue
                
                if stock_info:
                    if not sector:
                        sector = stock_info.get('sector')
                    if not market_cap:
                        market_cap = stock_info.get('marketCap')
                    if not week_52_high:
                        week_52_high = stock_info.get('fiftyTwoWeekHigh')
                    if not week_52_low:
                        week_52_low = stock_info.get('fiftyTwoWeekLow')
                    if not price:
                        price = stock_info.get('currentPrice') or stock_info.get('regularMarketPrice')
                    if not beta:
                        beta = stock_info.get('beta')
            except Exception as e:
                print(f"Error fetching yfinance data for {ticker}: {e}")
                pass
        
        # Parse indicators if available from ticker_reports table
        if report['indicators_json']:
            try:
                indicators = json.loads(report['indicators_json'])
                # Use indicators data if available, otherwise use fetched data
                if not price:
                    price = indicators.get('current_price')
                if not volume:
                    volume = indicators.get('volume')
                atr = indicators.get('atr')
                
                ticker_data.update({
                    'price': price,
                    'change': indicators.get('price_change'),
                    'changePercent': indicators.get('price_change_percent'),
                    'volume': volume,
                    'rsi': indicators.get('rsi'),
                    'macd': indicators.get('macd'),
                    'sma_20': indicators.get('sma_20'),
                    'sma_50': indicators.get('sma_50'),
                    'sma_200': indicators.get('sma_200'),
                    'atr': atr,
                })
                
                # Try to get 52-week data from indicators
                if not week_52_high:
                    week_52_high = indicators.get('fifty_two_week_high') or indicators.get('52w_high')
                if not week_52_low:
                    week_52_low = indicators.get('fifty_two_week_low') or indicators.get('52w_low')
                
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing indicators_json for {ticker}: {e}")
                pass
        
        # If we still don't have price/volume, use what we fetched from ticker_data.db
        if price and not ticker_data.get('price'):
            ticker_data['price'] = price
            # Calculate change if we have previous day's price
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
        
        # Calculate ATR if we have price data but no ATR
        if not atr and price and ticker_data_conn:
            try:
                # Simple ATR approximation: use recent price volatility
                ticker_cursor = ticker_data_conn.cursor()
                ticker_cursor.execute("""
                    SELECT high, low, close
                    FROM ticker_data
                    WHERE ticker = ?
                    ORDER BY date DESC
                    LIMIT 14
                """, (ticker,))
                recent_data = ticker_cursor.fetchall()
                if len(recent_data) >= 2:
                    # Calculate average true range
                    tr_values = []
                    for i in range(1, len(recent_data)):
                        curr_high = recent_data[i-1]['high']
                        curr_low = recent_data[i-1]['low']
                        prev_close = recent_data[i]['close']
                        tr = max(curr_high - curr_low, abs(curr_high - prev_close), abs(curr_low - prev_close))
                        tr_values.append(tr)
                    if tr_values:
                        atr = sum(tr_values) / len(tr_values)
                        ticker_data['atr'] = atr
            except Exception as e:
                print(f"Error calculating ATR for {ticker}: {e}")
                pass
        
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
        
        # Parse percentiles if available
        if report['percentiles_json']:
            try:
                percentiles = json.loads(report['percentiles_json'])
                ticker_data['percentiles'] = percentiles
            except (json.JSONDecodeError, TypeError):
                pass
        
        tiles_data.append(ticker_data)
    
    if ticker_data_conn:
        ticker_data_conn.close()

    return jsonify(tiles_data)


# Initialize database on startup
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
