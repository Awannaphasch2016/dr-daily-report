# System Invariants

Project-wide behavioral invariants that define system correctness. These are the minimum conditions that must hold for the system to function.

**Last Updated**: 2026-01-12

---

## Critical Path (Must Always Verify)

The minimum invariants that guarantee the system works:

```
User Message → Webhook → Lambda → Aurora → Report → User Response
```

### 1. Telegram Bot Critical Path

| Step | Invariant | Verification |
|------|-----------|--------------|
| 1 | Telegram webhook receives messages | Send test message, check CloudWatch |
| 2 | telegram-api Lambda invoked | Check Lambda invocation logs |
| 3 | Lambda can query Aurora | Test connection in Lambda |
| 4 | Aurora has price data | `SELECT COUNT(*) WHERE date = CURDATE()` |
| 5 | Report generated successfully | Check report-worker logs |
| 6 | User receives response | Confirm message received |

### 2. Frontend Critical Path

| Step | Invariant | Verification |
|------|-----------|--------------|
| 1 | CloudFront serves frontend | Load page, check status |
| 2 | Frontend can call API | Check network tab |
| 3 | API returns valid data | Validate response schema |
| 4 | Charts render correctly | Visual inspection |

---

## Level 0: User-Facing Invariants

### Telegram Bot
- [ ] `/start` returns welcome message
- [ ] `/report TICKER` returns PDF within 30 seconds
- [ ] `/watchlist` returns portfolio summary
- [ ] Invalid commands return helpful error

### Frontend
- [ ] Dashboard loads without error
- [ ] Charts display with current data
- [ ] Export functionality works

---

## Level 1: Service Invariants

### Lambda Functions
- [ ] `telegram-api` responds to health check with 200
- [ ] `telegram-api` processes webhook within timeout
- [ ] `report-worker` generates valid PDF
- [ ] `fund-data-sync` completes ETL successfully

### API Gateway
- [ ] Routes requests to correct Lambda
- [ ] CORS headers present
- [ ] No 5xx errors in last hour

---

## Level 2: Data Invariants

### Aurora
- [ ] `daily_prices` has data for today (46 tickers)
- [ ] `ticker_master` has all tracked tickers
- [ ] No orphaned foreign keys
- [ ] Data timestamps within expected range

### S3
- [ ] Static assets accessible
- [ ] Precomputed reports exist
- [ ] Data lake has recent uploads

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] Lambda → Aurora: Connection pool healthy
- [ ] Lambda → S3: Upload/download works
- [ ] Lambda → External APIs: Timeout configured

### Network
- [ ] VPC endpoints configured for S3
- [ ] NAT Gateway has capacity
- [ ] Security groups allow required traffic

---

## Level 4: Configuration Invariants

### Environment Variables
- [ ] `AURORA_HOST` set and correct
- [ ] `TZ=Asia/Bangkok` set
- [ ] `LANGFUSE_RELEASE` set (for observability)
- [ ] All Doppler secrets accessible

### Migrations
- [ ] All migrations applied
- [ ] Schema matches expected state
- [ ] No pending migrations

### IAM
- [ ] Lambda execution role has required permissions
- [ ] S3 bucket policy allows Lambda access
- [ ] Aurora credentials accessible via Secrets Manager

---

## Verification Commands

### Quick Health Check (All Levels)

```bash
# Level 4
/dev "verify env vars set"

# Level 3
/dev "test Aurora connectivity"

# Level 2
/dev "SELECT COUNT(*) FROM daily_prices WHERE date = CURDATE()"

# Level 1
/dev "invoke telegram-api health check"

# Level 0
# Manual: Send /start to Telegram bot
```

### Pre-Deployment Checklist

```bash
# 1. Configuration
doppler run --config dev -- printenv | grep -E "AURORA|TZ|LANGFUSE"

# 2. Infrastructure
aws lambda invoke --function-name telegram-api-dev --payload '{"test":"connectivity"}'

# 3. Data
/dev "SELECT MAX(date) FROM daily_prices"

# 4. Service
/dev "invoke Lambda and check response"

# 5. User (manual)
# Send test message to bot
```

---

## When to Verify

| Scenario | Levels to Verify |
|----------|------------------|
| Code change (logic only) | 1, 0 |
| Schema change | 4, 2, 1, 0 |
| Infrastructure change | 4, 3, 2, 1, 0 |
| Environment variable change | 4, 3, 1, 0 |
| Full deployment | All levels |

---

## See Also

- [CLAUDE.md - Principle #25](../CLAUDE.md)
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md)
- [Deployment Skill](../skills/deployment/)
