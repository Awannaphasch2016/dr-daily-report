# S3 Data Lake Module Outputs

output "bucket_id" {
  description = "The ID (name) of the data lake bucket"
  value       = aws_s3_bucket.data_lake.id
}

output "bucket_arn" {
  description = "The ARN of the data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "bucket_name" {
  description = "The name of the data lake bucket"
  value       = aws_s3_bucket.data_lake.bucket
}

output "bucket_regional_domain_name" {
  description = "The regional domain name of the bucket"
  value       = aws_s3_bucket.data_lake.bucket_regional_domain_name
}

output "versioning_enabled" {
  description = "Whether versioning is enabled"
  value       = aws_s3_bucket_versioning.data_lake.versioning_configuration[0].status == "Enabled"
}

output "encryption_algorithm" {
  description = "The encryption algorithm used"
  value       = aws_s3_bucket_server_side_encryption_configuration.data_lake.rule[0].apply_server_side_encryption_by_default.sse_algorithm
}
