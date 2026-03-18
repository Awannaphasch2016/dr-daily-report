-- Migration 035: Create mops_filings table
-- Purpose: MOPS (Taiwan Market Observation Post System) filings linked to shared acquisition provenance
-- Generated: 2026-03-16
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS mops_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (nullable)
    ticker_id INT NULL,
    symbol VARCHAR(20) NULL COMMENT 'DR symbol (e.g. TAIWAN19) -- NULL if not matched',

    -- MOPS filing identity
    filename VARCHAR(200) NOT NULL COMMENT 'MOPS unique filename (e.g. 202312_0050_AI3.pdf)',
    stock_code VARCHAR(10) NOT NULL COMMENT 'TWSE stock code (e.g. 0050)',

    -- Filing metadata
    filing_date DATE NULL COMMENT 'Derived from report year and period',
    report_year INT NOT NULL COMMENT 'Western calendar year (not ROC)',
    report_type VARCHAR(20) NOT NULL COMMENT 'annual_report or financial_statement',
    report_period VARCHAR(10) NULL COMMENT 'Q1, Q2, Q3, or annual',
    mtype VARCHAR(10) NULL COMMENT 'MOPS category code (F=annual report, A=IFRS)',
    dtype VARCHAR(10) NULL COMMENT 'MOPS sub-type code (F04, AI1, AI3, etc.)',

    -- Content
    company_name VARCHAR(300) NULL COMMENT 'Company name from MOPS listing',
    title VARCHAR(500) NULL COMMENT 'Report title (derived or from listing)',

    -- Document references
    file_url TEXT NULL COMMENT 'Constructed download URL for the PDF',
    pdf_s3_key VARCHAR(500) NULL COMMENT 'S3 key for archived PDF document',

    -- Raw data (full listing row + request params)
    raw_data JSON NOT NULL COMMENT 'Complete MOPS listing data -- preserves all fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT NULL COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per MOPS filename
    UNIQUE KEY uk_filename (filename),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_mf_stock_code (stock_code),
    INDEX idx_mf_filing_date (filing_date DESC),
    INDEX idx_mf_report_type (report_type),
    INDEX idx_mf_ticker_id (ticker_id),
    INDEX idx_mf_symbol (symbol),
    INDEX idx_mf_acquisition_id (acquisition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='MOPS (Taiwan Market Observation Post System) filings linked to shared acquisition provenance';
