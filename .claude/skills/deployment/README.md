# Deployment Skill

**Purpose**: Safe deployment workflow with pre-deployment verification, step-by-step plan, and post-deployment validation.

**Invoked by**: `/deploy` command

---

## Overview

This skill provides deployment procedures for multi-environment deployments:
- **Dev**: `dev` branch → dev environment
- **Staging**: `main` branch → staging environment
- **Production**: `v*.*.*` tags → production environment

---

## Deployment Components

### Lambda Functions by App

| App | Lambda Functions |
|-----|------------------|
| **Telegram API** | `telegram-api`, `report-worker` |
| **LINE Bot** | `line-bot` |
| **Scheduler** | `ticker-scheduler`, `precompute-controller`, `get-ticker-list`, `report-worker`, `pattern-precompute` |

### Infrastructure Components

| Component | Purpose |
|-----------|---------|
| ECR Repository | Docker image storage |
| Lambda Functions | Serverless compute |
| API Gateway | REST API routing |
| Step Functions | Workflow orchestration |
| EventBridge Scheduler | Daily scheduling |
| Aurora MySQL | Database |
| CloudFront | Frontend CDN |
| S3 | Frontend static assets |

---

## Deployment Phases

### Phase 1: Pre-Deployment Validation
- Check current branch
- Verify no uncommitted changes
- Validate Doppler config
- Verify required secrets

### Phase 2: Build Docker Image
- Build from Dockerfile
- Push to ECR
- Get immutable digest

### Phase 3: Update Lambda Functions
- Update all functions with new image
- Wait for each function to be ready
- **Includes pattern-precompute Lambda** (scheduler deployments)

### Phase 4: Terraform Sync
- Apply Terraform changes
- Update infrastructure state

### Phase 5: Post-Deployment Validation
- Health check
- Log monitoring
- Image digest verification
- **Pattern precompute Lambda verification** (scheduler deployments)
- **Step Functions state machine verification**

---

## Pattern Precomputation Deployment

**NEW (2026-01-15)**: Pattern precomputation reduces Telegram Mini App load time by 97-99%.

### What Deploys

| Resource | File |
|----------|------|
| Lambda Function | `src/scheduler/pattern_precompute_handler.py` |
| Step Functions Map State | `terraform/step_functions/precompute_workflow.json` |
| IAM Permissions | `terraform/precompute_workflow.tf` |
| CloudWatch Log Group | `/aws/lambda/dr-daily-report-pattern-precompute-{env}` |

### Verification After Deploy

```bash
# Verify Lambda exists
aws lambda get-function \
  --function-name dr-daily-report-pattern-precompute-{env} \
  --query 'Configuration.FunctionName'

# Verify Step Functions has pattern step
aws stepfunctions describe-state-machine \
  --state-machine-arn $(terraform output -raw precompute_workflow_arn) \
  --query 'definition' | grep -o 'FanOutToPatternWorkers'

# Test pattern precompute manually
aws lambda invoke \
  --function-name dr-daily-report-pattern-precompute-{env} \
  --payload '{"ticker":"NVDA19"}' \
  /tmp/test.json && cat /tmp/test.json
```

### Post-Deploy: Trigger First Precompute

After deploying pattern precompute Lambda:

```bash
# Option 1: Full precompute (recommended)
aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-{env} \
  --payload '{"source":"post-deploy"}' \
  /tmp/precompute.json

# Option 2: Single ticker test
aws lambda invoke \
  --function-name dr-daily-report-pattern-precompute-{env} \
  --payload '{"ticker":"NVDA19","ticker_id":1}' \
  /tmp/pattern.json
```

---

## Troubleshooting

### Pattern Lambda Not Deploying

**Symptom**: `pattern-precompute` Lambda not found after deploy

**Check**:
1. Verify code at `src/scheduler/pattern_precompute_handler.py` exists
2. Verify Terraform at `terraform/precompute_workflow.tf` includes `aws_lambda_function.pattern_precompute`
3. Confirm scheduler workflow triggered (path filter includes `src/scheduler/**`)

**Fix**: Re-run scheduler deployment workflow

### Step Functions Missing Pattern Step

**Symptom**: Precompute workflow doesn't run patterns

**Check**:
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn {arn} \
  --query 'definition' | jq -r '.' | grep -A5 'FanOutToPatternWorkers'
```

**Fix**: Re-apply Terraform to update state machine definition

### Pattern Cache Not Working

**Symptom**: API still slow (patterns computed ad-hoc)

**Check**:
1. Verify `chart_pattern_data` table exists (Migration 020)
2. Verify patterns in table: `SELECT COUNT(*) FROM chart_pattern_data WHERE pattern_date = CURDATE()`
3. Check API logs for "Cache lookup failed" messages

**Fix**: Apply Migration 020, trigger precompute

---

## Related Documentation

- [AUTOMATED_PRECOMPUTE.md](../../docs/deployment/AUTOMATED_PRECOMPUTE.md) - Full precompute architecture
- [CI_CD.md](../../docs/deployment/CI_CD.md) - CI/CD workflows
- [/deploy command](../commands/deploy.md) - Deployment command reference
- [chart_pattern_data spec](../specs/shared/chart_pattern_data.md) - Pattern data specification

---

## Checklist

### Pre-Deployment
- [ ] Code committed and pushed
- [ ] Tests passing
- [ ] Doppler config verified
- [ ] Required migrations applied (especially Migration 020 for patterns)

### Post-Deployment
- [ ] Health check passing
- [ ] No errors in CloudWatch logs
- [ ] Pattern precompute Lambda exists (scheduler deploy)
- [ ] Step Functions includes `FanOutToPatternWorkers`
- [ ] Trigger first precompute after new pattern deploy

---

*Skill: deployment*
*Last updated: 2026-01-15*
