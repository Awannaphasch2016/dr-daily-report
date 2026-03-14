#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGX Financial Reports Ingestion Script

Fetches all financial reports from the SGX Financial Reports API,
matches them to DR tickers, and stores them in Aurora with full
provenance tracking.

Usage:
    # Full ingestion
    ENV=dev doppler run -- python scripts/ingest_sgx_financial_reports.py

    # Dry run (test API + matching)
    ENV=dev doppler run -- python scripts/ingest_sgx_financial_reports.py --dry-run --max-pages 2

    # Single symbol
    ENV=dev doppler run -- python scripts/ingest_sgx_financial_reports.py --symbol DBS19

Architecture:
    SGX Financial Reports API → this script → Aurora sgx_filings table
                                            → Aurora data_acquisitions table (provenance)
                                            → S3 data lake (script artifact)
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Project imports (run from repo root with PYTHONPATH=.)
# ---------------------------------------------------------------------------
from src.data.aurora.data_acquisitions_repository import get_data_acquisitions_repository
from src.data.aurora.sgx_filings_repository import get_sgx_filings_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

SGX_CONFIG_URL = "https://www.sgx.com/config/appconfig.json"
SGX_CMS_API_URL = "https://api2.sgx.com/content-api"
SGX_FIN_REPORTS_URL = "https://api.sgx.com/financialreports/v1.0"

SCRIPT_SOURCE_NAME = "sgx_financial_reports_ingester"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.sgx.com",
    "Referer": "https://www.sgx.com/securities/company-announcements",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# SGX companyName substring (uppercase) → (yahoo_symbol, dr_symbol, sgx_stock_code)
# Only operating companies likely to file financial reports on SGX
SGX_COMPANY_MAP = {
    "DBS GROUP": ("D05.SI", "DBS19", "D05"),
    "SINGAPORE AIRLINES": ("C6L.SI", "SIA19", "C6L"),
    "UNITED OVERSEAS BANK": ("U11.SI", "UOB19", "U11"),
    "SATS ": ("S58.SI", "STEG19", "S58"),  # trailing space to avoid matching "SATS" in other names
    "SINGAPORE EXCHANGE": ("S68.SI", "SGX19", "S68"),
    "SEMBCORP": ("U96.SI", "SEMB19", "U96"),
    "VENTURE CORP": ("V03.SI", "VENTURE19", "V03"),
    "THAI BEVERAGE": ("Y92.SI", "THAIBEV19", "Y92"),
}


# ===========================================================================
# SGX Token Auth
# ===========================================================================

def _rot13(text: str) -> str:
    """ROT13 decode."""
    return "".join(
        chr((ord(c) - (base := (ord('a') if c.islower() else ord('A'))) + 13) % 26 + base)
        if c.isalpha() else c
        for c in text
    )


def _safe_json(resp: requests.Response) -> dict:
    """Parse SGX JSON response, stripping {}&& prefix if present."""
    text = resp.text.strip()
    if text.startswith("{}&&"):
        text = text[4:]
    return json.loads(text)


def get_sgx_token(session: requests.Session) -> Optional[str]:
    """Obtain SGX API auth token via CMS config + ROT13.

    Returns:
        Auth token string, or None if token fetch fails
    """
    try:
        resp = session.get(SGX_CONFIG_URL, timeout=10)
        resp.raise_for_status()
        config = _safe_json(resp)
        cms_version = config.get("CMS_VERSION", "")

        time.sleep(3)

        token_url = f"{SGX_CMS_API_URL}/?queryId={cms_version}:we_chat_qr_validator"
        resp = session.get(token_url, timeout=10)
        resp.raise_for_status()
        data = _safe_json(resp)

        qr_val = data.get("qrValidator")
        if not qr_val and "data" in data:
            d = data["data"]
            if isinstance(d, dict):
                qr_val = d.get("qrValidator")
            elif isinstance(d, list) and d:
                qr_val = d[0].get("qrValidator") if isinstance(d[0], dict) else None

        if not qr_val:
            logger.error("Failed to extract qrValidator from CMS response")
            return None

        return _rot13(qr_val)
    except Exception as e:
        logger.error(f"Token fetch failed: {e}")
        return None


# ===========================================================================
# API Fetching
# ===========================================================================

def fetch_page(
    session: requests.Session,
    token: Optional[str],
    page_start: int,
    page_size: int,
    max_retries: int = 3,
) -> Optional[dict]:
    """Fetch a single page from the SGX Financial Reports API.

    Retries with exponential backoff on failure.

    Returns:
        Parsed JSON response, or None if all retries exhausted
    """
    auth_headers = {}
    if token:
        auth_headers = {"Authorization": token, "authorizationtoken": token}

    params = {"pagestart": str(page_start), "pagesize": str(page_size)}

    for attempt in range(max_retries):
        try:
            resp = session.get(
                SGX_FIN_REPORTS_URL,
                params=params,
                headers=auth_headers,
                timeout=30,
            )
            if resp.status_code == 200:
                return _safe_json(resp)

            logger.warning(
                f"Page fetch HTTP {resp.status_code} (attempt {attempt + 1}/{max_retries}), "
                f"pagestart={page_start}"
            )

            if resp.status_code == 403:
                # WAF block — longer backoff
                wait = (attempt + 1) * 10
                logger.warning(f"WAF block detected, waiting {wait}s")
                time.sleep(wait)
            else:
                time.sleep((attempt + 1) * 5)

        except requests.RequestException as e:
            logger.warning(f"Page fetch error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep((attempt + 1) * 5)

    logger.error(f"All retries exhausted for pagestart={page_start}")
    return None


def fetch_all_reports(
    session: requests.Session,
    token: Optional[str],
    page_size: int = 250,
    delay: float = 5.0,
    max_pages: Optional[int] = None,
) -> Tuple[List[dict], int]:
    """Paginate through all SGX Financial Reports.

    Returns:
        (list_of_report_items, total_expected_from_meta)
    """
    all_items = []
    page_start = 0
    page_num = 0
    total_expected = 0

    while True:
        if max_pages and page_num >= max_pages:
            logger.info(f"Reached max_pages={max_pages}, stopping")
            break

        data = fetch_page(session, token, page_start, page_size)
        if data is None:
            logger.warning(f"Page fetch failed at pagestart={page_start}, stopping pagination")
            break

        if page_num == 0:
            meta = data.get("meta", {})
            total_expected = meta.get("totalRecords", 0)
            logger.info(f"API reports totalRecords={total_expected}")

        items = data.get("data", [])
        if not items:
            break

        all_items.extend(items)
        page_num += 1
        logger.info(f"Page {page_num}: fetched {len(items)} items (total so far: {len(all_items)})")

        if len(items) < page_size:
            break  # last page

        page_start += len(items)
        time.sleep(delay)

    return all_items, total_expected


# ===========================================================================
# Company-to-Ticker Matching
# ===========================================================================

def match_company(company_name: str) -> Optional[Tuple[str, str, str]]:
    """Match SGX companyName to DR ticker.

    Args:
        company_name: Company name from SGX API

    Returns:
        (yahoo_symbol, dr_symbol, sgx_stock_code) or None
    """
    upper = company_name.upper()
    for key, value in SGX_COMPANY_MAP.items():
        if key in upper:
            return value
    return None


def match_reports_to_tickers(
    reports: List[dict],
    resolver,
    symbol_filter: Optional[str] = None,
) -> List[dict]:
    """Match SGX reports to DR tickers and attach ticker_id.

    Args:
        reports: Raw API report items
        resolver: TickerResolver instance
        symbol_filter: If set, only include this DR symbol

    Returns:
        List of reports with ticker info attached (ticker_id, symbol, stock_code)
    """
    matched = []
    unmatched_companies = set()

    for report in reports:
        company_name = report.get("companyName", "")
        match = match_company(company_name)
        if match is None:
            unmatched_companies.add(company_name)
            continue

        yahoo_symbol, dr_symbol, stock_code = match

        if symbol_filter and dr_symbol != symbol_filter:
            continue

        ticker_info = resolver.resolve(yahoo_symbol)
        if ticker_info is None:
            logger.warning(f"TickerResolver cannot resolve {yahoo_symbol} for {company_name}")
            continue

        report['_ticker_id'] = ticker_info.ticker_id
        report['_dr_symbol'] = dr_symbol
        report['_stock_code'] = stock_code
        matched.append(report)

    logger.info(
        f"Matched {len(matched)} reports to DR tickers "
        f"({len(unmatched_companies)} companies not in DR universe)"
    )
    return matched


# ===========================================================================
# Transform to Filing Dicts
# ===========================================================================

def _epoch_ms_to_datetime_str(value) -> Optional[str]:
    """Convert epoch milliseconds to datetime string."""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        return value
    return None


def transform_to_filings(matched_reports: List[dict]) -> List[Dict[str, Any]]:
    """Transform matched SGX API reports to sgx_filings dict format.

    Maps API fields to table columns per the schema.
    """
    filings = []
    for report in matched_reports:
        broadcast = _epoch_ms_to_datetime_str(report.get("broadcastDateTime"))
        if not broadcast:
            logger.warning(f"Skipping report with no broadcastDateTime: {report.get('id')}")
            continue

        filing = {
            'ticker_id': report['_ticker_id'],
            'symbol': report['_dr_symbol'],
            'ann_id': str(report.get('id', '')),
            'broadcast_date_time': broadcast,
            'category_code': 'FIN_REPORT',
            'subcategory_code': None,
            'subcategory_name': None,
            'title': report.get('title', 'Untitled'),
            'issuer_name': report.get('companyName'),
            'stock_code': report.get('_stock_code'),
            'attachment_url': report.get('url'),
            'sgx_url': None,
            'raw_data': report,
        }
        filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings")
    return filings


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

    s3_key = f"scripts/data-acquisition/sgx-financial-reports/{version}.py"

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
        Tagging="type=script&purpose=data-acquisition&target=sgx_filings",
    )

    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key} (sha256={sha256_hex[:12]}...)")
    return s3_key, sha256_hex


# ===========================================================================
# Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest SGX Financial Reports into Aurora"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Fetch and match but do not write to Aurora or S3',
    )
    parser.add_argument(
        '--symbol', type=str, default=None,
        help='Filter to a specific DR symbol (e.g., DBS19)',
    )
    parser.add_argument(
        '--max-pages', type=int, default=None,
        help='Stop after N pages (for testing)',
    )
    parser.add_argument(
        '--page-size', type=int, default=250,
        help='Records per page (default: 250)',
    )
    parser.add_argument(
        '--delay', type=float, default=5.0,
        help='Delay between API calls in seconds (default: 5.0)',
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

    logger.info("=" * 60)
    logger.info("SGX Financial Reports Ingestion")
    logger.info(f"  dry_run={args.dry_run}, symbol={args.symbol}, "
                f"max_pages={args.max_pages}, version={args.version}")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. S3 self-archive (provenance)
    # ------------------------------------------------------------------
    artifact_s3_key = None
    artifact_checksum = None

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
    # 2. Start acquisition run
    # ------------------------------------------------------------------
    acq_repo = get_data_acquisitions_repository()
    acq_id = None

    if not args.dry_run:
        acq_id = acq_repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name=SCRIPT_SOURCE_NAME,
            source_version=args.version,
            artifact_s3_key=artifact_s3_key,
            artifact_checksum=artifact_checksum,
            endpoint_url=SGX_FIN_REPORTS_URL,
            endpoint_version='v1.0',
            description=f"SGX Financial Reports ingestion (symbol={args.symbol or 'all'})",
            parameters={
                'page_size': args.page_size,
                'delay': args.delay,
                'max_pages': args.max_pages,
                'symbol_filter': args.symbol,
            },
        )
        logger.info(f"Started acquisition run: id={acq_id}")

    records_fetched = 0
    records_upserted = 0

    try:
        # ------------------------------------------------------------------
        # 3. Fetch SGX token
        # ------------------------------------------------------------------
        session = requests.Session()
        session.headers.update(HEADERS)

        logger.info("Fetching SGX auth token...")
        token = get_sgx_token(session)
        if token:
            logger.info("Token obtained successfully")
        else:
            logger.warning("Token fetch failed, proceeding without auth")

        time.sleep(5)

        # ------------------------------------------------------------------
        # 4. Paginate all reports
        # ------------------------------------------------------------------
        logger.info("Fetching all financial reports from SGX...")
        all_reports, total_expected = fetch_all_reports(
            session, token,
            page_size=args.page_size,
            delay=args.delay,
            max_pages=args.max_pages,
        )
        records_fetched = len(all_reports)
        logger.info(f"Fetched {records_fetched} reports (expected {total_expected})")

        # ------------------------------------------------------------------
        # 5. Match to DR tickers
        # ------------------------------------------------------------------
        logger.info("Matching reports to DR ticker universe...")
        resolver = get_ticker_resolver()
        matched = match_reports_to_tickers(
            all_reports, resolver, symbol_filter=args.symbol
        )

        # ------------------------------------------------------------------
        # 6. Transform to filing dicts
        # ------------------------------------------------------------------
        filings = transform_to_filings(matched)

        # ------------------------------------------------------------------
        # 7. Dry run summary or upsert
        # ------------------------------------------------------------------
        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN — No data written")
            logger.info(f"  Total reports fetched: {records_fetched}")
            logger.info(f"  Matched to DR tickers: {len(matched)}")
            logger.info(f"  Filings to upsert: {len(filings)}")
            logger.info("")
            for f in filings:
                logger.info(
                    f"  {f['symbol']:12s} | {f['ann_id']:20s} | "
                    f"{f['broadcast_date_time'][:10]} | {f['title'][:60]}"
                )
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=records_fetched, records_upserted=0)
            return

        filings_repo = get_sgx_filings_repository()
        records_upserted = filings_repo.batch_upsert(
            filings, acquisition_id=acq_id
        )
        logger.info(f"Batch upsert complete: {records_upserted} rows affected")

        # ------------------------------------------------------------------
        # 8. Complete acquisition
        # ------------------------------------------------------------------
        status = 'success' if records_fetched >= total_expected else 'partial'
        if acq_id:
            acq_repo.complete_run(
                acq_id,
                records_fetched=records_fetched,
                records_upserted=records_upserted,
                status=status,
            )
        logger.info(f"Acquisition complete: status={status}")

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
    logger.info(f"  Reports fetched:  {records_fetched}")
    logger.info(f"  Rows upserted:    {records_upserted}")
    if acq_id:
        logger.info(f"  Acquisition ID:   {acq_id}")
    if artifact_s3_key:
        logger.info(f"  Script artifact:  {artifact_s3_key}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
