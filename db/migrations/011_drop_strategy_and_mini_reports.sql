-- Migration: Drop obsolete multi-stage columns from precomputed_reports table
-- Date: 2025-12-21
-- Reason: Semantic Layer Architecture replaces multi-stage report generation
--
-- Context:
--   ADR-001 adopts Semantic Layer Architecture which eliminates the need for:
--   - strategy column (ENUM 'single-stage' | 'multi-stage')
--   - mini_reports column (JSON breakdown for 6 specialist reports + synthesis)
--   - raw_data_json column (raw AgentState for regeneration)
--
-- Architecture Change:
--   Old: Multi-stage (7 LLM calls) - 6 mini-reports + synthesis
--   New: Semantic Layer (1 LLM call) - Code classifies semantic states, LLM synthesizes
--
-- Impact:
--   - 86% cost reduction (~$0.50 → ~$0.07 per report)
--   - 67% latency reduction (~15s → ~5s generation time)
--   - Simpler codebase (~1,262 lines removed)
--
-- Data Loss: Historical multi-stage reports will lose strategy/mini_reports metadata.
--            This is acceptable - obsolete architecture, no regeneration use case.
--
-- References:
--   - ADR-001: docs/adr/001-adopt-semantic-layer-architecture.md
--   - Implementation: docs/SEMANTIC_LAYER_ARCHITECTURE.md

USE ticker_data;

-- Drop strategy column (multi-stage strategy metadata)
ALTER TABLE precomputed_reports
DROP COLUMN IF EXISTS strategy;

-- Drop mini_reports column (specialist report breakdown)
ALTER TABLE precomputed_reports
DROP COLUMN IF EXISTS mini_reports;

-- Drop raw_data_json column (raw AgentState for regeneration)
ALTER TABLE precomputed_reports
DROP COLUMN IF EXISTS raw_data_json;

-- Verify columns were dropped
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_NAME = 'precomputed_reports'
  AND COLUMN_NAME IN ('strategy', 'mini_reports', 'raw_data_json')
ORDER BY ORDINAL_POSITION;

-- This query should return 0 rows if migration succeeded
