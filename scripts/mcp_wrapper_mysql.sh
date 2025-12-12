#!/bin/bash
# Wrapper script for MySQL MCP Server with Doppler environment variables
# Connects to Aurora MySQL cluster for direct schema queries and migrations

set -e

# Export Doppler secrets as environment variables
eval "$(doppler run --config dev -- printenv | grep -E '^(AURORA_|MYSQL_)' | sed 's/^/export /')"

# Map Doppler variables to MySQL MCP expected format
export MYSQL_HOST="${AURORA_HOST}"
export MYSQL_PORT="${AURORA_PORT:-3306}"
export MYSQL_USER="${AURORA_USER}"
export MYSQL_PASSWORD="${AURORA_PASSWORD:-${AURORA_MASTER_PASSWORD}}"
export MYSQL_DATABASE="${AURORA_DATABASE}"

# Set logging
export FASTMCP_LOG_LEVEL="${FASTMCP_LOG_LEVEL:-ERROR}"

# Run the MySQL MCP server
# Using @modelcontextprotocol/server-mysql (official MCP MySQL server)
exec uvx @modelcontextprotocol/server-mysql@latest "$@"
