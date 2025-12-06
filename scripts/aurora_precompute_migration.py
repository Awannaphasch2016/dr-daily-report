# -*- coding: utf-8 -*-
"""
Aurora Precomputation Tables Migration

Creates tables for precomputed indicators, percentiles, correlations,
comparative features, and full reports for instant retrieval.

Usage (from Lambda):
    from scripts.aurora_precompute_migration import run_migration
    result = run_migration()
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# SQL for precomputation table creation
CREATE_PRECOMPUTE_TABLES_SQL = """
-- Table 1: daily_indicators
-- Stores all technical indicators for each ticker/date
CREATE TABLE IF NOT EXISTS daily_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    indicator_date DATE NOT NULL,

    -- Price Data
    open_price DECIMAL(18, 6),
    high_price DECIMAL(18, 6),
    low_price DECIMAL(18, 6),
    close_price DECIMAL(18, 6),
    volume BIGINT,

    -- Moving Averages
    sma_20 DECIMAL(18, 6),
    sma_50 DECIMAL(18, 6),
    sma_200 DECIMAL(18, 6),

    -- Momentum
    rsi_14 DECIMAL(10, 4),
    macd DECIMAL(18, 6),
    macd_signal DECIMAL(18, 6),
    macd_histogram DECIMAL(18, 6),

    -- Volatility
    bb_upper DECIMAL(18, 6),
    bb_middle DECIMAL(18, 6),
    bb_lower DECIMAL(18, 6),
    atr_14 DECIMAL(18, 6),
    atr_percent DECIMAL(10, 4),

    -- Volume Weighted
    vwap DECIMAL(18, 6),
    volume_sma_20 BIGINT,
    volume_ratio DECIMAL(10, 4),

    -- Uncertainty
    uncertainty_score DECIMAL(10, 4),
    price_vwap_pct DECIMAL(10, 4),

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_symbol_indicator_date (symbol, indicator_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,
    INDEX idx_indicators_symbol (symbol),
    INDEX idx_indicators_date (indicator_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 2: indicator_percentiles
-- Stores percentile statistics for each ticker/date
CREATE TABLE IF NOT EXISTS indicator_percentiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    percentile_date DATE NOT NULL,
    lookback_days INT DEFAULT 365,

    -- Price Percentiles
    current_price_percentile DECIMAL(10, 4),

    -- RSI Percentiles
    rsi_percentile DECIMAL(10, 4),
    rsi_mean DECIMAL(10, 4),
    rsi_std DECIMAL(10, 4),
    rsi_freq_above_70 DECIMAL(10, 4),
    rsi_freq_below_30 DECIMAL(10, 4),

    -- MACD Percentiles
    macd_percentile DECIMAL(10, 4),
    macd_freq_positive DECIMAL(10, 4),

    -- Uncertainty Percentiles
    uncertainty_percentile DECIMAL(10, 4),
    uncertainty_freq_low DECIMAL(10, 4),
    uncertainty_freq_high DECIMAL(10, 4),

    -- ATR Percentiles
    atr_pct_percentile DECIMAL(10, 4),
    atr_freq_low DECIMAL(10, 4),
    atr_freq_high DECIMAL(10, 4),

    -- Volume Percentiles
    volume_ratio_percentile DECIMAL(10, 4),
    volume_freq_high DECIMAL(10, 4),
    volume_freq_low DECIMAL(10, 4),

    -- SMA Deviation Percentiles
    sma_20_dev_percentile DECIMAL(10, 4),
    sma_50_dev_percentile DECIMAL(10, 4),
    sma_200_dev_percentile DECIMAL(10, 4),

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_symbol_percentile_date (symbol, percentile_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,
    INDEX idx_percentiles_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 3: peer_correlations
-- Stores correlation matrix between tickers
CREATE TABLE IF NOT EXISTS peer_correlations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    peer_symbol VARCHAR(20) NOT NULL,
    correlation_90d DECIMAL(10, 6),
    correlation_30d DECIMAL(10, 6),
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_symbol_peer (symbol, peer_symbol),
    INDEX idx_corr_symbol (symbol),
    INDEX idx_corr_peer (peer_symbol),
    INDEX idx_corr_value (correlation_90d DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 4: comparative_features
-- Stores pre-computed features for comparative analysis
CREATE TABLE IF NOT EXISTS comparative_features (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_date DATE NOT NULL,

    -- Returns
    daily_return DECIMAL(10, 6),
    weekly_return DECIMAL(10, 6),
    monthly_return DECIMAL(10, 6),
    ytd_return DECIMAL(10, 6),

    -- Volatility
    volatility_30d DECIMAL(10, 6),
    volatility_90d DECIMAL(10, 6),

    -- Risk Metrics
    sharpe_ratio_30d DECIMAL(10, 6),
    sharpe_ratio_90d DECIMAL(10, 6),
    max_drawdown_30d DECIMAL(10, 6),
    max_drawdown_90d DECIMAL(10, 6),

    -- Relative Strength
    rs_vs_set DECIMAL(10, 6),

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_symbol_feature_date (symbol, feature_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,
    INDEX idx_features_symbol (symbol),
    INDEX idx_features_date (feature_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table 5: precomputed_reports
-- Stores full LLM-generated reports for instant retrieval
CREATE TABLE IF NOT EXISTS precomputed_reports (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,

    -- Report Content
    report_text MEDIUMTEXT,
    report_json JSON,

    -- Generation Metadata
    strategy ENUM('single-stage', 'multi-stage') DEFAULT 'multi-stage',
    model_used VARCHAR(50),
    generation_time_ms INT,
    token_count INT,
    cost_usd DECIMAL(10, 6),

    -- Mini Reports (for multi-stage)
    mini_reports JSON,

    -- Scoring
    faithfulness_score DECIMAL(5, 2),
    completeness_score DECIMAL(5, 2),
    reasoning_score DECIMAL(5, 2),

    -- Chart
    chart_base64 MEDIUMTEXT,

    -- Status
    status ENUM('pending', 'completed', 'failed', 'stale') DEFAULT 'pending',
    error_message TEXT,

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    UNIQUE KEY uk_symbol_report_date (symbol, report_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,
    INDEX idx_reports_symbol (symbol),
    INDEX idx_reports_status (status),
    INDEX idx_reports_date (report_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def get_aurora_client():
    """Get Aurora client (import here to avoid circular imports)."""
    from src.data.aurora.client import get_aurora_client as _get_aurora_client
    return _get_aurora_client()


def run_migration() -> Dict[str, Any]:
    """Run the precomputation tables migration.

    Returns:
        Dict with status and created tables
    """
    client = get_aurora_client()

    # Split into individual statements
    statements = [s.strip() for s in CREATE_PRECOMPUTE_TABLES_SQL.split(';') if s.strip()]

    results = []
    tables_created = []

    for stmt in statements:
        # Remove leading comments and whitespace
        lines = stmt.strip().split('\n')
        clean_lines = [l for l in lines if not l.strip().startswith('--')]
        clean_stmt = '\n'.join(clean_lines).strip()

        if not clean_stmt:
            continue

        try:
            client.execute(clean_stmt + ';', commit=True)

            # Extract table name from CREATE TABLE statement
            if 'CREATE TABLE' in clean_stmt.upper():
                # Parse table name
                parts = clean_stmt.split()
                for i, part in enumerate(parts):
                    if part.upper() == 'TABLE' and i + 2 < len(parts):
                        table_name = parts[i + 2].strip('(').replace('IF', '').replace('NOT', '').replace('EXISTS', '').strip()
                        if table_name and table_name not in tables_created:
                            tables_created.append(table_name)
                        break

            results.append({'statement': clean_stmt[:60] + '...', 'status': 'success'})
            logger.info(f"Executed: {clean_stmt[:60]}...")
        except Exception as e:
            results.append({'statement': clean_stmt[:60] + '...', 'status': 'error', 'error': str(e)})
            logger.error(f"Failed to execute: {clean_stmt[:60]}... Error: {e}")

    return {
        'status': 'completed',
        'tables_created': tables_created,
        'results': results
    }


def lambda_handler(event, context):
    """Lambda entry point for precomputation migration.

    Event params:
        action: 'migrate' (default)
    """
    from datetime import datetime
    import time

    start_time = time.time()

    try:
        result = run_migration()
        duration = time.time() - start_time

        return {
            'statusCode': 200,
            'body': {
                'message': 'Precomputation migration completed',
                'duration_seconds': round(duration, 3),
                **result
            }
        }
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'message': 'Migration failed',
                'error': str(e)
            }
        }


if __name__ == '__main__':
    # For local testing with Doppler
    result = run_migration()
    print(json.dumps(result, indent=2, default=str))
