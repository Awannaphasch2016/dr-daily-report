###############################################################################
# Report Pipeline — Split PreProcess → Generation → PostProcess
#
# Express Step Functions state machine orchestrating 3 Lambda phases.
# Feature-flagged via var.use_report_pipeline (default false).
# Same Docker image, different handler entry points.
###############################################################################

# Variables
variable "use_report_pipeline" {
  description = "Enable split report pipeline (Step Functions Express). When false, existing monolithic report_worker is used."
  type        = bool
  default     = false
}

variable "default_generation_strategy" {
  description = "Default generation strategy for the pipeline: 'single_pass' or 'quant_agent'"
  type        = string
  default     = "single_pass"
}

###############################################################################
# IAM Roles — One per Lambda (least-privilege)
###############################################################################

# --- PreProcess Role ---
resource "aws_iam_role" "pipeline_preprocess_role" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-preprocess-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-preprocess-role-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-preprocess-role"
  })
}

resource "aws_iam_role_policy_attachment" "pipeline_preprocess_basic" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_preprocess_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_preprocess_vpc" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_preprocess_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_preprocess_aurora" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_preprocess_role[0].name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

resource "aws_iam_role_policy" "pipeline_preprocess_policy" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-preprocess-policy-${var.environment}"
  role  = aws_iam_role.pipeline_preprocess_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${module.s3_data_lake.bucket_arn}/pipeline/*"
      }
    ]
  })
}

# --- Generation Role ---
resource "aws_iam_role" "pipeline_generation_role" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-generation-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-generation-role-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-generation-role"
  })
}

resource "aws_iam_role_policy_attachment" "pipeline_generation_basic" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_generation_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_generation_vpc" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_generation_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_generation_aurora" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_generation_role[0].name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

resource "aws_iam_role_policy" "pipeline_generation_policy" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-generation-policy-${var.environment}"
  role  = aws_iam_role.pipeline_generation_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${module.s3_data_lake.bucket_arn}/pipeline/*"
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.quant_agent_report.arn
      }
    ]
  })
}

# --- PostProcess Role ---
resource "aws_iam_role" "pipeline_postprocess_role" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-postprocess-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-postprocess-role-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-postprocess-role"
  })
}

resource "aws_iam_role_policy_attachment" "pipeline_postprocess_basic" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_postprocess_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_postprocess_vpc" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_postprocess_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "pipeline_postprocess_aurora" {
  count      = var.use_report_pipeline ? 1 : 0
  role       = aws_iam_role.pipeline_postprocess_role[0].name
  policy_arn = aws_iam_policy.lambda_aurora_access.arn
}

resource "aws_iam_role_policy" "pipeline_postprocess_policy" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-pipeline-postprocess-policy-${var.environment}"
  role  = aws_iam_role.pipeline_postprocess_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${module.s3_data_lake.bucket_arn}/pipeline/*"
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.report_jobs.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
      }
    ]
  })
}

###############################################################################
# Lambda Functions
###############################################################################

# --- PreProcess Lambda ---
resource "aws_lambda_function" "pipeline_preprocess" {
  count         = var.use_report_pipeline ? 1 : 0
  function_name = "${var.project_name}-pipeline-preprocess-${var.environment}"
  role          = aws_iam_role.pipeline_preprocess_role[0].arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.pipeline.preprocess_handler.handler"]
  }

  publish     = true
  memory_size = 1024
  timeout     = 120

  environment {
    variables = {
      TZ                 = "Asia/Bangkok"
      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
      DATA_LAKE_BUCKET   = module.s3_data_lake.bucket_id

      # Langfuse
      LANGFUSE_PUBLIC_KEY          = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY          = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST                = var.LANGFUSE_HOST
      LANGFUSE_TRACING_ENVIRONMENT = var.LANGFUSE_TRACING_ENVIRONMENT

      # Aurora
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-preprocess-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-preprocess"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.pipeline_preprocess_basic
  ]
}

# --- Generation Lambda ---
resource "aws_lambda_function" "pipeline_generation" {
  count         = var.use_report_pipeline ? 1 : 0
  function_name = "${var.project_name}-pipeline-generation-${var.environment}"
  role          = aws_iam_role.pipeline_generation_role[0].arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.pipeline.generation_handler.handler"]
  }

  publish     = true
  memory_size = 2048
  timeout     = 120

  environment {
    variables = {
      TZ                 = "Asia/Bangkok"
      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
      DATA_LAKE_BUCKET   = module.s3_data_lake.bucket_id
      LLM_MODEL          = "openai/gpt-4o"

      # Langfuse
      LANGFUSE_PUBLIC_KEY          = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY          = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST                = var.LANGFUSE_HOST
      LANGFUSE_TRACING_ENVIRONMENT = var.LANGFUSE_TRACING_ENVIRONMENT

      # Aurora (needed by ContextBuilder for model_catalog)
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      # QuantAgent function name (for delegation)
      QUANT_AGENT_FUNCTION_NAME = aws_lambda_function.quant_agent_report.function_name
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-generation-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-generation"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.pipeline_generation_basic
  ]
}

# --- PostProcess Lambda ---
resource "aws_lambda_function" "pipeline_postprocess" {
  count         = var.use_report_pipeline ? 1 : 0
  function_name = "${var.project_name}-pipeline-postprocess-${var.environment}"
  role          = aws_iam_role.pipeline_postprocess_role[0].arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["src.pipeline.postprocess_handler.handler"]
  }

  publish     = true
  memory_size = 512
  timeout     = 60

  environment {
    variables = {
      TZ               = "Asia/Bangkok"
      DATA_LAKE_BUCKET = module.s3_data_lake.bucket_id

      # Langfuse
      LANGFUSE_PUBLIC_KEY          = var.LANGFUSE_PUBLIC_KEY
      LANGFUSE_SECRET_KEY          = var.LANGFUSE_SECRET_KEY
      LANGFUSE_HOST                = var.LANGFUSE_HOST
      LANGFUSE_TRACING_ENVIRONMENT = var.LANGFUSE_TRACING_ENVIRONMENT

      # Aurora
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_PORT     = "3306"
      AURORA_DATABASE = var.aurora_database_name
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD

      # DynamoDB (for job completion)
      JOBS_TABLE_NAME = aws_dynamodb_table.report_jobs.name

      # S3 PDF
      PDF_BUCKET_NAME = aws_s3_bucket.pdf_reports.id
    }
  }

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-postprocess-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-postprocess"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.pipeline_postprocess_basic
  ]
}

###############################################################################
# Lambda Aliases
###############################################################################

resource "aws_lambda_alias" "pipeline_preprocess_live" {
  count            = var.use_report_pipeline ? 1 : 0
  name             = "live"
  description      = "Production alias for pipeline preprocess"
  function_name    = aws_lambda_function.pipeline_preprocess[0].function_name
  function_version = aws_lambda_function.pipeline_preprocess[0].version

  lifecycle { ignore_changes = [function_version] }
}

resource "aws_lambda_alias" "pipeline_generation_live" {
  count            = var.use_report_pipeline ? 1 : 0
  name             = "live"
  description      = "Production alias for pipeline generation"
  function_name    = aws_lambda_function.pipeline_generation[0].function_name
  function_version = aws_lambda_function.pipeline_generation[0].version

  lifecycle { ignore_changes = [function_version] }
}

resource "aws_lambda_alias" "pipeline_postprocess_live" {
  count            = var.use_report_pipeline ? 1 : 0
  name             = "live"
  description      = "Production alias for pipeline postprocess"
  function_name    = aws_lambda_function.pipeline_postprocess[0].function_name
  function_version = aws_lambda_function.pipeline_postprocess[0].version

  lifecycle { ignore_changes = [function_version] }
}

###############################################################################
# Step Functions Express State Machine
###############################################################################

# Construct Lambda ARNs from known values to avoid circular dependency
locals {
  pipeline_preprocess_function_name  = "${var.project_name}-pipeline-preprocess-${var.environment}"
  pipeline_generation_function_name  = "${var.project_name}-pipeline-generation-${var.environment}"
  pipeline_postprocess_function_name = "${var.project_name}-pipeline-postprocess-${var.environment}"

  report_pipeline_definition = var.use_report_pipeline ? templatefile("${path.module}/step_functions/report_pipeline.json", {
    region                           = var.aws_region
    account_id                       = data.aws_caller_identity.current.account_id
    preprocess_function_arn           = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_preprocess_function_name}"
    generation_function_arn           = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_generation_function_name}"
    postprocess_function_arn          = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_postprocess_function_name}"
    quant_agent_function_arn          = aws_lambda_function.quant_agent_report.arn
  }) : "{}"
}

resource "aws_sfn_state_machine" "report_pipeline" {
  count    = var.use_report_pipeline ? 1 : 0
  name     = "${var.project_name}-report-pipeline-${var.environment}"
  role_arn = aws_iam_role.report_pipeline_role[0].arn
  type     = "EXPRESS"

  definition = local.report_pipeline_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.report_pipeline_logs[0].arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-report-pipeline-${var.environment}"
    App       = "telegram-api"
    Component = "report-pipeline-orchestration"
  })
}

# CloudWatch Log Group for pipeline state machine
resource "aws_cloudwatch_log_group" "report_pipeline_logs" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "/aws/vendedlogs/states/${var.project_name}-report-pipeline-${var.environment}"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-report-pipeline-logs-${var.environment}"
    App       = "telegram-api"
    Component = "report-pipeline-logging"
  })
}

###############################################################################
# Step Functions IAM Role
###############################################################################

resource "aws_iam_role" "report_pipeline_role" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-report-pipeline-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-report-pipeline-role-${var.environment}"
    App       = "telegram-api"
    Component = "report-pipeline-role"
  })
}

resource "aws_iam_role_policy" "report_pipeline_policy" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-report-pipeline-policy-${var.environment}"
  role  = aws_iam_role.report_pipeline_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_preprocess_function_name}",
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_generation_function_name}",
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.pipeline_postprocess_function_name}",
          aws_lambda_function.quant_agent_report.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

###############################################################################
# Lambda Permissions for Step Functions
###############################################################################

resource "aws_lambda_permission" "pipeline_preprocess_sfn" {
  count         = var.use_report_pipeline ? 1 : 0
  statement_id  = "AllowReportPipelineInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pipeline_preprocess[0].function_name
  principal     = "states.amazonaws.com"
  source_arn    = aws_sfn_state_machine.report_pipeline[0].arn
}

resource "aws_lambda_permission" "pipeline_generation_sfn" {
  count         = var.use_report_pipeline ? 1 : 0
  statement_id  = "AllowReportPipelineInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pipeline_generation[0].function_name
  principal     = "states.amazonaws.com"
  source_arn    = aws_sfn_state_machine.report_pipeline[0].arn
}

resource "aws_lambda_permission" "pipeline_postprocess_sfn" {
  count         = var.use_report_pipeline ? 1 : 0
  statement_id  = "AllowReportPipelineInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pipeline_postprocess[0].function_name
  principal     = "states.amazonaws.com"
  source_arn    = aws_sfn_state_machine.report_pipeline[0].arn
}

###############################################################################
# CloudWatch Log Groups for Lambda functions
###############################################################################

resource "aws_cloudwatch_log_group" "pipeline_preprocess_logs" {
  count             = var.use_report_pipeline ? 1 : 0
  name              = "/aws/lambda/${local.pipeline_preprocess_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-preprocess-logs-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-preprocess-logging"
  })
}

resource "aws_cloudwatch_log_group" "pipeline_generation_logs" {
  count             = var.use_report_pipeline ? 1 : 0
  name              = "/aws/lambda/${local.pipeline_generation_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-generation-logs-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-generation-logging"
  })
}

resource "aws_cloudwatch_log_group" "pipeline_postprocess_logs" {
  count             = var.use_report_pipeline ? 1 : 0
  name              = "/aws/lambda/${local.pipeline_postprocess_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-pipeline-postprocess-logs-${var.environment}"
    App       = "telegram-api"
    Component = "pipeline-postprocess-logging"
  })
}

###############################################################################
# IAM: Allow callers to invoke pipeline
###############################################################################

# Allow telegram_api Lambda to start pipeline sync execution
resource "aws_iam_role_policy" "telegram_api_invoke_pipeline" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-telegram-api-invoke-pipeline-${var.environment}"
  role  = aws_iam_role.telegram_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartSyncExecution"]
      Resource = aws_sfn_state_machine.report_pipeline[0].arn
    }]
  })
}

# Allow precompute workflow to start pipeline execution
resource "aws_iam_role_policy" "precompute_invoke_pipeline" {
  count = var.use_report_pipeline ? 1 : 0
  name  = "${var.project_name}-precompute-invoke-pipeline-${var.environment}"
  role  = aws_iam_role.precompute_workflow_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartExecution", "states:StartSyncExecution", "states:DescribeExecution", "states:StopExecution"]
      Resource = aws_sfn_state_machine.report_pipeline[0].arn
    }]
  })
}

###############################################################################
# Outputs
###############################################################################

output "report_pipeline_arn" {
  value       = var.use_report_pipeline ? aws_sfn_state_machine.report_pipeline[0].arn : null
  description = "ARN of the report pipeline Step Functions state machine"
}

output "report_pipeline_console_url" {
  value       = var.use_report_pipeline ? "https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.report_pipeline[0].arn}" : null
  description = "AWS Console URL for report pipeline"
}
