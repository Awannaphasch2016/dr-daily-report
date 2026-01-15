# Claude Code Slash Commands

**Explicit orchestration layer for composable workflows.**

Slash commands provide direct user control over Claude's behavior by composing skills, other commands, and scripts into powerful multi-stage pipelines.

---

## Commands vs Skills

| Feature | Commands | Skills |
|---------|----------|--------|
| **Invocation** | Explicit (`/command-name`) | Auto-discovered by Claude |
| **Purpose** | Orchestration & workflow composition | Domain expertise |
| **User Control** | High - you decide when to use | Low - Claude decides |
| **Composition** | Can chain skills, commands, scripts | Cannot compose (referenced by commands) |
| **Arguments** | Accepts structured arguments | Uses conversation context |

**Think of it this way:**
- **Skills** = Tools in Claude's toolbox (auto-selected when relevant)
- **Commands** = Recipes that combine multiple tools in sequence

---

## Command Taxonomy (Naming Convention)

Commands are organized by their **relationship to existing state**:

### Inspection Commands (Reveal Existing)
Metaphor names that imply looking inside without modifying:
- `/x-ray` - Deep structural inspection of existing systems
- `/validate` - Verify claims about current state
- `/locate` - Find where functionality lives
- `/qna` - Reveal Claude's understanding and knowledge gaps

### Analysis Commands (Think About Existing)
Analysis names that imply reasoning about what exists:
- `/analysis` - Comprehensive analysis workflow
- `/what-if` - Counterfactual exploration
- `/impact` - Assess change scope
- `/trace` - Follow causality chains

### Design Commands (Create New)
Action verbs that imply producing something new:
- `/design` - Domain-aware thorough design
- `/specify` - Quick design sketches (exploratory)
- `/feature` - Contractual feature specification (persistent)
- `/explore` - Divergent option generation
- `/adapt` - Integrate external techniques

### Protocol Commands (Runtime Composition)
Commands that force structured reasoning protocols:
- `/step` - Thinking Tuple Protocol (Constraints → Invariant → Principles → Process → Actions → Check)
- `/invariant` - Identify behavioral invariants for a goal
- `/reconcile` - Converge violations back to compliance

**Workflow pattern:**
```bash
/x-ray "current auth system"     # SEE what exists
/what-if "OAuth instead of JWT"  # THINK about alternatives
/design python "OAuth2 handler"  # CREATE new solution
/step "deploy OAuth handler"     # EXECUTE with disciplined reasoning
```

---

## Available Commands

### `/journal` - Log Decisions with Smart Categorization
**Purpose**: Capture architectural decisions, bug solutions, patterns, and process improvements with automatic category detection from title/content keywords

**Usage**:
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

**Categories**:
- `architecture` - Pre-ADR exploration, design decisions
- `error` - Bug investigations and solutions
- `pattern` - Reusable code or workflow patterns
- `meta` - Process improvements, tooling enhancements

---

### `/validate` - Validate Claims with Evidence
**Purpose**: Validate claims and assumptions with evidence before implementing features or making decisions

**Usage**:
```bash
/validate "All Lambda functions have < 5s timeout"
/validate "Users rarely use the export feature" behavior
/validate "Performance regression caused by new database query" hypothesis
```

**Validation types** (auto-detected):
- `code` - Code structure validation (functions, imports, patterns)
- `performance` - Latency thresholds, resource usage
- `config` - Environment variables, infrastructure state
- `behavior` - User preferences, system patterns
- `hypothesis` - Root cause hypotheses, causal relationships

**Output**:
- Status: ✅ TRUE | ❌ FALSE | ⚠️ PARTIALLY TRUE | 🤔 INCONCLUSIVE
- Evidence summary (supporting, contradicting, missing)
- Analysis with confidence level
- Recommendations based on validation result

**Core Principle**: "Validate assumptions before implementing" - evidence-based decision making prevents wasted effort

---

### `/proof` - Formal Deductive Proofs
**Purpose**: Construct formal proofs about system properties from constraints and axioms

**Usage**:
```bash
# Capacity planning
/proof "Lambda with 512MB can process 100MB images"

# Type safety
/proof "All API endpoints return JSON-serializable data"

# Resource management
/proof "All database connections are properly closed"

# Save proof document
/proof "System can handle 1000 req/s" save
```

**Proof types** (auto-detected):
- `direct` - Given axioms → derive conclusion
- `contradiction` - Assume opposite → find contradiction
- `counterexample` - Find case that violates property
- `construction` - Build explicit example
- `induction` - Base case + inductive step

**Output**: Formal proof structure with axioms, derivation steps, conclusion, and QED

**Core Principle**: "What MUST be true given constraints?" - deductive reasoning complements empirical validation

---

## Exploration Commands

### `/explore` - Divergent Solution Exploration
**Purpose**: Systematically explore ALL potential solutions before committing to an approach. Prevents anchoring bias by generating, evaluating, and ranking alternatives with objective criteria.

**Usage**:
```bash
# Comprehensive exploration
/explore "How to expose backtester functionality to users"

# Focused exploration (weighted criterion)
/explore "Which chart library for Telegram Mini App" --focus=performance
/explore "Where to store historical price data" --focus=cost
/explore "How to manage global state in React" --focus=simplicity
```

**When to use**:
- Multiple valid approaches exist (architecture, library choice, API design)
- Decision has significant impact (cost, performance, maintainability)
- Novel problem domain (no obvious best practice)
- Exploring trade-offs between competing priorities

**When to skip**:
- Only one viable approach exists
- Best practice is well-established
- Decision is easily reversible
- Time-sensitive tactical fix

**Output**: Exploration document at `.claude/explorations/{date}-{slug}.md` including:
- Problem decomposition (requirements, constraints, stakeholders)
- Solution space (3-5 alternatives with pros/cons)
- Evaluation matrix (scored by performance, cost, complexity, maintainability)
- Ranked recommendations (top choice with clear rationale)
- Resources gathered (docs, examples, case studies)
- Next steps (`/specify` top choice or `/what-if` to compare)

**Workflow**: Diverge → Converge
```bash
# Step 1: Diverge (explore all options)
/explore "How to implement real-time price updates"
# → Output: explorations/2025-12-25-realtime-prices.md
# → Top choice: Server-Sent Events (SSE)

# Step 2: Converge (specify chosen approach)
/specify "Server-Sent Events (SSE) for real-time price updates"
# → Output: specifications/2025-12-25-sse-price-updates.md

# Step 3: Plan and implement
EnterPlanMode
```

**Core Principle**: "Explore before committing" - systematic exploration prevents anchoring on first idea and reveals better alternatives

---

### `/what-if` - Comprehensive Comparison Command
**Purpose**: Compare alternatives, explore scenarios, and analyze relationships between concepts

**Three Modes**:
1. **Binary comparison** (scenario analysis) - "What if X instead of Y?"
2. **Multi-way comparison** - "Compare X vs Y vs Z"
3. **Relationship analysis** - "How do X and Y relate?"

**Usage**:
```bash
# Pattern 1: Binary comparison (scenario analysis)
/what-if "We used PostgreSQL instead of Aurora"
/what-if "Lambda timeout was 15s instead of 30s"

# Pattern 2: Multi-way comparison (NEW)
/what-if "compare Redis vs DynamoDB vs ElastiCache for caching"
/what-if "compare Lambda vs ECS vs EKS for compute"

# Pattern 3: Relationship analysis (NEW)
/what-if "analyze relationship between caching and CDN"
/what-if "how do microservices and serverless relate"

# Save analysis
/what-if "compare PostgreSQL vs MySQL vs Aurora" save
```

**Binary comparison structure** (existing):
- Current reality → Under new assumption → What breaks → What improves → Insights → Recommendation

**Multi-way comparison structure** (NEW):
- Comparison context → Options analysis → Comparison matrix → Similarities/Differences → Relationships → Recommendation

**Relationship analysis structure** (NEW):
- Concepts definition → Similarity/Difference analysis → Relationship types (part-whole, complement, substitution, composition) → Interaction patterns → Recommendation

**Core Principle**: "Explore before committing" - systematic comparison prevents anchoring on first idea and reveals better alternatives

---

### `/specify` - Lightweight Design Sketches
**Purpose**: Create design specifications without full plan mode ceremony

**Usage**:
```bash
# API design
/specify "REST API for portfolio backtester"

# Schema design
/specify "DynamoDB schema for user preferences" schema

# Alternative exploration
/specify "SQS-based async processing" alternative

# Spike planning
/specify "Proof-of-concept: WebSocket updates" spike
```

**Focus types** (auto-detected):
- `api` - API endpoint design
- `schema` - Database/data structure design
- `workflow` - Process/workflow design
- `alternative` - Alternative approaches
- `spike` - Proof-of-concept experiments

**vs Plan Mode**: Specify = exploratory sketch, Plan Mode = implementation-ready plan

**Core Principle**: "Sometimes you just need to think out loud" - quick designs for exploration

---

### `/feature` - Contractual Feature Specification
**Purpose**: Create or update feature specifications in `.claude/specs/` that integrate with the Thinking Tuple kernel

**Usage**:
```bash
# Create new feature spec
/feature "stock-backtester"

# Update specific section
/feature "telegram" invariants
/feature "linebot" constraints
```

**Output structure**:
```
.claude/specs/{feature}/
  spec.yaml          # Metadata, dependencies, resources, flows
  invariants.md      # 5-level behavioral contracts (Level 4->0)
  constraints.md     # Learned restrictions (grows over time)
  acceptance.md      # "Done" criteria for verification
```

**Tuple Integration**:
- `spec.yaml` -> Populates **Constraints** (dependencies, resources)
- `invariants.md` -> Populates **Invariant** (5-level contracts)
- `constraints.md` -> Populates **Constraints** (learned knowledge)
- `acceptance.md` -> Populates **Check** (acceptance criteria)

**vs /specify**: `/specify` = exploratory (disposable), `/feature` = contractual (persistent)

**Workflow**:
```bash
/specify "backtester API" api     # Explore design (optional)
/feature "stock-backtester"       # Create contractual spec
/invariant "stock-backtester"     # Verify against spec
/reconcile "stock-backtester"     # Fix violations -> delta = 0
```

**Core Principle**: "Features have contracts" - specs define what MUST hold, what we've learned, and how to verify "done"

---

### `/adapt` - Integrate External Techniques
**Purpose**: Adapt techniques and patterns from external sources into the codebase while following local conventions and preserving knowledge

**Mode**: `transfer` (Tuple Effect: Heterogeneous transfer - maps source Constraints to target context)

**Usage**:
```bash
# From external repository
/adapt "https://github.com/user/repo" "authentication flow"

# From a library (not on PyPI)
/adapt "stock-pattern library" "chart pattern detection in frontend"

# From experiment branch
/adapt "experiment-branch" "PDF generation improvements"

# From documentation
/adapt "AWS SQS best practices" "message queue reliability"
```

**Six-Phase Workflow**:
1. **Study** - Understand what the source provides
2. **Map** - Surface assumptions with `/qna`, then map concepts to local equivalents
3. **Design** - Design local implementation using source techniques
4. **Implement** - Build using local patterns
5. **Verify** - Test with `/invariant` to verify behavioral invariants hold
6. **Document** - Record decisions and learnings

**Key integrations**:
- **Phase 2**: Use `/qna "adapting {source} for {goal}"` to surface assumptions before mapping
- **Phase 5**: Use `/invariant "adapted feature works"` to verify behavioral invariants

**Output**: Adaptation document at `.claude/adaptations/{date}-{slug}.md`

**Core Philosophy**: Focus on techniques, not code transplant. Understand before implementing. Create truly native code that applies external techniques.

**vs Other Commands**:
- `/explore` - Find sources to adapt from (precedes `/adapt`)
- `/adapt` - Adapt external sources to codebase
- `/abstract` - Extract patterns after adaptation (follows `/adapt`)

**Core Principle**: "Understand before implementing" - prevents unmaintainable foreign code

---

### `/design` - Domain-Aware Design
**Purpose**: Create new solutions with domain-specific checklists and patterns

**Usage**:
```bash
# Domain auto-detected from keywords
/design "VPC with private subnets for Lambda"         # Detects: aws
/design "Repository pattern for Aurora access"        # Detects: python
/design "REST API for backtester"                     # Detects: api

# Explicit domain override
/design aws "networking for multi-region deployment"
/design python "event sourcing implementation"
/design api "GraphQL schema for reports"
/design schema "user preferences storage"
/design frontend "chart component with WebSocket"
```

**Domains**:
- `aws` - Infrastructure design (VPC, Lambda, IAM, Terraform)
- `python` - Code architecture (SOLID, patterns, testing)
- `api` - API endpoints (REST, GraphQL, authentication)
- `schema` - Database design (tables, indexes, migrations)
- `frontend` - UI components (React, state management, styling)

**Output**: Design document at `.claude/designs/{date}-{domain}-{slug}.md`

**Design vs Specify**:
- `/specify` = Quick sketch, lightweight, exploratory
- `/design` = Thorough, domain-aware, implementation-ready

**Core Principle**: "Design is creation with constraints" - domain awareness ensures appropriate patterns

---

### `/x-ray` - Deep Structural Inspection
**Purpose**: Reveal internal structure of existing systems - components, boundaries, dependencies, patterns

**Usage**:
```bash
# Inspect architecture
/x-ray "report generation pipeline"
/x-ray "user request to report delivery"
/x-ray "CI/CD pipeline"
```

**Output**:
- Component inventory
- Boundary map (service, data, phase, network, permission)
- Dependency graph with critical path
- Pattern analysis (architecture, integration, anti-patterns)
- Trade-off analysis
- Strengths and weaknesses

**X-Ray vs Design**:
- `/x-ray` = Inspect existing (reveal structure)
- `/design` = Create new (produce solutions)

**Core Principle**: "See inside before changing" - inspection before modification

---

## Meta-Operations (Observational Learning Loop)

The following commands form a **meta-cognitive learning loop** that captures experience, analyzes patterns, and evolves principles:

```
/observe → /decompose → /abstract → /journal → /evolve
(capture)  (analyze)   (generalize) (interpret) (meta-learn)
```

### `/observe` - Capture Execution Traces
**Purpose**: Capture **what happened** without interpretation, enabling future analysis

**Smart Syntax** (auto-detects mode):
```bash
/observe "Deployed Lambda with new config"          # Detects: execution
/observe "Lambda timeout after 30 seconds"          # Detects: failure
/observe "Chose iterative approach over research"   # Detects: behavior
```

**Explicit mode** (optional):
```bash
/observe execution "Deployed Lambda with new config"
/observe failure "API timeout during peak traffic"
/observe behavior "Chose iterative approach over research"
```

**Detection**: Analyzes keywords (deployed/timeout/chose) to determine mode automatically

**Core Principle**: "Observations are immutable facts that can be re-analyzed when interpretations prove wrong"

---

### `/decompose` - Break Down Goals or Failures
**Purpose**: Decompose complex entities into components, dependencies, and preconditions

**Smart Syntax** (auto-detects mode):
```bash
/decompose "Implement zero-downtime deployment"     # Detects: goal (action verb)
/decompose "Lambda timeout in production"           # Detects: failure (error keyword)
/decompose ".claude/observations/.../failure-*.md"  # Detects: failure (file path)
```

**Explicit mode** (optional):
```bash
/decompose goal "Implement zero-downtime deployment"
/decompose failure .claude/observations/2025-12-23/failure-143205-lambda-timeout.md
```

**Detection**: File paths → failure, action verbs (Add/Implement) → goal, error keywords → failure

**Core Principle**: "Everything has parts" - understanding part-whole relationships reveals hidden complexity

---

### `/abstract` - Extract Patterns from Experience
**Purpose**: Generalize patterns from multiple concrete instances

**Smart Syntax** (auto-detects pattern type):
```bash
/abstract ".claude/observations/*/failure-*.md"     # Detects: failure_mode
/abstract ".claude/observations/*/execution-*.md"   # Detects: workflow
/abstract ".claude/journals/architecture/*.md"      # Detects: architecture
```

**Explicit type** (optional):
```bash
/abstract ".claude/journals/error/*.md" failure_mode  # Force failure_mode
/abstract ".claude/decompositions/goal-*.md" workflow # Force workflow
```

**Detection**: Analyzes file paths (/failure-/ → failure_mode, /execution-/ → workflow)

**Core Principle**: "Intelligence generalizes" - patterns extracted from specific instances enable reuse

---

### `/journal` - Document Interpreted Knowledge
**Purpose**: Capture interpreted solutions, decisions, and patterns

**Usage**:
```bash
/journal architecture "Aurora vs DynamoDB for caching"
/journal error "Lambda timeout in production"
/journal pattern "Validation gates before workflow nodes"
/journal meta "Research-before-iteration saves deploy cycles"
```

**Categories**:
- `architecture` - Pre-ADR exploration, design decisions
- `error` - Bug investigations and solutions
- `pattern` - Reusable code or workflow patterns
- `meta` - Process improvements, tooling enhancements

**Workflow**: Observations (facts) → Journals (interpretation) → ADRs (formal decisions)

---

### `/report` - Summarize Work Session
**Purpose**: Generate markdown summary of recent work, decisions, and next steps

**Usage**:
```bash
/report                    # Current session
/report 1h                 # Last hour
/report today              # Today's work
/report session output.md  # Save to file
```

**Output includes**:
- Summary of work accomplished
- Topics covered with outcomes
- Decisions made
- Problems solved
- Next steps / action items
- Links to journal entries and observations created

---

### `/evolve` - Reflect & Evolve Knowledge
**Purpose**: Meta-operation to detect drift between documented principles and actual practices

**Usage**:
```bash
/evolve              # Review all areas
/evolve testing      # Focus on testing patterns
/evolve deployment   # Focus on deployment
```

**What it does**:
1. Reviews recent commits and journal entries
2. Compares CLAUDE.md principles vs actual code
3. Identifies undocumented patterns
4. Proposes updates to CLAUDE.md and skills
5. Generates report with priorities

---

## Debugging

### `/bug-hunt` - Systematic Bug Investigation
**Purpose**: Type-specific bug investigation workflows for production errors, performance issues, race conditions, and data corruption

**Usage**:
```bash
# Auto-detect bug type from symptom
/bug-hunt "Lambda timeout after 30 seconds"
/bug-hunt "API latency increased from 200ms to 2s"
/bug-hunt "Intermittent 500 errors on /api/backtest"
/bug-hunt "Memory usage growing over time"

# Explicit bug type (override auto-detection)
/bug-hunt "slow query" performance
/bug-hunt "sometimes fails" race-condition
```

**Bug types** (auto-detected):
- `production-error` - Errors, exceptions, crashes, timeouts
- `performance` - Slowness, latency spikes, bottlenecks
- `data-corruption` - Incorrect data, missing fields
- `race-condition` - Intermittent, flaky, non-deterministic
- `memory-leak` - Memory growth, OOM errors
- `integration-failure` - External API/service issues

**Investigation workflow**:
```
Symptom → Classify Type → Gather Evidence → Form Hypotheses
                                                    ↓
          Test Systematically → Root Cause → Reproduction + Fixes
```

**Output**: Investigation report at `.claude/bug-hunts/{date}-{slug}.md` including:
- Evidence gathered (logs, metrics, code, git changes)
- Hypotheses tested (eliminated/confirmed/uncertain)
- Root cause + confidence level (High/Medium/Low)
- Reproduction steps
- Fix candidates with pros/cons/effort
- Recommended fix + rationale

**Core Principle**: "Systematic investigation beats random debugging" - structure prevents thrashing

**vs Other Debugging Tools**:
- `/observe failure` - Captures what happened (immutable record)
- `/decompose failure` - Breaks down failure structure
- `error-investigation` skill - AWS/Lambda patterns (auto-applied)
- **`/bug-hunt`** - **Active investigation with type-specific workflows**

---

## Verification Commands (Behavioral Contracts)

### `/invariant` - Identify Behavioral Invariants
**Purpose**: Identify what must remain true for a goal, generating verification checklists before claiming "done"

**Usage**:
```bash
# Goal-based invariant identification
/invariant "deploy new Langfuse scoring feature"
/invariant "add new API endpoint for backtest"

# Domain-specific focus
/invariant deployment "release v1.2.3"
/invariant data "add new Aurora table"
/invariant langfuse "add compliance score"
```

**5-Level Verification Hierarchy**:
| Level | Type | What to Verify |
|-------|------|----------------|
| 4 | Configuration | Env vars, constants, Doppler |
| 3 | Infrastructure | Lambda → Aurora, Lambda → S3 |
| 2 | Data | Schema valid, data fresh |
| 1 | Service | Lambda returns 200, API contract |
| 0 | User | End-to-end flow succeeds |

**Core Principle**: "Done" = All invariants verified (delta = 0), not just code written

---

### `/reconcile` - Converge Violations to Compliance
**Purpose**: Generate specific fix actions to converge invariant violations back to compliance

**Usage**:
```bash
# Reconcile by domain
/reconcile deployment
/reconcile langfuse

# Preview fixes without applying
/reconcile deployment --preview

# Apply fixes with confirmation
/reconcile deployment --apply
```

**Workflow Integration**:
```
/invariant "goal"    →    /reconcile    →    /invariant "goal"
    (detect)              (converge)           (verify)
       ↓                      ↓                    ↓
   Identify              Generate             Confirm
   invariants           fix actions          delta = 0
```

**Core Principle**: "Converge delta to zero" - systematic fix generation, not ad-hoc patching

---

### Invariant Feedback Loop

The invariant commands form a **convergence loop** distinct from failure-driven loops:

| Loop Type | Trigger | Purpose |
|-----------|---------|---------|
| Retrying | Failure occurred | Fix execution |
| Initial-Sensitive | Same failure repeats | Question assumptions |
| **Invariant** | Before claiming "done" | Verify contracts hold |

**Key difference**: Invariant Loop is **proactive** (verify before failure), not **reactive** (respond to failure).

**Invariant Domain Files**:
- `.claude/invariants/system-invariants.md` - Always verify (critical path)
- `.claude/invariants/deployment-invariants.md` - CI/CD, Lambda, Terraform
- `.claude/invariants/data-invariants.md` - Aurora, migrations, timezone
- `.claude/invariants/api-invariants.md` - Endpoints, contracts
- `.claude/invariants/langfuse-invariants.md` - Tracing, scoring
- `.claude/invariants/frontend-invariants.md` - React, state, charts

---

### `/step` - Thinking Tuple Protocol
**Purpose**: Instantiate a Thinking Tuple - the atomic unit of disciplined reasoning that forces composition of all layers at each reasoning step

**Usage**:
```bash
# Explicit tuple instantiation
/step "deploy new scoring feature"
/step "refactor authentication module"
/step "investigate timeout bug"

# With explicit mode selection
/step --mode=diverge "explore caching strategies"
/step --mode=converge "select best approach"
```

**Tuple Structure**:
```
Tuple = (Constraints, Invariant, Principles, Process, Actions, Check)
```

| Component | Question | Source |
|-----------|----------|--------|
| **Constraints** | What do we have/know? | Current state, resources |
| **Invariant** | What must be true at end? | `/invariant`, success criteria |
| **Principles** | What tradeoffs guide us? | Tier-0 + task clusters |
| **Process** | What thinking mode? | diverge, converge, decompose, compare, reframe, escape |
| **Actions** | What concrete steps? | Tool calls, commands |
| **Check** | Did we satisfy invariant? | Progressive Evidence (Layers 1-4) |

**Process Modes**:
- `diverge` - Generate multiple options, explore broadly
- `converge` - Narrow down, select from options
- `decompose` - Break into subproblems
- `compare` - Evaluate alternatives side-by-side
- `reframe` - Change perspective on the problem
- `escape` - Break out of local optimum

**When to Use**:
- Complex tasks (> 3 steps) where drift is possible
- Long-running work needing checkpoints
- After Check failures (spin new tuple with updated constraints)
- Autonomous mode (always)

**Error Bound**: Without tuples, error ∝ (steps × drift). With tuples, error bounded by check frequency.

**Core Principle**: Each tuple is a **checkpoint with full context**. If Check fails, spin a new tuple with updated Constraints—don't abandon the run.

See [/step command](step.md), [Thinking Tuple Guide](../../docs/guides/thinking-tuple-protocol.md), and [Thinking Process Architecture - Section 12](../diagrams/thinking-process-architecture.md#12-thinking-tuple-protocol).

---

## Worktree Management

Manage parallel git worktrees for concurrent agent execution. Enables multiple agents to work on different tasks simultaneously without file conflicts.

### `/wt-spin-off` - Create Branch and Worktree
**Purpose**: Create new branch and git worktree for parallel agent execution

**Usage**:
```bash
/wt-spin-off "task description"
```

**Examples**:
```bash
/wt-spin-off "fix timeout bug"
/wt-spin-off "add backtester API"
/wt-spin-off "refactor workflow layer"
/wt-spin-off "investigate memory leak"
```

**What it creates**:
- Branch: `wt-{date}-{time}-{slug}-{random}` (e.g., `wt-2025-12-24-143052-fix-timeout-bug-a3f2`)
- Directory: `{parent}/{repo}-wt-{slug}` (e.g., `../dr-daily-report_telegram-wt-fix-timeout-bug`)

**Features**:
- Deterministic naming with collision prevention
- Disk space check (warns if < 1GB)
- Independent `.claude/` state per worktree
- Creates from current HEAD (works from any branch)

**Use Case**: Run multiple agents in parallel without conflicts. Each agent gets isolated workspace.

---

### `/wt-list` - List Active Worktrees
**Purpose**: List all active git worktrees with activity status and cleanup suggestions

**Usage**:
```bash
/wt-list
```

**What it shows**:
- All worktrees (main + additional)
- Last modified time and relative age
- Activity status (🟢 Active, 🟡 Idle, 🔴 Stale)
- Branch names and commit messages
- Cleanup suggestions for stale worktrees (> 12 hours)

**Activity Thresholds**:
- 🟢 **Active**: < 30 minutes (currently being worked on)
- 🟡 **Idle**: 30 min - 12 hours (work paused)
- 🔴 **Stale**: > 12 hours (likely abandoned, should review)

**Use Case**: Track parallel agent workflows and identify abandoned worktrees.

---

### `/wt-merge` - Merge Worktree Branch to Dev
**Purpose**: Merge worktree branch back to dev with safety validation

**Usage**:
```bash
/wt-merge "slug"
```

**Examples**:
```bash
/wt-merge "investigate-lambda-timeout"
/wt-merge "rest-api-for-backtester"
```

**Safety Checks**:
- ✅ Must be on dev branch
- ✅ Dev must be clean (no uncommitted changes)
- ✅ Dev should be up-to-date with remote
- ✅ Worktree branch must exist
- ✅ Detects if already merged

**Merge Strategy**: Fast-forward only (linear history)
- If fast-forward fails, suggests rebase
- Preserves clean git history (no merge commits)
- Enforces best practice (rebase before merge)

**Post-Merge**: Worktree still exists (user decides when to remove separately)

**Use Case**: Integrate parallel work back to dev safely.

---

### `/wt-remove` - Remove Worktree Directory
**Purpose**: Remove worktree directory with safety validation and optional branch deletion

**Usage**:
```bash
/wt-remove "slug"
```

**Examples**:
```bash
/wt-remove "investigate-lambda-timeout"
/wt-remove "failed-experiment"
```

**Safety Checks**:
- ✅ Checks if branch is merged to dev
- ✅ Warns about uncommitted changes
- ✅ Prevents removal of main worktree
- ✅ Prevents removal if inside worktree
- ✅ Handles broken references (directory already deleted)

**Branch Deletion**:
- If merged: Prompts to delete branch (safe)
- If not merged: Keeps branch, requires manual force delete

**Use Case**: Clean up worktrees after work complete or discard failed experiments.

---

## Worktree Workflow Example

**Parallel Agent Execution**:
```bash
# Terminal 1: Agent investigating bug
/wt-spin-off "investigate lambda timeout"
cd ../dr-daily-report_telegram-wt-investigate-lambda-timeout
/bug-hunt "Lambda timeout after 30 seconds"
# ... work complete ...
/wt-merge "investigate-lambda-timeout"
/wt-remove "investigate-lambda-timeout"

# Terminal 2: Agent designing API (parallel!)
/wt-spin-off "REST API for backtester"
cd ../dr-daily-report_telegram-wt-rest-api-for-backtester
/specify api "Backtester REST API"
# ... still working ...

# Terminal 3: Check all worktrees
/wt-list
# Shows both worktrees with activity status
```

**Benefits**:
- ✅ No file conflicts between agents
- ✅ Independent `.claude/` state per worktree
- ✅ Each agent works at own pace
- ✅ Merge when ready (no coordination needed)

---

## Environment Commands

Target operations to specific environments **without switching worktrees**. Claude can execute commands against remote resources regardless of which branch/worktree is currently active.

**Core Philosophy**: "Target environment, not location" - the worktree is irrelevant; environment targeting is about resource names.

### `/local` - Local Development Environment
**Purpose**: Execute operations in local dev environment (localhost + SSM tunnel to Aurora)

**Usage**:
```bash
/local "start API server"
/local "verify local setup"
/local "SELECT COUNT(*) FROM daily_prices"  # Via SSM tunnel
/local "run integration tests"
```

**Characteristics**:
- API: `localhost:8000` (FastAPI/uvicorn)
- Aurora: SSM tunnel to dev cluster
- DynamoDB: LocalStack (`localhost:4566`)
- Doppler: `local_dev` config (inherits from `dev`)

**Safety**: Unrestricted (local only, no direct AWS impact)

---

### `/dev` - Development Environment Operations
**Purpose**: Execute ANY operation targeting the dev environment

**Usage**:
```bash
/dev "show telegram-api errors in last 30 min"
/dev "SELECT COUNT(*) FROM daily_prices"
/dev "get current image digest for telegram-api"
/dev deploy
```

**Safety**: Unrestricted - no confirmation required for any operation

---

### `/stg` - Staging Environment Operations
**Purpose**: Execute ANY operation targeting the staging environment

**Usage**:
```bash
/stg "verify deployment succeeded"
/stg "compare Lambda image with dev"
/stg "query Aurora to verify data sync"
/stg deploy  # Requires confirmation
```

**Safety**: Moderate gates
- Read operations: No confirmation
- Write operations: Confirmation required
- Deploy operations: Confirmation required

---

### `/prd` - Production Environment Operations
**Purpose**: Execute operations targeting production (read-only default)

**Usage**:
```bash
/prd "show errors in last 1 hour"
/prd "SELECT MAX(date) FROM daily_prices"
/prd "compare Lambda image with staging"
/prd deploy  # Redirects to /deploy prod
```

**Safety**: Restricted
- Read operations: Always allowed
- Write operations: Double confirmation required
- Deploy operations: Redirect to full `/deploy prod` workflow

---

### `/env` - Generic Feature Branch Environments
**Purpose**: Execute operations targeting feature branch environments (extends fixed commands)

**Usage**:
```bash
# Target feature branch environment
/env "feature-alerts" "show errors in last 30 min"
/env "feature-backtest" "SELECT COUNT(*) FROM users"
/env "feature-charts" deploy

# List available feature environments
/env --list
```

**Resource Resolution**:
```
/env "feature-alerts" → dr-daily-report-{component}-feature-alerts
```

**Safety Level Mapping**:
| Pattern | Safety | Confirmation |
|---------|--------|--------------|
| `feature-*`, `experiment-*` | Unrestricted | None |
| `staging-*`, `stg-*` | Moderate | Writes only |
| `hotfix-*`, `release-*` | Restricted | All writes + deploys |

**Why both fixed + generic?**
- Fixed commands (`/dev`, `/prd`) provide explicit safety differentiation
- `/prd` being distinct has psychological safety value
- `/env` extends the pattern to arbitrary feature branches
- 90% of operations use fixed environments; `/env` handles feature branches

---

### Resource Resolution

All commands automatically resolve resources using existing naming conventions:

| Resource Type | `/local` | `/dev`, `/stg`, `/prd` |
|---------------|----------|------------------------|
| API | `localhost:8000` | API Gateway |
| Lambda | N/A (local server) | `dr-daily-report-{component}-{env}` |
| Log Group | stdout/stderr | `/aws/lambda/dr-daily-report-{component}-{env}` |
| Aurora | SSM tunnel → dev | `dr-daily-report-{env}` cluster |
| DynamoDB | LocalStack | AWS DynamoDB |
| Doppler | `local_dev` | `dev`, `stg`, `prd` configs |

---

### Environment Commands vs `/deploy`

| Capability | `/deploy` | `/local` | `/dev`, `/stg`, `/prd` |
|------------|-----------|----------|------------------------|
| Deployment | Full workflow | N/A | Quick or delegates to `/deploy` |
| Server | N/A | Start/stop local | N/A |
| Logs | N/A | Local stdout | CloudWatch access |
| Queries | N/A | Aurora via tunnel | Aurora direct |
| Comparison | N/A | N/A | Cross-environment |

**Use `/deploy`** for: Full deployment workflow with all phases

**Use `/local`** for: Local development (server, tests, debugging)

**Use `/dev`, `/stg`, `/prd`** for: AWS operations (logs, queries, checks, comparisons)

---

## Code Quality

### `/qna` - Knowledge Alignment Check
**Purpose**: Proactively reveal Claude's understanding and knowledge gaps before implementation

**Usage**:
```bash
# Basic knowledge probe
/qna "real-time stock alerts"

# Probe with depth level
/qna "deployment pipeline" deep
/qna "error handling" surface

# Domain-specific probing
/qna "telegram mini app architecture"
```

**Depth levels**:
- `surface` - Quick alignment (3-5 facts, 2-3 gaps)
- `moderate` (default) - Standard probe (5-10 facts, 3-5 gaps)
- `deep` - Comprehensive audit (exhaustive facts, systematic gap analysis)

**Output**:
- What I Know (Confident) - Facts with sources
- What I Assume (Medium Confidence) - Inferred beliefs
- What I Don't Know (Knowledge Gaps) - Missing information
- Questions to Align - Clarifying questions with impact
- Confidence Score (1-10)

**Core Principle**: "Uncertainty should be explicit" - surface assumptions early to prevent rework

---

### `/pay-debt` - Technical Debt Payment Plan
**Purpose**: Identify technical debt with prioritized "payment plan" using complexity and hotspot analysis

**Usage**:
```bash
# Analyze directory with default budget (sprint)
/pay-debt "src/workflow/"

# With specific budget
/pay-debt "src/" quick        # Quick wins only (1-2 days)
/pay-debt "src/" sprint       # One sprint (5-10 days)
/pay-debt "src/" quarter      # Quarterly investment (20-40 days)
```

**Output**:
- **Debt Inventory**: P0/P1/P2/P3 items with complexity and churn metrics
- **Interest Calculation**: Cost of NOT fixing (hours/month wasted)
- **Payment Plan**: Phased actions with effort estimates
- **Verification Criteria**: Before/after complexity targets

**Priority Matrix**:
| Churn | Complexity | Priority | Action |
|-------|-----------|----------|--------|
| High | High | **P0** 🔥 | Pay immediately |
| High | Low | P1 ⚠️ | Pay this sprint |
| Low | High | P2 📝 | Schedule payment |
| Low | Low | P3 ✅ | Monitor only |

**Relationship to `/refacter` skill**:
- `/pay-debt` = WHAT to refactor (prioritization, planning)
- `/refacter` skill = HOW to refactor (patterns, techniques)

**Core Principle**: "Debt has interest" - quantify the cost of not paying to prioritize effectively

---

### `/refactor` - Analyze Complexity & Hotspots
**Purpose**: Identify high-priority refactoring opportunities using complexity analysis and git churn

**Usage**:
```bash
# Analyze single file (complexity mode)
/refactor src/workflow/workflow_nodes.py

# Analyze directory (all mode: complexity + hotspots)
/refactor src/workflow/

# Explicit hotspots analysis
/refactor src/ hotspots

# Save report to file
/refactor src/workflow/ report.md
```

**Analysis modes** (auto-detected):
- `complexity` - Cyclomatic/cognitive complexity, LOC, parameters
- `hotspots` - High churn (git commits) + high complexity
- `all` - Both complexity and hotspots (default for directories)

**Priority Matrix**:
| Churn | Complexity | Priority | Action |
|-------|-----------|----------|--------|
| High (> 15) | High (> 10 CC) | **P0** 🔥 | Refactor immediately |
| High | Low | P1 ⚠️ | Monitor |
| Low | High | P2 📝 | Schedule in sprint |
| Low | Low | P3 ✅ | Maintain quality |

**Output**: Verbose P0/P1/P2/P3 breakdown with pattern recommendations AND example refactoring for top P0 function

**Core Principle**: "Measure first, refactor second" - use data to prioritize where refactoring has maximum impact

---

### `/explain` - Multi-Stage Concept Explanation
**Purpose**: Demonstrate command composition via clarify → search → synthesize pipeline

**Usage**:
```bash
/explain "Lambda cold start optimization"
/explain "Aurora-First Data Architecture"
/explain "Validation gates before workflow nodes"
```

**Pipeline stages**:
1. **Clarify**: Determine audience level, context, depth needed
2. **Search**: Find info in CLAUDE.md, skills, docs, codebase
3. **Synthesize**: Generate structured explanation with examples

---

## Utility Commands

### `/handholding` - Step-by-Step Guidance
**Purpose**: Guide users through complex or unfamiliar tasks with explicit confirmation at each step

**Usage**:
```bash
# Basic usage
/handholding "deploy to production"
/handholding "set up feature-alerts environment"
/handholding "debug this timeout error"

# With pace modifier
/handholding "deploy to staging" quick      # Fewer confirmations
/handholding "migrate database" careful     # Default, confirm each step
/handholding "set up CI/CD" thorough        # Extra explanations
```

**What makes it different**:
| Aspect | Regular Commands | `/handholding` |
|--------|-----------------|----------------|
| **Confirmation** | At end or critical points | Every step |
| **Explanation** | Minimal | What, Why, Risk for each step |
| **Progress** | Implicit | Explicit "Step X of Y" |
| **Abort** | Say "stop" | Explicit [Abort] option |
| **Reversibility** | Not stated | Stated for each step |

**Step format**:
```markdown
## Step {N} of {Total}: {Step Name}

**What I'll do**: {Clear description}
**Why**: {Rationale}
**Reversible**: {Yes | No | Partially}
**Risk**: {None | Low | Medium | High}

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]
```

**Pace levels**:
- `careful` (default) - Confirm every step, full explanations
- `quick` - Auto-proceed read-only steps, confirm writes only
- `thorough` - Extended explanations with examples

**When to use**:
- Nervous about complex operations (first production deploy)
- Learning new workflows
- High-stakes tasks where mistakes are costly
- Teaching someone through a process

**Core Principle**: "Psychological safety through explicit control" - users feel safe attempting complex tasks because they understand each step and can abort anytime

---

## Command Composition Patterns

Commands can orchestrate multiple capabilities in sequence:

### 1. Command Invokes Skill

**Pattern**: Reference skill in `composition` frontmatter

```markdown
---
composition:
  - skill: research
  - skill: code-review
---

# In prompt template:
Invoke the `research` skill to investigate root cause:
[Include research skill's investigation methodology]

Then invoke the `code-review` skill to validate the fix:
[Include code-review security and performance patterns]
```

**Example**: `/update-capability` uses the `research` skill for systematic investigation

---

### 2. Command Chains Command

**Pattern**: Sequential execution via `composition`

```markdown
---
composition:
  - command: report
  - command: journal
---

# In prompt template:
First, generate work session report:
Execute /report session

Then, prompt user to journal key decisions:
Execute /journal [category inferred from report]
```

**Example**: End-of-day workflow could chain `/report` → `/journal` → commit

---

### 3. Command Runs Script

**Pattern**: Reference script in `composition`

```markdown
---
composition:
  - script: .claude/skills/refacter/scripts/analyze_complexity.py
  - skill: refacter
---

# In prompt template:
Run complexity analysis:
```bash
python .claude/skills/refacter/scripts/analyze_complexity.py src/
```

Then use refacter skill to interpret results and suggest improvements.
```

**Example**: Complexity review could run analysis script, then invoke refactor skill

---

## Argument Handling

Commands accept arguments via structured schema:

### Defining Arguments

```markdown
---
arg_schema:
  - name: category
    required: true
    description: One of architecture, error, pattern, meta
  - name: title
    required: true
    description: Title of entry (quoted if spaces)
  - name: details
    required: false
    description: Optional additional details
---
```

### Using Arguments in Prompts

```markdown
## Prompt Template

Category: $1
Title: $2
Optional details: ${3:-Not provided}

All arguments as single string: $ARGUMENTS
```

**Placeholder syntax**:
- `$1`, `$2`, `$3` - Individual positional arguments
- `$ARGUMENTS` - All arguments as space-separated string
- `${n:-default}` - Argument with default value if not provided

### Argument Examples

```bash
# Required arguments only
/journal architecture "Aurora caching decision"

# With optional argument
/journal error "Lambda timeout" "Occurred during peak traffic"

# Arguments with spaces (use quotes)
/journal pattern "Validation gates before workflow execution"

# Multiple arguments
/report session "output-$(date +%Y%m%d).md"
```

---

## Creating New Commands

### File Structure

Commands live in `.claude/commands/{command-name}.md`:

```markdown
---
name: command-name
description: Brief description (1-2 sentences)
accepts_args: true | false
arg_schema:
  - name: arg1
    required: true | false
    description: What this argument is for
composition:
  - skill: skill-name        # Can invoke skills
  - command: other-command   # Can chain commands
  - script: path/to/script   # Can run scripts
---

# Command Name

**Purpose**: What this command accomplishes

**When to use**: Scenarios where this command is appropriate

---

## Execution Flow

1. Step 1: Description of what happens
2. Step 2: Next action
3. Step 3: Final step

---

## Prompt Template

You are executing the `/{name}` command with arguments: $ARGUMENTS

[Command-specific instructions that Claude will follow...]

Step 1: [First action]
Step 2: [Second action]
Step 3: [Final action]

---

## Examples

### Example 1: Basic usage
```bash
/command-name arg1
```

### Example 2: With multiple arguments
```bash
/command-name arg1 arg2 "arg with spaces"
```

### Example 3: Optional arguments
```bash
/command-name required-arg optional-arg
```
```

---

## Command Design Guidelines

### When to Create a Command

Create a command when you need:
- **Explicit control** over when workflow runs (vs auto-discovery)
- **Composition** of multiple skills/commands/scripts
- **Structured arguments** with validation
- **Repeatable workflow** with consistent steps

**Don't create a command for**:
- Domain expertise (create a skill instead)
- One-time operations (just ask Claude)
- Simple shortcuts (not worth the overhead)

### Command Naming

- Use verb-noun format: `/journal`, `/report`, `/evolve`
- Be concise but descriptive
- Avoid abbreviations unless universally understood
- Match user's mental model of the action
- Meta-operations use single verbs: `/observe`, `/decompose`, `/abstract`

### Prompt Template Tips

- Be explicit about what Claude should do
- Use numbered steps for clarity
- Include examples in the prompt
- Reference skills by name when invoking them
- Provide fallback behavior for optional arguments

---

## Integration with Existing Skills

Commands complement the 9 existing auto-discovered skills:

| Skill | What It Provides | How Commands Use It |
|-------|------------------|---------------------|
| **research** | Investigation methodology | `/decompose` and `/abstract` invoke for systematic analysis |
| **code-review** | Security, performance checks | Commands can invoke for validation |
| **testing-workflow** | Test patterns | `/abstract` can extract test patterns |
| **refactor** | Complexity analysis | Commands can run scripts, apply patterns |
| **deployment** | Zero-downtime strategies | `/observe execution` captures deployment workflows |
| **error-investigation** | Multi-layer debugging | `/observe failure` → `/decompose failure` → skill update |
| **database-migration** | Migration patterns | Commands can validate migrations |
| **telegram-uiux** | UI patterns | `/abstract` can extract UI workflow patterns |
| **line-uiux** | Legacy patterns | Commands avoid (maintenance mode) |

**Key principle**: Skills provide expertise, commands orchestrate workflows

**Meta-operations learning loop**:
```
Concrete experience → /observe (capture facts)
     ↓
Analysis → /decompose (break down into parts)
     ↓
Generalization → /abstract (extract patterns)
     ↓
Documentation → /journal (interpret and document)
     ↓
Skill graduation → Pattern moves into skill docs
     ↓
Principle evolution → /evolve detects drift, updates CLAUDE.md
```

---

## FAQ

### When should I use a command vs just asking Claude?

**Use a command when**:
- You need consistent, repeatable workflow
- Multiple steps need to happen in specific order
- You want explicit control over invocation timing
- Arguments need validation

**Just ask Claude when**:
- It's a one-time request
- Context is sufficient without structure
- Flexibility is more important than consistency

### Can commands call other commands?

Yes! Commands can chain other commands via the `composition` field. The chained command executes in sequence.

Example: `/end-of-day` could chain `/report` → `/journal` → commit message generation

### What's the difference between commands and skills?

**Commands** = Explicit workflows you invoke (`/command`)
**Skills** = Expertise Claude auto-applies when relevant

Think: Commands are recipes, skills are ingredients.

### How do I pass arguments with spaces?

Use quotes:
```bash
/journal architecture "This is a single argument with spaces"
```

### Can commands invoke skills that are auto-discovered?

Yes! Commands can reference skills in their prompts. The skill's patterns and methodology are available to the command.

### What if I have a typo in a command name?

Claude Code will show available commands. Check `.claude/commands/` directory for exact names.

---

## Directory Structure

```
.claude/
├── commands/              # Slash command definitions
│   ├── README.md          # This file
│   ├── journal.md         # Document interpreted knowledge
│   ├── validate.md        # Validate claims with evidence
│   ├── observe.md         # Capture execution traces
│   ├── decompose.md       # Break down goals/failures
│   ├── abstract.md        # Extract patterns
│   ├── report.md          # Summarize sessions
│   ├── evolve.md          # Detect drift & evolve principles
│   └── explain.md         # Composition demo
├── observations/          # NEW: Immutable observation storage
│   ├── README.md          # Observation system guide
│   ├── 2025-12-23/        # Daily directories
│   │   ├── execution-143052-deployed-lambda.md
│   │   ├── failure-143205-lambda-timeout.md
│   │   └── behavior-143420-iteration-over-research.md
│   └── archive/           # Old observations (>90 days)
├── adaptations/           # External source adaptation documents
│   ├── README.md          # Adaptation process overview
│   └── {date}-{slug}.md   # Individual adaptation documents
├── decompositions/        # Goal/failure analysis outputs
│   ├── goal-2025-12-23-add-caching.md
│   ├── failure-2025-12-23-lambda-timeout.md
│   └── ...
├── abstractions/          # NEW: Extracted patterns
│   ├── failure_mode-2025-12-23-api-timeout.md
│   ├── workflow-2025-12-23-staged-deployment.md
│   ├── decision-2025-12-24-research-vs-iterate.md
│   └── architecture-2025-12-25-aurora-first.md
├── validations/           # NEW: Claim validation reports
│   ├── 2025-12-23-lambda-timeout-claim.md
│   ├── 2025-12-24-user-behavior-assumption.md
│   └── ...
├── journals/              # Interpreted knowledge capture
│   ├── README.md          # Journal system guide
│   ├── architecture/      # Design decisions (pre-ADR)
│   ├── error/             # Bug solutions
│   ├── pattern/           # Reusable patterns
│   └── meta/              # Process improvements
└── skills/                # Auto-discovered skills (existing)
    ├── research/
    ├── code-review/
    ├── testing-workflow/
    ├── deployment/
    ├── error-investigation/
    └── ... (9 total)
```

---

## Next Steps

### Getting Started

1. **Start with `/observe`**: Capture execution traces and failures as you work
   - After deployments: `/observe execution "Deployed X to Y"`
   - When errors occur: `/observe failure "Error description"`

2. **Use `/journal`**: Document solutions and decisions
   - After solving bugs: `/journal error "Bug title"`
   - When making choices: `/journal architecture "Decision title"`

3. **Try `/decompose`**: Break down complex goals before implementing
   - Before starting: `/decompose goal "Feature description"`
   - When debugging: `/decompose failure .claude/observations/{file}.md`

### Building the Learning Loop

4. **Extract patterns with `/abstract`**: After 3+ similar cases
   - Recurring failures: `/abstract ".claude/observations/*/failure-*.md" failure_mode`
   - Common workflows: `/abstract ".claude/observations/*/execution-*.md" workflow`

5. **Evolve principles with `/evolve`**: Monthly review
   - Detect drift: `/evolve`
   - Focus areas: `/evolve testing` or `/evolve deployment`

6. **Summarize sessions with `/report`**: End of day/week
   - Session summary: `/report`
   - Save to file: `/report session output.md`

### Advanced

7. **Try `/explain`**: See command composition in action
   - Multi-stage pipeline demo
   - Learn how commands can chain together

For detailed command documentation, see individual command files in `.claude/commands/`.

---

## Command Reference Quick Links

### Core Commands
- [/journal](journal.md) - Document knowledge with smart categorization
- [/validate](validate.md) - Validate claims with evidence (empirical)
- [/proof](proof.md) - Formal deductive proofs (deductive)

### Inspection (Reveal Existing)
- [/x-ray](x-ray.md) - Deep structural inspection of existing systems
- [/locate](locate.md) - Find where functionality lives in the codebase
- [/qna](qna.md) - Reveal Claude's understanding and knowledge gaps

### Analysis (Think About Existing)
- [/what-if](what-if.md) - Counterfactual reasoning and comparison
- [/analysis](analysis.md) - Comprehensive analysis workflow
- [/impact](impact.md) - Assess change scope

### Design (Create New)
- [/design](design.md) - Domain-aware thorough design (aws, python, api, schema, frontend)
- [/specify](specify.md) - Lightweight design sketches
- [/explore](explore.md) - Divergent solution exploration
- [/adapt](adapt.md) - Integrate external techniques into codebase

### Meta-Operations
- [/observe](observe.md) - Capture execution traces
- [/decompose](decompose.md) - Break down goals/failures
- [/abstract](abstract.md) - Extract patterns
- [/report](report.md) - Summarize sessions
- [/evolve](evolve.md) - Detect drift & evolve

### Debugging
- [/bug-hunt](bug-hunt.md) - Systematic bug investigation with type-specific workflows

### Verification (Behavioral Contracts)
- [/invariant](invariant.md) - Identify behavioral invariants that must hold
- [/reconcile](reconcile.md) - Converge violations back to compliance

### Worktree Management
- [/wt-spin-off](wt-spin-off.md) - Create branch and worktree for parallel work
- [/wt-list](wt-list.md) - List active worktrees with activity status
- [/wt-merge](wt-merge.md) - Merge worktree branch to dev
- [/wt-remove](wt-remove.md) - Remove worktree directory

### Code Quality
- [/qna](qna.md) - Knowledge alignment check before implementation
- [/pay-debt](pay-debt.md) - Technical debt payment plan
- [/refactor](refactor.md) - Analyze complexity & hotspots

### Environment Commands
- [/local](local.md) - Execute operations targeting local environment (localhost + SSM tunnel)
- [/dev](dev.md) - Execute operations targeting dev environment (unrestricted)
- [/stg](stg.md) - Execute operations targeting staging environment (moderate gates)
- [/prd](prd.md) - Execute operations targeting production environment (read-only default)
- [/env](env.md) - Generic feature branch environment targeting

### Utility Commands
- [/handholding](handholding.md) - Step-by-step guidance through complex tasks

### Demos
- [/explain](explain.md) - Composition demo
