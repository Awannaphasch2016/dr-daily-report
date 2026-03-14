-- Migration 027: Drop consensus columns from backtest_results
-- Consensus logic moved from backtesting layer to report generation layer.
-- Per-strategy raw results are kept; interpretation happens at report time.

ALTER TABLE backtest_results
    DROP COLUMN IF EXISTS consensus_signal,
    DROP COLUMN IF EXISTS consensus_strength,
    DROP COLUMN IF EXISTS consensus_data;

DELETE FROM backtest_results WHERE strategy_name = '_consensus';
