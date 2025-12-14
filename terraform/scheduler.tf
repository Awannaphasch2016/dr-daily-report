# Ticker Data Scheduler Infrastructure
# EventBridge rule + Lambda for daily pre-fetching of Yahoo Finance ticker data
#
# Schedule: Daily at 8 AM Bangkok time (01:00 UTC)
# Manual testing: aws lambda invoke --function-name dr-daily-report-ticker-scheduler-dev --payload '{}' /tmp/response.json

###############################################################################
# Lambda Function for Ticker Scheduler
###############################################################################

resource "aws_lambda_function" "ticker_scheduler" {
  function_name = "${var.project_name}-ticker-scheduler-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn # Reuse existing role (has S3 + DynamoDB access)

  # Container image deployment from ECR (same image as telegram-api)
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.handler.lambda_handler"]
  }

  # 5 minutes timeout for fetching ~47 tickers
  timeout     = 300
  memory_size = 512

  environment {
    variables = {
      # S3 Storage (for caching)
      PDF_BUCKET_NAME = aws_s3_bucket.pdf_reports.id

      # S3 Data Lake (Phase 1: Raw data staging)
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id

      # Environment
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"

      # LLM API Key (required for report generation)
      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY

      # SQS Queue for parallel precompute fan-out
      REPORT_JOBS_QUEUE_URL = aws_sqs_queue.report_jobs.url

      # DynamoDB for job tracking
      JOBS_TABLE_NAME = aws_dynamodb_table.report_jobs.name

      # Aurora MySQL (direct env vars - bypasses Secrets Manager for simplicity)
      # NOTE: Using direct env vars instead of AURORA_SECRET_ARN to avoid VPC endpoint requirement
      # TODO: Add VPC endpoint for Secrets Manager for production security
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
    }
  }

  # VPC Configuration for Aurora access
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  # Lambda needs internet access for yfinance, OpenRouter, and DynamoDB APIs
  vpc_config {
      subnet_ids         = local.private_subnets_with_nat
      security_group_ids = [aws_security_group.lambda_aurora.id]
    }


  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-ticker-scheduler-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler"
    Schedule  = "daily-8am-bangkok"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy.telegram_lambda_custom
  ]
}

# Attach Aurora access policy to scheduler Lambda role (when aurora is enabled)
resource "aws_iam_role_policy_attachment" "scheduler_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# Allow Lambda role to read Aurora secrets from Secrets Manager
resource "aws_iam_role_policy" "scheduler_secrets_access" {
  # Aurora always enabled

  name = "${var.project_name}-scheduler-secrets-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.aurora_credentials.arn
      }
    ]
  })
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "ticker_scheduler_logs" {
  name              = "/aws/lambda/${aws_lambda_function.ticker_scheduler.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-ticker-scheduler-logs-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler-logging"
  })
}

###############################################################################
# Lambda Alias for Zero-Downtime Deployment
###############################################################################

# Initial alias pointing to $LATEST - CI/CD will update this after smoke tests
# Using lifecycle ignore to let CI/CD control the version pointer
resource "aws_lambda_alias" "ticker_scheduler_live" {
  name             = "live"
  description      = "Production alias - CI/CD updates after smoke tests pass"
  function_name    = aws_lambda_function.ticker_scheduler.function_name
  function_version = "$LATEST" # Initial value, CI/CD will update

  lifecycle {
    ignore_changes = [function_version] # Let CI/CD control the version
  }
}

###############################################################################
# EventBridge Rule for Daily Schedule
###############################################################################

# NOTE: Schedule is initially DISABLED for manual testing
# To enable: Change enabled = true, then terraform apply
resource "aws_cloudwatch_event_rule" "daily_ticker_fetch" {
  name                = "${var.project_name}-daily-ticker-fetch-${var.environment}"
  description         = "Fetch ticker data daily at 8 AM Bangkok time (UTC+7)"
  schedule_expression = "cron(0 1 * * ? *)" # 01:00 UTC = 08:00 Bangkok

  # Rule enabled - daily precomputation at 8 AM Bangkok (01:00 UTC)
  # With include_report: true, generates full LLM reports for all tickers
  state = "ENABLED"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-daily-ticker-fetch-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler-trigger"
    Schedule  = "daily-8am-bangkok"
  })
}

# EventBridge Target - connects rule to Lambda (via live alias)
# Uses alias ARN for zero-downtime deployment - EventBridge always invokes tested code
resource "aws_cloudwatch_event_target" "ticker_scheduler" {
  rule      = aws_cloudwatch_event_rule.daily_ticker_fetch.name
  target_id = "ticker-scheduler-lambda"
  arn       = aws_lambda_alias.ticker_scheduler_live.arn # Invoke via alias, not $LATEST

  # Precompute all tickers with full LLM report generation
  # Reports are cached in Aurora and served instantly via API
  input = jsonencode({
    action         = "precompute"
    include_report = true
  })
}

# Lambda Permission for EventBridge to invoke (via live alias)
resource "aws_lambda_permission" "eventbridge_invoke_scheduler" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ticker_scheduler.function_name
  qualifier     = aws_lambda_alias.ticker_scheduler_live.name # Permission for alias, not $LATEST
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_ticker_fetch.arn
}

###############################################################################
# Outputs
###############################################################################

output "ticker_scheduler_function_name" {
  value       = aws_lambda_function.ticker_scheduler.function_name
  description = "Name of the ticker scheduler Lambda function"
}

output "ticker_scheduler_function_arn" {
  value       = aws_lambda_function.ticker_scheduler.arn
  description = "ARN of the ticker scheduler Lambda function"
}

output "ticker_scheduler_alias_arn" {
  value       = aws_lambda_alias.ticker_scheduler_live.arn
  description = "ARN of the ticker scheduler live alias (for EventBridge invocation)"
}

output "ticker_scheduler_eventbridge_rule" {
  value       = aws_cloudwatch_event_rule.daily_ticker_fetch.name
  description = "Name of the EventBridge rule for daily ticker fetch"
}

output "ticker_scheduler_enabled" {
  value       = aws_cloudwatch_event_rule.daily_ticker_fetch.state == "ENABLED"
  description = "Whether the daily ticker fetch schedule is enabled"
}
