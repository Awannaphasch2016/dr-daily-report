---
name: bug-hunt
description: Systematic bug investigation with type-specific workflows for production errors, performance issues, race conditions, and data corruption
accepts_args: true
arg_schema:
  - name: symptom
    required: true
    description: "Description of observed bug (quoted if spaces)"
  - name: bug_type
    required: false
    description: "Optional explicit type: production-error, performance, race-condition, data-corruption, memory-leak, integration-failure"
composition:
  - skill: error-investigation
  - skill: research
---

# Bug Hunt Command

**Purpose**: Systematic bug investigation with type-specific workflows

**Core Principle**: "Systematic investigation beats random debugging" - structure prevents thrashing

**When to use**:
- Production error spike (investigate cause systematically)
- Performance degradation (identify bottleneck)
- Intermittent failures (narrow down conditions)
- Data corruption (trace data flow)
- Memory leaks (identify leak source)
- Integration failures (dependency issues)

---

## Quick Reference

```bash
# Auto-detect bug type from symptom
/bug-hunt "Lambda timeout after 30s"
/bug-hunt "Intermittent 500 errors on /api/backtest"
/bug-hunt "Memory usage growing over time"
/bug-hunt "Incorrect data in user_preferences table"

# Explicit bug type (override auto-detection)
/bug-hunt "slow query" performance
/bug-hunt "sometimes fails" race-condition
```

---

## Bug Types

| Type | Auto-Detect Keywords | Investigation Focus |
|------|---------------------|---------------------|
| **production-error** | error, exception, 500, crash, timeout, failed | Logs, stack traces, recent changes |
| **performance** | slow, latency, timeout, degraded, bottleneck | Metrics, profiling, resource usage |
| **data-corruption** | incorrect data, missing fields, wrong values | Data flow, validation, transformations |
| **race-condition** | intermittent, sometimes, flaky, non-deterministic | Timing, concurrency, state management |
| **memory-leak** | memory, OOM, growing, leak | Memory profiling, reference tracking |
| **integration-failure** | API failed, external service, third-party | Dependency status, contract validation |

---

## Investigation Workflow

```
[Symptom] → [Classify Type] → [Gather Evidence] → [Form Hypotheses]
                                                          ↓
[Test Systematically] → [Root Cause?] → [Reproduction + Fixes]
                              ↓ NO
                        [Refine Hypotheses]
```

---

## vs Other Debugging Tools

| Tool | Purpose | When | Output |
|------|---------|------|--------|
| `/observe failure` | Capture observation | After failure | Immutable record |
| `/decompose failure` | Break down failure | Analyze structure | Decomposition tree |
| `error-investigation` skill | AWS/Lambda patterns | Auto-applied | Investigation guidance |
| **`/bug-hunt`** | **Active investigation** | **During debugging** | **Investigation report + fixes** |

**Complementary usage**:
```bash
/observe failure "Lambda timeout after 30s"  # Capture
/bug-hunt "Lambda timeout after 30s"         # Investigate
/journal error "Lambda timeout root cause"   # Document solution
```

---

## Output

**File location**: `.claude/bug-hunts/{date}-{slug}.md`

**Report includes**:
- Evidence gathered (logs, metrics, code, recent changes)
- Hypotheses tested (eliminated, confirmed, uncertain)
- Root cause + confidence level (High/Medium/Low)
- Reproduction steps
- Fix candidates with pros/cons/effort
- Recommended fix + rationale

---

## Prompt Template

You are executing the `/bug-hunt` command with symptom: "$1"

Optional explicit bug type: ${2:-auto-detect}

---

### Execution Steps

**Step 1: Classify Bug Type**

Analyze symptom description to determine bug type:

```python
SYMPTOM = "$1"
BUG_TYPE = "${2:-auto-detect}"

if BUG_TYPE == "auto-detect":
    # Auto-detect from keywords
    if any(keyword in SYMPTOM.lower() for keyword in ["error", "exception", "500", "crash", "timeout", "failed"]):
        BUG_TYPE = "production-error"
    elif any(keyword in SYMPTOM.lower() for keyword in ["slow", "latency", "degraded", "bottleneck"]):
        BUG_TYPE = "performance"
    elif any(keyword in SYMPTOM.lower() for keyword in ["incorrect", "missing", "wrong values", "data"]):
        BUG_TYPE = "data-corruption"
    elif any(keyword in SYMPTOM.lower() for keyword in ["intermittent", "sometimes", "flaky", "non-deterministic"]):
        BUG_TYPE = "race-condition"
    elif any(keyword in SYMPTOM.lower() for keyword in ["memory", "OOM", "growing", "leak"]):
        BUG_TYPE = "memory-leak"
    elif any(keyword in SYMPTOM.lower() for keyword in ["API failed", "external", "third-party"]):
        BUG_TYPE = "integration-failure"
    else:
        BUG_TYPE = "production-error"  # Default
```

Output to user:
```
🔍 Bug Type Detected: {BUG_TYPE}
📋 Investigation Template: {bug_type_name}
```

---

**Step 2: Execute Type-Specific Investigation**

Based on detected bug type, follow the appropriate investigation template below.

---

## Investigation Templates

### Template: Production Error Investigation

**Use when**: Errors, exceptions, crashes, timeouts, 500s

**Investigation workflow**:

1. **Gather Error Context**

   Use available tools to collect:
   - **CloudWatch logs** (if AWS Lambda):
     ```bash
     aws logs filter-log-events \
       --log-group-name /aws/lambda/{function-name} \
       --start-time {timestamp-1h-ago} \
       --filter-pattern "ERROR"
     ```
   - **Stack traces**: Extract from logs, identify failing line
   - **First occurrence**: When did error first appear?
   - **Affected scope**: All users or specific subset?
   - **Recent deployments**: Check git log for changes

2. **Multi-Layer Verification**

   Check all layers (principle from error-investigation skill):
   - **Status code/exit code**: HTTP 500, Lambda exit code
   - **Log levels**: ERROR vs WARNING (ERROR = discovered, WARNING = hidden)
   - **Data state**: What actually happened in database/cache?
   - **Metrics**: Error rate, latency spikes

3. **Form Hypotheses** (3-5 ranked by likelihood)

   Common hypotheses:
   - **Recent code change**: Git log shows deployment before error started
   - **Configuration change**: Environment variables, feature flags
   - **External dependency failure**: Third-party API down
   - **Data-driven bug**: Specific input triggers error
   - **Infrastructure issue**: Resource limits, network

   Rank by:
   - **High likelihood**: Evidence strongly suggests
   - **Medium likelihood**: Plausible, needs testing
   - **Low likelihood**: Possible but unlikely

4. **Test Hypotheses Systematically**

   For each hypothesis (highest likelihood first):

   **Hypothesis: Recent code change**
   - Check: `git log --since="1 day ago" --oneline`
   - Look for: Changes to failing code path
   - Test: Can you revert and see error disappear?
   - Status: Eliminated | Confirmed | Uncertain

   **Hypothesis: Configuration change**
   - Check: Doppler activity log, terraform changes
   - Look for: Environment variable modifications
   - Test: Compare staging vs production config
   - Status: Eliminated | Confirmed | Uncertain

   **Hypothesis: External dependency**
   - Check: Dependency status page, network logs
   - Look for: Timeout errors, connection refused
   - Test: Can you reproduce by mocking dependency failure?
   - Status: Eliminated | Confirmed | Uncertain

5. **Identify Root Cause**

   When hypothesis confirmed:
   - **Root cause**: {Specific description}
   - **Confidence**: High (reproduction steps work) | Medium (strong evidence) | Low (inference)
   - **Evidence**:
     - Evidence point 1
     - Evidence point 2
   - **Code location**: {file:line}

---

### Template: Performance Investigation

**Use when**: Slowness, latency spikes, bottlenecks, degradation

**Investigation workflow**:

1. **Establish Baseline**

   - **Normal performance**: What was baseline latency/throughput?
   - **When degradation started**: Specific timestamp or gradual?
   - **Magnitude**: 2x slower? 10x? 100x?
   - **Correlation**: With specific inputs, load level, time of day?

2. **Identify Bottleneck Layer**

   Use CloudWatch metrics (if Lambda) or profiling:

   - **CPU-bound**: High CPU usage (check Lambda metrics, profiler)
   - **I/O-bound**: High wait time (disk, network)
   - **Memory-bound**: Excessive allocation, GC pressure
   - **External API-bound**: Waiting on dependencies

   Tools:
   - Lambda: CloudWatch Insights, X-Ray traces
   - Python: `py-spy top --pid {pid}` or `cProfile`

3. **Profile Hot Paths**

   Identify top time consumers:
   ```bash
   # Python profiling
   python -m cProfile -o output.prof script.py
   # Analyze
   python -c "import pstats; p = pstats.Stats('output.prof'); p.sort_stats('cumulative'); p.print_stats(20)"
   ```

   Look for:
   - **N+1 queries**: Database called in loop
   - **Redundant calls**: Same function called multiple times
   - **Blocking I/O**: Sequential when could be parallel

4. **Form Hypotheses**

   Common performance hypotheses:
   - **Algorithmic inefficiency**: O(n²) where O(n) possible
   - **Missing database index**: Full table scan
   - **External API latency**: Dependency slowed down
   - **Memory thrashing**: Excessive garbage collection
   - **Resource contention**: Lock contention, thread pool saturated

5. **Validate Bottleneck**

   - **Measure before/after**: Quantify improvement
   - **Isolate component**: Mock dependencies to test in isolation
   - **Test with different data sizes**: Does it scale linearly?

---

### Template: Race Condition Investigation

**Use when**: Intermittent, flaky, non-deterministic failures

**Investigation workflow**:

1. **Characterize Non-Determinism**

   - **Failure rate**: 1%? 10%? 50%?
   - **Correlation with load**: Fails more under high concurrency?
   - **Single-threaded mode**: Does it still happen?
   - **Timing**: Does adding delays change behavior?

2. **Identify Shared State**

   Map concurrent access:
   - **What state is shared**: Global variables, class attributes, database rows
   - **Who accesses it**: Which functions/threads/async tasks
   - **Is it protected**: Locks, atomic operations, immutability
   - **Order assumptions**: Does code assume operation order?

3. **Check Synchronization**

   Common race condition patterns:
   - **Missing locks**: Shared state modified without protection
   - **Lock ordering issues**: Thread A locks X then Y, Thread B locks Y then X (deadlock)
   - **Async/await misuse**: Fire-and-forget without awaiting
   - **Check-then-act**: Read state, then act on it (state changed between)

4. **Reproduce Deterministically**

   Techniques:
   - **Add delays**: `time.sleep()` to expose race window
   - **Stress test**: Increase concurrency to amplify failure rate
   - **Thread sanitizer** (if available): Detects data races
   - **Logging**: Add timestamps to trace interleaving

5. **Fix Strategy**

   Options:
   - **Add synchronization**: Use locks, semaphores
   - **Eliminate shared state**: Make data immutable, use message passing
   - **Atomic operations**: Use `threading.Lock()`, `asyncio.Lock()`
   - **Restructure**: Redesign to avoid race

---

### Template: Data Corruption Investigation

**Use when**: Incorrect data, missing fields, wrong values

**Investigation workflow**:

1. **Identify Corruption Scope**

   - **Which fields are wrong**: Specific columns/attributes
   - **All records or subset**: Pattern to corrupted data?
   - **When started**: First corrupted record timestamp
   - **How many affected**: Count of bad records

2. **Trace Data Flow**

   Map the pipeline:
   ```
   Source → Transform 1 → Transform 2 → ... → Destination
   ```

   For each stage:
   - What transformation happens?
   - What validation is applied?
   - Where could data become incorrect?

3. **Check Type Boundaries** (Critical!)

   System boundaries where type mismatches cause silent failures:

   - **Serialization/deserialization**: JSON encoding (NumPy int64 → native int)
   - **Database type mismatches**: MySQL ENUM failures (wrong type → silent skip)
   - **API request/response**: Pydantic validation
   - **Lambda responses**: Must be JSON-serializable

   Test round-trip:
   ```python
   original = {"field": value}
   serialized = json.dumps(original)
   deserialized = json.loads(serialized)
   assert original == deserialized  # Should pass
   ```

4. **Validate Transformations**

   Test each transformation:
   - **Happy path**: Normal inputs
   - **Edge cases**: Null, empty string, special characters
   - **Type safety**: What if wrong type passed?
   - **Round-trip**: Write → Read → Compare

5. **Locate Corruption Point**

   Binary search through pipeline:
   - Add logging at each stage
   - Compare expected vs actual
   - Narrow to specific transformation

---

### Template: Memory Leak Investigation

**Use when**: Memory usage growing, OOM errors

**Investigation workflow**:

1. **Characterize Growth Pattern**

   - **Linear growth**: Memory grows steadily over time
   - **Step growth**: Jumps at specific events
   - **Gradual then sudden**: Slow leak then OOM
   - **Correlation**: With request count, data size?

2. **Profile Memory Usage**

   Python tools:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... run code ...
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')
   for stat in top_stats[:10]:
       print(stat)
   ```

   Lambda: Check CloudWatch memory metrics

3. **Identify Leak Sources**

   Common patterns:
   - **Global caches**: Never evicted
   - **Event listeners**: Not cleaned up
   - **Circular references**: Objects reference each other
   - **Unclosed resources**: Files, connections not closed

4. **Reproduce and Measure**

   - Run leak scenario repeatedly
   - Measure memory before/after
   - Confirm leak with metrics

5. **Fix Strategy**

   - **Limit cache size**: Use LRU cache with max size
   - **Cleanup handlers**: Remove listeners, close connections
   - **Weak references**: Break circular references
   - **Resource management**: Use context managers (`with` statement)

---

### Template: Integration Failure Investigation

**Use when**: External API failures, third-party service issues

**Investigation workflow**:

1. **Identify Failed Integration**

   - **Which service**: Name of external API/service
   - **Error message**: Exact error from logs
   - **Failure rate**: All requests or intermittent?
   - **Since when**: Timestamp of first failure

2. **Check Service Status**

   - **Status page**: Check vendor status page
   - **Recent changes**: Did vendor deploy update?
   - **Rate limits**: Are we hitting limits?
   - **Authentication**: Credentials still valid?

3. **Validate Contract**

   - **API version**: Did vendor change API version?
   - **Request format**: Are we sending correct format?
   - **Response format**: Did vendor change response schema?
   - **Type compatibility**: Heterogeneous type system mismatch?

4. **Test Isolation**

   - **Can we call directly**: Test with curl/Postman
   - **Network path**: Is network route working?
   - **Credentials**: Test with different credentials
   - **Minimal reproduction**: Simplest possible call

5. **Fix Strategy**

   - **Update integration**: Adapt to vendor changes
   - **Add retry logic**: Handle transient failures
   - **Circuit breaker**: Fail fast when vendor down
   - **Fallback**: Use cached data or alternative source

---

## Output Report Generation

After investigation completes, generate report at:

`.claude/bug-hunts/{date}-{slug}.md`

**Report structure**:

```markdown
---
title: {Symptom description}
bug_type: {detected type}
date: {YYYY-MM-DD}
status: {investigating | root_cause_found | inconclusive}
confidence: {High | Medium | Low}
---

# Bug Hunt Report: {Symptom}

## Symptom

**Description**: {User-provided symptom}

**First occurrence**: {Timestamp if found}

**Affected scope**: {Users/requests/components affected}

**Impact**: {High | Medium | Low}

---

## Investigation Summary

**Bug type**: {production-error | performance | race-condition | data-corruption | memory-leak | integration-failure}

**Investigation duration**: {Time spent}

**Status**: {Root cause found | Still investigating | Inconclusive}

---

## Evidence Gathered

### Logs

{Relevant log snippets with timestamps}

### Metrics

- {Metric 1}: {Value}
- {Metric 2}: {Value}

### Code References

- `{file:line}` - {What this code does}

### Recent Changes

{Output of git log showing recent commits}

---

## Hypotheses Tested

### Hypothesis 1: {Description}

**Likelihood**: {High | Medium | Low}

**Test performed**: {How we tested this hypothesis}

**Result**: {Eliminated | Confirmed | Uncertain}

**Reasoning**: {Why we eliminated/confirmed this}

**Evidence**:
- {Evidence point 1}
- {Evidence point 2}

---

### Hypothesis 2: {Description}

[Repeat structure for each hypothesis]

---

## Root Cause

{If found}

**Identified cause**: {Specific root cause description}

**Confidence**: {High | Medium | Low}

**Supporting evidence**:
- {Evidence 1}
- {Evidence 2}
- {Evidence 3}

**Code location**: `{file:line}`

**Why this causes the symptom**: {Explanation}

---

{If not found}

**Status**: Investigation incomplete

**What we know**:
- {Finding 1}
- {Finding 2}

**What we don't know**:
- {Unknown 1}
- {Unknown 2}

**Next investigation steps**:
- [ ] {Step 1}
- [ ] {Step 2}

---

## Reproduction Steps

{If root cause found}

1. {Step 1}
2. {Step 2}
3. {Step 3}

**Expected behavior**: {What should happen}

**Actual behavior**: {What actually happens (the bug)}

---

## Fix Candidates

### Fix 1: {Short description}

**Approach**: {Detailed explanation of fix}

**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

**Estimated effort**: {Hours/days}

**Risk**: {Low | Medium | High}

---

### Fix 2: {Short description}

[Repeat structure for each fix candidate]

---

## Recommendation

**Recommended fix**: {Fix number and name}

**Rationale**: {Why this fix is best}

**Implementation priority**: {P0 | P1 | P2}

---

## Next Steps

- [ ] Review investigation findings
- [ ] Implement recommended fix
- [ ] Write regression test
- [ ] Deploy to staging
- [ ] Verify fix in production
- [ ] Monitor metrics post-fix
- [ ] Document solution: `/journal error "{symptom}"`

---

## Investigation Trail

**What was checked**:
- {Thing 1 checked}
- {Thing 2 checked}

**What was ruled out**:
- {Hypothesis X eliminated because Y}
- {Hypothesis Z eliminated because W}

**Tools used**:
- {Tool 1}
- {Tool 2}

**Time spent**:
- Evidence gathering: {X} min
- Hypothesis testing: {Y} min
- Total: {Z} min
```

---

## Examples

### Example 1: Lambda Timeout

```bash
/bug-hunt "Lambda timeout after 30 seconds in production"
```

**Investigation**:
- Detected type: `production-error`
- Evidence: CloudWatch logs show timeout, recent deployment 2 hours ago
- Hypothesis: Recent code change introduced slow query
- Test: Check git log, find new database query without index
- Root cause: Missing index on `user_id` column (High confidence)
- Fix: Add database index
- Result: Investigation report saved

---

### Example 2: Performance Degradation

```bash
/bug-hunt "API latency increased from 200ms to 2s" performance
```

**Investigation**:
- Explicit type: `performance`
- Baseline: 200ms normal, 2s current (10x slower)
- Profiling: 95% time in database query
- Hypothesis: N+1 query pattern
- Root cause: Loop calling database for each item (High confidence)
- Fix: Single query with JOIN
- Result: Investigation report with profiling data

---

### Example 3: Intermittent Failure

```bash
/bug-hunt "Sometimes returns 500, sometimes succeeds with same input"
```

**Investigation**:
- Detected type: `race-condition`
- Characterization: 10% failure rate, correlates with high load
- Shared state: Global cache modified concurrently
- Hypothesis: Missing lock on cache access
- Root cause: Race condition in cache update (Medium confidence)
- Fix: Add `asyncio.Lock()` around cache access
- Result: Investigation report with concurrency analysis

---

## Tips

### Do
- **Start investigation immediately** (don't wait for more failures)
- **Follow the template** (systematic beats random)
- **Test hypotheses in order** (highest likelihood first)
- **Capture evidence** (logs, metrics, code refs)
- **Assign confidence levels** (be honest about certainty)

### Don't
- **Skip evidence gathering** (jumping to conclusions)
- **Test all hypotheses at once** (confusing, can't isolate cause)
- **Assume root cause without testing** (confirmation bias)
- **Forget to document investigation trail** (helps future debugging)

---

## Integration with Other Commands

**Before investigation**:
```bash
/observe failure "Lambda timeout after 30s"
```

**During investigation**:
```bash
/bug-hunt "Lambda timeout after 30s"
# Uses error-investigation skill patterns
# Follows production-error template
```

**After investigation**:
```bash
/journal error "Lambda timeout root cause: missing index"
# Document solution for future reference
```

---

## See Also

- `/observe` - Capture failure observations
- `/decompose` - Break down failures into components
- `error-investigation` skill - AWS/Lambda debugging patterns
- `/validate` - Validate hypotheses
- `/journal` - Document solutions
