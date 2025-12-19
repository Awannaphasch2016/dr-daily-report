# Terraform Variables for LINE Bot Infrastructure

variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "project_name" {
  description = "Project name for resource naming and tagging"
  type        = string
  default     = "dr-daily-report"
}

variable "owner" {
  description = "Team or individual responsible for the resources"
  type        = string
  default     = "data-team"
}

variable "cost_center" {
  description = "Cost center for billing attribution"
  type        = string
  default     = "engineering"
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "line-bot-ticker-report"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository for Lambda container images"
  type        = string
  default     = "line-bot-ticker-report"
}

variable "lambda_memory" {
  description = "Memory size for Lambda function in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 60
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 7
}

###############################################################################
# Environment Variables for Lambda
# NOTE: Variable names are UPPERCASE to match Doppler's TF_VAR_* naming
# (Doppler requires UPPER_SNAKE_CASE for secret names)
###############################################################################

variable "OPENROUTER_API_KEY" {
  description = "OpenRouter API key for the Lambda function (provides access to OpenAI models)"
  type        = string
  sensitive   = true

  validation {
    condition     = !can(regex("placeholder", var.OPENROUTER_API_KEY))
    error_message = "OPENROUTER_API_KEY contains 'placeholder' - Doppler value not injected. Run with: doppler run -- terraform plan"
  }
}

variable "LINE_CHANNEL_ACCESS_TOKEN" {
  description = "LINE channel access token"
  type        = string
  sensitive   = true

  validation {
    condition     = !can(regex("placeholder", var.LINE_CHANNEL_ACCESS_TOKEN))
    error_message = "LINE_CHANNEL_ACCESS_TOKEN contains 'placeholder' - Doppler value not injected. Run with: doppler run -- terraform plan"
  }
}

variable "LINE_CHANNEL_SECRET" {
  description = "LINE channel secret"
  type        = string
  sensitive   = true

  validation {
    condition     = !can(regex("placeholder", var.LINE_CHANNEL_SECRET))
    error_message = "LINE_CHANNEL_SECRET contains 'placeholder' - Doppler value not injected. Run with: doppler run -- terraform plan"
  }
}

###############################################################################
# Telegram Mini App Variables
###############################################################################

variable "telegram_bot_token" {
  description = "Telegram Bot Token for Mini App"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_app_id" {
  description = "Telegram App ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_app_hash" {
  description = "Telegram App Hash"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_webapp_url" {
  description = "Telegram Mini App WebApp URL (legacy, use telegram_webapp_urls for multiple)"
  type        = string
  default     = ""
}

variable "telegram_webapp_urls" {
  description = "List of Telegram Mini App WebApp URLs (for CORS - dev, staging, prod)"
  type        = list(string)
  default     = []
}

###############################################################################
# Langfuse Observability Variables
###############################################################################

variable "LANGFUSE_PUBLIC_KEY" {
  description = "Langfuse public API key for tracing"
  type        = string
  sensitive   = true
  default     = ""
}

variable "LANGFUSE_SECRET_KEY" {
  description = "Langfuse secret API key for tracing"
  type        = string
  sensitive   = true
  default     = ""
}

variable "LANGFUSE_HOST" {
  description = "Langfuse instance URL (cloud or self-hosted)"
  type        = string
  default     = "https://cloud.langfuse.com"
}

###############################################################################
# Lambda Container Image Configuration
###############################################################################

variable "lambda_image_tag" {
  description = "Docker image tag for Lambda functions (set by CI/CD, e.g., 'v20251201182404'). Use 'latest' only for initial bootstrap."
  type        = string
  default     = "latest"

  # Note: CI/CD should override this with timestamped tag:
  # terraform apply -var="lambda_image_tag=v20251201182404"
}

###############################################################################
# Terraform IAM Role Configuration (AssumeRole Pattern)
###############################################################################

variable "terraform_user_name" {
  description = "IAM user name allowed to assume TerraformDeployRole"
  type        = string
  default     = "anak"
}

variable "terraform_external_id" {
  description = "External ID for AssumeRole (optional security measure)"
  type        = string
  default     = ""
}

variable "use_assume_role" {
  description = "Whether to use AssumeRole pattern for Terraform operations"
  type        = bool
  default     = false
}

variable "terraform_role_arn" {
  description = "ARN of Terraform deployment role (required if use_assume_role = true)"
  type        = string
  default     = ""
}
