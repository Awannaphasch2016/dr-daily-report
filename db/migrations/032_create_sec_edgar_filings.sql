-- Migration 032: Create sec_edgar_filings table
-- Purpose: SEC EDGAR (US) filings linked to shared acquisition provenance
-- Generated: 2026-03-16
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS sec_edgar_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (nullable)
    ticker_id INT NULL,
    symbol VARCHAR(20) NULL COMMENT 'DR symbol (e.g. NVDA19) -- NULL if not matched',

    -- SEC filing identity
    accession_number VARCHAR(25) NOT NULL COMMENT 'SEC accession number (globally unique per filing)',
    cik VARCHAR(10) NOT NULL COMMENT 'SEC Central Index Key (company identifier)',

    -- Filing metadata
    form_type VARCHAR(20) NULL COMMENT 'SEC form type: 10-K, 10-Q, 8-K, N-CSR, etc.',
    filing_date DATE NOT NULL COMMENT 'Date filed with SEC',
    report_date DATE NULL COMMENT 'Period of report (fiscal period end)',
    acceptance_datetime DATETIME NULL COMMENT 'When SEC accepted the filing',

    -- Content
    company_name VARCHAR(300) NULL COMMENT 'Company name as reported to SEC',
    title VARCHAR(500) NULL COMMENT 'Filing description',

    -- Document references
    primary_document VARCHAR(500) NULL COMMENT 'Primary document filename (e.g. nvda-20240128.htm)',
    primary_doc_url TEXT NULL COMMENT 'Full URL to primary filing document',
    filing_index_url TEXT NULL COMMENT 'URL to SEC filing index page',
    pdf_s3_key VARCHAR(500) NULL COMMENT 'S3 key for archived filing document',

    -- Raw data (full API response item for this filing)
    raw_data JSON NOT NULL COMMENT 'Complete API response item -- preserves all SEC fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT NULL COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per SEC accession number
    UNIQUE KEY uk_accession (accession_number),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_sef_cik (cik),
    INDEX idx_sef_form_type (form_type),
    INDEX idx_sef_filing_date (filing_date DESC),
    INDEX idx_sef_ticker_id (ticker_id),
    INDEX idx_sef_symbol (symbol),
    INDEX idx_sef_acquisition_id (acquisition_id),
    INDEX idx_sef_report_date (report_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='SEC EDGAR (US) filings linked to shared acquisition provenance';
