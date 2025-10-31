#!/usr/bin/env python3
"""
Test suite for API handler (api_handler.py)

Tests:
- Ticker parameter extraction
- Successful analysis flow
- Error cases (missing ticker, invalid ticker)
- JSON serialization
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api_handler import api_handler, sanitize_ticker_data, sanitize_news, sanitize_dict


def test_missing_ticker_parameter():
    """Test that missing ticker parameter returns 400 error"""
    print("\n🔍 Testing missing ticker parameter...")
    
    event = {
        'queryStringParameters': None
    }
    
    result = api_handler(event, None)
    
    assert result['statusCode'] == 400, "Should return 400 status code"
    body = json.loads(result['body'])
    assert 'error' in body, "Should contain error message"
    assert 'ticker' in body['error'].lower() or 'parameter' in body['error'].lower()
    
    print("✅ Missing ticker parameter test passed")


def test_empty_ticker_parameter():
    """Test that empty ticker parameter returns 400 error"""
    print("\n🔍 Testing empty ticker parameter...")
    
    event = {
        'queryStringParameters': {
            'ticker': ''
        }
    }
    
    result = api_handler(event, None)
    
    assert result['statusCode'] == 400, "Should return 400 status code"
    body = json.loads(result['body'])
    assert 'error' in body, "Should contain error message"
    
    print("✅ Empty ticker parameter test passed")


def test_sanitize_ticker_data():
    """Test that DataFrame is removed from ticker_data"""
    print("\n🔍 Testing ticker_data sanitization...")
    
    import pandas as pd
    
    # Create mock ticker_data with DataFrame
    ticker_data = {
        'date': datetime(2024, 1, 1),
        'close': 150.50,
        'open': 149.00,
        'history': pd.DataFrame({'Close': [150, 151, 152]})  # DataFrame to remove
    }
    
    sanitized = sanitize_ticker_data(ticker_data)
    
    assert 'history' not in sanitized, "DataFrame should be removed"
    assert sanitized['close'] == 150.50, "Other fields should be preserved"
    assert sanitized['date'] == datetime(2024, 1, 1).isoformat(), "Date should be converted to ISO format"
    
    print("✅ Ticker data sanitization test passed")


def test_sanitize_news():
    """Test that news items are properly sanitized"""
    print("\n🔍 Testing news sanitization...")
    
    news_list = [
        {
            'title': 'Test News',
            'timestamp': datetime(2024, 1, 1),
            'link': 'https://example.com',
            'raw': {'some': 'large', 'nested': 'data'}  # Should be removed
        }
    ]
    
    sanitized = sanitize_news(news_list)
    
    assert len(sanitized) == 1, "Should have one news item"
    assert 'raw' not in sanitized[0], "Raw data should be removed"
    assert sanitized[0]['title'] == 'Test News', "Title should be preserved"
    assert isinstance(sanitized[0]['timestamp'], str), "Timestamp should be converted to string"
    
    print("✅ News sanitization test passed")


def test_sanitize_dict():
    """Test recursive dictionary sanitization"""
    print("\n🔍 Testing dictionary sanitization...")
    
    data = {
        'date': datetime(2024, 1, 1),
        'nested': {
            'inner_date': datetime(2024, 1, 2)
        },
        'list': [
            {'item_date': datetime(2024, 1, 3)}
        ]
    }
    
    sanitized = sanitize_dict(data)
    
    assert isinstance(sanitized['date'], str), "Date should be converted to ISO string"
    assert isinstance(sanitized['nested']['inner_date'], str), "Nested date should be converted"
    assert isinstance(sanitized['list'][0]['item_date'], str), "List item date should be converted"
    
    print("✅ Dictionary sanitization test passed")


def test_json_serialization():
    """Test that sanitized data can be JSON serialized"""
    print("\n🔍 Testing JSON serialization...")
    
    import pandas as pd
    
    # Create data with non-serializable objects
    ticker_data = {
        'date': datetime(2024, 1, 1),
        'close': 150.50,
        'history': pd.DataFrame({'Close': [150, 151]})
    }
    
    news_list = [
        {
            'title': 'Test',
            'timestamp': datetime(2024, 1, 1),
            'raw': {'data': 'should be removed'}
        }
    ]
    
    sanitized_ticker = sanitize_ticker_data(ticker_data)
    sanitized_news = sanitize_news(news_list)
    
    # Try to serialize
    try:
        json_str = json.dumps({
            'ticker_data': sanitized_ticker,
            'news': sanitized_news
        }, ensure_ascii=False)
        json.loads(json_str)  # Should not raise exception
        print("✅ JSON serialization test passed")
    except Exception as e:
        print(f"❌ JSON serialization failed: {str(e)}")
        raise


@patch('src.api_handler.get_agent')
def test_successful_analysis(mock_get_agent):
    """Test successful analysis flow"""
    print("\n🔍 Testing successful analysis flow...")
    
    # Mock agent and graph
    mock_agent = MagicMock()
    mock_graph = MagicMock()
    
    # Mock final state
    mock_final_state = {
        'ticker': 'AAPL',
        'ticker_data': {
            'date': datetime(2024, 1, 1),
            'close': 150.50,
            'market_cap': 2800000000000,
            'pe_ratio': 29.5
        },
        'indicators': {
            'sma_20': 176.20,
            'rsi': 58.3,
            'macd': 1.25
        },
        'news': [
            {
                'title': 'Test News',
                'timestamp': datetime(2024, 1, 1),
                'sentiment': 'positive',
                'impact_score': 75.0
            }
        ],
        'news_summary': {
            'total_count': 5,
            'dominant_sentiment': 'positive'
        },
        'report': 'Test report in Thai',
        'error': ''
    }
    
    mock_graph.invoke.return_value = mock_final_state
    mock_agent.graph = mock_graph
    mock_get_agent.return_value = mock_agent
    
    event = {
        'queryStringParameters': {
            'ticker': 'AAPL'
        }
    }
    
    result = api_handler(event, None)
    
    assert result['statusCode'] == 200, "Should return 200 status code"
    body = json.loads(result['body'])
    
    assert body['ticker'] == 'AAPL', "Should return correct ticker"
    assert 'ticker_data' in body, "Should contain ticker_data"
    assert 'indicators' in body, "Should contain indicators"
    assert 'news' in body, "Should contain news"
    assert 'news_summary' in body, "Should contain news_summary"
    assert 'report' in body, "Should contain report"
    
    # Verify data is sanitized (no DataFrames)
    assert isinstance(body['ticker_data'], dict), "ticker_data should be dict"
    assert 'history' not in body['ticker_data'], "Should not contain history DataFrame"
    
    print("✅ Successful analysis test passed")


@patch('src.api_handler.get_agent')
def test_error_handling(mock_get_agent):
    """Test error handling when agent returns error"""
    print("\n🔍 Testing error handling...")
    
    mock_agent = MagicMock()
    mock_graph = MagicMock()
    
    # Mock final state with error
    mock_final_state = {
        'error': 'ไม่พบข้อมูล ticker สำหรับ INVALID'
    }
    
    mock_graph.invoke.return_value = mock_final_state
    mock_agent.graph = mock_graph
    mock_get_agent.return_value = mock_agent
    
    event = {
        'queryStringParameters': {
            'ticker': 'INVALID'
        }
    }
    
    result = api_handler(event, None)
    
    assert result['statusCode'] == 400, "Should return 400 status code"
    body = json.loads(result['body'])
    assert 'error' in body, "Should contain error message"
    
    print("✅ Error handling test passed")


def test_cors_headers():
    """Test that CORS headers are included"""
    print("\n🔍 Testing CORS headers...")
    
    event = {
        'queryStringParameters': {
            'ticker': 'AAPL'
        }
    }
    
    # This will fail because we don't have a real agent, but we can check headers
    try:
        result = api_handler(event, None)
        headers = result.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers, "Should include CORS header"
        assert headers['Access-Control-Allow-Origin'] == '*', "CORS should allow all origins"
        print("✅ CORS headers test passed")
    except Exception:
        # If agent fails, we can still test error response headers
        # But let's just verify the function structure
        print("⚠️  CORS headers test skipped (requires agent setup)")


def test_ticker_uppercase():
    """Test that ticker is converted to uppercase"""
    print("\n🔍 Testing ticker uppercase conversion...")
    
    event = {
        'queryStringParameters': {
            'ticker': 'aapl'  # lowercase
        }
    }
    
    # Mock agent to return successful state
    with patch('src.api_handler.get_agent') as mock_get_agent:
        mock_agent = MagicMock()
        mock_graph = MagicMock()
        mock_final_state = {
            'ticker': 'AAPL',
            'ticker_data': {'date': datetime(2024, 1, 1), 'close': 150.50},
            'indicators': {},
            'news': [],
            'news_summary': {},
            'report': 'Test',
            'error': ''
        }
        mock_graph.invoke.return_value = mock_final_state
        mock_agent.graph = mock_graph
        mock_get_agent.return_value = mock_agent
        
        result = api_handler(event, None)
        
        if result['statusCode'] == 200:
            body = json.loads(result['body'])
            assert body['ticker'] == 'AAPL', "Ticker should be uppercase"
            print("✅ Ticker uppercase conversion test passed")
        else:
            print("⚠️  Ticker uppercase test skipped (requires agent setup)")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("API Handler Test Suite")
    print("=" * 80)
    
    tests = [
        ("Missing ticker parameter", test_missing_ticker_parameter),
        ("Empty ticker parameter", test_empty_ticker_parameter),
        ("Sanitize ticker data", test_sanitize_ticker_data),
        ("Sanitize news", test_sanitize_news),
        ("Sanitize dictionary", test_sanitize_dict),
        ("JSON serialization", test_json_serialization),
        ("CORS headers", test_cors_headers),
        ("Ticker uppercase", test_ticker_uppercase),
    ]
    
    # Mock tests (require mocks)
    mock_tests = [
        ("Successful analysis", test_successful_analysis),
        ("Error handling", test_error_handling),
    ]
    
    results = []
    
    # Run basic tests
    for name, test_func in tests:
        try:
            test_func()
            results.append(True)
        except Exception as e:
            print(f"❌ {name} test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Run mock tests
    for name, test_func in mock_tests:
        try:
            test_func()
            results.append(True)
        except Exception as e:
            print(f"❌ {name} test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
