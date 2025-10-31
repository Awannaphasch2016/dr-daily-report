#!/usr/bin/env python3
"""
Test script for percentile analysis of technical indicators
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
import json

def test_percentile_analysis(ticker_symbol="AAPL"):
    """Test percentile analysis for a ticker"""
    print("=" * 80)
    print(f"Testing Percentile Analysis for: {ticker_symbol}")
    print("=" * 80)
    print()

    # Initialize components
    print("🔧 Initializing components...")
    data_fetcher = DataFetcher()
    technical_analyzer = TechnicalAnalyzer()

    # Load ticker map
    ticker_map = data_fetcher.load_tickers()
    yahoo_ticker = ticker_map.get(ticker_symbol.upper(), ticker_symbol.upper())

    print(f"📊 Yahoo Finance ticker: {yahoo_ticker}")
    print()

    # Fetch historical data
    print("📥 Fetching historical data...")
    data = data_fetcher.fetch_ticker_data(yahoo_ticker, period="1y")

    if not data or data.get('history') is None:
        print(f"❌ Failed to fetch data for {ticker_symbol}")
        return

    hist_data = data['history']
    print(f"✅ Fetched {len(hist_data)} days of historical data")
    print()

    # Calculate indicators with percentiles
    print("🔍 Calculating indicators with percentiles...")
    result = technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)

    if not result:
        print("❌ Failed to calculate indicators")
        return

    indicators = result['indicators']
    percentiles = result.get('percentiles', {})

    print("✅ Indicators calculated successfully")
    print()

    # Display current indicators
    print("=" * 80)
    print("CURRENT INDICATORS")
    print("=" * 80)
    print(f"Price: ${indicators.get('current_price', 0):.2f}")
    print(f"RSI: {indicators.get('rsi', 0):.2f}")
    print(f"MACD: {indicators.get('macd', 0):.4f}")
    print(f"Uncertainty Score: {indicators.get('uncertainty_score', 0):.2f}/100")
    print(f"ATR: {indicators.get('atr', 0):.4f}")
    print(f"VWAP: ${indicators.get('vwap', 0):.2f}")
    print()

    # Display percentile analysis
    print("=" * 80)
    print("PERCENTILE ANALYSIS")
    print("=" * 80)
    print()

    if not percentiles:
        print("⚠️  No percentile data available")
        return

    # RSI Percentiles
    if 'rsi' in percentiles:
        rsi_stats = percentiles['rsi']
        print("📊 RSI Percentile Analysis:")
        print(f"  Current Value: {rsi_stats['current_value']:.2f}")
        print(f"  Percentile: {rsi_stats['percentile']:.1f}%")
        print(f"  Mean: {rsi_stats['mean']:.2f}")
        print(f"  Std Dev: {rsi_stats['std']:.2f}")
        print(f"  Min: {rsi_stats['min']:.2f}")
        print(f"  Max: {rsi_stats['max']:.2f}")
        print(f"  Frequency above 70: {rsi_stats['frequency_above_70']:.1f}%")
        print(f"  Frequency below 30: {rsi_stats['frequency_below_30']:.1f}%")
        print()

    # MACD Percentiles
    if 'macd' in percentiles:
        macd_stats = percentiles['macd']
        print("📊 MACD Percentile Analysis:")
        print(f"  Current Value: {macd_stats['current_value']:.4f}")
        print(f"  Percentile: {macd_stats['percentile']:.1f}%")
        print(f"  Mean: {macd_stats['mean']:.4f}")
        print(f"  Frequency positive: {macd_stats['frequency_positive']:.1f}%")
        print()

    # Uncertainty Score Percentiles
    if 'uncertainty_score' in percentiles:
        unc_stats = percentiles['uncertainty_score']
        print("📊 Uncertainty Score Percentile Analysis:")
        print(f"  Current Value: {unc_stats['current_value']:.2f}/100")
        print(f"  Percentile: {unc_stats['percentile']:.1f}%")
        print(f"  Mean: {unc_stats['mean']:.2f}")
        print(f"  Frequency low (<25): {unc_stats['frequency_low']:.1f}%")
        print(f"  Frequency high (>75): {unc_stats['frequency_high']:.1f}%")
        print()

    # ATR Percent Percentiles
    if 'atr_percent' in percentiles:
        atr_stats = percentiles['atr_percent']
        print("📊 ATR Percent Percentile Analysis:")
        print(f"  Current Value: {atr_stats['current_value']:.2f}%")
        print(f"  Percentile: {atr_stats['percentile']:.1f}%")
        print(f"  Mean: {atr_stats['mean']:.2f}%")
        print(f"  Frequency low volatility (<1%): {atr_stats['frequency_low_volatility']:.1f}%")
        print(f"  Frequency high volatility (>4%): {atr_stats['frequency_high_volatility']:.1f}%")
        print()

    # Volume Ratio Percentiles
    if 'volume_ratio' in percentiles:
        vol_stats = percentiles['volume_ratio']
        print("📊 Volume Ratio Percentile Analysis:")
        print(f"  Current Value: {vol_stats['current_value']:.2f}x")
        print(f"  Percentile: {vol_stats['percentile']:.1f}%")
        print(f"  Mean: {vol_stats['mean']:.2f}x")
        print(f"  Frequency high volume (>2x): {vol_stats['frequency_high_volume']:.1f}%")
        print(f"  Frequency low volume (<0.7x): {vol_stats['frequency_low_volume']:.1f}%")
        print()

    # Display formatted percentile analysis
    print("=" * 80)
    print("FORMATTED PERCENTILE ANALYSIS (Thai)")
    print("=" * 80)
    print()
    formatted = technical_analyzer.format_percentile_analysis(percentiles)
    print(formatted)

    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    test_percentile_analysis(ticker)
