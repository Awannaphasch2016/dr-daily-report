# MCP Server Security Policy
#
# Enforces security and configuration best practices for MCP (Model Context Protocol) servers:
# - Lambda Function URL authorization (warn if NONE without IP whitelisting)
# - Lambda timeout limits (prevent excessive execution time)
# - Lambda memory configuration (ensure adequate resources)
# - CORS configuration (verify proper CORS setup)
# - Environment variables (verify required env vars are set)
#
# Usage: conftest test tfplan.json --policy policies/ --all-namespaces

package terraform.security.mcp

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Helper: Check if resource is an MCP server Lambda (by name pattern or tags)
is_mcp_server_lambda(resource) if {
    resource.type == "aws_lambda_function"
    contains(resource.change.after.function_name, "mcp-server")
}

is_mcp_server_lambda(resource) if {
    resource.type == "aws_lambda_function"
    resource.change.after.tags["App"] == "mcp-server"
}

# Helper: Check if resource is an MCP server Function URL
is_mcp_server_function_url(resource) if {
    resource.type == "aws_lambda_function_url"
    contains(resource.address, "mcp")
}

# Deny MCP server Lambda with timeout > 30 seconds
# MCP servers should respond quickly to avoid client timeouts
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_lambda(resource)
    resource.change.actions[_] != "delete"
    timeout := resource.change.after.timeout
    timeout > 30
    msg := sprintf("MCP server Lambda '%s' has timeout %d seconds. MCP servers should have timeout <= 30 seconds to avoid client timeouts.", [resource.address, timeout])
}

# Deny MCP server Lambda with memory < 512 MB
# MCP servers need adequate memory for HTTP requests and JSON processing
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_lambda(resource)
    resource.change.actions[_] != "delete"
    memory := resource.change.after.memory_size
    memory < 512
    msg := sprintf("MCP server Lambda '%s' has memory %d MB. MCP servers should have at least 512 MB memory for HTTP requests and JSON processing.", [resource.address, memory])
}

# Warn about Function URL with authorization_type = NONE
# MCP servers should use API keys or IP whitelisting in production
warn contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_function_url(resource)
    resource.change.actions[_] != "delete"
    resource.change.after.authorization_type == "NONE"
    msg := sprintf("MCP server Function URL '%s' has authorization_type = NONE. Consider using AWS_IAM or API keys/IP whitelisting for production deployments.", [resource.address])
}

# Verify CORS configuration for MCP server Function URLs
# MCP servers need CORS to allow cross-origin requests from clients
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_function_url(resource)
    resource.change.actions[_] != "delete"
    cors_config := resource.change.after.cors
    cors_config == null
    msg := sprintf("MCP server Function URL '%s' must have CORS configuration. MCP clients may need cross-origin requests.", [resource.address])
}

# Verify CORS allows POST method (required for MCP JSON-RPC 2.0)
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_function_url(resource)
    resource.change.actions[_] != "delete"
    cors_config := resource.change.after.cors
    cors_config != null
    allowed_methods := cors_config.allow_methods
    not "POST" in allowed_methods
    msg := sprintf("MCP server Function URL '%s' CORS must allow POST method for JSON-RPC 2.0 requests.", [resource.address])
}

# Verify CORS allows OPTIONS method (required for CORS preflight)
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_function_url(resource)
    resource.change.actions[_] != "delete"
    cors_config := resource.change.after.cors
    cors_config != null
    allowed_methods := cors_config.allow_methods
    not "OPTIONS" in allowed_methods
    msg := sprintf("MCP server Function URL '%s' CORS must allow OPTIONS method for CORS preflight requests.", [resource.address])
}

# Verify CORS allows content-type header (required for JSON-RPC 2.0)
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_function_url(resource)
    resource.change.actions[_] != "delete"
    cors_config := resource.change.after.cors
    cors_config != null
    allowed_headers := cors_config.allow_headers
    not "content-type" in allowed_headers
    msg := sprintf("MCP server Function URL '%s' CORS must allow 'content-type' header for JSON-RPC 2.0 requests.", [resource.address])
}

# Warn about MCP server Lambda without required environment variables
# SEC EDGAR MCP server requires SEC_EDGAR_USER_AGENT
warn contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_lambda(resource)
    resource.change.actions[_] != "delete"
    contains(resource.change.after.function_name, "sec-edgar")
    env_vars := resource.change.after.environment
    env_vars != null
    env_vars.variables != null
    not "SEC_EDGAR_USER_AGENT" in env_vars.variables
    msg := sprintf("SEC EDGAR MCP server Lambda '%s' should have SEC_EDGAR_USER_AGENT environment variable for SEC EDGAR API compliance.", [resource.address])
}

# Deny MCP server Lambda without CloudWatch log retention
# MCP servers need logs for debugging and compliance
deny contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_lambda(resource)
    resource.change.actions[_] != "delete"
    # Check if log group exists with retention
    log_group_address := sprintf("%s.logs", [resource.address])
    log_group := input.resource_changes[_]
    log_group.type == "aws_cloudwatch_log_group"
    log_group.address == log_group_address
    log_group.change.after.retention_in_days == null
    msg := sprintf("MCP server Lambda '%s' CloudWatch log group should have retention_in_days configured for log management.", [resource.address])
}

# Warn about MCP server Lambda without VPC configuration
# MCP servers typically don't need VPC (they call external APIs), but warn if VPC is missing
# when it might be needed for internal service access
warn contains msg if {
    resource := input.resource_changes[_]
    is_mcp_server_lambda(resource)
    resource.change.actions[_] != "delete"
    vpc_config := resource.change.after.vpc_config
    vpc_config == null
    # Only warn if Lambda might need VPC access (e.g., for internal services)
    # SEC EDGAR MCP server doesn't need VPC (calls public SEC EDGAR API)
    msg := sprintf("MCP server Lambda '%s' has no VPC configuration. This is OK for servers calling external APIs (e.g., SEC EDGAR), but ensure internal service access is not required.", [resource.address])
}
