#!/usr/bin/env python3
"""
Generate PDF report and output faithfulness score separately
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.agent import TickerAnalysisAgent


def generate_report_with_faithfulness(ticker: str = "AAPL19"):
    """
    Generate PDF report and output faithfulness score separately
    
    Args:
        ticker: Ticker symbol to analyze (default: AAPL19)
    """
    print("=" * 80)
    print(f"PDF REPORT GENERATION WITH FAITHFULNESS SCORE - {ticker}")
    print("=" * 80)
    print()

    # Initialize agent
    print("?? Initializing agent...")
    try:
        agent = TickerAnalysisAgent()
        print("? Agent initialized")
    except Exception as e:
        if "api_key" in str(e).lower() or "OPENAI_API_KEY" in str(e):
            print("? Error: OPENAI_API_KEY environment variable is not set")
            print("   Please set it before running this script:")
            print("   export OPENAI_API_KEY='your-api-key-here'")
            return False
        raise
    print()

    # Run analysis to get full state (including faithfulness score)
    print(f"?? Running analysis for {ticker}...")
    print("   This will:")
    print("   1. Fetch ticker data from Yahoo Finance")
    print("   2. Calculate technical indicators")
    print("   3. Fetch and analyze news")
    print("   4. Generate chart visualization")
    print("   5. Create narrative report with GPT-4o")
    print("   6. Score narrative faithfulness")
    print("   7. Compile everything into PDF")
    print()
    print("? Please wait... (this may take 10-15 seconds)")
    print()

    try:
        # Run the graph to get full state
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "chart_base64": "",
            "report": "",
            "error": ""
        }

        final_state = agent.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            raise ValueError(f"Analysis failed: {final_state['error']}")

        # Generate PDF
        print("?? Generating PDF report...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{ticker}_report_{timestamp}.pdf"

        pdf_bytes = agent.pdf_generator.generate_report(
            ticker=ticker,
            ticker_data=final_state.get("ticker_data", {}),
            indicators=final_state.get("indicators", {}),
            percentiles=final_state.get("percentiles", {}),
            news=final_state.get("news", []),
            news_summary=final_state.get("news_summary", {}),
            chart_base64=final_state.get("chart_base64", ""),
            report=final_state.get("report", ""),
            output_path=output_filename
        )

        print("? PDF report generated successfully!")
        print()
        print("?? Report Details:")
        print(f"   File: {output_filename}")
        print(f"   Size: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
        print()

        # Output faithfulness score separately
        faithfulness_score = final_state.get("faithfulness_score")
        if faithfulness_score:
            print("\n" + "=" * 80)
            print("FAITHFULNESS SCORE FOR NARRATIVE + NUMBER SECTION")
            print("=" * 80)
            print()
            print(agent.faithfulness_scorer.format_score_report(faithfulness_score))
            print()
        else:
            print("??  No faithfulness score found in final state")

        print("=" * 80)
        print("? Process completed successfully!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"? Report generation failed!")
        print(f"   Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate PDF report and output faithfulness score")
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL19",
        help="Ticker symbol to analyze (default: AAPL19)"
    )

    args = parser.parse_args()
    generate_report_with_faithfulness(args.ticker)
