-- Master Migration Script
-- Database: ticker_data (Aurora MySQL Serverless v2)
-- Purpose: Apply ALL migrations to bring Aurora schema up to date with code expectations
--
-- Execution order: 001 → 003 → 004 → 005 → 006
-- (002 is skipped - it contains ALTER TABLE for columns that don't match current schema)
--
-- Created: 2025-12-12
-- Context: TDD system detected missing tables. This script fixes the schema.

-- ============================================================================
-- Migration 001: Initial Schema (ticker_info, daily_prices)
-- ============================================================================

-- Note: Run the full migration file instead of embedding it here
-- SOURCE db/migrations/001_initial_schema.sql;

-- ============================================================================
-- Migration 003: Add computed_at, expires_at, error_message to precomputed_reports
-- ============================================================================

ALTER TABLE precomputed_reports
  ADD COLUMN IF NOT EXISTS computed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When report computation completed',
  ADD COLUMN IF NOT EXISTS expires_at DATETIME DEFAULT NULL COMMENT 'When cached report expires (TTL)',
  ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL COMMENT 'Error message if status=failed';

-- ============================================================================
-- Migration 004: Create daily_indicators table
-- ============================================================================

-- Note: Run the full migration file instead of embedding it here
-- SOURCE db/migrations/004_daily_indicators_schema.sql;

-- ============================================================================
-- Migration 005: Create indicator_percentiles table
-- ============================================================================

-- Note: Run the full migration file instead of embedding it here
-- SOURCE db/migrations/005_indicator_percentiles_schema.sql;

-- ============================================================================
-- Migration 006: Create comparative_features table
-- ============================================================================

-- Note: Run the full migration file instead of embedding it here
-- SOURCE db/migrations/006_comparative_features_schema.sql;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Show all tables in database
SHOW TABLES;

-- Verify precomputed_reports has required columns
DESCRIBE precomputed_reports;

-- Verify new tables exist
SHOW CREATE TABLE daily_indicators;
SHOW CREATE TABLE indicator_percentiles;
SHOW CREATE TABLE comparative_features;

-- Count rows in each table
SELECT 'precomputed_reports' AS table_name, COUNT(*) AS row_count FROM precomputed_reports
UNION ALL
SELECT 'daily_indicators', COUNT(*) FROM daily_indicators
UNION ALL
SELECT 'indicator_percentiles', COUNT(*) FROM indicator_percentiles
UNION ALL
SELECT 'comparative_features', COUNT(*) FROM comparative_features
UNION ALL
SELECT 'ticker_info', COUNT(*) FROM ticker_info
UNION ALL
SELECT 'fund_data', COUNT(*) FROM fund_data;
