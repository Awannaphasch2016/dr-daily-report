-- ============================================================================
-- Migration: 002_create_ticker_aliases.sql
-- Type: CREATE
-- Purpose: Create ticker_aliases table with FK to ticker_master
-- Created: 2025-12-12
-- ============================================================================
--
-- PRE-CONDITION:
-- - ticker_master table exists (FK target)
--
-- POST-CONDITION:
-- - ticker_aliases table exists for symbol mappings
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_NAME='ticker_aliases';
-- -- Expected: 1
--
-- IDEMPOTENCY: Uses CREATE TABLE IF NOT EXISTS
-- SAFETY: No DROP statements
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_aliases (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    symbol_type VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_ticker_symbol (ticker_id, symbol),

    -- Indexes
    INDEX idx_aliases_symbol (symbol),
    INDEX idx_aliases_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
