# SQS Module - Main Resources
# Queue with optional DLQ and Lambda trigger

locals {
  full_queue_name = "${var.project_name}-${var.queue_name}-${var.environment}"
  dlq_name        = "${var.project_name}-${var.queue_name}-dlq-${var.environment}"

  # Merge tags
  resource_tags = merge(var.common_tags, {
    Name      = local.full_queue_name
    App       = var.app_tag
    Component = var.component_tag
  })
}

#------------------------------------------------------------------------------
# Dead Letter Queue (Optional)
#------------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  count = var.create_dlq ? 1 : 0

  name                       = local.dlq_name
  message_retention_seconds  = var.dlq_message_retention_seconds
  visibility_timeout_seconds = var.visibility_timeout_seconds

  tags = merge(local.resource_tags, {
    Name      = local.dlq_name
    Component = "dead-letter-queue"
  })
}

#------------------------------------------------------------------------------
# Main SQS Queue
#------------------------------------------------------------------------------

resource "aws_sqs_queue" "this" {
  name                       = local.full_queue_name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = var.receive_wait_time_seconds
  delay_seconds              = var.delay_seconds
  max_message_size           = var.max_message_size

  # DLQ redrive policy (only if DLQ is created)
  redrive_policy = var.create_dlq ? jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
    maxReceiveCount     = var.max_receive_count
  }) : null

  tags = local.resource_tags
}

#------------------------------------------------------------------------------
# Lambda Event Source Mapping (Optional)
#------------------------------------------------------------------------------

resource "aws_lambda_event_source_mapping" "trigger" {
  count = var.create_lambda_trigger ? 1 : 0

  event_source_arn                   = aws_sqs_queue.this.arn
  function_name                      = var.lambda_function_arn
  batch_size                         = var.lambda_batch_size
  maximum_batching_window_in_seconds = var.lambda_maximum_batching_window_seconds

  # Don't report failures back to SQS - let DLQ handle it
  function_response_types = []
}
