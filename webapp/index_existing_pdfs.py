#!/usr/bin/env python3
"""
Migration script to index existing PDF reports into pdf_archive table
Scans /reports directory and populates the database
"""

import os
import sys
import sqlite3
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_pdf_filename(filename):
    """
    Parse PDF filename to extract ticker and date
    Expected format: {TICKER}_report_{YYYYMMDD_HHMMSS}.pdf
    Example: DBS19_report_20251101_180300.pdf
    """
    pattern = r'^([A-Z0-9]+)_report_(\d{8})_(\d{6})\.pdf$'
    match = re.match(pattern, filename)

    if not match:
        return None

    ticker = match.group(1)
    date_str = match.group(2)  # YYYYMMDD
    time_str = match.group(3)  # HHMMSS

    # Convert to standard date format YYYY-MM-DD
    try:
        report_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        return {
            'ticker': ticker,
            'report_date': report_date,
            'filename': filename
        }
    except ValueError:
        return None


def index_pdfs(reports_dir='../reports', db_path='data/ticker_reports.db'):
    """Index all PDF files from reports directory into database"""

    # Get absolute paths
    script_dir = Path(__file__).parent
    reports_path = (script_dir / reports_dir).resolve()
    db_file = (script_dir / db_path).resolve()

    if not reports_path.exists():
        print(f"❌ Reports directory not found: {reports_path}")
        return False

    # Find all PDF files
    pdf_files = list(reports_path.glob('*.pdf'))

    if not pdf_files:
        print(f"❌ No PDF files found in {reports_path}")
        return False

    print(f"Found {len(pdf_files)} PDF files in {reports_path}")
    print(f"Database: {db_file}")
    print("=" * 80)

    # Connect to database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    indexed_count = 0
    skipped_count = 0
    error_count = 0

    for pdf_file in sorted(pdf_files):
        filename = pdf_file.name

        # Parse filename
        parsed = parse_pdf_filename(filename)

        if not parsed:
            print(f"⚠️  Skipped (invalid format): {filename}")
            skipped_count += 1
            continue

        try:
            # Insert into database
            cursor.execute("""
                INSERT OR REPLACE INTO pdf_archive
                (ticker, report_date, pdf_filename)
                VALUES (?, ?, ?)
            """, (
                parsed['ticker'],
                parsed['report_date'],
                parsed['filename']
            ))

            print(f"✅ Indexed: {parsed['ticker']:15s} | {parsed['report_date']} | {filename}")
            indexed_count += 1

        except sqlite3.Error as e:
            print(f"❌ Error indexing {filename}: {str(e)}")
            error_count += 1

    # Commit changes
    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"✅ Successfully indexed: {indexed_count} PDFs")
    if skipped_count > 0:
        print(f"⚠️  Skipped (invalid format): {skipped_count} PDFs")
    if error_count > 0:
        print(f"❌ Errors: {error_count} PDFs")

    return indexed_count > 0


def verify_index(db_path='data/ticker_reports.db'):
    """Verify indexed PDFs in database"""
    script_dir = Path(__file__).parent
    db_file = (script_dir / db_path).resolve()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pdf_archive")
    count = cursor.fetchone()[0]

    print(f"\n📊 Database contains {count} indexed PDFs")

    if count > 0:
        print("\nSample records:")
        cursor.execute("""
            SELECT ticker, report_date, pdf_filename
            FROM pdf_archive
            ORDER BY report_date DESC, ticker ASC
            LIMIT 5
        """)

        for row in cursor.fetchall():
            print(f"  {row[0]:15s} | {row[1]} | {row[2]}")

    conn.close()


if __name__ == "__main__":
    print("PDF Archive Indexer")
    print("=" * 80)

    success = index_pdfs()

    if success:
        verify_index()
        print("\n✅ Migration complete!")
        print("   You can now run the webapp: python webapp/app.py")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
