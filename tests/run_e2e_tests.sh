#!/usr/bin/env bash
# Run Playwright E2E tests for Stock Tiles Dashboard

set -e

echo "=========================================="
echo "Running Playwright E2E Tests"
echo "=========================================="
echo ""

# Check if Flask app is running
if ! curl -s http://127.0.0.1:5000/tiles > /dev/null; then
    echo "⚠️  Flask app is not running at http://127.0.0.1:5000"
    echo "Please start the Flask app first:"
    echo "  cd webapp && python app.py"
    echo ""
    exit 1
fi

echo "✅ Flask app is running"
echo ""

# Install Playwright browsers if not already installed
echo "Installing Playwright browsers..."
playwright install chromium || echo "Playwright browsers already installed"
echo ""

# Run tests
echo "Running E2E tests..."
echo ""

# Run with pytest-playwright
pytest tests/test_tiles_e2e.py \
    --browser chromium \
    -v \
    --tb=short \
    "$@"

echo ""
echo "=========================================="
echo "Tests completed!"
echo "=========================================="
