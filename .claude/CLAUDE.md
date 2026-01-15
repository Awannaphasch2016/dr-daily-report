# Daily Report - Development Guide

**CLAUDE.md is the ground truth contract for how we work.**

---

## About This Document

Principles are organized by **applicability tier**:
- **Tier-0 (Core)**: Apply to EVERY task - documented here
- **Tier-1/2/3 (Context-specific)**: Apply by task/domain - documented in `.claude/principles/`

This reduces token usage by ~60% while maintaining full principle coverage.

---

## Project Context

**Multi-App Architecture:** LINE Bot (chat-based) + Telegram Mini App (web dashboard) share identical core backend. Resources separated via AWS tags (`App = line-bot | telegram-api | shared`).

**Branch Strategy:** `dev` → dev environment (~8 min) | `main` → staging environment (~10 min) | Tags `v*.*.*` → production (~12 min)

**AWS Permissions Philosophy:** Full IAM permissions available. When encountering permission errors, create necessary IAM policy and attach—don't ask for permission. See [AWS Setup](docs/AWS_SETUP.md).

For complete component inventory, technology stack, and directory structure, see [Documentation Index](docs/README.md) and [Project Conventions](docs/PROJECT_CONVENTIONS.md).

---

## Tier-0: Core Principles (ALWAYS Apply)

These 8 principles guide EVERY task. They are non-negotiable.

### 1. Defensive Programming
Fail fast and visibly when something is wrong. Silent failures hide bugs. Validate configuration at startup, not on first use. Explicitly detect operation failures (rowcount, status codes). No silent fallbacks or default values that hide error recovery. **Never assume data exists** without validating first. See [code-review skill](.claude/skills/code-review/).

### 2. Progressive Evidence Strengthening
Execution completion ≠ Operational success. Verify through increasingly strong evidence:
- **Layer 1 (Surface)**: Status codes, exit codes (weakest)
- **Layer 2 (Content)**: Payloads, data structures
- **Layer 3 (Observability)**: Traces, logs
- **Layer 4 (Ground truth)**: Actual state changes (strongest)

Never stop at weak evidence—progress until ground truth verified. See [error-investigation skill](.claude/skills/error-investigation/).

### 18. Logging Discipline (Storytelling Pattern)
Log for narrative reconstruction: ERROR (what failed), WARNING (unexpected), INFO (what happened), DEBUG (how). Logs are Layer 3 evidence.

**Narrative**: Beginning (context) → Middle (milestones) → End (✅/❌).

**Boundary logging**: WHERE you log determines WHAT survives Lambda failures. Log at handler boundaries.

See [Logging Discipline Guide](docs/guides/logging-discipline.md).

### 20. Execution Boundary Discipline
**Reading code ≠ Verifying code works.** Before concluding "correct", verify:
- WHERE does code run?
- WHAT environment required?
- WHAT systems called?
- WHAT entity properties?
- HOW verify contract?

See [Execution Boundary Discipline Guide](docs/guides/execution-boundary-discipline.md).

### 23. Configuration Variation Axis
Choose config mechanism by WHAT varies:
- **Secret** → Doppler
- **Environment-specific** → Doppler
- **Complex structure** → JSON file
- **Static** → Python constant

Read env vars ONCE at startup. See [Configuration Variation Guide](docs/guides/configuration-variation.md).

### 25. Behavioral Invariant Verification
Before claiming "done", verify the **invariant envelope**:
- **Level 0 (User)**: User can X
- **Level 1 (Service)**: Lambda returns Y
- **Level 2 (Data)**: Aurora has Z
- **Level 3 (Infra)**: A can reach B
- **Level 4 (Config)**: X is set to Y

**The Invariant Feedback Loop**:
```
/invariant → /reconcile → /invariant
  (detect)    (converge)   (verify)
```

Use `/invariant "goal"` to identify what must hold, `/reconcile domain` to fix violations, then `/invariant` again to verify delta = 0.

**Cascade Violation Pattern**: A single visible symptom often masks multiple sequential dependencies. When one fix reveals another violation, you're in a cascade. **Pre-scan ALL levels (4→3→2→1→0) BEFORE fixing anything.** This prevents the "fix-reveal-fix" loop:
```
❌ Wrong: Fix L1 → Discover L2 broken → Fix L2 → Discover L3 broken...
✅ Right: Scan L4→L3→L2→L1→L0 → Build dependency graph → Fix in order
```

**Dependency-Aware Reconciliation**: Violations have dependencies. Fix in dependency order:
1. **Config** (env vars, URLs, CORS) - foundation for everything
2. **Schema** (tables, columns) - foundation for data
3. **Data** (rows, relationships) - foundation for service
4. **Cache** (rankings, computed values) - derived from data
5. **Runtime** (verify user can X) - depends on all above

**Cache Invalidation Rule**: After populating data, verify cache reflects it. Either force refresh (`?force_refresh=true`) or wait for TTL expiry. Stale cache is a common "invisible" violation.

**Spec-Driven Development**: For long-running tasks, use specification files to maintain ground truth:
- **Create Feature Specs**: `/feature "name"` creates contractual specs in [.claude/specs/](.claude/specs/)
- **Specifications by Objective**: [.claude/specs/](.claude/specs/) - LINE Bot, Telegram, shared components
- **Environment Constraints**: local (mocks) → dev/stg (real APIs) → prd (real APIs + SLAs)
- **Convergence Tracking**: [.claude/state/convergence/](.claude/state/convergence/) - Track verification status

See [Behavioral Invariant Guide](docs/guides/behavioral-invariant-verification.md), [/feature](.claude/commands/feature.md), [/invariant](.claude/commands/invariant.md), [/reconcile](.claude/commands/reconcile.md), [Invariants Directory](.claude/invariants/), and [Specifications](.claude/specs/).

### 26. Thinking Tuple Protocol (Universal Kernel)

**Meta-Invariant**: Every reasoning episode runs through a Thinking Tuple. The tuple is the OS; commands are apps running on it.

```
Tuple = (Constraints, Invariant, Principles, Strategy, Check)
```

| Component | Question | Source |
|-----------|----------|--------|
| **Constraints** | What do we have/know? | Current state, specs, context |
| **Invariant** | What must be true at end? | Success criteria, `/invariant` |
| **Principles** | What tradeoffs guide us? | Tier-0 + task-specific clusters |
| **Strategy** | What modes to execute? | Pipeline of command-modes |
| **Check** | Did we satisfy invariant? | Progressive Evidence (Layers 1-4) |

**Strategy** is a pipeline of modes (commands as first-class functions):
```
Strategy = [
  { mode: "/decompose", prompt: "break the problem" },
  { mode: "/explore",   prompt: "find alternatives" },
  { mode: "/consolidate", prompt: "synthesize" }
]
```

**Tuple Router** (for any prompt, slash or plain):
| Intent | Default Strategy |
|--------|------------------|
| Goal-oriented (build X, fix Y) | `[/step]` |
| Exploration (what are options) | `[/explore]` |
| Verification (is X correct) | `[/validate]` |
| Explanation (how does X work) | `[/understand]` |
| Comparison (X vs Y) | `[/what-if]` |
| Causal analysis (why X) | `[/trace]` |

**Check Loop**: After Strategy completes, evaluate Invariant. If insufficient, extend Strategy or spin new tuple with updated Constraints.

**Error bound**: Without tuples, error ∝ (steps × drift). With tuples, error bounded by check frequency.

See [Thinking Tuple Guide](docs/guides/thinking-tuple-protocol.md), [/step command](.claude/commands/step.md), and [Tuple Architecture](.claude/diagrams/tuple-kernel-architecture.md).

### 27. Commands as Strategy Modes

Commands are not independent—they are **modes within Strategy**. Each mode defines:
- **Tuple Effects**: How it modifies Constraints, Invariant, Principles
- **Local Check**: Mode-specific completion criteria

| Command | Mode | Tuple Effect |
|---------|------|--------------|
| `/step` | goal_oriented | Full tuple control |
| `/explore` | divergent | Expands Constraints with alternatives |
| `/understand` | clarify | Refines Invariant with understanding criteria |
| `/validate` | verify | Tests Invariant, annotates Check |
| `/what-if` | compare | Adds alternatives to Constraints |
| `/consolidate` | converge | Synthesizes Constraints into decision |
| `/trace` | causal | Adds causal chain to Constraints |
| `/decompose` | decompose | Breaks Invariant into sub-invariants |
| `/feature` | define | Populates Constraints + Invariant from spec files |
| `/invariant` | scan | Evaluates Check against specification |
| `/reconcile` | fix | Executes Actions to satisfy Invariant |
| `/qna` | probe | Reveals Constraints (knowledge state) for user verification |
| `/pay-debt` | analyze | Reveals Constraints (debt inventory) + defines Invariant (targets) |
| `/transfer` | transform | **Foundation**: Transform(X, A, B, Invariants) → X' |
| `/adapt` | transform | Specialization: code, external→internal, adapt |
| `/provision-env` | transform | Specialization: infra, internal→internal, copy |
| `/perf` | observe | Reveals performance Constraints from CloudWatch metrics |
| `/optimize` | transform | Transforms Constraints while maintaining Invariant stability (Tier-2) |

**Chaining**: Strategy can chain modes. Each mode updates tuple state before next mode executes.

**Internal Modes**: Beyond slash commands, internal modes exist for micro-operations:
- `summarize`, `rewrite_simple`, `extract_criteria`, `compare_two`

See [Command Mode Specifications](.claude/commands/README.md).

### 28. Compositional Hierarchy (Meta-Architectural Principle)

> "Everything is layered. Make the layers explicit."

**Core Concept**: Tier-N composition replaces undifferentiated "references" with structured relationships.

**Relationship Taxonomy**:
| Relationship | Direction | Meaning | Example |
|--------------|-----------|---------|---------|
| `composes` | Higher → Lower | Builds on, combines | Tier-2 skill → Tier-1 skills |
| `depends` | Same/Cross tier | Requires, doesn't build | Skill → external library |
| `invokes` | Cross-domain | Calls as capability | Command → skill |
| `grounds` | Meta → Instance | Provides foundation | Principle → implementation |

**Universal Tier Structure**:
```
Tier-0: Core/Atomic (always present, self-contained)
Tier-1: Modular (reusable, independent)
Tier-2: Composed (builds on Tier-1)
Tier-N: Higher composition (builds on lower tiers)
```

**Applied Across Domains**:
| Domain | Tier-0 | Tier-1 | Tier-2+ |
|--------|--------|--------|---------|
| Principles | Core (#1,2,18,20,23,25-28) | Domain clusters | Task-specific |
| Skills | — | Modular (prompt-eng, testing) | Composed (report-workflow) |
| Commands | Atomic (/explore, /validate) | — | Orchestrated (/optimize, /analysis) |
| Invariants | Level 4 (config) | Levels 3-2 (infra, data) | Levels 1-0 (service, user) |
| Tests | Tier-0 (unit) | Tier-1-2 (integration) | Tier-3-4 (e2e) |

**Why This Matters**:
- **Clarity**: "A composes B" is more precise than "A references B"
- **Reusability**: Tier-1 modules can be composed into multiple Tier-2 solutions
- **Maintainability**: Changes to Tier-1 automatically benefit all Tier-2 dependents
- **Cognitive load**: Hierarchical structure is easier to navigate than flat references

See [Compositional Hierarchy Guide](.claude/principles/compositional-hierarchy.md).

---

## Principle Routing Index

**Load additional principles based on current task:**

| If doing... | Load cluster | Principles |
|-------------|--------------|------------|
| **Deploying** | [deployment-principles](.claude/principles/deployment-principles.md) | #6, #11, #15, #19, #21 |
| **Writing tests** | [testing-principles](.claude/principles/testing-principles.md) | #10, #19 |
| **Aurora/data work** | [data-principles](.claude/principles/data-principles.md) | #3, #5, #14, #16 |
| **Secrets/config** | [configuration-principles](.claude/principles/configuration-principles.md) | #13, #24 |
| **API/error handling** | [integration-principles](.claude/principles/integration-principles.md) | #4, #7, #8, #22 |
| **Debugging/analysis** | [meta-principles](.claude/principles/meta-principles.md) | #9, #12, #17 |

See [Principles Index](.claude/principles/index.md) for keyword triggers and multi-cluster scenarios.

---

## Quick Principle Reference

| # | Principle | Tier | Cluster |
|---|-----------|------|---------|
| 1 | Defensive Programming | 0 | Core |
| 2 | Progressive Evidence | 0 | Core |
| 3 | Aurora-First Data | 1 | Data |
| 4 | Type System Integration | 2 | Integration |
| 5 | Database Migrations | 2 | Data |
| 6 | Deployment Monitoring | 2 | Deployment |
| 7 | Loud Mock Pattern | 2 | Integration |
| 8 | Error Handling Duality | 2 | Integration |
| 9 | Feedback Loop Awareness | 3 | Meta |
| 10 | Testing Anti-Patterns | 2 | Testing |
| 11 | Artifact Promotion | 2 | Deployment |
| 12 | OWL Relationship Analysis | 3 | Meta |
| 13 | Secret Management | 2 | Configuration |
| 14 | Table Name Centralization | 1 | Data |
| 15 | Infrastructure-App Contract | 2 | Deployment |
| 16 | Timezone Discipline | 1 | Data |
| 17 | Shared Virtual Environment | 3 | Meta |
| 18 | Logging Discipline | 0 | Core |
| 19 | Cross-Boundary Testing | 2 | Testing/Deployment |
| 20 | Execution Boundary | 0 | Core |
| 21 | Deployment Blocker | 2 | Deployment |
| 22 | LLM Observability | 2 | Integration |
| 23 | Configuration Variation | 0 | Core |
| 24 | External Service Credentials | 2 | Configuration |
| 25 | Behavioral Invariant | 0 | Core |
| 26 | Thinking Tuple Protocol (Universal Kernel) | 0 | Core |
| 27 | Commands as Strategy Modes | 0 | Core |
| 28 | Compositional Hierarchy | 0 | Core |

---

## Extension Points

1. **Adding Scoring Metrics**: Create scorer class in `src/scoring/` → integrate into `src/workflow/workflow_nodes.py` → extend `AgentState` TypedDict in `src/types.py`. See [Project Conventions](docs/PROJECT_CONVENTIONS.md#extension-points).

2. **Adding CLI Commands**: Create command in `dr_cli/commands/<group>.py` with Click decorators → add Justfile recipe for intent layer. Two-layer design: Justfile (WHEN/WHY), dr CLI (HOW).

3. **Extending State**: Update `AgentState` TypedDict in `src/types.py` → add workflow node that populates field. All state fields must be JSON-serializable for Lambda responses.

4. **Adding API Endpoints**: Create service singleton → define Pydantic models → add FastAPI route → write integration tests. Follow async/sync dual method pattern for LangGraph compatibility.

---

## References

- **Specifications**: [.claude/specs/](.claude/specs/) - Spec-driven development by objective (LINE Bot, Telegram, shared)
- **Convergence State**: [.claude/state/](.claude/state/) - Runtime verification and checkpoint tracking
- **Principle Clusters**: [.claude/principles/](.claude/principles/) - Context-specific principles by task/domain
- **Project Conventions**: [docs/PROJECT_CONVENTIONS.md](docs/PROJECT_CONVENTIONS.md) - Directory structure, naming patterns, CLI commands
- **Implementation Guides**: [docs/guides/README.md](docs/guides/README.md) - Comprehensive how-to guides
- **Skills**: [.claude/skills/README.md](.claude/skills/README.md) - Executable workflows and checklists
- **Documentation**: [docs/README.md](docs/README.md) - Complete documentation index
- **Invariants**: [.claude/invariants/](.claude/invariants/) - System invariant checklists
- **Architecture Decisions**: [docs/adr/README.md](docs/adr/README.md) - ADRs for major technology choices
- **Deployment**: [docs/deployment/](docs/deployment/) - Complete deployment guides and runbooks
- **Code Style**: [docs/CODE_STYLE.md](docs/CODE_STYLE.md) - Detailed coding patterns and conventions
