import sqlite3
from datetime import datetime
import json

class TickerDatabase:
    def __init__(self, db_path="/tmp/ticker_data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table for ticker data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticker_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                market_cap REAL,
                pe_ratio REAL,
                eps REAL,
                dividend_yield REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date)
            )
        """)

        # Table for technical indicators
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                sma_20 REAL,
                sma_50 REAL,
                sma_200 REAL,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                volume_sma REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date)
            )
        """)

        # Table for generated reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                report_text TEXT,
                technical_summary TEXT,
                fundamental_summary TEXT,
                sector_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, date)
            )
        """)

        conn.commit()
        conn.close()

    def insert_ticker_data(self, symbol, ticker, date, data):
        """Insert ticker price and fundamental data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO ticker_data
            (symbol, ticker, date, open, high, low, close, volume, market_cap, pe_ratio, eps, dividend_yield)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, ticker, date, data.get('open'), data.get('high'),
              data.get('low'), data.get('close'), data.get('volume'),
              data.get('market_cap'), data.get('pe_ratio'),
              data.get('eps'), data.get('dividend_yield')))

        conn.commit()
        conn.close()

    def insert_technical_indicators(self, ticker, date, indicators):
        """Insert technical indicators"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO technical_indicators
            (ticker, date, sma_20, sma_50, sma_200, rsi, macd, macd_signal,
             bb_upper, bb_middle, bb_lower, volume_sma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, date, indicators.get('sma_20'), indicators.get('sma_50'),
              indicators.get('sma_200'), indicators.get('rsi'),
              indicators.get('macd'), indicators.get('macd_signal'),
              indicators.get('bb_upper'), indicators.get('bb_middle'),
              indicators.get('bb_lower'), indicators.get('volume_sma')))

        conn.commit()
        conn.close()

    def save_report(self, ticker, date, report_data):
        """Save generated report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO reports
            (ticker, date, report_text, technical_summary, fundamental_summary, sector_analysis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, date, report_data.get('report_text'),
              report_data.get('technical_summary'),
              report_data.get('fundamental_summary'),
              report_data.get('sector_analysis')))

        conn.commit()
        conn.close()

    def get_latest_data(self, ticker, days=30):
        """Get latest ticker data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ticker_data
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
        """, (ticker, days))

        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_latest_indicators(self, ticker):
        """Get latest technical indicators"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM technical_indicators
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
        """, (ticker,))

        row = cursor.fetchone()
        conn.close()
        return row

    def get_cached_report(self, ticker, date):
        """Get cached report if available"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT report_text FROM reports
            WHERE ticker = ? AND date = ?
        """, (ticker, date))

        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
