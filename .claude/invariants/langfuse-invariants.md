# Langfuse Invariants

**Domain**: LLM Observability, Tracing, Scoring, Prompt Management
**Load when**: langfuse, trace, score, observe, LLM, evaluation, prompt

**Related**: [Integration Principles](../principles/integration-principles.md), [Principle #22], [Langfuse Guide](../../docs/guides/langfuse-integration.md)

---

## Critical Path

```
LLM Call → @observe Trace → Score Attachment → flush() → Dashboard
```

Every Langfuse operation must preserve this invariant: **Traces are captured, scores are attached, observability is non-blocking.**

---

## Level 4: Configuration Invariants

### Credentials (Doppler)
- [ ] `LANGFUSE_PUBLIC_KEY` set (all environments)
- [ ] `LANGFUSE_SECRET_KEY` set (all environments)
- [ ] `LANGFUSE_HOST` set (`https://us.cloud.langfuse.com`)

### Versioning (Doppler)
- [ ] `LANGFUSE_RELEASE` set with format `{env}-{version|branch}-{short_sha}`
- [ ] Version updated on each deployment (CI/CD sets automatically)
- [ ] Local dev uses `dev-local` or similar

### Environment Tagging (Doppler)
- [ ] `LANGFUSE_TRACING_ENVIRONMENT` set (`local`, `dev`, `stg`, `prd`)

### Python Constants
- [ ] Score names defined in `src/config/langfuse.py`
- [ ] Trace names follow convention (`analyze_ticker`, `test_scoring`)
- [ ] No hardcoded score names in business logic

### Verification Commands
```bash
# Check Doppler config
doppler secrets get LANGFUSE_PUBLIC_KEY -p dr-daily-report -c dev
doppler secrets get LANGFUSE_SECRET_KEY -p dr-daily-report -c dev
doppler secrets get LANGFUSE_RELEASE -p dr-daily-report -c dev

# Verify constants exist
grep -r "SCORE_NAMES" src/config/

# Check version format in CI
grep "LANGFUSE_RELEASE" .github/workflows/*.yml
```

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] Lambda → Langfuse API connectivity works
- [ ] HTTPS traffic allowed through security groups
- [ ] No firewall blocking `us.cloud.langfuse.com`

### Graceful Degradation
- [ ] App works when Langfuse unavailable
- [ ] No blocking on Langfuse operations
- [ ] Errors logged but not propagated to users

### SDK Initialization
- [ ] Client initialized once (singleton pattern)
- [ ] No repeated initialization per request
- [ ] Environment vars read at startup

### Verification Commands
```bash
# Test Langfuse connectivity from Lambda
/dev "test Langfuse connectivity"

# Verify non-blocking behavior
# (Run report generation, check response time doesn't include Langfuse latency)

# Check for singleton pattern
grep -A5 "Langfuse" src/integrations/langfuse_client.py | head -20
```

---

## Level 2: Data Invariants

### Trace Structure
- [ ] Traces have `name` (descriptive, not generic)
- [ ] Traces have `user_id` (for per-user analytics)
- [ ] Traces have `session_id` (for grouping related operations)
- [ ] Traces have `metadata` (ticker, workflow, model)

### Score Attachment
- [ ] Scores attached to correct trace (not orphaned)
- [ ] Score values in valid range (0-1 after normalization)
- [ ] Score names from approved list
- [ ] Score comments provide context

### Score Values
- [ ] `faithfulness` (0-100) → numeric accuracy
- [ ] `completeness` (0-100) → coverage of dimensions
- [ ] `reasoning_quality` (0-100) → clarity, structure
- [ ] `compliance` (0-100) → format adherence
- [ ] `consistency` (0-100) → logical consistency

### Data Quality
- [ ] No PII in trace inputs/outputs
- [ ] Metadata JSON-serializable
- [ ] Timestamps in correct timezone
- [ ] Large payloads truncated appropriately

### Verification Commands
```bash
# In Langfuse UI:
# 1. Navigate to Traces
# 2. Filter by recent time range
# 3. Click trace to verify:
#    - name is descriptive
#    - user_id present
#    - scores attached (5 scores per report)
#    - metadata complete

# Via API (if needed):
# Check trace has expected structure
```

---

## Level 1: Service Invariants

### Decorator Usage
- [ ] `@observe(name="...")` on entry points
- [ ] Name is descriptive (not `"process"`)
- [ ] Nested `@observe` creates proper span hierarchy
- [ ] No missing `@observe` on LLM-calling functions

### Flush Discipline
- [ ] `flush()` called before Lambda returns
- [ ] `flush()` in finally block (executes on error too)
- [ ] No multiple `flush()` calls per request
- [ ] Flush timeout appropriate (not blocking too long)

### Scoring Integration
- [ ] `score_current_trace()` within `@observe` context
- [ ] Scores computed after generation complete
- [ ] Batch scoring used for multiple scores
- [ ] Scoring errors don't fail main operation

### Error Handling
- [ ] Langfuse errors caught and logged
- [ ] Main operation continues on Langfuse failure
- [ ] Error traces still created (capture failures)
- [ ] No sensitive data in error logs

### Verification Commands
```bash
# Check decorator usage
grep -r "@observe" src/

# Check flush calls
grep -r "flush()" src/

# Verify scoring in workflow
grep -A10 "score_trace_batch" src/workflow/

# Check error handling
grep -B5 -A5 "except.*Langfuse" src/
```

---

## Level 0: User Invariants

### Trace Visibility
- [ ] User actions generate visible traces
- [ ] Trace name indicates what user did
- [ ] Metadata includes user context (ticker, etc.)
- [ ] Can filter by user_id in dashboard

### Score Visibility
- [ ] Scores appear on traces in dashboard
- [ ] Score values reflect actual quality
- [ ] Score comments explain reasoning
- [ ] Can analyze score trends over time

### Dashboard Usability
- [ ] Recent traces appear within minutes
- [ ] Can search/filter effectively
- [ ] Score distributions visible
- [ ] Can identify quality regressions

### Debugging Capability
- [ ] Can trace issue to specific generation
- [ ] Input/output visible for debugging
- [ ] Error traces capture failure details
- [ ] Can correlate with CloudWatch logs

### Verification Commands
```bash
# Generate a report and verify in Langfuse
# 1. Send /report ADVANC via Telegram
# 2. Open Langfuse dashboard
# 3. Filter traces by last 5 minutes
# 4. Verify:
#    - Trace appears with name "analyze_ticker"
#    - 5 scores attached
#    - Metadata includes ticker=ADVANC
#    - Can see LLM input/output
```

---

## Versioning Invariants

### Release Tracking
- [ ] Every deployment has unique `LANGFUSE_RELEASE`
- [ ] Format: `{env}-{version|branch}-{short_sha}`
- [ ] CI/CD sets version automatically
- [ ] Local dev has distinguishable version

### A/B Testing Capability
- [ ] Different versions can be compared in dashboard
- [ ] Score trends correlate with releases
- [ ] Can identify quality regression by version
- [ ] Rollback decisions informed by metrics

### Examples
```
prd-v1.2.3-abc1234     # Production release
stg-main-def5678       # Staging from main branch
dev-dev-ghi9012        # Dev environment
dev-local              # Local development
```

---

## Anti-Patterns (What Breaks Invariants)

| Anti-Pattern | Invariant Violated | Fix |
|--------------|-------------------|-----|
| Missing `flush()` | Level 1 (traces lost) | Add flush in finally block |
| Generic trace name | Level 2 (data quality) | Use descriptive names |
| Score outside @observe | Level 1 (orphaned score) | Score within decorated function |
| Hardcoded score names | Level 4 (config) | Use SCORE_NAMES constant |
| Blocking on heavy eval | Level 3 (degradation) | Use async for expensive scores |
| Environment-only version | Level 4 (versioning) | Include SHA in LANGFUSE_RELEASE |
| Log full prompts | Level 2 (data quality) | Truncate or mask sensitive content |

---

## New Score Integration Checklist

When adding a new score type:

### Configuration
- [ ] Add score name to `SCORE_NAMES` in `src/config/langfuse.py`
- [ ] Define score range (typically 0-100)
- [ ] Document what score measures

### Implementation
- [ ] Create scorer class/function
- [ ] Integrate into scoring pipeline
- [ ] Add to `score_trace_batch()` call
- [ ] Handle scoring errors gracefully

### Validation
- [ ] Score appears in Langfuse dashboard
- [ ] Values in expected range
- [ ] Comments provide useful context
- [ ] Trends can be analyzed

### Documentation
- [ ] Update Langfuse integration guide
- [ ] Add to SCHEMA.md
- [ ] Document interpretation guidelines

---

## Claiming "Langfuse Work Done"

```markdown
✅ Langfuse work complete: {description}

**Type**: {new instrumentation | new score | bug fix | config}

**Invariants Verified**:
- [x] Level 4: Credentials set, version format correct, constants defined
- [x] Level 3: Connectivity works, graceful degradation verified
- [x] Level 2: Traces structured correctly, scores attached
- [x] Level 1: @observe used, flush() called, errors handled
- [x] Level 0: Traces visible in dashboard, scores meaningful

**Confidence**: {HIGH | MEDIUM | LOW}
**Evidence**: {Langfuse trace URL, dashboard screenshot, test output}
```

---

*Domain: langfuse*
*Last updated: 2026-01-12*
