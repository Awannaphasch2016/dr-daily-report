# Layer 03: Telegram API Application
# Lambda function, API Gateway, and IAM for Telegram Mini App
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
    key            = "layers/03-apps/telegram-api/terraform.tfstate"
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
    App         = "telegram-api"
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
# IAM Role for Telegram API Lambda
###############################################################################

resource "aws_iam_role" "telegram_lambda_role" {
  name = "${var.project_name}-telegram-api-role-${var.environment}"

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
    Name      = "${var.project_name}-telegram-api-role-${var.environment}"
    Component = "iam-role"
  })
}

resource "aws_iam_role_policy_attachment" "telegram_lambda_basic" {
  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach DynamoDB policy from Layer 01-data
resource "aws_iam_role_policy_attachment" "telegram_lambda_dynamodb" {
  role       = aws_iam_role.telegram_lambda_role.name
  policy_arn = local.dynamodb_policy_arn
}

# Custom policy for S3 and ECR access
resource "aws_iam_role_policy" "telegram_lambda_custom" {
  name = "${var.project_name}-telegram-api-custom-policy-${var.environment}"
  role = aws_iam_role.telegram_lambda_role.id

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

resource "aws_lambda_function" "telegram_api" {
  function_name = "${var.project_name}-telegram-api-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn

  package_type = "Image"
  image_uri    = "${local.ecr_repository_url}:latest"

  image_config {
    command = ["telegram_lambda_handler.handler"]
  }

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment {
    variables = {
      OPENAI_API_KEY           = var.openai_api_key
      PDF_STORAGE_BUCKET       = local.pdf_bucket_name
      PDF_BUCKET_NAME          = local.pdf_bucket_name
      PDF_URL_EXPIRATION_HOURS = "24"
      CACHE_BACKEND            = "hybrid"
      CACHE_TTL_HOURS          = "24"
      DYNAMODB_WATCHLIST_TABLE = local.watchlist_table
      DYNAMODB_CACHE_TABLE     = local.cache_table
      TELEGRAM_BOT_TOKEN       = var.telegram_bot_token
      TELEGRAM_APP_ID          = var.telegram_app_id
      TELEGRAM_APP_HASH        = var.telegram_app_hash
      TELEGRAM_WEBAPP_URL      = var.telegram_webapp_url
      LANGSMITH_TRACING_V2     = var.langsmith_tracing_enabled ? "true" : "false"
      LANGSMITH_API_KEY        = var.langsmith_api_key
      ENVIRONMENT              = var.environment
      LOG_LEVEL                = "INFO"
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-${var.environment}"
    Component = "rest-api"
    Interface = "api-gateway"
  })

  depends_on = [
    aws_iam_role_policy_attachment.telegram_lambda_basic,
    aws_iam_role_policy_attachment.telegram_lambda_dynamodb
  ]
}

resource "aws_cloudwatch_log_group" "telegram_api_logs" {
  name              = "/aws/lambda/${aws_lambda_function.telegram_api.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-logs-${var.environment}"
    Component = "logging"
  })
}

###############################################################################
# API Gateway HTTP API
###############################################################################

resource "aws_apigatewayv2_api" "telegram_api" {
  name          = "${var.project_name}-telegram-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "REST API for Telegram Mini App - ticker analysis and reports"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = [
      "Content-Type",
      "X-Telegram-User-Id",
      "X-Telegram-Init-Data",
      "Authorization"
    ]
    expose_headers = ["X-Request-Id"]
    max_age        = 300
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-${var.environment}"
    Component = "api-gateway"
  })
}

resource "aws_apigatewayv2_integration" "telegram_lambda" {
  api_id             = aws_apigatewayv2_api.telegram_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.telegram_api.invoke_arn
  description        = "Lambda integration for Telegram Mini App API"

  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

# Catch-all route
resource "aws_apigatewayv2_route" "telegram_default" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

# Explicit routes for monitoring
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/health"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "search" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/search"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "report" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/report/{ticker}"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "rankings" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/rankings"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_get" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/watchlist"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_post" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "POST /api/v1/watchlist"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_delete" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "DELETE /api/v1/watchlist/{ticker}"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_stage" "telegram_default" {
  api_id      = aws_apigatewayv2_api.telegram_api.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 100
    throttling_rate_limit    = 50
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-stage-${var.environment}"
    Component = "api-gateway-stage"
  })
}

resource "aws_cloudwatch_log_group" "telegram_api_gateway_logs" {
  name              = "/aws/apigateway/${var.project_name}-telegram-api-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-gateway-logs-${var.environment}"
    Component = "logging"
  })
}

resource "aws_lambda_permission" "telegram_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telegram_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.telegram_api.execution_arn}/*/*"
}
