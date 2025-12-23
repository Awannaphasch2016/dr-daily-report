#!/bin/bash
# Test Lambda handler imports inside Docker container
#
# Purpose: Catch import/dependency errors BEFORE deploying to AWS
# Runtime: ~30-60 seconds (Docker build + import tests)
#
# This tests:
# - All Python dependencies are installed
# - System libraries are available
# - Module paths are correct
# - Handlers can be imported without errors
#
# Usage:
#   ./scripts/test_docker_imports.sh
#   ./scripts/test_docker_imports.sh --rebuild  # Force rebuild image

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="dr-lambda-import-test"
DOCKERFILE="lambda.Dockerfile"

echo "======================================================"
echo "Docker Import Test - Lambda Handlers"
echo "======================================================"
echo ""

# Parse arguments
REBUILD=false
if [[ "$1" == "--rebuild" ]]; then
    REBUILD=true
    echo "ℹ️  Rebuild requested - will force Docker build"
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Step 1: Build Docker image (unless already exists and not rebuilding)
echo "Step 1: Building Lambda Docker image..."
echo "----------------------------------------"

if docker image inspect $IMAGE_NAME >/dev/null 2>&1 && [ "$REBUILD" = false ]; then
    echo -e "${GREEN}✓ Using existing image: $IMAGE_NAME${NC}"
else
    echo "Building Docker image from $DOCKERFILE..."

    if docker build -t $IMAGE_NAME -f $DOCKERFILE . ; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    fi
fi

echo ""

# Step 2: Test imports for each handler
echo "Step 2: Testing handler imports..."
echo "----------------------------------------"

test_import() {
    local handler_module=$1
    local handler_name=$2

    echo -n "Testing: $handler_name... "

    # Run import test inside container
    if docker run --rm $IMAGE_NAME python3 -c "
import sys
try:
    # Test import
    from $handler_module import lambda_handler
    print('✓ Import successful', file=sys.stderr)

    # Verify handler is callable
    if not callable(lambda_handler):
        print('❌ lambda_handler is not callable', file=sys.stderr)
        sys.exit(1)

    # Success
    sys.exit(0)
except ImportError as e:
    print(f'❌ Import failed: {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Track failures
FAILED_TESTS=()

# Test each handler
test_import "src.scheduler.get_ticker_list_handler" "get_ticker_list_handler" || FAILED_TESTS+=("get_ticker_list_handler")
test_import "src.scheduler.ticker_fetcher_handler" "ticker_fetcher_handler" || FAILED_TESTS+=("ticker_fetcher_handler")

echo ""

# Step 3: Test critical dependencies
echo "Step 3: Testing critical dependencies..."
echo "----------------------------------------"

test_dependency() {
    local package=$1
    local import_name=$2

    echo -n "Testing: $package... "

    if docker run --rm $IMAGE_NAME python3 -c "import $import_name" 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Test critical dependencies
test_dependency "pymysql" "pymysql" || FAILED_TESTS+=("pymysql")
test_dependency "boto3" "boto3" || FAILED_TESTS+=("boto3")
test_dependency "yfinance" "yfinance" || FAILED_TESTS+=("yfinance")

echo ""

# Step 4: Summary
echo "======================================================"
echo "Summary"
echo "======================================================"

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All import tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run local execution tests: ./scripts/test_docker_local.sh"
    echo "  2. Deploy to AWS: just deploy-dev"
    exit 0
else
    echo -e "${RED}❌ ${#FAILED_TESTS[@]} import test(s) failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - $test"
    done
    echo ""
    echo "Fix these issues before deploying to AWS:"
    echo "  1. Check requirements.txt for missing dependencies"
    echo "  2. Verify module paths are correct"
    echo "  3. Check lambda.Dockerfile for system library dependencies"
    exit 1
fi
