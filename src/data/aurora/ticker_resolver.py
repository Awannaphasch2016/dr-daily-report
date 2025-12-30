# -*- coding: utf-8 -*-
"""
Ticker Resolver Service

Centralized ticker symbol resolution that maps any symbol format
(DR, Yahoo, ISIN, etc.) to a canonical ticker and provides
conversions between different symbol types.

Usage:
    from src.data.aurora.ticker_resolver import get_ticker_resolver

    resolver = get_ticker_resolver()

    # Resolve any symbol to canonical info
    info = resolver.resolve("NVDA19")  # or "NVDA" or "NVDA.US"
    print(info.yahoo_symbol)  # "NVDA"
    print(info.dr_symbol)     # "NVDA19"

    # Quick conversions
    yahoo = resolver.to_yahoo("NVDA19")   # "NVDA"
    dr = resolver.to_dr("NVDA")           # "NVDA19"
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.data.aurora.client import AuroraClient, get_aurora_client
from src.data.aurora.table_names import TICKER_MASTER, TICKER_ALIASES

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TickerInfo:
    """Canonical ticker information resolved from any symbol."""

    ticker_id: int
    company_name: str
    exchange: str
    currency: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    quote_type: str = "equity"
    is_active: bool = True

    # Symbol aliases
    dr_symbol: Optional[str] = None       # Thai DR symbol (e.g., NVDA19)
    yahoo_symbol: Optional[str] = None    # Yahoo Finance symbol (e.g., NVDA)
    eikon_symbol: Optional[str] = None    # Eikon/Refinitiv symbol (e.g., DBSM.SI)

    def get_symbol(self, symbol_type: str) -> Optional[str]:
        """Get symbol for a specific type.

        Args:
            symbol_type: One of 'dr', 'yahoo', 'isin', etc.

        Returns:
            Symbol string or None
        """
        return getattr(self, f"{symbol_type}_symbol", None)


# =============================================================================
# SQL Statements
# =============================================================================

CREATE_TICKER_MASTER_TABLE = f"""
CREATE TABLE IF NOT EXISTS {TICKER_MASTER} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50) DEFAULT 'equity',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_active (is_active),
    INDEX idx_exchange (exchange)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TICKER_ALIASES_TABLE = f"""
CREATE TABLE IF NOT EXISTS {TICKER_ALIASES} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    symbol_type VARCHAR(20) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_symbol_type (symbol, symbol_type),
    INDEX idx_ticker_id (ticker_id),

    FOREIGN KEY (ticker_id) REFERENCES {TICKER_MASTER}(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


# =============================================================================
# Ticker Resolver Service
# =============================================================================

class TickerResolver:
    """Service for resolving any ticker symbol to canonical form.

    Maintains an in-memory cache of symbol mappings loaded from Aurora.
    Falls back to tickers.csv if Aurora is unavailable.

    Symbol Types:
        - dr: Thai Depository Receipt (e.g., NVDA19, DBS19)
        - yahoo: Yahoo Finance symbol (e.g., NVDA, D05.SI)
        - isin: International Securities ID (future)
        - bloomberg: Bloomberg ticker (future)
    """

    def __init__(self, client: Optional[AuroraClient] = None):
        """Initialize resolver.

        Args:
            client: AuroraClient instance (uses singleton if not provided)
        """
        self.client = client
        self._cache: Dict[str, TickerInfo] = {}  # symbol (any) -> TickerInfo
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization - load cache on first use."""
        if self._initialized:
            return

        try:
            # Try to get client if not provided
            if self.client is None:
                self.client = get_aurora_client()

            # Check if tables exist and load from Aurora
            if self._tables_exist():
                self._load_from_aurora()
            else:
                logger.info("Ticker mapping tables not found, loading from CSV")
                self._load_from_csv()
        except Exception as e:
            logger.warning(f"Aurora unavailable ({e}), loading from CSV")
            self._load_from_csv()

        self._initialized = True
        logger.info(f"TickerResolver initialized with {len(self._cache)} symbol mappings")

    def _tables_exist(self) -> bool:
        """Check if ticker_master and ticker_aliases tables exist."""
        try:
            result = self.client.fetch_one(
                f"SELECT COUNT(*) as cnt FROM information_schema.tables "
                f"WHERE table_schema = DATABASE() AND table_name = '{TICKER_MASTER}'"
            )
            return result and result.get('cnt', 0) > 0
        except Exception:
            return False

    def _load_from_aurora(self) -> None:
        """Load symbol mappings from Aurora database."""
        query = f"""
            SELECT
                m.id as ticker_id,
                m.company_name,
                m.exchange,
                m.currency,
                m.sector,
                m.industry,
                m.quote_type,
                m.is_active,
                GROUP_CONCAT(
                    CONCAT(a.symbol_type, ':', a.symbol)
                    ORDER BY a.is_primary DESC
                    SEPARATOR '|'
                ) as aliases
            FROM {TICKER_MASTER} m
            LEFT JOIN {TICKER_ALIASES} a ON m.id = a.ticker_id
            WHERE m.is_active = TRUE
            GROUP BY m.id
        """

        rows = self.client.fetch_all(query)

        for row in rows:
            info = TickerInfo(
                ticker_id=row['ticker_id'],
                company_name=row['company_name'],
                exchange=row.get('exchange', ''),
                currency=row.get('currency', 'USD'),
                sector=row.get('sector'),
                industry=row.get('industry'),
                quote_type=row.get('quote_type', 'equity'),
                is_active=row.get('is_active', True),
            )

            # Parse aliases
            aliases_str = row.get('aliases', '')
            if aliases_str:
                for alias in aliases_str.split('|'):
                    if ':' in alias:
                        symbol_type, symbol = alias.split(':', 1)
                        setattr(info, f"{symbol_type}_symbol", symbol)
                        # Add to cache keyed by symbol (uppercase)
                        self._cache[symbol.upper()] = info

        logger.info(f"Loaded {len(rows)} tickers from Aurora")

    def _load_from_csv(self) -> None:
        """Fallback: Load from tickers.csv file."""
        csv_paths = [
            Path(__file__).parent.parent.parent.parent / "data" / "tickers.csv",
            Path("data/tickers.csv"),
            Path("tickers.csv"),
        ]

        csv_path = None
        for path in csv_paths:
            if path.exists():
                csv_path = path
                break

        if csv_path is None:
            logger.error("tickers.csv not found in any expected location")
            return

        # Company name mapping (from ticker_service.py)
        name_map = {
            'SIA19': 'Singapore Airlines',
            'STEG19': 'SATS Ltd',
            'VENTURE19': 'Venture Corporation',
            'NINTENDO19': 'Nintendo Co Ltd',
            'SMFG19': 'Sumitomo Mitsui Financial Group',
            'GOLD19': 'SPDR Gold Shares Singapore',
            'INDIAESG19': 'India ESG ETF',
            'DBS19': 'DBS Group Holdings',
            'THAIBEV19': 'Thai Beverage',
            'UOB19': 'United Overseas Bank',
            'MITSU19': 'Mitsubishi Heavy Industries',
            'HONDA19': 'Honda Motor Co',
            'MUFG19': 'Mitsubishi UFJ Financial Group',
            'VNM19': 'Vietnam Dairy Products',
            'TAIWAN19': 'Taiwan 50 ETF',
            'FPTVN19': 'FPT Corporation',
            'VCB19': 'Vietcombank',
            'MWG19': 'Mobile World Investment',
            'TENCENT19': 'Tencent Holdings',
            'CHMOBILE19': 'China Mobile',
            'XIAOMI19': 'Xiaomi Corporation',
            'MEITUAN19': 'Meituan',
            'HAIERS19': 'Haier Smart Home',
            'JPMUS19': 'JPMorgan Chase & Co',
            'PFIZER19': 'Pfizer Inc',
            'DISNEY19': 'The Walt Disney Company',
            'NVDA19': 'NVIDIA Corporation',
            'COSTCO19': 'Costco Wholesale',
            'QQQM19': 'Invesco NASDAQ 100 ETF',
            'GOLDUS19': 'SPDR Gold Trust',
            'ITOCHU19': 'ITOCHU Corporation',
            'AIA19': 'AIA Group',
            'CHHONGQ19': 'China Hongqiao Group',
            'ICBC19': 'Industrial and Commercial Bank of China',
            'SUNNY19': 'Sunny Optical Technology',
            'JDHEAL19': 'JD Health International',
            'HPG19': 'Hoa Phat Group',
            'VHM19': 'Vinhomes',
            'ABBV19': 'AbbVie Inc',
            'DELL19': 'Dell Technologies',
            'ORCL19': 'Oracle Corporation',
            'SP500US19': 'SPDR Portfolio S&P 500 ETF',
            'SGX19': 'Singapore Exchange',
            'SEMB19': 'SEMBCORP Industries',
            'BONDAS19': 'ABF Singapore Bond Index Fund',
            'UNH19': 'UnitedHealth Group'
        }

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ticker_id = 0

            for row in reader:
                dr_symbol = row['Symbol'].strip()
                yahoo_symbol = row['Ticker'].strip()

                if not dr_symbol or not yahoo_symbol:
                    continue

                ticker_id += 1

                # Determine exchange and currency from Yahoo symbol
                exchange, currency = self._extract_exchange_info(yahoo_symbol)

                info = TickerInfo(
                    ticker_id=ticker_id,
                    company_name=name_map.get(dr_symbol, dr_symbol.replace('19', '')),
                    exchange=exchange,
                    currency=currency,
                    dr_symbol=dr_symbol,
                    yahoo_symbol=yahoo_symbol,
                )

                # Add both symbols to cache
                self._cache[dr_symbol.upper()] = info
                self._cache[yahoo_symbol.upper()] = info

        logger.info(f"Loaded {ticker_id} tickers from CSV")

    def _extract_exchange_info(self, yahoo_symbol: str) -> tuple:
        """Extract exchange and currency from Yahoo symbol suffix."""
        exchange_map = {
            '.SI': ('SGX', 'SGD'),
            '.T': ('TSE', 'JPY'),
            '.HK': ('HKEX', 'HKD'),
            '.VN': ('HOSE', 'VND'),
            '.TW': ('TWSE', 'TWD'),
        }

        for suffix, (exchange, currency) in exchange_map.items():
            if yahoo_symbol.upper().endswith(suffix):
                return exchange, currency

        # Default to US market
        return 'NASDAQ', 'USD'

    # =========================================================================
    # Public API
    # =========================================================================

    def resolve(self, symbol: str) -> Optional[TickerInfo]:
        """Resolve any symbol to canonical TickerInfo.

        Args:
            symbol: Any symbol format (DR, Yahoo, ISIN, etc.)

        Returns:
            TickerInfo or None if not found

        Example:
            >>> resolver.resolve("NVDA19")
            TickerInfo(ticker_id=1, company_name='NVIDIA', dr_symbol='NVDA19', yahoo_symbol='NVDA')
            >>> resolver.resolve("NVDA")  # Same result
            TickerInfo(ticker_id=1, ...)
        """
        self._ensure_initialized()
        return self._cache.get(symbol.upper())

    def to_yahoo(self, symbol: str) -> Optional[str]:
        """Convert any symbol to Yahoo Finance format.

        Args:
            symbol: Any symbol format

        Returns:
            Yahoo symbol (e.g., 'NVDA', 'D05.SI') or None
        """
        info = self.resolve(symbol)
        return info.yahoo_symbol if info else None

    def to_dr(self, symbol: str) -> Optional[str]:
        """Convert any symbol to Thai DR format.

        Args:
            symbol: Any symbol format

        Returns:
            DR symbol (e.g., 'NVDA19', 'DBS19') or None
        """
        info = self.resolve(symbol)
        return info.dr_symbol if info else None

    def get_all_tickers(self) -> List[TickerInfo]:
        """Get all unique tickers.

        Returns:
            List of TickerInfo (deduplicated by ticker_id)
        """
        self._ensure_initialized()
        seen = set()
        result = []
        for info in self._cache.values():
            if info.ticker_id not in seen:
                seen.add(info.ticker_id)
                result.append(info)
        return result

    def get_yahoo_tickers(self) -> List[str]:
        """Get list of all Yahoo ticker symbols.

        Returns:
            List of Yahoo symbols
        """
        return [t.yahoo_symbol for t in self.get_all_tickers() if t.yahoo_symbol]

    def get_dr_symbols(self) -> List[str]:
        """Get list of all DR symbols.

        Returns:
            List of DR symbols
        """
        return [t.dr_symbol for t in self.get_all_tickers() if t.dr_symbol]

    def is_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported.

        Args:
            symbol: Any symbol format

        Returns:
            True if symbol resolves to a known ticker
        """
        return self.resolve(symbol) is not None

    def get_master_id(self, symbol: str) -> Optional[int]:
        """Get ticker_master.id for any symbol format.

        This is the canonical identifier that should be used for all data lookups.

        Args:
            symbol: Any symbol format (DR, Yahoo, etc.)

        Returns:
            ticker_master.id or None if not found

        Example:
            >>> resolver.get_master_id("NVDA19")  # Returns: 1
            >>> resolver.get_master_id("NVDA")    # Returns: 1 (same)
            >>> resolver.get_master_id("D05.SI")  # Returns: 2
        """
        info = self.resolve(symbol)
        return info.ticker_id if info else None

    # =========================================================================
    # Table Management
    # =========================================================================

    def create_tables(self) -> None:
        """Create ticker_master and ticker_aliases tables if they don't exist."""
        if self.client is None:
            self.client = get_aurora_client()

        self.client.execute(CREATE_TICKER_MASTER_TABLE, commit=True)
        logger.info("Created ticker_master table")

        self.client.execute(CREATE_TICKER_ALIASES_TABLE, commit=True)
        logger.info("Created ticker_aliases table")

    def populate_from_csv(self, csv_path: Optional[str] = None) -> int:
        """Populate Aurora tables from tickers.csv.

        Args:
            csv_path: Path to CSV file (auto-detected if not provided)

        Returns:
            Number of tickers inserted
        """
        if self.client is None:
            self.client = get_aurora_client()

        # Find CSV file
        if csv_path is None:
            csv_paths = [
                Path(__file__).parent.parent.parent.parent / "data" / "tickers.csv",
                Path("data/tickers.csv"),
                Path("tickers.csv"),
            ]
            for path in csv_paths:
                if path.exists():
                    csv_path = str(path)
                    break

        if csv_path is None:
            raise FileNotFoundError("tickers.csv not found")

        # Load CSV and company names
        self._load_from_csv()  # Populate cache with company names

        count = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                dr_symbol = row['Symbol'].strip()
                yahoo_symbol = row['Ticker'].strip()

                if not dr_symbol or not yahoo_symbol:
                    continue

                # Get info from cache (has company name)
                info = self._cache.get(dr_symbol.upper())
                if not info:
                    continue

                # Insert into ticker_master
                insert_master = f"""
                    INSERT INTO {TICKER_MASTER} (company_name, exchange, currency, sector, industry, quote_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                self.client.execute(
                    insert_master,
                    (info.company_name, info.exchange, info.currency,
                     info.sector, info.industry, info.quote_type),
                    commit=True
                )

                # Get the inserted ID
                result = self.client.fetch_one("SELECT LAST_INSERT_ID() as id")
                ticker_id = result['id']

                # Insert aliases
                insert_alias = f"""
                    INSERT INTO {TICKER_ALIASES} (ticker_id, symbol, symbol_type, is_primary)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE ticker_id = VALUES(ticker_id)
                """

                # DR symbol
                self.client.execute(
                    insert_alias,
                    (ticker_id, dr_symbol, 'dr', True),
                    commit=True
                )

                # Yahoo symbol
                self.client.execute(
                    insert_alias,
                    (ticker_id, yahoo_symbol, 'yahoo', True),
                    commit=True
                )

                count += 1
                logger.debug(f"Inserted ticker {dr_symbol} -> {yahoo_symbol}")

        logger.info(f"Populated {count} tickers into Aurora")

        # Refresh cache from Aurora
        self._initialized = False
        self._cache.clear()
        self._ensure_initialized()

        return count

    def refresh_cache(self) -> None:
        """Force refresh of in-memory cache from database."""
        self._initialized = False
        self._cache.clear()
        self._ensure_initialized()


# =============================================================================
# Singleton
# =============================================================================

_ticker_resolver: Optional[TickerResolver] = None


def get_ticker_resolver() -> TickerResolver:
    """Get or create global TickerResolver singleton.

    Returns:
        TickerResolver: Singleton instance

    Example:
        >>> resolver = get_ticker_resolver()
        >>> yahoo = resolver.to_yahoo("NVDA19")  # "NVDA"
    """
    global _ticker_resolver
    if _ticker_resolver is None:
        _ticker_resolver = TickerResolver()
    return _ticker_resolver
