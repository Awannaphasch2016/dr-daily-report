# Fund Data Sync Lambda Infrastructure
#
# Purpose: Event-driven ETL pipeline for syncing fund data from S3 to Aurora
# Trigger: S3 ObjectCreated events → SQS queue → Lambda → Aurora MySQL
#
# Architecture:
#   On-Premises SQL Server → CSV Export → S3 Data Lake (raw/)
#   → S3 Event Notification → SQS Queue
#   → Lambda (this function) → Aurora MySQL (fund_data table)
#
# Design Principles:
# - Idempotency: Lambda can process same S3 event multiple times safely
# - Fault Isolation: DLQ captures poison messages after N retries
# - Observability: CloudWatch Logs + Metrics, X-Ray tracing
# - Security: VPC isolation, least privilege IAM

# ============================================================================
# SQS Queue for S3 Events
# ============================================================================

module "fund_data_sync_queue" {
  source = "./modules/sqs-etl-queue"

  queue_name                   = "fund-data-sync-${var.environment}"
  message_retention_seconds    = 345600  # 4 days (debugging window)
  visibility_timeout_seconds   = 120     # 2 minutes (matches Lambda timeout)
  max_receive_count            = 3       # 3 retries before DLQ
  enable_cloudwatch_alarms     = true
  allow_s3_event_source        = true
  s3_bucket_arns               = [module.s3_data_lake.bucket_arn]

  # CloudWatch Alarms (notify on failures)
  dlq_alarm_threshold          = 1       # Alert on first DLQ message
  queue_depth_alarm_threshold  = 100     # Alert if backlog > 100 messages
  message_age_alarm_threshold  = 3600    # Alert if message > 1 hour old

  # Metadata
  queue_purpose = "etl-fund-data"
  data_source   = "sql-server-csv"

  common_tags = merge(
    local.common_tags,
    {
      Component   = "fund-data-sync"
      Purpose     = "etl-pipeline"
      DataSource  = "sql-server"
      App         = "shared"  # Used by both LINE bot and Telegram API
    }
  )
}

# ============================================================================
# Lambda Function for Fund Data Sync
# ============================================================================

# ECR Repository for Lambda container image
resource "aws_ecr_repository" "fund_data_sync" {
  name                 = "${var.project_name}-fund-data-sync"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    local.common_tags,
    {
      Name      = "${var.project_name}-fund-data-sync"
      Component = "fund-data-sync"
      App       = "shared"
    }
  )
}

# Lambda Function
resource "aws_lambda_function" "fund_data_sync" {
  function_name = "${var.project_name}-fund-data-sync-${var.environment}"
  role          = aws_iam_role.fund_data_sync_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.fund_data_sync.repository_url}:latest"

  # Resource Configuration
  timeout     = 120  # 2 minutes (CSV parse + batch upsert)
  memory_size = 512  # CSV parsing + NumPy/Pandas

  # VPC Configuration (only when Aurora is enabled)
  # Lambda needs VPC access to connect to Aurora MySQL
  dynamic "vpc_config" {
    for_each = var.aurora_enabled ? [1] : []
    content {
      subnet_ids         = local.private_subnets_with_nat
      security_group_ids = [aws_security_group.lambda_aurora[0].id]
    }
  }

  # Environment Variables
  environment {
    variables = {
      ENVIRONMENT          = var.environment
      AURORA_HOST          = var.aurora_enabled ? aws_rds_cluster.aurora[0].endpoint : ""
      AURORA_USER          = var.aurora_master_username
      AURORA_DATABASE      = var.aurora_database_name
      AURORA_PASSWORD      = var.aurora_enabled ? var.AURORA_MASTER_PASSWORD : ""
      DATA_LAKE_BUCKET     = module.s3_data_lake.bucket_id
      SQS_QUEUE_URL        = module.fund_data_sync_queue.queue_url
      LOG_LEVEL            = "INFO"
      PYTHONUNBUFFERED     = "1"  # Real-time CloudWatch Logs
    }
  }

  # Tracing
  tracing_config {
    mode = "Active"  # X-Ray tracing
  }

  # Dead Letter Queue (Lambda-level DLQ, in addition to SQS DLQ)
  dead_letter_config {
    target_arn = module.fund_data_sync_queue.dlq_arn
  }

  tags = merge(
    local.common_tags,
    {
      Name      = "${var.project_name}-fund-data-sync-${var.environment}"
      Component = "fund-data-sync"
      App       = "shared"
    }
  )

  depends_on = [
    aws_cloudwatch_log_group.fund_data_sync_lambda,
    aws_iam_role_policy_attachment.fund_data_sync_lambda_basic,
    aws_iam_role_policy_attachment.fund_data_sync_lambda_vpc,
    aws_iam_role_policy_attachment.fund_data_sync_lambda_xray
  ]
}

# Lambda Event Source Mapping (SQS → Lambda)
resource "aws_lambda_event_source_mapping" "fund_data_sync_sqs" {
  event_source_arn = module.fund_data_sync_queue.queue_arn
  function_name    = aws_lambda_function.fund_data_sync.arn
  enabled          = true

  # Batch Configuration
  batch_size                         = 10   # Process up to 10 messages per invocation
  maximum_batching_window_in_seconds = 5    # Wait up to 5s to collect batch

  # Error Handling
  function_response_types = ["ReportBatchItemFailures"]  # Enable partial batch response

  # Scaling Configuration
  scaling_config {
    maximum_concurrency = 10  # Max 10 concurrent Lambda invocations
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "fund_data_sync_lambda" {
  name              = "/aws/lambda/${var.project_name}-fund-data-sync-${var.environment}"
  retention_in_days = 7  # 7 days retention (adjust for compliance)

  tags = merge(
    local.common_tags,
    {
      Name      = "/aws/lambda/${var.project_name}-fund-data-sync-${var.environment}"
      Component = "fund-data-sync"
    }
  )
}

# ============================================================================
# Lambda IAM Role and Policies
# ============================================================================

# IAM Role
resource "aws_iam_role" "fund_data_sync_lambda" {
  name = "${var.project_name}-fund-data-sync-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name      = "${var.project_name}-fund-data-sync-lambda-${var.environment}"
      Component = "fund-data-sync"
    }
  )
}

# Basic Lambda Execution Policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "fund_data_sync_lambda_basic" {
  role       = aws_iam_role.fund_data_sync_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC Access Policy (ENI management)
resource "aws_iam_role_policy_attachment" "fund_data_sync_lambda_vpc" {
  role       = aws_iam_role.fund_data_sync_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# X-Ray Tracing Policy
resource "aws_iam_role_policy_attachment" "fund_data_sync_lambda_xray" {
  role       = aws_iam_role.fund_data_sync_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Custom Policy: S3 Data Lake Access
resource "aws_iam_role_policy" "fund_data_sync_s3" {
  name = "${var.project_name}-fund-data-sync-s3-${var.environment}"
  role = aws_iam_role.fund_data_sync_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectTagging"
        ]
        Resource = "${module.s3_data_lake.bucket_arn}/raw/sql_server/fund_data/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = module.s3_data_lake.bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["raw/sql_server/fund_data/*"]
          }
        }
      }
    ]
  })
}

# Custom Policy: SQS Access
resource "aws_iam_role_policy" "fund_data_sync_sqs" {
  name = "${var.project_name}-fund-data-sync-sqs-${var.environment}"
  role = aws_iam_role.fund_data_sync_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = module.fund_data_sync_queue.queue_arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = module.fund_data_sync_queue.dlq_arn
      }
    ]
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "fund_data_sync_lambda_arn" {
  description = "ARN of Fund Data Sync Lambda function"
  value       = aws_lambda_function.fund_data_sync.arn
}

output "fund_data_sync_queue_url" {
  description = "URL of Fund Data Sync SQS queue"
  value       = module.fund_data_sync_queue.queue_url
}

output "fund_data_sync_dlq_url" {
  description = "URL of Fund Data Sync Dead Letter Queue"
  value       = module.fund_data_sync_queue.dlq_url
}

output "fund_data_sync_ecr_repository_url" {
  description = "ECR repository URL for Fund Data Sync Lambda images"
  value       = aws_ecr_repository.fund_data_sync.repository_url
}
