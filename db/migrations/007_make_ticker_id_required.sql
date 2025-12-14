-- ============================================================================
-- Migration 007: Make ticker_id required in precomputed_reports
-- ============================================================================
-- Purpose: Enforce ticker_id as NOT NULL with foreign key constraint
-- Rationale: Code always populates ticker_id before INSERT (fails fast if
--            ticker_info not found). Making it NOT NULL enforces this at
--            schema level and enables query optimization.
--
-- Changes:
-- 1. Change ticker_id to INT NOT NULL (matches ticker_master.id type)
-- 2. Add foreign key constraint to ticker_master(id)
--
-- Reconciliation Strategy: Idempotent ALTERs that only apply if needed
-- Type Match: ticker_master.id is INT, so ticker_id must also be INT
-- ============================================================================

-- Step 1: Modify column type and nullability
-- Note: This will fail if any NULL values exist (defensive - ensures data quality)
-- Type: INT (not BIGINT) to match ticker_master.id
ALTER TABLE precomputed_reports
    MODIFY COLUMN ticker_id INT NOT NULL;

-- Step 2: Add foreign key constraint (if not exists)
-- MySQL doesn't have IF NOT EXISTS for foreign keys, so we wrap in a procedure
DELIMITER //
CREATE PROCEDURE add_ticker_id_fk()
BEGIN
    -- Check if FK already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'precomputed_reports'
        AND CONSTRAINT_NAME = 'fk_precomputed_reports_ticker_id'
    ) THEN
        ALTER TABLE precomputed_reports
            ADD CONSTRAINT fk_precomputed_reports_ticker_id
            FOREIGN KEY (ticker_id) REFERENCES ticker_master(id);
    END IF;
END //
DELIMITER ;

CALL add_ticker_id_fk();
DROP PROCEDURE add_ticker_id_fk;
