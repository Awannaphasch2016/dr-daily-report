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
# NOTE: Variable names are UPPERCASE to match Doppler's TF_VAR_* naming
###############################################################################

variable "OPENROUTER_API_KEY" {
  description = "OpenRouter API key (provides access to OpenAI models)"
  type        = string
  sensitive   = true

  validation {
    condition     = !can(regex("placeholder", var.OPENROUTER_API_KEY))
    error_message = "OPENROUTER_API_KEY contains 'placeholder' - Doppler value not injected"
  }
}

variable "LINE_CHANNEL_ACCESS_TOKEN" {
  description = "LINE Channel Access Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "LINE_CHANNEL_SECRET" {
  description = "LINE Channel Secret"
  type        = string
  sensitive   = true
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
