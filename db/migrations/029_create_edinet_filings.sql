-- Migration 029: Create edinet_filings table
-- Purpose: EDINET (Japan FSA) filings linked to shared acquisition provenance
-- Generated: 2026-03-15
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS edinet_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (nullable: most filings won't match DR tickers)
    ticker_id INT NULL,
    symbol VARCHAR(20) NULL COMMENT 'DR symbol (e.g. NINTENDO19) -- NULL if not matched',

    -- EDINET document identity
    doc_id VARCHAR(50) NOT NULL COMMENT 'EDINET document ID (globally unique per filing)',
    edinet_code VARCHAR(10) NULL COMMENT 'EDINET filer code (persistent company identifier, e.g. E02116)',
    sec_code VARCHAR(10) NULL COMMENT '5-digit security code (e.g. 79740 for Nintendo)',

    -- Filing date context
    filing_date DATE NOT NULL COMMENT 'Date this filing appeared in EDINET listing',
    submit_date_time DATETIME NULL COMMENT 'When filer submitted the document to EDINET',

    -- Classification
    doc_type_code VARCHAR(10) NULL COMMENT 'EDINET doc type: 120=Annual, 140=Quarterly, 160=Semi-Annual',
    doc_description VARCHAR(500) NULL COMMENT 'Human-readable document type description',

    -- Content
    filer_name VARCHAR(300) NULL COMMENT 'Company name as reported by EDINET (Japanese)',
    title VARCHAR(500) NULL COMMENT 'Document title / description',

    -- Fiscal period
    period_start DATE NULL COMMENT 'Fiscal period start date',
    period_end DATE NULL COMMENT 'Fiscal period end date',

    -- Document availability flags
    xbrl_flag BOOLEAN DEFAULT FALSE COMMENT 'Whether XBRL data is available',
    pdf_flag BOOLEAN DEFAULT FALSE COMMENT 'Whether PDF is available for download',
    english_doc_flag BOOLEAN DEFAULT FALSE COMMENT 'Whether English version exists',

    -- Document references
    pdf_url TEXT NULL COMMENT 'Constructed URL to download PDF from EDINET',
    pdf_s3_key VARCHAR(500) NULL COMMENT 'S3 key for archived PDF document',

    -- Raw data (full API response item for this filing)
    raw_data JSON NOT NULL COMMENT 'Complete API response item -- preserves all EDINET fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT NULL COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per EDINET document ID
    UNIQUE KEY uk_doc_id (doc_id),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_edf_filing_date (filing_date DESC),
    INDEX idx_edf_edinet_code (edinet_code),
    INDEX idx_edf_sec_code (sec_code),
    INDEX idx_edf_doc_type (doc_type_code),
    INDEX idx_edf_ticker_id (ticker_id),
    INDEX idx_edf_symbol (symbol),
    INDEX idx_edf_acquisition_id (acquisition_id),
    INDEX idx_edf_period_end (period_end DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='EDINET (Japan FSA) filings linked to shared acquisition provenance';
