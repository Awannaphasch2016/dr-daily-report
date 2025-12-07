# AWS Setup Guide

Quick IAM setup for deploying DR Daily Report Telegram Mini App.

---

## Quick Start

### 1. Create IAM User

```bash
# Create deployment user
aws iam create-user --user-name dr-deploy

# Generate access keys
aws iam create-access-key --user-name dr-deploy
# Save AccessKeyId and SecretAccessKey
```

### 2. Attach Required Policies

**Method A: Use Pre-Defined AWS Policies** (Quick but broad permissions)

```bash
aws iam attach-user-policy \
  --user-name dr-deploy \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

aws iam attach-user-policy \
  --user-name dr-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-user-policy \
  --user-name dr-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-user-policy \
  --user-name dr-deploy \
  --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess
```

**Method B: Use Least Privilege Policy** (Recommended for production)

See [docs/deployment/PERMISSIONS_REQUIRED.md](deployment/PERMISSIONS_REQUIRED.md) for complete IAM policy JSON.

---

### 3. Configure AWS CLI

```bash
# Configure with new credentials
aws configure --profile dr-prod
# AWS Access Key ID: <from step 1>
# AWS Secret Access Key: <from step 1>
# Default region: ap-southeast-1
# Default output format: json

# Test configuration
aws sts get-caller-identity --profile dr-prod
```

---

### 4. Set GitHub Secrets

For CI/CD deployment, add these secrets to GitHub repository:

```bash
# Via GitHub CLI
gh secret set AWS_ACCESS_KEY_ID --body "<access-key-id>"
gh secret set AWS_SECRET_ACCESS_KEY --body "<secret-access-key>"
gh secret set AWS_REGION --body "ap-southeast-1"

# Via GitHub UI
# Settings → Secrets and variables → Actions → New repository secret
```

**Required secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (ap-southeast-1)
- `CLOUDFRONT_DISTRIBUTION_ID` (from terraform output)
- `CLOUDFRONT_TEST_DISTRIBUTION_ID` (from terraform output)

---

## Permissions Breakdown

### Lambda Deployment
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:PublishVersion`
- `lambda:UpdateAlias`
- `lambda:GetFunction`

### S3 Frontend Deployment
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`
- `s3:DeleteObject`

### CloudFront Invalidation
- `cloudfront:CreateInvalidation`
- `cloudfront:GetInvalidation`

### DynamoDB Access
- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:Query`
- `dynamodb:Scan`

### RDS Aurora (Optional)
- `rds:DescribeDBClusters`
- `rds:DescribeDBInstances`

---

## Verify Setup

```bash
# Test Lambda access
aws lambda list-functions --profile dr-prod

# Test S3 access
aws s3 ls --profile dr-prod

# Test DynamoDB access
aws dynamodb list-tables --profile dr-prod

# Test CloudFront access
aws cloudfront list-distributions --profile dr-prod
```

---

## Troubleshooting

### Access Denied Errors

**Problem:** `User is not authorized to perform: <action>`

**Solution:**
```bash
# Check attached policies
aws iam list-attached-user-policies --user-name dr-deploy

# Check inline policies
aws iam list-user-policies --user-name dr-deploy

# Verify policy permissions
aws iam get-policy-version \
  --policy-arn <policy-arn> \
  --version-id v1
```

### Wrong Region

**Problem:** Resources not found

**Solution:**
```bash
# Check current region
aws configure get region --profile dr-prod

# Set correct region
aws configure set region ap-southeast-1 --profile dr-prod
```

---

## Security Best Practices

1. **Use IAM Roles for EC2/Lambda** (not user credentials)
2. **Rotate access keys every 90 days**
3. **Enable MFA for IAM users**
4. **Use least privilege policies** (not *FullAccess)
5. **Monitor with CloudTrail**

---

## References

- [Complete Permissions List](deployment/PERMISSIONS_REQUIRED.md)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Terraform Documentation](../terraform/README.md)
