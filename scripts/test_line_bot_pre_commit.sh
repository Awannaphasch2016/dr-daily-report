#!/bin/bash
# Pre-commit validation for LINE bot changes
#
# Purpose: Run all tests locally before committing to catch errors early
# Runtime: ~20-40 seconds (syntax + unit tests + Docker import tests)
#
# This runs:
# 1. Python syntax check (fast - <1s)
# 2. Unit tests (medium - ~5-10s)
# 3. Docker import tests (medium - ~10-30s)
#
# Usage:
#   ./scripts/test_line_bot_pre_commit.sh
#
# Add to git pre-commit hook (optional):
#   ln -s ../../scripts/test_line_bot_pre_commit.sh .git/hooks/pre-commit

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================"
echo "LINE Bot Pre-Commit Validation"
echo "======================================================"
echo ""

# Check we're in project root
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Run this script from project root${NC}"
    exit 1
fi

# Stage 1: Syntax check
echo -e "${BLUE}Stage 1: Python syntax check${NC}"
echo "----------------------------------------"
echo -n "Checking syntax... "

if python -m py_compile src/integrations/line_bot.py src/lambda_handler.py 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo ""
    echo -e "${RED}❌ Syntax errors found${NC}"
    echo "Fix syntax errors before committing"
    exit 1
fi

echo ""

# Stage 2: Unit tests
echo -e "${BLUE}Stage 2: Unit tests${NC}"
echo "----------------------------------------"
echo "Running LINE bot tests..."
echo ""

if pytest tests/line_bot/ -m "not integration and not e2e" -v --tb=short -x; then
    echo ""
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo ""
    echo -e "${RED}❌ Unit tests failed${NC}"
    echo "Fix failing tests before committing"
    exit 1
fi

echo ""

# Stage 3: Docker import tests
echo -e "${BLUE}Stage 3: Docker import validation${NC}"
echo "----------------------------------------"
echo "Testing imports in Lambda Docker container..."
echo ""

if ./scripts/test_line_bot_docker.sh; then
    echo ""
    echo -e "${GREEN}✓ Docker import tests passed${NC}"
else
    echo ""
    echo -e "${RED}❌ Docker import tests failed${NC}"
    echo ""
    echo -e "${RED}⚠️  Import errors detected!${NC}"
    echo "These errors will occur in production Lambda if you deploy now."
    echo ""
    echo "Fix import errors before committing:"
    echo "  1. Check src/integrations/line_bot.py for missing handle_webhook function"
    echo "  2. Check requirements.txt for missing dependencies"
    echo "  3. Run: ./scripts/test_line_bot_docker.sh --rebuild"
    exit 1
fi

echo ""

# Success summary
echo "======================================================"
echo -e "${GREEN}✅ All pre-commit checks passed!${NC}"
echo "======================================================"
echo ""
echo "Summary:"
echo "  ✓ Python syntax valid"
echo "  ✓ Unit tests passed"
echo "  ✓ Docker imports validated (Lambda-ready)"
echo ""
echo -e "${GREEN}🎉 Safe to commit and push!${NC}"
echo ""
echo "Next steps:"
echo "  git add ."
echo "  git commit -m \"your message\""
echo "  git push origin dev  # Triggers CI/CD deployment"
