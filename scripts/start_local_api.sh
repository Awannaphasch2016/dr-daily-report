#!/bin/bash
#
# Start FastAPI server with local DynamoDB
#
# Prerequisites:
#   - DynamoDB Local running (docker run -p 8000:8000 amazon/dynamodb-local)
#   - Tables created (python scripts/create_local_dynamodb_tables.py)
#

set -e

echo "🚀 Starting FastAPI with Local DynamoDB"
echo "========================================"
echo ""
echo "Configuration:"
echo "  - USE_LOCAL_DYNAMODB=true"
echo "  - WATCHLIST_TABLE_NAME=dr-daily-report-telegram-watchlist-dev"
echo "  - DynamoDB Local: http://localhost:8000"
echo "  - FastAPI Server: http://localhost:8001"
echo ""

# Set environment variables for local DynamoDB
export USE_LOCAL_DYNAMODB=true
export WATCHLIST_TABLE_NAME=dr-daily-report-telegram-watchlist-dev
export CACHE_TABLE_NAME=dr-daily-report-telegram-cache-dev

# Check if DynamoDB Local is running
if ! nc -z localhost 8000 2>/dev/null; then
    echo "⚠️  Warning: DynamoDB Local doesn't seem to be running on port 8000"
    echo ""
    echo "Start it with:"
    echo "  docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local"
    echo ""
    echo "Or if container already exists:"
    echo "  docker start dynamodb-local"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting server..."
echo ""

# Start API server with Doppler (for other env vars like OPENROUTER_API_KEY)
# Note: Using port 8001 because DynamoDB Local uses 8000
doppler run -- python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001
