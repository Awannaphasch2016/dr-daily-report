---
name: journal
description: Log architecture decisions, error solutions, patterns, and process improvements with automatic category detection from title/content keywords
accepts_args: true
arg_schema:
  - name: title_or_category
    required: true
    description: "Title (auto-detects category) OR explicit category (architecture/error/pattern/meta)"
  - name: title_if_explicit
    required: false
    description: "Title if first argument was explicit category"
  - name: content
    required: false
    description: "Optional brief content (used for detection if category auto-detected)"
composition: []
---

# Journal Command

**Purpose**: Capture decisions, solutions, and patterns as they emerge during development

**When to use**:
- After solving a difficult bug → `error` category
- When making architectural choice → `architecture` category
- When discovering reusable pattern → `pattern` category
- When reflecting on process → `meta` category

---

## Quick Reference

```bash
# Smart detection (recommended) - category auto-detected from keywords
/journal "Aurora vs DynamoDB for caching"              # → architecture
/journal "Lambda timeout in production"                # → error
/journal "Validation gates before workflow nodes"      # → pattern
/journal "Research-before-iteration saves deploy cycles"  # → meta

# Explicit category (backward compatible) - override auto-detection
/journal architecture "Aurora vs DynamoDB for caching"
/journal error "Lambda timeout in production"
/journal pattern "Validation gates before workflow nodes"
/journal meta "Research-before-iteration saves deploy cycles"
```

---

## Execution Flow

1. **Validate Category**: Ensure category is `architecture`, `error`, `pattern`, or `meta`
2. **Generate Filename**: `.claude/journals/{category}/{YYYY-MM-DD}-{slug}.md`
3. **Create Entry File**: Use category-specific template
4. **Update Index**: Add entry to `.claude/journals/README.md`
5. **Suggest Next Steps**: Based on category

---

## Prompt Template

You are executing the `/journal` command.

**Arguments**:
- `$1`: Title OR explicit category
- `$2`: Title (if $1 was explicit category), OR optional content (if $1 was title)
- `$3`: Optional content (if $1 was explicit category)

### Step 1: Parse Arguments and Detect Category Mode

**Mode Detection**:
```bash
# Check if $1 is explicit category
if [[ "$1" =~ ^(architecture|error|pattern|meta)$ ]]; then
  MODE="explicit"
  CATEGORY="$1"
  TITLE="$2"
  CONTENT="${3:-}"
else
  MODE="smart"
  TITLE="$1"
  CONTENT="${2:-}"
  # Run smart detection (see Step 1a below)
  # Sets: CATEGORY, CONFIDENCE_PERCENT
fi
```

**If MODE == "explicit"** → Skip to Step 1b (Validate Explicit Category)

**If MODE == "smart"** → Continue to Step 1a (Smart Category Detection)

---

### Step 1a: Smart Category Detection

**Only execute if MODE == "smart"**

**Keyword Registry** (weighted scoring):

| Category | Required Keywords (2 pts) | Supporting Keywords (1 pt) | Confidence Boost (0.5 pts) |
|----------|---------------------------|---------------------------|---------------------------|
| **architecture** | decision, choice, design, approach, architecture, tradeoff, trade-off | vs, versus, option, alternative, compare, consider, evaluate | ADR, comparison, strategy, pros, cons |
| **error** | bug, error, failed, failure, exception, crash, timeout, broken | fixed, solved, root cause, investigation, hypothesis, stack trace | Lambda, 500, 503, 504, production |
| **pattern** | pattern, technique, method | reusable, proven, applies to, template, abstraction, 3+ uses, recipe | workflow, standard, best practice |
| **meta** | process, workflow, improvement, lesson, observation, reflection, velocity | learned, measured, impact, team, retro, efficiency, practice | deploy cycles, time saved, productivity, measured |

**Detection Algorithm**:
```
1. Combine title + content for analysis:
   TEXT = lowercase($TITLE + " " + $CONTENT)

2. Score each category:
   For each category:
     score = 0

     For each required keyword:
       if keyword in TEXT: score += 2

     For each supporting keyword:
       if keyword in TEXT: score += 1

     For each confidence_boost keyword:
       if keyword in TEXT: score += 0.5

3. Select highest-scoring category:
   CATEGORY = category with max(score)

4. Calculate confidence percentage:
   CONFIDENCE_PERCENT = (score / total_keywords_for_category) * 100
   # Normalize to reasonable scale (capped at 100%)
```

**Confidence Thresholds and User Messaging**:

**High Confidence (≥80%)**:
```
✅ Detected category: {CATEGORY} ({CONFIDENCE}% confidence)

Creating: .claude/journals/{CATEGORY}/{date}-{slug}.md
```
→ Auto-create file, proceed to Step 2

**Medium Confidence (60-79%)**:
```
🤔 Detected category: {CATEGORY} ({CONFIDENCE}% confidence)

Does this look correct? If not, use explicit category:
  /journal architecture "{title}"
  /journal error "{title}"
  /journal pattern "{title}"
  /journal meta "{title}"

Creating: .claude/journals/{CATEGORY}/{date}-{slug}.md
```
→ Create file with confirmation message, proceed to Step 2

**Low Confidence (40-59%)**:
```
⚠️  Ambiguous category detected

Top matches:
  1. {category1} ({score1}%)
  2. {category2} ({score2}%)

Please specify category explicitly:
  /journal {category1} "{title}"
  /journal {category2} "{title}"

[Wait for user input - do NOT create file]
```
→ STOP execution, wait for user to re-run with explicit category

**Very Low Confidence (<40%)**:
```
❌ Cannot determine category from title/content

Keywords detected: {list_of_matched_keywords}

Please use explicit category:
  /journal architecture "{title}" - Design decisions
  /journal error "{title}"        - Bug solutions
  /journal pattern "{title}"      - Reusable patterns
  /journal meta "{title}"         - Process improvements

[Wait for user input - do NOT create file]
```
→ STOP execution, wait for user to re-run with explicit category

---

### Step 1b: Validate Explicit Category (Backward Compatibility)

**Only execute if MODE == "explicit"**

Check that `$1` (CATEGORY) is exactly one of: `architecture`, `error`, `pattern`, `meta`

If invalid, respond:
```
❌ Invalid category: $1

Valid categories:
  architecture - Design decisions, pre-ADR exploration
  error        - Bug investigations and solutions
  pattern      - Reusable code or workflow patterns
  meta         - Process improvements, tooling

Usage: /journal <category> "<title>" [content]
```
→ STOP execution, wait for user to correct input

If valid:
```
✅ Using explicit category: {CATEGORY}

Creating: .claude/journals/{CATEGORY}/{date}-{slug}.md
```
→ Proceed to Step 2

### Step 2: Generate Filename

```bash
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$2" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
FILEPATH=".claude/journals/$1/${DATE}-${SLUG}.md"
```

**Example**:
- Title: "Aurora vs DynamoDB"
- Generated: `.claude/journals/architecture/2025-12-23-aurora-vs-dynamodb.md`

### Step 3: Create Entry with Template

Choose template based on category `$1`:

---

#### Template: `architecture`

```markdown
---
title: {$2}
category: architecture
date: {date}
status: exploring
related_adrs: []
tags: []
---

# {$2}

## Context

**What problem are we solving?**

[Describe the situation, constraints, and why this decision matters]

## Options Considered

### Option 1: [Name]
**Pros**:
- [Benefit 1]
- [Benefit 2]

**Cons**:
- [Drawback 1]
- [Drawback 2]

**Trade-offs**:
- [Trade-off consideration]

### Option 2: [Name]
**Pros**:
- [Benefit 1]

**Cons**:
- [Drawback 1]

**Trade-offs**:
- [Trade-off consideration]

## Decision

**What did we choose?**

[State the decision clearly]

**Why this option?**

[Rationale - what made this the best choice given the constraints?]

## Consequences

**Positive**:
- [Expected benefit 1]
- [Expected benefit 2]

**Negative**:
- [Acceptable drawback 1]
- [Mitigation strategy]

**Risks**:
- [Risk 1]: [Likelihood] - [Impact] - [Mitigation]
- [Risk 2]: [Likelihood] - [Impact] - [Mitigation]

## Next Steps

- [ ] Action item 1
- [ ] Action item 2
- [ ] Create ADR if decision is significant
- [ ] Update CLAUDE.md if this affects principles

---

**Optional Content from user**: ${3:-None}
```

---

#### Template: `error`

```markdown
---
title: {$2}
category: error
date: {date}
resolved: yes
severity: high | medium | low
environment: production | staging | dev | local
tags: []
---

# {$2}

## Symptoms

**What went wrong?**

[Describe the observable problem - error messages, unexpected behavior, user impact]

**When did it occur?**

[Timing, frequency, conditions that trigger it]

**Who discovered it?**

[User report, monitoring alert, developer found]

## Investigation

### Hypothesis 1: [Description]
**Test**: [How did we test this?]
**Result**: ❌ Ruled out | ✅ Confirmed
**Evidence**: [What we found]

### Hypothesis 2: [Description]
**Test**: [How did we test this?]
**Result**: ❌ Ruled out | ✅ Confirmed
**Evidence**: [What we found]

### Hypothesis 3: [Description]
**Test**: [How did we test this?]
**Result**: ❌ Ruled out | ✅ Confirmed | ⏸️ Inconclusive
**Evidence**: [What we found]

## Root Cause

**What was actually wrong?**

[Detailed explanation of the underlying cause, not just symptoms]

**Why did this happen?**

[Chain of events or conditions that led to the problem]

**Why didn't we catch this earlier?**

[Gap in testing, monitoring, or process]

## Solution

**What did we fix?**

[Description of the fix - be specific about what changed]

**Code/Config Changes**:
```
[Relevant code snippets or config changes]
```

**Verification**:
- [How we verified the fix works]
- [Test we ran]
- [Monitoring we checked]

## Prevention

**How do we prevent this in the future?**

Action items:
- [ ] Update skill: [which skill] with [what pattern]
- [ ] Add test: [describe test that would have caught this]
- [ ] Add monitoring: [alert or dashboard]
- [ ] Update docs: [where and what]
- [ ] Review similar code: [locations that might have same issue]

**Lesson learned**:

[One-sentence takeaway for future reference]

---

**Optional Content from user**: ${3:-None}
```

---

#### Template: `pattern`

```markdown
---
title: {$2}
category: pattern
date: {date}
applies_to: [backend, frontend, infrastructure, testing, deployment]
confidence: proven | experimental | hypothesis
tags: []
---

# {$2}

## Problem

**What problem does this pattern solve?**

[Describe the recurring problem or challenge]

**Why is this a problem?**

[Explain the impact if not addressed]

**How often does this occur?**

[Frequency - helps prioritize pattern adoption]

## Solution

**How does the pattern work?**

[High-level explanation of the approach]

**Implementation**:

```python
# Example implementation
def example_function():
    """
    Demonstrate the pattern with concrete code
    """
    pass
```

**Key aspects**:
- [Critical element 1 that makes this work]
- [Critical element 2]
- [Critical element 3]

## When to Use

**Use this pattern when**:
- [Scenario 1 where pattern applies]
- [Scenario 2]
- [Scenario 3]

**Don't use when**:
- [Scenario where pattern is wrong choice]
- [Scenario where simpler approach works]

## Trade-offs

**Pros**:
- [Benefit 1]
- [Benefit 2]
- [Benefit 3]

**Cons**:
- [Cost/complexity 1]
- [Cost/complexity 2]

**When to pay the cost**:

[Guidance on when benefits outweigh costs]

## Examples in Project

**Current usage**:
- `{file_path}:{line}` - {brief description}
- `{file_path}:{line}` - {brief description}

**Related patterns**:
- Similar to: [related pattern name]
- Complements: [complementary pattern]
- Supersedes: [old pattern this replaces]

## Related Principles

**From CLAUDE.md**:
- [Relevant principle 1]
- [Relevant principle 2]

**From skills**:
- [Skill name]: [Relevant pattern]

---

**Optional Content from user**: ${3:-None}
```

---

#### Template: `meta`

```markdown
---
title: {$2}
category: meta
date: {date}
impact: high | medium | low
status: proposed | adopted | measuring
tags: []
---

# {$2}

## Observation

**What did we notice about our development process?**

[Describe the pattern, pain point, or opportunity]

**Evidence**:
- [Data point 1: commit messages, time spent, bugs found, etc.]
- [Data point 2]
- [Data point 3]

**Context**:

[When/where this observation applies]

## Analysis

**Why is this happening?**

[Root cause analysis of the process issue or success]

**What's the impact?**

- **Time**: [How much time saved/wasted?]
- **Quality**: [Effect on code quality]
- **Velocity**: [Effect on development speed]
- **Team**: [Effect on team satisfaction]

**What if we don't change?**

[Cost of inaction]

## Improvement

**What can we change?**

[Proposed process improvement]

**How will this help?**

[Expected benefits - be specific]

**What's the cost?**

[Time/effort required to implement]

**Experiment design** (if status: proposed):

```
Hypothesis: [What we believe will improve]
Measure: [How we'll know it worked]
Duration: [How long we'll try this]
Success criteria: [Specific threshold]
Rollback plan: [If it doesn't work]
```

## Action Items

- [ ] **Short-term** (this week): [immediate action]
- [ ] **Medium-term** (this month): [follow-up action]
- [ ] **Long-term** (this quarter): [systemic change]
- [ ] **Measurement**: [How we'll track impact]

## Follow-up

**Review date**: [When to revisit this]

**Questions to answer**:
- [Question 1 we need to answer to evaluate success]
- [Question 2]

---

**Optional Content from user**: ${3:-None}
```

---

### Step 4: Write File

Write the template content to `$FILEPATH`:

```bash
cat > "$FILEPATH" << 'EOF'
[Template content from above based on category]
EOF
```

Display confirmation:
```
✅ Created journal entry: .claude/journals/{category}/{filename}.md

Next: Edit file to fill in template sections
```

### Step 5: Update Index

Append entry to `.claude/journals/README.md` in the "Recent Entries" section:

```markdown
- [{date}] [{category}] [{title}]({category}/{filename}.md)
```

**Example**:
```markdown
- [2025-12-23] [architecture] [Aurora vs DynamoDB](architecture/2025-12-23-aurora-vs-dynamodb.md)
```

Update in reverse chronological order (newest first).

### Step 6: Suggest Next Steps

Based on category, suggest relevant actions:

#### For `architecture`:
```
💡 Next steps:
  - Fill in template sections (Context, Options, Decision)
  - If decision is significant, consider creating ADR: docs/adr/
  - Review in weekly planning to track decision outcome
```

#### For `error`:
```
💡 Next steps:
  - Document root cause and prevention measures
  - Consider if pattern should be added to error-investigation skill
  - Review similar code locations for same issue
  - Add test that would have caught this
```

#### For `pattern`:
```
💡 Next steps:
  - Document examples from current codebase
  - After pattern proves useful (3+ uses), graduate to:
    - Skill documentation if general
    - CODE_STYLE.md if project-specific
  - Tag other code locations that could use this pattern
```

#### For `meta`:
```
💡 Next steps:
  - Define measurement criteria for impact
  - Schedule follow-up review (suggest 2-4 weeks)
  - If impactful, update CLAUDE.md principles
  - Share insights with team in weekly retro
```

---

## Examples

### Example 1: Architecture Decision

```bash
/journal architecture "Aurora vs DynamoDB for report caching"
```

**Creates**:
- File: `.claude/journals/architecture/2025-12-23-aurora-vs-dynamodb-for-report-caching.md`
- Updates: `.claude/journals/README.md` index
- Suggests: "Consider creating ADR if decision is significant"

---

### Example 2: Bug Solution with Context

```bash
/journal error "Lambda timeout during peak traffic" "Cold start took 7.5s"
```

**Creates**:
- File: `.claude/journals/error/2025-12-23-lambda-timeout-during-peak-traffic.md`
- Includes user content: "Cold start took 7.5s" in Optional Content section
- Suggests: "Consider adding pattern to error-investigation skill"

---

### Example 3: Pattern Discovery

```bash
/journal pattern "Validation gates before workflow execution"
```

**Creates**:
- File: `.claude/journals/pattern/2025-12-23-validation-gates-before-workflow-execution.md`
- Suggests: "After 3+ uses, graduate to skill documentation"

---

### Example 4: Process Improvement

```bash
/journal meta "Research-before-iteration saved 3 deploy cycles"
```

**Creates**:
- File: `.claude/journals/meta/2025-12-23-research-before-iteration-saved-3-deploy-cycles.md`
- Suggests: "Schedule follow-up review in 2-4 weeks"

---

## Error Handling

### Invalid Category

```bash
/journal invalid-category "Some title"
```

**Response**:
```
❌ Invalid category: invalid-category

Valid categories:
  architecture - Design decisions
  error        - Bug solutions
  pattern      - Reusable patterns
  meta         - Process improvements

Usage: /journal <category> "<title>" [content]
```

### Missing Title

```bash
/journal architecture
```

**Response**:
```
❌ Missing required argument: title

Usage: /journal <category> "<title>" [content]

Example: /journal architecture "Aurora caching strategy"
```

### File Already Exists

If `.claude/journals/{category}/{date}-{slug}.md` already exists:

**Response**:
```
⚠️  Entry already exists: .claude/journals/{category}/{date}-{slug}.md

Options:
  1. Use different title
  2. Edit existing entry directly
  3. Append timestamp: /journal {category} "{title} v2"
```

---

## Related Commands

- `/report` - Summarize session (references journal entries)
- `/evolve` - Analyze journals for drift detection
- `/explain` - Can reference journal entries as examples

---

## Integration with Workflow

### Daily Use

```
Solve bug → /journal error "Bug title"
Make decision → /journal architecture "Decision title"
Find pattern → /journal pattern "Pattern title"
```

### Weekly Review

```
Friday afternoon:
1. Read this week's journals: ls -lt .claude/journals/*/*.md | head -10
2. Tag for graduation: Add #to-adr, #to-skill, #to-claude-md
3. Graduate significant entries
```

### Monthly Evolution

```
End of month:
1. Run: /evolve
2. Review drift between journals and CLAUDE.md
3. Graduate patterns to skills
4. Archive old entries
```

---

## Tips

### Do
- **Journal immediately** while context is fresh
- **Be honest** about uncertainties and failures
- **Include evidence** (error messages, metrics)
- **Keep it short** (2-5 minutes to create)
- **Review weekly** to catch patterns

### Don't
- **Over-think format** (templates are guidance)
- **Wait too long** (context fades fast)
- **Skip the "why"** (most important part)
- **Hide failures** (document what didn't work)

---

## See Also

- `.claude/journals/README.md` - Journal system overview
- `.claude/commands/README.md` - Command system docs
- `docs/adr/README.md` - Formal architecture decision records
- `.claude/CLAUDE.md` - Project principles
