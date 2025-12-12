-- Migration 004: Create daily_indicators table
-- Database: ticker_data (Aurora MySQL Serverless v2)
--
-- Purpose: Store computed technical indicators for each ticker-date
-- Source: src/data/aurora/precompute_service.py::store_daily_indicators()
--
-- Created: 2025-12-12 (TDD Migration - Schema validation detected missing table)

CREATE TABLE IF NOT EXISTS daily_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker identification
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    indicator_date DATE NOT NULL,

    -- Price data (OHLCV)
    open_price DECIMAL(18, 6),
    high_price DECIMAL(18, 6),
    low_price DECIMAL(18, 6),
    close_price DECIMAL(18, 6),
    volume BIGINT,

    -- Simple Moving Averages
    sma_20 DECIMAL(18, 6),
    sma_50 DECIMAL(18, 6),
    sma_200 DECIMAL(18, 6),

    -- RSI (Relative Strength Index)
    rsi_14 DECIMAL(10, 4),

    -- MACD (Moving Average Convergence Divergence)
    macd DECIMAL(18, 6),
    macd_signal DECIMAL(18, 6),
    macd_histogram DECIMAL(18, 6),

    -- Bollinger Bands
    bb_upper DECIMAL(18, 6),
    bb_middle DECIMAL(18, 6),
    bb_lower DECIMAL(18, 6),

    -- ATR (Average True Range)
    atr_14 DECIMAL(18, 6),
    atr_percent DECIMAL(10, 4),

    -- Volume indicators
    vwap DECIMAL(18, 6),
    volume_sma_20 BIGINT,
    volume_ratio DECIMAL(10, 4),

    -- Custom indicators
    uncertainty_score DECIMAL(10, 4),
    price_vwap_pct DECIMAL(10, 4),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: one row per ticker per date
    UNIQUE KEY uk_symbol_date (symbol, indicator_date),

    -- Indexes for common queries
    INDEX idx_indicators_date (indicator_date),
    INDEX idx_indicators_ticker (ticker_id),
    INDEX idx_indicators_updated (updated_at),

    -- Foreign key
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Technical indicators computed daily for each ticker';
