# Can IaC Work Without ECR, CloudWatch, and API Gateway?

**Date:** 2025-11-09
**Question:** Do we need ECR, CloudWatch Logs, and API Gateway for Infrastructure as Code to work?

---

## Quick Answer

**Yes, IaC can work without these 3 services**, but with modifications to the Terraform configuration. Here's what you need to know:

---

## Current Situation

### What You Have ✅
- **Lambda Function**: `line-bot-ticker-report` (exists, ZIP deployment)
- **Permissions**: Lambda Full Access, S3 Full Access, IAM Full Access
- **Current Deployment**: Manual ZIP upload via `scripts/deploy.sh`

### What You're Missing ❌
- **ECR Permissions**: Cannot create Docker container repositories
- **CloudWatch Logs Permissions**: Cannot create log groups explicitly
- **API Gateway Permissions**: Cannot create HTTP APIs

### What Terraform Currently Tries to Create
Looking at `terraform/main.tf`, it attempts to create:
1. ✅ ECR Repository (for container images)
2. ✅ CloudWatch Log Groups (for Lambda and API Gateway logs)
3. ✅ API Gateway HTTP API (for LINE webhook endpoint)
4. ✅ Lambda Function (container-based)

---

## Can You Skip These Services?

### Option 1: Skip ECR (Use ZIP Deployment Instead) ✅ **FEASIBLE**

**What Changes:**
- Use ZIP deployment instead of container images
- No Docker builds needed
- No ECR repository needed

**Pros:**
- ✅ Works with your current permissions
- ✅ Simpler deployment (just ZIP file)
- ✅ No ECR costs

**Cons:**
- ❌ ZIP size limit: 250 MB (unzipped: 50 MB)
- ❌ Less flexible than containers
- ❌ Your current ZIP is ~57.5 MB (within limits)

**Terraform Changes Needed:**
```hcl
# Instead of container image:
resource "aws_lambda_function" "line_bot" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_role.arn
  
  # ZIP deployment instead of container
  filename         = "../build/lambda_deployment.zip"
  source_code_hash = filebase64sha256("../build/lambda_deployment.zip")
  handler          = "lambda_handler.lambda_handler"
  runtime          = "python3.11"
  
  # ... rest of config
}
```

**Remove:**
- ECR repository resource
- Docker build/push `null_resource`
- Container image configuration

---

### Option 2: Skip CloudWatch Log Groups ✅ **FEASIBLE**

**What Happens:**
- Lambda automatically creates log groups when it runs (if you have `AWSLambdaBasicExecutionRole`)
- Terraform just won't manage retention policies explicitly

**Pros:**
- ✅ Lambda will create logs automatically
- ✅ No permission needed
- ✅ Logs still work

**Cons:**
- ❌ No explicit retention policy (defaults to never expire = higher costs)
- ❌ Can't manage log groups via Terraform

**Terraform Changes Needed:**
```hcl
# Remove or comment out:
# resource "aws_cloudwatch_log_group" "lambda_logs" { ... }
# resource "aws_cloudwatch_log_group" "api_logs" { ... }

# Lambda will auto-create log groups when it runs
```

**Note:** Lambda's `AWSLambdaBasicExecutionRole` includes `logs:CreateLogGroup` permission, so Lambda can create its own log groups automatically.

---

### Option 3: Skip API Gateway ⚠️ **PARTIALLY FEASIBLE**

**What Changes:**
- Use existing API Gateway (if you have one)
- Or use Lambda Function URLs (newer, simpler)
- Or use EventBridge/other triggers

**Option 3A: Use Lambda Function URLs (Recommended) ✅**

Lambda Function URLs provide HTTP endpoints without API Gateway:

**Pros:**
- ✅ No API Gateway needed
- ✅ Simpler (built into Lambda)
- ✅ Lower cost ($0.00 for requests, only Lambda execution)
- ✅ Works with your permissions

**Cons:**
- ❌ Less features than API Gateway (no rate limiting, custom domains harder)
- ❌ For LINE webhook, this should work fine

**Terraform Changes Needed:**
```hcl
# Add Lambda Function URL instead of API Gateway
resource "aws_lambda_function_url" "line_bot_url" {
  function_name      = aws_lambda_function.line_bot.function_name
  authorization_type = "NONE"  # LINE validates signatures itself

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["*"]
  }
}

# Output webhook URL
output "webhook_url" {
  value = aws_lambda_function_url.line_bot_url.function_url
}
```

**Option 3B: Import Existing API Gateway ⚠️**

If you already have an API Gateway set up manually:

**Steps:**
1. Find your existing API Gateway ID
2. Import it into Terraform:
```bash
terraform import aws_apigatewayv2_api.line_webhook <api-id>
```
3. Modify Terraform to reference existing API instead of creating new

**Pros:**
- ✅ Use existing infrastructure
- ✅ Terraform can manage it going forward

**Cons:**
- ❌ Requires finding existing API Gateway ID
- ❌ May need to match configuration exactly

**Option 3C: Skip API Gateway Entirely ❌**

**Problem:** LINE Bot needs an HTTP endpoint to receive webhooks. Without API Gateway or Function URL, there's no way for LINE to call your Lambda.

**Verdict:** You MUST have either:
- API Gateway (if you can get permissions or import existing)
- Lambda Function URL (recommended, works with your permissions)

---

## Recommended Approach: Minimal IaC

Based on your permissions, here's what I recommend:

### Minimal Terraform Configuration

**Keep:**
- ✅ Lambda Function (ZIP deployment)
- ✅ IAM Roles
- ✅ Lambda Function URL (instead of API Gateway)

**Remove:**
- ❌ ECR Repository
- ❌ Docker build/push
- ❌ CloudWatch Log Groups (let Lambda auto-create)
- ❌ API Gateway (use Function URL instead)

**Result:**
- ✅ Works with your current permissions
- ✅ Still get IaC benefits (version control, automation)
- ✅ Simpler infrastructure
- ✅ Lower costs

---

## Comparison: Full vs Minimal IaC

| Feature | Full IaC (Current Plan) | Minimal IaC (Recommended) |
|---------|------------------------|---------------------------|
| **ECR** | ✅ Container images | ❌ ZIP deployment |
| **CloudWatch Logs** | ✅ Managed by Terraform | ✅ Auto-created by Lambda |
| **API Gateway** | ✅ HTTP API | ✅ Lambda Function URL |
| **Permissions Needed** | ECR + CloudWatch + API Gateway | None (you already have) |
| **Deployment Size** | Up to 10GB (containers) | 250MB ZIP limit |
| **Cost** | ~$5-15/month | ~$3-10/month |
| **Complexity** | Higher | Lower |

---

## Implementation: Minimal IaC Version

I can create a modified `terraform/main.tf` that:
1. Uses ZIP deployment (no ECR)
2. Skips CloudWatch log group creation (Lambda auto-creates)
3. Uses Lambda Function URL (no API Gateway)

**Would you like me to create this minimal version?**

---

## What About Existing Infrastructure?

### Check What Already Exists

You can check if these resources already exist:

```bash
# Check for existing Lambda function
aws lambda get-function --function-name line-bot-ticker-report --region ap-southeast-1

# Check for existing API Gateway
aws apigatewayv2 get-apis --region ap-southeast-1

# Check for existing ECR repositories
aws ecr describe-repositories --region ap-southeast-1

# Check for existing log groups
aws logs describe-log-groups --region ap-southeast-1 --log-group-name-prefix "/aws/lambda/line-bot"
```

**If resources exist:**
- You can import them into Terraform
- Terraform will manage them going forward
- No need to recreate

---

## Summary

### Can IaC Work Without These 3 Services?

| Service | Required? | Alternative |
|---------|-----------|-------------|
| **ECR** | ❌ No | Use ZIP deployment |
| **CloudWatch Logs** | ❌ No | Lambda auto-creates log groups |
| **API Gateway** | ⚠️ Yes (for webhook) | Use Lambda Function URL ✅ |

### Recommendation

**Use Minimal IaC:**
- ZIP deployment (no ECR)
- Lambda Function URL (no API Gateway)
- Auto-created CloudWatch logs (no explicit management)

**Benefits:**
- ✅ Works with your current permissions
- ✅ Still get IaC benefits
- ✅ Simpler, cheaper
- ✅ Can upgrade later when permissions available

---

## Next Steps

1. **Option A: Request Permissions** (Best long-term)
   - Get ECR, CloudWatch, API Gateway permissions
   - Use full Terraform configuration
   - Most flexible, full IaC benefits

2. **Option B: Minimal IaC** (Works now) ⭐ **RECOMMENDED**
   - Modify Terraform to use ZIP + Function URL
   - Works with current permissions
   - Still get IaC benefits

3. **Option C: Hybrid**
   - Import existing resources
   - Use Terraform for what you can
   - Manual steps for rest

**Which approach would you prefer?**
