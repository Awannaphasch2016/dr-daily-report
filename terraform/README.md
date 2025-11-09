# LINE Bot Infrastructure - Terraform

This directory contains Terraform configuration for deploying the LINE Bot Lambda function with container images to AWS.

## Prerequisites

- Terraform >= 1.0 (installed)
- AWS CLI configured with credentials
- Docker installed and running (for building container images)
- AWS permissions: Lambda, ECR, API Gateway, IAM, CloudWatch Logs

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads required providers and prepares Terraform.

### 2. Review Configuration

```bash
terraform plan
```

This shows what resources will be created without making any changes.

### 3. Deploy Infrastructure

```bash
terraform apply
```

Review the changes and type `yes` to confirm. This will:
1. Create ECR repository for Docker images
2. Build and push Docker image to ECR
3. Create/update Lambda function with container image
4. Create API Gateway HTTP API
5. Configure webhook endpoint

### 4. Get Outputs

```bash
terraform output webhook_url
```

Or see all outputs:
```bash
terraform output
```

## Architecture

### Resources Created

- **ECR Repository**: Stores Docker container images
- **Lambda Function**: Runs as container image from ECR
- **API Gateway (HTTP API)**: Webhook endpoint for LINE
- **IAM Role**: Lambda execution role with necessary permissions
- **CloudWatch Log Groups**: For Lambda and API Gateway logs

### Configuration Files

- `main.tf` - Main infrastructure definition
- `variables.tf` - Variable declarations
- `outputs.tf` - Output definitions
- `terraform.tfvars` - Variable values (git-ignored, contains secrets)
- `terraform.tfvars.example` - Template for variable values

## Configuration

### Environment Variables

Secrets are configured in `terraform.tfvars`:

```hcl
openai_api_key            = "sk-proj-..."
line_channel_access_token = "..."
line_channel_secret       = "..."
```

**Security Note**: `terraform.tfvars` is git-ignored to prevent secret exposure.

### Customization

Edit `terraform.tfvars` to change:
- AWS region
- Lambda memory/timeout
- Log retention period
- Function name

## Deployment Workflow

### Making Code Changes

1. Modify your application code in `src/`
2. Run `terraform apply`
3. Terraform automatically:
   - Detects changes
   - Rebuilds Docker image
   - Pushes to ECR
   - Updates Lambda function

### Manual Image Build (Optional)

If you want to build/push manually without Terraform:

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin \
  755283537543.dkr.ecr.ap-southeast-1.amazonaws.com

# Build image
docker build -f Dockerfile.lambda.container -t line-bot-ticker-report:latest .

# Tag for ECR
docker tag line-bot-ticker-report:latest \
  755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/line-bot-ticker-report:latest

# Push to ECR
docker push 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/line-bot-ticker-report:latest

# Update Lambda (if needed)
terraform apply -target=aws_lambda_function.line_bot
```

## Managing Environments

### Development Environment

Create `terraform.tfvars.dev`:

```hcl
aws_region      = "ap-southeast-1"
environment     = "dev"
function_name   = "line-bot-ticker-report-dev"
lambda_memory   = 256  # Lower for cost savings
# ... other variables
```

Deploy:
```bash
terraform apply -var-file="terraform.tfvars.dev"
```

### Production vs Development

Use Terraform workspaces:

```bash
# Create dev workspace
terraform workspace new dev

# Switch to dev
terraform workspace select dev
terraform apply

# Switch back to production
terraform workspace select default
terraform apply
```

## Updating LINE Console

After deployment, update the webhook URL in LINE Developers Console:

1. Get webhook URL: `terraform output webhook_url`
2. Go to LINE Developers Console
3. Update Webhook URL
4. Verify webhook

## Monitoring

### View Lambda Logs

```bash
# Get log group name
terraform output cloudwatch_log_group

# Tail logs
aws logs tail /aws/lambda/line-bot-ticker-report --follow --region ap-southeast-1
```

### Check Lambda Function

```bash
aws lambda get-function \
  --function-name line-bot-ticker-report \
  --region ap-southeast-1
```

## Troubleshooting

### Docker Build Fails

```bash
# Test build manually
docker build -f Dockerfile.lambda.container -t test .

# Check Docker is running
docker ps
```

### Terraform Apply Fails

```bash
# See detailed error
terraform apply -debug

# Check state
terraform show

# Refresh state
terraform refresh
```

### Lambda Not Updating

Terraform tracks the image by tag (`latest`). If you want to force update:

```bash
# Force rebuild
terraform taint null_resource.docker_build_push
terraform apply
```

### Permission Errors

Verify AWS credentials:
```bash
aws sts get-caller-identity
```

Ensure you have permissions for:
- Lambda
- ECR
- API Gateway
- IAM
- CloudWatch Logs

## State Management

### Local State (Current)

Terraform state is stored locally in `terraform.tfstate`.

**Warning**: This file contains sensitive data. Never commit it.

### Remote State (Recommended for Teams)

Use S3 backend for team collaboration:

Create `backend.tf`:
```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state-bucket"
    key    = "linebot/terraform.tfstate"
    region = "ap-southeast-1"
  }
}
```

Initialize:
```bash
terraform init -migrate-state
```

## Cleanup

### Destroy All Resources

```bash
terraform destroy
```

**Warning**: This deletes:
- Lambda function
- ECR repository (and all images)
- API Gateway
- CloudWatch logs
- IAM roles

### Destroy Specific Resource

```bash
terraform destroy -target=aws_lambda_function.line_bot
```

## Cost Estimation

### Monthly Costs (Approximate)

- **Lambda**: Pay per request (~$0.20 per 1M requests) + compute time
- **ECR**: $0.10/GB/month for storage
- **API Gateway**: $1.00 per million requests
- **CloudWatch Logs**: $0.50/GB ingested

**Estimated Total**: $5-20/month depending on usage

### Cost Optimization

- Reduce Lambda memory if possible
- Shorter log retention (3 days vs 7 days)
- Use reserved concurrency for predictable workloads

## Migration from Manual Deployment

This Terraform configuration replaces the manual `scripts/deploy.sh` workflow:

| Manual | Terraform |
|--------|-----------|
| Build Docker manually | `terraform apply` builds automatically |
| Push to ECR manually | Automatic push to ECR |
| Update Lambda via CLI | Automatic Lambda update |
| No version control | Infrastructure as code |
| Error-prone | Reproducible |

## Next Steps

1. ✅ Initialize Terraform
2. ✅ Review plan
3. ⏳ Apply configuration
4. ⏳ Test webhook
5. ⏳ Update LINE console
6. ⏳ Monitor logs

## Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

---

**Last Updated**: 2025-11-09
**Terraform Version**: 1.10.3
**AWS Provider Version**: ~> 5.0
