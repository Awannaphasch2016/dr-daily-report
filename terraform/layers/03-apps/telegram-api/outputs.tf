output "lambda_function_arn" {
  value       = aws_lambda_function.telegram_api.arn
  description = "ARN of the Telegram API Lambda function"
}

output "lambda_function_name" {
  value       = aws_lambda_function.telegram_api.function_name
  description = "Name of the Telegram API Lambda function"
}

output "lambda_role_arn" {
  value       = aws_iam_role.telegram_lambda_role.arn
  description = "ARN of the Lambda IAM role"
}

output "api_gateway_url" {
  value       = aws_apigatewayv2_api.telegram_api.api_endpoint
  description = "Base URL for Telegram API Gateway"
}

output "api_gateway_id" {
  value       = aws_apigatewayv2_api.telegram_api.id
  description = "ID of the API Gateway"
}

output "api_invoke_url" {
  value       = "${aws_apigatewayv2_api.telegram_api.api_endpoint}/api/v1"
  description = "Full invoke URL with /api/v1 prefix"
}
