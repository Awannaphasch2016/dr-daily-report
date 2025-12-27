---
title: /research command - diverge before /specify converge
date: 2025-12-24
status: analysis
recommendation: CONDITIONALLY YES
---

# What-If Analysis: /research Command for Divergent Solution Exploration

## Question

"Should we implement `/research` as a divergent exploration phase before `/specify` converges on optimal solution?"

**Proposed model**:
```
/research (diverge) → explore ALL potential solutions
    ↓
/specify (converge) → select OPTIMAL solution
    ↓
Implementation
```

---

## Current Reality

### How We Currently Explore Solutions

**Without /research command**:

1. **Ad-hoc exploration** in conversation:
   ```
   User: "How should I implement feature X?"
   Claude: "Here are 3 approaches: A, B, C..."
   User: "Let's go with B"
   ```

2. **Direct to /specify**:
   ```
   /specify "Feature X with approach B"
   ```
   - Assumes approach B is already chosen
   - No systematic exploration phase
   - Might miss better alternatives

3. **Use /what-if for alternatives**:
   ```
   /what-if "We used approach A instead of B"
   /what-if "We used approach C instead of B"
   ```
   - Reactive (explores alternatives AFTER choosing)
   - Not proactive (doesn't generate alternatives BEFORE choosing)

### Current Gaps

**Problem 1: No systematic divergent phase**
- Exploration happens informally in conversation
- Easy to anchor on first idea
- Alternatives discovered too late (after specification)

**Problem 2: Specify assumes direction**
- `/specify "REST API for backtester"`
- Already assumes "REST API" (not GraphQL, gRPC, WebSockets)
- Skips the "what are ALL the ways to expose backtester?" question

**Problem 3: What-if is reactive, not proactive**
- `/what-if "GraphQL instead of REST"` requires you to KNOW about GraphQL first
- Doesn't help DISCOVER alternatives you haven't thought of

---

## Under New Assumption: /research Command Exists

### Proposed Workflow

```bash
# Step 1: DIVERGE - Explore all potential solutions
/research "How to expose backtester functionality to users"

# Output: Comprehensive research report
# - Approach 1: REST API
# - Approach 2: GraphQL API
# - Approach 3: gRPC for performance
# - Approach 4: WebSocket for real-time
# - Approach 5: Telegram Mini App native integration
# - Approach 6: Hybrid (REST + WebSocket)

# Step 2: CONVERGE - Select optimal based on constraints
/specify "REST API for backtester (from research: optimal for simplicity)"

# Step 3: IMPLEMENT
EnterPlanMode
```

### What /research Would Do

**Phase 1: Problem decomposition**
```markdown
Research Goal: "How to expose backtester functionality"

Decomposed into:
  1. What functionality to expose? (scope)
  2. Who are the consumers? (audience)
  3. What are the constraints? (technical, time, cost)
  4. What are the quality attributes? (performance, reliability, UX)
```

**Phase 2: Solution space exploration**
```markdown
Potential Solutions:

Solution 1: REST API
  Pros: Standard, easy to implement, well-understood
  Cons: Polling for long-running jobs, stateless
  Fit: High (for CRUD operations)
  Precedent: Industry standard, existing patterns

Solution 2: GraphQL API
  Pros: Flexible queries, single endpoint, schema-first
  Cons: Complexity, overkill for simple use case
  Fit: Medium (useful if many related entities)
  Precedent: GitHub API, Shopify

Solution 3: gRPC
  Pros: High performance, streaming, type-safe
  Cons: Less browser-friendly, steeper learning curve
  Fit: Low (browser client needed)
  Precedent: Google services, microservices

Solution 4: WebSocket
  Pros: Real-time updates, bidirectional
  Cons: Connection management, scaling complexity
  Fit: Medium (for real-time backtesting progress)
  Precedent: Trading platforms, chat apps

Solution 5: Telegram Mini App Native
  Pros: Native integration, no server needed
  Cons: Telegram-only, limited by platform
  Fit: High (already using Telegram)
  Precedent: Telegram bots with inline keyboards

Solution 6: Hybrid (REST + WebSocket)
  Pros: Best of both (CRUD + real-time)
  Cons: Complexity, two systems to maintain
  Fit: High (optimal for this use case)
  Precedent: Slack API, Discord API
```

**Phase 3: Evaluation matrix**
```markdown
Evaluation Criteria:
  - Implementation time: 1-5 (1=fastest)
  - Learning curve: 1-5 (1=easiest)
  - Performance: 1-5 (1=slowest)
  - Real-time capability: Y/N
  - Browser compatibility: Y/N
  - Telegram integration: Easy/Hard

Solution Comparison:
  | Solution | Time | Learn | Perf | RT | Browser | Telegram | Score |
  |----------|------|-------|------|----|---------|---------  |-------|
  | REST     | 2    | 1     | 3    | N  | Y       | Easy     | 9/15  |
  | GraphQL  | 4    | 4     | 3    | N  | Y       | Easy     | 11/15 |
  | gRPC     | 3    | 4     | 5    | Y  | N       | Hard     | 12/15 |
  | WebSocket| 3    | 3     | 4    | Y  | Y       | Medium   | 13/15 |
  | Mini App | 1    | 2     | 3    | N  | N/A     | Native   | 6/15  |
  | Hybrid   | 4    | 3     | 5    | Y  | Y       | Easy     | 15/15 |

Recommendation: Hybrid (REST + WebSocket) OR REST-only for MVP
```

**Phase 4: Resource gathering**
```markdown
Resources for Top Solutions:

REST API:
  - FastAPI docs: https://fastapi.tiangolo.com
  - Existing project: telegram_api/ (reference)
  - Skills: deployment, testing-workflow

WebSocket:
  - FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
  - Python websockets library
  - Pattern: SSE (Server-Sent Events) as simpler alternative

Hybrid:
  - Pattern: REST for CRUD, WebSocket for progress updates
  - Example architecture: [link to similar projects]
```

---

## What This Changes

### Command Workflow Transformation

**Before /research** (current):
```
User idea → /specify → Plan → Implement
  ↓
  Anchoring bias (first idea might not be best)
```

**After /research** (proposed):
```
User goal → /research (diverge) → /specify (converge) → Plan → Implement
              ↓                        ↓
         Explore ALL               Choose OPTIMAL
```

### Decision Quality Improvement

**Without /research**:
- User thinks: "I need a REST API"
- Claude: "OK, let's specify a REST API"
- Result: May miss better alternatives (GraphQL? gRPC? Hybrid?)

**With /research**:
- User thinks: "I need to expose backtester"
- Claude: "/research explores 6 approaches"
- User: "Oh, hybrid REST+WebSocket is better for real-time updates!"
- Result: Informed decision based on comprehensive exploration

---

## What Breaks

### Potential Issues

**Issue 1: Overhead for simple decisions**
```bash
# Overkill scenario
User: "Add a logout button"
/research "How to implement logout button"

# Output: 5 approaches (overkill!)
# - Approach 1: Standard button with onClick
# - Approach 2: Modal confirmation
# - Approach 3: Dropdown menu item
# - Approach 4: Keyboard shortcut
# - Approach 5: Timeout-based auto-logout
```

**Problem**: Not every decision needs divergent exploration.

**Mitigation**: Clear guidance on WHEN to use /research vs direct /specify.

---

**Issue 2: Analysis paralysis**
```bash
/research "How to implement caching"
# Returns: 12 different caching strategies

User: "Too many options, can't decide"
```

**Problem**: More options can make decision harder, not easier.

**Mitigation**: /research must rank/recommend, not just list.

---

**Issue 3: Duplication with existing commands**

**Overlap with /what-if**:
```bash
/research "How to implement caching"
# vs
/what-if "We used Redis instead of Aurora for caching"
```

Both explore alternatives, but:
- /research: Proactive (lists ALL options)
- /what-if: Reactive (compares specific alternatives)

**Overlap with Task tool (Explore agent)**:
```bash
/research "How to handle authentication"
# vs
Task tool with subagent_type=Explore: "Find authentication patterns in codebase"
```

Both explore, but:
- /research: External knowledge (web, docs, patterns)
- Explore: Internal knowledge (codebase analysis)

**Overlap with /specify**:
```bash
/research "How to implement feature X"
# Then: /specify "Feature X with approach B"

# vs (current)
/specify "Feature X with approach B (considered A, C, rejected because...)"
```

Could /specify just INCLUDE divergent exploration as first phase?

---

**Issue 4: Stale research artifacts**

```bash
# Week 1
/research "How to deploy Lambda functions"
# Output saved to: .claude/research/2025-12-18-deploy-lambda.md

# Week 4 (AWS releases new feature)
# Research artifact is now outdated

# User references old research
# Makes decision based on stale information
```

**Problem**: Research has shelf life, especially for fast-moving tech.

**Mitigation**: Timestamp research, warn if old, easy re-run.

---

## What Improves

### Benefit 1: Better decisions through comprehensive exploration

**Example scenario**:
```bash
User: "I need to add real-time updates to the backtester"

# Without /research
User: "Let's use WebSockets"
/specify "WebSocket for backtester updates"
# Implements WebSocket
# Later: "Wait, SSE (Server-Sent Events) would have been simpler"

# With /research
/research "How to implement real-time updates"
# Output:
#   - WebSocket (bidirectional, complex)
#   - SSE (unidirectional, simple)
#   - Long polling (simple, inefficient)
#   - GraphQL subscriptions (powerful, complex)
# Recommendation: SSE for this use case (server→client only)

/specify "SSE for backtester progress updates"
# Implements SSE (simpler, appropriate)
```

**Result**: Avoided over-engineering by exploring simpler alternatives.

---

### Benefit 2: Knowledge capture for future reference

**Research as reusable artifact**:
```bash
# First time
/research "How to implement caching"
# Saved: .claude/research/2025-12-24-implement-caching.md

# Later (different feature)
User: "Should we cache this?"
Claude: "See previous research: .claude/research/2025-12-24-implement-caching.md"
# Reuse analysis, faster decision
```

**Value**: Avoid re-researching same topics.

---

### Benefit 3: Learning opportunity

**Research as educational**:
```bash
/research "Authentication strategies for REST API"

# Output teaches user about:
# - JWT tokens
# - OAuth 2.0
# - API keys
# - Session cookies
# - When to use each

# User learns, makes informed choice
# Not just "do what Claude says"
```

**Value**: User understanding improves over time.

---

### Benefit 4: Reduces cognitive load

**Current** (all in user's head):
```
User must:
  1. Think of alternatives
  2. Research each one
  3. Compare trade-offs
  4. Make decision
```

**With /research** (externalized):
```
User specifies goal
  ↓
/research does exploration
  ↓
User reviews summary
  ↓
Decision made with less cognitive effort
```

**Value**: User focuses on DECIDING, not RESEARCHING.

---

## Insights Revealed

### Hidden Assumption: Specify = Diverge + Converge

**Current /specify behavior**:
```markdown
1. Receive topic (e.g., "REST API")
2. Generate detailed specification
3. Output: Single converged design
```

**Implicit**: User already did divergent exploration (chose "REST API").

**With /research**:
```markdown
1. /research: Diverge (explore ALL API styles)
2. User: Choose one (REST)
3. /specify: Converge (detail REST design)
```

**Explicit**: Separate divergent from convergent phases.

---

### Trade-off: Thoroughness vs Speed

**Without /research**:
- ✅ Fast (skip exploration, go straight to specification)
- ❌ Risk of missing better alternatives

**With /research**:
- ✅ Thorough (explore comprehensively)
- ❌ Slower (extra step before specification)

**Optimal**: Use /research for high-stakes decisions, skip for obvious ones.

---

### Boundary: When is divergence valuable?

**Valuable scenarios** (use /research):
1. **Novel problem**: "How to implement backtester?" (no precedent in codebase)
2. **High cost of error**: Architecture decisions (hard to reverse)
3. **Multiple constraints**: Performance + cost + complexity (trade-offs matter)
4. **User uncertainty**: "What are my options?" (exploration needed)

**Not valuable** (skip /research):
1. **Established patterns**: "Add CRUD endpoint" (well-known, use existing pattern)
2. **Low cost of error**: "Change button color" (easy to change)
3. **Single clear option**: "Fix bug" (no alternatives to explore)
4. **User certainty**: "Use Redis for this" (decision already made)

---

## Design Considerations

### /research Command Interface

**Proposed signature**:
```bash
/research "goal or question"
/research "goal" --focus=performance   # Filter by criteria
/research "goal" --save                # Save to .claude/research/
```

**Arguments**:
- `goal` (required): What to research (question or objective)
- `--focus` (optional): Filter solutions by criterion (performance, cost, simplicity)
- `--save` (optional): Save research artifact for future reference

---

### Output Structure

```markdown
# Research Report: {goal}

**Date**: {timestamp}
**Focus**: {criterion if specified}

---

## Problem Analysis

**Goal**: {user's goal}

**Constraints**:
- Constraint 1: {identified from context}
- Constraint 2: {identified from context}

**Success criteria**:
- Criterion 1: {what makes a good solution}
- Criterion 2: {what makes a good solution}

---

## Solution Space

### Solution 1: {Name}
**Description**: {What it is}

**Pros**:
- {Benefit 1}
- {Benefit 2}

**Cons**:
- {Limitation 1}
- {Limitation 2}

**Fit**: {Low | Medium | High}

**Precedent**: {Where it's used, examples}

**Resources**:
- {Link to docs}
- {Link to example}

---

### Solution 2: {Name}
[... same structure ...]

---

## Evaluation Matrix

| Solution | Criterion 1 | Criterion 2 | Criterion 3 | Score | Rank |
|----------|-------------|-------------|-------------|-------|------|
| Sol 1    | {rating}    | {rating}    | {rating}    | X/15  | 3    |
| Sol 2    | {rating}    | {rating}    | {rating}    | X/15  | 1    |
| Sol 3    | {rating}    | {rating}    | {rating}    | X/15  | 2    |

---

## Recommendation

**Top Choice**: {Solution 2}

**Rationale**: {Why this solution best fits constraints and criteria}

**Alternative**: {Solution 3} (if {condition})

**Not Recommended**: {Solution 1} (because {reason})

---

## Next Steps

**To proceed with top choice**:
```bash
/specify "{Solution 2} for {goal}"
```

**To explore alternative**:
```bash
/what-if "We used {Solution 3} instead of {Solution 2}"
```

**To validate assumption**:
```bash
/validate "{Claim about top choice}"
```

---

*Research generated by `/research` command*
*Saved to: .claude/research/{date}-{slug}.md (if --save flag used)*
```

---

### Integration with Existing Commands

**Workflow 1: Research → Specify → Plan**
```bash
/research "How to expose backtester functionality"
# → Recommends: REST API for MVP, hybrid for future

/specify "REST API for backtester (MVP, upgrade to hybrid later)"
# → Detailed API specification

EnterPlanMode
# → Implementation plan
```

---

**Workflow 2: Research → What-If → Specify**
```bash
/research "Caching strategies"
# → Top 2: Redis, Aurora

/what-if "We used Redis instead of Aurora for caching"
# → Compares specific trade-offs

/specify "Redis for hot data, Aurora for analytics (hybrid approach)"
```

---

**Workflow 3: Research → Validate → Specify**
```bash
/research "Database options for storing backtest results"
# → Recommends: DynamoDB (claim: scales better)

/validate "DynamoDB scales better than Aurora for our access patterns"
# → ✅ TRUE (for write-heavy workloads)

/specify "DynamoDB for backtest results storage"
```

---

## Recommendation

### Should We Implement /research?

**Decision**: ⚠️ **CONDITIONALLY YES**

---

### Rationale

**YES, because**:
1. ✅ **Fills a real gap**: No systematic divergent exploration phase currently
2. ✅ **Improves decision quality**: Reduces anchoring bias, explores comprehensively
3. ✅ **Complements existing commands**: /research diverges, /specify converges, /what-if compares
4. ✅ **Creates reusable artifacts**: Research reports can be referenced later
5. ✅ **Educational value**: Users learn about alternatives, not just "do this"

**CONDITIONALLY, because**:
1. ⚠️ **Not always needed**: Overkill for simple decisions
2. ⚠️ **Risk of duplication**: Overlaps with /specify's implicit exploration
3. ⚠️ **Analysis paralysis**: Too many options can paralyze decision-making
4. ⚠️ **Maintenance burden**: Research artifacts can become stale

---

### Conditions for Success

**Condition 1: Clear guidance on WHEN to use**

Documentation must specify:
```markdown
Use /research when:
  ✅ Novel problem (no established pattern)
  ✅ High stakes (hard to reverse decision)
  ✅ Multiple constraints (complex trade-offs)
  ✅ User uncertain (exploring options)

Skip /research when:
  ❌ Established pattern (use existing approach)
  ❌ Low stakes (easy to change later)
  ❌ Single option (no meaningful alternatives)
  ❌ User certain (decision already made)
```

---

**Condition 2: /research must RECOMMEND, not just list**

Output must include:
- ✅ Ranked solutions (best to worst)
- ✅ Clear top recommendation with rationale
- ✅ Explicit "not recommended" with reasons
- ❌ NOT just a menu of options (decision paralysis)

---

**Condition 3: Integration with /specify**

Two approaches:

**Option A: Separate commands** (your proposal):
```bash
/research "goal"    # Diverge
/specify "solution" # Converge
```

**Option B: Enhanced /specify**:
```bash
/specify "goal" --explore   # Includes divergent phase
/specify "solution"         # Direct convergence (current)
```

I recommend **Option A** (separate commands) because:
- Clearer separation of concerns (diverge vs converge)
- /research artifacts are reusable
- User explicitly opts into exploration (not default)

---

**Condition 4: Freshness indicators**

Research artifacts should:
- Include timestamp
- Warn if > 30 days old
- Easy to re-run: `/research --refresh "previous goal"`

---

### Action Items

**If implemented**:
- [ ] Create `/research` command specification
  - [ ] Define output structure (research report format)
  - [ ] Define evaluation criteria (how to rank solutions)
  - [ ] Define resource gathering (where to search)
  - [ ] Define integration points (/specify, /what-if, /validate)

- [ ] Document decision boundaries
  - [ ] When to use /research (novel, high-stakes, complex)
  - [ ] When to skip (established, low-stakes, simple)
  - [ ] Examples of each case

- [ ] Create research artifact directory
  - [ ] `.claude/research/` directory
  - [ ] README.md explaining research reports
  - [ ] Example research report

- [ ] Update command workflow documentation
  - [ ] Add /research to command flow diagrams
  - [ ] Show diverge→converge pattern
  - [ ] Update /specify to reference /research

- [ ] Test with real scenarios
  - [ ] Research architecture decisions (database choice, API style)
  - [ ] Research implementation approaches (caching, auth, deployment)
  - [ ] Validate that research improves decision quality

---

### Comparison with Similar Concepts

**vs Explore agent (Task tool)**:
- Explore: Searches CODEBASE for existing patterns
- Research: Searches EXTERNAL knowledge for potential approaches
- Complementary: Use both (internal + external exploration)

**vs /what-if**:
- What-if: REACTIVE (compares known alternatives: "A vs B")
- Research: PROACTIVE (discovers alternatives: "what are ALL options?")
- Sequential: Research discovers, what-if compares

**vs /specify --explore flag**:
- Functionally equivalent
- Separate command is clearer (explicit diverge phase)
- Produces reusable artifact (research report)

---

## Final Verdict

### ✅ **YES - Implement /research**

**Best use case**:
```bash
# User facing novel decision with high stakes
User: "I need to choose a database for storing backtest results"

# Without /research (current)
User: "Let's use DynamoDB"  # Anchored on first idea
/specify "DynamoDB for backtest results"
# Might miss that Aurora is better for analytics queries

# With /research (proposed)
/research "Database for backtest results storage"
# Output:
#   1. DynamoDB (best for write-heavy, poor for analytics)
#   2. Aurora (best for analytics, expensive for writes)
#   3. Hybrid (DynamoDB for writes, Aurora for analytics)
# Recommendation: Hybrid (optimal for this use case)

/specify "Hybrid: DynamoDB for writes, Aurora for analytics"
# Informed decision based on comprehensive exploration
```

**Value proposition**: /research prevents premature convergence by systematically exploring solution space before specifying details.

**Implementation priority**: Medium-High (fills real gap, complements existing commands)

**Alternative**: If not implementing separate /research command, enhance /specify with optional `--explore` flag for divergent phase.

---

*What-if analysis complete*
*Recommendation: CONDITIONALLY YES (with clear usage guidance)*
*Date: 2025-12-24*
