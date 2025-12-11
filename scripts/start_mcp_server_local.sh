#!/bin/bash
# -*- coding: utf-8 -*-
#
# Start Local MCP Server with Proper Environment Variables
#
# This script starts the MCP server with SEC_EDGAR_USER_AGENT configured.
# SEC EDGAR API requires a User-Agent header identifying the application.
#
# Usage:
#   ./scripts/start_mcp_server_local.sh [--port PORT]
#
# Environment Variables:
#   SEC_EDGAR_USER_AGENT - User-Agent string for SEC API (required)
#   MCP_SERVER_PORT - Port to run server on (default: 8002)
#   PYTHONPATH - Python path (auto-set to project root)
#

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
PORT="${MCP_SERVER_PORT:-8002}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--port PORT]"
            echo ""
            echo "Start local MCP server with SEC_EDGAR_USER_AGENT configured."
            echo ""
            echo "Options:"
            echo "  --port PORT    Port to run server on (default: 8002)"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  SEC_EDGAR_USER_AGENT - User-Agent string for SEC API (required)"
            echo "  MCP_SERVER_PORT      - Port to run server on (default: 8002)"
            echo ""
            echo "Examples:"
            echo "  # Start on default port 8002"
            echo "  export SEC_EDGAR_USER_AGENT='DR-Daily-Report-ResearchBot (anak@yourcompany.com)'"
            echo "  ./scripts/start_mcp_server_local.sh"
            echo ""
            echo "  # Start on custom port"
            echo "  ./scripts/start_mcp_server_local.sh --port 8000"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check for SEC_EDGAR_USER_AGENT
if [[ -z "${SEC_EDGAR_USER_AGENT:-}" ]]; then
    echo "⚠️  SEC_EDGAR_USER_AGENT not set!"
    echo ""
    echo "SEC EDGAR API requires a User-Agent header. Set it with:"
    echo ""
    echo "  export SEC_EDGAR_USER_AGENT='DR-Daily-Report-ResearchBot (anak@yourcompany.com)'"
    echo ""
    echo "Or use the format from Terraform:"
    echo ""
    echo "  export SEC_EDGAR_USER_AGENT='dr-daily-report/1.0 (contact: support@dr-daily-report.com)'"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# Change to project root
cd "$PROJECT_ROOT"

echo "🚀 Starting local MCP server..."
echo "   Port: $PORT"
echo "   MCP endpoint: http://127.0.0.1:$PORT/mcp"
echo "   Health check: http://127.0.0.1:$PORT/health"
if [[ -n "${SEC_EDGAR_USER_AGENT:-}" ]]; then
    echo "   SEC_EDGAR_USER_AGENT: ${SEC_EDGAR_USER_AGENT}"
fi
echo ""
echo "   Set SEC_EDGAR_MCP_URL=http://127.0.0.1:$PORT to use this server"
echo ""

# Start server
python3 scripts/run_mcp_server_local.py --port "$PORT"
