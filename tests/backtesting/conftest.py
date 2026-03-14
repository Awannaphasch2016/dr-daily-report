"""Shared fixtures for backtesting tests"""

import numpy as np
import pandas as pd
import pytest
import vectorbtpro as vbt


@pytest.fixture
def synthetic_ohlcv():
    """Deterministic synthetic OHLCV data using GBM simulation.

    Generates 252 rows (1 trading year) with Geometric Brownian Motion
    for financially realistic price behavior (volatility clustering, fat tails).
    """
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

    # GBM does not generate volume — add synthetic volume
    np.random.seed(42)
    df['Volume'] = np.random.randint(100_000, 1_000_000, n)

    return df


@pytest.fixture
def short_ohlcv():
    """Very short OHLCV data (20 rows) — edge case for insufficient data."""
    n = 20
    dates = pd.bdate_range(start='2024-01-02', periods=n)

    data = vbt.GBMOHLCData.pull(
        'SYN',
        start='2024-01-02',
        periods=n,
        start_value=100,
        seed=99,
        tz_localize=None,
    )
    df = data.get()
    df.index = dates

    np.random.seed(99)
    df['Volume'] = np.random.randint(100_000, 500_000, n)

    return df


@pytest.fixture
def flat_ohlcv():
    """Flat price data — no signals expected."""
    n = 100
    dates = pd.bdate_range(start='2024-01-02', periods=n)

    return pd.DataFrame({
        'Open': np.full(n, 100.0),
        'High': np.full(n, 101.0),
        'Low': np.full(n, 99.0),
        'Close': np.full(n, 100.0),
        'Volume': np.full(n, 500_000, dtype=int),
    }, index=dates)
