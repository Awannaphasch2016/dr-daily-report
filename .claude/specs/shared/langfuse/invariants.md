# Langfuse Observability Invariants

**Objective**: Shared observability layer
**Last Updated**: 2026-01-13

---

## Critical Path

```
LLM Operation → @observe Decorator → Langfuse API → flush() → Dashboard
```

Every LLM operation must preserve: **Traces captured, scores attached, failures graceful.**

---

## Level 4: Configuration Invariants

### Credentials (Doppler)
- [ ] `LANGFUSE_PUBLIC_KEY` set
- [ ] `LANGFUSE_SECRET_KEY` set
- [ ] `LANGFUSE_HOST` set (cloud.langfuse.com)
- [ ] `LANGFUSE_RELEASE` set (versioning)
- [ ] Credentials are environment-isolated

### Version Format
- [ ] Format: `{env}-{version|branch}-{short_sha}`
- [ ] Example: `prd-v1.2.3-abc1234`, `dev-dev-ghi9012`
- [ ] Set automatically by CI/CD

### Client Configuration
- [ ] Singleton pattern (one client per Lambda instance)
- [ ] Lazy initialization
- [ ] Non-blocking operations

### Verification
```bash
# Check credentials
doppler secrets get LANGFUSE_PUBLIC_KEY -p dr-daily-report -c {env}
doppler secrets get LANGFUSE_RELEASE -p dr-daily-report -c {env}

# Verify format
echo $LANGFUSE_RELEASE | grep -E '^(dev|stg|prd)-'
```

---

## Level 3: Infrastructure Invariants

### Connectivity
- [ ] Lambda can reach cloud.langfuse.com
- [ ] NAT Gateway allows outbound HTTPS
- [ ] No firewall blocking Langfuse

### Graceful Degradation
- [ ] Langfuse unavailability doesn't crash application
- [ ] Timeout on Langfuse operations (5s)
- [ ] Log warning if Langfuse unreachable

### Lambda Integration
- [ ] `flush()` called before Lambda return
- [ ] Traces not lost on cold start
- [ ] Memory not leaked across invocations

### Verification
```bash
# Check connectivity (from Lambda or local)
curl -I https://cloud.langfuse.com/api/public/health

# Check traces in dashboard
# Open Langfuse dashboard, filter by release
```

---

## Level 2: Data Invariants

### Trace Structure
- [ ] Trace name is descriptive (not generic)
- [ ] Trace includes input/output
- [ ] Trace includes metadata (ticker, user_id)
- [ ] Trace has correct release version

### Score Definitions
- [ ] 5 quality scores per report
- [ ] Score values 0-1 range
- [ ] Score names consistent across environments

### Score Types
| Score | Range | Description |
|-------|-------|-------------|
| faithfulness | 0-1 | Accuracy to source data |
| completeness | 0-1 | All required sections present |
| reasoning_quality | 0-1 | Logic and analysis quality |
| compliance | 0-1 | Format and structure compliance |
| consistency | 0-1 | Internal consistency |

### Verification
```bash
# Check trace in Langfuse dashboard:
# 1. Filter by release (LANGFUSE_RELEASE)
# 2. Verify trace has all expected spans
# 3. Verify scores attached
```

---

## Level 1: Service Invariants

### Tracing
- [ ] `@observe` decorator on entry points
- [ ] Nested spans for sub-operations
- [ ] Error spans on exceptions
- [ ] Duration captured automatically

### Scoring
- [ ] Scores attached to correct trace
- [ ] Scores computed after generation
- [ ] No blocking on score computation
- [ ] Score failures logged but not fatal

### Flush Pattern
```python
# REQUIRED in Lambda handlers
try:
    result = generate_report(ticker)
    return result
finally:
    langfuse.flush()  # Always flush
```

### Error Handling
- [ ] Langfuse errors don't propagate
- [ ] Errors logged at WARNING level
- [ ] Core functionality continues

### Verification
```python
# Check flush is called
grep -r "langfuse.flush()" src/
grep -r "flush()" src/*handler*.py
```

---

## Level 0: User Invariants

### Dashboard Experience
- [ ] Traces visible in Langfuse dashboard
- [ ] Can filter by release version
- [ ] Can see score trends over time
- [ ] Can drill into individual traces

### Debugging Support
- [ ] Trace shows what LLM received
- [ ] Trace shows what LLM produced
- [ ] Can identify slow operations
- [ ] Can identify failures

### Verification
```bash
# Manual in Langfuse dashboard:
# 1. Open traces
# 2. Filter by environment
# 3. Verify recent traces present
# 4. Check scores attached
# 5. Drill into trace details
```

---

## Environment-Specific

### dev
```yaml
relaxations:
  - Traces optional during local dev
  - Scores can be skipped
  - Debug logging enabled
```

### stg
```yaml
requirements:
  - All traces captured
  - All scores computed
  - Version tracking enabled
```

### prd
```yaml
requirements:
  - All traces captured
  - All scores computed
  - Version tracking required
  - Monitoring on score degradation
```

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Forgetting `flush()` in Lambda | Add to finally block |
| Blocking on heavy scores | Use async scoring |
| Generic trace names | Use descriptive names |
| Scoring everything | Only score high-value outputs |
| Environment-only versioning | Include SHA for traceability |

---

## Claiming "Langfuse Work Done"

```markdown
## Langfuse work complete: {description}

**Environment**: {dev | stg | prd}

**Invariants Verified**:
- [x] Level 4: Credentials set, version format correct
- [x] Level 3: Connectivity working, flush called
- [x] Level 2: Traces structured, scores defined
- [x] Level 1: Decorators applied, errors handled
- [x] Level 0: Traces visible in dashboard

**Evidence**: {Langfuse trace link, dashboard screenshot}
```

---

*Objective: shared/langfuse*
*Spec: .claude/specs/shared/langfuse/spec.yaml*
