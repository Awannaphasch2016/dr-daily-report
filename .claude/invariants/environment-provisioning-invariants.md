# Environment Provisioning Invariants

**Domain**: New environment setup, infrastructure transfer, environment cloning
**Load when**: provision, create environment, clone environment, transfer

**Related**: [/provision-env command](../commands/provision-env.md), [Deployment Invariants](./deployment-invariants.md), [Principle #25](../principles/)

**Lesson Learned**: When provisioning a new environment, violations form a dependency chain. A single visible symptom (e.g., "No markets found") often masks 5+ sequential dependencies. **Scan ALL layers before fixing.**

---

## The Environment Transfer Model

```
Source (dev/stg)           Target (new env)
┌──────────────────┐       ┌──────────────────┐
│ Config (L4)      │ ───→  │ Config (L4)      │  ← URLs, CORS, env vars
│ Infrastructure   │ ───→  │ Infrastructure   │  ← Lambda, API GW, S3
│ Schema (L2)      │ ───→  │ Schema (L2)      │  ← Tables, columns
│ Data (L2)        │ ───→  │ Data (L2)        │  ← Rows, relationships
│ Cache (L1)       │ ───→  │ Cache (L1)       │  ← Rankings, computed
└──────────────────┘       └──────────────────┘
```

**Critical Rule**: Transfers must happen in dependency order. Data cannot exist without Schema. Schema cannot function without Infrastructure. Infrastructure cannot be reached without Config.

---

## Pre-Provisioning Scan Checklist

**Before fixing ANYTHING**, scan ALL levels to build complete violation map:

### Level 4: Configuration Layer

| Check | Verification | Status |
|-------|--------------|--------|
| API URL configured for target env | Frontend calls correct API Gateway | ☐ |
| CORS includes target CloudFront domain | No CORS errors in browser | ☐ |
| Environment variables set in Doppler | `doppler secrets -c {env}` | ☐ |
| Frontend injected with correct URLs | Check built index.html | ☐ |
| API Gateway stage deployed | Check API Gateway console | ☐ |

```bash
# Verification commands
curl -I https://{api-id}.execute-api.{region}.amazonaws.com/api/v1/health
aws apigatewayv2 get-api --api-id {api-id} | jq '.CorsConfiguration'
```

### Level 3: Infrastructure Layer

| Check | Verification | Status |
|-------|--------------|--------|
| Lambda functions exist | `aws lambda list-functions --query 'Functions[?contains(FunctionName, `{env}`)]'` | ☐ |
| API Gateway routes configured | Check routes in AWS Console | ☐ |
| S3 bucket for frontend exists | `aws s3 ls s3://{bucket-name}` | ☐ |
| CloudFront distribution active | `aws cloudfront get-distribution --id {dist-id}` | ☐ |
| Aurora cluster accessible | VPC endpoint connectivity | ☐ |

```bash
# Verification commands
aws lambda get-function --function-name dr-daily-report-telegram-api-{env}
aws s3 ls s3://dr-daily-report-webapp-{env}/
```

### Level 2: Data Layer (Schema)

| Check | Verification | Status |
|-------|--------------|--------|
| `ticker_master` table exists | `SHOW TABLES LIKE 'ticker_master'` | ☐ |
| `ticker_aliases` table exists | `SHOW TABLES LIKE 'ticker_aliases'` | ☐ |
| `ticker_data` table exists | `SHOW TABLES LIKE 'ticker_data'` | ☐ |
| `precomputed_reports` table exists | `SHOW TABLES LIKE 'precomputed_reports'` | ☐ |
| `daily_indicators` table exists | `SHOW TABLES LIKE 'daily_indicators'` | ☐ |
| `indicator_percentiles` table exists | `SHOW TABLES LIKE 'indicator_percentiles'` | ☐ |

```bash
# Verification via query-tool Lambda
aws lambda invoke --function-name dr-daily-report-query-tool-{env} \
  --payload '{"action": "query", "query": "SHOW TABLES"}' \
  /tmp/tables.json && cat /tmp/tables.json
```

### Level 2: Data Layer (Content)

| Check | Verification | Status |
|-------|--------------|--------|
| Tickers populated in `ticker_master` | `SELECT COUNT(*) FROM ticker_master` | ☐ |
| Aliases populated in `ticker_aliases` | `SELECT COUNT(*) FROM ticker_aliases` | ☐ |
| Price history in `ticker_data` | `SELECT COUNT(DISTINCT symbol) FROM ticker_data` | ☐ |
| Reports computed in `precomputed_reports` | `SELECT COUNT(*) FROM precomputed_reports` | ☐ |

```bash
# Expected counts (approximate)
# ticker_master: 46 tickers
# ticker_aliases: 92 aliases (2 per ticker)
# ticker_data: 46 symbols × N days
# precomputed_reports: 46 reports
```

### Level 1: Service Layer

| Check | Verification | Status |
|-------|--------------|--------|
| Rankings API returns data | `GET /api/v1/rankings` returns tickers | ☐ |
| Rankings cache populated | `chart_data` field not null | ☐ |
| Report API works | `GET /api/v1/report/{ticker}` returns report | ☐ |

```bash
# Verification
curl https://{api-url}/api/v1/rankings | jq '.results | length'
curl https://{api-url}/api/v1/rankings | jq '.results[0].chart_data'
```

### Level 0: User Layer

| Check | Verification | Status |
|-------|--------------|--------|
| Dashboard loads | No JavaScript errors | ☐ |
| Market cards display | Cards with tickers visible | ☐ |
| Charts render | Chart canvas not empty | ☐ |
| Data is current | As-of date is today | ☐ |

```bash
# Screenshot verification
# Use Playwright to capture screenshot and verify visually
```

---

## Dependency-Aware Fix Order

**Fix violations in this exact order** to avoid cascade failures:

```
┌─────────────────────────────────────────────────────────────┐
│  1. CONFIG LAYER (L4)                                        │
│     - Fix API URLs in frontend build                         │
│     - Add CORS origins to API Gateway                        │
│     - Set environment variables in Doppler                   │
│                                                              │
│  ↓ (Config enables Infrastructure access)                    │
├─────────────────────────────────────────────────────────────┤
│  2. SCHEMA LAYER (L2)                                        │
│     - Create missing tables via query-tool                   │
│     - Verify column definitions match                        │
│     - Add indexes for performance                            │
│                                                              │
│  ↓ (Schema enables Data population)                          │
├─────────────────────────────────────────────────────────────┤
│  3. DATA LAYER (L2)                                          │
│     - Run ticker-fetcher to populate ticker_data             │
│     - Run setup_ticker_mapping for ticker_master/aliases     │
│     - Run precompute workflow for reports                    │
│                                                              │
│  ↓ (Data enables Service responses)                          │
├─────────────────────────────────────────────────────────────┤
│  4. CACHE LAYER (L1)                                         │
│     ⚠️  CRITICAL: Force refresh after data population         │
│     - Call rankings API with ?force_refresh=true             │
│     - Verify cache reflects new data                         │
│                                                              │
│  ↓ (Cache enables User experience)                           │
├─────────────────────────────────────────────────────────────┤
│  5. USER VERIFICATION (L0)                                   │
│     - Take screenshot of UI                                  │
│     - Verify market cards visible                            │
│     - Verify charts render with data                         │
│     - Compare to reference environment                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Cascade Violations

### Pattern: "No markets found" in UI

**Visible symptom**: Empty market grid in Telegram Mini App

**Actual dependency chain**:
```
L4 VIOLATION: Frontend calling wrong API URL
    ↓
L4 VIOLATION: CORS blocking cross-origin requests
    ↓
L2 VIOLATION: precomputed_reports table missing
    ↓
L2 VIOLATION: Table schema mismatch (JSON fields)
    ↓
L2 VIOLATION: No data in precomputed_reports
    ↓
L1 VIOLATION: Rankings cache empty/stale
    ↓
L0 SYMPTOM: "No markets found"
```

**Fix sequence** (takes ~6 steps, not 1):
1. Rebuild frontend with correct API URL
2. Add CloudFront domain to CORS
3. Create precomputed_reports table
4. Create supporting tables (daily_indicators, indicator_percentiles)
5. Run precompute workflow to populate data
6. Force refresh rankings cache
7. Verify UI shows markets

### Pattern: "chart_data: null" in API response

**Visible symptom**: Rankings API returns tickers but no chart data

**Actual cause**: Cache populated BEFORE precomputed_reports had data

**Fix**: Force cache refresh after data population
```bash
curl "https://{api-url}/api/v1/rankings?force_refresh=true"
```

---

## Post-Provisioning Verification Script

```bash
#!/bin/bash
# verify_environment.sh {env}

ENV=$1
API_URL=$(get_api_url $ENV)
CLOUDFRONT_URL=$(get_cloudfront_url $ENV)

echo "=== Verifying $ENV environment ==="

# L4: Config
echo "Checking CORS..."
curl -s -I -X OPTIONS $API_URL/health \
  -H "Origin: $CLOUDFRONT_URL" | grep -i "access-control"

# L2: Schema
echo "Checking tables..."
TABLES=$(query_aurora $ENV "SHOW TABLES")
echo "$TABLES" | grep -q "precomputed_reports" || echo "❌ Missing precomputed_reports"
echo "$TABLES" | grep -q "ticker_master" || echo "❌ Missing ticker_master"

# L2: Data
echo "Checking data..."
TICKER_COUNT=$(query_aurora $ENV "SELECT COUNT(*) FROM ticker_master")
REPORT_COUNT=$(query_aurora $ENV "SELECT COUNT(*) FROM precomputed_reports")
echo "Tickers: $TICKER_COUNT, Reports: $REPORT_COUNT"

# L1: Service
echo "Checking API..."
RANKINGS=$(curl -s "$API_URL/api/v1/rankings")
echo "$RANKINGS" | jq '.results | length'
echo "$RANKINGS" | jq '.results[0].chart_data != null'

# L0: User
echo "Checking UI..."
# Use Playwright for screenshot verification

echo "=== Verification complete ==="
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| Fix L0 first (UI) | Root cause at L4/L2 | Scan ALL levels, fix bottom-up |
| Skip cache refresh | Stale data served | Always force_refresh after data changes |
| Partial schema copy | Missing tables cause null fields | Copy ALL tables from reference |
| Fix one violation at a time | Cascade reveals next | Pre-scan ALL, batch fixes |
| Assume infra = data | Tables empty after Terraform | Schema ≠ Data, run population workflows |

---

## Claiming "Environment Provisioned"

```markdown
✅ Environment provisioned: {env}

**Source Environment**: {dev | stg}
**Target Environment**: {prd | new-env}

**Invariants Verified**:
- [x] Level 4: API URLs correct, CORS configured
- [x] Level 3: Lambda, API GW, S3, CloudFront deployed
- [x] Level 2: All 6 tables created, data populated
- [x] Level 1: Rankings API returns 46 tickers with chart_data
- [x] Level 0: UI shows market cards with charts (screenshot attached)

**Evidence**:
- Screenshot: {path/to/screenshot.png}
- API Response: {curl output}
- Data Counts: ticker_master=46, precomputed_reports=46

**Confidence**: HIGH
```

---

*Domain: environment-provisioning*
*Last updated: 2026-01-14*
*Pattern discovered: Production Telegram Mini App reconciliation*
