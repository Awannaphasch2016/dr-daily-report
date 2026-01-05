#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone Chart Server

Provides API endpoints for the standalone chart viewer to fetch:
- OHLC data via yfinance
- Pattern detection results

Run with: python standalone_chart_server.py
Then open: http://localhost:8080
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import yfinance as yf
import logging

from src.analysis.pattern_detectors import (
    ChartPatternDetector,
    CandlestickPatternDetector,
    SupportResistanceDetector,
)

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Serve the standalone chart viewer HTML."""
    return send_file('standalone_chart_viewer.html')


@app.route('/patterns')
def pattern_explorer():
    """Serve the pattern explorer HTML."""
    return send_file('standalone_pattern_explorer.html')


@app.route('/api/pattern-analysis')
def get_pattern_analysis():
    """
    Get pre-computed pattern analysis results.

    Returns:
        JSON with ticker-pattern combinations
    """
    try:
        analysis_path = Path('/tmp/pattern_analysis.json')

        if not analysis_path.exists():
            return jsonify({
                'error': 'Pattern analysis not found. Run scripts/analyze_pattern_results.py first.'
            }), 404

        with open(analysis_path, 'r') as f:
            data = json.load(f)

        return jsonify(data)

    except Exception as e:
        logger.error(f"Error loading pattern analysis: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/chart-data/<symbol>')
def get_chart_data(symbol):
    """
    Get OHLC data and pattern detection for a ticker.

    Args:
        symbol: Ticker symbol (e.g., AAPL)
        period: Query param for time period (30d, 60d, 90d, 6mo)

    Returns:
        JSON with ohlc data and detected patterns
    """
    from flask import request

    period = request.args.get('period', '60d')

    try:
        logger.info(f"Fetching chart data for {symbol} ({period})")

        # Fetch OHLC data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return jsonify({
                'error': f'No data available for {symbol}'
            }), 404

        # Convert to OHLC format for Chart.js
        ohlc = []
        for date, row in hist.iterrows():
            ohlc.append({
                'x': int(date.timestamp() * 1000),  # Unix timestamp in ms
                'o': float(row['Open']),
                'h': float(row['High']),
                'l': float(row['Low']),
                'c': float(row['Close'])
            })

        # Run pattern detection
        patterns = detect_patterns_from_df(hist)

        logger.info(f"Found {len(patterns['chart_patterns'])} chart patterns for {symbol}")

        return jsonify({
            'symbol': symbol.upper(),
            'ohlc': ohlc,
            'patterns': patterns
        })

    except Exception as e:
        logger.error(f"Error fetching chart data: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


def detect_patterns_from_df(data):
    """
    Detect patterns from OHLC DataFrame.

    Args:
        data: DataFrame with OHLC columns

    Returns:
        Dict with chart_patterns and support_resistance
    """
    chart_detector = ChartPatternDetector()
    sr_detector = SupportResistanceDetector()

    # Detect patterns
    chart_patterns = chart_detector.detect(data)
    sr_levels = sr_detector.calculate_levels(data, num_levels=3)

    # Format for JSON response
    patterns_formatted = []
    for pattern in chart_patterns:
        patterns_formatted.append({
            'pattern': pattern['pattern'],
            'type': pattern['type'],
            'confidence': pattern['confidence'],
            'start_date': pattern.get('start_date'),
            'end_date': pattern.get('end_date'),
            'date': pattern.get('date'),
            'resistance_slope': pattern.get('resistance_slope'),
            'support_slope': pattern.get('support_slope'),
            'convergence_ratio': pattern.get('convergence_ratio')
        })

    return {
        'chart_patterns': patterns_formatted,
        'support_resistance': {
            'support': [float(s) for s in sr_levels['support']],
            'resistance': [float(r) for r in sr_levels['resistance']],
            'current_price': float(sr_levels['current_price'])
        }
    }


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Standalone Chart Server Starting")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📊 Chart Viewer: http://localhost:8080")
    logger.info("🎯 Pattern Explorer: http://localhost:8080/patterns")
    logger.info("")
    logger.info("🔌 API Endpoints:")
    logger.info("   - Chart Data: http://localhost:8080/api/chart-data/<symbol>?period=60d")
    logger.info("   - Pattern Analysis: http://localhost:8080/api/pattern-analysis")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    app.run(host='0.0.0.0', port=8080, debug=True)
