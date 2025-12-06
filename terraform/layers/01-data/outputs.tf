# Outputs for upper layers to consume via remote state

output "watchlist_table_name" {
  value       = aws_dynamodb_table.telegram_watchlist.name
  description = "Name of the watchlist DynamoDB table"
}

output "watchlist_table_arn" {
  value       = aws_dynamodb_table.telegram_watchlist.arn
  description = "ARN of the watchlist DynamoDB table"
}

# NOTE: cache_table_name and cache_table_arn outputs removed
# Cache functionality moved to Aurora ticker_data_cache table
# See db/migrations/002_schema_redesign.sql

output "dynamodb_policy_arn" {
  value       = aws_iam_policy.dynamodb_access.arn
  description = "ARN of the DynamoDB access policy (attach to app Lambda roles)"
}
