-- Migration 025: Create backtest_results table
-- Purpose: Store precomputed backtesting results for multiple strategies
-- Generated: 2026-03-14
-- Principle #5: Idempotent operations (safe for retry)

-- ============================================================================
-- Table: backtest_results
-- Purpose: Strategy backtesting results precomputed daily
-- Used by: BacktestRepository, backtest_precompute_handler
-- ============================================================================

CREATE TABLE IF NOT EXISTS backtest_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Ticker reference (matches existing pattern in daily_indicators, etc.)
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    backtest_date DATE NOT NULL COMMENT 'Date backtest was run (analysis date)',

    -- Strategy identification
    strategy_name VARCHAR(50) NOT NULL COMMENT 'Strategy key: sma_crossover, rsi_threshold, macd_crossover, bollinger_band, _consensus',
    strategy_params JSON NOT NULL COMMENT 'Strategy parameters: {"fast_period": 20, "slow_period": 50}',

    -- Buy-only backtest metrics
    buy_total_return_pct FLOAT DEFAULT 0.0,
    buy_sharpe_ratio FLOAT DEFAULT 0.0,
    buy_win_rate FLOAT DEFAULT 0.0,
    buy_max_drawdown_pct FLOAT DEFAULT 0.0,
    buy_num_signals INT DEFAULT 0,
    buy_total_trades INT DEFAULT 0,
    buy_profit_factor FLOAT DEFAULT 0.0,

    -- Sell-only backtest metrics
    sell_total_return_pct FLOAT DEFAULT 0.0,
    sell_sharpe_ratio FLOAT DEFAULT 0.0,
    sell_win_rate FLOAT DEFAULT 0.0,
    sell_max_drawdown_pct FLOAT DEFAULT 0.0,
    sell_num_signals INT DEFAULT 0,
    sell_total_trades INT DEFAULT 0,
    sell_profit_factor FLOAT DEFAULT 0.0,

    -- Consensus fields (only populated on _consensus summary row)
    consensus_signal VARCHAR(10) COMMENT 'Majority direction: BUY or SELL (NULL for per-strategy rows)',
    consensus_strength VARCHAR(20) COMMENT 'UNANIMOUS, STRONG, MIXED, WEAK (NULL for per-strategy rows)',
    consensus_data JSON COMMENT 'Full consensus summary JSON (NULL for per-strategy rows)',

    -- Timestamps (Principle #16: DATE for business, TIMESTAMP for system)
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When backtest ran',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint: One result per (symbol, date, strategy)
    -- Enables idempotent ON DUPLICATE KEY UPDATE for re-runs
    UNIQUE KEY uk_symbol_date_strategy (symbol, backtest_date, strategy_name),

    -- Foreign key to ticker_master
    FOREIGN KEY (ticker_id) REFERENCES ticker_master(id),

    -- Indexes for common query patterns
    INDEX idx_bt_symbol (symbol),
    INDEX idx_bt_date (backtest_date DESC),
    INDEX idx_bt_strategy (strategy_name),
    INDEX idx_bt_ticker_id (ticker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Strategy backtesting results precomputed daily';
