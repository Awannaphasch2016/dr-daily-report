# Lambda Module - Outputs
# Expose Lambda function and related resource attributes

#------------------------------------------------------------------------------
# Lambda Function Outputs
#------------------------------------------------------------------------------

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "ARN for invoking the Lambda function (for API Gateway integration)"
  value       = aws_lambda_function.this.invoke_arn
}

output "version" {
  description = "Published version of the Lambda function"
  value       = aws_lambda_function.this.version
}

output "qualified_arn" {
  description = "ARN with version suffix"
  value       = aws_lambda_function.this.qualified_arn
}

#------------------------------------------------------------------------------
# Lambda Alias Outputs
#------------------------------------------------------------------------------

output "alias_name" {
  description = "Name of the Lambda alias (null if create_alias = false)"
  value       = var.create_alias ? aws_lambda_alias.live[0].name : null
}

output "alias_arn" {
  description = "ARN of the Lambda 'live' alias (null if create_alias = false)"
  value       = var.create_alias ? aws_lambda_alias.live[0].arn : null
}

output "alias_invoke_arn" {
  description = "Invoke ARN of the Lambda 'live' alias (null if create_alias = false)"
  value       = var.create_alias ? aws_lambda_alias.live[0].invoke_arn : null
}

#------------------------------------------------------------------------------
# IAM Role Outputs
#------------------------------------------------------------------------------

output "role_arn" {
  description = "ARN of the Lambda IAM role (null if create_iam_role = false)"
  value       = var.create_iam_role ? aws_iam_role.lambda[0].arn : null
}

output "role_name" {
  description = "Name of the Lambda IAM role (null if create_iam_role = false)"
  value       = var.create_iam_role ? aws_iam_role.lambda[0].name : null
}

output "role_id" {
  description = "ID of the Lambda IAM role for attaching additional policies"
  value       = var.create_iam_role ? aws_iam_role.lambda[0].id : null
}

#------------------------------------------------------------------------------
# CloudWatch Log Group Output
#------------------------------------------------------------------------------

output "log_group_name" {
  description = "Name of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.logs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.logs.arn
}
