#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGX Financial Reports Ingestion Script

Fetches ALL financial reports from the SGX Financial Reports API,
optionally matches them to DR tickers, downloads PDF attachments to S3,
and stores everything in Aurora with full provenance tracking.

No pre-filtering: ALL filings are stored. Categorization/filtering
happens at query time by downstream services.

Usage:
    # Full ingestion (all filings + PDF attachments)
    ENV=dev doppler run -- python -m scripts.ingest_sgx_financial_reports

    # Dry run (test API, no writes)
    ENV=dev doppler run -- python -m scripts.ingest_sgx_financial_reports --dry-run --max-pages 1

    # Skip PDF downloads (faster re-runs)
    ENV=dev doppler run -- python -m scripts.ingest_sgx_financial_reports --skip-attachments

Architecture:
    SGX Financial Reports API -> this script -> Aurora sgx_filings table
                                             -> Aurora data_acquisitions table (provenance)
                                             -> S3 data lake (script artifact + PDF attachments)
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
from urllib.parse import urlparse

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

# SGX companyName substring (uppercase) -> (yahoo_symbol, dr_symbol, sgx_stock_code)
# Used for opportunistic ticker matching — filings that don't match are still stored.
SGX_COMPANY_MAP = {
    "DBS GROUP": ("D05.SI", "DBS19", "D05"),
    "SINGAPORE AIRLINES": ("C6L.SI", "SIA19", "C6L"),
    "UNITED OVERSEAS BANK": ("U11.SI", "UOB19", "U11"),
    "SATS ": ("S58.SI", "STEG19", "S58"),  # trailing space to avoid partial match
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
                # WAF block -- longer backoff
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
# Transform to Filing Dicts (ALL reports, no filtering)
# ===========================================================================

def _epoch_ms_to_datetime_str(value) -> Optional[str]:
    """Convert epoch milliseconds to datetime string."""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        return value
    return None


def transform_to_filings(reports: List[dict]) -> List[Dict[str, Any]]:
    """Transform ALL SGX API reports to sgx_filings dict format.

    No filtering — every report becomes a filing. ticker_id and symbol
    are set to None; populated later by try_match_tickers().
    """
    filings = []
    for report in reports:
        broadcast = _epoch_ms_to_datetime_str(report.get("broadcastDateTime"))
        if not broadcast:
            logger.warning(f"Skipping report with no broadcastDateTime: {report.get('id')}")
            continue

        filing = {
            'ticker_id': None,
            'symbol': None,
            'ann_id': str(report.get('id', '')),
            'broadcast_date_time': broadcast,
            'category_code': 'FIN_REPORT',
            'subcategory_code': None,
            'subcategory_name': None,
            'title': report.get('title', 'Untitled'),
            'issuer_name': report.get('companyName'),
            'stock_code': report.get('stockCode'),
            'attachment_url': report.get('url'),
            'attachment_s3_key': None,
            'sgx_url': None,
            'raw_data': report,
        }
        filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings from {len(reports)} reports")
    return filings


# ===========================================================================
# Opportunistic Ticker Matching
# ===========================================================================

def _match_company(company_name: str) -> Optional[Tuple[str, str, str]]:
    """Match SGX companyName to DR ticker.

    Returns:
        (yahoo_symbol, dr_symbol, sgx_stock_code) or None
    """
    upper = company_name.upper()
    for key, value in SGX_COMPANY_MAP.items():
        if key in upper:
            return value
    return None


def try_match_tickers(filings: List[Dict[str, Any]], resolver) -> int:
    """Opportunistically match filings to DR tickers.

    For each filing, try to match its issuer_name to a DR ticker.
    If matched: set ticker_id + symbol on the filing dict.
    If not matched: leave both as None (filing is still stored).

    Args:
        filings: List of filing dicts (modified in-place)
        resolver: TickerResolver instance

    Returns:
        Number of filings matched to DR tickers
    """
    matched_count = 0
    unmatched_companies = set()

    for filing in filings:
        company_name = filing.get('issuer_name', '')
        if not company_name:
            continue

        match = _match_company(company_name)
        if match is None:
            unmatched_companies.add(company_name)
            continue

        yahoo_symbol, dr_symbol, stock_code = match

        ticker_info = resolver.resolve(yahoo_symbol)
        if ticker_info is None:
            logger.warning(f"TickerResolver cannot resolve {yahoo_symbol} for {company_name}")
            continue

        filing['ticker_id'] = ticker_info.ticker_id
        filing['symbol'] = dr_symbol
        if not filing.get('stock_code'):
            filing['stock_code'] = stock_code
        matched_count += 1

    logger.info(
        f"Ticker matching: {matched_count} matched to DR tickers, "
        f"{len(unmatched_companies)} unique companies not in DR universe"
    )
    return matched_count


# ===========================================================================
# PDF Attachment Download to S3
# ===========================================================================

def _extract_filename_from_url(url: str) -> str:
    """Extract filename from URL path, fallback to 'attachment.pdf'."""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if path:
            filename = Path(path).name
            if filename:
                return filename
    except Exception:
        pass
    return "attachment.pdf"


def download_attachments(
    filings: List[Dict[str, Any]],
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 1.0,
) -> int:
    """Download PDF attachments from SGX and archive to S3.

    For each filing with an attachment_url, downloads the PDF and uploads
    it to S3 under sgx-filings/attachments/{ann_id}/{filename}.

    Failures are logged but don't fail the whole run.

    Args:
        filings: List of filing dicts (modified in-place to set attachment_s3_key)
        data_lake: DataLakeStorage instance for S3 access
        session: requests.Session for downloading
        delay: Seconds to wait between downloads (rate limiting)

    Returns:
        Number of attachments successfully archived
    """
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping attachment downloads")
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    filings_with_url = [f for f in filings if f.get('attachment_url')]
    logger.info(f"Downloading {len(filings_with_url)} PDF attachments to S3...")

    for i, filing in enumerate(filings_with_url):
        url = filing['attachment_url']
        ann_id = filing['ann_id']
        filename = _extract_filename_from_url(url)
        s3_key = f"sgx-filings/attachments/{ann_id}/{filename}"

        try:
            # Check if already archived (idempotent)
            try:
                data_lake.s3_client.head_object(
                    Bucket=data_lake.bucket_name,
                    Key=s3_key,
                )
                # Already exists
                filing['attachment_s3_key'] = s3_key
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass  # Not found, proceed to download

            # Download PDF (stream to avoid buffering large files)
            resp = session.get(url, timeout=60, stream=True)
            if resp.status_code != 200:
                logger.warning(
                    f"Attachment download failed HTTP {resp.status_code}: "
                    f"ann_id={ann_id} url={url}"
                )
                failed_count += 1
                continue

            # Read content
            content = resp.content
            content_type = resp.headers.get('Content-Type', 'application/pdf')

            # Upload to S3
            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'ann_id': ann_id,
                    'source_url': url,
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=attachment&source=sgx&purpose=filing-archive",
            )

            filing['attachment_s3_key'] = s3_key
            archived_count += 1

            if (i + 1) % 50 == 0:
                logger.info(
                    f"Attachment progress: {i + 1}/{len(filings_with_url)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"Attachment archive failed for ann_id={ann_id}: {e}")
            failed_count += 1

        # Rate limit between downloads
        if delay > 0 and i < len(filings_with_url) - 1:
            time.sleep(delay)

    logger.info(
        f"Attachment download complete: "
        f"archived={archived_count}, skipped={skipped_count}, failed={failed_count}"
    )
    return archived_count


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
        help='Fetch and transform but do not write to Aurora or S3',
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
        '--version', type=str, default='v2',
        help='Script version tag for provenance (default: v2)',
    )
    parser.add_argument(
        '--skip-self-archive', action='store_true',
        help='Skip uploading script to S3',
    )
    parser.add_argument(
        '--skip-attachments', action='store_true',
        help='Skip downloading PDF attachments to S3',
    )
    parser.add_argument(
        '--attachment-delay', type=float, default=1.0,
        help='Delay between attachment downloads in seconds (default: 1.0)',
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
    logger.info("SGX Financial Reports Ingestion (v2 — all filings)")
    logger.info(f"  dry_run={args.dry_run}, symbol={args.symbol}, "
                f"max_pages={args.max_pages}, version={args.version}")
    logger.info(f"  skip_attachments={args.skip_attachments}")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. S3 self-archive (provenance)
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
            description=f"SGX Financial Reports ingestion v2 (symbol={args.symbol or 'all'})",
            parameters={
                'page_size': args.page_size,
                'delay': args.delay,
                'max_pages': args.max_pages,
                'symbol_filter': args.symbol,
                'skip_attachments': args.skip_attachments,
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
        # 5. Transform ALL reports to filing dicts (no filtering)
        # ------------------------------------------------------------------
        filings = transform_to_filings(all_reports)

        # ------------------------------------------------------------------
        # 6. Opportunistic ticker matching
        # ------------------------------------------------------------------
        logger.info("Attempting opportunistic DR ticker matching...")
        resolver = get_ticker_resolver()
        matched_count = try_match_tickers(filings, resolver)

        # Filter by --symbol if requested (post-matching)
        if args.symbol:
            filings = [f for f in filings if f.get('symbol') == args.symbol]
            logger.info(f"Filtered to symbol={args.symbol}: {len(filings)} filings")

        # ------------------------------------------------------------------
        # 7. Download PDF attachments to S3
        # ------------------------------------------------------------------
        attachments_archived = 0
        if not args.dry_run and not args.skip_attachments:
            if data_lake is None:
                data_lake = DataLakeStorage()
            if data_lake.enabled:
                attachments_archived = download_attachments(
                    filings, data_lake, session,
                    delay=args.attachment_delay,
                )
            else:
                logger.warning("Data lake not configured, skipping attachment downloads")

        # ------------------------------------------------------------------
        # 8. Dry run summary or upsert
        # ------------------------------------------------------------------
        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN -- No data written")
            logger.info(f"  Total reports fetched:    {records_fetched}")
            logger.info(f"  Filings to upsert:       {len(filings)}")
            logger.info(f"  Matched to DR tickers:   {matched_count}")
            logger.info(f"  Unmatched (still stored): {len(filings) - matched_count}")
            logger.info("")
            for f in filings[:20]:
                symbol_str = f['symbol'] or '(none)'
                logger.info(
                    f"  {symbol_str:12s} | {f['ann_id']:20s} | "
                    f"{f['broadcast_date_time'][:10]} | "
                    f"{(f.get('issuer_name') or '')[:30]:30s} | "
                    f"{f['title'][:40]}"
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

        filings_repo = get_sgx_filings_repository()
        records_upserted = filings_repo.batch_upsert(
            filings, acquisition_id=acq_id
        )
        logger.info(f"Batch upsert complete: {records_upserted} rows affected")

        # ------------------------------------------------------------------
        # 9. Complete acquisition
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
    logger.info(f"  Reports fetched:      {records_fetched}")
    logger.info(f"  Filings upserted:     {records_upserted}")
    logger.info(f"  DR ticker matches:    {matched_count}")
    logger.info(f"  Attachments archived: {attachments_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:       {acq_id}")
    if artifact_s3_key:
        logger.info(f"  Script artifact:      {artifact_s3_key}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
