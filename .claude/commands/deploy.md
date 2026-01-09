---
name: deploy
description: Safe deployment workflow with pre-deployment verification, step-by-step plan, and post-deployment validation
accepts_args: true
arg_schema:
  - name: environment
    required: true
    description: "Target environment: dev, staging, or prod"
composition:
  - skill: deployment
---

# Deploy Command

**Purpose**: Deploy current branch code to specified AWS environment

**Core Principle**: "Deploy from current branch to any environment" - same code, different targets

**When to use**:
- Deploying code changes to dev/staging/prod
- Manual deployment when CI/CD unavailable
- Promoting tested code to higher environments
- Deploying hotfixes directly to staging/prod

**When NOT to use**:
- Infrastructure-only changes (use `terraform apply`)
- Emergency rollbacks (use direct `aws lambda update-alias`)
- Local testing (no deployment needed)

---

## Quick Reference

```bash
# Deploy current branch to dev
/deploy dev

# Deploy current branch to staging
/deploy staging

# Deploy current branch to production
/deploy prod
```

---

## Environment Mapping

| Argument | Environment | Doppler Config | ECR Repository |
|----------|-------------|----------------|----------------|
| `dev` | Development | `dev` | `dr-daily-report-lambda-dev` |
| `staging` | Staging | `stg` | `dr-daily-report-lambda-staging` |
| `prod` | Production | `prd` | `dr-daily-report-lambda-prod` |

---

## Execution Flow

### Phase 1: Pre-Deployment Validation

**Check current state**:
```bash
# 1. Get current branch
git branch --show-current

# 2. Check for uncommitted changes
git status --porcelain

# 3. Verify Doppler config exists
doppler run --config {config} -- printenv | head -5
```

**Validation rules**:
- ✅ Current branch has no uncommitted changes
- ✅ Doppler config exists for target environment
- ✅ Required secrets are set (TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, etc.)

---

### Phase 2: Build Docker Image

**Build for target environment**:
```bash
# Get ECR registry
ECR_REGISTRY=$(aws ecr describe-repositories \
  --repository-names dr-daily-report-lambda-{env} \
  --query 'repositories[0].repositoryUri' --output text)

# Generate image tag (timestamp-based)
IMAGE_TAG="v$(date +%Y%m%d%H%M%S)"

# Build Docker image
docker build -t $ECR_REGISTRY:$IMAGE_TAG .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
docker push $ECR_REGISTRY:$IMAGE_TAG

# Get immutable digest
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $ECR_REGISTRY:$IMAGE_TAG)
```

---

### Phase 3: Update Lambda Functions

**Deploy to all Lambda functions in environment**:
```bash
# List all Lambda functions for environment
FUNCTIONS=$(aws lambda list-functions \
  --query "Functions[?contains(FunctionName, '-{env}')].FunctionName" \
  --output text)

# Update each function
for FUNC in $FUNCTIONS; do
  echo "Updating $FUNC..."
  aws lambda update-function-code \
    --function-name $FUNC \
    --image-uri $DIGEST

  aws lambda wait function-updated --function-name $FUNC
  echo "✅ $FUNC updated"
done
```

---

### Phase 4: Update Terraform State

**Sync Terraform with new image tag**:
```bash
cd terraform

# Initialize for target environment
terraform init -backend-config=backend-{env}.hcl -reconfigure

# Apply with new image tag
doppler run --config {config} -- terraform apply \
  -var-file=terraform.{env}.tfvars \
  -var="lambda_image_tag=$IMAGE_TAG" \
  -auto-approve
```

---

### Phase 5: Post-Deployment Validation

**Verify deployment success**:
```bash
# 1. Check Lambda image URI
aws lambda get-function --function-name dr-daily-report-telegram-api-{env} \
  --query 'Code.ImageUri'

# 2. Health check
curl -s https://{api-gateway-url}/api/v1/health

# 3. Check for errors in logs (last 5 minutes)
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-{env} \
  --start-time $(date -d '5 minutes ago' +%s000) \
  --filter-pattern "ERROR"
```

---

## Output Format

```markdown
# Deployment: {environment}

**Branch**: {current-branch}
**Target**: {environment}
**Date**: {YYYY-MM-DD HH:MM Bangkok}

---

## Phase 1: Pre-Deployment Validation

- [✅] No uncommitted changes
- [✅] Doppler config exists ({config})
- [✅] Required secrets set

---

## Phase 2: Build Docker Image

ECR Registry: {registry-url}
Image Tag: {tag}
Digest: {digest}

Build time: {duration}

---

## Phase 3: Update Lambda Functions

| Function | Status | Duration |
|----------|--------|----------|
| telegram-api-{env} | ✅ | 45s |
| report-worker-{env} | ✅ | 42s |
| ticker-scheduler-{env} | ✅ | 38s |
| ... | ... | ... |

Total functions: {count}
Total time: {duration}

---

## Phase 4: Terraform Sync

Resources updated: {count}
Apply time: {duration}

---

## Phase 5: Validation

- [✅] Health check: {"status":"ok"}
- [✅] No errors in logs (last 5 min)
- [✅] Image digest matches

---

## Summary

**Status**: ✅ SUCCESS
**Duration**: {total-duration}
**Image**: {digest}

**URLs**:
- API: {api-gateway-url}
- CloudFront: {cloudfront-url}
```

---

## Examples

### Example 1: Deploy to Dev

```bash
/deploy dev
```

**Output**:
```markdown
# Deployment: dev

**Branch**: feature/add-pattern-detection
**Target**: dev
**Date**: 2026-01-09 22:30 Bangkok

## Phase 1: Pre-Deployment Validation
- [✅] No uncommitted changes
- [✅] Doppler config exists (dev)
- [✅] Required secrets set

## Phase 2: Build Docker Image
ECR Registry: 755283537543.dkr.ecr.ap-southeast-1.amazonaws.com/dr-daily-report-lambda-dev
Image Tag: v20260109223015
Digest: sha256:abc123...

Build time: 2m 15s

## Phase 3: Update Lambda Functions
Total functions: 12
Total time: 4m 30s

## Phase 4: Terraform Sync
Resources updated: 12
Apply time: 1m 45s

## Phase 5: Validation
- [✅] Health check: {"status":"ok"}
- [✅] No errors in logs

## Summary
**Status**: ✅ SUCCESS
**Duration**: 8m 30s

**URLs**:
- API: https://xyz123.execute-api.ap-southeast-1.amazonaws.com
- CloudFront: https://demjoigiw6myp.cloudfront.net
```

---

### Example 2: Deploy to Staging

```bash
/deploy staging
```

**Execution notes**:
- Uses `stg` Doppler config
- Pushes to `dr-daily-report-lambda-staging` ECR
- Updates staging Lambda functions
- Uses `terraform.staging.tfvars`

---

### Example 3: Deploy to Production (with extra confirmation)

```bash
/deploy prod
```

**Additional checks for production**:
- Require explicit confirmation before proceeding
- Verify staging health before promoting
- Create Lambda version after successful deployment
- Update 'live' alias to new version

---

## Rollback

If deployment fails or causes issues:

```bash
# Option 1: Deploy previous commit
git checkout HEAD~1
/deploy {env}

# Option 2: Direct Lambda rollback (instant)
aws lambda update-alias \
  --function-name dr-daily-report-telegram-api-{env} \
  --name live \
  --function-version {previous-version}

# Option 3: Use previous image digest
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-{env} \
  --image-uri {previous-digest}
```

---

## Best Practices

### Do
- **Commit changes before deploying** (clean working directory)
- **Deploy to dev first** (test before staging/prod)
- **Monitor logs after deployment** (catch issues early)
- **Use waiters** (not sleep)

### Don't
- **Don't deploy uncommitted changes** (not reproducible)
- **Don't skip dev** (unless hotfix)
- **Don't ignore validation failures** (will cause issues)
- **Don't deploy to prod without staging first** (except hotfixes)

---

## Integration with Branch Strategy

**Documented branch strategy** (from CLAUDE.md):
```
dev branch    → dev environment (~8 min)
main branch   → staging environment (~10 min)
Tags v*.*.*   → production (~12 min)
```

**This command overrides branch strategy** - deploy ANY branch to ANY environment:
- Useful for testing features in staging before merging to main
- Useful for hotfixes directly to prod
- Useful when CI/CD is unavailable

---

## See Also

- **Skills**: [deployment](../skills/deployment/) - Deployment methodology
- **Docs**: [MULTI_ENV.md](../../docs/deployment/MULTI_ENV.md) - Environment strategy
- **Principles**:
  - #6 Deployment Monitoring Discipline
  - #11 Artifact Promotion Principle
  - #15 Infrastructure-Application Contract

---

## Prompt Template

You are executing the `/deploy` command with arguments: $ARGUMENTS

**Target environment**: $1

---

### Execution Steps

**Phase 1: Pre-Deployment Validation**

1. Get current branch: `git branch --show-current`
2. Check uncommitted changes: `git status --porcelain`
3. Map environment to Doppler config:
   - dev → `dev`
   - staging → `stg`
   - prod → `prd`
4. Verify Doppler config: `doppler run --config {config} -- printenv | head -5`
5. If validation fails: STOP, show what's missing

**Phase 2: Build Docker Image**

1. Get ECR registry for environment
2. Generate timestamp-based image tag
3. Build Docker image
4. Push to ECR
5. Get immutable digest

**Phase 3: Update Lambda Functions**

1. List all Lambda functions for environment
2. Update each function with new image digest
3. Wait for each function to be ready
4. Track success/failure

**Phase 4: Update Terraform State**

1. Initialize Terraform for target environment
2. Apply with new image tag
3. Verify resources updated

**Phase 5: Post-Deployment Validation**

1. Run health check against API
2. Check CloudWatch logs for errors
3. Verify image digest matches

**Output**: Use format above with all phases and clear status indicators.

**For production deployments**: Require explicit user confirmation before proceeding.
