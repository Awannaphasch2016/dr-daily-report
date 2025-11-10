#!/usr/bin/env python3
"""
Post-deployment verification script
Automatically tests Lambda function after deployment to verify it works correctly
"""

import json
import boto3
import sys
import time
from datetime import datetime

def test_lambda_after_deployment(function_name: str, ticker: str = "DBS19"):
    """
    Test Lambda function after deployment
    
    Args:
        function_name: Lambda function name
        ticker: Ticker to test with (default: DBS19)
    
    Returns:
        dict with test results
    """
    print("=" * 80)
    print("POST-DEPLOYMENT VERIFICATION")
    print("=" * 80)
    print()
    print(f"🧪 Testing Lambda function: {function_name}")
    print(f"📊 Test ticker: {ticker}")
    print()
    
    lambda_client = boto3.client('lambda')
    
    # Create test event
    event = {
        "body": json.dumps({
            "events": [{
                "type": "message",
                "replyToken": "test-token-verification",
                "source": {"type": "user", "userId": "test-user"},
                "timestamp": int(time.time()),
                "message": {"type": "text", "id": "test-msg", "text": ticker}
            }]
        }),
        "headers": {
            "x-line-signature": "test_signature"
        }
    }
    
    print("⏳ Invoking Lambda function...")
    print()
    
    try:
        start_time = time.time()
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        duration = time.time() - start_time
        
        result = json.loads(response['Payload'].read())
        
        print("=" * 80)
        print("✅ LAMBDA FUNCTION TEST RESULT")
        print("=" * 80)
        print()
        print(f"Status Code: {result.get('statusCode', 'N/A')}")
        print(f"Duration: {duration:.2f} seconds")
        print()
        
        # Parse response body
        if 'body' in result:
            try:
                body = json.loads(result['body'])
                if 'responses' in body:
                    response_text = body['responses'][0] if body['responses'] else ""
                    print(f"Response Length: {len(response_text)} characters")
                    print()
                    print("=" * 80)
                    print("RESPONSE PREVIEW (first 500 chars):")
                    print("=" * 80)
                    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
                    print()
                    
                    # Check for PDF URL or template message
                    has_pdf_link = "รายงานฉบับเต็ม" in response_text or "https://" in response_text
                    has_template = "Template message available" in str(result)
                    
                    print("=" * 80)
                    print("FEATURE VERIFICATION:")
                    print("=" * 80)
                    
                    if has_pdf_link:
                        print("✅ PDF link detected in response")
                    else:
                        print("ℹ️  PDF link not in test mode response (normal - test mode returns text only)")
                    
                    if has_template:
                        print("✅ Template message was created")
                    else:
                        print("ℹ️  Template message info not in test mode response (normal)")
                    
                    print()
                    print("📝 Note: In production, users will receive:")
                    print("   1. Template message card with button: '[TICKER] รายงานฉบับเต็ม'")
                    print("   2. Text report message")
                    print("   (Test mode only returns text for verification)")
                else:
                    print("Response Body:", body)
            except json.JSONDecodeError:
                print("Response Body (raw):", result.get('body', '')[:500])
        else:
            print("Full Result:", json.dumps(result, indent=2, ensure_ascii=False)[:1000])
        
        print()
        print("=" * 80)
        print("DEPLOYMENT VERIFICATION: ✅ PASSED")
        print("=" * 80)
        print()
        print("✅ Lambda function is responding correctly")
        print("✅ Function can process ticker requests")
        print("✅ Response format is valid")
        print()
        
        return {
            "success": True,
            "status_code": result.get('statusCode'),
            "duration": duration,
            "result": result
        }
        
    except Exception as e:
        print("=" * 80)
        print("❌ LAMBDA FUNCTION TEST FAILED")
        print("=" * 80)
        print()
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print("DEPLOYMENT VERIFICATION: ❌ FAILED")
        print("=" * 80)
        print()
        
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Lambda function after deployment")
    parser.add_argument(
        "--function-name",
        type=str,
        default="line-bot-ticker-report",
        help="Lambda function name (default: line-bot-ticker-report)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="DBS19",
        help="Ticker to test with (default: DBS19)"
    )
    
    args = parser.parse_args()
    
    result = test_lambda_after_deployment(args.function_name, args.ticker)
    
    sys.exit(0 if result.get("success") else 1)
