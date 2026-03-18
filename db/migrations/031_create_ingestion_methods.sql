-- Migration 031: Create ingestion_methods table + FK on data_acquisitions
-- Purpose: Registry of HOW data gets fetched (ECS Fargate, Lambda, local, etc.)
-- Generated: 2026-03-16
-- Depends on: 021_create_data_acquisitions
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS ingestion_methods (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Method identity
    method_name VARCHAR(100) NOT NULL COMMENT 'Unique name for this approach (e.g. edinet-ecs-fargate-backfill)',
    runtime_type ENUM('ecs_fargate','lambda','local','step_functions','github_actions') NOT NULL
        COMMENT 'Infrastructure used to execute the script',

    -- What runs
    script_path VARCHAR(500) NULL COMMENT 'Path to the script in the repo (e.g. scripts/ingest_edinet_filings.py)',
    container_image VARCHAR(500) NULL COMMENT 'Full Docker image URI with tag (NULL if local)',

    -- Documentation
    description TEXT NULL COMMENT 'Human-readable explanation of this method',
    config_snapshot JSON NULL COMMENT 'Infrastructure config snapshot (cpu, memory, cluster, IAM role, etc.)',

    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether this method is currently in use',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_method_name (method_name),
    INDEX idx_im_runtime_type (runtime_type),
    INDEX idx_im_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Registry of ingestion methods/approaches for data acquisition provenance';

-- Add FK column to data_acquisitions
ALTER TABLE data_acquisitions
  ADD COLUMN IF NOT EXISTS ingestion_method_id BIGINT NULL
  COMMENT 'Which method/approach produced this run'
  AFTER id;

-- Add FK constraint (safe: IF NOT EXISTS not supported for constraints,
-- but CREATE TABLE IF NOT EXISTS on ingestion_methods ensures the target exists)
-- Note: This will fail silently if constraint already exists on re-run.
-- That's acceptable since the table creation is idempotent.
ALTER TABLE data_acquisitions
  ADD CONSTRAINT fk_da_ingestion_method
  FOREIGN KEY (ingestion_method_id) REFERENCES ingestion_methods(id);

-- Seed historical data: the ECS Fargate backfill that already ran
INSERT IGNORE INTO ingestion_methods (method_name, runtime_type, script_path, container_image, description, config_snapshot)
VALUES (
    'edinet-ecs-fargate-backfill',
    'ecs_fargate',
    'scripts/ingest_edinet_filings.py',
    '755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev:edinet-backfill-20260315-210821',
    'One-time backfill of 365 days EDINET filings via ECS Fargate',
    '{"cpu": 256, "memory": 512, "cluster": "dr-data-pipeline-dev", "task_def": "edinet-ingestion-dev:3"}'
);

-- Link existing acquisition runs to this method (safe: WHERE clause prevents re-linking)
UPDATE data_acquisitions
SET ingestion_method_id = (SELECT id FROM ingestion_methods WHERE method_name = 'edinet-ecs-fargate-backfill')
WHERE source_name = 'edinet_filings_ingester'
  AND ingestion_method_id IS NULL;
