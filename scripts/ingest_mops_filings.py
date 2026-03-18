#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOPS Filings Ingestion Script

Fetches annual reports and quarterly financial statements from Taiwan's
MOPS (Market Observation Post System) for tracked TWSE tickers, matches
to DR tickers, optionally downloads PDF documents to S3, and stores
everything in Aurora.

Usage:
    ENV=dev doppler run -- python -m scripts.ingest_mops_filings --dry-run --years-back 1
    ENV=dev doppler run -- python -m scripts.ingest_mops_filings --skip-doc-download --years-back 3
    ENV=dev doppler run -- python -m scripts.ingest_mops_filings --doc-only

Architecture:
    MOPS (doc.twse.com.tw) -> this script -> Aurora mops_filings table
                                            -> Aurora data_acquisitions (provenance)
                                            -> S3 data lake (documents)

MOPS 3-step PDF download flow:
    1. POST step=1 -> HTML listing with filenames
    2. POST step=9 with filename -> timestamped download path
    3. GET /pdf/{timestamped}.pdf -> binary PDF
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.data.aurora.data_acquisitions_repository import get_data_acquisitions_repository
from src.data.aurora.mops_filings_repository import get_mops_filings_repository
from src.data.aurora.ingestion_methods_repository import get_ingestion_methods_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

MOPS_TWSE_BASE = "https://doc.twse.com.tw"
MOPS_TWSE_URL = f"{MOPS_TWSE_BASE}/server-java/t57sb01"

SCRIPT_SOURCE_NAME = "mops_filings_ingester"

# TWSE stock code (4-digit) -> (yahoo_symbol, dr_symbol)
# Note: 0050 (Taiwan 50 ETF) does NOT publish annual reports or IFRS statements
# on MOPS — ETFs have different disclosure rules. Only add companies here.
MOPS_TICKER_MAP = {
    # "0050": ("0050.TW", "TAIWAN19"),  # ETF — no MOPS filings available
    # Add Taiwan-listed companies here when tracked, e.g.:
    # "2330": ("2330.TW", "TSMC19"),
}

TARGET_CODES = list(MOPS_TICKER_MAP.keys())

# Document types to fetch from MOPS
DOCUMENT_TYPES = [
    # Annual Reports (股東會年報)
    {"mtype": "F", "dtype": "F04", "report_type": "annual_report", "report_period": "annual",
     "label": "Annual Report"},
    # IFRS Consolidated Financial Statements - Q1
    {"mtype": "A", "dtype": "AI1", "report_type": "financial_statement", "report_period": "Q1",
     "label": "Q1 Financial Statement"},
    # IFRS Consolidated Financial Statements - Q3
    {"mtype": "A", "dtype": "AI2", "report_type": "financial_statement", "report_period": "Q3",
     "label": "Q3 Financial Statement"},
    # IFRS Consolidated Financial Statements - Annual
    {"mtype": "A", "dtype": "AI3", "report_type": "financial_statement", "report_period": "annual",
     "label": "Annual Financial Statement"},
]


# ===========================================================================
# ROC Calendar
# ===========================================================================

def western_to_roc(year: int) -> int:
    """Convert Western calendar year to ROC year (民國). 2024 -> 113."""
    return year - 1911


def roc_to_western(roc_year: int) -> int:
    """Convert ROC year to Western calendar year. 113 -> 2024."""
    return roc_year + 1911


# ===========================================================================
# MOPS API: Fetch Listings
# ===========================================================================

def _parse_listing_html(html_content: str, stock_code: str) -> List[str]:
    """Parse MOPS step=1 HTML response to extract filenames.

    MOPS returns HTML with links containing filenames like:
    - 202312_0050_AI3.pdf (financial statements)
    - 2022_0050_20230606F04.pdf (annual reports)

    Uses regex to extract filenames from anchor tags.
    """
    if not html_content or len(html_content) < 50:
        return []

    # Look for filenames in the HTML (various patterns)
    # Pattern 1: filename in onclick or href attributes
    filenames = re.findall(r'([A-Za-z0-9_\-]+\.pdf)', html_content)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for f in filenames:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique


def fetch_listing_for_stock(
    session: requests.Session,
    stock_code: str,
    roc_year: int,
    doc_type: Dict[str, str],
    delay: float = 2.0,
) -> List[Dict[str, Any]]:
    """Fetch MOPS listing for a stock/year/document-type combo.

    POST step=1 to get HTML listing of available filenames.

    Returns:
        List of filing dicts with filename and metadata.
    """
    mtype = doc_type['mtype']
    dtype = doc_type['dtype']
    western_year = roc_to_western(roc_year)

    data = {
        'id': '',
        'key': '',
        'step': '1',
        'co_id': stock_code,
        'year': str(roc_year),
        'seession': '',  # Note: MOPS has a typo in their form field name
        'mtype': mtype,
        'dtype': dtype,
    }

    try:
        resp = session.post(MOPS_TWSE_URL, data=data, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                f"MOPS HTTP {resp.status_code} for {stock_code} "
                f"year={western_year} {doc_type['label']}"
            )
            return []

        filenames = _parse_listing_html(resp.text, stock_code)

        listings = []
        for filename in filenames:
            filing_date = _derive_filing_date(western_year, doc_type['report_period'])
            listings.append({
                'filename': filename,
                'stock_code': stock_code,
                'report_year': western_year,
                'report_type': doc_type['report_type'],
                'report_period': doc_type['report_period'],
                'mtype': mtype,
                'dtype': dtype,
                'filing_date': filing_date,
                'raw_data': {
                    'roc_year': roc_year,
                    'western_year': western_year,
                    'mtype': mtype,
                    'dtype': dtype,
                    'html_length': len(resp.text),
                    'filenames_found': len(filenames),
                },
            })

        return listings

    except Exception as e:
        logger.warning(
            f"MOPS fetch failed for {stock_code} year={western_year} "
            f"{doc_type['label']}: {e}"
        )
        return []


def _derive_filing_date(year: int, period: str) -> Optional[str]:
    """Derive approximate filing date from report year and period."""
    period_dates = {
        'Q1': f"{year}-03-31",
        'Q2': f"{year}-06-30",
        'Q3': f"{year}-09-30",
        'annual': f"{year}-12-31",
    }
    return period_dates.get(period)


def fetch_all_filings(
    session: requests.Session,
    stock_codes: List[str],
    years: List[int],
    doc_types: List[Dict[str, str]],
    delay: float = 2.0,
) -> List[Dict[str, Any]]:
    """Fetch filings for all stocks, years, and document types.

    Iterates: stocks × years × doc_types
    """
    all_filings = []
    total_combos = len(stock_codes) * len(years) * len(doc_types)
    combo_num = 0

    for code in stock_codes:
        company_info = MOPS_TICKER_MAP.get(code, ("", ""))
        stock_filings = 0

        for year in years:
            roc_year = western_to_roc(year)

            for doc_type in doc_types:
                combo_num += 1
                logger.debug(
                    f"[{combo_num}/{total_combos}] {code} {year} {doc_type['label']}"
                )

                listings = fetch_listing_for_stock(
                    session, code, roc_year, doc_type, delay=delay
                )
                all_filings.extend(listings)
                stock_filings += len(listings)

                if delay > 0:
                    time.sleep(delay)

        logger.info(f"  {code} ({company_info[1]}): {stock_filings} filings")

    logger.info(
        f"Fetched {len(all_filings)} filings from "
        f"{len(stock_codes)} companies × {len(years)} years"
    )
    return all_filings


# ===========================================================================
# Ticker Matching
# ===========================================================================

def try_match_tickers(filings: List[Dict[str, Any]], resolver) -> int:
    """Match filings to DR tickers via stock_code."""
    matched_count = 0

    for filing in filings:
        code = filing.get('stock_code')
        if not code:
            continue

        match = MOPS_TICKER_MAP.get(code)
        if match is None:
            continue

        yahoo_symbol, dr_symbol = match

        ticker_info = resolver.resolve(yahoo_symbol)
        if ticker_info is None:
            logger.warning(f"TickerResolver cannot resolve {yahoo_symbol} for {code}")
            continue

        filing['ticker_id'] = ticker_info.ticker_id
        filing['symbol'] = dr_symbol
        matched_count += 1

    logger.info(f"Ticker matching: {matched_count}/{len(filings)} matched to DR tickers")
    return matched_count


# ===========================================================================
# Document Download (3-step MOPS flow)
# ===========================================================================

def resolve_download_path(
    session: requests.Session,
    filename: str,
) -> Optional[str]:
    """Step 2: POST with step=9 to get timestamped download path."""
    try:
        data = {
            'step': '9',
            'kind': 'A',
            'co_id': '',
            'filename': filename,
        }
        resp = session.post(MOPS_TWSE_URL, data=data, timeout=15)
        if resp.status_code != 200:
            return None

        timestamped = resp.text.strip()
        if timestamped and not timestamped.startswith('<'):
            return f"{MOPS_TWSE_BASE}/pdf/{timestamped}"

        return None
    except Exception as e:
        logger.warning(f"Step 2 failed for {filename}: {e}")
        return None


def download_and_archive_pdf(
    session: requests.Session,
    data_lake: DataLakeStorage,
    filing: Dict[str, Any],
    delay: float = 2.0,
) -> bool:
    """Download a single PDF via MOPS 3-step flow and archive to S3.

    Returns True if archived successfully.
    """
    filename = filing['filename']
    stock_code = filing['stock_code']
    s3_key = f"mops-filings/documents/{stock_code}/{filename}"

    # Check if already archived
    try:
        data_lake.s3_client.head_object(Bucket=data_lake.bucket_name, Key=s3_key)
        filing['pdf_s3_key'] = s3_key
        return False  # Already exists (skipped)
    except data_lake.s3_client.exceptions.ClientError:
        pass

    # Step 2: Get download path
    download_url = resolve_download_path(session, filename)
    if not download_url:
        logger.debug(f"No download path for {filename}")
        return False

    time.sleep(0.5)  # Rate limit between step 2 and 3

    # Step 3: Download PDF
    try:
        resp = session.get(download_url, timeout=120)
        if resp.status_code != 200:
            logger.warning(f"PDF download HTTP {resp.status_code}: {filename}")
            return False

        if len(resp.content) < 1000:
            logger.warning(f"PDF too small ({len(resp.content)} bytes): {filename}")
            return False

        # Upload to S3
        data_lake.s3_client.put_object(
            Bucket=data_lake.bucket_name,
            Key=s3_key,
            Body=resp.content,
            ContentType='application/pdf',
            Metadata={
                'filename': filename,
                'stock_code': stock_code,
                'archived_at': datetime.now(timezone.utc).isoformat(),
            },
            Tagging="type=document&source=mops&purpose=filing-archive",
        )

        filing['pdf_s3_key'] = s3_key
        filing['file_url'] = download_url
        return True

    except Exception as e:
        logger.warning(f"PDF download failed for {filename}: {e}")
        return False


def download_documents(
    filings: List[Dict[str, Any]],
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 2.0,
) -> int:
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping document downloads")
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    logger.info(f"Downloading {len(filings)} filing documents to S3...")

    for i, filing in enumerate(filings):
        result = download_and_archive_pdf(session, data_lake, filing, delay=delay)

        if result:
            archived_count += 1
        elif filing.get('pdf_s3_key'):
            skipped_count += 1
        else:
            failed_count += 1

        if (i + 1) % 10 == 0:
            logger.info(
                f"Document progress: {i + 1}/{len(filings)} "
                f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
            )

        if delay > 0 and i < len(filings) - 1:
            time.sleep(delay)

    logger.info(
        f"Document download complete: "
        f"archived={archived_count}, skipped={skipped_count}, failed={failed_count}"
    )
    return archived_count


def download_docs_from_aurora(
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 2.0,
) -> int:
    if not data_lake.enabled:
        logger.warning("Data lake not configured")
        return 0

    repo = get_mops_filings_repository()
    filings = repo.get_filings_needing_docs()
    logger.info(f"Found {len(filings)} filings needing document download")

    if not filings:
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    for i, filing in enumerate(filings):
        filename = filing['filename']
        stock_code = filing['stock_code']
        s3_key = f"mops-filings/documents/{stock_code}/{filename}"

        try:
            try:
                data_lake.s3_client.head_object(Bucket=data_lake.bucket_name, Key=s3_key)
                repo.update_pdf_s3_key(filename, s3_key)
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            download_url = resolve_download_path(session, filename)
            if not download_url:
                failed_count += 1
                continue

            time.sleep(0.5)

            resp = session.get(download_url, timeout=120)
            if resp.status_code != 200 or len(resp.content) < 1000:
                failed_count += 1
                continue

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name, Key=s3_key, Body=resp.content,
                ContentType='application/pdf',
                Metadata={'filename': filename, 'archived_at': datetime.now(timezone.utc).isoformat()},
                Tagging="type=document&source=mops&purpose=filing-archive",
            )
            repo.update_pdf_s3_key(filename, s3_key)
            archived_count += 1

            if (i + 1) % 10 == 0:
                logger.info(f"Document progress: {i+1}/{len(filings)} (archived={archived_count})")

        except Exception as e:
            logger.warning(f"Document archive failed for filename={filename}: {e}")
            failed_count += 1

        if delay > 0 and i < len(filings) - 1:
            time.sleep(delay)

    logger.info(f"Document download complete: archived={archived_count}, skipped={skipped_count}, failed={failed_count}")
    return archived_count


# ===========================================================================
# Runtime Detection + S3 Self-Archive
# ===========================================================================

def _detect_runtime_type() -> str:
    if os.environ.get('ECS_CONTAINER_METADATA_URI'):
        return 'ecs_fargate'
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return 'lambda'
    if os.environ.get('GITHUB_ACTIONS'):
        return 'github_actions'
    return 'local'


def self_archive_to_s3(data_lake: DataLakeStorage, version: str) -> Tuple[str, str]:
    script_path = Path(__file__)
    content = script_path.read_bytes()
    sha256_hex = hashlib.sha256(content).hexdigest()
    s3_key = f"scripts/data-acquisition/mops-filings/{version}.py"
    data_lake.s3_client.put_object(
        Bucket=data_lake.bucket_name, Key=s3_key, Body=content,
        ContentType='text/x-python',
        Metadata={'sha256': sha256_hex, 'source_file': script_path.name,
                  'archived_at': datetime.now(timezone.utc).isoformat()},
        Tagging="type=script&purpose=data-acquisition&target=mops_filings",
    )
    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key}")
    return s3_key, sha256_hex


# ===========================================================================
# Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest MOPS filings into Aurora")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--years-back', type=int, default=5)
    parser.add_argument('--year-from', type=int, default=None, help='Western year (e.g. 2020)')
    parser.add_argument('--year-to', type=int, default=None, help='Western year (e.g. 2025)')
    parser.add_argument('--delay', type=float, default=2.0)
    parser.add_argument('--version', type=str, default='v1')
    parser.add_argument('--skip-self-archive', action='store_true')
    parser.add_argument('--skip-doc-download', action='store_true')
    parser.add_argument('--doc-only', action='store_true')
    parser.add_argument('--doc-delay', type=float, default=2.0)
    parser.add_argument('--runtime-type', type=str, default=None)
    parser.add_argument('--verbose', '-v', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Resolve year range
    current_year = date.today().year
    if args.year_to:
        year_to = args.year_to
    else:
        year_to = current_year
    if args.year_from:
        year_from = args.year_from
    else:
        year_from = year_to - args.years_back

    years = list(range(year_from, year_to + 1))

    mode = "doc-only" if args.doc_only else "full"
    logger.info("=" * 60)
    logger.info(f"MOPS Filings Ingestion (mode={mode})")
    if not args.doc_only:
        logger.info(f"  dry_run={args.dry_run}, years={year_from}-{year_to} ({len(years)} years)")
        logger.info(f"  companies={len(TARGET_CODES)}, doc_types={len(DOCUMENT_TYPES)}, version={args.version}")
    else:
        logger.info(f"  Document-only: downloading docs for filings already in Aurora")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Doc-only mode
    # ------------------------------------------------------------------
    if args.doc_only:
        data_lake = DataLakeStorage()
        if not data_lake.enabled:
            logger.error("DATA_LAKE_BUCKET not configured")
            sys.exit(1)
        session = _create_session()
        docs = download_docs_from_aurora(data_lake, session, delay=args.doc_delay)
        logger.info("=" * 60)
        logger.info(f"DOC-ONLY COMPLETE: {docs} documents archived to S3")
        logger.info("=" * 60)
        return

    # ------------------------------------------------------------------
    # Full ingestion
    # ------------------------------------------------------------------
    artifact_s3_key = None
    artifact_checksum = None
    data_lake = None

    if not args.dry_run and not args.skip_self_archive:
        try:
            data_lake = DataLakeStorage()
            if data_lake.enabled:
                artifact_s3_key, artifact_checksum = self_archive_to_s3(data_lake, args.version)
        except Exception as e:
            logger.warning(f"Self-archive failed (non-fatal): {e}")

    acq_repo = get_data_acquisitions_repository()
    acq_id = None
    ingestion_method_id = None

    if not args.dry_run:
        runtime_type = args.runtime_type or _detect_runtime_type()
        method_name = f"mops-{runtime_type}-{args.version}"
        try:
            methods_repo = get_ingestion_methods_repository()
            method = methods_repo.get_or_create(
                method_name=method_name, runtime_type=runtime_type,
                script_path='scripts/ingest_mops_filings.py',
                container_image=os.environ.get('CONTAINER_IMAGE'),
                description=f"MOPS filings ingestion via {runtime_type}",
            )
            ingestion_method_id = method['id']
        except Exception as e:
            logger.warning(f"Ingestion method registration failed (non-fatal): {e}")

        acq_id = acq_repo.start_run(
            source_table='mops_filings', source_type='script',
            source_name=SCRIPT_SOURCE_NAME, source_version=args.version,
            artifact_s3_key=artifact_s3_key, artifact_checksum=artifact_checksum,
            endpoint_url=MOPS_TWSE_URL, endpoint_version='v1',
            description=f"MOPS filings ingestion ({year_from}-{year_to})",
            parameters={'year_from': year_from, 'year_to': year_to,
                        'stock_count': len(TARGET_CODES), 'delay': args.delay,
                        'doc_types': len(DOCUMENT_TYPES)},
            ingestion_method_id=ingestion_method_id,
        )
        logger.info(f"Started acquisition run: id={acq_id}")

    records_fetched = 0
    records_upserted = 0
    matched_count = 0
    docs_archived = 0

    try:
        session = _create_session()

        logger.info(f"Fetching filings for {len(TARGET_CODES)} companies...")
        filings = fetch_all_filings(
            session, TARGET_CODES, years, DOCUMENT_TYPES, delay=args.delay
        )
        records_fetched = len(filings)

        logger.info("Matching filings to DR tickers...")
        resolver = get_ticker_resolver()
        matched_count = try_match_tickers(filings, resolver)

        if not args.dry_run and not args.skip_doc_download:
            if data_lake is None:
                data_lake = DataLakeStorage()
            if data_lake.enabled:
                docs_archived = download_documents(filings, data_lake, session, delay=args.doc_delay)

        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN -- No data written")
            logger.info(f"  Total filings: {records_fetched}")
            logger.info(f"  Matched to DR: {matched_count}")
            for code in TARGET_CODES:
                info = MOPS_TICKER_MAP.get(code, ('', ''))
                count = sum(1 for f in filings if f['stock_code'] == code)
                logger.info(f"  {code} ({info[1]:14s}): {count} filings")
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=0, records_upserted=0)
            return

        filings_repo = get_mops_filings_repository()
        records_upserted = filings_repo.batch_upsert(filings, acquisition_id=acq_id)
        logger.info(f"Batch upsert complete: {records_upserted} rows affected")

        if acq_id:
            acq_repo.complete_run(acq_id, records_fetched=records_fetched,
                                  records_upserted=records_upserted, status='success')
        logger.info("Acquisition complete: status=success")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        if acq_id:
            acq_repo.fail_run(acq_id, error_message=str(e),
                              records_fetched=records_fetched, records_upserted=records_upserted)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Companies:            {len(TARGET_CODES)}")
    logger.info(f"  Years:                {year_from}-{year_to}")
    logger.info(f"  Filings fetched:      {records_fetched}")
    logger.info(f"  Filings upserted:     {records_upserted}")
    logger.info(f"  DR ticker matches:    {matched_count}")
    logger.info(f"  Documents archived:   {docs_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:       {acq_id}")
    logger.info("=" * 60)


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Referer': 'https://doc.twse.com.tw/server-java/t57sb01',
    })
    return session


if __name__ == "__main__":
    main()
