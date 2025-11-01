import sqlite3
from datetime import datetime
import json

class TickerDatabase:
    def __init__(self, db_path="data/ticker_data.db"):
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

        # Table for QoS metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qos_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                overall_score REAL,
                latency_score REAL,
                cost_efficiency_score REAL,
                determinism_score REAL,
                reliability_score REAL,
                resource_efficiency_score REAL,
                scalability_score REAL,
                total_latency REAL,
                data_fetch_latency REAL,
                news_fetch_latency REAL,
                technical_analysis_latency REAL,
                chart_generation_latency REAL,
                llm_generation_latency REAL,
                scoring_latency REAL,
                llm_cost_actual REAL,
                llm_cost_estimated REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                llm_calls INTEGER,
                db_query_count INTEGER,
                cache_hit INTEGER DEFAULT 0,
                error_occurred INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for querying historical trends
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_qos_ticker_date 
            ON qos_metrics(ticker, date DESC)
        """)

        # Table for cost metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                overall_cost_thb REAL,
                cost_efficiency_score REAL,
                llm_cost_thb REAL,
                llm_cost_usd REAL,
                db_cost_thb REAL,
                db_query_count INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                llm_calls INTEGER,
                cache_hit INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for querying historical cost trends
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_ticker_date 
            ON cost_metrics(ticker, date DESC)
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
    
    def save_qos_metrics(self, ticker, date, qos_score):
        """
        Save QoS metrics to database
        
        Args:
            ticker: Ticker symbol
            date: Report date
            qos_score: QoSScore dataclass object
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timing = qos_score.metrics.get('timing', {})
        costs = qos_score.metrics.get('costs', {})
        database = qos_score.metrics.get('database', {})
        
        cursor.execute("""
            INSERT INTO qos_metrics (
                ticker, date,
                overall_score,
                latency_score, cost_efficiency_score, determinism_score,
                reliability_score, resource_efficiency_score, scalability_score,
                total_latency,
                data_fetch_latency, news_fetch_latency, technical_analysis_latency,
                chart_generation_latency, llm_generation_latency, scoring_latency,
                llm_cost_actual, llm_cost_estimated,
                input_tokens, output_tokens, llm_calls,
                db_query_count, cache_hit, error_occurred
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, date,
            qos_score.overall_score,
            qos_score.dimension_scores.get('latency', 0),
            qos_score.dimension_scores.get('cost_efficiency', 0),
            qos_score.dimension_scores.get('determinism', 0),
            qos_score.dimension_scores.get('reliability', 0),
            qos_score.dimension_scores.get('resource_efficiency', 0),
            qos_score.dimension_scores.get('scalability', 0),
            timing.get('total', 0),
            timing.get('data_fetch', 0),
            timing.get('news_fetch', 0),
            timing.get('technical_analysis', 0),
            timing.get('chart_generation', 0),
            timing.get('llm_generation', 0),
            timing.get('scoring', 0),
            costs.get('llm_actual'),
            costs.get('llm_estimated', 0),
            costs.get('input_tokens', 0),
            costs.get('output_tokens', 0),
            qos_score.metrics.get('llm_calls', 0),
            database.get('query_count', 0),
            1 if qos_score.metrics.get('cache_hit') else 0,
            1 if qos_score.metrics.get('error_occurred') else 0
        ))
        
        conn.commit()
        conn.close()
    
    def save_cost_metrics(self, ticker, date, cost_score):
        """
        Save cost metrics to database
        
        Args:
            ticker: Ticker symbol
            date: Report date
            cost_score: CostScore dataclass object
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cost_breakdown = cost_score.cost_breakdown
        token_usage = cost_score.token_usage
        
        cursor.execute("""
            INSERT INTO cost_metrics (
                ticker, date,
                overall_cost_thb, cost_efficiency_score,
                llm_cost_thb, llm_cost_usd, db_cost_thb,
                db_query_count,
                input_tokens, output_tokens, total_tokens,
                llm_calls, cache_hit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker, date,
            cost_score.overall_cost_thb,
            cost_score.cost_efficiency_score,
            cost_breakdown.get('llm_cost_thb', 0),
            cost_breakdown.get('llm_cost_usd', 0),
            cost_breakdown.get('db_cost_thb', 0),
            cost_breakdown.get('db_query_count', 0),
            token_usage.get('input_tokens', 0),
            token_usage.get('output_tokens', 0),
            token_usage.get('total_tokens', 0),
            cost_score.llm_calls,
            0  # cache_hit (could be enhanced)
        ))
        
        conn.commit()
        conn.close()
    
    def get_historical_qos(self, ticker, days=30):
        """
        Get historical QoS metrics for trend analysis
        
        Args:
            ticker: Ticker symbol
            days: Number of days to look back
        
        Returns:
            Dict with historical metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                overall_score, total_latency, llm_cost_estimated,
                data_fetch_latency, technical_analysis_latency,
                llm_calls, db_query_count, cache_hit, error_occurred,
                created_at
            FROM qos_metrics
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
        """, (ticker, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # Return most recent entry as baseline
        row = rows[0]
        return {
            'overall_score': row[0],
            'timing': {
                'total': row[1],
                'data_fetch': row[3],
                'technical_analysis': row[4]
            },
            'cost': row[2],
            'llm_calls': row[5],
            'db_query_count': row[6],
            'cache_hit': bool(row[7]),
            'error_occurred': bool(row[8]),
            'timestamp': row[9]
        }
