# SQS Module - Outputs
# Expose queue attributes for use in other resources

#------------------------------------------------------------------------------
# Main Queue Outputs
#------------------------------------------------------------------------------

output "queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.this.url
}

output "queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.this.arn
}

output "queue_name" {
  description = "Name of the SQS queue"
  value       = aws_sqs_queue.this.name
}

output "queue_id" {
  description = "ID of the SQS queue (same as URL)"
  value       = aws_sqs_queue.this.id
}

#------------------------------------------------------------------------------
# Dead Letter Queue Outputs
#------------------------------------------------------------------------------

output "dlq_url" {
  description = "URL of the Dead Letter Queue (null if create_dlq = false)"
  value       = var.create_dlq ? aws_sqs_queue.dlq[0].url : null
}

output "dlq_arn" {
  description = "ARN of the Dead Letter Queue (null if create_dlq = false)"
  value       = var.create_dlq ? aws_sqs_queue.dlq[0].arn : null
}

output "dlq_name" {
  description = "Name of the Dead Letter Queue (null if create_dlq = false)"
  value       = var.create_dlq ? aws_sqs_queue.dlq[0].name : null
}

#------------------------------------------------------------------------------
# Lambda Trigger Output
#------------------------------------------------------------------------------

output "event_source_mapping_uuid" {
  description = "UUID of Lambda event source mapping (null if create_lambda_trigger = false)"
  value       = var.create_lambda_trigger ? aws_lambda_event_source_mapping.trigger[0].uuid : null
}
