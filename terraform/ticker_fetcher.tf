# Ticker Fetcher Lambda - Extract Layer
#
# Single Responsibility: Fetch raw ticker data from yfinance and store to S3/Aurora/Data Lake
#
# Architecture Redesign (Sprint 1 of 5):
#   This Lambda is part of the scheduler redesign, splitting the monolithic "God Lambda"
#   (handler.py with 14 actions) into 4 focused Lambdas following AWS ETL best practices.
#
# Deployment Strategy: Shadow Run Approach
#   Phase 1 (Current): Deploy with EventBridge DISABLED - manual testing only
#   Phase 2 (After validation): Enable EventBridge to replace old ticker-scheduler
#   Phase 3 (After cutover): Delete old handler.py
#
# Schedule: Daily at 8 AM Bangkok time (01:00 UTC)
# Manual testing: aws lambda invoke --function-name dr-daily-report-ticker-fetcher-dev --payload '{}' /tmp/response.json

###############################################################################
# Lambda Function for Ticker Fetcher (Extract Layer)
###############################################################################

resource "aws_lambda_function" "ticker_fetcher" {
  function_name = "${var.project_name}-ticker-fetcher-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn # Reuse existing role (has S3 + Aurora access)

  # Container image deployment from ECR (same image as other Lambdas)
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.ticker_fetcher_handler.lambda_handler"]
  }

  # 5 minutes timeout for fetching ~47 tickers
  timeout     = 300
  memory_size = 512

  environment {
    variables = {
      # S3 Storage (for caching ticker data)
      PDF_BUCKET_NAME = aws_s3_bucket.pdf_reports.id

      # S3 Data Lake (raw data staging)
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id

      # Environment
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"

      # Aurora MySQL (for storing prices and ticker_info)
      # NOTE: Extract layer only WRITES raw data, does not need LLM API keys
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
    }
  }

  # VPC Configuration for Aurora access
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  # Lambda needs internet access for yfinance API and S3/Data Lake uploads
  vpc_config {
      subnet_ids         = local.private_subnets_with_nat
      security_group_ids = [aws_security_group.lambda_aurora.id]
    }


  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-ticker-fetcher-${var.environment}"
    App       = "telegram-api"
    Component = "ticker-fetcher"
    Layer     = "extract"
    Schedule  = "daily-8am-bangkok"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy.telegram_lambda_custom
  ]
}

# Attach Aurora access policy to ticker-fetcher Lambda role (when aurora is enabled)
resource "aws_iam_role_policy_attachment" "ticker_fetcher_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "ticker_fetcher_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ticker_fetcher.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-ticker-fetcher-logs-${var.environment}"
    App       = "telegram-api"
    Component = "ticker-fetcher-logging"
  })
}

###############################################################################
# Lambda Alias for Zero-Downtime Deployment
###############################################################################

# Initial alias pointing to $LATEST - CI/CD will update this after smoke tests
# Using lifecycle ignore to let CI/CD control the version pointer
resource "aws_lambda_alias" "ticker_fetcher_live" {
  name             = "live"
  description      = "Production alias - CI/CD updates after smoke tests pass"
  function_name    = aws_lambda_function.ticker_fetcher.function_name
  function_version = "$LATEST" # Initial value, CI/CD will update

  lifecycle {
    ignore_changes = [function_version] # Let CI/CD control the version
  }
}
###############################################################################
# Outputs
###############################################################################

output "ticker_fetcher_function_name" {
  value       = aws_lambda_function.ticker_fetcher.function_name
  description = "Name of the ticker fetcher Lambda function"
}

output "ticker_fetcher_function_arn" {
  value       = aws_lambda_function.ticker_fetcher.arn
  description = "ARN of the ticker fetcher Lambda function"
}

output "ticker_fetcher_alias_arn" {
  value       = aws_lambda_alias.ticker_fetcher_live.arn
  description = "ARN of the ticker fetcher live alias (for EventBridge invocation)"
}

