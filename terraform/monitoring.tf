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
