# Terraform Variables for DR Daily Report - Production Environment
# This file contains non-sensitive configuration values
# Sensitive values are injected via Doppler TF_VAR_* environment variables

# Project Configuration
project_name = "dr-daily-report"
environment  = "prod"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration
lambda_memory  = 1024  # More memory for production
lambda_timeout = 120

# CloudWatch Logs
log_retention_days = 30  # Longest retention for production

# Telegram Mini App Configuration
# Note: telegram_bot_token, telegram_app_id, telegram_app_hash come from Doppler
# telegram_webapp_url will be set after CloudFront creation for production
telegram_webapp_url = ""

# LangSmith Tracing
langsmith_tracing_enabled = true  # Enable tracing in production
