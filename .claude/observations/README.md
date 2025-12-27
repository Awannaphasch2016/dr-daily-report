# Observations

**Purpose**: Capture **what happened** without interpretation, enabling future analysis and safe disagreement

**Core Principle**: Observations are **immutable facts** that can be analyzed, decomposed, abstracted, and journaled—but never edited retroactively.

---

## Why Observations?

**Problem**: Interpretations made in the moment can be wrong. If we only capture conclusions ("Lambda timed out because of memory"), we lose the ability to re-analyze later when we have more context.

**Solution**: Separate **observation** (facts) from **interpretation** (analysis). Capture raw data first, analyze later.

**Benefit**: Future selves, teammates, or AI agents can disagree with interpretations while still trusting the underlying data.

---

## Observation Modes

### `execution` - Execution Trace Capture

**What**: Tool calls, resources accessed, timing, costs, side effects
**When**: After significant command sequences, deployments, experiments
**Output**: Timestamped action log
**Example**: `.claude/observations/2025-12-23/execution-143052-deployed-lambda.md`

**Use cases**:
- Deployment sequences (for runbook creation)
- Debugging sessions (to understand what was tried)
- Experimentation (to track approach evolution)
- Cost analysis (which operations are expensive)

---

### `failure` - Failure Surface Mapping

**What**: Error messages, stack traces, input state, environment context
**When**: Immediately after errors, before attempting fixes
**Output**: Raw failure data without diagnosis
**Example**: `.claude/observations/2025-12-23/failure-143205-lambda-timeout.md`

**Use cases**:
- Production incidents (preserve evidence)
- Debugging (capture state before changing things)
- Root cause analysis (raw data for investigation)
- Pattern detection (recurring failure modes)

---

### `behavior` - Behavioral Drift Detection

**What**: Decision points, tool usage patterns, principle adherence
**When**: Weekly reflection, before/after pattern changes
**Output**: Decision log for pattern analysis
**Example**: `.claude/observations/2025-12-23/behavior-143420-iteration-over-research.md`

**Use cases**:
- Skill evolution tracking (how approaches change over time)
- Principle drift detection (divergence from CLAUDE.md)
- Learning analysis (what patterns are emerging)
- Team onboarding (how experienced devs make decisions)

---

## Observation Workflow

```
Event happens → /observe {mode} "{context}"
    ↓
Raw observation created (immutable)
    ↓
Analysis phase:
  - /decompose (break down failures/goals)
  - /abstract (extract patterns)
  - /journal (document solutions/decisions)
    ↓
Knowledge evolution:
  - /evolve (detect drift, update principles)
```

---

## File Organization

### Directory Structure

```
.claude/observations/
├── README.md                    # This file
├── 2025-12-23/                  # Daily directories
│   ├── execution-143052-deployed-lambda.md
│   ├── failure-143205-lambda-timeout.md
│   └── behavior-143420-iteration-over-research.md
├── 2025-12-24/
│   └── ...
└── archive/                     # Old observations (>90 days)
    └── 2025-Q1/
        ├── 2025-01-15/
        └── ...
```

### Filename Convention

```
{mode}-{HHMMSS}-{slug}.md
```

**Components**:
- `mode`: execution | failure | behavior
- `HHMMSS`: Timestamp (enables multiple per day, chronological ordering)
- `slug`: Lowercase, hyphenated, descriptive (3-8 words)

**Examples**:
- `execution-143052-deployed-lambda-to-staging.md`
- `failure-143205-lambda-timeout-during-report-gen.md`
- `behavior-143420-chose-iteration-over-research.md`

**Why timestamp**: Multiple observations per day are common. Time ordering matters for analysis.

---

## Observation Principles

### 1. Immutability

Once created, **never edit** observations. If new information emerges:
- Create a new observation
- Reference the original observation
- Document the update in a journal entry

**Why**: Maintains chronological integrity, prevents rewriting history, enables trust in data

### 2. No Interpretation

Observations capture **facts**, not **conclusions**.

**Good observation**:
```
Error: "Runtime.ImportModuleError: No module named 'src.scheduler.ticker_fetcher_handler'"
Input: Lambda invocation with event {...}
Environment: Lambda function v27, Python 3.11, requirements.txt includes module
```

**Bad observation**:
```
Lambda failed because the module wasn't installed properly.
We need to rebuild the container.
```

The bad example mixes observation with interpretation. Save conclusions for `/decompose` or `/journal`.

### 3. Capture Raw Data

Include exact text:
- Error messages (don't paraphrase)
- Stack traces (full, not summarized)
- Logs (actual excerpts, not descriptions)
- Commands (exact syntax used)

**Why**: Paraphrasing loses information. Future analysis benefits from unfiltered data.

### 4. Link Observations

Create traceable investigation history:
- Reference related observations by filename
- Link to commits/branches if relevant
- Connect to journal entries when patterns emerge
- Reference skills/principles being tested

**Example**:
```markdown
**Related Observations**:
- `.claude/observations/2025-12-22/failure-091234-lambda-cold-start.md`
- `.claude/observations/2025-12-22/execution-142050-deployed-container-update.md`

**Related Journal**:
- `.claude/journals/error/2025-12-23-lambda-import-module-error.md`
```

### 5. Complete Context

Observations should be understandable in isolation. Include:
- **What** was being attempted
- **When** it happened (timestamp)
- **Where** it happened (environment, AWS region, branch)
- **How** it was triggered (command, API call, user action)

Don't assume future readers have context from conversation.

---

## Using `/observe` Command

### Basic Usage

```bash
/observe execution "Deployed Telegram API to staging"
/observe failure "Lambda timeout during report generation"
/observe behavior "Chose iteration over research approach"
```

### With Additional Details

```bash
/observe failure "API 500 error" "User: user123, Ticker: NVDA19, Timestamp: 2025-12-23T14:32:05Z"
```

### Workflow Integration

**Deployment sequence**:
```bash
# Before deployment
/observe execution "Starting staging deployment"

# If deployment fails
/observe failure "Terraform apply failed at ECR push"

# After deployment
/observe execution "Completed staging deployment"
```

**Debugging workflow**:
```bash
# Capture failure first
/observe failure "Lambda ImportModuleError"

# Analyze
/decompose failure .claude/observations/2025-12-23/failure-143205-...md

# Once solved
/journal error "Lambda module import error" "Missing __init__.py in new directory"
```

**Pattern tracking**:
```bash
# Over time, capture decisions
/observe behavior "Used research-first approach for database schema bug"
/observe behavior "Iterated quickly on UI styling bug"
/observe behavior "Used research-first approach for AWS permission error"

# Extract pattern
/abstract .claude/observations/2025-12-*/behavior-*.md

# Result: "Research-first for infrastructure, iterate for UI"
```

---

## Maintenance

### Weekly Review (Every Friday)

1. **Count observations by mode**:
```bash
grep -l "mode: execution" .claude/observations/2025-12-{16..23}/*.md | wc -l
grep -l "mode: failure" .claude/observations/2025-12-{16..23}/*.md | wc -l
grep -l "mode: behavior" .claude/observations/2025-12-{16..23}/*.md | wc -l
```

2. **Review failure observations** - Are any unresolved?
3. **Check for patterns** - Do multiple observations suggest a deeper issue?
4. **Extract learnings** - Use `/abstract` on related observations

### Monthly Evolution (Last Friday)

1. **Run pattern extraction**:
```bash
/abstract .claude/observations/{current-month}-*/*.md
```

2. **Check behavior drift**:
```bash
/evolve behavior
```

3. **Archive old observations**:
```bash
mkdir -p .claude/observations/archive/2025-Q1
mv .claude/observations/2025-01-* .claude/observations/archive/2025-Q1/
```

4. **Review unresolved failures** - Create issues or journal entries

### Quarterly Audit (Every 3 Months)

1. **Analyze observation trends**:
   - Failure observation frequency (increasing → systemic issue)
   - Behavior drift patterns (deviation from principles)
   - Execution trace commonalities (opportunities for automation)

2. **Graduate patterns to skills**:
   - Recurring failure modes → error-investigation skill
   - Common execution sequences → automation scripts
   - Behavioral patterns → CLAUDE.md principles

3. **Clean up archives**:
   - Compress very old observations (>1 year)
   - Ensure patterns extracted before deletion

---

## Observation vs Journal vs ADR

| Aspect | Observation | Journal | ADR |
|--------|-------------|---------|-----|
| **Purpose** | Capture facts | Interpret experience | Document decisions |
| **Timing** | Immediately | After understanding | After commitment |
| **Content** | Raw data | Analysis + solution | Context + rationale |
| **Mutability** | Immutable | Editable until graduation | Immutable once merged |
| **Interpretation** | None | Moderate | High |
| **Speed** | 1-2 min | 2-5 min | 30-60 min |

**Workflow**:
```
Observation (facts)
    ↓ analyze
Journal (interpretation)
    ↓ if significant
ADR (formal decision)
```

---

## Example: Full Investigation Workflow

### 1. Capture Failure (Observation)

```bash
/observe failure "Lambda timeout in production"
```

**Created**: `.claude/observations/2025-12-23/failure-143205-lambda-timeout.md`

**Contains**:
- Error: "Task timed out after 30.00 seconds"
- Input: `{"user_id": "user123", "ticker": "NVDA19"}`
- Environment: Production, Lambda v42, Python 3.11
- Logs: [raw CloudWatch logs]

### 2. Analyze Failure (Decompose)

```bash
/decompose failure .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
```

**Output**: Breakdown of:
- Preconditions (what was assumed)
- Components involved (Lambda, Aurora, yfinance API)
- Failure modes (timeout at yfinance call)
- Hypotheses (API slowdown, network issue, cold start)

### 3. Document Solution (Journal)

```bash
/journal error "Lambda timeout caused by yfinance API slowdown"
```

**Created**: `.claude/journals/error/2025-12-23-lambda-timeout-yfinance.md`

**Contains**:
- Root cause: yfinance API latency spike
- Solution: Added timeout and fallback to cached data
- Prevention: Monitoring alert on p95 latency > 5s

### 4. Extract Pattern (Abstract)

After 3 similar timeouts:

```bash
/abstract .claude/observations/2025-12-*/failure-*timeout*.md
```

**Output**: Pattern detected - external API timeouts

**Action**: Update `code-review` skill with "Add timeouts to all external API calls" pattern

### 5. Update Principles (Evolve)

```bash
/evolve
```

**Detects**: Gap in CLAUDE.md - no principle about external API resilience

**Proposes**: Add "External API Resilience Principle" to CLAUDE.md

---

## Tips

### Do

- **Observe immediately** - Details fade fast
- **Include raw data** - Error messages, stack traces, exact commands
- **Timestamp everything** - Multiple observations per day are common
- **Link related items** - Observations, commits, journal entries
- **Use failure mode liberally** - No cost to capturing data

### Don't

- **Edit observations** - Create new ones instead
- **Interpret too early** - Save analysis for /decompose
- **Skip context** - Future you won't remember
- **Paraphrase errors** - Exact text matters
- **Mix observation with solution** - Separate concerns

---

## Related Commands

- `/observe` - Create observations
- `/decompose` - Analyze observations (break down failures/goals)
- `/abstract` - Extract patterns from multiple observations
- `/journal` - Document interpreted solutions/decisions
- `/evolve` - Detect drift using behavior observations

---

## Questions?

- **When to observe vs journal?** → Observe = facts, Journal = interpretation
- **Can I edit observations?** → No - create new ones, link to previous
- **What if I forget context?** → That's why you capture immediately
- **How long to keep observations?** → Archive after 90 days, compress after 1 year
- **What if observation reveals wrong interpretation?** → Good! That's the point - immutable data enables re-analysis

---

## See Also

- `.claude/commands/observe.md` - Observation command documentation
- `.claude/commands/decompose.md` - Analysis command
- `.claude/commands/abstract.md` - Pattern extraction
- `.claude/journals/README.md` - Journal system
- `.claude/commands/README.md` - Command system overview
