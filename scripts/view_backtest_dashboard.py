"""Quick script to run SMA backtest and open interactive VBT Pro dashboard."""

import pandas as pd
import vectorbtpro as vbt
import webbrowser
import tempfile
import os

# GBM-simulated price data (deterministic via seed)
n = 252
dates = pd.bdate_range(start='2024-01-02', periods=n)

data = vbt.GBMOHLCData.pull(
    'SYN',
    start='2024-01-02',
    periods=n,
    start_value=100,
    seed=42,
    tz_localize=None,
)
df = data.get()
df.index = dates
close = df['Close']

# SMA crossover
fast_period, slow_period = 20, 50
fast_ma = vbt.MA.run(close, window=fast_period).ma
slow_ma = vbt.MA.run(close, window=slow_period).ma

entries = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
exits = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))

# Build portfolio
portfolio = vbt.Portfolio.from_signals(
    close=close,
    entries=entries,
    exits=exits,
    init_cash=100_000,
    fees=0.001,
)

# Print stats
print("=" * 60)
print(f"SMA Crossover ({fast_period}/{slow_period}) Backtest Results")
print("=" * 60)
print(portfolio.stats())
print()

# Save interactive dashboard as HTML and open
fig = portfolio.plot()
html_path = os.path.join(tempfile.gettempdir(), "vbt_dashboard.html")
fig.write_html(html_path)
print(f"Dashboard saved to: {html_path}")
webbrowser.open(f"file://{html_path}")
