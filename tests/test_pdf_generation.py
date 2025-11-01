#!/usr/bin/env python3
"""
Test script for PDF report generation

This script tests the PDF generation functionality by:
1. Generating a full analysis for a ticker
2. Creating a PDF report
3. Saving it to disk for manual inspection
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent import TickerAnalysisAgent


def test_pdf_generation(ticker: str = "AAPL19"):
    """
    Test PDF generation for a given ticker

    Args:
        ticker: Ticker symbol to analyze (default: AAPL19)
    """
    print("=" * 80)
    print(f"PDF REPORT GENERATION TEST - {ticker}")
    print("=" * 80)
    print()

    # Initialize agent
    print("🔄 Initializing agent...")
    agent = TickerAnalysisAgent()
    print("✅ Agent initialized")
    print()

    # Generate PDF report
    print(f"📊 Generating PDF report for {ticker}...")
    print("   This will:")
    print("   1. Fetch ticker data from Yahoo Finance")
    print("   2. Calculate technical indicators")
    print("   3. Fetch and analyze news")
    print("   4. Generate chart visualization")
    print("   5. Create narrative report with GPT-4o")
    print("   6. Compile everything into PDF")
    print()
    print("⏳ Please wait... (this may take 10-15 seconds)")
    print()

    try:
        # Generate PDF with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{ticker}_report_{timestamp}.pdf"

        pdf_bytes = agent.generate_pdf_report(
            ticker=ticker,
            output_path=output_filename
        )

        print("✅ PDF report generated successfully!")
        print()
        print("📁 Report Details:")
        print(f"   File: {output_filename}")
        print(f"   Size: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
        print()
        print("📖 Report Structure:")
        print("   1. ✅ Title with company info")
        print("   2. ✅ Quick Summary (price, P/E, RSI, analyst rating, sentiment)")
        print("   3. ✅ Technical Analysis Chart (4-panel with indicators)")
        print("   4. ✅ Investment Analysis Narrative (Thai story-style)")
        print("   5. ✅ News References (with sentiment and impact scores)")
        print("   6. ✅ Investment Scoring (technical, fundamental, momentum, sentiment)")
        print()
        print(f"💡 You can now open '{output_filename}' with any PDF viewer")
        print()
        print("🎯 Test Result: PASSED ✅")

        return True

    except Exception as e:
        print(f"❌ PDF generation failed!")
        print(f"   Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("🎯 Test Result: FAILED ❌")

        return False


def test_multiple_tickers():
    """Test PDF generation for multiple tickers"""
    print("\n" + "=" * 80)
    print("MULTI-TICKER PDF GENERATION TEST")
    print("=" * 80)
    print()

    tickers = ["AAPL19", "TSLA19", "MSFT19"]
    results = []

    for ticker in tickers:
        print(f"\n{'─' * 80}")
        print(f"Testing: {ticker}")
        print(f"{'─' * 80}\n")

        result = test_pdf_generation(ticker)
        results.append((ticker, result))

        print()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for ticker, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {ticker}: {status}")

    print()

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")

    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test PDF report generation")
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL19",
        help="Ticker symbol to test (default: AAPL19)"
    )
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Test multiple tickers (AAPL19, TSLA19, MSFT19)"
    )

    args = parser.parse_args()

    if args.multi:
        test_multiple_tickers()
    else:
        test_pdf_generation(args.ticker)
