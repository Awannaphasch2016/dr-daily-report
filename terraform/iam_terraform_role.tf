# Terraform IAM Role for AssumeRole Pattern
# 
# This role allows the IAM user to assume elevated permissions for Terraform operations.
# The role has all necessary policies attached (no 10-policy limit).
# The user only needs minimal AssumeRole permissions.
#
# Usage:
#   1. Apply this Terraform configuration to create the role
#   2. Run scripts/iam_setup_assume_role.sh to configure user permissions
#   3. Use AWS_PROFILE=terraform for Terraform operations
#

#------------------------------------------------------------------------------
# IAM Role for Terraform Operations
#------------------------------------------------------------------------------

resource "aws_iam_role" "terraform_deploy" {
  name = "TerraformDeployRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/${var.terraform_user_name}"
        }
        Action = "sts:AssumeRole"
        # Optional: Add external ID condition for extra security
        # Condition = {
        #   StringEquals = {
        #     "sts:ExternalId" = var.terraform_external_id
        #   }
        # }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name      = "TerraformDeployRole"
    Component = "iam-role"
    Purpose   = "Terraform infrastructure deployment"
  })
}

#------------------------------------------------------------------------------
# Attach AWS Managed Policies (EC2, RDS, VPC)
#------------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "ec2_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

resource "aws_iam_role_policy_attachment" "rds_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
}

resource "aws_iam_role_policy_attachment" "vpc_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonVPCFullAccess"
}

#------------------------------------------------------------------------------
# Attach Custom Policies (ECR, SQS, etc.)
#------------------------------------------------------------------------------

# ECR Policy
resource "aws_iam_role_policy_attachment" "ecr_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = aws_iam_policy.ecr_access.arn
}

resource "aws_iam_policy" "ecr_access" {
  name        = "TerraformECRAccess-Role"
  description = "ECR access for Terraform operations (attached to role)"

  policy = file("${path.module}/iam-ecr-policy.json")

  tags = merge(local.common_tags, {
    Component = "iam-policy"
  })
}

# SQS Policy
resource "aws_iam_role_policy_attachment" "sqs_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = aws_iam_policy.sqs_access.arn
}

resource "aws_iam_policy" "sqs_access" {
  name        = "dr-daily-report-sqs-access-Role"
  description = "SQS permissions for dr-daily-report async infrastructure (attached to role)"

  policy = file("${path.module}/iam-sqs-policy.json")

  tags = merge(local.common_tags, {
    Component = "iam-policy"
  })
}

#------------------------------------------------------------------------------
# Additional Terraform Permissions
#------------------------------------------------------------------------------

# Lambda permissions (for Lambda deployments)
resource "aws_iam_role_policy_attachment" "lambda_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
}

# API Gateway permissions
resource "aws_iam_role_policy_attachment" "api_gateway_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator"
}

# CloudFront permissions
resource "aws_iam_role_policy_attachment" "cloudfront_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/CloudFrontFullAccess"
}

# S3 permissions
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# DynamoDB permissions
resource "aws_iam_role_policy_attachment" "dynamodb_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# CloudWatch Logs permissions
resource "aws_iam_role_policy_attachment" "cloudwatch_logs_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# EventBridge permissions (for schedulers)
resource "aws_iam_role_policy_attachment" "eventbridge_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess"
}

# IAM permissions (for creating Lambda execution roles)
resource "aws_iam_role_policy_attachment" "iam_full_access" {
  role       = aws_iam_role.terraform_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/IAMFullAccess"
}

#------------------------------------------------------------------------------
# Outputs
#------------------------------------------------------------------------------

output "terraform_role_arn" {
  description = "ARN of the Terraform deployment role"
  value       = aws_iam_role.terraform_deploy.arn
}

output "terraform_role_name" {
  description = "Name of the Terraform deployment role"
  value       = aws_iam_role.terraform_deploy.name
}
