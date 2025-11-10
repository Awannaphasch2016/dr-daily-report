# Terraform configuration for LINE Bot Lambda Function
# This manages the Lambda function with ZIP deployment and Lambda Function URL

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source: Get current AWS account ID
data "aws_caller_identity" "current" {}

# Data source: Get current AWS region
data "aws_region" "current" {}

###############################################################################
# ZIP Deployment Package Build
###############################################################################

# Build ZIP deployment package
resource "null_resource" "zip_build" {
  # Trigger rebuild when source code or requirements change
  triggers = {
    requirements_hash        = filemd5("${path.module}/../requirements_minimal.txt")
    requirements_nodeps_hash = filemd5("${path.module}/../requirements_nodeps.txt")
    requirements_heavy_hash  = filemd5("${path.module}/../requirements_heavy.txt")
    src_hash                 = sha256(join("", [for f in fileset("${path.module}/../src", "**") : filemd5("${path.module}/../src/${f}")]))
    tickers_hash             = filemd5("${path.module}/../data/tickers.csv")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      
      # Create build directory
      echo "📦 Creating deployment package..."
      # Clean using Docker to handle permission issues
      if [ -d "build/deployment_package" ]; then
        docker run --rm -v "$(pwd)/build":/build alpine sh -c "rm -rf /build/deployment_package"
      fi
      mkdir -p build/deployment_package
      
      # Install dependencies using Lambda's Docker image for compatibility
      echo "📥 Installing dependencies (using Lambda Docker environment)..."
      docker run --rm --platform linux/amd64 \
        --entrypoint /bin/bash \
        -v "$(pwd)":/var/task \
        public.ecr.aws/lambda/python:3.11 \
        -c "pip install --upgrade pip && \
            pip install -r requirements_minimal.txt -t /var/task/build/deployment_package/ --prefer-binary && \
            pip install --no-deps -r requirements_nodeps.txt -t /var/task/build/deployment_package/ --prefer-binary"
      
      # Copy application files
      echo "📋 Copying application files..."
      cp -r src build/deployment_package/src
      cp src/lambda_handler.py build/deployment_package/lambda_handler.py
      cp data/tickers.csv build/deployment_package/
      
      # Create deployment package using Python
      echo "📦 Creating ZIP file..."
      python3 << 'PYTHON'
import os
import zipfile
import shutil

# Change to deployment package directory
os.chdir('build/deployment_package')

# Exclude patterns
exclude_dirs = {'__pycache__', '.pytest_cache', 'tests', 'test', 'docs', 'doc', '.git'}
exclude_extensions = {'.pyc', '.pyo', '.pyd', '.so.dbg', '.dist-info'}

# Create ZIP file
with zipfile.ZipFile('../lambda_deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        # Remove excluded directories from dirs list to prevent traversal
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            # Skip excluded files
            if any(file.endswith(ext) for ext in exclude_extensions):
                continue
            
            file_path = os.path.join(root, file)
            # Skip if in excluded directory
            if any(excluded in file_path.split(os.sep) for excluded in exclude_dirs):
                continue
            
            arcname = os.path.relpath(file_path, '.')
            zipf.write(file_path, arcname)

print("✅ ZIP file created successfully")
PYTHON
      
      echo "✅ Deployment package created: build/lambda_deployment.zip"
    EOT

    working_dir = "${path.module}/.."
  }
}

###############################################################################
# S3 Bucket for Lambda Deployment Package
###############################################################################

# Use existing bucket
data "aws_s3_bucket" "deployment" {
  bucket = "line-bot-ticker-deploy-20251030"
}

# Upload ZIP to S3
resource "aws_s3_object" "lambda_zip" {
  bucket = data.aws_s3_bucket.deployment.id
  key    = "lambda_deployment_${null_resource.zip_build.id}.zip"
  source = "${path.module}/../build/lambda_deployment.zip"

  depends_on = [null_resource.zip_build]
}

###############################################################################
# S3 Bucket for PDF Reports Storage
###############################################################################

resource "aws_s3_bucket" "pdf_reports" {
  bucket = "line-bot-pdf-reports-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "line-bot-pdf-reports"
    Environment = var.environment
    Project     = "LineBot"
  }
}

# Bucket versioning (optional, for recovery)
resource "aws_s3_bucket_versioning" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy - delete PDFs older than 30 days
resource "aws_s3_bucket_lifecycle_configuration" "pdf_reports" {
  bucket = aws_s3_bucket.pdf_reports.id

  rule {
    id     = "delete_old_pdfs"
    status = "Enabled"

    prefix = "reports/"

    expiration {
      days = 30
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

  tags = {
    Name        = "${var.function_name}-role"
    Environment = var.environment
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

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
      }
    ]
  })
}

###############################################################################
# Lambda Function (ZIP Deployment)
###############################################################################

resource "aws_lambda_function" "line_bot" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_handler.lambda_handler"

  # ZIP deployment configuration via S3
  s3_bucket = aws_s3_object.lambda_zip.bucket
  s3_key    = aws_s3_object.lambda_zip.key

  runtime     = "python3.11"
  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  # Heavy dependencies loaded from S3 at runtime (no layer needed)

  environment {
    variables = {
      OPENAI_API_KEY            = var.openai_api_key
      LINE_CHANNEL_ACCESS_TOKEN = var.line_channel_access_token
      LINE_CHANNEL_SECRET       = var.line_channel_secret
      PDF_STORAGE_BUCKET        = aws_s3_bucket.pdf_reports.id
      PDF_URL_EXPIRATION_HOURS  = "24"
    }
  }

  tags = {
    Name        = var.function_name
    Environment = var.environment
    Project     = "LineBot"
  }

  depends_on = [
    null_resource.zip_build,
    aws_s3_object.lambda_zip,
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
