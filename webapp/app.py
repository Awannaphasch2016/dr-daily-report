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


# Initialize database on startup
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
