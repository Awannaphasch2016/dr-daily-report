---
name: explore
description: Systematically explore ALL potential solutions before committing - divergent phase that generates, evaluates, and ranks alternatives with objective criteria
accepts_args: true
arg_schema:
  - name: goal
    required: true
    description: "Problem statement or question to explore (quoted if spaces)"
  - name: focus
    required: false
    description: "Optional focus criterion: performance, cost, simplicity, or maintainability (weighted 2x in scoring)"
composition: []
---

# /explore - Divergent Solution Exploration

**Status**: Active
**Category**: Decision Making
**Phase**: Divergent (explores ALL potential solutions)
**Pairs with**: `/specify` (convergent phase)

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `divergent`

When `/explore` executes as a mode within a Strategy pipeline:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **EXPAND**: Adds discovered alternatives, resources, patterns |
| **Invariant** | **NONE**: Does not modify success criteria |
| **Principles** | **ADD**: May discover domain-specific heuristics |
| **Strategy** | Consumes this mode; may suggest follow-up modes |
| **Check** | Evaluates coverage criteria (see Local Check) |

**Constraint Expansion Examples**:
```yaml
before:
  constraints:
    problem: "How to cache computed metrics"
    known: []

after:
  constraints:
    problem: "How to cache computed metrics"
    known:
      - "Option 1: Redis (sub-ms latency, new infrastructure)"
      - "Option 2: DynamoDB (already in use, 2-5ms latency)"
      - "Option 3: S3 + CloudFront (cost-effective, higher latency)"
      - "Option 4: In-memory (fastest, no persistence)"
    heuristics_discovered:
      - "Prefer existing infrastructure unless latency is critical"
```

---

## Local Check (Mode Completion Criteria)

The `/explore` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Coverage** | ≥3 viable alternatives identified |
| **Diversity** | Options span different approaches (not variants of same) |
| **Evaluation** | Scoring matrix completed with rationale |
| **Ranking** | Top choice identified with clear rationale |
| **Resources** | Authoritative sources gathered for each option |
| **Next Step** | Clear path to `/specify` or `/what-if` |

**Check Result Mapping**:
- **PASS**: All criteria satisfied → proceed to next mode
- **PARTIAL**: Some criteria missing → extend with more exploration
- **FAIL**: Unable to find viable alternatives → consider `/reframe`

---

## Purpose

Systematically explore the solution space BEFORE committing to a specific approach. Prevents anchoring bias by generating, evaluating, and ranking multiple alternatives with objective criteria.

**Use this command when**:
- Multiple valid approaches exist (architecture, library choice, API design)
- Decision has significant impact (cost, performance, maintainability)
- Novel problem domain (no obvious best practice)
- Exploring trade-offs between competing priorities

**Skip this command when**:
- Only one viable approach exists
- Best practice is well-established
- Decision is easily reversible
- Time-sensitive tactical fix

---

## Usage

```bash
/research "goal or problem to solve"
/research "goal" --focus=performance
/research "goal" --focus=cost
/research "goal" --focus=simplicity
```

### Arguments

- `goal` (required): Problem statement or question to research
- `--focus` (optional): Filter criterion (performance, cost, simplicity, maintainability)

### Examples

```bash
# Architecture decision
/research "How to expose backtester functionality to users"

# Library selection
/research "Which chart library for Telegram Mini App" --focus=performance

# API design
/research "How to handle real-time price updates in frontend"

# Infrastructure
/research "Where to store historical price data" --focus=cost

# Pattern selection
/research "How to manage global state in React" --focus=simplicity
```

### Online Tool Discovery Examples

```bash
# Find logging/monitoring services
/explore "Which logging service for production monitoring" --focus=cost
→ Compares: Datadog ($15/host/mo), New Relic ($25/host/mo), CloudWatch ($0.50/GB), Langfuse (free)
→ Evaluates: Features, pricing tiers, integration effort, AWS native vs third-party

# Find payment processors
/explore "Payment gateway for subscription billing"
→ Analyzes: Stripe (2.9% + $0.30), PayPal (3.5%), Braintree (2.9% + $0.30)
→ Compares: Recurring billing features, webhook reliability, API quality

# Find CDN providers
/explore "CDN for static asset delivery" --focus=performance
→ Evaluates: CloudFront (AWS native), Cloudflare (free tier), Fastly (edge compute)
→ Benchmarks: Latency by region, cache hit rates, purge speed
```

### Codebase Discovery Examples

```bash
# Discover existing patterns
/explore "How do we currently handle database connections"
→ Searches: src/ for connection pooling patterns
→ Finds: PyMySQL + RDS Proxy pattern in src/services/aurora.py
→ Documents: Current approach (connection per request vs pooling)

# Find integrated tools
/explore "What error monitoring tools are we using"
→ Searches: Import statements for monitoring libraries
→ Finds: Langfuse integration in src/report/ for LLM observability
→ Output: Current Langfuse setup, usage patterns, scoring dimensions

# Discover CLI commands
/explore "What CLI commands exist for deployment"
→ Searches: Justfile recipes, dr_cli/commands/deploy.py
→ Documents: `dr deploy dev`, `dr deploy staging`, `dr deploy prod`
→ Shows: Two-layer design (Justfile = intent, dr CLI = implementation)
```

### Hybrid Discovery (Online + Codebase)

```bash
# Compare current vs alternatives
/explore "Should we switch from OpenAI to Anthropic Claude"
→ Step 1: Analyzes current OpenAI usage (grep for 'openai' imports)
→ Step 2: Finds: GPT-4 for reports, tiktoken for token counting
→ Step 3: Compares alternatives:
  - OpenAI GPT-4: $0.03/1K tokens (current), 8K context, function calling
  - Anthropic Claude 3: $0.015/1K tokens, 100K context, XML preferred
  - Cost delta: ~50% savings but migration effort ~20 hours
→ Recommendation: Stay with OpenAI (migration cost > savings for current usage)

# Evaluate adoption of new tool
/explore "Add Redis for caching vs use DynamoDB"
→ Analyzes: Current DynamoDB usage for caching (src/cache/)
→ Compares:
  - Redis: Faster (sub-ms), more features, but new infrastructure
  - DynamoDB: Already in use, serverless, familiar to team
→ Trade-off: 2-5ms latency difference vs operational simplicity
→ Recommendation: DynamoDB unless latency becomes bottleneck
```

### Anti-Patterns to Avoid

```markdown
### ❌ Don't Use /explore For

**Simple lookups** (information readily available):
```bash
# Bad
/explore "What is Docker?"
# Good
Just ask: "What is Docker?" (no exploration needed, factual question)
```

**Answers already in docs**:
```bash
# Bad
/explore "What CLI commands exist?"
# Good
Read docs/cli.md or run `dr --help` (documented information)
```

**Single option** (no alternatives to compare):
```bash
# Bad
/explore "Should we use AWS Lambda?" (already decided by architecture)
# Good
Only use /explore when genuinely exploring multiple alternatives
```

**Trivial decisions** (easily reversible):
```bash
# Bad
/explore "Should this variable be named 'user_id' or 'userId'?"
# Good
Just pick one (low impact, easy to change later)
```

**When you already know the answer**:
```bash
# Bad
/explore "Best practice for password hashing" (industry consensus: bcrypt/argon2)
# Good
Use established best practice without exploration
```
```

---

## Output

Generates research document saved to `.claude/research/{date}-{slug}.md`:

```markdown
# Research: {Goal}

**Date**: 2025-12-24
**Focus**: {criterion or "comprehensive"}
**Status**: Complete

## Problem Decomposition

{Break down goal into components}

## Solution Space (Divergent Phase)

### Option 1: {Name}
**Description**: ...
**Pros**: ...
**Cons**: ...
**Examples**: ...
**Resources**: [link], [link]

### Option 2: {Name}
...

{Continue for all viable alternatives}

## Evaluation Matrix

| Criterion | Option 1 | Option 2 | Option 3 | Option 4 |
|-----------|----------|----------|----------|----------|
| Performance | 8/10 | 6/10 | 9/10 | 7/10 |
| Cost | 5/10 | 9/10 | 3/10 | 7/10 |
| Complexity | 7/10 | 8/10 | 4/10 | 6/10 |
| Maintainability | 6/10 | 7/10 | 8/10 | 9/10 |
| **Total** | **26** | **30** | **24** | **29** |

## Ranked Recommendations

### 1. {Top Choice} (Score: XX/40)
**Why**: {Clear rationale}
**Trade-offs**: {What you gain/lose}
**Next step**: `/specify "{Top Choice}"`

### 2. {Second Choice} (Score: XX/40)
**When to choose**: {Conditions where this is better}

### 3. {Third Choice} (Score: XX/40)
**When to choose**: {Conditions where this is better}

## Resources Gathered

- [Documentation] - {URL}
- [Example Implementation] - {URL}
- [Comparison Article] - {URL}
- [Community Discussion] - {URL}

## Next Steps

```bash
# Recommended: Converge on top choice
/specify "{Top Choice from research}"

# Alternative: Compare top 2 choices
/what-if "compare {Option 1} vs {Option 2}"

# Optional: Validate assumptions
/validate "hypothesis: {Top Choice} will meet {criterion}"
```
```

---

## Implementation

### Phase 1: Problem Decomposition

```bash
# Break down the research goal into components
echo "# Research: $GOAL" > "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "## Problem Decomposition" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Decompose goal into:
# - Core requirements (what MUST the solution provide?)
# - Constraints (what limits exist? budget, time, technology)
# - Success criteria (how will we measure success?)
# - Stakeholders (who cares about this decision?)
```

**Example decomposition**:
```
Goal: "How to expose backtester functionality to users"

Core requirements:
- Execute backtest with custom parameters
- Return historical performance metrics
- Support multiple ticker inputs
- Handle long-running computations

Constraints:
- Must integrate with existing Telegram Mini App
- Response time < 5 seconds for simple backtests
- Cost per backtest < $0.01
- No additional infrastructure if possible

Success criteria:
- Users can run backtest from UI
- Results displayed within acceptable latency
- System remains responsive during computation
- Errors communicated clearly

Stakeholders:
- End users (want simplicity)
- Backend team (want maintainability)
- DevOps (want reliability)
```

---

### Phase 2: Solution Space Exploration (Divergent)

```bash
# Generate ALL viable alternatives
# Don't filter yet - cast wide net

echo "## Solution Space (Divergent Phase)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# For each potential solution:
# 1. Name and brief description
# 2. How it works (technical approach)
# 3. Pros (strengths, benefits)
# 4. Cons (weaknesses, risks)
# 5. Real-world examples (who uses this?)
# 6. Resource links (docs, tutorials)
```

**Exploration strategies**:

1. **Pattern-based**: What patterns solve similar problems?
   - REST API (request/response)
   - GraphQL (query language)
   - WebSocket (bidirectional)
   - Server-Sent Events (unidirectional)
   - Hybrid (combine patterns)

2. **Technology-based**: What technologies are available?
   - Synchronous (Lambda)
   - Asynchronous (Step Functions)
   - Queue-based (SQS + worker)
   - Streaming (Kinesis)

3. **Architecture-based**: What architectures apply?
   - Monolithic (single service)
   - Microservices (separate service)
   - Serverless (event-driven)
   - Hybrid (mix approaches)

4. **Precedent-based**: How do others solve this?
   - Industry leaders (what does Google/AWS/Meta do?)
   - Open source projects (established patterns)
   - Community recommendations (Stack Overflow, Reddit)

---

### Phase 3: Evaluation Matrix

```bash
# Define evaluation criteria (adjust based on --focus)
CRITERIA=(
  "Performance:How fast/scalable is it?"
  "Cost:Ongoing operational cost"
  "Complexity:Implementation difficulty"
  "Maintainability:Ease of updates/debugging"
)

# Score each option (1-10 scale)
# Document rationale for each score

echo "## Evaluation Matrix" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "| Criterion | Opt1 | Opt2 | Opt3 | Opt4 |" >> "$RESEARCH_FILE"
echo "|-----------|------|------|------|------|" >> "$RESEARCH_FILE"
```

**Scoring guidelines**:

- **Performance** (1-10)
  - 1-3: Slow, doesn't scale, high latency
  - 4-6: Adequate, moderate scalability
  - 7-10: Fast, horizontally scalable, low latency

- **Cost** (1-10)
  - 1-3: Expensive (>$100/mo for expected usage)
  - 4-6: Moderate ($10-100/mo)
  - 7-10: Cheap (<$10/mo or free tier)

- **Complexity** (1-10)
  - 1-3: Very complex, many components, steep learning curve
  - 4-6: Moderate complexity, some new concepts
  - 7-10: Simple, uses existing skills/patterns

- **Maintainability** (1-10)
  - 1-3: Hard to debug, brittle, unclear error states
  - 4-6: Debuggable with effort, some edge cases
  - 7-10: Easy to debug, clear errors, well-documented

**Focus modifiers** (when `--focus` specified):

```bash
if [[ "$FOCUS" == "performance" ]]; then
  # Weight performance 2x
  PERF_WEIGHT=2
else
  PERF_WEIGHT=1
fi

TOTAL_SCORE=$((PERF * PERF_WEIGHT + COST + COMPLEXITY + MAINT))
```

---

### Phase 4: Resource Gathering

```bash
# Collect documentation, examples, discussions
echo "## Resources Gathered" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# For each option, gather:
# - Official documentation (authoritative source)
# - Example implementations (real code)
# - Comparison articles (pros/cons analysis)
# - Community discussions (lessons learned)
```

**Resource quality tiers**:

1. **Tier 1 (Primary sources)**:
   - Official documentation
   - API references
   - Canonical examples from maintainers

2. **Tier 2 (Validated secondary)**:
   - Production case studies
   - Published benchmarks
   - Conference talks from practitioners

3. **Tier 3 (Community)**:
   - Stack Overflow accepted answers
   - Blog posts from recognized experts
   - GitHub discussions with maintainer input

**Anti-pattern**: Don't include random blog posts, Reddit comments, or outdated tutorials (>2 years old unless still maintained)

---

### Phase 5: Ranked Recommendations

```bash
# Sort by total score
# Provide clear rationale for top choice

echo "## Ranked Recommendations" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# For each option (sorted by score):
echo "### 1. {Option Name} (Score: XX/40)" >> "$RESEARCH_FILE"
echo "**Why**: {Rationale}" >> "$RESEARCH_FILE"
echo "**Trade-offs**: {What you gain vs lose}" >> "$RESEARCH_FILE"
echo "**When to choose**: {Conditions}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
```

**Top choice rationale template**:

```markdown
### 1. Hybrid REST + WebSocket (Score: 34/40)

**Why**:
- Best balance of performance (WebSocket for real-time) and simplicity (REST for CRUD)
- Proven pattern for financial apps requiring live updates
- Leverages existing FastAPI backend (no new infrastructure)
- Graceful degradation (REST works even if WebSocket fails)

**Trade-offs**:
- Slightly more complex than pure REST (2 protocols to maintain)
- WebSocket connection management adds overhead
- BUT: Complexity is localized to real-time features only

**When to choose**:
- Real-time updates are core requirement
- Willing to accept moderate complexity for better UX
- Already have REST API (incremental addition)

**When NOT to choose**:
- Don't need real-time updates
- Simplicity is paramount
- Team lacks WebSocket experience
```

---

## Integration with Other Commands

### Sequential workflow (recommended)

```bash
# Step 1: Diverge (explore all options)
/research "How to expose backtester functionality"
# → Output: research/2025-12-24-backtester-api.md
# → Top choice: Hybrid REST + WebSocket

# Step 2: Converge (specify chosen approach)
/specify "Hybrid REST + WebSocket API for backtester"
# → Output: specifications/2025-12-24-backtester-hybrid-api.md
# → Detailed design with endpoints, schemas, error handling

# Step 3: Plan (break down implementation)
EnterPlanMode
# → Create step-by-step implementation plan

# Step 4: Validate (test assumptions)
/validate "hypothesis: WebSocket latency < 100ms for price updates"
```

### Alternative workflows

**When top 2 choices are close**:
```bash
/research "State management for Telegram Mini App"
# → Top 2: Zustand (32/40) vs Redux (30/40)

/what-if "compare Zustand vs Redux for our use case"
# → Deeper comparison of top candidates
```

**When validating assumptions**:
```bash
/research "Where to store historical price data"
# → Top choice: S3 with Athena

/validate "hypothesis: Athena query cost < $0.01 per backtest"
# → Test assumption before committing
```

**When decision is time-sensitive**:
```bash
# Skip /research if:
# - Production incident (use established patterns)
# - Obvious best practice exists
# - Decision easily reversible

# Go directly to:
/specify "Use existing REST pattern for new endpoint"
```

---

## Decision Criteria: When to Use /research

### ✅ USE /research when:

1. **Multiple viable alternatives exist**
   - Example: REST vs GraphQL vs WebSocket vs Hybrid
   - Why: Need objective comparison

2. **Decision has significant impact**
   - Example: Database choice (Aurora vs DynamoDB vs PostgreSQL)
   - Why: Reversal is expensive (migration cost, downtime)

3. **Novel problem domain**
   - Example: "How to implement real-time collaborative editing"
   - Why: No established best practice in codebase

4. **Exploring trade-offs**
   - Example: "Performance vs cost vs complexity for caching"
   - Why: Need explicit evaluation of competing priorities

5. **Team alignment needed**
   - Example: "Frontend framework for new project"
   - Why: Research document becomes decision record

### ❌ SKIP /research when:

1. **Only one viable option**
   - Example: "Must use AWS Lambda" (dictated by architecture)
   - Why: No alternatives to explore

2. **Best practice well-established**
   - Example: "Use bcrypt for password hashing"
   - Why: Industry consensus exists

3. **Decision easily reversible**
   - Example: "Should this function be async?"
   - Why: Can change with minimal cost

4. **Time-sensitive tactical fix**
   - Example: Production incident requiring hotfix
   - Why: Speed matters more than optimization

5. **Micro-decision with local scope**
   - Example: "Variable name for user ID"
   - Why: Low impact, high cost to research

---

## Research Quality Checklist

Before completing research, verify:

- [ ] **Completeness**: Explored ALL major alternatives (not just familiar ones)
- [ ] **Objectivity**: Scored based on criteria, not gut feeling
- [ ] **Evidence**: Each score backed by facts (benchmarks, examples, docs)
- [ ] **Resources**: Included authoritative sources (official docs, case studies)
- [ ] **Rationale**: Top choice has clear "why" explanation
- [ ] **Trade-offs**: Explicitly stated what you gain vs lose
- [ ] **Conditions**: Specified when to choose alternative options
- [ ] **Next steps**: Clear path to `/specify` or `/what-if`

---

## Example Research Documents

### Example 1: API Design

**Goal**: "How to expose backtester functionality to users"

**Options explored**:
1. Synchronous REST (simple, but blocks)
2. Async REST with polling (scalable, but complex)
3. WebSocket only (real-time, but overkill)
4. Hybrid REST + WebSocket (balanced)
5. Queue-based with webhooks (decoupled, but adds infrastructure)

**Evaluation matrix**:
| Criterion | Sync REST | Async+Poll | WS Only | Hybrid | Queue+Webhook |
|-----------|-----------|------------|---------|--------|---------------|
| Performance | 4/10 | 7/10 | 9/10 | 8/10 | 7/10 |
| Cost | 9/10 | 7/10 | 8/10 | 8/10 | 5/10 |
| Complexity | 9/10 | 6/10 | 7/10 | 7/10 | 4/10 |
| Maintainability | 8/10 | 6/10 | 6/10 | 7/10 | 5/10 |
| **Total** | **30** | **26** | **30** | **30** | **21** |

**Top choice**: Hybrid REST + WebSocket
- **Why**: Balanced performance + simplicity, leverages existing FastAPI
- **Trade-off**: Slightly more complex than pure REST, but enables real-time updates
- **Next**: `/specify "Hybrid REST + WebSocket API for backtester"`

---

### Example 2: State Management

**Goal**: "Which state management library for Telegram Mini App"

**Options explored**:
1. React Context (built-in, simple)
2. Zustand (lightweight, hooks-based)
3. Redux Toolkit (powerful, verbose)
4. Jotai (atomic, learning curve)
5. MobX (reactive, magic)

**Focus**: Simplicity (weighted 2x)

**Evaluation matrix**:
| Criterion | Context | Zustand | Redux | Jotai | MobX |
|-----------|---------|---------|-------|-------|------|
| Performance | 6/10 | 8/10 | 7/10 | 8/10 | 9/10 |
| Bundle Size | 10/10 | 9/10 | 7/10 | 9/10 | 6/10 |
| Complexity (2x) | 9/10 (18) | 8/10 (16) | 5/10 (10) | 6/10 (12) | 4/10 (8) |
| Maintainability | 7/10 | 8/10 | 9/10 | 7/10 | 6/10 |
| **Total** | **41** | **41** | **33** | **36** | **29** |

**Top choice**: Zustand (tie with Context, but better performance)
- **Why**: Best balance of simplicity + performance, hooks-based (familiar)
- **Trade-off**: Adds 1KB to bundle vs Context (negligible)
- **Next**: `/specify "Zustand state management for Telegram Mini App"`

---

## Implementation Script

```bash
#!/bin/bash

# /research implementation
GOAL="$1"
FOCUS="${2:-comprehensive}"  # performance, cost, simplicity, or comprehensive

# Validate input
if [[ -z "$GOAL" ]]; then
  echo "❌ Usage: /research \"goal or problem to solve\""
  echo ""
  echo "Examples:"
  echo "  /research \"How to expose backtester functionality\""
  echo "  /research \"State management library\" --focus=simplicity"
  exit 1
fi

# Generate filename
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "$GOAL" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
RESEARCH_FILE=".claude/research/${DATE}-${SLUG}.md"

# Ensure directory exists
mkdir -p .claude/research

# Generate research document
echo "# Research: $GOAL" > "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Date**: $DATE" >> "$RESEARCH_FILE"
echo "**Focus**: $FOCUS" >> "$RESEARCH_FILE"
echo "**Status**: In Progress" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Phase 1: Problem Decomposition
echo "## Problem Decomposition" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Goal**: $GOAL" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Core Requirements**:" >> "$RESEARCH_FILE"
echo "- [ ] {What MUST the solution provide?}" >> "$RESEARCH_FILE"
echo "- [ ] {What are non-negotiable features?}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Constraints**:" >> "$RESEARCH_FILE"
echo "- Budget: {Cost limits?}" >> "$RESEARCH_FILE"
echo "- Time: {Deadline?}" >> "$RESEARCH_FILE"
echo "- Technology: {Required stack?}" >> "$RESEARCH_FILE"
echo "- Team: {Skills available?}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Success Criteria**:" >> "$RESEARCH_FILE"
echo "- [ ] {How will we measure success?}" >> "$RESEARCH_FILE"
echo "- [ ] {What metrics matter?}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Stakeholders**:" >> "$RESEARCH_FILE"
echo "- End users: {What do they care about?}" >> "$RESEARCH_FILE"
echo "- Development team: {What do they care about?}" >> "$RESEARCH_FILE"
echo "- DevOps: {What do they care about?}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Phase 2: Solution Space
echo "## Solution Space (Divergent Phase)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "### Option 1: {Name}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Description**: {Brief overview}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**How it works**:" >> "$RESEARCH_FILE"
echo "{Technical approach}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Pros**:" >> "$RESEARCH_FILE"
echo "- {Strength 1}" >> "$RESEARCH_FILE"
echo "- {Strength 2}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Cons**:" >> "$RESEARCH_FILE"
echo "- {Weakness 1}" >> "$RESEARCH_FILE"
echo "- {Weakness 2}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Examples**:" >> "$RESEARCH_FILE"
echo "- {Company/project using this}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Resources**:" >> "$RESEARCH_FILE"
echo "- [Documentation](URL)" >> "$RESEARCH_FILE"
echo "- [Example Implementation](URL)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Repeat for additional options (template shows 1, actual research should have 3-5)

# Phase 3: Evaluation Matrix
echo "## Evaluation Matrix" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
if [[ "$FOCUS" != "comprehensive" ]]; then
  echo "**Focus**: $FOCUS (weighted 2x)" >> "$RESEARCH_FILE"
  echo "" >> "$RESEARCH_FILE"
fi
echo "| Criterion | Option 1 | Option 2 | Option 3 | Option 4 |" >> "$RESEARCH_FILE"
echo "|-----------|----------|----------|----------|----------|" >> "$RESEARCH_FILE"
echo "| Performance | ?/10 | ?/10 | ?/10 | ?/10 |" >> "$RESEARCH_FILE"
echo "| Cost | ?/10 | ?/10 | ?/10 | ?/10 |" >> "$RESEARCH_FILE"
echo "| Complexity | ?/10 | ?/10 | ?/10 | ?/10 |" >> "$RESEARCH_FILE"
echo "| Maintainability | ?/10 | ?/10 | ?/10 | ?/10 |" >> "$RESEARCH_FILE"
echo "| **Total** | **?** | **?** | **?** | **?** |" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Scoring rationale**:" >> "$RESEARCH_FILE"
echo "{Explain why each score was assigned}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Phase 4: Resources
echo "## Resources Gathered" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Official Documentation**:" >> "$RESEARCH_FILE"
echo "- [Link](URL)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Example Implementations**:" >> "$RESEARCH_FILE"
echo "- [Link](URL)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Comparison Articles**:" >> "$RESEARCH_FILE"
echo "- [Link](URL)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Community Discussions**:" >> "$RESEARCH_FILE"
echo "- [Link](URL)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Phase 5: Recommendations
echo "## Ranked Recommendations" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "### 1. {Top Choice} (Score: XX/40)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Why**: {Clear rationale for this choice}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Trade-offs**:" >> "$RESEARCH_FILE"
echo "- Gain: {What you get}" >> "$RESEARCH_FILE"
echo "- Lose: {What you sacrifice}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**When to choose**: {Conditions where this is optimal}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**Next step**:" >> "$RESEARCH_FILE"
echo "\`\`\`bash" >> "$RESEARCH_FILE"
echo "/specify \"{Top Choice}\"" >> "$RESEARCH_FILE"
echo "\`\`\`" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "### 2. {Second Choice} (Score: XX/40)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**When to choose**: {Conditions where this might be better}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "### 3. {Third Choice} (Score: XX/40)" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "**When to choose**: {Conditions where this might be better}" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "---" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"

# Next Steps
echo "## Next Steps" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "\`\`\`bash" >> "$RESEARCH_FILE"
echo "# Recommended: Converge on top choice" >> "$RESEARCH_FILE"
echo "/specify \"{Top Choice from research}\"" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "# Alternative: Compare top 2 choices" >> "$RESEARCH_FILE"
echo "/what-if \"compare {Option 1} vs {Option 2}\"" >> "$RESEARCH_FILE"
echo "" >> "$RESEARCH_FILE"
echo "# Optional: Validate assumptions" >> "$RESEARCH_FILE"
echo "/validate \"hypothesis: {Top Choice} will meet {criterion}\"" >> "$RESEARCH_FILE"
echo "\`\`\`" >> "$RESEARCH_FILE"

echo "✅ Research template created: $RESEARCH_FILE"
echo ""
echo "Next: Fill in the research sections with actual alternatives and analysis"
```

---

## Anti-Patterns to Avoid

### ❌ Shallow Research (The Checklist)
```markdown
## Options
1. REST - Simple
2. GraphQL - Complex
3. WebSocket - Real-time

Winner: REST (it's simple!)
```

**Why bad**: No actual exploration, anchored on first idea, no evaluation

**Fix**: Explore each option deeply, score objectively, explain rationale

---

### ❌ Analysis Paralysis (The Thesis)
```markdown
## Options
{50 pages analyzing every possible approach}
{6 months later, still researching}
```

**Why bad**: Research becomes goal instead of decision input

**Fix**: Time-box research (1-2 hours), limit to 3-5 viable options, make decision

---

### ❌ Confirmation Bias (The Predetermined Outcome)
```markdown
## Options
1. My preferred solution - 10/10 everything
2. Alternative I don't like - 2/10 everything

Winner: My solution!
```

**Why bad**: Research is theater, decision already made

**Fix**: Invite critiques of preferred solution, steelman alternatives

---

### ❌ Technology Resume (The Shiny Object)
```markdown
Winner: New framework X because:
- It's trending on HackerNews
- Uses cool technology Y
- Would be fun to learn
```

**Why bad**: Optimizes for learning, not business value

**Fix**: Optimize for project success criteria (performance, cost, maintainability)

---

## Success Metrics

Research is successful when:

- [ ] Generated 3-5 viable alternatives (not just obvious + strawman)
- [ ] Evaluation matrix completed with rationale for each score
- [ ] Top choice has clear "why" explanation with trade-offs
- [ ] Resources gathered include authoritative sources
- [ ] Next step is clear (`/specify` or `/what-if`)
- [ ] Research completed in 1-2 hours (not days/weeks)
- [ ] Team can understand decision from document alone

---

## Integration Examples

### Sequential: Research → Specify → Plan → Implement

```bash
# Step 1: Diverge (explore all options)
/research "How to implement real-time price updates in Telegram Mini App"

# Output: research/2025-12-24-realtime-prices.md
# Top choice: Server-Sent Events (SSE)
# Score: 34/40
# Why: Simpler than WebSocket, better than polling, native browser support

# Step 2: Converge (detail chosen approach)
/specify "Server-Sent Events (SSE) for real-time price updates"

# Output: specifications/2025-12-24-sse-price-updates.md
# Details: Endpoint design, reconnection logic, fallback strategy

# Step 3: Plan implementation
EnterPlanMode
# Creates step-by-step plan

# Step 4: Implement
{Work through plan}
```

---

### Parallel: Research Multiple Decisions

```bash
# Research infrastructure decisions in parallel
/research "Where to store historical price data"
/research "How to cache computed metrics"
/research "Which chart library for Telegram Mini App"

# Each generates independent research document
# Can be done in parallel by different team members
```

---

### Iterative: Research → What-If → Validate

```bash
# Initial research
/research "State management for Telegram Mini App"

# Top 2 are close: Zustand (32/40) vs Redux (30/40)
# Need deeper comparison

/what-if "use Zustand vs Redux for our specific use case"

# What-if analysis recommends Zustand
# But has assumption: "Zustand bundle size < 5KB"

/validate "hypothesis: Zustand bundle size is < 5KB gzipped"

# Validation confirms assumption
# Proceed with /specify "Zustand state management"
```

---

## Command Relationships

```
                    /research (diverge)
                         |
                         v
              +----------+----------+
              |                     |
        /what-if              /validate
      (compare top 2)      (test assumptions)
              |                     |
              +----------+----------+
                         |
                         v
                  /specify (converge)
                         |
                         v
                  EnterPlanMode
                         |
                         v
                    Implement
```

**Decision flow**:
1. `/research` - Explore solution space, rank options
2. `/what-if` (optional) - Deep dive on top candidates
3. `/validate` (optional) - Test critical assumptions
4. `/specify` - Converge on detailed design
5. `EnterPlanMode` - Break down implementation
6. Implement - Execute plan

---

## Maintenance

Update this command when:
- New evaluation criteria emerge (e.g., "security", "accessibility")
- New research strategies discovered (e.g., "performance-based", "compliance-based")
- Integration points change (new commands added to system)
- Anti-patterns identified from actual usage

**Owner**: Project architect
**Last updated**: 2025-12-24
