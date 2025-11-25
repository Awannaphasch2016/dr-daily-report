# Outputs for app layers to consume via remote state

output "ecr_repository_url" {
  value       = aws_ecr_repository.lambda.repository_url
  description = "ECR repository URL for Lambda container images"
}

output "ecr_repository_arn" {
  value       = aws_ecr_repository.lambda.arn
  description = "ECR repository ARN"
}

output "pdf_bucket_name" {
  value       = aws_s3_bucket.pdf_reports.id
  description = "S3 bucket name for PDF reports"
}

output "pdf_bucket_arn" {
  value       = aws_s3_bucket.pdf_reports.arn
  description = "S3 bucket ARN for PDF reports"
}
