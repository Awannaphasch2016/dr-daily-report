#!/bin/bash
# Wrapper script for AWS Step Functions MCP Server with Doppler environment variables
# This script exports Doppler secrets as environment variables, then runs the MCP server directly

set -e

# Export Doppler secrets as environment variables
eval "$(doppler run --config dev -- printenv | grep -E '^(AWS_|DOPPLER_)' | sed 's/^/export /')"

# Set additional environment variables
export FASTMCP_LOG_LEVEL="${FASTMCP_LOG_LEVEL:-ERROR}"
export AWS_REGION="${AWS_REGION:-ap-southeast-1}"

# Run the Step Functions MCP server directly (not wrapped in doppler)
exec uvx awslabs.stepfunctions-mcp-server@latest "$@"
