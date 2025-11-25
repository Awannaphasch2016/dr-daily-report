output "lambda_function_arn" {
  value       = aws_lambda_function.line_bot.arn
  description = "ARN of the LINE Bot Lambda function"
}

output "lambda_function_name" {
  value       = aws_lambda_function.line_bot.function_name
  description = "Name of the LINE Bot Lambda function"
}

output "lambda_role_arn" {
  value       = aws_iam_role.line_bot_role.arn
  description = "ARN of the Lambda IAM role"
}

output "function_url" {
  value       = aws_lambda_function_url.line_bot.function_url
  description = "LINE Bot Function URL for webhook"
}
