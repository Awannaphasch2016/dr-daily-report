-- Migration 020: Create chart_pattern_data table
-- Purpose: Store detected chart patterns with implementation provenance
-- Generated: 2026-01-14
-- Specification: .claude/specs/shared/chart_pattern_data.md
-- Principle #5: Idempotent operations (safe for retry)

-- ============================================================================
-- Table: chart_pattern_data
-- Purpose: Detected chart patterns with implementation tracking
-- Used by: ChartPatternDataRepository, PatternDetectionService
-- ============================================================================

CREATE TABLE IF NOT EXISTS chart_pattern_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (matches existing pattern in daily_indicators, etc.)
    -- Note: INT to match ticker_master.id type
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    pattern_date DATE NOT NULL COMMENT 'Date pattern was detected (analysis date)',

    -- Pattern identification
    pattern_type VARCHAR(50) NOT NULL COMMENT 'Pattern category: bullish_flag, head_shoulders, wedge, etc.',
    pattern_code VARCHAR(20) NOT NULL COMMENT 'Short code: FLAGU, FLAGD, HS, IHS, WDGU, WDGD, etc.',

    -- Implementation provenance (CRITICAL for debugging and A/B testing)
    implementation VARCHAR(50) NOT NULL COMMENT 'Which detector: stock_pattern, custom, talib',
    impl_version VARCHAR(20) NOT NULL COMMENT 'Version of implementation: 1.0.0, 2.1.3',

    -- Detection metadata
    confidence ENUM('high', 'medium', 'low') NOT NULL DEFAULT 'medium',
    start_date DATE COMMENT 'Pattern start date in price data',
    end_date DATE COMMENT 'Pattern end date in price data',

    -- Pattern data (flexible JSON for varying pattern structures)
    -- Example: {"points": {"A": {"date": "2026-01-01", "price": 150.25}}, "measurements": {...}}
    pattern_data JSON NOT NULL COMMENT 'Pattern-specific data: points, prices, measurements',

    -- Timestamps (Principle #16: DATE for business, TIMESTAMP for system)
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When detection ran',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: One pattern per (symbol, date, type, implementation)
    -- Allows multiple implementations to store results for same pattern type
    UNIQUE KEY uk_symbol_date_pattern_impl (symbol, pattern_date, pattern_type, implementation),

    -- Foreign key to ticker_master
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),

    -- Indexes for common query patterns
    INDEX idx_cpd_symbol (symbol),
    INDEX idx_cpd_pattern_date (pattern_date DESC),
    INDEX idx_cpd_pattern_type (pattern_type),
    INDEX idx_cpd_implementation (implementation),
    INDEX idx_cpd_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Detected chart patterns with implementation provenance tracking';
