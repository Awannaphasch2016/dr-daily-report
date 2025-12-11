#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Financial Markets MCP Handler

Tests the Financial Markets MCP server handler directly and via MCP client.
Verifies pattern detection, candlestick patterns, support/resistance, and technical indicators.
"""

import os
import sys
import json
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_servers.financial_markets_handler import (
    FinancialMarketsAnalyzer,
    handle_tool_call,
    lambda_handler
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_analyzer_direct():
    """Test FinancialMarketsAnalyzer directly."""
    logger.info("=" * 60)
    logger.info("Testing FinancialMarketsAnalyzer directly")
    logger.info("=" * 60)
    
    analyzer = FinancialMarketsAnalyzer()
    ticker = "AAPL"  # Use a well-known ticker
    
    # Fetch data
    logger.info(f"Fetching data for {ticker}...")
    data = analyzer.fetch_price_data(ticker, period="6mo")
    
    if data is None or data.empty:
        logger.error(f"Failed to fetch data for {ticker}")
        return False
    
    logger.info(f"✅ Fetched {len(data)} days of data")
    
    # Test chart patterns
    logger.info("\nTesting chart pattern detection...")
    chart_patterns = analyzer.detect_head_and_shoulders(data)
    logger.info(f"  Head & Shoulders: {len(chart_patterns)} patterns")
    
    triangles = analyzer.detect_triangles(data)
    logger.info(f"  Triangles: {len(triangles)} patterns")
    
    double_patterns = analyzer.detect_double_tops_bottoms(data)
    logger.info(f"  Double Tops/Bottoms: {len(double_patterns)} patterns")
    
    flags = analyzer.detect_flags_pennants(data)
    logger.info(f"  Flags/Pennants: {len(flags)} patterns")
    
    # Test candlestick patterns
    logger.info("\nTesting candlestick pattern detection...")
    candlestick_patterns = analyzer.detect_candlestick_patterns(data)
    logger.info(f"  Candlestick patterns: {len(candlestick_patterns)} patterns")
    if candlestick_patterns:
        for pattern in candlestick_patterns[:3]:  # Show first 3
            logger.info(f"    - {pattern['pattern']} ({pattern['type']}) on {pattern.get('date', 'N/A')}")
    
    # Test support/resistance
    logger.info("\nTesting support/resistance calculation...")
    support_resistance = analyzer.calculate_support_resistance(data, num_levels=5)
    logger.info(f"  Support levels: {support_resistance['support']}")
    logger.info(f"  Resistance levels: {support_resistance['resistance']}")
    logger.info(f"  Current price: {support_resistance['current_price']}")
    
    # Test technical indicators
    logger.info("\nTesting technical indicators...")
    adx = analyzer.calculate_adx(data)
    logger.info(f"  ADX: {adx:.2f}")
    
    stochastic = analyzer.calculate_stochastic(data)
    logger.info(f"  Stochastic %K: {stochastic['k']:.2f}, %D: {stochastic['d']:.2f}")
    
    williams_r = analyzer.calculate_williams_r(data)
    logger.info(f"  Williams %R: {williams_r:.2f}")
    
    cci = analyzer.calculate_cci(data)
    logger.info(f"  CCI: {cci:.2f}")
    
    obv = analyzer.calculate_obv(data)
    logger.info(f"  OBV: {obv:.2f}")
    
    mfi = analyzer.calculate_mfi(data)
    logger.info(f"  MFI: {mfi:.2f}")
    
    logger.info("\n✅ All analyzer tests passed!")
    return True


def test_mcp_handler():
    """Test MCP handler via handle_tool_call."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing MCP handler via handle_tool_call")
    logger.info("=" * 60)
    
    ticker = "NVDA"  # Use another ticker for variety
    
    # Test get_chart_patterns
    logger.info(f"\nTesting get_chart_patterns for {ticker}...")
    try:
        result = handle_tool_call('get_chart_patterns', {'ticker': ticker})
        if 'content' in result and len(result['content']) > 0:
            data = json.loads(result['content'][0]['text'])
            logger.info(f"  ✅ Chart patterns: {data.get('pattern_count', 0)} patterns found")
            if data.get('patterns'):
                logger.info(f"    Sample: {data['patterns'][0].get('pattern', 'N/A')}")
        else:
            logger.warning("  ⚠️  No content in response")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    # Test get_candlestick_patterns
    logger.info(f"\nTesting get_candlestick_patterns for {ticker}...")
    try:
        result = handle_tool_call('get_candlestick_patterns', {'ticker': ticker})
        if 'content' in result and len(result['content']) > 0:
            data = json.loads(result['content'][0]['text'])
            logger.info(f"  ✅ Candlestick patterns: {data.get('pattern_count', 0)} patterns found")
        else:
            logger.warning("  ⚠️  No content in response")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    # Test get_support_resistance
    logger.info(f"\nTesting get_support_resistance for {ticker}...")
    try:
        result = handle_tool_call('get_support_resistance', {'ticker': ticker, 'num_levels': 5})
        if 'content' in result and len(result['content']) > 0:
            data = json.loads(result['content'][0]['text'])
            logger.info(f"  ✅ Support levels: {len(data.get('support_levels', []))}")
            logger.info(f"  ✅ Resistance levels: {len(data.get('resistance_levels', []))}")
        else:
            logger.warning("  ⚠️  No content in response")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    # Test get_technical_indicators
    logger.info(f"\nTesting get_technical_indicators for {ticker}...")
    try:
        result = handle_tool_call('get_technical_indicators', {'ticker': ticker})
        if 'content' in result and len(result['content']) > 0:
            data = json.loads(result['content'][0]['text'])
            logger.info(f"  ✅ ADX: {data.get('adx', 0):.2f}")
            logger.info(f"  ✅ Stochastic: K={data.get('stochastic', {}).get('k', 0):.2f}, D={data.get('stochastic', {}).get('d', 0):.2f}")
            logger.info(f"  ✅ Williams %R: {data.get('williams_r', 0):.2f}")
            logger.info(f"  ✅ CCI: {data.get('cci', 0):.2f}")
            logger.info(f"  ✅ OBV: {data.get('obv', 0):.2f}")
            logger.info(f"  ✅ MFI: {data.get('mfi', 0):.2f}")
        else:
            logger.warning("  ⚠️  No content in response")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    logger.info("\n✅ All MCP handler tests passed!")
    return True


def test_lambda_handler():
    """Test lambda_handler with JSON-RPC format."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing lambda_handler (JSON-RPC format)")
    logger.info("=" * 60)
    
    # Test tools/list
    logger.info("\nTesting tools/list...")
    event = {
        'body': json.dumps({
            'jsonrpc': '2.0',
            'method': 'tools/list',
            'id': 1
        })
    }
    
    try:
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'result' in body
        assert 'tools' in body['result']
        logger.info(f"  ✅ tools/list returned {len(body['result']['tools'])} tools")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    # Test tools/call
    logger.info("\nTesting tools/call (get_chart_patterns)...")
    event = {
        'body': json.dumps({
            'jsonrpc': '2.0',
            'method': 'tools/call',
            'params': {
                'name': 'get_chart_patterns',
                'arguments': {'ticker': 'AAPL'}
            },
            'id': 1
        })
    }
    
    try:
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'result' in body
        assert 'content' in body['result']
        logger.info("  ✅ tools/call returned valid response")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False
    
    logger.info("\n✅ All lambda_handler tests passed!")
    return True


def main():
    """Run all tests."""
    logger.info("Starting Financial Markets MCP Handler Tests")
    logger.info("=" * 60)
    
    results = []
    
    # Test 1: Direct analyzer
    try:
        results.append(("Direct Analyzer", test_analyzer_direct()))
    except Exception as e:
        logger.error(f"Direct analyzer test failed: {e}", exc_info=True)
        results.append(("Direct Analyzer", False))
    
    # Test 2: MCP handler
    try:
        results.append(("MCP Handler", test_mcp_handler()))
    except Exception as e:
        logger.error(f"MCP handler test failed: {e}", exc_info=True)
        results.append(("MCP Handler", False))
    
    # Test 3: Lambda handler
    try:
        results.append(("Lambda Handler", test_lambda_handler()))
    except Exception as e:
        logger.error(f"Lambda handler test failed: {e}", exc_info=True)
        results.append(("Lambda Handler", False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
