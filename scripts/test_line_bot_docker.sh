#!/bin/bash
# Test LINE bot imports and execution inside Docker container
#
# Purpose: Catch import/dependency errors BEFORE deploying to AWS
# Context: Prevent production import errors like "cannot import handle_webhook"
# Runtime: ~10-30 seconds (Docker build + import tests)
#
# This tests:
# - LINE bot module imports work in Lambda Python 3.11 container
# - lambda_handler exists and is callable
# - handle_webhook module-level function exists (critical for LINE bot)
# - All dependencies are installed
# - Module paths are correct
#
# Usage:
#   ./scripts/test_line_bot_docker.sh
#   ./scripts/test_line_bot_docker.sh --rebuild  # Force rebuild image

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="dr-line-bot-test"
DOCKERFILE="Dockerfile"

echo "======================================================"
echo "Docker Import Test - LINE Bot Lambda Handler"
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

# Step 1: Build Docker image (same as production)
echo "Step 1: Building LINE bot Docker image..."
echo "----------------------------------------"

if docker image inspect $IMAGE_NAME >/dev/null 2>&1 && [ "$REBUILD" = false ]; then
    echo -e "${GREEN}✓ Using existing image: $IMAGE_NAME${NC}"
else
    echo "Building Docker image from $DOCKERFILE (same as production)..."

    if docker build -t $IMAGE_NAME -f $DOCKERFILE . ; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    fi
fi

echo ""

# Step 2: Test LINE bot handler imports
echo "Step 2: Testing LINE bot handler imports..."
echo "----------------------------------------"

test_import() {
    local import_statement=$1
    local description=$2

    echo -n "Testing: $description... "

    # Run import test inside container (override Lambda entrypoint to use Python directly)
    if docker run --rm --entrypoint python3 $IMAGE_NAME -c "
import sys
try:
    # Test import
    $import_statement
    print('✓ Import successful', file=sys.stderr)
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

# Critical imports that must work (these failed in production on Dec 21, 2025)
echo -e "${BLUE}Critical imports (production failures):${NC}"
test_import "from src.integrations.line_bot import handle_webhook" "handle_webhook function" || FAILED_TESTS+=("handle_webhook")
test_import "from src.lambda_handler import lambda_handler" "lambda_handler function" || FAILED_TESTS+=("lambda_handler")

echo ""

# Additional LINE bot imports
echo -e "${BLUE}LINE bot class imports:${NC}"
test_import "from src.integrations.line_bot import LineBot" "LineBot class" || FAILED_TESTS+=("LineBot")

echo ""

# Step 3: Test critical dependencies
echo "Step 3: Testing critical dependencies..."
echo "----------------------------------------"

test_dependency() {
    local package=$1
    local import_name=$2

    echo -n "Testing: $package... "

    if docker run --rm --entrypoint python3 $IMAGE_NAME -c "import $import_name" 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Test critical LINE bot dependencies (no line-bot-sdk - using direct REST API)
test_dependency "pymysql" "pymysql" || FAILED_TESTS+=("pymysql")
test_dependency "boto3" "boto3" || FAILED_TESTS+=("boto3")

echo ""

# Step 4: Verify handler callability
echo "Step 4: Verifying handler callability..."
echo "----------------------------------------"

echo -n "Testing: lambda_handler is callable... "

CALLABLE_TEST=$(docker run --rm --entrypoint python3 $IMAGE_NAME -c "
from src.lambda_handler import lambda_handler
import inspect

# Verify it's callable
if not callable(lambda_handler):
    print('❌ lambda_handler is not callable')
    exit(1)

# Verify signature (should accept event, context)
sig = inspect.signature(lambda_handler)
params = list(sig.parameters.keys())

if len(params) < 2:
    print(f'❌ lambda_handler has wrong signature: {params}')
    exit(1)

print('✓ lambda_handler is callable with correct signature')
" 2>&1)

if echo "$CALLABLE_TEST" | grep -q "✓"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED_TESTS+=("lambda_handler_callable")
fi

echo ""

echo -n "Testing: handle_webhook is callable... "

HANDLE_WEBHOOK_TEST=$(docker run --rm --entrypoint python3 $IMAGE_NAME -c "
from src.integrations.line_bot import handle_webhook
import inspect

# Verify it's callable
if not callable(handle_webhook):
    print('❌ handle_webhook is not callable')
    exit(1)

# Verify signature (should accept event)
sig = inspect.signature(handle_webhook)
params = list(sig.parameters.keys())

if len(params) < 1:
    print(f'❌ handle_webhook has wrong signature: {params}')
    exit(1)

print('✓ handle_webhook is callable with correct signature')
" 2>&1)

if echo "$HANDLE_WEBHOOK_TEST" | grep -q "✓"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    FAILED_TESTS+=("handle_webhook_callable")
fi

echo ""

# Step 5: Summary
echo "======================================================"
echo "Summary"
echo "======================================================"

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All LINE bot import tests passed!${NC}"
    echo ""
    echo "✓ handle_webhook function exists and is callable"
    echo "✓ lambda_handler function exists and is callable"
    echo "✓ All dependencies installed correctly"
    echo "✓ Import paths are correct"
    echo ""
    echo -e "${GREEN}🎉 LINE bot Lambda is ready to deploy!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run unit tests: pytest tests/line_bot/ -v"
    echo "  2. Deploy to dev: git push origin dev (triggers CI/CD)"
    exit 0
else
    echo -e "${RED}❌ ${#FAILED_TESTS[@]} import test(s) failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - $test"
    done
    echo ""
    echo -e "${RED}⚠️  DO NOT DEPLOY - These failures will cause production errors!${NC}"
    echo ""
    echo "Fix these issues before deploying:"
    echo "  1. Check that handle_webhook function exists in src/integrations/line_bot.py"
    echo "  2. Check requirements.txt for missing dependencies"
    echo "  3. Verify module paths are correct"
    echo "  4. Run: ./scripts/test_line_bot_docker.sh --rebuild"
    exit 1
fi
