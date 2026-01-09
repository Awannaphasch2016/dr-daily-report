# Terraform Variables for DR Daily Report - STAGING
# This file contains non-sensitive configuration values

# Project Configuration
project_name = "dr-daily-report"
environment  = "staging"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration
function_name  = "line-bot-ticker-report"
lambda_memory  = 512
lambda_timeout = 120

# CloudWatch Logs
log_retention_days = 14

# Sensitive variables - DO NOT set here!
# These are injected via Doppler TF_VAR_* environment variables.
# Run with: doppler run -c staging -- terraform plan

# Telegram Mini App Configuration
# TELEGRAM_BOT_TOKEN comes from Doppler via TF_VAR_TELEGRAM_BOT_TOKEN
# DO NOT set here - tfvars overrides TF_VAR_ environment variables
telegram_app_id     = ""
telegram_app_hash   = ""
telegram_webapp_url = "https://d3uuexs20crp9s.cloudfront.net"  # Staging CloudFront

# CORS: All allowed WebApp origins (dev, staging, prod CloudFront distributions)
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net",   # dev
  "https://d3uuexs20crp9s.cloudfront.net"   # staging
]

