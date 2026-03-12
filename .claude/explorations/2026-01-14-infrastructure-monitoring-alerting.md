# Exploration: Infrastructure Monitoring & Alerting System

**Date**: 2026-01-14
**Focus**: Cost-effective alerting with AWS-native solutions
**Status**: Complete

---

## Problem Decomposition

### Goal

Implement comprehensive monitoring and alerting for:
1. **Scheduler failures** - Alert when daily data population fails
2. **Application health** - Alert when LINE Bot or Telegram Mini App is down (dev/stg/prod)
3. **Additional value** - Identify other monitoring opportunities for the current infrastructure

### Current Infrastructure Inventory

| Component | Type | Terraform File | Environment |
|-----------|------|----------------|-------------|
| **LINE Bot** | Lambda + Function URL | main.tf:230 | dev/stg/prod |
| **Telegram API** | API Gateway + Lambda | telegram_api.tf | dev/stg/prod |
| **Report Worker** | Lambda (async) | async_report.tf | dev/stg/prod |
| **Ticker Scheduler** | EventBridge Scheduler → Lambda | scheduler.tf | dev/stg/prod |
| **Precompute Workflow** | Step Functions | precompute_workflow.tf | dev/stg/prod |
| **Aurora MySQL** | RDS Cluster | aurora.tf | dev/stg/prod |
| **Frontend** | S3 + CloudFront | frontend.tf | dev/stg/prod |

### Current Monitoring Status

**Existing (monitoring.tf):**
| Resource | Alarm | Status |
|----------|-------|--------|
| SNS Topic | `telegram-alerts` | Exists but **NO SUBSCRIBERS** |
| Telegram API Lambda | Error count > 5 | Active |
| Report Worker Lambda | Error count > 3 | Active |
| API Gateway | 5xx > 10, 4xx > 50 | Active |
| Lambda Duration | Avg > 45s | Active |

**GAPS (Missing):**
| Gap | Impact | Priority |
|-----|--------|----------|
| No scheduler failure monitoring | Silent data staleness | **P0** |
| No LINE Bot monitoring | LINE users affected undetected | **P0** |
| No SNS subscription | Alerts go nowhere | **P0** |
| No data freshness check | Stale data served silently | **P1** |
| No Step Functions monitoring | Workflow failures undetected | **P1** |
| No Aurora health monitoring | Database issues undetected | **P2** |
| No CloudFront monitoring | Frontend issues undetected | **P2** |

---

## Solution Space (Divergent Phase)

### Option 1: AWS CloudWatch + SNS (Native, Low Cost)

**Description**: Extend existing CloudWatch alarms with SNS email/SMS subscriptions

**How it works**:
1. Add CloudWatch alarms for missing components (Scheduler, LINE Bot, Step Functions)
2. Subscribe email/SMS to existing SNS topic
3. Create custom CloudWatch metric for data freshness

**Components to add**:
```terraform
# 1. SNS Email Subscription
resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.telegram_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# 2. Scheduler Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "scheduler_errors" {
  alarm_name          = "${var.project_name}-scheduler-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0  # Any error is critical for scheduler
  dimensions = { FunctionName = aws_lambda_function.ticker_scheduler.function_name }
  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
}

# 3. LINE Bot Error Alarm
resource "aws_cloudwatch_metric_alarm" "line_bot_errors" {
  alarm_name          = "${var.project_name}-line-bot-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  dimensions = { FunctionName = aws_lambda_function.line_bot.function_name }
  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
}

# 4. Step Functions Execution Failed Alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_failed" {
  alarm_name          = "${var.project_name}-precompute-failed-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  dimensions = { StateMachineArn = aws_sfn_state_machine.precompute_workflow.arn }
  alarm_actions = [aws_sns_topic.telegram_alerts.arn]
}

# 5. Data Freshness Custom Metric (via Lambda)
# Scheduler Lambda publishes custom metric after successful run
```

**Pros**:
- No additional cost (CloudWatch alarms are ~$0.10/alarm/month)
- Native AWS integration
- Already partially implemented (just extend)
- Simple to understand and maintain

**Cons**:
- Email alerts can be noisy
- No mobile push notifications (unless using SNS SMS)
- Manual correlation of related alerts
- No built-in incident management

**Cost**: ~$2-5/month (10-20 alarms + SNS)

---

### Option 2: AWS CloudWatch + EventBridge + Lambda Alerter (Custom Bot)

**Description**: Custom alerting Lambda that sends to Telegram/LINE directly

**How it works**:
1. CloudWatch alarms trigger SNS
2. SNS triggers custom Lambda
3. Lambda formats and sends to Telegram Bot / LINE

**Architecture**:
```
CloudWatch Alarm → SNS → Lambda Alerter → Telegram Bot API
                                       → LINE Messaging API
```

**Pros**:
- Alerts arrive where you already look (Telegram/LINE)
- Can include rich formatting, links to CloudWatch
- No email checking required
- Can group/deduplicate alerts

**Cons**:
- Need to build and maintain alerter Lambda
- Additional Lambda invocations (~$0.01/month)
- Telegram bot requires setup
- More moving parts

**Cost**: ~$3-8/month (alarms + Lambda + bot hosting)

---

### Option 3: AWS EventBridge Scheduler + SNS (Proactive Health Checks)

**Description**: Scheduled health checks that verify data freshness and app availability

**How it works**:
1. EventBridge runs health check Lambda every 15 minutes
2. Health check queries Aurora for data freshness, pings endpoints
3. Publishes pass/fail to CloudWatch custom metrics
4. Alarms trigger on failures

**Health Check Lambda**:
```python
def lambda_handler(event, context):
    checks = {
        "aurora_data_freshness": check_aurora_freshness(),  # MAX(date) >= today
        "telegram_api_health": ping_endpoint(TELEGRAM_API_URL),
        "line_bot_health": ping_endpoint(LINE_BOT_URL),
        "frontend_health": ping_endpoint(CLOUDFRONT_URL),
    }

    for name, passed in checks.items():
        cloudwatch.put_metric_data(
            Namespace='DR/HealthChecks',
            MetricData=[{
                'MetricName': name,
                'Value': 1 if passed else 0,
                'Unit': 'Count'
            }]
        )

    return checks
```

**Pros**:
- Proactive (catches issues before users report)
- Semantic health checks (not just Lambda errors)
- Data freshness verification
- End-to-end validation

**Cons**:
- More infrastructure (new Lambda)
- 15-minute latency for detection
- Additional CloudWatch costs

**Cost**: ~$5-10/month (Lambda invocations + custom metrics + alarms)

---

### Option 4: Datadog / New Relic / PagerDuty (Third-Party)

**Description**: Full-featured observability platform with alerting

**How it works**:
1. Install agent/integration for AWS
2. Auto-discovers Lambda, API Gateway, RDS
3. Built-in dashboards and alerting
4. Mobile app for notifications

**Pros**:
- Rich dashboards and visualizations
- AI-powered anomaly detection
- Incident management workflows
- Mobile push notifications
- Cross-service correlation

**Cons**:
- **Expensive** ($15-25/host/month for Datadog)
- Overkill for current scale
- Vendor lock-in
- Learning curve

**Cost**: ~$50-200/month (varies by usage)

---

### Option 5: Uptime Monitoring Service (Betterstack/Pingdom/UptimeRobot)

**Description**: External endpoint monitoring with alerting

**How it works**:
1. External service pings your endpoints every 1-5 minutes
2. Alerts via email, SMS, Slack, webhook
3. Status page for public visibility

**Services**:
- **BetterStack Uptime** (free tier: 10 monitors, 3-min intervals)
- **UptimeRobot** (free tier: 50 monitors, 5-min intervals)
- **Pingdom** (paid, $15/month)

**Pros**:
- External perspective (catches DNS, CDN issues)
- Free tiers available
- Status page included
- Simple setup (just provide URLs)

**Cons**:
- Only monitors HTTP endpoints
- Can't check Aurora directly
- Can't verify data freshness
- Limited to publicly accessible URLs

**Cost**: $0-15/month

---

### Option 6: Hybrid (CloudWatch + External Uptime + Telegram Bot)

**Description**: Best of multiple worlds - combine approaches

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│                    ALERTING SYSTEM                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  CloudWatch  │   │   BetterStack │   │   Lambda     │ │
│  │   Alarms     │   │    Uptime     │   │  Health Check│ │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │
│         │                  │                   │         │
│         │  Internal       │  External         │ Data    │
│         │  Errors         │  Availability     │ Quality │
│         │                  │                   │         │
│         └────────┬─────────┴─────────┬────────┘         │
│                  │                   │                   │
│                  v                   v                   │
│           ┌─────────────────────────────┐               │
│           │       SNS Topic              │               │
│           │  (email + alerter Lambda)   │               │
│           └─────────────┬───────────────┘               │
│                         │                               │
│                         v                               │
│           ┌─────────────────────────────┐               │
│           │    Telegram Alert Bot       │               │
│           │    (formatted messages)     │               │
│           └─────────────────────────────┘               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Pros**:
- Complete coverage (internal + external + data)
- Cost-effective (mostly AWS native)
- Alerts where you want them (Telegram)
- Scalable (can add more checks)

**Cons**:
- More components to maintain
- Initial setup complexity
- Need to manage multiple systems

**Cost**: ~$5-15/month

---

## Evaluation Matrix

| Criterion | Option 1 (CW+SNS) | Option 2 (Custom Bot) | Option 3 (Health Checks) | Option 4 (Datadog) | Option 5 (Uptime) | Option 6 (Hybrid) |
|-----------|-------------------|----------------------|--------------------------|--------------------|--------------------|-------------------|
| **Coverage** | 6/10 | 7/10 | 9/10 | 10/10 | 4/10 | 9/10 |
| **Cost** | 10/10 | 9/10 | 8/10 | 2/10 | 10/10 | 8/10 |
| **Setup Effort** | 9/10 | 6/10 | 6/10 | 7/10 | 10/10 | 5/10 |
| **Maintenance** | 9/10 | 6/10 | 7/10 | 9/10 | 10/10 | 6/10 |
| **Alert Quality** | 5/10 | 8/10 | 7/10 | 9/10 | 6/10 | 8/10 |
| **Data Freshness** | 3/10 | 3/10 | 10/10 | 8/10 | 0/10 | 10/10 |
| **Total** | **42** | **39** | **47** | **45** | **40** | **46** |

---

## Ranked Recommendations

### 1. Option 3: Health Checks (Score: 47/60) - **RECOMMENDED for Your Use Case**

**Why this is best for your requirements**:
- **Scheduler failure detection**: Health check verifies `MAX(date) FROM daily_prices >= TODAY`
- **App availability**: Pings LINE Bot and Telegram API endpoints
- **Proactive**: Catches issues before users report
- **Low cost**: ~$5-10/month

**Trade-offs**:
- Requires building health check Lambda
- 15-minute detection latency (acceptable for daily data)

**Implementation priority**:
1. Create health check Lambda
2. Add CloudWatch custom metrics
3. Add CloudWatch alarms
4. Subscribe email to SNS

---

### 2. Option 6: Hybrid (Score: 46/60) - **BEST LONG-TERM**

**Why**:
- Combines internal (CloudWatch) + external (BetterStack) + semantic (Health Checks)
- Free external monitoring via BetterStack/UptimeRobot
- Telegram bot for convenient alerting

**When to choose**: If you want complete coverage and don't mind initial setup time

---

### 3. Option 1: CloudWatch + SNS (Score: 42/60) - **QUICKEST WIN**

**Why**:
- Already 80% implemented
- Just need to add SNS subscription and missing alarms
- Can be done in 30 minutes

**When to choose**: If you need something working TODAY

---

## Additional Monitoring Recommendations

Based on your infrastructure, here are additional monitoring opportunities:

### High Priority (P0-P1)

| What to Monitor | Metric | Threshold | Why |
|-----------------|--------|-----------|-----|
| **Aurora CPU** | CPUUtilization | > 80% | Database performance |
| **Aurora Connections** | DatabaseConnections | > 80% of max | Connection pool exhaustion |
| **Aurora Storage** | FreeStorageSpace | < 10GB | Prevent write failures |
| **Lambda Throttles** | Throttles > 0 | Any throttle | Concurrent limit hit |
| **Lambda Dead Letter** | DLQ messages > 0 | Any message | Processing failures |
| **CloudFront Errors** | 5xxErrorRate > 1% | Frontend failures |

### Medium Priority (P2)

| What to Monitor | Metric | Threshold | Why |
|-----------------|--------|-----------|-----|
| **Lambda Memory** | MaxMemoryUsed > 90% | Memory pressure |
| **API Gateway Latency** | P99 > 5s | User experience |
| **S3 Bucket Size** | Bytes > 50GB | Cost control |
| **Step Functions Duration** | ExecutionTime > 10min | Workflow health |

### Low Priority (P3)

| What to Monitor | Why |
|-----------------|-----|
| CloudWatch Log Errors | Detect application bugs |
| AWS Health Events | AWS service issues |
| Cost Anomaly | Budget protection |

---

## Next Steps

```bash
# Quick Win: Add SNS email subscription (5 minutes)
# This alone makes existing alarms useful
terraform apply -target=aws_sns_topic_subscription.email_alerts

# Option 3 Implementation: Health Check Lambda
/design python "Health Check Lambda for data freshness and endpoint availability"

# Alternative: Hybrid approach
/specify "Hybrid monitoring with CloudWatch + BetterStack + Telegram alerter"
```

---

## Environment Management Pattern

**IMPORTANT**: This project uses the `-var-file` pattern for environment switching, NOT Terraform workspaces.

### Current Pattern
```bash
# Environment switching via -var-file flag
terraform plan -var-file=terraform.dev.tfvars      # dev environment
terraform plan -var-file=terraform.staging.tfvars  # staging environment
terraform plan -var-file=terraform.prod.tfvars     # production environment
```

### Environment Files
| File | Environment | Deployment Trigger |
|------|-------------|-------------------|
| `terraform.dev.tfvars` | dev | `dev` branch push |
| `terraform.staging.tfvars` | staging | `main` branch push |
| `terraform.prod.tfvars` | prod | `v*.*.*` tag |

### Feature Branch Environments
For feature branch isolated environments, create a new `.tfvars` file:
```bash
# Create feature branch environment
cp terraform/terraform.dev.tfvars terraform/terraform.feature-xyz.tfvars
# Edit: environment = "feature-xyz"

# Apply
terraform apply -var-file=terraform.feature-xyz.tfvars
```

See `/provision-env` command for automated feature branch environment provisioning.

### Why Not Workspaces?
- Single `default` workspace used (no workspace switching)
- `-var-file` pattern provides explicit, reviewable configuration
- CI/CD uses explicit file paths, not workspace state
- Easier to audit environment differences via `diff`

---

## Resources Gathered

**AWS Documentation**:
- [CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [SNS Notifications](https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html)
- [EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [Step Functions Metrics](https://docs.aws.amazon.com/step-functions/latest/dg/procedure-cw-metrics.html)

**Free External Monitoring**:
- [BetterStack Uptime](https://betterstack.com/uptime) - 10 monitors free
- [UptimeRobot](https://uptimerobot.com/) - 50 monitors free

**Terraform Examples**:
- [CloudWatch Alarm Module](https://registry.terraform.io/modules/terraform-aws-modules/cloudwatch/aws/latest)

---

*Generated by /explore command*
