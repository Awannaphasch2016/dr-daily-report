# SQS Queue Module for ETL Pipelines
#
# Purpose: Create SQS queue + DLQ for event-driven ETL processing
# Use Case: S3 ObjectCreated events → SQS → Lambda → Aurora
#
# Design Principles:
# - Idempotency: Content-based deduplication prevents duplicate processing
# - Fail fast: DLQ captures poison messages after N retries
# - Observability: CloudWatch metrics + DLQ monitoring
# - Security: Encryption at rest, explicit IAM policies

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# Dead Letter Queue (Created First - Dependency for Main Queue)
# ============================================================================

resource "aws_sqs_queue" "dlq" {
  name = "${var.queue_name}-dlq"

  # DLQ Configuration
  message_retention_seconds  = var.dlq_message_retention_seconds  # 14 days for investigation
  visibility_timeout_seconds = var.dlq_visibility_timeout_seconds # Short timeout (no processing)

  # Encryption (SSE-SQS managed)
  sqs_managed_sse_enabled = true

  # Tags
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.queue_name}-dlq"
      Purpose     = "dead-letter-queue"
      Description = "Dead letter queue for failed ${var.queue_name} messages"
    }
  )
}

# ============================================================================
# Main SQS Queue
# ============================================================================

resource "aws_sqs_queue" "main" {
  name = var.queue_name

  # Message Configuration
  message_retention_seconds = var.message_retention_seconds # 4 days for debugging
  max_message_size          = var.max_message_size          # 256 KB (CSV metadata, not file)
  receive_wait_time_seconds = var.receive_wait_time_seconds # Long polling (reduce API calls)

  # Processing Configuration
  visibility_timeout_seconds = var.visibility_timeout_seconds # 2x max processing time
  delay_seconds              = var.delay_seconds              # Optional delay before processing

  # Dead Letter Queue (Redrive Policy)
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count # 3-5 retries before DLQ
  })

  # Encryption (SSE-SQS managed by default, can upgrade to KMS)
  sqs_managed_sse_enabled = var.kms_master_key_id == null ? true : false
  kms_master_key_id       = var.kms_master_key_id

  # Data Protection (no PII expected in fund data, but enable for compliance)
  kms_data_key_reuse_period_seconds = var.kms_data_key_reuse_period_seconds

  # Tags
  tags = merge(
    var.common_tags,
    {
      Name        = var.queue_name
      Purpose     = var.queue_purpose
      DataSource  = var.data_source
      Description = "SQS queue for ${var.queue_purpose} from ${var.data_source}"
    }
  )
}

# ============================================================================
# CloudWatch Alarms for Queue Monitoring
# ============================================================================

# Alarm: DLQ has messages (indicates processing failures)
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.queue_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = var.dlq_alarm_threshold
  alarm_description   = "Alert when DLQ has messages (processing failures detected)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.queue_name}-dlq-alarm"
      Purpose = "monitor-processing-failures"
    }
  )
}

# Alarm: Main queue has too many messages (backlog)
resource "aws_cloudwatch_metric_alarm" "queue_depth" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.queue_name}-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = var.queue_depth_alarm_threshold
  alarm_description   = "Alert when queue depth exceeds threshold (processing too slow)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.queue_name}-depth-alarm"
      Purpose = "monitor-queue-backlog"
    }
  )
}

# Alarm: Old messages in queue (processing stalled)
resource "aws_cloudwatch_metric_alarm" "message_age" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.queue_name}-message-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Maximum"
  threshold           = var.message_age_alarm_threshold
  alarm_description   = "Alert when messages are stuck in queue (processing failed)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.queue_name}-age-alarm"
      Purpose = "monitor-processing-stalls"
    }
  )
}

# ============================================================================
# IAM Policy for S3 to Send Messages
# ============================================================================

# Allow S3 to send messages to this queue
data "aws_iam_policy_document" "s3_send" {
  count = var.allow_s3_event_source ? 1 : 0

  statement {
    sid    = "AllowS3ToSendMessage"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.main.arn,
    ]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = var.s3_bucket_arns
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sqs_queue_policy" "s3_send" {
  count = var.allow_s3_event_source ? 1 : 0

  queue_url = aws_sqs_queue.main.id
  policy    = data.aws_iam_policy_document.s3_send[0].json
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_caller_identity" "current" {}
