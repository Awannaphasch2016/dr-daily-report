#!/bin/bash
# Test Lambda handler execution inside Docker container
#
# Purpose: Verify handlers execute correctly with mocked AWS services
# Runtime: ~1-2 minutes (Docker run + handler execution)
#
# This tests:
# - Handler logic executes without errors
# - Environment variables are handled correctly
# - Response format matches Lambda contract
# - Error handling works as expected
#
# Usage:
#   ./scripts/test_docker_local.sh
#   ./scripts/test_docker_local.sh --verbose  # Show detailed output

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
IMAGE_NAME="dr-lambda-import-test"
VERBOSE=false

echo "======================================================"
echo "Docker Local Execution Test - Lambda Handlers"
echo "======================================================"
echo ""

# Parse arguments
if [[ "$1" == "--verbose" ]]; then
    VERBOSE=true
fi

# Check Docker
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Check image exists
if ! docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker image not found. Building...${NC}"
    ./scripts/test_docker_imports.sh --rebuild
fi

echo ""

# Test get_ticker_list_handler
echo "Test 1: get_ticker_list_handler"
echo "----------------------------------------"

GET_TICKER_TEST=$(cat <<'EOF'
import json
import os
import sys

# Mock environment variables
os.environ['AURORA_HOST'] = 'mock-aurora.cluster.amazonaws.com'
os.environ['AURORA_USERNAME'] = 'test_user'
os.environ['AURORA_PASSWORD'] = 'test_password'
os.environ['AURORA_DATABASE'] = 'ticker_data'
os.environ['AURORA_PORT'] = '3306'

# Mock pymysql
import unittest.mock as mock
sys.modules['pymysql'] = mock.MagicMock()

# Mock database response
mock_cursor = mock.MagicMock()
mock_cursor.fetchall.return_value = [
    ('NVDA19',), ('DBS19',), ('AAPL19',)
]

mock_conn = mock.MagicMock()
mock_conn.cursor.return_value = mock_cursor

# Patch pymysql.connect
with mock.patch('pymysql.connect', return_value=mock_conn):
    # Import after mocking
    from src.scheduler.get_ticker_list_handler import lambda_handler

    # Execute handler
    result = lambda_handler({}, None)

    # Verify result
    assert 'tickers' in result, "Missing 'tickers' field"
    assert 'count' in result, "Missing 'count' field"
    assert result['count'] == 3, f"Expected 3 tickers, got {result['count']}"
    assert 'NVDA19' in result['tickers'], "Missing expected ticker"

    print('✓ Handler executed successfully')
    print(f'✓ Returned {result["count"]} tickers')
EOF
)

if [ "$VERBOSE" = true ]; then
    docker run --rm $IMAGE_NAME python3 -c "$GET_TICKER_TEST"
else
    if docker run --rm $IMAGE_NAME python3 -c "$GET_TICKER_TEST" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS - Handler executed successfully${NC}"
    else
        echo -e "${RED}✗ FAIL - Handler execution failed${NC}"
        exit 1
    fi
fi

echo ""

# Test ticker_fetcher_handler
echo "Test 2: ticker_fetcher_handler"
echo "----------------------------------------"

TICKER_FETCHER_TEST=$(cat <<'EOF'
import json
import os
import sys

# Mock environment variables
os.environ['PDF_BUCKET_NAME'] = 'test-pdf-bucket'
os.environ['DATA_LAKE_BUCKET'] = 'test-data-lake-bucket'

# Mock boto3
import unittest.mock as mock
sys.modules['boto3'] = mock.MagicMock()

# Mock TickerFetcher
mock_results = {
    'success_count': 2,
    'failed_count': 0,
    'total': 2,
    'date': '2025-12-13',
    'success': [
        {'ticker': 'NVDA', 'yahoo_ticker': 'NVDA', 'rows_written': 365},
        {'ticker': 'DBS19', 'yahoo_ticker': 'D05.SI', 'rows_written': 365}
    ],
    'failed': []
}

with mock.patch('src.scheduler.ticker_fetcher.TickerFetcher') as mock_fetcher_class:
    mock_fetcher = mock.MagicMock()
    mock_fetcher.fetch_all_tickers.return_value = mock_results
    mock_fetcher_class.return_value = mock_fetcher

    # Import after mocking
    from src.scheduler.ticker_fetcher_handler import lambda_handler

    # Execute handler
    result = lambda_handler({}, None)

    # Verify result structure
    assert 'statusCode' in result, "Missing statusCode"
    assert 'body' in result, "Missing body"
    assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"

    # Verify body fields
    body = result['body']
    assert 'success_count' in body, "Missing success_count"
    assert 'failed_count' in body, "Missing failed_count"
    assert 'duration_seconds' in body, "Missing duration_seconds"
    assert 'precompute_triggered' in body, "Missing precompute_triggered"

    assert body['success_count'] == 2, f"Expected 2 successes, got {body['success_count']}"

    print('✓ Handler executed successfully')
    print(f'✓ Response format valid (statusCode={result["statusCode"]})')
EOF
)

if [ "$VERBOSE" = true ]; then
    docker run --rm $IMAGE_NAME python3 -c "$TICKER_FETCHER_TEST"
else
    if docker run --rm $IMAGE_NAME python3 -c "$TICKER_FETCHER_TEST" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS - Handler executed successfully${NC}"
    else
        echo -e "${RED}✗ FAIL - Handler execution failed${NC}"
        exit 1
    fi
fi

echo ""

# Test error handling
echo "Test 3: Error handling (missing env vars)"
echo "----------------------------------------"

ERROR_HANDLING_TEST=$(cat <<'EOF'
import sys
import os

# Clear all env vars
for key in list(os.environ.keys()):
    if key.startswith(('AURORA_', 'PDF_', 'DATA_')):
        del os.environ[key]

# Mock pymysql
import unittest.mock as mock
sys.modules['pymysql'] = mock.MagicMock()

from src.scheduler.get_ticker_list_handler import lambda_handler

# Should raise KeyError for missing env vars
try:
    result = lambda_handler({}, None)
    print('✗ Expected KeyError but handler succeeded')
    sys.exit(1)
except KeyError:
    print('✓ Correctly raised KeyError for missing env vars')
    sys.exit(0)
EOF
)

if [ "$VERBOSE" = true ]; then
    docker run --rm $IMAGE_NAME python3 -c "$ERROR_HANDLING_TEST"
else
    if docker run --rm $IMAGE_NAME python3 -c "$ERROR_HANDLING_TEST" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS - Error handling works correctly${NC}"
    else
        echo -e "${RED}✗ FAIL - Error handling test failed${NC}"
        exit 1
    fi
fi

echo ""

# Summary
echo "======================================================"
echo "Summary"
echo "======================================================"
echo -e "${GREEN}✅ All Docker local execution tests passed!${NC}"
echo ""
echo "The Lambda handlers execute correctly inside Docker container."
echo ""
echo "Next steps:"
echo "  1. Run Terraform validation: terraform validate"
echo "  2. Run contract tests: ./scripts/test_contracts.sh"
echo "  3. Deploy to AWS: just deploy-dev"
