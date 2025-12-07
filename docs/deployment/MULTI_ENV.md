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
