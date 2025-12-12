-- ============================================================================
-- Migration: 001_create_ticker_master.sql
-- Type: CREATE
-- Purpose: Create ticker_master table (root of ticker hierarchy)
-- Created: 2025-12-12
-- ============================================================================
--
-- PRE-CONDITION:
-- - None (root table, no dependencies)
--
-- POST-CONDITION:
-- - ticker_master table exists for company-level data
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
-- WHERE TABLE_NAME='ticker_master';
-- -- Expected: 1
--
-- IDEMPOTENCY: Uses CREATE TABLE IF NOT EXISTS
-- SAFETY: No DROP statements
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_master (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Company info
    company_name VARCHAR(255),
    exchange VARCHAR(100),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_ticker_master_company (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
