#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pattern Visualization Script

Fetches tickers from Aurora, runs pattern detection on each,
and generates visual diagrams showing detected patterns.

Usage:
    python scripts/visualize_patterns.py [--limit N]
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import mplfinance as mpf
import yfinance as yf

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import TICKER_MASTER
from src.analysis.pattern_detectors import (
    ChartPatternDetector,
    CandlestickPatternDetector,
    SupportResistanceDetector,
)
from src.analysis.pattern_types import (
    PATTERN_WEDGE_RISING,
    PATTERN_WEDGE_FALLING,
    PATTERN_TRIANGLE,
    PATTERN_HEAD_AND_SHOULDERS,
    PATTERN_DOUBLE_TOP,
    PATTERN_DOUBLE_BOTTOM,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_active_tickers(limit=None, use_aurora=True):
    """
    Get active tickers from Aurora ticker_master table or use default list.

    Args:
        limit: Maximum number of tickers to return
        use_aurora: Whether to fetch from Aurora (requires SSH tunnel)

    Returns:
        List of (symbol, name) tuples
    """
    logger.info("=" * 60)
    logger.info("📊 Fetching Active Tickers")
    logger.info("=" * 60)

    if use_aurora:
        try:
            client = get_aurora_client()

            query = f"""
                SELECT symbol, name
                FROM {TICKER_MASTER}
                WHERE is_active = TRUE
                ORDER BY symbol
            """

            if limit:
                query += f" LIMIT {limit}"

            results = client.fetch_all(query)

            # Convert dict results to tuples (symbol, name)
            tickers = [(row['symbol'], row['name']) for row in results]

            logger.info(f"✅ Found {len(tickers)} active tickers from Aurora")
            return tickers

        except Exception as e:
            logger.warning(f"⚠️  Aurora connection failed: {e}")
            logger.warning("⚠️  Falling back to default ticker list")
            use_aurora = False

    if not use_aurora:
        # Default ticker list for demonstration
        default_tickers = [
            ('AAPL', 'Apple Inc.'),
            ('MSFT', 'Microsoft Corporation'),
            ('GOOGL', 'Alphabet Inc.'),
            ('NVDA', 'NVIDIA Corporation'),
            ('TSLA', 'Tesla Inc.'),
            ('AMZN', 'Amazon.com Inc.'),
            ('META', 'Meta Platforms Inc.'),
            ('AMD', 'Advanced Micro Devices'),
            ('NFLX', 'Netflix Inc.'),
            ('INTC', 'Intel Corporation'),
        ]

        tickers = default_tickers[:limit] if limit else default_tickers
        logger.info(f"✅ Using {len(tickers)} default tickers")
        return tickers


def fetch_ohlc_data(symbol, period="60d"):
    """
    Fetch OHLC data for a ticker.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL')
        period: Time period ('60d', '3mo', '6mo', '1y')

    Returns:
        DataFrame with OHLC data or None if fetch fails
    """
    try:
        logger.info(f"📄 Fetching {period} OHLC data for {symbol}...")

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            logger.warning(f"⚠️  No data returned for {symbol}")
            return None

        logger.info(f"✅ Fetched {len(hist)} candles for {symbol}")
        return hist

    except Exception as e:
        logger.error(f"❌ Error fetching {symbol}: {e}")
        return None


def detect_all_patterns(data):
    """
    Run all pattern detectors on OHLC data.

    Args:
        data: DataFrame with OHLC columns

    Returns:
        Dict with chart_patterns, candlestick_patterns, support_resistance
    """
    logger.info("🔍 Running pattern detection...")

    chart_detector = ChartPatternDetector()
    candlestick_detector = CandlestickPatternDetector()
    sr_detector = SupportResistanceDetector()

    # Detect patterns
    chart_patterns = chart_detector.detect(data)
    candlestick_patterns = candlestick_detector.detect(data)
    sr_levels = sr_detector.calculate_levels(data, num_levels=3)

    logger.info(
        f"✅ Found {len(chart_patterns)} chart patterns, "
        f"{len(candlestick_patterns)} candlestick patterns, "
        f"{len(sr_levels['support'])} support levels, "
        f"{len(sr_levels['resistance'])} resistance levels"
    )

    return {
        'chart_patterns': chart_patterns,
        'candlestick_patterns': candlestick_patterns,
        'support_resistance': sr_levels
    }


def plot_patterns(symbol, name, data, patterns, output_path):
    """
    Generate chart diagram with detected patterns.

    Args:
        symbol: Ticker symbol
        name: Ticker name
        data: OHLC DataFrame
        patterns: Dict with detected patterns
        output_path: Path to save diagram
    """
    logger.info(f"📊 Generating chart diagram for {symbol}...")

    # Define mplfinance style
    mc = mpf.make_marketcolors(
        up='#26A69A', down='#EF5350',  # Teal green (up), red (down)
        edge={'up': '#1B5E20', 'down': '#B71C1C'},  # Dark green/red edges
        wick={'up': '#1B5E20', 'down': '#B71C1C'},  # Dark green/red wicks
        volume='in',
        alpha=0.9
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle=':',
        y_on_right=False,
        rc={'font.size': 10}
    )

    # Create candlestick chart using mplfinance with returnfig=True
    # This ensures update_width_config is actually applied
    fig, axes = mpf.plot(
        data,
        type='candle',
        style=s,
        volume=False,
        show_nontrading=False,
        figsize=(24, 8),  # Main chart height
        returnfig=True,
        update_width_config=dict(
            candle_linewidth=1.2,  # Thicker borders for visibility
            candle_width=0.9       # Wider bodies (0.0-1.0 range)
        )
    )

    # Get the main axis (mplfinance returns array of axes)
    ax_main = axes[0]

    # Add support/resistance levels
    sr_levels = patterns['support_resistance']
    for support in sr_levels['support']:
        ax_main.axhline(y=support, color='green', linestyle='--', linewidth=1, alpha=0.6)

    for resistance in sr_levels['resistance']:
        ax_main.axhline(y=resistance, color='red', linestyle='--', linewidth=1, alpha=0.6)

    # Annotate chart patterns
    for pattern in patterns['chart_patterns']:
        pattern_type = pattern['pattern']
        pattern_sentiment = pattern['type']

        # Get pattern date/range
        if 'date' in pattern:
            date_str = pattern['date']
            try:
                date_idx = data.index.get_loc(pd.to_datetime(date_str))
            except:
                continue
        elif 'end_date' in pattern:
            date_str = pattern['end_date']
            try:
                date_idx = data.index.get_loc(pd.to_datetime(date_str))
            except:
                continue
        else:
            continue

        # Color based on sentiment
        color = 'green' if pattern_sentiment == 'bullish' else 'red' if pattern_sentiment == 'bearish' else 'blue'

        # Annotation
        y_pos = data.iloc[date_idx]['High'] * 1.02

        pattern_label = pattern_type.replace('_', ' ').title()
        ax_main.annotate(
            pattern_label,
            xy=(data.index[date_idx], y_pos),
            xytext=(0, 20),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc=color, alpha=0.3),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color=color),
            fontsize=8,
            color=color,
            weight='bold'
        )

        # Draw pattern-specific markers
        if pattern_type == PATTERN_WEDGE_RISING or pattern_type == PATTERN_WEDGE_FALLING:
            # Draw converging trendlines using linear regression slopes
            if 'start_date' in pattern and 'end_date' in pattern:
                try:
                    start_idx = data.index.get_loc(pd.to_datetime(pattern['start_date']))
                    end_idx = data.index.get_loc(pd.to_datetime(pattern['end_date']))

                    # Get data segment
                    segment = data.iloc[start_idx:end_idx]
                    x_indices = np.arange(len(segment))

                    # Calculate resistance trendline (using stored slope)
                    resistance_slope = pattern.get('resistance_slope', 0)
                    resistance_intercept = segment['High'].iloc[0]
                    resistance_line = resistance_slope * x_indices + resistance_intercept

                    # Calculate support trendline (using stored slope)
                    support_slope = pattern.get('support_slope', 0)
                    support_intercept = segment['Low'].iloc[0]
                    support_line = support_slope * x_indices + support_intercept

                    # Draw trendlines
                    ax_main.plot(segment.index, resistance_line,
                            color='#FF6B6B', linewidth=2.5, alpha=0.8,
                            linestyle='-', label='Resistance Trendline')
                    ax_main.plot(segment.index, support_line,
                            color='#4ECDC4', linewidth=2.5, alpha=0.8,
                            linestyle='-', label='Support Trendline')

                    # Add shaded wedge area
                    ax_main.fill_between(segment.index, support_line, resistance_line,
                                    color=color, alpha=0.1)
                except Exception as e:
                    logger.debug(f"Could not draw wedge lines: {e}")

        elif pattern_type == PATTERN_HEAD_AND_SHOULDERS:
            if 'head_price' in pattern:
                ax_main.plot(data.index[date_idx], pattern['head_price'], 'ro', markersize=10)

        elif pattern_type == PATTERN_DOUBLE_TOP or pattern_type == PATTERN_DOUBLE_BOTTOM:
            if 'peak1_price' in pattern:
                ax_main.plot(data.index[date_idx], pattern['peak1_price'], 'ro', markersize=8)
                ax_main.plot(data.index[date_idx], pattern['peak2_price'], 'ro', markersize=8)
            elif 'bottom1_price' in pattern:
                ax_main.plot(data.index[date_idx], pattern['bottom1_price'], 'go', markersize=8)
                ax_main.plot(data.index[date_idx], pattern['bottom2_price'], 'go', markersize=8)

    # Title
    ax_main.set_title(
        f'{symbol} - {name}\n'
        f'{len(patterns["chart_patterns"])} Chart Patterns | '
        f'{len(patterns["candlestick_patterns"])} Candlestick Patterns',
        fontsize=14,
        weight='bold'
    )
    ax_main.set_ylabel('Price', fontsize=12)
    ax_main.grid(True, alpha=0.3)

    # Add summary subplot below
    fig.set_size_inches(24, 12)  # Increase height for summary
    ax_summary = fig.add_subplot(2, 1, 2)
    ax_summary.axis('off')

    # Build pattern summary
    summary_lines = []
    summary_lines.append("DETECTED PATTERNS:")
    summary_lines.append("=" * 80)

    # Chart patterns
    if patterns['chart_patterns']:
        summary_lines.append("\n📊 CHART PATTERNS:")
        for i, p in enumerate(patterns['chart_patterns'], 1):
            date = p.get('date') or p.get('end_date', 'N/A')
            summary_lines.append(
                f"  {i}. {p['pattern'].replace('_', ' ').title()} "
                f"({p['type']}) - {date} - Confidence: {p['confidence']}"
            )

            # Add pattern-specific details
            if p['pattern'] in [PATTERN_WEDGE_RISING, PATTERN_WEDGE_FALLING]:
                summary_lines.append(
                    f"     Convergence: {p.get('convergence_ratio', 0):.2f}, "
                    f"Resistance slope: {p.get('resistance_slope', 0):.4f}, "
                    f"Support slope: {p.get('support_slope', 0):.4f}"
                )
    else:
        summary_lines.append("\n📊 CHART PATTERNS: None detected")

    # Candlestick patterns (show first 5)
    if patterns['candlestick_patterns']:
        summary_lines.append("\n🕯️  CANDLESTICK PATTERNS (First 5):")
        for i, p in enumerate(patterns['candlestick_patterns'][:5], 1):
            summary_lines.append(
                f"  {i}. {p['pattern'].replace('_', ' ').title()} "
                f"({p['type']}) - {p['date']} - Confidence: {p['confidence']}"
            )
    else:
        summary_lines.append("\n🕯️  CANDLESTICK PATTERNS: None detected")

    # Support/Resistance
    summary_lines.append(f"\n📈 SUPPORT LEVELS: {sr_levels['support']}")
    summary_lines.append(f"📉 RESISTANCE LEVELS: {sr_levels['resistance']}")
    summary_lines.append(f"💰 CURRENT PRICE: {sr_levels['current_price']:.2f}")

    # Draw text
    summary_text = '\n'.join(summary_lines)
    ax_summary.text(
        0.05, 0.95,
        summary_text,
        transform=ax_summary.transAxes,
        fontsize=9,
        verticalalignment='top',
        fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

    logger.info(f"✅ Saved diagram to {output_path}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description='Visualize chart patterns for all tickers')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of tickers to process')
    parser.add_argument('--period', type=str, default='60d', help='Time period for OHLC data (default: 60d for optimal candlestick visibility)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("🎨 Pattern Visualization Script")
    logger.info("=" * 60)
    logger.info(f"Limit: {args.limit} tickers")
    logger.info(f"Period: {args.period}")
    logger.info("")

    # Get tickers from Aurora
    tickers = get_active_tickers(limit=args.limit)

    if not tickers:
        logger.error("❌ No tickers found in Aurora")
        return

    # Process each ticker
    output_dir = Path('/tmp/pattern_charts')
    output_dir.mkdir(exist_ok=True)

    success_count = 0
    fail_count = 0

    for symbol, name in tickers:
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Processing: {symbol} - {name}")
        logger.info("=" * 60)

        try:
            # Fetch OHLC data
            data = fetch_ohlc_data(symbol, period=args.period)

            if data is None or len(data) < 30:
                logger.warning(f"⚠️  Skipping {symbol} - insufficient data")
                fail_count += 1
                continue

            # Detect patterns
            patterns = detect_all_patterns(data)

            # Generate diagram
            output_path = output_dir / f'pattern_{symbol}.png'
            plot_patterns(symbol, name, data, patterns, output_path)

            success_count += 1

        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {e}", exc_info=True)
            fail_count += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Successfully processed: {success_count} tickers")
    logger.info(f"❌ Failed: {fail_count} tickers")
    logger.info(f"📁 Output directory: {output_dir}")
    logger.info("")
    logger.info(f"View charts: ls -lh {output_dir}")


if __name__ == '__main__':
    main()
