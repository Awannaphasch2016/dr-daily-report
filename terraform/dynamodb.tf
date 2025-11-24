# DynamoDB tables for Telegram Mini App

# Watchlist table - stores user watchlists
resource "aws_dynamodb_table" "telegram_watchlist" {
  name           = "${var.project_name}-telegram-watchlist-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST" # On-demand pricing
  hash_key       = "user_id"
  range_key      = "ticker"

  attribute {
    name = "user_id"
    type = "S" # String - Telegram user ID
  }

  attribute {
    name = "ticker"
    type = "S" # String - Ticker symbol (e.g., NVDA19)
  }

  # TTL for automatic cleanup of old watchlist items (optional)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-telegram-watchlist-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Cache table - stores API response cache
resource "aws_dynamodb_table" "telegram_cache" {
  name           = "${var.project_name}-telegram-cache-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cache_key"

  attribute {
    name = "cache_key"
    type = "S" # String - e.g., "report:NVDA19" or "rankings:top_gainers"
  }

  # TTL for automatic cache expiration
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-telegram-cache-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# IAM policy for Lambda to access DynamoDB tables
resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-access-${var.environment}"
  description = "Allow Lambda to access DynamoDB tables for Telegram Mini App"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.telegram_watchlist.arn,
          aws_dynamodb_table.telegram_cache.arn
        ]
      }
    ]
  })
}

# Attach policy to existing Lambda role (if exists)
# Note: Adjust role name based on your existing Lambda role
# resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
#   role       = aws_iam_role.lambda_role.name
#   policy_arn = aws_iam_policy.dynamodb_access.arn
# }

# Outputs for use in application
output "watchlist_table_name" {
  value       = aws_dynamodb_table.telegram_watchlist.name
  description = "Name of the watchlist DynamoDB table"
}

output "cache_table_name" {
  value       = aws_dynamodb_table.telegram_cache.name
  description = "Name of the cache DynamoDB table"
}

output "watchlist_table_arn" {
  value       = aws_dynamodb_table.telegram_watchlist.arn
  description = "ARN of the watchlist DynamoDB table"
}

output "cache_table_arn" {
  value       = aws_dynamodb_table.telegram_cache.arn
  description = "ARN of the cache DynamoDB table"
}
