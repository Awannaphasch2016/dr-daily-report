# Invariant Command

**Purpose**: Identify behavioral invariants that must remain true for a given goal, generating verification checklists before claiming "done"

**Core Principle**: "Done" means all relevant invariants verified, not just code written. This command makes implicit assumptions explicit.

**When to use**:
- Before starting implementation (know what must remain true)
- Before claiming "done" (verify invariant envelope)
- During code review (check invariants were considered)
- After incidents (identify which invariant was violated)

---

## Quick Reference

```bash
# Goal-based invariant identification
/invariant "deploy new Langfuse scoring feature"
/invariant "add new API endpoint for backtest"
/invariant "fix data migration bug"
/invariant "update frontend chart component"

# Domain-specific focus
/invariant deployment "release v1.2.3"
/invariant data "add new Aurora table"
/invariant api "new /v2/report endpoint"
/invariant langfuse "add compliance score"
/invariant frontend "ticker selection state"
```

---

## Invariant Hierarchy (Principle #25)

All invariants are organized by verification level:

| Level | Type | What to Verify | Example |
|-------|------|----------------|---------|
| **4** | Configuration | Settings are correct | Env vars set, constants defined |
| **3** | Infrastructure | Connectivity works | Lambda → Aurora, Lambda → S3 |
| **2** | Data | Data conditions hold | Schema valid, data fresh |
| **1** | Service | Service behavior correct | Lambda returns 200, API contract |
| **0** | User | User experience works | End-to-end flow succeeds |

**Verification order**: Always verify bottom-up (Level 4 → Level 0)

---

## Execution Flow

### Step 1: Parse Goal and Extract Context

```bash
/invariant "{goal}"
/invariant {domain} "{goal}"

# Examples:
/invariant "deploy new scoring feature"
  → Domain: deployment (detected from "deploy")
  → Task: new feature
  → Components: scoring, Langfuse

/invariant data "add ticker_fundamentals table"
  → Domain: data (explicit)
  → Task: schema change
  → Components: Aurora, migrations
```

---

### Step 2: Goal → Domain Mapping

| Keywords in Goal | Primary Domain | Secondary Domains |
|-----------------|----------------|-------------------|
| deploy, release, ship, promote | deployment | - |
| database, migration, aurora, table, schema | data | deployment |
| API, endpoint, route, handler | api | deployment |
| langfuse, trace, score, observe | langfuse | api |
| frontend, UI, chart, component, state | frontend | api |
| telegram, bot, webhook, message | telegram | api |
| test, coverage, assertion | testing | - |
| lambda, timeout, memory, concurrency | infrastructure | deployment |

---

### Step 3: Load Relevant Invariant Files

Based on detected domain(s), load from `.claude/invariants/`:

```
.claude/invariants/
├── system-invariants.md      (always loaded - critical path)
├── deployment-invariants.md  (if deploying)
├── data-invariants.md        (if data/schema work)
├── api-invariants.md         (if API changes)
├── langfuse-invariants.md    (if LLM observability)
├── frontend-invariants.md    (if UI changes)
└── telegram-invariants.md    (if bot changes)
```

---

### Step 4: Generate Verification Checklist

**Output format**:

```markdown
# Invariant Verification: {goal}

**Domain(s)**: {detected domains}
**Risk Level**: {LOW | MEDIUM | HIGH | CRITICAL}

---

## Pre-Implementation Invariants (State Before)

Before making changes, verify current state:

### Level 4: Configuration
- [ ] {Invariant 1}
- [ ] {Invariant 2}

### Level 3: Infrastructure
- [ ] {Invariant 1}

### Level 2: Data
- [ ] {Invariant 1}

### Level 1: Service
- [ ] {Invariant 1}

### Level 0: User
- [ ] {Invariant 1}

---

## Post-Implementation Invariants (State After)

After changes, verify these still hold:

### Level 4: Configuration
- [ ] {New config invariant}
- [ ] {Existing config still valid}

### Level 3: Infrastructure
- [ ] {Connectivity invariant}

### Level 2: Data
- [ ] {Data integrity invariant}

### Level 1: Service
- [ ] {Service behavior invariant}

### Level 0: User
- [ ] {User experience invariant}

---

## Verification Commands

```bash
# Level 4: Configuration
{command to verify config}

# Level 3: Infrastructure
{command to verify connectivity}

# Level 2: Data
{command to verify data}

# Level 1: Service
{command to verify service}

# Level 0: User
{manual test or E2E command}
```

---

## Claiming "Done"

Only claim done when ALL invariants verified:

```markdown
✅ Implementation complete: {goal}

**Invariants Verified**:
- [x] Level 4: {summary}
- [x] Level 3: {summary}
- [x] Level 2: {summary}
- [x] Level 1: {summary}
- [x] Level 0: {summary}

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {links to verification output}
```
```

---

### Step 5: Risk Assessment

**Risk factors**:

| Factor | Weight | Description |
|--------|--------|-------------|
| Cross-boundary change | HIGH | Affects multiple components |
| Data mutation | HIGH | Modifies existing data |
| User-facing change | MEDIUM | Visible to end users |
| Configuration change | MEDIUM | Env vars, secrets |
| Code-only change | LOW | Internal refactoring |

**Risk level calculation**:
- CRITICAL: Data mutation + User-facing
- HIGH: Cross-boundary OR Data mutation
- MEDIUM: User-facing OR Configuration
- LOW: Code-only internal changes

---

## Domain-Specific Invariant Templates

### Deployment Domain

```markdown
## Deployment Invariants: {feature}

### Level 4: Configuration
- [ ] New env vars added to Doppler (all environments)
- [ ] Terraform variables updated
- [ ] GitHub secrets configured (if needed)
- [ ] LANGFUSE_RELEASE version updated

### Level 3: Infrastructure
- [ ] Lambda deployment succeeded
- [ ] Database migration applied (if schema change)
- [ ] IAM permissions granted (if new resources)

### Level 2: Data
- [ ] No data corruption from migration
- [ ] Rollback path tested
- [ ] Cache invalidated (if cached data changed)

### Level 1: Service
- [ ] Health check passes
- [ ] Smoke test succeeds
- [ ] No 5xx errors in first 5 minutes
- [ ] Logs show expected behavior

### Level 0: User
- [ ] User flow works end-to-end
- [ ] Response time acceptable
- [ ] Error messages helpful (if errors expected)
```

### Data Domain

```markdown
## Data Invariants: {change}

### Level 4: Configuration
- [ ] Table name added to table_names.py (if new table)
- [ ] TZ env var set (Bangkok timezone)

### Level 3: Infrastructure
- [ ] Lambda → Aurora connectivity
- [ ] Connection pool healthy

### Level 2: Data
- [ ] Schema matches code expectations
- [ ] Foreign keys valid (no orphans)
- [ ] Data types correct (especially JSON, DECIMAL)
- [ ] Timezone consistent (Bangkok)

### Level 1: Service
- [ ] Queries return expected results
- [ ] No SQL injection vulnerabilities
- [ ] Transactions commit correctly

### Level 0: User
- [ ] Reports show correct data
- [ ] No missing data in UI
```

### API Domain

```markdown
## API Invariants: {endpoint}

### Level 4: Configuration
- [ ] Route registered in API Gateway
- [ ] Lambda handler configured

### Level 3: Infrastructure
- [ ] API Gateway → Lambda connectivity
- [ ] CORS headers configured

### Level 2: Data
- [ ] Request validation works
- [ ] Response schema correct

### Level 1: Service
- [ ] Returns correct status codes
- [ ] Error responses follow standard format
- [ ] Rate limiting works (if applicable)

### Level 0: User
- [ ] Frontend can call endpoint
- [ ] Response renders correctly
```

### Langfuse Domain

```markdown
## Langfuse Invariants: {feature}

### Level 4: Configuration
- [ ] LANGFUSE_PUBLIC_KEY set
- [ ] LANGFUSE_SECRET_KEY set
- [ ] LANGFUSE_RELEASE set with version format
- [ ] Score names in SCORE_NAMES constant

### Level 3: Infrastructure
- [ ] Lambda → Langfuse API connectivity
- [ ] Graceful degradation if Langfuse unavailable

### Level 2: Data
- [ ] Traces appear in dashboard
- [ ] Scores attached to correct traces
- [ ] Metadata captured correctly

### Level 1: Service
- [ ] @observe decorator on entry points
- [ ] flush() called before Lambda returns
- [ ] No blocking on Langfuse operations

### Level 0: User
- [ ] User action generates visible trace
- [ ] Scores reflect actual quality
```

### Frontend Domain

```markdown
## Frontend Invariants: {component}

### Level 4: Configuration
- [ ] Environment variables set (API URLs)
- [ ] Build configuration correct

### Level 3: Infrastructure
- [ ] CloudFront serves assets
- [ ] API endpoints accessible

### Level 2: Data
- [ ] State shape matches types
- [ ] Data never shrinks (monotonic invariant)
- [ ] No stale data displayed

### Level 1: Service
- [ ] Components render without error
- [ ] State updates correctly
- [ ] API calls succeed

### Level 0: User
- [ ] Page loads correctly
- [ ] Interactions work as expected
- [ ] No visual glitches
```

---

## Examples

### Example 1: Deployment Goal

```bash
/invariant "deploy new Langfuse compliance score"
```

**Output**:
```markdown
# Invariant Verification: Deploy new Langfuse compliance score

**Domain(s)**: deployment, langfuse
**Risk Level**: MEDIUM (user-facing + configuration)

---

## Pre-Implementation Invariants

### Level 4: Configuration
- [ ] Current LANGFUSE_RELEASE version noted
- [ ] SCORE_NAMES constant exists

### Level 1: Service
- [ ] Existing scores still work
- [ ] Lambda health check passes

### Level 0: User
- [ ] Existing traces visible in Langfuse

---

## Post-Implementation Invariants

### Level 4: Configuration
- [ ] "compliance" added to SCORE_NAMES constant
- [ ] LANGFUSE_RELEASE updated with new version
- [ ] Doppler secrets unchanged (no new keys needed)

### Level 3: Infrastructure
- [ ] Lambda → Langfuse connectivity works

### Level 2: Data
- [ ] New compliance scores appear in Langfuse
- [ ] Scores attached to correct traces
- [ ] Score values in valid range (0.0-1.0)

### Level 1: Service
- [ ] ComplianceScorer.score() returns valid scores
- [ ] flush() called after scoring
- [ ] No errors in CloudWatch logs

### Level 0: User
- [ ] Generate report → see compliance score in Langfuse
- [ ] Score reflects actual compliance

---

## Verification Commands

```bash
# Level 4: Configuration
grep "compliance" src/scoring/score_names.py
doppler secrets get LANGFUSE_RELEASE -p dr-daily-report -c dev

# Level 3: Infrastructure
/dev "test Langfuse connectivity"

# Level 2: Data
# Check Langfuse dashboard for new scores

# Level 1: Service
/dev "invoke report-worker with test ticker"
aws logs tail /aws/lambda/dr-daily-report-report-worker-dev --since 5m

# Level 0: User
# Generate report for ADVANC, verify score in Langfuse
```

---

## Claiming "Done"

```markdown
✅ Implementation complete: Deploy new Langfuse compliance score

**Invariants Verified**:
- [x] Level 4: SCORE_NAMES updated, LANGFUSE_RELEASE = dev-v1.2.3-abc1234
- [x] Level 3: Langfuse API reachable from Lambda
- [x] Level 2: Compliance scores visible in dashboard
- [x] Level 1: No errors in CloudWatch, scores in valid range
- [x] Level 0: ADVANC report shows compliance score

**Confidence**: HIGH
**Evidence**: Langfuse trace ID abc-123, CloudWatch logs attached
```
```

### Example 2: Data Goal

```bash
/invariant data "add ticker_fundamentals table"
```

**Output**:
```markdown
# Invariant Verification: Add ticker_fundamentals table

**Domain(s)**: data, deployment
**Risk Level**: HIGH (schema change)

---

## Pre-Implementation Invariants

### Level 2: Data
- [ ] Existing tables unchanged
- [ ] No foreign key conflicts

---

## Post-Implementation Invariants

### Level 4: Configuration
- [ ] TICKER_FUNDAMENTALS added to table_names.py
- [ ] Migration file created (immutable)

### Level 3: Infrastructure
- [ ] Lambda can query new table

### Level 2: Data
- [ ] Table created with correct schema
- [ ] Foreign key to ticker_master valid
- [ ] Indexes created for query patterns

### Level 1: Service
- [ ] Queries return expected results
- [ ] No performance regression

### Level 0: User
- [ ] Reports can access fundamental data

---

## Verification Commands

```bash
# Level 4: Configuration
grep "TICKER_FUNDAMENTALS" src/data/aurora/table_names.py

# Level 2: Data
/dev "DESCRIBE ticker_fundamentals"
/dev "SELECT COUNT(*) FROM ticker_fundamentals"

# Level 1: Service
/dev "SELECT * FROM ticker_fundamentals WHERE symbol = 'ADVANC' LIMIT 1"
```
```

---

## Integration with Other Commands

### Workflow: Plan → Invariant → Implement → Verify

```bash
# 1. Enter plan mode for complex task
EnterPlanMode

# 2. Identify invariants before implementing
/invariant "deploy new scoring feature"

# 3. Implement with invariants in mind

# 4. Verify invariants before claiming done
# (Use generated checklist)

# 5. Document if significant
/journal pattern "Invariant verification saved deployment"
```

### Workflow: Incident → Invariant → Reconcile → Verify

```bash
# 1. Incident occurs
# "Users report missing scores in Langfuse"

# 2. Identify which invariant was violated
/invariant langfuse "score submission"
# → Reveals: Level 1 invariant "flush() called" was violated

# 3. Generate fixes for violations
/reconcile langfuse
# → Generates specific fixes to add flush() calls

# 4. Apply fixes
/reconcile langfuse --apply

# 5. Verify all invariants restored
/invariant langfuse "score submission"
# → All invariants satisfied (delta = 0)
```

---

## Tips

### Do
- **Run before starting** (know what must remain true)
- **Check all levels** (bottom-up verification)
- **Document evidence** (link to logs, traces, tests)
- **Use verification commands** (don't just assume)

### Don't
- **Skip levels** (lower levels are prerequisites)
- **Assume success** (verify with evidence)
- **Ignore pre-implementation** (current state matters)
- **Forget user level** (end-to-end is ultimate test)

---

## Invariant Registry

All curated invariants are stored in `.claude/invariants/`:

| File | Domain | When to Load |
|------|--------|--------------|
| `system-invariants.md` | Core | Always (critical path) |
| `deployment-invariants.md` | Deployment | deploy, release, ship |
| `data-invariants.md` | Data | database, migration, aurora |
| `api-invariants.md` | API | endpoint, route, handler |
| `langfuse-invariants.md` | Langfuse | trace, score, observe |
| `frontend-invariants.md` | Frontend | UI, chart, component |
| `telegram-invariants.md` | Telegram | bot, webhook, message |

---

## See Also

- **Reconcile Command**: [/reconcile](./reconcile.md) - Converge violations back to compliance
- **Principle #25**: [Behavioral Invariant Verification](../../CLAUDE.md)
- **Guide**: [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md)
- **System Invariants**: [system-invariants.md](../invariants/system-invariants.md)
- **Invariants Directory**: [.claude/invariants/](../invariants/) - Domain-specific invariant files
- **Testing Skill**: [testing-workflow](../skills/testing-workflow/) - Invariant testing patterns
- **Deployment Skill**: [deployment](../skills/deployment/) - Deployment invariant verification

---

*Command: /invariant*
*Related: Principle #25 (Behavioral Invariant Verification)*
*Complements: /reconcile (converge violations to compliance)*
