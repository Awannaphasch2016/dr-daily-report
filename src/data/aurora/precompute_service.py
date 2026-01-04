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
from botocore.exceptions import ClientError

from src.types import extract_raw_data_for_storage
from src.data.aurora.table_names import (
    TICKER_DATA,
    DAILY_INDICATORS,
    INDICATOR_PERCENTILES,
    COMPARATIVE_FEATURES,
    PRECOMPUTED_REPORTS,
)

logger = logging.getLogger(__name__)


def _convert_numpy_to_primitives(obj: Any) -> Any:
    """Recursively convert NumPy/Pandas types to JSON-serializable Python primitives.

    This is a defensive function applied at the system boundary (Aurora JSON storage)
    to catch ANY NumPy/Pandas types regardless of source. Prevents MySQL Error 3140.

    Args:
        obj: Object potentially containing NumPy/Pandas types

    Returns:
        Same structure with all types converted to JSON-safe primitives

    Examples:
        >>> _convert_numpy_to_primitives(np.int64(42))
        42
        >>> _convert_numpy_to_primitives({'score': np.float64(7.5)})
        {'score': 7.5}
    """
    # NumPy scalar types
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        # Handle NaN/Inf
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)

    # Pandas types
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')

    # Python datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Recursive cases
    if isinstance(obj, dict):
        return {key: _convert_numpy_to_primitives(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy_to_primitives(item) for item in obj]

    # Python float NaN/Inf check (must come before returning obj)
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # Already JSON-safe (str, int, bool, None)
    return obj



class PrecomputeService:
    """Service for precomputing and storing ticker analysis data."""

    def __init__(self):
        """Initialize the precompute service."""
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.repository import TickerRepository
        from src.analysis.technical_analysis import TechnicalAnalyzer
        from src.data.data_lake import DataLakeStorage

        self.client = get_aurora_client()
        self.repo = TickerRepository(client=self.client)
        self.analyzer = TechnicalAnalyzer()
        self.data_lake = DataLakeStorage()  # Phase 2: Processed data storage

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

        query = f"""
            INSERT INTO {DAILY_INDICATORS} (
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

        query = f"""
            INSERT INTO {INDICATOR_PERCENTILES} (
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

        query = f"""
            INSERT INTO {COMPARATIVE_FEATURES} (
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
        # FIX: Explicitly check for EMPTY dicts, not just falsy values
        # Python truthiness bug: not {} evaluates to True (empty dict is falsy)
        # This caused silent early returns when workflow initialized fields to {}
        has_indicators = result.get('indicators') and len(result['indicators']) > 0
        has_ticker_data = result.get('ticker_data') and len(result['ticker_data']) > 0
        has_percentiles = result.get('percentiles') and len(result['percentiles']) > 0

        if not has_indicators or not has_ticker_data or not has_percentiles:
            # FAIL FAST WITH EXPLICIT ERROR (not buried WARNING)
            # Defensive programming: explicit failure detection
            logger.error(
                f"❌ Cannot extract user_facing_scores for {symbol}: "
                f"Required fields are empty or missing. "
                f"indicators={bool(has_indicators)} (len={len(result.get('indicators', {}))}), "
                f"ticker_data={bool(has_ticker_data)} (len={len(result.get('ticker_data', {}))}), "
                f"percentiles={bool(has_percentiles)} (len={len(result.get('percentiles', {}))})"
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
        generate_pdf: bool = True
    ) -> Dict[str, Any]:
        """Generate and store a full report for a ticker.

        Args:
            symbol: Ticker symbol
            data_date: Date of the underlying ticker data (defaults to today)
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
            result = agent.analyze_ticker(agent_symbol)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Extract report data
            report_text = result.get('report', '') if isinstance(result, dict) else str(result)
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
                generation_time_ms=generation_time_ms,
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

        Uses actual Aurora schema: report_date (date) and computed_at (timestamp).
        Schema confirmed via Lambda describe_table: 21 columns including report_date, computed_at.
        """
        # Use actual schema columns (report_date, computed_at)
        query = f"""
            INSERT INTO {PRECOMPUTED_REPORTS} (ticker_id, symbol, report_date, status, error_message, computed_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                error_message = VALUES(error_message),
                computed_at = NOW()
        """
        self.client.execute(query, (ticker_id, symbol, data_date, status, error_message), commit=True)

    def _store_completed_report(
        self,
        ticker_id: int,
        symbol: str,
        data_date: date,
        report_text: str,
        report_json: Dict[str, Any],
        generation_time_ms: int,
        chart_base64: str,
        pdf_s3_key: Optional[str] = None,
        pdf_generated_at: Optional[datetime] = None,
    ) -> int:
        """Store a completed report to Aurora cache.

        Returns:
            Number of rows affected (0 = failure, typically FK constraint)

        Schema columns (after migration 011):
            id, ticker_id, ticker_master_id, symbol, report_date,
            report_text, report_json, model_used,
            generation_time_ms, token_count, cost_usd,
            faithfulness_score, completeness_score, reasoning_score,
            chart_base64, status, error_message, computed_at, expires_at

        Note: strategy, mini_reports, and raw_data_json columns removed in migration 011.
        """
        query = f"""
            INSERT INTO {PRECOMPUTED_REPORTS} (
                ticker_id, symbol, report_date,
                report_text, report_json,
                generation_time_ms,
                chart_base64, status, expires_at, computed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, 'completed',
                DATE_ADD(NOW(), INTERVAL 1 DAY), NOW()
            )
            ON DUPLICATE KEY UPDATE
                report_text = VALUES(report_text),
                report_json = VALUES(report_json),
                generation_time_ms = VALUES(generation_time_ms),
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
            json.dumps(_convert_numpy_to_primitives(report_json), allow_nan=False),
            generation_time_ms,
            chart_base64,
        )

        return self.client.execute(query, params, commit=True)

    def store_report_from_api(
        self,
        symbol: str,
        report_text: str,
        report_json: Dict[str, Any],
        chart_base64: str = '',
        generation_time_ms: int = 0,
        pdf_s3_key: Optional[str] = None,
        pdf_generated_at: Optional[datetime] = None,
    ) -> bool:
        """Store a report generated by the API worker to Aurora cache.

        This method enables cache write-through from the async report worker,
        allowing subsequent requests for the same ticker to hit the cache
        instead of regenerating the report.

        PDF support: If pdf_s3_key provided, report will include PDF reference
        (used by scheduled workflows that generate PDFs).

        Args:
            symbol: Ticker symbol (e.g., 'DBS19')
            report_text: Full narrative report text
            report_json: Complete API response dict
            chart_base64: Optional base64-encoded chart image
            generation_time_ms: Time taken to generate (for metrics)
            pdf_s3_key: S3 key for generated PDF (optional, for scheduled workflows)
            pdf_generated_at: Timestamp when PDF generated (optional)

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
                generation_time_ms=generation_time_ms,
                chart_base64=chart_base64,
                pdf_s3_key=pdf_s3_key,
                pdf_generated_at=pdf_generated_at,
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

        Symbol-type invariant: Accepts any symbol format (DR, Yahoo, etc.)
        and automatically resolves to Yahoo Finance format for Aurora queries.
        Storage methods use the original symbol (they handle resolution internally).

        Args:
            symbol: Ticker symbol in any format (e.g., 'DBS19' or 'D05.SI')
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
            # Resolve symbol to Yahoo Finance format for Aurora queries
            # Aurora stores prices with Yahoo Finance symbols (e.g., 'D05.SI')
            from src.data.aurora.ticker_resolver import get_ticker_resolver
            resolver = get_ticker_resolver()
            ticker_info = resolver.resolve(symbol)
            yahoo_symbol = ticker_info.yahoo_symbol if ticker_info else symbol
            
            logger.debug(f"Resolved {symbol} -> {yahoo_symbol} for Aurora query")

            # Get historical data from Aurora using Yahoo Finance symbol
            # VALIDATION GATE: Verify we have price data before proceeding
            hist_df = self.repo.get_prices_as_dataframe(yahoo_symbol, limit=400)

            if hist_df.empty:
                error_msg = f"No price data for {symbol} (resolved to {yahoo_symbol})"
                logger.warning(error_msg)
                # Don't return early - set error in results for visibility
                results['error'] = error_msg
                return results

            today = date.today()

            # Compute and store indicators
            indicators = self.compute_daily_indicators(symbol, hist_df, today)
            if indicators:
                # Store to Aurora (existing)
                self.store_daily_indicators(symbol, indicators)
                
                # Store to Data Lake Phase 2 (non-blocking for S3 errors, but fail-fast for type errors)
                if self.data_lake.is_enabled():
                    try:
                        # Construct potential source raw data key (if available from today's fetch)
                        # Format: raw/yfinance/{ticker}/{date}/{timestamp}.json
                        # Note: We don't have exact timestamp, so we'll store without source link for now
                        # Future enhancement: Track source key from scheduler fetch
                        source_raw_key = None  # Optional - can be enhanced later
                        
                        # Use Yahoo symbol for data lake storage (consistent with raw data storage)
                        data_lake_success = self.data_lake.store_indicators(
                            ticker=yahoo_symbol,
                            indicators=indicators,
                            source_raw_data_key=source_raw_key,
                            computed_at=datetime.combine(today, datetime.min.time())
                        )
                        if data_lake_success:
                            logger.info(f"✅ Data lake stored indicators for {yahoo_symbol}")
                        else:
                            # Should not happen - store_indicators() raises on error now
                            logger.warning(f"⚠️ Data lake storage returned False (unexpected)")
                            
                    except TypeError as e:
                        # Type errors are CODE BUGS - fail fast, don't hide
                        # Error Handling Duality: Utility functions raise, we should propagate
                        logger.error(f"❌ Type error storing indicators to data lake: {e}")
                        raise  # Don't hide code bugs - fail fast
                        
                    except ClientError as e:
                        # S3 infrastructure errors - can be non-blocking
                        # But still log as ERROR (not WARNING) for visibility
                        logger.error(f"⚠️ S3 storage failed (non-blocking): {e}")
                        # Continue - Aurora storage succeeded
                        
                    except Exception as e:
                        # Unexpected errors - log as ERROR, consider raising
                        logger.error(f"❌ Unexpected error storing to data lake: {e}")
                        raise  # Fail fast for unexpected errors
                
                results['indicators'] = True
                logger.info(f"✅ Stored indicators for {symbol} (Yahoo: {yahoo_symbol})")

            # Compute and store percentiles
            percentiles = self.compute_percentiles(symbol, hist_df, today)
            if percentiles:
                # Store to Aurora (existing)
                self.store_percentiles(symbol, percentiles)
                
                # Store to Data Lake Phase 2 (non-blocking for S3 errors, but fail-fast for type errors)
                if self.data_lake.is_enabled():
                    try:
                        # Construct potential source raw data key (optional)
                        source_raw_key = None  # Optional - can be enhanced later
                        
                        # Use Yahoo symbol for data lake storage (consistent with raw data storage)
                        data_lake_success = self.data_lake.store_percentiles(
                            ticker=yahoo_symbol,
                            percentiles=percentiles,
                            source_raw_data_key=source_raw_key,
                            computed_at=datetime.combine(today, datetime.min.time())
                        )
                        if data_lake_success:
                            logger.info(f"✅ Data lake stored percentiles for {yahoo_symbol}")
                        else:
                            # Should not happen - store_percentiles() raises on error now
                            logger.warning(f"⚠️ Data lake storage returned False (unexpected)")
                            
                    except TypeError as e:
                        # Type errors are CODE BUGS - fail fast, don't hide
                        # Error Handling Duality: Utility functions raise, we should propagate
                        logger.error(f"❌ Type error storing percentiles to data lake: {e}")
                        raise  # Don't hide code bugs - fail fast
                        
                    except ClientError as e:
                        # S3 infrastructure errors - can be non-blocking
                        # But still log as ERROR (not WARNING) for visibility
                        logger.error(f"⚠️ S3 storage failed (non-blocking): {e}")
                        # Continue - Aurora storage succeeded
                        
                    except Exception as e:
                        # Unexpected errors - log as ERROR, consider raising
                        logger.error(f"❌ Unexpected error storing to data lake: {e}")
                        raise  # Fail fast for unexpected errors
                
                results['percentiles'] = True
                logger.info(f"✅ Stored percentiles for {symbol} (Yahoo: {yahoo_symbol})")

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

        query = f"""
            SELECT * FROM {DAILY_INDICATORS}
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

        query = f"""
            SELECT * FROM {INDICATOR_PERCENTILES}
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
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Use Bangkok timezone for business dates (CLAUDE.md Principle #14: Timezone Discipline)
        # Prevents date boundary bugs when UTC date differs from Bangkok date
        # Example: 21:00 UTC Dec 30 = 04:00 Bangkok Dec 31 (different dates!)
        bangkok_tz = ZoneInfo("Asia/Bangkok")
        data_date = data_date or datetime.now(bangkok_tz).date()

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
            SELECT * FROM {PRECOMPUTED_REPORTS}
            WHERE (symbol IN ({placeholders}) OR ticker_id = %s)
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
            from src.formatters.pdf_storage import PDFStorage

            # Generate PDF
            pdf_bytes = generate_pdf(
                report_text=report_text,
                ticker=symbol,
                chart_base64=chart_base64
            )

            if not pdf_bytes:
                logger.warning(f"PDF generation returned None for {symbol}")
                return None

            # Upload to S3 using PDFStorage
            pdf_storage = PDFStorage()
            if not pdf_storage.is_available():
                logger.warning("PDFStorage not available (S3 client not initialized)")
                return None

            # Upload PDF and get the S3 key
            # PDFStorage.upload_pdf() returns key like: reports/{ticker}/{date}/{ticker}_report_{date}_{timestamp}.pdf
            pdf_s3_key = pdf_storage.upload_pdf(
                pdf_bytes=pdf_bytes,
                ticker=symbol,
                date_str=data_date.strftime('%Y-%m-%d')
            )

            return pdf_s3_key

        except ImportError as e:
            logger.warning(f"PDF generation module not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate/upload PDF for {symbol}: {e}", exc_info=True)
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

    def update_pdf_metadata(
        self,
        report_id: int,
        pdf_s3_key: str,
        pdf_generated_at: datetime
    ) -> int:
        """Update PDF metadata for existing report (used by PDF worker).

        Args:
            report_id: Report ID to update
            pdf_s3_key: S3 key where PDF is stored
            pdf_generated_at: When PDF was generated

        Returns:
            Number of affected rows (should be 1)
        """
        query = f"""
            UPDATE {PRECOMPUTED_REPORTS}
            SET
                pdf_s3_key = %s,
                pdf_generated_at = %s
            WHERE id = %s
        """

        affected = self.client.execute(
            query,
            (pdf_s3_key, pdf_generated_at, report_id),
            commit=True
        )

        if affected == 0:
            logger.warning(f"⚠️ No report found with id={report_id}")
        else:
            logger.info(f"✅ Updated PDF metadata for report {report_id}")

        return affected

    def get_reports_needing_pdfs(
        self,
        report_date: date,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get reports that need PDF generation (called by get_report_list Lambda).

        Queries Aurora for reports where:
        - report_date matches
        - status = 'completed'
        - report_text IS NOT NULL
        - pdf_s3_key IS NULL (no PDF yet)

        Args:
            report_date: Business date to query (Bangkok timezone)
            limit: Maximum number of reports to return

        Returns:
            List of dicts with: id, symbol, report_date (minimal fields for Step Functions payload limit)
        """
        query = f"""
            SELECT
                id,
                symbol,
                report_date
            FROM {PRECOMPUTED_REPORTS}
            WHERE report_date = %s
              AND status = 'completed'
              AND report_text IS NOT NULL
              AND pdf_s3_key IS NULL
            ORDER BY computed_at ASC
            LIMIT %s
        """

        results = self.client.fetch_all(query, (report_date, limit))
        logger.info(f"Found {len(results)} reports needing PDFs for {report_date}")

        return results

    def get_report_by_id(self, report_id: int) -> dict | None:
        """Fetch full report data by ID for PDF generation.

        Args:
            report_id: Primary key of precomputed_reports table

        Returns:
            Dict with report data including report_text and chart_base64,
            or None if report not found
        """
        query = f"""
            SELECT
                id,
                symbol,
                report_date,
                report_text,
                chart_base64,
                report_json
            FROM {PRECOMPUTED_REPORTS}
            WHERE id = %s
        """

        result = self.client.fetch_one(query, (report_id,))
        if not result:
            logger.warning(f"Report not found: {report_id}")
            return None

        logger.info(f"Fetched report {report_id} for {result['symbol']}")
        return result

    # =========================================================================
    # Ticker Data Cache (replaces S3 cache/ticker_data/)
    # =========================================================================

    def store_ticker_data(
        self,
        symbol: str,
        data_date: date,
        price_history: List[Dict[str, Any]],
        company_info: Optional[Dict[str, Any]] = None,
        financials: Optional[Dict[str, Any]] = None
    ) -> int:
        """Store ticker data in Aurora (primary data store).

        Used by scheduler to populate Aurora with ticker data from external sources.

        Args:
            symbol: Ticker symbol
            data_date: Date of the data
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

        query = f"""
            INSERT INTO {TICKER_DATA} (
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

    def get_ticker_data(
        self,
        symbol: str,
        data_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Get ticker data from Aurora (ground truth).

        Args:
            symbol: Ticker symbol
            data_date: Date of the data (defaults to today)

        Returns:
            Dict with price_history, company_info, financials or None if not found
        """
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        data_date = data_date or date.today()

        resolver = get_ticker_resolver()
        master_id = resolver.get_master_id(symbol)

        if master_id is None:
            return None

        query = f"""
            SELECT * FROM {TICKER_DATA}
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

    def regenerate_report_from_cache(
        self,
        symbol: str,
        strategy: str = 'single-stage',
        data_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Regenerate report from cached raw data in Aurora (no API calls, no sink nodes).

        This enables fast iteration on report quality by reusing existing data.
        Useful for:
        - Testing new prompts without refetching data
        - Comparing single-stage vs multi-stage on same data
        - Cost-efficient development (no repeated API calls)

        Args:
            symbol: Ticker symbol (e.g., "DBS19")
            strategy: 'single-stage' or 'multi-stage'
            data_date: Report date (defaults to today)

        Returns:
            Dictionary with:
                - status: 'completed' or 'failed'
                - report_text: Generated report
                - generation_time_ms: Time taken
                - strategy: Strategy used

        Raises:
            ValueError: If no cached data exists for ticker/date
        """
        from src.report.report_generator_simple import SimpleReportGenerator

        data_date = data_date or date.today()
        logger.info(f"Regenerating {strategy} report for {symbol} from cached data (date={data_date})")

        # Read raw_data_json from Aurora (NOT report_json which is formatted)
        query = f"""
            SELECT raw_data_json
            FROM {PRECOMPUTED_REPORTS}
            WHERE symbol = %s AND report_date = %s
            ORDER BY computed_at DESC
            LIMIT 1
        """

        result = self.client.fetch_one(query, (symbol, data_date))

        if not result:
            error_msg = f"No cached data found for {symbol} on {data_date}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Extract raw data
        raw_data = result.get('raw_data_json')

        # Handle backward compatibility for old rows without raw_data_json
        if raw_data is None:
            logger.warning(
                f"⚠️  No raw_data_json for {symbol} on {data_date}. "
                f"This report was generated before raw data caching was implemented. "
                f"Please regenerate the report with fresh API calls to populate raw_data_json."
            )
            raise ValueError(
                f"No raw data available for {symbol} on {data_date}. "
                f"Run 'dr util report {symbol}' to regenerate with fresh data."
            )

        # Parse JSON if it's a string
        if isinstance(raw_data, str):
            import json
            raw_data = json.loads(raw_data)

        # Generate report using simple generator (no sink nodes)
        generator = SimpleReportGenerator()
        result = generator.generate_report(
            ticker=symbol,
            raw_data=raw_data,
            strategy=strategy
        )

        logger.info(f"✅ Regenerated report in {result['generation_time_ms']}ms using {strategy} strategy")

        return {
            'status': 'completed',
            'report_text': result['report'],
            'generation_time_ms': result['generation_time_ms'],
            'strategy': strategy,
            'mini_reports': result.get('mini_reports', {}),
            'api_costs': result.get('api_costs', {})
        }
