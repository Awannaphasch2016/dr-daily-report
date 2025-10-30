#!/usr/bin/env python3
"""
Generate demo reports for multiple tickers
"""

from agent import TickerAnalysisAgent
import time

def main():
    """Generate reports for demo tickers"""
    # Focus on tickers from the list
    demo_tickers = ['DBS19', 'HONDA19', 'TENCENT19']

    agent = TickerAnalysisAgent()

    for ticker in demo_tickers:
        print("=" * 80)
        print(f"📊 {ticker}")
        print("=" * 80)
        print()

        report = agent.analyze_ticker(ticker)
        print(report)
        print()
        print()

        time.sleep(2)  # Be nice to the APIs

if __name__ == "__main__":
    main()
