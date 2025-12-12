-- Migration 005: Create indicator_percentiles table
-- Database: ticker_data (Aurora MySQL Serverless v2)
--
-- Purpose: Store percentile statistics for technical indicators
-- Source: src/data/aurora/precompute_service.py::store_indicator_percentiles()
--
-- Created: 2025-12-12 (TDD Migration - Schema validation detected missing table)

CREATE TABLE IF NOT EXISTS indicator_percentiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker identification
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    percentile_date DATE NOT NULL,
    lookback_days INT NOT NULL DEFAULT 365,

    -- Price percentiles
    current_price_percentile DECIMAL(5, 2),

    -- RSI percentiles and frequency stats
    rsi_percentile DECIMAL(5, 2),
    rsi_mean DECIMAL(10, 4),
    rsi_std DECIMAL(10, 4),
    rsi_freq_above_70 DECIMAL(5, 2),
    rsi_freq_below_30 DECIMAL(5, 2),

    -- MACD percentiles and frequency stats
    macd_percentile DECIMAL(5, 2),
    macd_freq_positive DECIMAL(5, 2),

    -- Uncertainty percentiles and frequency stats
    uncertainty_percentile DECIMAL(5, 2),
    uncertainty_freq_low DECIMAL(5, 2),
    uncertainty_freq_high DECIMAL(5, 2),

    -- ATR percentiles and frequency stats
    atr_pct_percentile DECIMAL(5, 2),
    atr_freq_low DECIMAL(5, 2),
    atr_freq_high DECIMAL(5, 2),

    -- Volume percentiles and frequency stats
    volume_ratio_percentile DECIMAL(5, 2),
    volume_freq_high DECIMAL(5, 2),
    volume_freq_low DECIMAL(5, 2),

    -- SMA deviation percentiles
    sma_20_dev_percentile DECIMAL(5, 2),
    sma_50_dev_percentile DECIMAL(5, 2),
    sma_200_dev_percentile DECIMAL(5, 2),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: one row per ticker per date per lookback period
    UNIQUE KEY uk_symbol_date_lookback (symbol, percentile_date, lookback_days),

    -- Indexes for common queries
    INDEX idx_percentiles_date (percentile_date),
    INDEX idx_percentiles_ticker (ticker_id),
    INDEX idx_percentiles_updated (updated_at),

    -- Foreign key
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Percentile statistics for technical indicators';
