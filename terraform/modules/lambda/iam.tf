# Lambda Module - IAM Resources
# Optional IAM role creation with configurable policies

#------------------------------------------------------------------------------
# IAM Role (optional - only created if create_iam_role = true)
#------------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  count = var.create_iam_role ? 1 : 0

  name = "${local.full_function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = merge(local.resource_tags, {
    Component = "iam-role"
  })
}

#------------------------------------------------------------------------------
# Basic Lambda Execution Policy (required for CloudWatch Logs)
#------------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "basic_execution" {
  count = var.create_iam_role ? 1 : 0

  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#------------------------------------------------------------------------------
# VPC Execution Policy (required for Lambda in VPC)
#------------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "vpc_execution" {
  count = var.create_iam_role && var.vpc_enabled ? 1 : 0

  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

#------------------------------------------------------------------------------
# Managed Policy Attachments (additional AWS managed or custom policies)
#------------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "managed_policies" {
  count = var.create_iam_role ? length(var.managed_policy_arns) : 0

  role       = aws_iam_role.lambda[0].name
  policy_arn = var.managed_policy_arns[count.index]
}

#------------------------------------------------------------------------------
# Custom Inline Policy (for additional permissions)
#------------------------------------------------------------------------------

resource "aws_iam_role_policy" "custom" {
  count = var.create_iam_role && length(var.additional_policy_statements) > 0 ? 1 : 0

  name = "${local.full_function_name}-custom-policy"
  role = aws_iam_role.lambda[0].id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = var.additional_policy_statements
  })
}
