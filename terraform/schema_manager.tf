# Schema Manager Lambda - Admin Layer
#
# Single Responsibility: Manage Aurora schema, migrations, and one-time setup operations
#
# Architecture Redesign (Sprint 2 of 5):
#   Part of scheduler redesign - this Lambda handles all schema/migration operations
#   that were previously mixed with data fetching in the monolithic handler.
#
# Trigger: Manual invocation only (pre-deployment, migrations)
# Actions: execute_migration, precompute_migration, aurora_setup, setup_ticker_mapping, ticker_unification

###############################################################################
# Lambda Function for Schema Manager (Admin Layer)
###############################################################################

resource "aws_lambda_function" "schema_manager" {
  function_name = "${var.project_name}-schema-manager-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn # Reuse existing role (has S3 + Aurora access)

  # Container image deployment from ECR (same image as other Lambdas)
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.schema_manager_handler.lambda_handler"]
  }

  # 5 minutes timeout for migration operations
  timeout     = 300
  memory_size = 256 # Less memory than data operations (no heavy processing)

  environment {
    variables = {
      # Environment
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"

      # Aurora MySQL (for schema operations)
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      # S3 Storage (for some setup operations that read from S3)
      PDF_BUCKET_NAME  = aws_s3_bucket.pdf_reports.id
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id
    }
  }

  # VPC Configuration for Aurora access
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  # Lambda needs internet access for downloading packages/dependencies
  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-schema-manager-${var.environment}"
    App       = "telegram-api"
    Component = "schema-manager"
    Layer     = "admin"
    Trigger   = "manual"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy.telegram_lambda_custom
  ]
}

# Attach Aurora access policy to schema-manager Lambda role (when aurora is enabled)
resource "aws_iam_role_policy_attachment" "schema_manager_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "schema_manager_logs" {
  name              = "/aws/lambda/${aws_lambda_function.schema_manager.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-schema-manager-logs-${var.environment}"
    App       = "telegram-api"
    Component = "schema-manager-logging"
  })
}

###############################################################################
# Lambda Alias for Zero-Downtime Deployment
###############################################################################

# Initial alias pointing to $LATEST - CI/CD will update this after smoke tests
# Using lifecycle ignore to let CI/CD control the version pointer
resource "aws_lambda_alias" "schema_manager_live" {
  name             = "live"
  description      = "Production alias - CI/CD updates after smoke tests pass"
  function_name    = aws_lambda_function.schema_manager.function_name
  function_version = "$LATEST" # Initial value, CI/CD will update

  lifecycle {
    ignore_changes = [function_version] # Let CI/CD control the version
  }
}

###############################################################################
# Outputs
###############################################################################

output "schema_manager_function_name" {
  value       = aws_lambda_function.schema_manager.function_name
  description = "Name of the schema manager Lambda function"
}

output "schema_manager_function_arn" {
  value       = aws_lambda_function.schema_manager.arn
  description = "ARN of the schema manager Lambda function"
}

output "schema_manager_alias_arn" {
  value       = aws_lambda_alias.schema_manager_live.arn
  description = "ARN of the schema manager live alias (for manual invocation)"
}
