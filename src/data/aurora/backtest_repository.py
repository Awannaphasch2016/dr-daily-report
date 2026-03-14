# -*- coding: utf-8 -*-
"""
Backtest Results Repository

Data access layer for precomputed backtesting results.
Follows the same pattern as ChartPatternDataRepository.

Architecture:
    backtest_precompute_handler → this repository → Aurora backtest_results table
    workflow_nodes (read path) → this repository → Aurora backtest_results table
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import BACKTEST_RESULTS
from src.data.aurora.precompute_service import _convert_numpy_to_primitives

logger = logging.getLogger(__name__)


ALLOWED_STRATEGY_NAMES: Set[str] = {
    'sma_crossover',
    'rsi_threshold',
    'macd_crossover',
    'bollinger_band',
}


class BacktestRepository:
    """Repository for backtest results operations."""

    def __init__(self, client: Optional[AuroraClient] = None):
        self.client = client or get_aurora_client()

    def _validate_record(self, record: Dict[str, Any]) -> None:
        """Validate record before storage.

        Raises:
            ValueError: If required fields missing or invalid values
        """
        required_fields = {
            'ticker_id', 'symbol', 'backtest_date',
            'strategy_name', 'strategy_params'
        }
        missing = required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        if record['strategy_name'] not in ALLOWED_STRATEGY_NAMES:
            raise ValueError(
                f"Invalid strategy_name '{record['strategy_name']}'. "
                f"Allowed: {sorted(ALLOWED_STRATEGY_NAMES)}"
            )

    def _normalize_date(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value
        raise ValueError(f"Cannot normalize date: {value} (type: {type(value)})")

    def upsert(self, record: Dict[str, Any]) -> int:
        """Upsert a single backtest result.

        Uses INSERT ... ON DUPLICATE KEY UPDATE for idempotency.
        Unique key: (symbol, backtest_date, strategy_name)

        Returns:
            Number of affected rows (1 for insert, 2 for update)
        """
        self._validate_record(record)

        params_clean = _convert_numpy_to_primitives(record['strategy_params'])
        params_json = json.dumps(params_clean)

        query = f"""
            INSERT INTO {BACKTEST_RESULTS} (
                ticker_id, symbol, backtest_date,
                strategy_name, strategy_params,
                buy_total_return_pct, buy_sharpe_ratio, buy_win_rate,
                buy_max_drawdown_pct, buy_num_signals, buy_total_trades, buy_profit_factor,
                sell_total_return_pct, sell_sharpe_ratio, sell_win_rate,
                sell_max_drawdown_pct, sell_num_signals, sell_total_trades, sell_profit_factor,
                detected_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                NOW()
            )
            ON DUPLICATE KEY UPDATE
                strategy_params = VALUES(strategy_params),
                buy_total_return_pct = VALUES(buy_total_return_pct),
                buy_sharpe_ratio = VALUES(buy_sharpe_ratio),
                buy_win_rate = VALUES(buy_win_rate),
                buy_max_drawdown_pct = VALUES(buy_max_drawdown_pct),
                buy_num_signals = VALUES(buy_num_signals),
                buy_total_trades = VALUES(buy_total_trades),
                buy_profit_factor = VALUES(buy_profit_factor),
                sell_total_return_pct = VALUES(sell_total_return_pct),
                sell_sharpe_ratio = VALUES(sell_sharpe_ratio),
                sell_win_rate = VALUES(sell_win_rate),
                sell_max_drawdown_pct = VALUES(sell_max_drawdown_pct),
                sell_num_signals = VALUES(sell_num_signals),
                sell_total_trades = VALUES(sell_total_trades),
                sell_profit_factor = VALUES(sell_profit_factor),
                detected_at = NOW(),
                updated_at = NOW()
        """

        params = (
            record['ticker_id'],
            record['symbol'],
            self._normalize_date(record['backtest_date']),
            record['strategy_name'],
            params_json,
            record.get('buy_total_return_pct', 0.0),
            record.get('buy_sharpe_ratio', 0.0),
            record.get('buy_win_rate', 0.0),
            record.get('buy_max_drawdown_pct', 0.0),
            record.get('buy_num_signals', 0),
            record.get('buy_total_trades', 0),
            record.get('buy_profit_factor', 0.0),
            record.get('sell_total_return_pct', 0.0),
            record.get('sell_sharpe_ratio', 0.0),
            record.get('sell_win_rate', 0.0),
            record.get('sell_max_drawdown_pct', 0.0),
            record.get('sell_num_signals', 0),
            record.get('sell_total_trades', 0),
            record.get('sell_profit_factor', 0.0),
        )

        rowcount = self.client.execute(query, params)
        logger.debug(
            f"Upserted backtest: {record['symbol']} {record['strategy_name']} "
            f"- {rowcount} rows affected"
        )
        return rowcount

    def get_latest(
        self,
        symbol: str,
        backtest_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get latest backtest results for a symbol, reconstructed into
        the strategy_performance dict shape expected by the prompt pipeline.

        Args:
            symbol: Ticker symbol
            backtest_date: Specific date (default: most recent available)

        Returns:
            Dict with per_strategy, consensus, buy_only, sell_only keys
            or None if no data found
        """
        if backtest_date:
            date_condition = "backtest_date = %s"
            params = (symbol, self._normalize_date(backtest_date))
        else:
            date_condition = "backtest_date = (SELECT MAX(backtest_date) FROM {table} WHERE symbol = %s)".format(
                table=BACKTEST_RESULTS
            )
            params = (symbol, symbol)

        query = f"""
            SELECT
                strategy_name, strategy_params,
                buy_total_return_pct, buy_sharpe_ratio, buy_win_rate,
                buy_max_drawdown_pct, buy_num_signals, buy_total_trades, buy_profit_factor,
                sell_total_return_pct, sell_sharpe_ratio, sell_win_rate,
                sell_max_drawdown_pct, sell_num_signals, sell_total_trades, sell_profit_factor
            FROM {BACKTEST_RESULTS}
            WHERE symbol = %s AND {date_condition}
                AND strategy_name != '_consensus'
            ORDER BY strategy_name
        """

        rows = self.client.fetch_all(query, params)
        if not rows:
            return None

        return self._reconstruct_strategy_performance(rows)

    def _reconstruct_strategy_performance(
        self, rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Reconstruct the strategy_performance dict from database rows.

        Returns:
            {'per_strategy': {name: {'buy_only': {...}, 'sell_only': {...}}, ...}}
        """
        per_strategy = {}

        for row in rows:
            name = row['strategy_name']
            buy_only = {
                'total_return_pct': float(row.get('buy_total_return_pct', 0) or 0),
                'sharpe_ratio': float(row.get('buy_sharpe_ratio', 0) or 0),
                'win_rate': float(row.get('buy_win_rate', 0) or 0),
                'max_drawdown_pct': float(row.get('buy_max_drawdown_pct', 0) or 0),
                'num_signals': int(row.get('buy_num_signals', 0) or 0),
                'total_trades': int(row.get('buy_total_trades', 0) or 0),
                'profit_factor': float(row.get('buy_profit_factor', 0) or 0),
            }
            sell_only = {
                'total_return_pct': float(row.get('sell_total_return_pct', 0) or 0),
                'sharpe_ratio': float(row.get('sell_sharpe_ratio', 0) or 0),
                'win_rate': float(row.get('sell_win_rate', 0) or 0),
                'max_drawdown_pct': float(row.get('sell_max_drawdown_pct', 0) or 0),
                'num_signals': int(row.get('sell_num_signals', 0) or 0),
                'total_trades': int(row.get('sell_total_trades', 0) or 0),
                'profit_factor': float(row.get('sell_profit_factor', 0) or 0),
            }

            per_strategy[name] = {
                'buy_only': buy_only,
                'sell_only': sell_only,
            }

        return {'per_strategy': per_strategy}


_repository_instance: Optional[BacktestRepository] = None


def get_backtest_repository() -> BacktestRepository:
    """Get singleton BacktestRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = BacktestRepository()
    return _repository_instance
