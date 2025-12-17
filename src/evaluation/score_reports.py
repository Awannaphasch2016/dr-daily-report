#!/usr/bin/env python3
"""
Score Reports CLI Tool

⚠️  DEPRECATED: This script relies on SQLite database which has been removed.
    Evaluation data is now stored in Aurora MySQL.
    This script needs to be updated to use Aurora or removed.

Enables rescoring of historical reports using stored context data.
Useful for:
- Testing new scoring algorithms on historical data
- Batch rescoring after scoring logic changes
- Comparing scores across algorithm versions
"""

import argparse
import json
from typing import Optional
# from src.data.database import TickerDatabase  # REMOVED - SQLite deprecated
from src.scoring.scoring_service import ScoringService, ScoringContext


def rescore_report(ticker: str, date: str, verbose: bool = False) -> dict:
    """
    Rescore a single historical report using stored context.

    Args:
        ticker: Ticker symbol
        date: Report date (YYYY-MM-DD)
        verbose: Print detailed output

    Returns:
        Dictionary with all scores
    """
    # db = TickerDatabase()  # REMOVED - SQLite deprecated
    scoring_service = ScoringService()
    raise NotImplementedError("This function needs to be updated to use Aurora instead of SQLite")

    # Read report + context from database
    if verbose:
        print(f"📖 Reading report for {ticker} on {date}...")

    report_data = db.get_report_with_context(ticker, date)
    if not report_data:
        print(f"❌ No report found for {ticker} on {date}")
        return {}

    report_text = report_data['report_text']
    context_json = report_data['context_json']

    if not context_json:
        print(f"❌ No context data found for {ticker} on {date}")
        print(f"   (Report was generated before context storage was implemented)")
        return {}

    # Parse context
    if verbose:
        print(f"📊 Parsing context data...")

    context_dict = json.loads(context_json)
    context = ScoringContext.from_json(context_dict)

    # Recompute scores
    if verbose:
        print(f"🔄 Computing scores...")

    quality_scores = scoring_service.compute_all_quality_scores(report_text, context)

    # Save new scores
    if verbose:
        print(f"💾 Saving scores to database...")

    db.save_faithfulness_score(ticker, date, quality_scores['faithfulness'])
    db.save_completeness_score(ticker, date, quality_scores['completeness'])
    db.save_reasoning_quality_score(ticker, date, quality_scores['reasoning_quality'])
    db.save_compliance_score(ticker, date, quality_scores['compliance'])

    # Update score summary (keep qos/cost from original)
    db.save_score_summary(ticker, date, {
        'faithfulness': quality_scores['faithfulness'],
        'completeness': quality_scores['completeness'],
        'reasoning_quality': quality_scores['reasoning_quality'],
        'compliance': quality_scores['compliance'],
        'qos': None,  # Keep original
        'cost': None  # Keep original
    })

    print(f"✅ Rescored {ticker} on {date}")

    if verbose:
        print(f"\n📈 Score Summary:")
        print(f"   Faithfulness:       {quality_scores['faithfulness'].overall_score:.1f}/100")
        print(f"   Completeness:       {quality_scores['completeness'].overall_score:.1f}/100")
        print(f"   Reasoning Quality:  {quality_scores['reasoning_quality'].overall_score:.1f}/100")
        print(f"   Compliance:         {quality_scores['compliance'].overall_score:.1f}/100")

    return quality_scores


def batch_rescore(ticker: Optional[str] = None, days: int = 30, verbose: bool = False):
    """
    Batch rescore multiple reports.

    Args:
        ticker: Ticker symbol (None for all tickers)
        days: Number of days to look back
        verbose: Print detailed output
    """
    db = TickerDatabase()

    # Get reports to rescore
    print(f"🔍 Finding reports to rescore...")
    if ticker:
        print(f"   Ticker: {ticker}")
    else:
        print(f"   All tickers")
    print(f"   Days back: {days}")

    # Query reports (would need to implement this in database.py)
    # For now, just demonstrate with example
    print(f"\n⚠️  Note: Batch rescoring requires implementing db.get_reports() method")
    print(f"   For now, use single report rescoring with --ticker and --date")


def compare_scores(ticker: str, date: str):
    """
    Compare current scores with newly computed scores.

    Args:
        ticker: Ticker symbol
        date: Report date
    """
    db = TickerDatabase()

    # Get current scores from database
    print(f"📊 Comparing scores for {ticker} on {date}...")
    print(f"\n⚠️  Note: Score comparison requires implementing db.get_scores() method")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Rescore historical reports using stored context data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rescore single report
  python -m src.score_reports --ticker PFE --date 2025-10-31

  # Rescore with verbose output
  python -m src.score_reports --ticker PFE --date 2025-10-31 --verbose

  # Batch rescore all reports (future feature)
  python -m src.score_reports --batch --days 30

  # Compare old vs new scores
  python -m src.score_reports --ticker PFE --date 2025-10-31 --compare
        """
    )

    parser.add_argument(
        '--ticker',
        type=str,
        help='Ticker symbol (e.g., PFE, AAPL)'
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Report date in YYYY-MM-DD format'
    )

    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch rescore multiple reports'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (for batch mode)'
    )

    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare old vs new scores'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print detailed output'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.compare:
        if not args.ticker or not args.date:
            parser.error("--compare requires --ticker and --date")
        compare_scores(args.ticker, args.date)

    elif args.batch:
        batch_rescore(args.ticker, args.days, args.verbose)

    else:
        if not args.ticker or not args.date:
            parser.error("Single report rescoring requires --ticker and --date")
        rescore_report(args.ticker, args.date, args.verbose)


if __name__ == '__main__':
    main()
