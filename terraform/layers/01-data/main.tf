# Layer 01: Data Persistence
# DynamoDB tables for application data storage
# Can be developed/deployed independently from app layers

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "dr-daily-report-tf-state"
    key            = "layers/01-data/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "dr-daily-report-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Layer       = "01-data"
  }
}

###############################################################################
# Watchlist Table - User watchlist storage
###############################################################################

resource "aws_dynamodb_table" "telegram_watchlist" {
  name           = "${var.project_name}-telegram-watchlist-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "ticker"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "ticker"
    type = "S"
  }

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

###############################################################################
# Cache Table - API response caching
###############################################################################

resource "aws_dynamodb_table" "telegram_cache" {
  name           = "${var.project_name}-telegram-cache-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-cache-${var.environment}"
    App       = "telegram-api"
    Component = "cache-storage"
    DataType  = "temporary"
  })
}

###############################################################################
# IAM Policy for DynamoDB Access (attached by app layer)
###############################################################################

resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-access-${var.environment}"
  description = "Allow Lambda to access DynamoDB tables for Telegram Mini App"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-dynamodb-access-${var.environment}"
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
          aws_dynamodb_table.telegram_watchlist.arn,
          aws_dynamodb_table.telegram_cache.arn
        ]
      }
    ]
  })
}
