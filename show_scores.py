#!/usr/bin/env python3
"""
Generate report for DBS19 and show both completeness and faithfulness scores
"""

import sys
import os
import subprocess

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load environment variables from Doppler
def load_doppler_env():
    """Load environment variables from Doppler"""
    try:
        # Use doppler secrets download with env format
        result = subprocess.run(
            ['doppler', '--project', 'rag-chatbot-worktree', '--config', 'dev_personal', 'secrets', 'download', '--no-file', '--format', 'env'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            # Parse env format (KEY=value)
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
            print("✅ Loaded environment variables from Doppler")
            return True
        else:
            print(f"⚠️  Doppler command failed: {result.stderr}")
            # Try alternative: use doppler run with env command
            print("⚠️  Trying alternative method...")
            return False
    except FileNotFoundError:
        print("⚠️  Doppler CLI not found. Trying to use existing environment variables...")
        return False
    except Exception as e:
        print(f"⚠️  Error loading Doppler env: {str(e)}")
        return False

# Load Doppler environment variables
load_doppler_env()

from src.agent import TickerAnalysisAgent


def show_scores_for_ticker(ticker: str = "DBS19"):
    """Generate report and show both scores"""
    print("=" * 80)
    print(f"GENERATING REPORT AND SCORES FOR {ticker}")
    print("=" * 80)
    print()

    # Initialize agent
    print("🔄 Initializing agent...")
    try:
        agent = TickerAnalysisAgent()
        print("✅ Agent initialized")
    except Exception as e:
        if "api_key" in str(e).lower() or "OPENAI_API_KEY" in str(e):
            print("❌ Error: OPENAI_API_KEY environment variable is not set")
            print("   Please set it before running this script:")
            print("   export OPENAI_API_KEY='your-api-key-here'")
            return False
        raise
    print()

    # Run analysis
    print(f"📊 Running analysis for {ticker}...")
    print("⏳ Please wait... (this may take 10-15 seconds)")
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
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "error": ""
        }

        final_state = agent.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            print(f"❌ Error: {final_state['error']}")
            return False

        # Get scores
        faithfulness_score = final_state.get("faithfulness_score")
        completeness_score = final_state.get("completeness_score")
        reasoning_quality_score = final_state.get("reasoning_quality_score")

        # Print report (first 500 chars)
        report = final_state.get("report", "")
        if report:
            print("=" * 80)
            print("GENERATED REPORT (Preview)")
            print("=" * 80)
            print(report[:500] + "..." if len(report) > 500 else report)
            print()

        # Print faithfulness score
        if faithfulness_score:
            print("=" * 80)
            print("FAITHFULNESS SCORE")
            print("=" * 80)
            print()
            print(agent.faithfulness_scorer.format_score_report(faithfulness_score))
            print()
        else:
            print("⚠️  No faithfulness score found")

        # Print completeness score
        if completeness_score:
            print("=" * 80)
            print("COMPLETENESS SCORE")
            print("=" * 80)
            print()
            print(agent.completeness_scorer.format_score_report(completeness_score))
            print()
        else:
            print("⚠️  No completeness score found")

        # Print overall quality score
        if faithfulness_score and completeness_score:
            overall_quality = (
                faithfulness_score.overall_score * 0.8 +
                completeness_score.overall_score * 0.2
            )
            print("=" * 80)
            print("OVERALL QUALITY SCORE")
            print("=" * 80)
            print()
            print(f"📊 Overall Quality Score: {overall_quality:.1f}/100")
            print(f"   (Faithfulness: {faithfulness_score.overall_score:.1f}/100 × 0.8)")
            print(f"   (Completeness: {completeness_score.overall_score:.1f}/100 × 0.2)")
            print()

        print("=" * 80)
        print("✅ Process completed successfully!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"❌ Report generation failed!")
        print(f"   Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate report and show scores")
    parser.add_argument(
        "--ticker",
        type=str,
        default="DBS19",
        help="Ticker symbol to analyze (default: DBS19)"
    )

    args = parser.parse_args()
    show_scores_for_ticker(args.ticker)
