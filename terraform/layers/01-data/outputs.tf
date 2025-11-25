# Outputs for upper layers to consume via remote state

output "watchlist_table_name" {
  value       = aws_dynamodb_table.telegram_watchlist.name
  description = "Name of the watchlist DynamoDB table"
}

output "watchlist_table_arn" {
  value       = aws_dynamodb_table.telegram_watchlist.arn
  description = "ARN of the watchlist DynamoDB table"
}

output "cache_table_name" {
  value       = aws_dynamodb_table.telegram_cache.name
  description = "Name of the cache DynamoDB table"
}

output "cache_table_arn" {
  value       = aws_dynamodb_table.telegram_cache.arn
  description = "ARN of the cache DynamoDB table"
}

output "dynamodb_policy_arn" {
  value       = aws_iam_policy.dynamodb_access.arn
  description = "ARN of the DynamoDB access policy (attach to app Lambda roles)"
}
