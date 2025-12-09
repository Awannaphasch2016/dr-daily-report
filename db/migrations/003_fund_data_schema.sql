-- Fund Data Sync Schema Migration
-- Purpose: Store fund data synced from on-premises SQL Server via S3
-- Data Source: S3 raw/sql_server/fund_data/*.csv → Lambda → Aurora
--
-- Design Principles:
-- 1. Idempotency: Composite unique key prevents duplicates on reprocessing
-- 2. Data Lineage: s3_source_key tracks exact S3 object origin
-- 3. Schema Flexibility: value_numeric + value_text support varied data types
-- 4. Defensive Constraints: NOT NULL on critical fields, explicit defaults
--
-- Usage:
--   ENV=dev doppler run -- mysql -h <AURORA_HOST> -u admin -p ticker_data < db/migrations/003_fund_data_schema.sql

-- ============================================================================
-- Table: fund_data
-- ============================================================================

CREATE TABLE IF NOT EXISTS fund_data (
    -- Primary Key
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    -- Composite Business Key (matches SQL Server source structure)
    -- Unique constraint ensures idempotency on (d_trade, stock, ticker, col_code)
    d_trade DATE NOT NULL COMMENT 'Trading date from source system',
    stock VARCHAR(50) NOT NULL COMMENT 'Stock identifier from source system',
    ticker VARCHAR(50) NOT NULL COMMENT 'Ticker symbol (DR format or Yahoo format)',
    col_code VARCHAR(100) NOT NULL COMMENT 'Column code identifying data type',

    -- Data Values (flexible storage for numeric or text)
    -- Rationale: Source columns vary - some numeric (price, volume), some text (status, notes)
    value_numeric DECIMAL(18,6) DEFAULT NULL COMMENT 'Numeric value (prices, volumes, ratios)',
    value_text TEXT DEFAULT NULL COMMENT 'Text value (codes, statuses, descriptions)',

    -- Metadata
    source VARCHAR(50) NOT NULL DEFAULT 'sql_server' COMMENT 'Data source system',
    s3_source_key VARCHAR(500) NOT NULL COMMENT 'S3 object key for data lineage (e.g. raw/sql_server/fund_data/2025-12-09/fund_data_20251209_083829.csv)',

    -- Timestamps
    synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When synced to Aurora from S3',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last modification time',

    -- Primary Key
    PRIMARY KEY (id),

    -- Unique Constraint (Idempotency)
    -- ON DUPLICATE KEY UPDATE will use this to detect existing rows
    UNIQUE KEY uk_fund_data_composite (d_trade, stock, ticker, col_code),

    -- Query Performance Indexes
    INDEX idx_d_trade (d_trade DESC) COMMENT 'Time-series queries (recent first)',
    INDEX idx_ticker (ticker) COMMENT 'Ticker lookup queries',
    INDEX idx_stock (stock) COMMENT 'Stock identifier queries',
    INDEX idx_col_code (col_code) COMMENT 'Column code filtering',
    INDEX idx_s3_source (s3_source_key(255)) COMMENT 'Data lineage tracking (prefix limited to 255 for InnoDB)',
    INDEX idx_synced_at (synced_at DESC) COMMENT 'Audit trail queries'

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Fund data synced from on-premises SQL Server via S3 event-driven pipeline';

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify table created
-- SELECT TABLE_NAME, ENGINE, TABLE_ROWS, CREATE_TIME
-- FROM information_schema.TABLES
-- WHERE TABLE_SCHEMA = 'ticker_data' AND TABLE_NAME = 'fund_data';

-- Verify indexes
-- SHOW INDEX FROM fund_data;

-- Sample query pattern (latest data for a ticker)
-- SELECT d_trade, stock, ticker, col_code, value_numeric, value_text
-- FROM fund_data
-- WHERE ticker = 'DBS19' AND d_trade >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
-- ORDER BY d_trade DESC, col_code;

-- ============================================================================
-- Migration Notes
-- ============================================================================

-- Migration ID: 003
-- Previous Migration: 002 (ticker data cache tables)
-- Next Migration: TBD (depends on Phase 2 requirements)
--
-- Rollback:
--   DROP TABLE IF EXISTS fund_data;
--
-- Data Validation After Migration:
--   1. Row count matches CSV import: SELECT COUNT(*) FROM fund_data;
--   2. No duplicate composites: SELECT COUNT(*) vs SELECT COUNT(DISTINCT d_trade, stock, ticker, col_code);
--   3. S3 lineage populated: SELECT COUNT(*) FROM fund_data WHERE s3_source_key IS NULL OR s3_source_key = '';
--   4. Value fields populated: SELECT COUNT(*) FROM fund_data WHERE value_numeric IS NULL AND value_text IS NULL;
