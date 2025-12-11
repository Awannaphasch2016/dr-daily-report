#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local MCP Integration Test Script

Runs full workflow locally and validates SEC filing appears in report text.
Provides clear pass/fail feedback.
"""

import os
import sys
import argparse
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agent import TickerAnalysisAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mcp_integration(ticker: str, mcp_url: str = None, strategy: str = 'single-stage'):
    """
    Test MCP integration by generating a report and checking for SEC filing info.
    
    Args:
        ticker: Ticker symbol to test (e.g., 'AAPL')
        mcp_url: MCP server URL (default: from SEC_EDGAR_MCP_URL env var)
        strategy: Report generation strategy ('single-stage' or 'multi-stage')
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Set MCP URL if provided
    if mcp_url:
        os.environ['SEC_EDGAR_MCP_URL'] = mcp_url
        logger.info(f"Using MCP URL: {mcp_url}")
    else:
        mcp_url = os.getenv('SEC_EDGAR_MCP_URL')
        if not mcp_url:
            return False, "SEC_EDGAR_MCP_URL not set. Set environment variable or pass --mcp-url"
        logger.info(f"Using MCP URL from environment: {mcp_url}")

    # Check for LLM API key
    if not os.getenv('OPENROUTER_API_KEY'):
        return False, "OPENROUTER_API_KEY not set"

    logger.info(f"🧪 Testing MCP integration for ticker: {ticker}")
    logger.info(f"   Strategy: {strategy}")
    logger.info(f"   MCP URL: {mcp_url}")

    try:
        # Initialize agent
        logger.info("📦 Initializing agent...")
        agent = TickerAnalysisAgent()

        # Generate report
        logger.info(f"📝 Generating report for {ticker}...")
        report = agent.analyze_ticker(ticker, strategy=strategy)

        # Validate report
        if not isinstance(report, str):
            return False, f"Report should be string, got {type(report)}"

        if len(report) == 0:
            return False, "Report text is empty"

        logger.info(f"✅ Report generated ({len(report)} characters)")

        # Check for SEC filing indicators
        sec_indicators = ['SEC', 'EDGAR', '10-Q', '10-K', 'filing', 'รายงาน', 'Form Type', 'Filing Date']
        report_lower = report.lower()
        found_indicators = [ind for ind in sec_indicators if ind.lower() in report_lower]

        if not found_indicators:
            logger.warning("⚠️ No SEC filing indicators found in report")
            logger.info(f"Report preview (first 500 chars):\n{report[:500]}")
            return False, (
                f"Report missing SEC filing info. "
                f"Expected to find one of: {sec_indicators}"
            )

        logger.info(f"✅ Found SEC filing indicators: {found_indicators}")

        # Check for specific SEC filing details
        has_form_type = any(form in report for form in ['10-Q', '10-K', '8-K', 'quarterly', 'annual'])
        has_filing_reference = any(ref in report.lower() for ref in ['sec', 'edgar', 'filing', 'regulatory'])

        if not (has_form_type or has_filing_reference):
            logger.warning("⚠️ No specific SEC filing details found")
            return False, (
                f"Report should reference SEC filing form type or filing system. "
                f"Report preview: {report[:500]}"
            )

        logger.info("✅ SEC filing details found in report")
        return True, f"✅ Test passed! SEC filing info found in report for {ticker}"

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False, f"Test failed with exception: {str(e)}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test MCP integration locally',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with local MCP server
  python scripts/test_mcp_local.py AAPL --mcp-url http://127.0.0.1:8002/mcp

  # Test with environment variable
  export SEC_EDGAR_MCP_URL=http://127.0.0.1:8002/mcp
  python scripts/test_mcp_local.py AAPL

  # Test with multi-stage strategy
  python scripts/test_mcp_local.py AAPL --strategy multi-stage
        """
    )
    parser.add_argument(
        'ticker',
        help='Ticker symbol to test (e.g., AAPL)'
    )
    parser.add_argument(
        '--mcp-url',
        help='MCP server URL (default: from SEC_EDGAR_MCP_URL env var)'
    )
    parser.add_argument(
        '--strategy',
        choices=['single-stage', 'multi-stage'],
        default='single-stage',
        help='Report generation strategy (default: single-stage)'
    )

    args = parser.parse_args()

    # Run test
    success, message = test_mcp_integration(
        ticker=args.ticker,
        mcp_url=args.mcp_url,
        strategy=args.strategy
    )

    # Print result
    print("\n" + "="*60)
    if success:
        print(f"✅ PASS: {message}")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
