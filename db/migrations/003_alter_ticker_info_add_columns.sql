-- ============================================================================
-- Migration: 003_alter_ticker_info_add_columns.sql
-- Type: ALTER
-- Purpose: Add 9 missing columns to ticker_info table
-- Created: 2025-12-12
-- ============================================================================
--
-- PRE-CONDITION:
-- - ticker_info table exists with basic columns (id, symbol)
--
-- POST-CONDITION:
-- - ticker_info has all 13 required columns for yfinance data
--
-- VERIFICATION:
-- SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME='ticker_info' AND COLUMN_NAME IN
--   ('company_name', 'currency', 'display_name', 'exchange', 'industry',
--    'last_fetched_at', 'market', 'quote_type', 'sector');
-- -- Expected: 9
--
-- IDEMPOTENCY: Uses ADD COLUMN IF NOT EXISTS (MySQL 8.0.12+)
-- SAFETY: No DROP statements, additive only
-- ============================================================================

ALTER TABLE ticker_info
  ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS currency VARCHAR(10),
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),
  ADD COLUMN IF NOT EXISTS exchange VARCHAR(50),
  ADD COLUMN IF NOT EXISTS industry VARCHAR(100),
  ADD COLUMN IF NOT EXISTS last_fetched_at TIMESTAMP NULL,
  ADD COLUMN IF NOT EXISTS market VARCHAR(50),
  ADD COLUMN IF NOT EXISTS quote_type VARCHAR(50),
  ADD COLUMN IF NOT EXISTS sector VARCHAR(100),
  ALGORITHM=INSTANT;
