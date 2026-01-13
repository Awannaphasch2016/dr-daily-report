---
name: validate
description: Validate claims and assumptions with evidence before implementing (auto-detects validation type)
accepts_args: true
arg_schema:
  - name: claim
    required: true
    description: "Claim to validate (quoted if spaces)"
  - name: validation_type
    required: false
    description: "Optional: code, performance, config, behavior, hypothesis"
composition:
  - skill: research
---

# Validate Command

**Purpose**: Validate claims and assumptions with evidence **before** implementing or investing time

**Core Principle**: "Trust but verify" - assumptions that prove false waste time and create bugs. Validate before building.

**When to use**:
- Before implementing features → Validate assumptions
- Planning optimizations → Validate bottlenecks exist
- Making architectural decisions → Validate constraints
- Debugging → Validate hypotheses
- Code review → Validate security/performance claims

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `verify`

When `/validate` executes as a mode within a Strategy pipeline:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **REFINE**: Adds evidence (supporting/contradicting) |
| **Invariant** | **TEST**: Evaluates claim against evidence |
| **Principles** | **NONE**: Does not modify principles |
| **Strategy** | Consumes this mode; informs subsequent modes |
| **Check** | Annotates with confidence level (see Local Check) |

**Constraint Refinement Examples**:
```yaml
before:
  constraints:
    assumption: "yfinance API responds within 5s"
    evidence: []

after:
  constraints:
    assumption: "yfinance API responds within 5s"
    evidence:
      supporting: []
      contradicting:
        - "CloudWatch p95 latency: 8.7s"
        - "23% of requests exceed 5s threshold"
      confidence: LOW
    verdict: FALSE
```

**Check Annotation**:
```yaml
check:
  claim: "yfinance API responds within 5s"
  result: FALSE
  confidence: HIGH
  evidence_layers:
    layer_3: "CloudWatch logs show p95 = 8.7s"
  recommendation: "Add timeout=5 + fallback to cache"
```

---

## Local Check (Mode Completion Criteria)

The `/validate` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Evidence Collected** | Both supporting AND contradicting evidence sought |
| **Confidence Assigned** | HIGH, MEDIUM, or LOW with reasoning |
| **Verdict Rendered** | TRUE, FALSE, PARTIALLY TRUE, or INCONCLUSIVE |
| **Sources Documented** | Evidence sources linked (code, logs, observations) |
| **Recommendation Given** | Clear next step based on verdict |

**Check Result Mapping**:
- **PASS**: Claim validated with high confidence → proceed with assumption
- **PARTIAL**: Claim partially true → proceed with caveats documented
- **FAIL**: Claim false → alternative approach needed; DO NOT proceed

**Integration with Check Loop**:
The confidence level from `/validate` feeds directly into the tuple's Check component, allowing the Check Loop to make informed decisions about whether to proceed or spin a new tuple.

---

## Quick Reference

### Smart Validation (Auto-detects Type)
```bash
/validate "yfinance API responds within 5s"              # Detects: performance
/validate "All Lambda functions have timeouts < 30s"     # Detects: code
/validate "Users prefer cached data over fresh data"     # Detects: behavior
/validate "AURORA_HOST is set in all environments"       # Detects: config
```

### Explicit Type (Override)
```bash
/validate "API is slow" performance
/validate "Code has no TODOs" code
```

---

## Validation Types

### `code` - Code Structure Validation
**What it validates**:
- Code patterns exist/don't exist
- Functions/classes defined
- Dependencies imported
- TODOs/FIXMEs present

**Example**: "All external API calls have timeout parameter"

---

### `performance` - Performance Claims
**What it validates**:
- Latency thresholds
- Resource usage (memory, CPU)
- Query performance
- API response times

**Example**: "Aurora query completes in < 100ms for 10k rows"

---

### `config` - Configuration Validation
**What it validates**:
- Environment variables set
- Configuration values correct
- Infrastructure state
- AWS resources configured

**Example**: "Lambda timeout is 60s in production"

---

### `behavior` - User/System Behavior
**What it validates**:
- User preferences
- System behavior patterns
- Feature usage
- Error frequencies

**Example**: "Users rarely need reports older than 30 days"

---

### `hypothesis` - Hypothesis Testing
**What it validates**:
- Root cause hypotheses
- Causal relationships
- Assumptions about system state

**Example**: "Lambda timeout is caused by cold start, not API slowness"

---

## Smart Type Detection

### How Claude Detects Validation Type

#### `code` detected when claim mentions:
- **Code elements**: function, class, method, import, dependency
- **Code patterns**: "has timeout", "uses pattern", "implements"
- **File references**: specific file paths
- **Example**: "All Lambda handlers import logging" → code ✅

#### `performance` detected when claim mentions:
- **Metrics**: latency, response time, duration, throughput
- **Thresholds**: "< 5s", "> 100ms", "within X seconds"
- **Resources**: memory, CPU, I/O, network
- **Example**: "API responds within 5s" → performance ✅

#### `config` detected when claim mentions:
- **Environment vars**: AURORA_HOST, API_KEY, ENV
- **Infrastructure**: Lambda timeout, S3 bucket, VPC
- **Settings**: configuration, parameter, setting
- **Example**: "AURORA_HOST is set in dev environment" → config ✅

#### `behavior` detected when claim mentions:
- **Users**: user preference, user behavior, users want
- **Frequency**: rarely, often, always, never
- **Patterns**: pattern, trend, tendency
- **Example**: "Users prefer X over Y" → behavior ✅

#### `hypothesis` detected when claim mentions:
- **Causation**: "caused by", "due to", "because of"
- **Root cause**: "root cause is", "problem is"
- **Speculation**: "might be", "could be", "likely"
- **Example**: "Timeout caused by API slowdown" → hypothesis ✅

---

## Execution Flow

### Step 1: Parse Claim and Detect Type

**Smart detection**:
```bash
/validate "All Lambda functions have timeout configured"
```

1. Analyze claim: "Lambda functions" + "timeout" + "configured" → `config` + `code`
2. Primary type: `config` (infrastructure setting)
3. Confirm: "Detected config validation - correct? (y/n)"
4. Proceed with validation

**Explicit type**:
```bash
/validate "API is slow" performance
```

1. Skip detection
2. Use explicit type: `performance`
3. Proceed with validation

---

### Step 2: Determine Evidence Needed

**For each validation type**, identify what evidence would prove/disprove:

#### Code Validation Evidence
- **Source code**: Grep for patterns, functions, imports
- **Test files**: Check if tests exist
- **Dependencies**: Check package.json, requirements.txt

#### Performance Validation Evidence
- **Metrics**: CloudWatch logs, Lambda metrics
- **Benchmarks**: Run performance tests
- **Observations**: Past failure observations with timing data

#### Config Validation Evidence
- **Live config**: Query AWS (Lambda get-function-configuration)
- **Environment files**: Check Doppler, .env files
- **Terraform state**: Check infrastructure definitions

#### Behavior Validation Evidence
- **Analytics**: User behavior data (if exists)
- **Logs**: Usage patterns from CloudWatch
- **Observations**: Past behavior observations

#### Hypothesis Validation Evidence
- **Correlation analysis**: Do events correlate?
- **Controlled tests**: Reproduce with/without factor
- **Observations**: Past failure investigations

---

### Step 3: Invoke Research Skill

Use `research` skill methodology to:
- Search systematically across sources
- Collect evidence
- Avoid confirmation bias (look for counter-evidence too)
- Document what was found

---

### Step 4: Collect Evidence

**Search locations** (based on type):

1. **Codebase** (Grep, Read):
   - Source files
   - Test files
   - Configuration files

2. **Observations** (.claude/observations/):
   - Execution traces
   - Failure reports
   - Behavior observations

3. **Journals** (.claude/journals/):
   - Architecture decisions
   - Error solutions
   - Pattern documentation

4. **Live Systems** (Bash):
   - AWS CLI queries
   - CloudWatch logs
   - Infrastructure state

5. **Abstractions** (.claude/abstractions/):
   - Extracted patterns
   - Workflow templates

---

### Step 5: Analyze Evidence

**Categorize findings**:

```markdown
Evidence FOR claim:
  - [Source]: [Finding]
  - [Source]: [Finding]

Evidence AGAINST claim:
  - [Source]: [Finding]
  - [Source]: [Finding]

Inconclusive/Missing:
  - [What we couldn't verify]
  - [What data is missing]
```

**Calculate confidence**:
- **Strong evidence**: Direct measurements, code verification
- **Weak evidence**: Indirect indicators, assumptions
- **Missing evidence**: Gaps in data

---

### Step 6: Generate Validation Report

```markdown
# Validation Report

**Claim**: {claim}
**Type**: {detected or explicit type}
**Date**: {timestamp}

---

## Status: {✅ TRUE | ❌ FALSE | ⚠️ PARTIALLY TRUE | 🤔 INCONCLUSIVE}

## Evidence Summary

**Supporting evidence** ({count} items):
1. **{Source}**: {Finding}
   - Location: {file path or AWS resource}
   - Data: {specific measurement or observation}
   - Confidence: High | Medium | Low

2. **{Source}**: {Finding}
   [...]

**Contradicting evidence** ({count} items):
1. **{Source}**: {Finding}
   - Location: {file path or AWS resource}
   - Data: {specific measurement or observation}
   - Impact: {why this contradicts claim}

**Missing evidence**:
- {What we need but don't have}
- {How to get it}

---

## Analysis

### Overall Assessment

{Detailed explanation of why claim is true/false/partially true/inconclusive}

### Key Findings

- Finding 1: {Significance}
- Finding 2: {Significance}
- Finding 3: {Significance}

### Confidence Level: {High | Medium | Low}

**Reasoning**: {Why we're confident/uncertain}

---

## Recommendations

**If TRUE**:
- Proceed with assumption
- Document in: {where to document}
- Related: {related observations/journals}

**If FALSE**:
- DO NOT proceed with assumption
- Alternative approach: {suggestion}
- Update understanding: {what we learned}
- Related failures: {past observations where this assumption caused issues}

**If PARTIALLY TRUE**:
- Proceed with caution
- Caveats: {what conditions must hold}
- Fallback: {what to do if conditions don't hold}

**If INCONCLUSIVE**:
- Gather more evidence:
  1. {Action to get evidence}
  2. {Action to get evidence}
- Consider: {what to do in absence of evidence}
- Risk: {risk of proceeding without validation}

---

## Next Steps

- [ ] {Action based on validation result}
- [ ] {Action based on validation result}
- [ ] Document in /journal if significant finding
- [ ] Create /observe if need to track over time

---

## References

**Observations**:
- {.claude/observations/.../file.md}

**Journals**:
- {.claude/journals/.../file.md}

**Code**:
- {file_path:line_number}

**AWS Resources**:
- {resource type}: {resource ID}

**Metrics**:
- {CloudWatch log group}: {insight}
```

---

### Step 7: Save Validation Report

Create: `.claude/validations/{date}-{slug}.md`

**Example**: `.claude/validations/2025-12-24-yfinance-api-response-time.md`

Display summary:
```
✅ Validation complete

Claim: "yfinance API responds within 5s"
Status: ❌ FALSE
Confidence: High

Key finding: 23% of requests exceed 5s (CloudWatch p95: 8.7s)

Report: .claude/validations/2025-12-24-yfinance-api-response-time.md

Recommendation: Add timeout + fallback to cached data
See: /journal error "Lambda timeout caused by yfinance API slowdown"
```

---

## Examples

### Example 1: Performance Validation

```bash
/validate "yfinance API responds within 5s"
```

**Execution**:
1. Detect type: `performance` (has "responds within 5s")
2. Evidence needed: API latency metrics, observations, code
3. Collect:
   - CloudWatch logs: p95 latency = 8.7s ❌
   - Observations: 3 timeout failures citing slow yfinance
   - Code: No timeout configured ❌
4. Result: **FALSE** (23% exceed threshold)

**Report**:
```markdown
Status: ❌ FALSE

Evidence AGAINST:
1. CloudWatch Logs (last 7 days):
   - p95 latency: 8.7s (exceeds 5s threshold)
   - 23% of requests > 5s

2. Observations:
   - failure-143205-lambda-timeout.md: "yfinance took 12s"
   - failure-091234-api-slow.md: "yfinance latency spike to 18s"

3. Code:
   - src/data/ticker_fetcher.py:42 - No timeout configured

Conclusion: FALSE - API does NOT consistently respond within 5s

Recommendation: Add timeout=5 + fallback to cache
```

---

### Example 2: Code Validation

```bash
/validate "All external API calls have timeout parameter"
```

**Execution**:
1. Detect type: `code` (has "API calls" + "parameter")
2. Evidence needed: Grep for API calls, check timeout params
3. Collect:
   ```bash
   # Find API calls
   grep -r "requests.get\|requests.post" src/

   # Check for timeout parameter
   grep -r "timeout=" src/
   ```
4. Result: **PARTIALLY TRUE** (2 out of 5 have timeout)

**Report**:
```markdown
Status: ⚠️ PARTIALLY TRUE

Evidence:
1. External API calls found: 5 locations
   - src/data/ticker_fetcher.py:42 (yfinance)
   - src/data/news_fetcher.py:28 (NewsAPI)
   - src/services/openrouter.py:67 (OpenRouter)
   - src/services/notification.py:45 (LINE API)
   - src/services/notification.py:89 (Telegram API)

2. Timeout configured: 2/5 ❌
   ✅ src/services/openrouter.py:67 - timeout=30
   ✅ src/services/notification.py:45 - timeout=10
   ❌ src/data/ticker_fetcher.py:42 - NO TIMEOUT
   ❌ src/data/news_fetcher.py:28 - NO TIMEOUT
   ❌ src/services/notification.py:89 - NO TIMEOUT

Conclusion: PARTIALLY TRUE - Only 40% have timeout

Recommendation: Add timeout to remaining 3 API calls
Priority: High (yfinance caused 3 production timeouts)
```

---

### Example 3: Config Validation

```bash
/validate "Lambda timeout is 60s in production"
```

**Execution**:
1. Detect type: `config` (has "Lambda timeout" + environment)
2. Evidence needed: Query AWS Lambda configuration
3. Collect:
   ```bash
   ENV=prod doppler run -- aws lambda get-function-configuration \
     --function-name dr-daily-report-telegram-api
   ```
4. Result: **FALSE** (timeout is 30s, not 60s)

**Report**:
```markdown
Status: ❌ FALSE

Evidence:
1. AWS Lambda Configuration (production):
   Function: dr-daily-report-telegram-api
   Timeout: 30 seconds ❌
   Expected: 60 seconds

2. Terraform configuration:
   File: terraform/lambda.tf:45
   Value: timeout = 30

Conclusion: FALSE - Lambda timeout is 30s, not 60s

Recommendation:
- If 60s timeout needed, update Terraform:
  terraform/lambda.tf:45 → timeout = 60
- Re-deploy to apply change
```

---

### Example 4: Hypothesis Validation

```bash
/validate "Lambda timeout is caused by cold start, not API slowness"
```

**Execution**:
1. Detect type: `hypothesis` (has "caused by" causation)
2. Evidence needed: Lambda init metrics vs API latency
3. Collect:
   - CloudWatch Lambda metrics: InitDuration
   - CloudWatch logs: API call timing
   - Observations: Failure timing data
4. Result: **FALSE** (cold start avg 2s, API calls 8-15s)

**Report**:
```markdown
Status: ❌ FALSE

Hypothesis: "Lambda timeout is caused by cold start, not API slowness"

Evidence AGAINST hypothesis:
1. Lambda Cold Start Metrics (last 7 days):
   - Average InitDuration: 2.1s
   - p95 InitDuration: 3.4s
   - Max InitDuration: 5.2s
   → Cold starts account for max 5.2s, not 30s timeout

2. API Call Timing (CloudWatch logs):
   - yfinance calls: 8-15s (p95: 12.3s)
   - NewsAPI calls: 3-8s (p95: 6.1s)
   → API calls account for 14-23s combined

3. Observations:
   - 3 timeout failures all cite "waiting for yfinance"
   - None mention cold start issues

Conclusion: FALSE
- Cold start contributes ~3s (10% of timeout)
- API slowness contributes ~15s (50% of timeout)
- ROOT CAUSE: API slowness, NOT cold start

Recommendation:
- Focus optimization on API calls (timeout + fallback)
- Cold start optimization is secondary
- Update hypothesis: "Lambda timeout caused primarily by API slowness"
```

---

## Error Handling

### Missing Claim

```bash
/validate
```

**Response**:
```
❌ Missing required argument: claim

Usage: /validate "<claim>" [type]

Examples:
  /validate "API responds within 5s"
  /validate "All functions have tests" code
```

### Ambiguous Type

```bash
/validate "System is slow"
```

**Response**:
```
🤔 Ambiguous validation type - please clarify:

Claim: "System is slow"

Could be:
  1. performance - Measure actual latency/throughput
  2. behavior - User perception of slowness
  3. hypothesis - System slow due to specific cause

Which type? (1-3 or type name)
```

### Insufficient Evidence

```bash
/validate "Users prefer dark mode"
```

**Response** (in report):
```
Status: 🤔 INCONCLUSIVE

Evidence:
- No analytics data available ❌
- No user surveys ❌
- No A/B test results ❌

Missing Evidence:
- User behavior logs
- Feature usage metrics
- User feedback/surveys

Recommendation:
Cannot validate without data. Options:
1. Implement analytics to track dark mode usage
2. Survey users
3. A/B test dark mode vs light mode
4. Assume based on industry standards (risky)

Risk of proceeding: Medium - might build unwanted feature
```

---

## Directory Structure

```
.claude/
├── validations/          # NEW: Validation reports
│   ├── 2025-12-24-yfinance-api-response-time.md
│   ├── 2025-12-24-lambda-timeout-config.md
│   └── ...
```

---

## Integration with Other Commands

### Before Planning: Validate → Decompose
```
/validate "Aurora query is the bottleneck"
    ↓ (if TRUE)
/decompose goal "Optimize Aurora query performance"
    ↓
/journal architecture "Chose to add index on ticker column"
```

### During Investigation: Observe → Decompose → Validate
```
/observe failure "Lambda timeout"
    ↓
/decompose failure .claude/observations/.../failure-*.md
    ↓ (generates hypotheses)
/validate "Hypothesis 1: Cold start is the cause"
/validate "Hypothesis 2: API slowness is the cause"
    ↓ (hypothesis 2 validated as TRUE)
/journal error "Lambda timeout caused by yfinance API"
```

### Before Deciding: Validate → Compare → Journal
```
/validate "Redis is faster than DynamoDB"
/validate "Redis costs more than DynamoDB"
    ↓ (both TRUE)
/compare "Redis vs DynamoDB for caching"
    ↓
/journal architecture "Chose DynamoDB (cost > speed for our use case)"
```

---

## Principles

### 1. Validate Before Building

Don't build on false assumptions. Validate critical assumptions before implementation.

### 2. Evidence Over Intuition

Intuition is a hypothesis. Validate with evidence.

### 3. Seek Counter-Evidence

Don't just look for confirmation. Actively seek evidence that contradicts your claim.

### 4. Document Uncertainty

If evidence is inconclusive, document that. Uncertainty is information.

### 5. Automate Validation

If claim can be tested automatically (code patterns, config values), automate it.

---

## Related Commands

- `/decompose` - Break down goals (reveals assumptions to validate)
- `/observe` - Capture evidence for future validation
- `/abstract` - Extract validation patterns from multiple validations
- `/journal` - Document significant validation findings

---

## See Also

- `.claude/commands/decompose.md` - Goal/failure decomposition
- `.claude/commands/observe.md` - Evidence capture
- `.claude/skills/research/` - Research methodology
- `.claude/commands/README.md` - Command system overview
