# X-Ray: Agent Kernel Architecture

**Date**: 2026-01-13 (Updated: 2026-01-16)
**Scope**: .claude/*, slash commands, skills, thinking process, principles interconnection

---

## Executive Summary

**Architecture Pattern**: **Agent Kernel** - A hierarchical knowledge system with 4 layers

> **Agent Kernel** = The complete knowledge system that powers Claude's reasoning in this project. See [CLAUDE.md](../CLAUDE.md#agent-kernel) for the canonical definition.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION LAYER                               │
│   Natural Language  ←→  /commands  ←→  Claude Code Session                 │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                                  │
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│   │  /commands  │    │   Skills    │    │ CLAUDE.md   │                    │
│   │  (40+ cmds) │    │  (15 dirs)  │    │ (Tier-0)    │                    │
│   │             │    │             │    │             │                    │
│   │ Explicit    │    │ Implicit    │    │ Always-On   │                    │
│   │ User-Invoke │    │ Auto-Load   │    │ Principles  │                    │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                    │
│          │                  │                  │                           │
│          └────────────┬─────┴──────────────────┘                           │
│                       ▼                                                     │
│              ┌────────────────┐                                            │
│              │ Claude's Mind  │                                            │
│              │  (Cognition)   │                                            │
│              └────────────────┘                                            │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────────┐
│                        KNOWLEDGE LAYER                                      │
│                                                                             │
│  .claude/principles/    .claude/invariants/    .claude/diagrams/           │
│  .claude/skills/        .claude/journals/      .claude/what-if/            │
│  .claude/validations/   .claude/abstractions/  .claude/explorations/       │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────────┐
│                        EXECUTION LAYER                                      │
│   Tools (Read, Write, Edit, Bash, Grep, Glob)  |  MCP (AWS, GitHub)        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Inventory

### 1. Slash Commands (`.claude/commands/`) - 40+ Commands

**Purpose**: User-invokable workflows that orchestrate Claude's behavior

**Categories**:

| Category | Commands | Purpose |
|----------|----------|---------|
| **Metacognitive** | `/reflect`, `/trace`, `/hypothesis`, `/proof` | Thinking about thinking |
| **Workflow** | `/explore`, `/design`, `/deploy`, `/analysis` | Task execution patterns |
| **Decision** | `/what-if`, `/compare`, `/validate`, `/impact` | Evaluate alternatives |
| **Utility** | `/journal`, `/abstract`, `/consolidate`, `/report` | Knowledge capture |
| **Git Worktree** | `/wt-spin-off`, `/wt-merge`, `/wt-list`, `/wt-remove` | Parallel agent work |
| **Environment** | `/dev`, `/stg`, `/prd`, `/local` | Target-specific execution |
| **Invariant** | `/invariant`, `/reconcile` | Behavioral verification |

---

### 2. Skills (`.claude/skills/`) - 15 Domains

**Purpose**: Auto-discovered domain knowledge that guides HOW to approach tasks

```
.claude/skills/
├── code-review/          # Security, performance, defensive programming
├── testing-workflow/     # Test tiers, patterns, anti-patterns
├── deployment/           # Zero-downtime, multi-env, validation
├── database-migration/   # Aurora MySQL, reconciliation patterns
├── error-investigation/  # Multi-layer verification, CloudWatch
├── langfuse-observability/  # LLM tracing, scoring
├── research/             # Investigation methodology
├── refacter/             # Complexity analysis, hotspots
├── frontend-design/      # React, UI patterns
├── telegram-uiux/        # Telegram Mini App patterns
├── line-uiux/            # LINE Bot (legacy maintenance)
├── data-visualization/   # Charts, mathematical overlays
├── pdf/                  # PDF manipulation
├── webapp-testing/       # Playwright testing
└── infrastructure-verification/  # VPC, NAT, security groups
```

---

### 3. Principles (`.claude/CLAUDE.md` + `.claude/principles/`)

**Purpose**: Codified wisdom - WHY things should be done a certain way

**Tiered Structure**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIER-0: Core (Always Apply)                  │
│                                                                 │
│  #1  Defensive Programming     #20 Execution Boundary           │
│  #2  Progressive Evidence      #23 Configuration Variation      │
│  #18 Logging Discipline        #25 Behavioral Invariant         │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  DEPLOYMENT   │   │     DATA      │   │  INTEGRATION  │
│  PRINCIPLES   │   │  PRINCIPLES   │   │  PRINCIPLES   │
│               │   │               │   │               │
│ #6  Monitor   │   │ #3  Aurora    │   │ #4  Types     │
│ #11 Artifact  │   │ #5  Migration │   │ #7  Mocks     │
│ #15 Contract  │   │ #14 Tables    │   │ #8  Errors    │
│ #19 Boundary  │   │ #16 Timezone  │   │ #22 Langfuse  │
│ #21 Blocker   │   │               │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    TESTING    │   │ CONFIGURATION │   │     META      │
│  PRINCIPLES   │   │  PRINCIPLES   │   │  PRINCIPLES   │
│               │   │               │   │               │
│ #10 Anti-Pat  │   │ #13 Secrets   │   │ #9  Feedback  │
│ #19 Cross-Bnd │   │ #24 External  │   │ #12 OWL       │
│               │   │               │   │ #17 Shared    │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

### 4. Invariants (`.claude/invariants/`)

**Purpose**: Behavioral contracts that must hold true

```
.claude/invariants/
├── system-invariants.md       # Always verify (critical path)
├── deployment-invariants.md   # CI/CD, Lambda, Terraform
├── data-invariants.md         # Aurora, migrations, timezone
├── api-invariants.md          # Endpoints, contracts
├── langfuse-invariants.md     # Tracing, scoring
└── frontend-invariants.md     # React, state, charts
```

**Invariant Levels (5-tier verification)**:
```
Level 0 (User)    →  User experience works
Level 1 (Service) →  Lambda returns correctly
Level 2 (Data)    →  Aurora has correct data
Level 3 (Infra)   →  Connectivity works
Level 4 (Config)  →  Settings correct
```

---

## Relationship Diagram: Full System

```
                         ┌─────────────────────────────────────┐
                         │            USER REQUEST             │
                         │   "Deploy new scoring feature"      │
                         └─────────────────┬───────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │  SLASH COMMAND  │        │     SKILLS      │        │   PRINCIPLES    │
    │                 │        │                 │        │                 │
    │ /deploy         │◄──────►│ deployment/     │◄──────►│ Tier-0: #1,#2   │
    │ /invariant      │        │ langfuse-obs/   │        │ deployment: #6  │
    │ /reconcile      │        │ testing-wkflow/ │        │ #11, #15, #21   │
    └────────┬────────┘        └────────┬────────┘        └────────┬────────┘
             │                          │                          │
             │    ┌─────────────────────┴──────────────────────┐   │
             │    │                                            │   │
             ▼    ▼                                            ▼   ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                        CLAUDE'S COGNITION                            │
    │                                                                      │
    │  1. Load command template (workflow steps)                           │
    │  2. Auto-discover relevant skills (domain knowledge)                 │
    │  3. Apply Tier-0 principles (always active)                          │
    │  4. Load context-specific principles (based on task)                 │
    │  5. Execute with feedback loops (metacognitive awareness)            │
    │                                                                      │
    └──────────────────────────────────┬───────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────────┐
              │                        │                            │
              ▼                        ▼                            ▼
    ┌─────────────────┐    ┌─────────────────┐        ┌─────────────────┐
    │   INVARIANTS    │    │  THINKING PROC  │        │   KNOWLEDGE     │
    │                 │    │                 │        │    ARTIFACTS    │
    │ deployment-inv  │    │ Feedback Loops: │        │                 │
    │ langfuse-inv    │    │ - Retrying      │        │ journals/       │
    │                 │    │ - Branching     │        │ abstractions/   │
    │ Level 0-4       │    │ - Synchronizing │        │ what-if/        │
    │ Verification    │    │ - Meta-loop     │        │ validations/    │
    └────────┬────────┘    └────────┬────────┘        └────────┬────────┘
             │                      │                          │
             └──────────────────────┴──────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────────────────┐
                         │         EXECUTION LAYER             │
                         │                                     │
                         │  Tools: Read, Write, Edit, Bash     │
                         │  MCP: AWS CloudWatch, GitHub        │
                         └─────────────────────────────────────┘
```

---

## Information Flow Patterns

### Pattern 1: Command → Skill → Principle

```
User: /deploy "new scoring feature"
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ COMMAND: /deploy                                                │
│                                                                 │
│ 1. Load workflow: pre-deploy → deploy → post-deploy → verify   │
│ 2. Trigger skill discovery                                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SKILL: deployment/                                              │
│                                                                 │
│ 1. Zero-downtime deployment pattern                             │
│ 2. AWS waiter usage (wait for Lambda update)                    │
│ 3. Smoke test after deploy                                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PRINCIPLES:                                                     │
│                                                                 │
│ Tier-0: #2 (Progressive Evidence) → Verify weak → strong        │
│ Deployment: #6 (Monitoring) → Use waiters, not sleep            │
│ Deployment: #11 (Artifact) → Build once, promote                │
│ Deployment: #15 (Contract) → Infra matches app expectations     │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Invariant Feedback Loop

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       INVARIANT FEEDBACK LOOP                            │
│                                                                          │
│    /invariant "goal"          /reconcile            /invariant "goal"    │
│         │                          │                       │             │
│         ▼                          ▼                       ▼             │
│    ┌─────────┐              ┌─────────────┐          ┌─────────┐         │
│    │ DETECT  │─────────────►│  CONVERGE   │─────────►│ VERIFY  │         │
│    │         │  violations  │             │  fixes   │         │         │
│    │ What    │              │ How to fix  │          │ Delta=0 │         │
│    │ must    │              │ violations  │          │         │         │
│    │ hold?   │              │             │          │ Done!   │         │
│    └─────────┘              └─────────────┘          └─────────┘         │
│         │                          │                       │             │
│         ▼                          ▼                       ▼             │
│   invariants/*.md           Fix templates           All verified         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Pattern 3: Knowledge Graduation Pipeline

```
                     TIME →

OBSERVATION      ABSTRACTION      PRINCIPLE       SKILL
(single event)   (pattern)        (WHY)           (HOW)
     │                │               │               │
     ▼                ▼               ▼               ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ observe │────►│ abstract│────►│ journal │────►│ skill/  │
│ failure │     │ pattern │     │ decision│     │ CLAUDE  │
│         │     │         │     │         │     │ .md     │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     │                │               │               │
     ▼                ▼               ▼               ▼
observations/   abstractions/   journals/      skills/
                               principles/     CLAUDE.md

Example:
"Lambda timed out"  →  "NAT Gateway saturation"  →  Principle #15  →  deployment skill
```

---

## Thinking Process Architecture Integration

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    THINKING PROCESS ARCHITECTURE                          │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         METACOGNITIVE LAYER                         │  │
│  │                                                                     │  │
│  │   /reflect    /trace    /hypothesis    /proof    /what-if           │  │
│  │      │           │           │            │           │             │  │
│  │      └───────────┴───────────┴────────────┴───────────┘             │  │
│  │                              │                                      │  │
│  │                              ▼                                      │  │
│  │                    FEEDBACK LOOP SELECTION                          │  │
│  │                                                                     │  │
│  │   Retrying Loop ─────► Initial-Sensitive ─────► Branching Loop      │  │
│  │   (fix execution)        (change assumptions)   (try diff path)     │  │
│  │         │                      │                      │             │  │
│  │         └──────────────────────┴──────────────────────┘             │  │
│  │                              │                                      │  │
│  │                              ▼                                      │  │
│  │                    META-LOOP (if stuck)                             │  │
│  │                    "Am I using the right loop type?"                │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      PROGRESSIVE EVIDENCE                           │  │
│  │                                                                     │  │
│  │   Layer 1        Layer 2        Layer 3         Layer 4             │  │
│  │   (Surface)      (Content)      (Observability) (Ground Truth)      │  │
│  │      │              │               │               │               │  │
│  │   Status code    Payload        Logs/Traces      Actual state       │  │
│  │      │              │               │               │               │  │
│  │      └──────────────┴───────────────┴───────────────┘               │  │
│  │                              │                                      │  │
│  │                              ▼                                      │  │
│  │                    Never stop at weak evidence                      │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Purpose Map

```
.claude/
├── CLAUDE.md                 # Ground truth - Tier-0 principles (ALWAYS LOADED)
│
├── commands/                 # USER-INVOKABLE workflows
│   ├── invariant.md         #   /invariant - identify what must hold
│   ├── reconcile.md         #   /reconcile - converge violations
│   ├── deploy.md            #   /deploy - deployment workflow
│   └── ...40+ more          #   Each defines: steps, args, output format
│
├── skills/                   # AUTO-DISCOVERED domain knowledge
│   ├── deployment/          #   HOW to deploy safely
│   ├── testing-workflow/    #   HOW to write good tests
│   ├── error-investigation/ #   HOW to debug systematically
│   └── ...12 more           #   Claude loads when task matches domain
│
├── principles/               # CONTEXT-SPECIFIC principles (Tier 1-3)
│   ├── index.md             #   Routing table: task → principle cluster
│   ├── deployment-principles.md
│   ├── data-principles.md
│   └── ...4 more            #   WHY to do things certain way
│
├── invariants/               # BEHAVIORAL CONTRACTS (must hold true)
│   ├── system-invariants.md #   Critical path (always verify)
│   ├── deployment-invariants.md
│   └── ...4 domain files    #   WHAT must remain true
│
├── diagrams/                 # ARCHITECTURE DIAGRAMS
│   └── thinking-process-architecture.md
│
├── journals/                 # DECISION RECORDS (historical)
│   ├── architecture/        #   Why we chose X over Y
│   ├── error/               #   How we solved bug Z
│   └── meta/                #   Process improvements
│
├── abstractions/             # EXTRACTED PATTERNS
│   └── architecture-*.md    #   Generalized from specific events
│
├── what-if/                  # SCENARIO ANALYSES
│   └── 2025-*.md            #   What if we did X instead of Y?
│
├── validations/              # CLAIM VERIFICATIONS
│   └── 2026-*.md            #   Evidence that X is true
│
├── explorations/             # OPEN-ENDED RESEARCH
│   └── 2025-*.md            #   Understanding how X works
│
├── bug-hunts/                # SYSTEMATIC INVESTIGATIONS
│   └── 2025-*.md            #   Root cause analysis
│
└── reports/                  # SESSION SUMMARIES
    └── 2026-*.md            #   What was accomplished
```

---

## Trade-Off Analysis

| Trade-off | Current Position | Rationale |
|-----------|------------------|-----------|
| **Explicit vs Implicit** | Skills=implicit, Commands=explicit | Users invoke commands, skills auto-load based on context |
| **Centralized vs Distributed** | Tier-0 centralized, rest distributed | Core principles always apply, others loaded on-demand |
| **Flat vs Hierarchical** | Hierarchical (principles → skills → commands) | Clear dependency flow, reduces cognitive load |
| **Prescriptive vs Descriptive** | Principles=descriptive, Skills=prescriptive | WHY vs HOW separation |
| **Static vs Dynamic** | Principles static, knowledge artifacts dynamic | Stable core, evolving insights |

---

## Assessment

### Strengths
- Clear separation: Commands (WHAT), Skills (HOW), Principles (WHY)
- Tiered loading: Token-efficient (~60% reduction)
- Feedback loop: /invariant → /reconcile → /invariant
- Knowledge graduation: Observations → Abstractions → Principles

### Observations for Further Investigation
- Consider `/what-if "merge skills and invariants"` - some overlap
- Consider `/design "cross-referencing system"` - improve discoverability
- Consider `/evolve` - detect principle drift from practice

---

## See Also

- [Previous X-ray: Knowledge Architecture (2026-01-12)](./2026-01-12-xray-knowledge-architecture.md)
- [Thinking Process Architecture](../diagrams/thinking-process-architecture.md)
- [Principles Index](../principles/index.md)
- [Invariants README](../invariants/README.md)
- [Commands README](../commands/README.md)
- [Skills README](../skills/README.md)

---

*Report generated by `/x-ray`*
*Date: 2026-01-13*
