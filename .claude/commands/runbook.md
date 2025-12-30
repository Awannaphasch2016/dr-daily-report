---
name: runbook
description: Generate operational runbooks from execution patterns
accepts_args: true
arg_schema:
  - name: operation_type
    required: true
    description: "Type: deployment, rollback, incident-response, migration, scaling"
  - name: scope
    required: false
    description: "Optional scope: lambda, frontend, database, infrastructure"
composition:
  - skill: research
  - command: reproduce
---

# /runbook - Operational Runbook Generation

**Purpose**: Generate reusable operational procedures from execution patterns and observations

**Category**: Operations & DevOps

**vs `/reproduce`**:
- **`/reproduce`**: Reproduce ONE specific bug/feature from ONE observation file
- **`/runbook`**: Generate REUSABLE procedure from PATTERN of multiple observations

**Core Principle**: "Operations should be documented, repeatable, and tested"

---

## When to Use

**✅ Use /runbook when**:
- Need repeatable operational procedure (run it monthly)
- Multiple execution observations exist (pattern to extract)
- Operations team needs standard process
- Onboarding new ops team members
- Compliance requires documented procedures

**❌ Don't use when**:
- One-time operation (just do it manually)
- No execution pattern exists yet (create observation first)
- Procedure is trivial (1-2 commands)
- Development task, not operations (use /reproduce instead)

---

## Usage

```bash
# Deployment runbooks
/runbook deployment lambda
/runbook deployment frontend
/runbook deployment infrastructure

# Incident response
/runbook incident-response "API timeout"
/runbook incident-response "Database connection pool exhausted"
/runbook incident-response "Lambda cold start latency"

# Rollback procedures
/runbook rollback lambda
/runbook rollback database
/runbook rollback frontend

# Migration procedures
/runbook migration "Aurora schema change"
/runbook migration "Python 3.11 to 3.12"
/runbook migration "DynamoDB single-table design"

# Scaling procedures
/runbook scaling "Handle 10x traffic"
/runbook scaling "Aurora read replica addition"
```

---

## Runbook Types

### 1. Deployment Runbooks
**Pattern**: Build → Test → Deploy → Verify → Monitor

**Sources**:
- `.claude/observations/*/execution-*-deployment.md`
- `.claude/journals/process/deployment-*.md`
- `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`

**Output**: Step-by-step deployment procedure with verification gates

---

### 2. Rollback Runbooks
**Pattern**: Detect Issue → Decide → Revert → Verify → Investigate

**Sources**:
- `.claude/observations/*/failure-*-deployment-*.md`
- `.claude/journals/error/*-rollback-*.md`
- Failed deployment GitHub Actions logs

**Output**: Emergency rollback procedure with decision criteria

---

### 3. Incident Response Runbooks
**Pattern**: Detect → Triage → Mitigate → Root Cause → Fix → Document

**Sources**:
- `.claude/observations/*/failure-*.md`
- `.claude/journals/error/*.md`
- CloudWatch alarms and logs

**Output**: Incident response playbook with escalation paths

---

### 4. Migration Runbooks
**Pattern**: Backup → Test → Apply → Verify → Rollback Plan

**Sources**:
- `.claude/observations/*/execution-*-migration-*.md`
- `.claude/journals/architecture/*-migration-*.md`
- Database migration files (`migrations/*.sql`)

**Output**: Migration procedure with rollback and verification steps

---

### 5. Scaling Runbooks
**Pattern**: Analyze → Plan → Execute → Monitor → Optimize

**Sources**:
- `.claude/observations/*/behavior-*-scaling-*.md`
- CloudWatch metrics (load patterns)
- Performance journals

**Output**: Scaling procedure with capacity planning and monitoring

---

## Output Structure

### Runbook Template

```markdown
# Runbook: {Operation Type} - {Scope}

**Generated**: 2025-12-28
**Last Validated**: {Date from most recent observation}
**Estimated Duration**: {X} minutes
**Runbook Owner**: {Team/Individual}
**Review Frequency**: {Monthly/Quarterly}

---

## Overview

**Purpose**: {One-sentence description of what this runbook does}

**When to use**:
- {Condition 1}
- {Condition 2}
- {Condition 3}

**Dependencies**:
- {Prerequisite 1}
- {Prerequisite 2}

---

## Prerequisites

### Environment
- [ ] Environment: {dev/staging/prod}
- [ ] Branch: {branch name or tag}
- [ ] Permissions: {AWS IAM roles, GitHub access, etc.}

### Pre-Checks
- [ ] Tests passing: `dr test all`
- [ ] No pending deployments (check GitHub Actions)
- [ ] {Scope-specific checks}
- [ ] Stakeholders notified (if production)

### Required Tools
- [ ] AWS CLI v2 configured
- [ ] Terraform CLI installed
- [ ] Doppler configured
- [ ] GitHub CLI (`gh`) installed

### Required Access
- [ ] AWS Console (admin/operator role)
- [ ] GitHub (write access to repository)
- [ ] Doppler (read secrets for environment)

---

## Procedure

### Step 1: {Action Name}

**Purpose**: {Why this step is necessary}

**Command**:
```bash
{exact command from execution observations}
```

**Expected Output**:
```
{what you should see - copy from observation}
```

**Expected Duration**: ~{X} seconds

**Verification**:
```bash
{verification command}
```
**Expected**: {What verification should show}

**If Failed**:
- Check: {Common failure cause 1}
- Check: {Common failure cause 2}
- Fallback: {Alternative approach or skip to rollback}

**CloudWatch Logs**:
```bash
# Monitor this log group during step
aws logs tail /aws/lambda/{function-name} --follow
```

---

### Step 2: {Action Name}

{Repeat structure for each step}

---

[Continue for all steps - typically 5-10 steps]

---

## Verification

**Post-Operation Checks** (run ALL checks before marking complete):

### Check 1: Service Health
**Purpose**: Verify service is responding

```bash
curl https://api.example.com/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.2.3",
  "timestamp": "2025-12-28T10:00:00Z"
}
```

**If Failed**: Check CloudWatch logs for errors, verify Lambda deployment

---

### Check 2: Recent Logs (5 minutes)
**Purpose**: Ensure no errors in recent invocations

```bash
aws logs tail /aws/lambda/report_worker --since 5m
```

**Expected**: No ERROR or CRITICAL level logs

**If Failed**: Investigate error, may need to rollback

---

### Check 3: Smoke Tests
**Purpose**: Verify critical functionality works

```bash
dr test smoke
```

**Expected**: All smoke tests pass (typically 3-5 tests)

**If Failed**: Rollback immediately (critical functionality broken)

---

### Check 4: Metrics Dashboard
**Purpose**: Verify key metrics are healthy

**Navigate to**: CloudWatch Dashboard `dr-daily-report-{env}`

**Check**:
- [ ] Lambda invocation count > 0
- [ ] Lambda error rate < 5%
- [ ] Lambda p99 latency < 10s
- [ ] Aurora connections < 80% of max
- [ ] API Gateway 5xx errors = 0

**If Failed**: Investigate metric anomaly, consider rollback

---

## Rollback Procedure

**When to rollback**:
- Any verification check fails
- Error rate > 5% for 5+ minutes
- Critical functionality broken (smoke tests fail)
- Stakeholder decision (business impact)

**Decision Matrix**:
| Condition | Action |
|-----------|--------|
| Smoke tests fail | Rollback immediately (no discussion) |
| Error rate 5-10% | Rollback (high confidence) |
| Error rate 10-20% | Rollback mandatory |
| Metrics degraded but tests pass | Investigate 10 min, then decide |

---

### Rollback Steps

#### Step 1: Stop New Deployments
```bash
# Cancel any pending GitHub Actions
gh run list --workflow=deploy --status=in_progress
gh run cancel {run-id}
```

**Verification**: No in-progress deployments

---

#### Step 2: Revert to Previous Version
```bash
# Lambda deployment rollback
ENV=prod doppler run -- aws lambda update-function-code \
  --function-name report_worker \
  --image-uri {previous-image-digest}

aws lambda wait function-updated --function-name report_worker
```

**Expected Duration**: ~2-3 minutes

**Verification**: Lambda shows previous version

---

#### Step 3: Verify Rollback
```bash
# Run verification checks again
curl https://api.example.com/health
dr test smoke
```

**Expected**: All checks pass

---

#### Step 4: Notify Stakeholders
```markdown
# Post-mortem template
Subject: Rollback: {Operation} - {Scope}

Deployed: {timestamp}
Rolled back: {timestamp}
Duration: {X} minutes
Reason: {failure reason}

Impact:
- {What was affected}
- {How many users impacted}

Root cause:
- {Initial diagnosis}

Next steps:
- [ ] Full post-mortem (within 24h)
- [ ] Fix identified in {branch/PR}
- [ ] Re-deploy after fix verified
```

**Estimated Rollback Time**: ~{X} minutes (total)

---

## Monitoring

**What to monitor** (first 30 minutes post-deployment):

### CloudWatch Metrics
- **Invocations**: Should match baseline (±20%)
- **Errors**: Should be 0 or < 1% of invocations
- **Duration (p99)**: Should be < 10s (or baseline + 20%)
- **Concurrent Executions**: Should be < 80% of reserved concurrency

### CloudWatch Logs
```bash
# Real-time monitoring
aws logs tail /aws/lambda/report_worker --follow --filter-pattern ERROR
```

**Expected**: No ERROR or CRITICAL level logs
**Alert on**: Any ERROR pattern appearing

### Langfuse Dashboard
- **LLM Quality Scores**: Should maintain baseline (±5%)
- **Token Usage**: Should match baseline (±15%)
- **Latency**: Report generation < 30s (p95)

**Navigate to**: https://langfuse.example.com/projects/dr-daily-report

### API Gateway
```bash
# Check 5xx errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=telegram-api \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum
```

**Expected**: Sum = 0

---

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error Rate | > 5% | > 10% | Rollback |
| Latency p99 | > 10s | > 20s | Investigate |
| 5xx Errors | > 5 in 5min | > 10 in 5min | Rollback |
| Memory Usage | > 80% | > 90% | Scale up |

---

## Troubleshooting

### Issue 1: Lambda Timeout During Deployment

**Symptoms**:
- `Task timed out after 30.00 seconds`
- Deployment hangs at "Waiting for function update"

**Cause**: Lambda function actively processing requests during update

**Solution**:
1. Wait for current invocations to complete (~30s)
2. Re-run deployment command
3. If persists, scale down traffic temporarily

**Prevention**: Deploy during low-traffic window (2-4 AM UTC)

---

### Issue 2: Aurora Connection Pool Exhausted

**Symptoms**:
- `OperationalError: (2013, 'Lost connection to MySQL server')`
- High Aurora connections metric

**Cause**: Lambda concurrent executions exceeded connection pool

**Solution**:
```bash
# Reduce Lambda reserved concurrency temporarily
aws lambda put-function-concurrency \
  --function-name report_worker \
  --reserved-concurrent-executions 50

# Scale Aurora up (increase max_connections)
# Or add RDS Proxy (connection pooling)
```

**Root Cause**: Need RDS Proxy for connection pooling

---

### Issue 3: Docker Image Push Failed

**Symptoms**:
- `denied: Your authorization token has expired`
- ECR push fails in GitHub Actions

**Cause**: AWS ECR login token expired (12 hours)

**Solution**:
```bash
# Re-authenticate with ECR
ENV=prod doppler run -- aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin {account-id}.dkr.ecr.us-east-1.amazonaws.com

# Re-run docker push
docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/telegram-api:latest
```

**Prevention**: GitHub Actions workflow should handle re-auth automatically

---

### Issue 4: Terraform State Lock

**Symptoms**:
- `Error acquiring state lock`
- Terraform apply hangs

**Cause**: Previous terraform apply crashed without releasing DynamoDB lock

**Solution**:
```bash
# Check current lock
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"dr-daily-report/terraform.tfstate"}}'

# Force unlock (use with caution)
terraform force-unlock {lock-id}
```

**Prevention**: Always run `terraform apply` with timeout

---

### Issue 5: CloudFront Cache Not Invalidated

**Symptoms**:
- Frontend shows old version after deployment
- Users report stale data

**Cause**: CloudFront cache TTL not expired, invalidation not triggered

**Solution**:
```bash
# Create invalidation
aws cloudfront create-invalidation \
  --distribution-id {distribution-id} \
  --paths "/*"

# Wait for invalidation to complete (~5-10 min)
aws cloudfront wait invalidation-completed \
  --distribution-id {distribution-id} \
  --id {invalidation-id}
```

**Prevention**: Automate invalidation in deployment script

---

### Issue 6: Secrets Not Available in Lambda

**Symptoms**:
- `KeyError: 'OPENAI_API_KEY'`
- Lambda cannot access Doppler secrets

**Cause**: Doppler service token not configured in Lambda environment

**Solution**:
```bash
# Update Lambda environment with Doppler token
ENV=prod doppler run -- aws lambda update-function-configuration \
  --function-name report_worker \
  --environment "Variables={DOPPLER_TOKEN={token}}"

aws lambda wait function-updated --function-name report_worker
```

**Verification**: Lambda can now access secrets

---

## Related Resources

### Documentation
- [Deployment Guide](../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) - Step-by-step deployment
- [Troubleshooting](../docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Multi-Environment Deployment](../docs/deployment/MULTI_ENV.md) - Dev/staging/prod workflow

### Observations
- Execution observations: `.claude/observations/*/execution-*.md`
- Failure observations: `.claude/observations/*/failure-*.md`

### Journals
- Deployment journals: `.claude/journals/process/deployment-*.md`
- Error journals: `.claude/journals/error/*.md`

### Related Commands
- `/observe execution` - Capture successful execution for runbook source
- `/reproduce {observation}` - Reproduce specific instance (not reusable)
- `/onboard` - Developer onboarding (includes deployment training)

---

## Examples

### Example 1: Deployment Runbook

```bash
/runbook deployment lambda
```

**Output**: `runbooks/2025-12-28-deployment-lambda.md`

**Content**:
- Prerequisites (environment, tools, access)
- 8-step deployment procedure (build → test → deploy → verify → monitor)
- Verification checks (health, logs, smoke tests, metrics)
- Rollback procedure (when and how)
- Monitoring (what to watch, alert thresholds)
- Troubleshooting (6 common issues with solutions)

**Sources analyzed**:
- 12 execution observations from `.claude/observations/*/execution-*-deployed-lambda.md`
- Deployment journals from `.claude/journals/process/deployment-*.md`
- Existing deployment guide from `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`

**Duration**: ~15 minutes (generated runbook)

---

### Example 2: Incident Response Runbook

```bash
/runbook incident-response "API timeout"
```

**Output**: `runbooks/2025-12-28-incident-api-timeout.md`

**Content**:
- Detection (symptoms, metrics, alerts)
- Triage (severity assessment, impact analysis)
- Mitigation (immediate actions to restore service)
- Root cause analysis (investigation steps)
- Fix (permanent solution implementation)
- Post-mortem (documentation and prevention)

**Sources analyzed**:
- 5 failure observations with "API timeout" pattern
- CloudWatch alarm configurations
- Error journals documenting previous incidents

**Duration**: ~20 minutes (generated runbook)

---

### Example 3: Migration Runbook

```bash
/runbook migration "Aurora schema change"
```

**Output**: `runbooks/2025-12-28-migration-aurora-schema.md`

**Content**:
- Pre-migration (backup, testing, validation)
- Migration procedure (reconciliation migration pattern)
- Post-migration (verification, smoke tests)
- Rollback plan (when and how to revert)
- Monitoring (what changed, what to watch)

**Sources analyzed**:
- Database migration files (`migrations/*.sql`)
- Migration journals (`.claude/journals/architecture/*-migration-*.md`)
- Database-migration skill (`.claude/skills/database-migration/`)

**Duration**: ~25 minutes (generated runbook)

---

## Decision Tree: When to Use /runbook vs Related Commands

```
Need operational procedure?
  │
  ├─ YES, one-time operation
  │  → Just do it manually, document in /observe execution
  │
  ├─ YES, repeatable operation
  │  │
  │  ├─ Pattern exists (multiple observations)?
  │  │  ├─ YES → Use /runbook (generates reusable procedure)
  │  │  └─ NO → Use /reproduce (first time, then extract pattern later)
  │  │
  │  └─ Developer task (bug fix, feature)?
  │     ├─ YES → Use /reproduce (specific instance)
  │     └─ NO → Use /runbook (operations task)
  │
  └─ NO, understanding task
     └─ Use /consolidate, /understand, or /explore
```

---

## vs Related Commands

### vs /reproduce
- **`/reproduce`**: Single observation → Specific reproduction guide
- **`/runbook`**: Multiple observations → Reusable operational procedure
- **When to use /reproduce**: One-off bug reproduction, feature implementation
- **When to use /runbook**: Repeating operations, standard procedures

### vs /onboard
- **`/onboard`**: Developer setup and learning
- **`/runbook`**: Operations procedures (deployment, incident response)
- **Overlap**: Both document "how to do X"
- **Difference**: Onboard = learning, Runbook = operations

### vs /observe
- **`/observe`**: Capture what happened (input for runbooks)
- **`/runbook`**: Generate procedure from observations (output)
- **Relationship**: Observations → Runbook generation

---

## Runbook Maintenance

### Review Frequency
- **Critical runbooks** (deployment, incident): Monthly
- **Regular runbooks** (migration, scaling): Quarterly
- **Infrequent runbooks** (annual tasks): Before use

### Update Triggers
- Execution observation reveals outdated step
- Troubleshooting section missing common issue
- Infrastructure changes (new AWS service, tool version)
- Post-mortem identifies runbook gap

### Validation Process
1. Dry-run in dev environment
2. Update with latest observations
3. Verify all commands execute correctly
4. Test rollback procedure
5. Update "Last Validated" date

---

## Success Metrics

**Runbook is successful when**:
- [ ] Operator can execute without external help
- [ ] Verification gates catch failures before impact
- [ ] Rollback procedure is tested and works
- [ ] Troubleshooting section covers 80% of issues
- [ ] Estimated duration ±20% of actual duration
- [ ] No ambiguous steps ("check if it looks good")

---

## Anti-Patterns

### ❌ Runbook for One-Time Operation
```markdown
# Bad
/runbook "Fix typo in README.md"
```
**Why bad**: One-time operation doesn't need runbook
**Better**: Just fix it, document in git commit message

---

### ❌ Runbook Without Observations
```markdown
# Bad
/runbook deployment lambda
{No execution observations exist yet}
```
**Why bad**: No pattern to extract, will be guesswork
**Better**: Create observations first (`/observe execution "deployed Lambda"`)

---

### ❌ Runbook for Development Task
```markdown
# Bad
/runbook "Add new API endpoint"
```
**Why bad**: This is feature development, not operations
**Better**: Use `/reproduce` for implementation guide or just implement

---

### ❌ Overly Detailed Runbook
```markdown
# Bad
{500 steps with every CLI flag explained}
```
**Why bad**: Operator drowns in detail, loses focus
**Better**: 5-10 key steps, link to docs for details

---

## See Also

- `/reproduce` - Reproduce specific bug/feature from observation
- `/observe execution` - Capture successful execution for runbook source
- `/onboard` - Developer onboarding (includes operations training)
- `.claude/skills/deployment/` - Deployment patterns and best practices
- `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md` - Main deployment guide
