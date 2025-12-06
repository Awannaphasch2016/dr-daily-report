# Terraform Variables for DR Daily Report - Dev Environment
# This file contains non-sensitive configuration values
# Sensitive values are injected via Doppler TF_VAR_* environment variables

# Project Configuration
project_name = "dr-daily-report"
environment  = "dev"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration
lambda_memory  = 512
lambda_timeout = 120  # Report generation takes ~50-60s

# CloudWatch Logs
log_retention_days = 7

# Telegram Mini App Configuration
# Note: telegram_bot_token, telegram_app_id, telegram_app_hash come from Doppler
telegram_webapp_url = "https://demjoigiw6myp.cloudfront.net"

# LangSmith Tracing
langsmith_tracing_enabled = false

# Aurora MySQL Configuration
aurora_enabled         = true
aurora_min_acu         = 0.5   # ~$43/month minimum
aurora_max_acu         = 2     # Scale up to 2 ACU under load
aurora_database_name   = "ticker_data"
aurora_master_username = "admin"
# AURORA_MASTER_PASSWORD comes from Doppler TF_VAR_AURORA_MASTER_PASSWORD

# Lambda Container Image
# CI/CD overrides this with: -var="lambda_image_tag=v20251201182404"
# For manual Terraform runs, use the latest working tag from ECR
lambda_image_tag = "v20251201182404"  # Known working image from CI/CD
