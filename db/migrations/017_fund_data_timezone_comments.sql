-- ============================================================================
-- Migration 017: Add Timezone Semantic Comments to fund_data Table
-- Date: 2025-12-30
-- Purpose: Document Bangkok timezone usage in fund_data.synced_at column
--
-- Context: Bangkok timezone migration (2025-12-30)
--   - Aurora parameter group configured with time_zone = "Asia/Bangkok"
--   - Lambda TZ environment variable set to "Asia/Bangkok"
--   - This migration adds comments to document the timezone semantics
--
-- Timezone Migration Timeline:
--   Pre-2025-12-30:  synced_at stored in UTC (Aurora default)
--   Post-2025-12-30: synced_at stored in Bangkok time (Asia/Bangkok)
--   Note: Both are valid - no data migration required
-- ============================================================================

-- Add timezone comment to synced_at column
-- Note: Must use MODIFY COLUMN with full column definition to preserve existing constraints
ALTER TABLE fund_data
MODIFY COLUMN synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
COMMENT 'Database record last sync timestamp (Bangkok time after 2025-12-30, UTC before). On-premise export uses Bangkok time (UTC+7).';

-- Verify the comment was added
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'fund_data'
  AND COLUMN_NAME = 'synced_at';
