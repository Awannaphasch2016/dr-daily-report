---
name: observe
description: Capture execution traces, failure surfaces, and behavioral drift without interpretation (auto-detects mode from context)
accepts_args: true
arg_schema:
  - name: context
    required: true
    description: "Brief context/title (quoted if spaces) - mode auto-detected"
  - name: mode_or_details
    required: false
    description: "Explicit mode (execution/failure/behavior) OR additional details"
composition: []
---

# Observe Command

**Purpose**: Capture **what happened** without interpretation, enabling future analysis and disagreement

**Core Principle**: "/observe captures what happened so that future selves, agents, or evaluators can disagree safely."

**When to use**:
- After executing commands → `execution` mode
- When operations fail → `failure` mode
- Tracking decision patterns over time → `behavior` mode

---

## Quick Reference

### Smart Mode Detection (Recommended)
```bash
/observe "Deployed Lambda with new config"          # Auto-detects: execution
/observe "Lambda timeout after 30 seconds"          # Auto-detects: failure
/observe "Chose iterative approach over research"   # Auto-detects: behavior
```

### Explicit Mode (Backward Compatible)
```bash
/observe execution "Deployed Lambda with new config"
/observe failure "API timeout during peak traffic"
/observe behavior "Chose iterative approach over research"
```

**How it works**: Claude analyzes your text for keywords to determine mode. If ambiguous, you'll be asked to clarify.

---

## Observation Modes

### `execution` - Execution Trace Capture

**What it captures**:
- Tool calls made (Read, Write, Edit, Bash, etc.)
- Resources accessed (files, APIs, commands)
- Timing and sequence
- Cost/resource consumption
- Side effects produced

**When to use**:
- After significant command sequences
- Before/after deployment
- During debugging sessions
- When experimenting with new approaches

**Output**: Timestamped log of actions taken

---

### `failure` - Failure Surface Mapping

**What it captures**:
- Error messages (exact text)
- Stack traces (if available)
- Input state that triggered failure
- Environmental context (AWS, dependencies, config)
- Symptoms observed (not diagnosis)

**When to use**:
- Immediately after errors
- Before attempting fixes (capture state first)
- Production incidents
- Unexplained behavior

**Output**: Raw failure data without interpretation

---

### `behavior` - Behavioral Drift Detection

**What it captures**:
- Decision points and choices made
- Patterns in tool usage
- Preference shifts over time
- Deviation from documented principles

**When to use**:
- Weekly reflection on recent work
- Before/after adopting new patterns
- Tracking skill evolution
- Detecting principle drift

**Output**: Decision log for pattern analysis

---

## Smart Mode Detection

### How Claude Detects Mode

**Analyzes your text for keywords**:

#### `execution` mode detected when text contains:
- **Action verbs**: deployed, pushed, built, ran, executed, tested, updated, created
- **Infrastructure**: Lambda, Docker, ECR, deployed to, pushed to
- **Workflow**: pipeline, CI/CD, release, migration
- **Example**: "Deployed Lambda to staging" → execution ✅

#### `failure` mode detected when text contains:
- **Error keywords**: error, timeout, failed, exception, crash, bug, broken
- **HTTP codes**: 500, 503, 504, 403, 404
- **System failures**: OOM, segfault, connection refused, DNS failure
- **Example**: "Lambda timeout after 30 seconds" → failure ✅

#### `behavior` mode detected when text contains:
- **Decision keywords**: chose, decided, picked, selected, opted for
- **Pattern language**: pattern, approach, strategy, method
- **Iteration/Research**: iterated, researched, investigated, explored
- **Example**: "Chose iteration over research" → behavior ✅

### Ambiguous Cases

If text doesn't clearly match any mode:
```
🤔 Ambiguous observation - please clarify mode:

Your text: "Updated configuration"

Detected keywords:
  - "Updated" (could be execution or behavior)

Which mode did you intend?
  1. execution - You performed an action (updated config)
  2. failure - Something went wrong with the config
  3. behavior - You chose to update config (decision pattern)

Reply with number (1-3) or mode name.
```

**Override detection**: Provide explicit mode if auto-detection is wrong
```bash
/observe failure "Deployed successfully but..."  # Forces failure mode
```

---

## Execution Flow

### Step 1: Detect or Validate Mode

**If only context provided** (smart detection):
```bash
/observe "Lambda timeout in production"
```

1. Analyze text for keywords
2. Detect mode: `failure` (contains "timeout")
3. Confirm with user: "Detected failure mode - correct? (y/n)"
4. Proceed with detected mode

**If mode explicitly provided** (backward compatible):
```bash
/observe failure "Lambda timeout in production"
```

1. Validate mode is one of: `execution`, `failure`, `behavior`
2. Skip detection
3. Proceed with explicit mode

If invalid mode:
```
❌ Invalid mode: $1

Valid modes:
  execution - Capture tool calls, timing, resources
  failure   - Capture error surface without diagnosis
  behavior  - Track decision patterns over time

Usage: /observe "<context>" [mode or details]
   or: /observe <mode> "<context>" [details]
```

### Step 2: Generate Filename

```bash
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H%M%S)
SLUG=$(echo "$2" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
FILEPATH=".claude/observations/${DATE}/${1}-${TIME}-${SLUG}.md"
```

**Example**:
- Context: "Deployed Lambda with new config"
- Generated: `.claude/observations/2025-12-23/execution-143052-deployed-lambda-with-new-config.md`

**Why timestamp**: Multiple observations per day, need chronological ordering

### Step 3: Create Observation with Template

Choose template based on mode `$1`:

---

#### Template: `execution`

```markdown
---
mode: execution
date: {date}
time: {timestamp}
context: {$2}
session_id: {generate or retrieve from context}
tags: []
---

# Execution Observation: {$2}

**Started**: {timestamp}
**Session**: {session_id or "standalone"}
**Context**: {$2}

## Tool Calls

### {Tool Name} - {timestamp}
**Operation**: {what was done}
**Resources**: {files/APIs/commands accessed}
**Input**:
```
{input data or arguments}
```
**Output**:
```
{result or side effects}
```
**Duration**: {if measurable}
**Cost**: {if applicable - API calls, compute}

### {Tool Name} - {timestamp}
[Repeat for each tool call...]

## Side Effects

**Files Modified**:
- {file_path} - {what changed}
- {file_path} - {what changed}

**API Calls Made**:
- {API endpoint} - {result}

**Commands Executed**:
- {bash command} - {exit code} - {outcome}

## Resource Consumption

**Time**: {total duration}
**API Calls**: {count} ({cost if known})
**Files Touched**: {count}
**Network I/O**: {if measurable}

## Sequence

```
Tool1 → Tool2 → Tool3
  ↓       ↓       ↓
File    API    Command
```

## Raw Log

```
{Optional: Full conversation transcript or tool output}
```

---

**Additional Details**: ${3:-None}
```

---

#### Template: `failure`

```markdown
---
mode: failure
date: {date}
time: {timestamp}
context: {$2}
severity: high | medium | low
resolved: no
environment: production | staging | dev | local
tags: []
---

# Failure Observation: {$2}

**Occurred**: {timestamp}
**Severity**: {severity}
**Environment**: {environment}
**Context**: {$2}

## Symptoms Observed

**What went wrong** (observable behavior only, no interpretation):

[Describe exactly what was seen - error messages, unexpected output, system state]

## Error Messages

### Error 1
```
{Exact error text - no paraphrasing}
```

### Error 2
```
{Exact error text}
```

## Stack Traces

```
{Full stack trace if available}
```

## Input State

**What was attempted**:
```
{Command, API call, or operation that triggered failure}
```

**Input data**:
```
{Exact input provided}
```

**Expected outcome**:
{What should have happened}

**Actual outcome**:
{What actually happened}

## Environmental Context

**AWS Resources**:
- Lambda function: {name} ({version})
- Dependencies: {versions}
- Configuration: {relevant env vars}

**Code Version**:
- Branch: {branch_name}
- Commit: {commit_hash}
- Files involved: {paths}

**External Dependencies**:
- APIs: {which ones, versions}
- Databases: {connection info, state}
- Infrastructure: {relevant AWS services}

## Timeline

```
{timestamp} - Initiated operation
{timestamp} - First error observed
{timestamp} - Additional symptoms
{timestamp} - Operation terminated
```

## Data Captured

**Logs**:
```
{Relevant log excerpts - ERROR and WARNING levels}
```

**Metrics** (if available):
- Latency: {ms}
- Memory: {MB}
- Error rate: {%}

## What We DON'T Know Yet

- [ ] Root cause (requires investigation)
- [ ] Why this input triggered failure
- [ ] Whether this affects other cases
- [ ] Remediation steps

---

**Additional Details**: ${3:-None}

---

**Next Steps**: Use `/decompose failure` to analyze this observation, or `/journal error` after investigation completes.
```

---

#### Template: `behavior`

```markdown
---
mode: behavior
date: {date}
time: {timestamp}
context: {$2}
category: tool_usage | decision_pattern | principle_adherence
baseline: {reference to previous behavior observation if exists}
tags: []
---

# Behavior Observation: {$2}

**Observed**: {timestamp}
**Category**: {category}
**Context**: {$2}

## Decision Point

**Situation**:
{What required a decision}

**Options Considered**:
1. {Option 1}
2. {Option 2}
3. {Option 3}

**Choice Made**: {What was chosen}

**Reasoning Stated**:
{What rationale was given at the time}

## Tool Usage Pattern

**Tools Used** (in order):
1. {Tool name} - {purpose} - {outcome}
2. {Tool name} - {purpose} - {outcome}
3. {Tool name} - {purpose} - {outcome}

**Pattern Detected**:
{Describe the sequence or approach taken}

**Frequency**:
- This session: {count}
- This week: {count if tracking}
- This month: {count if tracking}

## Principle Adherence

**Relevant Principles** (from CLAUDE.md or skills):
- {Principle 1}: {adhered | deviated | unclear}
- {Principle 2}: {adhered | deviated | unclear}

**Deviations Observed**:
{If any principles were not followed, note without judgment}

## Comparison to Baseline

**Previous Behavior** (if baseline exists):
{How this compares to past decisions in similar situations}

**Drift Detected**:
- ✅ Consistent with documented approach
- ⚠️ Slight deviation: {describe}
- ❌ Significant deviation: {describe}

## Context Factors

**What influenced this decision**:
- Time pressure: {yes/no - details}
- New information: {what changed}
- Environmental constraints: {AWS limits, cost, etc.}
- Learning: {new pattern discovered}

## Metadata for Analysis

**Tags**: {tool_preference, research_first, iteration_first, etc.}
**Related Observations**: {links to other observations}
**Related Journal Entries**: {links if applicable}

---

**Additional Details**: ${3:-None}

---

**Next Steps**: Use `/abstract` to extract patterns from multiple behavior observations, or `/evolve` to detect drift from principles.
```

---

## Step 4: Write File

Write the template content to `$FILEPATH`:

```bash
mkdir -p ".claude/observations/$(date +%Y-%m-%d)"
cat > "$FILEPATH" << 'EOF'
[Template content from above based on mode]
EOF
```

Display confirmation:
```
✅ Created observation: .claude/observations/{date}/{mode}-{time}-{slug}.md

Mode: {mode}
Context: {context}

Next: {mode-specific suggestion}
```

### Step 5: Mode-Specific Suggestions

#### For `execution`:
```
💡 Next steps:
  - Review execution trace for inefficiencies
  - Extract patterns with /abstract if recurring workflow
  - Journal as architecture decision if significant choice made
  - Use /decompose to break down complex sequences
```

#### For `failure`:
```
💡 Next steps:
  - Run /decompose failure to analyze this observation
  - Investigate root cause (DO NOT modify observation file)
  - Once resolved, create /journal error with solution
  - Update relevant skill if pattern emerges
```

#### For `behavior`:
```
💡 Next steps:
  - Compare to previous behavior observations (if exist)
  - Run /abstract to extract patterns from multiple observations
  - If drift detected, investigate with /decompose
  - Run /evolve to check alignment with principles
```

---

## Examples

### Example 1: Execution Trace

```bash
/observe execution "Deployed Telegram API to staging"
```

**Creates**:
- File: `.claude/observations/2025-12-23/execution-143052-deployed-telegram-api-to-staging.md`
- Captures: Docker build → ECR push → Lambda update → smoke test sequence
- Suggests: "Extract deployment pattern with /abstract if reusable"

---

### Example 2: Failure Surface with Details

```bash
/observe failure "Lambda timeout during report generation" "User: user123, Ticker: NVDA19"
```

**Creates**:
- File: `.claude/observations/2025-12-23/failure-143205-lambda-timeout-during-report-generation.md`
- Includes: Error message, stack trace, input state, environment
- Includes user details: "user123" and "NVDA19" in Additional Details section
- Suggests: "Run /decompose failure to analyze"

---

### Example 3: Behavior Pattern

```bash
/observe behavior "Chose iteration over research despite 2 failures"
```

**Creates**:
- File: `.claude/observations/2025-12-23/behavior-143420-chose-iteration-over-research.md`
- Captures: Decision point, reasoning, deviation from "Research Before Iteration" principle
- Suggests: "Run /abstract to check if pattern shift is happening"

---

## Error Handling

### Invalid Mode

```bash
/observe invalid-mode "Some context"
```

**Response**:
```
❌ Invalid mode: invalid-mode

Valid modes:
  execution - Capture tool calls and resources
  failure   - Capture error surface
  behavior  - Track decision patterns

Usage: /observe <mode> "<context>" [details]
```

### Missing Context

```bash
/observe execution
```

**Response**:
```
❌ Missing required argument: context

Usage: /observe <mode> "<context>" [details]

Example: /observe execution "Deployed Lambda to staging"
```

---

## Directory Structure

```
.claude/
├── observations/         # NEW: Observation storage
│   ├── 2025-12-23/      # Daily directories
│   │   ├── execution-143052-deployed-lambda.md
│   │   ├── failure-143205-lambda-timeout.md
│   │   └── behavior-143420-iteration-over-research.md
│   └── 2025-12-24/      # Next day
│       └── ...
```

**Why daily directories**: Observations are timestamped and chronological, daily grouping aids review

---

## Integration with Other Commands

### Observation → Analysis Pipeline

```
/observe failure "..."
    ↓
/decompose failure .claude/observations/{date}/{file}.md
    ↓
/journal error "..." (after root cause found)
    ↓
/abstract (extract pattern from multiple failures)
    ↓
/evolve (update skills/principles if needed)
```

### Observation → Pattern Extraction

```
/observe behavior "..." (multiple times)
    ↓
/abstract .claude/observations/{date-range}/*.md
    ↓
/journal pattern "..." (if reusable pattern found)
```

---

## Principles

### 1. No Interpretation in Observations

**DO**: "Lambda returned 504 Gateway Timeout after 30.1 seconds"
**DON'T**: "Lambda timed out because it ran out of memory"

Observations capture **facts**, not **conclusions**. Save interpretation for `/decompose` or `/journal`.

### 2. Capture Raw Data

Include exact error messages, stack traces, logs - don't paraphrase. Future analysis benefits from unfiltered data.

### 3. Timestamp Everything

Use both date and time for observations. Multiple observations per day are common.

### 4. Link Observations

Reference related observations, journal entries, or code commits. Creates traceable investigation history.

### 5. Immutable After Creation

Don't edit observations after creation. If new information emerges, create a new observation or journal entry. Maintains chronological integrity.

---

## Related Commands

- `/decompose` - Analyze observations (break down failures/goals)
- `/abstract` - Extract patterns from multiple observations
- `/journal` - Interpret observations with solutions/decisions
- `/evolve` - Detect drift using behavior observations

---

## Maintenance

### Weekly Review

```bash
# List this week's observations
ls -lt .claude/observations/2025-12-{16..23}/*.md | head -20

# Look for patterns
grep "mode: failure" .claude/observations/**/*.md | wc -l
grep "mode: behavior" .claude/observations/**/*.md | wc -l
```

### Monthly Cleanup

**Archive old observations** (>90 days):
```bash
mkdir -p .claude/observations/archive/2025-Q1
mv .claude/observations/2025-01-* .claude/observations/archive/2025-Q1/
mv .claude/observations/2025-02-* .claude/observations/archive/2025-Q1/
mv .claude/observations/2025-03-* .claude/observations/archive/2025-Q1/
```

**Extract patterns before archiving**:
```bash
/abstract .claude/observations/2025-01-*/*.md
/abstract .claude/observations/2025-02-*/*.md
/abstract .claude/observations/2025-03-*/*.md
```

---

## Tips

### Do

- **Observe immediately** while details are fresh
- **Capture raw data** (error messages, stack traces, exact commands)
- **Include timestamps** for chronological ordering
- **Link related observations** (reference by filename)
- **Use failure mode generously** - no cost to capturing data

### Don't

- **Interpret too early** (save for /decompose or /journal)
- **Edit observations** (create new ones instead)
- **Skip context** (future you won't remember)
- **Paraphrase errors** (exact text matters for debugging)
- **Mix observation with analysis** (separate concerns)

---

## See Also

- `.claude/observations/README.md` - Observation system overview (to be created)
- `.claude/commands/decompose.md` - Analysis command
- `.claude/commands/abstract.md` - Pattern extraction
- `.claude/commands/journal.md` - Interpreted knowledge capture
- `.claude/commands/README.md` - Command system docs
