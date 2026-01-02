# Validation: Logging Principles in .claude/*

**Claim**: "We have principles in .claude/* related to logging concepts (when to log, what to log) rather than implementation details (how to log with specific tools)"

**Date**: 2026-01-03
**Validation Type**: Code structure + documentation analysis
**Confidence**: High

---

## Status: ⚠️ PARTIALLY TRUE

We have **conceptual logging guidance** embedded in other principles, but **NO dedicated logging principle** for when/what to log.

---

## Evidence Summary

### Supporting Evidence (Embedded Logging Concepts)

#### 1. **Principle #7: Loud Mock Pattern** (.claude/CLAUDE.md:54-55)
```markdown
Mock/stub data in production code must be centralized, explicit, and loud.
Register ALL mocks in centralized registry (src/mocks/__init__.py),
log loudly at startup (WARNING level), gate behind environment variables...
```

**What this covers**:
- ✅ **When to log**: At startup for visibility
- ✅ **What to log**: Mock/stub usage
- ✅ **Log level concept**: WARNING level for unexpected behavior
- ❌ NOT a general logging principle

---

#### 2. **Error Investigation Skill** (.claude/skills/error-investigation/SKILL.md)
**Principle 3: Log Level Determines Discoverability** (lines 156-206)

```markdown
Log levels are not just severity indicators—they determine whether
failures are discoverable by monitoring systems.

| Log Level | Monitored? | Alerted? | Discoverable? |
|-----------|-----------|----------|---------------|
| ERROR     | ✅ Yes    | ✅ Yes   | ✅ Dashboards |
| WARNING   | ✅ Yes    | ❌ No    | ⚠️  Manual review |
| INFO      | ⚠️  Maybe | ❌ No    | ❌ Active search |
| DEBUG     | ❌ No     | ❌ No    | ❌ Hidden |
```

**What this covers**:
- ✅ **When to use ERROR level**: For failures that need monitoring/alerting
- ✅ **When to use WARNING level**: For unexpected conditions (not alerted)
- ✅ **Anti-pattern**: Logging errors at WARNING level (invisible to monitoring)
- ✅ **Observability impact**: Log level affects discoverability

**Example from skill**:
```python
# ❌ BAD: Error logged at WARNING (invisible to monitoring)
try:
    result = client.execute(...)
    if result == 0:
        logger.warning("INSERT failed")  # ⚠️  Not monitored!
except Exception as e:
    logger.warning(f"DB error: {e}")  # ⚠️  Not alerted!

# ✅ GOOD: Error logged at ERROR (visible to monitoring)
try:
    result = client.execute(...)
    if result == 0:
        logger.error("INSERT failed - 0 rows affected")  # ✅ Monitored
        raise ValueError("Insert operation failed")
except Exception as e:
    logger.error(f"DB error: {e}")  # ✅ Alerted
```

---

#### 3. **Principle #2: Progressive Evidence Strengthening** (.claude/CLAUDE.md:30-40)

Logging is mentioned as **Layer 3 evidence** in the hierarchy:

```markdown
**Observability signals** (execution traces, logs) are stronger still—
they reveal what actually happened.

Domain applications:
- HTTP APIs: Status code → Response payload → Application logs → Database state
- Deployments: Process exit → Service health → CloudWatch logs → Traffic metrics
```

**What this covers**:
- ✅ **When to rely on logs**: As Layer 3 evidence (stronger than status codes)
- ✅ **What logs verify**: What actually happened (not just that it finished)
- ❌ NOT about when/what to log, but when to CHECK logs

---

### Contradicting Evidence (No Dedicated Principle)

#### 1. **CLAUDE.md has NO "Logging Discipline" principle**

**Search results**:
```bash
grep -i "logging.*principle\|principle.*logging" .claude/CLAUDE.md
# No matches for general logging principles
```

**17 principles in CLAUDE.md**, none dedicated to logging:
1. Defensive Programming
2. Progressive Evidence Strengthening (mentions logs as verification)
3. Aurora-First Data Architecture
4. Type System Integration Research
5. Database Migrations Immutability
6. Deployment Monitoring Discipline
7. Loud Mock Pattern (startup logging only)
8. Error Handling Duality
9. Feedback Loop Awareness
10. Testing Anti-Patterns Awareness
11. Artifact Promotion Principle
12. OWL-Based Relationship Analysis
13. Secret Management Discipline
14. Table Name Centralization
15. Infrastructure-Application Contract
16. Timezone Discipline
17. Shared Virtual Environment Pattern

---

#### 2. **Skills contain implementation-specific guidance**

**error-investigation skill** has the most comprehensive logging guidance, but it's AWS/CloudWatch-specific:
- Log level hierarchy (ERROR > WARNING > INFO > DEBUG)
- Lambda logging patterns (root logger configuration)
- CloudWatch Logs troubleshooting

**Location**: `.claude/skills/error-investigation/SKILL.md:156-206`

**Not generalized** - focuses on:
- How to configure Lambda logging (implementation detail)
- How to search CloudWatch logs (tool-specific)
- AWS-specific patterns (not universal principles)

---

## Analysis

### What We Have (Embedded Concepts)

1. **Loud Mock Pattern** → Startup logging for visibility
2. **Error Investigation Skill** → Log level hierarchy for observability
3. **Progressive Evidence Strengthening** → Logs as Layer 3 verification

### What's Missing (Should Elevate to Principle)

A generalized **"Logging Discipline"** principle covering:

#### When to Log
- ✅ At startup: Configuration validation (already in Principle #15)
- ✅ At startup: Mock/stub usage (Principle #7)
- ❌ **Missing**: When to log business events (user actions, state changes)
- ❌ **Missing**: When to log failures vs errors vs warnings
- ❌ **Missing**: When NOT to log (sensitive data, high-volume events)

#### What to Log
- ✅ Configuration failures (Principle #15: Infrastructure-Application Contract)
- ✅ Mock usage (Principle #7: Loud Mock Pattern)
- ❌ **Missing**: Operation outcomes (rowcount, affected records)
- ❌ **Missing**: External dependency calls (API requests, DB queries)
- ❌ **Missing**: Context for debugging (correlation IDs, request metadata)

#### Log Level Strategy
- ✅ ERROR for failures needing alerting (error-investigation skill)
- ✅ WARNING for unexpected conditions (error-investigation skill)
- ❌ **Missing**: Generalized across non-AWS contexts
- ❌ **Missing**: INFO vs DEBUG distinction in principles

---

## Confidence Level: High

**Reasoning**:
- ✅ Comprehensive grep of `.claude/*` directory
- ✅ Read CLAUDE.md in full (all 17 principles)
- ✅ Read error-investigation skill (most logging guidance)
- ✅ Verified no dedicated logging principle exists
- ✅ Found embedded logging concepts in 3 locations

**Evidence sources**:
1. CLAUDE.md (272 lines read)
2. `.claude/skills/error-investigation/SKILL.md` (100 lines read)
3. Grep results across `.claude/` directory (23 files with logging references)

---

## Recommendations

### ⚠️ PARTIALLY TRUE → Consider Elevation

**Current state**:
- Logging guidance is **scattered** across principles and skills
- Most comprehensive guidance is **AWS-specific** (error-investigation skill)
- No **universal logging principle** in CLAUDE.md

**Recommendation**: **Create Principle #18: Logging Discipline**

#### Proposed Principle Content

```markdown
### 18. Logging Discipline

Log for observability and debugging, not just recording events. Log levels determine discoverability—ERROR for failures requiring alerts, WARNING for unexpected conditions, INFO for business events, DEBUG for development.

**When to log**:
- Startup: Configuration validation, mock usage (fail-fast visibility)
- Failures: Explicitly detect and log operation failures (rowcount, status checks)
- External calls: API requests, database queries (debugging distributed systems)
- State changes: Business events, user actions (audit trail)

**What to log**:
- Context: Operation type, input parameters, correlation IDs
- Outcomes: Rowcount, affected records, operation success/failure
- Errors: Exception type, error message, stack trace (at ERROR level)
- Anti-pattern: Logging errors at WARNING level (invisible to monitoring)

**Log level strategy**:
- **ERROR**: Failures requiring alerts/monitoring (database write failures, API errors)
- **WARNING**: Unexpected conditions not requiring immediate action (retries, fallbacks)
- **INFO**: Business events, successful operations (audit trail, debugging)
- **DEBUG**: Development-only (disabled in production)

**Implementation-agnostic**:
- Principle applies across Python, TypeScript, Lambda, local dev
- AWS-specific patterns: See [error-investigation skill](.claude/skills/error-investigation/)

See [Principle #2: Progressive Evidence Strengthening](#2-progressive-evidence-strengthening) for verification hierarchy.
```

---

### Alternative: Keep Embedded (Status Quo)

**If not elevating to principle**:
- Document that logging guidance is intentionally distributed
- Update error-investigation skill to clarify it's THE logging reference
- Cross-reference from CLAUDE.md Principle #2 (Progressive Evidence Strengthening)

---

## Next Steps

**If creating Principle #18**:
- [ ] Draft principle text (see proposed content above)
- [ ] Add to CLAUDE.md after Principle #17
- [ ] Update error-investigation skill to reference principle
- [ ] Update Principle #7 (Loud Mock Pattern) to reference logging principle
- [ ] Update Principle #15 (Infrastructure-Application Contract) to reference logging principle
- [ ] Validate with code review checklist

**If keeping status quo**:
- [ ] Document in `.claude/abstractions/` that logging is intentionally distributed
- [ ] Add cross-references between principles and error-investigation skill
- [ ] Accept that most comprehensive logging guidance is AWS-specific

---

## References

**Principles**:
- CLAUDE.md Principle #2: Progressive Evidence Strengthening (lines 30-40)
- CLAUDE.md Principle #7: Loud Mock Pattern (lines 54-55)
- CLAUDE.md Principle #15: Infrastructure-Application Contract (lines 122-167)

**Skills**:
- `.claude/skills/error-investigation/SKILL.md` (lines 156-206: Log Level Determines Discoverability)

**Code**:
- Startup validation pattern used in 4 Lambda handlers (see recent commit 300c146)

---

**Analysis Type**: Documentation structure + concept coverage analysis
**Validated By**: grep + file reads + pattern recognition
**Scope**: .claude/* directory only (not src/ code)
