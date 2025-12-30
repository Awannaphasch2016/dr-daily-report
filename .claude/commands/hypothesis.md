---
name: hypothesis
description: Construct explanations - generate testable hypotheses to explain observations
accepts_args: true
arg_schema:
  - name: observation
    required: true
    description: "Phenomenon or observation to explain (what you observed that needs explanation)"
composition:
  - skill: research
---

# Hypothesis Command

**Purpose**: Ask "why" and construct plausible paths to explore

**Core Principle**: "Multiple working hypotheses" - generate several candidate explanations, then test to determine which is correct

**When to use**:
- Before `/research` (generate what to investigate)
- Initial-sensitive loop (propose alternative assumptions)
- Root cause analysis (generate candidate causes)
- After `/observe` (explain phenomenon you observed)

**Prerequisite**: Requires `/observe` output (need something to explain)

---

## Execution Flow

### Phase 1: Understand the Observation

1. **Parse observation**: What phenomenon needs explanation?
2. **Identify what's unexpected**: What violated expectations?
3. **Gather context**: What do we know about the situation?
4. **Define success criteria**: What would constitute a good explanation?

---

### Phase 2: Generate Candidate Hypotheses

For each plausible explanation:

1. **State hypothesis clearly**: "X occurs because Y"
2. **Identify mechanism**: How would this cause the observation?
3. **Testable predictions**: If this hypothesis is true, what else should we observe?
4. **Evidence needed**: What would prove/disprove this hypothesis?
5. **Likelihood assessment**: How likely is this explanation?

**Aim for 3-5 hypotheses** covering different causal mechanisms

---

### Phase 3: Rank Hypotheses

Rank by:
1. **Likelihood** (based on available knowledge, past observations)
2. **Testability** (how easy to validate/falsify)
3. **Specificity** (precise vs vague)

**Prioritize**: Hypotheses that are both likely AND testable

---

### Phase 4: Generate Validation Strategy

For top 2-3 hypotheses:
- **How to test**: Specific actions to validate
- **Expected outcomes**: What results would confirm/refute
- **Next steps**: Which hypothesis to test first

---

## Output Format

```markdown
## Hypotheses for: {observation}

### Context

**Observation**: {What was observed}

**What's unexpected**: {Why this needs explanation}

**Known facts**:
- {Fact 1}
- {Fact 2}

---

### Hypothesis 1: {Name} (Likelihood: High/Medium/Low | Testability: Easy/Medium/Hard)

**Explanation**: {Why this might cause the observation}

**Mechanism**: {How this would work}

**Testable predictions**:
- If true: {Prediction 1}
- If true: {Prediction 2}

**Evidence needed**:
- {Evidence 1}: How to obtain
- {Evidence 2}: How to obtain

**Likelihood reasoning**: {Why we think this is likely/unlikely}

---

### Hypothesis 2: {Name} (Likelihood: High/Medium/Low | Testability: Easy/Medium/Hard)

[... repeat structure ...]

---

### Hypothesis 3: {Name} (Likelihood: High/Medium/Low | Testability: Easy/Medium/Hard)

[... repeat structure ...]

---

## Ranked Recommendations

### 1. Test {Hypothesis Name} first

**Why**: {Most likely and testable}

**How to validate**:
```bash
/validate "hypothesis: {hypothesis statement}"
```

**Expected outcome**: {What would confirm/refute}

---

### 2. If Hypothesis 1 fails, test {Hypothesis Name}

**Why**: {Second best option}

**How to validate**: {Approach}

---

## Next Steps

```bash
# Recommended workflow
/validate "hypothesis: {top hypothesis}"
# If validated → proceed based on confirmed understanding
# If refuted → test next hypothesis
```
```

---

## Examples

### Example 1: Lambda Timeout Investigation

```bash
/hypothesis "Lambda times out after 25 seconds consistently"
```

**Output**:
```markdown
## Hypotheses for: Lambda times out after 25 seconds consistently

### Context

**Observation**: Lambda times out after 25 seconds (configured timeout: 30s)

**What's unexpected**: Timeout occurs before limit, consistently at 25s

**Known facts**:
- Lambda timeout set to 30s
- Error occurs during external API call
- No database queries in timeout window

---

### Hypothesis 1: External API has 25s timeout (Likelihood: High | Testability: Easy)

**Explanation**: yfinance or NewsAPI has internal 25s timeout

**Mechanism**: External API times out before our Lambda timeout triggers

**Testable predictions**:
- If true: CloudWatch logs show API call duration approaching 25s
- If true: API documentation mentions 25s timeout
- If true: Direct API test outside Lambda also times out at 25s

**Evidence needed**:
- CloudWatch logs: Search for API call durations
- API documentation: Check timeout specifications
- Direct test: curl API endpoint with timing

**Likelihood reasoning**: Consistent 25s suggests external timeout, not our 30s

---

### Hypothesis 2: Lambda network timeout (Likelihood: Medium | Testability: Medium)

**Explanation**: VPC network configuration has 25s socket timeout

**Mechanism**: VPC security group or network ACL enforces connection timeout

**Testable predictions**:
- If true: Other Lambda functions in same VPC have same issue
- If true: VPC flow logs show connection termination at 25s
- If true: Problem doesn't occur outside VPC

**Evidence needed**:
- VPC configuration: Check network settings
- Other Lambdas: Test if they experience same timeout
- VPC flow logs: Analyze network traffic

**Likelihood reasoning**: Possible but less likely (would affect all external calls)

---

### Hypothesis 3: Lambda cold start overhead (Likelihood: Low | Testability: Easy)

**Explanation**: Cold start + execution reaches 25s, hitting retry logic

**Mechanism**: Long init time + slow execution triggers timeout

**Testable predictions**:
- If true: Only cold starts timeout (warm starts succeed)
- If true: InitDuration + execution time ≈ 25s
- If true: Increasing timeout to 60s would allow completion

**Likelihood reasoning**: Unlikely (cold start avg 3s, API call shouldn't take 22s)

---

## Ranked Recommendations

### 1. Test Hypothesis 1 (External API timeout) first

**Why**: Most likely (consistent 25s) and easiest to test

**How to validate**:
```bash
/validate "hypothesis: yfinance API has 25s internal timeout"
```

**Expected outcome**: CloudWatch logs show API calls approaching 25s, API docs confirm timeout

---

### 2. If Hypothesis 1 fails, test Hypothesis 2 (VPC network timeout)

**Why**: Second most likely explanation

**How to validate**: Check VPC network configuration, test other Lambdas

---

## Next Steps

```bash
# Start with most likely hypothesis
/validate "hypothesis: yfinance API has 25s internal timeout"
# If validated → Add request timeout parameter to API calls
# If refuted → Move to Hypothesis 2 (VPC network)
```
```

---

### Example 2: Test Failure Investigation

```bash
/hypothesis "Integration test fails only in CI, passes locally"
```

**Output**:
```markdown
## Hypotheses for: Integration test fails only in CI, passes locally

### Context

**Observation**: `test_report_generation` passes on local machine, fails in GitHub Actions

**What's unexpected**: Same code, different environments, different results

**Known facts**:
- Test passes 100% locally (MacOS, Python 3.11)
- Test fails 100% in CI (Ubuntu, Python 3.11)
- Error: "AssertionError: Expected 5 tickers, got 3"

---

### Hypothesis 1: CI environment missing test data (Likelihood: High | Testability: Easy)

**Explanation**: CI database seed script incomplete

**Mechanism**: Local has manually added test data, CI only has automated seed

**Testable predictions**:
- If true: Database query in CI returns fewer records
- If true: Local database has more test data than CI
- If true: Adding data to CI seed script fixes test

**Evidence needed**:
- CI logs: Check database record count
- Seed scripts: Compare local vs CI data setup
- Database dump: Verify data differences

**Likelihood reasoning**: Most common cause of environment-specific test failures

---

### Hypothesis 2: Timing issue (race condition) (Likelihood: Medium | Testability: Medium)

**Explanation**: CI runs faster/slower, exposing race condition

**Mechanism**: Async operation not properly awaited

**Testable predictions**:
- If true: Adding sleep/wait makes test pass in CI
- If true: Test occasionally flakes locally if run many times
- If true: Async calls visible in code path

**Evidence needed**:
- Code review: Check for async/await patterns
- Multiple runs: Run test 100x locally to detect flakes
- Timing logs: Compare execution duration CI vs local

**Likelihood reasoning**: Common in CI but error message suggests data issue

---

### Hypothesis 3: Python environment difference (Likelihood: Low | Testability: Easy)

**Explanation**: Dependency version mismatch between local and CI

**Mechanism**: Different library versions behave differently

**Testable predictions**:
- If true: requirements.txt vs actual CI versions differ
- If true: Freezing versions in CI matches local
- If true: Library changelog shows breaking change

**Evidence needed**:
- requirements.txt: Check if versions pinned
- CI logs: Verify installed package versions
- Library changelogs: Search for breaking changes

**Likelihood reasoning**: Unlikely (Python version same, error is data-related)

---

## Ranked Recommendations

### 1. Test Hypothesis 1 (Missing test data) first

**Why**: Most likely and easiest to verify

**How to validate**:
```bash
# Check CI database
ENV=ci /validate "hypothesis: CI database has only 3 tickers, not 5"
```

**Expected outcome**: CI database query returns 3 records, local returns 5

---

## Next Steps

```bash
/validate "hypothesis: CI database missing test data"
# If validated → Update CI seed script with missing tickers
# If refuted → Test Hypothesis 2 (race condition)
```
```

---

## Relationship to Other Commands

### Workflow Integration

**Before `/hypothesis`**:
- `/observe` - Capture phenomenon that needs explanation

**After `/hypothesis`**:
- `/validate` - Test generated hypotheses
- `/research` - Investigate hypotheses further
- `/trace` - Follow causal chains for validated hypothesis

**Sequential workflow**:
```bash
/observe failure "Lambda timeout at 25s"
   ↓
/hypothesis "Lambda times out after 25 seconds consistently"
   ↓ (generates 3 hypotheses)
/validate "hypothesis: yfinance API has 25s timeout"
   ↓ (validates hypothesis)
/trace backward "yfinance API timeout"
   ↓ (traces root cause)
/journal error "yfinance API timeout causes Lambda failure"
```

### Loop Relationships

**Initial-sensitive loop**:
- Use `/hypothesis` to generate alternative assumptions
- Test each hypothesis with `/validate`
- Iterate until finding correct assumption

**Retrying loop**:
- Use `/hypothesis` to propose alternative root causes
- Test root causes systematically
- Fix validated root cause

---

## Best Practices

### Do
- **Generate multiple hypotheses** (3-5 candidates)
- **Make hypotheses testable** (specify evidence needed)
- **Rank by likelihood AND testability** (best hypothesis is both)
- **Be specific** ("API timeout" not "it's slow")

### Don't
- **Don't anchor on first hypothesis** (generate alternatives first, then evaluate)
- **Don't make untestable hypotheses** ("gremlins" is not testable)
- **Don't skip validation** (hypothesis ≠ fact until tested)
- **Don't forget context** (use `/observe` output as input)

---

## See Also

- `/observe` - Capture observations to explain
- `/validate` - Test hypotheses
- `/trace` - Follow causality backward to root cause
- `/research` - Investigate hypotheses systematically
- `.claude/diagrams/thinking-process-architecture.md` - Section 5 (Metacognitive Commands)

---

## Prompt Template

You are executing the `/hypothesis` command with arguments: $ARGUMENTS

**Observation**: $1

---

### Execution Steps

**Step 1: Understand the Observation**

Parse the observation and identify:
- What phenomenon needs explanation?
- What's unexpected or surprising?
- What context is available?

**Step 2: Generate 3-5 Candidate Hypotheses**

For each hypothesis:
1. State hypothesis clearly: "X occurs because Y"
2. Explain mechanism: How would Y cause X?
3. Identify testable predictions: If true, what else should we observe?
4. Specify evidence needed: What would prove/disprove this?
5. Assess likelihood: High/Medium/Low based on available knowledge

**Generate diverse hypotheses** covering different causal mechanisms (external factors, internal bugs, configuration, timing, etc.)

**Step 3: Rank Hypotheses**

Rank by:
1. Likelihood (based on evidence, past observations, domain knowledge)
2. Testability (how easy to validate/falsify)

Prioritize hypotheses that are both likely AND testable.

**Step 4: Generate Validation Strategy**

For top 2-3 hypotheses:
- How to test (specific `/validate` or research actions)
- Expected outcomes (what would confirm/refute)
- Next steps (which hypothesis to test first, what to do if validated/refuted)

**Step 5: Output Structured Hypotheses**

Use the output format above, including:
- Context section (observation, known facts)
- 3-5 hypotheses (each with mechanism, predictions, evidence, likelihood)
- Ranked recommendations (which to test first, why)
- Next steps (concrete commands to run)

---

### Notes

- If observation is from `/observe` output, extract key details
- If observation is vague, infer context from conversation
- Focus on **testable** hypotheses (can be validated with evidence)
- Avoid vague hypotheses like "it's broken" or "something is wrong"
- Provide specific validation strategies (how to test each hypothesis)
