# SNS Alert System Constraints

**Objective**: CloudWatch alarms monitoring data pipeline and app health with Slack notifications
**Last Updated**: 2026-01-14

---

## Technical Constraints

### AWS Limitations
- **SNS to Slack**: SNS cannot directly call Slack webhooks (HTTPS endpoint must return 200 with empty body). Options:
  1. Use email subscription (simplest)
  2. Use Lambda as SNS→Slack bridge (richest formatting)
  3. Use AWS Chatbot (requires Slack workspace integration)

- **CloudWatch Alarm Resolution**: Minimum period is 60 seconds for standard metrics

- **SNS Email Confirmation**: Email subscriptions require manual confirmation click

### Cost Constraints
- CloudWatch alarms: ~$0.10/alarm/month
- SNS notifications: First 1M free, then $0.50/1M
- Lambda (if using Slack bridge): Negligible (~$0.01/month)

### Existing Infrastructure
- SNS topic already exists: `dr-daily-report-telegram-alerts-{env}`
- Some alarms already exist: `telegram-api-errors`, `report-worker-errors`, `api-5xx`, `api-4xx`, `telegram-api-duration`
- **GAP**: No subscribers on SNS topic (alerts go nowhere)
- **GAP**: No scheduler alarm, no LINE Bot alarm, no Step Functions alarm

---

## Business Constraints

### Alert Severity Levels
- **CRITICAL**: Data pipeline failures (scheduler, precompute) - immediate attention required
- **HIGH**: App health issues (API errors) - investigate within 1 hour
- **MEDIUM**: Performance degradation (duration approaching timeout) - investigate within 4 hours

### On-Call Expectations
- Alerts should be actionable (not just "something is wrong")
- False positives should be < 5% (tune thresholds based on baseline)
- Weekend/off-hours: Only CRITICAL alerts

---

## Lessons Learned

### 2026-01-14: SNS Topic Exists But Has No Subscribers
- **Discovery**: `/invariant` scan revealed SNS topic exists but alerts go nowhere
- **Impact**: All existing alarms (telegram-api-errors, report-worker-errors, etc.) were firing but not notifying anyone
- **Fix**: Add email and/or Slack subscription to SNS topic

### 2026-01-14: Feature Branch Environment Creates Full Infrastructure
- **Discovery**: `/provision-env` creates separate Aurora cluster per environment (~$75/month)
- **Impact**: Feature branch isolation is expensive
- **Learning**: For alert system development, apply directly to dev (alerts are cheap and non-destructive)

---

## Anti-Patterns to Avoid

### Alert Fatigue
- **Problem**: Too many alerts → on-call ignores all alerts
- **Solution**: Set thresholds high enough to avoid noise, tune based on baseline

### Missing Context
- **Problem**: Alert says "Lambda error" but doesn't say which Lambda or what error
- **Solution**: Include function name, error type, timestamp, CloudWatch link

### No Resolution Notification
- **Problem**: Alert fires but no notification when issue resolves
- **Solution**: Include OK actions to notify when alarm returns to healthy state

### Silent Failures
- **Problem**: Alarm exists but SNS has no subscribers
- **Solution**: Verify SNS subscriptions as part of deployment checklist

---

## Environment-Specific Constraints

| Environment | Alert Threshold | Notification Channel |
|-------------|-----------------|---------------------|
| dev | Lower (catch issues early) | Email + Slack (test channel) |
| stg | Same as prod | Email + Slack (test channel) |
| prd | Tuned for baseline | Email + Slack (production channel) |
