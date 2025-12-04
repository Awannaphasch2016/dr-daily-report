# SQS Module Variables
# Reusable SQS queue module with DLQ support

#------------------------------------------------------------------------------
# Required Variables
#------------------------------------------------------------------------------

variable "queue_name" {
  description = "Name of the SQS queue (will be prefixed with project-name and suffixed with environment)"
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

#------------------------------------------------------------------------------
# Queue Configuration
#------------------------------------------------------------------------------

variable "visibility_timeout_seconds" {
  description = "Visibility timeout in seconds (should be 2x Lambda timeout)"
  type        = number
  default     = 120
}

variable "message_retention_seconds" {
  description = "Message retention period in seconds (default: 1 hour)"
  type        = number
  default     = 3600
}

variable "receive_wait_time_seconds" {
  description = "Long polling wait time (0-20 seconds, default: 10 for cost efficiency)"
  type        = number
  default     = 10
}

variable "delay_seconds" {
  description = "Delay before messages become visible (0-900 seconds)"
  type        = number
  default     = 0
}

variable "max_message_size" {
  description = "Maximum message size in bytes (1-262144, default: 262144 = 256KB)"
  type        = number
  default     = 262144
}

#------------------------------------------------------------------------------
# Dead Letter Queue Configuration
#------------------------------------------------------------------------------

variable "create_dlq" {
  description = "Whether to create a Dead Letter Queue"
  type        = bool
  default     = true
}

variable "dlq_message_retention_seconds" {
  description = "Message retention for DLQ (default: 14 days for debugging)"
  type        = number
  default     = 1209600
}

variable "max_receive_count" {
  description = "Number of receives before message moves to DLQ (1 = no retries)"
  type        = number
  default     = 1
}

#------------------------------------------------------------------------------
# Lambda Integration (Optional)
#------------------------------------------------------------------------------

variable "create_lambda_trigger" {
  description = "Whether to create Lambda event source mapping"
  type        = bool
  default     = false
}

variable "lambda_function_arn" {
  description = "ARN of Lambda function to trigger (required if create_lambda_trigger = true)"
  type        = string
  default     = null
}

variable "lambda_batch_size" {
  description = "Number of messages to process per Lambda invocation"
  type        = number
  default     = 1
}

variable "lambda_maximum_batching_window_seconds" {
  description = "Maximum time to wait for batch (0 for no batching)"
  type        = number
  default     = 0
}

#------------------------------------------------------------------------------
# Tags
#------------------------------------------------------------------------------

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "app_tag" {
  description = "App tag value for resource identification"
  type        = string
  default     = "shared"
}

variable "component_tag" {
  description = "Component tag value for resource identification"
  type        = string
  default     = "job-queue"
}
