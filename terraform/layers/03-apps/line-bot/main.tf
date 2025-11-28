# Layer 03: LINE Bot Application
# Lambda function with Function URL for LINE Messaging API webhook
# Consumes outputs from Layer 01 (data) and Layer 02 (platform) via remote state

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
    key            = "layers/03-apps/line-bot/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "dr-daily-report-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

###############################################################################
# Remote State Data Sources (Layer Dependencies)
###############################################################################

data "terraform_remote_state" "data" {
  backend = "s3"
  config = {
    bucket = "dr-daily-report-tf-state"
    key    = "layers/01-data/terraform.tfstate"
    region = "ap-southeast-1"
  }
}

data "terraform_remote_state" "platform" {
  backend = "s3"
  config = {
    bucket = "dr-daily-report-tf-state"
    key    = "layers/02-platform/terraform.tfstate"
    region = "ap-southeast-1"
  }
}

locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Owner       = "data-team"
    CostCenter  = "engineering"
    App         = "line-bot"
  }

  # Values from lower layers
  ecr_repository_url  = data.terraform_remote_state.platform.outputs.ecr_repository_url
  pdf_bucket_name     = data.terraform_remote_state.platform.outputs.pdf_bucket_name
  pdf_bucket_arn      = data.terraform_remote_state.platform.outputs.pdf_bucket_arn
  watchlist_table     = data.terraform_remote_state.data.outputs.watchlist_table_name
  cache_table         = data.terraform_remote_state.data.outputs.cache_table_name
  dynamodb_policy_arn = data.terraform_remote_state.data.outputs.dynamodb_policy_arn
}

###############################################################################
# IAM Role for LINE Bot Lambda
###############################################################################

resource "aws_iam_role" "line_bot_role" {
  name = "line-bot-ticker-report-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "line-bot-ticker-report-role"
    Component = "iam-role"
  })
}

resource "aws_iam_role_policy_attachment" "line_bot_basic" {
  role       = aws_iam_role.line_bot_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "line_bot_vpc" {
  role       = aws_iam_role.line_bot_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Attach DynamoDB policy from Layer 01-data
resource "aws_iam_role_policy_attachment" "line_bot_dynamodb" {
  role       = aws_iam_role.line_bot_role.name
  policy_arn = local.dynamodb_policy_arn
}

# Custom policy for S3 and ECR access
resource "aws_iam_role_policy" "line_bot_custom" {
  name = "line-bot-ticker-report-custom-policy"
  role = aws_iam_role.line_bot_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::line-bot-ticker-deploy-20251030/python-libs/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${local.pdf_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = local.pdf_bucket_arn
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

###############################################################################
# Lambda Function
###############################################################################

resource "aws_lambda_function" "line_bot" {
  function_name = "line-bot-ticker-report"
  role          = aws_iam_role.line_bot_role.arn

  package_type = "Image"
  image_uri    = "${local.ecr_repository_url}:latest"

  image_config {
    command = ["lambda_handler.lambda_handler"]
  }

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment {
    variables = {
      LINE_CHANNEL_ACCESS_TOKEN = var.LINE_CHANNEL_ACCESS_TOKEN
      LINE_CHANNEL_SECRET       = var.LINE_CHANNEL_SECRET
      OPENROUTER_API_KEY        = var.OPENROUTER_API_KEY
      PDF_STORAGE_BUCKET        = local.pdf_bucket_name
      PDF_BUCKET_NAME           = local.pdf_bucket_name
      PDF_URL_EXPIRATION_HOURS  = "24"
      CACHE_BACKEND             = "hybrid"
      CACHE_TTL_HOURS           = "24"
      DYNAMODB_WATCHLIST_TABLE  = local.watchlist_table
      DYNAMODB_CACHE_TABLE      = local.cache_table
      LANGSMITH_TRACING_V2      = var.langsmith_tracing_enabled ? "true" : "false"
      LANGSMITH_API_KEY         = var.langsmith_api_key
      ENVIRONMENT               = var.environment
      LOG_LEVEL                 = "INFO"
    }
  }

  tags = merge(local.common_tags, {
    Name      = "line-bot-ticker-report"
    Component = "webhook-handler"
    Interface = "function-url"
  })

  depends_on = [
    aws_iam_role_policy_attachment.line_bot_basic,
    aws_iam_role_policy_attachment.line_bot_dynamodb
  ]
}

resource "aws_cloudwatch_log_group" "line_bot_logs" {
  name              = "/aws/lambda/${aws_lambda_function.line_bot.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "line-bot-ticker-report-logs"
    Component = "logging"
  })
}

###############################################################################
# Lambda Function URL (instead of API Gateway)
###############################################################################

resource "aws_lambda_function_url" "line_bot" {
  function_name      = aws_lambda_function.line_bot.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_origins     = ["*"]
  }
}
