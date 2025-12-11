#!/bin/bash
# Run report generation with MCP validation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check for required environment variables
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "❌ ERROR: OPENROUTER_API_KEY not set"
    echo ""
    echo "Please set it:"
    echo "  export OPENROUTER_API_KEY='your-key-here'"
    echo ""
    echo "Or use Doppler:"
    echo "  ENV=dev doppler run -- python3 scripts/generate_report_output.py DBS19"
    exit 1
fi

TICKER="${1:-DBS19}"
MCP_URL="${SEC_EDGAR_MCP_URL:-http://localhost:8000/mcp}"
STRATEGY="${2:-single-stage}"

echo "=========================================="
echo "📊 Report Generation with MCP Validation"
echo "=========================================="
echo "Ticker: $TICKER"
echo "MCP URL: ${MCP_URL:-Not configured}"
echo "Strategy: $STRATEGY"
echo "=========================================="
echo ""

# Check if MCP server is running (for US tickers)
if [[ ! "$TICKER" =~ (19|\.SI|\.HK|\.T|\.TW)$ ]]; then
    echo "🔍 Checking MCP server..."
    if curl -s "${MCP_URL%/mcp}/health" > /dev/null 2>&1; then
        echo "✅ MCP server is running"
    else
        echo "⚠️  MCP server not running at $MCP_URL"
        echo "   Starting local MCP server..."
        python3 scripts/run_mcp_server_local.py --port 8000 > /tmp/mcp_server.log 2>&1 &
        MCP_PID=$!
        sleep 3
        if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
            echo "✅ MCP server started (PID: $MCP_PID)"
        else
            echo "❌ Failed to start MCP server. Check /tmp/mcp_server.log"
            exit 1
        fi
    fi
    export SEC_EDGAR_MCP_URL="$MCP_URL"
else
    echo "ℹ️  $TICKER is a non-US ticker - MCP will be skipped (expected)"
fi

echo ""
echo "📝 Generating report..."
echo ""

# Run report generation
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python3 scripts/generate_report_output.py "$TICKER" --mcp-url "${SEC_EDGAR_MCP_URL:-}" --strategy "$STRATEGY"

echo ""
echo "=========================================="
echo "✅ Report generation complete!"
echo "=========================================="
