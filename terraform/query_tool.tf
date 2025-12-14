# Query Tool Lambda - Utility Layer
#
# Single Responsibility: Execute SQL queries, inspect schema, debug data
#
# Architecture Redesign (Sprint 3 of 5):
#   Part of scheduler redesign - this Lambda handles all query/debug operations
#   Used by CI/CD for schema validation and developers for debugging
#
# Trigger: Manual invocation (CI/CD, debugging)
# Actions: query, describe_table, query_precomputed, debug_cache, debug_prices

###############################################################################
# Lambda Function for Query Tool (Utility Layer)
###############################################################################

resource "aws_lambda_function" "query_tool" {
  function_name = "${var.project_name}-query-tool-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn # Reuse existing role (has Aurora access)

  # Container image deployment from ECR (same image as other Lambdas)
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.query_tool_handler.lambda_handler"]
  }

  # 2 minutes timeout for query operations
  timeout     = 120
  memory_size = 256 # Less memory than data operations

  environment {
    variables = {
      # Environment
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"

      # Aurora MySQL (for queries)
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
    }
  }

  # VPC Configuration for Aurora access
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  vpc_config {
      subnet_ids         = local.private_subnets_with_nat
      security_group_ids = [aws_security_group.lambda_aurora.id]
    }


  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-query-tool-${var.environment}"
    App       = "telegram-api"
    Component = "query-tool"
    Layer     = "utility"
    Trigger   = "manual-cicd"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy.telegram_lambda_custom
  ]
}

# Attach Aurora access policy to query-tool Lambda role (when aurora is enabled)
resource "aws_iam_role_policy_attachment" "query_tool_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "query_tool_logs" {
  name              = "/aws/lambda/${aws_lambda_function.query_tool.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-query-tool-logs-${var.environment}"
    App       = "telegram-api"
    Component = "query-tool-logging"
  })
}

###############################################################################
# Lambda Alias for Zero-Downtime Deployment
###############################################################################

# Initial alias pointing to $LATEST - CI/CD will update this after smoke tests
# Using lifecycle ignore to let CI/CD control the version pointer
resource "aws_lambda_alias" "query_tool_live" {
  name             = "live"
  description      = "Production alias - CI/CD updates after smoke tests pass"
  function_name    = aws_lambda_function.query_tool.function_name
  function_version = "$LATEST" # Initial value, CI/CD will update

  lifecycle {
    ignore_changes = [function_version] # Let CI/CD control the version
  }
}

###############################################################################
# Outputs
###############################################################################

output "query_tool_function_name" {
  value       = aws_lambda_function.query_tool.function_name
  description = "Name of the query tool Lambda function"
}

output "query_tool_function_arn" {
  value       = aws_lambda_function.query_tool.arn
  description = "ARN of the query tool Lambda function"
}

output "query_tool_alias_arn" {
  value       = aws_lambda_alias.query_tool_live.arn
  description = "ARN of the query tool live alias (for manual/CI-CD invocation)"
}
