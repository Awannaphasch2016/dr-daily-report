# LINE Bot Invariants

**Objective**: Chat-based financial reports via LINE
**Last Updated**: 2026-01-13

---

## Critical Path

```
LINE Message → Webhook → Lambda → Aurora → Report → LINE Reply
```

Every LINE Bot operation must preserve: **User sends command → User receives response within SLA.**

---

## Level 4: Configuration Invariants

### Credentials (Doppler)
- [ ] `LINE_CHANNEL_SECRET` set (webhook signature verification)
- [ ] `LINE_CHANNEL_ACCESS_TOKEN` set (reply API)
- [ ] Credentials are environment-isolated (dev ≠ stg ≠ prd)

### Backend Configuration
- [ ] `AURORA_HOST` set and correct for environment
- [ ] `TZ=Asia/Bangkok` set (report dates)
- [ ] `LANGFUSE_RELEASE` set (observability versioning)

### Lambda Configuration
- [ ] Timeout ≥ 30s (LINE webhook allows 20s, need buffer)
- [ ] Memory ≥ 512MB (PDF generation)
- [ ] VPC configured (Aurora access)

### Environment Overrides
| Invariant | dev | stg | prd |
|-----------|-----|-----|-----|
| `MOCK_LINE` allowed | ✅ | ❌ | ❌ |
| Test channel | ✅ | ✅ | ❌ |
| Debug logging | ✅ | ✅ | ❌ |

### Verification
```bash
doppler secrets get LINE_CHANNEL_SECRET -p dr-daily-report -c {env}
doppler secrets get LINE_CHANNEL_ACCESS_TOKEN -p dr-daily-report -c {env}
aws lambda get-function --function-name dr-line-bot-{env} --query "Configuration.Timeout"
```

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] Lambda → Aurora: VPC endpoint or NAT Gateway
- [ ] Lambda → LINE API: NAT Gateway (external HTTPS)
- [ ] Lambda → S3: VPC endpoint or NAT Gateway (PDF storage)
- [ ] Lambda → Langfuse: NAT Gateway (external HTTPS)

### Permissions
- [ ] Lambda execution role has Aurora access
- [ ] Lambda can invoke S3 for PDF storage
- [ ] Lambda can publish to CloudWatch Logs

### Network
- [ ] Security groups allow Aurora port (3306)
- [ ] NAT Gateway has capacity for LINE API calls
- [ ] No firewall blocking LINE API domains

### Verification
```bash
# Test Lambda → Aurora
aws lambda invoke --function-name dr-line-bot-{env} \
  --payload '{"test": "aurora_connectivity"}' response.json

# Check VPC configuration
aws lambda get-function --function-name dr-line-bot-{env} \
  --query "Configuration.VpcConfig"
```

---

## Level 2: Data Invariants

### Aurora Data
- [ ] `daily_prices` has data for today (46 tickers)
- [ ] `ticker_master` has all tracked tickers
- [ ] Precomputed data < 24h stale
- [ ] All foreign keys valid

### Report Data
- [ ] Report contains 5 sections (market, portfolio, news, sentiment, recommendation)
- [ ] Price data reflects market close
- [ ] Dates in Bangkok timezone

### PDF Storage
- [ ] PDFs stored in S3 with correct prefix
- [ ] PDF URLs are accessible (signed or public)
- [ ] Old PDFs cleaned up (lifecycle policy)

### Verification
```bash
# Check data freshness
/dev "SELECT MAX(date) FROM daily_prices"

# Check ticker count
/dev "SELECT COUNT(*) FROM ticker_master"
```

---

## Level 1: Service Invariants

### Webhook Handler
- [ ] Signature verification works (LINE_CHANNEL_SECRET)
- [ ] Returns 200 within 20s (LINE timeout)
- [ ] Handles malformed requests gracefully
- [ ] Logs all incoming events

### Report Generation
- [ ] Generates report for valid ticker
- [ ] Returns helpful error for invalid ticker
- [ ] PDF generation completes < 10s
- [ ] Langfuse trace created for each report

### Reply API
- [ ] Can send text messages
- [ ] Can send PDF as document
- [ ] Handles LINE API errors gracefully
- [ ] Retries on transient failures

### Error Handling
- [ ] Invalid commands return help message
- [ ] Missing data returns informative error
- [ ] Internal errors don't expose stack traces
- [ ] All errors logged to CloudWatch

### Verification
```bash
# Invoke Lambda with test event
aws lambda invoke --function-name dr-line-bot-{env} \
  --payload file://test-events/line-webhook.json response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/dr-line-bot-{env} --since 5m
```

---

## Level 0: User Invariants

### Core Commands
- [ ] `/start` returns welcome message with command list
- [ ] `/report TICKER` returns PDF or text report
- [ ] `/watchlist` returns portfolio summary
- [ ] `/help` returns command reference

### Response Quality
- [ ] Reports are accurate (prices match market data)
- [ ] Reports are readable (clear formatting)
- [ ] Response time < 30s for report
- [ ] Response time < 5s for simple commands

### Error Experience
- [ ] Invalid ticker returns "Ticker not found" with suggestions
- [ ] Network errors return "Please try again"
- [ ] Overload returns "System busy, try later"

### Verification
```bash
# Manual testing (required for Level 0):
# 1. Open LINE app
# 2. Message bot: /start
# 3. Message bot: /report ADVANC
# 4. Verify PDF received or text report displayed
# 5. Message bot: /watchlist
# 6. Message bot: invalid-command
# 7. Verify error handling
```

---

## Environment-Specific Overrides

### local
```yaml
relaxations:
  - MOCK_LINE=true allowed (bypass LINE API)
  - Mock data allowed
  - No SLA requirements
  - Debug logging: enabled
  - Source maps: exposed
```

### dev (AWS)
```yaml
requirements:
  - Real LINE API (test channel)
  - Real Aurora connectivity
  - NO MOCKS (mocks only in local)
relaxations:
  - Stale data tolerance: 24h
  - Response time SLA: best effort
  - Debug logging: enabled
```

### stg (AWS)
```yaml
requirements:
  - Real LINE API (test channel)
  - Real Aurora connectivity
  - NO MOCKS
  - Performance monitored
relaxations:
  - Stale data tolerance: 24h
  - SLAs monitored but not enforced
  - Debug logging: enabled
```

### prd (AWS)
```yaml
requirements:
  - Production LINE channel ONLY
  - Real Aurora (Multi-AZ)
  - NO MOCKS (zero tolerance)
  - SLAs ENFORCED:
    - Webhook < 20s
    - Report < 30s
    - Error rate < 1%
  - Debug logging: disabled
```

---

## Claiming "LINE Bot Work Done"

```markdown
✅ LINE Bot work complete: {description}

**Environment**: {dev | stg | prd}

**Invariants Verified**:
- [x] Level 4: Credentials set, Lambda configured
- [x] Level 3: Aurora connectivity, LINE API reachable
- [x] Level 2: Data fresh, report data complete
- [x] Level 1: Webhook responds, report generates, reply sent
- [x] Level 0: User receives correct response

**Convergence**: δ = 0 (all invariants satisfied)
**Evidence**: {CloudWatch logs, LINE message screenshot, Langfuse trace}
```

---

*Objective: linebot*
*Spec: .claude/specs/linebot/spec.yaml*
