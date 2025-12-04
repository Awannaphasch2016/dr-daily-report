# Lambda Module - Main Resources
# Container image Lambda function with optional VPC configuration

locals {
  full_function_name = "${var.project_name}-${var.function_name}-${var.environment}"

  # Determine which IAM role to use
  lambda_role_arn = var.create_iam_role ? aws_iam_role.lambda[0].arn : var.role_arn

  # Merge tags
  resource_tags = merge(var.common_tags, {
    Name      = local.full_function_name
    App       = var.app_tag
    Component = var.component_tag
  }, var.extra_tags)
}

#------------------------------------------------------------------------------
# Lambda Function
#------------------------------------------------------------------------------

resource "aws_lambda_function" "this" {
  function_name = local.full_function_name
  role          = local.lambda_role_arn

  # Container image deployment from ECR
  package_type = "Image"
  image_uri    = var.image_uri

  image_config {
    command = [var.handler_command]
  }

  # Enable versioning for safe rollbacks
  publish = true

  memory_size = var.memory_size
  timeout     = var.timeout

  environment {
    variables = var.environment_variables
  }

  # VPC Configuration (optional)
  dynamic "vpc_config" {
    for_each = var.vpc_enabled ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = local.resource_tags

  depends_on = [
    aws_iam_role_policy_attachment.basic_execution,
    aws_iam_role_policy_attachment.vpc_execution,
    aws_iam_role_policy_attachment.managed_policies,
    aws_iam_role_policy.custom
  ]
}

#------------------------------------------------------------------------------
# Lambda Alias (optional)
#------------------------------------------------------------------------------

resource "aws_lambda_alias" "live" {
  count = var.create_alias ? 1 : 0

  name             = "live"
  description      = "Production traffic alias - update to rollback"
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version

  lifecycle {
    # Allow external updates (from CI/CD) without Terraform drift
    ignore_changes = [function_version]
  }
}

#------------------------------------------------------------------------------
# CloudWatch Log Group
#------------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "logs" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.resource_tags, {
    Component = "logging"
  })
}
