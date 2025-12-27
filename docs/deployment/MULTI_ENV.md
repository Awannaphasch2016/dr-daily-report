# Multi-Environment Strategy

How dev, staging, and prod environments are managed.

---

## Environment Architecture

**Core Principle:** Same infrastructure code, different configuration values.

```
terraform/*.tf (SHARED CODE)
     │
     ├──▶ envs/dev/terraform.tfvars      → Dev environment
     ├──▶ envs/staging/terraform.tfvars  → Staging environment
     └──▶ envs/prod/terraform.tfvars     → Production environment
```

---

## Configuration Differences

### Infrastructure Configuration

| Config | Dev | Staging | Prod |
|--------|-----|---------|------|
| Lambda Memory | 512 MB | 1024 MB | 1024 MB |
| Lambda Timeout | 120s | 120s | 300s |
| Log Retention | 7 days | 14 days | 30 days |
| API Rate Limit | 10 req/s | 50 req/s | 100 req/s |
| Reserved Concurrency | 5 | 10 | 50 |
| Auto-scaling Target | 70% CPU | 60% CPU | 50% CPU |

### State Isolation

Each environment has its own Terraform state file in S3:

```
s3://dr-daily-report-tf-state/
├── telegram-api/dev/terraform.tfstate
├── telegram-api/staging/terraform.tfstate
└── telegram-api/prod/terraform.tfstate
```

**Why separate states:**
- Prevents accidental cross-environment changes
- Enables independent lifecycle management
- Reduces blast radius (dev changes can't break prod)

---

## Terraform Backend Configuration

### Backend Files

```bash
# envs/dev/backend.hcl
bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/dev/terraform.tfstate"
region         = "ap-southeast-1"
dynamodb_table = "terraform-state-lock"
encrypt        = true

# envs/staging/backend.hcl
bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/staging/terraform.tfstate"  # Different key
region         = "ap-southeast-1"
dynamodb_table = "terraform-state-lock"
encrypt        = true

# envs/prod/backend.hcl
bucket         = "dr-daily-report-tf-state"
key            = "telegram-api/prod/terraform.tfstate"  # Different key
region         = "ap-southeast-1"
dynamodb_table = "terraform-state-lock"
encrypt        = true
```

### Switching Environments

```bash
# Initialize for dev
cd terraform
terraform init -backend-config=envs/dev/backend.hcl

# Switch to staging (must reconfigure)
terraform init -backend-config=envs/staging/backend.hcl -reconfigure

# Switch to prod
terraform init -backend-config=envs/prod/backend.hcl -reconfigure
```

**CRITICAL:** Always use `-reconfigure` when switching environments to ensure correct state file.

---

## Environment Variables

### Doppler Configuration

Each environment has separate Doppler config:

```bash
# Dev environment
doppler setup --config dev
doppler secrets --config dev

# Staging environment
doppler setup --config staging
doppler secrets --config staging

# Prod environment
doppler setup --config prod
doppler secrets --config prod
```

### Environment-Specific Secrets

| Secret | Dev | Staging | Prod |
|--------|-----|---------|------|
| `OPENAI_API_KEY` | Test key | Test key | Production key |
| `DATABASE_URL` | Dev Aurora | Staging Aurora | Prod Aurora |
| `CLOUDFRONT_DISTRIBUTION_ID` | Dev CloudFront | Staging CloudFront | Prod CloudFront |
| `LOG_LEVEL` | DEBUG | INFO | WARNING |

---

## Deployment Workflow Per Environment

### Dev Environment

**Purpose:** Rapid iteration, testing new features.

**Deployment:**
- Auto-deploys on push to `telegram` branch
- No manual approval required
- Smoke tests run, but failures don't block deployment

```bash
# Manual deploy to dev
cd terraform
terraform init -backend-config=envs/dev/backend.hcl
terraform apply -var-file=envs/dev/terraform.tfvars

# Code deployment (auto via CI/CD)
git push origin telegram  # Auto-deploys to dev
```

### Staging Environment

**Purpose:** Pre-production validation, E2E testing.

**Deployment:**
- Auto-deploys after dev succeeds (CI/CD)
- Same Docker image as dev (artifact promotion)
- E2E tests must pass before promoting to prod

```bash
# Manual deploy to staging
cd terraform
terraform init -backend-config=envs/staging/backend.hcl -reconfigure
terraform apply -var-file=envs/staging/terraform.tfvars

# Code deployment (auto via CI/CD after dev succeeds)
# No manual action needed - CI/CD handles promotion
```

### Production Environment

**Purpose:** User-facing, stability critical.

**Deployment:**
- Auto-deploys after staging succeeds (CI/CD)
- Same Docker image as staging (tested image)
- Rollback plan required before deploy

```bash
# Manual deploy to prod
cd terraform
terraform init -backend-config=envs/prod/backend.hcl -reconfigure
terraform apply -var-file=envs/prod/terraform.tfvars

# Code deployment (auto via CI/CD after staging succeeds)
# CI/CD handles promotion with smoke tests
```

---

## Branch-Based Deployment

**Principle:** Git branches determine environment deployment.

### Development Environment (dev branch)

**Purpose:** Fast feedback loop for active development.

**Deployment Trigger:**
```bash
# Work on feature branch
git checkout -b feature/user-analytics
# ... make changes ...
git add .
git commit -m "feat: Add user analytics tracking"

# Merge to dev branch
git checkout dev
git merge feature/user-analytics
git push origin dev

# GitHub Actions automatically deploys to dev
```

**CI/CD Workflow (.github/workflows/deploy-dev.yml):**

```yaml
name: Deploy to Dev
on:
  push:
    branches: [dev]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        id: build
        run: |
          IMAGE_TAG=${{ secrets.ECR_REGISTRY }}/worker:${{ github.sha }}
          docker build -t $IMAGE_TAG .
          docker push $IMAGE_TAG

          # Get immutable digest for promotion
          DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $IMAGE_TAG)
          echo "digest=$DIGEST" >> $GITHUB_OUTPUT

      - name: Deploy to dev Lambda
        run: |
          aws lambda update-function-code \
            --function-name dr-daily-report-worker-dev \
            --image-uri ${{ steps.build.outputs.digest }}

          aws lambda wait function-updated \
            --function-name dr-daily-report-worker-dev

      - name: Run smoke tests
        run: |
          pytest tests/smoke --env=dev --tier=3

      - name: Save digest for promotion
        run: |
          echo "${{ steps.build.outputs.digest }}" > digest.txt

      - uses: actions/upload-artifact@v4
        with:
          name: image-digest
          path: digest.txt
```

**What Gets Deployed:**
- Lambda function: `dr-daily-report-worker-dev`
- Database: `dr-daily-report-dev` (Aurora cluster)
- S3 bucket: `dr-daily-report-data-dev`
- CloudFront: dev distribution

**When to Use:**
- Feature development
- Bug fixes
- Experiments
- Fast iteration

### Staging Environment (main branch)

**Purpose:** Pre-production validation.

**Deployment Trigger:**
```bash
# Create PR from dev to main
git checkout dev
gh pr create --base main --title "Release v1.2.0"

# After review and approval
gh pr merge 123

# GitHub Actions automatically deploys to staging
```

**CI/CD Workflow (.github/workflows/deploy-staging.yml):**

```yaml
name: Deploy to Staging
on:
  push:
    branches: [main]

jobs:
  promote-to-staging:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Find dev image digest
        id: find-image
        run: |
          # Get digest from dev (don't rebuild!)
          DEV_DIGEST=$(aws lambda get-function \
            --function-name dr-daily-report-worker-dev \
            --query 'Code.ImageUri' --output text)

          echo "digest=$DEV_DIGEST" >> $GITHUB_OUTPUT

      - name: Deploy to staging Lambda
        run: |
          # Deploy SAME image as dev (artifact promotion)
          aws lambda update-function-code \
            --function-name dr-daily-report-worker-staging \
            --image-uri ${{ steps.find-image.outputs.digest }}

          aws lambda wait function-updated \
            --function-name dr-daily-report-worker-staging

      - name: Run integration tests
        run: |
          pytest tests/integration --env=staging --tier=2

      - name: Smoke test staging
        run: |
          curl -f https://staging.example.com/api/health || exit 1
```

**What Gets Deployed:**
- Lambda function: `dr-daily-report-worker-staging`
- Database: `dr-daily-report-staging` (Aurora cluster)
- S3 bucket: `dr-daily-report-data-staging`
- CloudFront: staging distribution

**When to Use:**
- Pre-production validation
- QA testing
- Performance testing
- Integration testing

### Production Environment (tags on main)

**Purpose:** Live user traffic.

**Deployment Trigger:**
```bash
# On main branch, create release tag
git tag v1.2.0 -m "Release v1.2.0: User analytics"
git push origin v1.2.0

# GitHub Actions automatically deploys to production
```

**CI/CD Workflow (.github/workflows/deploy-production.yml):**

```yaml
name: Deploy to Production
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  promote-to-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Find staging image digest
        id: find-image
        run: |
          # Get digest from staging
          STAGING_DIGEST=$(aws lambda get-function \
            --function-name dr-daily-report-worker-staging \
            --query 'Code.ImageUri' --output text)

          echo "digest=$STAGING_DIGEST" >> $GITHUB_OUTPUT

      - name: Deploy to production Lambda
        run: |
          # Deploy SAME image as staging
          aws lambda update-function-code \
            --function-name dr-daily-report-worker-prod \
            --image-uri ${{ steps.find-image.outputs.digest }}

          aws lambda wait function-updated \
            --function-name dr-daily-report-worker-prod

      - name: Smoke test production
        run: |
          curl -f https://api.example.com/health || exit 1

      - name: Publish version
        run: |
          VERSION=$(aws lambda publish-version \
            --function-name dr-daily-report-worker-prod \
            --query 'Version' --output text)

          echo "Published Lambda version: $VERSION"

          # Update live alias
          aws lambda update-alias \
            --function-name dr-daily-report-worker-prod \
            --name live \
            --function-version $VERSION
```

**What Gets Deployed:**
- Lambda function: `dr-daily-report-worker-prod`
- Database: `dr-daily-report-prod` (Aurora cluster)
- S3 bucket: `dr-daily-report-data-prod`
- CloudFront: production distribution

**When to Use:**
- Releases only
- After staging validation
- Semantic versioning (v1.2.3)

---

## Artifact Promotion Principle

**Principle:** Build once, deploy many times.

### The Problem: Rebuilding Per Environment

**Traditional approach (inefficient):**

```yaml
# ❌ DON'T: Rebuild for each environment
dev-deploy:
  - Build Docker image
  - Test
  - Deploy to dev

staging-deploy:
  - Build Docker image again  # Different build!
  - Test
  - Deploy to staging

prod-deploy:
  - Build Docker image again  # Yet another build!
  - Test
  - Deploy to production
```

**Problems:**
- Different builds may have subtle differences
- Can't guarantee "what you tested is what you deployed"
- Wastes build time (3x longer)
- Docker layer caching doesn't work across builds
- Git SHA doesn't guarantee identical binary

### The Solution: Immutable Artifact Promotion

```yaml
# ✅ DO: Build once, promote same artifact
build:
  - Build Docker image
  - Push to ECR with digest
  - Save digest as artifact

dev-deploy:
  - Deploy digest from build job
  - Test

staging-deploy:
  - Deploy SAME digest as dev
  - Test

prod-deploy:
  - Deploy SAME digest as staging
  - Publish version
```

**Benefits:**
- ✅ Exact same binary in all environments
- ✅ Staging validation applies to production
- ✅ Faster deployments (no rebuild)
- ✅ Traceability (Git SHA → Digest → Environments)

### Implementation Pattern

**Step 1: Build and Tag**

```bash
# Build image with Git SHA tag
IMAGE_TAG=$ECR_REGISTRY/worker:$GIT_SHA
docker build -t $IMAGE_TAG .
docker push $IMAGE_TAG

# Get immutable digest
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $IMAGE_TAG)
# Example: 123456.dkr.ecr.ap-southeast-1.amazonaws.com/worker@sha256:abc123...
```

**Step 2: Deploy to Dev**

```bash
aws lambda update-function-code \
  --function-name worker-dev \
  --image-uri $DIGEST
```

**Step 3: Promote to Staging**

```bash
# Get digest from dev (don't rebuild!)
DEV_DIGEST=$(aws lambda get-function \
  --function-name worker-dev \
  --query 'Code.ImageUri' --output text)

# Deploy SAME digest
aws lambda update-function-code \
  --function-name worker-staging \
  --image-uri $DEV_DIGEST
```

**Step 4: Promote to Production**

```bash
# Get digest from staging
STAGING_DIGEST=$(aws lambda get-function \
  --function-name worker-staging \
  --query 'Code.ImageUri' --output text)

# Deploy SAME digest
aws lambda update-function-code \
  --function-name worker-prod \
  --image-uri $STAGING_DIGEST
```

**Verification:**

```bash
# Prove all environments use EXACT same image
aws lambda get-function --function-name worker-dev --query 'Code.ImageUri'
aws lambda get-function --function-name worker-staging --query 'Code.ImageUri'
aws lambda get-function --function-name worker-prod --query 'Code.ImageUri'

# All three should output IDENTICAL digest:
# 123456.dkr.ecr.ap-southeast-1.amazonaws.com/worker@sha256:abc123...
```

---

## Environment Promotion Flow

```
Developer Push
     │
     ├─▶ BUILD: Docker image tagged sha-abc123
     │
     ├─▶ DEV: Deploy sha-abc123 → smoke test → promote
     │         └─ PASS → continue
     │         └─ FAIL → stop, notify
     │
     ├─▶ STAGING: Deploy sha-abc123 → smoke test → E2E tests → promote
     │              └─ PASS → continue
     │              └─ FAIL → stop, notify
     │
     └─▶ PROD: Deploy sha-abc123 → smoke test → promote
                 └─ PASS → success!
                 └─ FAIL → auto-rollback
```

**Key Points:**
- Same Docker image through all environments
- Progressive validation (smoke → E2E → smoke)
- Automatic rollback on prod failure

---

## Resource Naming Convention

### Naming Pattern

```
{project}-{component}-{environment}

Examples:
- dr-daily-report-telegram-api-dev
- dr-daily-report-telegram-api-staging
- dr-daily-report-telegram-api-prod
```

### AWS Resource Tags

All resources tagged with:
```hcl
tags = {
  Project     = "dr-daily-report"
  Environment = var.environment  # dev/staging/prod
  ManagedBy   = "Terraform"
  App         = "telegram-api"
  Component   = var.component_name
  Owner       = "data-team"
  CostCenter  = "engineering"
}
```

**Cost tracking by environment:**
```bash
# View dev costs
aws ce get-cost-and-usage \
  --filter file://dev-filter.json \
  --time-period Start=2025-12-01,End=2025-12-07 \
  --granularity DAILY \
  --metrics BlendedCost

# dev-filter.json
{
  "Tags": {
    "Key": "Environment",
    "Values": ["dev"]
  }
}
```

---

## Environment-Specific Configuration Files

### Directory Structure

```
terraform/
├── envs/
│   ├── dev/
│   │   ├── backend.hcl           # S3 backend config
│   │   └── terraform.tfvars      # Variable values
│   ├── staging/
│   │   ├── backend.hcl
│   │   └── terraform.tfvars
│   └── prod/
│       ├── backend.hcl
│       └── terraform.tfvars
└── *.tf                          # Shared infrastructure code
```

### Example terraform.tfvars

```hcl
# envs/dev/terraform.tfvars
environment = "dev"
aws_region  = "ap-southeast-1"

# Lambda configuration
lambda_memory_size    = 512
lambda_timeout        = 120
lambda_concurrency    = 5

# API Gateway configuration
api_throttle_rate_limit  = 10
api_throttle_burst_limit = 20

# CloudWatch configuration
log_retention_days = 7

# DynamoDB configuration
dynamodb_billing_mode = "PAY_PER_REQUEST"

# CloudFront configuration
telegram_webapp_urls = [
  "https://demjoigiw6myp.cloudfront.net"  # Dev CloudFront
]
```

```hcl
# envs/prod/terraform.tfvars
environment = "prod"
aws_region  = "ap-southeast-1"

# Lambda configuration
lambda_memory_size    = 1024
lambda_timeout        = 300
lambda_concurrency    = 50

# API Gateway configuration
api_throttle_rate_limit  = 100
api_throttle_burst_limit = 200

# CloudWatch configuration
log_retention_days = 30

# DynamoDB configuration
dynamodb_billing_mode = "PROVISIONED"
dynamodb_read_capacity  = 50
dynamodb_write_capacity = 25

# CloudFront configuration
telegram_webapp_urls = [
  "https://d3uuexs20crp9s.cloudfront.net"  # Prod CloudFront
]
```

---

## Multi-Environment Testing

### Integration Tests Per Environment

```bash
# Test dev environment
ENV=dev pytest tests/integration/ -v

# Test staging environment
ENV=staging pytest tests/integration/ -v

# Test prod environment (read-only smoke tests)
ENV=prod pytest tests/integration/test_smoke.py -v
```

### E2E Tests Per Environment

```bash
# Test dev frontend
E2E_BASE_URL="https://demjoigiw6myp.cloudfront.net" \
  pytest tests/e2e/ -v

# Test staging frontend
E2E_BASE_URL="https://d3uuexs20crp9s.cloudfront.net" \
  pytest tests/e2e/ -v

# Test prod frontend (read-only)
E2E_BASE_URL="https://d24cidhj2eghux.cloudfront.net" \
  pytest tests/e2e/test_smoke.py -v
```

---

## Common Environment Tasks

### Querying Current Environment

```bash
# Check which environment Terraform is configured for
terraform show | grep -i environment

# Check Lambda environment variables
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'Environment.Variables.ENVIRONMENT' \
  --output text
```

### Comparing Environments

```bash
# Compare Lambda memory
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev \
  --query 'MemorySize'
# → 512

aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-prod \
  --query 'MemorySize'
# → 1024
```

### Syncing Configuration Across Environments

```bash
# Apply same infra change to all environments
for env in dev staging prod; do
  echo "Applying to $env..."
  terraform init -backend-config=envs/$env/backend.hcl -reconfigure
  terraform apply -var-file=envs/$env/terraform.tfvars -auto-approve
done
```

**Warning:** Only use auto-approve for non-breaking changes.

---

## Environment Isolation Best Practices

### 1. Separate AWS Accounts (Future Improvement)

**Current:** All environments in same AWS account (755283537543)

**Future:** Move to separate accounts:
- Dev: 111111111111
- Staging: 222222222222
- Prod: 333333333333

**Benefits:**
- Complete billing separation
- IAM isolation (dev users can't access prod)
- Resource limit isolation

### 2. Network Isolation (Future Improvement)

**Current:** All environments use public API Gateway endpoints

**Future:** VPC isolation:
- Dev: VPC with public subnets only
- Staging: VPC with public + private subnets
- Prod: VPC with private subnets + NAT Gateway

### 3. State Lock Discipline

**NEVER run terraform commands in parallel across environments:**

```bash
# BAD: Parallel deploys can corrupt state
terraform apply -var-file=envs/dev/terraform.tfvars &
terraform apply -var-file=envs/staging/terraform.tfvars &
wait

# GOOD: Sequential deploys
terraform apply -var-file=envs/dev/terraform.tfvars
terraform apply -var-file=envs/staging/terraform.tfvars
```

---

## See Also

- [Lambda Versioning](LAMBDA_VERSIONING.md) - Zero-downtime deployment
- [Deployment Workflow](WORKFLOW.md) - Build and deploy process
- [CI/CD Architecture](CI_CD.md) - Auto-progressive deployment
