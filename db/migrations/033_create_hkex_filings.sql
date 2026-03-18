-- Migration 033: Create hkex_filings table
-- Purpose: HKEX (Hong Kong Exchange) filings linked to shared acquisition provenance
-- Generated: 2026-03-16
-- Depends on: 021_create_data_acquisitions (FK to data_acquisitions)
-- Principle #5: Idempotent operations (safe for retry)

CREATE TABLE IF NOT EXISTS hkex_filings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (nullable)
    ticker_id INT NULL,
    symbol VARCHAR(20) NULL COMMENT 'DR symbol (e.g. TENCENT19) -- NULL if not matched',

    -- HKEX filing identity
    news_id VARCHAR(50) NOT NULL COMMENT 'HKEXnews unique filing identifier',
    stock_code VARCHAR(10) NOT NULL COMMENT 'HKEX 5-digit stock code (e.g. 00700)',

    -- Filing metadata
    filing_date DATE NOT NULL COMMENT 'Date filing was published',
    date_time VARCHAR(50) NULL COMMENT 'Raw datetime string from API',
    category_code VARCHAR(10) NULL COMMENT 'HKEX t1code category',
    subcategory_code VARCHAR(10) NULL COMMENT 'HKEX t2code subcategory (40100=Annual, 40200=Interim)',

    -- Content
    stock_name VARCHAR(300) NULL COMMENT 'Company name as reported by HKEX',
    title TEXT NULL COMMENT 'Filing title/headline',
    long_text TEXT NULL COMMENT 'Full description from API',

    -- Document references
    file_link TEXT NULL COMMENT 'Relative path from API response',
    file_url TEXT NULL COMMENT 'Full URL to filing document',
    file_type VARCHAR(20) NULL COMMENT 'Document type: pdf, htm, xlsx',
    pdf_s3_key VARCHAR(500) NULL COMMENT 'S3 key for archived filing document',

    -- Raw data (full API response item for this filing)
    raw_data JSON NOT NULL COMMENT 'Complete API response item -- preserves all HKEX fields',

    -- Provenance (FK to shared table)
    acquisition_id BIGINT NULL COMMENT 'Which acquisition run produced this row',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'When we fetched this filing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique: one filing per HKEX news ID
    UNIQUE KEY uk_news_id (news_id),

    -- Foreign keys
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),
    FOREIGN KEY (acquisition_id) REFERENCES data_acquisitions(id),

    -- Query indexes
    INDEX idx_hf_stock_code (stock_code),
    INDEX idx_hf_filing_date (filing_date DESC),
    INDEX idx_hf_category (category_code, subcategory_code),
    INDEX idx_hf_ticker_id (ticker_id),
    INDEX idx_hf_symbol (symbol),
    INDEX idx_hf_acquisition_id (acquisition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='HKEX (Hong Kong Exchange) filings linked to shared acquisition provenance';
