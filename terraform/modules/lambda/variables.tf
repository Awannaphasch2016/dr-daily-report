# Lambda Module Variables
# Reusable Lambda function module for container image deployments

#------------------------------------------------------------------------------
# Required Variables
#------------------------------------------------------------------------------

variable "function_name" {
  description = "Name of the Lambda function (will be prefixed with project-name and suffixed with environment)"
  type        = string
}

variable "handler_command" {
  description = "Lambda handler command (e.g., 'telegram_lambda_handler.handler')"
  type        = string
}

variable "image_uri" {
  description = "Full ECR image URI including tag (e.g., '123456.dkr.ecr.region.amazonaws.com/repo:tag')"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

#------------------------------------------------------------------------------
# Lambda Configuration
#------------------------------------------------------------------------------

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

#------------------------------------------------------------------------------
# IAM Configuration
#------------------------------------------------------------------------------

variable "create_iam_role" {
  description = "Whether to create a new IAM role for this Lambda (false to use existing role_arn)"
  type        = bool
  default     = true
}

variable "role_arn" {
  description = "ARN of existing IAM role to use (required if create_iam_role = false)"
  type        = string
  default     = null
}

variable "additional_policy_statements" {
  description = "Additional IAM policy statements to attach to the Lambda role"
  type = list(object({
    Effect   = string
    Action   = list(string)
    Resource = any # Can be string or list(string)
  }))
  default = []
}

variable "managed_policy_arns" {
  description = "List of managed IAM policy ARNs to attach to the Lambda role"
  type        = list(string)
  default     = []
}

#------------------------------------------------------------------------------
# VPC Configuration (Optional)
#------------------------------------------------------------------------------

variable "vpc_enabled" {
  description = "Whether to deploy Lambda in VPC"
  type        = bool
  default     = false
}

variable "subnet_ids" {
  description = "List of subnet IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "List of security group IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

#------------------------------------------------------------------------------
# Alias Configuration
#------------------------------------------------------------------------------

variable "create_alias" {
  description = "Whether to create a 'live' alias for production traffic"
  type        = bool
  default     = true
}

#------------------------------------------------------------------------------
# Logging Configuration
#------------------------------------------------------------------------------

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 14
}

#------------------------------------------------------------------------------
# Tags
#------------------------------------------------------------------------------

variable "app_tag" {
  description = "App tag value for resource identification"
  type        = string
  default     = "shared"
}

variable "component_tag" {
  description = "Component tag value for resource identification"
  type        = string
  default     = "lambda"
}

variable "extra_tags" {
  description = "Additional tags specific to this Lambda"
  type        = map(string)
  default     = {}
}
