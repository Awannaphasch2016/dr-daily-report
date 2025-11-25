variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "dr-daily-report"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
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
# Sensitive Variables (passed from tfvars or environment)
###############################################################################

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token"
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
  description = "Telegram Mini App WebApp URL"
  type        = string
  default     = ""
}

variable "langsmith_tracing_enabled" {
  description = "Enable LangSmith tracing"
  type        = bool
  default     = false
}

variable "langsmith_api_key" {
  description = "LangSmith API key"
  type        = string
  sensitive   = true
  default     = ""
}
