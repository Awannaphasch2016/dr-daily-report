#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEC EDGAR Filings Ingestion Script

Fetches ALL filings from SEC EDGAR for tracked US tickers,
optionally matches them to DR tickers, downloads filing documents to S3,
and stores everything in Aurora with full provenance tracking.

No pre-filtering: ALL filing types (10-K, 10-Q, 8-K, N-CSR, etc.)
are stored. Filtering happens at query time.

Usage:
    # Full ingestion (all filings, skip doc downloads)
    ENV=dev doppler run -- python -m scripts.ingest_sec_edgar_filings --skip-doc-download

    # Dry run
    ENV=dev doppler run -- python -m scripts.ingest_sec_edgar_filings --dry-run

    # Document-only mode (download docs for filings already in Aurora)
    ENV=dev doppler run -- python -m scripts.ingest_sec_edgar_filings --doc-only

Architecture:
    SEC EDGAR API -> this script -> Aurora sec_edgar_filings table
                                  -> Aurora data_acquisitions table (provenance)
                                  -> S3 data lake (script artifact + filing documents)
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
# Project imports
# ---------------------------------------------------------------------------
from src.data.aurora.data_acquisitions_repository import get_data_acquisitions_repository
from src.data.aurora.ingestion_methods_repository import get_ingestion_methods_repository
from src.data.aurora.sec_edgar_filings_repository import get_sec_edgar_filings_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

SCRIPT_SOURCE_NAME = "sec_edgar_filings_ingester"

SEC_USER_AGENT = "dr-daily-report/1.0 (contact: support@dr-daily-report.com)"

# CIK -> (yahoo_symbol, dr_symbol)
# All 19 US tickers including ETFs
SEC_CIK_MAP = {
    "19617": ("JPM", "JPMUS19"),
    "78003": ("PFE", "PFIZER19"),
    "1744489": ("DIS", "DISNEY19"),
    "1045810": ("NVDA", "NVDA19"),
    "909832": ("COST", "COSTCO19"),
    "731766": ("UNH", "UNH19"),
    "320193": ("AAPL", "AAPL19"),
    "1551152": ("ABBV", "ABBV19"),
    "1571996": ("DELL", "DELL19"),
    "1341439": ("ORCL", "ORCL19"),
    "1561550": ("DDOG", "DDOG19"),
    "1035267": ("ISRG", "ISRG19"),
    "723125": ("MU", "MICRON19"),
    "789019": ("MSFT", "MSFT19"),
    "1373715": ("NOW", "NOW19"),
    "1222333": ("GLD", "GOLDUS19"),
    "1378872": ("QQQM", "QQQM19"),
    "1064642": ("SPLG", "SP500US19"),
}

# CIKs to fetch (all keys from the map)
TARGET_CIKS = list(SEC_CIK_MAP.keys())


# ===========================================================================
# API Fetching
# ===========================================================================

def fetch_company_filings(
    session: requests.Session,
    cik: str,
    max_retries: int = 3,
) -> Optional[dict]:
    """Fetch all filings for a company from SEC EDGAR.

    Args:
        session: requests.Session with User-Agent set
        cik: SEC Central Index Key (not padded)
        max_retries: Number of retry attempts

    Returns:
        Parsed JSON response or None
    """
    cik_padded = cik.zfill(10)
    url = f"{SEC_SUBMISSIONS_URL}/CIK{cik_padded}.json"

    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=30)

            if resp.status_code == 200:
                return resp.json()

            logger.warning(
                f"SEC fetch HTTP {resp.status_code} (attempt {attempt + 1}/{max_retries}), "
                f"cik={cik}"
            )

            if resp.status_code == 429:
                time.sleep(10)
            else:
                time.sleep((attempt + 1) * 2)

        except requests.RequestException as e:
            logger.warning(f"SEC fetch error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep((attempt + 1) * 2)

    logger.error(f"All retries exhausted for cik={cik}")
    return None


def fetch_all_company_filings(
    session: requests.Session,
    ciks: List[str],
    delay: float = 0.2,
) -> List[Tuple[str, dict]]:
    """Fetch filings for all target companies.

    Returns:
        List of (cik, company_data) tuples
    """
    results = []

    for i, cik in enumerate(ciks):
        company_info = SEC_CIK_MAP.get(cik, ("", ""))
        logger.info(f"Fetching CIK {cik} ({company_info[0]}) [{i + 1}/{len(ciks)}]")

        data = fetch_company_filings(session, cik)
        if data is not None:
            results.append((cik, data))
        else:
            logger.warning(f"Failed to fetch CIK {cik}")

        if delay > 0 and i < len(ciks) - 1:
            time.sleep(delay)

    logger.info(f"Fetched filings for {len(results)}/{len(ciks)} companies")
    return results


# ===========================================================================
# Transform to Filing Dicts
# ===========================================================================

def _extract_filings_from_submission(cik: str, data: dict) -> List[dict]:
    """Extract individual filing items from a submissions response.

    Handles both 'recent' filings and historical filing files.
    """
    items = []
    company_name = data.get("name", "")

    recent = data.get("filings", {}).get("recent", {})
    if not recent:
        return items

    # Get array length from any field
    accession_numbers = recent.get("accessionNumber", [])

    for idx in range(len(accession_numbers)):
        accession = accession_numbers[idx]
        if not accession:
            continue

        # Build document URL
        primary_doc = recent.get("primaryDocument", [])[idx] if idx < len(recent.get("primaryDocument", [])) else None
        accession_nodashes = accession.replace("-", "")
        primary_doc_url = None
        if primary_doc:
            primary_doc_url = f"{SEC_ARCHIVES_URL}/{cik}/{accession_nodashes}/{primary_doc}"

        filing_index_url = f"{SEC_ARCHIVES_URL}/{cik}/{accession_nodashes}/"

        item = {
            "accessionNumber": accession,
            "cik": cik,
            "companyName": company_name,
            "form": recent.get("form", [])[idx] if idx < len(recent.get("form", [])) else None,
            "filingDate": recent.get("filingDate", [])[idx] if idx < len(recent.get("filingDate", [])) else None,
            "reportDate": recent.get("reportDate", [])[idx] if idx < len(recent.get("reportDate", [])) else None,
            "acceptanceDateTime": recent.get("acceptanceDateTime", [])[idx] if idx < len(recent.get("acceptanceDateTime", [])) else None,
            "primaryDocument": primary_doc,
            "primaryDocDescription": recent.get("primaryDocDescription", [])[idx] if idx < len(recent.get("primaryDocDescription", [])) else None,
            "primaryDocUrl": primary_doc_url,
            "filingIndexUrl": filing_index_url,
        }
        items.append(item)

    return items


def transform_to_filings(all_company_data: List[Tuple[str, dict]]) -> List[Dict[str, Any]]:
    """Transform SEC API responses to sec_edgar_filings dict format.

    Extracts all filings from all companies. No filtering by form type.
    """
    filings = []
    for cik, data in all_company_data:
        items = _extract_filings_from_submission(cik, data)

        for item in items:
            filing_date = item.get("filingDate")
            if not filing_date:
                continue

            accession = item.get("accessionNumber")
            if not accession:
                continue

            # Parse acceptanceDateTime (format: 2024-11-01T16:05:25.000Z)
            acceptance_dt = None
            raw_acceptance = item.get("acceptanceDateTime")
            if raw_acceptance:
                try:
                    acceptance_dt = raw_acceptance[:19].replace("T", " ")
                except (ValueError, IndexError):
                    pass

            filing = {
                'ticker_id': None,
                'symbol': None,
                'accession_number': accession,
                'cik': cik,
                'form_type': item.get("form"),
                'filing_date': filing_date,
                'report_date': item.get("reportDate") or None,
                'acceptance_datetime': acceptance_dt,
                'company_name': item.get("companyName"),
                'title': item.get("primaryDocDescription") or item.get("form") or "Untitled",
                'primary_document': item.get("primaryDocument"),
                'primary_doc_url': item.get("primaryDocUrl"),
                'filing_index_url': item.get("filingIndexUrl"),
                'pdf_s3_key': None,
                'raw_data': item,
            }
            filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings from {len(all_company_data)} companies")
    return filings


# ===========================================================================
# Opportunistic Ticker Matching
# ===========================================================================

def try_match_tickers(filings: List[Dict[str, Any]], resolver) -> int:
    """Match filings to DR tickers via CIK.

    All filings should match since we only fetch for our target CIKs,
    but we still do it defensively.
    """
    matched_count = 0

    for filing in filings:
        cik = filing.get('cik')
        if not cik:
            continue

        match = SEC_CIK_MAP.get(cik)
        if match is None:
            continue

        yahoo_symbol, dr_symbol = match

        ticker_info = resolver.resolve(yahoo_symbol)
        if ticker_info is None:
            logger.warning(f"TickerResolver cannot resolve {yahoo_symbol} for CIK={cik}")
            continue

        filing['ticker_id'] = ticker_info.ticker_id
        filing['symbol'] = dr_symbol
        matched_count += 1

    logger.info(f"Ticker matching: {matched_count}/{len(filings)} matched to DR tickers")
    return matched_count


# ===========================================================================
# Document Download to S3
# ===========================================================================

def download_documents(
    filings: List[Dict[str, Any]],
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 1.0,
) -> int:
    """Download primary filing documents and archive to S3."""
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping document downloads")
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    filings_with_doc = [f for f in filings if f.get('primary_doc_url')]
    logger.info(f"Downloading {len(filings_with_doc)} filing documents to S3...")

    for i, filing in enumerate(filings_with_doc):
        accession = filing['accession_number']
        primary_doc = filing.get('primary_document', 'document.htm')
        s3_key = f"sec-edgar-filings/documents/{accession}/{primary_doc}"

        try:
            try:
                data_lake.s3_client.head_object(
                    Bucket=data_lake.bucket_name,
                    Key=s3_key,
                )
                filing['pdf_s3_key'] = s3_key
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            resp = session.get(filing['primary_doc_url'], timeout=60)
            if resp.status_code != 200:
                logger.warning(
                    f"Document download failed HTTP {resp.status_code}: accession={accession}"
                )
                failed_count += 1
                continue

            content = resp.content
            content_type = resp.headers.get('Content-Type', 'text/html')

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'accession_number': accession,
                    'cik': filing.get('cik', ''),
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=sec-edgar&purpose=filing-archive",
            )

            filing['pdf_s3_key'] = s3_key
            archived_count += 1

            if (i + 1) % 100 == 0:
                logger.info(
                    f"Document progress: {i + 1}/{len(filings_with_doc)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"Document archive failed for accession={accession}: {e}")
            failed_count += 1

        if delay > 0 and i < len(filings_with_doc) - 1:
            time.sleep(delay)

    logger.info(
        f"Document download complete: "
        f"archived={archived_count}, skipped={skipped_count}, failed={failed_count}"
    )
    return archived_count


def download_docs_from_aurora(
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 1.0,
) -> int:
    """Download documents for filings already in Aurora that don't have pdf_s3_key yet."""
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping document downloads")
        return 0

    repo = get_sec_edgar_filings_repository()
    filings = repo.get_filings_needing_docs()
    logger.info(f"Found {len(filings)} filings needing document download")

    if not filings:
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    for i, filing in enumerate(filings):
        accession = filing['accession_number']
        doc_url = filing['primary_doc_url']
        # Extract filename from URL
        primary_doc = doc_url.rstrip('/').split('/')[-1] if doc_url else 'document.htm'
        s3_key = f"sec-edgar-filings/documents/{accession}/{primary_doc}"

        try:
            try:
                data_lake.s3_client.head_object(Bucket=data_lake.bucket_name, Key=s3_key)
                repo.update_pdf_s3_key(accession, s3_key)
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            resp = session.get(doc_url, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"Document download failed HTTP {resp.status_code}: accession={accession}")
                failed_count += 1
                continue

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=resp.content,
                ContentType=resp.headers.get('Content-Type', 'text/html'),
                Metadata={
                    'accession_number': accession,
                    'cik': filing.get('cik', ''),
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=sec-edgar&purpose=filing-archive",
            )

            repo.update_pdf_s3_key(accession, s3_key)
            archived_count += 1

            if (i + 1) % 100 == 0:
                logger.info(
                    f"Document progress: {i + 1}/{len(filings)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"Document archive failed for accession={accession}: {e}")
            failed_count += 1

        if delay > 0 and i < len(filings) - 1:
            time.sleep(delay)

    logger.info(
        f"Document download complete: "
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
    """Upload this script to S3 for provenance tracking."""
    script_path = Path(__file__)
    content = script_path.read_bytes()
    sha256_hex = hashlib.sha256(content).hexdigest()

    s3_key = f"scripts/data-acquisition/sec-edgar-filings/{version}.py"

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
        Tagging="type=script&purpose=data-acquisition&target=sec_edgar_filings",
    )

    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key} (sha256={sha256_hex[:12]}...)")
    return s3_key, sha256_hex


# ===========================================================================
# Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest SEC EDGAR filings into Aurora"
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and transform but do not write')
    parser.add_argument('--delay', type=float, default=0.2,
                        help='Delay between company API calls (default: 0.2s)')
    parser.add_argument('--version', type=str, default='v1',
                        help='Script version tag for provenance')
    parser.add_argument('--skip-self-archive', action='store_true',
                        help='Skip uploading script to S3')
    parser.add_argument('--skip-doc-download', action='store_true',
                        help='Skip downloading filing documents to S3')
    parser.add_argument('--doc-only', action='store_true',
                        help='Document-only mode: query Aurora, download docs, skip API')
    parser.add_argument('--doc-delay', type=float, default=1.0,
                        help='Delay between document downloads (default: 1.0s)')
    parser.add_argument('--runtime-type', type=str, default=None,
                        help='Runtime type for ingestion_methods (auto-detected)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    mode = "doc-only" if args.doc_only else "full"
    logger.info("=" * 60)
    logger.info(f"SEC EDGAR Filings Ingestion (mode={mode})")
    if not args.doc_only:
        logger.info(f"  dry_run={args.dry_run}, companies={len(TARGET_CIKS)}")
        logger.info(f"  skip_doc_download={args.skip_doc_download}, version={args.version}")
    else:
        logger.info(f"  Document-only: downloading docs for filings already in Aurora")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 0. Document-only mode
    # ------------------------------------------------------------------
    if args.doc_only:
        data_lake = DataLakeStorage()
        if not data_lake.enabled:
            logger.error("DATA_LAKE_BUCKET not configured")
            sys.exit(1)

        session = requests.Session()
        session.headers.update({'User-Agent': SEC_USER_AGENT})
        docs_archived = download_docs_from_aurora(data_lake, session, delay=args.doc_delay)

        logger.info("=" * 60)
        logger.info(f"DOC-ONLY COMPLETE: {docs_archived} documents archived to S3")
        logger.info("=" * 60)
        return

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
    # 2. Register ingestion method + start acquisition run
    # ------------------------------------------------------------------
    acq_repo = get_data_acquisitions_repository()
    acq_id = None
    ingestion_method_id = None

    if not args.dry_run:
        runtime_type = args.runtime_type or _detect_runtime_type()
        method_name = f"sec-edgar-{runtime_type}-{args.version}"
        try:
            methods_repo = get_ingestion_methods_repository()
            method = methods_repo.get_or_create(
                method_name=method_name,
                runtime_type=runtime_type,
                script_path='scripts/ingest_sec_edgar_filings.py',
                container_image=os.environ.get('CONTAINER_IMAGE'),
                description=f"SEC EDGAR filings ingestion via {runtime_type}",
            )
            ingestion_method_id = method['id']
            logger.info(f"Ingestion method: {method_name} (id={ingestion_method_id})")
        except Exception as e:
            logger.warning(f"Ingestion method registration failed (non-fatal): {e}")

        acq_id = acq_repo.start_run(
            source_table='sec_edgar_filings',
            source_type='script',
            source_name=SCRIPT_SOURCE_NAME,
            source_version=args.version,
            artifact_s3_key=artifact_s3_key,
            artifact_checksum=artifact_checksum,
            endpoint_url=SEC_SUBMISSIONS_URL,
            endpoint_version='v1',
            description=f"SEC EDGAR filings ingestion ({len(TARGET_CIKS)} companies)",
            parameters={
                'cik_count': len(TARGET_CIKS),
                'delay': args.delay,
                'skip_doc_download': args.skip_doc_download,
            },
            ingestion_method_id=ingestion_method_id,
        )
        logger.info(f"Started acquisition run: id={acq_id}")

    records_fetched = 0
    records_upserted = 0
    matched_count = 0
    docs_archived = 0

    try:
        # ------------------------------------------------------------------
        # 3. Fetch filings for all companies
        # ------------------------------------------------------------------
        session = requests.Session()
        session.headers.update({'User-Agent': SEC_USER_AGENT})

        logger.info(f"Fetching filings for {len(TARGET_CIKS)} companies...")
        all_company_data = fetch_all_company_filings(
            session, TARGET_CIKS, delay=args.delay
        )

        # ------------------------------------------------------------------
        # 4. Transform ALL filings
        # ------------------------------------------------------------------
        filings = transform_to_filings(all_company_data)
        records_fetched = len(filings)
        logger.info(f"Total filings: {records_fetched}")

        # ------------------------------------------------------------------
        # 5. Opportunistic ticker matching
        # ------------------------------------------------------------------
        logger.info("Matching filings to DR tickers...")
        resolver = get_ticker_resolver()
        matched_count = try_match_tickers(filings, resolver)

        # ------------------------------------------------------------------
        # 6. Download documents to S3
        # ------------------------------------------------------------------
        if not args.dry_run and not args.skip_doc_download:
            if data_lake is None:
                data_lake = DataLakeStorage()
            if data_lake.enabled:
                docs_archived = download_documents(
                    filings, data_lake, session, delay=args.doc_delay
                )
            else:
                logger.warning("Data lake not configured, skipping document downloads")

        # ------------------------------------------------------------------
        # 7. Dry run summary or upsert
        # ------------------------------------------------------------------
        if args.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN -- No data written")
            logger.info(f"  Total filings fetched:    {records_fetched}")
            logger.info(f"  Matched to DR tickers:    {matched_count}")
            logger.info("")
            # Show form_type breakdown
            form_counts: Dict[str, int] = {}
            for f in filings:
                ft = f.get('form_type') or 'unknown'
                form_counts[ft] = form_counts.get(ft, 0) + 1
            for ft, count in sorted(form_counts.items(), key=lambda x: -x[1])[:15]:
                logger.info(f"  {ft:20s} {count:5d}")
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=0, records_upserted=0)
            return

        filings_repo = get_sec_edgar_filings_repository()
        records_upserted = filings_repo.batch_upsert(
            filings, acquisition_id=acq_id
        )
        logger.info(f"Batch upsert complete: {records_upserted} rows affected")

        # ------------------------------------------------------------------
        # 8. Complete acquisition
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
    logger.info(f"  Companies:            {len(TARGET_CIKS)}")
    logger.info(f"  Filings fetched:      {records_fetched}")
    logger.info(f"  Filings upserted:     {records_upserted}")
    logger.info(f"  DR ticker matches:    {matched_count}")
    logger.info(f"  Documents archived:   {docs_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:       {acq_id}")
    if artifact_s3_key:
        logger.info(f"  Script artifact:      {artifact_s3_key}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
