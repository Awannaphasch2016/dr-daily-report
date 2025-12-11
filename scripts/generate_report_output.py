#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate report and output full text for manual inspection.

This script generates a report for a ticker and prints the full output,
allowing manual inspection of whether MCP data was used.
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


def generate_and_print_report(ticker: str, mcp_url: str = None, strategy: str = 'single-stage'):
    """Generate report and print full output."""
    # Set MCP URL if provided
    if mcp_url:
        os.environ['SEC_EDGAR_MCP_URL'] = mcp_url
        logger.info(f"Using MCP URL: {mcp_url}")
    else:
        mcp_url = os.getenv('SEC_EDGAR_MCP_URL')
        if mcp_url:
            logger.info(f"Using MCP URL from environment: {mcp_url}")
        else:
            logger.warning("⚠️ SEC_EDGAR_MCP_URL not set - MCP will be skipped for non-US tickers")
    
    # Check for LLM API key
    if not os.getenv('OPENROUTER_API_KEY'):
        logger.error("❌ OPENROUTER_API_KEY not set")
        return None
    
    logger.info("=" * 80)
    logger.info(f"📊 Generating report for ticker: {ticker}")
    logger.info(f"   Strategy: {strategy}")
    logger.info(f"   MCP URL: {mcp_url or 'Not configured'}")
    logger.info("=" * 80)
    
    try:
        # Initialize agent
        logger.info("📦 Initializing agent...")
        agent = TickerAnalysisAgent()
        
        # Generate report
        logger.info(f"📝 Generating report...")
        result = agent.analyze_ticker(ticker, strategy=strategy)
        
        # Handle dict return (final_state)
        if isinstance(result, dict):
            report = result.get("report", "")
            error = result.get("error", "")
            
            if error:
                logger.error(f"❌ Workflow error: {error}")
                return None
            
            if not report or len(report) == 0:
                logger.error("❌ Report generation failed or returned empty")
                logger.error(f"   Final state keys: {list(result.keys())}")
                logger.error(f"   Report value: {repr(report)}")
                return None
        elif isinstance(result, str):
            # Backward compatibility
            report = result
            if len(report) == 0:
                logger.error("❌ Report generation failed or returned empty")
                return None
        else:
            logger.error(f"❌ Unexpected return type: {type(result)}")
            return None
        
        logger.info(f"✅ Report generated ({len(report)} characters)")
        
        # Print full report
        print("\n" + "=" * 80)
        print("📄 GENERATED REPORT")
        print("=" * 80)
        print(report)
        print("=" * 80)
        
        # Check if ticker is US-listed
        is_us_ticker = not any(ticker.endswith(suffix) for suffix in ['19', '.SI', '.HK', '.T', '.TW'])
        
        print("\n" + "=" * 80)
        print("🔍 MCP INTEGRATION STATUS")
        print("=" * 80)
        
        if is_us_ticker:
            print(f"✅ {ticker} is a US ticker - MCP should be used")
            if mcp_url:
                # Check for SEC filing indicators
                sec_indicators = ['SEC', 'EDGAR', '10-Q', '10-K', '8-K', 'filing', 'Form Type', 'Filing Date']
                report_lower = report.lower()
                found = [ind for ind in sec_indicators if ind.lower() in report_lower]
                
                if found:
                    print(f"✅ Found SEC filing indicators: {found}")
                    print("✅ MCP integration appears to be working!")
                else:
                    print("⚠️ No SEC filing indicators found in report")
                    print("   This could mean:")
                    print("   1. MCP server returned no data")
                    print("   2. LLM didn't include SEC info in report")
                    print("   3. MCP server is not configured correctly")
            else:
                print("⚠️ MCP URL not configured - MCP was skipped")
        else:
            print(f"✅ {ticker} is a non-US ticker (Thai/Singapore/etc.)")
            print("✅ MCP correctly skipped (SEC EDGAR only works for US tickers)")
            print("   This is expected behavior - no action needed")
        
        print("=" * 80)
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Error generating report: {e}", exc_info=True)
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate report and output full text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report for DBS19 (Thai ticker - MCP will be skipped)
  python scripts/generate_report_output.py DBS19

  # Generate report for AAPL (US ticker - MCP will be used if configured)
  python scripts/generate_report_output.py AAPL --mcp-url http://localhost:8000/mcp

  # Use multi-stage strategy
  python scripts/generate_report_output.py AAPL --strategy multi-stage
        """
    )
    parser.add_argument('ticker', help='Ticker symbol (e.g., DBS19 or AAPL)')
    parser.add_argument('--mcp-url', help='MCP server URL (default: from SEC_EDGAR_MCP_URL env var)')
    parser.add_argument(
        '--strategy',
        choices=['single-stage', 'multi-stage'],
        default='single-stage',
        help='Report generation strategy (default: single-stage)'
    )
    
    args = parser.parse_args()
    
    report = generate_and_print_report(
        ticker=args.ticker,
        mcp_url=args.mcp_url,
        strategy=args.strategy
    )
    
    if not report:
        sys.exit(1)


if __name__ == "__main__":
    main()
