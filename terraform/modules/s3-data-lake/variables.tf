# S3 Data Lake Module Variables

variable "project_name" {
  description = "Project name used in bucket naming"
  type        = string
  default     = "dr-daily-report"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "dr-daily-report"
    ManagedBy   = "terraform"
    Component   = "data-lake"
  }
}

variable "encryption_algorithm" {
  description = "Server-side encryption algorithm (AES256 or aws:kms)"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "aws:kms"], var.encryption_algorithm)
    error_message = "Encryption algorithm must be AES256 or aws:kms"
  }
}

variable "glacier_transition_days" {
  description = "Number of days before transitioning objects to Glacier"
  type        = number
  default     = 90
  validation {
    condition     = var.glacier_transition_days >= 30
    error_message = "Glacier transition must be at least 30 days"
  }
}

variable "deep_archive_transition_days" {
  description = "Number of days before transitioning objects to Deep Archive"
  type        = number
  default     = 365
  validation {
    condition     = var.deep_archive_transition_days >= 90
    error_message = "Deep Archive transition must be at least 90 days"
  }
}

variable "expiration_days" {
  description = "Number of days before objects expire (0 = never)"
  type        = number
  default     = 730  # 2 years
  validation {
    condition     = var.expiration_days == 0 || var.expiration_days >= 365
    error_message = "Expiration must be 0 (never) or at least 365 days"
  }
}

variable "enable_cors" {
  description = "Enable CORS configuration for direct browser uploads"
  type        = bool
  default     = false
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS (if enabled)"
  type        = list(string)
  default     = ["https://*.cloudfront.net"]
}
