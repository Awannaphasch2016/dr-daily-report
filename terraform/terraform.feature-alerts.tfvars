# Terraform Variables for Feature Branch: Alert System Development
# Created from: terraform.dev.tfvars
# Purpose: Isolated environment for developing infrastructure alerting
#
# Usage:
#   doppler run --config dev -- terraform plan -var-file=terraform.feature-alerts.tfvars
#   doppler run --config dev -- terraform apply -var-file=terraform.feature-alerts.tfvars
#
# Cleanup:
#   terraform destroy -var-file=terraform.feature-alerts.tfvars
#   rm terraform.feature-alerts.tfvars

# REQUIRED CHANGE: Unique environment name
environment  = "feature-alerts"

# Project Configuration (same as dev)
project_name = "dr-daily-report"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration
function_name  = "line-bot-ticker-report"
lambda_memory  = 512
lambda_timeout = 120

# CloudWatch Logs - shorter retention for feature env (cost savings)
log_retention_days = 3

# Telegram Mini App Configuration (same as dev - for testing)
telegram_webapp_url = "https://demjoigiw6myp.cloudfront.net"

# CORS: Same as dev for testing
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net",
  "https://d3uuexs20crp9s.cloudfront.net"
]

# Aurora MySQL Configuration (SHARED with dev - same cluster)
aurora_min_acu = 0.5
aurora_max_acu = 2
aurora_database_name = "ticker_data"
aurora_master_username = "admin"

# Lambda image tag (same as dev - uses same Docker images)
lambda_image_tag = "pdf-timeout-fix-20260105-061221"
