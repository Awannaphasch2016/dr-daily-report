-- Migration 038: Add cost tracking to traces + model pricing reference table
--
-- Purpose: Persist per-report LLM cost data (already calculated in-memory but not stored)
--          and track model pricing versions for backfill capability.
--
-- Background: OpenRouter credits ran out (HTTP 402) on 2026-03-18 with no proactive alert.
--             Cost data is needed to calculate dynamic alert thresholds based on actual spend.

-- 1. Model pricing reference table
-- Records input/output rates per model+version with calc_version for linking to traces.
-- Enables retroactive cost recalculation when pricing changes are discovered.
CREATE TABLE IF NOT EXISTS model_pricing (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    calc_version    VARCHAR(20)    NOT NULL COMMENT 'Calculation version linking to traces.calc_version',
    model_id        VARCHAR(100)   NOT NULL COMMENT 'OpenRouter model identifier e.g. openai/gpt-4o',
    model_version   VARCHAR(50)             COMMENT 'Model version e.g. 2024-08, 2025-03',
    input_rate_usd  DECIMAL(12,8)  NOT NULL COMMENT 'Cost per input token in USD',
    output_rate_usd DECIMAL(12,8)  NOT NULL COMMENT 'Cost per output token in USD',
    effective_from  DATE           NOT NULL COMMENT 'When this pricing became effective',
    notes           TEXT                    COMMENT 'Change reason e.g. OpenAI price cut March 2026',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_calc_model (calc_version, model_id),
    INDEX idx_model_effective (model_id, effective_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Model pricing reference for cost calculation and backfill';

-- 2. Add cost columns to traces table
-- Tokens are immutable facts. cost_usd is derived from tokens x rates at calc_version.
ALTER TABLE traces
    ADD COLUMN input_tokens   INT            AFTER trace_external_id,
    ADD COLUMN output_tokens  INT            AFTER input_tokens,
    ADD COLUMN cost_usd       DECIMAL(10,6)  AFTER output_tokens,
    ADD COLUMN calc_version   VARCHAR(20)    AFTER cost_usd;

-- Index for credit checker queries: sum recent report costs
ALTER TABLE traces
    ADD INDEX idx_traces_cost_lookup (trace_type, created_at, cost_usd);

-- 3. Seed initial pricing (OpenRouter rates as of 2025-01-01)
INSERT INTO model_pricing (calc_version, model_id, model_version, input_rate_usd, output_rate_usd, effective_from, notes)
VALUES
    ('v1', 'openai/gpt-4o',      '2024-08', 0.00000250, 0.00001000, '2025-01-01', 'Initial pricing - report writer model'),
    ('v1', 'openai/gpt-4o-mini', '2024-07', 0.00000015, 0.00000060, '2025-01-01', 'Initial pricing - judge/scoring model');
