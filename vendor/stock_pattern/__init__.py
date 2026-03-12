# -*- coding: utf-8 -*-
"""
Stock Pattern Library (Vendored)

Chart pattern detection library from BennyThadikaran/stock-pattern.
Source: https://github.com/BennyThadikaran/stock-pattern
License: GPL-3.0
Version: Commit 85c710d (2026-01-11)

This is a vendored copy containing only utils.py (pattern detection functions).
The full library includes Plotter.py (visualization), backtest.py, and loaders/
which are not needed for our use case.

Usage:
    from vendor.stock_pattern.utils import (
        find_bullish_flag,
        find_bearish_flag,
        find_triangles,
        make_serializable,
    )
"""

from .utils import (
    # Pattern detection functions
    find_bullish_flag,
    find_bearish_flag,
    find_triangles,
    find_double_bottom,
    find_double_top,
    find_hns,
    find_reverse_hns,
    find_bullish_vcp,
    find_bearish_vcp,
    # Utility functions
    make_serializable,
    get_atr,
    getY,
)

__all__ = [
    'find_bullish_flag',
    'find_bearish_flag',
    'find_triangles',
    'find_double_bottom',
    'find_double_top',
    'find_hns',
    'find_reverse_hns',
    'find_bullish_vcp',
    'find_bearish_vcp',
    'make_serializable',
    'get_atr',
    'getY',
]
