# Infrastructure Implementation Plan
## LINE Bot Ticker Report - Infrastructure as Code Migration

**Date:** 2025-11-09
**Author:** Claude
**Project:** dr-daily-report (LINE Bot)
**Current Status:** Manual deployment via bash scripts
**Target State:** Automated IaC deployment via **Terraform**

---

## ⚠️ IMPORTANT: Technology Change

**This project uses Terraform instead of AWS CDK.**

**Reason:** Your AWS IAM user lacks CloudFormation permissions required by CDK. Terraform works directly with AWS APIs, bypassing this limitation.

**Current Implementation:**
- ✅ **Terraform** configuration in `terraform/` directory
- ✅ Complete infrastructure definition (Lambda, API Gateway, ECR, IAM)
- ✅ Automated Docker build and push to ECR
- ✅ See `TERRAFORM_MIGRATION_SUMMARY.md` for details

**This document:** Originally planned for CDK, but kept for reference on infrastructure architecture and requirements. The actual implementation uses Terraform.

---

## What You're Implementing

You're automating the deployment of your LINE Bot ticker report service using Infrastructure as Code (IaC). Here's what this achieves:

### The Problem You're Solving
Currently, deploying your LINE Bot requires:
1. Manually building a ZIP file with `scripts/deploy.sh`
2. Uploading it to AWS Lambda console
3. Manually configuring environment variables
4. Manually setting up API Gateway
5. Remembering all these steps each time

### The Solution: Terraform Infrastructure as Code
With Terraform, you get:
- **One Command Deployment**: `terraform apply` does everything automatically
- **Version Control**: All infrastructure changes tracked in git
- **Reproducibility**: Same infrastructure every time, anywhere
- **Automation**: Docker builds, ECR pushes, Lambda updates - all automated
- **Safety**: Preview changes with `terraform plan` before applying

### What Gets Created
When you run `terraform apply`, it automatically:
1. ✅ Creates an ECR repository for Docker images
2. ✅ Builds your Docker container from `Dockerfile.lambda.container`
3. ✅ Pushes the image to ECR
4. ✅ Creates/updates the Lambda function with the container image
5. ✅ Sets up API Gateway HTTP API with `/webhook` endpoint
6. ✅ Configures IAM roles and permissions
7. ✅ Sets up CloudWatch logging
8. ✅ Outputs the webhook URL for LINE console

### Migration Path
- **From**: Manual ZIP deployment (~57.5 MB ZIP file)
- **To**: Automated container deployment (more flexible, up to 10GB)
- **Region**: ap-southeast-1 (Singapore)
- **Function Name**: Same (`line-bot-ticker-report`) - seamless migration

### Current Status
✅ Terraform configuration complete (`terraform/` directory)
✅ Dockerfile for Lambda containers ready
✅ Documentation complete
⏳ Ready for `terraform apply` deployment

---

## ⚠️ ACTUAL INFRASTRUCTURE DISCOVERED (Updated)

After inspecting the live AWS environment, the actual infrastructure differs from initial assumptions:

**Actual Current State:**
- **Function Name:** line-bot-ticker-report
- **Region:** **ap-southeast-1** (NOT us-east-1)
- **AWS Account:** 755283537543
- **Runtime:** Python 3.11
- **Package Type:** **ZIP deployment** (NOT container image)
- **Handler:** src.lambda_handler.lambda_handler
- **Memory:** 512 MB
- **Timeout:** 60 seconds
- **Code Size:** ~57.5 MB (well below 250MB ZIP limit)
- **Secrets:** Stored as **environment variables** in Lambda (NOT Secrets Manager)
- **Deployment:** Manual ZIP upload via scripts/deploy.sh

**Key Implications:**
1. Need to create proper Lambda container Dockerfile (current Dockerfile.lambda is for package extraction)
2. Will deploy to ap-southeast-1 region
3. Can optionally migrate secrets to Secrets Manager for better security
4. This is an upgrade from ZIP to container deployment

---

## Executive Summary

This plan outlines the migration from manual AWS Lambda deployment to Infrastructure as Code (IaC) using **Terraform**. The implementation automates Docker container builds, ECR pushes, and Lambda function updates into a single `terraform apply` command.

**Estimated Time:** 2-3 hours
**Risk Level:** Low (can rollback to manual deployment)
**Primary Benefit:** Reproducible, version-controlled infrastructure

**Note:** This document was originally written for AWS CDK, but the project was migrated to Terraform due to CloudFormation permission constraints. See `terraform/` directory for the actual implementation.

---

## Current State Analysis

### Existing Infrastructure (Manual) - UPDATED
- **Function Name:** line-bot-ticker-report
- **Region:** ap-southeast-1
- **AWS Account:** 755283537543
- **Runtime:** Python 3.11 (ZIP package)
- **Handler:** src.lambda_handler.lambda_handler
- **Deployment Script:** scripts/deploy.sh
- **Current Package:** ZIP file (~57.5 MB)

### Pain Points with Current Approach
1. ❌ No version control for infrastructure state
2. ❌ Manual, error-prone deployment process
3. ❌ No reproducibility across environments
4. ❌ Difficult to track infrastructure changes
5. ❌ No automated rollback capability
6. ❌ Environment variables managed manually
7. ❌ API Gateway configuration not codified

---

## Target Architecture

### Terraform Infrastructure Components

```
Terraform Configuration
├── Lambda Function (Container Image)
│   ├── Automatic Docker build from Dockerfile.lambda.container
│   ├── Automatic ECR push via null_resource
│   ├── Environment variables from terraform.tfvars
│   └── CloudWatch Logs (7-day retention)
├── API Gateway HTTP API
│   ├── POST /webhook endpoint
│   └── Lambda integration
├── IAM Roles & Policies
│   ├── Lambda execution role
│   └── CloudWatch Logs permissions
├── ECR Repository
│   ├── Image scanning enabled
│   └── Lifecycle policy (keep last 5 images)
└── CloudWatch Log Groups
    ├── Lambda logs
    └── API Gateway logs
```

**Implementation:** See `terraform/main.tf` for the actual Terraform code.

### File Structure (Actual Implementation)

```
dr-daily-report/
├── terraform/                   # Terraform configuration
│   ├── main.tf                  # Main infrastructure definition
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values (webhook URL, etc.)
│   ├── terraform.tfvars         # Secrets (git-ignored)
│   ├── terraform.tfvars.example # Template for secrets
│   ├── terraform.tfstate        # State file (git-ignored)
│   └── README.md                # Terraform deployment docs
├── src/                         # Existing application code
├── Dockerfile.lambda.container  # Lambda container Dockerfile
├── requirements_lambda.txt      # Existing (no changes)
└── scripts/
    └── deploy.sh                # Keep for reference/backup
```

**Note:** The original plan included CDK structure (`infrastructure/`), but actual implementation uses Terraform (`terraform/`).

---

## Implementation Phases

### Phase 1: Prerequisites & Setup
**Estimated Time:** 15 minutes
**Dependencies:** Node.js, npm, AWS credentials

#### Step 1.1: Verify Prerequisites
```bash
# Check Node.js (required for CDK CLI)
node --version  # Should be >= 14.x

# Check npm
npm --version

# Check AWS credentials
aws sts get-caller-identity

# Check current region
aws configure get region  # Should be us-east-1
```

#### Step 1.2: Install AWS CDK CLI
```bash
npm install -g aws-cdk

# Verify installation
cdk --version  # Should be >= 2.x
```

#### Step 1.3: Install Python CDK Libraries
```bash
pip install aws-cdk-lib constructs
```

**Success Criteria:**
- ✅ CDK CLI installed and accessible
- ✅ AWS credentials configured
- ✅ Python CDK libraries installed

---

### Phase 2: Initialize CDK Project
**Estimated Time:** 10 minutes
**Dependencies:** Phase 1 complete

#### Step 2.1: Create Infrastructure Directory
```bash
mkdir -p infrastructure
cd infrastructure
```

#### Step 2.2: Initialize CDK App
```bash
cdk init app --language python
```

This creates:
- `app.py` - Entry point
- `cdk.json` - CDK configuration
- `requirements.txt` - Python dependencies
- `infrastructure/` - Python package for stacks

#### Step 2.3: Activate Virtual Environment (if needed)
```bash
# CDK creates a .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

#### Step 2.4: Bootstrap CDK (One-Time)
```bash
cdk bootstrap aws://755283537543/us-east-1
```

This creates:
- CDK staging bucket for CloudFormation templates
- IAM roles for CDK operations
- SSM parameters for versioning

**Success Criteria:**
- ✅ CDK project initialized
- ✅ Bootstrap stack created in AWS
- ✅ `cdk ls` shows default stack (will be replaced)

---

### Phase 3: Create Infrastructure Stack
**Estimated Time:** 45 minutes
**Dependencies:** Phase 2 complete

#### Step 3.1: Create Configuration File

**File:** `infrastructure/infrastructure/config.py`

```python
"""
Configuration for different environments (dev, staging, prod)
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class EnvironmentConfig:
    """Configuration for a deployment environment"""
    env_name: str
    account: str
    region: str
    function_name: str
    memory_size: int
    timeout_seconds: int
    log_retention_days: int
    secrets: Dict[str, str]  # Secret names in AWS Secrets Manager

# Production configuration (current manual deployment)
PROD_CONFIG = EnvironmentConfig(
    env_name="prod",
    account="755283537543",
    region="us-east-1",
    function_name="line-bot-ticker-report",
    memory_size=512,
    timeout_seconds=60,
    log_retention_days=7,
    secrets={
        "openai_api_key": "openai-api-key",
        "line_channel_access_token": "line-channel-access-token",
        "line_channel_secret": "line-channel-secret",
    }
)

# Development configuration (for future multi-env support)
DEV_CONFIG = EnvironmentConfig(
    env_name="dev",
    account="755283537543",
    region="us-east-1",
    function_name="line-bot-ticker-report-dev",
    memory_size=512,
    timeout_seconds=60,
    log_retention_days=3,
    secrets=PROD_CONFIG.secrets,  # Same secrets for now
)

def get_config(env_name: str = "prod") -> EnvironmentConfig:
    """Get configuration for specified environment"""
    configs = {
        "prod": PROD_CONFIG,
        "dev": DEV_CONFIG,
    }
    return configs.get(env_name, PROD_CONFIG)
```

#### Step 3.2: Create Main Stack

**File:** `infrastructure/infrastructure/linebot_stack.py`

```python
"""
LINE Bot Infrastructure Stack
Defines Lambda function, API Gateway, and associated resources
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct
from .config import EnvironmentConfig


class LineBotStack(Stack):
    """
    CDK Stack for LINE Bot Ticker Report

    Resources:
    - Lambda Function (container image)
    - API Gateway HTTP API
    - IAM roles and policies
    - CloudWatch log groups
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: EnvironmentConfig,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Store config
        self.config = config

        # Create resources
        self.lambda_function = self._create_lambda_function()
        self.api_gateway = self._create_api_gateway()

        # Outputs
        self._create_outputs()

    def _create_lambda_function(self) -> lambda_.DockerImageFunction:
        """
        Create Lambda function from Docker container image

        CDK automatically:
        1. Builds the Docker image using Dockerfile.lambda
        2. Creates/updates ECR repository
        3. Pushes image to ECR
        4. Updates Lambda function with new image
        """

        # Reference existing secrets from AWS Secrets Manager
        openai_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "OpenAISecret",
            self.config.secrets["openai_api_key"]
        )

        line_token = secretsmanager.Secret.from_secret_name_v2(
            self,
            "LineToken",
            self.config.secrets["line_channel_access_token"]
        )

        line_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "LineSecret",
            self.config.secrets["line_channel_secret"]
        )

        # Create Lambda function
        function = lambda_.DockerImageFunction(
            self,
            "LineBotFunction",
            function_name=self.config.function_name,
            code=lambda_.DockerImageCode.from_image_asset(
                directory="../",  # Root of project
                file="Dockerfile.lambda",  # Dockerfile to use
            ),
            timeout=Duration.seconds(self.config.timeout_seconds),
            memory_size=self.config.memory_size,
            environment={
                "OPENAI_API_KEY": openai_secret.secret_value.unsafe_unwrap(),
                "LINE_CHANNEL_ACCESS_TOKEN": line_token.secret_value.unsafe_unwrap(),
                "LINE_CHANNEL_SECRET": line_secret.secret_value.unsafe_unwrap(),
            },
            log_retention=self._get_log_retention(),
            description=f"LINE Bot Ticker Report ({self.config.env_name})",
        )

        # Grant secrets read permission
        openai_secret.grant_read(function)
        line_token.grant_read(function)
        line_secret.grant_read(function)

        return function

    def _create_api_gateway(self) -> apigw.HttpApi:
        """
        Create API Gateway HTTP API for LINE webhook

        Creates:
        - HTTP API with POST /webhook endpoint
        - Lambda integration
        """

        # Create HTTP API
        api = apigw.HttpApi(
            self,
            "LineBotApi",
            api_name=f"line-bot-webhook-api-{self.config.env_name}",
            description=f"LINE Bot webhook endpoint ({self.config.env_name})",
        )

        # Add webhook route
        api.add_routes(
            path="/webhook",
            methods=[apigw.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration(
                "WebhookIntegration",
                self.lambda_function,
            ),
        )

        return api

    def _get_log_retention(self) -> logs.RetentionDays:
        """Convert config days to RetentionDays enum"""
        retention_map = {
            1: logs.RetentionDays.ONE_DAY,
            3: logs.RetentionDays.THREE_DAYS,
            7: logs.RetentionDays.ONE_WEEK,
            14: logs.RetentionDays.TWO_WEEKS,
            30: logs.RetentionDays.ONE_MONTH,
        }
        return retention_map.get(
            self.config.log_retention_days,
            logs.RetentionDays.ONE_WEEK
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for important values"""

        CfnOutput(
            self,
            "FunctionName",
            value=self.lambda_function.function_name,
            description="Lambda function name",
        )

        CfnOutput(
            self,
            "FunctionArn",
            value=self.lambda_function.function_arn,
            description="Lambda function ARN",
        )

        CfnOutput(
            self,
            "ApiEndpoint",
            value=self.api_gateway.url or "N/A",
            description="API Gateway endpoint URL",
        )

        CfnOutput(
            self,
            "WebhookUrl",
            value=f"{self.api_gateway.url}webhook" if self.api_gateway.url else "N/A",
            description="LINE webhook URL (update in LINE console)",
        )
```

#### Step 3.3: Update CDK App Entry Point

**File:** `infrastructure/app.py`

```python
#!/usr/bin/env python3
"""
AWS CDK App for LINE Bot Infrastructure
"""
import os
from aws_cdk import App, Environment
from infrastructure.linebot_stack import LineBotStack
from infrastructure.config import get_config

# Create CDK app
app = App()

# Get environment from context (defaults to 'prod')
env_name = app.node.try_get_context("env") or "prod"
config = get_config(env_name)

# Create stack
LineBotStack(
    app,
    f"LineBotStack-{config.env_name}",
    config=config,
    env=Environment(
        account=config.account,
        region=config.region,
    ),
    description=f"LINE Bot Ticker Report Infrastructure ({config.env_name})",
)

app.synth()
```

#### Step 3.4: Update Requirements

**File:** `infrastructure/requirements.txt`

```txt
aws-cdk-lib>=2.100.0
constructs>=10.0.0
```

**Success Criteria:**
- ✅ All Python files created without syntax errors
- ✅ Configuration properly structured
- ✅ Stack references correct Dockerfile path

---

### Phase 4: Secrets Management Setup
**Estimated Time:** 15 minutes
**Dependencies:** Phase 3 complete

#### Step 4.1: Check Existing Secrets

```bash
# Check if secrets already exist
aws secretsmanager list-secrets --region us-east-1 | grep -E "openai|line"
```

#### Step 4.2: Create Secrets (if needed)

If secrets don't exist in AWS Secrets Manager:

```bash
# Option 1: Create from environment variables (if they exist)
aws secretsmanager create-secret \
    --name openai-api-key \
    --secret-string "$OPENAI_API_KEY" \
    --region us-east-1

aws secretsmanager create-secret \
    --name line-channel-access-token \
    --secret-string "$LINE_CHANNEL_ACCESS_TOKEN" \
    --region us-east-1

aws secretsmanager create-secret \
    --name line-channel-secret \
    --secret-string "$LINE_CHANNEL_SECRET" \
    --region us-east-1

# Option 2: Create with placeholder (update manually in console)
aws secretsmanager create-secret \
    --name openai-api-key \
    --secret-string "PLACEHOLDER" \
    --region us-east-1
# Then update in AWS Console with actual value
```

#### Step 4.3: Verify Secrets

```bash
# List secret names (not values)
aws secretsmanager list-secrets \
    --region us-east-1 \
    --query 'SecretList[?contains(Name, `openai`) || contains(Name, `line`)].Name'
```

**Success Criteria:**
- ✅ All three secrets exist in AWS Secrets Manager
- ✅ Secrets contain correct values (test manually)

---

### Phase 5: Testing & Validation
**Estimated Time:** 20 minutes
**Dependencies:** Phases 1-4 complete

#### Step 5.1: Synthesize CloudFormation Template

```bash
cd infrastructure
cdk synth
```

This will:
- Validate Python code
- Generate CloudFormation template
- Show any errors/warnings

**Expected Output:** CloudFormation YAML template printed to console

#### Step 5.2: Review Generated Template

```bash
cdk synth > template.yaml
less template.yaml
```

Check for:
- Lambda function definition
- ECR repository
- API Gateway resources
- IAM roles
- Environment variables

#### Step 5.3: Compare with Current Infrastructure

```bash
# Get current Lambda config
aws lambda get-function --function-name line-bot-ticker-report

# Compare key settings:
# - Memory size (should be 512 MB)
# - Timeout (should be 60s)
# - Environment variables (count should match)
```

#### Step 5.4: Dry Run Deployment

```bash
cdk diff
```

This shows what will change when deployed. Should show:
- New resources to create (if first deployment)
- Or changes to existing resources

**Success Criteria:**
- ✅ `cdk synth` completes without errors
- ✅ Generated template looks correct
- ✅ `cdk diff` shows expected changes

---

### Phase 6: Deployment
**Estimated Time:** 15 minutes
**Dependencies:** Phase 5 validation passed

#### Step 6.1: First Deployment (Production)

```bash
cd infrastructure

# Deploy with confirmation prompt
cdk deploy

# Or skip confirmation (for CI/CD)
cdk deploy --require-approval never
```

**What happens during deployment:**
1. Docker image built from Dockerfile.lambda
2. Image tagged and pushed to ECR
3. CloudFormation stack created/updated
4. Lambda function created/updated with new image
5. API Gateway created/configured
6. Outputs displayed (webhook URL, function ARN, etc.)

**Expected Duration:** 5-10 minutes (mostly Docker build)

#### Step 6.2: Capture Outputs

```bash
# Get stack outputs
cdk output

# Or via AWS CLI
aws cloudformation describe-stacks \
    --stack-name LineBotStack-prod \
    --query 'Stacks[0].Outputs'
```

Save:
- Webhook URL (for LINE console)
- Function ARN
- API Gateway ID

#### Step 6.3: Update LINE Console

1. Log into LINE Developers Console
2. Navigate to your bot's settings
3. Update webhook URL to new API Gateway endpoint
4. Verify webhook (LINE sends test request)

**Success Criteria:**
- ✅ CloudFormation stack created successfully
- ✅ Lambda function updated with new deployment method
- ✅ API Gateway endpoint accessible
- ✅ LINE webhook verification passes

---

### Phase 7: Validation & Testing
**Estimated Time:** 20 minutes
**Dependencies:** Phase 6 deployment complete

#### Step 7.1: Test Lambda Function Directly

```bash
# Invoke function with test event
aws lambda invoke \
    --function-name line-bot-ticker-report \
    --payload '{"body": "test"}' \
    response.json

cat response.json
```

#### Step 7.2: Check CloudWatch Logs

```bash
# Get latest log stream
aws logs tail /aws/lambda/line-bot-ticker-report --follow
```

#### Step 7.3: Test API Gateway Endpoint

```bash
# Get webhook URL from outputs
WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name LineBotStack-prod \
    --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
    --output text)

echo "Webhook URL: $WEBHOOK_URL"

# Test with curl (will fail LINE signature check, but shows it's reachable)
curl -X POST $WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{"events": []}'
```

#### Step 7.4: End-to-End Test with LINE

Send a test message to your LINE bot:
1. Open LINE app
2. Find your bot
3. Send ticker symbol (e.g., "AAPL")
4. Verify report is generated

#### Step 7.5: Compare with Manual Deployment

```bash
# Check function configuration matches
aws lambda get-function-configuration \
    --function-name line-bot-ticker-report \
    | jq '{MemorySize, Timeout, Runtime: "Image"}'
```

**Success Criteria:**
- ✅ Lambda function responds correctly
- ✅ CloudWatch logs show execution
- ✅ API Gateway endpoint accessible
- ✅ LINE bot responds to messages
- ✅ Functionality identical to manual deployment

---

### Phase 8: Documentation & Cleanup
**Estimated Time:** 15 minutes
**Dependencies:** Phase 7 validation complete

#### Step 8.1: Create Infrastructure README

**File:** `infrastructure/README.md`

```markdown
# LINE Bot Infrastructure (AWS CDK)

This directory contains Infrastructure as Code (IaC) for the LINE Bot Ticker Report.

## Prerequisites

- Node.js >= 14.x
- Python >= 3.11
- AWS CLI configured with credentials
- AWS CDK CLI: `npm install -g aws-cdk`

## Quick Start

```bash
# Install dependencies
cd infrastructure
pip install -r requirements.txt

# Synthesize CloudFormation template
cdk synth

# Preview changes
cdk diff

# Deploy to AWS
cdk deploy
```

## Architecture

- **Lambda Function**: Container image from Dockerfile.lambda
- **API Gateway**: HTTP API with POST /webhook endpoint
- **Secrets Manager**: Stores sensitive credentials
- **CloudWatch Logs**: 7-day retention

## Deployment

### Production

```bash
cdk deploy
```

### Development

```bash
cdk deploy -c env=dev
```

## Updating the Application

1. Make code changes in `src/`
2. Run `cdk deploy`
3. CDK automatically rebuilds and pushes Docker image
4. Lambda function updated with new image

## Secrets Management

Secrets are stored in AWS Secrets Manager:
- `openai-api-key`
- `line-channel-access-token`
- `line-channel-secret`

Update via AWS Console or CLI:

```bash
aws secretsmanager update-secret \
    --secret-id openai-api-key \
    --secret-string "new-value"
```

## Rollback

```bash
# List previous versions
aws cloudformation list-stack-resources --stack-name LineBotStack-prod

# Rollback to previous version
cdk deploy --previous-parameters
```

## Cleanup

```bash
# Delete all resources
cdk destroy
```

## Troubleshooting

### Build fails

```bash
# Check Docker is running
docker ps

# Manually build to test
docker build -f Dockerfile.lambda -t test .
```

### Deployment fails

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name LineBotStack-prod

# Check CDK version
cdk --version  # Should be >= 2.100.0
```

### Lambda not updating

```bash
# Force new image build
cdk deploy --force
```
```

#### Step 8.2: Update Root README (Optional)

Add section to main README.md about deployment:

```markdown
## Deployment

### Using Infrastructure as Code (CDK)

```bash
cd infrastructure
cdk deploy
```

See [infrastructure/README.md](infrastructure/README.md) for details.

### Manual Deployment (Legacy)

See [scripts/deploy.sh](scripts/deploy.sh) for the legacy manual deployment process.
```

#### Step 8.3: Archive Old Deployment Script

```bash
# Keep for reference but mark as deprecated
mv scripts/deploy.sh scripts/deploy.sh.deprecated

# Or add warning comment
echo "# DEPRECATED: Use CDK deployment (cd infrastructure && cdk deploy)" | \
    cat - scripts/deploy.sh > temp && mv temp scripts/deploy.sh
```

#### Step 8.4: Create Deployment Runbook

**File:** `infrastructure/RUNBOOK.md`

```markdown
# Deployment Runbook

## Standard Deployment

```bash
cd infrastructure
cdk diff          # Review changes
cdk deploy        # Deploy
```

## Emergency Rollback

```bash
# Option 1: Via CloudFormation
aws cloudformation update-stack \
    --stack-name LineBotStack-prod \
    --use-previous-template

# Option 2: Via git
git checkout <previous-commit>
cdk deploy
```

## Monitoring

```bash
# Watch logs
aws logs tail /aws/lambda/line-bot-ticker-report --follow

# Check function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=line-bot-ticker-report \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum
```

## Common Issues

### Secret not found
```bash
aws secretsmanager describe-secret --secret-id <name>
```

### Image too large
- Check `requirements_lambda.txt` for unnecessary packages
- Use multi-stage Docker build

### Timeout
- Increase timeout in `config.py`
- Check for slow external API calls
```

**Success Criteria:**
- ✅ Infrastructure README created
- ✅ Runbook documented
- ✅ Root README updated (optional)
- ✅ Old scripts archived/marked deprecated

---

## Multi-Environment Support (Future)

### Creating Development Environment

```bash
# Deploy to dev
cd infrastructure
cdk deploy -c env=dev

# This creates separate:
# - Lambda function: line-bot-ticker-report-dev
# - API Gateway: line-bot-webhook-api-dev
# - CloudFormation stack: LineBotStack-dev
```

### Environment-Specific Configurations

Edit `infrastructure/infrastructure/config.py`:

```python
DEV_CONFIG = EnvironmentConfig(
    env_name="dev",
    memory_size=256,  # Lower memory for cost savings
    timeout_seconds=30,  # Shorter timeout
    log_retention_days=3,  # Less retention
)
```

---

## Cost Considerations

### Current Manual Deployment Costs
- Lambda: Pay per request + compute time
- ECR: Storage for images (~$0.10/GB/month)
- API Gateway: Pay per request
- CloudWatch: Log storage

### Additional CDK Costs
- **S3 Bucket**: CDK staging bucket (~$0.023/GB/month) - Minimal
- **CloudFormation**: Free
- **Total Additional**: < $1/month

**Net Impact:** Negligible cost increase, significant operational improvement

---

## Rollback Plan

If CDK deployment fails or causes issues:

### Option 1: Rollback via CloudFormation

```bash
aws cloudformation update-stack \
    --stack-name LineBotStack-prod \
    --use-previous-template \
    --parameters UsePreviousValue=true
```

### Option 2: Revert to Manual Deployment

```bash
# Use old deployment script
./scripts/deploy.sh

# CDK resources can be deleted later
cd infrastructure
cdk destroy
```

### Option 3: Update CDK Stack

```bash
# Fix issue in code
# Then redeploy
cd infrastructure
cdk deploy
```

---

## Success Metrics

### Deployment Time
- **Before (Manual)**: 10-15 minutes of manual steps
- **After (CDK)**: 5-10 minutes, mostly automated

### Reproducibility
- **Before**: Difficult to recreate exact configuration
- **After**: `cdk deploy` recreates everything

### Version Control
- **Before**: Infrastructure changes not tracked
- **After**: All infrastructure in git

### Multi-Environment
- **Before**: Manual copying of configuration
- **After**: `cdk deploy -c env=dev`

---

## Appendices

### A. CDK Commands Reference

```bash
cdk init            # Initialize new project
cdk synth           # Generate CloudFormation template
cdk diff            # Compare deployed vs local
cdk deploy          # Deploy stack
cdk destroy         # Delete all resources
cdk bootstrap       # One-time account setup
cdk ls              # List stacks
cdk docs            # Open CDK documentation
```

### B. AWS CLI Commands

```bash
# Lambda
aws lambda get-function --function-name <name>
aws lambda invoke --function-name <name> response.json

# CloudFormation
aws cloudformation describe-stacks --stack-name <name>
aws cloudformation list-stack-resources --stack-name <name>

# Secrets Manager
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id <name>

# ECR
aws ecr describe-repositories
aws ecr list-images --repository-name <name>

# CloudWatch Logs
aws logs tail /aws/lambda/<function-name> --follow
```

### C. Troubleshooting

**Error: "Resource already exists"**
- CDK trying to create existing resource
- Solution: Import existing resource or rename in config

**Error: "Unable to access secret"**
- Lambda doesn't have permission
- Solution: Check IAM role has `secretsmanager:GetSecretValue`

**Error: "Docker build failed"**
- Issue with Dockerfile or dependencies
- Solution: Test build locally: `docker build -f Dockerfile.lambda .`

**Error: "Stack is in UPDATE_ROLLBACK_FAILED state"**
- Previous deployment failed and left stack in bad state
- Solution: Manually fix resource or continue rollback via console

---

## Timeline

### Phase 1: Setup (15 min)
- Install CDK CLI
- Verify credentials

### Phase 2: Initialize (10 min)
- Create infrastructure directory
- Bootstrap CDK

### Phase 3: Code (45 min)
- Write config.py
- Write linebot_stack.py
- Update app.py

### Phase 4: Secrets (15 min)
- Create/verify secrets in AWS

### Phase 5: Test (20 min)
- cdk synth
- cdk diff
- Review template

### Phase 6: Deploy (15 min)
- cdk deploy
- Update LINE console

### Phase 7: Validate (20 min)
- Test Lambda
- Test API Gateway
- Test end-to-end with LINE

### Phase 8: Document (15 min)
- Write READMEs
- Create runbook

**Total: 2 hours 35 minutes**

---

## Next Steps After Implementation

1. **Set up CI/CD**: Automate deployment on git push
2. **Add Monitoring**: CloudWatch alarms for errors
3. **Create Dev Environment**: Test changes before prod
4. **Add Tests**: Unit tests for stack configuration
5. **Cost Optimization**: Reserved concurrency, right-sizing

---

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Python API Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [API Gateway HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Status:** Ready for Implementation
