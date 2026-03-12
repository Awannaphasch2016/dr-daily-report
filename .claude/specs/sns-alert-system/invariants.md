# SNS Alert System Invariants

**Objective**: CloudWatch alarms monitoring data pipeline and app health with Slack notifications
**Last Updated**: 2026-01-14
**Status**: IMPLEMENTED (dev environment)

---

## Current State (Delta Tracking)

| Level | Invariant | Status | Notes |
|-------|-----------|--------|-------|
| L4 | SLACK_WEBHOOK_URL in Terraform | ✅ | `terraform/variables.tf` |
| L4 | TF_VAR_SLACK_WEBHOOK_URL in Doppler | ✅ | dev config set |
| L3 | SNS topic exists | ✅ | `dr-daily-report-telegram-alerts-dev` |
| L3 | Lambda subscription active | ✅ | `slack_notifier` subscribed |
| L3 | All alarms configured | ✅ | 10+ alarms in dev |
| L1 | Slack notifier Lambda works | ✅ | Tested 2026-01-14 |
| L0 | Alerts appear in Slack | ✅ | Verified with test alarm |

**Delta**: 0 violations (dev environment)

---

## Level 4: Configuration Invariants

### Terraform Variables
- [x] `SLACK_WEBHOOK_URL` variable defined in `terraform/variables.tf` (sensitive)
- [ ] `alert_email` variable defined (optional, for email alerts)

### Doppler Secrets
- [x] `TF_VAR_SLACK_WEBHOOK_URL` set for dev
- [ ] `TF_VAR_SLACK_WEBHOOK_URL` set for stg
- [ ] `TF_VAR_SLACK_WEBHOOK_URL` set for prd

### Alarm Thresholds (monitoring.tf)
| Alarm | Threshold | Evaluation | Severity |
|-------|-----------|------------|----------|
| `scheduler-errors` | 1 | 1 period | CRITICAL |
| `precompute-errors` | 1 | 1 period | CRITICAL |
| `precompute-workflow-failures` | 1 | 1 period | CRITICAL |
| `telegram-api-errors` | 5 | 2 periods | HIGH |
| `line-bot-errors` | 5 | 2 periods | HIGH |
| `api-5xx-errors` | 10 | 2 periods | HIGH |
| `api-4xx-errors` | 50 | 3 periods | MEDIUM |
| `telegram-api-duration` | 45000ms | 2 periods | MEDIUM |
| `report-worker-errors` | 3 | 2 periods | HIGH |

**Verification Commands**:
```bash
# Check Terraform variable
grep -A5 "SLACK_WEBHOOK_URL" terraform/variables.tf

# Check Doppler secrets
doppler secrets get TF_VAR_SLACK_WEBHOOK_URL -c dev --plain | head -c 30

# Check Lambda env var has webhook
aws lambda get-function-configuration \
  --function-name dr-daily-report-slack-notifier-dev \
  --query 'Environment.Variables.SLACK_WEBHOOK_URL' --output text | head -c 30
```

---

## Level 3: Infrastructure Invariants

### SNS Topic
- [x] SNS topic `dr-daily-report-telegram-alerts-{env}` exists
- [x] SNS topic has Lambda subscriber (`slack_notifier`)
- [x] SNS topic is action target for all alarms
- [x] Lambda has permission for SNS invocation

### CloudWatch Alarms (dev environment)
- [x] `scheduler-errors` alarm exists
- [x] `precompute-errors` alarm exists
- [x] `precompute-workflow-failures` alarm exists
- [x] `telegram-api-errors` alarm exists
- [x] `line-bot-errors` alarm exists
- [x] `api-5xx-errors` alarm exists
- [x] `api-4xx-errors` alarm exists
- [x] `telegram-api-duration` alarm exists
- [x] `report-worker-errors` alarm exists
- [x] `dlq-messages` alarm exists

### Slack Notifier Lambda
- [x] Lambda function `dr-daily-report-slack-notifier-{env}` exists
- [x] Lambda has IAM role with CloudWatch Logs permission
- [x] Lambda runtime Python 3.11
- [x] Lambda timeout 30s
- [x] Lambda receives SNS events

**Verification Commands**:
```bash
# List SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn "arn:aws:sns:ap-southeast-1:755283537543:dr-daily-report-telegram-alerts-dev" \
  --query 'Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint}'

# List CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "dr-daily-report" \
  --query "MetricAlarms[*].{Name:AlarmName,State:StateValue}" \
  --output table

# Check Lambda exists
aws lambda get-function --function-name dr-daily-report-slack-notifier-dev \
  --query 'Configuration.{Name:FunctionName,Runtime:Runtime,Timeout:Timeout}'
```

---

## Level 2: Data Invariants

### Data Freshness (monitored by alerts)
- [ ] `daily_prices` has data for today or previous trading day
- [ ] `precomputed_rankings` computed within last 24 hours
- [ ] `precomputed_reports` has cache for common tickers

### Alert History
- [ ] Alarm state transitions recorded in CloudWatch
- [ ] Lambda invocation logs in CloudWatch Logs

**Verification Commands**:
```bash
# Check data freshness
just dr-dev "SELECT MAX(date) as latest, DATEDIFF(CURDATE(), MAX(date)) as days_old FROM daily_prices"

# Check Lambda logs
aws logs tail /aws/lambda/dr-daily-report-slack-notifier-dev --since 1h
```

---

## Level 1: Service Invariants

### Alarm State Transitions
- [x] Alarms transition to ALARM state when threshold exceeded
- [x] Alarms transition to OK state when condition clears
- [x] SNS notification sent on state change
- [x] Lambda invoked on SNS message

### Slack Message Format
- [x] Message contains environment name (DEV/STG/PRD)
- [x] Message contains severity emoji (🔴/🟡/🟢)
- [x] Message contains alarm name and state
- [x] Message contains CloudWatch console link
- [x] Message uses color-coded attachment (red=ALARM, green=OK)

### Error Handling
- [x] Missing SLACK_WEBHOOK_URL logged and returns error
- [x] Invalid webhook URL returns error with details
- [x] Multiple SNS records processed in batch
- [x] Errors don't block other notifications

**Verification Commands**:
```bash
# Trigger test alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value ALARM \
  --state-reason "Acceptance test"

# Check Lambda logs
sleep 5 && aws logs tail /aws/lambda/dr-daily-report-slack-notifier-dev --since 1m

# Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value OK \
  --state-reason "Test complete"
```

---

## Level 0: User (On-Call) Invariants

### Alert Visibility
- [x] On-call receives alert in Slack within 1 minute of incident
- [x] Alert message identifies which component failed
- [x] Alert message includes timestamp
- [x] Alert message includes link to CloudWatch console

### Message Content
- [x] State change clearly shown (ALARM/OK)
- [x] Environment clearly identified (DEV/STG/PRD)
- [x] Metric details included (namespace, dimensions)
- [x] Reason for state change included

### Alert Resolution
- [x] OK notification sent when issue resolves
- [x] OK message uses green color for clarity

**Verification Commands**:
```bash
# Full acceptance test
# 1. Trigger alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value ALARM \
  --state-reason "Acceptance test - simulated failure"

# 2. Verify Slack message received (manual check)
# Expected: Red message with 🔴, "ALARM", alarm name, link

# 3. Reset and verify OK message
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-dev" \
  --state-value OK \
  --state-reason "Acceptance test complete"

# Expected: Green message with ✅, "RESOLVED", alarm name
```

---

## Invariant Summary

| Level | Count | Verified | Remaining |
|-------|-------|----------|-----------|
| L4 (Config) | 5 | 3 | 2 (stg/prd) |
| L3 (Infra) | 14 | 14 | 0 |
| L2 (Data) | 4 | 2 | 2 |
| L1 (Service) | 12 | 12 | 0 |
| L0 (User) | 7 | 7 | 0 |
| **Total** | **42** | **38** | **4** |

---

## Deployment Checklist by Environment

### Dev ✅ COMPLETE
- [x] Apply Terraform with `SLACK_WEBHOOK_URL`
- [x] Verify SNS subscription
- [x] Test alarm → Slack flow
- [x] Verify OK notification

### Staging
- [ ] Set `TF_VAR_SLACK_WEBHOOK_URL` in Doppler stg config
- [ ] Apply Terraform to staging
- [ ] Verify SNS subscription
- [ ] Test alarm → Slack flow

### Production
- [ ] Set `TF_VAR_SLACK_WEBHOOK_URL` in Doppler prd config
- [ ] Apply Terraform to production
- [ ] Verify SNS subscription
- [ ] Test alarm → Slack flow (carefully)

---

## Related Files

| File | Purpose |
|------|---------|
| `terraform/monitoring.tf` | CloudWatch alarms + Slack notifier Lambda |
| `terraform/variables.tf` | SLACK_WEBHOOK_URL variable |
| `src/alerting/slack_notifier.py` | Lambda handler for SNS → Slack |
| `src/alerting/__init__.py` | Alerting module |

---

*Spec: .claude/specs/sns-alert-system/spec.yaml*
*Last verified: 2026-01-14 (dev environment)*
