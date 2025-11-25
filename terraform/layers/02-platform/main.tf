# Layer 02: Platform Services
# Shared infrastructure: ECR container registry, S3 storage
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
    key            = "layers/02-platform/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "dr-daily-report-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Layer       = "02-platform"
  }
}

###############################################################################
# ECR Repository for Lambda Container Images
###############################################################################

resource "aws_ecr_repository" "lambda" {
  name                 = "${var.project_name}-lambda-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-lambda-${var.environment}"
    Component = "container-registry"
  })
}

# Lifecycle policy to keep only recent images
resource "aws_ecr_lifecycle_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository policy to allow Lambda service to pull images
resource "aws_ecr_repository_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

###############################################################################
# S3 Bucket for PDF Reports (Shared between apps)
###############################################################################

resource "aws_s3_bucket" "pdf_reports" {
  bucket = "line-bot-pdf-reports-${data.aws_caller_identity.current.account_id}"

  tags = merge(local.common_tags, {
    Name      = "line-bot-pdf-reports"
    App       = "shared"
    Component = "pdf-storage"
    SharedBy  = "line-bot_telegram-api"
  })
}

resource "aws_s3_bucket_versioning" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

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
      days = 1
    }
  }
}

resource "aws_s3_bucket_public_access_block" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
