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
    command = ["src.scheduler.ticker_fetcher_handler.lambda_handler"]
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

      # Precompute Controller (for automatic triggering after fetch)
      PRECOMPUTE_CONTROLLER_ARN = aws_lambda_function.precompute_controller.arn

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
    Schedule  = "daily-5am-bangkok"
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

# Allow scheduler to invoke precompute controller (for automatic precompute triggering)
resource "aws_iam_role_policy" "scheduler_invoke_precompute" {
  name = "${var.project_name}-scheduler-invoke-precompute-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.precompute_controller.arn
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

# Daily ticker data fetch from Yahoo Finance
# Schedule: 5 AM Bangkok time (22:00 UTC previous day)
resource "aws_cloudwatch_event_rule" "daily_ticker_fetch" {
  name                = "${var.project_name}-daily-ticker-fetch-${var.environment}"
  description         = "Fetch ticker data daily at 5 AM Bangkok time (UTC+7)"
  schedule_expression = "cron(0 22 * * ? *)" # 22:00 UTC = 05:00 Bangkok next day

  # Shadow Run: Toggle controlled by var.old_scheduler_enabled
  # Phase 1-2: ENABLED (old continues as fallback)
  # Phase 3+: DISABLED (cutover to new Scheduler)
  state = var.old_scheduler_enabled ? "ENABLED" : "DISABLED"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-daily-ticker-fetch-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler-trigger"
    Schedule  = "daily-5am-bangkok"
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
# EventBridge Scheduler (NEW Architecture)
# Native timezone support: schedule_expression_timezone = "Asia/Bangkok"
# Replaces EventBridge Rules with better semantic clarity
###############################################################################

# IAM Role for EventBridge Scheduler to invoke Lambda
# Note: Scheduler uses IAM role (not resource-based policy like EventBridge Rules)
resource "aws_iam_role" "eventbridge_scheduler" {
  count = var.new_scheduler_enabled ? 1 : 0

  name = "${var.project_name}-eventbridge-scheduler-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com" # EventBridge Scheduler service principal
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-eventbridge-scheduler-role-${var.environment}"
    App       = "telegram-api"
    Component = "scheduler-role"
    Purpose   = "EventBridge Scheduler Lambda invocation"
  })
}

# IAM Policy: Allow Scheduler to invoke Lambda (via live alias)
resource "aws_iam_role_policy" "eventbridge_scheduler_lambda" {
  count = var.new_scheduler_enabled ? 1 : 0

  name = "${var.project_name}-scheduler-lambda-invoke-${var.environment}"
  role = aws_iam_role.eventbridge_scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction"
      ]
      Resource = [
        aws_lambda_alias.ticker_scheduler_live.arn,     # Specific alias
        "${aws_lambda_function.ticker_scheduler.arn}:*" # Any alias/version
      ]
    }]
  })
}

# EventBridge Scheduler Schedule - Daily ticker data fetch
# Semantic clarity: cron(0 5 * * ? *) + timezone = "Asia/Bangkok"
# No more UTC offset mental math!
resource "aws_scheduler_schedule" "daily_ticker_fetch_v2" {
  count = var.new_scheduler_enabled ? 1 : 0

  name       = "${var.project_name}-daily-ticker-fetch-v2-${var.environment}"
  group_name = "default" # Use default schedule group

  # Required parameter for Scheduler (not in EventBridge Rules)
  flexible_time_window {
    mode = "OFF" # Execute exactly at scheduled time (no flexibility)
  }

  # SEMANTIC CLARITY: Bangkok time with explicit timezone!
  # Phase 1-2: Runs at same time as old rule (5 AM Bangkok)
  # Replaces: cron(0 22 * * ? *) in UTC (confusing!)
  schedule_expression          = "cron(0 5 * * ? *)" # 5 AM Bangkok
  schedule_expression_timezone = "Asia/Bangkok"      # Explicit timezone

  # Shadow Run Phase 2: Enable for parallel testing
  # When new_scheduler_enabled=true, schedule becomes ENABLED
  # Both old and new will trigger (2x invocations per day)
  state = var.new_scheduler_enabled ? "ENABLED" : "DISABLED"

  # Lambda target configuration (same as old EventBridge target)
  target {
    arn      = aws_lambda_alias.ticker_scheduler_live.arn
    role_arn = aws_iam_role.eventbridge_scheduler[0].arn

    # Same payload as old EventBridge target (line 197-200)
    input = jsonencode({
      action         = "precompute"
      include_report = true
    })

    # Retry policy (optional but recommended)
    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600 # 1 hour
    }

    # Dead letter queue (optional, for failed invocations)
    # Future enhancement: Add DLQ for monitoring failures
    # dead_letter_config {
    #   arn = aws_sqs_queue.scheduler_dlq.arn
    # }
  }

  # Note: aws_scheduler_schedule does not support tags argument
  # Tags can be applied via schedule groups instead

  # Ensure IAM role exists before creating schedule
  depends_on = [
    aws_iam_role.eventbridge_scheduler,
    aws_iam_role_policy.eventbridge_scheduler_lambda
  ]
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
  description = "Name of legacy EventBridge rule (Phase 1-2)"
}

output "ticker_scheduler_eventbridge_rule_v2" {
  value       = var.new_scheduler_enabled ? aws_scheduler_schedule.daily_ticker_fetch_v2[0].name : null
  description = "Name of new Scheduler schedule (Phase 2+, null if disabled)"
}

output "ticker_scheduler_enabled" {
  value       = aws_cloudwatch_event_rule.daily_ticker_fetch.state == "ENABLED"
  description = "Whether the legacy daily ticker fetch schedule is enabled"
}

output "ticker_scheduler_v2_enabled" {
  value       = var.new_scheduler_enabled ? aws_scheduler_schedule.daily_ticker_fetch_v2[0].state == "ENABLED" : false
  description = "Whether the new Scheduler schedule is enabled (false if not deployed)"
}

output "ticker_scheduler_migration_phase" {
  value = var.old_scheduler_enabled && !var.new_scheduler_enabled ? "phase-1-new-disabled" : (
    var.old_scheduler_enabled && var.new_scheduler_enabled ? "phase-2-parallel" : (
      !var.old_scheduler_enabled && var.new_scheduler_enabled ? "phase-3-cutover" : "phase-4-cleanup"
    )
  )
  description = "Current migration phase based on toggle variables"
}
