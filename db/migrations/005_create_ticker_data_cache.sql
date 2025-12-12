-- ============================================================================
-- Migration: 005_create_ticker_data_cache.sql
-- Type: CREATE
-- Purpose: Create ticker_data_cache table for fetched yfinance data
-- Created: 2025-12-12
-- ============================================================================
--
-- PRE-CONDITION:
-- - ticker_master table exists (FK target for ticker_master_id)
--
-- POST-CONDITION:
-- - ticker_data_cache table exists for caching raw yfinance responses
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_NAME='ticker_data_cache';
-- -- Expected: 1
--
-- IDEMPOTENCY: Uses CREATE TABLE IF NOT EXISTS
-- SAFETY: No DROP statements
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_data_cache (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_master_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,

    -- Cached data (JSON)
    price_history JSON NOT NULL,
    company_info JSON,
    financials_json JSON,

    -- Metadata
    history_start_date DATE,
    history_end_date DATE,
    row_count INT,
    source VARCHAR(50) DEFAULT 'yfinance',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, date),

    -- Indexes
    INDEX idx_cache_fetched (fetched_at),
    INDEX idx_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
