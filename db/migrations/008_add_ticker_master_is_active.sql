-- Migration 008: Add is_active column to ticker_master table
--
-- Purpose: Fix scheduler Aurora query failure
-- Context: ticker_resolver.py expects m.is_active but column doesn't exist
-- Error: "Unknown column 'm.is_active' in 'field list'"
--
-- This migration is idempotent and safe to run multiple times

-- Add is_active column if it doesn't exist
ALTER TABLE ticker_master
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
AFTER quote_type;

-- Add index for performance (WHERE is_active = TRUE is common filter)
ALTER TABLE ticker_master
ADD INDEX IF NOT EXISTS idx_ticker_master_active (is_active);

-- Set all existing records to active (default behavior)
UPDATE ticker_master
SET is_active = TRUE
WHERE is_active IS NULL;

-- Verification query (run manually to confirm)
-- SELECT COUNT(*) as total, SUM(is_active) as active FROM ticker_master;
