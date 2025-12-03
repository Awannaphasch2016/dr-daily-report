# CodeBuild for VPC Integration Tests
#
# Purpose:
#   Runs Terratest integration tests inside VPC to verify Aurora connectivity.
#   GitHub Actions triggers this CodeBuild project after successful deployments.
#
# Why CodeBuild:
#   GitHub Actions runners cannot reach Aurora in private VPC.
#   CodeBuild can be attached to VPC with same network access as Lambda.
#
# Tests Run:
#   - Aurora cache-first behavior tests
#   - Direct database query tests
#   - Lambda→Aurora integration tests
#
# Cost Estimate:
#   BUILD_GENERAL1_SMALL: ~$0.005/min × ~10 min/run = $0.05/run
#   Expected: ~$10-15/month during active development

###############################################################################
# CodeBuild Project for VPC Tests
###############################################################################

resource "aws_codebuild_project" "vpc_tests" {
  count = var.aurora_enabled ? 1 : 0

  name          = "${var.project_name}-vpc-tests-${var.environment}"
  description   = "Run Terratest integration tests inside VPC (Aurora access)"
  build_timeout = 30 # minutes

  service_role = aws_iam_role.codebuild_vpc_tests[0].arn

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/amazonlinux2-x86_64-standard:5.0" # Has Go 1.21
    type            = "LINUX_CONTAINER"
    privileged_mode = false

    # Aurora connection (matches Lambda pattern from telegram_api.tf)
    environment_variable {
      name  = "AURORA_HOST"
      value = aws_rds_cluster.aurora[0].endpoint
    }
    environment_variable {
      name  = "AURORA_PORT"
      value = "3306"
    }
    environment_variable {
      name  = "AURORA_DATABASE"
      value = var.aurora_database_name
    }
    environment_variable {
      name  = "AURORA_USER"
      value = var.aurora_master_username
    }
    environment_variable {
      name  = "AURORA_PASSWORD"
      type  = "SECRETS_MANAGER"
      value = "${aws_secretsmanager_secret.aurora_credentials[0].arn}:password::"
    }
    environment_variable {
      name  = "ENVIRONMENT"
      value = var.environment
    }
    environment_variable {
      name  = "TELEGRAM_API_URL"
      value = aws_apigatewayv2_api.telegram_api.api_endpoint
    }
    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
  }

  # VPC Configuration - CRITICAL: Uses same subnets as Lambda
  vpc_config {
    vpc_id             = data.aws_vpc.default.id
    subnets            = local.private_subnets_with_nat # NAT-routed subnets
    security_group_ids = [aws_security_group.codebuild_vpc[0].id]
  }

  source {
    type      = "NO_SOURCE" # Code provided via start-build --source-location-override
    buildspec = file("${path.module}/tests/buildspec.yml")
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${var.project_name}-vpc-tests-${var.environment}"
      stream_name = "build-log"
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-vpc-tests"
    App       = "shared"
    Component = "vpc-integration-tests"
  })
}

###############################################################################
# Security Group for CodeBuild (mirrors Lambda Aurora security group pattern)
###############################################################################

resource "aws_security_group" "codebuild_vpc" {
  count = var.aurora_enabled ? 1 : 0

  name        = "${var.project_name}-codebuild-vpc-${var.environment}"
  description = "Security group for CodeBuild VPC tests - Aurora access"
  vpc_id      = data.aws_vpc.default.id

  # No ingress (CodeBuild doesn't need inbound connections)

  # All outbound (Aurora, internet for Go modules, API Gateway)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-codebuild-vpc-sg"
    App       = "shared"
    Component = "codebuild-security-group"
  })
}

# Add CodeBuild to Aurora security group ingress
resource "aws_security_group_rule" "aurora_from_codebuild" {
  count = var.aurora_enabled ? 1 : 0

  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.aurora[0].id
  source_security_group_id = aws_security_group.codebuild_vpc[0].id
  description              = "Allow CodeBuild VPC tests to connect to Aurora"
}

###############################################################################
# IAM Role for CodeBuild
###############################################################################

resource "aws_iam_role" "codebuild_vpc_tests" {
  count = var.aurora_enabled ? 1 : 0

  name = "${var.project_name}-codebuild-vpc-tests-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "codebuild.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-codebuild-vpc-tests-role"
    App       = "shared"
    Component = "iam-role"
  })
}

resource "aws_iam_role_policy" "codebuild_vpc_tests" {
  count = var.aurora_enabled ? 1 : 0

  name = "codebuild-vpc-tests-policy"
  role = aws_iam_role.codebuild_vpc_tests[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/*"
      },
      # VPC networking (required for VPC-attached CodeBuild)
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeVpcs",
          "ec2:CreateNetworkInterfacePermission"
        ]
        Resource = "*"
      },
      # Secrets Manager (Aurora password)
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.aurora_credentials[0].arn
      },
      # Read-only AWS SDK calls for tests (Lambda, API Gateway, DynamoDB)
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:GetAlias",
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "apigateway:GET"
        ]
        Resource = [
          "arn:aws:apigateway:${var.aws_region}::/apis/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}-*"
        ]
      }
    ]
  })
}

###############################################################################
# Outputs
###############################################################################

output "codebuild_project_name" {
  description = "CodeBuild project name for VPC tests (use in GitHub Actions)"
  value       = var.aurora_enabled ? aws_codebuild_project.vpc_tests[0].name : null
}

output "codebuild_project_arn" {
  description = "CodeBuild project ARN for VPC tests"
  value       = var.aurora_enabled ? aws_codebuild_project.vpc_tests[0].arn : null
}

output "codebuild_security_group_id" {
  description = "Security group ID for CodeBuild VPC tests"
  value       = var.aurora_enabled ? aws_security_group.codebuild_vpc[0].id : null
}
