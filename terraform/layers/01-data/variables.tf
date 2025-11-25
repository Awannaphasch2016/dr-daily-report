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
