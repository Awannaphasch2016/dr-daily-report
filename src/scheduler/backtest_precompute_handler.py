# -*- coding: utf-8 -*-
"""
Lambda handler for precomputing backtest results for a single ticker.

Single Responsibility: Run 4 strategies for one ticker, store in Aurora.

Architecture: Called by Step Functions Map state (one invocation per ticker).
Follows the same pattern as pattern_precompute_handler.py.

Triggered by: Step Functions precompute workflow (daily after market close)
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup.

    Raises:
        RuntimeError: If any required environment variable is missing
    """
    required_vars = {
        'TZ': 'Bangkok timezone for date handling',
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Precompute backtest results for a single ticker.

    Event format:
        {"ticker": "NVDA19", "ticker_id": 1}

    Returns:
        {"ticker": "NVDA19", "strategies_computed": 4, "status": "success" | "error"}
    """
    _validate_required_config()

    start_time = datetime.now()
    ticker = event.get('ticker')
    ticker_id = event.get('ticker_id')

    logger.info(f"▶️ Backtest precompute starting: {ticker} (id={ticker_id})")

    if not ticker:
        logger.error("Missing ticker in event")
        return {
            'ticker': ticker,
            'status': 'error',
            'error': 'Missing ticker in event',
        }

    # Lookup ticker_id if not provided
    if not ticker_id:
        try:
            from src.data.aurora.repository import TickerRepository
            repo = TickerRepository()
            ticker_info = repo.get_ticker_by_symbol(ticker)
            if ticker_info:
                ticker_id = ticker_info.get('id')
            else:
                logger.warning(f"Ticker {ticker} not found in ticker_master, using placeholder")
                ticker_id = 0
        except Exception as e:
            logger.warning(f"Could not lookup ticker_id for {ticker}: {e}")
            ticker_id = 0

    try:
        from src.data.aurora.repository import TickerRepository
        from src.data.aurora.backtest_repository import get_backtest_repository
        from src.backtesting.engine import BacktestEngine
        from src.backtesting.strategies import get_strategy
        from src.backtesting.types import StrategyType

        # Fetch historical price data from Aurora
        price_repo = TickerRepository()
        hist_data = price_repo.get_prices_as_dataframe(ticker, days=365)

        if hist_data is None or hist_data.empty:
            duration = (datetime.now() - start_time).total_seconds()
            logger.warning(f"No price data for {ticker}")
            return {
                'ticker': ticker,
                'ticker_id': ticker_id,
                'strategies_computed': 0,
                'duration_seconds': duration,
                'status': 'success',
            }

        # Build engine with all 4 strategies
        engine = BacktestEngine()
        for st in StrategyType:
            engine.register_strategy(st.value, get_strategy(st))

        # Run all strategies
        results = engine.run_all(hist_data)
        summary = BacktestEngine.summarize(results)

        if not results:
            duration = (datetime.now() - start_time).total_seconds()
            logger.warning(f"All strategies failed for {ticker}")
            return {
                'ticker': ticker,
                'ticker_id': ticker_id,
                'strategies_computed': 0,
                'duration_seconds': duration,
                'status': 'success',
            }

        # Store results in Aurora
        bt_repo = get_backtest_repository()
        stored_count = 0
        today = date.today()

        # Upsert per-strategy rows
        for strategy_name, directions in summary['per_strategy'].items():
            try:
                buy = directions.get('buy_only', {})
                sell = directions.get('sell_only', {})

                # Get strategy params from the engine
                strategy_obj = engine._strategies.get(strategy_name)
                strategy_params = {}
                if strategy_obj and hasattr(strategy_obj, '__dict__'):
                    strategy_params = {
                        k: v for k, v in strategy_obj.__dict__.items()
                        if isinstance(v, (int, float, str, bool))
                    }

                record = {
                    'ticker_id': ticker_id,
                    'symbol': ticker,
                    'backtest_date': today,
                    'strategy_name': strategy_name,
                    'strategy_params': strategy_params,
                    'buy_total_return_pct': buy.get('total_return_pct', 0.0),
                    'buy_sharpe_ratio': buy.get('sharpe_ratio', 0.0),
                    'buy_win_rate': buy.get('win_rate', 0.0),
                    'buy_max_drawdown_pct': buy.get('max_drawdown_pct', 0.0),
                    'buy_num_signals': buy.get('num_signals', 0),
                    'buy_total_trades': buy.get('total_trades', 0),
                    'buy_profit_factor': buy.get('profit_factor', 0.0),
                    'sell_total_return_pct': sell.get('total_return_pct', 0.0),
                    'sell_sharpe_ratio': sell.get('sharpe_ratio', 0.0),
                    'sell_win_rate': sell.get('win_rate', 0.0),
                    'sell_max_drawdown_pct': sell.get('max_drawdown_pct', 0.0),
                    'sell_num_signals': sell.get('num_signals', 0),
                    'sell_total_trades': sell.get('total_trades', 0),
                    'sell_profit_factor': sell.get('profit_factor', 0.0),
                }

                bt_repo.upsert(record)
                stored_count += 1

            except Exception as e:
                logger.error(f"  Failed to store {strategy_name}: {e}")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ Stored {stored_count} strategy results for {ticker} "
            f"in {duration:.2f}s"
        )

        return {
            'ticker': ticker,
            'ticker_id': ticker_id,
            'strategies_computed': stored_count,
            'duration_seconds': duration,
            'status': 'success',
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Backtest precompute failed for {ticker}: {e}")
        return {
            'ticker': ticker,
            'ticker_id': ticker_id,
            'status': 'error',
            'error': str(e),
            'duration_seconds': duration,
        }


if __name__ == '__main__':
    import os
    os.environ['TZ'] = 'Asia/Bangkok'

    test_event = {
        'ticker': 'NVDA19',
        'ticker_id': 1,
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
