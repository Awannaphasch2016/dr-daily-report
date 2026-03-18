-- Migration 036: Create hose_filings table
-- Purpose: HOSE (Ho Chi Minh City Stock Exchange) filings linked to shared acquisition provenance
-- Generated: 2026-03-16
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS hose_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (nullable)
    ticker_id INT NULL,
    symbol VARCHAR(20) NULL COMMENT 'DR symbol (e.g. VNM19) -- NULL if not matched',

    -- HOSE filing identity
    news_id VARCHAR(50) NOT NULL COMMENT 'HOSE API newsId -- unique filing identifier',
    ticker_code VARCHAR(20) NULL COMMENT 'HOSE ticker code (e.g. VNM, FPT)',

    -- Filing metadata
    filing_date DATE NOT NULL COMMENT 'Date filing was published',
    news_type VARCHAR(50) NULL COMMENT 'HOSE API type field',
    report_type VARCHAR(30) NULL COMMENT 'annual_report, quarterly_report, other',
    related_id VARCHAR(50) NULL COMMENT 'HOSE entity association',
    category_alias VARCHAR(50) NULL COMMENT 'aliasCate used in query',

    -- Content
    company_name VARCHAR(300) NULL COMMENT 'Vietnamese company name',
    title TEXT NULL COMMENT 'Filing title/headline',

    -- Document references
    document_path VARCHAR(500) NULL COMMENT 'Relative path from API response',
    file_url TEXT NULL COMMENT 'Full URL to filing document (PDF)',
    pdf_s3_key VARCHAR(500) NULL COMMENT 'S3 key for archived filing document',

    -- Raw data (full API response item for this filing)
    raw_data JSON NOT NULL COMMENT 'Complete API response item -- preserves all HOSE fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT NULL COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per HOSE news ID
    UNIQUE KEY uk_news_id (news_id),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_hof_ticker_code (ticker_code),
    INDEX idx_hof_filing_date (filing_date DESC),
    INDEX idx_hof_report_type (report_type),
    INDEX idx_hof_ticker_id (ticker_id),
    INDEX idx_hof_symbol (symbol),
    INDEX idx_hof_acquisition_id (acquisition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='HOSE (Ho Chi Minh City Stock Exchange) filings linked to shared acquisition provenance';
