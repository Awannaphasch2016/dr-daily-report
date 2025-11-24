"""Ticker search and lookup service"""

import csv
from pathlib import Path
from typing import Optional
from .models import SearchResult


class TickerService:
    """Service for ticker search and lookup"""

    def __init__(self, ticker_csv_path: str | None = None):
        """Initialize ticker service

        Args:
            ticker_csv_path: Path to tickers.csv (defaults to data/tickers.csv)
        """
        if ticker_csv_path is None:
            # Default to data/tickers.csv relative to project root
            ticker_csv_path = str(Path(__file__).parent.parent.parent / "data" / "tickers.csv")

        self.ticker_map: dict[str, str] = {}  # Symbol -> Yahoo ticker
        self.ticker_info: dict[str, dict] = {}  # Symbol -> full info
        self._load_tickers(ticker_csv_path)

    def _load_tickers(self, csv_path: str) -> None:
        """Load tickers from CSV file"""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row['Symbol'].strip()
                yahoo_ticker = row['Ticker'].strip()

                if not symbol or not yahoo_ticker:
                    continue

                self.ticker_map[symbol] = yahoo_ticker

                # Parse ticker info
                company_name = self._extract_company_name(symbol)
                exchange = self._extract_exchange(yahoo_ticker)
                currency = self._extract_currency(exchange)

                self.ticker_info[symbol] = {
                    'symbol': symbol,
                    'yahoo_ticker': yahoo_ticker,
                    'company_name': company_name,
                    'exchange': exchange,
                    'currency': currency,
                    'type': 'equity'
                }

    def _extract_company_name(self, symbol: str) -> str:
        """Extract company name from symbol"""
        # Simple mapping - can be enhanced with external data source
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
            'MITSU19': 'Mitsubishi Motors',
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
        return name_map.get(symbol, symbol.replace('19', ''))

    def _extract_exchange(self, yahoo_ticker: str) -> str:
        """Extract exchange from Yahoo ticker"""
        if yahoo_ticker.endswith('.SI'):
            return 'SGX'
        elif yahoo_ticker.endswith('.T'):
            return 'TSE'
        elif yahoo_ticker.endswith('.HK'):
            return 'HKEX'
        elif yahoo_ticker.endswith('.VN'):
            return 'HOSE'
        elif yahoo_ticker.endswith('.TW'):
            return 'TWSE'
        else:
            return 'NASDAQ'  # US tickers without suffix

    def _extract_currency(self, exchange: str) -> str:
        """Extract currency from exchange"""
        currency_map = {
            'SGX': 'SGD',
            'TSE': 'JPY',
            'HKEX': 'HKD',
            'HOSE': 'VND',
            'TWSE': 'TWD',
            'NASDAQ': 'USD',
            'NYSE': 'USD'
        }
        return currency_map.get(exchange, 'USD')

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search tickers by query string

        Args:
            query: Search query (ticker or company name)
            limit: Maximum results to return

        Returns:
            List of matching SearchResult objects
        """
        query_upper = query.upper().strip()
        results = []

        for symbol, info in self.ticker_info.items():
            # Match by symbol prefix or company name substring
            if (symbol.upper().startswith(query_upper) or
                query_upper in info['company_name'].upper()):
                results.append(SearchResult(
                    ticker=info['symbol'],
                    company_name=info['company_name'],
                    exchange=info['exchange'],
                    currency=info['currency'],
                    type=info['type']
                ))

        # Sort by relevance (exact match first, then starts-with, then contains)
        def sort_key(result: SearchResult) -> tuple:
            ticker_upper = result.ticker.upper()
            if ticker_upper == query_upper:
                return (0, result.ticker)  # Exact match
            elif ticker_upper.startswith(query_upper):
                return (1, result.ticker)  # Starts with
            else:
                return (2, result.ticker)  # Contains in name

        results.sort(key=sort_key)
        return results[:limit]

    def get_ticker_info(self, symbol: str) -> dict | None:
        """Get full ticker info by symbol

        Args:
            symbol: Ticker symbol (e.g., 'NVDA19')

        Returns:
            Ticker info dict or None if not found
        """
        return self.ticker_info.get(symbol.upper())

    def get_yahoo_ticker(self, symbol: str) -> str | None:
        """Get Yahoo Finance ticker for a symbol

        Args:
            symbol: Ticker symbol (e.g., 'NVDA19')

        Returns:
            Yahoo ticker (e.g., 'NVDA') or None if not found
        """
        return self.ticker_map.get(symbol.upper())

    def is_supported(self, symbol: str) -> bool:
        """Check if ticker is supported

        Args:
            symbol: Ticker symbol

        Returns:
            True if ticker is in supported list
        """
        return symbol.upper() in self.ticker_map


# Global ticker service instance
_ticker_service: TickerService | None = None


def get_ticker_service() -> TickerService:
    """Get or create global ticker service instance"""
    global _ticker_service
    if _ticker_service is None:
        _ticker_service = TickerService()
    return _ticker_service
