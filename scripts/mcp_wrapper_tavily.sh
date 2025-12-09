#!/bin/bash
# Wrapper script for Tavily MCP Server with Doppler environment variables
# Uses rag-chatbot-worktree/dev_personal config for TAVILY_API_KEY

# Don't exit on error - let MCP server handle its own errors
set +e

# Export Doppler secrets as environment variables from rag-chatbot-worktree/dev_personal
eval "$(doppler run --project rag-chatbot-worktree --config dev_personal -- printenv | grep -E '^(TAVILY_|DOPPLER_)' | sed 's/^/export /')"

# Run the MCP server directly
# Redirect stderr to /dev/null to suppress Pydantic deprecation warnings
# These warnings don't affect functionality but cause validation scripts to fail
exec uvx tavily-mcp-server@latest "$@" 2>/dev/null
