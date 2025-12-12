-- Add missing columns to precomputed_reports table
-- These are application-managed timestamps, different from MySQL's auto-generated created_at/updated_at

-- Check current schema first
DESCRIBE precomputed_reports;

-- Add the missing columns
ALTER TABLE precomputed_reports
  ADD COLUMN IF NOT EXISTS computed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When report computation completed',
  ADD COLUMN IF NOT EXISTS expires_at DATETIME DEFAULT NULL COMMENT 'When cached report expires (TTL)';

-- Verify columns were added
DESCRIBE precomputed_reports;

-- Show sample to verify
SELECT
  symbol,
  report_date,
  status,
  created_at,
  updated_at,
  computed_at,
  expires_at
FROM precomputed_reports
LIMIT 5;
