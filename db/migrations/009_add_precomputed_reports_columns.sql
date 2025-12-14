-- Migration: Add missing columns to precomputed_reports table
-- Date: 2025-12-14
-- Reason: Fix MySQL Error 1054 "Unknown column 'generation_time_ms' in 'field list'"
--
-- Root Cause:
--   Code in src/data/aurora/precompute_service.py (_store_completed_report)
--   tries to INSERT into columns that don't exist in Aurora table:
--   - generation_time_ms (for metrics)
--   - mini_reports (for multi-stage strategy details)
--   - chart_base64 (for cached chart images)
--
-- Impact: Without these columns, all Aurora cache writes fail silently
--         (caught in try-catch, job still marked "completed")
--
-- Reconciliation Pattern: Uses ADD COLUMN IF NOT EXISTS for idempotency

USE ticker_data;

-- Add generation_time_ms column (metrics)
ALTER TABLE precomputed_reports
ADD COLUMN IF NOT EXISTS generation_time_ms INT UNSIGNED DEFAULT 0
COMMENT 'Report generation time in milliseconds';

-- Add mini_reports column (multi-stage strategy details)
ALTER TABLE precomputed_reports
ADD COLUMN IF NOT EXISTS mini_reports JSON
COMMENT 'Breakdown reports for multi-stage strategy';

-- Add chart_base64 column (cached chart images)
ALTER TABLE precomputed_reports
ADD COLUMN IF NOT EXISTS chart_base64 LONGTEXT
COMMENT 'Base64-encoded chart image for cached reports';

-- Verify columns were added
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_NAME = 'precomputed_reports'
  AND COLUMN_NAME IN ('generation_time_ms', 'mini_reports', 'chart_base64')
ORDER BY ORDINAL_POSITION;
