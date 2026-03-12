# X-Ray: Claude Knowledge Architecture

**Date**: 2026-01-12
**Scope**: Organization and interconnection of `.claude/*`, `docs/*`, slash commands, skills, and principles

---

## Executive Summary

**Architecture Pattern**: **Tiered Knowledge Graph** with separation of concerns by purpose (WHY → WHAT → HOW) and abstraction level (Principles → Guides → Skills → Commands)

**Key Observations**:
- **3-layer knowledge hierarchy**: Principles (WHY) → Guides/Skills (HOW) → Commands (Orchestration)
- **Tier-based loading**: Core always loaded, context-specific on demand (~60% token savings)
- **Dual invocation model**: Skills (auto-discovered) vs Commands (explicit user control)
- **Graduation pipeline**: Abstractions → Principles → Guides → Skills

---

## Component Inventory

| Directory | Files | Purpose | Invocation |
|-----------|-------|---------|------------|
| `.claude/CLAUDE.md` | 1 | Ground truth contract, Tier-0 principles | Auto-loaded |
| `.claude/principles/` | 8 | Context-specific principle clusters | On-demand by task |
| `.claude/commands/` | 50 | Slash command orchestration | Explicit `/command` |
| `.claude/skills/` | 14 skills (61 files) | Domain expertise workflows | Auto-discovered |
| `.claude/invariants/` | 3 | System behavioral invariants | Referenced |
| `.claude/abstractions/` | ~30 | Pattern analysis (pre-principle) | Archive |
| `docs/guides/` | 12 | Implementation how-to guides | Referenced |
| `docs/*.md` | 118 total | Project documentation | Referenced |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           KNOWLEDGE ARCHITECTURE                                     │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        LAYER 1: PRINCIPLES (WHY)                            │    │
│  │                                                                              │    │
│  │   ┌──────────────────────────────────────────────────────────────────┐      │    │
│  │   │                     .claude/CLAUDE.md                            │      │    │
│  │   │  ┌───────────────────────────────────────────────────────────┐   │      │    │
│  │   │  │ Tier-0: ALWAYS APPLY (6 principles)                       │   │      │    │
│  │   │  │  #1 Defensive Programming                                 │   │      │    │
│  │   │  │  #2 Progressive Evidence Strengthening                    │   │      │    │
│  │   │  │  #18 Logging Discipline                                   │   │      │    │
│  │   │  │  #20 Execution Boundary Discipline                        │   │      │    │
│  │   │  │  #23 Configuration Variation                              │   │      │    │
│  │   │  │  #25 Behavioral Invariant Verification                    │   │      │    │
│  │   │  └───────────────────────────────────────────────────────────┘   │      │    │
│  │   │                           │                                       │      │    │
│  │   │                   Routing Index                                   │      │    │
│  │   │                           │                                       │      │    │
│  │   └───────────────────────────┼──────────────────────────────────────┘      │    │
│  │                               ▼                                              │    │
│  │   ┌──────────────── .claude/principles/ ─────────────────────────┐          │    │
│  │   │                                                               │          │    │
│  │   │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │          │    │
│  │   │  │ deployment-     │  │ data-           │  │ testing-     │  │          │    │
│  │   │  │ principles.md   │  │ principles.md   │  │ principles.md│  │          │    │
│  │   │  │ #6,#11,#15,     │  │ #3,#5,#14,#16   │  │ #10,#19      │  │          │    │
│  │   │  │ #19,#21         │  │                 │  │              │  │          │    │
│  │   │  └─────────────────┘  └─────────────────┘  └──────────────┘  │          │    │
│  │   │                                                               │          │    │
│  │   │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │          │    │
│  │   │  │ configuration-  │  │ integration-    │  │ meta-        │  │          │    │
│  │   │  │ principles.md   │  │ principles.md   │  │ principles.md│  │          │    │
│  │   │  │ #13,#24         │  │ #4,#7,#8,#22    │  │ #9,#12,#17   │  │          │    │
│  │   │  └─────────────────┘  └─────────────────┘  └──────────────┘  │          │    │
│  │   └───────────────────────────────────────────────────────────────┘          │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                         │                                            │
│                          ┌──────────────┼──────────────┐                            │
│                          ▼              ▼              ▼                            │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                    LAYER 2: IMPLEMENTATION (HOW)                               │  │
│  │                                                                                │  │
│  │  ┌─────────────────────────┐    ┌──────────────────────────────────────────┐  │  │
│  │  │     docs/guides/        │    │           .claude/skills/                │  │  │
│  │  │  (Implementation Guides)│    │        (Executable Workflows)            │  │  │
│  │  │                         │    │                                          │  │  │
│  │  │  • behavioral-invariant-│    │  ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │  │
│  │  │    verification.md      │    │  │ testing- │ │deployment│ │code-    │  │  │  │
│  │  │  • cross-boundary-      │◄───┼──│ workflow │ │          │ │review   │  │  │  │
│  │  │    contract-testing.md  │    │  │ SKILL.md │ │ SKILL.md │ │SKILL.md │  │  │  │
│  │  │  • execution-boundary-  │    │  └──────────┘ └──────────┘ └─────────┘  │  │  │
│  │  │    discipline.md        │    │                                          │  │  │
│  │  │  • deployment-blocker-  │    │  ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │  │
│  │  │    resolution.md        │    │  │telegram- │ │ refacter │ │research │  │  │  │
│  │  │  • infrastructure-      │    │  │uiux      │ │          │ │         │  │  │  │
│  │  │    application-         │    │  │ SKILL.md │ │ SKILL.md │ │SKILL.md │  │  │  │
│  │  │    contract.md          │    │  └──────────┘ └──────────┘ └─────────┘  │  │  │
│  │  │  • logging-discipline   │    │                                          │  │  │
│  │  │  • timezone-discipline  │    │  ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │  │
│  │  │  • langfuse-integration │    │  │ error-   │ │ database │ │langfuse │  │  │  │
│  │  │  • etc.                 │    │  │ invest-  │ │-migration│ │observ-  │  │  │  │
│  │  │                         │    │  │ igation  │ │          │ │ability  │  │  │  │
│  │  └─────────────────────────┘    │  └──────────┘ └──────────┘ └─────────┘  │  │  │
│  │                                  │                                          │  │  │
│  │                                  │  + data-visualization, pdf,             │  │  │
│  │                                  │    infrastructure-verification,         │  │  │
│  │                                  │    webapp-testing, line-uiux,           │  │  │
│  │                                  │    frontend-design                      │  │  │
│  │                                  └──────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                         │                                            │
│                          ┌──────────────┴──────────────┐                            │
│                          ▼                              ▼                            │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                  LAYER 3: ORCHESTRATION (USER CONTROL)                         │  │
│  │                                                                                │  │
│  │   ┌─────────────────────── .claude/commands/ ─────────────────────────────┐   │  │
│  │   │                        (50 Slash Commands)                             │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ METACOGNITIVE (Thinking about thinking)                         │  │   │  │
│  │   │  │  /reflect, /trace, /hypothesis, /proof, /decompose              │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ WORKFLOW (Task execution)                                       │  │   │  │
│  │   │  │  /deploy, /bug-hunt, /design, /adapt, /provision-env            │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ DECISION (Analysis & comparison)                                │  │   │  │
│  │   │  │  /what-if, /compare, /impact, /explore, /analysis               │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ UTILITY (Environment & knowledge management)                    │  │   │  │
│  │   │  │  /dev, /stg, /prd, /local, /journal, /consolidate, /evolve      │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ INSPECTION (Reveal existing)                                    │  │   │  │
│  │   │  │  /x-ray, /validate, /locate, /check-principles, /understand     │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐  │   │  │
│  │   │  │ GIT-WORKTREE (Parallel development)                             │  │   │  │
│  │   │  │  /wt-spin-off, /wt-merge, /wt-list, /wt-remove                  │  │   │  │
│  │   │  └─────────────────────────────────────────────────────────────────┘  │   │  │
│  │   │                                                                        │   │  │
│  │   └────────────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                      SUPPORTING STRUCTURES                                     │  │
│  │                                                                                │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐   │  │
│  │  │ .claude/invariants/ │  │ .claude/abstractions│  │ docs/ (118 files)   │   │  │
│  │  │ (System invariants) │  │ (Pattern analysis)  │  │                     │   │  │
│  │  │                     │  │                     │  │ • PROJECT_CONVENTIONS│   │  │
│  │  │ • system-invariants │  │ • Pre-principle     │  │ • CODE_STYLE        │   │  │
│  │  │ • TEMPLATE.md       │  │   patterns          │  │ • TESTING_GUIDE     │   │  │
│  │  │                     │  │ • Graduation queue  │  │ • deployment/       │   │  │
│  │  │   Referenced by     │  │                     │  │ • architecture/     │   │  │
│  │  │   Principle #25     │  │   Graduates to →    │  │ • adr/              │   │  │
│  │  │                     │  │   principles        │  │ • features/         │   │  │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Interconnection Map

```
                            ┌─────────────────────────────────────────┐
                            │        USER REQUEST / CONTEXT           │
                            └──────────────────┬──────────────────────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         ▼                     ▼                     ▼
                   ┌──────────┐         ┌──────────┐         ┌──────────┐
                   │ Explicit │         │   Auto   │         │ Context  │
                   │ /command │         │Discovery │         │ Loading  │
                   └────┬─────┘         └────┬─────┘         └────┬─────┘
                        │                    │                    │
                        ▼                    ▼                    ▼
              ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
              │   COMMANDS (50)  │  │   SKILLS (14)    │  │   PRINCIPLES     │
              │                  │  │                  │  │                  │
              │ User control:    │  │ Claude control:  │  │ Always loaded:   │
              │ /design          │  │ testing-workflow │  │ CLAUDE.md Tier-0 │
              │ /deploy          │  │ deployment       │  │                  │
              │ /bug-hunt        │  │ code-review      │  │ On-demand:       │
              │ /validate        │  │ telegram-uiux    │  │ /principles/*    │
              └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                       │                     │                     │
                       │    ┌────────────────┼────────────────┐    │
                       │    │                │                │    │
                       ▼    ▼                ▼                ▼    ▼
              ┌───────────────────────────────────────────────────────────┐
              │                    REFERENCE LAYER                        │
              │                                                           │
              │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
              │  │ docs/guides │  │   docs/*    │  │ .claude/        │   │
              │  │ (HOW-TO)    │  │ (REFERENCE) │  │ invariants/     │   │
              │  │             │  │             │  │ (MUST BE TRUE)  │   │
              │  │ 12 guides   │  │ 118 files   │  │                 │   │
              │  └─────────────┘  └─────────────┘  └─────────────────┘   │
              └───────────────────────────────────────────────────────────┘
```

---

## Relationship Types

### 1. Principles → Skills (Implements)
```
Principle #25 (Behavioral Invariant)
    ├── testing-workflow/SKILL.md (Invariant Testing section)
    └── deployment/SKILL.md (Invariant Verification section)

Principle #2 (Progressive Evidence)
    ├── error-investigation/SKILL.md (Evidence layers)
    └── deployment/SKILL.md (Verification workflow)

Principle #22 (LLM Observability)
    └── langfuse-observability/SKILL.md (Full implementation)
```

### 2. Principles → Guides (Explains)
```
Principle #20 (Execution Boundary) → docs/guides/execution-boundary-discipline.md
Principle #19 (Cross-Boundary) → docs/guides/cross-boundary-contract-testing.md
Principle #25 (Behavioral Invariant) → docs/guides/behavioral-invariant-verification.md
Principle #15 (Infra-App Contract) → docs/guides/infrastructure-application-contract.md
```

### 3. Commands → Skills (Invokes)
```
/bug-hunt → error-investigation skill
/design → code-review skill (for validation)
/deploy → deployment skill
/refacter → refacter skill
```

### 4. Commands → Principles (References)
```
/check-principles → All 25 principles
/reflect → Principle #9 (Feedback Loops)
/trace → Principle #2 (Progressive Evidence)
/adapt → Principles #1, #3, #8, #18, #19
```

### 5. Skills → Skills (Cross-references)
```
testing-workflow → deployment (deployment fidelity testing)
telegram-uiux → testing-workflow (property-based testing)
deployment → testing-workflow (pre-deployment tests)
```

---

## Information Flow Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE FLOW PATTERNS                                 │
│                                                                                 │
│  Pattern 1: PRINCIPLE PROPAGATION (WHY → HOW)                                  │
│  ═══════════════════════════════════════════                                   │
│                                                                                 │
│  CLAUDE.md Tier-0     →   Principle Cluster    →   Implementation Guide        │
│  (Condensed WHY)          (Full principle)         (Detailed HOW)              │
│       │                        │                        │                       │
│       └────────────────────────┼────────────────────────┘                       │
│                                ▼                                                │
│                          Skill SKILL.md                                         │
│                       (Executable workflow)                                     │
│                                                                                 │
│  Example:                                                                       │
│  CLAUDE.md #25 → .claude/principles/deployment-principles.md                   │
│       → docs/guides/behavioral-invariant-verification.md                       │
│       → .claude/skills/testing-workflow/SKILL.md#invariant-testing             │
│                                                                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Pattern 2: COMMAND ORCHESTRATION (User → Multi-tool)                          │
│  ════════════════════════════════════════════════════                          │
│                                                                                 │
│     User                                                                        │
│       │                                                                         │
│       ▼                                                                         │
│  /command arg    →   Loads principles   →   Invokes skills   →   Output        │
│       │                    │                     │                              │
│       │                    ▼                     ▼                              │
│       │              (context-based)      (auto-discovered)                     │
│       │                                                                         │
│  Example:                                                                       │
│  /deploy → deployment-principles.md → deployment/SKILL.md                      │
│         → Progressive Evidence (#2) + Invariant (#25) verification             │
│                                                                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Pattern 3: KNOWLEDGE GRADUATION (Experience → Principle)                      │
│  ════════════════════════════════════════════════════════                      │
│                                                                                 │
│  .claude/observations/      .claude/abstractions/      CLAUDE.md              │
│  (Raw experience)    →    (Pattern analysis)    →    (Principle)               │
│       │                        │                        │                       │
│       │                        ▼                        ▼                       │
│       │               .claude/principles/       docs/guides/                   │
│       │                 (if tier 1-3)        (Implementation)                  │
│       │                                             │                          │
│       │                                             ▼                          │
│       │                                      .claude/skills/                   │
│       │                                       (Workflow)                       │
│       │                                                                         │
│  Example:                                                                       │
│  Observed: "Lambda import failures in production"                              │
│  → Abstract: boundary-blindness.md                                             │
│  → Principle #19: Cross-Boundary Contract Testing                              │
│  → Guide: cross-boundary-contract-testing.md                                   │
│  → Skill: testing-workflow (deployment fidelity section)                       │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dependency Graph (Simplified)

```
                    ┌─────────────────┐
                    │   User Input    │
                    └────────┬────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │/commands │    │  Skills  │    │CLAUDE.md │
      │  (50)    │    │  (14)    │    │(always)  │
      └────┬─────┘    └────┬─────┘    └────┬─────┘
           │               │               │
           │               │               ▼
           │               │         ┌──────────┐
           │               │         │principles│
           │               │         │clusters  │
           │               │         │(on-demand│
           │               │         └────┬─────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │docs/guides/  │
                    │(reference)   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │.claude/      │
                    │invariants/   │
                    │(contracts)   │
                    └──────────────┘
```

---

## Trade-off Analysis

| Trade-off | Current Position | Rationale |
|-----------|------------------|-----------|
| **Token efficiency vs completeness** | Tier-based loading (~60% savings) | Load core always, load clusters on demand |
| **Auto-discovery vs explicit control** | Dual model (skills + commands) | Skills for expertise, commands for orchestration |
| **Centralization vs distribution** | Distributed with routing | Single source of truth (CLAUDE.md) routes to distributed clusters |
| **Abstraction vs detail** | 3-layer depth | Principle → Guide → Skill provides progressive detail |

---

## Assessment

### Strengths
- **Clear separation of concerns**: WHY (principles) / HOW (guides+skills) / WHEN (commands)
- **Token-efficient**: Tier-based loading reduces context usage by ~60%
- **High discoverability**: Routing index + auto-discovery + explicit commands
- **Graduation path**: Experiences become principles systematically

### Weaknesses
- **Complexity**: 50 commands + 14 skills + 25 principles = steep learning curve
- **Maintenance overhead**: Many cross-references to keep synchronized
- **Duplication risk**: Same concept may appear in principle, guide, and skill

### Observations (Not Recommendations)
- **Potential drift**: Skills reference principle numbers that may change
- **Command proliferation**: 50 commands may be too many to discover
- **Missing**: No automated consistency checker for cross-references

---

## Key Takeaways

1. **3-layer knowledge architecture**: Principles (6 Tier-0 + 19 in clusters) → Guides (12) + Skills (14) → Commands (50)
2. **Dual invocation**: Skills = auto-discovered expertise, Commands = explicit user orchestration
3. **Token efficiency**: ~60% savings via tier-based loading vs always-loading all principles
4. **Graduation pipeline**: Observations → Abstractions → Principles → Guides → Skills

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - Ground truth, Tier-0 principles
- [Principles Index](../principles/index.md) - Routing table for context-specific principles
- [Skills README](../skills/README.md) - Skill inventory and auto-discovery
- [Commands README](../commands/README.md) - Command taxonomy and usage
- [Implementation Guides](../../docs/guides/README.md) - Deep how-to guides

---

*Generated by /x-ray command*
*Report version: 2026-01-12*
