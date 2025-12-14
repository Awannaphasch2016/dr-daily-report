-- Complete Aurora Schema Migration
-- Purpose: Single source of truth for all database tables
-- Created: 2025-12-12
-- Description: Creates all 11 tables required by the application based on INSERT query analysis

-- ============================================================================
-- Table 1: ticker_info
-- Purpose: Core ticker metadata and company information
-- Used by: repository.py (ticker management, upsert operations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_info (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Primary identifier
    symbol VARCHAR(20) NOT NULL UNIQUE,

    -- Display names
    display_name VARCHAR(100),
    company_name VARCHAR(255),

    -- Market/Exchange info
    exchange VARCHAR(50),
    market VARCHAR(50),
    currency VARCHAR(10),

    -- Classification
    sector VARCHAR(100),
    industry VARCHAR(100),

    -- Additional metadata
    quote_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    last_fetched_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_symbol (symbol),
    INDEX idx_market (market),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table 2: daily_prices
-- Purpose: Historical OHLCV price data
-- Used by: repository.py (price data storage and retrieval)
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Date of price data
    price_date DATE NOT NULL,

    -- OHLCV data
    open DECIMAL(18, 6),
    high DECIMAL(18, 6),
    low DECIMAL(18, 6),
    close DECIMAL(18, 6),
    adj_close DECIMAL(18, 6),
    volume BIGINT,

    -- Calculated fields
    daily_return DECIMAL(10, 6),

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, price_date),

    -- Indexes
    INDEX idx_daily_prices_symbol (symbol),
    INDEX idx_daily_prices_date (price_date),
    INDEX idx_daily_prices_symbol_date (symbol, price_date DESC),
    INDEX idx_daily_prices_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table 3: ticker_cache_metadata
-- Purpose: Metadata for S3 cache synchronization
-- Used by: repository.py (cache tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_cache_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    symbol VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',

    -- S3 tracking
    s3_key VARCHAR(255),
    rows_in_aurora INT DEFAULT 0,

    -- Error handling
    error_message TEXT,

    -- Timestamps
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_cache_date (symbol, cache_date),

    -- Indexes
    INDEX idx_cache_status (status),
    INDEX idx_cache_date (cache_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table 4: precomputed_reports
-- Purpose: Cache for generated ticker analysis reports
-- Used by: precompute_service.py (report storage and retrieval)
-- ============================================================================

CREATE TABLE IF NOT EXISTS precomputed_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Ticker reference
    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,

    -- Report content
    report_text TEXT,
    report_json JSON,

    -- Report metadata
    strategy VARCHAR(50),
    generation_time_ms INT,
    mini_reports JSON,
    chart_base64 LONGTEXT,

    -- Status tracking
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, report_date),
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),

    -- Indexes
    INDEX idx_report_date (report_date DESC),
    INDEX idx_status (status),
    INDEX idx_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table 5: ticker_data_cache
-- Purpose: Cache for 1-year price history and company info (JSON storage)
-- Used by: precompute_service.py (bulk data caching)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_data_cache (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_master_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,

    -- Cached data (JSON)
    price_history JSON NOT NULL,
    company_info JSON,
    financials_json JSON,

    -- Metadata
    history_start_date DATE,
    history_end_date DATE,
    row_count INT,
    source VARCHAR(50) DEFAULT 'yfinance',

    -- Timestamps
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, date),

    -- Indexes
    INDEX idx_cache_fetched (fetched_at),
    INDEX idx_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Table 6: fund_data
-- Purpose: Fund data synced from on-premises SQL Server via S3
-- Used by: fund_data_repository.py (external data sync)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fund_data (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    -- Composite business key
    d_trade DATE NOT NULL COMMENT 'Trading date from source system',
    stock VARCHAR(50) NOT NULL COMMENT 'Stock identifier from source system',
    ticker VARCHAR(50) NOT NULL COMMENT 'Ticker symbol (DR format or Yahoo format)',
    col_code VARCHAR(100) NOT NULL COMMENT 'Column code identifying data type',

    -- Data values
    value_numeric DECIMAL(20, 6) COMMENT 'Numeric value (price, volume, etc.)',
    value_text TEXT COMMENT 'Text value (status, notes, etc.)',

    -- Metadata
    source VARCHAR(50) DEFAULT 'sql_server' COMMENT 'Source system identifier',
    s3_source_key VARCHAR(500) COMMENT 'S3 object key that sourced this data',

    -- Timestamps
    synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When data was synced to Aurora',

    PRIMARY KEY (id),

    -- Unique constraint for idempotent sync
    UNIQUE KEY uk_fund_data_composite (d_trade, stock, ticker, col_code),

    -- Indexes
    INDEX idx_fund_data_ticker (ticker),
    INDEX idx_fund_data_d_trade (d_trade DESC),
    INDEX idx_fund_data_col_code (col_code),
    INDEX idx_fund_data_synced (synced_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table 7: daily_indicators
-- Purpose: Technical indicators computed daily per ticker
-- Used by: precompute_service.py (technical analysis)
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    indicator_date DATE NOT NULL,

    -- Price data
    open_price DECIMAL(18, 6),
    high_price DECIMAL(18, 6),
    low_price DECIMAL(18, 6),
    close_price DECIMAL(18, 6),
    volume BIGINT,

    -- Moving averages
    sma_20 DECIMAL(18, 6),
    sma_50 DECIMAL(18, 6),
    sma_200 DECIMAL(18, 6),

    -- Momentum indicators
    rsi_14 DECIMAL(10, 4),

    -- MACD
    macd DECIMAL(18, 6),
    macd_signal DECIMAL(18, 6),
    macd_histogram DECIMAL(18, 6),

    -- Bollinger Bands
    bb_upper DECIMAL(18, 6),
    bb_middle DECIMAL(18, 6),
    bb_lower DECIMAL(18, 6),

    -- Volatility
    atr_14 DECIMAL(18, 6),
    atr_percent DECIMAL(10, 4),

    -- Volume indicators
    vwap DECIMAL(18, 6),
    volume_sma_20 BIGINT,
    volume_ratio DECIMAL(10, 4),

    -- Custom indicators
    uncertainty_score DECIMAL(10, 4),
    price_vwap_pct DECIMAL(10, 4),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, indicator_date),

    -- Indexes
    INDEX idx_indicators_date (indicator_date),
    INDEX idx_indicators_ticker (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Table 8: indicator_percentiles
-- Purpose: Percentile rankings for indicators (historical context)
-- Used by: precompute_service.py (relative strength analysis)
-- ============================================================================

CREATE TABLE IF NOT EXISTS indicator_percentiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    percentile_date DATE NOT NULL,
    lookback_days INT NOT NULL DEFAULT 365,

    -- Price percentiles
    current_price_percentile DECIMAL(5, 2),

    -- RSI analysis
    rsi_percentile DECIMAL(5, 2),
    rsi_mean DECIMAL(10, 4),
    rsi_std DECIMAL(10, 4),
    rsi_freq_above_70 DECIMAL(5, 2),
    rsi_freq_below_30 DECIMAL(5, 2),

    -- MACD analysis
    macd_percentile DECIMAL(5, 2),
    macd_freq_positive DECIMAL(5, 2),

    -- Uncertainty analysis
    uncertainty_percentile DECIMAL(5, 2),
    uncertainty_freq_low DECIMAL(5, 2),
    uncertainty_freq_high DECIMAL(5, 2),

    -- ATR analysis
    atr_pct_percentile DECIMAL(5, 2),
    atr_freq_low DECIMAL(5, 2),
    atr_freq_high DECIMAL(5, 2),

    -- Volume analysis
    volume_ratio_percentile DECIMAL(5, 2),
    volume_freq_high DECIMAL(5, 2),
    volume_freq_low DECIMAL(5, 2),

    -- SMA deviation percentiles
    sma_20_dev_percentile DECIMAL(5, 2),
    sma_50_dev_percentile DECIMAL(5, 2),
    sma_200_dev_percentile DECIMAL(5, 2),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date_lookback (symbol, percentile_date, lookback_days),

    -- Indexes
    INDEX idx_percentiles_date (percentile_date),
    INDEX idx_percentiles_ticker (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Table 9: comparative_features
-- Purpose: Comparative metrics for peer analysis
-- Used by: precompute_service.py (peer comparison)
-- ============================================================================

CREATE TABLE IF NOT EXISTS comparative_features (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_date DATE NOT NULL,

    -- Return metrics
    daily_return DECIMAL(10, 6),
    weekly_return DECIMAL(10, 6),
    monthly_return DECIMAL(10, 6),
    ytd_return DECIMAL(10, 6),

    -- Volatility metrics
    volatility_30d DECIMAL(10, 6),
    volatility_90d DECIMAL(10, 6),

    -- Risk-adjusted returns
    sharpe_ratio_30d DECIMAL(10, 4),
    sharpe_ratio_90d DECIMAL(10, 4),

    -- Drawdown metrics
    max_drawdown_30d DECIMAL(10, 6),
    max_drawdown_90d DECIMAL(10, 6),

    -- Relative strength
    rs_vs_set DECIMAL(10, 6),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, feature_date),

    -- Indexes
    INDEX idx_features_date (feature_date),
    INDEX idx_features_ticker (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Table 10: ticker_master (Optional - check if ticker_resolver.py is used)
-- Purpose: Master ticker registry for ticker resolution
-- Used by: ticker_resolver.py (ticker normalization)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_master (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Company info
    company_name VARCHAR(255),
    exchange VARCHAR(100),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_ticker_master_company (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- Table 11: ticker_aliases (Optional - check if ticker_resolver.py is used)
-- Purpose: Ticker symbol aliases and mappings
-- Used by: ticker_resolver.py (ticker resolution)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticker_aliases (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    symbol_type VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE KEY uk_ticker_symbol (ticker_id, symbol),

    -- Indexes
    INDEX idx_aliases_symbol (symbol),
    INDEX idx_aliases_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
