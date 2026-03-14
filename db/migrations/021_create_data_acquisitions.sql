-- Migration 021: Create data_acquisitions table
-- Purpose: Shared provenance table with script artifact tracking in S3
-- Generated: 2026-03-14 (v2 — redesigned with tool identity + S3 artifacts)
-- Principle #5: Idempotent operations (safe for retry)

-- ============================================================================
-- Table: data_acquisitions
-- Purpose: Track acquisition runs — WHO (tool), WHAT (code version in S3),
--          WHERE (endpoint), and HOW IT WENT (metrics)
-- Used by: DataAcquisitionsRepository, any data pipeline
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_acquisitions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- What table was populated
    source_table VARCHAR(50) NOT NULL COMMENT 'Target table: sgx_filings, daily_prices, etc.',

    -- Tool identity
    source_type ENUM('script', 'service', 'export', 'manual') NOT NULL
        COMMENT 'What kind of tool: script (ad-hoc), service (Lambda), export (DB dump), manual (CSV)',
    source_name VARCHAR(100) NOT NULL
        COMMENT 'Tool name: sgx_financial_reports_scraper, fund_data_sqlserver, etc.',
    source_version VARCHAR(50)
        COMMENT 'Tool version tag: v1, v2_2026-03-20, git:a1b2c3d',

    -- Code artifact in S3 (points to exact script that ran)
    artifact_s3_key VARCHAR(500)
        COMMENT 'S3 key to script file: scripts/data-acquisition/sgx-fin-reports/v2.py',
    artifact_checksum VARCHAR(64)
        COMMENT 'SHA256 of the script file for integrity verification',

    -- Data source (what API/endpoint was called)
    endpoint_url VARCHAR(500)
        COMMENT 'API endpoint or data source: https://api.sgx.com/financialreports/v1.0',
    endpoint_version VARCHAR(20)
        COMMENT 'API version: v1.0, v1.1',

    -- Run configuration
    description VARCHAR(500)
        COMMENT 'Human description of this run',
    parameters JSON
        COMMENT 'Request parameters, filters, config used for this run',

    -- Run metrics
    records_fetched INT DEFAULT 0 COMMENT 'Records obtained from source',
    records_upserted INT DEFAULT 0 COMMENT 'Records written to target table',
    status ENUM('running', 'success', 'partial', 'failed') NOT NULL DEFAULT 'running',
    error_message TEXT COMMENT 'Error details if status = failed/partial',

    -- Timestamps
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL COMMENT 'When acquisition finished',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_da_source_table (source_table),
    INDEX idx_da_source_type (source_type),
    INDEX idx_da_source_name (source_name),
    INDEX idx_da_status (status),
    INDEX idx_da_started_at (started_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Shared data acquisition provenance — tracks tool, code version, endpoint, and run metrics';
