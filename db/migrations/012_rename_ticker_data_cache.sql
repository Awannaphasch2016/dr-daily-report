-- Migration 012: Rename ticker_data_cache to ticker_data
-- Purpose: Fix terminology - Aurora is primary data store, not a "cache"
-- Date: 2024-12-21

-- Rename table from ticker_data_cache to ticker_data
-- This reflects the architectural reality: Aurora is the ground truth data source,
-- not a cache layer. Data is pre-populated nightly by scheduler.
ALTER TABLE ticker_data_cache RENAME TO ticker_data;

-- Verify rename succeeded
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME,
    UPDATE_TIME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ticker_data'
LIMIT 1;
