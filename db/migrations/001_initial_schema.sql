-- Initial Schema for Ticker Data Storage
-- Database: ticker_data (Aurora MySQL Serverless v2)
--
-- Tables:
--   1. ticker_info: Company metadata and mappings
--   2. daily_prices: Historical OHLCV data from Yahoo Finance
--   3. ticker_cache_metadata: Cache management for S3 sync
--
-- Design Principles:
--   - Partitioned daily_prices by year for efficient queries
--   - Indexes optimized for common query patterns
--   - UTF8MB4 for Thai language support
--
-- Migration: 001_initial_schema.sql
-- Created: 2025-12-01

-- ============================================================================
-- Table: ticker_info
-- Description: Company metadata and ticker mappings
-- Source: data/tickers.csv + yfinance info API
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_info (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Primary identifier (e.g., "NVDA", "DBS.SI", "0700.HK")
    symbol VARCHAR(20) NOT NULL UNIQUE,

    -- Display name (from tickers.csv or yfinance)
    display_name VARCHAR(100) NOT NULL,

    -- Full company name (from yfinance)
    company_name VARCHAR(255),

    -- Market/Exchange info
    exchange VARCHAR(50),            -- e.g., "NMS", "SGX", "HKEX"
    market VARCHAR(50),              -- e.g., "us_market", "sg_market"
    currency VARCHAR(10),            -- e.g., "USD", "SGD", "HKD"

    -- Classification (from yfinance)
    sector VARCHAR(100),             -- e.g., "Technology"
    industry VARCHAR(100),           -- e.g., "Semiconductors"

    -- Additional metadata
    quote_type VARCHAR(50),          -- e.g., "EQUITY", "ETF"
    is_active BOOLEAN DEFAULT TRUE,  -- For soft delete

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_fetched_at TIMESTAMP NULL,  -- Last time yfinance data was fetched

    -- Indexes for common queries
    INDEX idx_ticker_info_market (market),
    INDEX idx_ticker_info_sector (sector),
    INDEX idx_ticker_info_exchange (exchange),
    INDEX idx_ticker_info_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Table: daily_prices
-- Description: Historical OHLCV data from Yahoo Finance
-- Source: yfinance.Ticker.history()
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Foreign key to ticker_info (denormalized symbol for query efficiency)
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Date of the price data
    price_date DATE NOT NULL,

    -- OHLCV data
    open DECIMAL(18, 6),
    high DECIMAL(18, 6),
    low DECIMAL(18, 6),
    close DECIMAL(18, 6),
    adj_close DECIMAL(18, 6),        -- Adjusted close (for splits/dividends)
    volume BIGINT,

    -- Calculated fields (optional, can be computed)
    daily_return DECIMAL(10, 6),     -- (close - prev_close) / prev_close

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one row per ticker per day
    UNIQUE KEY uk_symbol_date (symbol, price_date),

    -- Foreign key
    FOREIGN KEY (ticker_id) REFERENCES ticker_info(id) ON DELETE CASCADE,

    -- Indexes for common queries
    INDEX idx_daily_prices_symbol (symbol),
    INDEX idx_daily_prices_date (price_date),
    INDEX idx_daily_prices_symbol_date (symbol, price_date DESC),
    INDEX idx_daily_prices_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
PARTITION BY RANGE (YEAR(price_date)) (
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);


-- ============================================================================
-- Table: ticker_cache_metadata
-- Description: Track cache status for S3/Aurora sync
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_cache_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,

    -- S3 cache info
    s3_key VARCHAR(500),             -- Full S3 key path
    s3_etag VARCHAR(100),            -- S3 object ETag for change detection

    -- Cache status
    status ENUM('pending', 'cached', 'expired', 'error') DEFAULT 'pending',
    error_message TEXT,

    -- Row counts for validation
    rows_in_s3 INT DEFAULT 0,
    rows_in_aurora INT DEFAULT 0,

    -- Timestamps
    cached_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint
    UNIQUE KEY uk_symbol_cache_date (symbol, cache_date),

    -- Indexes
    INDEX idx_cache_status (status),
    INDEX idx_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Views for common queries
-- ============================================================================

-- Latest prices for all tickers
CREATE OR REPLACE VIEW v_latest_prices AS
SELECT
    ti.symbol,
    ti.display_name,
    ti.company_name,
    ti.sector,
    ti.industry,
    dp.price_date,
    dp.open,
    dp.high,
    dp.low,
    dp.close,
    dp.adj_close,
    dp.volume,
    dp.daily_return
FROM ticker_info ti
LEFT JOIN daily_prices dp ON ti.symbol = dp.symbol
WHERE dp.price_date = (
    SELECT MAX(price_date)
    FROM daily_prices
    WHERE symbol = ti.symbol
)
AND ti.is_active = TRUE;


-- Price summary for the last 30 days
CREATE OR REPLACE VIEW v_price_summary_30d AS
SELECT
    symbol,
    MIN(low) as min_low_30d,
    MAX(high) as max_high_30d,
    AVG(close) as avg_close_30d,
    SUM(volume) as total_volume_30d,
    COUNT(*) as trading_days,
    MAX(price_date) as latest_date
FROM daily_prices
WHERE price_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY symbol;


-- ============================================================================
-- Stored Procedures
-- ============================================================================

DELIMITER //

-- Procedure to upsert daily price data (for batch imports)
CREATE PROCEDURE upsert_daily_price(
    IN p_symbol VARCHAR(20),
    IN p_price_date DATE,
    IN p_open DECIMAL(18, 6),
    IN p_high DECIMAL(18, 6),
    IN p_low DECIMAL(18, 6),
    IN p_close DECIMAL(18, 6),
    IN p_adj_close DECIMAL(18, 6),
    IN p_volume BIGINT
)
BEGIN
    DECLARE v_ticker_id INT;
    DECLARE v_prev_close DECIMAL(18, 6);
    DECLARE v_daily_return DECIMAL(10, 6);

    -- Get ticker_id
    SELECT id INTO v_ticker_id FROM ticker_info WHERE symbol = p_symbol;

    -- Get previous close for daily return calculation
    SELECT close INTO v_prev_close
    FROM daily_prices
    WHERE symbol = p_symbol
    AND price_date < p_price_date
    ORDER BY price_date DESC
    LIMIT 1;

    -- Calculate daily return
    IF v_prev_close IS NOT NULL AND v_prev_close != 0 THEN
        SET v_daily_return = (p_close - v_prev_close) / v_prev_close;
    ELSE
        SET v_daily_return = NULL;
    END IF;

    -- Upsert the price data
    INSERT INTO daily_prices (
        ticker_id, symbol, price_date,
        open, high, low, close, adj_close, volume,
        daily_return, fetched_at
    )
    VALUES (
        v_ticker_id, p_symbol, p_price_date,
        p_open, p_high, p_low, p_close, p_adj_close, p_volume,
        v_daily_return, CURRENT_TIMESTAMP
    )
    ON DUPLICATE KEY UPDATE
        open = VALUES(open),
        high = VALUES(high),
        low = VALUES(low),
        close = VALUES(close),
        adj_close = VALUES(adj_close),
        volume = VALUES(volume),
        daily_return = VALUES(daily_return),
        fetched_at = CURRENT_TIMESTAMP;
END //

DELIMITER ;


-- ============================================================================
-- Initial Data: Populate ticker_info from tickers.csv
-- This will be done via Python script after table creation
-- ============================================================================

-- Sample insert for reference:
-- INSERT INTO ticker_info (symbol, display_name, market) VALUES
-- ('NVDA', 'NVIDIA', 'us_market'),
-- ('DBS.SI', 'DBS Group', 'sg_market'),
-- ('0700.HK', 'Tencent', 'hk_market');
