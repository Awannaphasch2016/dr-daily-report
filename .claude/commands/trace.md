---
name: trace
description: Follow causality - trace backward (why did X happen?) or forward (what will X cause?)
accepts_args: true
arg_schema:
  - name: event
    required: true
    description: "Event or observation to trace (starting point)"
  - name: direction
    required: false
    description: "Optional: 'backward' (default, root cause) or 'forward' (consequences)"
composition:
  - skill: research
---

# Trace Command

**Purpose**: Follow causal chains backward or forward

**Core Principle**: "Follow the thread" - understand how one thing leads to another

**When to use**:
- Retrying loop (trace backward to root cause)
- Impact analysis (trace forward to consequences)
- Debugging (why did this fail?)
- Understanding data flow
- Following execution paths

---

## Execution Flow

### Phase 1: Identify Direction

**Backward tracing** (default): Why did X happen?
- Start from observed event
- Work backward through causal chain
- Find root cause(s)

**Forward tracing**: What will X cause?
- Start from proposed change/event
- Work forward through causal chain
- Predict downstream effects

---

### Phase 2: Build Causal Chain

**For each step in the chain**:

1. **Identify immediate cause/effect**:
   - What directly caused this? (backward)
   - What will this directly cause? (forward)

2. **Gather evidence**:
   - Code: Execution paths, function calls
   - Data: Value transformations, state changes
   - Logs: Observed sequences
   - Configuration: Settings that affect behavior

3. **Continue until terminal condition**:
   - Backward: Reach root cause (external input, configuration, user action)
   - Forward: Reach final effect (output, side effect, state change)

---

### Phase 3: Identify Contributing Factors

At each step:
- **Primary cause**: Main reason this occurred
- **Contributing factors**: Conditions that enabled/amplified
- **Confidence level**: How certain are we about this link?

---

### Phase 4: Generate Causal Diagram

Visualize chain:
```
[Root Cause] → [Step 1] → [Step 2] → [Observed Effect]
     ↓             ↓            ↓
[Contributing] [Contributing] [Contributing]
```

---

## Output Format

```markdown
## Trace Analysis: {event} ({direction})

### Starting Point

**Event**: {What we're tracing from}

**Direction**: {Backward (root cause) | Forward (consequences)}

**Context**: {Relevant background information}

---

## Causal Chain

### Step 1: {event-name}

**What happened**: {Description of this step}

**Caused by** (backward) / **Causes** (forward): {Previous/next step in chain}

**Evidence**:
- Code: `{file:line}` - {What code shows}
- Logs: {What logs show}
- Data: {What data shows}

**Contributing factors**:
- {Factor 1}: {How it contributed}
- {Factor 2}: {How it contributed}

**Confidence**: High | Medium | Low

---

### Step 2: {event-name}

[... repeat structure ...]

---

### Terminal: {root-cause OR final-effect}

**What happened**: {Description}

**Why this is terminal**:
- Backward: This is the root cause because {reason}
- Forward: This is the final effect because {reason}

**Evidence**: {Supporting evidence}

---

## Causal Diagram

```
{Visual representation of chain}

Example (backward):
[External API Timeout] → [Lambda Waits] → [Lambda Timeout] → [User Error]
        ↓                      ↓                  ↓
[No timeout config]    [25s API limit]    [30s Lambda limit]
```

---

## Analysis

### Primary Causal Path

{Narrative explanation of how we got from start to end}

### Key Contributing Factors

1. **{Factor 1}**: {How it contributed to the chain}
2. **{Factor 2}**: {How it contributed to the chain}

### Confidence Assessment

**Overall confidence**: High | Medium | Low

**Why**: {Explanation of confidence level}

**Uncertainty areas**:
- {What we're not sure about}
- {What we're not sure about}

---

## Recommendations

**Based on trace analysis**:

**Backward trace** (root cause found):
- Fix root cause: {Specific action}
- Address contributing factors: {Actions}
- Prevent recurrence: {Actions}

**Forward trace** (consequences identified):
- Acceptable consequences: {Which are OK}
- Unacceptable consequences: {Which to mitigate}
- Mitigation strategy: {How to handle}

**Next steps**:
```bash
{Suggested follow-up commands}
```
```

---

## Examples

### Example 1: Backward Trace (Root Cause Analysis)

```bash
/trace "Lambda timeout after 25 seconds" backward
```

**Output**:
```markdown
## Trace Analysis: Lambda timeout after 25 seconds (backward)

### Starting Point

**Event**: Lambda function times out after 25 seconds

**Direction**: Backward (finding root cause)

**Context**: Lambda configured with 30s timeout, consistently fails at 25s during yfinance API call

---

## Causal Chain

### Step 4 (Observed): Lambda Timeout

**What happened**: Lambda execution terminates with timeout error

**Caused by**: Lambda waits indefinitely for yfinance API response

**Evidence**:
- Code: `src/data/ticker_fetcher.py:42` - No timeout parameter on requests.get()
- Logs: CloudWatch shows "Task timed out after 25.03 seconds"
- Data: No response received from yfinance

**Contributing factors**:
- Lambda timeout set to 30s (allowed wait to continue)
- No retry logic (single attempt waits full duration)

**Confidence**: High (logs confirm timeout at 25s)

---

### Step 3: Lambda Waits for API Response

**What happened**: Lambda execution blocked waiting for HTTP response

**Caused by**: yfinance API takes longer than 25s to respond

**Evidence**:
- Code: `requests.get(url)` - No timeout parameter
- Logs: Request initiated, no response logged
- Pattern: Consistent 25s timing across failures

**Contributing factors**:
- Synchronous HTTP call (blocks execution)
- No timeout configured (waits indefinitely)

**Confidence**: High (code shows no timeout, logs confirm)

---

### Step 2: yfinance API Slow Response

**What happened**: yfinance API takes >25s to generate response

**Caused by**: yfinance internal timeout (25s limit)

**Evidence**:
- Pattern: Consistently 25s (suggests fixed timeout)
- Documentation: yfinance uses Yahoo Finance API (has rate limits)
- Similar reports: Community reports of yfinance slowness

**Contributing factors**:
- Peak usage time (market hours)
- Complex query (historical data + fundamentals)

**Confidence**: Medium (inferred from pattern, not confirmed)

---

### Terminal (Root Cause): yfinance API Has 25s Internal Timeout

**What happened**: yfinance library has hardcoded 25s timeout for Yahoo Finance API calls

**Why this is terminal**: This is the original cause - external library behavior we don't control

**Evidence**:
- Consistent 25s timing (not variable)
- External dependency (yfinance library)
- Library issue (not our code)

---

## Causal Diagram

```
[Root Cause]           [Step 2]              [Step 3]                [Step 4]
yfinance API      →    API Response      →   Lambda Waits       →    Lambda Timeout
(25s timeout)          Takes >25s             Indefinitely            (25s observed)
     ↓                      ↓                      ↓                       ↓
[Internal limit]    [Peak usage time]    [No timeout config]    [Exceeds before 30s]
```

---

## Analysis

### Primary Causal Path

The Lambda timeout originates from yfinance library's internal 25s timeout. When yfinance calls Yahoo Finance API during peak hours, responses take longer than 25s, triggering yfinance's internal timeout. Since our code doesn't specify a timeout parameter on the HTTP request, it waits indefinitely for yfinance to respond. After 25s, yfinance times out but our Lambda is still waiting, leading to the observed Lambda timeout before reaching the configured 30s limit.

### Key Contributing Factors

1. **No timeout configuration in our code**: Allows indefinite wait instead of failing fast
2. **Peak usage time**: Increases yfinance API response time beyond normal
3. **Synchronous execution**: Blocks Lambda execution during wait

### Confidence Assessment

**Overall confidence**: Medium-High

**Why**: Strong evidence from consistent timing patterns and code inspection, but yfinance internal timeout is inferred rather than confirmed

**Uncertainty areas**:
- Exact yfinance timeout value (inferred as 25s from observations)
- Whether timeout is configurable in yfinance library
- Yahoo Finance API's actual behavior during peaks

---

## Recommendations

**Root cause**: yfinance library has 25s internal timeout

**Fix root cause**:
```python
# Add explicit timeout to requests
import yfinance as yf
ticker = yf.Ticker("AAPL")
# Set timeout=20 to fail faster than yfinance's 25s
hist = ticker.history(period="1mo", timeout=20)
```

**Address contributing factors**:
- Add retry logic with exponential backoff
- Cache yfinance results to reduce API calls
- Schedule during off-peak hours when possible

**Prevent recurrence**:
- Set timeouts on all external API calls
- Monitor external API response times
- Alert on timeouts before Lambda limit

**Next steps**:
```bash
# Validate hypothesis about yfinance timeout
/validate "hypothesis: yfinance has 25s internal timeout"

# If validated, implement fix
EnterPlanMode  # Plan timeout implementation + retry logic

# After fix, verify
/trace "yfinance API call with timeout" forward  # Trace consequences of fix
```
```

---

### Example 2: Forward Trace (Consequence Analysis)

```bash
/trace "Add request timeout to yfinance calls" forward
```

**Output**:
```markdown
## Trace Analysis: Add request timeout to yfinance calls (forward)

### Starting Point

**Event**: Add `timeout=20` parameter to all yfinance API calls

**Direction**: Forward (predicting consequences)

**Context**: Proposed change to prevent Lambda timeouts

---

## Causal Chain

### Step 1: yfinance Call Fails Faster

**What happens**: yfinance API calls timeout after 20s instead of 25s

**Causes**: Lambda receives timeout exception earlier

**Evidence**:
- Code: `ticker.history(timeout=20)` - Explicit timeout
- Behavior: requests.exceptions.Timeout raised after 20s

**Contributing factors**:
- Faster failure detection
- Earlier error handling trigger

**Confidence**: High (standard requests library behavior)

---

### Step 2: Lambda Catches Timeout Exception

**What happens**: Exception handler in Lambda processes timeout

**Causes**: Either error response to user OR retry attempt (depending on implementation)

**Evidence**:
- Code: Current implementation has no exception handling
- Pattern: Unhandled exception → Lambda error

**Impact**:
- **Without exception handling**: Lambda fails with 500 error (same as before, but faster)
- **With exception handling**: Can retry, fallback to cache, or return graceful error

**Confidence**: High (current code has no handler, will fail)

---

### Step 3a (No Handler): Lambda Returns 500 Error

**What happens**: Lambda fails fast (20s instead of 25s)

**Causes**: User receives error response 5 seconds earlier

**Impact**:
- ✅ Pro: Faster failure (better UX)
- ❌ Con: Still fails (user sees error)
- ⚠️ Neutral: 5s saved but request still fails

**Confidence**: High (direct consequence of no exception handling)

---

### Step 3b (With Handler): Lambda Retries or Falls Back

**What happens**: Exception caught, retry or fallback executed

**Causes**: Either eventual success (retry works) or graceful degradation (cache fallback)

**Impact**:
- ✅ Pro: Resilient (handles transient failures)
- ✅ Pro: Better UX (graceful errors or cached data)
- ⚠️ Con: More complex (need retry logic + cache)

**Confidence**: Medium (depends on implementation choice)

---

### Terminal: User Experience

**Without exception handling**:
- User gets error 5s faster
- Still a failed request
- Marginal improvement

**With exception handling + retry**:
- User might get successful response (if retry succeeds)
- Or graceful error with explanation
- Significant improvement

**With exception handling + cache fallback**:
- User gets cached data (slightly stale)
- No error seen
- Best UX but requires cache implementation

---

## Causal Diagram

```
[Proposed Change]     [Step 1]              [Step 2]                [Step 3]
Add timeout=20    →   Fails at 20s      →   Exception Raised   →    Handler Decides
                          ↓                      ↓                       ↓
                   [Faster failure]        [Caught/Uncaught]    [Retry/Fallback/Error]
                                                                         ↓
                                                                   [User Experience]
```

---

## Analysis

### Primary Causal Path

Adding `timeout=20` to yfinance calls will cause API calls to fail after 20 seconds (instead of yfinance's internal 25s). This timeout exception propagates to Lambda's exception handling. Currently, there is no exception handler, so Lambda will fail fast with a 500 error. While this is marginally better than before (fails 5s earlier), it's still a failure. The real benefit comes from adding exception handling to retry or fallback to cached data.

### Key Contributing Factors

1. **No exception handling exists**: Timeout will propagate to Lambda error
2. **No cache implemented**: Cannot fallback to stale data
3. **No retry logic**: Cannot recover from transient failures

### Confidence Assessment

**Overall confidence**: High

**Why**: Direct code inspection shows current implementation, consequences follow deterministically

**Uncertainty areas**:
- Whether retry would succeed (depends on external API state)
- Cache hit rate (depends on usage patterns)

---

## Recommendations

**Acceptable consequences**:
- ✅ Faster failure is marginal improvement

**Unacceptable consequences**:
- ❌ Still fails requests (timeout alone doesn't solve problem)

**Mitigation strategy**:

**Option 1: Add retry logic** (recommended for transient failures)
```python
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(requests.exceptions.Timeout)
)
def fetch_ticker_data(ticker):
    return yf.Ticker(ticker).history(period="1mo", timeout=20)
```

**Option 2: Add cache fallback** (recommended for better UX)
```python
def fetch_ticker_data(ticker):
    try:
        return yf.Ticker(ticker).history(timeout=20)
    except requests.exceptions.Timeout:
        logger.warning(f"yfinance timeout for {ticker}, using cache")
        return get_cached_ticker_data(ticker)  # Fallback
```

**Option 3: Combine both** (best resilience)
- Try fresh data with timeout
- Retry on transient failure
- Fallback to cache if all retries fail

**Next steps**:
```bash
# Assess impact of adding retry + cache
/impact "Add retry logic and cache fallback to yfinance calls"

# If acceptable, implement
EnterPlanMode  # Detailed implementation plan
```
```

---

## Relationship to Other Commands

### Workflow Integration

**Before `/trace`**:
- `/observe` - Capture event to trace
- `/hypothesis` - Generate hypotheses about causation

**After `/trace`**:
- `/validate` - Validate causal links identified
- `/impact` - Assess impact of addressing root cause
- `/journal` - Document root cause for future reference

**Sequential workflow (backward)**:
```bash
/observe failure "Lambda timeout"
   ↓
/hypothesis "Lambda times out after 25 seconds"
   ↓ (generates hypotheses about cause)
/trace "Lambda timeout after 25 seconds" backward
   ↓ (identifies root cause: yfinance timeout)
/validate "hypothesis: yfinance has 25s internal timeout"
   ↓ (confirms root cause)
/journal error "yfinance 25s timeout causes Lambda failures"
```

**Sequential workflow (forward)**:
```bash
/trace "Add timeout parameter to yfinance" forward
   ↓ (predicts: still fails, just faster)
/impact "Add retry logic and cache fallback"
   ↓ (assesses: medium risk, high benefit)
EnterPlanMode  # Implement solution
```

### Loop Relationships

**Retrying loop**:
- Use `/trace` backward to find root cause
- Fix root cause to exit loop

**Branching loop**:
- Use `/trace` forward to predict consequences of different paths
- Choose path with acceptable consequences

---

## Best Practices

### Do
- **Start from concrete event** (not vague "it's broken")
- **Follow evidence** (code, logs, data, not speculation)
- **Identify contributing factors** (not just primary cause)
- **Assess confidence** (mark uncertain links as such)

### Don't
- **Don't skip steps** (trace every link in chain)
- **Don't assume causation** (correlation ≠ causation, verify)
- **Don't stop early** (backward: reach root cause, forward: reach final effect)
- **Don't ignore alternatives** (multiple causal paths may exist)

---

## See Also

- `/observe` - Capture events to trace
- `/hypothesis` - Generate causal hypotheses
- `/validate` - Validate causal links
- `/impact` - Forward trace specialized for code changes
- `.claude/diagrams/thinking-process-architecture.md` - Section 5 (Metacognitive Commands)

---

## Prompt Template

You are executing the `/trace` command with arguments: $ARGUMENTS

**Event**: $1
**Direction**: ${2:-backward}  # Default to backward (root cause)

---

### Execution Steps

**Step 1: Identify Direction**

- If direction is "backward" (or not specified): Trace to root cause
- If direction is "forward": Trace to consequences

**Step 2: Build Causal Chain**

**Backward tracing** (root cause):
1. Start from observed event
2. Ask: "What caused this?"
3. Search for evidence:
   - Code: Function calls, execution paths, data flow
   - Logs: Sequences, timings, errors
   - Configuration: Settings that affect behavior
4. Identify immediate cause
5. Repeat from new cause until reaching root cause

**Forward tracing** (consequences):
1. Start from proposed change/event
2. Ask: "What will this cause?"
3. Search for evidence:
   - Code: What depends on this?
   - Data: What consumes this?
   - Systems: What integrates with this?
4. Identify immediate effect
5. Repeat from new effect until reaching final consequences

**Terminal conditions**:
- Backward: External input, configuration, user action (root cause)
- Forward: Final output, side effect, state change (terminal effect)

**Step 3: Identify Contributing Factors**

At each step:
- Primary cause (main reason)
- Contributing factors (conditions that enabled/amplified)
- Confidence level (high/medium/low)

**Step 4: Generate Causal Diagram**

Create ASCII diagram showing:
- Primary causal path (horizontal)
- Contributing factors (vertical)
- Clear labels at each step

**Step 5: Provide Analysis and Recommendations**

- Summarize causal path (narrative)
- List key contributing factors
- Assess confidence (overall + uncertainties)
- Recommend actions:
  - Backward: How to fix root cause
  - Forward: How to handle consequences

---

### Notes

- Use grep/read to find evidence in code
- Reference specific file:line locations
- Mark uncertain links with lower confidence
- For forward traces, consider multiple outcome branches
- For backward traces, may have multiple root causes
