# CloudWatch Monitoring and Alarms for Telegram API

###############################################################################
# CloudWatch Alarms
###############################################################################

# Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-telegram-api-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda function error rate too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_api.function_name
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-errors-alarm-${var.environment}"
    Component = "monitoring"
  })
}

# Lambda Duration Alarm (slow responses)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-telegram-api-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 25000  # 25 seconds
  alarm_description   = "Lambda function taking too long"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_api.function_name
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-duration-alarm-${var.environment}"
    Component = "monitoring"
  })
}

# Lambda Throttles Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-telegram-api-throttles-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Lambda function being throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_api.function_name
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-throttles-alarm-${var.environment}"
    Component = "monitoring"
  })
}

# API Gateway 5xx Errors
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${var.project_name}-telegram-api-5xx-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gateway returning too many 5xx errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.telegram_api.id
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-5xx-alarm-${var.environment}"
    Component = "monitoring"
  })
}

# API Gateway 4xx Errors (info only, not alerting)
resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  alarm_name          = "${var.project_name}-telegram-api-4xx-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "4xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 100  # Higher threshold for 4xx (client errors)
  alarm_description   = "API Gateway returning many 4xx errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.telegram_api.id
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-4xx-alarm-${var.environment}"
    Component = "monitoring"
  })
}

###############################################################################
# CloudWatch Dashboard
###############################################################################

resource "aws_cloudwatch_dashboard" "telegram_api" {
  dashboard_name = "${var.project_name}-telegram-api-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Invocations & Errors"
          region  = var.aws_region
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.telegram_api.function_name, { stat = "Sum", period = 300 }],
            [".", "Errors", ".", ".", { stat = "Sum", period = 300, color = "#d62728" }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Duration"
          region  = var.aws_region
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.telegram_api.function_name, { stat = "Average", period = 300 }],
            [".", ".", ".", ".", { stat = "p95", period = 300, color = "#ff7f0e" }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "API Gateway Requests"
          region  = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.telegram_api.id, { stat = "Sum", period = 300 }],
            [".", "5xx", ".", ".", { stat = "Sum", period = 300, color = "#d62728" }],
            [".", "4xx", ".", ".", { stat = "Sum", period = 300, color = "#ff7f0e" }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "API Gateway Latency"
          region  = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.telegram_api.id, { stat = "Average", period = 300 }],
            [".", ".", ".", ".", { stat = "p95", period = 300, color = "#ff7f0e" }]
          ]
          view = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title   = "Lambda Concurrent Executions"
          region  = var.aws_region
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", aws_lambda_function.telegram_api.function_name, { stat = "Maximum", period = 60 }]
          ]
          view = "timeSeries"
        }
      }
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "cloudwatch_dashboard_url" {
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.telegram_api.dashboard_name}"
  description = "URL to the CloudWatch dashboard"
}
