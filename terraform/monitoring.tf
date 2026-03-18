# CloudWatch Monitoring and Alarms for Telegram Mini App
# Provides observability into system health and error rates

###############################################################################
# SNS Topic for Alarm Notifications (Optional)
###############################################################################

resource "aws_sns_topic" "telegram_alerts" {
  name = "${var.project_name}-telegram-alerts-${var.environment}"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-alerts-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# Lambda Error Rate Alarm
###############################################################################

resource "aws_cloudwatch_metric_alarm" "telegram_api_errors" {
  alarm_name          = "${var.project_name}-telegram-api-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Telegram API Lambda error rate is high (>5 errors in 5 minutes)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_api.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-errors-alarm-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# Report Worker Lambda Error Alarm
###############################################################################

resource "aws_cloudwatch_metric_alarm" "report_worker_errors" {
  alarm_name          = "${var.project_name}-report-worker-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Report Worker Lambda error rate is high (>3 errors in 5 minutes)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.report_worker.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-report-worker-errors-alarm-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# API Gateway 5xx Errors Alarm
###############################################################################

resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${var.project_name}-api-5xx-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gateway 5xx error rate is high (>10 errors in 5 minutes)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.telegram_api.id
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-api-5xx-alarm-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# API Gateway 4xx Errors Alarm (Client Errors - informational)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  alarm_name          = "${var.project_name}-api-4xx-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3  # More lenient - 3 periods
  metric_name         = "4xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 50  # Higher threshold - client errors are common
  alarm_description   = "API Gateway 4xx error rate is high (>50 errors in 15 minutes)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.telegram_api.id
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  # No ok_actions - don't spam on recovery

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-api-4xx-alarm-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# Lambda Duration Alarm (Approaching Timeout)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "telegram_api_duration" {
  alarm_name          = "${var.project_name}-telegram-api-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 45000  # 45 seconds (Lambda timeout is 60s)
  alarm_description   = "Telegram API Lambda average duration is approaching timeout"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_api.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-duration-alarm-${var.environment}"
    App       = "telegram-api"
    Component = "monitoring"
  })
}

###############################################################################
# Slack Notifier Lambda (SNS → Slack bridge)
###############################################################################

# IAM Role for Slack Notifier Lambda
resource "aws_iam_role" "slack_notifier" {
  name = "${var.project_name}-slack-notifier-role-${var.environment}"

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
    Name      = "${var.project_name}-slack-notifier-role-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

# IAM Policy for Slack Notifier (CloudWatch Logs only)
resource "aws_iam_role_policy" "slack_notifier" {
  name = "${var.project_name}-slack-notifier-policy-${var.environment}"
  role = aws_iam_role.slack_notifier.id

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
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-slack-notifier-${var.environment}:*"
      }
    ]
  })
}

# Slack Notifier Lambda Function
resource "aws_lambda_function" "slack_notifier" {
  function_name = "${var.project_name}-slack-notifier-${var.environment}"
  role          = aws_iam_role.slack_notifier.arn
  handler       = "slack_notifier.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  # Use zip deployment for simple Python function
  filename         = data.archive_file.slack_notifier.output_path
  source_code_hash = data.archive_file.slack_notifier.output_base64sha256

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.SLACK_WEBHOOK_URL
      ENVIRONMENT       = var.environment
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-slack-notifier-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

# Archive the Slack notifier source code
data "archive_file" "slack_notifier" {
  type        = "zip"
  source_file = "${path.module}/../src/alerting/slack_notifier.py"
  output_path = "${path.module}/.terraform/tmp/slack_notifier.zip"
}

# CloudWatch Log Group for Slack Notifier
resource "aws_cloudwatch_log_group" "slack_notifier" {
  name              = "/aws/lambda/${aws_lambda_function.slack_notifier.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-slack-notifier-logs-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

# SNS → Lambda Subscription (triggers Slack notifier on alarm)
resource "aws_sns_topic_subscription" "slack_notifier" {
  topic_arn = aws_sns_topic.telegram_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_notifier.arn
}

# Lambda permission for SNS to invoke
resource "aws_lambda_permission" "slack_notifier_sns" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_notifier.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.telegram_alerts.arn
}

###############################################################################
# Scheduler Lambda Error Alarm (CRITICAL - Data Pipeline)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "scheduler_errors" {
  alarm_name          = "${var.project_name}-scheduler-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1  # Any error is critical for scheduler
  alarm_description   = "CRITICAL: Scheduler Lambda failed - data pipeline may not run"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ticker_scheduler.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-scheduler-errors-alarm-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

###############################################################################
# Precompute Controller Lambda Error Alarm (CRITICAL - Data Pipeline)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "precompute_errors" {
  alarm_name          = "${var.project_name}-precompute-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1  # Any error is critical for precompute
  alarm_description   = "CRITICAL: Precompute Controller failed - cached reports may be stale"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.precompute_controller.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-errors-alarm-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

###############################################################################
# LINE Bot Lambda Error Alarm (HIGH - User-facing)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "line_bot_errors" {
  alarm_name          = "${var.project_name}-line-bot-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "HIGH: LINE Bot Lambda error rate is high (>5 errors in 5 minutes)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.line_bot.function_name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-line-bot-errors-alarm-${var.environment}"
    App       = "line-bot"
    Component = "monitoring"
  })
}

###############################################################################
# Step Functions Failure Alarm (CRITICAL - Workflow Failures)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "precompute_workflow_failures" {
  alarm_name          = "${var.project_name}-precompute-workflow-failures-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 1  # Any workflow failure is critical
  alarm_description   = "CRITICAL: Precompute Step Functions workflow failed"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.precompute_workflow.arn
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-workflow-failures-alarm-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

###############################################################################
# OpenRouter Credit Checker Lambda (ZIP Deployment)
###############################################################################

# IAM Role for Credit Checker Lambda
resource "aws_iam_role" "credit_checker" {
  name = "${var.project_name}-credit-checker-role-${var.environment}"

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
    Name      = "${var.project_name}-credit-checker-role-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

# IAM Policy: CloudWatch Logs + PutMetricData + GetMetricStatistics
resource "aws_iam_role_policy" "credit_checker" {
  name = "${var.project_name}-credit-checker-policy-${var.environment}"
  role = aws_iam_role.credit_checker.id

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
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-credit-checker-${var.environment}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*" # PutMetricData does not support resource-level permissions
      }
    ]
  })
}

# Archive the credit checker source code
data "archive_file" "credit_checker" {
  type        = "zip"
  source_file = "${path.module}/../src/alerting/credit_checker.py"
  output_path = "${path.module}/.terraform/tmp/credit_checker.zip"
}

# Credit Checker Lambda Function
resource "aws_lambda_function" "credit_checker" {
  function_name = "${var.project_name}-credit-checker-${var.environment}"
  role          = aws_iam_role.credit_checker.arn
  handler       = "credit_checker.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  # Use zip deployment for simple Python function (same pattern as slack_notifier)
  filename         = data.archive_file.credit_checker.output_path
  source_code_hash = data.archive_file.credit_checker.output_base64sha256

  environment {
    variables = {
      OPENROUTER_API_KEY     = var.OPENROUTER_API_KEY
      LANGFUSE_PUBLIC_KEY    = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY    = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST          = var.LANGFUSE_HOST
      SLACK_WEBHOOK_URL      = var.SLACK_WEBHOOK_URL
      ENVIRONMENT            = var.environment
      ESTIMATED_DAILY_COST   = "2.5"
      GRAFANA_DASHBOARD_URL  = ""
      COST_MARGIN            = "1.5"
    }
  }

  # No VPC - only calls external APIs (OpenRouter, Langfuse, CloudWatch, Slack)

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-credit-checker-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

# CloudWatch Log Group for Credit Checker
resource "aws_cloudwatch_log_group" "credit_checker" {
  name              = "/aws/lambda/${aws_lambda_function.credit_checker.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-credit-checker-logs-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

###############################################################################
# Credit Checker EventBridge Schedule (every 6 hours)
###############################################################################

# Allow EventBridge Scheduler to invoke credit checker Lambda
resource "aws_iam_role_policy" "eventbridge_scheduler_credit_checker" {
  name = "${var.project_name}-scheduler-credit-checker-invoke-${var.environment}"
  role = aws_iam_role.eventbridge_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction"
      ]
      Resource = [
        aws_lambda_function.credit_checker.arn
      ]
    }]
  })
}

resource "aws_scheduler_schedule" "credit_checker" {
  name       = "${var.project_name}-credit-checker-${var.environment}"
  group_name = "default"

  flexible_time_window {
    mode = "OFF" # Execute exactly at scheduled time
  }

  # Every 6 hours Bangkok time: 5AM, 11AM, 5PM, 11PM
  # 11PM check = 6h warning before 5AM scheduler
  schedule_expression          = "cron(0 5,11,17,23 * * ? *)"
  schedule_expression_timezone = "Asia/Bangkok"

  state = "ENABLED"

  target {
    arn      = aws_lambda_function.credit_checker.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    input = jsonencode({
      source = "eventbridge-scheduler"
    })

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600
    }
  }

  depends_on = [
    aws_iam_role.eventbridge_scheduler,
    aws_iam_role_policy.eventbridge_scheduler_credit_checker
  ]
}

###############################################################################
# Credit Balance CloudWatch Alarm (backup alert via SNS → Slack notifier)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "credit_balance_low" {
  alarm_name          = "${var.project_name}-openrouter-credit-low-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CreditBalance"
  namespace           = "DR/OpenRouter"
  period              = 21600 # 6 hours (matches check frequency)
  statistic           = "Minimum"
  threshold           = 5
  alarm_description   = "CRITICAL: OpenRouter credit balance below $5 - daily reports will fail with HTTP 402. Top up at https://openrouter.ai/settings/credits"
  treat_missing_data  = "breaching" # Alert if credit checker stops running

  dimensions = {
    Environment = var.environment
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-credit-balance-alarm-${var.environment}"
    App       = "shared"
    Component = "monitoring"
  })
}

###############################################################################
# Outputs
###############################################################################

output "sns_alerts_topic_arn" {
  value       = aws_sns_topic.telegram_alerts.arn
  description = "ARN of SNS topic for alarm notifications"
}

output "slack_notifier_function_name" {
  value       = aws_lambda_function.slack_notifier.function_name
  description = "Name of the Slack notifier Lambda function"
}

output "credit_checker_function_name" {
  value       = aws_lambda_function.credit_checker.function_name
  description = "Name of the credit checker Lambda function"
}
