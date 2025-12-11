#!/bin/bash
# Verify MCP Server Deployment
# Usage: ./scripts/verify_mcp_server.sh [dev|staging|prod] [sec-edgar|all]

set -e

ENV=${1:-dev}
SERVER=${2:-sec-edgar}
PROJECT_NAME="dr-daily-report"
AWS_REGION="ap-southeast-1"

echo "🔍 Verifying MCP server deployment for ${ENV}..."

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [dev|staging|prod] [sec-edgar|all]"
    exit 1
fi

# Get Function URL from Terraform
cd terraform
FUNCTION_URL=$(terraform output -raw sec_edgar_mcp_url 2>/dev/null) || {
    echo "❌ Failed to get SEC EDGAR MCP URL from Terraform"
    echo "Make sure terraform has been applied"
    exit 1
}
cd ..

if [ -z "$FUNCTION_URL" ]; then
    echo "❌ SEC EDGAR MCP URL not found"
    exit 1
fi

echo "📍 Function URL: ${FUNCTION_URL}"
echo ""

# Test tools/list
echo "🧪 Testing tools/list..."
LIST_RESPONSE=$(curl -s -X POST "${FUNCTION_URL}/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }')

if echo "$LIST_RESPONSE" | grep -q '"result"'; then
    echo "✅ tools/list: SUCCESS"
    echo "$LIST_RESPONSE" | jq '.' 2>/dev/null || echo "$LIST_RESPONSE"
else
    echo "❌ tools/list: FAILED"
    echo "$LIST_RESPONSE"
    exit 1
fi

echo ""

# Test tools/call
echo "🧪 Testing tools/call (get_latest_filing for AAPL)..."
CALL_RESPONSE=$(curl -s -X POST "${FUNCTION_URL}/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_latest_filing",
      "arguments": {
        "ticker": "AAPL",
        "form_type": "10-Q"
      }
    },
    "id": 1
  }')

if echo "$CALL_RESPONSE" | grep -q '"result"'; then
    echo "✅ tools/call: SUCCESS"
    echo "$CALL_RESPONSE" | jq '.' 2>/dev/null || echo "$CALL_RESPONSE"
else
    echo "⚠️ tools/call: Response received but may contain errors"
    echo "$CALL_RESPONSE" | jq '.' 2>/dev/null || echo "$CALL_RESPONSE"
    
    # Check for error
    if echo "$CALL_RESPONSE" | grep -q '"error"'; then
        echo ""
        echo "❌ MCP call returned an error"
        exit 1
    fi
fi

echo ""
echo "✅ MCP server verification complete!"
