# Terraform Variables for DR Daily Report - PRODUCTION
# This file contains non-sensitive configuration values

# Project Configuration
project_name = "dr-daily-report"
environment  = "prod"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration - Higher resources for production
function_name  = "line-bot-ticker-report"
lambda_memory  = 1024  # More memory for production
lambda_timeout = 300   # Longer timeout for production

# CloudWatch Logs - Longer retention for production
log_retention_days = 30

# Sensitive variables - DO NOT set here!
# These are injected via Doppler TF_VAR_* environment variables.
# Run with: doppler run -c prod -- terraform plan

# Telegram Mini App Configuration
# TELEGRAM_BOT_TOKEN comes from Doppler via TF_VAR_TELEGRAM_BOT_TOKEN
# DO NOT set here - tfvars overrides TF_VAR_ environment variables
telegram_app_id     = ""
telegram_app_hash   = ""
telegram_webapp_url = ""  # Will be set after CloudFront creation

