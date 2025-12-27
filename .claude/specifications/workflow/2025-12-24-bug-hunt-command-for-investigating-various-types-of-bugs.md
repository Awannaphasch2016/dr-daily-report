---
title: /bug-hunt command for investigating various types of bugs
focus: workflow
date: 2025-12-24
status: draft
tags: [debugging, investigation, error-handling, command-design]
---

# Workflow Specification: /bug-hunt Command

## Goal

**What does this workflow accomplish?**

The `/bug-hunt` command provides a **specialized, structured bug investigation workflow** that adapts to different bug types (production errors, performance issues, data corruption, race conditions, etc.). It combines systematic debugging methodology with type-specific investigation patterns to guide users from symptom to root cause.

**Why this command?**

**Current state**:
- `/observe failure` - Captures failure observations (what happened)
- `/decompose failure` - Breaks down failure into components
- `error-investigation` skill - Auto-applied multi-layer debugging (AWS/Lambda)
- `/validate` - Validates claims about bugs

**Gap**: No explicit workflow command for **active bug hunting** that:
1. Guides investigation systematically (prevents random debugging)
2. Adapts methodology to bug type (performance vs race condition needs different approach)
3. Captures investigation trail (what was checked, what was ruled out)
4. Produces actionable output (reproduction steps, fix candidates, confidence levels)

**Use cases**:
- Production error spike (investigate cause systematically)
- Performance degradation (identify bottleneck)
- Intermittent failures (narrow down conditions)
- Data corruption (trace data flow)
- Memory leaks (identify leak source)

---

## Workflow Diagram

```
[Symptom Description]
         ↓
[Classify Bug Type] ← Auto-detect from keywords
         ↓
[Type-Specific Investigation Template]
         ↓
[Gather Evidence] → Logs, metrics, code, data
         ↓
[Hypothesis Formation] → 3-5 hypotheses ranked by likelihood
         ↓
[Systematic Elimination] → Test each hypothesis
         ↓
[Root Cause Identified?]
   ├─ YES → [Reproduction Steps] → [Fix Candidates] → [Confidence Level]
   └─ NO  → [Refine Hypotheses] → [Continue Investigation]
         ↓
[Output Report] → .claude/bug-hunts/{date}-{slug}.md
```

---

## Bug Type Classification

**Auto-detect bug type from symptom keywords**:

| Bug Type | Keywords | Investigation Focus |
|----------|----------|---------------------|
| **Production Error** | error, exception, 500, crash, timeout, failed | Logs, stack traces, recent changes |
| **Performance** | slow, latency, timeout, degraded, bottleneck | Metrics, profiling, resource usage |
| **Data Corruption** | incorrect data, missing fields, wrong values | Data flow, validation, transformations |
| **Race Condition** | intermittent, sometimes, flaky, non-deterministic | Timing, concurrency, state management |
| **Memory Leak** | memory, OOM, growing, leak | Memory profiling, reference tracking |
| **Integration Failure** | API failed, external service, third-party | Dependency status, contract validation |

---

## Type-Specific Investigation Templates

### Template 1: Production Error Investigation

**Workflow nodes**:

1. **Gather Error Context**
   - Collect stack traces, error messages
   - Find timestamp of first occurrence
   - Identify affected users/requests
   - Check deployment timeline (recent changes?)

2. **Check Multi-Layer Signals**
   - Exit code/status (weakest signal)
   - Log level (ERROR vs WARNING vs INFO)
   - Data state (strongest signal - what actually happened?)
   - Metrics/alarms

3. **Form Hypotheses**
   - Recent code change introduced bug
   - Configuration change broke functionality
   - External dependency failure
   - Data-driven bug (specific input triggers)
   - Infrastructure issue

4. **Test Hypotheses Systematically**
   - Check git log for recent changes
   - Compare config before/after
   - Test external dependencies
   - Reproduce with sample input
   - Check infrastructure metrics

5. **Identify Root Cause**
   - Narrow to specific code path/config/dependency
   - Verify with reproduction steps
   - Assign confidence level (High/Medium/Low)

---

### Template 2: Performance Investigation

**Workflow nodes**:

1. **Establish Baseline**
   - What is "normal" performance?
   - When did degradation start?
   - How much slower (2x, 10x, 100x)?

2. **Identify Bottleneck Layer**
   - CPU-bound (high CPU usage)
   - I/O-bound (waiting on disk/network)
   - Memory-bound (excessive allocation/GC)
   - External API-bound (waiting on dependencies)

3. **Profile Hot Paths**
   - Use profiler (py-spy, cProfile, etc.)
   - Identify top functions by time
   - Check for N+1 queries, redundant calls

4. **Form Hypotheses**
   - Algorithmic inefficiency (O(n²) where O(n) possible)
   - Database query missing index
   - External API latency increased
   - Memory thrashing (excessive GC)
   - Resource contention (locks, thread pool saturation)

5. **Validate Bottleneck**
   - Measure before/after metrics
   - Isolate component (mock dependencies)
   - Test with different data sizes

---

### Template 3: Race Condition Investigation

**Workflow nodes**:

1. **Characterize Non-Determinism**
   - How often does it fail? (1%, 10%, 50%?)
   - Does it correlate with load/concurrency?
   - Does it happen in single-threaded mode?

2. **Identify Shared State**
   - What state is accessed concurrently?
   - Is state protected (locks, atomic operations)?
   - Are there implicit dependencies (order assumptions)?

3. **Check Synchronization**
   - Missing locks
   - Lock ordering issues (deadlock potential)
   - Async/await misuse (fire-and-forget)

4. **Reproduce Deterministically**
   - Add delays to expose race window
   - Run with thread sanitizer
   - Increase concurrency (stress test)

5. **Fix Strategy**
   - Add synchronization (locks, semaphores)
   - Eliminate shared state (immutability)
   - Use atomic operations
   - Restructure to avoid race

---

### Template 4: Data Corruption Investigation

**Workflow nodes**:

1. **Identify Corruption Scope**
   - Which fields are wrong?
   - All records or subset?
   - When did corruption start?

2. **Trace Data Flow**
   - Source → Transformations → Destination
   - Map each transformation step
   - Identify where data becomes incorrect

3. **Check Type Boundaries**
   - Serialization/deserialization
   - Database type mismatches (ENUM failures)
   - API request/response format
   - JSON encoding (NumPy types!)

4. **Validate Transformations**
   - Check validation logic
   - Test with edge cases (null, empty, special chars)
   - Verify round-trip (write → read → compare)

5. **Locate Corruption Point**
   - Binary search through pipeline
   - Add logging at each stage
   - Compare expected vs actual at each boundary

---

## State Management

**State structure**:
```python
class BugHuntState(TypedDict):
    symptom: str                      # User-provided symptom description
    bug_type: str                     # Classified type (production_error, performance, etc.)
    evidence: List[str]               # Gathered evidence (log snippets, metrics, code refs)
    hypotheses: List[Dict[str, Any]]  # {hypothesis: str, likelihood: str, status: str}
    root_cause: Optional[str]         # Identified root cause (if found)
    confidence: str                   # High | Medium | Low
    reproduction_steps: List[str]     # Steps to reproduce
    fix_candidates: List[str]         # Potential fixes
    investigation_trail: List[str]    # What was checked, what was ruled out
```

**State transitions**:
- Initial → After Classification: `bug_type` populated
- After Evidence Gathering: `evidence` list grows
- After Hypothesis Formation: `hypotheses` list created
- After Testing: `hypotheses[i].status` updated (eliminated, confirmed, uncertain)
- After Root Cause: `root_cause`, `confidence`, `reproduction_steps` populated

---

## Error Handling

**Error propagation**:
- Node sets `state["error"]` on failure (e.g., "Cannot access logs")
- Workflow continues with partial evidence (graceful degradation)
- User warned about missing evidence layers

**Retry logic**:
- Transient errors (network): Retry 3 times
- Permanent errors (no access): Skip and warn

---

## Integration with Existing Commands/Skills

### Composition Pattern

```yaml
composition:
  - command: observe       # Optionally capture failure observation
  - skill: error-investigation  # Use AWS/Lambda investigation patterns
  - skill: research        # Systematic investigation methodology
  - command: validate      # Validate hypotheses
```

### Workflow Integration

**Before /bug-hunt**:
- User notices bug (production error, performance issue)
- Optionally: `/observe failure "description"` (capture observation)

**During /bug-hunt**:
- `/bug-hunt "Lambda timeout after 30s"` (launches investigation)
- Auto-detects bug type (production error)
- Follows production error template
- Gathers evidence (CloudWatch logs, metrics, git log)
- Forms hypotheses (recent change, config, dependency)
- Tests hypotheses systematically
- Identifies root cause with confidence level

**After /bug-hunt**:
- Report saved to `.claude/bug-hunts/2025-12-24-lambda-timeout-after-30s.md`
- User can `/journal error "Lambda timeout root cause"` (document solution)
- If fix implemented: `/observe execution "Fixed Lambda timeout"`

---

## Output Format

**File location**: `.claude/bug-hunts/{date}-{slug}.md`

**Report structure**:
```markdown
---
title: {Symptom description}
bug_type: {production_error | performance | race_condition | data_corruption | memory_leak | integration_failure}
date: {YYYY-MM-DD}
status: {investigating | root_cause_found | inconclusive}
confidence: {High | Medium | Low}
---

# Bug Hunt Report: {Symptom}

## Symptom

**Description**: {What user observed}

**First occurrence**: {Timestamp}

**Affected scope**: {Users/requests/components}

**Impact**: {High | Medium | Low}

---

## Investigation Trail

### Evidence Gathered

**Logs**:
```
{Relevant log snippets}
```

**Metrics**:
- {Metric 1}: {Value}
- {Metric 2}: {Value}

**Code references**:
- {File:line} - {What this code does}

**Recent changes**:
- {Commit hash} - {Change description}

---

### Hypotheses Tested

#### Hypothesis 1: {Description}

**Likelihood**: {High | Medium | Low}

**Test**: {How we tested this}

**Result**: {Eliminated | Confirmed | Uncertain}

**Reasoning**: {Why eliminated/confirmed}

---

#### Hypothesis 2: {Description}

[... repeat structure ...]

---

## Root Cause

**Identified cause**: {Root cause description}

**Confidence**: {High | Medium | Low}

**Evidence**:
- {Evidence 1}
- {Evidence 2}

**Code location**: {File:line}

---

## Reproduction Steps

1. {Step 1}
2. {Step 2}
3. {Step 3}

**Expected behavior**: {What should happen}

**Actual behavior**: {What actually happens}

---

## Fix Candidates

### Fix 1: {Description}

**Approach**: {How to fix}

**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

**Estimated effort**: {Time}

---

### Fix 2: {Description}

[... repeat structure ...]

---

## Recommendation

**Recommended fix**: {Fix number}

**Rationale**: {Why this fix}

**Next steps**:
- [ ] Implement fix
- [ ] Write test to prevent regression
- [ ] Deploy to staging
- [ ] Verify fix in production
- [ ] Journal solution: `/journal error "{symptom}"`
```

---

## Performance

**Expected duration**:
- Best case: 5-10 minutes (simple, obvious bug)
- Average case: 20-30 minutes (requires evidence gathering + hypothesis testing)
- Worst case: 1-2 hours (complex, requires deep investigation)

**Bottlenecks**:
- Evidence gathering (CloudWatch queries, log analysis)
- Hypothesis testing (may require code changes, redeployments)

**Optimization opportunities**:
- Cache common evidence sources (recent git log, metrics)
- Parallel hypothesis testing (if independent)
- Pre-populate known patterns (common bugs in this codebase)

---

## Command Interface

**Invocation**:
```bash
/bug-hunt "symptom description"
/bug-hunt "Lambda timeout after 30s"
/bug-hunt "Intermittent 500 errors on /api/backtest"
/bug-hunt "Memory usage growing over time"
```

**Arguments**:
- `symptom` (required): Description of observed bug

**Auto-detection**:
- Bug type detected from symptom keywords
- No explicit type argument needed (but can override)

**Optional explicit type**:
```bash
/bug-hunt "slow query" performance
/bug-hunt "sometimes fails" race-condition
```

---

## Comparison with Existing Commands/Skills

| Feature | `/bug-hunt` | `/observe failure` | `/decompose failure` | `error-investigation` skill |
|---------|-------------|-------------------|----------------------|----------------------------|
| **Purpose** | Active investigation workflow | Capture observation | Break down failure | AWS/Lambda debugging patterns |
| **When** | During debugging | After failure occurred | After observation | Auto-applied by Claude |
| **Output** | Investigation report + fixes | Observation record | Decomposition tree | Investigation guidance |
| **User control** | Explicit invocation | Explicit invocation | Explicit invocation | Auto-discovered |
| **Methodology** | Type-specific templates | Immutable capture | Part-whole analysis | Multi-layer verification |

**Complementary usage**:
```bash
# Failure occurs
/observe failure "Lambda timeout after 30s"

# Start investigation
/bug-hunt "Lambda timeout after 30s"
# → Uses error-investigation skill patterns
# → Follows production error template
# → Produces investigation report

# Document solution
/journal error "Lambda timeout root cause: missing index"
```

---

## Open Questions

- [ ] Should `/bug-hunt` automatically create `/observe failure` entry if not already captured?
- [ ] Should it integrate with GitHub issues (create issue with investigation report)?
- [ ] Should it track time spent on investigation (for velocity metrics)?
- [ ] Should it suggest related bugs (similar symptoms in history)?
- [ ] Should it have a "pairing mode" (two-person debugging with explicit role switching)?

---

## Next Steps

- [ ] Review workflow design with focus on:
  - Bug type templates completeness
  - Integration with existing commands/skills
  - Output format usefulness
- [ ] Decide on GitHub integration (create issues?)
- [ ] If approved, implement as command in `.claude/commands/bug-hunt.md`
- [ ] Test with real bugs from project history
- [ ] Iterate on templates based on usage

---

## Design Principles

**Core Principle**: "Systematic investigation beats random debugging" - structure prevents thrashing

**Why type-specific templates**:
- ✅ Different bugs need different approaches (performance ≠ race condition)
- ✅ Templates encode expert knowledge (what to check for each type)
- ✅ Prevents missing evidence layers (logs + metrics + code + data)

**Why capture investigation trail**:
- ✅ Shows what was ruled out (prevents re-checking)
- ✅ Helps others learn debugging methodology
- ✅ Enables pattern extraction (common bug types in this codebase)

**Why hypothesis-driven**:
- ✅ Prevents confirmation bias (test multiple hypotheses)
- ✅ Prioritizes likely causes first (save time)
- ✅ Clear stopping condition (hypothesis confirmed with confidence)
