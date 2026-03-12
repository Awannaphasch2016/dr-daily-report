# SNS Alert System Acceptance Criteria

**Objective**: CloudWatch alarms monitoring data pipeline and app health with Slack notifications
**Last Updated**: 2026-01-14

---

## Definition of Done

### Phase 1: Email Alerts (Minimum Viable)

#### Functional Requirements
- [ ] `alert_email` variable added to `terraform/variables.tf`
- [ ] SNS email subscription created in `terraform/monitoring.tf`
- [ ] Scheduler error alarm created
- [ ] LINE Bot error alarm created
- [ ] Step Functions failed alarm created
- [ ] Email confirmation link clicked to activate subscription

#### Verification
- [ ] Trigger test alarm → email received within 5 minutes
- [ ] Email contains alarm name and state change reason
- [ ] All 8 alarms (existing + new) have SNS topic as action

```bash
# Verification command
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value ALARM \
  --state-reason "Acceptance test"
# → Check email inbox
```

---

### Phase 2: Slack Integration (Enhanced)

#### Functional Requirements
- [ ] Slack incoming webhook created in workspace
- [ ] `SLACK_WEBHOOK_URL` added to Doppler (dev/stg/prd)
- [ ] Slack alerter Lambda created (for rich formatting)
- [ ] SNS → Lambda → Slack flow working

#### Message Format Requirements
- [ ] Alert includes: Component name (Scheduler, LINE Bot, etc.)
- [ ] Alert includes: Environment (dev/stg/prd)
- [ ] Alert includes: Severity (CRITICAL/HIGH/MEDIUM)
- [ ] Alert includes: Timestamp (Bangkok time)
- [ ] Alert includes: CloudWatch console link

#### Verification
- [ ] Trigger CRITICAL alarm → Slack message in < 5 minutes
- [ ] Slack message is readable and actionable
- [ ] OK notification sent when alarm resolves

---

### Phase 3: Data Freshness Check (Future Enhancement)

#### Functional Requirements
- [ ] Health check Lambda created
- [ ] EventBridge scheduled every 15 minutes
- [ ] Custom CloudWatch metric published
- [ ] Alarm on data staleness (MAX(date) < TODAY - 1)

#### Verification
- [ ] Data staleness detected within 15 minutes
- [ ] Alert distinguishes between "no data" and "stale data"

---

## Performance Requirements

| Metric | Target |
|--------|--------|
| Alert delivery latency | < 5 minutes |
| False positive rate | < 5% |
| Alert acknowledgment time (on-call) | < 30 minutes for CRITICAL |

---

## Quality Requirements

- [ ] Terraform `plan` shows expected changes
- [ ] Terraform `apply` succeeds without errors
- [ ] No orphaned resources after deployment
- [ ] Alarms follow naming convention: `{project}-{component}-{env}`

---

## Operational Requirements

- [ ] Deployed to dev environment
- [ ] SNS subscription confirmed (email link clicked)
- [ ] Test alarm triggered and resolved
- [ ] On-call documentation updated (if applicable)

---

## Acceptance Test Protocol

### Test 1: Scheduler Failure Alert
```bash
# 1. Trigger alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value ALARM \
  --state-reason "Acceptance test - simulated scheduler failure"

# 2. Verify notification (email or Slack)
# 3. Verify message content

# 4. Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value OK \
  --state-reason "Acceptance test complete"

# 5. Verify OK notification
```

### Test 2: Real Failure Detection
```bash
# 1. Intentionally cause Lambda error (e.g., invalid input)
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --payload '{"invalid": "request"}' \
  /tmp/response.json

# 2. Repeat until error threshold reached (5 errors)
# 3. Verify alarm transitions to ALARM
# 4. Verify notification received
```

### Test 3: Alert Resolution
```bash
# 1. After test alarm, verify OK notification sent
# 2. Verify Slack shows "Resolved" or similar
```

---

## Sign-Off Criteria

| Stakeholder | Sign-Off Criteria |
|-------------|-------------------|
| Developer | All terraform applies successfully, tests pass |
| On-Call | Alert is actionable, no false positives in 24h |
| Product | Coverage for all critical paths |

---

## Rollback Plan

If alerts cause issues (e.g., too noisy):
1. Set alarms to INSUFFICIENT_DATA state: `aws cloudwatch disable-alarm-actions`
2. Adjust thresholds in terraform
3. Re-enable: `aws cloudwatch enable-alarm-actions`
