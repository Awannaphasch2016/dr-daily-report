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

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-watchlist-${var.environment}"
    App       = "telegram-api"
    Component = "watchlist-storage"
    DataType  = "user-preferences"
  })
}

# NOTE: telegram_cache table REMOVED as part of Data Storage Architecture Redesign
# Cache functionality moved to Aurora ticker_data_cache table
# See db/migrations/002_schema_redesign.sql

# IAM policy for Lambda to access DynamoDB tables
resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-access-${var.environment}"
  description = "Allow Lambda to access DynamoDB tables for Telegram Mini App"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-dynamodb-access-${var.environment}"
    App       = "telegram-api"
    Component = "iam-policy"
  })

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
          aws_dynamodb_table.telegram_watchlist.arn
          # NOTE: telegram_cache.arn removed - cache moved to Aurora
        ]
      }
    ]
  })
}

# Attach policy to Lambda role for DynamoDB access
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

# Outputs for use in application
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
