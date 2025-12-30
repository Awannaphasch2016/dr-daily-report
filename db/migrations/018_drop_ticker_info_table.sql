-- ============================================================================
-- Migration 018: Drop ticker_info Table (Unused Legacy Table)
-- Date: 2025-12-30
-- Purpose: Remove ticker_info table that was never populated or used
--
-- Context: ticker_info cleanup (2025-12-30)
--   - ticker_info table exists but has 0 rows (never populated)
--   - AURORA_ENABLED flag never set → scheduler never writes to it
--   - No production code queries ticker_info
--   - System uses ticker_master + ticker_aliases instead (46 + 115 rows)
--
-- Evidence:
--   1. ticker_info: 0 rows (empty since creation)
--   2. ticker_master: 46 rows (actually used by TickerResolver)
--   3. ticker_aliases: 115 rows (actually used by TickerResolver)
--   4. TickerService uses data/tickers.csv (not Aurora ticker_info)
--   5. Scheduler disabled: AURORA_ENABLED=NOT_SET
--
-- Why Safe to Drop:
--   - Never populated (0 rows, AURORA_ENABLED not set)
--   - Not queried by any production code
--   - TickerResolver uses ticker_master + ticker_aliases
--   - TickerService uses CSV file
--   - LINE Bot uses CSV file
--   - Telegram API uses CSV file
--
-- Migration Strategy:
--   - Drop table (idempotent - IF EXISTS)
--   - No data migration needed (table empty)
--   - Follow-up: Remove code references in separate commits
-- ============================================================================

-- Drop ticker_info table (idempotent)
DROP TABLE IF EXISTS ticker_info;

-- Verify table was dropped
SELECT
    COUNT(*) as ticker_info_exists
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ticker_info';
-- Expected: 0 (table should not exist)

-- Verify ticker_master and ticker_aliases still exist (the tables actually used)
-- Note: Table names defined in src/data/aurora/table_names.py as constants
SELECT
    TABLE_NAME,
    TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('ticker_master', 'ticker_aliases')
ORDER BY TABLE_NAME;
-- Expected:
--   ticker_aliases: 115 rows
--   ticker_master: 46 rows
--
-- After this migration, all code should use:
--   from src.data.aurora.table_names import TICKER_MASTER, TICKER_ALIASES
