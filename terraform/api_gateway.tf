# API Gateway HTTP API for Telegram Mini App
# Routes REST API requests to Telegram Lambda function

###############################################################################
# HTTP API Gateway
###############################################################################

resource "aws_apigatewayv2_api" "telegram_api" {
  name          = "${var.project_name}-telegram-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "REST API for Telegram Mini App - ticker analysis and reports"

  cors_configuration {
    allow_origins = ["*"] # Telegram WebApp origin - should be restricted in production
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = [
      "Content-Type",
      "X-Telegram-User-Id",
      "X-Telegram-Init-Data",
      "Authorization"
    ]
    expose_headers = ["X-Request-Id"]
    max_age        = 300
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-${var.environment}"
    App       = "telegram-api"
    Component = "api-gateway"
  })
}

###############################################################################
# Lambda Integration
###############################################################################

resource "aws_apigatewayv2_integration" "telegram_lambda" {
  api_id             = aws_apigatewayv2_api.telegram_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.telegram_api.invoke_arn

  payload_format_version = "2.0"
  timeout_milliseconds   = 30000 # 30 seconds (Lambda timeout is 60s)

  description = "Lambda integration for Telegram Mini App API"
}

###############################################################################
# Routes
###############################################################################

# Catch-all route - forwards all paths to Lambda (FastAPI handles routing)
resource "aws_apigatewayv2_route" "telegram_default" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

# Optional: Specific routes for better monitoring/logging
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/health"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "search" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/search"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "report" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/report/{ticker}"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "rankings" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/rankings"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_get" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "GET /api/v1/watchlist"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_post" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "POST /api/v1/watchlist"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

resource "aws_apigatewayv2_route" "watchlist_delete" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "DELETE /api/v1/watchlist/{ticker}"
  target    = "integrations/${aws_apigatewayv2_integration.telegram_lambda.id}"
}

###############################################################################
# Stage (Deployment)
###############################################################################

resource "aws_apigatewayv2_stage" "telegram_default" {
  api_id      = aws_apigatewayv2_api.telegram_api.id
  name        = "$default"
  auto_deploy = true

  # Temporarily disabled - requires additional IAM service-linked role permissions
  # access_log_settings {
  #   destination_arn = aws_cloudwatch_log_group.telegram_api_gateway_logs.arn
  #   format = jsonencode({
  #     requestId      = "$context.requestId"
  #     ip             = "$context.identity.sourceIp"
  #     caller         = "$context.identity.caller"
  #     user           = "$context.identity.user"
  #     requestTime    = "$context.requestTime"
  #     httpMethod     = "$context.httpMethod"
  #     resourcePath   = "$context.resourcePath"
  #     status         = "$context.status"
  #     protocol       = "$context.protocol"
  #     responseLength = "$context.responseLength"
  #     errorMessage   = "$context.error.message"
  #     integrationErrorMessage = "$context.integrationErrorMessage"
  #   })
  # }

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 100
    throttling_rate_limit    = 50
  }

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-stage-${var.environment}"
    App       = "telegram-api"
    Component = "api-gateway-stage"
  })
}

# CloudWatch Log Group for API Gateway Access Logs
resource "aws_cloudwatch_log_group" "telegram_api_gateway_logs" {
  name              = "/aws/apigateway/${var.project_name}-telegram-api-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-telegram-api-gateway-logs-${var.environment}"
    App       = "telegram-api"
    Component = "logging"
  })
}

###############################################################################
# Lambda Permission for API Gateway
###############################################################################

resource "aws_lambda_permission" "telegram_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telegram_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.telegram_api.execution_arn}/*/*"
}

###############################################################################
# Outputs
###############################################################################

output "telegram_api_gateway_url" {
  value       = aws_apigatewayv2_api.telegram_api.api_endpoint
  description = "Base URL for Telegram API Gateway"
}

output "telegram_api_gateway_id" {
  value       = aws_apigatewayv2_api.telegram_api.id
  description = "ID of the Telegram API Gateway"
}

output "telegram_api_invoke_url" {
  value       = "${aws_apigatewayv2_api.telegram_api.api_endpoint}/api/v1"
  description = "Full invoke URL for Telegram API (with /api/v1 prefix)"
}
