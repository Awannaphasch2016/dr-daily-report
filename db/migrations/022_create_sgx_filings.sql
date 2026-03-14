-- Migration 022: Create sgx_filings table
-- Purpose: SGX exchange filings linked to shared acquisition provenance
-- Generated: 2026-03-14 (v2 — nullable category for Financial Reports API)
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

-- ============================================================================
-- Table: sgx_filings
-- Purpose: Store SGX announcements/filings with provenance tracking
-- Used by: SgxFilingsRepository
-- Sources: Announcements API (has cat/sub), Financial Reports API (no cat/sub)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sgx_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL COMMENT 'DR symbol (e.g. DBS19)',

    -- SGX announcement identity (from API response)
    ann_id VARCHAR(50) NOT NULL COMMENT 'SGX announcement/report ID (unique per filing)',
    broadcast_date_time DATETIME NOT NULL COMMENT 'SGX broadcast timestamp',

    -- Classification (nullable: Financial Reports API has no cat/sub)
    category_code VARCHAR(20) COMMENT 'SGX category: ANNC, FIN_REPORT, etc.',
    subcategory_code VARCHAR(20) COMMENT 'SGX subcategory: ANNC09, ANNC13, etc.',
    subcategory_name VARCHAR(100) COMMENT 'Human-readable subcategory name',

    -- Filing content
    title TEXT NOT NULL COMMENT 'Announcement title/subject',
    issuer_name VARCHAR(200) COMMENT 'Company name as reported by SGX',
    stock_code VARCHAR(20) COMMENT 'SGX stock code (e.g. D05) — not available from all APIs',

    -- Document references
    attachment_url TEXT COMMENT 'URL to PDF/document attachment',
    sgx_url TEXT COMMENT 'URL to SGX announcement page',

    -- Raw data (full API response item for this filing)
    raw_data JSON NOT NULL COMMENT 'Complete API response item — preserves all fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per SGX announcement ID
    UNIQUE KEY uk_ann_id (ann_id),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_sgxf_symbol (symbol),
    INDEX idx_sgxf_broadcast_date (broadcast_date_time DESC),
    INDEX idx_sgxf_category (category_code, subcategory_code),
    INDEX idx_sgxf_stock_code (stock_code),
    INDEX idx_sgxf_ticker_id (ticker_id),
    INDEX idx_sgxf_acquisition_id (acquisition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='SGX exchange filings linked to shared acquisition provenance';
