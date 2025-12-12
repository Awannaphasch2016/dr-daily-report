-- Migration 006: Create comparative_features table
-- Database: ticker_data (Aurora MySQL Serverless v2)
--
-- Purpose: Store comparative return and risk metrics for each ticker
-- Source: src/data/aurora/precompute_service.py::store_comparative_features()
--
-- Created: 2025-12-12 (TDD Migration - Schema validation detected missing table)

CREATE TABLE IF NOT EXISTS comparative_features (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker identification
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_date DATE NOT NULL,

    -- Return metrics (relative performance)
    daily_return DECIMAL(10, 6),
    weekly_return DECIMAL(10, 6),
    monthly_return DECIMAL(10, 6),
    ytd_return DECIMAL(10, 6),

    -- Risk metrics (volatility)
    volatility_30d DECIMAL(10, 6),
    volatility_90d DECIMAL(10, 6),

    -- Risk-adjusted return (Sharpe ratio)
    sharpe_ratio_30d DECIMAL(10, 4),
    sharpe_ratio_90d DECIMAL(10, 4),

    -- Drawdown metrics
    max_drawdown_30d DECIMAL(10, 6),
    max_drawdown_90d DECIMAL(10, 6),

    -- Relative strength (vs peer group)
    rs_vs_set DECIMAL(10, 6),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: one row per ticker per date
    UNIQUE KEY uk_symbol_date (symbol, feature_date),

    -- Indexes for common queries
    INDEX idx_features_date (feature_date),
    INDEX idx_features_ticker (ticker_id),
    INDEX idx_features_updated (updated_at),
    INDEX idx_features_rs (rs_vs_set),

    -- Foreign key
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Comparative return and risk metrics for peer analysis';
