#!/bin/bash
# -*- coding: utf-8 -*-
#
# Automated Setup and Test Script for SEC EDGAR MCP Server
#
# This script performs a complete setup and validation of the MCP server:
# 1. Tests SEC EDGAR API connectivity
# 2. Starts MCP server with proper environment
# 3. Tests MCP server endpoints
# 4. Optionally runs report generation test
#
# Usage:
#   ./scripts/setup_and_test_mcp.sh [--port PORT] [--skip-report-test]
#
# Environment Variables:
#   SEC_EDGAR_USER_AGENT - User-Agent string for SEC API (required)
#   OPENROUTER_API_KEY   - Required for report generation test
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
PORT="${MCP_SERVER_PORT:-8002}"
SKIP_REPORT_TEST=false
USER_AGENT="${SEC_EDGAR_USER_AGENT:-}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --skip-report-test)
            SKIP_REPORT_TEST=true
            shift
            ;;
        --user-agent)
            USER_AGENT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Automated setup and test script for SEC EDGAR MCP server."
            echo ""
            echo "Options:"
            echo "  --port PORT           Port to run server on (default: 8002)"
            echo "  --user-agent STRING   User-Agent string for SEC API"
            echo "  --skip-report-test    Skip report generation test"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  SEC_EDGAR_USER_AGENT - User-Agent string for SEC API"
            echo "  OPENROUTER_API_KEY   - Required for report generation test"
            echo ""
            echo "Examples:"
            echo "  # Full test suite"
            echo "  export SEC_EDGAR_USER_AGENT='DR-Daily-Report-ResearchBot (anak@yourcompany.com)'"
            echo "  export OPENROUTER_API_KEY='your-key'"
            echo "  ./scripts/setup_and_test_mcp.sh"
            echo ""
            echo "  # Skip report generation (faster)"
            echo "  ./scripts/setup_and_test_mcp.sh --skip-report-test"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set USER_AGENT from environment if not provided
if [[ -z "$USER_AGENT" ]]; then
    USER_AGENT="${SEC_EDGAR_USER_AGENT:-}"
fi

# Check for SEC_EDGAR_USER_AGENT
if [[ -z "$USER_AGENT" ]]; then
    echo -e "${YELLOW}⚠️  SEC_EDGAR_USER_AGENT not set!${NC}"
    echo ""
    echo "SEC EDGAR API requires a User-Agent header. Set it with:"
    echo ""
    echo "  export SEC_EDGAR_USER_AGENT='DR-Daily-Report-ResearchBot (anak@yourcompany.com)'"
    echo ""
    echo "Or pass it via --user-agent flag:"
    echo ""
    echo "  $0 --user-agent 'DR-Daily-Report-ResearchBot (anak@yourcompany.com)'"
    echo ""
    exit 1
fi

export SEC_EDGAR_USER_AGENT="$USER_AGENT"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SEC EDGAR MCP Server Setup and Test${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Test SEC EDGAR API Connectivity
echo -e "${BLUE}Step 1: Testing SEC EDGAR API connectivity...${NC}"
echo ""

SEC_API_URL="https://data.sec.gov/files/company_tickers.json"
echo "Testing: $SEC_API_URL"
echo "User-Agent: $USER_AGENT"
echo ""

HTTP_CODE=$(curl -s -o /tmp/sec_test_response.json -w "%{http_code}" \
    -H "User-Agent: $USER_AGENT" \
    "$SEC_API_URL" || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ SEC API returned 200 OK${NC}"
    echo "Response preview:"
    head -20 /tmp/sec_test_response.json | head -5
    echo "..."
    echo ""
elif [[ "$HTTP_CODE" == "403" ]] || [[ "$HTTP_CODE" == "404" ]]; then
    echo -e "${RED}❌ SEC API returned $HTTP_CODE${NC}"
    echo ""
    echo "This usually means:"
    echo "  1. User-Agent header is missing or invalid"
    echo "  2. SEC is blocking requests (rate limiting or IP ban)"
    echo ""
    echo "Check your User-Agent format:"
    echo "  Format: 'AppName (contact@email.com)' or 'AppName contact@email.com'"
    echo "  Your value: $USER_AGENT"
    echo ""
    exit 1
else
    echo -e "${YELLOW}⚠️  SEC API returned $HTTP_CODE${NC}"
    echo "Response:"
    cat /tmp/sec_test_response.json 2>/dev/null || echo "(no response)"
    echo ""
fi

# Step 2: Start MCP Server
echo -e "${BLUE}Step 2: Starting MCP server...${NC}"
echo ""

# Set PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Start server in background
echo "Starting server on port $PORT..."
python3 scripts/run_mcp_server_local.py --port "$PORT" > /tmp/mcp_server.log 2>&1 &
MCP_SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..10}; do
    if curl -s "http://127.0.0.1:$PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server started successfully${NC}"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo -e "${RED}❌ Server failed to start${NC}"
        echo "Logs:"
        cat /tmp/mcp_server.log
        kill $MCP_SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""

# Step 3: Test MCP Server Endpoints
echo -e "${BLUE}Step 3: Testing MCP server endpoints...${NC}"
echo ""

# Test tools/list
echo "Testing tools/list..."
TOOLS_LIST_RESPONSE=$(curl -s -X POST "http://127.0.0.1:$PORT/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }' || echo '{"error": "request failed"}')

if echo "$TOOLS_LIST_RESPONSE" | grep -q "get_latest_filing"; then
    echo -e "${GREEN}✅ tools/list returned get_latest_filing tool${NC}"
else
    echo -e "${RED}❌ tools/list failed or missing get_latest_filing${NC}"
    echo "Response: $TOOLS_LIST_RESPONSE"
    kill $MCP_SERVER_PID 2>/dev/null || true
    exit 1
fi
echo ""

# Test tools/call
echo "Testing tools/call with NVDA..."
TOOLS_CALL_RESPONSE=$(curl -s -X POST "http://127.0.0.1:$PORT/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_latest_filing",
            "arguments": {
                "ticker": "NVDA",
                "form_type": "10-Q"
            }
        }
    }' || echo '{"error": "request failed"}')

if echo "$TOOLS_CALL_RESPONSE" | grep -q "NVDA\|ticker\|filing_date"; then
    echo -e "${GREEN}✅ tools/call returned SEC filing data for NVDA${NC}"
    echo "Response preview:"
    echo "$TOOLS_CALL_RESPONSE" | head -20
    echo "..."
else
    echo -e "${YELLOW}⚠️  tools/call response may be incomplete${NC}"
    echo "Response: $TOOLS_CALL_RESPONSE"
fi
echo ""

# Step 4: Report Generation Test (optional)
if [[ "$SKIP_REPORT_TEST" == "false" ]]; then
    echo -e "${BLUE}Step 4: Testing report generation with MCP...${NC}"
    echo ""
    
    if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
        echo -e "${YELLOW}⚠️  OPENROUTER_API_KEY not set - skipping report generation test${NC}"
        echo "Set it to test report generation:"
        echo "  export OPENROUTER_API_KEY='your-key'"
        echo ""
    else
        echo "Generating report for NVDA19 (US ticker)..."
        echo ""
        
        export SEC_EDGAR_MCP_URL="http://127.0.0.1:$PORT"
        
        REPORT_OUTPUT=$(python3 scripts/generate_report_output.py NVDA19 --mcp-url "http://127.0.0.1:$PORT" 2>&1 || true)
        
        if echo "$REPORT_OUTPUT" | grep -qi "SEC\|EDGAR\|10-Q\|10-K\|filing"; then
            echo -e "${GREEN}✅ Report contains SEC filing indicators${NC}"
            echo "MCP integration appears to be working!"
        else
            echo -e "${YELLOW}⚠️  No SEC filing indicators found in report${NC}"
            echo "This could mean:"
            echo "  1. MCP server returned no data"
            echo "  2. LLM didn't include SEC info in report"
            echo "  3. MCP server is not configured correctly"
        fi
        echo ""
    fi
else
    echo -e "${BLUE}Step 4: Skipped (--skip-report-test)${NC}"
    echo ""
fi

# Cleanup
echo -e "${BLUE}Cleaning up...${NC}"
kill $MCP_SERVER_PID 2>/dev/null || true
wait $MCP_SERVER_PID 2>/dev/null || true

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup and test complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Start MCP server: ./scripts/start_mcp_server_local.sh --port $PORT"
echo "  2. Generate report: python3 scripts/generate_report_output.py NVDA19 --mcp-url http://127.0.0.1:$PORT"
echo "  3. Run tests: pytest tests/integration/test_mcp_sec_edgar.py -v"
echo ""
