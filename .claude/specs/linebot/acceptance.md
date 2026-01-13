# LINE Bot Acceptance Criteria

**Objective**: Chat-based financial reports via LINE
**Last Updated**: 2026-01-13

---

## What is Acceptance?

Acceptance criteria define **when work is "done"**. They are the conditions that must be met before claiming completion of any LINE Bot feature or fix.

---

## Feature: Generate Report (`/report {TICKER}`)

### Acceptance Criteria

#### Functional
- [ ] User sends `/report ADVANC` → receives PDF or text report
- [ ] Report contains 5 sections: market, portfolio, news, sentiment, recommendation
- [ ] Prices reflect most recent market close
- [ ] Invalid ticker returns "Ticker not found" with suggestions

#### Performance
- [ ] Response time < 30 seconds (LINE webhook SLA)
- [ ] PDF generation < 10 seconds
- [ ] No timeout errors in CloudWatch logs

#### Observability
- [ ] Langfuse trace created with `generate_report` span
- [ ] Quality scores attached (faithfulness, completeness, reasoning_quality)
- [ ] Error cases logged with full context

#### Verification Commands
```bash
# Functional
aws lambda invoke --function-name dr-line-bot-{env} \
  --payload '{"type": "message", "message": {"text": "/report ADVANC"}}' response.json
cat response.json | jq '.statusCode'  # Should be 200

# Performance
aws logs tail /aws/lambda/dr-line-bot-{env} --since 5m | grep "duration"

# Observability
# Check Langfuse dashboard for trace
```

---

## Feature: View Watchlist (`/watchlist`)

### Acceptance Criteria

#### Functional
- [ ] User sends `/watchlist` → receives portfolio summary
- [ ] Summary shows all tracked tickers with current prices
- [ ] Prices are from today's market data

#### Performance
- [ ] Response time < 5 seconds

#### Verification
```bash
# Send test message
aws lambda invoke --function-name dr-line-bot-{env} \
  --payload '{"type": "message", "message": {"text": "/watchlist"}}' response.json
```

---

## Feature: Help Commands (`/start`, `/help`)

### Acceptance Criteria

#### Functional
- [ ] `/start` returns welcome message with command list
- [ ] `/help` returns detailed command reference
- [ ] Unknown commands return help message

#### Performance
- [ ] Response time < 2 seconds

---

## Deployment Acceptance

Before any LINE Bot deployment is considered "done":

### Pre-Deployment
- [ ] All unit tests pass (`just test-unit`)
- [ ] Integration tests pass (`just test-integration`)
- [ ] Docker image builds successfully
- [ ] No new security vulnerabilities (dependency scan)

### Post-Deployment
- [ ] Smoke test passes (send `/start` to bot)
- [ ] CloudWatch logs show successful invocations
- [ ] No errors in first 5 minutes of operation
- [ ] Langfuse traces appearing for new deployments

### Rollback Criteria
Rollback immediately if:
- [ ] Import errors in Lambda logs
- [ ] >5% error rate in first 5 minutes
- [ ] Webhook returns non-200 to LINE
- [ ] No application logs (only START/END)

---

## Environment-Specific Acceptance

### dev
- [ ] Can be tested with `MOCK_LINE=true`
- [ ] Aurora connectivity verified
- [ ] Langfuse traces visible in dev environment

### stg
- [ ] Real LINE API integration works
- [ ] Test channel receives messages
- [ ] Full report generation completes
- [ ] Performance within SLA

### prd
- [ ] Production LINE channel configured
- [ ] All stg acceptance criteria pass
- [ ] Monitoring alerts configured
- [ ] On-call notification working

---

## Claiming "Done"

Use this template when completing LINE Bot work:

```markdown
## LINE Bot Work Complete: {description}

**Environment**: {dev | stg | prd}

### Acceptance Verified
- [x] Functional: {specific criteria checked}
- [x] Performance: {response time observed}
- [x] Observability: {trace/log evidence}

### Invariant Convergence
- [x] Level 4 (Config): All env vars set
- [x] Level 3 (Infra): Connectivity verified
- [x] Level 2 (Data): Data fresh
- [x] Level 1 (Service): API contracts met
- [x] Level 0 (User): End-to-end working

### Evidence
- CloudWatch logs: {link or query}
- Langfuse trace: {trace ID}
- Test result: {screenshot or response}

**Convergence**: delta = 0 (all invariants satisfied)
```

---

*Objective: linebot*
*Spec: .claude/specs/linebot/spec.yaml*
