# S3 Data Lake Module
#
# Creates an S3 bucket for raw data staging following Phase 1 requirements:
# - Versioning enabled (data lineage)
# - Encryption at rest (security)
# - Public access blocked (compliance)
# - Lifecycle policies (cost optimization)
# - Required tags (cost tracking)
#
# This module is tested by:
# - OPA policies: terraform/policies/security/s3_data_lake.rego
# - Terratest: terraform/tests/s3_data_lake_test.go
# - pytest: tests/infrastructure/test_s3_data_lake_integration.py

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 Bucket for Data Lake
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-data-lake-${var.environment}"

  tags = merge(
    var.common_tags,
    {
      Name               = "Data Lake ${title(var.environment)}"
      Purpose            = "raw-data-staging"
      DataClassification = "public-api-data"
    }
  )
}

# Enable Versioning (REQUIRED for data lineage)
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"  # MUST be Enabled per OPA policy
  }
}

# Enable Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.encryption_algorithm  # "AES256" or "aws:kms"
    }
    bucket_key_enabled = var.encryption_algorithm == "aws:kms" ? true : false
  }
}

# Block All Public Access
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Policy (Cost Optimization)
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "transition-raw-data-to-glacier"
    status = "Enabled"

    filter {
      prefix = "raw/"  # Apply to raw data only
    }

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    transition {
      days          = var.deep_archive_transition_days
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.expiration_days
    }
  }

  rule {
    id     = "transition-processed-data-to-glacier"
    status = "Enabled"

    filter {
      prefix = "processed/"  # Apply to processed data
    }

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.expiration_days
    }
  }
}

# CORS Configuration (if needed for direct browser uploads)
resource "aws_s3_bucket_cors_configuration" "data_lake" {
  count  = var.enable_cors ? 1 : 0
  bucket = aws_s3_bucket.data_lake.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    max_age_seconds = 3600
  }
}
