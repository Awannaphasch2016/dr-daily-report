# DynamoDB Module - Outputs
# Expose table attributes for use in other resources

output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.this.arn
}

output "table_id" {
  description = "ID of the DynamoDB table (same as name)"
  value       = aws_dynamodb_table.this.id
}

output "hash_key" {
  description = "Hash key attribute name"
  value       = aws_dynamodb_table.this.hash_key
}

output "range_key" {
  description = "Range key attribute name (null if not defined)"
  value       = aws_dynamodb_table.this.range_key
}

output "stream_arn" {
  description = "ARN of the DynamoDB table stream (null if streams not enabled)"
  value       = aws_dynamodb_table.this.stream_arn
}
