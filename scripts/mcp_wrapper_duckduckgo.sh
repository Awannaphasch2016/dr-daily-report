#!/bin/bash
# Wrapper script for DuckDuckGo MCP Server
# No API key required - free search service

set -e

# Run the MCP server directly
exec uvx duckduckgo-mcp-server@latest "$@"
