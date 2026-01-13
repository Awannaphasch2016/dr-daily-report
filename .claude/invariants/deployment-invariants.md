# Deployment Invariants

**Domain**: Deployment, CI/CD, Release Management
**Load when**: deploy, release, ship, promote, rollback

**Related**: [Deployment Skill](../skills/deployment/), [Principle #6](../principles/deployment-principles.md), [Principle #11](../principles/deployment-principles.md)

---

## Critical Path

```
Code Change → Build → Test → Deploy → Verify → User Traffic
```

Every deployment must preserve this invariant: **What works before deployment must work after deployment.**

---

## Level 4: Configuration Invariants

### Environment Variables
- [ ] New env vars added to Doppler (ALL environments: local, dev, stg, prd)
- [ ] Existing env vars unchanged (no accidental removal)
- [ ] LANGFUSE_RELEASE updated with deployment version
- [ ] TZ = "Asia/Bangkok" still set

### Terraform
- [ ] New Lambda env vars in terraform/*.tf
- [ ] Resource tags correct (App = line-bot | telegram-api | shared)
- [ ] Memory/timeout settings appropriate

### Secrets
- [ ] No secrets committed to code
- [ ] GitHub secrets configured (if new)
- [ ] Doppler secrets not duplicated

### Verification Commands
```bash
# Check Doppler config
doppler secrets -p dr-daily-report -c dev | grep NEW_VAR

# Check Terraform
grep "NEW_VAR" terraform/*.tf

# Verify no secrets in code
git diff HEAD~1 | grep -i "secret\|password\|key" || echo "Clean"
```

---

## Level 3: Infrastructure Invariants

### Lambda Deployment
- [ ] Lambda function updated (not just created)
- [ ] Image digest matches ECR (artifact promotion)
- [ ] Concurrency limits appropriate
- [ ] VPC configuration unchanged (unless intentional)

### Connectivity
- [ ] Lambda → Aurora connectivity works
- [ ] Lambda → S3 connectivity works
- [ ] Lambda → External APIs (timeout configured)
- [ ] VPC endpoints still configured

### IAM
- [ ] Execution role has required permissions
- [ ] No overly permissive policies added
- [ ] Cross-account access unchanged

### Verification Commands
```bash
# Check Lambda status
aws lambda get-function --function-name dr-daily-report-telegram-api-dev

# Test Aurora connectivity
/dev "SELECT 1"

# Test S3 connectivity
/dev "list S3 buckets"
```

---

## Level 2: Data Invariants

### Schema
- [ ] Database schema matches code expectations
- [ ] Migrations applied before code deployment
- [ ] No data corruption from migration
- [ ] Rollback path documented and tested

### Data Integrity
- [ ] Foreign keys valid
- [ ] No orphaned records
- [ ] Timestamps in Bangkok timezone
- [ ] JSON columns valid

### Cache
- [ ] Cache invalidated (if cached data changed)
- [ ] Cache TTL appropriate
- [ ] No stale data served

### Verification Commands
```bash
# Check schema
/dev "DESCRIBE daily_prices"

# Check data integrity
/dev "SELECT COUNT(*) FROM daily_prices WHERE date = CURDATE()"

# Verify no orphans
/dev "SELECT COUNT(*) FROM precomputed_reports r
      LEFT JOIN ticker_master t ON r.symbol = t.symbol
      WHERE t.symbol IS NULL"
```

---

## Level 1: Service Invariants

### Health
- [ ] Lambda health check returns 200
- [ ] No startup errors (check first invocation logs)
- [ ] Cold start time acceptable (< 3s)
- [ ] Warm response time acceptable (< 500ms)

### Behavior
- [ ] API contracts unchanged (unless versioned)
- [ ] Error responses follow standard format
- [ ] Logging produces expected output
- [ ] No 5xx errors in first 5 minutes

### Monitoring
- [ ] CloudWatch logs flowing
- [ ] Metrics being recorded
- [ ] Alerts not firing

### Verification Commands
```bash
# Health check
/dev "invoke telegram-api health check"

# Check logs
aws logs tail /aws/lambda/dr-daily-report-telegram-api-dev --since 5m

# Check errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '5 minutes ago' +%s000)
```

---

## Level 0: User Invariants

### Telegram Bot
- [ ] /start returns welcome message
- [ ] /report TICKER returns PDF within 30s
- [ ] /watchlist returns portfolio summary
- [ ] Invalid commands return helpful error

### Frontend (Mini App)
- [ ] Dashboard loads without error
- [ ] Charts display with current data
- [ ] Ticker selection works
- [ ] Export functionality works

### End-to-End
- [ ] Complete user flow works
- [ ] Response time acceptable
- [ ] Error messages helpful

### Verification Commands
```bash
# Manual test via Telegram
# Send: /report ADVANC
# Expect: PDF within 30s

# Or use E2E test
pytest tests/e2e/test_telegram_flow.py -v
```

---

## Rollback Invariants

When rolling back, verify:

- [ ] Previous artifact identified (commit SHA, image digest)
- [ ] Rollback deployment succeeded
- [ ] All Level 1-4 invariants restored
- [ ] User-facing functionality restored
- [ ] Incident documented

### Rollback Commands
```bash
# Identify previous version
git log --oneline -5

# Rollback Lambda
aws lambda update-function-code \
  --function-name dr-daily-report-telegram-api-dev \
  --image-uri <previous-image-digest>

# Wait for update
aws lambda wait function-updated \
  --function-name dr-daily-report-telegram-api-dev

# Verify rollback
/dev "invoke health check"
```

---

## Anti-Patterns (What Breaks Invariants)

| Anti-Pattern | Invariant Violated | Fix |
|--------------|-------------------|-----|
| Deploy without migration | Level 2 (schema mismatch) | Always migrate BEFORE deploy |
| Missing env var | Level 4 (config) | Validate at startup |
| Force push to main | Level 3 (artifact) | Use PR workflow |
| Skip smoke test | Level 1 (service) | Always run post-deploy test |
| Deploy Friday 5pm | Level 0 (user) | Deploy early in week |

---

## Claiming "Deployment Done"

```markdown
✅ Deployment complete: {version}

**Environment**: {dev | stg | prd}
**Commit**: {SHA}
**Image**: {digest}

**Invariants Verified**:
- [x] Level 4: Doppler updated, Terraform applied
- [x] Level 3: Lambda deployed, connectivity confirmed
- [x] Level 2: Migration applied, data intact
- [x] Level 1: Health check passes, no errors
- [x] Level 0: User flow works

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {CloudWatch logs, Langfuse traces, manual test}
```

---

*Domain: deployment*
*Last updated: 2026-01-12*
