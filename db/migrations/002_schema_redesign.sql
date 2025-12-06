-- Schema Redesign Migration
-- Database: ticker_data (Aurora MySQL Serverless v2)
--
-- Changes:
--   1. Add PDF tracking columns to precomputed_reports
--   2. Rename report_date → date for clarity
--   3. Add report_generated_at (renamed from computed_at)
--   4. Create ticker_data_cache table (replaces S3 cache/ticker_data/)
--   5. Deprecate ticker_cache_metadata (S3 tracking no longer needed)
--
-- Migration: 002_schema_redesign.sql
-- Created: 2025-12-01

-- ============================================================================
-- Step 1: ALTER precomputed_reports - Add new columns
-- ============================================================================

-- Add new columns for date tracking and PDF storage
-- Note: We add columns first, then migrate data, then drop old columns

-- Add date column (will be populated from report_date)
ALTER TABLE precomputed_reports
ADD COLUMN date DATE AFTER symbol;

-- Add report_generated_at (will be populated from computed_at)
ALTER TABLE precomputed_reports
ADD COLUMN report_generated_at TIMESTAMP AFTER date;

-- Add PDF tracking columns
ALTER TABLE precomputed_reports
ADD COLUMN pdf_s3_key VARCHAR(255) AFTER chart_base64,
ADD COLUMN pdf_presigned_url TEXT AFTER pdf_s3_key,
ADD COLUMN pdf_url_expires_at TIMESTAMP NULL AFTER pdf_presigned_url,
ADD COLUMN pdf_generated_at TIMESTAMP NULL AFTER pdf_url_expires_at;


-- ============================================================================
-- Step 2: Migrate existing data
-- ============================================================================

-- Copy report_date values to date column
UPDATE precomputed_reports
SET date = report_date
WHERE date IS NULL AND report_date IS NOT NULL;

-- Copy computed_at values to report_generated_at column
UPDATE precomputed_reports
SET report_generated_at = COALESCE(computed_at, CURRENT_TIMESTAMP)
WHERE report_generated_at IS NULL;

-- Backfill pdf_s3_key for completed reports (matching PDF naming convention)
UPDATE precomputed_reports
SET pdf_s3_key = CONCAT('reports/', symbol, '/', DATE_FORMAT(date, '%Y-%m-%d'), '.pdf')
WHERE pdf_s3_key IS NULL
AND status = 'completed';


-- ============================================================================
-- Step 3: Update constraints and indexes
-- ============================================================================

-- Make date NOT NULL after migration
ALTER TABLE precomputed_reports
MODIFY COLUMN date DATE NOT NULL;

-- Make report_generated_at NOT NULL after migration
ALTER TABLE precomputed_reports
MODIFY COLUMN report_generated_at TIMESTAMP NOT NULL;

-- Drop old unique key and create new one
ALTER TABLE precomputed_reports
DROP INDEX uk_symbol_report_date,
ADD UNIQUE KEY uk_symbol_date (symbol, date);

-- Add index for PDF tracking queries
ALTER TABLE precomputed_reports
ADD INDEX idx_reports_pdf_expires (pdf_url_expires_at);


-- ============================================================================
-- Step 4: Drop old columns (run separately after verifying migration)
-- ============================================================================

-- NOTE: Run these AFTER verifying all data is migrated correctly
-- ALTER TABLE precomputed_reports DROP COLUMN report_date;
-- ALTER TABLE precomputed_reports DROP COLUMN computed_at;


-- ============================================================================
-- Step 5: Create ticker_data_cache table
-- Description: Full yfinance data cache (replaces S3 cache/ticker_data/)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_data_cache (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Link to ticker_master for robust lookup
    ticker_master_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Date tracking
    date DATE NOT NULL,                           -- Date of the cached data
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Full 1-year price history (JSON array, ~60KB)
    -- Schema: [{date, open, high, low, close, volume, adj_close}, ...]
    -- Contains 365 rows of daily OHLCV data
    price_history JSON NOT NULL,

    -- Company info (cached from yfinance)
    -- Schema: {name, sector, industry, market_cap, currency, exchange, etc.}
    company_info JSON,

    -- Financials snapshot (optional, for fundamental analysis)
    -- Schema: {balance_sheet: {...}, income_statement: {...}, cash_flow: {...}}
    financials_json JSON,

    -- Cache metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    expires_at TIMESTAMP NULL,                    -- TTL: next trading day 8 AM Bangkok
    history_start_date DATE,                      -- First date in price_history
    history_end_date DATE,                        -- Last date in price_history (usually yesterday)
    row_count INT,                                -- Number of rows in price_history

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: one cache entry per ticker per date
    UNIQUE KEY uk_symbol_date (symbol, date),

    -- Indexes for common queries
    INDEX idx_cache_fetched (fetched_at),
    INDEX idx_cache_expires (expires_at),
    INDEX idx_cache_ticker_master (ticker_master_id),

    -- Foreign key to ticker_master
    FOREIGN KEY (ticker_master_id) REFERENCES ticker_master(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Step 6: Create view for cache status monitoring
-- ============================================================================

CREATE OR REPLACE VIEW v_ticker_cache_status AS
SELECT
    tdc.symbol,
    tdc.date,
    tdc.fetched_at,
    tdc.expires_at,
    tdc.row_count,
    tdc.history_start_date,
    tdc.history_end_date,
    CASE
        WHEN tdc.expires_at IS NULL THEN 'no_expiry'
        WHEN tdc.expires_at < NOW() THEN 'expired'
        ELSE 'valid'
    END AS cache_status,
    pr.status AS report_status,
    pr.report_generated_at,
    pr.pdf_s3_key IS NOT NULL AS has_pdf
FROM ticker_data_cache tdc
LEFT JOIN precomputed_reports pr
    ON tdc.symbol = pr.symbol
    AND tdc.date = pr.date;


-- ============================================================================
-- Step 7: Deprecation notes for ticker_cache_metadata
-- ============================================================================

-- The ticker_cache_metadata table tracked S3 cache status.
-- With ticker_data_cache storing data directly in Aurora, this table is no longer needed.
--
-- DEPRECATION PLAN:
-- 1. Stop writing to ticker_cache_metadata (code change)
-- 2. Monitor for 1 week to ensure no reads
-- 3. Drop table: DROP TABLE ticker_cache_metadata;
--
-- DO NOT DROP YET - leave for rollback capability


-- ============================================================================
-- Migration verification queries (run after migration)
-- ============================================================================

-- Verify precomputed_reports migration:
-- SELECT COUNT(*) as total,
--        COUNT(date) as has_date,
--        COUNT(report_date) as has_report_date,
--        COUNT(report_generated_at) as has_generated_at,
--        COUNT(computed_at) as has_computed_at,
--        COUNT(pdf_s3_key) as has_pdf_key
-- FROM precomputed_reports;

-- Verify unique key works:
-- SELECT symbol, date, COUNT(*) as cnt
-- FROM precomputed_reports
-- GROUP BY symbol, date
-- HAVING cnt > 1;

-- Check ticker_data_cache table:
-- SHOW CREATE TABLE ticker_data_cache;
