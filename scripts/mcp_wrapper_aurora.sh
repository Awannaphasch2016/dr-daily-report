#!/bin/bash
# Wrapper script for Aurora MySQL MCP Server with Doppler environment variables

set -e

# Export Doppler secrets as environment variables
eval "$(doppler run --config dev -- printenv | grep -E '^(AWS_|AURORA_|DOPPLER_)' | sed 's/^/export /')"

# Set additional environment variables
export AWS_REGION="${AWS_REGION:-ap-southeast-1}"
export AURORA_CLUSTER_IDENTIFIER="${AURORA_CLUSTER_IDENTIFIER:-dr-daily-report-aurora-dev}"
export AURORA_DATABASE_NAME="${AURORA_DATABASE_NAME:-ticker_data}"

# Run the MCP server directly
exec uvx awslabs.mysql-mcp-server@latest "$@"
