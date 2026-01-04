# PDF Generation Workflow - Step Functions Orchestration
#
# Two-Stage Architecture:
#   Step Function 1 (precompute_workflow.tf): Generate reports → Store to Aurora (WITHOUT PDF)
#   Step Function 2 (this file): Query Aurora → Generate PDFs → UPDATE Aurora with PDF metadata
#
# Pattern: Triggered by EventBridge when precompute workflow completes
#
# Benefits:
# - Clean separation of concerns (reports vs PDFs)
# - Independent retry logic (PDF failures don't fail reports)
# - Can run on different schedules
# - Observable PDF generation process

###############################################################################
# Step Functions State Machine
###############################################################################

# IAM Role for Step Functions
resource "aws_iam_role" "pdf_workflow_role" {
  name = "${var.project_name}-pdf-workflow-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pdf-workflow-role-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-role"
  })
}

# IAM Policy for Step Functions to invoke Lambdas directly
# MIGRATED: Removed SQS permissions (no longer using SQS queue pattern)
resource "aws_iam_role_policy" "pdf_workflow_policy" {
  name = "${var.project_name}-pdf-workflow-policy-${var.environment}"
  role = aws_iam_role.pdf_workflow_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      # Lambda - Invoke get_report_list and pdf_worker functions
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.get_report_list.arn,
          aws_lambda_function.pdf_worker.arn
        ]
      }
    ]
  })
}

# Read state machine definition template and substitute variables
# MIGRATED: Using direct Lambda invocation pattern (no SQS)
# Migration date: 2026-01-04
# Previous: pdf_workflow.json (SQS-based with 3-minute blind wait)
# Current: pdf_workflow_direct.json (direct invocation with real-time completion)
locals {
  pdf_workflow_definition = templatefile("${path.module}/step_functions/pdf_workflow_direct.json", {
    get_report_list_function_arn = aws_lambda_function.get_report_list.arn
    pdf_worker_function_arn      = aws_lambda_function.pdf_worker.arn
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "pdf_workflow" {
  name     = "${var.project_name}-pdf-workflow-${var.environment}"
  role_arn = aws_iam_role.pdf_workflow_role.arn

  definition = local.pdf_workflow_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.pdf_workflow_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pdf-workflow-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-orchestration"
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "pdf_workflow_logs" {
  name = "/aws/vendedlogs/states/${var.project_name}-pdf-workflow-${var.environment}"
  # Note: retention_in_days removed - requires logs:PutRetentionPolicy permission
  # Logs will use default retention

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pdf-workflow-logs-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-logging"
  })
}

###############################################################################
# SQS Queue for PDF Jobs (REMOVED - replaced by direct Lambda invocation)
###############################################################################
# REMOVAL DATE: 2026-01-04
# Migration completed: 2026-01-04
# Previous pattern: Step Functions → SQS → Lambda (async processing)
# Current pattern: Step Functions → Lambda (direct invocation)
#
# Validation: Zero SQS messages for 2 days (2026-01-02 to 2026-01-04)
# Lambda event source mapping: DELETED 2026-01-04T15:35:29
# Terraform resources: REMOVED 2026-01-04
#
# Related: .claude/validations/2026-01-04-sqs-usage-pdf-workflow.md
###############################################################################

# resource "aws_sqs_queue" "pdf_jobs" {
#   name                       = "${var.project_name}-pdf-jobs-${var.environment}"
#   visibility_timeout_seconds = 300 # 5 minutes (PDF generation timeout)
#   message_retention_seconds  = 1209600 # 14 days
#   receive_wait_time_seconds  = 20 # Long polling
#
#   # Dead Letter Queue configuration
#   redrive_policy = jsonencode({
#     deadLetterTargetArn = aws_sqs_queue.pdf_jobs_dlq.arn
#     maxReceiveCount     = 3
#   })
#
#   tags = merge(local.common_tags, {
#     Name      = "${var.project_name}-pdf-jobs-${var.environment}"
#     App       = "telegram-api"
#     Component = "pdf-job-queue"
#   })
# }
#
# # Dead Letter Queue for failed PDF jobs
# resource "aws_sqs_queue" "pdf_jobs_dlq" {
#   name                      = "${var.project_name}-pdf-jobs-dlq-${var.environment}"
#   message_retention_seconds = 1209600 # 14 days
#
#   tags = merge(local.common_tags, {
#     Name      = "${var.project_name}-pdf-jobs-dlq-${var.environment}"
#     App       = "telegram-api"
#     Component = "pdf-job-dlq"
#   })
# }

###############################################################################
# Get Report List Lambda (for Step Functions)
###############################################################################

resource "aws_lambda_function" "get_report_list" {
  function_name = "${var.project_name}-get-report-list-${var.environment}"
  role          = aws_iam_role.get_report_list_role.arn

  # Container image deployment from ECR (same image as other Lambdas)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.get_report_list_handler.lambda_handler"]
  }

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      LOG_LEVEL        = "INFO"
      AURORA_HOST      = aws_rds_cluster.aurora.endpoint
      AURORA_PORT      = "3306"
      AURORA_DATABASE  = var.aurora_database_name
      AURORA_USER      = var.aurora_master_username
      AURORA_PASSWORD  = var.AURORA_MASTER_PASSWORD

      # Timezone (Principle #16: Timezone Discipline)
      TZ               = "Asia/Bangkok"
    }
  }

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-get-report-list-${var.environment}"
    App       = "telegram-api"
    Component = "report-list-query"
    Layer     = "data"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_rds_cluster.aurora
  ]
}

# IAM Role for Get Report List Lambda
resource "aws_iam_role" "get_report_list_role" {
  name = "${var.project_name}-get-report-list-role-${var.environment}"

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
    Name      = "${var.project_name}-get-report-list-role-${var.environment}"
    App       = "telegram-api"
    Component = "get-report-list-role"
  })
}

# VPC + CloudWatch Logs permissions
resource "aws_iam_role_policy_attachment" "get_report_list_vpc" {
  role       = aws_iam_role.get_report_list_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "get_report_list_logs" {
  name              = "/aws/lambda/${aws_lambda_function.get_report_list.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-get-report-list-logs-${var.environment}"
    App       = "telegram-api"
    Component = "get-report-list-logging"
  })
}

###############################################################################
# PDF Worker Lambda
###############################################################################

resource "aws_lambda_function" "pdf_worker" {
  function_name = "${var.project_name}-pdf-worker-${var.environment}"
  role          = aws_iam_role.pdf_worker_role.arn

  # Container image deployment from ECR (same image as other Lambdas)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.pdf_worker_handler.handler"]
  }

  timeout     = 600 # 10 minutes (handles large PDFs with complex charts and S3 upload time)
  memory_size = 512 # PDF generation needs more memory (ReportLab)

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      LOG_LEVEL            = "INFO"
      AURORA_HOST          = aws_rds_cluster.aurora.endpoint
      AURORA_PORT          = "3306"
      AURORA_DATABASE      = var.aurora_database_name
      AURORA_USER          = var.aurora_master_username
      AURORA_PASSWORD      = var.AURORA_MASTER_PASSWORD
      PDF_BUCKET_NAME      = aws_s3_bucket.pdf_reports.id
      PDF_STORAGE_BUCKET   = aws_s3_bucket.pdf_reports.id

      # Timezone (Principle #16: Timezone Discipline)
      TZ                   = "Asia/Bangkok"
    }
  }

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pdf-worker-${var.environment}"
    App       = "telegram-api"
    Component = "pdf-generation-worker"
    Layer     = "worker"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_rds_cluster.aurora,
    aws_s3_bucket.pdf_reports
  ]
}

# IAM Role for PDF Worker Lambda
resource "aws_iam_role" "pdf_worker_role" {
  name = "${var.project_name}-pdf-worker-role-${var.environment}"

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
    Name      = "${var.project_name}-pdf-worker-role-${var.environment}"
    App       = "telegram-api"
    Component = "pdf-worker-role"
  })
}

# VPC + CloudWatch Logs permissions
resource "aws_iam_role_policy_attachment" "pdf_worker_vpc" {
  role       = aws_iam_role.pdf_worker_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# S3 permissions for PDF uploads
resource "aws_iam_role_policy" "pdf_worker_s3_policy" {
  name = "${var.project_name}-pdf-worker-s3-${var.environment}"
  role = aws_iam_role.pdf_worker_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      }
    ]
  })
}

# SQS permissions for PDF worker (REMOVED - no longer uses SQS)
# REMOVAL DATE: 2026-01-04
# PDF worker now invoked directly by Step Functions, not via SQS queue

# resource "aws_iam_role_policy" "pdf_worker_sqs_policy" {
#   name = "${var.project_name}-pdf-worker-sqs-${var.environment}"
#   role = aws_iam_role.pdf_worker_role.id
#
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Effect = "Allow"
#         Action = [
#           "sqs:ReceiveMessage",
#           "sqs:DeleteMessage",
#           "sqs:GetQueueAttributes"
#         ]
#         Resource = aws_sqs_queue.pdf_jobs.arn
#       }
#     ]
#   })
# }

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "pdf_worker_logs" {
  name              = "/aws/lambda/${aws_lambda_function.pdf_worker.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pdf-worker-logs-${var.environment}"
    App       = "telegram-api"
    Component = "pdf-worker-logging"
  })
}

# Event Source Mapping - SQS → PDF Worker Lambda (REMOVED)
# REMOVAL DATE: 2026-01-04T15:35:29
# Replaced by: Direct Lambda invocation via Step Functions
# No longer needed with direct Lambda invocation pattern
# Deleted via AWS CLI: aws lambda delete-event-source-mapping --uuid 3b9f810d-ae93-4657-8cfb-e41dd63fa23b

# resource "aws_lambda_event_source_mapping" "pdf_jobs_to_worker" {
#   event_source_arn = aws_sqs_queue.pdf_jobs.arn
#   function_name    = aws_lambda_function.pdf_worker.arn
#   batch_size       = 1 # Process one PDF at a time (memory-intensive)
#   enabled          = true
#
#   # Scaling configuration
#   scaling_config {
#     maximum_concurrency = 10 # Max 10 PDFs in parallel
#   }
# }

###############################################################################
# EventBridge Rule - Trigger PDF workflow when precompute workflow completes
###############################################################################

resource "aws_cloudwatch_event_rule" "precompute_complete" {
  name        = "${var.project_name}-precompute-complete-${var.environment}"
  description = "Trigger PDF workflow when precompute workflow completes"

  event_pattern = jsonencode({
    source      = ["aws.states"]
    detail-type = ["Step Functions Execution Status Change"]
    detail = {
      status          = ["SUCCEEDED"]
      stateMachineArn = [aws_sfn_state_machine.precompute_workflow.arn]
    }
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-complete-rule-${var.environment}"
    App       = "telegram-api"
    Component = "eventbridge-rule"
  })
}

# EventBridge Target - Start PDF workflow
resource "aws_cloudwatch_event_target" "start_pdf_workflow" {
  rule      = aws_cloudwatch_event_rule.precompute_complete.name
  target_id = "StartPDFWorkflow"
  arn       = aws_sfn_state_machine.pdf_workflow.arn
  role_arn  = aws_iam_role.eventbridge_sfn_role.arn

  # Input transformer: Extract timestamp and pass as report_date
  # EventBridge provides UTC timestamp, Lambda will convert to Bangkok timezone
  input_transformer {
    input_paths = {
      event_time = "$.time"
    }
    input_template = <<EOF
{
  "report_date": "<event_time>"
}
EOF
  }
}

# IAM Role for EventBridge to start Step Functions
resource "aws_iam_role" "eventbridge_sfn_role" {
  name = "${var.project_name}-eventbridge-sfn-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-eventbridge-sfn-role-${var.environment}"
    App       = "telegram-api"
    Component = "eventbridge-role"
  })
}

# IAM Policy for EventBridge to start PDF workflow
resource "aws_iam_role_policy" "eventbridge_sfn_policy" {
  name = "${var.project_name}-eventbridge-sfn-policy-${var.environment}"
  role = aws_iam_role.eventbridge_sfn_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.pdf_workflow.arn
      }
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "pdf_workflow_arn" {
  value       = aws_sfn_state_machine.pdf_workflow.arn
  description = "ARN of the PDF Step Functions state machine"
}

output "pdf_workflow_console_url" {
  value       = "https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.pdf_workflow.arn}"
  description = "AWS Console URL for PDF workflow"
}

# output "pdf_jobs_queue_url" {
#   value       = aws_sqs_queue.pdf_jobs.url
#   description = "URL of the PDF jobs SQS queue (REMOVED 2026-01-04)"
# }

output "pdf_worker_function_name" {
  value       = aws_lambda_function.pdf_worker.function_name
  description = "Name of the PDF worker Lambda function"
}

output "get_report_list_function_name" {
  value       = aws_lambda_function.get_report_list.function_name
  description = "Name of the get report list Lambda function"
}
