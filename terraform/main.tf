# Terraform configuration for DR Daily Report Infrastructure
# Manages Lambda functions, API Gateway, DynamoDB, S3 for both LINE Bot and Telegram Mini App
#
# Usage:
#   terraform init -backend-config=envs/{env}/backend.hcl
#   terraform plan -var-file=envs/{env}/terraform.tfvars
#   terraform apply -var-file=envs/{env}/terraform.tfvars

terraform {
  required_version = ">= 1.0"

  # S3 backend with partial configuration
  # Values provided via: terraform init -backend-config=envs/{env}/backend.hcl
  backend "s3" {
    # bucket, key, region, dynamodb_table, encrypt are set in backend.hcl
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # AssumeRole configuration (optional - for Phase 2 migration)
  dynamic "assume_role" {
    for_each = var.use_assume_role && var.terraform_role_arn != "" ? [1] : []
    content {
      role_arn = var.terraform_role_arn
      # Optional: Add external_id for extra security
      # external_id = var.terraform_external_id
    }
  }
}

###############################################################################
# Common Tags for All Resources
###############################################################################

locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Owner       = var.owner
    CostCenter  = var.cost_center
  }
}

# Data source: Get current AWS account ID
data "aws_caller_identity" "current" {}

# Data source: Get current AWS region
data "aws_region" "current" {}

###############################################################################
# S3 Bucket for PDF Reports Storage
###############################################################################
# NOTE: ZIP deployment removed - all Lambda functions now use container images
# from ECR (see ecr.tf). The old null_resource.zip_build and aws_s3_object.lambda_zip
# were legacy from before container migration.

resource "aws_s3_bucket" "pdf_reports" {
  bucket = "line-bot-pdf-reports-${data.aws_caller_identity.current.account_id}"

  tags = merge(local.common_tags, {
    Name      = "line-bot-pdf-reports"
    App       = "shared"
    Component = "pdf-storage"
    SharedBy  = "line-bot_telegram-api"
  })
}

# Bucket versioning (optional, for recovery)
resource "aws_s3_bucket_versioning" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy - delete old PDFs and cache
resource "aws_s3_bucket_lifecycle_configuration" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  rule {
    id     = "delete_old_pdfs"
    status = "Enabled"

    filter {
      prefix = "reports/"
    }

    expiration {
      days = 30
    }
  }

  rule {
    id     = "delete_old_cache"
    status = "Enabled"

    filter {
      prefix = "cache/"
    }

    expiration {
      days = 1  # Cache expires after 24 hours
    }
  }
}

# Block public access (keep bucket private)
resource "aws_s3_bucket_public_access_block" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls       = true
  restrict_public_buckets  = true
}

###############################################################################
# IAM Role for Lambda
###############################################################################

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

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
    Name      = "${var.function_name}-role"
    App       = "line-bot"
    Component = "iam-role"
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach VPC execution policy (for Aurora access)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# NOTE: DynamoDB policy attachment is in dynamodb.tf (line 72-75)
# to avoid duplication

# Custom policy for additional permissions (if needed)
resource "aws_iam_role_policy" "lambda_custom" {
  name = "${var.function_name}-custom-policy"
  role = aws_iam_role.lambda_role.id

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
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::line-bot-ticker-deploy-20251030/python-libs/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.pdf_reports.arn
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
# Lambda Function (ZIP Deployment)
###############################################################################

resource "aws_lambda_function" "line_bot" {
  # Use standard naming pattern: {project}-line-bot-{env}
  # Note: Legacy function_name variable preserved for backwards compatibility
  function_name = "${var.project_name}-line-bot-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  # Container image deployment from ECR
  # Note: CI/CD sets lambda_image_tag to timestamped version (e.g., v20251201182404)
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["lambda_handler.lambda_handler"]
  }

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  # VPC configuration for Aurora database access
  # IMPORTANT: Use subnets with NAT Gateway (same as Telegram) for internet access
  # Lambda needs internet to respond to LINE Platform webhook
  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  environment {
    variables = {
      # LINE Bot credentials
      LINE_CHANNEL_ACCESS_TOKEN = var.LINE_CHANNEL_ACCESS_TOKEN
      LINE_CHANNEL_SECRET       = var.LINE_CHANNEL_SECRET

      # LLM API
      OPENROUTER_API_KEY        = var.OPENROUTER_API_KEY

      # Aurora database
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_DATABASE           = "ticker_data"
      AURORA_USER               = var.aurora_master_username
      AURORA_PASSWORD           = var.AURORA_MASTER_PASSWORD
      AURORA_PORT               = "3306"

      # PDF storage
      PDF_STORAGE_BUCKET        = aws_s3_bucket.pdf_reports.id
      PDF_BUCKET_NAME           = aws_s3_bucket.pdf_reports.id
      PDF_URL_EXPIRATION_HOURS  = "24"

      # Application config
      ENVIRONMENT               = var.environment
      LOG_LEVEL                 = "INFO"

      # Beta user limit (0 = unlimited, N = limit to next N users)
      BETA_USER_LIMIT           = tostring(var.beta_user_limit)
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-line-bot-${var.environment}"
    App       = "line-bot"
    Component = "webhook-handler"
    Interface = "function-url"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

###############################################################################
# Lambda Function URL for LINE Webhook
###############################################################################

resource "aws_lambda_function_url" "line_webhook" {
  function_name      = aws_lambda_function.line_bot.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET"]
    allow_headers = ["*"]
  }

  depends_on = [aws_lambda_function.line_bot]
}
