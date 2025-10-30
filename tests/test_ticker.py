#!/usr/bin/env python3
"""
Quick test script to see the actual report output
"""

import sys
from src.agent import TickerAnalysisAgent

def test_ticker(ticker_symbol):
    """Test a single ticker and show the report"""
    print("=" * 80)
    print(f"Testing Ticker: {ticker_symbol}")
    print("=" * 80)
    print()

    # Initialize agent
    print("🔧 Initializing agent...")
    agent = TickerAnalysisAgent()

    # Generate report
    print(f"🔍 Fetching data and generating report for {ticker_symbol}...")
    print()

    report = agent.analyze_ticker(ticker_symbol)

    print("=" * 80)
    print("REPORT OUTPUT:")
    print("=" * 80)
    print()
    print(report)
    print()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    test_ticker(ticker)
