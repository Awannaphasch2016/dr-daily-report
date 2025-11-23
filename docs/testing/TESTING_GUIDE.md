# LINE Bot Lambda Function Testing Guide

This guide provides step-by-step instructions to test the `line-bot-ticker-report` Lambda function locally and remotely.

## Prerequisites

1. **Environment Variables** - Ensure these are set:
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export LINE_CHANNEL_ACCESS_TOKEN="your-line-access-token"
   export LINE_CHANNEL_SECRET="your-line-secret"
   ```

2. **Python Dependencies** - Install minimal requirements:
   ```bash
   pip install -r requirements_minimal.txt
   ```

3. **AWS CLI** - For remote testing (optional):
   ```bash
   aws --version  # Should be configured with credentials
   ```

---

## Step 1: Verify Environment Setup

### 1.1 Check Environment Variables

```bash
cd /home/anak/dev/dr-daily-report

# Check if environment variables are set
python3 << 'EOF'
import os
required_vars = [
    'OPENAI_API_KEY',
    'LINE_CHANNEL_ACCESS_TOKEN', 
    'LINE_CHANNEL_SECRET'
]

print("=" * 60)
print("Environment Variables Check")
print("=" * 60)

all_set = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Show first 10 chars for security
        print(f"✅ {var}: {value[:10]}...")
    else:
        print(f"❌ {var}: NOT SET")
        all_set = False

if all_set:
    print("\n✅ All environment variables are set!")
else:
    print("\n❌ Missing environment variables. Please set them before testing.")
EOF
```

### 1.2 Verify Dependencies

```bash
# Check if key packages are installed
python3 -c "
import sys
packages = ['yfinance', 'langchain', 'pandas', 'requests']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        print(f'❌ {pkg} - MISSING')
        missing.append(pkg)

if missing:
    print(f'\n❌ Missing packages: {missing}')
    print('Run: pip install -r requirements_minimal.txt')
    sys.exit(1)
else:
    print('\n✅ All required packages installed')
"
```

---

## Step 2: Test Lambda Handler Directly (Local)

### 2.1 Test Handler Function

Create a simple test script:

```bash
cat > test_lambda_handler.py << 'EOF'
#!/usr/bin/env python3
"""Test Lambda handler directly"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lambda_handler import lambda_handler

def test_lambda_handler():
    """Test the Lambda handler with a mock event"""
    
    print("=" * 80)
    print("🧪 Testing Lambda Handler Locally")
    print("=" * 80)
    print()
    
    # Create mock Lambda event (simulating API Gateway / Function URL)
    test_event = {
        "body": json.dumps({
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token_12345",
                    "source": {
                        "userId": "test_user_123",
                        "type": "user"
                    },
                    "timestamp": 1462629479859,
                    "message": {
                        "type": "text",
                        "id": "325708",
                        "text": "DBS19"  # Test ticker
                    }
                }
            ]
        }),
        "headers": {
            "x-line-signature": "test_signature"  # Will skip verification
        }
    }
    
    # Mock context (not used but required)
    class MockContext:
        def __init__(self):
            self.function_name = "line-bot-ticker-report"
            self.function_version = "$LATEST"
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:line-bot-ticker-report"
    
    context = MockContext()
    
    print("📨 Test Event:")
    print(json.dumps(test_event, indent=2))
    print()
    print("🤖 Processing...")
    print()
    
    try:
        # Call Lambda handler
        result = lambda_handler(test_event, context)
        
        print("=" * 80)
        print("✅ Handler Response:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()
        
        # Check result
        if result.get('statusCode') == 200:
            print("✅ Test PASSED - Handler returned 200 OK")
        else:
            print(f"⚠️  Handler returned status code: {result.get('statusCode')}")
            
    except Exception as e:
        print("=" * 80)
        print("❌ Test FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_lambda_handler()
    sys.exit(0 if success else 1)
EOF

chmod +x test_lambda_handler.py
python3 test_lambda_handler.py
```

**Expected Output:**
- Handler should return `{"statusCode": 200, "body": "..."}`
- No exceptions should be raised
- Bot should process the ticker "DBS19"

---

## Step 3: Test LINE Bot Integration (Mocked Replies)

### 3.1 Run Integration Test

```bash
cd /home/anak/dev/dr-daily-report

# Test with default ticker (DBS19)
python3 tests/test_line_integration.py

# Test with custom ticker
python3 tests/test_line_integration.py PFIZER19
```

**What this does:**
- Creates a mock LINE webhook event
- Mocks the `reply_message` function (doesn't actually send to LINE)
- Shows what message would be sent to the user
- Verifies the bot processes the request correctly

**Expected Output:**
- Bot processes the ticker
- Mock reply shows the analysis message
- Status code 200 returned

---

## Step 4: Test with Local Flask Server

### 4.1 Start Local Test Server

```bash
cd /home/anak/dev/dr-daily-report

# Start Flask test server
python3 tests/test_line_local.py
```

The server will start on `http://0.0.0.0:5000`

### 4.2 Test Endpoints

**Test 1: Health Check**
```bash
curl http://localhost:5000/health
```

**Test 2: Test Endpoint (with ticker)**
```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{"ticker": "DBS19"}'
```

**Test 3: Simulate LINE Webhook**
```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: test_signature" \
  -d '{
    "events": [{
      "type": "message",
      "replyToken": "test_token",
      "message": {
        "type": "text",
        "text": "DBS19"
      }
    }]
  }'
```

**Expected Results:**
- Health check returns `{"status": "healthy"}`
- Test endpoint processes ticker and returns result
- Webhook endpoint returns 200 status

---

## Step 5: Test Lambda Handler with Real Event Format

### 5.1 Create Test Script for Function URL Format

```bash
cat > test_lambda_function_url.py << 'EOF'
#!/usr/bin/env python3
"""Test Lambda handler with Function URL event format"""

import json
import os
import sys
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lambda_handler import lambda_handler

def test_function_url_event():
    """Test with Lambda Function URL event format"""
    
    print("=" * 80)
    print("🧪 Testing Lambda Handler (Function URL Event Format)")
    print("=" * 80)
    print()
    
    # Lambda Function URL event format
    line_event = {
        "events": [
            {
                "type": "message",
                "replyToken": "test_reply_token_12345",
                "source": {
                    "userId": "test_user_123",
                    "type": "user"
                },
                "timestamp": 1462629479859,
                "message": {
                    "type": "text",
                    "id": "325708",
                    "text": "DBS19"
                }
            }
        ]
    }
    
    # Function URL passes body as base64 encoded string
    body_json = json.dumps(line_event)
    body_base64 = base64.b64encode(body_json.encode('utf-8')).decode('utf-8')
    
    test_event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "x-line-signature": "test_signature",
            "content-type": "application/json"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api-id",
            "domainName": "test.lambda-url.ap-southeast-1.on.aws",
            "domainPrefix": "test",
            "http": {
                "method": "POST",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-agent"
            },
            "requestId": "test-request-id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "09/Nov/2025:12:00:00 +0000",
            "timeEpoch": 1731153600000
        },
        "body": body_json,  # Function URL may pass as plain JSON or base64
        "isBase64Encoded": False
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "line-bot-ticker-report"
            self.function_version = "$LATEST"
            self.memory_limit_in_mb = 512
    
    context = MockContext()
    
    print("📨 Function URL Event:")
    print(json.dumps(test_event, indent=2))
    print()
    print("🤖 Processing...")
    print()
    
    try:
        result = lambda_handler(test_event, context)
        
        print("=" * 80)
        print("✅ Handler Response:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()
        
        if result.get('statusCode') == 200:
            print("✅ Test PASSED")
        else:
            print(f"⚠️  Status: {result.get('statusCode')}")
            
    except Exception as e:
        print("=" * 80)
        print("❌ Test FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_function_url_event()
    sys.exit(0 if success else 1)
EOF

chmod +x test_lambda_function_url.py
python3 test_lambda_function_url.py
```

---

## Step 6: Remote Testing - Invoke Lambda Function

### 6.1 Test Lambda Function Directly

```bash
# Create a test payload file
cat > test_payload.json << 'EOF'
{
  "body": "{\"events\":[{\"type\":\"message\",\"replyToken\":\"test_token\",\"source\":{\"userId\":\"test_user\"},\"message\":{\"type\":\"text\",\"text\":\"DBS19\"}}]}",
  "headers": {
    "x-line-signature": "test_signature"
  }
}
EOF

# Invoke Lambda function
aws lambda invoke \
  --function-name line-bot-ticker-report \
  --region ap-southeast-1 \
  --payload file://test_payload.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json | jq .
```

### 6.2 Test Lambda Function URL

```bash
# Get Function URL
FUNCTION_URL=$(aws lambda get-function-url-config \
  --function-name line-bot-ticker-report \
  --region ap-southeast-1 \
  --query 'FunctionUrl' \
  --output text)

echo "Function URL: $FUNCTION_URL"

# Test with curl
curl -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: test_signature" \
  -d '{
    "events": [{
      "type": "message",
      "replyToken": "test_token",
      "source": {"userId": "test_user"},
      "message": {
        "type": "text",
        "text": "DBS19"
      }
    }]
  }'
```

### 6.3 Check CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/line-bot-ticker-report \
  --region ap-southeast-1 \
  --follow \
  --format short

# Or get last 50 log entries
aws logs tail /aws/lambda/line-bot-ticker-report \
  --region ap-southeast-1 \
  --since 1h \
  --format short
```

---

## Step 7: Test with Real LINE Webhook (Production Test)

### 7.1 Update LINE Console Webhook URL

1. Go to [LINE Developers Console](https://developers.line.biz/console/)
2. Select your channel
3. Go to "Messaging API" tab
4. Set Webhook URL to your Function URL:
   ```
   https://vlrlxykbzbb5pj4aogbnudfxi40sgyxk.lambda-url.ap-southeast-1.on.aws/
   ```
5. Enable "Webhook" toggle
6. Verify webhook (if available)

### 7.2 Send Test Message from LINE App

1. Open LINE app on your phone
2. Add your LINE bot as a friend
3. Send a message: `DBS19`
4. Wait for response

### 7.3 Monitor Logs in Real-Time

```bash
# Watch logs in real-time
aws logs tail /aws/lambda/line-bot-ticker-report \
  --region ap-southeast-1 \
  --follow \
  --format short
```

---

## Troubleshooting

### Issue: Environment Variables Not Set

**Solution:**
```bash
# Check if set
env | grep -E "(OPENAI|LINE)"

# Set them
export OPENAI_API_KEY="your-key"
export LINE_CHANNEL_ACCESS_TOKEN="your-token"
export LINE_CHANNEL_SECRET="your-secret"
```

### Issue: Import Errors

**Solution:**
```bash
# Ensure you're in the project root
cd /home/anak/dev/dr-daily-report

# Install dependencies
pip install -r requirements_minimal.txt

# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"
```

### Issue: Lambda Function Not Found

**Solution:**
```bash
# List functions
aws lambda list-functions --region ap-southeast-1 | grep line-bot

# Check if function exists
aws lambda get-function \
  --function-name line-bot-ticker-report \
  --region ap-southeast-1
```

### Issue: Function URL Not Working

**Solution:**
```bash
# Get Function URL config
aws lambda get-function-url-config \
  --function-name line-bot-ticker-report \
  --region ap-southeast-1

# Check if URL is accessible
curl -I https://vlrlxykbzbb5pj4aogbnudfxi40sgyxk.lambda-url.ap-southeast-1.on.aws/
```

---

## Quick Test Checklist

- [ ] Step 1: Environment variables set
- [ ] Step 2: Lambda handler test passes locally
- [ ] Step 3: Integration test passes (mocked)
- [ ] Step 4: Flask server test passes
- [ ] Step 5: Function URL event format test passes
- [ ] Step 6: Remote Lambda invocation works
- [ ] Step 7: Real LINE webhook test works

---

## Summary

1. **Local Testing**: Use Steps 1-5 to test without deploying
2. **Remote Testing**: Use Step 6 to test the deployed Lambda
3. **Production Testing**: Use Step 7 to test with real LINE messages

All tests should return status code 200 and process ticker requests correctly.
