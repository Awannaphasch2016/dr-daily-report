#!/usr/bin/env python3
"""
Generate PDF reports for all tickers and store in SQLite
"""

import sys
import os
import csv
import time
import sqlite3
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.agent import TickerAnalysisAgent


def save_pdf_to_archive(ticker, report_date, pdf_filename, db_path='webapp/data/ticker_reports.db'):
    """Save PDF filename to pdf_archive table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO pdf_archive
            (ticker, report_date, pdf_filename)
            VALUES (?, ?, ?)
        """, (ticker, report_date, pdf_filename))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to save to pdf_archive: {str(e)}")
        return False


def load_tickers(csv_path='data/tickers.csv'):
    """Load tickers from CSV file"""
    tickers = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Symbol'] and row['Ticker']:  # Skip empty rows
                tickers.append(row['Symbol'])
    return tickers


def generate_all_reports(output_dir='reports', delay_between_requests=2):
    """
    Generate PDF reports for all tickers and store in SQLite
    
    Args:
        output_dir: Directory to save PDF files
        delay_between_requests: Delay in seconds between ticker requests (to avoid rate limiting)
    """
    print("=" * 80)
    print("BATCH PDF REPORT GENERATION FOR ALL TICKERS")
    print("=" * 80)
    print()

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    print(f"📁 PDF reports will be saved to: {output_dir}/")
    print()

    # Load all tickers
    print("📋 Loading tickers from data/tickers.csv...")
    tickers = load_tickers()
    print(f"✅ Loaded {len(tickers)} tickers")
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
            print("   Or use Doppler:")
            print("   doppler run --project rag-chatbot-worktree --config dev_personal -- python3 generate_all_reports.py")
            return False
        raise
    print()

    # Statistics
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    # Process each ticker
    print("=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    print()

    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Run the graph to get full state (this automatically saves to SQLite)
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
                "audio_base64": "",
                "error": ""
            }

            final_state = agent.graph.invoke(initial_state)

            # Check for errors
            if final_state.get("error"):
                error_msg = final_state['error']
                print(f"   ⚠️  Error: {error_msg}")
                results['failed'].append((ticker, error_msg))
                
                # Rate limiting even on errors
                if i < len(tickers):
                    time.sleep(delay_between_requests)
                continue

            # Generate PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = os.path.join(output_dir, f"{ticker}_report_{timestamp}.pdf")
            pdf_filename_only = f"{ticker}_report_{timestamp}.pdf"

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

            # Get faithfulness score
            faithfulness_score = final_state.get("faithfulness_score")
            overall_score = faithfulness_score.overall_score if faithfulness_score else None

            print(f"   ✅ PDF generated: {output_filename} ({len(pdf_bytes)/1024:.1f} KB)")
            if overall_score:
                print(f"   📊 Faithfulness Score: {overall_score:.1f}/100")
            print(f"   💾 Report saved to SQLite database")

            # Save PDF filename to pdf_archive table
            report_date = datetime.now().strftime("%Y-%m-%d")
            if save_pdf_to_archive(ticker, report_date, pdf_filename_only):
                print(f"   📑 PDF indexed in archive database")

            results['success'].append({
                'ticker': ticker,
                'pdf_file': output_filename,
                'pdf_size': len(pdf_bytes),
                'faithfulness_score': overall_score
            })

            # Rate limiting - be nice to APIs
            if i < len(tickers):
                print(f"   ⏳ Waiting {delay_between_requests}s before next ticker...")
                time.sleep(delay_between_requests)
            print()

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
            results['failed'].append((ticker, str(e)))
            import traceback
            traceback.print_exc()
            print()
            
            # Rate limiting even on errors
            if i < len(tickers):
                time.sleep(delay_between_requests)

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"✅ Successfully processed: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"📊 Total: {len(tickers)}")
    print()

    if results['success']:
        print("✅ Successful Reports:")
        avg_faithfulness = sum(r['faithfulness_score'] for r in results['success'] if r['faithfulness_score']) / len([r for r in results['success'] if r['faithfulness_score']])
        print(f"   Average Faithfulness Score: {avg_faithfulness:.1f}/100")
        total_size = sum(r['pdf_size'] for r in results['success'])
        print(f"   Total PDF Size: {total_size/1024/1024:.1f} MB")
        print()

    if results['failed']:
        print("❌ Failed Tickers:")
        for ticker, error in results['failed']:
            print(f"   - {ticker}: {error}")
        print()

    print("💾 All reports have been saved to SQLite database:")
    print(f"   Database: data/ticker_data.db")
    print(f"   Table: reports")
    print()
    print("=" * 80)

    return len(results['success']) > 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate PDF reports for all tickers and store in SQLite"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to save PDF files (default: reports)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between ticker requests (default: 2.0)"
    )

    args = parser.parse_args()
    generate_all_reports(
        output_dir=args.output_dir,
        delay_between_requests=args.delay
    )
