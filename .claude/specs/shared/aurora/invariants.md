# Aurora MySQL Invariants

**Objective**: Shared data layer
**Last Updated**: 2026-01-13

---

## Critical Path

```
Application → Aurora Connection → Query → Result
```

Every Aurora operation must preserve: **Data is fresh, consistent, and accessible.**

---

## Level 4: Configuration Invariants

### Credentials (Doppler)
- [ ] `AURORA_HOST` set and correct for environment
- [ ] `AURORA_USER` set
- [ ] `AURORA_PASSWORD` set
- [ ] `AURORA_DATABASE` set
- [ ] Credentials are environment-isolated

### RDS Parameter Group
- [ ] `time_zone = 'Asia/Bangkok'`
- [ ] `max_connections` sufficient for workload
- [ ] `slow_query_log` enabled
- [ ] `long_query_time` configured

### Table Names
- [ ] All table names centralized in `src/data/aurora/table_names.py`
- [ ] No hardcoded table names in queries

### Verification
```bash
# Check credentials exist
doppler secrets get AURORA_HOST -p dr-daily-report -c {env}

# Check parameter group
aws rds describe-db-cluster-parameters --db-cluster-parameter-group-name dr-aurora-{env}
```

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] Aurora cluster is running
- [ ] Lambda can connect (VPC configuration)
- [ ] Security group allows port 3306
- [ ] Subnet group includes Lambda subnets

### Performance
- [ ] Read replicas configured (if needed)
- [ ] Connection pooling (Lambda reuse)
- [ ] Query timeout < 30s

### Backup
- [ ] Automated backups enabled
- [ ] Retention period configured
- [ ] Point-in-time recovery available

### Verification
```bash
# Check cluster status
aws rds describe-db-clusters --db-cluster-identifier dr-aurora-{env} \
  --query "DBClusters[0].Status"

# Test connectivity from Lambda
aws lambda invoke --function-name dr-telegram-api-{env} \
  --payload '{"test": "aurora_connectivity"}' response.json
```

---

## Level 2: Data Invariants

### daily_prices
- [ ] Has data for today (or most recent trading day)
- [ ] Contains all 46 tracked tickers
- [ ] OHLCV columns not null
- [ ] Dates in Bangkok timezone

### ticker_master
- [ ] Contains all 46 tickers
- [ ] Symbol column is unique
- [ ] Required metadata present

### precomputed_reports (if applicable)
- [ ] < 24h stale
- [ ] JSON is valid
- [ ] All required fields present

### Data Freshness
- [ ] Nightly scheduler runs successfully
- [ ] No gaps in daily data
- [ ] Latest date = most recent trading day

### Verification
```sql
-- Check data freshness
SELECT MAX(date) as latest, COUNT(DISTINCT symbol) as tickers
FROM daily_prices;

-- Check ticker count
SELECT COUNT(*) FROM ticker_master;

-- Check for gaps
SELECT date, COUNT(*)
FROM daily_prices
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY date ORDER BY date;
```

---

## Level 1: Service Invariants

### Query Performance
- [ ] SELECT queries < 5s
- [ ] No full table scans on large tables
- [ ] Indexes on frequently queried columns
- [ ] Connection reuse in Lambda

### Error Handling
- [ ] Connection errors raise exceptions
- [ ] Query errors raise exceptions
- [ ] No silent failures
- [ ] Errors logged with context

### Transaction Safety
- [ ] Write operations use transactions
- [ ] Rollback on failure
- [ ] No partial updates

### Verification
```bash
# Check slow query log
aws rds download-db-log-file-portion --db-instance-identifier dr-aurora-{env} \
  --log-file-name slowquery/mysql-slowquery.log

# Check active connections
# Via Aurora: SHOW PROCESSLIST;
```

---

## Level 0: User Invariants

### Data Accuracy
- [ ] Prices match market data
- [ ] Dates are correct
- [ ] No duplicate records
- [ ] All required tickers present

### Availability
- [ ] Database accessible during business hours
- [ ] Maintenance windows during off-hours
- [ ] Failover works (multi-AZ)

### Verification
```sql
-- Verify sample data accuracy
SELECT symbol, date, open, high, low, close, volume
FROM daily_prices
WHERE symbol = 'ADVANC'
ORDER BY date DESC LIMIT 5;
```

---

## Environment-Specific

### dev
```yaml
relaxations:
  - Stale data up to 48h
  - Single AZ acceptable
  - Smaller instance class
```

### stg
```yaml
requirements:
  - Stale data < 24h
  - Multi-AZ recommended
  - Production-like data
```

### prd
```yaml
requirements:
  - Stale data < 24h
  - Multi-AZ required
  - Automated backups
  - Monitoring alerts
```

---

## Claiming "Aurora Work Done"

```markdown
## Aurora work complete: {description}

**Environment**: {dev | stg | prd}

**Invariants Verified**:
- [x] Level 4: Credentials set, timezone correct
- [x] Level 3: Connectivity working, performance acceptable
- [x] Level 2: Data fresh, schema correct
- [x] Level 1: Queries fast, errors handled
- [x] Level 0: Data accurate

**Evidence**: {Query output, CloudWatch metrics}
```

---

*Objective: shared/aurora*
*Spec: .claude/specs/shared/aurora/spec.yaml*
