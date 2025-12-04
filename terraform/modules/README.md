# Terraform Modules

Reusable Terraform modules for common infrastructure patterns in this project.

## Available Modules

| Module | Description | Key Features |
|--------|-------------|--------------|
| `lambda/` | Container image Lambda function | VPC support, IAM role, alias, logging |
| `dynamodb/` | DynamoDB table | Optional range key, TTL, GSIs |
| `sqs/` | SQS queue with DLQ | Dead letter queue, Lambda trigger |

## Module Usage Examples

### Lambda Module

```hcl
# Example: Telegram API Lambda
module "telegram_api" {
  source = "./modules/lambda"

  function_name   = "telegram-api"
  handler_command = "telegram_lambda_handler.handler"
  image_uri       = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment_variables = {
    OPENROUTER_API_KEY   = var.OPENROUTER_API_KEY
    PDF_STORAGE_BUCKET   = aws_s3_bucket.pdf_reports.id
    JOBS_TABLE_NAME      = module.jobs_table.table_name
    REPORT_JOBS_QUEUE_URL = module.report_queue.queue_url
  }

  # VPC configuration for Aurora access
  vpc_enabled        = var.aurora_enabled
  subnet_ids         = local.private_subnets_with_nat
  security_group_ids = var.aurora_enabled ? [aws_security_group.lambda_aurora[0].id] : []

  # Custom IAM permissions
  additional_policy_statements = [
    {
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject"]
      Resource = "${aws_s3_bucket.pdf_reports.arn}/*"
    },
    {
      Effect = "Allow"
      Action = ["sqs:SendMessage"]
      Resource = module.report_queue.queue_arn
    }
  ]

  # Managed policies to attach
  managed_policy_arns = var.aurora_enabled ? [
    aws_iam_policy.lambda_aurora_access[0].arn
  ] : []

  app_tag       = "telegram-api"
  component_tag = "rest-api"
}

# Example: Scheduler Lambda (using existing IAM role)
module "scheduler" {
  source = "./modules/lambda"

  function_name   = "ticker-scheduler"
  handler_command = "src.scheduler.handler.lambda_handler"
  image_uri       = "${aws_ecr_repository.lambda.repository_url}:${var.lambda_image_tag}"

  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  memory_size = 512
  timeout     = 300

  # Reuse existing IAM role (don't create new one)
  create_iam_role = false
  role_arn        = aws_iam_role.telegram_lambda_role.arn

  environment_variables = {
    PDF_BUCKET_NAME    = aws_s3_bucket.pdf_reports.id
    ENVIRONMENT        = var.environment
    OPENROUTER_API_KEY = var.OPENROUTER_API_KEY
    AURORA_HOST        = var.aurora_enabled ? aws_rds_cluster.aurora[0].endpoint : ""
  }

  vpc_enabled        = var.aurora_enabled
  subnet_ids         = local.private_subnets_with_nat
  security_group_ids = var.aurora_enabled ? [aws_security_group.lambda_aurora[0].id] : []

  # No alias for scheduler (invoked by EventBridge directly)
  create_alias = false

  app_tag       = "telegram-api"
  component_tag = "scheduler"
}
```

### DynamoDB Module

```hcl
# Example: Jobs table (hash key only)
module "jobs_table" {
  source = "./modules/dynamodb"

  table_name   = "telegram-jobs"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  hash_key      = "job_id"
  hash_key_type = "S"

  ttl_enabled        = true
  ttl_attribute_name = "ttl"

  app_tag       = "telegram-api"
  component_tag = "job-storage"
  data_type_tag = "async-jobs"
}

# Example: Watchlist table (hash + range key)
module "watchlist_table" {
  source = "./modules/dynamodb"

  table_name   = "telegram-watchlist"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  hash_key       = "user_id"
  hash_key_type  = "S"
  range_key      = "ticker"
  range_key_type = "S"

  ttl_enabled        = true
  ttl_attribute_name = "ttl"

  app_tag       = "telegram-api"
  component_tag = "watchlist-storage"
  data_type_tag = "user-preferences"
}

# Example: Table with GSI
module "orders_table" {
  source = "./modules/dynamodb"

  table_name   = "orders"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  hash_key  = "order_id"
  range_key = "created_at"

  global_secondary_indexes = [
    {
      name            = "user-orders-index"
      hash_key        = "user_id"
      range_key       = "created_at"
      projection_type = "ALL"
    }
  ]
}
```

### SQS Module

```hcl
# Example: Report jobs queue with DLQ and Lambda trigger
module "report_queue" {
  source = "./modules/sqs"

  queue_name   = "report-jobs"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  visibility_timeout_seconds = 120  # 2x Lambda timeout
  message_retention_seconds  = 3600 # 1 hour
  receive_wait_time_seconds  = 10   # Long polling

  # DLQ configuration
  create_dlq                    = true
  dlq_message_retention_seconds = 1209600 # 14 days
  max_receive_count             = 1       # No retries, straight to DLQ

  # Lambda trigger (optional)
  create_lambda_trigger = true
  lambda_function_arn   = module.report_worker.alias_arn
  lambda_batch_size     = 1

  app_tag       = "telegram-api"
  component_tag = "job-queue"
}

# Example: Simple queue without DLQ or Lambda
module "notification_queue" {
  source = "./modules/sqs"

  queue_name   = "notifications"
  project_name = var.project_name
  environment  = var.environment
  common_tags  = local.common_tags

  create_dlq            = false
  create_lambda_trigger = false
}
```

## Module Outputs Reference

### Lambda Module Outputs

| Output | Description |
|--------|-------------|
| `function_name` | Lambda function name |
| `function_arn` | Lambda function ARN |
| `invoke_arn` | ARN for API Gateway integration |
| `version` | Published version number |
| `alias_name` | "live" alias name (if created) |
| `alias_arn` | "live" alias ARN (if created) |
| `role_arn` | IAM role ARN (if created) |
| `role_name` | IAM role name (if created) |
| `log_group_name` | CloudWatch log group name |

### DynamoDB Module Outputs

| Output | Description |
|--------|-------------|
| `table_name` | DynamoDB table name |
| `table_arn` | DynamoDB table ARN |
| `hash_key` | Hash key attribute name |
| `range_key` | Range key attribute name (if defined) |
| `stream_arn` | Stream ARN (if streams enabled) |

### SQS Module Outputs

| Output | Description |
|--------|-------------|
| `queue_url` | SQS queue URL |
| `queue_arn` | SQS queue ARN |
| `queue_name` | SQS queue name |
| `dlq_url` | Dead letter queue URL (if created) |
| `dlq_arn` | Dead letter queue ARN (if created) |
| `event_source_mapping_uuid` | Lambda trigger UUID (if created) |

## Migration Guide

To migrate existing resources to use these modules:

1. **Add module block** alongside existing resource
2. **Import state**: `terraform import module.name.aws_lambda_function.this <function-name>`
3. **Remove old resource** from .tf file
4. **Run terraform plan** to verify no changes

Example state import commands:

```bash
# Import Lambda function
terraform import 'module.telegram_api.aws_lambda_function.this' dr-daily-report-telegram-api-dev

# Import DynamoDB table
terraform import 'module.jobs_table.aws_dynamodb_table.this' dr-daily-report-telegram-jobs-dev

# Import SQS queue
terraform import 'module.report_queue.aws_sqs_queue.this' https://sqs.ap-southeast-1.amazonaws.com/123456789/dr-daily-report-report-jobs-dev
```

## Best Practices

1. **Naming**: Modules automatically construct names as `{project}-{name}-{env}`
2. **Tags**: Pass `common_tags` from root module for consistent tagging
3. **VPC**: Only enable VPC if Lambda needs to access VPC resources (adds cold start latency)
4. **Aliases**: Use aliases for Lambdas invoked by API Gateway/SQS for safe deployments
5. **IAM**: Prefer `managed_policy_arns` for shared policies, `additional_policy_statements` for unique permissions
