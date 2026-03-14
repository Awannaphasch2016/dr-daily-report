"""Backtest commands — run strategy backtests via VectorBT Pro"""

import json
import sys
import click
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

STRATEGY_CHOICES = ['sma', 'rsi', 'macd', 'bollinger', 'all']


@click.group()
@click.pass_context
def backtest(ctx):
    """Backtesting commands - run strategy backtests on ticker data"""
    pass


@backtest.command()
@click.argument('ticker')
@click.option('--strategy', '-s', type=click.Choice(STRATEGY_CHOICES), default='sma', help='Strategy to run')
@click.option('--fast', type=int, default=20, help='Fast period (SMA)')
@click.option('--slow', type=int, default=50, help='Slow period (SMA)')
@click.option('--period', '-p', default='1y', help='Data period (e.g. 6mo, 1y, 2y)')
@click.option('--json-output', is_flag=True, help='Output as JSON')
@click.pass_context
def run(ctx, ticker, strategy, fast, slow, period, json_output):
    """Run backtest for a ticker

    Examples:

        dr backtest run DBS19 --strategy sma --fast 10 --slow 50

        dr backtest run DBS19 --strategy all --period 1y

        dr backtest run DBS19 --strategy rsi --json-output
    """
    try:
        import yfinance as yf
    except ImportError:
        click.echo("Error: yfinance not installed. Run: pip install yfinance", err=True)
        sys.exit(1)

    click.echo(f"Fetching {period} data for {ticker}...")
    hist_data = yf.download(ticker, period=period, progress=False)

    if hist_data.empty:
        click.echo(f"Error: No data returned for ticker '{ticker}'", err=True)
        sys.exit(1)

    # Flatten MultiIndex columns if present (yfinance returns MultiIndex for single ticker)
    if hasattr(hist_data.columns, 'levels') and len(hist_data.columns.levels) > 1:
        hist_data.columns = hist_data.columns.get_level_values(0)

    click.echo(f"Data: {len(hist_data)} rows, {hist_data.index[0].date()} → {hist_data.index[-1].date()}")

    from src.backtesting.types import StrategyType
    from src.backtesting.strategies import get_strategy

    strategy_map = {
        'sma': (StrategyType.SMA_CROSSOVER, {'fast_period': fast, 'slow_period': slow}),
        'rsi': (StrategyType.RSI_THRESHOLD, {}),
        'macd': (StrategyType.MACD_CROSSOVER, {}),
        'bollinger': (StrategyType.BOLLINGER_BAND, {}),
    }

    strategies_to_run = list(strategy_map.keys()) if strategy == 'all' else [strategy]
    all_results = {}

    for strat_name in strategies_to_run:
        strat_type, kwargs = strategy_map[strat_name]
        click.echo(f"\nRunning {strat_name.upper()} strategy...")

        try:
            strat = get_strategy(strat_type, **kwargs)
            buy_result = strat.backtest(hist_data, 'buy_only')
            sell_result = strat.backtest(hist_data, 'sell_only')

            results = {
                'strategy': strat.name,
                'buy_only': buy_result.to_dict(),
                'sell_only': sell_result.to_dict(),
            }
            all_results[strat_name] = results

            if not json_output:
                _print_results(strat.name, buy_result, sell_result)
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            continue

    if json_output:
        click.echo(json.dumps(all_results, indent=2, default=str))


def _print_results(name, buy_result, sell_result):
    """Pretty-print backtest results to terminal."""
    click.echo(f"  Strategy: {name}")
    click.echo(f"  {'Metric':<25} {'Buy-Only':>12} {'Sell-Only':>12}")
    click.echo(f"  {'─' * 49}")

    metrics = [
        ('Total Return %', 'total_return_pct', '.2f'),
        ('Sharpe Ratio', 'sharpe_ratio', '.2f'),
        ('Win Rate %', 'win_rate', '.1f'),
        ('Max Drawdown %', 'max_drawdown_pct', '.2f'),
        ('Num Signals', 'num_signals', 'd'),
        ('Total Trades', 'total_trades', 'd'),
        ('Profit Factor', 'profit_factor', '.2f'),
    ]

    for label, attr, fmt in metrics:
        buy_val = getattr(buy_result, attr)
        sell_val = getattr(sell_result, attr)
        click.echo(f"  {label:<25} {buy_val:>12{fmt}} {sell_val:>12{fmt}}")
