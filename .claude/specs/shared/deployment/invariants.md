# Deployment Invariants

**Objective**: Shared CI/CD pipeline
**Last Updated**: 2026-01-13

---

## Critical Path

```
Code Push → GitHub Actions → Build → Test → Deploy → Verify
```

Every deployment must preserve: **What you test is what you deploy.**

---

## Level 4: Configuration Invariants

### GitHub Secrets
- [ ] `AWS_ACCESS_KEY_ID` set
- [ ] `AWS_SECRET_ACCESS_KEY` set
- [ ] `AWS_REGION` set
- [ ] `DOPPLER_TOKEN` set (for secret injection)
- [ ] Secrets scoped to correct environment

### Doppler Integration
- [ ] CI/CD can fetch secrets from Doppler
- [ ] Secrets injected at build time (for LANGFUSE_RELEASE)
- [ ] Secrets injected at runtime (for Lambda env vars)

### Branch Protection
- [ ] `main` branch protected
- [ ] PRs required for main
- [ ] CI must pass before merge

### Verification
```bash
# Check GitHub secrets (via UI or gh CLI)
gh secret list

# Verify Doppler access
doppler secrets --config ci
```

---

## Level 3: Infrastructure Invariants

### ECR Repository
- [ ] Repository exists
- [ ] Push permissions configured
- [ ] Lifecycle policy for old images
- [ ] Image scanning enabled

### Lambda Functions
- [ ] Functions exist in all environments
- [ ] VPC configured correctly
- [ ] IAM roles have required permissions
- [ ] Environment variables set

### S3 (Frontend)
- [ ] Bucket exists
- [ ] Static website hosting configured
- [ ] CloudFront invalidation works
- [ ] CORS configured

### Verification
```bash
# Check ECR
aws ecr describe-repositories --repository-names dr-daily-report

# Check Lambda
aws lambda get-function --function-name dr-telegram-api-{env}

# Check S3
aws s3 ls s3://dr-telegram-frontend-{env}/
```

---

## Level 2: Data Invariants

### Docker Image
- [ ] Single image built once
- [ ] Image digest tracked (not just tag)
- [ ] Same digest promoted through environments
- [ ] No rebuilding between environments

### Image Tags
- [ ] Format: `{env}-{sha}`
- [ ] SHA matches git commit
- [ ] Tag is immutable (no overwriting)

### Build Artifacts
- [ ] Frontend bundle versioned
- [ ] Source maps stored (but not exposed in prd)
- [ ] Build metadata captured

### Verification
```bash
# Check image digest consistency
aws ecr describe-images --repository-name dr-daily-report \
  --image-ids imageTag={env}-{sha} --query "imageDetails[0].imageDigest"
```

---

## Level 1: Service Invariants

### Build Stage
- [ ] Docker build succeeds
- [ ] All dependencies installed
- [ ] No security vulnerabilities (critical)
- [ ] Build < 5 minutes

### Test Stage
- [ ] Unit tests pass (100%)
- [ ] Integration tests pass
- [ ] Type check passes
- [ ] Lint passes

### Deploy Stage
- [ ] Use `aws lambda wait function-updated`
- [ ] Never use `sleep X`
- [ ] Rollback on failure
- [ ] Deployment < 5 minutes

### Verify Stage
- [ ] Health check returns 200
- [ ] CloudWatch logs show activity
- [ ] No errors in first 5 minutes
- [ ] Langfuse traces appearing

### Smoke Test
- [ ] Call health endpoint
- [ ] Call one real endpoint
- [ ] Verify response structure
- [ ] Check for import errors

### Verification
```bash
# Check workflow status
gh run list --workflow=deploy.yml

# Watch deployment
gh run watch --exit-status
```

---

## Level 0: User Invariants

### Deployment Experience
- [ ] Deployments are automated
- [ ] Status visible in GitHub Actions
- [ ] Notifications on failure
- [ ] Easy rollback process

### Service Continuity
- [ ] Zero downtime deployments
- [ ] Users not affected during deploy
- [ ] Instant rollback if needed

### Verification
```bash
# Monitor during deployment:
# 1. Check GitHub Actions UI
# 2. Watch CloudWatch logs
# 3. Test endpoint during deploy
# 4. Verify no errors
```

---

## Environment-Specific

### dev
```yaml
triggers:
  - push to dev branch

relaxations:
  - Fast feedback over thorough testing
  - Can skip some integration tests
  - Debug artifacts allowed
```

### stg
```yaml
triggers:
  - push to main branch

requirements:
  - All tests must pass
  - Production-like testing
  - Performance benchmarks
```

### prd
```yaml
triggers:
  - push v*.*.* tag

requirements:
  - All stg requirements
  - Manual approval (optional)
  - Extended smoke tests
  - Monitoring alert verification
```

---

## Rollback Triggers

Rollback immediately if:
- [ ] Import errors in Lambda logs
- [ ] Health endpoint returns non-200
- [ ] > 5% error rate in first 5 minutes
- [ ] Only START/END logs (no application logs)

### Rollback Process
1. Identify last known-good image digest
2. Update Lambda to use previous image
3. Wait for function update
4. Verify health check passes
5. Document incident

```bash
# Rollback command
aws lambda update-function-code \
  --function-name dr-telegram-api-{env} \
  --image-uri {ecr-uri}@{previous-digest}

aws lambda wait function-updated \
  --function-name dr-telegram-api-{env}
```

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Using `sleep 30` | Use `aws lambda wait` |
| Rebuilding for each env | Build once, promote digest |
| Skipping smoke tests | Always run post-deploy checks |
| No rollback plan | Document rollback before deploy |
| Manual deployments | Automate via GitHub Actions |

---

## Claiming "Deployment Work Done"

```markdown
## Deployment complete: {description}

**Environment**: {dev | stg | prd}
**Commit**: {SHA}
**Image Digest**: {sha256:...}

**Invariants Verified**:
- [x] Level 4: Secrets configured, branch protection
- [x] Level 3: ECR/Lambda/S3 exist and accessible
- [x] Level 2: Same image promoted, digest tracked
- [x] Level 1: Build/Test/Deploy/Verify all passed
- [x] Level 0: Service available, zero downtime

**Evidence**:
- GitHub Actions: {run URL}
- CloudWatch: {log group query}
- Health check: {response}

**Convergence**: delta = 0
```

---

*Objective: shared/deployment*
*Spec: .claude/specs/shared/deployment/spec.yaml*
