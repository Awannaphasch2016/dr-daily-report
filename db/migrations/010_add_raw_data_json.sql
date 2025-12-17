-- Migration: Add raw_data_json column for report regeneration
-- Date: 2025-12-16
-- Purpose: Store original AgentState (indicators, ticker_data, percentiles, etc.)
--          to enable report regeneration without API calls

-- Add column to store original AgentState before transformation
ALTER TABLE precomputed_reports
ADD COLUMN raw_data_json JSON COMMENT 'Original AgentState (indicators, ticker_data, percentiles, etc.) for report regeneration';

-- Verify column was added
SELECT 'Migration 010: raw_data_json column added successfully' AS status;
