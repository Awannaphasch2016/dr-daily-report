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
###############################################################################

variable "openai_api_key" {
  description = "OpenAI API key for the Lambda function"
  type        = string
  sensitive   = true
}

variable "line_channel_access_token" {
  description = "LINE channel access token"
  type        = string
  sensitive   = true
}

variable "line_channel_secret" {
  description = "LINE channel secret"
  type        = string
  sensitive   = true
}
