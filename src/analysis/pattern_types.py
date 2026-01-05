# -*- coding: utf-8 -*-
"""
Chart Pattern Type Constants - Single Source of Truth

Centralized pattern names following Principle #14 (Table Name Centralization).
Using constants prevents typos and enables autocomplete/type safety.

Usage:
    from src.analysis.pattern_types import PATTERN_HEAD_AND_SHOULDERS

    pattern = {
        'pattern': PATTERN_HEAD_AND_SHOULDERS,
        'type': 'bearish',
        ...
    }
"""

# =============================================================================
# Chart Patterns (Price Action Patterns)
# =============================================================================

# Reversal Patterns
PATTERN_HEAD_AND_SHOULDERS = 'head_and_shoulders'
PATTERN_INVERSE_HEAD_AND_SHOULDERS = 'inverse_head_and_shoulders'
PATTERN_DOUBLE_TOP = 'double_top'
PATTERN_DOUBLE_BOTTOM = 'double_bottom'
PATTERN_TRIPLE_TOP = 'triple_top'
PATTERN_TRIPLE_BOTTOM = 'triple_bottom'

# Triangle Patterns (Continuation/Reversal)
PATTERN_TRIANGLE = 'triangle'  # Generic triangle
PATTERN_TRIANGLE_ASCENDING = 'ascending_triangle'
PATTERN_TRIANGLE_DESCENDING = 'descending_triangle'
PATTERN_TRIANGLE_SYMMETRICAL = 'symmetrical_triangle'

# Continuation Patterns
PATTERN_FLAG_PENNANT = 'flag_pennant'
PATTERN_FLAG_BULLISH = 'flag_bullish'
PATTERN_FLAG_BEARISH = 'flag_bearish'
PATTERN_PENNANT_BULLISH = 'pennant_bullish'
PATTERN_PENNANT_BEARISH = 'pennant_bearish'

# Cup Patterns
PATTERN_CUP_AND_HANDLE = 'cup_and_handle'
PATTERN_INVERSE_CUP_AND_HANDLE = 'inverse_cup_and_handle'

# Wedge Patterns
PATTERN_WEDGE_RISING = 'wedge_rising'
PATTERN_WEDGE_FALLING = 'wedge_falling'

# Channel Patterns
PATTERN_CHANNEL_ASCENDING = 'channel_ascending'
PATTERN_CHANNEL_DESCENDING = 'channel_descending'
PATTERN_CHANNEL_HORIZONTAL = 'channel_horizontal'

# Rounding Patterns
PATTERN_ROUNDING_BOTTOM = 'rounding_bottom'
PATTERN_ROUNDING_TOP = 'rounding_top'

# =============================================================================
# Candlestick Patterns (Single or Multi-Candle)
# =============================================================================

# Reversal Candlesticks (Single Candle)
PATTERN_DOJI = 'doji'
PATTERN_HAMMER = 'hammer'
PATTERN_INVERTED_HAMMER = 'inverted_hammer'
PATTERN_HANGING_MAN = 'hanging_man'
PATTERN_SHOOTING_STAR = 'shooting_star'
PATTERN_SPINNING_TOP = 'spinning_top'

# Reversal Candlesticks (Multi-Candle)
PATTERN_ENGULFING_BULLISH = 'engulfing_bullish'
PATTERN_ENGULFING_BEARISH = 'engulfing_bearish'
PATTERN_HARAMI_BULLISH = 'harami_bullish'
PATTERN_HARAMI_BEARISH = 'harami_bearish'
PATTERN_PIERCING_LINE = 'piercing_line'
PATTERN_DARK_CLOUD_COVER = 'dark_cloud_cover'
PATTERN_MORNING_STAR = 'morning_star'
PATTERN_EVENING_STAR = 'evening_star'
PATTERN_THREE_WHITE_SOLDIERS = 'three_white_soldiers'
PATTERN_THREE_BLACK_CROWS = 'three_black_crows'
PATTERN_THREE_LINE_STRIKE = 'three_line_strike'

# =============================================================================
# Support & Resistance Levels
# =============================================================================

LEVEL_SUPPORT = 'support'
LEVEL_RESISTANCE = 'resistance'
LEVEL_SUPPORT_RESISTANCE = 'support_resistance'  # Level acting as both

# =============================================================================
# Gap Patterns
# =============================================================================

PATTERN_GAP_UP = 'gap_up'
PATTERN_GAP_DOWN = 'gap_down'
PATTERN_GAP_EXHAUSTION = 'gap_exhaustion'
PATTERN_GAP_BREAKAWAY = 'gap_breakaway'
PATTERN_GAP_RUNAWAY = 'gap_runaway'

# =============================================================================
# Pattern Categories (for filtering and grouping)
# =============================================================================

CHART_PATTERNS_REVERSAL = [
    PATTERN_HEAD_AND_SHOULDERS,
    PATTERN_INVERSE_HEAD_AND_SHOULDERS,
    PATTERN_DOUBLE_TOP,
    PATTERN_DOUBLE_BOTTOM,
    PATTERN_TRIPLE_TOP,
    PATTERN_TRIPLE_BOTTOM,
    PATTERN_ROUNDING_BOTTOM,
    PATTERN_ROUNDING_TOP,
]

CHART_PATTERNS_CONTINUATION = [
    PATTERN_FLAG_PENNANT,
    PATTERN_FLAG_BULLISH,
    PATTERN_FLAG_BEARISH,
    PATTERN_PENNANT_BULLISH,
    PATTERN_PENNANT_BEARISH,
    PATTERN_CHANNEL_ASCENDING,
    PATTERN_CHANNEL_DESCENDING,
]

CHART_PATTERNS_TRIANGLE = [
    PATTERN_TRIANGLE,
    PATTERN_TRIANGLE_ASCENDING,
    PATTERN_TRIANGLE_DESCENDING,
    PATTERN_TRIANGLE_SYMMETRICAL,
]

CHART_PATTERNS_CUP = [
    PATTERN_CUP_AND_HANDLE,
    PATTERN_INVERSE_CUP_AND_HANDLE,
]

CHART_PATTERNS_WEDGE = [
    PATTERN_WEDGE_RISING,
    PATTERN_WEDGE_FALLING,
]

CHART_PATTERNS = (
    CHART_PATTERNS_REVERSAL +
    CHART_PATTERNS_CONTINUATION +
    CHART_PATTERNS_TRIANGLE +
    CHART_PATTERNS_CUP +
    CHART_PATTERNS_WEDGE +
    [PATTERN_CHANNEL_HORIZONTAL]
)

CANDLESTICK_PATTERNS_SINGLE = [
    PATTERN_DOJI,
    PATTERN_HAMMER,
    PATTERN_INVERTED_HAMMER,
    PATTERN_HANGING_MAN,
    PATTERN_SHOOTING_STAR,
    PATTERN_SPINNING_TOP,
]

CANDLESTICK_PATTERNS_MULTI = [
    PATTERN_ENGULFING_BULLISH,
    PATTERN_ENGULFING_BEARISH,
    PATTERN_HARAMI_BULLISH,
    PATTERN_HARAMI_BEARISH,
    PATTERN_PIERCING_LINE,
    PATTERN_DARK_CLOUD_COVER,
    PATTERN_MORNING_STAR,
    PATTERN_EVENING_STAR,
    PATTERN_THREE_WHITE_SOLDIERS,
    PATTERN_THREE_BLACK_CROWS,
    PATTERN_THREE_LINE_STRIKE,
]

CANDLESTICK_PATTERNS = CANDLESTICK_PATTERNS_SINGLE + CANDLESTICK_PATTERNS_MULTI

GAP_PATTERNS = [
    PATTERN_GAP_UP,
    PATTERN_GAP_DOWN,
    PATTERN_GAP_EXHAUSTION,
    PATTERN_GAP_BREAKAWAY,
    PATTERN_GAP_RUNAWAY,
]

ALL_PATTERNS = CHART_PATTERNS + CANDLESTICK_PATTERNS + GAP_PATTERNS

# =============================================================================
# Pattern Type Classification (Bullish/Bearish/Neutral)
# =============================================================================

PATTERN_TYPE_BULLISH = 'bullish'
PATTERN_TYPE_BEARISH = 'bearish'
PATTERN_TYPE_NEUTRAL = 'neutral'

# =============================================================================
# Confidence Levels
# =============================================================================

CONFIDENCE_HIGH = 'high'
CONFIDENCE_MEDIUM = 'medium'
CONFIDENCE_LOW = 'low'
