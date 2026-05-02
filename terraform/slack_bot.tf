###############################################################################
# Slack Bot Lambda — TICKER message → cached Aurora report reply
###############################################################################
# Mirrors aws_lambda_function.line_bot (terraform/main.tf:234-297).
# Reuses:
#   - same ECR image (one container, multiple Lambdas with command override)
#   - same lambda_aurora SG and NAT-routable private subnets (Aurora + Slack API egress)
#   - same IAM execution role (read-only Aurora client; no SQS / state machine writes)
#
# Doppler dev secrets required (TF_VAR_-prefixed):
#   - TF_VAR_SLACK_BOT_TOKEN          (xoxb-…)
#   - TF_VAR_SLACK_SIGNING_SECRET     (32 hex chars)
###############################################################################

resource "aws_lambda_function" "slack_bot" {
  function_name = "${var.project_name}-slack-bot-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  image_config {
    command = ["slack_handler.lambda_handler"]
  }

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  vpc_config {
    subnet_ids         = local.private_subnets_with_nat
    security_group_ids = [aws_security_group.lambda_aurora.id]
  }

  environment {
    variables = {
      # Slack credentials
      SLACK_BOT_TOKEN      = var.SLACK_BOT_TOKEN
      SLACK_SIGNING_SECRET = var.SLACK_SIGNING_SECRET

      # OpenRouter — imported by shared modules at module load (TickerAnalysisAgent)
      OPENROUTER_API_KEY = var.OPENROUTER_API_KEY

      # Aurora database (cache lookups)
      AURORA_HOST     = local.aurora_connection_endpoint
      AURORA_DATABASE = "ticker_data"
      AURORA_USER     = var.aurora_master_username
      AURORA_PASSWORD = var.AURORA_MASTER_PASSWORD
      AURORA_PORT     = "3306"

      # PDF storage (presigned URL is read from Aurora cache row)
      PDF_STORAGE_BUCKET       = aws_s3_bucket.pdf_reports.id
      PDF_BUCKET_NAME          = aws_s3_bucket.pdf_reports.id
      PDF_URL_EXPIRATION_HOURS = "24"

      ENVIRONMENT = var.environment
    }
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-slack-bot-${var.environment}"
    App       = "slack-bot"
    Component = "webhook-handler"
    Interface = "function-url"
  })

  depends_on = [
    aws_ecr_repository.lambda,
    aws_iam_role_policy_attachment.lambda_basic
  ]
}

###############################################################################
# Lambda Function URL for Slack Events API webhook
###############################################################################
# Auth NONE — request validation is done in-handler via SLACK_SIGNING_SECRET
# (HMAC v0= over `v0:{ts}:{raw_body}`, 5-min replay window).
###############################################################################

resource "aws_lambda_function_url" "slack_webhook" {
  function_name      = aws_lambda_function.slack_bot.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["*"]
  }

  depends_on = [aws_lambda_function.slack_bot]
}

output "slack_webhook_function_url" {
  description = "Function URL to paste into Slack app's Event Subscriptions > Request URL"
  value       = aws_lambda_function_url.slack_webhook.function_url
}
