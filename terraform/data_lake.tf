# S3 Data Lake Module
# Phase 1: Raw data staging for reproducibility and data lineage
#
# Principle: Separate staging (S3 raw data) from production (Aurora computed data)
# - Raw yfinance API responses stored immutably with versioning
# - Enables recomputation from exact historical data
# - Cost-optimized lifecycle: 90d → Glacier, 365d → Deep Archive, 730d → Delete
#
# TDD Approach: Tests written BEFORE infrastructure
# - OPA policies: terraform/policies/security/s3_data_lake.rego
# - Terratest: terraform/tests/s3_data_lake_test.go
# - pytest: tests/infrastructure/test_s3_data_lake_integration.py

###############################################################################
# S3 Data Lake Module
###############################################################################

module "s3_data_lake" {
  source = "./modules/s3-data-lake"

  project_name = var.project_name
  environment  = var.environment

  # Encryption: Start with SSE-S3 (AES256), can upgrade to SSE-KMS later
  encryption_algorithm = "AES256"

  # Lifecycle: Balance cost vs retention requirements
  glacier_transition_days      = 90  # Transition to Glacier after 90 days
  deep_archive_transition_days = 365 # Transition to Deep Archive after 1 year
  expiration_days              = 730 # Delete after 2 years

  # CORS: Disabled for Phase 1 (no direct browser uploads)
  enable_cors = false

  common_tags = merge(local.common_tags, {
    App                = "shared"
    Component          = "data-lake"
    Purpose            = "raw-data-staging"
    DataClassification = "public-api-data"
    SharedBy           = "telegram-api_scheduler"
  })
}

###############################################################################
# Outputs for Other Modules
###############################################################################

output "data_lake_bucket_id" {
  description = "S3 Data Lake bucket ID for Lambda environment variables"
  value       = module.s3_data_lake.bucket_id
}

output "data_lake_bucket_arn" {
  description = "S3 Data Lake bucket ARN for IAM policies"
  value       = module.s3_data_lake.bucket_arn
}
