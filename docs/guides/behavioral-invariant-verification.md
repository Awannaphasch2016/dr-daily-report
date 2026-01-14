# Behavioral Invariant Verification Guide

## Overview

Every implementation operates within an **invariant envelope** - the set of behaviors that MUST remain true for the system to function correctly. This guide provides comprehensive patterns for identifying, stating, and verifying behavioral invariants.

**Core Insight**: When Claude (or any agent) claims "✅ Done", that claim has weak epistemic weight unless the invariant envelope has been explicitly verified. "Code deployed" ≠ "System works".

---

## Why This Matters

### The Problem

| What We Say | What We Mean | What's Actually Verified |
|-------------|--------------|-------------------------|
| "Implementation complete" | Code changes deployed | Exit code = 0 |
| "Feature works" | User can use feature | Lambda returns 200 |
| "Bug fixed" | Issue resolved | Test passes |

**Gap**: None of these verify that the **system still works as a whole**.

### Real Incidents Caused by Implicit Invariants

| Incident | Implicit Assumption | What Broke |
|----------|---------------------|-----------|
| LINE bot 7-day outage | "Lambda imports work" | ImportError at runtime |
| ETL timezone bug | "TZ env var is set" | Missing configuration |
| NAT Gateway timeout | "Lambda → S3 path works" | Network saturation |
| Staging silent failure | "Webhook routes to Lambda" | Wrong channel credentials |

**Pattern**: Every incident involved an implicit invariant that was never explicitly stated or verified.

### Surfacing Implicit Assumptions with /qna

Before implementation, use `/qna` to surface implicit assumptions that might become implicit invariants:

```bash
/qna "deploy new caching feature"
```

**What /qna reveals**:
- **Confident knowledge**: Facts you know with certainty (from code, docs)
- **Assumptions**: Beliefs you've inferred but haven't verified
- **Knowledge gaps**: Information you need but don't have

**Example output**:
```
Confident: "Lambda uses Python 3.11"
Assumed: "Cache invalidates on data change" ← Might be wrong!
Unknown: "How TTL is configured"
```

By surfacing assumptions BEFORE implementation, you can convert them into explicit invariants and verify them, preventing incidents like those above.

**See also**: [/qna command](../../.claude/commands/qna.md)

---

## Invariant Hierarchy

Invariants exist at multiple levels. Higher levels depend on lower levels.

```
┌─────────────────────────────────────────────────────────────┐
│ Level 0: USER-FACING BEHAVIOR                               │
│ "User can send /report and receive PDF via Telegram"        │
├─────────────────────────────────────────────────────────────┤
│ Level 1: SERVICE BEHAVIOR                                   │
│ "telegram-api Lambda returns valid report payload"          │
├─────────────────────────────────────────────────────────────┤
│ Level 2: DATA BEHAVIOR                                      │
│ "Aurora has today's price data for requested ticker"        │
├─────────────────────────────────────────────────────────────┤
│ Level 3: INFRASTRUCTURE BEHAVIOR                            │
│ "Lambda can connect to Aurora within timeout"               │
├─────────────────────────────────────────────────────────────┤
│ Level 4: CONFIGURATION BEHAVIOR                             │
│ "Migrations applied, env vars set, IAM policies attached"   │
└─────────────────────────────────────────────────────────────┘
```

### Level Definitions

#### Level 0: User-Facing Behavior
What the end user experiences. The ultimate ground truth.

**Examples**:
- User sends `/report AAPL` → receives PDF in Telegram
- User opens frontend → sees chart with current data
- User clicks export → downloads CSV file

**Verification**: Manual test or E2E automation with real user flow.

#### Level 1: Service Behavior
What individual services/Lambdas produce.

**Examples**:
- `telegram-api` returns `{"status": "success", "report_url": "..."}`
- `report-worker` generates valid PDF bytes
- API Gateway routes request to correct Lambda

**Verification**: Invoke Lambda directly, check response structure.

#### Level 2: Data Behavior
What data exists and its correctness.

**Examples**:
- `daily_prices` table has rows for today
- Precomputed reports exist for all 46 tickers
- S3 bucket contains required static assets

**Verification**: Query Aurora, list S3 objects, check data freshness.

#### Level 3: Infrastructure Behavior
Connectivity and resource availability.

**Examples**:
- Lambda → Aurora connection succeeds
- Lambda → S3 upload works
- VPC endpoints are correctly configured

**Verification**: Network tests, connection pool health, timeout checks.

#### Level 4: Configuration Behavior
Static configuration that enables the system.

**Examples**:
- All migrations applied to Aurora
- Environment variables set in Lambda
- IAM policies allow required actions
- Doppler secrets accessible

**Verification**: Describe resources, check env vars, validate IAM.

---

## Implementation Workflow

### Before Implementation: State Invariant Envelope

Before starting any implementation, explicitly state:

```markdown
## Invariant Envelope

**What I'm changing**: {description}

**Invariants that MUST remain true**:

### Level 0 (User)
- [ ] User can send /report and receive response

### Level 1 (Service)
- [ ] telegram-api Lambda responds to webhook
- [ ] report-worker generates valid PDF

### Level 2 (Data)
- [ ] Aurora has price data (not affected by this change)

### Level 3 (Infrastructure)
- [ ] Lambda → Aurora connectivity (not affected)

### Level 4 (Configuration)
- [ ] New env var X must be set in Doppler/Terraform
```

**Key Questions**:
1. What behaviors could this change break?
2. What implicit assumptions am I making?
3. What MUST be true for this to work?

### During Implementation: Don't Violate Invariants

As you implement:
- Check each change against stated invariants
- If scope expands, add new invariants
- If you discover implicit invariants, make them explicit

**Anti-pattern**: Proceeding when you realize an invariant might be violated.

### After Implementation: Verify Invariant Envelope

Systematically verify each level that could be affected:

```markdown
## Invariant Verification

### Level 4 (Configuration) ✅
- [x] New env var `FEATURE_FLAG_X` added to Doppler dev config
- [x] Terraform updated with new variable
- [x] Verified: `doppler run -- printenv | grep FEATURE_FLAG_X`

### Level 3 (Infrastructure) ✅
- [x] Lambda → Aurora: `SELECT 1` succeeds
- [x] No new infrastructure dependencies

### Level 2 (Data) ✅
- [x] `SELECT COUNT(*) FROM daily_prices WHERE date = CURDATE()` → 46 rows
- [x] Data schema unchanged

### Level 1 (Service) ✅
- [x] `aws lambda invoke --function-name telegram-api-dev` → 200
- [x] Response contains expected fields

### Level 0 (User) ✅
- [x] Sent `/report AAPL` via Telegram → received PDF
- [x] PDF contains correct data
```

---

## Verification Strength by Level

Apply Progressive Evidence Strengthening (Principle #2) to invariant verification:

| Level | Layer 1 (Weak) | Layer 2 | Layer 3 | Layer 4 (Strong) |
|-------|----------------|---------|---------|------------------|
| Level 0 | N/A | N/A | Logs show success | User received message |
| Level 1 | Exit code 0 | HTTP 200 | Logs show processing | Response validates |
| Level 2 | Query succeeds | Row count > 0 | Data timestamp recent | Data matches source |
| Level 3 | No timeout | Connection opened | Query executed | Round-trip successful |
| Level 4 | Describe succeeds | Value exists | Value is correct | Dependent service works |

**Critical invariants require Layer 4 verification**.

---

## Invariant Checklist Template

Use this template for any implementation:

```markdown
# Invariant Checklist: {Feature/Change Name}

## Pre-Implementation

### Invariant Envelope
**Scope**: {What's being changed}

**Level 0 (User)**:
- [ ] {User behavior that must work}

**Level 1 (Service)**:
- [ ] {Service behavior that must work}

**Level 2 (Data)**:
- [ ] {Data condition that must hold}

**Level 3 (Infrastructure)**:
- [ ] {Connectivity that must work}

**Level 4 (Configuration)**:
- [ ] {Configuration that must be set}

### Assumptions
- {Assumption 1}
- {Assumption 2}

---

## Post-Implementation

### Verification Results

**Level 4 (Configuration)**:
- [ ] {Check}: {Result}

**Level 3 (Infrastructure)**:
- [ ] {Check}: {Result}

**Level 2 (Data)**:
- [ ] {Check}: {Result}

**Level 1 (Service)**:
- [ ] {Check}: {Result}

**Level 0 (User)**:
- [ ] {Check}: {Result}

### Evidence
- {Link to logs}
- {Screenshot/output}

### Confidence
- [ ] HIGH: All levels verified to Layer 4
- [ ] MEDIUM: Critical levels verified, others to Layer 2
- [ ] LOW: Partial verification only

---

## Claiming "Done"

**Implementation complete**: {timestamp}

**Invariants verified**: {count}/{total}

**Verification evidence**: {links}

**Confidence**: HIGH | MEDIUM | LOW
```

---

## Project-Specific Invariants

### This Project's Level 0 Invariants

These are the user-facing behaviors that define system success:

```markdown
## User-Facing Invariants

### Telegram Bot
- [ ] User sends `/start` → receives welcome message
- [ ] User sends `/report TICKER` → receives PDF report
- [ ] User sends `/watchlist` → receives portfolio summary

### LINE Bot (Legacy - Maintenance Mode)
- [ ] User sends message → receives response
- [ ] Webhook processes without timeout

### Frontend (Telegram Mini App)
- [ ] User opens app → sees dashboard
- [ ] User views chart → sees current data
- [ ] User exports data → downloads file
```

### This Project's Critical Path

The minimum invariants that guarantee system works:

```
1. Telegram webhook receives message
   ↓
2. telegram-api Lambda invoked
   ↓
3. Lambda can query Aurora
   ↓
4. Aurora has price data
   ↓
5. Report generated successfully
   ↓
6. User receives response
```

**If any link breaks, user experience fails.**

---

## Integration with Deployment Workflow

### Pre-Deployment Invariant Check

Before deploying:

```bash
# Level 4: Configuration
/dev "verify all env vars set for new code"
doppler run --config dev -- printenv | grep REQUIRED_VAR

# Level 3: Infrastructure
/dev "test Aurora connectivity"
aws lambda invoke --function-name telegram-api-dev --payload '{"test":"aurora"}'

# Level 2: Data
/dev "verify data freshness"
# SELECT MAX(date) FROM daily_prices

# Level 1: Service (smoke test on dev)
/dev "invoke Lambda health check"
```

### Post-Deployment Invariant Check

After deploying:

```bash
# Level 1: Service responds
/stg "verify Lambda responds"

# Level 0: User flow works
/stg "send test message to staging bot"
# Or: Manual test via Telegram
```

### Invariant Verification in `/deploy`

The deployment workflow should include:

```markdown
## Deployment Checklist

### Pre-Deploy
- [ ] State invariant envelope for this deployment
- [ ] Verify Level 4 (configuration) in target environment

### Deploy
- [ ] Deploy code changes

### Post-Deploy
- [ ] Verify Level 3 (infrastructure) - connectivity
- [ ] Verify Level 2 (data) - data availability
- [ ] Verify Level 1 (service) - Lambda responds correctly
- [ ] Verify Level 0 (user) - end-to-end test

### Claim "Done"
- [ ] All invariants verified
- [ ] Evidence collected
- [ ] Confidence level: HIGH
```

---

## Cascade Violation Pattern

**Key Learning**: A single visible symptom often masks multiple sequential dependencies. When one fix reveals another violation, you're experiencing a **cascade**—not a simple bug.

### The Problem

Traditional debugging fixes one violation, then discovers another:

```
❌ Wrong approach (fix-reveal-fix loop):
┌──────────────────────────────────────────────────────────────────┐
│ Symptom: "No markets found" in UI                                │
│    ↓                                                             │
│ Fix 1: Found wrong API URL → Fixed frontend                      │
│    ↓                                                             │
│ NEW symptom: CORS error                                          │
│    ↓                                                             │
│ Fix 2: Added CloudFront to CORS → Fixed                          │
│    ↓                                                             │
│ NEW symptom: API returns empty results                           │
│    ↓                                                             │
│ Fix 3: Found missing table → Created it                          │
│    ↓                                                             │
│ NEW symptom: table empty                                         │
│    ↓                                                             │
│ ... (continues for 6+ iterations)                                │
└──────────────────────────────────────────────────────────────────┘
```

This is inefficient because each fix only reveals the next hidden violation.

### The Solution: Pre-Scan ALL Levels

Before fixing anything, scan ALL invariant levels (4→3→2→1→0) to build a complete violation map:

```
✅ Correct approach (pre-scan then fix):
┌──────────────────────────────────────────────────────────────────┐
│ Step 1: PRE-SCAN ALL LEVELS                                      │
│                                                                  │
│ L4 Config:  ❌ Wrong API URL, ❌ Missing CORS origin              │
│ L3 Infra:   ✅ Lambda deployed, ✅ API Gateway active             │
│ L2 Schema:  ❌ precomputed_reports missing                        │
│ L2 Data:    ❌ No reports populated                               │
│ L1 Service: ❌ Cache stale                                        │
│ L0 User:    ❌ "No markets found"                                 │
│                                                                  │
│ Step 2: BUILD DEPENDENCY GRAPH                                   │
│                                                                  │
│ Config → Schema → Data → Cache → UI                              │
│                                                                  │
│ Step 3: FIX IN DEPENDENCY ORDER                                  │
│                                                                  │
│ 1. Fix API URL (L4)                                              │
│ 2. Add CORS origin (L4)                                          │
│ 3. Create table (L2)                                             │
│ 4. Populate data (L2)                                            │
│ 5. Force refresh cache (L1)                                      │
│ 6. Verify UI (L0)                                                │
│                                                                  │
│ Step 4: VERIFY DELTA = 0                                         │
└──────────────────────────────────────────────────────────────────┘
```

### Dependency Order

Violations have dependencies. Fix in this order:

| Order | Layer | Examples | Why First |
|-------|-------|----------|-----------|
| 1 | Config (L4) | URLs, CORS, env vars | Everything needs correct addressing |
| 2 | Schema (L2) | Tables, columns | Data needs structure |
| 3 | Data (L2) | Rows, relationships | Services need data |
| 4 | Cache (L1) | Rankings, computed values | Derived from data |
| 5 | User (L0) | UI verification | Depends on everything |

### Cache Invalidation Rule

**Critical**: After populating data, cache may still be stale. Always:

1. Check cache TTL (is it using old data?)
2. Force refresh if needed: `?force_refresh=true`
3. Verify cache reflects new data before checking L0

```bash
# After populating precomputed_reports:
curl "https://{api}/api/v1/rankings?force_refresh=true"

# Verify cache now has data:
curl "https://{api}/api/v1/rankings" | jq '.results[0].chart_data != null'
```

### When to Suspect a Cascade

| Signal | Meaning |
|--------|---------|
| Fix one thing, another breaks | Hidden dependencies |
| L0 symptom, L4 root cause | Long dependency chain |
| "It worked in dev" | Environment delta |
| New environment, old code | Missing transfer steps |

### Real Example: Production Telegram Mini App

**Visible symptom**: "No markets found" in production UI

**Actual cascade** (6 violations in dependency order):
1. ❌ L4: Frontend calling dev API URL (wrong environment)
2. ❌ L4: CORS missing production CloudFront domain
3. ❌ L2: precomputed_reports table missing
4. ❌ L2: daily_indicators table missing
5. ❌ L2: No report data populated
6. ❌ L1: Rankings cache stale (populated before data existed)

**Solution**: Pre-scan revealed all 6, fixed in order, single reconciliation pass.

See [Environment Provisioning Invariants](../../.claude/invariants/environment-provisioning-invariants.md) for complete checklist.

---

## Anti-Patterns

### 1. "Done" Without Stating Invariants

**Bad**:
```markdown
✅ Implementation complete
- Added new feature X
- Deployed to dev
```

**Good**:
```markdown
✅ Implementation complete

**Invariants Verified**:
- [x] Level 0: User can use feature X
- [x] Level 1: Lambda returns correct response
- [x] Level 2: Data persisted correctly
- [x] Level 3: No new infrastructure dependencies
- [x] Level 4: New env var set in Doppler
```

### 2. Verifying Only Changed Component

**Bad**: "I changed the report generator, so I tested report generation."

**Good**: "I changed the report generator, so I verified:
- Report generation works (Level 1)
- User receives correct report (Level 0)
- No regression in related features (Level 0)"

### 3. Layer 1 Verification Only

**Bad**: "Lambda returned 200, so it works."

**Good**: "Lambda returned 200 (Layer 1), response contains expected fields (Layer 2), logs show correct processing (Layer 3), user received message (Layer 4)."

### 4. Implicit Assumptions

**Bad**: Deploying code that requires new env var without setting it.

**Good**: Stating "This code requires `NEW_VAR` to be set" → Setting it → Verifying it's accessible.

---

## Verification Commands by Level

### Level 4 (Configuration)

```bash
# Check env vars
/dev "verify LANGFUSE_RELEASE env var is set"
doppler run --config dev -- printenv | grep LANGFUSE_RELEASE

# Check migrations
/dev "DESCRIBE daily_prices"
/dev "SHOW TABLES"

# Check IAM
aws iam get-role-policy --role-name lambda-role --policy-name s3-access
```

### Level 3 (Infrastructure)

```bash
# Aurora connectivity
/dev "test Aurora connection"
# Lambda invoke with connectivity test payload

# S3 connectivity
/dev "list S3 bucket contents"

# Network path
/dev "check VPC endpoint status"
```

### Level 2 (Data)

```bash
# Data freshness
/dev "SELECT MAX(date) FROM daily_prices"

# Data completeness
/dev "SELECT COUNT(DISTINCT symbol) FROM daily_prices WHERE date = CURDATE()"

# Precomputed data
/dev "check precomputed reports exist"
```

### Level 1 (Service)

```bash
# Lambda health
/dev "invoke telegram-api health check"

# API response
/dev "test API endpoint response"

# Error rate
/dev "check error rate in last 30 minutes"
```

### Level 0 (User)

```bash
# End-to-end test
# Manual: Send message to Telegram bot
# Or: Automated E2E test

/dev "send test message to dev bot"
# Verify user receives response
```

---

## Slash Commands: The Invariant Feedback Loop

Two slash commands complete the invariant workflow:

### /invariant - Identify What Must Hold (Divergent)

Use `/invariant` to identify invariants for a goal:

```bash
# Goal-based invariant identification
/invariant "deploy new Langfuse scoring feature"
/invariant "add new API endpoint for backtest"

# Domain-specific focus
/invariant deployment "release v1.2.3"
/invariant data "add new Aurora table"
```

**Output**: Checklist of invariants organized by level (0-4).

### /reconcile - Converge Violations to Compliance (Convergent)

Use `/reconcile` when violations are found:

```bash
# Reconcile by domain
/reconcile deployment
/reconcile langfuse

# Preview fixes without applying
/reconcile deployment --preview

# Apply fixes with confirmation
/reconcile deployment --apply
```

**Output**: Specific fix actions to converge delta to zero.

### The Complete Workflow

```
/invariant    →    /reconcile    →    /invariant
  (detect)          (converge)        (verify)
     ↓                  ↓                ↓
  Identify         Generate          Confirm
  invariants       fix actions       delta = 0
```

**Example**:
```bash
# 1. Before implementation: identify invariants
/invariant "deploy new scoring feature"

# 2. Implement feature

# 3. Check for violations
/invariant "deploy new scoring feature"
# → Shows: 2 violations found

# 4. Generate and apply fixes
/reconcile langfuse
/reconcile langfuse --apply

# 5. Verify convergence (delta = 0)
/invariant "deploy new scoring feature"
# → All invariants satisfied
```

See [/invariant command](../../.claude/commands/invariant.md) and [/reconcile command](../../.claude/commands/reconcile.md) for full documentation.

---

## Related Principles

- **Principle #2 (Progressive Evidence Strengthening)**: Invariant verification uses evidence hierarchy
- **Principle #15 (Infrastructure-Application Contract)**: Infrastructure invariants are part of envelope
- **Principle #19 (Cross-Boundary Contract Testing)**: Boundaries define invariant levels
- **Principle #20 (Execution Boundary Discipline)**: Invariants exist at each execution boundary

---

## See Also

- [CLAUDE.md - Principle #25](../../.claude/CLAUDE.md) - Behavioral Invariant Verification (Tier-0)
- [Thinking Process Architecture - Section 11.5](../../.claude/diagrams/thinking-process-architecture.md#115-invariant-feedback-loop-convergence-pattern) - Invariant Feedback Loop pattern
- [/invariant command](../../.claude/commands/invariant.md) - Identify invariants for a goal
- [/reconcile command](../../.claude/commands/reconcile.md) - Converge violations to compliance
- [Invariants Directory](../../.claude/invariants/) - Domain-specific invariant files
- [Cross-Boundary Contract Testing](cross-boundary-contract-testing.md)
- [Execution Boundary Discipline](execution-boundary-discipline.md)
- [Deployment Skill](../../.claude/skills/deployment/)
