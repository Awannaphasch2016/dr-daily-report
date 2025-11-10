# Terraform Outputs for LINE Bot Infrastructure

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.line_bot.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.line_bot.arn
}

output "lambda_function_version" {
  description = "Version of the Lambda function"
  value       = aws_lambda_function.line_bot.version
}

output "webhook_url" {
  description = "Lambda Function URL for LINE webhook"
  value       = aws_lambda_function_url.line_webhook.function_url
}

output "pdf_storage_bucket" {
  description = "S3 bucket name for PDF reports storage"
  value       = aws_s3_bucket.pdf_reports.id
}

# Summary output for easy reference
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    function_name = aws_lambda_function.line_bot.function_name
    webhook_url   = aws_lambda_function_url.line_webhook.function_url
    region        = var.aws_region
    environment   = var.environment
  }
}
