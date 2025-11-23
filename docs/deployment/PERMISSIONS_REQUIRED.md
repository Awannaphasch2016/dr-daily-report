# AWS Permissions Required for Infrastructure Deployment

**Date:** 2025-11-09
**Status:** Deployment blocked - Missing IAM permissions

---

## Problem Summary

Attempted to deploy LINE Bot infrastructure using Terraform, but the AWS IAM user `anak` lacks necessary permissions.

### Failed Operations:
1. ❌ ECR:CreateRepository
2. ❌ CloudWatch Logs:CreateLogGroup
3. ❌ API Gateway:CreateApi

### Successful Operations:
1. ✅ IAM Role creation
2. ✅ IAM Policy attachments

---

## Required AWS IAM Permissions

To deploy the LINE Bot infrastructure via Terraform, your IAM user needs these additional AWS managed policies:

### Option 1: AWS Managed Policies (Recommended)

```
AmazonEC2ContainerRegistryFullAccess
CloudWatchLogsFullAccess
AmazonAPIGatewayAdministrator
```

### Option 2: Custom Policy (Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRManagement",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:DeleteRepository",
        "ecr:DescribeRepositories",
        "ecr:GetRepositoryPolicy",
        "ecr:SetRepositoryPolicy",
        "ecr:PutLifecyclePolicy",
        "ecr:GetLifecyclePolicy",
        "ecr:PutImage",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsManagement",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DeleteLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "logs:TagLogGroup",
        "logs:CreateLogStream",
        "logs:DeleteLogStream",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "APIGatewayManagement",
      "Effect": "Allow",
      "Action": [
        "apigateway:POST",
        "apigateway:GET",
        "apigateway:PUT",
        "apigateway:PATCH",
        "apigateway:DELETE",
        "apigateway:UpdateRestApiPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## How to Request Permissions

### For AWS Organization Administrator:

**Subject:** Request Additional IAM Permissions for LINE Bot Deployment

**Body:**
```
Hi [Admin Name],

I need additional AWS IAM permissions to deploy our LINE Bot infrastructure using
Infrastructure as Code (IaC).

Current Status:
- User: anak (arn:aws:iam::755283537543:user/anak)
- Project: LINE Bot Ticker Report
- Deployment Method: Terraform (Infrastructure as Code)

Required Permissions:
Please attach these AWS managed policies to my IAM user:

1. AmazonEC2ContainerRegistryFullAccess (for Docker container images)
2. CloudWatchLogsFullAccess (for application logging)
3. AmazonAPIGatewayAdministrator (for webhook endpoint)

Alternative: If you prefer least-privilege access, I can provide a custom policy JSON.

Why These Are Needed:
- ECR: Store Lambda container images
- CloudWatch Logs: Monitor application execution
- API Gateway: Provide webhook endpoint for LINE messaging

Current Permissions (Already Have):
- AWSLambda_FullAccess
- AmazonS3FullAccess
- IAMFullAccess

Project Details:
- Region: ap-southeast-1
- Resources: Lambda function, ECR repository, API Gateway, CloudWatch Logs
- Estimated Monthly Cost: < $20

Thank you!
```

---

## Alternative Approaches

### Approach 1: Request Full Permissions (Recommended)

**Pros:**
- ✅ Can use Terraform fully
- ✅ Infrastructure as Code benefits
- ✅ Automated, reproducible deployments

**Cons:**
- ⏱️ Requires approval from AWS admin

**Next Steps:**
1. Send permission request email
2. Wait for approval
3. Run `terraform apply` again

---

### Approach 2: Manual Resource Creation + Terraform

Create resources manually that require permissions, then let Terraform manage the rest.

**Manual Steps:**
```bash
# 1. Create ECR repository manually (via AWS Console or admin help)
aws ecr create-repository --repository-name line-bot-ticker-report --region ap-southeast-1

# 2. Create CloudWatch log groups manually
aws logs create-log-group --log-group-name /aws/lambda/line-bot-ticker-report --region ap-southeast-1
aws logs create-log-group --log-group-name /aws/apigateway/line-bot-ticker-report --region ap-southeast-1

# 3. Create API Gateway manually (AWS Console)
# Go to API Gateway → Create HTTP API → line-bot-ticker-report-api
```

**Then modify Terraform:**
```hcl
# Import existing resources instead of creating
terraform import aws_ecr_repository.lambda_repo line-bot-ticker-report
terraform import aws_cloudwatch_log_group.lambda_logs /aws/lambda/line-bot-ticker-report
terraform import aws_apigatewayv2_api.line_webhook <api-id>
```

**Pros:**
- ✅ Can proceed without waiting for permissions
- ✅ Still use Terraform for Lambda deployment

**Cons:**
- ❌ More complex setup
- ❌ Manual steps defeat IaC purpose
- ❌ Resource drift if manual changes made

---

### Approach 3: Continue with Manual Deployment

Stay with the original manual deployment method.

**Pros:**
- ✅ No permission changes needed
- ✅ Works with current permissions

**Cons:**
- ❌ No Infrastructure as Code
- ❌ Manual, error-prone process
- ❌ No version control for infrastructure

**Files:**
- Use existing `scripts/deploy.sh`
- Maintain current ZIP-based Lambda deployment

---

### Approach 4: Use AWS CLI for Permitted Operations Only

Since you have Lambda Full Access, you can update the Lambda function code directly.

**What You CAN Do:**
```bash
# Build Docker image locally
docker build -f Dockerfile.lambda.container -t line-bot-ticker-report:latest .

# Tag and push to existing ECR (if it exists)
docker tag line-bot-ticker-report:latest <ecr-url>:latest
docker push <ecr-url>:latest

# Update Lambda function (you have permission for this!)
aws lambda update-function-code \
  --function-name line-bot-ticker-report \
  --image-uri <ecr-url>:latest \
  --region ap-southeast-1
```

**Pros:**
- ✅ Can update Lambda with container images
- ✅ Partial automation possible

**Cons:**
- ❌ Requires ECR repository to already exist
- ❌ Cannot create new infrastructure
- ❌ API Gateway must exist already

---

## Current Infrastructure Status

### Created Successfully ✅:
- IAM Role: `line-bot-ticker-report-role`
- IAM Policy: `line-bot-ticker-report-custom-policy`
- IAM Policy Attachment: AWSLambdaBasicExecutionRole

### Failed to Create ❌:
- ECR Repository: `line-bot-ticker-report`
- CloudWatch Log Group: `/aws/lambda/line-bot-ticker-report`
- CloudWatch Log Group: `/aws/apigateway/line-bot-ticker-report`
- API Gateway: `line-bot-ticker-report-api`
- Lambda Function: (not attempted, depends on ECR)

### Cleanup Command:
```bash
cd terraform
terraform destroy  # Removes the IAM resources that were created
```

---

## Recommended Path Forward

### Immediate Action (Choose One):

**Option A: Request Permissions (Best Long-term)**
1. Send permission request to AWS admin using template above
2. Wait for approval
3. Run `terraform apply` again
4. **Estimated Time:** 1-3 days (depends on admin response)

**Option B: Hybrid Approach (Fastest)**
1. Ask AWS admin to create ECR repository + Log Groups + API Gateway
2. Import them into Terraform
3. Let Terraform manage Lambda updates going forward
4. **Estimated Time:** Few hours to 1 day

**Option C: Stay with Manual Deployment**
1. Continue using `scripts/deploy.sh`
2. Revisit IaC when permissions available
3. **Estimated Time:** Immediate (no changes needed)

---

## Permission Request Template (Copy-Paste Ready)

### Email Subject:
```
Request: Additional IAM Permissions for LINE Bot Infrastructure Deployment
```

### Email Body:
```
Hi [Admin Name],

I'm working on implementing Infrastructure as Code (IaC) for our LINE Bot project
to improve deployment automation and reliability.

**Request:**
Please add these AWS managed policies to my IAM user (anak):

1. AmazonEC2ContainerRegistryFullAccess
2. CloudWatchLogsFullAccess
3. AmazonAPIGatewayAdministrator

**Project Details:**
- User: anak (arn:aws:iam::755283537543:user/anak)
- Project: LINE Bot Ticker Report (Financial reports for LINE messaging)
- Region: ap-southeast-1
- Current Permissions: Lambda Full Access, S3 Full Access, IAM Full Access

**Why Needed:**
These permissions allow me to automate infrastructure deployment using Terraform:

- ECR: Store Docker container images for Lambda function (~500MB)
- CloudWatch Logs: Monitor application logs (7-day retention)
- API Gateway: Provide HTTP webhook endpoint for LINE messaging platform

**Benefits:**
- Version-controlled infrastructure (trackable changes)
- Reproducible deployments across environments
- Automated rollback capabilities
- Reduced manual errors

**Security:**
- Resources are isolated to this project
- All resources tagged with Project=LineBot
- Cost limit: < $20/month
- No sensitive data in infrastructure code (secrets in terraform.tfvars, git-ignored)

**Alternative:**
If full policies are too broad, I can provide a custom least-privilege policy JSON
that grants only the specific actions needed.

**Timeline:**
Once approved, deployment takes ~10 minutes. Currently blocked without these permissions.

Happy to discuss or provide more details!

Thank you,
[Your Name]
```

---

## Technical Details for Admin

### Resources to be Created:
```
1. ECR Repository: line-bot-ticker-report
   - Image scanning enabled
   - Lifecycle policy: keep last 5 images
   - Estimated size: 500MB per image
   - Cost: ~$0.10/GB/month (~$0.05/month)

2. CloudWatch Log Groups:
   - /aws/lambda/line-bot-ticker-report (7-day retention)
   - /aws/apigateway/line-bot-ticker-report (7-day retention)
   - Cost: $0.50/GB ingested + $0.03/GB stored

3. API Gateway HTTP API:
   - line-bot-ticker-report-api
   - POST /webhook endpoint
   - Lambda proxy integration
   - Cost: $1.00/million requests

4. Lambda Function:
   - line-bot-ticker-report (already exists, will be updated to container image)
   - No additional cost
```

### Total Estimated Monthly Cost: $5-15
- Most cost is Lambda execution time (same as current)
- New costs: ECR storage (~$0.05) + CloudWatch logs (~$0-5)

---

## Next Actions

1. **Choose an approach** from the options above
2. **If requesting permissions:**
   - Copy permission request email template
   - Send to AWS administrator
   - Wait for approval
3. **If going hybrid:**
   - Request manual creation of ECR, Log Groups, API Gateway
   - Then run: `terraform import <resources>`
4. **If continuing manual:**
   - Run: `cd terraform && terraform destroy` (cleanup)
   - Use: `scripts/deploy.sh` as before

---

**Status:** Awaiting decision on approach
**Documentation:** Complete (Terraform config ready when permissions available)
**Infrastructure Code:** ✅ Ready in `terraform/` directory
**Blocker:** IAM permissions

---

**Created:** 2025-11-09
**Last Updated:** 2025-11-09
