-- ============================================================================
-- Migration: 004_create_daily_prices.sql
-- Type: CREATE
-- Purpose: Create daily_prices table with historical OHLCV data
-- Created: 2025-12-12
-- ============================================================================
--
-- PRE-CONDITION:
-- - ticker_info table exists with id column (FK target)
--
-- POST-CONDITION:
-- - daily_prices table exists with historical OHLCV data
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_NAME='daily_prices';
-- -- Expected: 1
--
-- IDEMPOTENCY: Uses CREATE TABLE IF NOT EXISTS
-- SAFETY: No DROP statements
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,

    -- OHLCV data
    open DECIMAL(18, 6),
    high DECIMAL(18, 6),
    low DECIMAL(18, 6),
    close DECIMAL(18, 6),
    adj_close DECIMAL(18, 6),
    volume BIGINT,

    -- Calculated fields
    daily_return DECIMAL(10, 6),

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, price_date),

    -- Indexes
    INDEX idx_daily_prices_symbol (symbol),
    INDEX idx_daily_prices_date (price_date),
    INDEX idx_daily_prices_symbol_date (symbol, price_date DESC),
    INDEX idx_daily_prices_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
