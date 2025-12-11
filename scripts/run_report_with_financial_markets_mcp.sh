#!/bin/bash
# Run report generation with Financial Markets MCP server

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

TICKER="${1:-NVDA19}"
STRATEGY="${2:-single-stage}"
MCP_PORT="${FINANCIAL_MARKETS_MCP_PORT:-8003}"
MCP_URL="http://localhost:${MCP_PORT}"

echo "=========================================="
echo "📊 Report Generation with Financial Markets MCP"
echo "=========================================="
echo "Ticker: $TICKER"
echo "Strategy: $STRATEGY"
echo "MCP URL: $MCP_URL"
echo "=========================================="
echo ""

# Check if MCP server is running
echo "🔍 Checking Financial Markets MCP server..."
if curl -s "${MCP_URL}/health" > /dev/null 2>&1; then
    echo "✅ Financial Markets MCP server is running"
else
    echo "⚠️  Financial Markets MCP server not running at $MCP_URL"
    echo "   Starting local Financial Markets MCP server..."
    nohup python3 "${PROJECT_ROOT}/scripts/run_financial_markets_mcp_local.py" --port ${MCP_PORT} > /tmp/financial_markets_mcp.log 2>&1 &
    MCP_PID=$!
    echo "   Waiting for server to start (PID: $MCP_PID)..."
    sleep 5  # Increased wait time
    for i in {1..5}; do
        if curl -s "${MCP_URL}/health" > /dev/null 2>&1; then
            echo "✅ Financial Markets MCP server started (PID: $MCP_PID)"
            break
        fi
        if [ $i -eq 5 ]; then
            echo "❌ Failed to start Financial Markets MCP server after 5 attempts"
            echo "   Check /tmp/financial_markets_mcp.log:"
            tail -20 /tmp/financial_markets_mcp.log
            exit 1
        fi
        sleep 2
    done
fi

# Set MCP URL
export FINANCIAL_MARKETS_MCP_URL="$MCP_URL"
echo "✅ Set FINANCIAL_MARKETS_MCP_URL=$MCP_URL"
echo ""

# Check for OPENROUTER_API_KEY
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "⚠️  OPENROUTER_API_KEY not set"
    echo ""
    echo "Please set it:"
    echo "  export OPENROUTER_API_KEY='your-key-here'"
    echo ""
    echo "Or use Doppler:"
    echo "  ENV=dev doppler run -- $0 $TICKER $STRATEGY"
    exit 1
fi

echo "📝 Generating report..."
echo ""

# Run report generation
PYTHONPATH="${PYTHONPATH:-}:$PROJECT_ROOT" python3 scripts/generate_report_output.py "$TICKER" --strategy "$STRATEGY"

echo ""
echo "=========================================="
echo "✅ Report generation complete!"
echo "=========================================="
echo ""
echo "💡 To stop the MCP server:"
echo "   kill $MCP_PID 2>/dev/null || pkill -f 'run_financial_markets_mcp_local.py'"
