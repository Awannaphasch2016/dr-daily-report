# Variables for SQS ETL Queue Module

# ============================================================================
# Required Variables
# ============================================================================

variable "queue_name" {
  description = "Name of the SQS queue (should include environment suffix: -dev, -staging, -prod)"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]+$", var.queue_name))
    error_message = "Queue name must contain only alphanumeric characters, hyphens, and underscores."
  }

  validation {
    condition = (
      endswith(var.queue_name, "-dev") ||
      endswith(var.queue_name, "-staging") ||
      endswith(var.queue_name, "-prod")
    )
    error_message = "Queue name must end with environment suffix (-dev, -staging, or -prod)."
  }
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)

  validation {
    condition     = contains(keys(var.common_tags), "Environment")
    error_message = "common_tags must include 'Environment' key."
  }
}

# ============================================================================
# Queue Configuration
# ============================================================================

variable "message_retention_seconds" {
  description = "Time (in seconds) that messages are retained in the queue (1 minute to 14 days)"
  type        = number
  default     = 345600 # 4 days (good balance for ETL debugging)

  validation {
    condition     = var.message_retention_seconds >= 60 && var.message_retention_seconds <= 1209600
    error_message = "Message retention must be between 60 seconds (1 minute) and 1209600 seconds (14 days)."
  }

  validation {
    condition     = var.message_retention_seconds >= 86400
    error_message = "ETL pipelines should retain messages for at least 1 day (86400s) for debugging."
  }
}

variable "visibility_timeout_seconds" {
  description = "Time (in seconds) that a message is invisible after being received (should be 2x max processing time)"
  type        = number
  default     = 120 # 2 minutes (CSV parse + batch upsert ~30-60s)

  validation {
    condition     = var.visibility_timeout_seconds >= 0 && var.visibility_timeout_seconds <= 43200
    error_message = "Visibility timeout must be between 0 and 43200 seconds (12 hours)."
  }

  validation {
    condition     = var.visibility_timeout_seconds >= 60
    error_message = "ETL processing requires minimum 60s visibility timeout to prevent duplicate processing."
  }
}

variable "max_message_size" {
  description = "Maximum message size in bytes (1024 to 262144)"
  type        = number
  default     = 262144 # 256 KB (stores S3 event metadata, not CSV file itself)

  validation {
    condition     = var.max_message_size >= 1024 && var.max_message_size <= 262144
    error_message = "Max message size must be between 1024 bytes (1 KB) and 262144 bytes (256 KB)."
  }
}

variable "receive_wait_time_seconds" {
  description = "Time (in seconds) for long polling (0 = short polling, 1-20 = long polling)"
  type        = number
  default     = 20 # Maximum long polling (reduces API calls and cost)

  validation {
    condition     = var.receive_wait_time_seconds >= 0 && var.receive_wait_time_seconds <= 20
    error_message = "Receive wait time must be between 0 and 20 seconds."
  }
}

variable "delay_seconds" {
  description = "Time (in seconds) to delay message delivery (0 to 900)"
  type        = number
  default     = 0 # No delay for real-time ETL

  validation {
    condition     = var.delay_seconds >= 0 && var.delay_seconds <= 900
    error_message = "Delay seconds must be between 0 and 900 seconds (15 minutes)."
  }
}

# ============================================================================
# Dead Letter Queue Configuration
# ============================================================================

variable "max_receive_count" {
  description = "Number of times a message can be received before moving to DLQ (3-5 recommended for ETL)"
  type        = number
  default     = 3

  validation {
    condition     = var.max_receive_count >= 1 && var.max_receive_count <= 10
    error_message = "Max receive count must be between 1 and 10."
  }

  validation {
    condition     = var.max_receive_count >= 3 && var.max_receive_count <= 5
    error_message = "ETL pipelines should allow 3-5 retries before sending to DLQ."
  }
}

variable "dlq_message_retention_seconds" {
  description = "Time (in seconds) that messages are retained in the DLQ"
  type        = number
  default     = 1209600 # 14 days (maximum retention for investigation)

  validation {
    condition     = var.dlq_message_retention_seconds >= 60 && var.dlq_message_retention_seconds <= 1209600
    error_message = "DLQ message retention must be between 60 seconds and 1209600 seconds (14 days)."
  }
}

variable "dlq_visibility_timeout_seconds" {
  description = "Visibility timeout for DLQ (short since DLQ messages are not processed)"
  type        = number
  default     = 30 # Short timeout (DLQ is for investigation, not processing)

  validation {
    condition     = var.dlq_visibility_timeout_seconds >= 0 && var.dlq_visibility_timeout_seconds <= 43200
    error_message = "DLQ visibility timeout must be between 0 and 43200 seconds."
  }
}

# ============================================================================
# Encryption Configuration
# ============================================================================

variable "kms_master_key_id" {
  description = "KMS key ID for SSE-KMS encryption (null = use SSE-SQS managed encryption)"
  type        = string
  default     = null
}

variable "kms_data_key_reuse_period_seconds" {
  description = "Time (in seconds) that SQS can reuse a data key (60 to 86400)"
  type        = number
  default     = 300 # 5 minutes

  validation {
    condition     = var.kms_data_key_reuse_period_seconds >= 60 && var.kms_data_key_reuse_period_seconds <= 86400
    error_message = "KMS data key reuse period must be between 60 and 86400 seconds."
  }
}

# ============================================================================
# S3 Event Source Configuration
# ============================================================================

variable "allow_s3_event_source" {
  description = "Whether to allow S3 to send events to this queue"
  type        = bool
  default     = true
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs allowed to send events to this queue"
  type        = list(string)
  default     = []
}

# ============================================================================
# CloudWatch Alarms Configuration
# ============================================================================

variable "enable_cloudwatch_alarms" {
  description = "Whether to create CloudWatch alarms for queue monitoring"
  type        = bool
  default     = true
}

variable "alarm_sns_topic_arns" {
  description = "List of SNS topic ARNs to notify on alarm"
  type        = list(string)
  default     = []
}

variable "dlq_alarm_threshold" {
  description = "Number of messages in DLQ before triggering alarm"
  type        = number
  default     = 1 # Alert on first DLQ message (indicates processing failure)

  validation {
    condition     = var.dlq_alarm_threshold >= 1
    error_message = "DLQ alarm threshold must be at least 1."
  }
}

variable "queue_depth_alarm_threshold" {
  description = "Number of messages in main queue before triggering alarm (backlog detection)"
  type        = number
  default     = 100

  validation {
    condition     = var.queue_depth_alarm_threshold >= 1
    error_message = "Queue depth alarm threshold must be at least 1."
  }
}

variable "message_age_alarm_threshold" {
  description = "Maximum age (in seconds) of oldest message before triggering alarm"
  type        = number
  default     = 3600 # 1 hour (indicates processing stalled)

  validation {
    condition     = var.message_age_alarm_threshold >= 60
    error_message = "Message age alarm threshold must be at least 60 seconds."
  }
}

# ============================================================================
# Metadata
# ============================================================================

variable "queue_purpose" {
  description = "Purpose of this queue (used in tags and documentation)"
  type        = string
  default     = "etl-processing"
}

variable "data_source" {
  description = "Data source for this ETL pipeline (used in tags)"
  type        = string
  default     = "s3-csv-import"
}
