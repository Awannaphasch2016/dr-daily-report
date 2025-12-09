# Outputs for SQS ETL Queue Module

# ============================================================================
# Main Queue Outputs
# ============================================================================

output "queue_id" {
  description = "SQS queue ID (URL)"
  value       = aws_sqs_queue.main.id
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.main.arn
}

output "queue_name" {
  description = "SQS queue name"
  value       = aws_sqs_queue.main.name
}

output "queue_url" {
  description = "SQS queue URL (alias for queue_id)"
  value       = aws_sqs_queue.main.url
}

# ============================================================================
# Dead Letter Queue Outputs
# ============================================================================

output "dlq_id" {
  description = "DLQ ID (URL)"
  value       = aws_sqs_queue.dlq.id
}

output "dlq_arn" {
  description = "DLQ ARN"
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_name" {
  description = "DLQ name"
  value       = aws_sqs_queue.dlq.name
}

output "dlq_url" {
  description = "DLQ URL (alias for dlq_id)"
  value       = aws_sqs_queue.dlq.url
}

# ============================================================================
# CloudWatch Alarms Outputs
# ============================================================================

output "dlq_alarm_arn" {
  description = "CloudWatch alarm ARN for DLQ messages (null if alarms disabled)"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.dlq_messages[0].arn : null
}

output "queue_depth_alarm_arn" {
  description = "CloudWatch alarm ARN for queue depth (null if alarms disabled)"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.queue_depth[0].arn : null
}

output "message_age_alarm_arn" {
  description = "CloudWatch alarm ARN for message age (null if alarms disabled)"
  value       = var.enable_cloudwatch_alarms ? aws_cloudwatch_metric_alarm.message_age[0].arn : null
}

# ============================================================================
# Configuration Outputs (for Lambda environment variables)
# ============================================================================

output "config" {
  description = "Queue configuration summary for Lambda environment variables"
  value = {
    queue_url                  = aws_sqs_queue.main.url
    queue_arn                  = aws_sqs_queue.main.arn
    dlq_url                    = aws_sqs_queue.dlq.url
    dlq_arn                    = aws_sqs_queue.dlq.arn
    visibility_timeout_seconds = var.visibility_timeout_seconds
    max_receive_count          = var.max_receive_count
  }
}
