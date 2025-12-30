-- Migration 016: Add semantic comments to database schema
-- Purpose: Prevent semantic misinterpretation of column meanings
-- Issue: Bug hunt 2025-12-29 revealed date field confusion (trading date vs fetch date)
-- Solution: Use MySQL COMMENT syntax to document column semantics inline
-- Impact: Zero (comments are metadata only, no data/query changes)

-- ============================================================================
-- Table 1: ticker_data (HIGH PRIORITY - date confusion)
-- ============================================================================

ALTER TABLE ticker_data
MODIFY COLUMN date DATE NOT NULL
COMMENT 'Trading date for stock market data (NOT fetch date). Represents the date when market closed, not when data was retrieved. Data for date D is fetched at 5:00 AM Bangkok on date D+1.';

ALTER TABLE ticker_data
MODIFY COLUMN fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
COMMENT 'UTC timestamp when this data was fetched from Yahoo Finance API. Compare with date field to understand data age.';

ALTER TABLE ticker_data
MODIFY COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
COMMENT 'Database record creation timestamp. When this row was first inserted into ticker_data table.';

ALTER TABLE ticker_data
MODIFY COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
COMMENT 'Database record last modification timestamp. Auto-updated on any UPDATE to this row.';

ALTER TABLE ticker_data
MODIFY COLUMN history_start_date DATE
COMMENT 'Earliest date in price_history JSON array. Used for data quality validation.';

ALTER TABLE ticker_data
MODIFY COLUMN history_end_date DATE
COMMENT 'Latest date in price_history JSON array. Should match date field for complete data.';

ALTER TABLE ticker_data
MODIFY COLUMN expires_at TIMESTAMP
COMMENT 'Cache expiration timestamp. When this data should be re-fetched from Yahoo Finance.';

ALTER TABLE ticker_data
MODIFY COLUMN price_history JSON NOT NULL
COMMENT 'Array of OHLCV data for 365 days. Each element: {date, open, high, low, close, volume}. Sorted by date ASC.';

ALTER TABLE ticker_data
MODIFY COLUMN company_info JSON
COMMENT 'Company metadata from Yahoo Finance (sector, industry, marketCap, etc.). Stored as JSON object.';

ALTER TABLE ticker_data
MODIFY COLUMN source VARCHAR(50) DEFAULT 'yfinance'
COMMENT 'Data source identifier. Currently only "yfinance" supported. Future: "alpha_vantage", "polygon", etc.';

-- ============================================================================
-- Table 2: fund_data (trading date semantic alignment)
-- ============================================================================

ALTER TABLE fund_data
MODIFY COLUMN d_trade DATE NOT NULL
COMMENT 'Trading date for fundamental metrics. Matches ticker_data.date semantic (trading date, NOT fetch date).';

ALTER TABLE fund_data
MODIFY COLUMN synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
COMMENT 'Database record last sync timestamp. When this row was last synced from S3 CSV source.';

ALTER TABLE fund_data
MODIFY COLUMN s3_source_key VARCHAR(500)
COMMENT 'S3 key of source CSV file. Data lineage tracking: which file this record came from.';

ALTER TABLE fund_data
MODIFY COLUMN value_numeric DECIMAL(20,6)
COMMENT 'Numeric value for this metric (e.g., 15.75 for P/E ratio). NULL if value_text is set.';

ALTER TABLE fund_data
MODIFY COLUMN value_text TEXT
COMMENT 'Text value for this metric (e.g., "BUY" for recommendation). NULL if value_numeric is set.';

ALTER TABLE fund_data
MODIFY COLUMN col_code VARCHAR(100)
COMMENT 'Metric code identifier (e.g., "FY1_PE", "ROE", "TARGET_PRC"). See fund_data_parser.py for full list.';

-- ============================================================================
-- Table 3: ticker_master (ticker metadata)
-- ============================================================================

ALTER TABLE ticker_master
MODIFY COLUMN is_active TINYINT(1) DEFAULT 1
COMMENT 'Whether this ticker is actively tracked. Inactive tickers excluded from daily ETL runs.';

ALTER TABLE ticker_master
MODIFY COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
COMMENT 'When this ticker was added to ticker_master table.';

ALTER TABLE ticker_master
MODIFY COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
COMMENT 'When this ticker metadata was last updated.';

-- ============================================================================
-- Verification Query (run after migration)
-- ============================================================================

-- Uncomment to verify comments were added:
-- SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND DATA_TYPE IN ('date', 'timestamp', 'datetime')
--   AND TABLE_NAME IN ('ticker_data', 'fund_data', 'ticker_master')
-- ORDER BY TABLE_NAME, ORDINAL_POSITION;
