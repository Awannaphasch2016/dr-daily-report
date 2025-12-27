---
name: abstract
description: Extract general patterns, templates, and heuristics from concrete experiences (auto-detects pattern type from file paths)
accepts_args: true
arg_schema:
  - name: sources
    required: true
    description: "Glob pattern or file paths - pattern type auto-detected from paths"
  - name: pattern_type
    required: false
    description: "Override auto-detection: failure_mode, workflow, decision, architecture"
composition:
  - skill: research
---

# Abstract Command

**Purpose**: Extract general rules, templates, and heuristics from concrete experiences

**Core Principle**: "Intelligence generalizes" - the foundation of learning across domains. Patterns extracted from specific instances enable reuse and prediction.

**When to use**:
- After solving similar problems multiple times
- Detecting recurring failure modes
- Identifying decision patterns
- Creating reusable templates
- Building skill patterns

---

## Quick Reference

### Smart Pattern Detection (Recommended)
```bash
/abstract ".claude/observations/*/failure-*.md"        # Auto-detects: failure_mode
/abstract ".claude/observations/*/execution-*.md"      # Auto-detects: workflow
/abstract ".claude/observations/*/behavior-*.md"       # Auto-detects: decision
/abstract ".claude/journals/architecture/*.md"         # Auto-detects: architecture
```

### Explicit Pattern Type (Override)
```bash
/abstract ".claude/journals/error/*.md" failure_mode   # Force failure_mode
/abstract ".claude/decompositions/goal-*.md" workflow  # Force workflow
```

**How it works**:
- **File paths** analyzed for patterns: `/failure-` → failure_mode, `/execution-` → workflow
- **Multiple types** detected → Analyzes content to determine predominant type
- **Override** if auto-detection incorrect

---

## Pattern Types

### `failure_mode` - Recurring Failure Patterns

**What it extracts**:
- Common error signatures
- Shared root causes
- Consistent preconditions that fail
- Predictable cascade effects

**Output**: Failure pattern template for skill documentation

**Example**:
```
Pattern: External API Timeout
Signature: "Task timed out after X seconds" + API call
Precondition: Assumption that API responds within timeout
Detection: Timeout exception + recent API call in trace
Prevention: Add timeout + fallback + circuit breaker
```

---

### `workflow` - Execution Patterns

**What it extracts**:
- Common tool sequences
- Successful workflows
- Step dependencies
- Reusable procedures

**Output**: Workflow template for automation or documentation

**Example**:
```
Pattern: Staged Deployment Workflow
Steps:
1. Build artifact (Docker image)
2. Push to registry (ECR)
3. Update function code (Lambda)
4. Wait for update
5. Run smoke tests
6. Promote alias (if tests pass)
```

---

### `decision` - Decision Patterns

**What it extracts**:
- Recurring decision points
- Selection criteria
- Trade-off patterns
- Heuristics for choosing

**Output**: Decision tree or heuristic for future choices

**Example**:
```
Pattern: Research vs Iterate Decision
Decision Point: Bug persists after N attempts
Heuristic:
  - N = 1: Iterate (quick fix likely)
  - N = 2: Research (root cause unclear)
  - Infrastructure bugs: Always research first
  - UI bugs: Iterate first (fast feedback)
```

---

### `architecture` - Architectural Patterns

**What it extracts**:
- Design solutions to recurring problems
- Trade-offs made consistently
- System boundary patterns
- Integration strategies

**Output**: Architecture pattern for ADR or CLAUDE.md

**Example**:
```
Pattern: Aurora-First Data Architecture
Problem: Inconsistent data from multiple sources
Solution: Single source of truth (Aurora) + pre-population
Trade-offs:
  - Pro: Consistent performance, no API rate limits
  - Con: Data can be stale (up to 24h)
  - When to use: User-facing APIs with predictable data needs
```

---

## Smart Pattern Detection

### How Claude Detects Pattern Type

**Analyzes file paths in your glob pattern**:

#### `failure_mode` detected when paths contain:
- `/failure-` in filename (observations)
- `/error/` in directory (journals)
- Keywords: timeout, crash, exception, bug
- **Example**: `.claude/observations/*/failure-*.md` → failure_mode ✅

#### `workflow` detected when paths contain:
- `/execution-` in filename (observations)
- `/goal-` in filename (decompositions)
- Keywords: deploy, build, pipeline, workflow
- **Example**: `.claude/observations/*/execution-*.md` → workflow ✅

#### `decision` detected when paths contain:
- `/behavior-` in filename (observations)
- `/meta/` in directory (journals)
- Keywords: chose, decided, pattern, heuristic
- **Example**: `.claude/observations/*/behavior-*.md` → decision ✅

#### `architecture` detected when paths contain:
- `/architecture/` in directory (journals)
- Keywords: design, pattern, structure, system
- **Example**: `.claude/journals/architecture/*.md` → architecture ✅

### Mixed Types

If paths contain multiple types:
```
📊 Multiple pattern types detected:
  - failure observations: 5 files
  - execution observations: 3 files

Analyzing content to determine predominant pattern...

Detected: failure_mode (62% of content about failures)

Continue with failure_mode pattern extraction? (y/n)
Or specify explicit type: /abstract <files> workflow
```

**Override detection**: Provide explicit pattern type
```bash
/abstract ".claude/observations/*/*.md" workflow  # Force workflow (ignores failures)
```

---

## Execution Flow

### Step 1: Parse Sources and Detect Pattern Type

**If only sources provided** (smart detection):
```bash
/abstract ".claude/observations/*/failure-*.md"
```

1. Expand glob pattern to file list
2. Analyze paths: All contain `/failure-` → `failure_mode`
3. Confirm: "Detected failure_mode pattern - correct? (y/n)"
4. Proceed with failure_mode extraction

**If pattern type provided** (explicit):
```bash
/abstract ".claude/journals/error/*.md" failure_mode
```

1. Expand glob pattern
2. Skip detection, use explicit type
3. Proceed with failure_mode extraction

**Glob pattern** (single argument):
```bash
/abstract ".claude/observations/2025-12-*/failure-*.md"
```

**Multiple files** (space-separated):
```bash
/abstract file1.md file2.md file3.md
```

**Mixed**:
```bash
/abstract ".claude/journals/error/*.md" .claude/observations/2025-12-23/failure-*.md
```

Expand glob patterns to file list, then proceed.

### Step 2: Validate Sources

Check that:
- At least 2 files exist (can't abstract from single instance)
- Files are readable
- Files have relevant content (observations, journals, decompositions)

If < 2 files:
```
⚠️  Pattern extraction requires multiple instances (found {count})

You need at least 2 similar cases to extract a pattern.
Create more observations/journals/decompositions first.
```

### Step 3: Load and Categorize Content

**For each file**:
- Load markdown content
- Extract frontmatter (mode, category, date, etc.)
- Extract body content (symptoms, solutions, decisions)
- Categorize by type (observation, journal, decomposition)

**Group by similarity**:
- Failure observations → failure_mode patterns
- Architecture journals → architecture patterns
- Goal decompositions → workflow patterns
- Behavior observations → decision patterns

### Step 4: Invoke Research Skill

Use `research` skill methodology to:
- Analyze commonalities across instances
- Identify unique elements vs shared patterns
- Search codebase for existing similar patterns
- Check CLAUDE.md and skills for related principles

### Step 5: Extract Patterns

**For each pattern type**, generate template:

---

## Pattern Extraction Template (General)

### Pattern: {Generated Pattern Name}

**Abstracted From**:
- `.claude/observations/2025-12-23/failure-143205-lambda-timeout.md`
- `.claude/observations/2025-12-24/failure-091234-api-timeout.md`
- `.claude/journals/error/2025-12-25-timeout-resolution.md`

**Total Instances**: {count} (found {count} similar cases)

**Confidence**: High | Medium | Low
- High: 5+ instances, consistent pattern
- Medium: 3-4 instances, mostly consistent
- Low: 2 instances, possible pattern

---

### Pattern Description

**What it is**:
{High-level description of the pattern}

**When it occurs**:
{Conditions that trigger this pattern}

**Why it happens**:
{Root cause or underlying mechanism}

---

### Concrete Instances

#### Instance 1: {Specific case}
**From**: {file path}
**Context**: {Brief context from that case}
**Manifestation**: {How pattern appeared}

#### Instance 2: {Specific case}
[...]

---

### Generalized Pattern

**Signature** (how to recognize it):
- {Observable characteristic 1}
- {Observable characteristic 2}
- {Observable characteristic 3}

**Preconditions** (what enables it):
- {Condition 1 that must hold}
- {Condition 2 that must hold}

**Components** (what's involved):
- {Component/entity 1}
- {Component/entity 2}

**Mechanism** (how it works/fails):
```
{Step-by-step description or diagram}
```

---

### Pattern Template

**For {pattern_type}**:

#### Failure Mode Template
```
Pattern Name: {name}

Symptoms:
  - Error: {error signature}
  - Timing: {when it occurs}
  - Frequency: {how often}

Root Cause:
  - {What actually causes this}

Detection:
  - Check: {what to look for}
  - Logs: {what logs show}
  - Metrics: {what metrics indicate}

Prevention:
  - Pre-deployment: {what to check before deploying}
  - Runtime: {what safeguards to add}
  - Monitoring: {what alerts to create}

Resolution:
  1. {Step to resolve}
  2. {Step to resolve}
  3. {Step to resolve}
```

#### Workflow Template
```
Pattern Name: {name}

Purpose: {What this workflow achieves}

Preconditions:
  - {What must exist before starting}

Steps:
  1. {Step 1} - {Tool/method}
     Dependencies: {What step 1 needs}
     Verification: {How to verify step 1 succeeded}

  2. {Step 2} - {Tool/method}
     Dependencies: {Step 1 complete}
     Verification: {How to verify step 2 succeeded}

  [...]

Success Criteria:
  - {How to verify entire workflow succeeded}

Failure Handling:
  - If step N fails: {Recovery procedure}
```

#### Decision Template
```
Pattern Name: {name}

Decision Point: {When you face this choice}

Options:
  A. {Option 1}
  B. {Option 2}
  C. {Option 3}

Selection Heuristic:
  Choose A when:
    - {Condition for A}
    - {Condition for A}

  Choose B when:
    - {Condition for B}
    - {Condition for B}

  Choose C when:
    - {Condition for C}

Default: {If unclear, choose this}

Trade-offs:
  - Option A: {Pros and cons}
  - Option B: {Pros and cons}
  - Option C: {Pros and cons}
```

#### Architecture Template
```
Pattern Name: {name}

Problem: {What problem this solves}

Context: {When this problem occurs}

Solution: {How this pattern solves it}

Structure:
  - Components: {What parts are involved}
  - Relationships: {How they interact}
  - Data flow: {How data moves}

Implementation:
  - {Key implementation detail 1}
  - {Key implementation detail 2}

Trade-offs:
  Pros:
    - {Benefit 1}
    - {Benefit 2}

  Cons:
    - {Cost/limitation 1}
    - {Cost/limitation 2}

When to use:
  - {Scenario 1 where pattern fits}
  - {Scenario 2}

When NOT to use:
  - {Scenario where pattern is wrong}
  - {Scenario where simpler approach works}

Related patterns:
  - {Similar pattern}: {How they differ}
  - {Complementary pattern}: {How they combine}
```

---

### Variations

**Observed variations** across instances:
- Variation 1: {How pattern manifests differently}
- Variation 2: {Context-specific adaptation}

**When to deviate**:
- {Scenario where standard pattern doesn't apply}
- {Modification needed for special case}

---

### Graduation Path

**If pattern confidence is HIGH** (5+ instances):
- Graduate to skill documentation
- Add to CLAUDE.md as principle
- Create reusable template/script

**If pattern confidence is MEDIUM** (3-4 instances):
- Keep in working memory (this abstraction file)
- Watch for more instances
- Refine pattern as new cases emerge

**If pattern confidence is LOW** (2 instances):
- Note as potential pattern
- Actively look for more instances
- May be coincidence, not true pattern

---

### Action Items

- [ ] Test pattern against new case (validation)
- [ ] Add to skill: {which skill} (if high confidence)
- [ ] Update CLAUDE.md: {which section} (if architectural)
- [ ] Create automation: {what to automate} (if workflow)
- [ ] Share with team: {when/how} (if significant)

---

### Metadata

**Pattern Type**: {failure_mode | workflow | decision | architecture}
**Confidence**: {high | medium | low}
**Created**: {date}
**Instances**: {count}
**Last Updated**: {date}

---

## Step 6: Generate Output File

Create: `.claude/abstractions/{pattern_type}-{date}-{slug}.md`

**Example**:
- `.claude/abstractions/failure_mode-2025-12-23-external-api-timeout.md`
- `.claude/abstractions/workflow-2025-12-23-staged-deployment.md`
- `.claude/abstractions/decision-2025-12-24-research-vs-iterate.md`

Display summary:
```
✅ Pattern extracted

Type: {pattern_type}
Instances: {count} files analyzed
Confidence: {high/medium/low}
Pattern: {pattern name}

Output: .claude/abstractions/{file}

{Next steps based on confidence level}
```

---

## Examples

### Example 1: Extract Failure Pattern

```bash
/abstract ".claude/observations/2025-12-*/failure-*timeout*.md" failure_mode
```

**Input files**:
- `failure-143205-lambda-timeout.md` (Lambda → yfinance timeout)
- `failure-091234-api-timeout.md` (Lambda → Aurora timeout)
- `failure-153042-external-timeout.md` (Lambda → news API timeout)

**Output**:
```markdown
Pattern: External API Timeout Failures

Instances: 3
Confidence: High

Signature:
- Error: "Task timed out after 30.00 seconds"
- Component: Lambda calling external API
- Timing: Production during peak traffic
- Frequency: 3-5 times per week

Root Cause:
- External APIs have variable latency (no SLA)
- Lambda timeout (30s) < worst-case API latency
- No fallback when API slow

Detection:
- Error signature: timeout + recent API call in logs
- CloudWatch: Lambda duration metric near timeout
- Pattern: Happens during market hours (high volume)

Prevention:
- Add explicit timeout to API calls (5s)
- Implement fallback to cached data
- Add circuit breaker after 3 consecutive failures
- Monitoring: Alert on p95 API latency > 3s

Resolution:
1. Short-term: Increase Lambda timeout to 60s
2. Medium-term: Add timeout + fallback
3. Long-term: Pre-populate data, make API read-only

Graduation: Add to error-investigation skill as "External API Resilience" pattern
```

---

### Example 2: Extract Workflow Pattern

```bash
/abstract ".claude/observations/2025-12-*/execution-*deploy*.md" workflow
```

**Input files**:
- `execution-143052-deployed-lambda-staging.md`
- `execution-091540-deployed-lambda-production.md`
- `execution-164823-deployed-api-update.md`

**Output**:
```markdown
Pattern: Staged Lambda Deployment Workflow

Instances: 3
Confidence: Medium (consistent sequence, minor variations)

Purpose: Deploy Lambda with zero downtime and validation

Preconditions:
- Docker image built and tagged
- ECR repository exists
- Lambda function exists
- Smoke tests defined

Steps:
1. Login to ECR
   Tool: aws ecr get-login-password
   Verification: Login succeeds (exit code 0)

2. Push image to ECR
   Tool: docker push
   Verification: Image in ECR (aws ecr describe-images)

3. Update Lambda code
   Tool: aws lambda update-function-code
   Verification: UpdateFunctionCode returns 200

4. Wait for update
   Tool: aws lambda wait function-updated
   Verification: State = Active

5. Run smoke tests
   Tool: pytest -m smoke
   Verification: All tests pass

6. Promote alias (if tests pass)
   Tool: aws lambda update-alias
   Verification: Alias points to new version

Success Criteria:
- All steps exit code 0
- Smoke tests pass
- Alias updated

Failure Handling:
- If step 5 fails: Don't promote alias, rollback to previous version
- If step 3 fails: Retry once, then abort

Template file: Create .claude/templates/lambda-deploy.sh

Graduation: Add to deployment skill as "Lambda Deployment Procedure"
```

---

### Example 3: Extract Decision Pattern

```bash
/abstract ".claude/observations/2025-12-*/behavior-*.md" decision
```

**Input files**:
- `behavior-143420-chose-iteration-over-research.md` (UI bug)
- `behavior-091234-chose-research-over-iteration.md` (AWS permission bug)
- `behavior-102541-chose-research-first.md` (Database migration bug)

**Output**:
```markdown
Pattern: Research vs Iterate Decision Heuristic

Instances: 3
Confidence: Medium

Decision Point: Bug persists after first fix attempt

Options:
A. Iterate (try another fix quickly)
B. Research (stop and investigate root cause)

Selection Heuristic:

Choose ITERATE when:
- UI/frontend bugs (fast feedback cycle)
- First attempt (haven't tried anything yet)
- Error message is clear and specific
- Change is reversible
- Impact is low (dev/staging only)

Choose RESEARCH when:
- Infrastructure bugs (AWS, database, networking)
- Bug persists after 2 attempts
- Error message is vague or misleading
- Root cause unclear
- Production impact

Observed Pattern:
- Instance 1: UI bug → iterated → solved in 2 attempts
- Instance 2: AWS permissions → researched → solved in 1 attempt after 30min research
- Instance 3: Database migration → researched → solved in 1 attempt after 60min research

Principle: "Research Before Iteration Principle" from CLAUDE.md
Heuristic refinement: "Infrastructure bugs: always research first"

Graduation: Update CLAUDE.md to include infrastructure vs UI distinction
```

---

### Example 4: Cross-Category Abstraction

```bash
/abstract ".claude/observations/2025-12-23/*.md"
```

**Analyzes all observations from Dec 23**:
- 2 execution traces
- 3 failure observations
- 1 behavior observation

**Output**:
```markdown
Cross-Category Pattern Analysis

Date: 2025-12-23
Files analyzed: 6
Categories: execution (2), failure (3), behavior (1)

Patterns Detected:

1. Deployment Pattern (from execution traces)
   - Consistent sequence: build → push → update → test
   - Variation: Staging has smoke tests, production has full suite
   - Confidence: Medium (2 instances)

2. Timeout Pattern (from failure observations)
   - All 3 failures involved timeouts
   - 2 external API, 1 database
   - Common: No fallback strategy
   - Confidence: High (3 instances with same root cause)

3. Decision Pattern (from behavior observation)
   - Research-first approach worked for infrastructure bug
   - Aligns with CLAUDE.md principle
   - Confidence: Low (1 instance, but confirms documented principle)

Recommendations:
1. Extract deployment pattern → automation script
2. Extract timeout pattern → add to error-investigation skill
3. Behavior observation confirms existing principle (no action needed)

Next: Create 2 abstraction files (deployment workflow, timeout failure_mode)
```

---

## Error Handling

### Insufficient Sources

```bash
/abstract .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
```

**Response**:
```
⚠️  Pattern extraction requires multiple instances (found 1)

You need at least 2 similar cases to extract a pattern.

Suggestions:
- Wait for more similar cases to emerge
- Search for similar failures: grep -r "timeout" .claude/observations/
- Check journals: grep -r "timeout" .claude/journals/error/
```

### No Files Match Pattern

```bash
/abstract ".claude/observations/2025-12-99/*.md"
```

**Response**:
```
❌ No files found matching: .claude/observations/2025-12-99/*.md

Check:
- Glob pattern syntax
- Directory exists
- Files exist in directory

Try: ls .claude/observations/ to see available dates
```

### Mixed Incompatible Types

```bash
/abstract .claude/observations/*/failure-*.md .claude/journals/architecture/*.md
```

**Response**:
```
⚠️  Mixed incompatible types detected:
  - failure observations (from failures)
  - architecture journals (from design decisions)

These don't form a coherent pattern.

Suggestions:
- Extract failure patterns separately
- Extract architecture patterns separately
- Or specify pattern_type to focus analysis
```

---

## Directory Structure

```
.claude/
├── abstractions/         # NEW: Extracted patterns
│   ├── failure_mode-2025-12-23-api-timeout.md
│   ├── workflow-2025-12-23-staged-deployment.md
│   ├── decision-2025-12-24-research-vs-iterate.md
│   └── architecture-2025-12-25-aurora-first.md
```

---

## Integration with Other Commands

### Observe → Abstract → Journal

```
/observe failure "..." (3+ times)
    ↓
/abstract .claude/observations/*/failure-*.md failure_mode
    ↓ (pattern emerges)
/journal pattern "External API timeout handling"
    ↓ (if high confidence)
Update skill: error-investigation/EXTERNAL-API-PATTERNS.md
```

### Decompose → Abstract → Skill

```
/decompose goal "..." (multiple goals)
    ↓
/abstract .claude/decompositions/goal-*.md workflow
    ↓ (workflow pattern emerges)
Create template: .claude/templates/workflow-{name}.md
    ↓ (if very useful)
Graduate to skill documentation
```

### Behavior → Abstract → Principle

```
/observe behavior "..." (weekly)
    ↓
/abstract .claude/observations/*/behavior-*.md decision
    ↓ (decision heuristic emerges)
/journal meta "Decision heuristic for X"
    ↓
/evolve
    ↓ (if significant)
Update CLAUDE.md with new principle
```

---

## Principles

### 1. Need Multiple Instances

Can't abstract from single case - that's just documentation, not pattern extraction. Minimum 2, prefer 3+.

### 2. High Confidence = High Value

Don't rush to graduate patterns. Low confidence patterns may be coincidence. Wait for 5+ instances before formalizing.

### 3. Cross-Validate

After extracting pattern, test against new case to verify it actually generalizes.

### 4. Pattern Refinement

Patterns evolve. First extraction is hypothesis, refinements add nuance as edge cases emerge.

### 5. Link to Source

Always reference source files in abstraction. Enables re-analysis if pattern proves wrong.

---

## Related Commands

- `/observe` - Create concrete instances
- `/decompose` - Break down instances for analysis
- `/journal` - Document patterns after validation
- `/evolve` - Detect when patterns should become principles

---

## See Also

- `.claude/commands/observe.md` - Observation capture
- `.claude/commands/decompose.md` - Instance analysis
- `.claude/commands/journal.md` - Pattern documentation
- `.claude/skills/research/` - Research methodology
- `.claude/commands/README.md` - Command system overview
