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
