# -*- coding: utf-8 -*-
"""
Financial Markets MCP Server Lambda Handler

Implements Model Context Protocol (MCP) server for advanced technical analysis.
Exposes tools for chart pattern detection, candlestick patterns, support/resistance levels,
and advanced technical indicators (ADX, Stochastic, Williams %R, CCI, OBV, MFI).

MCP Protocol:
- Endpoint: /mcp
- Method: POST
- Content-Type: application/json
- Protocol: JSON-RPC 2.0
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FinancialMarketsAnalyzer:
    """Analyzer for chart patterns, candlestick patterns, and technical indicators."""
    
    def __init__(self):
        """Initialize Financial Markets Analyzer."""
        pass
    
    def fetch_price_data(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'NVDA')
            period: Time period ('1y', '6mo', '3mo', etc.)
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                logger.warning(f"No data returned for {ticker}")
                return None
            return hist
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None
    
    def detect_head_and_shoulders(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Head & Shoulders patterns.
        
        Pattern: Three peaks with middle peak (head) highest, two shoulders similar height.
        
        Args:
            data: DataFrame with High prices
            
        Returns:
            List of detected patterns with details
        """
        patterns = []
        if len(data) < 20:
            return patterns
        
        highs = data['High'].values
        window = 5
        
        for i in range(window, len(highs) - window * 2):
            # Find local peaks
            left_shoulder_idx = i
            head_idx = i + window
            right_shoulder_idx = i + window * 2
            
            if (head_idx >= len(highs) or right_shoulder_idx >= len(highs)):
                continue
            
            left_shoulder = highs[left_shoulder_idx]
            head = highs[head_idx]
            right_shoulder = highs[right_shoulder_idx]
            
            # Check if head is highest and shoulders are similar
            if (head > left_shoulder * 1.05 and head > right_shoulder * 1.05 and
                abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder) < 0.1):
                
                patterns.append({
                    'pattern': 'head_and_shoulders',
                    'type': 'bearish',
                    'left_shoulder_price': float(left_shoulder),
                    'head_price': float(head),
                    'right_shoulder_price': float(right_shoulder),
                    'neckline': float((left_shoulder + right_shoulder) / 2),
                    'date': data.index[right_shoulder_idx].strftime('%Y-%m-%d') if hasattr(data.index[right_shoulder_idx], 'strftime') else str(data.index[right_shoulder_idx]),
                    'confidence': 'medium'
                })
        
        return patterns[:5]  # Return top 5
    
    def detect_triangles(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect triangle patterns (ascending, descending, symmetrical).
        
        Args:
            data: DataFrame with High and Low prices
            
        Returns:
            List of detected triangle patterns
        """
        patterns = []
        if len(data) < 20:
            return patterns
        
        # Use rolling windows to detect converging trendlines
        window = 20
        for i in range(window, len(data)):
            segment = data.iloc[i-window:i]
            
            highs = segment['High'].values
            lows = segment['Low'].values
            
            # Calculate trendline slopes
            high_slope = np.polyfit(range(len(highs)), highs, 1)[0]
            low_slope = np.polyfit(range(len(lows)), lows, 1)[0]
            
            # Detect triangle type
            if abs(high_slope) < 0.01 and low_slope > 0.01:
                pattern_type = 'ascending_triangle'
            elif high_slope < -0.01 and abs(low_slope) < 0.01:
                pattern_type = 'descending_triangle'
            elif abs(high_slope) < 0.01 and abs(low_slope) < 0.01:
                pattern_type = 'symmetrical_triangle'
            else:
                continue
            
            # Check if lines are converging
            high_range = highs.max() - highs.min()
            low_range = lows.max() - lows.min()
            
            if high_range > 0 and low_range > 0:
                patterns.append({
                    'pattern': 'triangle',
                    'type': pattern_type,
                    'start_date': segment.index[0].strftime('%Y-%m-%d') if hasattr(segment.index[0], 'strftime') else str(segment.index[0]),
                    'end_date': segment.index[-1].strftime('%Y-%m-%d') if hasattr(segment.index[-1], 'strftime') else str(segment.index[-1]),
                    'resistance_level': float(highs.max()),
                    'support_level': float(lows.min()),
                    'confidence': 'medium'
                })
        
        return patterns[:5]
    
    def detect_double_tops_bottoms(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect double tops and double bottoms.
        
        Args:
            data: DataFrame with High and Low prices
            
        Returns:
            List of detected double top/bottom patterns
        """
        patterns = []
        if len(data) < 20:
            return patterns
        
        # Detect double tops
        highs = data['High'].values
        for i in range(10, len(highs) - 10):
            peak1 = highs[i]
            peak2_idx = i + 5
            if peak2_idx >= len(highs):
                continue
            peak2 = highs[peak2_idx]
            
            # Check if peaks are similar (within 2%)
            if abs(peak1 - peak2) / max(peak1, peak2) < 0.02:
                # Check if there's a valley between peaks
                valley = highs[i:i+peak2_idx-i].min()
                if valley < peak1 * 0.95:  # At least 5% drop
                    patterns.append({
                        'pattern': 'double_top',
                        'type': 'bearish',
                        'peak1_price': float(peak1),
                        'peak2_price': float(peak2),
                        'valley_price': float(valley),
                        'date': data.index[peak2_idx].strftime('%Y-%m-%d') if hasattr(data.index[peak2_idx], 'strftime') else str(data.index[peak2_idx]),
                        'confidence': 'medium'
                    })
        
        # Detect double bottoms
        lows = data['Low'].values
        for i in range(10, len(lows) - 10):
            bottom1 = lows[i]
            bottom2_idx = i + 5
            if bottom2_idx >= len(lows):
                continue
            bottom2 = lows[bottom2_idx]
            
            # Check if bottoms are similar
            if abs(bottom1 - bottom2) / max(bottom1, bottom2) < 0.02:
                # Check if there's a peak between bottoms
                peak = lows[i:i+bottom2_idx-i].max()
                if peak > bottom1 * 1.05:  # At least 5% rise
                    patterns.append({
                        'pattern': 'double_bottom',
                        'type': 'bullish',
                        'bottom1_price': float(bottom1),
                        'bottom2_price': float(bottom2),
                        'peak_price': float(peak),
                        'date': data.index[bottom2_idx].strftime('%Y-%m-%d') if hasattr(data.index[bottom2_idx], 'strftime') else str(data.index[bottom2_idx]),
                        'confidence': 'medium'
                    })
        
        return patterns[:5]
    
    def detect_flags_pennants(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect flag and pennant patterns (consolidation after trend).
        
        Args:
            data: DataFrame with price data
            
        Returns:
            List of detected flag/pennant patterns
        """
        patterns = []
        if len(data) < 15:
            return patterns
        
        closes = data['Close'].values
        volumes = data['Volume'].values
        
        # Look for strong trend followed by consolidation
        for i in range(10, len(data) - 5):
            # Check for uptrend before consolidation
            trend_segment = closes[i-10:i]
            consolidation_segment = closes[i:i+5]
            
            trend_slope = np.polyfit(range(len(trend_segment)), trend_segment, 1)[0]
            consolidation_std = np.std(consolidation_segment)
            
            if trend_slope > 0.01 and consolidation_std < np.std(trend_segment) * 0.5:
                # Bullish flag/pennant
                patterns.append({
                    'pattern': 'flag_pennant',
                    'type': 'bullish',
                    'start_date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'end_date': data.index[i+5].strftime('%Y-%m-%d') if hasattr(data.index[i+5], 'strftime') else str(data.index[i+5]),
                    'trend_direction': 'up',
                    'confidence': 'low'
                })
            elif trend_slope < -0.01 and consolidation_std < np.std(trend_segment) * 0.5:
                # Bearish flag/pennant
                patterns.append({
                    'pattern': 'flag_pennant',
                    'type': 'bearish',
                    'start_date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'end_date': data.index[i+5].strftime('%Y-%m-%d') if hasattr(data.index[i+5], 'strftime') else str(data.index[i+5]),
                    'trend_direction': 'down',
                    'confidence': 'low'
                })
        
        return patterns[:5]
    
    def detect_candlestick_patterns(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect candlestick patterns: doji, hammer, shooting star, engulfing, three line strike.
        
        Args:
            data: DataFrame with OHLC data
            
        Returns:
            List of detected candlestick patterns
        """
        patterns = []
        if len(data) < 2:
            return patterns
        
        for i in range(1, len(data)):
            open_price = data.iloc[i]['Open']
            high = data.iloc[i]['High']
            low = data.iloc[i]['Low']
            close = data.iloc[i]['Close']
            
            body = abs(close - open_price)
            upper_shadow = high - max(open_price, close)
            lower_shadow = min(open_price, close) - low
            total_range = high - low
            
            if total_range == 0:
                continue
            
            # Doji: Very small body relative to range
            if body / total_range < 0.1:
                patterns.append({
                    'pattern': 'doji',
                    'type': 'neutral',
                    'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'open': float(open_price),
                    'close': float(close),
                    'confidence': 'medium'
                })
            
            # Hammer: Small body at top, long lower shadow
            if body / total_range < 0.3 and lower_shadow > body * 2 and upper_shadow < body * 0.5:
                patterns.append({
                    'pattern': 'hammer',
                    'type': 'bullish',
                    'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'open': float(open_price),
                    'close': float(close),
                    'confidence': 'medium'
                })
            
            # Shooting Star: Small body at bottom, long upper shadow
            if body / total_range < 0.3 and upper_shadow > body * 2 and lower_shadow < body * 0.5:
                patterns.append({
                    'pattern': 'shooting_star',
                    'type': 'bearish',
                    'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'open': float(open_price),
                    'close': float(close),
                    'confidence': 'medium'
                })
            
            # Engulfing pattern
            prev_open = data.iloc[i-1]['Open']
            prev_close = data.iloc[i-1]['Close']
            
            # Bullish engulfing: current candle completely engulfs previous
            if (close > open_price and prev_close < prev_open and
                open_price < prev_close and close > prev_open):
                patterns.append({
                    'pattern': 'engulfing',
                    'type': 'bullish',
                    'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'open': float(open_price),
                    'close': float(close),
                    'confidence': 'high'
                })
            
            # Bearish engulfing
            if (close < open_price and prev_close > prev_open and
                open_price > prev_close and close < prev_open):
                patterns.append({
                    'pattern': 'engulfing',
                    'type': 'bearish',
                    'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                    'open': float(open_price),
                    'close': float(close),
                    'confidence': 'high'
                })
            
            # Three Line Strike (simplified - check last 3 candles)
            if i >= 3:
                candles = data.iloc[i-2:i+1]
                if len(candles) == 3:
                    # Bullish: three consecutive up candles
                    if all(candles['Close'] > candles['Open']):
                        patterns.append({
                            'pattern': 'three_line_strike',
                            'type': 'bullish',
                            'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                            'confidence': 'medium'
                        })
                    # Bearish: three consecutive down candles
                    elif all(candles['Close'] < candles['Open']):
                        patterns.append({
                            'pattern': 'three_line_strike',
                            'type': 'bearish',
                            'date': data.index[i].strftime('%Y-%m-%d') if hasattr(data.index[i], 'strftime') else str(data.index[i]),
                            'confidence': 'medium'
                        })
        
        return patterns[:10]  # Return top 10
    
    def calculate_support_resistance(self, data: pd.DataFrame, num_levels: int = 5) -> Dict[str, Any]:
        """
        Calculate support and resistance levels.
        
        Finds local minima (support) and maxima (resistance) using rolling windows.
        
        Args:
            data: DataFrame with High and Low prices
            num_levels: Number of levels to return
            
        Returns:
            Dictionary with support and resistance levels
        """
        if len(data) < 20:
            return {'support': [], 'resistance': []}
        
        # Use rolling window to find local extrema
        window = 10
        highs = data['High'].values
        lows = data['Low'].values
        
        # Find local maxima (resistance)
        resistance_levels = []
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                resistance_levels.append(float(highs[i]))
        
        # Find local minima (support)
        support_levels = []
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window+1]):
                support_levels.append(float(lows[i]))
        
        # Remove duplicates and sort
        resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
        support_levels = sorted(set(support_levels))[:num_levels]
        
        return {
            'support': support_levels,
            'resistance': resistance_levels,
            'current_price': float(data['Close'].iloc[-1])
        }
    
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average Directional Index (ADX) - measures trend strength.
        
        Args:
            data: DataFrame with High, Low, Close
            period: Period for ADX calculation
            
        Returns:
            ADX value (0-100)
        """
        if len(data) < period * 2:
            return 0.0
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smooth TR, +DM, -DM
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # ADX is smoothed DX
        adx = dx.rolling(window=period).mean()
        
        return float(adx.iloc[-1]) if not adx.empty else 0.0
    
    def calculate_stochastic(self, data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """
        Calculate Stochastic Oscillator (%K and %D).
        
        Args:
            data: DataFrame with High, Low, Close
            k_period: Period for %K calculation
            d_period: Period for %D (smoothing)
            
        Returns:
            Dictionary with %K and %D values
        """
        if len(data) < k_period + d_period:
            return {'k': 0.0, 'd': 0.0}
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Calculate %K
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        
        # Calculate %D (smoothing of %K)
        d = k.rolling(window=d_period).mean()
        
        return {
            'k': float(k.iloc[-1]) if not k.empty else 0.0,
            'd': float(d.iloc[-1]) if not d.empty else 0.0
        }
    
    def calculate_williams_r(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Williams %R - momentum oscillator.
        
        Args:
            data: DataFrame with High, Low, Close
            period: Period for calculation
            
        Returns:
            Williams %R value (-100 to 0)
        """
        if len(data) < period:
            return 0.0
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
        
        return float(wr.iloc[-1]) if not wr.empty else 0.0
    
    def calculate_cci(self, data: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate Commodity Channel Index (CCI).
        
        Args:
            data: DataFrame with High, Low, Close
            period: Period for calculation
            
        Returns:
            CCI value
        """
        if len(data) < period:
            return 0.0
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Typical Price
        tp = (high + low + close) / 3
        
        # Simple Moving Average of TP
        sma_tp = tp.rolling(window=period).mean()
        
        # Mean Deviation
        md = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        # CCI
        cci = (tp - sma_tp) / (0.015 * md)
        
        return float(cci.iloc[-1]) if not cci.empty else 0.0
    
    def calculate_obv(self, data: pd.DataFrame) -> float:
        """
        Calculate On-Balance Volume (OBV).
        
        Args:
            data: DataFrame with Close and Volume
            
        Returns:
            OBV value
        """
        if len(data) < 2:
            return 0.0
        
        close = data['Close']
        volume = data['Volume']
        
        obv = []
        obv_value = 0.0
        
        for i in range(len(close)):
            if i == 0:
                obv_value = float(volume.iloc[i])
            else:
                if close.iloc[i] > close.iloc[i-1]:
                    obv_value += float(volume.iloc[i])
                elif close.iloc[i] < close.iloc[i-1]:
                    obv_value -= float(volume.iloc[i])
                # If equal, OBV stays the same
            
            obv.append(obv_value)
        
        return obv[-1] if obv else 0.0
    
    def calculate_mfi(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Money Flow Index (MFI).
        
        Args:
            data: DataFrame with High, Low, Close, Volume
            period: Period for calculation
            
        Returns:
            MFI value (0-100)
        """
        if len(data) < period:
            return 50.0
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        volume = data['Volume']
        
        # Typical Price
        tp = (high + low + close) / 3
        
        # Raw Money Flow
        rmf = tp * volume
        
        # Positive and Negative Money Flow
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(tp)):
            if tp.iloc[i] > tp.iloc[i-1]:
                positive_flow.append(rmf.iloc[i])
                negative_flow.append(0)
            elif tp.iloc[i] < tp.iloc[i-1]:
                positive_flow.append(0)
                negative_flow.append(rmf.iloc[i])
            else:
                positive_flow.append(0)
                negative_flow.append(0)
        
        # Calculate MFI
        positive_flow_series = pd.Series(positive_flow, index=data.index[1:])
        negative_flow_series = pd.Series(negative_flow, index=data.index[1:])
        
        positive_sum = positive_flow_series.rolling(window=period).sum()
        negative_sum = negative_flow_series.rolling(window=period).sum()
        
        money_ratio = positive_sum / negative_sum
        mfi = 100 - (100 / (1 + money_ratio))
        
        return float(mfi.iloc[-1]) if not mfi.empty else 50.0


# Initialize analyzer singleton
_analyzer: Optional[FinancialMarketsAnalyzer] = None


def get_analyzer() -> FinancialMarketsAnalyzer:
    """Get singleton Financial Markets Analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FinancialMarketsAnalyzer()
    return _analyzer


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Financial Markets MCP server.
    
    Supports both Lambda Function URL and API Gateway events.
    Implements JSON-RPC 2.0 protocol for MCP.
    
    Args:
        event: Lambda event (Function URL or API Gateway)
        context: Lambda context
        
    Returns:
        For Function URL: Dict with statusCode, headers, body
        For API Gateway: Dict with statusCode, headers, body
    """
    try:
        # Detect event source (Function URL vs API Gateway)
        is_function_url = 'requestContext' in event and 'http' in event.get('requestContext', {})
        is_api_gateway = 'httpMethod' in event or 'requestContext' in event and 'httpMethod' in event.get('requestContext', {})
        
        # Parse request body
        if is_function_url or is_api_gateway:
            # HTTP event (Function URL or API Gateway)
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
        else:
            # Direct invocation (for testing)
            body = event
        
        # Extract JSON-RPC fields
        method = body.get('method')
        params = body.get('params', {})
        request_id = body.get('id', 1)
        
        logger.info(f"MCP request: method={method}, params={params}")
        
        # Route to appropriate handler
        if method == 'tools/list':
            result = handle_tools_list()
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            result = handle_tool_call(tool_name, arguments)
        else:
            error_response = {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }
            return _format_http_response(error_response, 400)
        
        # Return success response
        success_response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }
        return _format_http_response(success_response, 200)
        
    except Exception as e:
        logger.error(f"MCP server error: {e}", exc_info=True)
        error_response = {
            'jsonrpc': '2.0',
            'id': body.get('id', 1) if 'body' in locals() else 1,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }
        return _format_http_response(error_response, 500)


def _format_http_response(data: Dict[str, Any], status_code: int) -> Dict[str, Any]:
    """
    Format response for Lambda Function URL or API Gateway.
    
    Args:
        data: Response data (JSON-RPC response)
        status_code: HTTP status code
        
    Returns:
        Formatted HTTP response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # CORS for MCP clients
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data)
    }


def handle_tools_list() -> Dict[str, Any]:
    """Handle tools/list MCP request."""
    return {
        'tools': [
            {
                'name': 'get_chart_patterns',
                'description': 'Detect chart patterns (head & shoulders, triangles, double tops/bottoms, flags/pennants)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        }
                    },
                    'required': ['ticker']
                }
            },
            {
                'name': 'get_candlestick_patterns',
                'description': 'Detect candlestick patterns (doji, hammer, shooting star, engulfing, three line strike)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        }
                    },
                    'required': ['ticker']
                }
            },
            {
                'name': 'get_support_resistance',
                'description': 'Calculate support and resistance levels',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        },
                        'num_levels': {
                            'type': 'integer',
                            'description': 'Number of support/resistance levels to return',
                            'default': 5
                        }
                    },
                    'required': ['ticker']
                }
            },
            {
                'name': 'get_technical_indicators',
                'description': 'Calculate advanced technical indicators (ADX, Stochastic, Williams %R, CCI, OBV, MFI)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        }
                    },
                    'required': ['ticker']
                }
            }
        ]
    }


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle tools/call MCP request.
    
    Args:
        tool_name: Tool name to call
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    analyzer = get_analyzer()
    ticker = arguments.get('ticker')
    
    if not ticker:
        raise ValueError("ticker argument is required")
    
    # Fetch price data
    data = analyzer.fetch_price_data(ticker)
    if data is None or data.empty:
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'error': f'Could not fetch data for ticker: {ticker}'
                    })
                }
            ]
        }
    
    if tool_name == 'get_chart_patterns':
        patterns = []
        patterns.extend(analyzer.detect_head_and_shoulders(data))
        patterns.extend(analyzer.detect_triangles(data))
        patterns.extend(analyzer.detect_double_tops_bottoms(data))
        patterns.extend(analyzer.detect_flags_pennants(data))
        
        result = {
            'ticker': ticker,
            'patterns': patterns,
            'pattern_count': len(patterns)
        }
        
    elif tool_name == 'get_candlestick_patterns':
        patterns = analyzer.detect_candlestick_patterns(data)
        result = {
            'ticker': ticker,
            'patterns': patterns,
            'pattern_count': len(patterns)
        }
        
    elif tool_name == 'get_support_resistance':
        num_levels = arguments.get('num_levels', 5)
        levels = analyzer.calculate_support_resistance(data, num_levels)
        result = {
            'ticker': ticker,
            'support_levels': levels['support'],
            'resistance_levels': levels['resistance'],
            'current_price': levels['current_price']
        }
        
    elif tool_name == 'get_technical_indicators':
        adx = analyzer.calculate_adx(data)
        stochastic = analyzer.calculate_stochastic(data)
        williams_r = analyzer.calculate_williams_r(data)
        cci = analyzer.calculate_cci(data)
        obv = analyzer.calculate_obv(data)
        mfi = analyzer.calculate_mfi(data)
        
        result = {
            'ticker': ticker,
            'adx': adx,
            'stochastic': stochastic,
            'williams_r': williams_r,
            'cci': cci,
            'obv': obv,
            'mfi': mfi
        }
        
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    return {
        'content': [
            {
                'type': 'text',
                'text': json.dumps(result, indent=2)
            }
        ]
    }
