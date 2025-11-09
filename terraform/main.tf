# Terraform configuration for LINE Bot Lambda Function
# This manages the Lambda function, API Gateway, and related resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source: Get current AWS account ID
data "aws_caller_identity" "current" {}

# Data source: Get current AWS region
data "aws_region" "current" {}

###############################################################################
# ECR Repository for Lambda Container Images
###############################################################################

resource "aws_ecr_repository" "lambda_repo" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = var.ecr_repository_name
    Environment = var.environment
    Project     = "LineBot"
  }
}

# ECR lifecycle policy to keep only recent images
resource "aws_ecr_lifecycle_policy" "lambda_repo_policy" {
  repository = aws_ecr_repository.lambda_repo.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}

###############################################################################
# Docker Image Build and Push
###############################################################################

# Build and push Docker image to ECR
resource "null_resource" "docker_build_push" {
  # Trigger rebuild when Dockerfile or source code changes
  triggers = {
    dockerfile_hash = filemd5("${path.module}/../Dockerfile.lambda.container")
    always_run      = timestamp() # Always rebuild for now
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Login to ECR
      aws ecr get-login-password --region ${var.aws_region} | \
        docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com

      # Build Docker image
      docker build -f Dockerfile.lambda.container -t ${var.function_name}:latest .

      # Tag image for ECR
      docker tag ${var.function_name}:latest \
        ${aws_ecr_repository.lambda_repo.repository_url}:latest

      # Push to ECR
      docker push ${aws_ecr_repository.lambda_repo.repository_url}:latest
    EOT

    working_dir = "${path.module}/.."
  }

  depends_on = [aws_ecr_repository.lambda_repo]
}

###############################################################################
# IAM Role for Lambda
###############################################################################

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

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

  tags = {
    Name        = "${var.function_name}-role"
    Environment = var.environment
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for additional permissions (if needed)
resource "aws_iam_role_policy" "lambda_custom" {
  name = "${var.function_name}-custom-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

###############################################################################
# Lambda Function (Container Image)
###############################################################################

resource "aws_lambda_function" "line_bot" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_role.arn

  # Container image configuration
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda_repo.repository_url}:latest"

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment {
    variables = {
      OPENAI_API_KEY              = var.openai_api_key
      LINE_CHANNEL_ACCESS_TOKEN   = var.line_channel_access_token
      LINE_CHANNEL_SECRET         = var.line_channel_secret
    }
  }

  tags = {
    Name        = var.function_name
    Environment = var.environment
    Project     = "LineBot"
  }

  depends_on = [
    null_resource.docker_build_push,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.function_name}-logs"
    Environment = var.environment
  }
}

###############################################################################
# API Gateway (HTTP API) for LINE Webhook
###############################################################################

resource "aws_apigatewayv2_api" "line_webhook" {
  name          = "${var.function_name}-api"
  protocol_type = "HTTP"

  description = "LINE Bot webhook endpoint"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET"]
    allow_headers = ["*"]
  }

  tags = {
    Name        = "${var.function_name}-api"
    Environment = var.environment
  }
}

# API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda" {
  api_id = aws_apigatewayv2_api.line_webhook.id

  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.line_bot.invoke_arn
  integration_method = "POST"

  payload_format_version = "2.0"
}

# API Gateway Route
resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.line_webhook.id
  route_key = "POST /webhook"

  target = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# API Gateway Stage (default)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.line_webhook.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = {
    Name        = "${var.function_name}-stage"
    Environment = var.environment
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.function_name}-api-logs"
    Environment = var.environment
  }
}

# Lambda permission for API Gateway to invoke
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.line_bot.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.line_webhook.execution_arn}/*/*"
}
