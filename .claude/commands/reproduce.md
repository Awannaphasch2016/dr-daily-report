---
name: reproduce
description: Generate step-by-step reproduction guide from observation files (execution, failure, behavior modes)
accepts_args: true
arg_schema:
  - name: observation_file
    required: true
    description: "Path to observation file (.claude/observations/{date}/{mode}-{time}-{slug}.md)"
composition:
  - skill: research
---

# Reproduce Command

**Purpose**: Convert observation files into actionable reproduction guides for debugging, onboarding, and documentation

**Core Principle**: "Reproduction enables fixing" - if you can't reproduce it, you can't fix it. Observations capture what happened; reproduction guides show how to trigger it again.

**When to use**:
- After capturing failure observation → create repro steps for issue report
- After complex deployment → create runbook from execution trace
- After behavioral pattern → create example workflow
- For onboarding → show how specific tasks are done
- Before fixing → verify you can reproduce the issue

---

## Quick Reference

```bash
# From failure observation
/reproduce ".claude/observations/2025-12-23/failure-143205-lambda-timeout.md"

# From execution trace
/reproduce ".claude/observations/2025-12-23/execution-143052-deployed-lambda.md"

# From behavior pattern
/reproduce ".claude/observations/2025-12-23/behavior-143420-iteration-over-research.md"
```

---

## Observation Modes

### `execution` - Execution Trace → Deployment Runbook

**Input**: Observation capturing successful execution (deployment, migration, complex task)

**Output**: Step-by-step runbook with:
- Prerequisites (environment, tools, permissions)
- Exact commands to execute (from observation)
- Verification steps
- Expected timing
- Rollback procedure

**Use case**: "How do I deploy this?" or "How was this task done?"

---

### `failure` - Failure Surface → Bug Reproduction

**Input**: Observation capturing failure (error, timeout, crash)

**Output**: Bug reproduction guide with:
- Prerequisites (input data, environment state)
- Steps to trigger failure
- Expected error message
- Debugging commands
- Verification that fix resolves issue

**Use case**: "How do I reproduce this bug?" or "How do I test my fix?"

---

### `behavior` - Behavioral Pattern → Workflow Example

**Input**: Observation capturing decision-making behavior (tool usage, approach choice)

**Output**: Workflow example with:
- When to use this approach
- Step-by-step decision process
- Commands executed in sequence
- Principle adherence notes
- Outcome comparison vs alternatives

**Use case**: "When should I use this pattern?" or "How was this decision made?"

---

## Execution Flow

### Step 1: Validate Input

```bash
OBSERVATION_FILE="$1"

# Check file exists
if [[ ! -f "$OBSERVATION_FILE" ]]; then
  echo "❌ Observation file not found: $OBSERVATION_FILE"
  echo ""
  echo "Expected format: .claude/observations/{date}/{mode}-{time}-{slug}.md"
  echo ""
  echo "List recent observations:"
  echo "  find .claude/observations/ -name '*.md' -mtime -7"
  exit 1
fi

# Check file is in observations directory
if [[ ! "$OBSERVATION_FILE" =~ \.claude/observations/ ]]; then
  echo "⚠️  Warning: File is not in .claude/observations/ directory"
  echo "Are you sure this is an observation file?"
fi
```

**Validation checks**:
- File exists
- File is in `.claude/observations/` directory
- File has observation frontmatter

---

### Step 2: Parse Observation File

```bash
# Extract frontmatter
MODE=$(awk '/^mode:/ {print $2; exit}' "$OBSERVATION_FILE")
CONTEXT=$(awk '/^context:/ {$1=""; print substr($0,2); exit}' "$OBSERVATION_FILE")
DATE=$(awk '/^date:/ {print $2; exit}' "$OBSERVATION_FILE")
ENVIRONMENT=$(awk '/^environment:/ {print $2; exit}' "$OBSERVATION_FILE")
TAGS=$(awk '/^tags:/ {$1=""; print substr($0,2); exit}' "$OBSERVATION_FILE")

# Validate mode
if [[ ! "$MODE" =~ ^(execution|failure|behavior)$ ]]; then
  echo "❌ Invalid observation mode: $MODE"
  echo "Expected: execution, failure, or behavior"
  exit 1
fi
```

**Extracted information**:
- Mode (execution/failure/behavior)
- Context (what was happening)
- Date/time observed
- Environment (dev/staging/prod)
- Tags

---

### Step 3: Extract Content Sections (Mode-Specific)

**For execution mode**:
```bash
# Extract: Actions Taken, Commands Executed, Resources, Timing
ACTIONS=$(sed -n '/## Actions Taken/,/^##/p' "$OBSERVATION_FILE")
COMMANDS=$(sed -n '/## Commands Executed/,/^##/p' "$OBSERVATION_FILE")
RESOURCES=$(sed -n '/## Resources Accessed/,/^##/p' "$OBSERVATION_FILE")
TIMING=$(sed -n '/## Timing/,/^##/p' "$OBSERVATION_FILE")
SIDE_EFFECTS=$(sed -n '/## Side Effects/,/^##/p' "$OBSERVATION_FILE")
```

**For failure mode**:
```bash
# Extract: Error Messages, Input State, Environment, Stack Traces
ERROR_MSG=$(sed -n '/## Error Messages/,/^##/p' "$OBSERVATION_FILE")
INPUT_STATE=$(sed -n '/## Input State/,/^##/p' "$OBSERVATION_FILE")
ENV_CONTEXT=$(sed -n '/## Environment Context/,/^##/p' "$OBSERVATION_FILE")
STACK_TRACE=$(sed -n '/## Stack Traces/,/^##/p' "$OBSERVATION_FILE")
SYMPTOMS=$(sed -n '/## Symptoms Observed/,/^##/p' "$OBSERVATION_FILE")
```

**For behavior mode**:
```bash
# Extract: Decision Points, Tool Usage, Principles
DECISIONS=$(sed -n '/## Decision Points/,/^##/p' "$OBSERVATION_FILE")
TOOL_USAGE=$(sed -n '/## Tool Usage Patterns/,/^##/p' "$OBSERVATION_FILE")
PRINCIPLES=$(sed -n '/## Principle Adherence/,/^##/p' "$OBSERVATION_FILE")
BASELINE=$(sed -n '/## Comparison to Baseline/,/^##/p' "$OBSERVATION_FILE")
```

---

### Step 4: Use Research Skill

Invoke research skill to:
- Systematically analyze observation content
- Extract commands and sequences
- Identify prerequisites and dependencies
- Structure reproduction steps logically
- Avoid missing critical context

---

### Step 5: Generate Reproduction Guide (Mode-Specific Template)

Choose template based on observation mode:

**execution mode** → Generate deployment runbook
**failure mode** → Generate bug reproduction guide
**behavior mode** → Generate workflow example

---

### Step 6: Create Reproduction Directory

```bash
# Create reproductions directory if not exists
mkdir -p .claude/reproductions

# Generate filename
DATE=$(date +%Y-%m-%d)
SLUG=$(basename "$OBSERVATION_FILE" | sed 's/^[a-z]*-[0-9]*-//' | sed 's/.md$//')
REPRO_FILE=".claude/reproductions/${DATE}-${SLUG}.md"

# Write reproduction guide
cat > "$REPRO_FILE" <<'EOF'
{generated content}
EOF
```

---

### Step 7: Output Reproduction Document

Display summary:
```
✅ Reproduction guide created

Source: {observation_file}
Mode: {execution|failure|behavior}
Output: {reproduction_file}

Next steps:
  - Review reproduction guide
  - Test reproduction steps
  - Update if steps incomplete
  - Share with team if needed
```

---

## Output Templates

### Template 1: Execution Mode → Deployment Runbook

```markdown
---
source: {observation_file}
mode: execution
date_observed: {date}
date_generated: {current_date}
environment: {environment}
tags: {tags}
---

# Deployment Runbook: {Context}

**Generated from observation**: `{observation_file}`

**Original execution**: {date} in {environment}

---

## Prerequisites

### Environment Requirements
- **Environment**: {environment} (dev/staging/prod)
- **Tools required**: {extracted from observation}
  - {tool 1} (version X.X)
  - {tool 2}
  - {tool 3}

### Permissions Required
- {permission 1}
- {permission 2}
- {AWS IAM policies needed}

### Pre-Deployment Checklist
- [ ] Environment variables configured (Doppler)
- [ ] AWS credentials valid
- [ ] {Other prerequisites from observation}

---

## Deployment Steps

### Step 1: {First major action from observation}

**Purpose**: {Why this step is needed}

**Command**:
```bash
{exact command from observation}
```

**Expected output**:
```
{output from observation}
```

**Verification**:
```bash
{how to verify success}
```

**Duration**: ~{X} seconds

---

### Step 2: {Second major action}

**Purpose**: {Why this step is needed}

**Command**:
```bash
{exact command from observation}
```

**Expected output**:
```
{output from observation}
```

**Verification**:
```bash
{how to verify success}
```

**Duration**: ~{X} seconds

---

{Repeat for all major steps}

---

## Verification

**Post-deployment checks**:
```bash
# Check 1: {Description}
{verification command}

# Check 2: {Description}
{verification command}

# Check 3: {Description}
{verification command}
```

**Expected results**:
- {Result 1}: ✅
- {Result 2}: ✅
- {Result 3}: ✅

---

## Timing

**Total duration**: ~{X} minutes

**Breakdown**:
- Step 1: {X}s
- Step 2: {X}s
- Step 3: {X}s
- Verification: {X}s

---

## Rollback Procedure

**If deployment fails**:

### Step 1: {Rollback action 1}
```bash
{rollback command}
```

### Step 2: {Rollback action 2}
```bash
{rollback command}
```

### Step 3: Verify rollback
```bash
{verification command}
```

---

## Resources Modified

**Files changed**:
- {file 1}
- {file 2}

**AWS resources updated**:
- {resource 1}: {ARN}
- {resource 2}: {ARN}

**Environment variables**:
- {var 1}: {description}
- {var 2}: {description}

---

## Troubleshooting

**Common issues**:

### Issue 1: {Common error from experience}
**Symptoms**: {Error message}
**Solution**: {How to fix}

### Issue 2: {Another common issue}
**Symptoms**: {Error message}
**Solution**: {How to fix}

---

## See Also

- Original observation: `{observation_file}`
- Related deployment docs: `docs/deployment/`
- Environment setup: `docs/AWS_SETUP.md`
```

---

### Template 2: Failure Mode → Bug Reproduction Guide

```markdown
---
source: {observation_file}
mode: failure
date_observed: {date}
date_generated: {current_date}
environment: {environment}
severity: {severity from observation}
tags: {tags}
---

# Bug Reproduction: {Context}

**Generated from observation**: `{observation_file}`

**Original failure**: {date} in {environment}

---

## Prerequisites

### Environment Setup
- **Environment**: {environment}
- **Branch**: {branch from observation}
- **Commit**: {commit hash from observation}

### Required State
- {Prerequisite 1 from input state}
- {Prerequisite 2 from input state}
- {Database state if applicable}

### Test Data
```{language}
{input data from observation}
```

---

## Reproduction Steps

### Step 1: Setup Environment

```bash
# Checkout correct branch/commit
git checkout {branch}
git pull origin {branch}

# Install dependencies
{installation commands if needed}

# Set environment variables
{environment setup from observation}
```

---

### Step 2: Prepare Input Data

```bash
# {Description of data preparation}
{commands to prepare data}
```

---

### Step 3: Trigger Failure

**Exact command that triggers failure**:
```bash
{command from observation}
```

**Alternative trigger** (if multiple ways):
```bash
{alternative method}
```

---

## Expected Behavior vs Actual

### Expected (What Should Happen)
{expected outcome from input state}

### Actual (What Actually Happens)
{actual outcome from symptoms}

---

## Error Details

### Error Message
```
{exact error message from observation}
```

### Stack Trace (if available)
```
{stack trace from observation}
```

### Error Location
- **File**: {file path}
- **Line**: {line number}
- **Function**: {function name}

---

## Reproduction Rate

**Success rate**: {X} out of {Y} attempts (from observation or estimate)

**Timing**: Error occurs after ~{X} seconds

---

## Environment Details

### System Information
- **OS**: {OS from environment context}
- **Python version**: {version}
- **Key dependencies**: {versions}

### AWS Resources
- **Lambda function**: {function name}
- **Timeout**: {timeout setting}
- **Memory**: {memory setting}

### External Dependencies
- **API**: {API name} (latency: {X}s from observation)
- **Database**: {database info}

---

## Debugging Commands

**To investigate further**:

```bash
# Check logs
{log查看命令 from observation}

# Verify state
{state verification commands}

# Test hypothesis
{debugging commands}
```

---

## Verification After Fix

**To verify fix resolves issue**:

1. Apply fix
2. Run reproduction steps above
3. Verify:
   - [ ] Error no longer occurs
   - [ ] Expected behavior achieved
   - [ ] No new errors introduced

**Success criteria**:
```bash
# Test command
{test command}

# Expected output
{expected output indicating fix works}
```

---

## Related Issues

**Similar failures** (from observations):
- {related observation 1}
- {related observation 2}

**Root cause hypothesis** (if investigated):
{hypothesis from journal if exists}

---

## See Also

- Original observation: `{observation_file}`
- Error journal: {journal path if exists}
- Related skill: `.claude/skills/error-investigation/`
```

---

### Template 3: Behavior Mode → Workflow Example

```markdown
---
source: {observation_file}
mode: behavior
date_observed: {date}
date_generated: {current_date}
context: {context}
tags: {tags}
---

# Workflow Example: {Context}

**Generated from observation**: `{observation_file}`

**Observed behavior**: {date}

---

## When to Use This Approach

**Situation**: {context from observation}

**Use this workflow when**:
- {Condition 1 from decision points}
- {Condition 2 from decision points}
- {Condition 3 from decision points}

**Don't use when**:
- {Opposite condition 1}
- {Opposite condition 2}

---

## Decision Process

### Initial Situation
{situation from decision points}

### Options Considered
1. **Option A**: {option 1 from decision points}
   - Pros: {pros}
   - Cons: {cons}

2. **Option B**: {option 2 from decision points}
   - Pros: {pros}
   - Cons: {cons}

### Choice Made
**Selected**: {choice from decision points}

**Reasoning**: {reasoning from decision points}

---

## Workflow Steps

### Step 1: {First tool/command from tool usage}

**Purpose**: {Why this step}

**Tool used**: {tool name}

**Command**:
```bash
{exact command from observation}
```

**Output**: {what was learned}

---

### Step 2: {Second tool/command}

**Purpose**: {Why this step}

**Tool used**: {tool name}

**Command**:
```bash
{exact command from observation}
```

**Output**: {what was learned}

---

{Repeat for all steps in workflow}

---

## Principle Adherence

**Principles followed**:
- {Principle 1 from observation}: {how followed}
- {Principle 2 from observation}: {how followed}

**Deviations** (if any):
- {Deviation 1}: {justification from observation}

---

## Outcome

### Results Achieved
{outcome from observation}

### Comparison to Baseline
**Previous approach**: {baseline from observation}
**This approach**: {current approach}

**Improvement**:
- {Metric 1}: {improvement}
- {Metric 2}: {improvement}

---

## Pattern Extracted

**When you encounter**: {situation pattern}

**Do this**:
1. {Step 1 pattern}
2. {Step 2 pattern}
3. {Step 3 pattern}

**Why it works**: {reasoning}

---

## Related Patterns

**Similar workflows**:
- {related observation 1}
- {related observation 2}

**Alternative approaches**:
- {alternative 1}: When to use
- {alternative 2}: When to use

---

## See Also

- Original observation: `{observation_file}`
- Related principles: `.claude/CLAUDE.md`
- Related workflow: {journal path if exists}
```

---

## Examples

### Example 1: From Failure Observation

```bash
/reproduce ".claude/observations/2025-12-23/failure-143205-lambda-timeout.md"
```

**Creates**: `.claude/reproductions/2025-12-28-lambda-timeout.md`

**Output**: Bug reproduction guide with:
- Prerequisites: Lambda function ARN, test ticker, environment
- Steps to trigger: Exact API call with payload
- Expected error: "Task timed out after 30.00 seconds"
- Debugging commands: Check CloudWatch logs, verify API latency
- Verification: After fix, timeout should not occur

---

### Example 2: From Execution Trace

```bash
/reproduce ".claude/observations/2025-12-23/execution-143052-deployed-lambda.md"
```

**Creates**: `.claude/reproductions/2025-12-28-deployed-lambda.md`

**Output**: Deployment runbook with:
- Prerequisites: AWS credentials, Docker, Doppler
- Step 1: Build Lambda package (`dr build`)
- Step 2: Deploy to AWS (`dr deploy lambda-deploy`)
- Step 3: Sync environment variables (`dr deploy sync-env`)
- Verification: Check Lambda console, test invocation
- Rollback: Revert to previous version

---

### Example 3: From Behavior Pattern

```bash
/reproduce ".claude/observations/2025-12-23/behavior-143420-research-first.md"
```

**Creates**: `.claude/reproductions/2025-12-28-research-first.md`

**Output**: Workflow example with:
- When to use: Infrastructure bugs, complex systems
- Decision: Research first vs iterate first
- Workflow: `/observe` → `/bug-hunt` → `/validate` → `/journal`
- Outcome: 100% fix rate when researching first for infrastructure
- Pattern: ALWAYS research first for infrastructure bugs

---

## Error Handling

### File Not Found

```bash
/reproduce ".claude/observations/2025-12-23/nonexistent.md"
```

**Response**:
```
❌ Observation file not found: .claude/observations/2025-12-23/nonexistent.md

Expected format: .claude/observations/{date}/{mode}-{time}-{slug}.md

List recent observations:
  find .claude/observations/ -name '*.md' -mtime -7

Recent observations:
  .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
  .claude/observations/2025-12-23/execution-143052-deployed-lambda.md
```

---

### Invalid Mode

**If observation has invalid mode**:
```
❌ Invalid observation mode: unknown

Expected: execution, failure, or behavior

Please check observation frontmatter:
  head -20 {observation_file}
```

---

### Missing Required Sections

**If observation is incomplete**:
```
⚠️  Warning: Observation missing some sections

Missing sections:
  - Commands Executed
  - Error Messages

Reproduction guide will be partial. Consider:
  - Re-observing with complete data
  - Manually filling in missing information
```

**Continues with partial reproduction guide**

---

## Directory Structure

```
.claude/
├── observations/          # Source observations
│   └── {date}/
│       ├── execution-*.md
│       ├── failure-*.md
│       └── behavior-*.md
├── reproductions/         # Generated reproduction guides
│   ├── {date}-{slug}.md
│   └── ...
└── journals/              # Interpretations (created after fixing)
    └── error/
        └── {date}-{solution}.md
```

**Workflow**:
1. **Capture**: `/observe` → `.claude/observations/`
2. **Reproduce**: `/reproduce` → `.claude/reproductions/`
3. **Fix**: Apply solution
4. **Document**: `/journal error` → `.claude/journals/error/`

---

## Integration with Other Commands

### Observe → Reproduce → Fix → Journal

```
/observe failure "Lambda timeout"
    ↓ (captures what happened)
/reproduce .claude/observations/2025-12-23/failure-*.md
    ↓ (creates reproduction guide)
{Fix the bug using reproduction guide}
    ↓
/journal error "Lambda timeout solution"
    ↓ (documents how it was fixed)
```

### Reproduce → Validate → Evolve

```
/reproduce .claude/observations/2025-12-23/execution-*.md
    ↓ (creates runbook)
/validate "Runbook steps work correctly"
    ↓ (tests reproduction guide)
/evolve docs
    ↓ (checks if runbook should become official docs)
```

---

## Principles

### 1. Reproduction Before Fix

Can't fix what you can't reproduce. Always create reproduction guide first.

### 2. Exact Commands

Use exact commands from observation, not paraphrased versions.

### 3. Complete Context

Include all prerequisites, environment details, and dependencies.

### 4. Verifiable Steps

Every step should have verification to confirm success.

### 5. Actionable Output

Reproduction guide should be copy-pasteable and executable.

---

## Related Commands

- `/observe` - Create observations to reproduce later
- `/journal` - Document solutions after reproducing and fixing
- `/abstract` - Extract patterns from multiple reproduction guides
- `/validate` - Verify reproduction guide works correctly

---

## See Also

- `.claude/observations/README.md` - Observation file structure
- `.claude/commands/observe.md` - How to create observations
- `.claude/commands/journal.md` - Documenting solutions
- `.claude/skills/error-investigation/` - Error investigation methodology
