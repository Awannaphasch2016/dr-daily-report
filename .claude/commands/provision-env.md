---
name: provision-env
description: Create new isolated infrastructure environment by transferring from existing working environment
accepts_args: true
arg_schema:
  - name: target_env
    required: true
    description: "Target environment name (staging, prod, feature-x)"
  - name: source_env
    required: false
    default: dev
    description: "Source environment to clone from (default: dev)"
---

# Provision Environment Command

**Extends**: [/transfer](transfer.md) (Foundation Layer)
**Domain**: Infrastructure configuration
**Transfer Type**: Homogeneous (source env = target env type)

---

## Foundation Parameters

This command is a **specialization** of the [Transform Foundation](transfer.md):

```
Transform(X, Context_A, Context_B, Invariants) → X'

/provision-env instantiation:
├── WHAT (X):        infra (infrastructure configuration)
├── WHERE:           internal→internal (env to env)
├── HOW:             copy (mechanical reproduction with name substitution)
└── Invariants:      {resource_isolation, functionality, behavioral_contracts}
```

---

## Purpose

Create a new isolated infrastructure environment by cloning and adapting an existing working environment. This is a **homogeneous transfer** - source and target are both AWS environments.

**IMPORTANT**: This project uses `-var-file` pattern, NOT Terraform workspaces.

---

## Quick Start: Feature Branch Environment

The fastest path to creating an isolated feature branch environment:

```bash
# 1. Create tfvars file from dev
cp terraform/terraform.dev.tfvars terraform/terraform.feature-auth.tfvars

# 2. Edit environment name (the only REQUIRED change)
sed -i 's/environment  = "dev"/environment  = "feature-auth"/' terraform/terraform.feature-auth.tfvars

# 3. Plan (verify what will be created)
cd terraform && doppler run --config dev -- terraform plan -var-file=terraform.feature-auth.tfvars

# 4. Apply (create infrastructure)
doppler run --config dev -- terraform apply -var-file=terraform.feature-auth.tfvars

# 5. Cleanup when done
terraform destroy -var-file=terraform.feature-auth.tfvars
rm terraform.feature-auth.tfvars
```

**What this creates**: Complete isolated infrastructure with `-feature-auth` suffix:
- Lambda: `dr-daily-report-line-bot-feature-auth`
- Lambda: `dr-daily-report-telegram-api-feature-auth`
- DynamoDB: `dr-daily-report-telegram-watchlist-feature-auth`
- **Aurora**: `dr-daily-report-aurora-feature-auth` (+$43/month)
- etc.

**What is shared**: S3 buckets, ECR repository (same Docker images), VPC/NAT Gateway

---

## Feature Branch .tfvars Pattern

### Environment Naming Convention

| Environment Type | tfvars File | Example |
|-----------------|-------------|---------|
| Development | `terraform.dev.tfvars` | `environment = "dev"` |
| Staging | `terraform.staging.tfvars` | `environment = "staging"` |
| Production | `terraform.prod.tfvars` | `environment = "prod"` |
| **Feature Branch** | `terraform.feature-{name}.tfvars` | `environment = "feature-auth"` |

### Feature Branch tfvars Template

```hcl
# terraform/terraform.feature-{name}.tfvars
# Created from: terraform.dev.tfvars
# Purpose: Isolated environment for feature development

# REQUIRED CHANGE: Set unique environment name
environment  = "feature-{name}"  # e.g., "feature-auth", "feature-charts"

# Project Configuration (inherit from dev)
project_name = "dr-daily-report"
owner        = "data-team"
cost_center  = "engineering"

# AWS Configuration
aws_region = "ap-southeast-1"

# Lambda Configuration
lambda_memory  = 512
lambda_timeout = 120
log_retention_days = 3  # Shorter retention for feature envs (cost savings)

# OPTIONAL: Override for testing
# aurora_min_acu = 0.5  # Same as dev by default
```

### What Gets Isolated vs Shared

| Resource | Isolated Per-Environment | Shared | Notes |
|----------|-------------------------|--------|-------|
| Lambda functions | ✓ (suffixed) | | `dr-daily-report-*-{env}` |
| IAM roles | ✓ (suffixed) | | `dr-daily-report-*-role-{env}` |
| DynamoDB tables | ✓ (suffixed) | | `dr-daily-report-*-{env}` |
| API Gateway | ✓ (suffixed) | | Separate API per env |
| Step Functions | ✓ (suffixed) | | `dr-daily-report-*-{env}` |
| CloudWatch Log Groups | ✓ (prefixed) | | Per-function logs |
| **Aurora MySQL** | ✓ (suffixed) | | `dr-daily-report-aurora-{env}` |
| S3 buckets | | ✓ (same buckets) | Shared across envs |
| ECR repository | | ✓ (same images) | Docker images shared |
| VPC/Subnets | | ✓ (same network) | Default VPC |
| NAT Gateway | | ✓ (shared) | Single NAT for all |

**Note**: Aurora IS isolated per environment. Each environment creates its own Aurora cluster with `${var.environment}` suffix. This is by design in `terraform/aurora.tf`.

### Cost Considerations

| Resource | Dev Cost | Feature Branch Additional |
|----------|----------|---------------------------|
| Lambda | Pay-per-use | ~$0/month (idle) |
| DynamoDB | On-demand | ~$0/month (idle) |
| API Gateway | Pay-per-call | ~$0/month (idle) |
| **Aurora** | ~$43/month | **+$43/month** (new cluster) |
| **NAT Gateway** | ~$32/month | $0 (shared) |

**Cost warning**: Each new environment creates a NEW Aurora cluster (~$43/month minimum). Feature branches are NOT free if you need Aurora.

**When to create isolated environment**:
- Testing infrastructure changes (Lambda, IAM, API Gateway) → Low cost (pay-per-use)
- Testing schema migrations → **Costs $43+/month** for Aurora cluster
- Frontend-only changes → **Don't need new env** (use existing dev API)

### Cleanup Procedure

```bash
# 1. Destroy infrastructure
cd terraform
doppler run --config dev -- terraform destroy -var-file=terraform.feature-auth.tfvars

# 2. Remove tfvars file (not tracked in git)
rm terraform.feature-auth.tfvars

# 3. Verify no orphaned resources
aws lambda list-functions --query "Functions[?contains(FunctionName, 'feature-auth')]"
```

### CI/CD Integration (Future)

Feature branch environments can be automatically provisioned via GitHub Actions:

```yaml
# .github/workflows/feature-env.yml (future)
on:
  push:
    branches:
      - 'feature/**'

jobs:
  provision:
    runs-on: ubuntu-latest
    steps:
      - name: Create tfvars
        run: |
          BRANCH_NAME=${GITHUB_REF#refs/heads/}
          ENV_NAME=${BRANCH_NAME//\//-}  # feature/auth -> feature-auth
          cp terraform/terraform.dev.tfvars terraform/terraform.${ENV_NAME}.tfvars
          sed -i "s/environment  = \"dev\"/environment  = \"${ENV_NAME}\"/" terraform/terraform.${ENV_NAME}.tfvars

      - name: Terraform Apply
        run: |
          cd terraform
          terraform apply -var-file=terraform.${ENV_NAME}.tfvars -auto-approve
```

---

## Quick Reference

```bash
# Create staging from dev
/provision-env staging from=dev

# Create production from staging
/provision-env prod from=staging

# Create feature environment from dev
/provision-env feature-auth from=dev
```

---

## Relationship to Foundation Layer

This command implements the [Transform Foundation](transfer.md) for infrastructure domains:

| Foundation Aspect | /provision-env Value |
|-------------------|----------------------|
| **X (What)** | Infrastructure configuration (Terraform, IAM, env vars) |
| **Context_A** | Existing environment (e.g., dev) |
| **Context_B** | New environment (e.g., staging) |
| **Invariants** | Resource isolation, functionality, behavioral contracts |
| **Transfer type** | Homogeneous (env → env) |

**Portable** (Foundation Step 5 - UNTANGLE):
- Terraform structure, IAM policy shapes, env var keys

**Context-bound** (Foundation Step 5 - UNTANGLE):
- Resource names, external credentials, ARNs

---

## The 7-Step Process (Infrastructure Specialization)

### Step 1: IDENTIFY - Infrastructure Domain

**What infrastructure to transfer?**

Checklist:
- [ ] Lambda functions (list all)
- [ ] IAM roles and policies
- [ ] DynamoDB tables
- [ ] S3 buckets
- [ ] VPC configuration (if applicable)
- [ ] External service integrations (LINE, Telegram, etc.)

**Output**: Infrastructure inventory

```markdown
## Infrastructure Inventory for {source_env}

### Compute
- Lambda: dr-daily-report-line-bot-{env}
- Lambda: dr-daily-report-telegram-api-{env}

### IAM
- Role: dr-daily-report-line-bot-role-{env}
- Role: dr-daily-report-telegram-api-role-{env}

### Storage
- DynamoDB: dr-daily-report-telegram-watchlist-{env}
- S3: line-bot-pdf-reports-{account_id}

### External Services
- LINE Bot channel
- Telegram Bot

### Database
- Aurora cluster: dr-daily-report-aurora-{env} (isolated per environment)
```

---

### Step 2: ANALYZE SOURCE - Infrastructure Domain

**What does source environment have?**

Use AWS CLI to gather:
```bash
# List Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, 'dr-daily-report')]"

# Get Lambda configuration
aws lambda get-function-configuration --function-name {function_name}

# List IAM roles
aws iam list-roles --query "Roles[?contains(RoleName, 'dr-daily-report')]"

# Get environment variables
aws lambda get-function-configuration --function-name {function_name} --query "Environment.Variables"
```

**Output**: Source environment snapshot

---

### Step 3: ANALYZE TARGET - Infrastructure Domain

**What constraints apply to target?**

Constraints checklist:
- [ ] Resource naming convention: `{resource}-{env}`
- [ ] Environment isolation required (no credential sharing)
- [ ] CLAUDE.md principles apply (Principle #1, #15, #24)
- [ ] Doppler config needed for secrets

**External service requirements**:

| Service | Isolation Required? | Action |
|---------|--------------------| -------|
| LINE Bot | YES (per-channel webhooks) | Create new channel |
| Telegram Bot | YES (per-bot tokens) | Create new bot |
| Aurora | YES (per-env cluster) | New cluster created (+$43/month) |
| S3 | NO (shared buckets) | Same buckets |
| OpenRouter | NO (API key shared) | Same key |

---

### Step 4: MAP - Infrastructure Domain

**Create resource mapping table**:

| Source Resource | Target Resource | Action |
|-----------------|-----------------|--------|
| `dr-daily-report-line-bot-dev` | `dr-daily-report-line-bot-staging` | Clone + rename |
| `dr-daily-report-line-bot-role-dev` | `dr-daily-report-line-bot-role-staging` | Clone + rename |
| `dr-daily-report-aurora-dev` | `dr-daily-report-aurora-staging` | **NEW CLUSTER** (+$43/mo) |
| `LINE_CHANNEL_ACCESS_TOKEN` (dev) | `LINE_CHANNEL_ACCESS_TOKEN` (staging) | **NEW CREDENTIAL** |
| `AURORA_HOST` | `AURORA_HOST` | **NEW VALUE** (new cluster endpoint) |
| `OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` | Same value |

---

### Step 5: UNTANGLE - Infrastructure Domain

**Separate portable from context-bound**:

#### Portable (can copy)
- Terraform resource structure
- IAM policy shapes (permissions)
- Environment variable keys (not values)
- Lambda handler configuration
- Memory/timeout settings

#### Context-Bound (must isolate)
- **Resource names** → Add environment suffix
- **External service credentials** → Create NEW
  - `LINE_CHANNEL_ACCESS_TOKEN`
  - `LINE_CHANNEL_SECRET`
  - `TELEGRAM_BOT_TOKEN`
- **ARNs** → Auto-generated (don't copy)
- **Function URLs** → Auto-generated (don't copy)

---

### Step 6: REWIRE - Infrastructure Domain

**Execute the transfer**:

#### 6.1 Create Doppler Config
```bash
# Create new config inheriting from parent
doppler configs create {target_env} --project dr-daily-report
```

#### 6.2 Create Infrastructure (Terraform or AWS CLI)

**Option A: Terraform (preferred)**
```hcl
# Use environment variable in resource names
resource "aws_lambda_function" "line_bot" {
  function_name = "dr-daily-report-line-bot-${var.environment}"
  # ... rest of config
}
```

**Option B: AWS CLI (manual)**
```bash
# Create IAM role
aws iam create-role \
  --role-name dr-daily-report-line-bot-role-{target_env} \
  --assume-role-policy-document file://trust-policy.json

# Create Lambda
aws lambda create-function \
  --function-name dr-daily-report-line-bot-{target_env} \
  --role arn:aws:iam::{account}:role/dr-daily-report-line-bot-role-{target_env} \
  # ... rest of config
```

#### 6.3 Create External Service Credentials

**LINE Bot**:
1. Go to [LINE Developer Console](https://developers.line.biz/console/)
2. Create new channel for {target_env}
3. Issue channel access token
4. Copy channel secret
5. Update Doppler with new credentials

**Telegram Bot** (if applicable):
1. Message @BotFather
2. Create new bot for {target_env}
3. Copy bot token
4. Update Doppler with new token

#### 6.4 Update Doppler Secrets
```bash
# Set isolated credentials (external services)
doppler secrets set LINE_CHANNEL_ACCESS_TOKEN="{new_token}" --config {target_env}
doppler secrets set LINE_CHANNEL_SECRET="{new_secret}" --config {target_env}

# Aurora credentials (NEW cluster created by Terraform)
# AURORA_HOST will be the new cluster endpoint from terraform output
doppler secrets set AURORA_HOST="{new_cluster_endpoint}" --config {target_env}
doppler secrets set AURORA_PASSWORD="{same_password_or_new}" --config {target_env}
```

---

### Step 7: VERIFY - Infrastructure Domain

**Verification checklist** (Progressive Evidence - Principle #2):

#### Layer 1: Surface (Execution)
- [ ] Lambda exists: `aws lambda get-function --function-name {name}`
- [ ] Lambda returns 200: `aws lambda invoke --function-name {name} response.json`

#### Layer 2: Content (Payload)
- [ ] Response body is valid JSON
- [ ] No error messages in response

#### Layer 3: Observability (Logs)
- [ ] CloudWatch shows execution
- [ ] No errors in logs
- [ ] Application logs present (not just START/END)

#### Layer 4: Ground Truth (User Experience)
- [ ] **User receives message** (for LINE/Telegram)
- [ ] Webhook URL configured in external service
- [ ] End-to-end flow works

**Critical**: Don't stop at Layer 1 or 2. Layer 4 is required for external services.

---

## Master Checklist

### Infrastructure
- [ ] Lambda function created with correct name
- [ ] IAM role created with correct permissions
- [ ] Function URL or API Gateway configured
- [ ] DynamoDB tables created (if env-specific)

### Secrets (Doppler)
- [ ] Config created in Doppler
- [ ] Shared secrets configured (AURORA_*, OPENROUTER_API_KEY)
- [ ] **Isolated secrets configured** (LINE_*, TELEGRAM_*)

### External Services
- [ ] New LINE channel created (if applicable)
- [ ] New Telegram bot created (if applicable)
- [ ] Webhook URL updated in external service console
- [ ] Access token issued and stored in Doppler

### Verification
- [ ] Lambda responds 200
- [ ] CloudWatch logs show execution
- [ ] **E2E test passed** (user receives message)

---

## Common Failures and Solutions

### Failure 1: "Account cannot reply" (LINE)
**Cause**: Used dev credentials for staging (credential isolation violated)
**Solution**: Create new LINE channel and use staging-specific credentials
**Reference**: [LINE Staging Lessons Learned](../reports/2026-01-11-line-staging-credential-isolation-lessons.md)

### Failure 2: Missing environment variables
**Cause**: Incomplete Doppler config
**Solution**: Compare source env vars with target, fill gaps

### Failure 3: Wrong Lambda handler
**Cause**: Default handler doesn't match application
**Solution**: Explicitly set handler in Lambda config

### Failure 4: Permission denied
**Cause**: IAM role missing required permissions
**Solution**: Copy policy from source role, update resource ARNs

---

## Example: Dev → Staging

```bash
/provision-env staging from=dev
```

**Execution trace**:

```markdown
## Step 1: IDENTIFY
Infrastructure: LINE bot Lambda + IAM + external integration

## Step 2: ANALYZE SOURCE (dev)
- Lambda: dr-daily-report-line-bot-dev
- Role: dr-daily-report-line-bot-role-dev
- Env vars: 16 variables
- External: LINE channel (dev)

## Step 3: ANALYZE TARGET (staging)
- Must be isolated from dev
- LINE channel must be separate (per-channel webhooks)
- Aurora cluster will be NEW (created by Terraform)

## Step 4: MAP
| Source | Target | Action |
|--------|--------|--------|
| Lambda name | -staging suffix | Clone |
| Aurora cluster | -staging suffix | **NEW** (+$43/mo) |
| LINE_CHANNEL_* | NEW | Isolate |
| AURORA_HOST | NEW endpoint | Update after terraform |

## Step 5: UNTANGLE
Portable: Lambda config, IAM shape
Context-bound: LINE credentials, Aurora endpoint, resource names

## Step 6: REWIRE
1. Created IAM role: dr-daily-report-line-bot-role-staging
2. Created Lambda: dr-daily-report-line-bot-staging
3. Created Aurora cluster: dr-daily-report-aurora-staging
4. Created LINE channel in Developer Console
5. Updated Doppler with staging credentials (LINE + Aurora endpoint)

## Step 7: VERIFY
- [ ] Lambda returns 200 ✓
- [ ] CloudWatch logs present ✓
- [ ] User receives LINE message ✓

✅ Environment provisioned successfully
```

---

## See Also

- [/transfer](transfer.md) - Abstract transfer framework
- [/adapt](adapt.md) - Code transfer (heterogeneous)
- [Infrastructure Monitoring Exploration](../explorations/2026-01-14-infrastructure-monitoring-alerting.md) - Environment management pattern
- [Credential Isolation Lessons](../reports/2026-01-11-line-staging-credential-isolation-lessons.md) - Real incident
- [Deployment Skill](../skills/deployment/) - Deployment workflows
- [CLAUDE.md Principle #24](../CLAUDE.md) - External Service Credential Isolation
