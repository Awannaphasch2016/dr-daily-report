# MCP Servers Infrastructure
# Deploys Lambda functions for Model Context Protocol (MCP) servers

###############################################################################
# SEC EDGAR MCP Server Lambda
###############################################################################

module "sec_edgar_mcp_server" {
  source = "./modules/lambda"

  project_name   = var.project_name
  function_name  = "sec-edgar-mcp-server"
  environment    = var.environment
  app_tag        = "mcp-server"
  component_tag  = "sec-edgar"

  # Container image configuration
  # Use same ECR image as main Lambda, but different handler command
  image_uri = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"
  handler_command = "src.mcp_servers.sec_edgar_handler"

  # Lambda configuration
  memory_size = 512
  timeout     = 30

  # Environment variables
  environment_variables = {
    SEC_EDGAR_USER_AGENT = "dr-daily-report/1.0 (contact: support@dr-daily-report.com)"
  }

  # IAM permissions
  create_iam_role = true
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]

  # Logging
  log_retention_days = var.log_retention_days

  # Tags
  common_tags = local.common_tags
}

###############################################################################
# Lambda Function URL for SEC EDGAR MCP Server
###############################################################################

resource "aws_lambda_function_url" "sec_edgar_mcp" {
  function_name      = module.sec_edgar_mcp_server.function_name
  authorization_type = "NONE" # MCP servers use API keys or IP whitelisting in production

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST", "OPTIONS"]
    allow_headers     = ["content-type"]
    expose_headers    = []
    max_age          = 300
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-sec-edgar-mcp-url-${var.environment}"
    App       = "mcp-server"
    Component = "function-url"
  })
}

###############################################################################
# Outputs
###############################################################################

output "sec_edgar_mcp_url" {
  description = "Function URL for SEC EDGAR MCP server"
  value       = aws_lambda_function_url.sec_edgar_mcp.function_url
}

output "sec_edgar_mcp_function_name" {
  description = "Lambda function name for SEC EDGAR MCP server"
  value       = module.sec_edgar_mcp_server.function_name
}
