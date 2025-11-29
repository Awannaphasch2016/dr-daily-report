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
telegram_bot_token  = ""  # Get from @BotFather
telegram_app_id     = ""  # Get from https://my.telegram.org/apps
telegram_app_hash   = ""  # Get from https://my.telegram.org/apps
telegram_webapp_url = "https://demjoigiw6myp.cloudfront.net"  # CloudFront distribution URL

# LangSmith Tracing
langsmith_tracing_enabled = false
langsmith_api_key         = ""
