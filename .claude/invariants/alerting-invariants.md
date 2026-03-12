# Alerting System Invariants

**Domain**: CloudWatch Alarms → SNS → Slack notification pipeline
**Last Updated**: 2026-01-14
**Status**: Implemented (dev), Pending (stg/prd)

---

## Critical Path

```
CloudWatch Alarm → SNS Topic → Lambda (slack_notifier) → Slack Webhook → Slack Channel
```

Every alert must preserve: **Alarm fires → On-call receives notification within 1 minute.**

---

## Level 4: Configuration Invariants

### Terraform Variables
- [ ] `SLACK_WEBHOOK_URL` variable defined in `terraform/variables.tf` (sensitive)
- [ ] `TF_VAR_SLACK_WEBHOOK_URL` set in Doppler for each environment

### Lambda Environment
- [ ] `SLACK_WEBHOOK_URL` env var set in Lambda
- [ ] `ENVIRONMENT` env var set (dev/staging/prod)

### Alarm Thresholds
| Alarm | Metric | Threshold | Evaluation |
|-------|--------|-----------|------------|
| scheduler-errors | Errors | 1 | 1 period |
| precompute-errors | Errors | 1 | 1 period |
| precompute-workflow-failures | ExecutionsFailed | 1 | 1 period |
| telegram-api-errors | Errors | 5 | 2 periods |
| line-bot-errors | Errors | 5 | 2 periods |
| api-5xx-errors | 5xx | 10 | 2 periods |
| api-4xx-errors | 4xx | 50 | 3 periods |
| telegram-api-duration | Duration | 45000ms | 2 periods |
| report-worker-errors | Errors | 3 | 2 periods |

### Verification
```bash
# Check Terraform variable
grep -A5 "SLACK_WEBHOOK_URL" terraform/variables.tf

# Check Doppler secrets
doppler secrets get TF_VAR_SLACK_WEBHOOK_URL -c {env} --plain | head -c 30

# Check Lambda env var
aws lambda get-function-configuration \
  --function-name dr-daily-report-slack-notifier-{env} \
  --query 'Environment.Variables.SLACK_WEBHOOK_URL' --output text | head -c 30
```

---

## Level 3: Infrastructure Invariants

### SNS Topic
- [ ] SNS topic `dr-daily-report-telegram-alerts-{env}` exists
- [ ] Lambda has subscription to SNS topic
- [ ] All CloudWatch alarms have SNS as action target
- [ ] Lambda permission allows SNS invocation

### Lambda Function
- [ ] `dr-daily-report-slack-notifier-{env}` exists
- [ ] Runtime: Python 3.11
- [ ] Timeout: 30s
- [ ] Memory: 128MB
- [ ] IAM role has CloudWatch Logs permission

### CloudWatch Alarms
- [ ] All alarms exist with correct namespaces
- [ ] All alarms have SNS topic as alarm_action
- [ ] All alarms have SNS topic as ok_action (except 4xx)

### Verification
```bash
# List SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn "arn:aws:sns:ap-southeast-1:755283537543:dr-daily-report-telegram-alerts-{env}" \
  --query 'Subscriptions[*].{Protocol:Protocol,Endpoint:Endpoint}'

# List CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "dr-daily-report" \
  --query "MetricAlarms[*].{Name:AlarmName,State:StateValue}" \
  --output table

# Check Lambda exists
aws lambda get-function --function-name dr-daily-report-slack-notifier-{env}
```

---

## Level 2: Data Invariants

### Message Format
- [ ] Slack message contains alarm name
- [ ] Slack message contains state transition (ALARM/OK)
- [ ] Slack message contains environment name
- [ ] Slack message contains severity level
- [ ] Slack message contains CloudWatch console link
- [ ] Slack message contains reason for state change

### Severity Classification
| Keyword | Severity | Emoji |
|---------|----------|-------|
| scheduler, precompute | CRITICAL | :rotating_light: |
| 5xx, errors | HIGH | :x: |
| 4xx, duration | MEDIUM | :warning: |
| other | INFO | :bell: |

### Color Coding
| State | Color |
|-------|-------|
| ALARM | danger (red) |
| OK | good (green) |
| other | warning (yellow) |

### Verification
```bash
# Check message format in Lambda logs
aws logs tail /aws/lambda/dr-daily-report-slack-notifier-{env} --since 1h
```

---

## Level 1: Service Invariants

### Lambda Handler
- [ ] Receives SNS event with Records array
- [ ] Parses JSON message from SNS
- [ ] Handles malformed JSON gracefully (treats as plain text)
- [ ] Logs incoming events
- [ ] Returns 200 on success, 207 on partial failure

### Slack Integration
- [ ] Posts to webhook URL via HTTPS
- [ ] Uses correct Content-Type header (application/json)
- [ ] Handles webhook errors without crashing
- [ ] Logs success/failure of each notification

### Error Handling
- [ ] Missing SLACK_WEBHOOK_URL returns 500
- [ ] Invalid webhook URL logs error and continues
- [ ] Multiple records processed independently
- [ ] Errors don't block other notifications

### Verification
```bash
# Trigger test alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-{env}" \
  --state-value ALARM \
  --state-reason "Acceptance test"

# Check Lambda logs
sleep 5 && aws logs tail /aws/lambda/dr-daily-report-slack-notifier-{env} --since 1m

# Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name "dr-daily-report-scheduler-errors-{env}" \
  --state-value OK \
  --state-reason "Test complete"
```

---

## Level 0: User (On-Call) Invariants

### Alert Visibility
- [ ] Alert appears in Slack within 1 minute
- [ ] Alert clearly identifies failed component
- [ ] Alert shows timestamp
- [ ] Alert includes clickable link to CloudWatch

### Message Clarity
- [ ] State change is obvious (ALARM/OK)
- [ ] Environment is clearly identified (DEV/STG/PRD)
- [ ] Severity is appropriate for the issue
- [ ] Color coding aids quick triage

### Alert Resolution
- [ ] OK notification sent when issue resolves
- [ ] OK message uses green color
- [ ] Resolution message includes "RESOLVED" prefix

### Verification
```bash
# Full acceptance test (manual):
# 1. Trigger test alarm
# 2. Verify Slack message received
# 3. Check message contains all required fields
# 4. Reset alarm
# 5. Verify OK message received
```

---

## Test Coverage Invariants

### Unit Tests Required
| Function | Expected Test | Status |
|----------|--------------|--------|
| `get_severity_emoji` | Test all alarm name patterns | ❌ MISSING |
| `get_severity_level` | Test CRITICAL/HIGH/MEDIUM/INFO mapping | ❌ MISSING |
| `get_color` | Test ALARM/OK/other states | ❌ MISSING |
| `format_slack_message` | Test complete message structure | ❌ MISSING |
| `send_to_slack` | Test success/failure cases | ❌ MISSING |
| `lambda_handler` | Test SNS event processing | ❌ MISSING |

### Required Test Additions
```python
# tests/alerting/test_slack_notifier.py

def test_severity_emoji_critical():
    """CRITICAL alarms (scheduler, precompute) get rotating_light."""
    assert get_severity_emoji("scheduler-errors") == ":rotating_light:"
    assert get_severity_emoji("precompute-errors") == ":rotating_light:"

def test_severity_emoji_high():
    """5xx alarms get x emoji."""
    assert get_severity_emoji("api-5xx-errors") == ":x:"

def test_severity_level_mapping():
    """Alarm names map to correct severity levels."""
    assert get_severity_level("scheduler-errors") == "CRITICAL"
    assert get_severity_level("api-5xx-errors") == "HIGH"
    assert get_severity_level("api-4xx-errors") == "MEDIUM"

def test_color_mapping():
    """Alarm states map to correct Slack colors."""
    assert get_color("ALARM") == "danger"
    assert get_color("OK") == "good"
    assert get_color("INSUFFICIENT_DATA") == "warning"

def test_format_slack_message_structure():
    """Message contains all required fields."""
    sns_message = {
        "AlarmName": "test-alarm",
        "NewStateValue": "ALARM",
        "OldStateValue": "OK",
        "NewStateReason": "Test reason"
    }
    result = format_slack_message(sns_message)

    assert "attachments" in result
    assert result["attachments"][0]["color"] == "danger"
    assert "test-alarm" in result["attachments"][0]["title"]

def test_lambda_handler_missing_webhook():
    """Handler returns 500 when webhook URL not set."""
    # Temporarily unset SLACK_WEBHOOK_URL
    # Assert statusCode == 500

def test_lambda_handler_processes_records():
    """Handler processes all SNS records."""
    event = {
        "Records": [
            {"Sns": {"Message": '{"AlarmName": "test"}'}},
            {"Sns": {"Message": '{"AlarmName": "test2"}'}}
        ]
    }
    # Mock send_to_slack
    # Assert processed == 2
```

### Verification Commands
```bash
# Run alerting tests
pytest tests/alerting/ -v

# Check test count
grep -c "def test_" tests/alerting/test_slack_notifier.py
```

---

## Environment Deployment Status

| Environment | Status | Last Verified |
|-------------|--------|---------------|
| dev | ✅ COMPLETE | 2026-01-14 |
| staging | ❌ PENDING | - |
| production | ❌ PENDING | - |

### Deployment Checklist
- [ ] Set `TF_VAR_SLACK_WEBHOOK_URL` in Doppler
- [ ] Apply Terraform
- [ ] Verify SNS subscription
- [ ] Trigger test alarm
- [ ] Verify Slack message received
- [ ] Reset alarm
- [ ] Verify OK message received

---

## Related Files

| File | Purpose |
|------|---------|
| `terraform/monitoring.tf` | CloudWatch alarms + Slack notifier Lambda |
| `terraform/variables.tf` | SLACK_WEBHOOK_URL variable |
| `src/alerting/slack_notifier.py` | Lambda handler |
| `.claude/specs/sns-alert-system/` | Feature specification |

---

*Domain: alerting*
*Last Updated: 2026-01-14*
