# Terraform Variables for DR Daily Report
# This file contains non-sensitive configuration values

# Project Configuration
project_name = "dr-daily-report"
environment  = "dev"  # Start with dev environment
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration (for LINE Bot - not used if not in state)
function_name  = "line-bot-ticker-report"
lambda_memory  = 512
lambda_timeout = 120  # Increased from 60s - report generation takes ~50-60s

# CloudWatch Logs
log_retention_days = 7

# Sensitive variables - DO NOT set here!
# These are injected via Doppler TF_VAR_* environment variables.
# Run with: doppler run -- terraform plan
#
# Required Doppler secrets:
#   - TF_VAR_OPENROUTER_API_KEY
#   - TF_VAR_LINE_CHANNEL_ACCESS_TOKEN
#   - TF_VAR_LINE_CHANNEL_SECRET

# Telegram Mini App Configuration
# TELEGRAM_BOT_TOKEN comes from Doppler via TF_VAR_TELEGRAM_BOT_TOKEN
# DO NOT set here - tfvars overrides TF_VAR_ environment variables
telegram_app_id     = ""
telegram_app_hash   = ""
telegram_webapp_url = "https://demjoigiw6myp.cloudfront.net"  # CloudFront distribution URL (legacy)

# CORS: All allowed WebApp origins (dev, staging, prod CloudFront distributions)
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net",   # dev
  "https://d3uuexs20crp9s.cloudfront.net"   # staging
]


# Aurora MySQL Configuration (always deployed, no flag)
aurora_min_acu = 0.5  # ~$43/month
aurora_max_acu = 2
aurora_database_name = "ticker_data"
aurora_master_username = "admin"
lambda_image_tag = "pdf-timeout-fix-20260105-061221"
