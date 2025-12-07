# -*- coding: utf-8 -*-
"""
Precompute Service

Computes and stores technical indicators, percentiles, comparative features,
and full reports for instant retrieval.

Usage:
    from src.data.aurora.precompute_service import PrecomputeService
    service = PrecomputeService()

    # Compute for single ticker
    result = service.compute_for_ticker('NVDA19')

    # Compute for all tickers
    results = service.compute_all()
"""

import json
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PrecomputeService:
    """Service for precomputing and storing ticker analysis data."""

    def __init__(self):
        """Initialize the precompute service."""
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.repository import TickerRepository
        from src.analysis.technical_analysis import TechnicalAnalyzer

        self.client = get_aurora_client()
        self.repo = TickerRepository(client=self.client)
        self.analyzer = TechnicalAnalyzer()

    # =========================================================================
    # Daily Indicators
    # =========================================================================

    def compute_daily_indicators(
        self,
        symbol: str,
        hist_df: pd.DataFrame,
        indicator_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Compute all technical indicators for a ticker.

        Args:
            symbol: Ticker symbol
            hist_df: DataFrame with OHLCV data
            indicator_date: Date to compute for (defaults to latest)

        Returns:
            Dict with computed indicators
        """
        if hist_df.empty:
            return {}

        indicator_date = indicator_date or date.today()

        # Compute all indicators
        df = self.analyzer.calculate_historical_indicators(hist_df)
        if df is None or df.empty:
            return {}

        # Get latest row
        latest = df.iloc[-1]

        return {
            'symbol': symbol,
            'indicator_date': indicator_date,
            'open_price': self._safe_float(latest.get('Open')),
            'high_price': self._safe_float(latest.get('High')),
            'low_price': self._safe_float(latest.get('Low')),
            'close_price': self._safe_float(latest.get('Close')),
            'volume': self._safe_int(latest.get('Volume')),
            'sma_20': self._safe_float(latest.get('SMA_20')),
            'sma_50': self._safe_float(latest.get('SMA_50')),
            'sma_200': self._safe_float(latest.get('SMA_200')),
            'rsi_14': self._safe_float(latest.get('RSI')),
            'macd': self._safe_float(latest.get('MACD')),
            'macd_signal': self._safe_float(latest.get('MACD_Signal')),
            'macd_histogram': self._safe_float(
                latest.get('MACD') - latest.get('MACD_Signal')
                if latest.get('MACD') and latest.get('MACD_Signal') else None
            ),
            'bb_upper': self._safe_float(latest.get('BB_Upper')),
            'bb_middle': self._safe_float(latest.get('BB_Middle')),
            'bb_lower': self._safe_float(latest.get('BB_Lower')),
            'atr_14': self._safe_float(latest.get('ATR')),
            'atr_percent': self._safe_float(
                (latest.get('ATR') / latest.get('Close') * 100)
                if latest.get('ATR') and latest.get('Close') else None
            ),
            'vwap': self._safe_float(latest.get('VWAP')),
            'volume_sma_20': self._safe_int(latest.get('Volume_SMA')),
            'volume_ratio': self._safe_float(latest.get('Volume_Ratio')),
            'uncertainty_score': self._safe_float(latest.get('Uncertainty_Score')),
            'price_vwap_pct': self._safe_float(latest.get('Price_VWAP_Pct')),
        }

    def store_daily_indicators(self, symbol: str, indicators: Dict[str, Any]) -> int:
        """Store daily indicators in Aurora.

        Args:
            symbol: Ticker symbol
            indicators: Dict with indicator values

        Returns:
            Number of affected rows
        """
        if not indicators:
            return 0

        # Get ticker_id
        ticker_info = self.repo.get_ticker_info(symbol)
        if not ticker_info:
            logger.warning(f"Ticker not found: {symbol}")
            return 0

        ticker_id = ticker_info['id']

        query = """
            INSERT INTO daily_indicators (
                ticker_id, symbol, indicator_date,
                open_price, high_price, low_price, close_price, volume,
                sma_20, sma_50, sma_200,
                rsi_14, macd, macd_signal, macd_histogram,
                bb_upper, bb_middle, bb_lower, atr_14, atr_percent,
                vwap, volume_sma_20, volume_ratio,
                uncertainty_score, price_vwap_pct
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                volume = VALUES(volume),
                sma_20 = VALUES(sma_20),
                sma_50 = VALUES(sma_50),
                sma_200 = VALUES(sma_200),
                rsi_14 = VALUES(rsi_14),
                macd = VALUES(macd),
                macd_signal = VALUES(macd_signal),
                macd_histogram = VALUES(macd_histogram),
                bb_upper = VALUES(bb_upper),
                bb_middle = VALUES(bb_middle),
                bb_lower = VALUES(bb_lower),
                atr_14 = VALUES(atr_14),
                atr_percent = VALUES(atr_percent),
                vwap = VALUES(vwap),
                volume_sma_20 = VALUES(volume_sma_20),
                volume_ratio = VALUES(volume_ratio),
                uncertainty_score = VALUES(uncertainty_score),
                price_vwap_pct = VALUES(price_vwap_pct),
                computed_at = NOW()
        """

        params = (
            ticker_id,
            symbol,
            indicators['indicator_date'],
            indicators.get('open_price'),
            indicators.get('high_price'),
            indicators.get('low_price'),
            indicators.get('close_price'),
            indicators.get('volume'),
            indicators.get('sma_20'),
            indicators.get('sma_50'),
            indicators.get('sma_200'),
            indicators.get('rsi_14'),
            indicators.get('macd'),
            indicators.get('macd_signal'),
            indicators.get('macd_histogram'),
            indicators.get('bb_upper'),
            indicators.get('bb_middle'),
            indicators.get('bb_lower'),
            indicators.get('atr_14'),
            indicators.get('atr_percent'),
            indicators.get('vwap'),
            indicators.get('volume_sma_20'),
            indicators.get('volume_ratio'),
            indicators.get('uncertainty_score'),
            indicators.get('price_vwap_pct'),
        )

        return self.client.execute(query, params, commit=True)

    # =========================================================================
    # Percentiles
    # =========================================================================

    def compute_percentiles(
        self,
        symbol: str,
        hist_df: pd.DataFrame,
        percentile_date: Optional[date] = None,
        lookback_days: int = 365
    ) -> Dict[str, Any]:
        """Compute percentile statistics for a ticker.

        Args:
            symbol: Ticker symbol
            hist_df: DataFrame with OHLCV data
            percentile_date: Date to compute for (defaults to latest)
            lookback_days: Number of days for percentile calculation

        Returns:
            Dict with percentile values
        """
        if hist_df.empty:
            return {}

        percentile_date = percentile_date or date.today()

        # Compute indicators with percentiles
        result = self.analyzer.calculate_all_indicators_with_percentiles(hist_df)
        if result is None:
            return {}

        indicators = result.get('indicators', {})
        percentiles = result.get('percentiles', {})

        output = {
            'symbol': symbol,
            'percentile_date': percentile_date,
            'lookback_days': lookback_days,
            'current_price_percentile': self._safe_float(
                self._calculate_price_percentile(hist_df)
            ),
        }

        # RSI percentiles
        if 'rsi' in percentiles:
            rsi_p = percentiles['rsi']
            output.update({
                'rsi_percentile': self._safe_float(rsi_p.get('percentile')),
                'rsi_mean': self._safe_float(rsi_p.get('mean')),
                'rsi_std': self._safe_float(rsi_p.get('std')),
                'rsi_freq_above_70': self._safe_float(rsi_p.get('frequency_above_70')),
                'rsi_freq_below_30': self._safe_float(rsi_p.get('frequency_below_30')),
            })

        # MACD percentiles
        if 'macd' in percentiles:
            macd_p = percentiles['macd']
            output.update({
                'macd_percentile': self._safe_float(macd_p.get('percentile')),
                'macd_freq_positive': self._safe_float(macd_p.get('frequency_positive')),
            })

        # Uncertainty percentiles
        if 'uncertainty_score' in percentiles:
            unc_p = percentiles['uncertainty_score']
            output.update({
                'uncertainty_percentile': self._safe_float(unc_p.get('percentile')),
                'uncertainty_freq_low': self._safe_float(unc_p.get('frequency_low')),
                'uncertainty_freq_high': self._safe_float(unc_p.get('frequency_high')),
            })

        # ATR percentiles
        if 'atr_percent' in percentiles:
            atr_p = percentiles['atr_percent']
            output.update({
                'atr_pct_percentile': self._safe_float(atr_p.get('percentile')),
                'atr_freq_low': self._safe_float(atr_p.get('frequency_low_volatility')),
                'atr_freq_high': self._safe_float(atr_p.get('frequency_high_volatility')),
            })

        # Volume percentiles
        if 'volume_ratio' in percentiles:
            vol_p = percentiles['volume_ratio']
            output.update({
                'volume_ratio_percentile': self._safe_float(vol_p.get('percentile')),
                'volume_freq_high': self._safe_float(vol_p.get('frequency_high_volume')),
                'volume_freq_low': self._safe_float(vol_p.get('frequency_low_volume')),
            })

        # SMA deviation percentiles
        for sma_period in [20, 50, 200]:
            key = f'sma_{sma_period}_deviation'
            if key in percentiles:
                output[f'sma_{sma_period}_dev_percentile'] = self._safe_float(
                    percentiles[key].get('percentile')
                )

        return output

    def store_percentiles(self, symbol: str, percentiles: Dict[str, Any]) -> int:
        """Store percentile data in Aurora.

        Args:
            symbol: Ticker symbol
            percentiles: Dict with percentile values

        Returns:
            Number of affected rows
        """
        if not percentiles:
            return 0

        ticker_info = self.repo.get_ticker_info(symbol)
        if not ticker_info:
            return 0

        ticker_id = ticker_info['id']

        query = """
            INSERT INTO indicator_percentiles (
                ticker_id, symbol, percentile_date, lookback_days,
                current_price_percentile,
                rsi_percentile, rsi_mean, rsi_std, rsi_freq_above_70, rsi_freq_below_30,
                macd_percentile, macd_freq_positive,
                uncertainty_percentile, uncertainty_freq_low, uncertainty_freq_high,
                atr_pct_percentile, atr_freq_low, atr_freq_high,
                volume_ratio_percentile, volume_freq_high, volume_freq_low,
                sma_20_dev_percentile, sma_50_dev_percentile, sma_200_dev_percentile
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                lookback_days = VALUES(lookback_days),
                current_price_percentile = VALUES(current_price_percentile),
                rsi_percentile = VALUES(rsi_percentile),
                rsi_mean = VALUES(rsi_mean),
                rsi_std = VALUES(rsi_std),
                rsi_freq_above_70 = VALUES(rsi_freq_above_70),
                rsi_freq_below_30 = VALUES(rsi_freq_below_30),
                macd_percentile = VALUES(macd_percentile),
                macd_freq_positive = VALUES(macd_freq_positive),
                uncertainty_percentile = VALUES(uncertainty_percentile),
                uncertainty_freq_low = VALUES(uncertainty_freq_low),
                uncertainty_freq_high = VALUES(uncertainty_freq_high),
                atr_pct_percentile = VALUES(atr_pct_percentile),
                atr_freq_low = VALUES(atr_freq_low),
                atr_freq_high = VALUES(atr_freq_high),
                volume_ratio_percentile = VALUES(volume_ratio_percentile),
                volume_freq_high = VALUES(volume_freq_high),
                volume_freq_low = VALUES(volume_freq_low),
                sma_20_dev_percentile = VALUES(sma_20_dev_percentile),
                sma_50_dev_percentile = VALUES(sma_50_dev_percentile),
                sma_200_dev_percentile = VALUES(sma_200_dev_percentile),
                computed_at = NOW()
        """

        params = (
            ticker_id,
            symbol,
            percentiles['percentile_date'],
            percentiles.get('lookback_days', 365),
            percentiles.get('current_price_percentile'),
            percentiles.get('rsi_percentile'),
            percentiles.get('rsi_mean'),
            percentiles.get('rsi_std'),
            percentiles.get('rsi_freq_above_70'),
            percentiles.get('rsi_freq_below_30'),
            percentiles.get('macd_percentile'),
            percentiles.get('macd_freq_positive'),
            percentiles.get('uncertainty_percentile'),
            percentiles.get('uncertainty_freq_low'),
            percentiles.get('uncertainty_freq_high'),
            percentiles.get('atr_pct_percentile'),
            percentiles.get('atr_freq_low'),
            percentiles.get('atr_freq_high'),
            percentiles.get('volume_ratio_percentile'),
            percentiles.get('volume_freq_high'),
            percentiles.get('volume_freq_low'),
            percentiles.get('sma_20_dev_percentile'),
            percentiles.get('sma_50_dev_percentile'),
            percentiles.get('sma_200_dev_percentile'),
        )

        return self.client.execute(query, params, commit=True)

    # =========================================================================
    # Comparative Features
    # =========================================================================

    def compute_comparative_features(
        self,
        symbol: str,
        hist_df: pd.DataFrame,
        feature_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Compute comparative analysis features for a ticker.

        Args:
            symbol: Ticker symbol
            hist_df: DataFrame with OHLCV data
            feature_date: Date to compute for

        Returns:
            Dict with feature values
        """
        if hist_df.empty or len(hist_df) < 30:
            return {}

        feature_date = feature_date or date.today()

        prices = hist_df['Close']
        returns = prices.pct_change().dropna()

        if len(returns) < 30:
            return {}

        # Returns
        daily_return = returns.iloc[-1] if len(returns) > 0 else None
        weekly_return = (prices.iloc[-1] / prices.iloc[-5] - 1) if len(prices) > 5 else None
        monthly_return = (prices.iloc[-1] / prices.iloc[-22] - 1) if len(prices) > 22 else None

        # YTD return
        ytd_return = None
        try:
            year_start = hist_df[hist_df.index.year == datetime.now().year].iloc[0]['Close']
            ytd_return = (prices.iloc[-1] / year_start - 1)
        except (IndexError, KeyError):
            pass

        # Volatility
        volatility_30d = returns.tail(30).std() * np.sqrt(252) if len(returns) >= 30 else None
        volatility_90d = returns.tail(90).std() * np.sqrt(252) if len(returns) >= 90 else None

        # Sharpe ratio (assuming risk-free rate = 0)
        sharpe_30d = None
        sharpe_90d = None
        if volatility_30d and volatility_30d > 0:
            sharpe_30d = (returns.tail(30).mean() * 252) / volatility_30d
        if volatility_90d and volatility_90d > 0:
            sharpe_90d = (returns.tail(90).mean() * 252) / volatility_90d

        # Max drawdown
        max_dd_30d = self._calculate_max_drawdown(prices.tail(30))
        max_dd_90d = self._calculate_max_drawdown(prices.tail(90))

        return {
            'symbol': symbol,
            'feature_date': feature_date,
            'daily_return': self._safe_float(daily_return),
            'weekly_return': self._safe_float(weekly_return),
            'monthly_return': self._safe_float(monthly_return),
            'ytd_return': self._safe_float(ytd_return),
            'volatility_30d': self._safe_float(volatility_30d),
            'volatility_90d': self._safe_float(volatility_90d),
            'sharpe_ratio_30d': self._safe_float(sharpe_30d),
            'sharpe_ratio_90d': self._safe_float(sharpe_90d),
            'max_drawdown_30d': self._safe_float(max_dd_30d),
            'max_drawdown_90d': self._safe_float(max_dd_90d),
            'rs_vs_set': None,  # Computed separately across all tickers
        }

    def store_comparative_features(self, symbol: str, features: Dict[str, Any]) -> int:
        """Store comparative features in Aurora.

        Args:
            symbol: Ticker symbol
            features: Dict with feature values

        Returns:
            Number of affected rows
        """
        if not features:
            return 0

        ticker_info = self.repo.get_ticker_info(symbol)
        if not ticker_info:
            return 0

        ticker_id = ticker_info['id']

        query = """
            INSERT INTO comparative_features (
                ticker_id, symbol, feature_date,
                daily_return, weekly_return, monthly_return, ytd_return,
                volatility_30d, volatility_90d,
                sharpe_ratio_30d, sharpe_ratio_90d,
                max_drawdown_30d, max_drawdown_90d,
                rs_vs_set
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                daily_return = VALUES(daily_return),
                weekly_return = VALUES(weekly_return),
                monthly_return = VALUES(monthly_return),
                ytd_return = VALUES(ytd_return),
                volatility_30d = VALUES(volatility_30d),
                volatility_90d = VALUES(volatility_90d),
                sharpe_ratio_30d = VALUES(sharpe_ratio_30d),
                sharpe_ratio_90d = VALUES(sharpe_ratio_90d),
                max_drawdown_30d = VALUES(max_drawdown_30d),
                max_drawdown_90d = VALUES(max_drawdown_90d),
                rs_vs_set = VALUES(rs_vs_set),
                computed_at = NOW()
        """

        params = (
            ticker_id,
            symbol,
            features['feature_date'],
            features.get('daily_return'),
            features.get('weekly_return'),
            features.get('monthly_return'),
            features.get('ytd_return'),
            features.get('volatility_30d'),
            features.get('volatility_90d'),
            features.get('sharpe_ratio_30d'),
            features.get('sharpe_ratio_90d'),
            features.get('max_drawdown_30d'),
            features.get('max_drawdown_90d'),
            features.get('rs_vs_set'),
        )

        return self.client.execute(query, params, commit=True)

    # =========================================================================
    # Report Precomputation
    # =========================================================================

    def _enhance_report_json_with_portfolio_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Add price_history and projections to report_json for storage.

        Args:
            state: AgentState dict from workflow

        Returns:
            Enhanced state with price_history and projections
        """
        try:
            from src.analysis.projection_calculator import ProjectionCalculator

            ticker_data = state.get('ticker_data', {})
            history_df = ticker_data.get('history')

            if history_df is None or (hasattr(history_df, 'empty') and history_df.empty):
                logger.debug("No history data for portfolio calculations")
                return state

            # Extract close prices and dates
            close_prices = history_df['Close'].tolist()
            dates = [idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                     for idx in history_df.index]

            # Calculate projections
            calc = ProjectionCalculator(initial_investment=1000.0)
            projections = calc.calculate_projections(close_prices, dates, days_ahead=7)

            # Convert DataFrame to OHLCV dict list for price_history
            price_history = []
            for idx, row in history_df.iterrows():
                price_history.append({
                    'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                })

            # Enhance with portfolio metrics (cumulative value, returns, etc.)
            price_history_enhanced = calc.enhance_historical_data(price_history)

            # Add to state - ALL required fields for chart rendering
            state['price_history'] = price_history_enhanced
            state['projections'] = projections
            state['initial_investment'] = 1000.0

            logger.info(f"✅ Added {len(price_history_enhanced)} price_history points and {len(projections)} projections to report_json")

        except Exception as e:
            logger.warning(f"Failed to calculate projections for precompute: {e}")

        return state

    def _extract_stance_from_state(self, state: Dict[str, Any]) -> str:
        """Extract overall stance from agent state.

        Uses technical indicators to determine bullish/bearish/neutral stance.
        Logic mirrors transformer.py _extract_stance() method.

        Args:
            state: AgentState dict from workflow

        Returns:
            'bullish' | 'bearish' | 'neutral'
        """
        try:
            indicators = state.get('indicators', {})

            # Extract key indicators
            rsi = indicators.get('rsi')
            sma_20 = indicators.get('sma_20')
            current_price = indicators.get('current_price')

            # Determine stance based on technical signals
            if rsi and sma_20 and current_price:
                # Bullish: RSI > 70 AND price > SMA20
                if rsi > 70 and current_price > sma_20:
                    return 'bullish'
                # Bearish: RSI < 30 AND price < SMA20
                elif rsi < 30 and current_price < sma_20:
                    return 'bearish'

            # Default to neutral
            return 'neutral'

        except Exception as e:
            logger.debug(f"Could not extract stance: {e}")
            return 'neutral'

    def _ensure_user_facing_scores(self, result: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Ensure user_facing_scores are present in result dict.

        Extracts user_facing_scores from indicators/ticker_data/percentiles if missing.
        Critical for UI ScoreTable display.

        DEFENSIVE PROGRAMMING:
        - Validates required data exists AND is non-empty before attempting extraction
        - Logs explicit warnings/errors when data is missing (fail fast with visibility)
        - Verifies operation succeeded (explicit failure detection)
        - Never silently fails

        Args:
            result: Report result dict from workflow
            symbol: Ticker symbol (for logging)

        Returns:
            Updated result dict with user_facing_scores added if possible
        """
        # FAIL FAST: Check if already present
        if 'user_facing_scores' in result:
            logger.debug(f"✅ user_facing_scores already present for {symbol}")
            return result

        # EXPLICIT VALIDATION: Check required data exists
        required_fields = ['indicators', 'ticker_data', 'percentiles']
        missing_fields = [f for f in required_fields if not result.get(f)]

        if missing_fields:
            # FAIL FAST WITH VISIBILITY - WARNING level (not DEBUG)
            logger.warning(
                f"⚠️  Cannot extract user_facing_scores for {symbol}: "
                f"Missing required data: {missing_fields}. "
                f"Available fields: {list(result.keys())}"
            )
            return result

        # Validate data is not empty (existence check is not enough)
        if not result['indicators'] or not result['ticker_data'] or not result['percentiles']:
            # FAIL FAST WITH VISIBILITY
            logger.warning(
                f"⚠️  Cannot extract user_facing_scores for {symbol}: "
                f"Required fields are EMPTY. "
                f"indicators={bool(result['indicators'])}, "
                f"ticker_data={bool(result['ticker_data'])}, "
                f"percentiles={bool(result['percentiles'])}"
            )
            return result

        try:
            from src.scoring.user_facing_scorer import UserFacingScorer

            logger.info(f"🔄 Extracting user_facing_scores for {symbol}...")

            scorer = UserFacingScorer()
            scores = scorer.calculate_all_scores(
                ticker_data=result.get('ticker_data', {}),
                indicators=result.get('indicators', {}),
                percentiles=result.get('percentiles', {})
            )

            # EXPLICIT FAILURE DETECTION - Check operation outcome
            if not scores:
                logger.error(
                    f"❌ UserFacingScorer returned EMPTY scores for {symbol}! "
                    f"This should not happen with valid data."
                )
                return result

            if not isinstance(scores, dict):
                logger.error(
                    f"❌ UserFacingScorer returned INVALID type for {symbol}: {type(scores)}. "
                    f"Expected dict."
                )
                return result

            # Add to result
            result['user_facing_scores'] = scores

            # VERIFY ADDITION SUCCEEDED - Explicit failure detection
            if 'user_facing_scores' not in result:
                logger.error(
                    f"❌ CRITICAL: Failed to add user_facing_scores to result dict for {symbol}! "
                    f"Dict assignment failed."
                )
                return result

            logger.info(
                f"✅ Successfully extracted user_facing_scores for {symbol}: "
                f"{len(scores)} categories"
            )

        except Exception as e:
            # NEVER SILENT FAILURE - ERROR level with stack trace
            logger.error(
                f"❌ Exception while extracting user_facing_scores for {symbol}: {e}",
                exc_info=True  # Include stack trace
            )

        return result

    def compute_and_store_report(
        self,
        symbol: str,
        data_date: Optional[date] = None,
        strategy: str = 'multi-stage',
        generate_pdf: bool = True
    ) -> Dict[str, Any]:
        """Generate and store a full report for a ticker.

        Args:
            symbol: Ticker symbol
            data_date: Date of the underlying ticker data (defaults to today)
            strategy: 'single-stage' or 'multi-stage'
            generate_pdf: Whether to generate PDF and store S3 key

        Returns:
            Dict with report metadata
        """
        data_date = data_date or date.today()

        ticker_info = self.repo.get_ticker_info(symbol)
        if not ticker_info:
            return {'status': 'error', 'error': f'Ticker not found: {symbol}'}

        ticker_id = ticker_info['id']

        # Mark as pending
        self._update_report_status(ticker_id, symbol, data_date, 'pending')

        try:
            start_time = time.time()

            # Resolve symbol to DR format (agent expects DR symbol like NVDA19)
            from src.data.aurora.ticker_resolver import get_ticker_resolver

            resolver = get_ticker_resolver()
            ticker_info_resolved = resolver.resolve(symbol)

            # Use DR symbol for agent (e.g., NVDA19) or fallback to original
            agent_symbol = ticker_info_resolved.dr_symbol if ticker_info_resolved else symbol
            logger.info(f"Generating report: yahoo={symbol} -> dr={agent_symbol}")

            # Generate report using the agent
            from src.agent import TickerAnalysisAgent

            agent = TickerAnalysisAgent()
            result = agent.analyze_ticker(agent_symbol, strategy=strategy)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Extract report data
            report_text = result.get('report', '') if isinstance(result, dict) else str(result)
            mini_reports = result.get('mini_reports', {}) if isinstance(result, dict) else {}
            chart_base64 = result.get('chart_base64', '') if isinstance(result, dict) else ''

            # Calculate and add projections + price history to report_json
            if isinstance(result, dict):
                result = self._enhance_report_json_with_portfolio_data(result)

                # Add user_facing_scores if present (critical for UI ScoreTable)
                result = self._ensure_user_facing_scores(result, symbol)

                # Add stance if not present (critical for UI chart colors)
                if 'stance' not in result:
                    result['stance'] = self._extract_stance_from_state(result)
                    logger.debug(f"Added stance={result['stance']} for {symbol}")

            # Generate PDF if requested
            pdf_s3_key = None
            pdf_generated_at = None
            if generate_pdf and report_text:
                try:
                    pdf_s3_key = self._generate_and_upload_pdf(symbol, data_date, report_text, chart_base64)
                    pdf_generated_at = datetime.now()
                    logger.info(f"✅ Generated PDF: {pdf_s3_key}")
                except Exception as pdf_error:
                    logger.warning(f"⚠️ PDF generation failed for {symbol}: {pdf_error}")
                    # Continue without PDF - report is still valid

            # Store the report
            self._store_completed_report(
                ticker_id=ticker_id,
                symbol=symbol,
                data_date=data_date,
                report_text=report_text,
                report_json=result if isinstance(result, dict) else {},
                strategy=strategy,
                generation_time_ms=generation_time_ms,
                mini_reports=mini_reports,
                chart_base64=chart_base64,
                pdf_s3_key=pdf_s3_key,
                pdf_generated_at=pdf_generated_at,
            )

            return {
                'status': 'completed',
                'symbol': symbol,
                'generation_time_ms': generation_time_ms,
                'report_length': len(report_text),
                'pdf_s3_key': pdf_s3_key,
            }

        except Exception as e:
            logger.error(f"Failed to generate report for {symbol}: {e}")
            self._update_report_status(
                ticker_id, symbol, data_date, 'failed', error_message=str(e)
            )
            return {'status': 'failed', 'error': str(e)}

    def _update_report_status(
        self,
        ticker_id: int,
        symbol: str,
        data_date: date,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update report status in database.

        Uses the new schema with 'date' (data date) and 'report_generated_at'.
        Also supports legacy 'report_date' column during migration period.
        """
        # Use new schema columns (date, report_generated_at)
        # Also set report_date for backwards compatibility during migration
        query = """
            INSERT INTO precomputed_reports (ticker_id, symbol, date, report_date, status, error_message, report_generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                error_message = VALUES(error_message),
                report_generated_at = NOW()
        """
        self.client.execute(query, (ticker_id, symbol, data_date, data_date, status, error_message), commit=True)

    def _store_completed_report(
        self,
        ticker_id: int,
        symbol: str,
        data_date: date,
        report_text: str,
        report_json: Dict[str, Any],
        strategy: str,
        generation_time_ms: int,
        mini_reports: Dict[str, Any],
        chart_base64: str,
        pdf_s3_key: Optional[str] = None,
        pdf_generated_at: Optional[datetime] = None,
    ) -> int:
        """Store a completed report to Aurora cache.

        Returns:
            Number of rows affected (0 = failure, typically FK constraint)

        Schema columns (as of 2025-12-02):
            id, ticker_id, ticker_master_id, symbol, report_date,
            report_text, report_json, strategy, model_used,
            generation_time_ms, token_count, cost_usd, mini_reports,
            faithfulness_score, completeness_score, reasoning_score,
            chart_base64, status, error_message, computed_at, expires_at
        """
        # Match actual schema - only use columns that exist
        query = """
            INSERT INTO precomputed_reports (
                ticker_id, symbol, report_date,
                report_text, report_json, strategy,
                generation_time_ms, mini_reports, chart_base64,
                status, expires_at, computed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed',
                DATE_ADD(NOW(), INTERVAL 1 DAY), NOW()
            )
            ON DUPLICATE KEY UPDATE
                report_text = VALUES(report_text),
                report_json = VALUES(report_json),
                strategy = VALUES(strategy),
                generation_time_ms = VALUES(generation_time_ms),
                mini_reports = VALUES(mini_reports),
                chart_base64 = VALUES(chart_base64),
                status = 'completed',
                expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY),
                error_message = NULL,
                computed_at = NOW()
        """

        params = (
            ticker_id,
            symbol,
            data_date,
            report_text,
            json.dumps(report_json, default=str),
            strategy,
            generation_time_ms,
            json.dumps(mini_reports, default=str) if mini_reports else None,
            chart_base64,
        )

        return self.client.execute(query, params, commit=True)

    def store_report_from_api(
        self,
        symbol: str,
        report_text: str,
        report_json: Dict[str, Any],
        strategy: str = 'multi-stage',  # Must match MySQL ENUM('single-stage', 'multi-stage')
        chart_base64: str = '',
        generation_time_ms: int = 0,
    ) -> bool:
        """Store a report generated by the API worker to Aurora cache.

        This method enables cache write-through from the async report worker,
        allowing subsequent requests for the same ticker to hit the cache
        instead of regenerating the report.

        Args:
            symbol: Ticker symbol (e.g., 'DBS19')
            report_text: Full narrative report text
            report_json: Complete API response dict
            strategy: Generation strategy used (default: 'multi_stage_analysis')
            chart_base64: Optional base64-encoded chart image
            generation_time_ms: Time taken to generate (for metrics)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Use TickerResolver to get canonical ticker info
            # This correctly uses ticker_master + ticker_aliases tables
            logger.info(f"store_report_from_api: Resolving symbol {symbol}")
            from src.data.aurora.ticker_resolver import get_ticker_resolver
            resolver = get_ticker_resolver()
            ticker_info = resolver.resolve(symbol)

            if not ticker_info:
                logger.warning(f"Cannot cache report for unknown ticker: {symbol}")
                return False

            ticker_id = ticker_info.ticker_id
            yahoo_symbol = ticker_info.yahoo_symbol or symbol
            logger.info(f"store_report_from_api: Resolved {symbol} -> ticker_id={ticker_id}, yahoo={yahoo_symbol}")

            data_date = date.today()

            # Store using the internal method with Yahoo symbol
            logger.info(f"store_report_from_api: Calling _store_completed_report for {yahoo_symbol}")
            rowcount = self._store_completed_report(
                ticker_id=ticker_id,
                symbol=yahoo_symbol,  # Use Yahoo symbol for Aurora storage
                data_date=data_date,
                report_text=report_text,
                report_json=report_json,
                strategy=strategy,
                generation_time_ms=generation_time_ms,
                mini_reports={},  # Not available from API worker
                chart_base64=chart_base64,
                pdf_s3_key=None,
                pdf_generated_at=None,
            )

            # Check rowcount - 0 means INSERT failed (e.g., FK constraint violation)
            if rowcount == 0:
                logger.warning(f"⚠️ INSERT affected 0 rows for {symbol} - possible FK constraint failure")
                return False

            logger.info(f"✅ Cached API-generated report for {symbol} (yahoo={yahoo_symbol})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to cache report for {symbol}: {e}")
            return False

    # =========================================================================
    # High-Level Methods
    # =========================================================================

    def compute_for_ticker(
        self,
        symbol: str,
        include_report: bool = True
    ) -> Dict[str, Any]:
        """Compute all precomputed data for a single ticker.

        Args:
            symbol: Ticker symbol
            include_report: Whether to generate full LLM report

        Returns:
            Dict with computation results
        """
        results = {
            'symbol': symbol,
            'indicators': False,
            'percentiles': False,
            'comparative': False,
            'report': False,
        }

        try:
            # Get historical data from Aurora
            hist_df = self.repo.get_prices_as_dataframe(symbol, limit=400)

            if hist_df.empty:
                logger.warning(f"No price data for {symbol}")
                return results

            today = date.today()

            # Compute and store indicators
            indicators = self.compute_daily_indicators(symbol, hist_df, today)
            if indicators:
                self.store_daily_indicators(symbol, indicators)
                results['indicators'] = True
                logger.info(f"✅ Stored indicators for {symbol}")

            # Compute and store percentiles
            percentiles = self.compute_percentiles(symbol, hist_df, today)
            if percentiles:
                self.store_percentiles(symbol, percentiles)
                results['percentiles'] = True
                logger.info(f"✅ Stored percentiles for {symbol}")

            # Compute and store comparative features
            features = self.compute_comparative_features(symbol, hist_df, today)
            if features:
                self.store_comparative_features(symbol, features)
                results['comparative'] = True
                logger.info(f"✅ Stored comparative features for {symbol}")

            # Generate and store report
            if include_report:
                report_result = self.compute_and_store_report(symbol, today)
                results['report'] = report_result.get('status') == 'completed'
                logger.info(f"✅ Generated report for {symbol} ({report_result.get('generation_time_ms')}ms)")

        except Exception as e:
            logger.error(f"Failed to compute for {symbol}: {e}")
            results['error'] = str(e)

        return results

    def compute_all(self, include_report: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """Compute precomputed data for all active tickers.

        Args:
            include_report: Whether to generate full LLM reports
            limit: Max number of tickers to process

        Returns:
            Dict with summary of computations
        """
        tickers = self.repo.get_all_tickers()
        if limit:
            tickers = tickers[:limit]

        logger.info(f"Computing precomputed data for {len(tickers)} tickers...")

        results = {
            'total': len(tickers),
            'success': 0,
            'failed': 0,
            'details': [],
        }

        for ticker_info in tickers:
            symbol = ticker_info['symbol']
            result = self.compute_for_ticker(symbol, include_report=include_report)

            if result.get('error'):
                results['failed'] += 1
            else:
                results['success'] += 1

            results['details'].append(result)

        logger.info(
            f"Completed: {results['success']} success, {results['failed']} failed"
        )

        return results

    # =========================================================================
    # Retrieval Methods
    # =========================================================================

    def get_latest_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest precomputed indicators for a ticker.

        Uses ticker_master_id for robust lookup regardless of symbol format.

        Args:
            symbol: Ticker symbol (any format - DR or Yahoo)

        Returns:
            Dict with indicator values or None
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        resolver = get_ticker_resolver()
        master_id = resolver.get_master_id(symbol)

        if master_id is None:
            logger.warning(f"Symbol '{symbol}' not found in ticker_master")
            return None

        query = """
            SELECT * FROM daily_indicators
            WHERE ticker_master_id = %s
            ORDER BY indicator_date DESC
            LIMIT 1
        """
        return self.client.fetch_one(query, (master_id,))

    def get_latest_percentiles(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest precomputed percentiles for a ticker.

        Uses ticker_master_id for robust lookup regardless of symbol format.

        Args:
            symbol: Ticker symbol (any format - DR or Yahoo)

        Returns:
            Dict with percentile values or None
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        resolver = get_ticker_resolver()
        master_id = resolver.get_master_id(symbol)

        if master_id is None:
            logger.warning(f"Symbol '{symbol}' not found in ticker_master")
            return None

        query = """
            SELECT * FROM indicator_percentiles
            WHERE ticker_master_id = %s
            ORDER BY percentile_date DESC
            LIMIT 1
        """
        return self.client.fetch_one(query, (master_id,))

    def get_cached_report(
        self,
        symbol: str,
        data_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached report for a ticker using symbol matching.

        This method looks up reports by symbol, supporting multiple formats
        (DR like 'NVDA19', Yahoo like 'NVDA'). It uses the ticker_resolver
        to find all possible symbol aliases for robust cache lookup.

        Args:
            symbol: Ticker symbol (any format - DR like 'NVDA19' or Yahoo like 'NVDA')
            data_date: Date of the underlying data (defaults to today)

        Returns:
            Dict with report data including PDF tracking columns or None
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        data_date = data_date or date.today()

        # Get ticker info to resolve symbol to all possible formats
        resolver = get_ticker_resolver()
        ticker_info = resolver.resolve(symbol)  # Returns TickerInfo or None
        master_id = ticker_info.ticker_id if ticker_info else None

        # Build list of possible symbols to search for
        symbols_to_check = [symbol]
        if ticker_info:
            if ticker_info.yahoo_symbol and ticker_info.yahoo_symbol not in symbols_to_check:
                symbols_to_check.append(ticker_info.yahoo_symbol)
            if ticker_info.dr_symbol and ticker_info.dr_symbol not in symbols_to_check:
                symbols_to_check.append(ticker_info.dr_symbol)

        # Query using symbol (direct match) with fallback to ticker_id
        # This ensures we can find reports stored with the resolved ticker_id
        placeholders = ', '.join(['%s'] * len(symbols_to_check))
        query = f"""
            SELECT * FROM precomputed_reports
            WHERE (symbol IN ({placeholders}) OR (ticker_id IS NOT NULL AND ticker_id = %s))
            AND report_date = %s
            AND status = 'completed'
            ORDER BY id DESC
            LIMIT 1
        """

        params = list(symbols_to_check) + [master_id, data_date]
        logger.info(f"Cache lookup for {symbol}: symbols={symbols_to_check}, master_id={master_id}, date={data_date}")
        result = self.client.fetch_one(query, tuple(params))
        if result:
            logger.info(f"Cache HIT for {symbol}")
        else:
            logger.info(f"Cache MISS for {symbol}")
        return result

    # =========================================================================
    # PDF Generation
    # =========================================================================

    def _generate_and_upload_pdf(
        self,
        symbol: str,
        data_date: date,
        report_text: str,
        chart_base64: str
    ) -> Optional[str]:
        """Generate PDF from report and upload to S3.

        Args:
            symbol: Ticker symbol
            data_date: Date of the underlying data
            report_text: Report text content
            chart_base64: Chart image as base64 string

        Returns:
            S3 key for the uploaded PDF or None if failed
        """
        try:
            from src.formatters.pdf_generator import generate_pdf
            from src.data.s3_cache import upload_pdf_to_s3

            # Generate PDF
            pdf_bytes = generate_pdf(
                report_text=report_text,
                ticker=symbol,
                chart_base64=chart_base64
            )

            if not pdf_bytes:
                return None

            # Upload to S3 with the standard key format
            pdf_s3_key = f"reports/{symbol}/{data_date.strftime('%Y-%m-%d')}.pdf"
            upload_pdf_to_s3(pdf_bytes, pdf_s3_key)

            return pdf_s3_key

        except ImportError as e:
            logger.warning(f"PDF generation module not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate/upload PDF: {e}")
            return None

    def update_pdf_presigned_url(
        self,
        symbol: str,
        data_date: date,
        presigned_url: str,
        expires_at: datetime
    ) -> int:
        """Update the cached presigned URL for a report's PDF.

        Args:
            symbol: Ticker symbol
            data_date: Date of the underlying data
            presigned_url: New presigned URL
            expires_at: When the URL expires

        Returns:
            Number of affected rows
        """
        # Use new 'date' column with fallback to report_date
        query = """
            UPDATE precomputed_reports
            SET pdf_presigned_url = %s, pdf_url_expires_at = %s
            WHERE symbol = %s AND (date = %s OR report_date = %s)
        """
        return self.client.execute(
            query,
            (presigned_url, expires_at, symbol, data_date, data_date),
            commit=True
        )

    # =========================================================================
    # Ticker Data Cache (replaces S3 cache/ticker_data/)
    # =========================================================================

    def store_ticker_data_cache(
        self,
        symbol: str,
        data_date: date,
        price_history: List[Dict[str, Any]],
        company_info: Optional[Dict[str, Any]] = None,
        financials: Optional[Dict[str, Any]] = None
    ) -> int:
        """Store full ticker data in Aurora cache.

        Replaces S3 cache/ticker_data/ with Aurora storage for faster access.

        Args:
            symbol: Ticker symbol
            data_date: Date of the cached data
            price_history: List of OHLCV dicts (1-year history, ~365 rows)
            company_info: Company metadata dict
            financials: Financial statements dict

        Returns:
            Number of affected rows
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        resolver = get_ticker_resolver()
        master_id = resolver.get_master_id(symbol)

        if master_id is None:
            logger.warning(f"Symbol '{symbol}' not found in ticker_master")
            return 0

        # Extract history dates for metadata
        history_start_date = None
        history_end_date = None
        row_count = len(price_history) if price_history else 0

        if price_history and len(price_history) > 0:
            history_start_date = price_history[0].get('date')
            history_end_date = price_history[-1].get('date')

        # Calculate expires_at (next trading day 8 AM Bangkok = UTC+7)
        # For simplicity, set to tomorrow 8 AM
        expires_at = datetime.combine(data_date + timedelta(days=1), datetime.min.time())
        expires_at = expires_at.replace(hour=1)  # 8 AM Bangkok = 1 AM UTC

        query = """
            INSERT INTO ticker_data_cache (
                ticker_master_id, symbol, date, fetched_at,
                price_history, company_info, financials_json,
                history_start_date, history_end_date, row_count,
                expires_at
            ) VALUES (
                %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                price_history = VALUES(price_history),
                company_info = VALUES(company_info),
                financials_json = VALUES(financials_json),
                history_start_date = VALUES(history_start_date),
                history_end_date = VALUES(history_end_date),
                row_count = VALUES(row_count),
                expires_at = VALUES(expires_at),
                fetched_at = NOW()
        """

        params = (
            master_id,
            symbol,
            data_date,
            json.dumps(price_history, default=str) if price_history else None,
            json.dumps(company_info, default=str) if company_info else None,
            json.dumps(financials, default=str) if financials else None,
            history_start_date,
            history_end_date,
            row_count,
            expires_at,
        )

        return self.client.execute(query, params, commit=True)

    def get_ticker_data_cache(
        self,
        symbol: str,
        data_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached ticker data from Aurora.

        Args:
            symbol: Ticker symbol
            data_date: Date of the cached data (defaults to today)

        Returns:
            Dict with price_history, company_info, financials or None
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        data_date = data_date or date.today()

        resolver = get_ticker_resolver()
        master_id = resolver.get_master_id(symbol)

        if master_id is None:
            return None

        query = """
            SELECT * FROM ticker_data_cache
            WHERE ticker_master_id = %s AND date = %s
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        result = self.client.fetch_one(query, (master_id, data_date))

        if result:
            # Parse JSON fields
            if result.get('price_history'):
                result['price_history'] = json.loads(result['price_history'])
            if result.get('company_info'):
                result['company_info'] = json.loads(result['company_info'])
            if result.get('financials_json'):
                result['financials_json'] = json.loads(result['financials_json'])

        return result

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Convert value to float, handling NaN and None."""
        if value is None:
            return None
        try:
            f = float(value)
            if np.isnan(f) or np.isinf(f):
                return None
            return f
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Convert value to int, handling NaN and None."""
        if value is None:
            return None
        try:
            f = float(value)
            if np.isnan(f) or np.isinf(f):
                return None
            return int(f)
        except (TypeError, ValueError):
            return None

    def _calculate_price_percentile(self, hist_df: pd.DataFrame) -> Optional[float]:
        """Calculate current price percentile vs historical range."""
        if hist_df.empty:
            return None

        prices = hist_df['Close']
        current = prices.iloc[-1]
        min_price = prices.min()
        max_price = prices.max()

        if max_price == min_price:
            return 50.0

        return ((current - min_price) / (max_price - min_price)) * 100

    def _calculate_max_drawdown(self, prices: pd.Series) -> Optional[float]:
        """Calculate maximum drawdown."""
        if len(prices) < 2:
            return None

        cummax = prices.expanding().max()
        drawdown = (prices - cummax) / cummax
        return abs(drawdown.min()) * 100
