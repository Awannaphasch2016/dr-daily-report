# -*- coding: utf-8 -*-
"""
Financial Markets MCP Server Lambda Handler - THIN ADAPTER

Implements Model Context Protocol (MCP) server for advanced technical analysis.
Delegates pattern detection to core analysis modules (Principle #20: Execution Boundary Discipline).

Architecture:
- MCP Server (this file): Protocol adapter for JSON-RPC 2.0
- Core Analysis: src/analysis/pattern_detectors/ (reusable across reports/API/ETL)

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

# Import core analysis modules (refactored from inline implementation)
from src.analysis.pattern_detectors import (
    ChartPatternDetector,
    CandlestickPatternDetector,
    SupportResistanceDetector,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FinancialMarketsAnalyzer:
    """
    MCP Server Analyzer - Thin Adapter Pattern.

    Delegates pattern detection to core analysis modules:
    - ChartPatternDetector: Head & shoulders, triangles, double tops/bottoms, flags/pennants
    - CandlestickPatternDetector: Doji, hammer, shooting star, engulfing, three line strike
    - SupportResistanceDetector: Support/resistance level calculation

    This class focuses on:
    - Data fetching (yfinance)
    - Technical indicators (ADX, Stochastic, etc.)
    - MCP protocol adaptation (JSON-RPC)
    """

    def __init__(self):
        """Initialize Financial Markets Analyzer with pattern detectors."""
        # Initialize core analysis modules (Principle #20: Execution Boundary Discipline)
        self.chart_detector = ChartPatternDetector()
        self.candlestick_detector = CandlestickPatternDetector()
        self.sr_detector = SupportResistanceDetector()
    
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
        Detect Head & Shoulders patterns (DELEGATED TO CORE MODULE).

        Delegates to ChartPatternDetector for reusable pattern detection.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected head & shoulders patterns
        """
        return self.chart_detector.detect_head_and_shoulders(data)
    
    def detect_triangles(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect triangle patterns (DELEGATED TO CORE MODULE).

        Delegates to ChartPatternDetector for reusable pattern detection.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected triangle patterns (ascending, descending, symmetrical)
        """
        return self.chart_detector.detect_triangles(data)
    
    def detect_double_tops_bottoms(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect double tops and double bottoms (DELEGATED TO CORE MODULE).

        Delegates to ChartPatternDetector for reusable pattern detection.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected double top/bottom patterns
        """
        return self.chart_detector.detect_double_tops_bottoms(data)
    
    def detect_flags_pennants(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect flag and pennant patterns (DELEGATED TO CORE MODULE).

        Delegates to ChartPatternDetector for reusable pattern detection.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected flag/pennant patterns
        """
        return self.chart_detector.detect_flags_pennants(data)
    
    def detect_candlestick_patterns(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect candlestick patterns (DELEGATED TO CORE MODULE).

        Delegates to CandlestickPatternDetector for reusable pattern detection.

        Args:
            data: DataFrame with OHLC columns

        Returns:
            List of detected candlestick patterns (doji, hammer, shooting star, engulfing, three line strike)
        """
        return self.candlestick_detector.detect(data)
    
    def calculate_support_resistance(self, data: pd.DataFrame, num_levels: int = 5) -> Dict[str, Any]:
        """
        Calculate support and resistance levels (DELEGATED TO CORE MODULE).

        Delegates to SupportResistanceDetector for reusable level calculation.

        Args:
            data: DataFrame with OHLC columns
            num_levels: Number of levels to return for each type

        Returns:
            Dictionary with support and resistance levels
        """
        return self.sr_detector.calculate_levels(data, num_levels=num_levels)
    
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
