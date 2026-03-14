#!/usr/bin/env python3
"""
SGX Announcements API Probe Script

Reverse-engineers the SGX (Singapore Exchange) internal REST APIs
for company announcements. Systematically discovers endpoints, parameters,
response schemas, and documents findings.

Usage:
    python scripts/probe_sgx_api.py
    python scripts/probe_sgx_api.py --token YOUR_TOKEN
    python scripts/probe_sgx_api.py --output sgx_api_report.json
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.sgx.com",
    "Referer": "https://www.sgx.com/",
}

# Alternative header sets discovered from working SGX scrapers
ALT_HEADER_SETS = {
    "www2_origin": {
        "Origin": "https://www2.sgx.com",
        "Referer": "https://www2.sgx.com/securities/securities-prices",
    },
    "no_origin": {
        "Origin": None,  # Remove Origin header
        "Referer": None,
    },
    "sgx_securities": {
        "Origin": "https://www.sgx.com",
        "Referer": "https://www.sgx.com/securities/company-announcements",
    },
}

REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 5  # seconds between requests

# SGX CMS token discovery (reverse-engineered from SGX SPA JS bundle)
# Token flow: fetch CMS endpoint → extract qrValidator → ROT13 decode → use as authorizationToken
SGX_CMS_API_URL = "https://api2.sgx.com/content-api"
SGX_CMS_VERSION = "dd24dd8e5b3ef52e535a662e01b58d76471f335e"
SGX_TOKEN_URL = f"{SGX_CMS_API_URL}/?queryId={SGX_CMS_VERSION}:we_chat_qr_validator"
SGX_ANNOUNCEMENTS_URL = "https://api.sgx.com/announcements/v1.1/"
SGX_CONFIG_URL = "https://www.sgx.com/config/appconfig.json"

# SGX ticker codes for our 10 DR tickers (SGX stock codes)
DR_SG_TICKERS = {
    "D05": "DBS Group Holdings",
    "O39": "OCBC Bank",
    "U11": "United Overseas Bank",
    "Z74": "Singapore Telecommunications",
    "BN4": "Keppel Corporation",
    "C6L": "Singapore Airlines",
    "BS6": "YZJ Shipbldg SGD",
    "A17U": "CapitaLand Ascendas REIT",
    "C38U": "CapitaLand Integrated Commercial Trust",
    "S58": "SATS",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
    """Parse JSON from SGX response, stripping `{}&&` prefix if present."""
    text = response.text.strip()
    # SGX sometimes prefixes JSON with {}&&
    if text.startswith("{}&&"):
        text = text[4:]
    # Also handle )]}' prefix (another common anti-XSSI pattern)
    if text.startswith(")]}'"):
        text = text[4:].lstrip("\n")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s | First 200 chars: %s", e, text[:200])
        return None


def _truncate(text: str, max_len: int = 500) -> str:
    """Truncate text for logging."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [truncated, total {len(text)} chars]"


def _delay():
    """Rate-limit between requests."""
    logger.info("Waiting %ds (rate limit)...", RATE_LIMIT_DELAY)
    time.sleep(RATE_LIMIT_DELAY)


def _rot13(text: str) -> str:
    """ROT13 decode/encode (symmetric). Used by SGX to obfuscate the auth token."""
    result = []
    for ch in text:
        code = ord(ch)
        if ord("a") <= code <= ord("z"):
            result.append(chr((code - ord("a") + 13) % 26 + ord("a")))
        elif ord("A") <= code <= ord("Z"):
            result.append(chr((code - ord("A") + 13) % 26 + ord("A")))
        else:
            result.append(ch)
    return "".join(result)


def _infer_type(value: Any) -> str:
    """Infer a human-readable type string for a value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            return "datetime_string"
        if value.startswith("http"):
            return "url"
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


# ---------------------------------------------------------------------------
# Probe class
# ---------------------------------------------------------------------------


class SGXProbe:
    """Systematically probes SGX API endpoints."""

    def __init__(self, token: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(BASE_HEADERS)
        self.token = token
        self.results: Dict[str, Any] = {
            "probe_timestamp": datetime.utcnow().isoformat() + "Z",
            "endpoints": {},
            "parameters": {},
            "schema": {},
            "subcategories": {},
            "company_filter": {},
            "pagination": {},
            "dbs_test": {},
            "observations": [],
        }
        # Track which announcements endpoint works
        self._working_ann_url: Optional[str] = None
        self._working_ann_needs_auth: bool = False
        self._working_ann_headers: Dict[str, str] = {}

    def _get(
        self,
        url: str,
        params: Optional[Dict] = None,
        use_auth: bool = False,
        extra_headers: Optional[Dict] = None,
    ) -> requests.Response:
        """Make a GET request with optional auth header."""
        headers = {}
        if use_auth and self.token:
            headers["Authorization"] = self.token
            headers["authorizationtoken"] = self.token
        if extra_headers:
            for k, v in extra_headers.items():
                if v is None:
                    # Remove header from session defaults for this request
                    headers[k] = ""
                else:
                    headers[k] = v
        return self.session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

    def _probe_endpoint(
        self,
        name: str,
        url: str,
        params: Optional[Dict] = None,
        use_auth: bool = False,
        extra_headers: Optional[Dict] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        """Probe a single endpoint and record results."""
        logger.info("Probing [%s]: %s (auth=%s)", name, url, use_auth)
        try:
            resp = self._get(url, params=params, use_auth=use_auth, extra_headers=extra_headers)
            data = _safe_json(resp) if resp.status_code == 200 else None
            result = {
                "url": url,
                "params": params,
                "auth_used": use_auth,
                "status_code": resp.status_code,
                "response_size": len(resp.text),
                "has_json_prefix": resp.text.strip().startswith("{}&&"),
                "content_type": resp.headers.get("Content-Type", ""),
                "preview": _truncate(resp.text),
                "parsed": data is not None,
            }
            self.results["endpoints"][name] = result
            success = resp.status_code == 200 and data is not None
            if success:
                logger.info(
                    "  ✓ %s: %d, %d bytes, parsed OK",
                    name,
                    resp.status_code,
                    len(resp.text),
                )
            else:
                logger.warning(
                    "  ✗ %s: %d, %d bytes",
                    name,
                    resp.status_code,
                    len(resp.text),
                )
            return success, data
        except requests.RequestException as e:
            logger.error("  ✗ %s: request failed: %s", name, e)
            self.results["endpoints"][name] = {"error": str(e)}
            return False, None

    # -------------------------------------------------------------------
    # Step 2: Probe no-auth endpoints
    # -------------------------------------------------------------------

    def _try_token_discovery(self):
        """Discover auth token from SGX CMS (reverse-engineered from SGX SPA).

        Token flow:
        1. Fetch appconfig.json to get CMS_API_URL and CMS_VERSION (or use known values)
        2. Fetch CMS endpoint: {CMS_API_URL}/?queryId={CMS_VERSION}:we_chat_qr_validator
        3. Extract data.qrValidator from response
        4. ROT13 decode the value → this is the authorizationToken
        """
        logger.info("--- Attempting token discovery via SGX CMS ---")

        # Step 1: Optionally refresh config (in case CMS_VERSION changed)
        cms_api_url = SGX_CMS_API_URL
        cms_version = SGX_CMS_VERSION
        try:
            resp = self.session.get(SGX_CONFIG_URL, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                config = _safe_json(resp)
                if config:
                    cms_api_url = config.get("endpoints", {}).get("CMS_API_URL", cms_api_url)
                    cms_version = config.get("CMS_VERSION", cms_version)
                    ann_url = config.get("endpoints", {}).get("ANNOUNCEMENTS_API_URL")
                    if ann_url:
                        self.results["observations"].append(
                            f"Config says announcements URL: {ann_url}"
                        )
                    logger.info("  Config loaded: CMS_VERSION=%s...", cms_version[:16])
        except requests.RequestException as e:
            logger.warning("  Config fetch failed: %s (using defaults)", e)
        _delay()

        # Step 2: Fetch the token from CMS
        token_url = f"{cms_api_url}/?queryId={cms_version}:we_chat_qr_validator"
        logger.info("  Fetching token from: %s", _truncate(token_url, 100))
        try:
            resp = self.session.get(token_url, timeout=REQUEST_TIMEOUT)
            logger.info("  Token endpoint: HTTP %d, %d bytes", resp.status_code, len(resp.text))
            if resp.status_code == 200:
                data = _safe_json(resp)
                if data:
                    # Step 3: Extract qrValidator
                    qr_val = None
                    if isinstance(data, dict):
                        qr_val = data.get("qrValidator")
                        if not qr_val and "data" in data:
                            d = data["data"]
                            if isinstance(d, dict):
                                qr_val = d.get("qrValidator")
                            elif isinstance(d, list) and len(d) > 0:
                                qr_val = d[0].get("qrValidator") if isinstance(d[0], dict) else None

                    if qr_val:
                        # Step 4: ROT13 decode
                        decoded = _rot13(qr_val)
                        self.token = decoded
                        self.results["observations"].append(
                            f"Token discovered via CMS (ROT13 of qrValidator). "
                            f"Length: {len(decoded)}"
                        )
                        logger.info("  ★ Token discovered! Length: %d", len(decoded))
                        return
                    else:
                        self.results["observations"].append(
                            f"CMS response parsed but no qrValidator found. "
                            f"Keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
                        )
                        logger.warning("  No qrValidator in response: %s", _truncate(str(data), 200))
            else:
                self.results["observations"].append(
                    f"CMS token endpoint returned HTTP {resp.status_code}"
                )
        except requests.RequestException as e:
            logger.error("  Token fetch failed: %s", e)
            self.results["observations"].append(f"CMS token fetch error: {e}")
        _delay()

    def probe_noauth_endpoints(self):
        """Test endpoints without authentication."""
        logger.info("=" * 60)
        logger.info("STEP 2: Probing no-auth endpoints")
        logger.info("=" * 60)

        # 1. Securities endpoint (known to work) — validate our setup
        ok, data = self._probe_endpoint(
            "securities_v1.1",
            "https://api.sgx.com/securities/v1.1",
            params={
                "excludetypes": "bonds",
                "params": "nc,lt,c,p,change_vs_pc,change_vs_pc_percentage,v",
            },
            extra_headers={
                "Origin": "https://www2.sgx.com",
                "Referer": "https://www2.sgx.com/securities/securities-prices",
            },
        )
        if ok:
            self.results["observations"].append("securities/v1.1 works (setup validated)")
        _delay()

        # 2. Stock screener — map stock codes to company names
        ok, data = self._probe_endpoint(
            "stock_screener_v2",
            "https://api.sgx.com/stockscreener/v2.0/all",
            params={"params": "nc,adjustedPrice,bv,p,c"},
        )
        if ok and isinstance(data, dict):
            self.results["observations"].append(
                f"stock_screener: {_truncate(str(list(data.keys())), 200)}"
            )
        _delay()

        # 3. Corporate actions — verify no-auth pattern
        ok, data = self._probe_endpoint(
            "corporate_actions_v1",
            "https://api.sgx.com/corporateactions/v1.0",
            params={"pagestart": "0", "pagesize": "5"},
        )
        if ok:
            self.results["observations"].append("corporate_actions works without auth")
        _delay()

        # 4. Announcements — try all version + header combinations
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        ann_params = {
            "periodstart": week_ago.strftime("%Y%m%d_160000"),
            "periodend": now.strftime("%Y%m%d_155959"),
            "pagestart": "0",
            "pagesize": "5",
        }

        ann_urls = [
            ("v1.0/", "https://api.sgx.com/announcements/v1.0/"),
            ("v1.0", "https://api.sgx.com/announcements/v1.0"),
            ("v1.1/", "https://api.sgx.com/announcements/v1.1/"),
            ("v1.1", "https://api.sgx.com/announcements/v1.1"),
        ]

        header_combos = [
            ("default", {}),
            ("www2_origin", ALT_HEADER_SETS["www2_origin"]),
            ("sgx_ann_referer", ALT_HEADER_SETS["sgx_securities"]),
        ]

        for url_name, url in ann_urls:
            if self._working_ann_url:
                break
            for hdr_name, hdrs in header_combos:
                if self._working_ann_url:
                    break
                probe_name = f"ann_{url_name}_{hdr_name}"
                ok, data = self._probe_endpoint(
                    probe_name,
                    url,
                    params=ann_params,
                    extra_headers=hdrs if hdrs else None,
                )
                if ok:
                    self._working_ann_url = url
                    self._working_ann_needs_auth = False
                    self._working_ann_headers = hdrs
                    self.results["observations"].append(
                        f"announcements works: {url} with headers={hdr_name}"
                    )
                _delay()

        # 5. Try with auth token if provided
        if self.token and not self._working_ann_url:
            for url_name, url in ann_urls:
                if self._working_ann_url:
                    break
                ok, data = self._probe_endpoint(
                    f"ann_{url_name}_auth",
                    url,
                    params=ann_params,
                    use_auth=True,
                )
                if ok:
                    self._working_ann_url = url
                    self._working_ann_needs_auth = True
                    self._working_ann_headers = {}
                    self.results["observations"].append(
                        f"announcements works WITH auth: {url}"
                    )
                _delay()

        # 6. Try token discovery if no endpoint found
        if not self._working_ann_url:
            self._try_token_discovery()
            # Retry with discovered token
            if self.token:
                for url_name, url in ann_urls:
                    if self._working_ann_url:
                        break
                    ok, data = self._probe_endpoint(
                        f"ann_{url_name}_discovered_token",
                        url,
                        params=ann_params,
                        use_auth=True,
                    )
                    if ok:
                        self._working_ann_url = url
                        self._working_ann_needs_auth = True
                        self._working_ann_headers = {}
                        self.results["observations"].append(
                            f"announcements works with discovered token: {url}"
                        )
                    _delay()

        # 7. Try alternative URL patterns
        if not self._working_ann_url:
            alt_urls = [
                ("api2_v1.0", "https://api2.sgx.com/announcements/v1.0/"),
                ("links_corp", "https://links.sgx.com/1.0/corporate-announcements/"),
                ("proxy", "https://www.sgx.com/proxy/SgxDominoHttpProxy"),
            ]
            for alt_name, alt_url in alt_urls:
                if alt_name == "proxy":
                    # Old proxy endpoint — different param format
                    proxy_params = {
                        "timeout": "100",
                        "dominoHost": (
                            "http://infofeed.sgx.com/Apps"
                            "?A=COW_CorpAnnouncement_Content"
                            "&B=AnnouncementToday&R_C=&C_T=200"
                        ),
                    }
                    ok, data = self._probe_endpoint(alt_name, alt_url, params=proxy_params)
                else:
                    ok, data = self._probe_endpoint(alt_name, alt_url, params=ann_params)
                if ok:
                    self._working_ann_url = alt_url
                    self._working_ann_needs_auth = False
                    self._working_ann_headers = {}
                    self.results["observations"].append(f"Alternative URL works: {alt_url}")
                    break
                _delay()

        if not self._working_ann_url:
            self.results["observations"].append(
                "NO announcements endpoint found. "
                "All v1.0/v1.1 endpoints return 403. "
                "The API likely requires a session token obtained from the SGX SPA. "
                "Try: 1) Open browser DevTools on sgx.com/securities/company-announcements "
                "2) Find the announcements API call in Network tab "
                "3) Copy the authorization header value "
                "4) Run: python scripts/probe_sgx_api.py --token YOUR_TOKEN"
            )
            logger.error("No working announcements endpoint found!")

    # -------------------------------------------------------------------
    # Step 3: Parameter discovery
    # -------------------------------------------------------------------

    def probe_parameters(self):
        """Systematically test parameters on the working endpoint."""
        if not self._working_ann_url:
            logger.warning("Skipping parameter discovery — no working endpoint")
            return

        logger.info("=" * 60)
        logger.info("STEP 3: Parameter discovery on %s", self._working_ann_url)
        logger.info("=" * 60)

        now = datetime.utcnow()
        week_ago = now - timedelta(days=11)

        base_params = {
            "periodstart": week_ago.strftime("%Y%m%d_160000"),
            "periodend": now.strftime("%Y%m%d_155959"),
            "pagestart": "0",
            "pagesize": "10",
        }

        # --- Baseline ---
        ok, baseline_data = self._probe_endpoint(
            "param_baseline",
            self._working_ann_url,
            params=base_params,
            use_auth=self._working_ann_needs_auth,
            extra_headers=self._working_ann_headers or None,
        )
        baseline_total = None
        if ok and isinstance(baseline_data, dict):
            # Try common keys for total count
            baseline_total = (
                baseline_data.get("totalSize")
                or baseline_data.get("meta", {}).get("totalItems")
                or baseline_data.get("meta", {}).get("totalSize")
                or baseline_data.get("total")
            )
            self.results["parameters"]["baseline"] = {
                "params": base_params,
                "totalSize": baseline_total,
            }
            logger.info("  Baseline totalSize: %s", baseline_total)
        _delay()

        # --- Company filter candidates ---
        # SPA maps: value → issuername, announcementtitle → announcementtitle
        filter_candidates = [
            ("issuername", "DBS GROUP HOLDINGS"),  # full name (SPA's primary filter)
            ("issuername", "DBS"),                  # partial name
            ("value", "DBS"),                       # SPA's URL param (mapped to issuername)
            ("issuercode", "D05"),
            ("stockcode", "D05"),
            ("company", "DBS"),
            ("securityname", "DBS"),
            ("code", "D05"),
            ("announcementtitle", "DBS"),
        ]

        self.results["company_filter"]["baseline_total"] = baseline_total
        self.results["company_filter"]["tests"] = {}

        for param_name, param_value in filter_candidates:
            test_params = {**base_params, param_name: param_value}
            ok, data = self._probe_endpoint(
                f"filter_{param_name}",
                self._working_ann_url,
                params=test_params,
                use_auth=self._working_ann_needs_auth,
            )
            if ok and isinstance(data, dict):
                total = (
                    data.get("totalSize")
                    or data.get("meta", {}).get("totalItems")
                    or data.get("meta", {}).get("totalSize")
                    or data.get("total")
                )
                filtered = baseline_total is not None and total is not None and total < baseline_total
                self.results["company_filter"]["tests"][param_name] = {
                    "value": param_value,
                    "totalSize": total,
                    "reduced_results": filtered,
                }
                if filtered:
                    logger.info(
                        "  ★ Filter '%s=%s' reduced results: %s → %s",
                        param_name,
                        param_value,
                        baseline_total,
                        total,
                    )
                    self.results["observations"].append(
                        f"Company filter works: {param_name}={param_value} "
                        f"(total {baseline_total} → {total})"
                    )
            _delay()

        # --- Category/subcategory codes ---
        logger.info("Testing category codes...")
        cat_params = {**base_params, "cat": "ANNC"}
        ok, data = self._probe_endpoint(
            "cat_ANNC",
            self._working_ann_url,
            params=cat_params,
            use_auth=self._working_ann_needs_auth,
            extra_headers=self._working_ann_headers or None,
        )
        if ok and isinstance(data, dict):
            total = (
                data.get("totalSize")
                or data.get("meta", {}).get("totalSize")
                or data.get("total")
            )
            self.results["subcategories"]["ANNC_total"] = total
        _delay()

        # Sweep subcategory codes
        self.results["subcategories"]["valid_codes"] = {}
        for i in range(1, 31):
            sub_code = f"ANNC{i:02d}"
            sub_params = {**base_params, "cat": "ANNC", "sub": sub_code}
            ok, data = self._probe_endpoint(
                f"sub_{sub_code}",
                self._working_ann_url,
                params=sub_params,
                use_auth=self._working_ann_needs_auth,
            )
            if ok and isinstance(data, dict):
                total = (
                    data.get("totalSize")
                    or data.get("meta", {}).get("totalItems")
                    or data.get("meta", {}).get("totalSize")
                    or data.get("total")
                )
                if total and total > 0:
                    self.results["subcategories"]["valid_codes"][sub_code] = total
                    logger.info("  Found subcategory %s with %s results", sub_code, total)
            _delay()

        # --- Pagination ---
        logger.info("Testing pagination...")
        page0_params = {**base_params, "pagestart": "0", "pagesize": "3"}
        ok0, data0 = self._probe_endpoint(
            "pagination_page0",
            self._working_ann_url,
            params=page0_params,
            use_auth=self._working_ann_needs_auth,
            extra_headers=self._working_ann_headers or None,
        )
        _delay()

        page1_params = {**base_params, "pagestart": "3", "pagesize": "3"}
        ok1, data1 = self._probe_endpoint(
            "pagination_page1",
            self._working_ann_url,
            params=page1_params,
            use_auth=self._working_ann_needs_auth,
            extra_headers=self._working_ann_headers or None,
        )

        if ok0 and ok1:
            items0 = self._extract_items(data0)
            items1 = self._extract_items(data1)
            # Check for overlap
            ids0 = {self._item_id(i) for i in items0 if self._item_id(i)}
            ids1 = {self._item_id(i) for i in items1 if self._item_id(i)}
            overlap = ids0 & ids1
            self.results["pagination"] = {
                "page0_count": len(items0),
                "page1_count": len(items1),
                "overlap_count": len(overlap),
                "overlap_ids": list(overlap),
                "pagestart_is_offset": len(overlap) == 0,
            }
            if overlap:
                logger.warning("  Pagination has overlapping items: %s", overlap)
            else:
                logger.info("  Pagination clean — no overlap between pages")
        _delay()

        # --- Sort parameters ---
        logger.info("Testing sort parameters...")
        for sort_param in [
            {"order": "asc"},
            {"order": "desc"},
            {"orderby": "date"},
            {"sort": "date"},
            {"sortby": "date"},
        ]:
            test_params = {**base_params, **sort_param}
            key = "_".join(f"{k}_{v}" for k, v in sort_param.items())
            ok, data = self._probe_endpoint(
                f"sort_{key}",
                self._working_ann_url,
                params=test_params,
                use_auth=self._working_ann_needs_auth,
            )
            if ok and isinstance(data, dict):
                items = self._extract_items(data)
                if len(items) >= 2:
                    # Check if dates are sorted
                    dates = [
                        i.get("ann_date") or i.get("date") or i.get("broadcast_date_time", "")
                        for i in items[:5]
                    ]
                    self.results["parameters"][f"sort_{key}"] = {
                        "works": True,
                        "first_dates": dates,
                    }
            _delay()

    # -------------------------------------------------------------------
    # Step 4: Schema extraction
    # -------------------------------------------------------------------

    def extract_schema(self):
        """Extract full response schema from a larger result set."""
        if not self._working_ann_url:
            logger.warning("Skipping schema extraction — no working endpoint")
            return

        logger.info("=" * 60)
        logger.info("STEP 4: Schema extraction")
        logger.info("=" * 60)

        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        params = {
            "periodstart": month_ago.strftime("%Y%m%d_160000"),
            "periodend": now.strftime("%Y%m%d_155959"),
            "pagestart": "0",
            "pagesize": "50",
        }

        ok, data = self._probe_endpoint(
            "schema_sample",
            self._working_ann_url,
            params=params,
            use_auth=self._working_ann_needs_auth,
            extra_headers=self._working_ann_headers or None,
        )

        if not ok or not isinstance(data, dict):
            return

        # Top-level keys
        self.results["schema"]["top_level_keys"] = list(data.keys())

        items = self._extract_items(data)
        if not items:
            self.results["observations"].append("No data items found for schema extraction")
            return

        # Merge all keys across items
        all_keys: Dict[str, Dict[str, Any]] = {}
        for item in items:
            for key, value in item.items():
                if key not in all_keys:
                    all_keys[key] = {
                        "type": _infer_type(value),
                        "example": _truncate(str(value), 150) if value is not None else None,
                        "null_count": 0,
                        "total_count": 0,
                    }
                all_keys[key]["total_count"] += 1
                if value is None:
                    all_keys[key]["null_count"] += 1

        # Identify URL fields (for PDFs/documents)
        url_fields = [k for k, v in all_keys.items() if v["type"] == "url"]

        self.results["schema"]["fields"] = all_keys
        self.results["schema"]["field_count"] = len(all_keys)
        self.results["schema"]["sample_size"] = len(items)
        self.results["schema"]["url_fields"] = url_fields

        logger.info("  Extracted %d fields from %d items", len(all_keys), len(items))
        logger.info("  URL fields: %s", url_fields)

    # -------------------------------------------------------------------
    # Step 5: DBS-specific test
    # -------------------------------------------------------------------

    def test_dbs_filter(self):
        """Fetch DBS (D05) announcements."""
        if not self._working_ann_url:
            logger.warning("Skipping DBS test — no working endpoint")
            return

        logger.info("=" * 60)
        logger.info("STEP 5: DBS-specific test")
        logger.info("=" * 60)

        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        base_params = {
            "periodstart": month_ago.strftime("%Y%m%d_160000"),
            "periodend": now.strftime("%Y%m%d_155959"),
            "pagestart": "0",
            "pagesize": "50",
        }

        # Check if any server-side filter worked
        working_filter = None
        for param_name, test_info in self.results.get("company_filter", {}).get("tests", {}).items():
            if test_info.get("reduced_results"):
                working_filter = (param_name, test_info["value"])
                break

        dbs_items = []

        if working_filter:
            # Use server-side filter
            param_name, param_value = working_filter
            params = {**base_params, param_name: param_value}
            logger.info("Using server-side filter: %s=%s", param_name, param_value)
            ok, data = self._probe_endpoint(
                "dbs_server_filter",
                self._working_ann_url,
                params=params,
                use_auth=self._working_ann_needs_auth,
            )
            if ok:
                dbs_items = self._extract_items(data)
                self.results["dbs_test"]["filter_method"] = "server_side"
                self.results["dbs_test"]["filter_param"] = f"{param_name}={param_value}"
        else:
            # Fall back to client-side filter
            logger.info("No server-side filter found — using client-side filter")
            ok, data = self._probe_endpoint(
                "dbs_client_filter",
                self._working_ann_url,
                params=base_params,
                use_auth=self._working_ann_needs_auth,
            )
            if ok:
                all_items = self._extract_items(data)
                # Filter for DBS by any name/code field
                for item in all_items:
                    item_str = json.dumps(item).upper()
                    if "DBS" in item_str or "D05" in item_str:
                        dbs_items.append(item)
                self.results["dbs_test"]["filter_method"] = "client_side"
                self.results["dbs_test"]["total_fetched"] = len(all_items)

        # Format results
        dbs_announcements = []
        for item in dbs_items:
            ann = {
                "title": (
                    item.get("title")
                    or item.get("ann_title")
                    or item.get("announcement_title")
                    or "N/A"
                ),
                "date": (
                    item.get("ann_date")
                    or item.get("date")
                    or item.get("broadcast_date_time")
                    or "N/A"
                ),
                "url": item.get("url") or item.get("attm_url") or item.get("attachment_url") or "",
                "issuer": item.get("issuer_name") or item.get("company_name") or "",
                "category": item.get("cat") or item.get("category") or "",
            }
            dbs_announcements.append(ann)

        self.results["dbs_test"]["count"] = len(dbs_announcements)
        self.results["dbs_test"]["announcements"] = dbs_announcements

        logger.info("Found %d DBS announcements", len(dbs_announcements))
        for ann in dbs_announcements[:5]:
            logger.info("  - [%s] %s", ann["date"], ann["title"])

    # -------------------------------------------------------------------
    # Step 6: Output report
    # -------------------------------------------------------------------

    def print_report(self):
        """Print structured report to stdout."""
        logger.info("=" * 60)
        logger.info("STEP 6: Report")
        logger.info("=" * 60)

        print("\n" + "=" * 70)
        print("SGX API PROBE REPORT")
        print(f"Timestamp: {self.results['probe_timestamp']}")
        print("=" * 70)

        # Working endpoint
        print("\n--- Working Endpoint ---")
        if self._working_ann_url:
            print(f"URL:  {self._working_ann_url}")
            print(f"Auth: {'Required (token header)' if self._working_ann_needs_auth else 'Not required'}")
        else:
            print("NO working announcements endpoint found!")

        # Endpoint status
        print("\n--- Endpoint Status ---")
        for name, info in self.results["endpoints"].items():
            if isinstance(info, dict) and "status_code" in info:
                status = info["status_code"]
                marker = "✓" if status == 200 and info.get("parsed") else "✗"
                prefix_marker = " ({}&&)" if info.get("has_json_prefix") else ""
                print(f"  {marker} {name}: HTTP {status}, {info.get('response_size', '?')} bytes{prefix_marker}")
            elif isinstance(info, dict) and "error" in info:
                print(f"  ✗ {name}: {info['error']}")

        # Company filter
        print("\n--- Company Filter ---")
        tests = self.results.get("company_filter", {}).get("tests", {})
        if tests:
            baseline = self.results["company_filter"].get("baseline_total")
            print(f"  Baseline total: {baseline}")
            for param, info in tests.items():
                reduced = "★ WORKS" if info.get("reduced_results") else "no effect"
                print(f"  {param}={info['value']}: total={info.get('totalSize')} ({reduced})")
        else:
            print("  No filter tests run")

        # Subcategories
        print("\n--- Subcategory Codes ---")
        valid = self.results.get("subcategories", {}).get("valid_codes", {})
        if valid:
            for code, total in sorted(valid.items()):
                print(f"  {code}: {total} results")
        else:
            print("  No valid subcategory codes found")

        # Pagination
        print("\n--- Pagination ---")
        pag = self.results.get("pagination", {})
        if pag:
            print(f"  Page 0 items: {pag.get('page0_count')}")
            print(f"  Page 1 items: {pag.get('page1_count')}")
            print(f"  Overlap: {pag.get('overlap_count', '?')}")
            print(f"  pagestart is offset: {pag.get('pagestart_is_offset', '?')}")
        else:
            print("  No pagination data")

        # Schema
        print("\n--- Response Schema ---")
        schema = self.results.get("schema", {})
        if schema.get("fields"):
            print(f"  Top-level keys: {schema.get('top_level_keys')}")
            print(f"  Item field count: {schema.get('field_count')}")
            print(f"  Sample size: {schema.get('sample_size')}")
            print(f"  URL fields: {schema.get('url_fields')}")
            print("\n  Fields:")
            for field, info in sorted(schema["fields"].items()):
                print(f"    {field:30s} {info['type']:20s} {info.get('example', '')}")
        else:
            print("  No schema data")

        # DBS test
        print("\n--- DBS Announcements ---")
        dbs = self.results.get("dbs_test", {})
        if dbs:
            print(f"  Filter method: {dbs.get('filter_method', 'N/A')}")
            print(f"  Count: {dbs.get('count', 0)}")
            for ann in dbs.get("announcements", [])[:10]:
                print(f"  [{ann['date']}] {ann['title']}")
                if ann.get("url"):
                    print(f"    → {ann['url']}")
        else:
            print("  No DBS test data")

        # Observations
        print("\n--- Observations ---")
        for obs in self.results.get("observations", []):
            print(f"  • {obs}")

        print("\n" + "=" * 70)

    def save_results(self, path: str):
        """Save full results to JSON file."""
        # Convert non-serializable items
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info("Results saved to %s", path)

    # -------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------

    def _extract_items(self, data: Optional[Dict]) -> List[Dict]:
        """Extract announcement items from various response structures."""
        if not data:
            return []
        # Try common structures
        if "data" in data:
            d = data["data"]
            if isinstance(d, list):
                return d
            if isinstance(d, dict):
                # data might contain a nested list
                for key in ("records", "items", "announcements", "results"):
                    if key in d and isinstance(d[key], list):
                        return d[key]
                return [d]
        if "results" in data and isinstance(data["results"], list):
            return data["results"]
        if "records" in data and isinstance(data["records"], list):
            return data["records"]
        if isinstance(data, list):
            return data
        return []

    def _item_id(self, item: Dict) -> Optional[str]:
        """Extract a unique ID from an announcement item."""
        for key in ("id", "ann_id", "announcement_id", "ref_no"):
            if key in item and item[key] is not None:
                return str(item[key])
        # Fall back to title + date
        title = item.get("title") or item.get("ann_title") or ""
        date = item.get("ann_date") or item.get("date") or ""
        if title and date:
            return f"{date}_{title[:50]}"
        return None

    # -------------------------------------------------------------------
    # Run all steps
    # -------------------------------------------------------------------

    def run(self):
        """Execute the full probe sequence."""
        logger.info("Starting SGX API probe...")
        if self.token:
            logger.info("Auth token provided (first 10 chars): %s...", self.token[:10])
        else:
            logger.info("No auth token provided — will test no-auth endpoints only")

        self.probe_noauth_endpoints()    # Step 2
        self.probe_parameters()           # Step 3
        self.extract_schema()             # Step 4
        self.test_dbs_filter()            # Step 5
        self.print_report()               # Step 6


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Probe SGX API endpoints for announcements"
    )
    parser.add_argument(
        "--token",
        help="Authorization token for v1.1 endpoints",
        default=None,
    )
    parser.add_argument(
        "--output",
        help="Save full results to JSON file",
        default=None,
    )
    args = parser.parse_args()

    probe = SGXProbe(token=args.token)
    probe.run()

    if args.output:
        probe.save_results(args.output)


if __name__ == "__main__":
    main()
