# Precompute Workflow - Step Functions Orchestration
#
# Architecture Redesign (Sprint 4 of 5):
#   Replaces fire-and-forget SQS pattern with observable Step Functions orchestration
#
# Old pattern: Scheduler → SQS (47 messages) → ??? (no visibility)
# New pattern: Controller → Step Functions → SQS → Workers → Complete (full observability)
#
# Benefits:
# - Visual workflow dashboard
# - Built-in retry logic
# - Completion tracking
# - Error handling
# - Execution history

###############################################################################
# Step Functions State Machine
###############################################################################

# IAM Role for Step Functions
resource "aws_iam_role" "precompute_workflow_role" {
  name = "${var.project_name}-precompute-workflow-role-${var.environment}"

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
    Name      = "${var.project_name}-precompute-workflow-role-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-role"
  })
}

# IAM Policy for Step Functions to send SQS messages and invoke Lambda
resource "aws_iam_role_policy" "precompute_workflow_policy" {
  name = "${var.project_name}-precompute-workflow-policy-${var.environment}"
  role = aws_iam_role.precompute_workflow_role.id

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
      # SQS - Send messages to report jobs queue
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.report_jobs.arn
      },
      # Lambda - Invoke get_ticker_list function
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.get_ticker_list.arn
      }
    ]
  })
}

# Read state machine definition template and substitute variables
locals {
  precompute_workflow_definition = templatefile("${path.module}/step_functions/precompute_workflow.json", {
    sqs_queue_url                 = aws_sqs_queue.report_jobs.url
    region                        = var.aws_region
    account_id                    = data.aws_caller_identity.current.account_id
    get_ticker_list_function_name = aws_lambda_function.get_ticker_list.function_name
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "precompute_workflow" {
  name     = "${var.project_name}-precompute-workflow-${var.environment}"
  role_arn = aws_iam_role.precompute_workflow_role.arn

  definition = local.precompute_workflow_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.precompute_workflow_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-workflow-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-orchestration"
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "precompute_workflow_logs" {
  name = "/aws/vendedlogs/states/${var.project_name}-precompute-workflow-${var.environment}"
  # Note: retention_in_days removed - requires logs:PutRetentionPolicy permission
  # Logs will use default retention

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-workflow-logs-${var.environment}"
    App       = "telegram-api"
    Component = "step-functions-logging"
  })
}

###############################################################################
# Precompute Controller Lambda
###############################################################################

resource "aws_lambda_function" "precompute_controller" {
  function_name = "${var.project_name}-precompute-controller-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn

  # Container image deployment from ECR (same image as other Lambdas)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.precompute_controller_handler.lambda_handler"]
  }

  timeout     = 60
  memory_size = 256

  environment {
    variables = {
      ENVIRONMENT                    = var.environment
      LOG_LEVEL                      = "INFO"
      PRECOMPUTE_STATE_MACHINE_ARN  = aws_sfn_state_machine.precompute_workflow.arn
      # Note: AWS_REGION is automatically provided by Lambda, cannot be set manually
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-controller-${var.environment}"
    App       = "telegram-api"
    Component = "precompute-controller"
    Layer     = "orchestration"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_sfn_state_machine.precompute_workflow
  ]
}

# IAM Policy for precompute controller to start Step Functions executions
resource "aws_iam_role_policy" "precompute_controller_sfn_policy" {
  name = "${var.project_name}-precompute-controller-sfn-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:DescribeExecution",
          "states:ListExecutions"
        ]
        Resource = aws_sfn_state_machine.precompute_workflow.arn
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "precompute_controller_logs" {
  name              = "/aws/lambda/${aws_lambda_function.precompute_controller.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-controller-logs-${var.environment}"
    App       = "telegram-api"
    Component = "precompute-controller-logging"
  })
}

###############################################################################
# Get Ticker List Lambda (for Step Functions)
###############################################################################

resource "aws_lambda_function" "get_ticker_list" {
  function_name = "${var.project_name}-get-ticker-list-${var.environment}"
  role          = aws_iam_role.get_ticker_list_role.arn

  # Container image deployment from ECR (same image as other Lambdas)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.get_ticker_list_handler.lambda_handler"]
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
    }
  }

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-get-ticker-list-${var.environment}"
    App       = "telegram-api"
    Component = "ticker-list-query"
    Layer     = "data"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_rds_cluster.aurora
  ]
}

# IAM Role for Get Ticker List Lambda
resource "aws_iam_role" "get_ticker_list_role" {
  name = "${var.project_name}-get-ticker-list-role-${var.environment}"

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
    Name      = "${var.project_name}-get-ticker-list-role-${var.environment}"
    App       = "telegram-api"
    Component = "get-ticker-list-role"
  })
}

# VPC + CloudWatch Logs permissions
resource "aws_iam_role_policy_attachment" "get_ticker_list_vpc" {
  role       = aws_iam_role.get_ticker_list_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "get_ticker_list_logs" {
  name              = "/aws/lambda/${aws_lambda_function.get_ticker_list.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-get-ticker-list-logs-${var.environment}"
    App       = "telegram-api"
    Component = "get-ticker-list-logging"
  })
}

###############################################################################
# Precompute Controller Alias
###############################################################################

# Lambda Alias
resource "aws_lambda_alias" "precompute_controller_live" {
  name             = "live"
  description      = "Production alias for precompute controller"
  function_name    = aws_lambda_function.precompute_controller.function_name
  function_version = "$LATEST"

  lifecycle {
    ignore_changes = [function_version]
  }
}

###############################################################################
# Outputs
###############################################################################

output "precompute_workflow_arn" {
  value       = aws_sfn_state_machine.precompute_workflow.arn
  description = "ARN of the precompute Step Functions state machine"
}

output "precompute_workflow_console_url" {
  value       = "https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.precompute_workflow.arn}"
  description = "AWS Console URL for precompute workflow"
}

output "precompute_controller_function_name" {
  value       = aws_lambda_function.precompute_controller.function_name
  description = "Name of the precompute controller Lambda function"
}

output "precompute_controller_function_arn" {
  value       = aws_lambda_function.precompute_controller.arn
  description = "ARN of the precompute controller Lambda function"
}

output "precompute_schedule" {
  value       = "Triggered automatically by EventBridge Scheduler at 5:00 AM Bangkok time"
  description = "Precompute workflow schedule (invoked by scheduler Lambda)"
}
