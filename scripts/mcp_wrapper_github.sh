#!/bin/bash
# Wrapper script for GitHub MCP Server with Doppler environment variables

set -e

# Export Doppler secrets as environment variables from rag-chatbot-worktree/dev_personal
eval "$(doppler run --project rag-chatbot-worktree --config dev_personal -- printenv | grep -E '^(GITHUB_|GH_|DOPPLER_)' | sed 's/^/export /')"

# Run the MCP server directly
exec npx -y @modelcontextprotocol/server-github "$@"
