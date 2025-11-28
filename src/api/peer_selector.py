"""
Peer Selector Service

Identifies similar tickers based on correlation analysis for peer comparison.

Features:
- Uses ComparativeAnalyzer for correlation calculations
- Fetches historical price data for correlation analysis
- Returns peer tickers with correlation scores
- Integration with API models
"""

import asyncio
import logging
from typing import List, Dict, Optional
from pathlib import Path

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field

from src.analysis.comparative_analysis import ComparativeAnalyzer
from src.api.models import Peer
from src.api.ticker_service import get_ticker_service

logger = logging.getLogger(__name__)


class PeerInfo(BaseModel):
    """Information about a peer ticker"""
    ticker: str = Field(..., description="Ticker symbol")
    company_name: str = Field(..., description="Company name")
    correlation: float = Field(..., description="Correlation with target ticker (-1 to 1)")
    price_change_pct: float = Field(default=0.0, description="Price change percentage")
    estimated_upside_pct: Optional[float] = Field(None, description="Estimated upside")
    stance: str = Field(default="neutral", description="Investment stance")
    valuation_label: str = Field(default="fair", description="Valuation assessment")


class PeerSelectorService:
    """
    Service for selecting peer tickers based on correlation analysis

    Uses historical price data and correlation analysis to identify similar tickers
    for comparison purposes.
    """

    def __init__(self):
        """Initialize peer selector service"""
        self._analyzer = ComparativeAnalyzer()
        self._ticker_service = get_ticker_service()
        # Get ticker map from ticker service
        self._ticker_map = self._ticker_service.ticker_map  # Symbol -> Yahoo ticker
        logger.info(f"PeerSelectorService initialized with {len(self._ticker_map)} tickers")

    def find_peers(
        self,
        target_ticker: str,
        correlation_matrix: pd.DataFrame,
        limit: int = 5,
        min_correlation: float = 0.3
    ) -> List[PeerInfo]:
        """
        Find peer tickers similar to target ticker

        Args:
            target_ticker: Target ticker symbol (e.g., 'NVDA19')
            correlation_matrix: Pre-calculated correlation matrix
            limit: Maximum number of peers to return
            min_correlation: Minimum absolute correlation to include

        Returns:
            List of PeerInfo objects sorted by correlation
        """
        if correlation_matrix.empty or target_ticker not in correlation_matrix.index:
            logger.warning(f"Ticker {target_ticker} not found in correlation matrix")
            return []

        # Find similar tickers using ComparativeAnalyzer
        similar_tickers = self._analyzer.find_similar_tickers(
            correlation_matrix,
            target_ticker,
            top_n=limit * 2  # Get extra to filter by min_correlation
        )

        if not similar_tickers:
            logger.info(f"No similar tickers found for {target_ticker}")
            return []

        # Filter by minimum correlation and convert to PeerInfo
        peers = []
        for ticker, correlation in similar_tickers:
            if abs(correlation) < min_correlation:
                continue

            # Get company name
            company_name = self._get_company_name(ticker)

            # Create PeerInfo with defaults (will be updated with real data later)
            peer_info = PeerInfo(
                ticker=ticker,
                company_name=company_name,
                correlation=round(correlation, 3),
                price_change_pct=0.0,  # Will be updated
                estimated_upside_pct=None,
                stance="neutral",  # Will be updated based on price change
                valuation_label="fair"  # Default
            )
            peers.append(peer_info)

            if len(peers) >= limit:
                break

        return peers

    async def find_peers_async(
        self,
        target_ticker: str,
        limit: int = 5,
        period: str = '3mo',
        min_correlation: float = 0.3
    ) -> List[PeerInfo]:
        """
        Find peers by fetching historical data and calculating correlations

        Args:
            target_ticker: Target ticker symbol
            limit: Maximum number of peers
            period: Historical data period (e.g., '3mo', '6mo', '1y')
            min_correlation: Minimum absolute correlation

        Returns:
            List of PeerInfo with correlation data and current prices
        """
        try:
            # Get all ticker symbols
            all_symbols = list(self._ticker_map.keys())

            if target_ticker not in all_symbols:
                logger.warning(f"Target ticker {target_ticker} not in ticker list")
                return []

            # Fetch historical data for all tickers
            logger.info(f"Fetching historical data for correlation analysis (period={period})")
            ticker_data = await self._fetch_historical_data(all_symbols, period=period)

            if not ticker_data or target_ticker not in ticker_data:
                logger.warning(f"No historical data available for {target_ticker}")
                return []

            # Calculate correlation matrix
            correlation_matrix = self._analyzer.calculate_correlation_matrix(ticker_data)

            if correlation_matrix.empty:
                logger.warning("Failed to calculate correlation matrix")
                return []

            # Find peers using correlation matrix
            peers = self.find_peers(target_ticker, correlation_matrix, limit, min_correlation)

            # Fetch current prices for peers
            if peers:
                peer_tickers = [p.ticker for p in peers]
                current_data = await self._get_peer_current_data(peer_tickers)

                # Update peers with current data
                for peer in peers:
                    if peer.ticker in current_data:
                        data = current_data[peer.ticker]
                        peer.price_change_pct = data.get('price_change_pct', 0.0)

                        # Generate stance based on price change (simple heuristic)
                        peer.stance = self._calculate_stance(peer.price_change_pct)

                        # Update upside and valuation from real data
                        peer.estimated_upside_pct = data.get('estimated_upside_pct')
                        peer.valuation_label = data.get('valuation_label', 'unknown')

            return peers

        except Exception as e:
            logger.error(f"Error finding peers for {target_ticker}: {e}", exc_info=True)
            return []

    async def _fetch_historical_data(
        self,
        symbols: List[str],
        period: str = '3mo'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for multiple tickers

        Args:
            symbols: List of ticker symbols
            period: Historical period ('1mo', '3mo', '6mo', '1y', etc.)

        Returns:
            Dict mapping symbols to DataFrames with price history
        """
        try:
            # Convert symbols to Yahoo tickers
            yahoo_tickers = []
            symbol_to_yahoo = {}
            for symbol in symbols:
                yahoo_ticker = self._ticker_map.get(symbol)
                if yahoo_ticker:
                    yahoo_tickers.append(yahoo_ticker)
                    symbol_to_yahoo[yahoo_ticker] = symbol

            if not yahoo_tickers:
                logger.warning("No valid yahoo tickers to fetch")
                return {}

            # Fetch data in thread pool
            loop = asyncio.get_event_loop()
            logger.info(f"Downloading historical data for {len(yahoo_tickers)} tickers...")

            # yfinance.download is synchronous, run in executor
            def download_data():
                return yf.download(
                    ' '.join(yahoo_tickers),
                    period=period,
                    group_by='ticker',
                    progress=False,
                    threads=True
                )

            df = await loop.run_in_executor(None, download_data)

            if df.empty:
                logger.warning("No data returned from yfinance")
                return {}

            # Convert to dict of DataFrames (one per symbol)
            ticker_data = {}
            for yahoo_ticker in yahoo_tickers:
                symbol = symbol_to_yahoo[yahoo_ticker]
                try:
                    # Handle multi-ticker and single-ticker formats
                    if len(yahoo_tickers) == 1:
                        ticker_df = df
                    else:
                        ticker_df = df[yahoo_ticker]

                    if not ticker_df.empty and 'Close' in ticker_df.columns:
                        ticker_data[symbol] = ticker_df

                except (KeyError, AttributeError) as e:
                    logger.debug(f"No data for {symbol}: {e}")
                    continue

            logger.info(f"Successfully fetched data for {len(ticker_data)} tickers")
            return ticker_data

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}", exc_info=True)
            return {}

    async def _get_peer_current_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get current price and change data for peer tickers

        Args:
            symbols: List of ticker symbols

        Returns:
            Dict mapping symbols to current market data
        """
        try:
            result = {}

            # Fetch data for each ticker
            tasks = [self._fetch_single_ticker_data(symbol) for symbol in symbols]
            ticker_results = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, data in zip(symbols, ticker_results):
                if isinstance(data, dict) and data:
                    result[symbol] = data

            return result

        except Exception as e:
            logger.error(f"Error fetching peer current data: {e}")
            return {}

    async def _fetch_single_ticker_data(self, symbol: str) -> Optional[Dict]:
        """Fetch current data for a single ticker including upside and valuation"""
        try:
            yahoo_ticker = self._ticker_map.get(symbol)
            if not yahoo_ticker:
                return None

            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yahoo_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)

            price = info.get('regularMarketPrice') or info.get('currentPrice')
            prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')

            if not price or not prev_close:
                return None

            price_change_pct = ((price - prev_close) / prev_close) * 100

            # Calculate upside and valuation from info
            estimated_upside = self._calculate_upside(info)
            valuation_label = self._get_valuation_label(info)

            return {
                'price_change_pct': round(price_change_pct, 2),
                'estimated_upside_pct': estimated_upside,
                'valuation_label': valuation_label
            }

        except Exception as e:
            logger.debug(f"Error fetching data for {symbol}: {e}")
            return None

    def _calculate_stance(self, price_change_pct: float) -> str:
        """
        Calculate investment stance based on price change

        Simple heuristic:
        - > 2%: bullish
        - < -2%: bearish
        - else: neutral

        Args:
            price_change_pct: Price change percentage

        Returns:
            Stance label ('bullish', 'bearish', or 'neutral')
        """
        if price_change_pct > 2.0:
            return "bullish"
        elif price_change_pct < -2.0:
            return "bearish"
        else:
            return "neutral"

    def _calculate_upside(self, info: Dict) -> Optional[float]:
        """
        Calculate estimated upside based on analyst target price

        Args:
            info: yfinance ticker info dict

        Returns:
            Upside percentage (positive) or downside (negative), or None if unavailable
        """
        try:
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            target_price = info.get('targetMeanPrice')

            if current_price and target_price and current_price > 0:
                upside = ((target_price - current_price) / current_price) * 100
                return round(upside, 1)

            return None
        except Exception as e:
            logger.debug(f"Error calculating upside: {e}")
            return None

    def _get_valuation_label(self, info: Dict) -> str:
        """
        Determine valuation label based on P/E ratio

        Uses forward P/E if available, falls back to trailing P/E.
        Market average P/E ~20 used as benchmark.

        Thresholds:
        - P/E < 15: cheap
        - P/E 15-30: fair
        - P/E > 30: expensive

        Args:
            info: yfinance ticker info dict

        Returns:
            Valuation label ('cheap', 'fair', 'expensive')
        """
        try:
            # Prefer forward P/E, fall back to trailing
            pe_ratio = info.get('forwardPE') or info.get('trailingPE')

            if pe_ratio is None:
                return "fair"

            # Simple thresholds based on market averages
            if pe_ratio < 15:
                return "cheap"
            elif pe_ratio > 30:
                return "expensive"
            else:
                return "fair"

        except Exception as e:
            logger.debug(f"Error determining valuation label: {e}")
            return "fair"

    def _get_company_name(self, symbol: str) -> str:
        """Get company name for a ticker symbol"""
        try:
            ticker_info = self._ticker_service.ticker_info.get(symbol)
            if ticker_info:
                return ticker_info.get('company_name', symbol)
            return symbol
        except Exception:
            return symbol

    def to_api_peer(self, peer_info: PeerInfo) -> Peer:
        """
        Convert PeerInfo to API Peer model

        Args:
            peer_info: PeerInfo object

        Returns:
            Peer model for API responses
        """
        return Peer(
            ticker=peer_info.ticker,
            company_name=peer_info.company_name,
            estimated_upside_pct=peer_info.estimated_upside_pct,
            stance=peer_info.stance,
            valuation_label=peer_info.valuation_label
        )


# Singleton instance
_peer_selector_service: Optional[PeerSelectorService] = None


def get_peer_selector_service() -> PeerSelectorService:
    """Get or create singleton PeerSelectorService instance"""
    global _peer_selector_service
    if _peer_selector_service is None:
        _peer_selector_service = PeerSelectorService()
    return _peer_selector_service
