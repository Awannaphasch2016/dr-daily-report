# Precompute Consumer — second instance of the Throttled Pipeline pattern
#
# Pattern: Source -> Buffered Queue (with DLQ) -> Paced Consumer (bounded
# concurrency) -> Sink. First instance is fund_data_sync (Aurora-bound,
# max_concurrency=10); this is the second (Yahoo-IP-bound, max_concurrency=5).
#
# What this file declares:
#   1. SQS queue + DLQ (via shared module terraform/modules/sqs-etl-queue/)
#   2. precompute_consumer Lambda — same image as report-worker, command override
#   3. Event Source Mapping with maximum_concurrency=5 (the throttle)
#   4. IAM policy for the Lambda (SQS receive/delete + DLQ send) added inline
#      to the existing telegram_lambda_role
#   5. IAM policy for the precompute_workflow Step Functions role to allow
#      sqs:SendMessage on the queue (the SFN Map iterator now enqueues
#      instead of invoking the worker directly)
#
# What this file does NOT declare:
#   - The SFN Map iterator itself — that's modified in
#     terraform/step_functions/precompute_workflow.json (Lambda invoke -> sqs:sendMessage)
#   - The queue URL is wired into the SFN templatefile() call in
#     terraform/precompute_workflow.tf
#
# Companion docs:
#   docs/architecture/c4-plantuml/rendered/rate_limit_solutions_design.html

###############################################################################
# SQS Queue (Buffer) + DLQ via shared module
###############################################################################

module "precompute_queue" {
  source = "./modules/sqs-etl-queue"

  queue_name = "precompute-tickers-${var.environment}"

  # Visibility timeout > Lambda timeout. Consumer Lambda timeout = 120s
  # (matches report_worker). Set 5x for safety against retries during slow
  # Yahoo windows.
  visibility_timeout_seconds = 600 # 10 minutes

  # 4 days for debugging window — same as fund_data_sync default
  message_retention_seconds = 345600

  max_receive_count = 3

  # The queue is fed by Step Functions, not S3
  allow_s3_event_source = false

  # CloudWatch alarms
  enable_cloudwatch_alarms    = true
  dlq_alarm_threshold         = 1    # any message in DLQ = page
  queue_depth_alarm_threshold = 100  # ~2x worst-case batch (56 tickers)
  message_age_alarm_threshold = 1800 # 30 minutes — stall detector

  queue_purpose = "throttled-precompute-fanout"
  data_source   = "step-functions-precompute-workflow"

  common_tags = merge(
    local.common_tags,
    {
      Component = "precompute-consumer"
      Purpose   = "throttled-pipeline"
      App       = "telegram-api"
    }
  )
}

###############################################################################
# Consumer Lambda — reuses report-worker image with command override
###############################################################################

resource "aws_lambda_function" "precompute_consumer" {
  function_name = "${var.project_name}-precompute-consumer-${var.environment}"

  # Reuse the same role as the other precompute Lambdas (pattern_precompute,
  # backtest_precompute, get_ticker_list, precompute_controller).
  role = aws_iam_role.telegram_lambda_role.arn

  # Same image as report_worker — only the command differs
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.lambda_handlers.precompute_consumer_handler.lambda_handler"]
  }

  # Match report_worker — LLM + Aurora + transform takes up to ~120s per ticker
  timeout     = 120
  memory_size = 1024

  # Mirror report_worker env block exactly so behavior of
  # _handle_step_functions_mode is identical to direct invocation
  environment {
    variables = {
      TZ = "Asia/Bangkok"

      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
      PDF_STORAGE_BUCKET = aws_s3_bucket.pdf_reports.id
      PDF_BUCKET_NAME    = aws_s3_bucket.pdf_reports.id

      LANGFUSE_PUBLIC_KEY          = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY          = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST                = var.LANGFUSE_HOST
      LANGFUSE_TRACING_ENVIRONMENT = var.LANGFUSE_TRACING_ENVIRONMENT

      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      USE_REPORT_PIPELINE = var.use_report_pipeline ? "true" : "false"
      REPORT_PIPELINE_ARN = var.use_report_pipeline ? aws_sfn_state_machine.report_pipeline[0].arn : ""
      DATA_LAKE_BUCKET    = module.s3_data_lake.bucket_id

      LOG_LEVEL = "INFO"
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-consumer-${var.environment}"
    App       = "telegram-api"
    Component = "precompute-consumer"
    Trigger   = "sqs"
    Pattern   = "throttled-pipeline"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_rds_cluster.aurora,
  ]
}

resource "aws_cloudwatch_log_group" "precompute_consumer_logs" {
  name              = "/aws/lambda/${aws_lambda_function.precompute_consumer.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-precompute-consumer-logs-${var.environment}"
    App       = "telegram-api"
    Component = "precompute-consumer-logging"
  })
}

###############################################################################
# Event Source Mapping — the throttle (token bucket = max_concurrency)
###############################################################################

resource "aws_lambda_event_source_mapping" "precompute_consumer_sqs" {
  event_source_arn = module.precompute_queue.queue_arn
  function_name    = aws_lambda_function.precompute_consumer.arn
  enabled          = true

  # batch_size=1 because each ticker is independent and we want
  # per-ticker concurrency control. Larger batches would let one slow
  # ticker block N others under the same invocation.
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0

  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    # The throttle. Yahoo per-IP rate limit tolerates ~5 concurrent
    # fetches via shared NAT. fund_data_sync uses 10 because its
    # bottleneck is Aurora connection pool, not Yahoo.
    maximum_concurrency = 5
  }
}

###############################################################################
# IAM — Lambda's SQS permissions (added to existing telegram_lambda_role)
###############################################################################

resource "aws_iam_role_policy" "precompute_consumer_sqs" {
  name = "${var.project_name}-precompute-consumer-sqs-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility",
        ]
        Resource = module.precompute_queue.queue_arn
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = module.precompute_queue.dlq_arn
      },
    ]
  })
}

###############################################################################
# IAM — Step Functions permission to enqueue tickers
###############################################################################
#
# The SFN Map iterator's task changes from arn:aws:states:::lambda:invoke
# to arn:aws:states:::sqs:sendMessage. Add the matching SendMessage
# permission to the existing precompute_workflow_role.

resource "aws_iam_role_policy" "precompute_workflow_sqs_send" {
  name = "${var.project_name}-precompute-workflow-sqs-send-${var.environment}"
  role = aws_iam_role.precompute_workflow_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = module.precompute_queue.queue_arn
      },
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "precompute_consumer_function_name" {
  value       = aws_lambda_function.precompute_consumer.function_name
  description = "Name of the precompute consumer Lambda function"
}

output "precompute_consumer_function_arn" {
  value       = aws_lambda_function.precompute_consumer.arn
  description = "ARN of the precompute consumer Lambda function"
}

output "precompute_queue_url" {
  value       = module.precompute_queue.queue_url
  description = "URL of the precompute SQS queue (consumed by SFN Map iterator)"
}

output "precompute_queue_arn" {
  value       = module.precompute_queue.queue_arn
  description = "ARN of the precompute SQS queue"
}

output "precompute_dlq_url" {
  value       = module.precompute_queue.dlq_url
  description = "URL of the precompute Dead Letter Queue"
}
