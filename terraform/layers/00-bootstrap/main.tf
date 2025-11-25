# Bootstrap layer: Remote state infrastructure
# This creates the S3 bucket and DynamoDB table for Terraform state management
# Run this FIRST with local state, then migrate to remote state

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Initially use local state, then migrate to S3 after creation
  # Uncomment after first apply:
  # backend "s3" {
  #   bucket         = "dr-daily-report-tf-state"
  #   key            = "bootstrap/terraform.tfstate"
  #   region         = "ap-southeast-1"
  #   dynamodb_table = "dr-daily-report-tf-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

###############################################################################
# S3 Bucket for Terraform State
###############################################################################

resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-tf-state"

  tags = {
    Name        = "${var.project_name}-tf-state"
    Purpose     = "Terraform state storage"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

# Enable versioning for state file recovery
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to manage old versions
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "cleanup_old_versions"
    status = "Enabled"

    filter {}  # Apply to all objects

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

###############################################################################
# DynamoDB Table for State Locking
###############################################################################

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "${var.project_name}-tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-tf-locks"
    Purpose     = "Terraform state locking"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

###############################################################################
# Outputs
###############################################################################

output "state_bucket_name" {
  value       = aws_s3_bucket.terraform_state.id
  description = "S3 bucket name for Terraform state"
}

output "state_bucket_arn" {
  value       = aws_s3_bucket.terraform_state.arn
  description = "S3 bucket ARN for Terraform state"
}

output "locks_table_name" {
  value       = aws_dynamodb_table.terraform_locks.name
  description = "DynamoDB table name for state locking"
}

output "backend_config" {
  value = <<-EOT
    backend "s3" {
      bucket         = "${aws_s3_bucket.terraform_state.id}"
      region         = "${data.aws_region.current.name}"
      dynamodb_table = "${aws_dynamodb_table.terraform_locks.name}"
      encrypt        = true
    }
  EOT
  description = "Backend configuration to use in other layers"
}
