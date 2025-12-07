# Deployment Workflow

Complete build and deployment process for Telegram Mini App.

---

## Build Process

### Docker Image Build

```bash
# Build Lambda container image
docker build -t dr-daily-report-lambda-dev:latest -f Dockerfile.lambda.container .

# Tag with immutable SHA-based tag
TAG="sha-$(git rev-parse --short HEAD)-$(date '+%Y%m%d-%H%M%S')"
docker tag dr-daily-report-lambda-dev:latest $ECR_REPO:$TAG

# Push to ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin $ECR_REPO
docker push $ECR_REPO:$TAG
```

**Why SHA-based tags:**
- Immutable: can't be overwritten
- Traceable: links deployment to exact commit
- Promotable: same image through all envs

### Frontend Build

```bash
# Install dependencies
cd frontend/telegram-webapp
npm install

# Build production bundle
npm run build

# Sync to S3
aws s3 sync dist/ s3://telegram-webapp-bucket-dev/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_DIST_ID \
  --paths "/*"
```

---

## Deployment Commands

### Backend Deployment (Lambda)

```bash
# Update Lambda function code
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-dev \
  --image-uri $ECR_REPO:$TAG \
  --query 'FunctionArn' \
  --output text

# Wait for update (CRITICAL - use waiter, not sleep)
aws lambda wait function-updated \
  --function-name dr-daily-report-telegram-api-dev

# Smoke test $LATEST
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --qualifier '$LATEST' \
  --payload '{"httpMethod": "GET", "path": "/api/v1/health"}' \
  /tmp/smoke-test.json

# Publish immutable version
VERSION=$(aws lambda publish-version \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'Version' \
  --output text)

# Update "live" alias (zero-downtime cutover)
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-dev \
  --name live \
  --function-version $VERSION

echo "✅ Deployed version $VERSION to live alias"
```

### Frontend Deployment (CloudFront)

```bash
# Two-CloudFront pattern for zero-risk deployment

# 1. Deploy to TEST CloudFront
./scripts/deploy-frontend.sh dev --test-only

# 2. Run E2E tests against TEST CloudFront
E2E_BASE_URL="$CLOUDFRONT_TEST_DOMAIN" pytest tests/e2e/ -v

# 3. If tests pass, deploy to APP CloudFront
./scripts/deploy-frontend.sh dev --app-only

# 4. If tests fail, APP CloudFront unchanged (users see old version)
```

**Why two CloudFronts:**
- TEST CloudFront = staging area for E2E testing
- APP CloudFront = user-facing (only updated after tests pass)
- Mirrors Lambda $LATEST vs "live" alias pattern

---

## Justfile Recipes

### Common Development Tasks

```bash
# Daily development
just daily                # Pull, setup, test

# Pre-commit
just pre-commit          # Syntax check + tests

# Testing
just test                # All tests
just test-deploy         # Deploy gate tests only

# Report generation
just report DBS19        # Single-stage report
just report-multi DBS19  # Multi-stage report

# Build & deploy
just build               # Build Lambda package
just deploy-dev         # Deploy to dev
just ship-it            # Build + deploy to all envs
```

### Deployment Recipes

```bash
# Backend deployment
just deploy-backend dev    # Deploy Lambda to dev
just deploy-backend staging
just deploy-backend prod

# Frontend deployment
just deploy-frontend dev   # Deploy webapp to dev
just deploy-frontend staging
just deploy-frontend prod

# Full deployment (backend + frontend)
just deploy-all dev       # Deploy everything to dev
```

---

## Environment-Specific Deployment

### Dev Environment

```bash
# Quick iteration cycle
cd terraform
terraform init -backend-config=envs/dev/backend.hcl
terraform apply -var-file=envs/dev/terraform.tfvars

# Deploy code
TAG="sha-abc123" ./scripts/deploy-backend.sh dev
```

### Staging Environment

```bash
# Promote tested dev image
cd terraform
terraform init -backend-config=envs/staging/backend.hcl -reconfigure
terraform apply -var-file=envs/staging/terraform.tfvars

# Deploy same image as dev
TAG="sha-abc123" ./scripts/deploy-backend.sh staging
```

### Production Environment

```bash
# Promote tested staging image
cd terraform
terraform init -backend-config=envs/prod/backend.hcl -reconfigure
terraform apply -var-file=envs/prod/terraform.tfvars

# Deploy same image as staging
TAG="sha-abc123" ./scripts/deploy-backend.sh prod
```

**Critical:** Always use same TAG across all environments (artifact promotion).

---

## Rollback Procedures

### Backend Rollback

```bash
# List recent versions
aws lambda list-versions-by-function \
  --function-name dr-daily-report-telegram-api-prod \
  --max-items 5

# Rollback to previous version
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live \
  --function-version <previous-version>

# Verify rollback
aws lambda get-alias \
  --function-name dr-daily-report-telegram-api-prod \
  --name live
```

### Frontend Rollback

```bash
# Option 1: Rollback S3 files (if versioning enabled)
aws s3 cp s3://telegram-webapp-bucket-prod/ s3://telegram-webapp-bucket-prod/ \
  --recursive \
  --metadata-directive COPY \
  --source-version-id <previous-version-id>

# Option 2: Re-deploy previous git commit
git checkout <previous-commit>
npm run build
aws s3 sync dist/ s3://telegram-webapp-bucket-prod/
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

---

## Smoke Testing

### Backend Health Check

```bash
# Test Lambda directly
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --qualifier '$LATEST' \
  --payload '{"httpMethod": "GET", "path": "/api/v1/health"}' \
  /tmp/health.json

# Check response
cat /tmp/health.json | jq '.statusCode'
# Expected: 200

# Test via API Gateway
curl "https://api.example.com/api/v1/health"
# Expected: {"status": "healthy", "version": "1.0.0"}
```

### Frontend Smoke Test

```bash
# Check CloudFront serves index.html
curl -I "https://d24cidhj2eghux.cloudfront.net/"
# Expected: HTTP/2 200

# Check JavaScript bundle loads
curl "https://d24cidhj2eghux.cloudfront.net/assets/index-*.js" | head -c 100
# Expected: valid JavaScript code
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image_uri: ${{ steps.build.outputs.image_uri }}
    steps:
      - name: Build Docker image
        id: build
        run: |
          TAG="sha-${GITHUB_SHA::7}-$(date '+%Y%m%d-%H%M%S')"
          docker build -t $ECR_REPO:$TAG .
          docker push $ECR_REPO:$TAG
          echo "image_uri=$ECR_REPO:$TAG" >> $GITHUB_OUTPUT

  deploy-dev:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to dev
        run: |
          aws lambda update-function-code \
            --function-name dr-daily-report-telegram-api-dev \
            --image-uri ${{ needs.build.outputs.image_uri }}
```

---

## Troubleshooting

### Deployment Fails Silently

**Symptom:** `terraform apply` succeeds but Lambda shows old code.

**Cause:** Didn't wait for update to complete before testing.

**Fix:**
```bash
# Always use waiter
aws lambda wait function-updated --function-name $FUNC
```

### CloudFront Still Serves Old Files

**Symptom:** Deployed new frontend but users see old version.

**Cause:** CloudFront cache not invalidated or invalidation not complete.

**Fix:**
```bash
# Create invalidation
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

# Wait for completion (CRITICAL)
aws cloudfront wait invalidation-completed \
  --distribution-id $DIST_ID \
  --id $INVALIDATION_ID
```

### Lambda Permission Denied

**Symptom:** `aws lambda update-function-code` returns access denied.

**Cause:** IAM policy missing `lambda:UpdateFunctionCode` permission.

**Fix:**
```bash
# Add permission to IAM policy
aws iam create-policy-version \
  --policy-arn $POLICY_ARN \
  --policy-document file://policy.json \
  --set-as-default
```

---

## See Also

- [Lambda Versioning](LAMBDA_VERSIONING.md) - Zero-downtime pattern
- [CI/CD Architecture](CI_CD.md) - GitHub Actions integration
- [Monitoring Guide](MONITORING.md) - Proper waiter usage
- [Multi-Environment Guide](MULTI_ENV.md) - Environment strategy
