# Stage 2c — /tf-aws absorb stubs (Chunk A: Lambdas + aliases + log groups)
# Created: 2026-05-02 by Stage 2 of the dr-bot replica reconciliation
# See: .claude/journals/architecture/2026-04-30-quant-agent-rename.md
#      .claude/replicas/dr-bot.yaml
#
# These resources existed in AWS-live as ORPHANs (Edge B: not in .tfstate).
# The stubs below are minimal — field-level reconciliation deferred to Stage 4.
# `lifecycle.ignore_changes` is used aggressively for fields that are
# Doppler-injected (environment), CI/CD-managed (image_uri, last_modified,
# code_sha256), or auto-rotating (function_version on aliases).
#
# Note on ECR repo: webhook_health and model_catalog_sync are deployed from a
# different ECR repo (dr-daily-report-telegram-api, not in TFM). The
# image_uri reference below uses aws_ecr_repository.lambda.repository_url for
# stub-syntax purposes only; ignore_changes suppresses the resulting diff.
# Tracking the missing ECR repo as a separate Edge-B finding for Stage 3.

###############################################################################
# Lambda: webhook_health (scheduled health check, 5min cadence)
###############################################################################

resource "aws_lambda_function" "webhook_health" {
  function_name = "dr-daily-report-webhook-health-dev"
  role          = aws_iam_role.telegram_lambda_role.arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.scheduler.webhook_health_handler.lambda_handler"]
  }

  memory_size = 256
  timeout     = 60
  publish     = true

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  environment {
    variables = {
      TZ = "Asia/Bangkok"
    }
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-webhook-health-dev"
    App       = "telegram-api"
    Component = "webhook-health"
  })

  lifecycle {
    ignore_changes = [
      image_uri,
      environment,
      tags,
      tags_all,
    ]
  }
}

resource "aws_lambda_alias" "webhook_health_live" {
  name             = "live"
  description      = "Production alias for webhook health Lambda"
  function_name    = aws_lambda_function.webhook_health.function_name
  function_version = aws_lambda_function.webhook_health.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

###############################################################################
# Lambda: model_catalog_sync (daily OpenRouter model catalog refresh)
###############################################################################

resource "aws_lambda_function" "model_catalog_sync" {
  function_name = "dr-daily-report-model-catalog-sync-dev"
  role          = aws_iam_role.telegram_lambda_role.arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.alerting.model_catalog_sync.lambda_handler"]
  }

  memory_size = 256
  timeout     = 60
  publish     = true

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  environment {
    variables = {
      TZ = "Asia/Bangkok"
    }
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-model-catalog-sync-dev"
    App       = "telegram-api"
    Component = "model-catalog-sync"
  })

  lifecycle {
    ignore_changes = [
      image_uri,
      environment,
      tags,
      tags_all,
    ]
  }
}

resource "aws_lambda_alias" "model_catalog_sync_live" {
  name             = "live"
  description      = "Production alias for model catalog sync Lambda"
  function_name    = aws_lambda_function.model_catalog_sync.function_name
  function_version = aws_lambda_function.model_catalog_sync.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

###############################################################################
# CloudWatch Log Groups (always_import_classes per dr-bot.yaml triage)
###############################################################################

resource "aws_cloudwatch_log_group" "webhook_health" {
  name              = "/aws/lambda/dr-daily-report-webhook-health-dev"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name      = "/aws/lambda/dr-daily-report-webhook-health-dev"
    App       = "telegram-api"
    Component = "webhook-health"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_cloudwatch_log_group" "model_catalog_sync" {
  name              = "/aws/lambda/dr-daily-report-model-catalog-sync-dev"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name      = "/aws/lambda/dr-daily-report-model-catalog-sync-dev"
    App       = "telegram-api"
    Component = "model-catalog-sync"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_cloudwatch_log_group" "quant_agent" {
  name = "/aws/lambda/dr-daily-report-quant-agent-dev"
  # Live AWS log group has retention=null (Never expire).
  # Matching reality here keeps Chunk A's plan clean; aligning to 30d policy
  # convention is deferred to Stage 4 (configuration reconciliation).

  tags = merge(local.common_tags, {
    Name      = "/aws/lambda/dr-daily-report-quant-agent-dev"
    App       = "telegram-api"
    Component = "quant-agent"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

###############################################################################
# Chunk B (2026-05-02): error alarms + EventBridge scheduler chain
###############################################################################
# - 2 CloudWatch alarms watching Lambda Errors metric, alerting via SNS
# - 2 IAM roles for EventBridge Scheduler to assume + invoke each Lambda
# - 2 inline policies on those roles granting lambda:InvokeFunction
# - 2 schedulers (cron in Asia/Bangkok timezone) targeting the :live aliases
###############################################################################

###############################################################################
# CloudWatch Error Alarms
###############################################################################

resource "aws_cloudwatch_metric_alarm" "webhook_health_errors" {
  alarm_name          = "dr-daily-report-webhook-health-dev-errors-dev"
  alarm_description   = "Webhook health check Lambda errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 86400
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.telegram_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.webhook_health.function_name
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-webhook-health-dev-errors-dev"
    App       = "telegram-api"
    Component = "webhook-health-alarm"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_cloudwatch_metric_alarm" "model_catalog_sync_errors" {
  alarm_name          = "dr-daily-report-model-catalog-sync-dev-errors-dev"
  alarm_description   = "Model catalog sync Lambda errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 86400
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.telegram_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.model_catalog_sync.function_name
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-model-catalog-sync-dev-errors-dev"
    App       = "telegram-api"
    Component = "model-catalog-sync-alarm"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

###############################################################################
# EventBridge Scheduler IAM Roles
###############################################################################

resource "aws_iam_role" "scheduler_model_catalog" {
  name = "dr-daily-report-scheduler-model-catalog-dev"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-scheduler-model-catalog-dev"
    App       = "telegram-api"
    Component = "scheduler-iam"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_role" "scheduler_webhook_health" {
  name = "dr-daily-report-scheduler-webhook-health-dev"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-scheduler-webhook-health-dev"
    App       = "telegram-api"
    Component = "scheduler-iam"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

###############################################################################
# Inline policies: scheduler invoke-lambda
###############################################################################

resource "aws_iam_role_policy" "scheduler_model_catalog_invoke_lambda" {
  name = "invoke-lambda"
  role = aws_iam_role.scheduler_model_catalog.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "lambda:InvokeFunction"
      Resource = [
        aws_lambda_function.model_catalog_sync.arn,
        "${aws_lambda_function.model_catalog_sync.arn}:*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_webhook_health_invoke_lambda" {
  name = "invoke-lambda"
  role = aws_iam_role.scheduler_webhook_health.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "lambda:InvokeFunction"
      Resource = [
        aws_lambda_function.webhook_health.arn,
        "${aws_lambda_function.webhook_health.arn}:*",
      ]
    }]
  })
}

###############################################################################
# EventBridge Schedulers
###############################################################################

resource "aws_scheduler_schedule" "model_catalog_sync" {
  name                         = "dr-daily-report-model-catalog-sync-dev"
  group_name                   = "default"
  schedule_expression          = "cron(0 4 * * ? *)"
  schedule_expression_timezone = "Asia/Bangkok"
  state                        = "ENABLED"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 60
  }

  target {
    arn      = aws_lambda_alias.model_catalog_sync_live.arn
    role_arn = aws_iam_role.scheduler_model_catalog.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}

resource "aws_scheduler_schedule" "webhook_health" {
  name                         = "dr-daily-report-webhook-health-dev"
  group_name                   = "default"
  schedule_expression          = "cron(0 5 * * ? *)"
  schedule_expression_timezone = "Asia/Bangkok"
  state                        = "ENABLED"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 60
  }

  target {
    arn      = aws_lambda_alias.webhook_health_live.arn
    role_arn = aws_iam_role.scheduler_webhook_health.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }
}

###############################################################################
# Stage 3 imports (2026-05-02): preserve real-but-untracked AWS resources
###############################################################################
# Per .claude/journals/architecture/2026-05-02-stage-3-advisory-deletes.md:
#   #6: Grafana SG (real dependency: Aurora SG ingress)
#   #9: Grafana IAM role (paired with #6)
#  #11: ECR repo dr-daily-report-telegram-api (used by webhook_health,
#       model_catalog_sync Lambdas)
###############################################################################

resource "aws_security_group" "grafana" {
  name        = "dr-daily-report-grafana-dev"
  description = "Security group for Managed Grafana VPC connectivity"
  vpc_id      = "vpc-0fb04b10ef8c3d18b" # project VPC; replace with data source ref in Stage 4 cleanup if desired

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-grafana-sg"
    App       = "shared"
    Component = "grafana-security-group"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_role" "grafana" {
  name        = "dr-daily-report-grafana-role-dev"
  description = "Role assumed by Managed Grafana for CloudWatch + SNS data sources"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "grafana.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-grafana-role-dev"
    App       = "shared"
    Component = "grafana-iam"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

# Inline policies on the Grafana role — minimal stubs so import succeeds.
# Field-level policy reconciliation deferred to Stage 4 (pull AWS reality
# into the policy doc once the role is bound).
resource "aws_iam_role_policy" "grafana_cloudwatch" {
  name = "dr-daily-report-grafana-cloudwatch-dev"
  role = aws_iam_role.grafana.id

  # Stub policy — actual policy fetched from AWS on import; ignore_changes
  # below prevents an apply from clobbering reality before Stage 4 fixes
  # the source declaration.
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = []
  })

  lifecycle {
    ignore_changes = [policy]
  }
}

resource "aws_iam_role_policy" "grafana_sns" {
  name = "dr-daily-report-grafana-sns-dev"
  role = aws_iam_role.grafana.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = []
  })

  lifecycle {
    ignore_changes = [policy]
  }
}

resource "aws_ecr_repository" "telegram_api" {
  name                 = "dr-daily-report-telegram-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name      = "dr-daily-report-telegram-api"
    App       = "telegram-api"
    Component = "ecr-repo"
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}
