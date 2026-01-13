# Telegram Mini App Invariants

**Objective**: Web dashboard via Telegram Mini App
**Last Updated**: 2026-01-13

---

## Critical Path

### Backend
```
HTTP Request → API Gateway → Lambda → Aurora → JSON Response
```

### Frontend
```
User Action → State Update → API Call → State Update → Render
```

Every Telegram operation must preserve: **UI reflects state, state reflects reality.**

---

## Level 4: Configuration Invariants

### Backend Credentials (Doppler)
- [ ] `OPENROUTER_API_KEY` set (LLM API)
- [ ] `DYNAMODB_WATCHLIST_TABLE` set (user watchlist)
- [ ] `PDF_STORAGE_BUCKET` set (report storage)
- [ ] `AURORA_HOST` set and correct for environment
- [ ] `TZ=Asia/Bangkok` set (report dates)
- [ ] `LANGFUSE_RELEASE` set (observability versioning)
- [ ] Credentials are environment-isolated

### Frontend Configuration
- [ ] `VITE_API_URL` set (API endpoint)
- [ ] Build-time env vars baked into bundle
- [ ] `vite.config.ts` correct for target environment

### Lambda Configuration
- [ ] Timeout >= 30s (report generation)
- [ ] Memory >= 1024MB (API processing)
- [ ] VPC configured (Aurora access)

### Build Configuration
- [ ] TailwindCSS configured properly
- [ ] TypeScript strict mode enabled
- [ ] No build warnings or errors

### Verification
```bash
# Backend
doppler secrets get OPENROUTER_API_KEY -p dr-daily-report -c {env}
aws lambda get-function --function-name dr-telegram-api-{env} --query "Configuration.Timeout"

# Frontend
cat frontend/twinbar/.env.{env}
cd frontend/twinbar && npm run build
```

---

## Level 3: Infrastructure Invariants

### Backend Connectivity
- [ ] Lambda → Aurora: VPC endpoint or NAT Gateway
- [ ] Lambda → S3: VPC Gateway Endpoint (not NAT)
- [ ] Lambda → Langfuse: NAT Gateway (external HTTPS)
- [ ] Lambda → OpenRouter: NAT Gateway (external HTTPS)

### Frontend Delivery
- [ ] CloudFront serves static assets
- [ ] Cache headers configured correctly
- [ ] Gzip/Brotli compression enabled
- [ ] CORS headers allow API calls

### API Gateway
- [ ] HTTP API Gateway v2 configured
- [ ] CORS enabled for frontend origin
- [ ] Routes correctly mapped to Lambda
- [ ] Custom domain (if applicable)

### Telegram Integration
- [ ] Mini App registered with BotFather
- [ ] Web App URL configured correctly
- [ ] Telegram WebApp SDK initialized
- [ ] Theme colors sync with Telegram

### Permissions
- [ ] Lambda execution role has Aurora access
- [ ] Lambda can read/write to S3
- [ ] Lambda can write to CloudWatch Logs

### Verification
```bash
# Backend connectivity
aws lambda invoke --function-name dr-telegram-api-{env} \
  --payload '{"requestContext": {"http": {"method": "GET", "path": "/api/v1/health"}}}' response.json

# Frontend delivery
curl -I https://d123xyz.cloudfront.net/index.html

# API Gateway
aws apigatewayv2 get-apis --query "Items[?Name=='dr-telegram-api-{env}']"
```

---

## Level 2: Data Invariants

### Aurora Data (Backend)
- [ ] `daily_prices` has data for today (46 tickers)
- [ ] `ticker_master` has all tracked tickers
- [ ] Precomputed data < 24h stale
- [ ] All foreign keys valid

### State Shape (Frontend)
- [ ] TypeScript types match actual state
- [ ] No `any` types in state definitions
- [ ] State is JSON-serializable
- [ ] Initial state is valid

### Data Never Shrinks (Monotonic)
- [ ] Array lengths don't decrease unexpectedly
- [ ] Loaded data persists until explicit clear
- [ ] Pagination adds, doesn't replace
- [ ] Cache invalidation is explicit

### API Response Data
- [ ] Report contains all required sections
- [ ] Price data reflects market close
- [ ] Dates in Bangkok timezone
- [ ] Chart data includes OHLCV

### Verification
```bash
# Aurora data
/dev "SELECT MAX(date) FROM daily_prices"
/dev "SELECT COUNT(*) FROM ticker_master"

# Frontend types
cd frontend/twinbar && npm run type-check
grep -r ": any" frontend/twinbar/src/
```

---

## Level 1: Service Invariants

### API Endpoints
- [ ] `/health` returns 200
- [ ] `/report/{ticker}` returns valid report JSON
- [ ] `/tickers` returns list of all tickers
- [ ] `/watchlist` returns user's watchlist
- [ ] Invalid ticker returns 404 with message

### Error Handling
- [ ] API errors return structured error response
- [ ] Missing data returns informative error
- [ ] Internal errors don't expose stack traces
- [ ] All errors logged to CloudWatch

### Frontend Rendering
- [ ] Components render without errors
- [ ] No React key warnings
- [ ] No memory leaks (useEffect cleanup)
- [ ] Loading states shown during async ops

### State Management (Zustand)
- [ ] Actions update state immutably
- [ ] Selectors prevent unnecessary re-renders
- [ ] No state mutations outside actions
- [ ] Async operations use loading states

### Chart Rendering
- [ ] Candlesticks render correctly
- [ ] Pattern overlays align with candles
- [ ] Tooltips show accurate data
- [ ] Responsive across screen sizes

### Observability
- [ ] Langfuse trace created for each report
- [ ] Quality scores attached to reports
- [ ] Request/response logged

### Verification
```bash
# API
curl https://api.{env}.example.com/api/v1/health
curl https://api.{env}.example.com/api/v1/report/ADVANC

# Frontend
cd frontend/twinbar && npm run lint

# Logs
aws logs tail /aws/lambda/dr-telegram-api-{env} --since 5m
```

---

## Level 0: User Invariants

### Dashboard Experience
- [ ] Dashboard loads within 3 seconds
- [ ] Watchlist displays current prices
- [ ] Can navigate between tickers
- [ ] Refresh updates data

### Report Experience
- [ ] Selecting ticker shows detailed report
- [ ] Report sections are readable
- [ ] Can generate PDF
- [ ] PDF downloads correctly

### Chart Experience
- [ ] Chart renders with price data
- [ ] Can zoom and pan
- [ ] Pattern overlays toggleable
- [ ] Touch gestures work on mobile

### Visual Feedback
- [ ] Loading spinners during data fetch
- [ ] Success/error toasts for actions
- [ ] Disabled buttons prevent double-submit
- [ ] Progress indicators for PDF generation

### Error Experience
- [ ] Invalid ticker shows friendly message
- [ ] Network errors show retry option
- [ ] Server errors don't crash app

### Telegram Integration
- [ ] Theme matches Telegram app
- [ ] Share button works
- [ ] Back button navigates correctly
- [ ] Mini App feels native

### Verification
```bash
# Manual testing (required for Level 0):
# 1. Open Telegram, find bot
# 2. Open Mini App
# 3. Verify dashboard loads
# 4. Select a ticker
# 5. Verify chart renders
# 6. Toggle pattern overlays
# 7. Generate PDF report
# 8. Test share functionality
# 9. Test error scenarios (offline, invalid ticker)
```

---

## Environment-Specific Overrides

### local
```yaml
relaxations:
  - Mock external APIs allowed
  - Mock Telegram SDK allowed
  - No SLA requirements
  - Debug logging: enabled
  - Hot module replacement
  - React DevTools allowed
```

### dev (AWS)
```yaml
requirements:
  - Real APIs (NO MOCKS)
  - Real Aurora connectivity
  - Real S3/CloudFront
relaxations:
  - Stale data tolerance: 24h
  - Response time SLA: best effort
  - Debug logging: enabled
```

### stg (AWS)
```yaml
requirements:
  - Real APIs (NO MOCKS)
  - Real Aurora connectivity
  - Production-like data volume
  - Performance monitored
relaxations:
  - Stale data tolerance: 24h
  - SLAs monitored but not enforced
  - Debug logging: enabled
```

### prd (AWS)
```yaml
requirements:
  - Production APIs ONLY
  - Real Aurora (Multi-AZ)
  - NO MOCKS (zero tolerance)
  - SLAs ENFORCED:
    - API response < 2s
    - Frontend load < 3s
    - Error rate < 1%
  - Debug logging: disabled
  - Production CloudFront
```

---

## Claiming "Telegram Work Done"

```markdown
## Telegram work complete: {description}

**Environment**: {dev | stg | prd}
**Component**: {backend | frontend | both}

**Invariants Verified**:
- [x] Level 4: Credentials set, build succeeds, Lambda configured
- [x] Level 3: Aurora connectivity, CloudFront serving, API Gateway routed
- [x] Level 2: Data fresh, state types correct, no data shrinkage
- [x] Level 1: API responds, components render, charts display
- [x] Level 0: User can view dashboard, generate report, interact with chart

**Convergence**: delta = 0 (all invariants satisfied)
**Evidence**: {API response, screenshot, Langfuse trace}
```

---

*Objective: telegram*
*Spec: .claude/specs/telegram/spec.yaml*
