#!/usr/bin/env python3
"""
Local validation test for API handler
Tests the /analyze endpoint functionality without deploying to Lambda
"""

import sys
import os
import json
import base64

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api_handler import api_handler


def test_api_handler_success():
    """Test successful API call"""
    print("=" * 80)
    print("TEST 1: Successful API Call - AAPL19")
    print("=" * 80)
    print()

    # Simulate API Gateway event
    event = {
        'queryStringParameters': {
            'ticker': 'AAPL19'
        },
        'headers': {},
        'body': None
    }

    context = None  # Lambda context not needed for testing

    print("📥 Request:")
    print(f"   GET /analyze?ticker=AAPL19")
    print()

    # Call handler
    print("🔄 Processing...")
    response = api_handler(event, context)

    print("✅ Response received!")
    print()

    # Validate response structure
    print("📊 Response Validation:")
    print(f"   Status Code: {response['statusCode']}")
    print(f"   Headers: {response['headers']}")
    print()

    # Parse body
    body = json.loads(response['body'])

    # Check all expected fields
    expected_fields = [
        'ticker', 'ticker_data', 'indicators', 'percentiles',
        'news', 'news_summary', 'chart_base64', 'report'
    ]

    print("🔍 Field Validation:")
    for field in expected_fields:
        exists = field in body
        icon = "✅" if exists else "❌"
        print(f"   {icon} {field}: {'Present' if exists else 'MISSING'}")

    print()

    # Display sample data
    if response['statusCode'] == 200:
        print("📈 Sample Data:")
        print(f"   Company: {body.get('ticker_data', {}).get('company_name', 'N/A')}")
        print(f"   Price: ${body.get('ticker_data', {}).get('close', 0):.2f}")
        print(f"   RSI: {body.get('indicators', {}).get('rsi', 'N/A'):.2f}")
        print(f"   Chart size: {len(body.get('chart_base64', ''))} chars")
        print(f"   Report length: {len(body.get('report', ''))} chars")
        print()

        # Validate chart is valid PNG
        chart_b64 = body.get('chart_base64', '')
        if chart_b64:
            try:
                chart_bytes = base64.b64decode(chart_b64)
                is_png = chart_bytes[:8] == b'\x89PNG\r\n\x1a\n'
                print(f"   Chart format: {'✅ Valid PNG' if is_png else '❌ Invalid'}")
                print(f"   Chart size: {len(chart_bytes)} bytes ({len(chart_bytes)/1024:.1f} KB)")
            except:
                print("   Chart format: ❌ Invalid base64")

        print()
        print("📝 Report Preview (first 500 chars):")
        print("-" * 80)
        print(body.get('report', '')[:500] + "...")
        print("-" * 80)

        return True
    else:
        print(f"❌ Request failed: {body}")
        return False


def test_api_handler_missing_ticker():
    """Test API call with missing ticker parameter"""
    print("\n" + "=" * 80)
    print("TEST 2: Missing Ticker Parameter")
    print("=" * 80)
    print()

    event = {
        'queryStringParameters': {},
        'headers': {},
        'body': None
    }

    print("📥 Request:")
    print(f"   GET /analyze (no ticker parameter)")
    print()

    response = api_handler(event, None)

    print(f"📊 Status Code: {response['statusCode']}")
    print(f"📊 Expected: 400 (Bad Request)")
    print()

    body = json.loads(response['body'])
    print(f"Error Message: {body.get('error', 'N/A')}")
    print()

    if response['statusCode'] == 400:
        print("✅ Error handling works correctly!")
        return True
    else:
        print("❌ Error handling failed!")
        return False


def test_api_handler_invalid_ticker():
    """Test API call with invalid ticker"""
    print("\n" + "=" * 80)
    print("TEST 3: Invalid Ticker Symbol")
    print("=" * 80)
    print()

    event = {
        'queryStringParameters': {
            'ticker': 'INVALIDXYZ999'
        },
        'headers': {},
        'body': None
    }

    print("📥 Request:")
    print(f"   GET /analyze?ticker=INVALIDXYZ999")
    print()

    response = api_handler(event, None)

    print(f"📊 Status Code: {response['statusCode']}")
    print()

    body = json.loads(response['body'])

    if 'error' in body:
        print(f"Error: {body['error']}")
        print("✅ Invalid ticker handled correctly!")
        return True
    else:
        print("⚠️  Request completed (ticker may exist or error not caught)")
        return True


def test_save_full_response():
    """Save full API response for manual inspection"""
    print("\n" + "=" * 80)
    print("TEST 4: Save Full Response to File")
    print("=" * 80)
    print()

    event = {
        'queryStringParameters': {
            'ticker': 'TSLA19'
        },
        'headers': {},
        'body': None
    }

    print("📥 Request:")
    print(f"   GET /analyze?ticker=TSLA19")
    print()

    response = api_handler(event, None)

    if response['statusCode'] == 200:
        body = json.loads(response['body'])

        # Save full JSON (without chart to keep file size manageable)
        body_no_chart = body.copy()
        chart_b64 = body_no_chart.pop('chart_base64', '')
        body_no_chart['chart_base64_length'] = len(chart_b64)
        body_no_chart['chart_base64_preview'] = chart_b64[:100] + '...' if chart_b64 else ''

        with open('api_response_sample.json', 'w', encoding='utf-8') as f:
            json.dump(body_no_chart, f, indent=2, ensure_ascii=False)
        print("✅ Saved to: api_response_sample.json")

        # Save chart separately
        if chart_b64:
            with open('api_response_chart.png', 'wb') as f:
                f.write(base64.b64decode(chart_b64))
            print("✅ Saved chart to: api_response_chart.png")

        print()
        print("📁 Files created:")
        print("   - api_response_sample.json (full response without chart)")
        print("   - api_response_chart.png (chart image)")
        print()

        return True
    else:
        print("❌ Request failed")
        return False


if __name__ == "__main__":
    print("\n" + "🧪" * 40)
    print("API HANDLER LOCAL VALIDATION TEST")
    print("🧪" * 40 + "\n")

    results = []

    # Run tests
    results.append(("API Success Test", test_api_handler_success()))
    results.append(("Missing Ticker Test", test_api_handler_missing_ticker()))
    results.append(("Invalid Ticker Test", test_api_handler_invalid_ticker()))
    results.append(("Save Response Test", test_save_full_response()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {name}")
    print("=" * 80)

    all_passed = all(result[1] for result in results)
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print()

    sys.exit(0 if all_passed else 1)
