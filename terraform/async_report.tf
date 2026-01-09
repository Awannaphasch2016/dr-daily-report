# Terraform configuration for Async Report Generation
# Architecture: API Gateway -> API Lambda -> Direct Lambda Invocation -> Worker Lambda -> DynamoDB

###############################################################################
# DynamoDB Table for Report Jobs
###############################################################################

resource "aws_dynamodb_table" "report_jobs" {
  name         = "${var.project_name}-telegram-jobs-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # On-demand pricing

  hash_key = "job_id"

  attribute {
    name = "job_id"
    type = "S" # String - e.g., "rpt_abc123"
  }

  # TTL for automatic cleanup of completed/failed jobs after 24 hours
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-jobs-${var.environment}"
    App       = "telegram-api"
    Component = "job-storage"
    DataType  = "async-jobs"
  })
}

###############################################################################
# IAM Role for Report Worker Lambda
###############################################################################

resource "aws_iam_role" "report_worker_role" {
  name = "${var.project_name}-report-worker-role-${var.environment}"

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
    Name      = "${var.project_name}-report-worker-role-${var.environment}"
    App       = "telegram-api"
    Component = "iam-role"
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "report_worker_basic" {
  role       = aws_iam_role.report_worker_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach VPC execution policy (required for Lambda in VPC)
resource "aws_iam_role_policy_attachment" "report_worker_vpc" {
  # Aurora always enabled

  role       = aws_iam_role.report_worker_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Attach Aurora access policy to report worker role
resource "aws_iam_role_policy_attachment" "report_worker_aurora_access" {
  # Aurora always enabled

  role       = aws_iam_role.report_worker_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

# Custom policy for Report Worker Lambda
resource "aws_iam_role_policy" "report_worker_policy" {
  name = "${var.project_name}-report-worker-policy-${var.environment}"
  role = aws_iam_role.report_worker_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # DynamoDB - Create and update job status
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.report_jobs.arn
      },
      # S3 - PDF storage
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      }
    ]
  })
}

# IAM permission for telegram_api Lambda to invoke report_worker
# Migration: Added for direct Lambda invocation (replaces SQS pattern)
# Date: 2026-01-04
resource "aws_iam_role_policy" "telegram_api_invoke_worker" {
  name = "${var.project_name}-telegram-api-invoke-worker-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.report_worker.arn
      }
    ]
  })
}

###############################################################################
# Report Worker Lambda Function
###############################################################################

resource "aws_lambda_function" "report_worker" {
  function_name = "${var.project_name}-report-worker-${var.environment}"
  role          = aws_iam_role.report_worker_role.arn

  # Container image deployment from ECR (same image as API)
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["report_worker_handler.handler"]
  }

  # Enable versioning for safe rollbacks
  publish = true

  memory_size = 1024       # Higher memory for LLM processing
  timeout     = 120        # 120 second timeout for report generation (LLM takes ~60s)

  environment {
    variables = {
      # Timezone (Principle #16: Timezone Discipline)
      TZ = "Asia/Bangkok"

      OPENROUTER_API_KEY       = var.OPENROUTER_API_KEY
      JOBS_TABLE_NAME          = aws_dynamodb_table.report_jobs.name
      PDF_STORAGE_BUCKET       = aws_s3_bucket.pdf_reports.id
      PDF_BUCKET_NAME          = aws_s3_bucket.pdf_reports.id

      # Langfuse Observability
      LANGFUSE_PUBLIC_KEY = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST       = var.LANGFUSE_HOST

      # Aurora MySQL connection (for caching reports)
      AURORA_HOST     = aws_rds_cluster.aurora.endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
    }
  }

  # VPC Configuration for Aurora access (required to connect to Aurora in VPC)
  # IMPORTANT: Only use subnets with NAT Gateway routes (local.private_subnets_with_nat)
  # Lambda needs internet access for yfinance, OpenRouter, and DynamoDB APIs
  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-report-worker-${var.environment}"
    App       = "telegram-api"
    Component = "report-worker"
    Trigger   = "sqs"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.report_worker_basic
  ]
}

###############################################################################
# Report Worker Lambda Alias
###############################################################################

resource "aws_lambda_alias" "report_worker_live" {
  name             = "live"
  description      = "Production alias for report worker - update to rollback"
  function_name    = aws_lambda_function.report_worker.function_name
  function_version = aws_lambda_function.report_worker.version

  lifecycle {
    # Allow external updates (from CI/CD) without Terraform drift
    ignore_changes = [function_version]
  }
}

###############################################################################
# Telegram API Lambda IAM Policy for Jobs Table
###############################################################################

# Policy for Telegram API Lambda to create and read jobs
resource "aws_iam_role_policy" "telegram_api_async_policy" {
  name = "${var.project_name}-telegram-api-async-policy-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # DynamoDB - Create and read jobs
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.report_jobs.arn
      }
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "report_jobs_table_name" {
  value       = aws_dynamodb_table.report_jobs.name
  description = "Name of the DynamoDB table for report jobs"
}

output "report_jobs_table_arn" {
  value       = aws_dynamodb_table.report_jobs.arn
  description = "ARN of the DynamoDB table for report jobs"
}

output "report_worker_function_name" {
  value       = aws_lambda_function.report_worker.function_name
  description = "Name of the Report Worker Lambda function"
}

output "report_worker_function_arn" {
  value       = aws_lambda_function.report_worker.arn
  description = "ARN of the Report Worker Lambda function"
}
