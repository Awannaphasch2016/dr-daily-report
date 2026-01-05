#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyze Pattern Detection Results

Scans all tickers, runs pattern detection, and outputs JSON file
with ticker-pattern combinations for the standalone chart viewer.

Usage:
    python scripts/analyze_pattern_results.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf

from src.analysis.pattern_detectors import (
    ChartPatternDetector,
    SupportResistanceDetector,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_default_tickers():
    """Get default ticker list."""
    return [
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


def analyze_ticker(symbol, period="60d"):
    """
    Analyze patterns for a single ticker.

    Returns:
        Dict with pattern counts and examples
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty or len(hist) < 30:
            return None

        # Detect patterns
        chart_detector = ChartPatternDetector()
        chart_patterns = chart_detector.detect(hist)

        # Group by pattern type
        pattern_types = {}
        for pattern in chart_patterns:
            ptype = pattern['pattern']
            if ptype not in pattern_types:
                pattern_types[ptype] = []
            pattern_types[ptype].append({
                'date': pattern.get('date') or pattern.get('end_date', 'N/A'),
                'type': pattern['type'],
                'confidence': pattern['confidence']
            })

        return {
            'symbol': symbol,
            'total_patterns': len(chart_patterns),
            'pattern_types': pattern_types
        }

    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None


def main():
    logger.info("=" * 60)
    logger.info("📊 Analyzing Chart Pattern Results")
    logger.info("=" * 60)

    tickers = get_default_tickers()
    results = []
    ticker_pattern_buttons = []

    for symbol, name in tickers:
        logger.info(f"Analyzing {symbol}...")

        analysis = analyze_ticker(symbol)
        if analysis:
            results.append(analysis)

            # Create button entries for each pattern type
            for pattern_type, instances in analysis['pattern_types'].items():
                ticker_pattern_buttons.append({
                    'symbol': symbol,
                    'name': name,
                    'pattern': pattern_type,
                    'count': len(instances),
                    'sentiment': instances[0]['type'],
                    'latest_date': instances[0]['date']
                })

    # Summary
    total_patterns = sum(r['total_patterns'] for r in results)
    unique_pattern_types = set()
    for r in results:
        unique_pattern_types.update(r['pattern_types'].keys())

    logger.info("")
    logger.info("=" * 60)
    logger.info("📈 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Tickers analyzed: {len(results)}")
    logger.info(f"Total chart patterns: {total_patterns}")
    logger.info(f"Unique pattern types: {len(unique_pattern_types)}")
    logger.info(f"Ticker-pattern combinations: {len(ticker_pattern_buttons)}")
    logger.info("")

    # Pattern type breakdown
    logger.info("Pattern type counts:")
    pattern_counts = {}
    for r in results:
        for ptype, instances in r['pattern_types'].items():
            pattern_counts[ptype] = pattern_counts.get(ptype, 0) + len(instances)

    for ptype, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {ptype}: {count}")

    # Save to JSON
    output = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_tickers': len(results),
            'total_patterns': total_patterns,
            'unique_pattern_types': len(unique_pattern_types),
            'ticker_pattern_combinations': len(ticker_pattern_buttons)
        },
        'pattern_counts': pattern_counts,
        'ticker_patterns': ticker_pattern_buttons,
        'details': results
    }

    output_path = Path('/tmp/pattern_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f"📁 Saved analysis to {output_path}")


if __name__ == '__main__':
    main()
