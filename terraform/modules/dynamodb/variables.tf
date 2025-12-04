# DynamoDB Module Variables
# Reusable DynamoDB table module with flexible schema support

#------------------------------------------------------------------------------
# Required Variables
#------------------------------------------------------------------------------

variable "table_name" {
  description = "Name of the DynamoDB table (will be prefixed with project-name and suffixed with environment)"
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
# Key Schema
#------------------------------------------------------------------------------

variable "hash_key" {
  description = "Hash key (partition key) attribute name"
  type        = string
}

variable "hash_key_type" {
  description = "Hash key attribute type (S = String, N = Number, B = Binary)"
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "hash_key_type must be S, N, or B"
  }
}

variable "range_key" {
  description = "Range key (sort key) attribute name (optional)"
  type        = string
  default     = null
}

variable "range_key_type" {
  description = "Range key attribute type (S = String, N = Number, B = Binary)"
  type        = string
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.range_key_type)
    error_message = "range_key_type must be S, N, or B"
  }
}

#------------------------------------------------------------------------------
# Billing Configuration
#------------------------------------------------------------------------------

variable "billing_mode" {
  description = "DynamoDB billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.billing_mode)
    error_message = "billing_mode must be PAY_PER_REQUEST or PROVISIONED"
  }
}

variable "read_capacity" {
  description = "Read capacity units (only used if billing_mode = PROVISIONED)"
  type        = number
  default     = 5
}

variable "write_capacity" {
  description = "Write capacity units (only used if billing_mode = PROVISIONED)"
  type        = number
  default     = 5
}

#------------------------------------------------------------------------------
# TTL Configuration
#------------------------------------------------------------------------------

variable "ttl_enabled" {
  description = "Whether to enable TTL on the table"
  type        = bool
  default     = true
}

variable "ttl_attribute_name" {
  description = "Name of the TTL attribute (must be Number type containing Unix timestamp)"
  type        = string
  default     = "ttl"
}

#------------------------------------------------------------------------------
# Global Secondary Indexes (Optional)
#------------------------------------------------------------------------------

variable "global_secondary_indexes" {
  description = "List of Global Secondary Indexes to create"
  type = list(object({
    name               = string
    hash_key           = string
    range_key          = optional(string)
    projection_type    = optional(string, "ALL")
    non_key_attributes = optional(list(string))
    read_capacity      = optional(number)
    write_capacity     = optional(number)
  }))
  default = []
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
  default     = "dynamodb"
}

variable "data_type_tag" {
  description = "DataType tag value describing the data stored"
  type        = string
  default     = "general"
}
