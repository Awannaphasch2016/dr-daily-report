#!/bin/bash
#
# Test rankings endpoints
#
# Prerequisites:
#   - API server running with Doppler (./scripts/start_local_api.sh)
#   - Internet connection for yfinance
#
# Note: First request will take ~30-60 seconds to fetch all 47 tickers.
#       Subsequent requests use 5-minute cache and are instant.
#

set -e

API_URL="http://localhost:8001"

echo "🧪 Testing Rankings Endpoints"
echo "=============================="
echo "API URL: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Top Gainers
echo -e "${BLUE}Test 1: Get Top Gainers (limit 5)${NC}"
echo "GET /api/v1/rankings?category=top_gainers&limit=5"
echo "⏳ Fetching... (first request may take 30-60 seconds)"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=top_gainers&limit=5")
echo "$RESPONSE" | jq '.'
echo ""

# Test 2: Top Losers
echo -e "${BLUE}Test 2: Get Top Losers (limit 5)${NC}"
echo "GET /api/v1/rankings?category=top_losers&limit=5"
echo "⚡ Using cache... (should be instant)"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=top_losers&limit=5")
echo "$RESPONSE" | jq '.'
echo ""

# Test 3: Volume Surge
echo -e "${BLUE}Test 3: Get Volume Surge (limit 5)${NC}"
echo "GET /api/v1/rankings?category=volume_surge&limit=5"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=volume_surge&limit=5")
echo "$RESPONSE" | jq '.'
echo ""

# Test 4: Trending
echo -e "${BLUE}Test 4: Get Trending (limit 5)${NC}"
echo "GET /api/v1/rankings?category=trending&limit=5"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=trending&limit=5")
echo "$RESPONSE" | jq '.'
echo ""

# Test 5: Different limit
echo -e "${BLUE}Test 5: Get Top Gainers (limit 3)${NC}"
echo "GET /api/v1/rankings?category=top_gainers&limit=3"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=top_gainers&limit=3")
echo "$RESPONSE" | jq '.'
RESULT_COUNT=$(echo "$RESPONSE" | jq '.results | length')
echo "Result count: $RESULT_COUNT"
if [ "$RESULT_COUNT" -eq 3 ]; then
    echo -e "${GREEN}✅ Limit parameter works correctly${NC}"
else
    echo -e "${RED}❌ Expected 3 results, got $RESULT_COUNT${NC}"
fi
echo ""

# Test 6: Maximum limit
echo -e "${BLUE}Test 6: Get Top Gainers (max limit 50)${NC}"
echo "GET /api/v1/rankings?category=top_gainers&limit=50"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=top_gainers&limit=50")
RESULT_COUNT=$(echo "$RESPONSE" | jq '.results | length')
echo "Result count: $RESULT_COUNT"
echo ""

# Test 7: Invalid category (should fail)
echo -e "${BLUE}Test 7: Invalid category (should fail with 422)${NC}"
echo "GET /api/v1/rankings?category=invalid&limit=5"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/rankings?category=invalid&limit=5")
if [ "$HTTP_CODE" -eq 422 ]; then
    echo -e "${GREEN}✅ Correctly rejected invalid category (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Expected HTTP 422, got $HTTP_CODE${NC}"
fi
echo ""

# Test 8: Missing category (should fail)
echo -e "${BLUE}Test 8: Missing category parameter (should fail with 422)${NC}"
echo "GET /api/v1/rankings?limit=5"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/rankings?limit=5")
if [ "$HTTP_CODE" -eq 422 ]; then
    echo -e "${GREEN}✅ Correctly rejected missing category (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Expected HTTP 422, got $HTTP_CODE${NC}"
fi
echo ""

# Test 9: Invalid limit (should fail)
echo -e "${BLUE}Test 9: Invalid limit (should fail with 422)${NC}"
echo "GET /api/v1/rankings?category=top_gainers&limit=100"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/rankings?category=top_gainers&limit=100")
if [ "$HTTP_CODE" -eq 422 ]; then
    echo -e "${GREEN}✅ Correctly rejected limit > 50 (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Expected HTTP 422, got $HTTP_CODE${NC}"
fi
echo ""

# Test 10: Verify response format
echo -e "${BLUE}Test 10: Verify response format${NC}"
RESPONSE=$(curl -s "$API_URL/api/v1/rankings?category=top_gainers&limit=3")

# Check category field
CATEGORY=$(echo "$RESPONSE" | jq -r '.category')
if [ "$CATEGORY" == "top_gainers" ]; then
    echo -e "${GREEN}✅ Category field correct${NC}"
else
    echo -e "${RED}❌ Category field incorrect: $CATEGORY${NC}"
fi

# Check results is array
RESULTS_TYPE=$(echo "$RESPONSE" | jq -r '.results | type')
if [ "$RESULTS_TYPE" == "array" ]; then
    echo -e "${GREEN}✅ Results is array${NC}"
else
    echo -e "${RED}❌ Results should be array, got: $RESULTS_TYPE${NC}"
fi

# Check first result has required fields
FIRST_TICKER=$(echo "$RESPONSE" | jq -r '.results[0].ticker')
FIRST_COMPANY=$(echo "$RESPONSE" | jq -r '.results[0].company_name')
FIRST_PRICE=$(echo "$RESPONSE" | jq -r '.results[0].price')
FIRST_CHANGE=$(echo "$RESPONSE" | jq -r '.results[0].price_change_pct')
FIRST_VOLUME=$(echo "$RESPONSE" | jq -r '.results[0].volume_ratio')

if [ -n "$FIRST_TICKER" ] && [ "$FIRST_TICKER" != "null" ]; then
    echo -e "${GREEN}✅ Ticker field present: $FIRST_TICKER${NC}"
else
    echo -e "${RED}❌ Ticker field missing${NC}"
fi

if [ -n "$FIRST_COMPANY" ] && [ "$FIRST_COMPANY" != "null" ]; then
    echo -e "${GREEN}✅ Company name present: $FIRST_COMPANY${NC}"
else
    echo -e "${RED}❌ Company name missing${NC}"
fi

if [ -n "$FIRST_PRICE" ] && [ "$FIRST_PRICE" != "null" ]; then
    echo -e "${GREEN}✅ Price present: $FIRST_PRICE${NC}"
else
    echo -e "${RED}❌ Price missing${NC}"
fi

if [ -n "$FIRST_CHANGE" ] && [ "$FIRST_CHANGE" != "null" ]; then
    echo -e "${GREEN}✅ Price change % present: $FIRST_CHANGE${NC}"
else
    echo -e "${RED}❌ Price change % missing${NC}"
fi

if [ -n "$FIRST_VOLUME" ] && [ "$FIRST_VOLUME" != "null" ]; then
    echo -e "${GREEN}✅ Volume ratio present: $FIRST_VOLUME${NC}"
else
    echo -e "${RED}❌ Volume ratio missing${NC}"
fi

echo ""
echo -e "${GREEN}✅ All rankings tests completed!${NC}"
echo ""
echo "📝 Notes:"
echo "  - First request fetches all 47 tickers (30-60 seconds)"
echo "  - Cache lasts 5 minutes"
echo "  - Rankings are calculated from live market data"
echo "  - All categories are calculated from the same data fetch"
