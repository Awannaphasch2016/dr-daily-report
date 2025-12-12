-- Migration: Add computed_at and expires_at columns to precomputed_reports
-- Date: 2025-12-12
-- Reason: Code expects these columns but Aurora has created_at/updated_at instead
--
-- Context: Comprehensive schema validation tests detected schema mismatch
--          Code in _store_completed_report() expects computed_at, expires_at
--          Aurora has auto-generated created_at, updated_at timestamps
--
-- This migration adds the application-managed timestamp columns

ALTER TABLE precomputed_reports
  ADD COLUMN computed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When report computation completed',
  ADD COLUMN expires_at DATETIME DEFAULT NULL COMMENT 'When cached report expires (TTL)';

-- Verify columns were added
DESCRIBE precomputed_reports;
