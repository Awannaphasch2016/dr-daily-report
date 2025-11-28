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
# DLQ Messages Alarm (Failed Report Jobs)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-dlq-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Messages in DLQ - report jobs are failing"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.report_jobs_dlq.name
  }

  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
  ok_actions    = [aws_sns_topic.telegram_alerts.arn]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-dlq-messages-alarm-${var.environment}"
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
# Outputs
###############################################################################

output "sns_alerts_topic_arn" {
  value       = aws_sns_topic.telegram_alerts.arn
  description = "ARN of SNS topic for alarm notifications"
}
