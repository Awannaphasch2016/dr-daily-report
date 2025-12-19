# Telegram Mini App API Infrastructure
# Separate Lambda function and resources for Telegram Mini App REST API

###############################################################################
# IAM Role for Telegram API Lambda
###############################################################################

resource "aws_iam_role" "telegram_lambda_role" {
  name = "${var.project_name}-telegram-api-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-role-${var.environment}"
    App       = "telegram-api"
    Component = "iam-role"
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "telegram_lambda_basic" {
  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach DynamoDB access policy (already created in dynamodb.tf)
resource "aws_iam_role_policy_attachment" "telegram_lambda_dynamodb" {
  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

# Attach VPC execution policy (required for Lambda in VPC to access Aurora)
resource "aws_iam_role_policy_attachment" "telegram_lambda_vpc" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Attach Aurora access policy
resource "aws_iam_role_policy_attachment" "telegram_lambda_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# Custom policy for S3 PDF storage access and ECR access
resource "aws_iam_role_policy" "telegram_lambda_custom" {
  name = "${var.project_name}-telegram-api-custom-policy-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.pdf_reports.arn
      },
      # S3 Data Lake Access (Phase 1: Raw data staging)
      # Worker Lambda needs to store raw yfinance API responses with tagging
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectTagging",
          "s3:GetObject",
          "s3:GetObjectTagging"
        ]
        Resource = "${module.s3_data_lake.bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = module.s3_data_lake.bucket_arn
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

###############################################################################
# Lambda Function for Telegram API
###############################################################################

resource "aws_lambda_function" "telegram_api" {
  function_name = "${var.project_name}-telegram-api-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn

  # Container image deployment from ECR
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["telegram_lambda_handler.handler"]
  }

  # Enable versioning for safe rollbacks
  publish = true

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment {
    variables = {
      # OpenRouter API (shared)
      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY

      # S3 Storage (shared)
      PDF_STORAGE_BUCKET       = aws_s3_bucket.pdf_reports.id
      PDF_BUCKET_NAME          = aws_s3_bucket.pdf_reports.id
      PDF_URL_EXPIRATION_HOURS = "24"

      # S3 Data Lake (Phase 1: Raw data staging)
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id

      # Cache Configuration
      CACHE_BACKEND  = "hybrid" # hybrid, s3, or sqlite
      CACHE_TTL_HOURS = "24"

      # DynamoDB Tables
      DYNAMODB_WATCHLIST_TABLE = aws_dynamodb_table.telegram_watchlist.name
      # NOTE: DYNAMODB_CACHE_TABLE removed - cache moved to Aurora ticker_data_cache
      JOBS_TABLE_NAME          = aws_dynamodb_table.report_jobs.name

      # SQS Queue for Async Reports
      REPORT_JOBS_QUEUE_URL = aws_sqs_queue.report_jobs.url

      # Telegram Configuration
      TELEGRAM_BOT_TOKEN  = var.telegram_bot_token
      TELEGRAM_APP_ID     = var.telegram_app_id
      TELEGRAM_APP_HASH   = var.telegram_app_hash
      TELEGRAM_WEBAPP_URL = var.telegram_webapp_url

      # Langfuse Observability
      LANGFUSE_PUBLIC_KEY = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST       = var.LANGFUSE_HOST

      # Aurora MySQL connection (for cache-first report lookup)
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      # Environment
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"
    }
  }

  # VPC Configuration for Aurora access (required to connect to Aurora in VPC)
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  # Lambda needs internet access for yfinance, OpenRouter, DynamoDB, and SQS APIs
  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-${var.environment}"
    App       = "telegram-api"
    Component = "rest-api"
    Interface = "api-gateway"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy_attachment.telegram_lambda_dynamodb,
    aws_iam_role_policy_attachment.telegram_lambda_vpc,
    aws_iam_role_policy_attachment.telegram_lambda_aurora_access
  ]
}

###############################################################################
# Lambda Alias for Production Traffic
###############################################################################

resource "aws_lambda_alias" "telegram_api_live" {
  name             = "live"
  description      = "Production traffic alias - update to rollback"
  function_name    = aws_lambda_function.telegram_api.function_name
  function_version = aws_lambda_function.telegram_api.version

  lifecycle {
    # Allow external updates (from CI/CD) without Terraform drift
    ignore_changes = [function_version]
  }
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "telegram_api_logs" {
  name              = "/aws/lambda/${aws_lambda_function.telegram_api.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-logs-${var.environment}"
    App       = "telegram-api"
    Component = "logging"
  })
}

###############################################################################
# Outputs
###############################################################################

output "telegram_lambda_function_arn" {
  value       = aws_lambda_function.telegram_api.arn
  description = "ARN of the Telegram API Lambda function"
}

output "telegram_lambda_function_name" {
  value       = aws_lambda_function.telegram_api.function_name
  description = "Name of the Telegram API Lambda function"
}

output "telegram_lambda_role_arn" {
  value       = aws_iam_role.telegram_lambda_role.arn
  description = "ARN of the Telegram API Lambda IAM role"
}

output "telegram_lambda_alias_arn" {
  value       = aws_lambda_alias.telegram_api_live.arn
  description = "ARN of the Telegram API Lambda 'live' alias"
}

output "telegram_lambda_version" {
  value       = aws_lambda_function.telegram_api.version
  description = "Current published version of the Telegram API Lambda"
}
