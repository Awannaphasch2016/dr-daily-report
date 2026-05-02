###############################################################################
# QuantAgent Report Generation Lambda
#
# Multi-agent Writer/Judge inner loop for iterative report refinement.
# Invoked by report_worker when REPORT_GENERATION_MODE=quant_agent.
# Same Docker image, different handler entry point.
###############################################################################

# Variables
variable "report_generation_mode" {
  description = "Report generation mode: 'single_pass' (existing) or 'quant_agent' (multi-agent loop)"
  type        = string
  default     = "single_pass"

  validation {
    condition     = contains(["single_pass", "quant_agent"], var.report_generation_mode)
    error_message = "report_generation_mode must be 'single_pass' or 'quant_agent'"
  }
}

variable "quant_agent_beta" {
  description = "Quality score threshold (0-100) for QuantAgent inner loop"
  type        = number
  default     = 75
}

variable "quant_agent_max_iterations" {
  description = "Maximum Writer/Judge iterations in QuantAgent inner loop"
  type        = number
  default     = 3
}

###############################################################################
# IAM Role
###############################################################################

resource "aws_iam_role" "quant_agent_role" {
  name = "${var.project_name}-quant-agent-role-${var.environment}"

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

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-quant-agent-role-${var.environment}"
    App       = "telegram-api"
    Component = "iam-role"
  })
}

resource "aws_iam_role_policy_attachment" "quant_agent_basic" {
  role       = aws_iam_role.quant_agent_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "quant_agent_vpc" {
  role       = aws_iam_role.quant_agent_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "quant_agent_aurora_access" {
  role       = aws_iam_role.quant_agent_role.name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

resource "aws_iam_role_policy" "quant_agent_policy" {
  name = "${var.project_name}-quant-agent-policy-${var.environment}"
  role = aws_iam_role.quant_agent_role.id

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
# Lambda Function
###############################################################################

resource "aws_lambda_function" "quant_agent" {
  function_name = "${var.project_name}-quant-agent-${var.environment}"
  role          = aws_iam_role.quant_agent_role.arn

  # Same container image as report_worker, different handler
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["quant_agent_handler.handler"]
  }

  publish = true

  memory_size = 2048  # Higher memory for multiple LLM calls per iteration
  timeout     = 120   # 120s budget for inner loop (typically ~22s worst case)

  environment {
    variables = {
      TZ = "Asia/Bangkok"

      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY

      # Langfuse Observability
      LANGFUSE_PUBLIC_KEY          = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY          = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST                = var.LANGFUSE_HOST
      LANGFUSE_TRACING_ENVIRONMENT = var.LANGFUSE_TRACING_ENVIRONMENT

      # Aurora MySQL connection (needed by ScoringService context)
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      # QuantAgent configuration
      QUANT_AGENT_BETA           = tostring(var.quant_agent_beta)
      QUANT_AGENT_MAX_ITERATIONS = tostring(var.quant_agent_max_iterations)
      QUANT_AGENT_TIMEOUT_BUDGET = "90"
      QUANT_AGENT_JUDGE_MODEL    = "openai/gpt-4o-mini"
      QUANT_AGENT_WRITER_MODEL   = "openai/gpt-4o"
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-quant-agent-${var.environment}"
    App       = "telegram-api"
    Component = "quant-agent"
    Trigger   = "lambda-invoke"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.quant_agent_basic
  ]
}

###############################################################################
# Lambda Alias
###############################################################################

resource "aws_lambda_alias" "quant_agent_live" {
  name             = "live"
  description      = "Production alias for quant agent"
  function_name    = aws_lambda_function.quant_agent.function_name
  function_version = aws_lambda_function.quant_agent.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

###############################################################################
# IAM: Allow report_worker to invoke quant_agent
###############################################################################

resource "aws_iam_role_policy" "report_worker_invoke_quant_agent" {
  name = "${var.project_name}-worker-invoke-quant-agent-${var.environment}"
  role = aws_iam_role.report_worker_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.quant_agent.arn
      }
    ]
  })
}
