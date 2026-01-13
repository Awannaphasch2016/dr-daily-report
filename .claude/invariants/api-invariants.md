# API Invariants

**Domain**: API, Endpoints, Routes, Handlers, Contracts
**Load when**: API, endpoint, route, handler, FastAPI, Lambda, request, response

**Related**: [Integration Principles](../principles/integration-principles.md), [Principle #4, #8]

---

## Critical Path

```
Request → Validation → Handler → Response → Client
```

Every API operation must preserve this invariant: **Contracts are honored, errors are explicit.**

---

## Level 4: Configuration Invariants

### Lambda Configuration
- [ ] Handler path correct (`src.api.handler.handler`)
- [ ] Memory allocation appropriate (512MB minimum)
- [ ] Timeout set (30s for API, 900s for report generation)
- [ ] Environment variables configured

### API Gateway
- [ ] Routes mapped to Lambda
- [ ] CORS configured (if frontend calls API)
- [ ] Request/response content types defined
- [ ] API key configured (if required)

### Environment
- [ ] `AURORA_*` variables set (database access)
- [ ] `TZ = "Asia/Bangkok"` set
- [ ] Feature flags configured (if any)

### Verification Commands
```bash
# Check Lambda configuration
aws lambda get-function-configuration \
  --function-name dr-daily-report-telegram-api-dev

# Check API Gateway routes
aws apigatewayv2 get-routes --api-id <api-id>

# Verify env vars
doppler secrets -p dr-daily-report -c dev | grep AURORA
```

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] API Gateway → Lambda invocation works
- [ ] Lambda → Aurora connectivity works
- [ ] Lambda → external APIs accessible (if called)
- [ ] VPC configuration correct (if in VPC)

### Permissions
- [ ] Lambda execution role has required permissions
- [ ] API Gateway has invoke permission on Lambda
- [ ] No overly permissive IAM policies

### Network
- [ ] Security groups allow required traffic
- [ ] NAT Gateway configured (if Lambda needs internet)
- [ ] VPC endpoints configured (for AWS services)

### Verification Commands
```bash
# Test Lambda invocation
aws lambda invoke \
  --function-name dr-daily-report-telegram-api-dev \
  --payload '{"httpMethod":"GET","path":"/health"}' \
  /tmp/response.json && cat /tmp/response.json

# Test Aurora from Lambda
/dev "SELECT 1"

# Check security groups
aws ec2 describe-security-groups --group-ids <sg-id>
```

---

## Level 2: Data Invariants

### Request Validation
- [ ] Required fields enforced
- [ ] Type validation works (string, int, etc.)
- [ ] Value constraints enforced (min, max, enum)
- [ ] Invalid requests return 400 with details

### Response Schema
- [ ] Response matches documented schema
- [ ] No extra fields leaked (security)
- [ ] Timestamps in consistent format (ISO 8601)
- [ ] Numbers in consistent format (no floating point errors)

### Data Transformation
- [ ] Input sanitized (no SQL injection, XSS)
- [ ] Output encoded correctly (JSON, UTF-8)
- [ ] Sensitive data masked in logs
- [ ] PII handled per policy

### Verification Commands
```bash
# Test validation - missing required field
curl -X POST https://api.example.com/report \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 400 with validation error

# Test validation - invalid type
curl -X POST https://api.example.com/report \
  -H "Content-Type: application/json" \
  -d '{"ticker": 123}'
# Expected: 400 with type error

# Verify response schema
curl https://api.example.com/report/ADVANC | jq 'keys'
```

---

## Level 1: Service Invariants

### Status Codes
- [ ] 200 for successful GET/POST
- [ ] 201 for successful resource creation
- [ ] 400 for validation errors
- [ ] 401 for authentication failures
- [ ] 403 for authorization failures
- [ ] 404 for not found
- [ ] 500 for server errors (with error ID)

### Error Responses
- [ ] Consistent error format (`{error: string, details?: object}`)
- [ ] No stack traces in production errors
- [ ] Error IDs for correlation
- [ ] Actionable error messages

### Performance
- [ ] Response time < 500ms for read operations
- [ ] Response time < 30s for report generation
- [ ] No memory leaks
- [ ] Connection pool managed correctly

### Logging
- [ ] Request logged (method, path, user)
- [ ] Response logged (status, duration)
- [ ] Errors logged with stack trace
- [ ] Sensitive data NOT logged

### Verification Commands
```bash
# Test health endpoint
curl -w "\n%{http_code}\n" https://api.example.com/health
# Expected: 200

# Test error handling
curl -w "\n%{http_code}\n" https://api.example.com/report/INVALID_TICKER
# Expected: 404 with error message

# Check response time
time curl -s https://api.example.com/report/ADVANC > /dev/null

# Check logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '5 minutes ago' +%s000)
```

---

## Level 0: User Invariants

### Telegram Bot
- [ ] `/start` returns welcome message
- [ ] `/report TICKER` returns PDF within 30s
- [ ] `/watchlist` returns portfolio summary
- [ ] Invalid commands return helpful error
- [ ] Bot responds to callback queries

### Mini App API
- [ ] Dashboard data loads correctly
- [ ] Ticker list returns all 46 tickers
- [ ] Chart data includes recent dates
- [ ] Export generates valid file

### Error Experience
- [ ] User sees friendly error messages
- [ ] Errors suggest next action
- [ ] Timeout shows "please try again"
- [ ] Server errors show "contact support"

### Verification Commands
```bash
# Manual Telegram test
# Send: /report ADVANC
# Expected: PDF within 30s

# Test Mini App endpoint
curl https://api.example.com/v1/tickers | jq 'length'
# Expected: 46

# Test error message formatting
curl https://api.example.com/report/INVALID
# Expected: User-friendly error
```

---

## Contract Invariants

### API Versioning
- [ ] Version in URL path (`/v1/`, `/v2/`)
- [ ] Breaking changes increment major version
- [ ] Old versions supported during transition
- [ ] Deprecation warnings in responses

### Backward Compatibility
- [ ] New fields are additive (no removal)
- [ ] Optional fields have defaults
- [ ] Field types never change
- [ ] Enum values only added (not removed)

### Documentation
- [ ] OpenAPI spec matches implementation
- [ ] Examples in documentation work
- [ ] Error codes documented
- [ ] Rate limits documented

---

## Anti-Patterns (What Breaks Invariants)

| Anti-Pattern | Invariant Violated | Fix |
|--------------|-------------------|-----|
| Return 200 for errors | Level 1 (status codes) | Use appropriate status codes |
| Stack trace in response | Level 1 (error format) | Log error, return error ID |
| No input validation | Level 2 (request) | Use Pydantic models |
| Hardcoded timeout | Level 4 (config) | Use environment variable |
| Log password/token | Level 1 (logging) | Mask sensitive fields |
| Break API contract | Level 2 (schema) | Version the API |

---

## Endpoint Checklist Template

For each new endpoint:

### Design
- [ ] HTTP method appropriate (GET for read, POST for create)
- [ ] URL path follows convention (`/v1/resource/{id}`)
- [ ] Request body schema defined (Pydantic)
- [ ] Response body schema defined (Pydantic)
- [ ] Error responses defined

### Implementation
- [ ] Handler function created
- [ ] Input validation implemented
- [ ] Business logic in service layer
- [ ] Response serialization correct
- [ ] Error handling complete

### Testing
- [ ] Happy path test
- [ ] Validation error test
- [ ] Not found test
- [ ] Permission error test (if auth required)
- [ ] Integration test with database

### Deployment
- [ ] Route registered in API Gateway
- [ ] Lambda handler configured
- [ ] Environment variables set
- [ ] Smoke test passes

---

## Claiming "API Work Done"

```markdown
✅ API work complete: {endpoint description}

**Endpoint**: {METHOD /path}
**Type**: {new endpoint | modification | bug fix}

**Invariants Verified**:
- [x] Level 4: Lambda config correct, env vars set
- [x] Level 3: Connectivity works, permissions valid
- [x] Level 2: Validation works, response schema correct
- [x] Level 1: Status codes correct, errors formatted
- [x] Level 0: User experience works end-to-end

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {curl output, test results, CloudWatch logs}
```

---

*Domain: api*
*Last updated: 2026-01-12*
