#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOSE Filings Ingestion Script

Fetches annual and quarterly report filings for tracked Vietnamese tickers
from Vietstock CDN (static2.vietstock.vn) and CafeF API (cafef.vn),
matches to DR tickers, optionally downloads filing documents to S3,
and stores everything in Aurora.

Usage:
    ENV=dev doppler run -- python -m scripts.ingest_hose_filings --skip-doc-download
    ENV=dev doppler run -- python -m scripts.ingest_hose_filings --dry-run --days-back 365 --verbose
    ENV=dev doppler run -- python -m scripts.ingest_hose_filings --doc-only
    ENV=dev doppler run -- python -m scripts.ingest_hose_filings --dry-run --ticker VNM --verbose

Architecture:
    Vietstock CDN (VNM/FPT/VCB/HPG) ─┐
    CafeF API (MWG/VHM) ─────────────┼→ this script → Aurora hose_filings table
                                      │              → Aurora data_acquisitions (provenance)
                                      │              → S3 data lake (documents)
"""

import argparse
import hashlib
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
from src.data.aurora.hose_filings_repository import get_hose_filings_repository
from src.data.aurora.ingestion_methods_repository import get_ingestion_methods_repository
from src.data.aurora.ticker_resolver import get_ticker_resolver
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================

VIETSTOCK_CDN_BASE = "https://static2.vietstock.vn"
VIETSTOCK_DATA_CDN = f"{VIETSTOCK_CDN_BASE}/data"

SCRIPT_SOURCE_NAME = "hose_filings_ingester"

# HOSE ticker code -> (yahoo_symbol, dr_symbol)
HOSE_TICKER_MAP = {
    "VNM": ("VNM.VN", "VNM19"),
    "FPT": ("FPT.VN", "FPTVN19"),
    "VCB": ("VCB.VN", "VCB19"),
    "MWG": ("MWG.VN", "MWG19"),
    "HPG": ("HPG.VN", "HPG19"),
    "VHM": ("VHM.VN", "VHM19"),
}

TARGET_TICKERS = list(HOSE_TICKER_MAP.keys())

# Tickers confirmed available on Vietstock CDN
VIETSTOCK_CDN_TICKERS = {"VNM", "FPT", "VCB", "HPG"}
# CafeF API (fallback for tickers not on Vietstock CDN)
CAFEF_API_URL = "https://cafef.vn/du-lieu/ajax/ajaxcongbothongtin.ashx"
CAFEF_CDN_PREFIX = "https://cafefnew.mediacdn.vn/Images/Uploaded/DuLieuDownload/BCTC/"
CAFEF_TICKERS = {"MWG", "VHM"}

# Quarterly CDN filename patterns (try in order, stop on first hit)
# Example: static2.vietstock.vn/data/HOSE/2024/BCTC/VN/QUY%201/VNM_Baocaotaichinh_Q1_2024.pdf
QUARTERLY_FILENAME_PATTERNS = [
    "{ticker}_Baocaotaichinh_Q{quarter}_{year}.pdf",
    "{ticker}_FinancialStatement_Q{quarter}_{year}.pdf",
    "{ticker}_FinancialReport_Q{quarter}_{year}.pdf",
]

# Annual CDN URL template (requires date probing)
# Example: static2.vietstock.vn/vietstock/2025/3/21/20250321_vnm_250321_annual_report_2024.pdf
ANNUAL_REPORT_TEMPLATE = (
    "{base}/vietstock/{y}/{m}/{d}/"
    "{y}{m:02d}{d:02d}_{ticker_lower}_{yy}{m:02d}{d:02d}_annual_report_{fy}.pdf"
)

# Quarter end dates for synthetic filing_date
QUARTER_END_DATES = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}

# Priority month order for annual report probing (March/April most common)
ANNUAL_PROBE_MONTHS = [3, 4, 2, 5, 6]


# ===========================================================================
# Layer 1: Vietstock CDN Fetch
# ===========================================================================

def _head_probe(session: requests.Session, url: str) -> bool:
    """HEAD-probe a URL. Returns True if resource exists (HTTP 200)."""
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _build_quarterly_item(ticker: str, year: int, quarter: int, url: str, doc_path: str) -> dict:
    """Build a synthetic item dict matching the Layer 2 contract."""
    filing_date = f"{year}-{QUARTER_END_DATES[quarter]}"
    return {
        'news_id': f"vs-q{quarter}-{year}-{ticker}",
        'tickerCode': ticker,
        'publishDate': filing_date,
        'title': f"{ticker} - Q{quarter} {year} Financial Report",
        'companyName': '',
        'file_url': url,
        'document_path': doc_path,
        'newsType': 'quarterly_report',
        'source': 'vietstock_cdn',
    }


def _build_annual_item(ticker: str, fiscal_year: int, url: str, doc_path: str, upload_date: str) -> dict:
    """Build a synthetic item dict matching the Layer 2 contract."""
    return {
        'news_id': f"vs-annual-{fiscal_year}-{ticker}",
        'tickerCode': ticker,
        'publishDate': upload_date,
        'title': f"{ticker} - Annual Report {fiscal_year}",
        'companyName': '',
        'file_url': url,
        'document_path': doc_path,
        'newsType': 'annual_report',
        'source': 'vietstock_cdn',
    }


def fetch_quarterly_reports_from_cdn(
    session: requests.Session,
    ticker_codes: List[str],
    years: List[int],
    quarters: Optional[List[int]] = None,
    delay: float = 0.3,
) -> List[dict]:
    """Probe Vietstock CDN for quarterly financial reports.

    Constructs predictable CDN URLs and HEAD-probes each.
    Cost: len(tickers) x len(years) x 4 quarters x 3 patterns max.

    Returns:
        List of synthetic item dicts for discovered reports.
    """
    if quarters is None:
        quarters = [1, 2, 3, 4]

    items: List[dict] = []
    probes = 0

    for ticker in ticker_codes:
        for year in years:
            for quarter in quarters:
                found = False
                for pattern in QUARTERLY_FILENAME_PATTERNS:
                    filename = pattern.format(ticker=ticker, quarter=quarter, year=year)
                    doc_path = f"/data/HOSE/{year}/BCTC/VN/QUY%20{quarter}/{filename}"
                    url = f"{VIETSTOCK_DATA_CDN}/HOSE/{year}/BCTC/VN/QUY%20{quarter}/{filename}"
                    probes += 1

                    if _head_probe(session, url):
                        items.append(_build_quarterly_item(ticker, year, quarter, url, doc_path))
                        logger.debug(f"Found quarterly: {ticker} Q{quarter} {year}")
                        found = True
                        break

                    if delay > 0:
                        time.sleep(delay)

                if found and delay > 0:
                    time.sleep(delay)

    logger.info(f"Quarterly CDN probe: {len(items)} found in {probes} probes")
    return items


def fetch_annual_reports_from_cdn(
    session: requests.Session,
    ticker_codes: List[str],
    fiscal_years: List[int],
    delay: float = 0.3,
) -> List[dict]:
    """Probe Vietstock CDN for annual reports.

    Annual report URLs include the upload date, so we probe a window
    of months (Feb–Jun of fiscal_year+1) to discover the exact date.

    Returns:
        List of synthetic item dicts for discovered reports.
    """
    items: List[dict] = []
    probes = 0

    for ticker in ticker_codes:
        ticker_lower = ticker.lower()
        for fy in fiscal_years:
            probe_year = fy + 1
            yy = str(probe_year)[-2:]  # e.g. 2025 -> "25"
            found = False

            for month in ANNUAL_PROBE_MONTHS:
                if found:
                    break
                for day in range(1, 29):
                    url = ANNUAL_REPORT_TEMPLATE.format(
                        base=VIETSTOCK_CDN_BASE,
                        y=probe_year, m=month, d=day,
                        ticker_lower=ticker_lower, yy=yy, fy=fy,
                    )
                    doc_path = url.replace(VIETSTOCK_CDN_BASE, '')
                    probes += 1

                    if _head_probe(session, url):
                        upload_date = f"{probe_year}-{month:02d}-{day:02d}"
                        items.append(_build_annual_item(ticker, fy, url, doc_path, upload_date))
                        logger.debug(f"Found annual: {ticker} FY{fy} uploaded {upload_date}")
                        found = True
                        break

                    if delay > 0:
                        time.sleep(delay)

    logger.info(f"Annual CDN probe: {len(items)} found in {probes} probes")
    return items


# ===========================================================================
# Layer 1b: CafeF API Fetch (MWG, VHM)
# ===========================================================================

def _parse_cafef_date(date_val: str) -> Optional[str]:
    """Parse CafeF .NET date format '/Date(1770003434246)/' to YYYY-MM-DD."""
    if not date_val:
        return None
    match = re.search(r'/Date\((\d+)\)/', str(date_val))
    if match:
        ts_ms = int(match.group(1))
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.strftime('%Y-%m-%d')
    return None


def _cafef_file_url(filename: str) -> str:
    """Normalize CafeF FileName to absolute URL."""
    if filename.startswith('http'):
        return filename
    return CAFEF_CDN_PREFIX + filename


def fetch_filings_from_cafef(
    session: requests.Session,
    ticker_codes: List[str],
    years: List[int],
    delay: float = 1.0,
) -> Tuple[List[dict], List[dict]]:
    """Fetch filings from CafeF API for tickers not on Vietstock CDN.

    CafeF API returns JSON with filing metadata and direct PDF URLs.
    Quarter values: 1-4 = quarterly, 5 = annual/full-year.

    Returns:
        Tuple of (annual_items, quarterly_items) as synthetic item dicts.
    """
    annual_items: List[dict] = []
    quarterly_items: List[dict] = []
    year_set = set(years)

    for ticker in ticker_codes:
        try:
            resp = session.get(
                CAFEF_API_URL,
                params={
                    'symbol': ticker,
                    'pageindex': 1,
                    'pagesize': 100,
                    'reporttype': 'H',
                    'startdate': '',
                    'enddate': '',
                    'center': 1,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"CafeF API HTTP {resp.status_code} for {ticker}")
                continue

            data = resp.json()
            if not data.get('Success'):
                logger.warning(f"CafeF API returned Success=false for {ticker}")
                continue

            bctc_list = data.get('Data', {}).get('BctcList', [])
            if not bctc_list:
                logger.debug(f"CafeF: no filings for {ticker}")
                continue

            for item in bctc_list:
                item_year = item.get('Year')
                if item_year not in year_set:
                    continue

                quarter = item.get('Quarter')
                filename = item.get('FileName', '')
                if not filename:
                    continue

                file_url = _cafef_file_url(filename)
                doc_path = file_url.replace('https://cafefnew.mediacdn.vn', '')
                publish_date = _parse_cafef_date(item.get('CreateDate'))
                company_name = item.get('CompanyName', '')
                title = item.get('Content', '')

                if quarter == 5:
                    news_id = f"cafef-annual-{item_year}-{ticker}"
                    news_type = 'annual_report'
                    if not publish_date:
                        publish_date = f"{item_year}-12-31"
                    synthetic = {
                        'news_id': news_id,
                        'tickerCode': ticker,
                        'publishDate': publish_date,
                        'title': title or f"{ticker} - Annual Report {item_year}",
                        'companyName': company_name,
                        'file_url': file_url,
                        'document_path': doc_path,
                        'newsType': news_type,
                        'source': 'cafef',
                    }
                    annual_items.append(synthetic)
                    logger.debug(f"CafeF annual: {ticker} FY{item_year}")
                elif quarter in (1, 2, 3, 4):
                    news_id = f"cafef-q{quarter}-{item_year}-{ticker}"
                    news_type = 'quarterly_report'
                    if not publish_date:
                        publish_date = f"{item_year}-{QUARTER_END_DATES[quarter]}"
                    synthetic = {
                        'news_id': news_id,
                        'tickerCode': ticker,
                        'publishDate': publish_date,
                        'title': title or f"{ticker} - Q{quarter} {item_year} Financial Report",
                        'companyName': company_name,
                        'file_url': file_url,
                        'document_path': doc_path,
                        'newsType': news_type,
                        'source': 'cafef',
                    }
                    quarterly_items.append(synthetic)
                    logger.debug(f"CafeF quarterly: {ticker} Q{quarter} {item_year}")

        except Exception as e:
            logger.warning(f"CafeF fetch failed for {ticker}: {e}")

        if delay > 0:
            time.sleep(delay)

    logger.info(
        f"CafeF API: {len(annual_items)} annual + "
        f"{len(quarterly_items)} quarterly for {len(ticker_codes)} tickers"
    )
    return annual_items, quarterly_items


# ===========================================================================
# Layer 1 Orchestration
# ===========================================================================

def fetch_all_filings(
    session: requests.Session,
    date_from: str,
    date_to: str,
    delay: float = 1.0,
) -> Tuple[List[dict], List[dict]]:
    """Fetch all filing types from Vietstock CDN + CafeF API.

    Routes tickers to appropriate data source:
    - VNM, FPT, VCB, HPG → Vietstock CDN (HEAD probing)
    - MWG, VHM → CafeF API (JSON)

    Returns:
        Tuple of (annual_reports, quarterly_reports)
    """
    year_from = int(date_from[:4])
    year_to = int(date_to[:4])
    years = list(range(year_from, year_to + 1))

    # Source 1: Vietstock CDN
    cdn_tickers = [t for t in TARGET_TICKERS if t in VIETSTOCK_CDN_TICKERS]
    logger.info(f"Probing Vietstock CDN for {len(cdn_tickers)} tickers, years {years}")

    quarterly = fetch_quarterly_reports_from_cdn(
        session, cdn_tickers, years, delay=delay,
    )
    annual = fetch_annual_reports_from_cdn(
        session, cdn_tickers, years, delay=delay,
    )

    # Source 2: CafeF API
    cafef_tickers = [t for t in TARGET_TICKERS if t in CAFEF_TICKERS]
    if cafef_tickers:
        logger.info(f"Fetching CafeF API for {len(cafef_tickers)} tickers: {', '.join(cafef_tickers)}")
        cafef_annual, cafef_quarterly = fetch_filings_from_cafef(
            session, cafef_tickers, years, delay=delay,
        )
        annual.extend(cafef_annual)
        quarterly.extend(cafef_quarterly)

    logger.info(
        f"Total fetched: {len(annual)} annual + "
        f"{len(quarterly)} quarterly = "
        f"{len(annual) + len(quarterly)} filings"
    )
    return annual, quarterly


# ===========================================================================
# Layer 2: Transform
# ===========================================================================

def _parse_hose_date(date_val: Any) -> Optional[str]:
    """Parse HOSE date to YYYY-MM-DD format.

    Handles multiple formats:
    - ISO datetime string (2026-03-15T00:00:00)
    - YYYY-MM-DD string
    - Unix timestamp (milliseconds)
    - DD/MM/YYYY string
    """
    if not date_val:
        return None

    if isinstance(date_val, (int, float)):
        try:
            dt = datetime.fromtimestamp(date_val / 1000, tz=timezone.utc)
            return dt.strftime('%Y-%m-%d')
        except (ValueError, OSError):
            return None

    date_str = str(date_val)
    try:
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        if '/' in date_str:
            dt = datetime.strptime(date_str.split(' ')[0], '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        if len(date_str) >= 10 and date_str[4] == '-':
            return date_str[:10]
    except ValueError:
        pass

    return date_str[:10] if len(date_str) >= 10 else None


def _classify_report_type(item: dict, endpoint: str) -> str:
    """Classify report type from endpoint or title patterns."""
    if endpoint == 'annual_report':
        return 'annual_report'

    title = (item.get('title') or item.get('newTitle') or '').lower()

    if any(kw in title for kw in ['annual', 'bao cao thuong nien', 'báo cáo thường niên']):
        return 'annual_report'
    if any(kw in title for kw in ['quarterly', 'quy', 'quý', 'bao cao tai chinh', 'báo cáo tài chính']):
        return 'quarterly_report'

    return 'other'


def _extract_ticker_from_title(title: str) -> Optional[str]:
    """Extract ticker code from filing title.

    HOSE filing titles often contain ticker codes like:
    'VNM - Annual Report 2025' or 'FPT Corporation quarterly report'
    """
    if not title:
        return None

    title_upper = title.upper()
    for ticker_code in HOSE_TICKER_MAP:
        # Match ticker at word boundary: "VNM - ...", "VNM:", "VNM ", start of string
        pattern = r'(?:^|[\s\-:,.(])' + re.escape(ticker_code) + r'(?:[\s\-:,.)_]|$)'
        if re.search(pattern, title_upper):
            return ticker_code

    return None


def _build_file_url(item: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extract document path and build full URL from item.

    Vietstock CDN items already have absolute file_url; legacy HOSE API
    items have a relative documentPath that needs a base URL prefix.

    Returns:
        Tuple of (document_path, file_url)
    """
    # Vietstock CDN items: file_url is already absolute
    file_url = item.get('file_url')
    if file_url and file_url.startswith('http'):
        return item.get('document_path'), file_url

    # Legacy fallback: relative document path
    doc_path = (
        item.get('documentPath')
        or item.get('document_path')
        or item.get('filePath')
        or item.get('file_path')
    )

    if not doc_path:
        return None, None

    clean_path = doc_path.replace('~', '')
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path

    full_url = f"{VIETSTOCK_CDN_BASE}{clean_path}"
    return doc_path, full_url


def transform_to_filings(
    annual_reports: List[dict],
    quarterly_reports: List[dict],
) -> List[Dict[str, Any]]:
    """Transform HOSE API responses to hose_filings dict format."""
    filings = []
    seen_ids = set()

    for endpoint, items in [('annual_report', annual_reports), ('quarterly_report', quarterly_reports)]:
        for item in items:
            news_id = str(
                item.get('newsId')
                or item.get('news_id')
                or item.get('id')
                or ''
            )
            if not news_id:
                continue
            if news_id in seen_ids:
                continue
            seen_ids.add(news_id)

            date_val = (
                item.get('publishDate')
                or item.get('publish_date')
                or item.get('createdDate')
                or item.get('created_date')
                or item.get('newsDate')
            )
            filing_date = _parse_hose_date(date_val)
            if not filing_date:
                continue

            title = item.get('newTitle') or item.get('title') or item.get('newsTitle') or ''
            ticker_code = (
                item.get('tickerCode')
                or item.get('ticker_code')
                or item.get('stockCode')
                or _extract_ticker_from_title(title)
            )

            document_path, file_url = _build_file_url(item)
            report_type = _classify_report_type(item, endpoint)
            category_alias = 'annual-report' if endpoint == 'annual_report' else 'bao-cao-tai-chinh'

            filing = {
                'ticker_id': None,
                'symbol': None,
                'news_id': news_id,
                'ticker_code': ticker_code,
                'filing_date': filing_date,
                'news_type': item.get('newsType') or item.get('type'),
                'report_type': report_type,
                'related_id': str(item.get('relatedId') or item.get('related_id') or ''),
                'category_alias': category_alias,
                'company_name': item.get('companyName') or item.get('company_name') or '',
                'title': title,
                'document_path': document_path,
                'file_url': file_url,
                'pdf_s3_key': None,
                'raw_data': item,
            }

            # Clean empty strings to None
            for key in ('ticker_code', 'related_id', 'company_name'):
                if filing[key] == '':
                    filing[key] = None

            filings.append(filing)

    logger.info(f"Transformed {len(filings)} filings ({len(annual_reports)} annual + {len(quarterly_reports)} quarterly)")
    return filings


# ===========================================================================
# Layer 3: Ticker Matching
# ===========================================================================

def try_match_tickers(filings: List[Dict[str, Any]], resolver) -> int:
    """Match filings to DR tickers via ticker_code or title extraction."""
    matched_count = 0

    for filing in filings:
        code = filing.get('ticker_code')
        if not code:
            continue

        match = HOSE_TICKER_MAP.get(code)
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
# Layer 4: Document Download
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
        s3_key = f"hose-filings/documents/{news_id}/{filename}"

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
                    'ticker_code': filing.get('ticker_code') or '',
                    'archived_at': datetime.now(timezone.utc).isoformat(),
                },
                Tagging="type=document&source=hose&purpose=filing-archive",
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

    repo = get_hose_filings_repository()
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
        s3_key = f"hose-filings/documents/{news_id}/{filename}"

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
                Tagging="type=document&source=hose&purpose=filing-archive",
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
# Layer 5: Runtime Detection + S3 Self-Archive
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
    s3_key = f"scripts/data-acquisition/hose-filings/{version}.py"
    data_lake.s3_client.put_object(
        Bucket=data_lake.bucket_name, Key=s3_key, Body=content,
        ContentType='text/x-python',
        Metadata={'sha256': sha256_hex, 'source_file': script_path.name,
                  'archived_at': datetime.now(timezone.utc).isoformat()},
        Tagging="type=script&purpose=data-acquisition&target=hose_filings",
    )
    logger.info(f"Self-archived to s3://{data_lake.bucket_name}/{s3_key}")
    return s3_key, sha256_hex


# ===========================================================================
# Layer 6: Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest HOSE filings from Vietstock CDN + CafeF into Aurora")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--days-back', type=int, default=365)
    parser.add_argument('--date-from', type=str, default=None, help='YYYY-MM-DD')
    parser.add_argument('--date-to', type=str, default=None, help='YYYY-MM-DD')
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--version', type=str, default='v1')
    parser.add_argument('--skip-self-archive', action='store_true')
    parser.add_argument('--skip-doc-download', action='store_true')
    parser.add_argument('--doc-only', action='store_true')
    parser.add_argument('--doc-delay', type=float, default=1.0)
    parser.add_argument('--runtime-type', type=str, default=None)
    parser.add_argument('--ticker', type=str, default=None, help='Filter single ticker code (e.g. VNM)')
    parser.add_argument('--verbose', '-v', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    # Resolve date range
    date_to_obj = date.today()
    if args.date_to:
        date_to_obj = datetime.strptime(args.date_to, '%Y-%m-%d').date()
    if args.date_from:
        date_from_obj = datetime.strptime(args.date_from, '%Y-%m-%d').date()
    else:
        date_from_obj = date_to_obj - timedelta(days=args.days_back)

    date_from_str = date_from_obj.strftime('%Y-%m-%d')
    date_to_str = date_to_obj.strftime('%Y-%m-%d')

    mode = "doc-only" if args.doc_only else "full"
    logger.info("=" * 60)
    logger.info(f"HOSE Filings Ingestion via Vietstock CDN + CafeF (mode={mode})")
    if not args.doc_only:
        logger.info(f"  dry_run={args.dry_run}, date_range={date_from_str} to {date_to_str}")
        logger.info(f"  tickers={len(TARGET_TICKERS)}, version={args.version}")
        if args.ticker:
            logger.info(f"  filter_ticker={args.ticker}")
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
        method_name = f"hose-{runtime_type}-{args.version}"
        try:
            methods_repo = get_ingestion_methods_repository()
            method = methods_repo.get_or_create(
                method_name=method_name, runtime_type=runtime_type,
                script_path='scripts/ingest_hose_filings.py',
                container_image=os.environ.get('CONTAINER_IMAGE'),
                description=f"HOSE filings ingestion via {runtime_type}",
            )
            ingestion_method_id = method['id']
        except Exception as e:
            logger.warning(f"Ingestion method registration failed (non-fatal): {e}")

        acq_id = acq_repo.start_run(
            source_table='hose_filings', source_type='script',
            source_name=SCRIPT_SOURCE_NAME, source_version=args.version,
            artifact_s3_key=artifact_s3_key, artifact_checksum=artifact_checksum,
            endpoint_url=VIETSTOCK_CDN_BASE, endpoint_version='v1',
            description=f"HOSE filings ingestion via Vietstock CDN + CafeF ({date_from_str} to {date_to_str})",
            parameters={'date_from': date_from_str, 'date_to': date_to_str,
                        'ticker_count': len(TARGET_TICKERS), 'delay': args.delay,
                        'cdn_tickers': sorted(VIETSTOCK_CDN_TICKERS),
                        'cafef_tickers': sorted(CAFEF_TICKERS)},
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
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        })

        logger.info(f"Fetching filings for {len(TARGET_TICKERS)} tickers...")
        annual_reports, quarterly_reports = fetch_all_filings(
            session, date_from_str, date_to_str, delay=args.delay,
        )

        filings = transform_to_filings(annual_reports, quarterly_reports)

        # Filter by ticker if specified
        if args.ticker:
            ticker_upper = args.ticker.upper()
            filings = [f for f in filings if f.get('ticker_code') == ticker_upper]
            logger.info(f"Filtered to {len(filings)} filings for ticker={ticker_upper}")

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
            logger.info(f"  Annual reports: {len(annual_reports)}")
            logger.info(f"  Quarterly reports: {len(quarterly_reports)}")
            for code in TARGET_TICKERS:
                count = sum(1 for f in filings if f.get('ticker_code') == code)
                info = HOSE_TICKER_MAP.get(code, ('', ''))
                logger.info(f"  {code:6s} ({info[1]:10s}): {count} filings")
            logger.info("=" * 60)
            return

        if not filings:
            logger.info("No filings to upsert")
            if acq_id:
                acq_repo.complete_run(acq_id, records_fetched=0, records_upserted=0)
            return

        filings_repo = get_hose_filings_repository()
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
    logger.info(f"  Tickers:              {len(TARGET_TICKERS)}")
    logger.info(f"  Filings fetched:      {records_fetched}")
    logger.info(f"  Filings upserted:     {records_upserted}")
    logger.info(f"  DR ticker matches:    {matched_count}")
    logger.info(f"  Documents archived:   {docs_archived}")
    if acq_id:
        logger.info(f"  Acquisition ID:       {acq_id}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
