---
name: decompose
description: Break down goals or failures into components, dependencies, and preconditions (auto-detects mode from content)
accepts_args: true
arg_schema:
  - name: target
    required: true
    description: "Goal description, failure description, or path to observation file - mode auto-detected"
  - name: mode_or_depth
    required: false
    description: "Explicit mode (goal/failure) OR depth level (shallow/medium/deep)"
composition:
  - skill: research
---

# Decompose Command

**Purpose**: Break complex entities (goals, failures) into constituent parts for analysis

**Core Principle**: "Everything has parts" - understanding the part-whole relationship reveals dependencies, assumptions, and failure modes

**When to use**:
- Planning complex goals → `goal` mode
- Analyzing failures → `failure` mode
- Understanding dependencies → Both modes
- Revealing hidden assumptions → Both modes

---

## Quick Reference

### Smart Mode Detection (Recommended)
```bash
/decompose "Implement zero-downtime deployment"     # Auto-detects: goal
/decompose "Lambda timeout in production"           # Auto-detects: failure
/decompose ".claude/observations/.../failure-*.md"  # Auto-detects: failure (file path)
/decompose "Add caching layer" deep                 # Auto-detects: goal, depth: deep
```

### Explicit Mode (Backward Compatible)
```bash
/decompose goal "Implement zero-downtime deployment"
/decompose failure .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
/decompose goal "Add caching layer" deep
```

**How it works**:
- **File paths** → failure mode (observation files)
- **Action verbs** (Add, Implement, Build) → goal mode
- **Error keywords** (timeout, failed) → failure mode
- **Ambiguous** → Asks you to clarify

---

## Decomposition Modes

### `goal` - Goal Decomposition

**What it does**:
- Breaks goal into sub-goals
- Identifies dependencies (what must exist first)
- Reveals preconditions (assumptions that must hold)
- Exposes hidden complexity
- Suggests implementation order

**When to use**:
- Before starting complex features
- Planning multi-step migrations
- Understanding scope of "simple" requests
- Revealing what you don't know yet

**Output**: Dependency tree with preconditions

---

### `failure` - Failure Decomposition

**What it does**:
- Breaks failure into component failures
- Identifies which component actually failed
- Reveals cascade effects
- Maps failure surface
- Generates testable hypotheses

**When to use**:
- After capturing failure observation
- When root cause is unclear
- Multiple possible failure modes
- Cascading failures (A → B → C)

**Output**: Failure tree with hypotheses

---

## Smart Mode Detection

### How Claude Detects Mode

**Analyzes your input for signals**:

#### `goal` mode detected when:
- **Starts with action verbs**: Add, Implement, Build, Create, Migrate, Deploy, Refactor, Fix
- **Goal language**: feature, improvement, enhancement, upgrade, migration
- **Future tense**: "will", "need to", "should"
- **Examples**:
  - "Add caching layer to API" → goal ✅
  - "Implement zero-downtime deployment" → goal ✅
  - "Migrate to Aurora-First architecture" → goal ✅

#### `failure` mode detected when:
- **File path** to observation: `.claude/observations/.../failure-*.md`
- **Error keywords**: timeout, failed, error, exception, crash, broken
- **Problem description**: "bug in", "issue with", "not working"
- **Examples**:
  - ".claude/observations/2025-12-23/failure-143205-lambda-timeout.md" → failure ✅
  - "Lambda timeout in production" → failure ✅
  - "Bug in report generation" → failure ✅

### Ambiguous Cases

If input doesn't clearly match either mode:
```
🤔 Ambiguous decomposition - please clarify:

Your input: "Update authentication system"

Could be:
  1. goal - Planning to implement the update (what to do)
  2. failure - Authentication is broken (what went wrong)

Which mode? (1-2 or goal/failure)
```

**Override detection**: Provide explicit mode
```bash
/decompose failure "Add new feature"  # Forces failure mode (unusual but allowed)
```

---

## Execution Flow

### Step 1: Detect or Validate Mode

**If only target provided** (smart detection):
```bash
/decompose "Add caching layer to API"
```

1. Analyze for keywords: "Add" → action verb → `goal` mode
2. Confirm: "Detected goal decomposition - correct? (y/n)"
3. Proceed with goal mode

**If target is file path**:
```bash
/decompose ".claude/observations/2025-12-23/failure-143205-lambda-timeout.md"
```

1. Detect file path → `failure` mode
2. Load observation file
3. Proceed with failure mode

**If mode explicitly provided** (backward compatible):
```bash
/decompose goal "Add caching layer"
```

1. Validate mode is one of: `goal`, `failure`
2. Skip detection
3. Proceed with explicit mode

If invalid mode:
```
❌ Invalid mode: $1

Valid modes:
  goal    - Break down goals into sub-goals and dependencies
  failure - Break down failures into component failures

Usage: /decompose "<target>" [depth]
   or: /decompose <mode> "<target>" [depth]
```

### Step 2: Load Target

**For `goal` mode**:
- Target is a goal description (string)
- Parse goal into actionable statement

**For `failure` mode**:
- Target is path to observation file or failure description
- If file path: Load observation and extract failure data
- If description: Use as-is

**Depth levels**:
- `shallow` (default): 1 level of decomposition
- `medium`: 2-3 levels (most useful)
- `deep`: Full decomposition until atomic components

### Step 3: Invoke Research Skill

For both modes, use the `research` skill methodology to:
- Investigate codebase for relevant patterns
- Check existing documentation
- Search for similar past cases
- Understand current system state

### Step 4: Generate Decomposition

Choose template based on mode:

---

## Goal Decomposition Template

### Step 3A: Goal Decomposition

**Goal**: {$2}
**Depth**: {$3 or "medium"}

---

### Goal Breakdown

#### High-Level Goal
{$2}

#### Sub-Goals (Level 1)

1. **{Sub-goal 1}**
   - **Purpose**: {Why this is needed}
   - **Dependencies**: {What must exist first}
   - **Complexity**: {Estimate: trivial/simple/moderate/complex}
   - **Risk**: {Potential issues}

2. **{Sub-goal 2}**
   - **Purpose**: {Why this is needed}
   - **Dependencies**: {What must exist first}
   - **Complexity**: {Estimate: trivial/simple/moderate/complex}
   - **Risk**: {Potential issues}

3. **{Sub-goal 3}**
   [...]

#### Sub-Goals (Level 2) - If depth >= medium

**For Sub-goal 1**:
1.1. {Detailed sub-task}
     - Dependencies: {What's needed}
     - Completion criteria: {How to verify}

1.2. {Detailed sub-task}
     [...]

**For Sub-goal 2**:
2.1. {Detailed sub-task}
     [...]

---

### Dependency Graph

```
Goal: {$2}
  ├─ Sub-goal 1 (depends on: precondition A)
  │   ├─ Task 1.1 (depends on: codebase knowledge)
  │   └─ Task 1.2 (depends on: task 1.1)
  ├─ Sub-goal 2 (depends on: sub-goal 1)
  │   ├─ Task 2.1
  │   └─ Task 2.2 (depends on: external API)
  └─ Sub-goal 3 (depends on: sub-goal 2)
      └─ Task 3.1
```

---

### Preconditions (Assumptions That Must Hold)

**Known**:
- ✅ {Precondition that is verified}
- ✅ {Precondition that exists}

**Unknown**:
- ❓ {Assumption that needs verification}
- ❓ {Assumption that might not hold}

**Risks**:
- ⚠️ {Precondition that might break}
- ⚠️ {Assumption that could fail}

---

### Implementation Order

**Recommended sequence**:
1. Verify preconditions first (prevent surprises)
2. {Sub-goal with fewest dependencies}
3. {Sub-goal that unblocks others}
4. {Sub-goal that depends on previous}
5. Integration and testing

**Critical path**: {Which sub-goals are blocking}

**Parallelizable**: {Which sub-goals can be done simultaneously}

---

### Hidden Complexity

**What looks simple but isn't**:
- {Sub-goal that's deceptively complex}
- {Assumption that might not hold}
- {Integration point that's risky}

**What you don't know yet**:
- [ ] {Question that needs research}
- [ ] {Technical detail that's unclear}
- [ ] {External dependency that's unknown}

---

### Success Criteria

**How to verify each sub-goal**:
- Sub-goal 1: {Testable criterion}
- Sub-goal 2: {Testable criterion}
- Sub-goal 3: {Testable criterion}

**Overall goal complete when**:
- All sub-goals verified
- Integration tests pass
- {Domain-specific success criterion}

---

### Effort Estimate

**Complexity analysis**:
- Trivial tasks: {count} ({total estimated time})
- Simple tasks: {count} ({total estimated time})
- Moderate tasks: {count} ({total estimated time})
- Complex tasks: {count} ({total estimated time})

**Note**: Estimates are for understanding scope, not commitments.

---

### Next Steps

```
1. Verify preconditions ({list critical ones})
2. Use /observe execution to track implementation
3. Create /journal architecture if significant decisions needed
4. Use /evolve after completion to update patterns
```

---

## Failure Decomposition Template

### Step 3B: Failure Decomposition

**Failure**: {from $2 - observation file or description}
**Depth**: {$3 or "medium"}

---

### Failure Summary

**High-Level Failure**:
{What went wrong at the surface level}

**Observable Symptoms**:
- {Symptom 1}
- {Symptom 2}
- {Symptom 3}

**From Observation** (if file provided):
- File: {observation file path}
- Date: {from observation metadata}
- Environment: {from observation}
- Error: {exact error message from observation}

---

### Component Breakdown

#### System Components Involved

1. **{Component 1}** (e.g., Lambda function)
   - **Role in failure**: {What this component did}
   - **Expected behavior**: {What should have happened}
   - **Actual behavior**: {What actually happened}
   - **Failure mode**: {How this could fail}

2. **{Component 2}** (e.g., Database)
   - **Role in failure**: {What this component did}
   - **Expected behavior**: {What should have happened}
   - **Actual behavior**: {What actually happened}
   - **Failure mode**: {How this could fail}

3. **{Component 3}** (e.g., External API)
   [...]

---

### Failure Tree

```
Observable Failure: {high-level symptom}
  ├─ Component 1 failure?
  │   ├─ Sub-failure 1.1 (Hypothesis: ...)
  │   │   └─ Test: {...}
  │   └─ Sub-failure 1.2 (Hypothesis: ...)
  │       └─ Test: {...}
  ├─ Component 2 failure?
  │   ├─ Sub-failure 2.1 (Hypothesis: ...)
  │   └─ Sub-failure 2.2 (Hypothesis: ...)
  └─ Integration failure?
      └─ Sub-failure 3.1 (Hypothesis: ...)
```

---

### Hypotheses (Testable)

#### Hypothesis 1: {Component X failed because Y}
**Likelihood**: High | Medium | Low
**Test**: {How to verify this}
**Evidence for**:
- {Supporting evidence from observation}
- {Pattern from past failures}

**Evidence against**:
- {Contradictory evidence}

**Next step**: {What to investigate}

#### Hypothesis 2: {Component X failed because Z}
[...]

#### Hypothesis 3: {Integration between X and Y failed}
[...]

---

### Preconditions (What Was Assumed)

**Precondition 1**: {What must be true for success}
- **Verified?** ✅ Yes | ❌ No | ❓ Unknown
- **Actually held?** {Check against observation}

**Precondition 2**: {What must be true for success}
- **Verified?** ✅ Yes | ❌ No | ❓ Unknown
- **Actually held?** {Check against observation}

**Violated preconditions** (likely culprits):
- {Precondition that didn't hold}
- {Assumption that was wrong}

---

### Cascade Analysis

**Failure propagation**:
```
Root cause: {Most likely root}
     ↓
Immediate effect: {What failed first}
     ↓
Secondary effect: {What failed next}
     ↓
Observable symptom: {What user/system saw}
```

**Critical question**: Which layer actually failed?

---

### Investigation Plan

**Priority 1 - Most Likely** (test first):
1. {Hypothesis with highest likelihood}
   - Test: {Specific verification}
   - Tool: {Bash, AWS CLI, etc.}
   - Expected result: {What confirms hypothesis}

**Priority 2 - Medium Likelihood**:
2. {Next hypothesis}
   [...]

**Priority 3 - Low Likelihood** (test if others ruled out):
3. {Long-shot hypothesis}
   [...]

---

### Data Gaps

**What we need to know**:
- [ ] {Missing information from observation}
- [ ] {Metric not captured}
- [ ] {Log level insufficient}
- [ ] {Component state unknown}

**How to get it**:
- {Add logging to component}
- {Query CloudWatch for metric}
- {Check database state}

---

### Related Failures

**Similar past failures** (from observations or journals):
- `.claude/observations/{date}/failure-{similar}.md`
- `.claude/journals/error/{date}-{similar}.md`

**Pattern?** {If multiple similar failures, note pattern}

---

### Next Steps

```
1. Test Priority 1 hypotheses first
2. Use /observe execution to track investigation
3. Once root cause found, create /journal error
4. If pattern emerges, use /abstract across failures
5. Update relevant skill with prevention pattern
```

---

## Step 5: Generate Output

**For `goal` mode**:
Create markdown file: `.claude/decompositions/goal-{date}-{slug}.md`

**For `failure` mode**:
Create markdown file: `.claude/decompositions/failure-{date}-{slug}.md`

Display summary:
```
✅ Decomposition complete

Mode: {mode}
Target: {target}
Depth: {depth}
Output: .claude/decompositions/{mode}-{date}-{slug}.md

{Mode-specific next steps}
```

---

## Examples

### Example 1: Goal Decomposition (Simple)

```bash
/decompose goal "Add caching layer to API"
```

**Output**:
```markdown
Goal: Add caching layer to API
Sub-goals:
1. Choose caching strategy (Redis vs DynamoDB vs Aurora)
2. Implement cache storage
3. Add cache-check middleware
4. Handle cache invalidation
5. Add monitoring

Dependencies:
- Goal 2 depends on Goal 1 (strategy chosen)
- Goal 3 depends on Goal 2 (storage exists)
- Goal 4 depends on Goal 3 (cache is being used)

Preconditions:
✅ API endpoints defined
❓ Performance requirements known
⚠️ Cache invalidation strategy agreed upon

Hidden Complexity:
- Cache invalidation is hard (when to invalidate?)
- Consistency vs performance trade-off
- Cold cache behavior (stampeding herd)
```

---

### Example 2: Failure Decomposition (From Observation)

```bash
/decompose failure .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
```

**Loads observation**, extracts:
- Error: "Task timed out after 30.00 seconds"
- Component: Lambda function
- Environment: Production

**Output**:
```markdown
Failure: Lambda timeout in production

Components:
1. Lambda function (timeout: 30s)
2. Aurora database (query performance)
3. yfinance API (external dependency)

Failure Tree:
Lambda timeout
  ├─ yfinance API slow? (Hypothesis 1)
  │   └─ Test: Check API latency metrics
  ├─ Aurora query slow? (Hypothesis 2)
  │   └─ Test: Check slow query log
  └─ Lambda cold start? (Hypothesis 3)
      └─ Test: Check init duration metric

Hypotheses:
1. yfinance API latency spike (Likelihood: High)
   - Evidence: Known to have variability
   - Test: curl yfinance endpoint, measure time

2. Aurora query performance (Likelihood: Medium)
   - Evidence: Complex query might be slow
   - Test: Run EXPLAIN on query

3. Lambda cold start (Likelihood: Low)
   - Evidence: Would show in init duration metric
   - Test: Check CloudWatch metrics

Investigation Plan:
1. Check yfinance API latency (most likely)
2. Review Aurora slow query log
3. Check Lambda init duration metrics

Next: Use /observe execution to track investigation, /journal error when solved
```

---

### Example 3: Deep Goal Decomposition

```bash
/decompose goal "Migrate to Aurora-First architecture" deep
```

**Output**:
```markdown
Goal: Migrate to Aurora-First architecture

Level 1 Sub-goals:
1. Design Aurora schema
2. Implement data population pipeline
3. Update API to read from Aurora
4. Deprecate old data sources
5. Add monitoring

Level 2 Sub-goals:

1.1. Research Aurora data types (vs DynamoDB types)
     - Dependencies: None
     - Complexity: Simple
     - Risk: Type compatibility issues

1.2. Design table schema
     - Dependencies: 1.1 complete
     - Complexity: Moderate
     - Risk: Schema changes are expensive

1.3. Create migration scripts
     - Dependencies: 1.2 complete
     - Complexity: Moderate
     - Risk: Data loss if not idempotent

2.1. Build Lambda for nightly population
     [...]

Dependency Graph:
[Full tree with all dependencies]

Preconditions:
✅ Aurora cluster exists
✅ VPC networking configured
❓ Type compatibility verified (Need to test!)
⚠️ Migration can complete within maintenance window

Hidden Complexity:
- Type system incompatibility (NumPy → MySQL)
- Timezone handling (UTC vs Bangkok time)
- Idempotent migrations (can re-run safely)
- Zero-downtime migration strategy

Effort Estimate:
- Research: 4-6 hours (type compatibility, schema design)
- Implementation: 16-24 hours (pipeline, API changes, testing)
- Testing: 8-12 hours (integration tests, migration dry-run)
- Deployment: 4-6 hours (staged rollout)

Total: 32-48 hours (not including surprises)
```

---

## Error Handling

### Invalid Mode

```bash
/decompose invalid-mode "something"
```

**Response**:
```
❌ Invalid mode: invalid-mode

Valid modes:
  goal    - Break down goals into sub-goals
  failure - Break down failures into components

Usage: /decompose <mode> "<target>" [depth]
```

### Missing Target

```bash
/decompose goal
```

**Response**:
```
❌ Missing required argument: target

For goal mode: Provide goal description
For failure mode: Provide observation file path or failure description

Usage: /decompose goal "Add feature X"
Usage: /decompose failure .claude/observations/{date}/{file}.md
```

### File Not Found (Failure Mode)

```bash
/decompose failure .claude/observations/nonexistent.md
```

**Response**:
```
❌ Observation file not found: .claude/observations/nonexistent.md

Use /observe failure "..." to create observation first, then decompose.
Or provide failure description directly:
/decompose failure "Lambda timeout in production"
```

---

## Directory Structure

```
.claude/
├── decompositions/       # NEW: Decomposition outputs
│   ├── goal-2025-12-23-add-caching.md
│   ├── failure-2025-12-23-lambda-timeout.md
│   └── ...
```

---

## Integration with Other Commands

### Decompose → Journal (After Understanding)

```
/decompose goal "Complex feature"
    ↓ (reveals decisions needed)
/journal architecture "Choice between X and Y"
    ↓ (decision made)
/observe execution "Implementing approach X"
```

### Observe → Decompose → Journal (Failure Investigation)

```
/observe failure "Production error"
    ↓ (raw data captured)
/decompose failure .claude/observations/{file}.md
    ↓ (hypotheses generated)
[Test hypotheses, find root cause]
    ↓
/journal error "Root cause was X" "Solution: Y"
```

### Decompose → Abstract (Pattern Recognition)

```
/decompose failure [failure 1]
/decompose failure [failure 2]
/decompose failure [failure 3]
    ↓ (multiple decompositions exist)
/abstract .claude/decompositions/failure-*.md
    ↓ (pattern emerges: all timeouts from external APIs)
/journal pattern "External API timeout handling"
```

---

## Principles

### 1. Start Shallow, Go Deeper If Needed

Default to `medium` depth. Only go `deep` if:
- Goal is very complex
- Initial decomposition reveals more complexity
- Planning requires detailed breakdown

### 2. Decompose Before Implementing

For non-trivial goals, decompose first to:
- Reveal hidden complexity
- Identify unknown unknowns
- Estimate effort realistically
- Plan implementation order

### 3. Decompose Failures Before Fixing

For non-obvious failures, decompose before iterating fixes to:
- Generate testable hypotheses
- Avoid guessing
- Map failure surface systematically
- Prevent treating symptoms instead of root cause

### 4. Link to Observations

Failure decompositions should reference observation files to maintain data trail and enable re-analysis if hypotheses prove wrong.

---

## Related Commands

- `/observe` - Capture failures before decomposing
- `/abstract` - Extract patterns from multiple decompositions
- `/journal` - Document solutions after decomposition completes
- `/evolve` - Update principles based on decomposition learnings

---

## See Also

- `.claude/commands/observe.md` - Observation command
- `.claude/commands/abstract.md` - Pattern extraction
- `.claude/commands/journal.md` - Knowledge journaling
- `.claude/skills/research/` - Research skill methodology
- `.claude/commands/README.md` - Command system overview
