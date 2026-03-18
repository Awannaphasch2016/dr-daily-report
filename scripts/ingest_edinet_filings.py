#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDINET Filings Ingestion Script

Fetches ALL corporate filings from the EDINET API (Japan FSA),
optionally matches them to DR tickers, downloads PDF documents to S3,
and stores everything in Aurora with full provenance tracking.

No pre-filtering: ALL filings are stored. Categorization/filtering
happens at query time by downstream services.

Usage:
    # Full ingestion (all filings + PDF downloads, last 365 days)
    ENV=dev doppler run -- python -m scripts.ingest_edinet_filings

    # Dry run (test API, no writes)
    ENV=dev doppler run -- python -m scripts.ingest_edinet_filings --dry-run --days-back 3

    # Metadata only (skip PDF downloads)
    ENV=dev doppler run -- python -m scripts.ingest_edinet_filings --skip-pdf-download

    # Specific date range
    ENV=dev doppler run -- python -m scripts.ingest_edinet_filings \
        --date-from 2026-01-01 --date-to 2026-03-15

Architecture:
    EDINET API (v2) -> this script -> Aurora edinet_filings table
                                    -> Aurora data_acquisitions table (provenance)
                                    -> S3 data lake (script artifact + PDF documents)
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Project imports (run from repo root with PYTHONPATH=.)
# ---------------------------------------------------------------------------
from src.data.aurora.data_acquisitions_repository import get_data_acquisitions_repository
from src.data.aurora.edinet_filings_repository import get_edinet_filings_repository
from src.data.aurora.ingestion_methods_repository import get_ingestion_methods_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

EDINET_API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
EDINET_DOCUMENTS_URL = f"{EDINET_API_BASE}/documents.json"

SCRIPT_SOURCE_NAME = "edinet_filings_ingester"

# EDINET secCode (5-digit) -> (yahoo_symbol, dr_symbol)
# Used for opportunistic ticker matching -- filings that don't match are still stored.
EDINET_SEC_CODE_MAP = {
    "79740": ("7974.T", "NINTENDO19"),
    "83160": ("8316.T", "SMFG19"),
    "70110": ("7011.T", "MITSU19"),
    "72670": ("7267.T", "HONDA19"),
    "83060": ("8306.T", "MUFG19"),
    "80010": ("8001.T", "ITOCHU19"),
    "68570": ("6857.T", "ADVANT19"),
}


# ===========================================================================
# API Fetching
# ===========================================================================

def fetch_filings_for_date(
    session: requests.Session,
    api_key: str,
    target_date: str,
    max_retries: int = 3,
) -> Optional[dict]:
    """Fetch all filings for a single date from EDINET.

    Args:
        session: requests.Session
        api_key: EDINET Subscription-Key
        target_date: Date string (YYYY-MM-DD)
        max_retries: Number of retry attempts

    Returns:
        Parsed JSON response, or None if all retries exhausted
    """
    params = {
        "date": target_date,
        "type": "2",
        "Subscription-Key": api_key,
    }

    for attempt in range(max_retries):
        try:
            resp = session.get(
                EDINET_DOCUMENTS_URL,
                params=params,
                timeout=30,
            )

            if resp.status_code == 200:
                return resp.json()

            logger.warning(
                f"EDINET fetch HTTP {resp.status_code} (attempt {attempt + 1}/{max_retries}), "
                f"date={target_date}"
            )

            if resp.status_code == 429:
                wait = 30
                logger.warning(f"Rate limited, waiting {wait}s")
                time.sleep(wait)
            else:
                time.sleep((attempt + 1) * 5)

        except requests.RequestException as e:
            logger.warning(f"EDINET fetch error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep((attempt + 1) * 5)

    logger.error(f"All retries exhausted for date={target_date}")
    return None


def fetch_all_filings(
    session: requests.Session,
    api_key: str,
    date_from: date,
    date_to: date,
    delay: float = 3.0,
) -> Tuple[List[dict], int]:
    """Fetch filings for a date range from EDINET.

    Iterates one day at a time (EDINET's API model).

    Returns:
        (list_of_filing_items, total_days_fetched)
    """
    all_items = []
    current = date_from
    days_fetched = 0
    days_with_data = 0

    total_days = (date_to - date_from).days + 1
    logger.info(f"Fetching EDINET filings for {total_days} days: {date_from} to {date_to}")

    while current <= date_to:
        date_str = current.isoformat()
        data = fetch_filings_for_date(session, api_key, date_str)

        if data is not None:
            results = data.get("results", [])
            if results:
                all_items.extend(results)
                days_with_data += 1
            days_fetched += 1

            if days_fetched % 30 == 0:
                logger.info(
                    f"Progress: {days_fetched}/{total_days} days fetched, "
                    f"{len(all_items)} filings so far"
                )
        else:
            logger.warning(f"Failed to fetch date={date_str}, continuing to next date")

        current += timedelta(days=1)

        if current <= date_to and delay > 0:
            time.sleep(delay)

    logger.info(
        f"Fetch complete: {days_fetched} days fetched, {days_with_data} had data, "
        f"{len(all_items)} total filings"
    )
    return all_items, days_fetched


# ===========================================================================
# Transform to Filing Dicts (ALL filings, no filtering)
# ===========================================================================

def transform_to_filings(
    items: List[dict],
    api_key: str,
) -> List[Dict[str, Any]]:
    """Transform ALL EDINET API items to edinet_filings dict format.

    No filtering -- every item becomes a filing. ticker_id and symbol
    are set to None; populated later by try_match_tickers().
    """
    filings = []
    for item in items:
        doc_id = item.get("docID")
        if not doc_id:
            logger.warning(f"Skipping item with no docID: {item.get('seqNumber')}")
            continue

        filing_date = item.get("filingDate") or (item.get("submitDateTime") or "")[:10]
        if not filing_date:
            logger.warning(f"Skipping item with no date: doc_id={doc_id}")
            continue

        pdf_flag = item.get("pdfFlag") == "1"
        pdf_url = None
        if pdf_flag:
            pdf_url = f"{EDINET_API_BASE}/documents/{doc_id}?type=2&Subscription-Key={api_key}"

        filing = {
            'ticker_id': None,
            'symbol': None,
            'doc_id': doc_id,
            'edinet_code': item.get('edinetCode'),
            'sec_code': item.get('secCode'),
            'filing_date': filing_date,
            'submit_date_time': item.get('submitDateTime'),
            'doc_type_code': item.get('docTypeCode'),
            'doc_description': item.get('docDescription'),
            'filer_name': item.get('filerName'),
            'title': item.get('docDescription') or 'Untitled',
            'period_start': item.get('periodStart'),
            'period_end': item.get('periodEnd'),
            'xbrl_flag': item.get('xbrlFlag') == "1",
            'pdf_flag': pdf_flag,
            'english_doc_flag': item.get('englishDocFlag') == "1",
            'pdf_url': pdf_url,
            'pdf_s3_key': None,
            'raw_data': item,
        }
        filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings from {len(items)} items")
    return filings


# ===========================================================================
# Opportunistic Ticker Matching
# ===========================================================================

def try_match_tickers(filings: List[Dict[str, Any]], resolver) -> int:
    """Opportunistically match filings to DR tickers via secCode.

    For each filing, check if its sec_code is in EDINET_SEC_CODE_MAP.
    If matched: resolve via TickerResolver, set ticker_id + symbol.
    If not matched: leave both as None (filing is still stored).

    Args:
        filings: List of filing dicts (modified in-place)
        resolver: TickerResolver instance

    Returns:
        Number of filings matched to DR tickers
    """
    matched_count = 0

    for filing in filings:
        sec_code = filing.get('sec_code')
        if not sec_code:
            continue

        match = EDINET_SEC_CODE_MAP.get(sec_code)
        if match is None:
            continue

        yahoo_symbol, dr_symbol = match

        ticker_info = resolver.resolve(yahoo_symbol)
        if ticker_info is None:
            logger.warning(f"TickerResolver cannot resolve {yahoo_symbol} for secCode={sec_code}")
            continue

        filing['ticker_id'] = ticker_info.ticker_id
        filing['symbol'] = dr_symbol
        matched_count += 1

    logger.info(
        f"Ticker matching: {matched_count} filings matched to DR tickers "
        f"out of {len(filings)} total"
    )
    return matched_count


# ===========================================================================
# PDF Document Download to S3
# ===========================================================================

def download_pdfs(
    filings: List[Dict[str, Any]],
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 2.0,
) -> int:
    """Download PDF documents from EDINET and archive to S3.

    For each filing with pdf_flag=True, downloads the PDF and uploads
    it to S3 under edinet-filings/documents/{doc_id}/{doc_id}.pdf.

    Failures are logged but don't fail the whole run.

    Args:
        filings: List of filing dicts (modified in-place to set pdf_s3_key)
        data_lake: DataLakeStorage instance for S3 access
        session: requests.Session for downloading
        delay: Seconds to wait between downloads (rate limiting)

    Returns:
        Number of PDFs successfully archived
    """
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping PDF downloads")
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    filings_with_pdf = [f for f in filings if f.get('pdf_flag') and f.get('pdf_url')]
    logger.info(f"Downloading {len(filings_with_pdf)} PDF documents to S3...")

    for i, filing in enumerate(filings_with_pdf):
        doc_id = filing['doc_id']
        s3_key = f"edinet-filings/documents/{doc_id}/{doc_id}.pdf"

        try:
            # Check if already archived (idempotent)
            try:
                data_lake.s3_client.head_object(
                    Bucket=data_lake.bucket_name,
                    Key=s3_key,
                )
                filing['pdf_s3_key'] = s3_key
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass  # Not found, proceed to download

            # Download PDF from EDINET
            resp = session.get(filing['pdf_url'], timeout=60)
            if resp.status_code != 200:
                logger.warning(
                    f"PDF download failed HTTP {resp.status_code}: doc_id={doc_id}"
                )
                failed_count += 1
                continue

            content = resp.content
            content_type = resp.headers.get('Content-Type', 'application/pdf')

            # Upload to S3
            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'doc_id': doc_id,
                    'edinet_code': filing.get('edinet_code') or '',
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=edinet&purpose=filing-archive",
            )

            filing['pdf_s3_key'] = s3_key
            archived_count += 1

            if (i + 1) % 50 == 0:
                logger.info(
                    f"PDF progress: {i + 1}/{len(filings_with_pdf)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"PDF archive failed for doc_id={doc_id}: {e}")
            failed_count += 1

        # Rate limit between downloads
        if delay > 0 and i < len(filings_with_pdf) - 1:
            time.sleep(delay)

    logger.info(
        f"PDF download complete: "
        f"archived={archived_count}, skipped={skipped_count}, failed={failed_count}"
    )
    return archived_count


# ===========================================================================
# PDF-Only Mode: Download from Aurora metadata
# ===========================================================================

def download_pdfs_from_aurora(
    data_lake: DataLakeStorage,
    session: requests.Session,
    api_key: str,
    delay: float = 2.0,
) -> int:
    """Download PDFs for filings already in Aurora that don't have pdf_s3_key yet.

    Reads from Aurora (not API), downloads PDFs, updates pdf_s3_key.

    Returns:
        Number of PDFs successfully archived
    """
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping PDF downloads")
        return 0

    repo = get_edinet_filings_repository()
    filings = repo.get_filings_needing_pdfs()
    logger.info(f"Found {len(filings)} filings needing PDF download")

    if not filings:
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    for i, filing in enumerate(filings):
        doc_id = filing['doc_id']
        s3_key = f"edinet-filings/documents/{doc_id}/{doc_id}.pdf"
        pdf_url = filing.get('pdf_url')

        if not pdf_url:
            # Construct URL if not stored
            pdf_url = f"{EDINET_API_BASE}/documents/{doc_id}?type=2&Subscription-Key={api_key}"

        try:
            # Check if already in S3 (idempotent)
            try:
                data_lake.s3_client.head_object(
                    Bucket=data_lake.bucket_name,
                    Key=s3_key,
                )
                repo.update_pdf_s3_key(doc_id, s3_key)
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            resp = session.get(pdf_url, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"PDF download failed HTTP {resp.status_code}: doc_id={doc_id}")
                failed_count += 1
                continue

            content = resp.content
            content_type = resp.headers.get('Content-Type', 'application/pdf')

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'doc_id': doc_id,
                    'edinet_code': filing.get('edinet_code') or '',
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=edinet&purpose=filing-archive",
            )

            repo.update_pdf_s3_key(doc_id, s3_key)
            archived_count += 1

            if (i + 1) % 50 == 0:
                logger.info(
                    f"PDF progress: {i + 1}/{len(filings)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"PDF archive failed for doc_id={doc_id}: {e}")
            failed_count += 1

        if delay > 0 and i < len(filings) - 1:
            time.sleep(delay)

    logger.info(
        f"PDF download complete: "
        f"archived={archived_count}, skipped={skipped_count}, failed={failed_count}"
    )
    return archived_count


# ===========================================================================
# Runtime Detection
# ===========================================================================

def _detect_runtime_type() -> str:
    """Auto-detect the runtime environment."""
    if os.environ.get('ECS_CONTAINER_METADATA_URI'):
        return 'ecs_fargate'
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return 'lambda'
    if os.environ.get('GITHUB_ACTIONS'):
        return 'github_actions'
    return 'local'


# ===========================================================================
# S3 Self-Archive
# ===========================================================================

def self_archive_to_s3(data_lake: DataLakeStorage, version: str) -> Tuple[str, str]:
    """Upload this script to S3 for provenance tracking.

    Returns:
        (s3_key, sha256_hex)
    """
    script_path = Path(__file__)
    content = script_path.read_bytes()
    sha256_hex = hashlib.sha256(content).hexdigest()

    s3_key = f"scripts/data-acquisition/edinet-filings/{version}.py"

    data_lake.s3_client.put_object(
        Bucket=data_lake.bucket_name,
        Key=s3_key,
        Body=content,
        ContentType='text/x-python',
        Metadata={
            'sha256': sha256_hex,
            'source_file': script_path.name,
            'archived_at': datetime.now(timezone.utc).isoformat(),
        },
        Tagging="type=script&purpose=data-acquisition&target=edinet_filings",
    )

    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key} (sha256={sha256_hex[:12]}...)")
    return s3_key, sha256_hex


# ===========================================================================
# Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest EDINET (Japan FSA) filings into Aurora"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Fetch and transform but do not write to Aurora or S3',
    )
    parser.add_argument(
        '--days-back', type=int, default=365,
        help='Number of days to look back (default: 365)',
    )
    parser.add_argument(
        '--date-from', type=str, default=None,
        help='Explicit start date YYYY-MM-DD (overrides --days-back)',
    )
    parser.add_argument(
        '--date-to', type=str, default=None,
        help='Explicit end date YYYY-MM-DD (default: today)',
    )
    parser.add_argument(
        '--delay', type=float, default=3.0,
        help='Delay between date API calls in seconds (default: 3.0)',
    )
    parser.add_argument(
        '--version', type=str, default='v1',
        help='Script version tag for provenance (default: v1)',
    )
    parser.add_argument(
        '--skip-self-archive', action='store_true',
        help='Skip uploading script to S3',
    )
    parser.add_argument(
        '--skip-pdf-download', action='store_true',
        help='Skip downloading PDF documents to S3',
    )
    parser.add_argument(
        '--pdf-only', action='store_true',
        help='PDF-only mode: query Aurora for filings needing PDFs, skip API fetch',
    )
    parser.add_argument(
        '--pdf-delay', type=float, default=2.0,
        help='Delay between PDF downloads in seconds (default: 2.0)',
    )
    parser.add_argument(
        '--runtime-type', type=str, default=None,
        help='Runtime type for ingestion_methods (auto-detected if not set)',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable debug logging',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Resolve date range
    date_to = date.fromisoformat(args.date_to) if args.date_to else date.today()
    if args.date_from:
        date_from = date.fromisoformat(args.date_from)
    else:
        date_from = date_to - timedelta(days=args.days_back)

    mode = "pdf-only" if args.pdf_only else "full"
    logger.info("=" * 60)
    logger.info(f"EDINET Filings Ingestion (mode={mode})")
    if not args.pdf_only:
        logger.info(f"  dry_run={args.dry_run}, date_range={date_from} to {date_to}")
        logger.info(f"  skip_pdf_download={args.skip_pdf_download}, version={args.version}")
    else:
        logger.info(f"  PDF-only: downloading PDFs for filings already in Aurora")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 0. PDF-only mode (skip everything, just download PDFs from Aurora)
    # ------------------------------------------------------------------
    if args.pdf_only:
        api_key = os.environ.get('EDINET_API_KEY', '')
        if not api_key:
            logger.error("EDINET_API_KEY required for PDF downloads")
            sys.exit(1)

        data_lake = DataLakeStorage()
        if not data_lake.enabled:
            logger.error("DATA_LAKE_BUCKET not configured")
            sys.exit(1)

        session = requests.Session()
        pdfs_archived = download_pdfs_from_aurora(
            data_lake, session, api_key, delay=args.pdf_delay
        )

        logger.info("=" * 60)
        logger.info(f"PDF-ONLY COMPLETE: {pdfs_archived} PDFs archived to S3")
        logger.info("=" * 60)
        return

    # ------------------------------------------------------------------
    # 1. Read API key
    # ------------------------------------------------------------------
    api_key = os.environ.get('EDINET_API_KEY')
    if not api_key and not args.dry_run:
        logger.error("EDINET_API_KEY not set. Register at https://disclosure2dl.edinet-fsa.go.jp/")
        sys.exit(1)
    if not api_key:
        logger.warning("EDINET_API_KEY not set, dry-run will show empty results")
        api_key = ""

    # ------------------------------------------------------------------
    # 2. S3 self-archive (provenance)
    # ------------------------------------------------------------------
    artifact_s3_key = None
    artifact_checksum = None
    data_lake = None

    if not args.dry_run and not args.skip_self_archive:
        try:
            data_lake = DataLakeStorage()
            if data_lake.enabled:
                artifact_s3_key, artifact_checksum = self_archive_to_s3(
                    data_lake, args.version
                )
            else:
                logger.warning("Data lake not configured, skipping self-archive")
        except Exception as e:
            logger.warning(f"Self-archive failed (non-fatal): {e}")

    # ------------------------------------------------------------------
    # 3. Register ingestion method + start acquisition run
    # ------------------------------------------------------------------
    acq_repo = get_data_acquisitions_repository()
    acq_id = None
    ingestion_method_id = None

    if not args.dry_run:
        # Register ingestion method for provenance
        runtime_type = args.runtime_type or _detect_runtime_type()
        method_name = f"edinet-{runtime_type}-{args.version}"
        try:
            methods_repo = get_ingestion_methods_repository()
            method = methods_repo.get_or_create(
                method_name=method_name,
                runtime_type=runtime_type,
                script_path='scripts/ingest_edinet_filings.py',
                container_image=os.environ.get('CONTAINER_IMAGE'),
                description=f"EDINET filings ingestion via {runtime_type}",
            )
            ingestion_method_id = method['id']
            logger.info(f"Ingestion method: {method_name} (id={ingestion_method_id})")
        except Exception as e:
            logger.warning(f"Ingestion method registration failed (non-fatal): {e}")

        acq_id = acq_repo.start_run(
            source_table='edinet_filings',
            source_type='script',
            source_name=SCRIPT_SOURCE_NAME,
            source_version=args.version,
            artifact_s3_key=artifact_s3_key,
            artifact_checksum=artifact_checksum,
            endpoint_url=EDINET_DOCUMENTS_URL,
            endpoint_version='v2',
            description=f"EDINET filings ingestion ({date_from} to {date_to})",
            parameters={
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'delay': args.delay,
                'skip_pdf_download': args.skip_pdf_download,
            },
            ingestion_method_id=ingestion_method_id,
        )
        logger.info(f"Started acquisition run: id={acq_id}")

    records_fetched = 0
    records_upserted = 0
    matched_count = 0
    pdfs_archived = 0

    try:
        # ------------------------------------------------------------------
        # 4. Fetch filings for date range
        # ------------------------------------------------------------------
        session = requests.Session()

        if api_key:
            logger.info("Fetching EDINET filings...")
            all_items, days_fetched = fetch_all_filings(
                session, api_key,
                date_from=date_from,
                date_to=date_to,
                delay=args.delay,
            )
            records_fetched = len(all_items)
            logger.info(f"Fetched {records_fetched} filings from {days_fetched} days")
        else:
            all_items = []
            records_fetched = 0

        # ------------------------------------------------------------------
        # 5. Transform ALL items to filing dicts (no filtering)
        # ------------------------------------------------------------------
        filings = transform_to_filings(all_items, api_key)

        # ------------------------------------------------------------------
        # 6. Opportunistic ticker matching
        # ------------------------------------------------------------------
        logger.info("Attempting opportunistic DR ticker matching...")
        resolver = get_ticker_resolver()
        matched_count = try_match_tickers(filings, resolver)

        # ------------------------------------------------------------------
        # 7. Download PDFs to S3
        # ------------------------------------------------------------------
        if not args.dry_run and not args.skip_pdf_download:
            if data_lake is None:
                data_lake = DataLakeStorage()
            if data_lake.enabled:
                pdfs_archived = download_pdfs(
                    filings, data_lake, session,
                    delay=args.pdf_delay,
                )
            else:
                logger.warning("Data lake not configured, skipping PDF downloads")

        # ------------------------------------------------------------------
        # 8. Dry run summary or upsert
        # ------------------------------------------------------------------
        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN -- No data written")
            logger.info(f"  Total filings fetched:    {records_fetched}")
            logger.info(f"  Filings to upsert:        {len(filings)}")
            logger.info(f"  Matched to DR tickers:    {matched_count}")
            logger.info(f"  Unmatched (still stored):  {len(filings) - matched_count}")
            logger.info("")
            for f in filings[:20]:
                symbol_str = f.get('symbol') or '(none)'
                logger.info(
                    f"  {symbol_str:14s} | {f['doc_id']:12s} | "
                    f"{f['filing_date']} | "
                    f"{f.get('doc_type_code') or '':5s} | "
                    f"{(f.get('filer_name') or '')[:30]:30s} | "
                    f"{(f.get('title') or '')[:30]}"
                )
            if len(filings) > 20:
                logger.info(f"  ... and {len(filings) - 20} more")
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=records_fetched, records_upserted=0)
            return

        filings_repo = get_edinet_filings_repository()
        records_upserted = filings_repo.batch_upsert(
            filings, acquisition_id=acq_id
        )
        logger.info(f"Batch upsert complete: {records_upserted} rows affected")

        # ------------------------------------------------------------------
        # 9. Complete acquisition
        # ------------------------------------------------------------------
        if acq_id:
            acq_repo.complete_run(
                acq_id,
                records_fetched=records_fetched,
                records_upserted=records_upserted,
                status='success',
            )
        logger.info("Acquisition complete: status=success")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        if acq_id:
            acq_repo.fail_run(
                acq_id,
                error_message=str(e),
                records_fetched=records_fetched,
                records_upserted=records_upserted,
            )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Date range:          {date_from} to {date_to}")
    logger.info(f"  Filings fetched:     {records_fetched}")
    logger.info(f"  Filings upserted:    {records_upserted}")
    logger.info(f"  DR ticker matches:   {matched_count}")
    logger.info(f"  PDFs archived:       {pdfs_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:      {acq_id}")
    if artifact_s3_key:
        logger.info(f"  Script artifact:     {artifact_s3_key}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
