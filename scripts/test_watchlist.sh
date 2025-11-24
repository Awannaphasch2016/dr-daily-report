#!/bin/bash
#
# Test watchlist endpoints
#
# Prerequisites:
#   - DynamoDB Local running (docker run -p 8000:8000 amazon/dynamodb-local)
#   - Tables created (python scripts/create_local_dynamodb_tables.py)
#   - API server running with USE_LOCAL_DYNAMODB=true
#

set -e

API_URL="http://localhost:8001"
USER_ID="test_user_123456"

echo "🧪 Testing Watchlist Endpoints"
echo "================================"
echo "API URL: $API_URL"
echo "User ID: $USER_ID"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Get empty watchlist
echo -e "${BLUE}Test 1: Get empty watchlist${NC}"
echo "GET /api/v1/watchlist"
RESPONSE=$(curl -s "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

# Test 2: Add ticker (NVDA19)
echo -e "${BLUE}Test 2: Add NVDA19 to watchlist${NC}"
echo "POST /api/v1/watchlist"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA19"}')
echo "Response: $RESPONSE"
echo ""

# Test 3: Get watchlist (should have NVDA19)
echo -e "${BLUE}Test 3: Get watchlist (should have NVDA19)${NC}"
RESPONSE=$(curl -s "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

# Test 4: Add more tickers
echo -e "${BLUE}Test 4: Add DBS19 to watchlist${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "DBS19"}')
echo "Response: $RESPONSE"
echo ""

echo -e "${BLUE}Test 5: Add JPMUS19 to watchlist${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "JPMUS19"}')
echo "Response: $RESPONSE"
echo ""

# Test 6: Get full watchlist
echo -e "${BLUE}Test 6: Get full watchlist (should have 3 tickers)${NC}"
RESPONSE=$(curl -s "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

# Test 7: Try to add invalid ticker
echo -e "${BLUE}Test 7: Try to add invalid ticker (should fail)${NC}"
echo "POST /api/v1/watchlist with INVALID ticker"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "INVALID"}')
echo "Response: $RESPONSE"
echo ""

# Test 8: Remove ticker
echo -e "${BLUE}Test 8: Remove NVDA19 from watchlist${NC}"
echo "DELETE /api/v1/watchlist/NVDA19"
RESPONSE=$(curl -s -X DELETE "$API_URL/api/v1/watchlist/NVDA19?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

# Test 9: Verify removal
echo -e "${BLUE}Test 9: Get watchlist (should have 2 tickers)${NC}"
RESPONSE=$(curl -s "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

# Test 10: Remove all remaining tickers
echo -e "${BLUE}Test 10: Remove remaining tickers${NC}"
curl -s -X DELETE "$API_URL/api/v1/watchlist/DBS19?X-Telegram-User-Id=$USER_ID" > /dev/null
curl -s -X DELETE "$API_URL/api/v1/watchlist/JPMUS19?X-Telegram-User-Id=$USER_ID" > /dev/null
echo "Removed DBS19 and JPMUS19"
echo ""

# Test 11: Verify empty again
echo -e "${BLUE}Test 11: Get watchlist (should be empty)${NC}"
RESPONSE=$(curl -s "$API_URL/api/v1/watchlist?X-Telegram-User-Id=$USER_ID")
echo "Response: $RESPONSE"
echo ""

echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "To view data in DynamoDB Local:"
echo "  aws dynamodb scan --table-name dr-daily-report-telegram-watchlist-dev --endpoint-url http://localhost:8000"
