---
name: specify
description: Create lightweight design specification without entering full plan mode - quick design sketches and alternative explorations
accepts_args: true
arg_schema:
  - name: title
    required: true
    description: "What you're specifying (quoted if spaces)"
  - name: focus
    required: false
    description: "Optional focus: api, schema, workflow, alternative, spike"
composition:
  - skill: research
---

# Specify Command

**Purpose**: Create lightweight design specifications without full plan mode ceremony

**Core Principle**: "Sometimes you just need to think out loud" - quick design sketches for exploration, alternatives, and spikes

**When to use**:
- Exploring alternative approaches while working on primary approach
- Quick API/schema design before implementation
- Spike planning (proof-of-concept experiments)
- Design sketches that may not pan out
- "What would this look like?" without committing to implementation

---

## Quick Reference

```bash
# API design (first time - creates new spec)
/specify "REST API for backtester"

# Update existing spec with new requirements (diff mode)
# User: "Also add cancel endpoint and email notifications"
/specify "REST API for backtester"
# → Detects existing spec, shows diff of changes

# Schema design
/specify "DynamoDB schema for user preferences" schema

# Alternative exploration
/specify "SQS-based async processing" alternative

# Spike planning
/specify "Proof-of-concept: WebSocket real-time updates" spike

# Workflow design
/specify "Multi-stage report generation workflow" workflow
```

---

## Specify vs Plan Mode

| Aspect | `/specify` (Lightweight) | Plan Mode (Full) |
|--------|-------------------------|------------------|
| **Purpose** | Design sketch | Implementation plan |
| **Approval** | None required | User must approve |
| **Depth** | High-level | Detailed steps |
| **Output** | `.claude/specifications/` | `.claude/plans/` |
| **Commitment** | Exploratory | Ready to implement |
| **When** | Thinking out loud | Ready to code |

**Use both**:
```bash
/specify "Alternative caching strategy"    # Explore design
# → Like the design, ready to implement
EnterPlanMode                              # Create full plan
```

---

## Execution Flow

### Step 1: Parse Arguments and Detect Focus

```bash
TITLE="$1"
FOCUS="${2:-general}"

# Auto-detect focus if not provided
if [[ -z "$2" ]]; then
  if [[ "$TITLE" =~ (API|endpoint|route) ]]; then
    FOCUS="api"
  elif [[ "$TITLE" =~ (schema|table|database|DB) ]]; then
    FOCUS="schema"
  elif [[ "$TITLE" =~ (workflow|pipeline|process) ]]; then
    FOCUS="workflow"
  elif [[ "$TITLE" =~ (alternative|instead|other approach) ]]; then
    FOCUS="alternative"
  elif [[ "$TITLE" =~ (spike|POC|proof.of.concept|experiment) ]]; then
    FOCUS="spike"
  fi
fi
```

---

### Step 2: Check for Existing Specification (Diff Detection)

**Pattern**: Same title → update existing spec with diff

```bash
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

# Search for existing spec with same title (any date)
EXISTING_SPEC=$(find .claude/specifications/${FOCUS}/ -name "*-${SLUG}.md" 2>/dev/null | head -1)

if [[ -n "$EXISTING_SPEC" ]]; then
  MODE="update"
  OLD_SPEC="$EXISTING_SPEC"
  NEW_SPEC=".claude/specifications/${FOCUS}/${DATE}-${SLUG}.md"
else
  MODE="create"
  NEW_SPEC=".claude/specifications/${FOCUS}/${DATE}-${SLUG}.md"
fi
```

**Diff detection triggers when**:
- Specification with same title already exists
- New requirements added (inferred from conversation context)
- User re-runs `/specify` with same title

**Output**:
```markdown
⚠️ Found existing specification: .claude/specifications/api/2025-12-20-rest-api-for-backtester.md

Generating updated spec with changes highlighted...

📋 DIFF SUMMARY:
  - Added: 2 new endpoints
  - Modified: 1 endpoint (authentication requirements)
  - Removed: 1 deprecated endpoint
  - Changed: Error handling strategy

See full diff below ⬇️
```

---

### Step 3: Create or Update Specification Document

**File location**:
```bash
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
FILEPATH=".claude/specifications/${FOCUS}/${DATE}-${SLUG}.md"

mkdir -p ".claude/specifications/${FOCUS}"
```

**Directory structure**:
```
.claude/specifications/
├── api/           # API designs
├── schema/        # Database/data structure designs
├── workflow/      # Process/workflow designs
├── alternative/   # Alternative approaches
├── spike/         # Proof-of-concept experiments
└── general/       # Uncategorized specs
```

---

### Step 3: Use Focus-Specific Template

#### Template: API Design

```markdown
---
title: {title}
focus: api
date: {date}
status: draft
tags: []
---

# API Specification: {title}

## Goal

**What problem does this API solve?**

{Describe the use case, who uses it, why they need it}

## Endpoints

### Endpoint 1: {Method} {Path}

**Purpose**: {What this endpoint does}

**Request**:
```json
{
  "parameter1": "value",
  "parameter2": 123
}
```

**Response** (Success - 200):
```json
{
  "result": "data",
  "metadata": {}
}
```

**Response** (Error - 4xx/5xx):
```json
{
  "error": "error_code",
  "message": "Human-readable description"
}
```

**Validation**:
- `parameter1`: Required, string, max 100 chars
- `parameter2`: Optional, integer, range 0-1000

**Authentication**: {Required | Optional | None}

**Rate limit**: {X requests per Y seconds}

---

### Endpoint 2: {Method} {Path}

[... repeat structure ...]

---

## Data Models

### Model 1: {Name}

```typescript
interface ModelName {
  id: string;              // UUID
  field1: string;          // Description
  field2: number;          // Description
  created_at: timestamp;   // ISO 8601
}
```

---

## Authentication & Authorization

**Method**: {API key | JWT | OAuth | None}

**Permissions**:
- Role 1: Can {action1, action2}
- Role 2: Can {action3, action4}

---

## Error Handling

**Error codes**:
- `ERROR_CODE_1`: Description, when it occurs, how to fix
- `ERROR_CODE_2`: Description, when it occurs, how to fix

**Error format**:
```json
{
  "error": "CODE",
  "message": "Human-readable",
  "details": {},
  "request_id": "uuid"
}
```

---

## Implementation Notes

**Tech stack**:
- Framework: {FastAPI | Flask | etc}
- Validation: {Pydantic | etc}
- Database: {What it queries}

**Open questions**:
- [ ] {Question 1}
- [ ] {Question 2}

**Next steps**:
- [ ] Review API design
- [ ] If approved, create full implementation plan
- [ ] {Other steps}
```

---

#### Template: Schema Design

```markdown
---
title: {title}
focus: schema
date: {date}
status: draft
tags: []
---

# Schema Specification: {title}

## Goal

**What data does this schema store?**

{Describe the data, access patterns, scale requirements}

## Schema Design

### Table 1: {table_name}

**Purpose**: {What this table stores}

**Schema**:
```sql
CREATE TABLE {table_name} (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  field1 VARCHAR(100) NOT NULL,
  field2 TEXT,
  field3 INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_field1 (field1),
  INDEX idx_created_at (created_at)
);
```

**Constraints**:
- Primary key: `id`
- Unique: {field name(s)}
- Foreign keys: {field} → {references}
- Not null: {field1, field2}

**Indexes**:
- `idx_field1`: For {query pattern}
- `idx_created_at`: For {query pattern}

---

### Table 2: {table_name}

[... repeat structure ...]

---

## Access Patterns

### Pattern 1: {Description}

**Query**:
```sql
SELECT field1, field2
FROM table1
WHERE condition
ORDER BY field1
LIMIT 100;
```

**Frequency**: {High | Medium | Low}

**Index used**: {idx_name}

**Performance**: {Expected time}

---

### Pattern 2: {Description}

[... repeat structure ...]

---

## Data Types & Validation

**Type choices**:
- `field1`: VARCHAR(100) because {reason}
- `field2`: TEXT because {reason}
- `field3`: INT because {reason}

**Validation rules**:
- {Rule 1}
- {Rule 2}

---

## Migration Strategy

**From current state**:
{How to migrate existing data if applicable}

**Rollback plan**:
{How to undo if migration fails}

---

## Open Questions

- [ ] {Question 1 about schema}
- [ ] {Question 2 about access patterns}
- [ ] {Question 3 about scale}

---

## Next Steps

- [ ] Review schema design
- [ ] Test with sample queries
- [ ] If approved, create migration
- [ ] {Other steps}
```

---

#### Template: Workflow Design

```markdown
---
title: {title}
focus: workflow
date: {date}
status: draft
tags: []
---

# Workflow Specification: {title}

## Goal

**What does this workflow accomplish?**

{Describe the end-to-end process, inputs, outputs}

## Workflow Diagram

```
[Input] → [Node 1] → [Node 2] → [Decision] → [Node 3] → [Output]
                                     ↓
                                [Node 4] → [Error Handler]
```

---

## Nodes

### Node 1: {node_name}

**Purpose**: {What this node does}

**Input**:
```python
{
  "field1": "value",
  "field2": 123
}
```

**Processing**:
- Step 1: {What happens}
- Step 2: {What happens}

**Output**:
```python
{
  "field1": "transformed_value",
  "field3": "new_field"
}
```

**Duration**: {Expected time}

**Error conditions**:
- Error 1: {When it occurs, how handled}
- Error 2: {When it occurs, how handled}

---

### Node 2: {node_name}

[... repeat structure ...]

---

## State Management

**State structure**:
```python
class WorkflowState(TypedDict):
    field1: str
    field2: int
    field3: Optional[str]
    error: Optional[str]
```

**State transitions**:
- Initial → After Node 1: {What changes}
- After Node 1 → After Node 2: {What changes}

---

## Error Handling

**Error propagation**:
- Nodes set `state["error"]` on failure
- Workflow continues or halts based on error type

**Retry logic**:
- Transient errors: Retry {X} times
- Permanent errors: Halt immediately

---

## Performance

**Expected duration**:
- Best case: {X} seconds
- Average case: {Y} seconds
- Worst case: {Z} seconds

**Bottlenecks**:
- {Node name}: {Why it's slow}

**Optimization opportunities**:
- {Optimization 1}
- {Optimization 2}

---

## Open Questions

- [ ] {Question 1 about workflow}
- [ ] {Question 2 about error handling}

---

## Next Steps

- [ ] Review workflow design
- [ ] Test with sample data
- [ ] If approved, implement nodes
- [ ] {Other steps}
```

---

#### Template: Alternative Approach

```markdown
---
title: {title}
focus: alternative
date: {date}
status: draft
tags: []
---

# Alternative Specification: {title}

## Context

**Current approach**:
{How it works now}

**Why consider alternative**:
{What problem with current approach, what we hope to gain}

---

## Alternative Design

**High-level approach**:
{Describe the alternative at 10,000 feet}

**Key differences from current**:
- Difference 1: {Current vs Alternative}
- Difference 2: {Current vs Alternative}
- Difference 3: {Current vs Alternative}

---

## Pros vs Current Approach

**Advantages**:
- ✅ {Advantage 1}
- ✅ {Advantage 2}
- ✅ {Advantage 3}

**Quantified benefits** (if applicable):
- Performance: {X% faster/slower}
- Cost: {$X cheaper/more expensive}
- Complexity: {Simpler/More complex}

---

## Cons vs Current Approach

**Disadvantages**:
- ❌ {Disadvantage 1}
- ❌ {Disadvantage 2}
- ❌ {Disadvantage 3}

**Risks**:
- Risk 1: {Description, likelihood, mitigation}
- Risk 2: {Description, likelihood, mitigation}

---

## Migration Path

**From current to alternative**:
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Effort estimate**: {Time/complexity}

**Rollback strategy**: {How to revert if alternative fails}

---

## Decision Criteria

**Choose alternative if**:
- Criterion 1: {Condition that makes alternative better}
- Criterion 2: {Condition that makes alternative better}

**Stick with current if**:
- Criterion 1: {Condition that makes current better}
- Criterion 2: {Condition that makes current better}

---

## Recommendation

**Should we switch?**: {Yes | No | Need more info}

**Rationale**:
{Why based on analysis above}

**Next steps**:
- [ ] {Action 1}
- [ ] {Action 2}
```

---

#### Template: Spike (Proof-of-Concept)

```markdown
---
title: {title}
focus: spike
date: {date}
status: experiment
tags: []
---

# Spike Specification: {title}

## Hypothesis

**What are we trying to prove/disprove?**

{State the hypothesis clearly}

**Success criteria**:
- Criterion 1: {What must be demonstrated}
- Criterion 2: {What must be demonstrated}

**Time box**: {X hours/days max}

---

## Experiment Design

**What to build**:
{Minimal implementation needed to test hypothesis}

**What to skip**:
- {Thing 1 not needed for spike}
- {Thing 2 not needed for spike}

**Acceptance test**:
{How to know if spike succeeded}

---

## Implementation Approach

**Technology stack**:
- {Tech 1}: {Why chosen for spike}
- {Tech 2}: {Why chosen for spike}

**Key components**:
1. {Component 1}: {Purpose}
2. {Component 2}: {Purpose}
3. {Component 3}: {Purpose}

**Code location**:
- Create in: `experiments/{spike-name}/`
- Keep separate from main codebase

---

## Measurements

**Metrics to collect**:
- Metric 1: {What to measure, how}
- Metric 2: {What to measure, how}

**Expected results**:
- If hypothesis TRUE: {Expected metric values}
- If hypothesis FALSE: {Expected metric values}

---

## Learnings Capture

**If spike succeeds**:
- [ ] Document findings
- [ ] Journal: `/journal pattern "{what we learned}"`
- [ ] Consider graduation to production (create plan)

**If spike fails**:
- [ ] Document why it failed
- [ ] Journal: `/journal architecture "Why {approach} doesn't work"`
- [ ] Archive experiment code

**Either way**:
- [ ] Delete experiment code or move to `experiments/archive/`
- [ ] Update this spec with results

---

## Results (Fill in after spike)

**Hypothesis outcome**: {Confirmed | Disproven | Inconclusive}

**Metrics achieved**:
- Metric 1: {Actual value}
- Metric 2: {Actual value}

**Key learnings**:
- {Learning 1}
- {Learning 2}

**Recommendation**:
- {Proceed to production | Try different approach | Abandon}

**Next steps**:
- [ ] {Action 1}
- [ ] {Action 2}
```

---

## Examples

### Example 1: API Design

```bash
/specify "REST API for portfolio backtester"
```

**Creates**: `.claude/specifications/api/2025-12-24-rest-api-for-portfolio-backtester.md`

**Output**:
```
✅ Created specification: .claude/specifications/api/2025-12-24-rest-api-for-portfolio-backtester.md

Next steps:
  - Edit file to fill in API design
  - Review endpoints and data models
  - If ready to implement, use plan mode
```

---

### Example 2: Alternative Exploration

```bash
/specify "SQS-based async processing instead of Lambda sync" alternative
```

**Creates**: `.claude/specifications/alternative/2025-12-24-sqs-based-async-processing-instead-of-lambda-sync.md`

**Output**:
```
✅ Created specification: .claude/specifications/alternative/2025-12-24-sqs-based-async-processing-instead-of-lambda-sync.md

Focus: Alternative approach exploration

Template includes:
  - Comparison with current approach
  - Pros/cons analysis
  - Migration path
  - Decision criteria

Next steps:
  - Fill in alternative design
  - Compare with current Lambda sync approach
  - Use `/what-if` to explore implications
  - If promising, create full implementation plan
```

---

### Example 3: Spike Planning

```bash
/specify "Proof-of-concept: WebSocket real-time chart updates" spike
```

**Creates**: `.claude/specifications/spike/2025-12-24-proof-of-concept-websocket-real-time-chart-updates.md`

**Output**:
```
✅ Created specification: .claude/specifications/spike/2025-12-24-proof-of-concept-websocket-real-time-chart-updates.md

Focus: Proof-of-concept experiment

Template includes:
  - Hypothesis to test
  - Success criteria
  - Time box (recommended: 4-8 hours)
  - Experiment design
  - Results section (fill in after spike)

Next steps:
  - Define hypothesis clearly
  - Set time box (don't let spike drag on)
  - Build minimal POC
  - Document results
  - Decide: proceed to production or abandon
```

---

### Example 4: Iterative Refinement with Diff Detection

**Workflow**: Design → Get feedback → Refine → Show diff

**Initial specification**:
```bash
User: I need to design a REST API for portfolio backtesting
Assistant: /specify "REST API for backtester" api
```

**Creates**: `.claude/specifications/api/2025-12-20-rest-api-for-backtester.md`

**Output**:
```markdown
✅ Created specification: .claude/specifications/api/2025-12-20-rest-api-for-backtester.md

Template includes:
  - Endpoints: POST /backtest/run, GET /backtest/results
  - Data models
  - Authentication (basic)
  - Error handling

Next steps:
  - Review API design
  - Add missing endpoints if needed
```

---

**Adding new requirements** (same conversation or later):
```bash
User: The backtester API also needs to:
      - Support canceling running jobs
      - Send email notifications when done
      - Increase rate limit to 100 req/min

### Do
- **Start with goal** (what problem are you solving?)
- **Be concise** (high-level only, details come later)
- **Leave questions** (mark uncertainties as open questions)
- **Use focus templates** (api/schema/workflow/alternative/spike)
- **Iterate quickly** (spec is cheap, implementation is expensive)

### Don't
- **Over-detail** (that's what plan mode is for)
- **Commit prematurely** (spec is exploration, not commitment)
- **Skip open questions** (better to flag them now)
- **Forget to review** (read your spec before implementing)

---

## When to Graduate to Plan Mode

**Specify is done** when:
- ✅ High-level design is clear
- ✅ Open questions answered (or acceptable to proceed)
- ✅ Looks promising enough to commit
- ✅ Ready for detailed implementation planning

**Then**:
```bash
EnterPlanMode
# Reference your spec from .claude/specifications/
# Create detailed step-by-step implementation plan
```

---

## See Also

- `EnterPlanMode` - Full implementation planning (heavyweight)
- `.claude/commands/what-if.md` - Explore alternatives before specifying
- `.claude/commands/proof.md` - Prove properties of your design
- `.claude/commands/journal.md` - Document learnings from spikes

---

## Prompt Template

You are executing the `/specify` command with arguments: $ARGUMENTS

**Title**: $1
**Focus**: ${2:-auto-detect}

---

### Execution Steps

**Step 1: Parse Arguments and Detect Focus**

Extract title and focus type (api/schema/workflow/alternative/spike). If focus not provided, auto-detect from title keywords.

**Step 2: Check for Existing Specification**

Search for existing specification with same title:
```bash
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
EXISTING_SPEC=$(find .claude/specifications/${FOCUS}/ -name "*-${SLUG}.md" 2>/dev/null | head -1)
```

If existing specification found:
- Set MODE="update"
- Read old specification
- Extract current requirements from conversation context
- Identify what changed (added/modified/removed)
- Generate diff summary

If no existing specification:
- Set MODE="create"
- Use focus-specific template

**Step 3: Generate Specification**

**If MODE="create"**:
1. Use focus-specific template (api/schema/workflow/alternative/spike)
2. Fill in sections based on conversation context
3. Mark open questions with `[ ]`
4. Save to `.claude/specifications/${FOCUS}/${DATE}-${SLUG}.md`

**If MODE="update"**:
1. Read existing specification
2. Analyze conversation for new/changed requirements
3. Generate updated specification with:
   - **Diff summary at top** (what changed)
   - **Inline change markers**: `[ADDED]`, `[MODIFIED]`, `[REMOVED]`
   - Full updated specification (new version)
4. Save new version to `.claude/specifications/${FOCUS}/${DATE}-${SLUG}.md`
5. Keep old version (don't delete)
6. Show diff summary and both file paths

---

### Diff Mode Output Format

When updating existing specification, use this format:

```markdown
⚠️ **SPECIFICATION UPDATE**

**Old specification**: .claude/specifications/api/2025-12-20-rest-api-for-backtester.md
**New specification**: .claude/specifications/api/2025-12-24-rest-api-for-backtester.md

---

## 📋 DIFF SUMMARY

**Added**:
- Endpoint: POST /backtest/cancel (cancel running backtest)
- Field: `backtest_id` in response (for tracking)
- Authentication: API key required for all endpoints

**Modified**:
- Endpoint: POST /backtest/run (added optional `email_notify` parameter)
- Error handling: Now returns structured error codes instead of messages

**Removed**:
- Endpoint: GET /backtest/legacy (deprecated, use /backtest/run)

**Changed**:
- Rate limit: 10 req/min → 100 req/min (performance improvement)

---

## 🔍 DETAILED CHANGES

### [ADDED] Endpoint: POST /backtest/cancel

**Purpose**: Cancel a running backtest job

**Request**:
```json
{
  "backtest_id": "uuid-here"
}
```

**Response** (200):
```json
{
  "status": "cancelled",
  "backtest_id": "uuid-here"
}
```

---

### [MODIFIED] Endpoint: POST /backtest/run

**Changes**:
- Added optional parameter: `email_notify` (boolean)
- Response now includes `backtest_id` for tracking

**Old**:
```json
// Request
{
  "tickers": ["AAPL", "GOOGL"]
}

// Response
{
  "status": "running"
}
```

**New**:
```json
// Request
{
  "tickers": ["AAPL", "GOOGL"],
  "email_notify": true  // [ADDED]
}

// Response
{
  "status": "running",
  "backtest_id": "uuid-here"  // [ADDED]
}
```

---

### [REMOVED] Endpoint: GET /backtest/legacy

**Reason**: Deprecated in favor of POST /backtest/run

**Migration**: Use POST /backtest/run instead

---

## 📄 FULL UPDATED SPECIFICATION

[Include complete updated specification with all changes incorporated]

---

## 📌 NEXT STEPS

- [ ] Review diff to ensure all requirements captured
- [ ] Answer open questions (if any)
- [ ] If approved, ready for plan mode: `EnterPlanMode`
- [ ] Archive old specification if no longer needed
```

---

### Change Detection Logic

**How to identify changes**:

1. **Analyze conversation context** before `/specify` invocation:
   - Look for phrases like "also add...", "change X to Y", "remove Z"
   - New requirements mentioned in current session
   - Modifications to existing design

2. **Compare old vs new requirements**:
   - Old requirements: Extract from existing specification
   - New requirements: Extract from conversation
   - Compute diff: added, modified, removed

3. **Categorize changes**:
   - **Added**: Entirely new sections, endpoints, fields, features
   - **Modified**: Changed parameters, validation, behavior
   - **Removed**: Deleted sections, deprecated features
   - **Changed**: Different values (rate limits, timeouts, etc.)

4. **Mark inline changes**:
   - Use `[ADDED]` comment after new content
   - Use `[MODIFIED]` with old/new comparison
   - Use `[REMOVED]` for deleted content (show what was removed)

---

### Example Invocations

**First time** (create mode):
```
User: I need to design a REST API for portfolio backtesting
Assistant: /specify "REST API for backtester" api
→ Creates .claude/specifications/api/2025-12-20-rest-api-for-backtester.md
```

**Update with new requirements** (diff mode):
```
User: The backtester API also needs to support canceling running jobs and email notifications
Assistant: /specify "REST API for backtester" api
→ Detects existing spec from 2025-12-20
→ Analyzes new requirements: cancel endpoint, email notifications
→ Generates diff summary
→ Creates .claude/specifications/api/2025-12-24-rest-api-for-backtester.md
→ Shows what changed (added cancel endpoint, modified run endpoint)
```

**Further refinement** (diff mode):
```
User: Actually, increase rate limit to 100 req/min and remove the legacy endpoint
Assistant: /specify "REST API for backtester" api
→ Detects spec from 2025-12-24
→ Analyzes changes: rate limit change, endpoint removal
→ Generates diff summary
→ Creates .claude/specifications/api/2025-12-24-rest-api-for-backtester-v2.md
→ Shows rate limit changed, legacy endpoint removed
```

---

### Diff Detection Principles

**Core Principle**: "Specifications evolve as requirements clarify" - capture the delta explicitly

**Why diff mode matters**:
- ✅ **Visibility**: See exactly what changed between iterations
- ✅ **Traceability**: Understand why design evolved
- ✅ **Review efficiency**: Focus on changes, not entire spec
- ✅ **Decision tracking**: See what was added/removed/modified over time

**When to use**:
- Same design, new requirements added
- Design refinement based on feedback
- Iterative exploration (try different approaches)

**When NOT to use**:
- Completely different design (create new spec with different title)
- Unrelated feature (create separate spec)
