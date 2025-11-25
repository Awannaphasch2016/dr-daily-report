# AWS Resource Tagging Policy

## Overview

This document defines the tagging policy for all AWS resources in the DR Daily Report project. Tags are used for cost allocation, resource management, automation, and compliance.

## Required Tags (All Resources)

These tags MUST be present on all AWS resources:

| Tag Key      | Description                              | Possible Values                  | Example            |
|--------------|------------------------------------------|----------------------------------|--------------------|
| `Project`    | Project name for identification          | `dr-daily-report`                | dr-daily-report    |
| `ManagedBy`  | Tool used to provision the resource      | `Terraform`, `Manual`            | Terraform          |
| `Environment`| Deployment environment                   | `dev`, `staging`, `prod`         | prod               |
| `Owner`      | Team or person responsible               | Team/individual name             | data-team          |
| `CostCenter` | Department for cost allocation           | Department name                  | engineering        |

## Application-Specific Tags

These tags identify which application owns the resource:

| Tag Key     | Description                              | Possible Values                               | Example          |
|-------------|------------------------------------------|-----------------------------------------------|------------------|
| `App`       | Application that owns this resource      | `line-bot`, `telegram-api`, `shared`          | telegram-api     |
| `Component` | Purpose/function of the resource         | See component list below                      | webhook-handler  |

### Valid Component Values

| Component Value      | Description                                    | Used By              |
|---------------------|------------------------------------------------|----------------------|
| `webhook-handler`   | Lambda function handling webhooks              | line-bot             |
| `rest-api`          | Lambda function serving REST API               | telegram-api         |
| `pdf-storage`       | S3 bucket for PDF report storage               | shared               |
| `watchlist-storage` | DynamoDB table for user watchlists             | telegram-api         |
| `cache-storage`     | DynamoDB table for API response cache          | telegram-api         |
| `iam-role`          | IAM role for service permissions               | line-bot, telegram   |
| `iam-policy`        | IAM policy defining permissions                | telegram-api         |
| `deployment`        | S3 bucket for deployment artifacts             | line-bot             |

## Optional Tags

These tags provide additional context when applicable:

| Tag Key        | Description                              | Example                    |
|----------------|------------------------------------------|----------------------------|
| `Name`         | Human-readable name                      | telegram-api-main-prod     |
| `Interface`    | How the service is accessed              | function-url, api-gateway  |
| `DataType`     | Type of data stored                      | user-preferences, temporary|
| `SharedBy`     | Apps that share this resource            | line-bot,telegram-api      |

## Tag Implementation in Terraform

### 1. Common Tags Block

All tags are defined in a `locals` block in `main.tf`:

```hcl
locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Environment = var.environment
    Owner       = var.owner
    CostCenter  = var.cost_center
  }
}
```

### 2. Resource-Specific Tags

Resources use `merge()` to combine common tags with specific tags:

```hcl
resource "aws_lambda_function" "telegram_api" {
  # ... other configuration ...

  tags = merge(local.common_tags, {
    Name      = "telegram-api-main-${var.environment}"
    App       = "telegram-api"
    Component = "rest-api"
    Interface = "api-gateway"
  })
}
```

### 3. Shared Resources Example

```hcl
resource "aws_s3_bucket" "pdf_reports" {
  # ... other configuration ...

  tags = merge(local.common_tags, {
    Name      = "pdf-storage"
    App       = "shared"
    Component = "pdf-storage"
    SharedBy  = "line-bot,telegram-api"
  })
}
```

## Current Resource Tagging

### LINE Bot Resources

| Resource                      | App      | Component        | Interface    |
|-------------------------------|----------|------------------|--------------|
| Lambda Function (line_bot)   | line-bot | webhook-handler  | function-url |
| IAM Role (lambda_role)        | line-bot | iam-role         | -            |
| S3 Bucket (pdf_reports)       | shared   | pdf-storage      | -            |

### Telegram Mini App Resources

| Resource                        | App          | Component          | DataType         |
|---------------------------------|--------------|--------------------|------------------|
| DynamoDB (telegram_watchlist)   | telegram-api | watchlist-storage  | user-preferences |
| DynamoDB (telegram_cache)       | telegram-api | cache-storage      | temporary        |
| IAM Policy (dynamodb_access)    | telegram-api | iam-policy         | -                |

## Cost Allocation

### AWS Cost Explorer Filtering

Use these tag combinations to analyze costs:

**By Application:**
```
Tag: App = line-bot
Tag: App = telegram-api
Tag: App = shared
```

**By Environment:**
```
Tag: Environment = dev
Tag: Environment = prod
```

**By Component:**
```
Tag: Component = webhook-handler
Tag: Component = rest-api
Tag: Component = pdf-storage
```

### Example Cost Queries

1. **Total LINE Bot costs:**
   - Filter: `App = line-bot`

2. **Telegram Mini App development costs:**
   - Filter: `App = telegram-api AND Environment = dev`

3. **Shared infrastructure costs:**
   - Filter: `App = shared`

4. **Storage costs across all apps:**
   - Filter: `Component = *-storage`

## Tag Compliance

### Validation Rules

1. **Environment Tag:** Must be one of: `dev`, `staging`, `prod`
   ```hcl
   validation {
     condition     = contains(["dev", "staging", "prod"], var.environment)
     error_message = "Environment must be dev, staging, or prod"
   }
   ```

2. **Required Tags:** All resources must have Project, ManagedBy, Environment, Owner, CostCenter
3. **App Tag:** Must be `line-bot`, `telegram-api`, or `shared`
4. **Naming Convention:** Use lowercase with hyphens (e.g., `telegram-api`, not `Telegram_API`)

### Checking Tag Compliance

**List all resources by tag:**
```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=dr-daily-report
```

**Find untagged resources:**
```bash
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters lambda dynamodb s3 \
  | jq '.ResourceTagMappingList[] | select(.Tags | length == 0)'
```

**Find resources by App tag:**
```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=App,Values=telegram-api
```

## Automation

### Resource Groups

Create AWS Resource Groups for easier management:

**LINE Bot Resources:**
```bash
aws resource-groups create-group \
  --name line-bot-resources \
  --resource-query '{"Type":"TAG_FILTERS_1_0","Query":"{\"ResourceTypeFilters\":[\"AWS::AllSupported\"],\"TagFilters\":[{\"Key\":\"App\",\"Values\":[\"line-bot\"]}]}"}'
```

**Telegram API Resources:**
```bash
aws resource-groups create-group \
  --name telegram-api-resources \
  --resource-query '{"Type":"TAG_FILTERS_1_0","Query":"{\"ResourceTypeFilters\":[\"AWS::AllSupported\"],\"TagFilters\":[{\"Key\":\"App\",\"Values\":[\"telegram-api\"]}]}"}'
```

### Backup Automation

Use tags to automate backups:

```python
import boto3

# Find all telegram-api DynamoDB tables
client = boto3.client('resourcegroupstaggingapi')
resources = client.get_resources(
    TagFilters=[
        {'Key': 'App', 'Values': ['telegram-api']},
        {'Key': 'Component', 'Values': ['*-storage']}
    ]
)

# Create backups
for resource in resources['ResourceTagMappingList']:
    if 'dynamodb' in resource['ResourceARN']:
        # Trigger backup...
```

## Best Practices

### DO:
- ✅ Use consistent naming conventions (lowercase, hyphens)
- ✅ Tag resources as soon as they're created
- ✅ Document tag meanings and valid values
- ✅ Use tags for cost tracking and automation
- ✅ Review and update tags regularly

### DON'T:
- ❌ Use PII (personal information) in tags
- ❌ Store secrets or credentials in tags
- ❌ Use inconsistent capitalization (Environment vs environment)
- ❌ Create tags without documenting their purpose
- ❌ Skip required tags on any resource

## Tag Lifecycle

### When Creating Resources:
1. Use `locals.common_tags` as base
2. Add `merge()` with resource-specific tags
3. Verify tags appear in `terraform plan`

### When Modifying Resources:
1. Update tag values in variables or merge block
2. Run `terraform plan` to preview changes
3. Apply changes (tags are non-destructive)

### When Deleting Resources:
- Tags are automatically removed with the resource
- No manual tag cleanup needed

## Examples

### Complete Lambda Function with Tags

```hcl
resource "aws_lambda_function" "telegram_api" {
  function_name = "telegram-api-main-${var.environment}"
  role          = aws_iam_role.telegram_lambda_role.arn
  handler       = "app.handler"
  runtime       = "python3.11"

  tags = merge(local.common_tags, {
    Name      = "telegram-api-main-${var.environment}"
    App       = "telegram-api"
    Component = "rest-api"
    Interface = "api-gateway"
  })
}
```

### Complete DynamoDB Table with Tags

```hcl
resource "aws_dynamodb_table" "watchlist" {
  name         = "${var.project_name}-watchlist-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-watchlist-${var.environment}"
    App       = "telegram-api"
    Component = "watchlist-storage"
    DataType  = "user-preferences"
  })
}
```

## References

- [AWS Tagging Best Practices](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
- [Terraform merge() function](https://developer.hashicorp.com/terraform/language/functions/merge)
- [AWS Resource Groups](https://docs.aws.amazon.com/ARG/latest/userguide/welcome.html)
- [AWS Cost Allocation Tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)

## Version History

| Version | Date       | Author    | Changes                           |
|---------|------------|-----------|-----------------------------------|
| 1.0     | 2025-11-24 | Claude    | Initial tagging policy created    |
