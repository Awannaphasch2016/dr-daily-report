---
name: what-if
description: Explore scenarios, compare alternatives, and analyze relationships between concepts
accepts_args: true
arg_schema:
  - name: assumption
    required: true
    description: "Scenario to explore, comparison request, or relationship analysis (quoted if spaces)"
  - name: save
    required: false
    description: "Optional: 'save' to create persistent analysis document in .claude/what-if/"
composition:
  - skill: research
---

# What-If Command

**Purpose**: Comprehensive comparison command - explore scenarios, compare alternatives, and analyze relationships

**Three Modes**:
1. **Binary comparison** (scenario analysis) - "What if X instead of Y?"
2. **Multi-way comparison** - "Compare X vs Y vs Z"
3. **Relationship analysis** - "How do X and Y relate?"

**When to use**:
- Before making major architectural decisions
- When comparing multiple alternatives (2+)
- To understand relationships between concepts
- To validate assumptions about constraints
- To explore failure modes without breaking things

---

## Quick Reference

### Pattern 1: Binary Comparison (Scenario Analysis)
```bash
# Architecture exploration
/what-if "We used PostgreSQL instead of Aurora"

# Performance analysis
/what-if "Lambda timeout was 15s instead of 30s"

# Design validation
/what-if "We removed the Necessary Condition Principle"

# Scaling scenarios
/what-if "Traffic increased 10x overnight"
```

### Pattern 2: Multi-Way Comparison (NEW)
```bash
# Compare 3+ options
/what-if "compare Redis vs DynamoDB vs ElastiCache for caching"

# Technology evaluation
/what-if "compare Lambda vs ECS vs EKS for compute"

# Save comparison
/what-if "compare PostgreSQL vs MySQL vs Aurora" save
```

### Pattern 3: Relationship Analysis (NEW)
```bash
# Analyze how concepts relate
/what-if "analyze relationship between caching and CDN"

# Understand connections
/what-if "how do microservices and serverless relate"

# Part-whole analysis
/what-if "relationship between Lambda and API Gateway"
```

---

## What-If vs Other Commands

| Command | Purpose | Question |
|---------|---------|----------|
| **`/validate`** | Check current reality | "What IS true now?" |
| **`/proof`** | Derive from constraints | "What MUST be true?" |
| **`/what-if`** | Explore alternatives | "What WOULD BE true if...?" |
| **`/journal`** | Document decisions | "What WAS decided?" |

**Complementary usage**:
```bash
/what-if "Lambda timeout 15s"      # Explore scenario
/proof "15s timeout breaks X"      # Prove implication
/journal architecture "Why 30s"    # Document rationale
```

---

## Execution Flow

### Step 1: Parse Counterfactual Assumption

**Extract the change**:
```bash
ASSUMPTION="$1"
SAVE_FLAG="${2:-}"

# Parse assumption type
if [[ "$ASSUMPTION" =~ (instead of|rather than|replace) ]]; then
  TYPE="replacement"  # Swapping one thing for another
elif [[ "$ASSUMPTION" =~ (removed|without|eliminated) ]]; then
  TYPE="removal"      # Taking something away
elif [[ "$ASSUMPTION" =~ (added|with|included) ]]; then
  TYPE="addition"     # Adding something new
elif [[ "$ASSUMPTION" =~ (increased|decreased|was.*instead) ]]; then
  TYPE="modification" # Changing a parameter
else
  TYPE="general"      # Generic scenario
fi
```

---

### Step 2: Establish Current Reality (Baseline)

**Document current state**:
```markdown
## Current Reality

**Current design**:
{How it works now - from code/docs/config}

**Key properties**:
- Property 1: {Current value/behavior}
- Property 2: {Current value/behavior}

**Sources**:
- Code: {file:line references}
- Config: {terraform/doppler references}
- Docs: {CLAUDE.md references}
```

**Example**:
```markdown
Current Reality: Lambda timeout = 30s

Sources:
  - terraform/lambda.tf:46: timeout = 30
  - CLAUDE.md: "30s timeout necessary for image processing"
  - src/processor.py:12: Image processing takes 20-25s
```

---

### Step 3: Trace Implications Under New Assumption

**Ripple effect analysis**:
```markdown
## Under New Assumption: {assumption}

### What Changes Immediately
- Change 1: {Direct consequence}
- Change 2: {Direct consequence}

### Cascading Effects
- Level 1: {What breaks/improves as direct result}
- Level 2: {What breaks/improves from Level 1}
- Level 3: {What breaks/improves from Level 2}

### Components Affected
- Component A: {How it's affected}
- Component B: {How it's affected}
```

**Example**:
```markdown
Under New Assumption: Lambda timeout = 15s

What Changes Immediately:
  - Lambda max execution time drops from 30s → 15s

Cascading Effects:
  Level 1 (Direct):
    - Image processing (20-25s) exceeds timeout ❌
    - Report generation (8-12s) still within limit ✓

  Level 2 (Indirect):
    - Image processing jobs fail
    - Users get timeout errors
    - Manual retry needed

  Level 3 (System-wide):
    - SLA violations (99% uptime target missed)
    - Increased support tickets
    - Data pipeline gaps

Components Affected:
  - src/processor.py: Breaks (exceeds 15s)
  - src/report.py: Works (under 15s)
  - terraform/lambda.tf: Needs update
```

---

### Step 4: Identify What Breaks

**Failure analysis**:
```markdown
## What Breaks

### Critical Failures (Showstoppers)
- **Failure 1**: {Description}
  - Impact: {User/system impact}
  - Frequency: {How often}
  - Severity: {Critical | High | Medium | Low}
  - Workaround: {Possible | None}

### Degraded Functionality
- **Degradation 1**: {What works but worse}
  - Before: {Current state}
  - After: {Degraded state}
  - Impact: {Acceptable | Unacceptable}
```

**Example**:
```markdown
What Breaks

Critical Failures:
  - **Image processing timeouts**
    - Impact: Users cannot generate reports with charts
    - Frequency: 100% of image-heavy reports
    - Severity: Critical (core feature broken)
    - Workaround: None (hard timeout limit)

Degraded Functionality:
  - **Report generation slower**
    - Before: 8-12s generation
    - After: Multiple retries due to cold starts
    - Impact: Acceptable (still under 15s)
```

---

### Step 5: Identify What Improves

**Benefit analysis**:
```markdown
## What Improves

### Performance Gains
- **Gain 1**: {Description}
  - Metric: {What improves}
  - Magnitude: {How much}
  - Value: {Worth the trade-off?}

### Cost Reductions
- **Savings 1**: {Description}
  - Before: {Current cost}
  - After: {New cost}
  - Annual savings: {Amount}

### Simplifications
- **Simplification 1**: {What becomes simpler}
  - Complexity reduced: {How}
  - Maintenance: {Easier | Same | Harder}
```

**Example**:
```markdown
What Improves

Performance Gains:
  - **Faster failure detection**
    - Metric: Time to detect timeout
    - Magnitude: 30s → 15s (50% faster)
    - Value: Minor (fails faster, but still fails)

Cost Reductions:
  - **Lower Lambda costs**
    - Before: $X per month (avg 25s execution)
    - After: $Y per month (avg 12s execution, failures excluded)
    - Annual savings: Negligible (failures negate savings)

Simplifications:
  - **None identified**
    - Actually increases complexity (need error handling)
```

---

### Step 6: Extract Insights

**What this reveals**:
```markdown
## Insights Revealed

### Assumptions Exposed
- **Hidden assumption 1**: {What we didn't realize we assumed}
  - Evidence: {What breaks reveals this assumption}
  - Criticality: {How critical is this assumption}

### Trade-offs Clarified
- **Trade-off 1**: {What we gave up for what we got}
  - Original choice: {What we chose}
  - Alternative cost: {What we avoided}
  - Validated: {Yes | No | Partially}

### Boundary Conditions
- **Boundary 1**: {Limit that would be violated}
  - Threshold: {What's the limit}
  - Current margin: {How close are we}
  - Safety factor: {How much buffer}

### Design Rationale
- **Why current design exists**: {Revealed by what-if}
  - Constraint 1: {Must satisfy}
  - Constraint 2: {Must satisfy}
  - Conclusion: {Why current design is optimal/necessary}
```

**Example**:
```markdown
Insights Revealed

Assumptions Exposed:
  - **Image processing is non-negotiable**
    - Evidence: 15s timeout breaks core feature
    - Criticality: High (defines product capability)
    - Implicit: We never questioned "must process images synchronously"

Trade-offs Clarified:
  - **Cost vs Reliability**
    - Original choice: 30s timeout (higher cost, more reliability)
    - Alternative cost: 15s timeout (lower cost, broken features)
    - Validated: Yes (30s is necessary, not arbitrary)

Boundary Conditions:
  - **Image processing time: 20-25s**
    - Threshold: Must be < Lambda timeout
    - Current margin: 30s - 25s = 5s (20% buffer)
    - Safety factor: Adequate for p95, tight for p99

Design Rationale:
  - **Why 30s timeout exists**:
    - Constraint 1: Image processing takes 20-25s
    - Constraint 2: Need buffer for variance (p99)
    - Constraint 3: AWS max timeout is 15 minutes (30s well within)
    - Conclusion: 30s is minimum viable, not arbitrary choice
```

---

### Step 7: Generate Recommendation

**Decision guidance**:
```markdown
## Recommendation

### Should We Make This Change?

**Decision**: ✅ YES | ❌ NO | ⚠️ CONDITIONALLY

**Rationale**:
{Why this decision based on analysis}

**Conditions** (if conditional):
- Condition 1: {What must be true}
- Condition 2: {What must be addressed}

### Action Items

**If YES**:
- [ ] {Implementation step 1}
- [ ] {Implementation step 2}

**If NO**:
- [ ] Document why (use `/journal`)
- [ ] Revisit if constraints change

**If CONDITIONAL**:
- [ ] {Prerequisite 1}
- [ ] {Prerequisite 2}
- [ ] Re-evaluate after prerequisites met

### Follow-Up

**Journal this**:
{If insights are significant, suggest journaling}
- Use: `/journal architecture "{title}"`
- Capture: {What to document}

**Prove implications**:
{If formal proof would help}
- Use: `/proof "{theorem}"`
- Verify: {What to prove}

**Validate assumptions**:
{If empirical check needed}
- Use: `/validate "{claim}"`
- Check: {What to verify}
```

**Example**:
```markdown
Recommendation

Should We Make This Change?

Decision: ❌ NO

Rationale:
  Reducing Lambda timeout from 30s to 15s breaks critical image processing
  functionality with no viable workaround. Cost savings are negligible and
  do not justify losing core product feature.

Action Items:

If NO:
  - [x] Document why 30s timeout is necessary
  - [ ] Journal: `/journal architecture "Lambda 30s timeout rationale"`
  - [ ] Consider async image processing for future (decouples from timeout)

Follow-Up:

Journal this:
  Title: "Why Lambda needs 30s timeout for image processing"
  Capture: Boundary condition (20-25s processing time), lack of async alternative

Prove implications:
  Use: `/proof "Lambda with 15s timeout cannot process 100MB images"`
  Verify: Formal proof that 15s is insufficient

Alternative exploration:
  Use: `/what-if "Image processing was async via SQS"`
  Explore: How to decouple image processing from request timeout
```

---

## Analysis Templates by Type

### Template 1: Technology Replacement

```markdown
WHAT-IF: We used {Technology B} instead of {Technology A}

CURRENT: {Technology A}
  - Features: {What it provides}
  - Limitations: {Known constraints}
  - Integrations: {What depends on it}

PROPOSED: {Technology B}
  - Features: {What it provides}
  - Gaps: {What it doesn't provide}
  - Migration: {How to switch}

COMPARISON:
  | Aspect | Tech A (current) | Tech B (proposed) |
  |--------|------------------|-------------------|
  | Feature 1 | {A value} | {B value} |
  | Feature 2 | {A value} | {B value} |
  | Cost | {A cost} | {B cost} |

BREAKS:
  - {Feature using Tech A that wouldn't work with Tech B}

IMPROVES:
  - {What gets better with Tech B}

INSIGHT:
  - Why we chose Tech A: {Revealed by what breaks}

RECOMMENDATION: {Stay | Switch | Hybrid}
```

---

### Template 2: Parameter Modification

```markdown
WHAT-IF: {Parameter} was {New Value} instead of {Current Value}

CURRENT VALUE: {Current}
  - Source: {Config file}
  - Rationale: {Why this value}

PROPOSED VALUE: {New}
  - Difference: {New - Current}
  - Percentage: {(New/Current - 1) * 100}%

THRESHOLD ANALYSIS:
  - Minimum: {Below this breaks}
  - Current: {What we have}
  - Proposed: {What we're considering}
  - Maximum: {Above this doesn't help}

IMPACT CASCADE:
  {Parameter} = {New Value}
    → Affects: {Dependent A}
      → Which affects: {Dependent B}
        → Which affects: {Dependent C}

BREAKS IF TOO LOW:
  - {Component that fails}

IMPROVES IF HIGHER:
  - {Component that benefits}

INSIGHT:
  Current value is: {Minimum necessary | Optimal | Over-provisioned}

RECOMMENDATION: {Increase | Decrease | Keep Current}
```

---

### Template 3: Principle Removal

```markdown
WHAT-IF: We removed the "{Principle Name}" principle

CURRENT PRINCIPLE: {Principle}
  - Source: {CLAUDE.md section}
  - Purpose: {What it prevents/ensures}
  - Examples: {Where it's applied}

WITHOUT PRINCIPLE:
  - Code changes: {What would be allowed}
  - Removed constraints: {What freedom we gain}

FAILURE SCENARIOS:
  Scenario 1: {What could go wrong}
    - Frequency: {How often}
    - Impact: {Severity}
    - Example: {Concrete case}

  Scenario 2: {What could go wrong}
    - Frequency: {How often}
    - Impact: {Severity}
    - Example: {Concrete case}

BENEFITS:
  - {What becomes easier/faster without principle}

INSIGHT:
  This principle exists because: {Revealed by failures}
  Prevents: {Failure modes that would occur}
  Trade-off: {Safety vs Convenience}

RECOMMENDATION: {Keep | Modify | Remove}
```

---

### Template 4: Scaling Scenario

```markdown
WHAT-IF: {Metric} increased by {Multiplier}x

CURRENT SCALE:
  - {Metric}: {Current value}
  - Capacity: {Current limit}
  - Utilization: {Current percentage}

PROPOSED SCALE:
  - {Metric}: {New value} ({Multiplier}x increase)
  - Required capacity: {Calculated need}

BOTTLENECK ANALYSIS:
  Component | Current Limit | Required | Status |
  ----------|--------------|----------|--------|
  Lambda    | {limit}      | {need}   | {✓ | ✗} |
  Database  | {limit}      | {need}   | {✓ | ✗} |
  Cache     | {limit}      | {need}   | {✓ | ✗} |

FIRST BOTTLENECK: {Component that fails first}
  - Limit: {Current capacity}
  - Needed: {Required capacity}
  - Gap: {Shortfall}

CASCADING FAILURES:
  {First bottleneck}
    → Causes: {Secondary failure}
      → Causes: {Tertiary failure}

UPGRADES NEEDED:
  - [ ] {Upgrade 1}: {Current} → {Required}
  - [ ] {Upgrade 2}: {Current} → {Required}
  - [ ] {Upgrade 3}: {Current} → {Required}

COST IMPACT:
  - Current: {$/month}
  - After scaling: {$/month} ({+X}% increase)

RECOMMENDATION: {Can scale | Cannot scale | Needs redesign}
```

---

## Examples

### Example 1: Architecture Alternative

```bash
/what-if "We used PostgreSQL instead of Aurora MySQL"
```

**Output**:
```markdown
WHAT-IF ANALYSIS: PostgreSQL instead of Aurora MySQL

CURRENT REALITY
  Database: Aurora MySQL
  - Serverless v2: Auto-scaling
  - Compatibility: MySQL 8.0
  - Integrations: Existing schemas, pymysql driver

UNDER NEW ASSUMPTION: PostgreSQL

What Changes:
  - Database engine: MySQL → PostgreSQL
  - Driver: pymysql → psycopg2
  - SQL dialect: MySQL-specific → PostgreSQL-specific

WHAT BREAKS

Critical Failures:
  - **JSON column syntax**
    - MySQL: JSON_EXTRACT(col, '$.path')
    - PostgreSQL: col->>'path'
    - Files affected: All data layer (src/data/*.py)
    - Migration effort: High (50+ queries to rewrite)

  - **Auto-increment columns**
    - MySQL: AUTO_INCREMENT
    - PostgreSQL: SERIAL or SEQUENCE
    - Schema migration: Required for all tables

  - **Date functions**
    - MySQL: DATE_FORMAT(), NOW()
    - PostgreSQL: TO_CHAR(), CURRENT_TIMESTAMP
    - Queries affected: 20+ time-based queries

WHAT IMPROVES

Performance Gains:
  - **Better JSON support**
    - PostgreSQL JSONB is faster than MySQL JSON
    - Indexable (GIN indexes)
    - Potential 2-3x speedup for JSON queries

  - **Advanced features**
    - Window functions (better analytics)
    - Full-text search (native)
    - Array types (flexible schemas)

Cost:
  - Similar pricing (Aurora PostgreSQL exists)
  - No significant cost difference

INSIGHTS REVEALED

Assumptions Exposed:
  - **Heavy reliance on MySQL-specific syntax**
    - Assumed: "SQL is portable"
    - Reality: 50+ queries use MySQL-specific features
    - Lock-in: High (switching cost ~2 weeks work)

Trade-offs Clarified:
  - **MySQL chosen for**: Familiarity, existing schemas
  - **PostgreSQL benefits**: Better JSON, more features
  - **Switching cost**: High (not worth it without strong reason)

Design Rationale:
  - Aurora MySQL chosen because:
    1. Team familiar with MySQL
    2. Existing schemas already in MySQL
    3. Aurora serverless v2 fits workload
  - PostgreSQL would be better for greenfield
  - But migration cost outweighs benefits now

RECOMMENDATION: ❌ NO (Stay with Aurora MySQL)

Rationale:
  PostgreSQL has technical advantages (better JSON, more features) but
  migration cost is too high for incremental benefit. Switching would
  require rewriting 50+ queries and migrating schemas with no clear ROI.

  Consider PostgreSQL for NEW projects, but keep MySQL for this one.

Action Items:
  - [ ] Document MySQL decision in ADR
  - [ ] Journal: `/journal architecture "Why Aurora MySQL over PostgreSQL"`
  - [ ] Avoid MySQL-specific features in NEW code (easier future migration)
```

---

### Example 2: Parameter Change

```bash
/what-if "Lambda timeout was 15s instead of 30s"
```

**Output**:
```markdown
WHAT-IF ANALYSIS: Lambda timeout 15s instead of 30s

CURRENT REALITY
  Lambda timeout: 30s
  - Source: terraform/lambda.tf:46
  - Rationale: Image processing takes 20-25s (needs buffer)

UNDER NEW ASSUMPTION: Timeout = 15s

What Changes Immediately:
  - Max execution time: 30s → 15s (50% reduction)
  - Cost per invocation: Potentially lower (shorter execution)

WHAT BREAKS

Critical Failures:
  - **Image processing timeouts**
    - Current: 20-25s execution (p95)
    - Timeout: 15s
    - Result: 100% failure rate for image processing
    - Impact: Core feature broken
    - Workaround: None (hard limit)

WHAT IMPROVES

Performance:
  - **Faster failure detection**
    - Failed jobs detected in 15s instead of 30s
    - Value: Minimal (still fails)

Cost:
  - **Marginal savings**
    - Before: Average 25s * $0.000001667/s = $0.000041675
    - After: Jobs fail at 15s or succeed faster
    - Savings: Negligible (failures cost same, successes unaffected)

INSIGHTS REVEALED

Assumptions Exposed:
  - **Image processing is synchronous and slow**
    - Evidence: Takes 20-25s (cannot be reduced)
    - Implicit: We never considered async processing
    - Constraint: Lambda is request-response model

Boundary Conditions:
  - **Image processing time: 20-25s minimum**
    - Threshold: Cannot go below due to PIL library
    - Current margin: 30s - 25s = 5s (20% buffer)
    - Safety factor: Tight (p99 might exceed 30s)

Design Rationale:
  - **Why 30s timeout**:
    - Must be > 25s (p95 processing time)
    - Buffer for variance (p99 spikes)
    - Still well under AWS max (900s)
  - Conclusion: 30s is minimum viable, not arbitrary

RECOMMENDATION: ❌ NO (Keep 30s timeout)

Rationale:
  15s timeout breaks image processing with no workaround.
  No significant cost savings. 30s is driven by actual
  constraint (processing time), not arbitrary choice.

Alternative to Explore:
  - Use: `/what-if "Image processing was async via SQS"`
  - Benefit: Decouple from request timeout
  - Then could reduce Lambda timeout to 10s for API-only

Follow-Up:
  - Journal: `/journal architecture "Lambda 30s timeout for image processing"`
  - Prove: `/proof "Lambda with 15s timeout cannot process 100MB images"`
  - Consider: Async image processing architecture (future work)
```

---

### Example 3: Save Analysis

```bash
/what-if "We removed the Necessary Condition Principle" save
```

**Output**:
```markdown
[... full analysis ...]

✅ What-if analysis saved: .claude/what-if/2025-12-24-removed-necessary-condition-principle.md

Next steps:
  - Review analysis in .claude/what-if/
  - If insights significant, journal them
  - Reference in architectural decisions
```

---

## Integration with Other Commands

### Workflow 1: What-If → Proof → Journal

```bash
# Explore scenario
/what-if "Lambda timeout 15s instead of 30s"
# → Reveals: Would break image processing

# Prove the implication
/proof "Lambda with 15s timeout cannot process 100MB images"
# → ✅ PROVEN (would fail)

# Document the finding
/journal architecture "Why Lambda needs 30s timeout"
```

---

### Workflow 2: What-If → Specify → Plan

```bash
# Explore limitation
/what-if "Traffic increased 10x"
# → Reveals: Current architecture maxes at 5000 req/s

# Design alternative
/specify "SQS-based async processing for 10x scale"

# Full implementation plan
EnterPlanMode
```

---

### Workflow 3: What-If → Validate → What-If (Iteration)

```bash
# Initial exploration
/what-if "We used Redis instead of Aurora for caching"
# → Suggests: Might be faster

# Validate assumption
/validate "Redis is faster than Aurora for our access patterns"
# → ⚠️ PARTIALLY TRUE (depends on query type)

# Refined exploration
/what-if "We used Redis for hot data, Aurora for analytics"
# → Better: Hybrid approach balances trade-offs
```

---

## Tips

### Do
- **Be specific** about the change (avoid vague assumptions)
- **Trace cascades** (second/third-order effects matter)
- **Check both directions** (what breaks AND what improves)
- **Expose assumptions** (what the scenario reveals)
- **Save significant analyses** (use "save" argument)
- **Follow up** with proof/validation as needed

### Don't
- **Assume without evidence** (ground in actual constraints)
- **Ignore trade-offs** (every change has costs)
- **Stop at first-order** (cascade effects reveal more)
- **Treat as prediction** (it's exploration, not forecast)

---

## NEW: Multi-Way Comparison Template

**Pattern**: Compare 3+ alternatives with evaluation matrix

**Trigger keywords**:
- "compare X vs Y vs Z"
- "compare X, Y, and Z"
- "evaluate X vs Y vs Z"
- "which is better: X, Y, or Z"

**Template**:
```markdown
MULTI-WAY COMPARISON: {Option A} vs {Option B} vs {Option C}

COMPARISON CONTEXT
  Purpose: {What you're trying to achieve}
  Scale: {Usage level / requirements}
  Budget: {Cost constraints}
  Timeline: {Implementation urgency}

---

## Option 1: {Name}

**Description**: {Brief explanation}

**Strengths**:
- {Key advantage 1}
- {Key advantage 2}
- {Key advantage 3}

**Weaknesses**:
- {Key limitation 1}
- {Key limitation 2}
- {Key limitation 3}

**Cost**: {Monthly/annual cost estimate}
**Complexity**: {Low | Medium | High}
**Performance**: {Score/10 with justification}

---

## Option 2: {Name}
[Same structure as Option 1]

---

## Option 3: {Name}
[Same structure as Option 1]

---

## COMPARISON MATRIX

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| **Performance** | X/10 | Y/10 | Z/10 |
| **Cost** | X/10 | Y/10 | Z/10 |
| **Complexity** | X/10 | Y/10 | Z/10 |
| **Scalability** | X/10 | Y/10 | Z/10 |
| **TOTAL** | XX/40 | YY/40 | ZZ/40 |

---

## SIMILARITIES

What all options share:
- {Common feature 1}
- {Common feature 2}
- {Common feature 3}

---

## DIFFERENCES

**{Dimension 1}**:
- Option A: {Characteristic}
- Option B: {Characteristic}
- Option C: {Characteristic}

**{Dimension 2}**:
- Option A: {Characteristic}
- Option B: {Characteristic}
- Option C: {Characteristic}

---

## RELATIONSHIPS

**Substitution**: {Which options can replace each other}
- {Option X} can substitute {Option Y} for: {Use case}
- But NOT for: {Limitation}

**Complement**: {Which options work well together}
- {Option X} + {Option Y} complement because: {Synergy}
- Example: {Concrete composition pattern}

**Composition**: {How options can be layered}
```
{Layer diagram showing how options compose}
```

---

## RECOMMENDATION: {Winner} (Score: XX/40)

**Why**:
- {Primary reason for choice}
- {Secondary reason}
- {Trade-off acceptance}

**Trade-off**:
- Lose: {What you give up}
- Gain: {What you get}

**When to choose {Alternative} instead**:
- {Scenario 1 where alternative is better}
- {Scenario 2 where alternative is better}

---

## NEXT STEPS

```bash
# Recommended validation
/validate "{Key assumption about chosen option}"

# Then specify implementation
/specify "{Chosen option} implementation"

# Then plan
EnterPlanMode
```
```

**Example**: See specification document for full Redis vs DynamoDB vs ElastiCache comparison

---

## NEW: Relationship Analysis Template

**Pattern**: Analyze how two concepts relate to each other

**Trigger keywords**:
- "analyze relationship between X and Y"
- "how do X and Y relate"
- "relationship between X and Y"
- "how are X and Y connected"

**Template**:
```markdown
RELATIONSHIP ANALYSIS: {Concept A} and {Concept B}

---

## Concepts Being Analyzed

### Concept 1: {Name A}
**Definition**: {What it is}
**Location**: {Where it operates / layer}
**Purpose**: {Why it exists}
**Examples**: {Concrete instances}

### Concept 2: {Name B}
**Definition**: {What it is}
**Location**: {Where it operates / layer}
**Purpose**: {Why it exists}
**Examples**: {Concrete instances}

---

## SIMILARITY ANALYSIS

**What they share**:
- ✅ {Similarity 1}
- ✅ {Similarity 2}
- ✅ {Similarity 3}
- ✅ {Similarity 4}
- ✅ {Similarity 5}

**Similarity score**: X/10 ({High | Medium | Low} similarity)

---

## DIFFERENCE ANALYSIS

**What makes them different**:

| Aspect | Concept A | Concept B |
|--------|-----------|-----------|
| **{Dimension 1}** | {A value} | {B value} |
| **{Dimension 2}** | {A value} | {B value} |
| **{Dimension 3}** | {A value} | {B value} |
| **{Dimension 4}** | {A value} | {B value} |

**Difference score**: X/10 ({High | Medium | Low} difference)

---

## RELATIONSHIP TYPES

### 1. Part-Whole Relationship: {YES | NO}
- {Analysis of whether one is part of the other}
- {Or whether they are peer concepts}

### 2. Complement Relationship: {YES | NO}
- **{If yes, explain how they complement each other}**
- {Concrete example of complementary usage}

**Example**:
```
{Diagram showing complementary pattern}
```

### 3. Substitution Relationship: {YES | NO | PARTIAL}
- **{Analysis of substitutability}**
- {What scenarios allow substitution}
- {What scenarios don't allow substitution}

**Example substitution**:
```
{Concrete example of substitution pattern}

Limitation: {What you lose with substitution}
```

### 4. Composition Relationship: {YES | NO}
- **{Analysis of how they compose}**

**Composition pattern**:
```
{Layer diagram showing composition}
```

**Benefits of composition**:
- {Benefit 1}
- {Benefit 2}
- {Benefit 3}

---

## INTERACTION PATTERNS

### Pattern 1: {Pattern Name}
```
{Description of how they interact}
  +
{Second component}
  =
{Result}
```

### Pattern 2: {Pattern Name}
```
{Description of interaction}
```

### Pattern 3: Conflict (if applicable)
```
{Scenario where they conflict}
  BUT
{Problem that arises}
  =
{Consequence}

FIX: {How to resolve conflict}
```

---

## PROS & CONS OF USING BOTH

### Pros of Combined Usage
- ✅ {Advantage 1}
- ✅ {Advantage 2}
- ✅ {Advantage 3}

### Cons of Combined Usage
- ❌ {Disadvantage 1}
- ❌ {Disadvantage 2}
- ❌ {Disadvantage 3}

---

## RISK ANALYSIS

### Risk 1: {Risk Name}
**Description**: {What could go wrong}
**Likelihood**: {High | Medium | Low}
**Mitigation**: {How to prevent/reduce}

### Risk 2: {Risk Name}
[Same structure]

---

## RECOMMENDATION

**Use both** | **Use only A** | **Use only B** | **Use {specific pattern}**

**Rationale**:
{Why this recommendation based on analysis}

**Avoid**:
- {Anti-pattern 1}
- {Anti-pattern 2}

**Best practice**:
```
{Concrete recommended usage pattern}
```

---

## NEXT STEPS

```bash
# Document this pattern
/journal architecture "{Title}"

# Specify implementation
/specify "{Implementation approach}"

# Validate assumptions
/validate "{Key assumption}"
```
```

**Example**: See specification document for full Caching vs CDN relationship analysis

---

## See Also

- `.claude/commands/proof.md` - Prove implications deductively
- `.claude/commands/validate.md` - Check current reality empirically
- `.claude/commands/journal.md` - Document insights from what-if
- `.claude/commands/specify.md` - Design alternatives explored
- `.claude/specifications/workflow/2025-12-26-enhance-what-if-as-comparison-command.md` - Full specification with examples
