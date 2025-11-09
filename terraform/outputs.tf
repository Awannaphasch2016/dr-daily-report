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

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.lambda_repo.repository_url
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.line_webhook.api_endpoint
}

output "webhook_url" {
  description = "Full webhook URL for LINE console"
  value       = "${aws_apigatewayv2_api.line_webhook.api_endpoint}/webhook"
}

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_apigatewayv2_api.line_webhook.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

# Summary output for easy reference
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    function_name  = aws_lambda_function.line_bot.function_name
    webhook_url    = "${aws_apigatewayv2_api.line_webhook.api_endpoint}/webhook"
    ecr_repository = aws_ecr_repository.lambda_repo.repository_url
    region         = var.aws_region
    environment    = var.environment
  }
}
