# -*- coding: utf-8 -*-
"""
Ticker data fetcher for scheduled pre-caching.

Fetches Yahoo Finance data for all supported tickers and stores
in S3 cache (and optionally Aurora MySQL) for faster user responses.

Architecture:
    - S3 Cache: Primary storage for raw JSON data
    - Aurora MySQL: Optional relational storage for structured queries
"""

import os
import logging
from datetime import date
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from src.data.data_fetcher import DataFetcher
from src.data.s3_cache import S3Cache
from src.data.data_lake import DataLakeStorage

logger = logging.getLogger(__name__)


class TickerFetcher:
    """Fetches and caches ticker data for all supported tickers.

    Supports hybrid storage:
    - S3 for raw JSON data (always enabled)
    - Aurora MySQL for structured price data (optional)
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        enable_aurora: bool = False,
        data_lake_bucket: Optional[str] = None
    ):
        """
        Initialize TickerFetcher.

        Args:
            bucket_name: S3 bucket for cache storage. Defaults to PDF_BUCKET_NAME env var.
            enable_aurora: Enable writing to Aurora MySQL (default: False)
            data_lake_bucket: S3 bucket for data lake storage. Defaults to DATA_LAKE_BUCKET env var.
        """
        self.bucket_name = bucket_name or os.environ.get('PDF_BUCKET_NAME', 'line-bot-pdf-reports-755283537543')
        self.data_fetcher = DataFetcher()
        self.s3_cache = S3Cache(bucket_name=self.bucket_name, ttl_hours=24)
        self.tickers = self._load_supported_tickers()

        # Data Lake storage (optional, for raw data archival)
        self.data_lake = DataLakeStorage(bucket_name=data_lake_bucket)

        # Aurora MySQL integration (optional)
        self.enable_aurora = enable_aurora or os.environ.get('AURORA_ENABLED', 'false').lower() == 'true'
        self._aurora_repo = None

        if self.enable_aurora:
            try:
                from src.data.aurora import TickerRepository
                self._aurora_repo = TickerRepository()
                logger.info("Aurora MySQL integration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Aurora repository: {e}")
                self.enable_aurora = False

        # PrecomputeService for ticker_data table (ground truth storage)
        # Always enabled - Aurora is the primary data store
        print("🔧 DEBUG: About to initialize PrecomputeService")  # DEBUG
        try:
            from src.data.aurora.precompute_service import PrecomputeService
            self.precompute_service = PrecomputeService()
            print("🔧 DEBUG: PrecomputeService initialized successfully")  # DEBUG
            logger.info("PrecomputeService initialized for ticker_data storage")
        except Exception as e:
            print(f"🔧 DEBUG: PrecomputeService init FAILED: {e}")  # DEBUG
            logger.error(f"Failed to initialize PrecomputeService: {e}")
            self.precompute_service = None

        logger.info(
            f"TickerFetcher initialized with {len(self.tickers)} tickers, "
            f"bucket: {self.bucket_name}, "
            f"data_lake: {self.data_lake.is_enabled()}, "
            f"aurora: {self.enable_aurora}"
        )

    def _load_supported_tickers(self) -> List[str]:
        """
        Load supported tickers from CSV.

        Returns:
            List of Yahoo Finance ticker symbols
        """
        ticker_map = self.data_fetcher.load_tickers()
        # Return the Yahoo Finance ticker symbols (values), not the display symbols (keys)
        tickers = list(ticker_map.values())
        logger.info(f"Loaded {len(tickers)} supported tickers")
        return tickers

    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Convert numpy/pandas/datetime objects to JSON-serializable types.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable object
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            # Convert DataFrame to dict with string dates
            return obj.to_dict(orient='records')
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        return obj

    def fetch_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch data for a single ticker and cache it.

        Symbol-type invariant: Accepts any symbol format (DR, Yahoo, etc.)
        and automatically resolves to Yahoo Finance format for API calls and storage.

        Args:
            ticker: Ticker symbol in any format (e.g., 'DBS19' or 'D05.SI')

        Returns:
            Dict with status and data/error
        """
        # Resolve symbol to Yahoo Finance format for consistent storage
        # DataFetcher will also resolve internally, but we need Yahoo symbol for data lake storage
        from src.data.aurora.ticker_resolver import get_ticker_resolver
        resolver = get_ticker_resolver()
        ticker_info = resolver.resolve(ticker)
        yahoo_ticker = ticker_info.yahoo_symbol if ticker_info else ticker

        # TIMEZONE FIX: Use UTC date to match Aurora storage (Aurora runs in UTC)
        today = datetime.utcnow().date().isoformat()

        try:
            logger.info(f"Fetching data for {ticker} -> {yahoo_ticker}...")

            # Fetch from yfinance (DataFetcher handles symbol resolution internally)
            data = self.data_fetcher.fetch_ticker_data(ticker)

            # Store to Aurora ticker_data table (PRIMARY STORAGE - GROUND TRUTH)
            # This must succeed before other storage operations
            if self.precompute_service:
                try:
                    hist_df = data.get('history')
                    if isinstance(hist_df, pd.DataFrame) and not hist_df.empty:
                        price_history = hist_df.to_dict('records')
                    else:
                        price_history = []

                    # Extract company_info (all fields except history)
                    company_info = {k: v for k, v in data.items() if k != 'history'}

                    # TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
                    self.precompute_service.store_ticker_data(
                        symbol=ticker,
                        data_date=datetime.utcnow().date(),
                        price_history=price_history,
                        company_info=company_info,
                        financials=None  # Not fetched yet
                    )
                    logger.info(f"✅ Stored {ticker} to Aurora ticker_data table ({len(price_history)} rows)")
                except Exception as e:
                    logger.error(f"❌ Failed to store {ticker} to Aurora ticker_data: {e}", exc_info=True)
                    # CRITICAL: If Aurora storage fails, consider this a failure
                    # Aurora is the ground truth - without it, reports won't work
                    return {
                        'ticker': ticker,
                        'status': 'failed',
                        'error': f'Aurora ticker_data storage failed: {str(e)}'
                    }

            # Store raw data to data lake BEFORE processing (for data lineage)
            # This preserves the exact API response for reproducibility
            # Use Yahoo ticker for data lake storage (consistent with Yahoo Finance API)
            fetched_at = datetime.now()
            if self.data_lake.is_enabled():
                try:
                    # Make raw data JSON-serializable for data lake storage
                    raw_serializable = self._make_json_serializable(data)
                    data_lake_success = self.data_lake.store_raw_yfinance_data(
                        ticker=yahoo_ticker,  # Use resolved Yahoo symbol for storage
                        data=raw_serializable,
                        fetched_at=fetched_at
                    )
                    if data_lake_success:
                        logger.info(f"✅ Data lake stored raw data for {yahoo_ticker}")
                    else:
                        logger.warning(f"⚠️ Data lake storage failed for {yahoo_ticker} (non-blocking)")
                except Exception as e:
                    # Data lake storage failures should not block cache storage
                    logger.warning(f"⚠️ Data lake storage error for {yahoo_ticker} (non-blocking): {e}")

            # Make data JSON-serializable for cache storage
            serializable_data = self._make_json_serializable(data)

            # Store in S3 cache (always)
            cache_key = f"ticker_data"
            s3_success = self.s3_cache.put_json(
                cache_type=cache_key,
                ticker=ticker,
                date=today,
                filename='data.json',
                data=serializable_data
            )

            if not s3_success:
                return {
                    'ticker': ticker,
                    'status': 'failed',
                    'error': 'Failed to save to S3 cache'
                }

            logger.info(f"S3 cached {ticker} for {today}")

            # Store in Aurora MySQL (optional)
            # Use Yahoo ticker for Aurora storage (Aurora stores prices with Yahoo symbols)
            aurora_rows = 0
            if self.enable_aurora and self._aurora_repo:
                aurora_rows = self._write_to_aurora(yahoo_ticker, data)

            return {
                'ticker': ticker,
                'status': 'success',
                'date': today,
                'company_name': data.get('company_name', ticker),
                'aurora_rows': aurora_rows
            }

        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            return {
                'ticker': ticker,
                'status': 'failed',
                'error': str(e)
            }

    def _write_to_aurora(self, ticker: str, data: Dict[str, Any]) -> int:
        """
        Write ticker data to Aurora MySQL.

        Args:
            ticker: Yahoo Finance ticker symbol (must be resolved before calling)
            data: Data dict from DataFetcher

        Returns:
            Number of price rows written
        """
        if not self._aurora_repo:
            return 0

        try:
            # Upsert ticker info
            info = data.get('info', {})
            self._aurora_repo.upsert_ticker_info(
                symbol=ticker,
                display_name=info.get('shortName', ticker),
                company_name=info.get('longName'),
                exchange=info.get('exchange'),
                market=info.get('market'),
                currency=info.get('currency'),
                sector=info.get('sector'),
                industry=info.get('industry'),
                quote_type=info.get('quoteType'),
            )
            logger.debug(f"Aurora: upserted ticker_info for {ticker}")

            # Upsert historical prices
            history = data.get('history')
            if history is not None and isinstance(history, pd.DataFrame) and not history.empty:
                rows = self._aurora_repo.bulk_upsert_from_dataframe(ticker, history)
                logger.info(f"Aurora: upserted {rows} price rows for {ticker}")
                return rows

            return 0

        except Exception as e:
            logger.error(f"Aurora write failed for {ticker}: {e}")
            return 0

    def fetch_tickers(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Fetch data for specific tickers.

        Args:
            tickers: List of ticker symbols to fetch

        Returns:
            Dict with success/failed lists and summary
        """
        # TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
        results = {
            'success': [],
            'failed': [],
            'total': len(tickers),
            'date': datetime.utcnow().date().isoformat()
        }

        for ticker in tickers:
            result = self.fetch_ticker(ticker)

            if result['status'] == 'success':
                results['success'].append(result)
            else:
                results['failed'].append(result)

        results['success_count'] = len(results['success'])
        results['failed_count'] = len(results['failed'])

        logger.info(
            f"Fetch complete: {results['success_count']} success, "
            f"{results['failed_count']} failed out of {results['total']}"
        )

        return results

    def fetch_all_tickers(self) -> Dict[str, Any]:
        """
        Fetch data for all supported tickers.

        Returns:
            Dict with success/failed lists and summary
        """
        logger.info(f"Starting fetch for all {len(self.tickers)} tickers...")
        return self.fetch_tickers(self.tickers)

    def get_cached_ticker_data(self, ticker: str, fetch_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached ticker data from S3.

        Args:
            ticker: Yahoo Finance ticker symbol
            fetch_date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Cached data dict or None if not found
        """
        # TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
        if fetch_date is None:
            fetch_date = datetime.utcnow().date().isoformat()

        return self.s3_cache.get_json(
            cache_type='ticker_data',
            ticker=ticker,
            date=fetch_date,
            filename='data.json'
        )
