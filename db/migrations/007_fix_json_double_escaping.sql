-- Migration: Fix JSON Double-Escaping Bug
-- Date: 2025-12-13
-- Issue: LONGTEXT columns with json.dumps() cause double-escaping when MySQL connector
--        escapes the %s parameter again. This breaks JSON parsing for reports containing
--        quoted text (e.g., Thai "ถือ" in narrative).
-- Fix: Change to JSON column type and pass dict directly (no json.dumps)

-- Aurora MySQL 5.7+ supports native JSON type
-- Benefits:
--   1. No double-escaping (connector handles dict → JSON internally)
--   2. JSON validation on insert
--   3. Queryable with JSON functions (JSON_EXTRACT, etc.)
--   4. Binary storage (more efficient)

USE ticker_data;

-- Change report_json from LONGTEXT to JSON
ALTER TABLE precomputed_reports
  MODIFY COLUMN report_json JSON;

-- Change mini_reports from LONGTEXT to JSON
ALTER TABLE precomputed_reports
  MODIFY COLUMN mini_reports JSON;

-- Verify changes
DESCRIBE precomputed_reports;
