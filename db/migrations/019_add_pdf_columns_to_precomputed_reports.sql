-- Migration 019: Add PDF columns to precomputed_reports
-- Purpose: Store PDF metadata (S3 key, presigned URL, generation timestamp)
-- Generated: 2026-01-03
-- Principle #5: Idempotent operations (safe for retry)

-- Add PDF storage columns
ALTER TABLE precomputed_reports
    ADD COLUMN IF NOT EXISTS pdf_s3_key VARCHAR(500) DEFAULT NULL
        COMMENT 'S3 key for uploaded PDF',
    ADD COLUMN IF NOT EXISTS pdf_presigned_url TEXT DEFAULT NULL
        COMMENT 'Cached presigned URL (24h TTL)',
    ADD COLUMN IF NOT EXISTS pdf_url_expires_at DATETIME DEFAULT NULL
        COMMENT 'When presigned URL expires',
    ADD COLUMN IF NOT EXISTS pdf_generated_at TIMESTAMP NULL DEFAULT NULL
        COMMENT 'When PDF was generated';

-- Add index for PDF lookups
CREATE INDEX IF NOT EXISTS idx_pdf_generated
    ON precomputed_reports(pdf_generated_at DESC);
