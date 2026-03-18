-- Migration 028: Make sgx_filings.ticker_id nullable + add attachment_s3_key
-- Purpose: Allow storing ALL SGX filings (not just DR-matched ones)
-- Generated: 2026-03-14
-- Depends on: 022_create_sgx_filings
--
-- Why: The original schema required ticker_id NOT NULL, which prevented
-- storing filings for companies not in ticker_master. We want to store
-- ALL filings and do filtering at query time.

-- Step 1: Drop FK → make columns nullable → re-add FK
-- FK allows NULL values — NULL just means "no match in ticker_master"
ALTER TABLE sgx_filings
  DROP FOREIGN KEY sgx_filings_ibfk_1,
  MODIFY COLUMN ticker_id INT NULL,
  MODIFY COLUMN symbol VARCHAR(20) NULL;

ALTER TABLE sgx_filings
  ADD CONSTRAINT fk_sgx_filings_ticker_id
  FOREIGN KEY (ticker_id) REFERENCES ticker_master(id);

-- Step 2: Add column for S3-archived PDF attachments
ALTER TABLE sgx_filings
  ADD COLUMN attachment_s3_key VARCHAR(500) NULL
  COMMENT 'S3 key for archived PDF attachment'
  AFTER attachment_url;
