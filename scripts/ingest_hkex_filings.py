#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HKEX Filings Ingestion Script

Fetches ALL filings from HKEXnews (undocumented Servlet API) for tracked
HK tickers, matches to DR tickers, optionally downloads filing documents
to S3, and stores everything in Aurora.

Usage:
    ENV=dev doppler run -- python -m scripts.ingest_hkex_filings --skip-doc-download
    ENV=dev doppler run -- python -m scripts.ingest_hkex_filings --dry-run --days-back 30
    ENV=dev doppler run -- python -m scripts.ingest_hkex_filings --doc-only

Architecture:
    HKEXnews Servlet API -> this script -> Aurora hkex_filings table
                                         -> Aurora data_acquisitions (provenance)
                                         -> S3 data lake (documents)
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.data.aurora.data_acquisitions_repository import get_data_acquisitions_repository
from src.data.aurora.hkex_filings_repository import get_hkex_filings_repository
from src.data.aurora.ingestion_methods_repository import get_ingestion_methods_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

HKEX_BASE_URL = "https://www1.hkexnews.hk"
HKEX_PREFIX_URL = f"{HKEX_BASE_URL}/search/prefix.do"
HKEX_SEARCH_URL = f"{HKEX_BASE_URL}/search/titleSearchServlet.do"

SCRIPT_SOURCE_NAME = "hkex_filings_ingester"

PAGE_SIZE = 100

# HKEX stock code (5-digit) -> (yahoo_symbol, dr_symbol)
HKEX_STOCK_MAP = {
    "00700": ("0700.HK", "TENCENT19"),
    "00941": ("0941.HK", "CHMOBILE19"),
    "01810": ("1810.HK", "XIAOMI19"),
    "03690": ("3690.HK", "MEITUAN19"),
    "06690": ("6690.HK", "HAIERS19"),
    "01299": ("1299.HK", "AIA19"),
    "01378": ("1378.HK", "CHHONGQ19"),
    "01398": ("1398.HK", "ICBC19"),
    "02382": ("2382.HK", "SUNNY19"),
    "06618": ("6618.HK", "JDHEAL19"),
    "03692": ("3692.HK", "HANSOH19"),
    "01177": ("1177.HK", "SINOBIO19"),
}

# Extract the numeric part for prefix.do lookup
TARGET_CODES = list(HKEX_STOCK_MAP.keys())


# ===========================================================================
# API: Stock ID Resolution
# ===========================================================================

def resolve_stock_id(
    session: requests.Session,
    stock_code: str,
) -> Optional[int]:
    """Resolve HKEX stock code to internal stockId via prefix.do.

    Args:
        session: requests.Session
        stock_code: 5-digit code (e.g. '00700')

    Returns:
        stockId integer, or None if not found
    """
    # Strip leading zeros for the search (700, not 00700)
    search_name = stock_code.lstrip('0') or '0'

    try:
        resp = session.get(
            HKEX_PREFIX_URL,
            params={
                'callback': 'cb',
                'lang': 'EN',
                'type': 'A',
                'name': search_name,
                'market': 'SEHK',
            },
            timeout=15,
        )

        if resp.status_code != 200:
            logger.warning(f"prefix.do HTTP {resp.status_code} for {stock_code}")
            return None

        # Parse JSONP: callback({...}); or cb({...})
        text = resp.text.strip().rstrip(';')
        # Find the JSON object between the first ( and last )
        paren_start = text.find('(')
        paren_end = text.rfind(')')
        if paren_start == -1 or paren_end == -1 or paren_end <= paren_start:
            logger.warning(f"Cannot parse JSONP for {stock_code}: {text[:100]}")
            return None

        json_str = text[paren_start + 1:paren_end]
        data = json.loads(json_str)
        stock_infos = data.get('stockInfo', [])

        # Find exact match
        for info in stock_infos:
            if info.get('code') == stock_code:
                stock_id = info.get('stockId')
                logger.debug(f"Resolved {stock_code} -> stockId={stock_id} ({info.get('name')})")
                return stock_id

        logger.warning(f"No exact match for {stock_code} in prefix.do response")
        return None

    except Exception as e:
        logger.warning(f"prefix.do failed for {stock_code}: {e}")
        return None


# ===========================================================================
# API: Fetch Filings
# ===========================================================================

def fetch_filings_for_stock(
    session: requests.Session,
    stock_id: int,
    stock_code: str,
    date_from: str,
    date_to: str,
    delay: float = 0.5,
) -> List[dict]:
    """Fetch all filings for a stock via titleSearchServlet.do.

    Paginates through all results using rowRange.

    Args:
        stock_id: Internal stockId from prefix.do
        stock_code: 5-digit code (for logging)
        date_from: YYYYMMDD format
        date_to: YYYYMMDD format
        delay: Seconds between paginated requests

    Returns:
        List of filing items
    """
    all_items = []
    row_count = PAGE_SIZE

    while True:
        try:
            resp = session.get(
                HKEX_SEARCH_URL,
                params={
                    'sortDir': '0',
                    'sortByOptions': 'DateTime',
                    'lang': 'en',
                    'category': '0',
                    'market': 'SEHK',
                    'stockId': str(stock_id),
                    'documentType': '',
                    'fromDate': date_from,
                    'toDate': date_to,
                    'title': '',
                    'searchType': '0',
                    't1code': '-2',
                    't2Gcode': '-2',
                    't2code': '-2',
                    'rowRange': str(row_count),
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"titleSearchServlet HTTP {resp.status_code} for {stock_code} "
                    f"rowRange={row_count}"
                )
                break

            # Response may be JSON or may need content-type check
            resp_text = resp.text.strip()
            if not resp_text:
                logger.warning(f"Empty response for {stock_code} rowRange={row_count}")
                break

            try:
                data = json.loads(resp_text)
            except json.JSONDecodeError:
                # Maybe JSONP wrapped
                resp_text = resp_text.rstrip(';')
                paren_start = resp_text.find('(')
                paren_end = resp_text.rfind(')')
                if paren_start != -1 and paren_end > paren_start:
                    data = json.loads(resp_text[paren_start + 1:paren_end])
                else:
                    logger.warning(f"Cannot parse response for {stock_code}: {resp_text[:200]}")
                    break

            # The 'result' field is a JSON string that must be parsed again
            result_str = data.get('result', '[]')
            if isinstance(result_str, str):
                items = json.loads(result_str)
            else:
                items = result_str

            if not items:
                break

            all_items.extend(items)

            # Check if there are more pages
            has_next = data.get('hasNextRow', False)
            if isinstance(has_next, str):
                has_next = has_next.lower() == 'true'

            if not has_next:
                break

            row_count += PAGE_SIZE

            if delay > 0:
                time.sleep(delay)

        except Exception as e:
            logger.warning(f"titleSearchServlet failed for {stock_code} rowRange={row_count}: {e}")
            break

    return all_items


def fetch_all_filings(
    session: requests.Session,
    stock_codes: List[str],
    date_from: str,
    date_to: str,
    delay: float = 1.0,
) -> List[Tuple[str, List[dict]]]:
    """Fetch filings for all target stocks.

    Returns:
        List of (stock_code, items) tuples
    """
    results = []

    for i, code in enumerate(stock_codes):
        company_info = HKEX_STOCK_MAP.get(code, ("", ""))
        logger.info(f"Fetching {code} ({company_info[1]}) [{i + 1}/{len(stock_codes)}]")

        # Resolve stockId
        stock_id = resolve_stock_id(session, code)
        if stock_id is None:
            logger.warning(f"Cannot resolve stockId for {code}, skipping")
            continue

        time.sleep(0.3)

        # Fetch filings
        items = fetch_filings_for_stock(
            session, stock_id, code, date_from, date_to, delay=0.5
        )
        results.append((code, items))
        logger.info(f"  {code}: {len(items)} filings")

        if delay > 0 and i < len(stock_codes) - 1:
            time.sleep(delay)

    total = sum(len(items) for _, items in results)
    logger.info(f"Fetched {total} filings from {len(results)}/{len(stock_codes)} companies")
    return results


# ===========================================================================
# Transform
# ===========================================================================

def _parse_hkex_date(date_str: str) -> Optional[str]:
    """Parse HKEX date format (DD/MM/YYYY HH:MM or YYYYMMDD) to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        # Try DD/MM/YYYY HH:MM format
        if '/' in date_str:
            dt = datetime.strptime(date_str.split(' ')[0], '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        # Try YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            dt = datetime.strptime(date_str, '%Y%m%d')
            return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    return date_str[:10] if len(date_str) >= 10 else None


def transform_to_filings(
    all_stock_data: List[Tuple[str, List[dict]]],
) -> List[Dict[str, Any]]:
    """Transform HKEXnews API responses to hkex_filings dict format."""
    filings = []

    for stock_code, items in all_stock_data:
        for item in items:
            news_id = item.get('NEWS_ID') or item.get('newsId')
            if not news_id:
                continue

            date_time = item.get('DATE_TIME') or item.get('relTime', '')
            filing_date = _parse_hkex_date(date_time)
            if not filing_date:
                continue

            # Build document URL
            file_link = item.get('FILE_LINK') or item.get('webPath')
            file_url = None
            if file_link:
                if file_link.startswith('http'):
                    file_url = file_link
                else:
                    file_url = f"{HKEX_BASE_URL}{file_link}"

            file_type = item.get('FILE_TYPE') or item.get('ext')

            filing = {
                'ticker_id': None,
                'symbol': None,
                'news_id': str(news_id),
                'stock_code': item.get('STOCK_CODE', stock_code).split('<br/>')[0].split('/')[0],  # take first if dual-listed
                'filing_date': filing_date,
                'date_time': date_time,
                'category_code': item.get('t1Code'),
                'subcategory_code': item.get('t2Code'),
                'stock_name': (item.get('STOCK_NAME') or item.get('sn') or '').split('<br/>')[0],
                'title': item.get('TITLE') or item.get('title'),
                'long_text': item.get('LONG_TEXT') or item.get('lTxt'),
                'file_link': file_link,
                'file_url': file_url,
                'file_type': file_type,
                'pdf_s3_key': None,
                'raw_data': item,
            }
            filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings from {len(all_stock_data)} companies")
    return filings


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

        match = HKEX_STOCK_MAP.get(code)
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
# Document Download
# ===========================================================================

def download_documents(
    filings: List[Dict[str, Any]],
    data_lake: DataLakeStorage,
    session: requests.Session,
    delay: float = 1.0,
) -> int:
    if not data_lake.enabled:
        logger.warning("Data lake not configured, skipping document downloads")
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    filings_with_doc = [f for f in filings if f.get('file_url')]
    logger.info(f"Downloading {len(filings_with_doc)} filing documents to S3...")

    for i, filing in enumerate(filings_with_doc):
        news_id = filing['news_id']
        file_url = filing['file_url']
        filename = file_url.rstrip('/').split('/')[-1] or f"{news_id}.pdf"
        s3_key = f"hkex-filings/documents/{news_id}/{filename}"

        try:
            try:
                data_lake.s3_client.head_object(Bucket=data_lake.bucket_name, Key=s3_key)
                filing['pdf_s3_key'] = s3_key
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            resp = session.get(file_url, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"Document download failed HTTP {resp.status_code}: news_id={news_id}")
                failed_count += 1
                continue

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name,
                Key=s3_key,
                Body=resp.content,
                ContentType=resp.headers.get('Content-Type', 'application/pdf'),
                Metadata={
                    'news_id': news_id,
                    'stock_code': filing.get('stock_code', ''),
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=hkex&purpose=filing-archive",
            )

            filing['pdf_s3_key'] = s3_key
            archived_count += 1

            if (i + 1) % 50 == 0:
                logger.info(
                    f"Document progress: {i + 1}/{len(filings_with_doc)} "
                    f"(archived={archived_count}, skipped={skipped_count}, failed={failed_count})"
                )

        except Exception as e:
            logger.warning(f"Document archive failed for news_id={news_id}: {e}")
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
    if not data_lake.enabled:
        logger.warning("Data lake not configured")
        return 0

    repo = get_hkex_filings_repository()
    filings = repo.get_filings_needing_docs()
    logger.info(f"Found {len(filings)} filings needing document download")

    if not filings:
        return 0

    archived_count = 0
    skipped_count = 0
    failed_count = 0

    for i, filing in enumerate(filings):
        news_id = filing['news_id']
        file_url = filing['file_url']
        filename = file_url.rstrip('/').split('/')[-1] or f"{news_id}.pdf"
        s3_key = f"hkex-filings/documents/{news_id}/{filename}"

        try:
            try:
                data_lake.s3_client.head_object(Bucket=data_lake.bucket_name, Key=s3_key)
                repo.update_pdf_s3_key(news_id, s3_key)
                skipped_count += 1
                continue
            except data_lake.s3_client.exceptions.ClientError:
                pass

            resp = session.get(file_url, timeout=60)
            if resp.status_code != 200:
                failed_count += 1
                continue

            data_lake.s3_client.put_object(
                Bucket=data_lake.bucket_name, Key=s3_key, Body=resp.content,
                ContentType=resp.headers.get('Content-Type', 'application/pdf'),
                Metadata={'news_id': news_id, 'archived_at': datetime.now(timezone.utc).isoformat()},
                Tagging="type=document&source=hkex&purpose=filing-archive",
            )
            repo.update_pdf_s3_key(news_id, s3_key)
            archived_count += 1

            if (i + 1) % 50 == 0:
                logger.info(f"Document progress: {i+1}/{len(filings)} (archived={archived_count})")

        except Exception as e:
            logger.warning(f"Document archive failed for news_id={news_id}: {e}")
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
    s3_key = f"scripts/data-acquisition/hkex-filings/{version}.py"
    data_lake.s3_client.put_object(
        Bucket=data_lake.bucket_name, Key=s3_key, Body=content,
        ContentType='text/x-python',
        Metadata={'sha256': sha256_hex, 'source_file': script_path.name,
                  'archived_at': datetime.now(timezone.utc).isoformat()},
        Tagging="type=script&purpose=data-acquisition&target=hkex_filings",
    )
    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key}")
    return s3_key, sha256_hex


# ===========================================================================
# Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest HKEX filings into Aurora")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--days-back', type=int, default=365)
    parser.add_argument('--date-from', type=str, default=None, help='YYYYMMDD')
    parser.add_argument('--date-to', type=str, default=None, help='YYYYMMDD')
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--version', type=str, default='v1')
    parser.add_argument('--skip-self-archive', action='store_true')
    parser.add_argument('--skip-doc-download', action='store_true')
    parser.add_argument('--doc-only', action='store_true')
    parser.add_argument('--doc-delay', type=float, default=1.0)
    parser.add_argument('--runtime-type', type=str, default=None)
    parser.add_argument('--verbose', '-v', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Resolve date range (YYYYMMDD format for HKEX API)
    date_to_obj = date.today()
    if args.date_to:
        date_to_obj = datetime.strptime(args.date_to, '%Y%m%d').date()
    if args.date_from:
        date_from_obj = datetime.strptime(args.date_from, '%Y%m%d').date()
    else:
        date_from_obj = date_to_obj - timedelta(days=args.days_back)

    date_from_str = date_from_obj.strftime('%Y%m%d')
    date_to_str = date_to_obj.strftime('%Y%m%d')

    mode = "doc-only" if args.doc_only else "full"
    logger.info("=" * 60)
    logger.info(f"HKEX Filings Ingestion (mode={mode})")
    if not args.doc_only:
        logger.info(f"  dry_run={args.dry_run}, date_range={date_from_str} to {date_to_str}")
        logger.info(f"  companies={len(TARGET_CODES)}, version={args.version}")
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
        session = requests.Session()
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
        method_name = f"hkex-{runtime_type}-{args.version}"
        try:
            methods_repo = get_ingestion_methods_repository()
            method = methods_repo.get_or_create(
                method_name=method_name, runtime_type=runtime_type,
                script_path='scripts/ingest_hkex_filings.py',
                container_image=os.environ.get('CONTAINER_IMAGE'),
                description=f"HKEX filings ingestion via {runtime_type}",
            )
            ingestion_method_id = method['id']
        except Exception as e:
            logger.warning(f"Ingestion method registration failed (non-fatal): {e}")

        acq_id = acq_repo.start_run(
            source_table='hkex_filings', source_type='script',
            source_name=SCRIPT_SOURCE_NAME, source_version=args.version,
            artifact_s3_key=artifact_s3_key, artifact_checksum=artifact_checksum,
            endpoint_url=HKEX_SEARCH_URL, endpoint_version='v1',
            description=f"HKEX filings ingestion ({date_from_str} to {date_to_str})",
            parameters={'date_from': date_from_str, 'date_to': date_to_str,
                        'stock_count': len(TARGET_CODES), 'delay': args.delay},
            ingestion_method_id=ingestion_method_id,
        )
        logger.info(f"Started acquisition run: id={acq_id}")

    records_fetched = 0
    records_upserted = 0
    matched_count = 0
    docs_archived = 0

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www1.hkexnews.hk/search/titlesearch.xhtml',
        })

        logger.info(f"Fetching filings for {len(TARGET_CODES)} companies...")
        all_stock_data = fetch_all_filings(
            session, TARGET_CODES, date_from_str, date_to_str, delay=args.delay
        )

        filings = transform_to_filings(all_stock_data)
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
                count = sum(1 for _, items in all_stock_data for _ in items if True)
                # Per-company count
            for code, items in all_stock_data:
                info = HKEX_STOCK_MAP.get(code, ('', ''))
                logger.info(f"  {code} ({info[1]:14s}): {len(items)} filings")
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=0, records_upserted=0)
            return

        filings_repo = get_hkex_filings_repository()
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
    logger.info(f"  Filings fetched:      {records_fetched}")
    logger.info(f"  Filings upserted:     {records_upserted}")
    logger.info(f"  DR ticker matches:    {matched_count}")
    logger.info(f"  Documents archived:   {docs_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:       {acq_id}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
