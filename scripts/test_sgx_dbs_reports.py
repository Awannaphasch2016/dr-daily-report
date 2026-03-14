#!/usr/bin/env python3
"""
SGX Financial Reports API exploration.

Discovered: https://api.sgx.com/financialreports/v1.0 works without WAF issues.
Returns structured financial reports with companyName, title, url, documentDate.

Goal: Find DBS annual and quarterly reports.
"""

import json
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

SGX_CONFIG_URL = "https://www.sgx.com/config/appconfig.json"
SGX_CMS_API_URL = "https://api2.sgx.com/content-api"
SGX_FIN_REPORTS_URL = "https://api.sgx.com/financialreports/v1.0"

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


def rot13(text: str) -> str:
    return "".join(
        chr((ord(c) - (base := (ord('a') if c.islower() else ord('A'))) + 13) % 26 + base)
        if c.isalpha() else c
        for c in text
    )


def safe_json(resp):
    text = resp.text.strip()
    if text.startswith("{}&&"):
        text = text[4:]
    return json.loads(text)


def get_token(session):
    resp = session.get(SGX_CONFIG_URL, timeout=10)
    config = safe_json(resp)
    cms_version = config.get("CMS_VERSION", "")
    time.sleep(3)

    token_url = f"{SGX_CMS_API_URL}/?queryId={cms_version}:we_chat_qr_validator"
    resp = session.get(token_url, timeout=10)
    data = safe_json(resp)
    qr_val = data.get("qrValidator")
    if not qr_val and "data" in data:
        d = data["data"]
        if isinstance(d, dict):
            qr_val = d.get("qrValidator")
        elif isinstance(d, list) and d:
            qr_val = d[0].get("qrValidator") if isinstance(d[0], dict) else None

    return rot13(qr_val) if qr_val else None


def fetch(session, url, token, params):
    auth = {"Authorization": token, "authorizationtoken": token} if token else {}
    resp = session.get(url, params=params, headers=auth, timeout=30)
    if resp.status_code != 200:
        print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    return safe_json(resp)


def main():
    print("=" * 60)
    print("SGX Financial Reports API: DBS Search")
    print("=" * 60)

    session = requests.Session()
    session.headers.update(HEADERS)

    token = get_token(session)
    print(f"Token: {'OK' if token else 'FAILED'}")

    time.sleep(5)

    # Step 1: Explore the API - basic fetch
    print(f"\n--- Step 1: Basic fetch (first 10) ---")
    data = fetch(session, SGX_FIN_REPORTS_URL, token, {"pagestart": "0", "pagesize": "10"})
    if not data:
        return

    meta = data.get("meta", {})
    items = data.get("data", [])
    print(f"meta: {json.dumps(meta)}")
    print(f"Items: {len(items)}")
    if items:
        print(f"Item keys: {sorted(items[0].keys())}")
        for i, item in enumerate(items[:3], 1):
            print(f"\n  [{i}] {item.get('companyName', '?')}")
            print(f"      Title: {item.get('title', '?')}")
            print(f"      Date: {item.get('documentDate', '?')} (broadcast: {item.get('broadcastDateTime', '?')})")
            print(f"      URL: {item.get('url', '?')[:100]}")

    time.sleep(5)

    # Step 2: Try filtering parameters
    print(f"\n--- Step 2: Test server-side filters for DBS ---")
    filter_tests = [
        {"companyName": "DBS"},
        {"companyName": "DBS GROUP HOLDINGS"},
        {"value": "DBS"},
        {"issuername": "DBS"},
        {"stockcode": "D05"},
        {"code": "D05"},
    ]

    baseline_meta = meta
    for filt in filter_tests:
        time.sleep(3)
        params = {"pagestart": "0", "pagesize": "5", **filt}
        data = fetch(session, SGX_FIN_REPORTS_URL, token, params)
        if data:
            f_meta = data.get("meta", {})
            f_items = data.get("data", [])
            # Check if results differ from baseline
            first_company = f_items[0].get("companyName", "?") if f_items else "none"
            k, v = list(filt.items())[0]
            print(f"  {k}={v}: {len(f_items)} items, first='{first_company}'")
            if f_items and "DBS" in first_company.upper():
                print(f"    ★ DBS FOUND!")
                for item in f_items:
                    print(f"    - {item.get('title', '?')[:70]} ({item.get('companyName', '?')})")

    time.sleep(5)

    # Step 3: Paginate through ALL and client-side filter
    print(f"\n--- Step 3: Paginate all financial reports, filter for DBS ---")
    dbs_reports = []
    all_companies = Counter()
    page_start = 0
    page_size = 250
    total_fetched = 0

    while True:
        data = fetch(session, SGX_FIN_REPORTS_URL, token, {
            "pagestart": str(page_start),
            "pagesize": str(page_size),
        })
        if not data:
            break

        items = data.get("data", [])
        if not items:
            break

        for item in items:
            company = item.get("companyName", "")
            all_companies[company] += 1
            if "DBS" in company.upper():
                dbs_reports.append(item)

        total_fetched += len(items)
        print(f"  Fetched {total_fetched} — DBS so far: {len(dbs_reports)}")

        if len(items) < page_size:
            break  # last page

        page_start += len(items)
        time.sleep(5)

    print(f"\nTotal reports scanned: {total_fetched}")
    print(f"Unique companies: {len(all_companies)}")

    # Show our DR companies
    dr_keywords = ["DBS", "OCBC", "UOB", "SINGAPORE TELECOMM", "KEPPEL", "SINGAPORE AIRLINES",
                    "YZJ", "CAPITALAN", "SATS"]
    print(f"\nDR-related companies found:")
    for company, count in all_companies.most_common():
        for kw in dr_keywords:
            if kw in company.upper():
                print(f"  {company}: {count} reports")
                break

    # DBS results
    print(f"\n--- DBS Financial Reports: {len(dbs_reports)} ---")
    for i, item in enumerate(dbs_reports, 1):
        title = item.get("title", "N/A")
        company = item.get("companyName", "")
        doc_date = item.get("documentDate", "?")
        broadcast = item.get("broadcastDateTime", "?")
        url = item.get("url", "")
        ann_id = item.get("id", "?")

        # Convert epoch ms to readable date
        if isinstance(doc_date, (int, float)):
            doc_date = datetime.utcfromtimestamp(doc_date / 1000).strftime("%Y-%m-%d")
        if isinstance(broadcast, (int, float)):
            broadcast = datetime.utcfromtimestamp(broadcast / 1000).strftime("%Y-%m-%d %H:%M")

        print(f"\n  [{i}] {title}")
        print(f"      Company:   {company}")
        print(f"      Doc Date:  {doc_date}")
        print(f"      Broadcast: {broadcast}")
        print(f"      ID:        {ann_id}")
        if url:
            print(f"      URL:       {url[:120]}")

    print(f"\n{'='*60}")
    print("DONE")


if __name__ == "__main__":
    main()
