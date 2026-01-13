# Slash Command Fundamentality Architecture

**Purpose**: Visualize how slash commands depend on and compose other slash commands, identifying which are foundational vs derived.

**Date**: 2026-01-13

---

## Core Insight

Commands form a **layered dependency graph**:
- **Foundational commands** (Tier 0): Used by many, depend on none
- **Derived commands** (Tier 3+): Orchestrate multiple lower-tier commands
- **Aliases** (Tier 4): Delegate entirely to another command

---

## Fundamentality Hierarchy

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        SLASH COMMAND FUNDAMENTALITY                            ║
║                                                                                 ║
║  TIER 0: FOUNDATIONAL (Used by many, use none)                                 ║
║  ══════════════════════════════════════════════                                ║
║                                                                                 ║
║    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       ║
║    │ /journal │  │ /observe │  │ /validate│  │/invariant│  │  /trace  │       ║
║    │  (sink)  │  │ (source) │  │ (verify) │  │(contract)│  │ (cause)  │       ║
║    └────▲─────┘  └────┬─────┘  └────▲─────┘  └────▲─────┘  └────▲─────┘       ║
║         │             │             │             │             │              ║
║  ═══════╪═════════════╪═════════════╪═════════════╪═════════════╪══════════   ║
║         │             │             │             │             │              ║
║  TIER 1: ANALYTICAL PRIMITIVES                                                 ║
║  ═════════════════════════════════                                             ║
║         │             │             │             │             │              ║
║    ┌────┴────┐  ┌─────▼────┐  ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐       ║
║    │/abstract│  │/decompose│  │/hypothesis│  │/reconcile│  │ /impact │       ║
║    └────▲────┘  └────┬─────┘  └────▲─────┘  └────▲─────┘  └────▲─────┘       ║
║         │            │             │             │             │              ║
║  ═══════╪════════════╪═════════════╪═════════════╪═════════════╪══════════   ║
║         │            │             │             │             │              ║
║  TIER 2: THINKING MODES                                                        ║
║  ═════════════════════                                                         ║
║         │            │             │             │             │              ║
║    ┌────┴────┐  ┌────▼────┐  ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐       ║
║    │/explore │  │/what-if │  │ /reflect │  │  /proof  │  │  /x-ray  │       ║
║    │(diverge)│  │(compare)│  │  (meta)  │  │ (deduce) │  │(inspect) │       ║
║    └────▲────┘  └────▲────┘  └────▲─────┘  └────▲─────┘  └────▲─────┘       ║
║         │            │             │             │             │              ║
║  ═══════╪════════════╪═════════════╪═════════════╪═════════════╪══════════   ║
║         │            │             │             │             │              ║
║  TIER 3: WORKFLOW ORCHESTRATORS                                                ║
║  ══════════════════════════════                                                ║
║         │            │             │             │             │              ║
║    ┌────┴────┐  ┌────┴────┐  ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐       ║
║    │/analysis│  │  /step  │  │ /bug-hunt│  │ /design  │  │  /evolve │       ║
║    │(chain 4)│  │(tuple 6)│  │(workflow)│  │(workflow)│  │ (drift)  │       ║
║    └─────────┘  └─────────┘  └──────────┘  └──────────┘  └──────────┘       ║
║                                                                                 ║
║  TIER 4: ALIASES (Delegate to others)                                          ║
║  ════════════════════════════════════                                          ║
║                                                                                 ║
║    /explain → /understand    /summary → /consolidate    /compare → /what-if    ║
║                                                                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Dependency Flow Diagram

```
                            ┌─────────────────────────────────────────┐
                            │         ORCHESTRATION LAYER              │
                            │   (Compose multiple commands)            │
                            └─────────────────────────────────────────┘
                                              │
          ┌───────────────────────────────────┼───────────────────────────────────┐
          │                                   │                                   │
          ▼                                   ▼                                   ▼
    ┌───────────┐                       ┌───────────┐                       ┌───────────┐
    │ /analysis │                       │   /step   │                       │  /deploy  │
    │           │                       │           │                       │           │
    │ Chains:   │                       │ Slots for:│                       │ Chains:   │
    │ • explore │                       │ • invari- │                       │ • build   │
    │ • what-if │                       │   ant     │                       │ • test    │
    │ • validate│                       │ • reconcile                       │ • deploy  │
    │ • consoli-│                       │ • explore │                       │ • verify  │
    │   date    │                       │ • what-if │                       │           │
    └─────┬─────┘                       │ • reflect │                       └─────┬─────┘
          │                             └─────┬─────┘                             │
          │                                   │                                   │
          └───────────────────────────────────┼───────────────────────────────────┘
                                              │
                            ┌─────────────────────────────────────────┐
                            │          THINKING MODES                  │
                            │   (Single cognitive operations)          │
                            └─────────────────────────────────────────┘
                                              │
    ┌─────────┬─────────┬─────────┬─────────┬─┴───────┬─────────┬─────────┬─────────┐
    │         │         │         │         │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼         ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│explore│ │what-if│ │reflect│ │x-ray  │ │proof  │ │consoli│ │under- │ │specify│ │locate │
│       │ │       │ │       │ │       │ │       │ │date   │ │stand  │ │       │ │       │
│diverge│ │compare│ │ meta  │ │inspect│ │deduce │ │synth- │ │explain│ │quick  │ │find   │
│       │ │       │ │       │ │       │ │       │ │esize  │ │       │ │design │ │code   │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │         │         │         │         │         │
    └─────────┴─────────┴─────────┴─────────┼─────────┴─────────┴─────────┴─────────┘
                                            │
                            ┌─────────────────────────────────────────┐
                            │       VERIFICATION PRIMITIVES            │
                            │   (Atomic verification operations)       │
                            └─────────────────────────────────────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────────────────┐
          │                                 │                                 │
          ▼                                 ▼                                 ▼
    ┌───────────┐                     ┌───────────┐                     ┌───────────┐
    │ /validate │                     │/invariant │                     │ /reconcile│
    │           │                     │           │                     │           │
    │  Test     │                     │ Identify  │                     │ Converge  │
    │  claims   │◄────────────────────│ contracts │────────────────────►│ violations│
    │           │                     │           │                     │           │
    └─────┬─────┘                     └─────┬─────┘                     └─────┬─────┘
          │                                 │                                 │
          └─────────────────────────────────┼─────────────────────────────────┘
                                            │
                            ┌─────────────────────────────────────────┐
                            │        DATA CAPTURE & SINK              │
                            │   (Terminal points for knowledge)       │
                            └─────────────────────────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
              ┌───────────┐           ┌───────────┐           ┌───────────┐
              │ /observe  │           │ /journal  │           │ /abstract │
              │           │           │           │           │           │
              │  Capture  │──────────►│   Store   │◄──────────│  Extract  │
              │  evidence │           │  findings │           │  patterns │
              │           │           │           │           │           │
              └───────────┘           └───────────┘           └───────────┘
                SOURCE                    SINK                 TRANSFORM
```

---

## Fundamentality Score

| Score | Tier | Commands | Characteristic |
|-------|------|----------|----------------|
| **5** | 0 | `/journal`, `/observe`, `/validate` | Terminal points, no dependencies |
| **4** | 0 | `/invariant`, `/trace`, `/hypothesis` | Verification primitives |
| **3** | 2 | `/explore`, `/what-if`, `/reflect`, `/x-ray` | Single thinking operations |
| **2** | 1 | `/decompose`, `/abstract`, `/reconcile` | Intermediate transformations |
| **1** | 3 | `/analysis`, `/step`, `/deploy`, `/bug-hunt` | Orchestrate many commands |
| **0** | 4 | `/explain`, `/summary`, `/compare` | Delegate to other commands |

---

## Command Dependency Matrix

### Direct Composition (via frontmatter)

| Command | Uses These Commands |
|---------|---------------------|
| `/analysis` | `/explore` → `/what-if` → `/validate` → `/consolidate` |
| `/compare` | `/what-if` (alias for multi-way mode) |
| `/explain` | `/understand` (direct delegation) |
| `/summary` | `/consolidate` (direct delegation) |
| `/runbook` | `/reproduce` |

### Slot-Based Composition (`/step` Thinking Tuple)

| Tuple Slot | Command That Fills It |
|------------|----------------------|
| Invariant | `/invariant` output |
| Check (violations) | `/reconcile` |
| Process: diverge | `/explore` |
| Process: compare | `/what-if` |
| Process: decompose | `/decompose` |
| Process: escape | `/reflect` |

### Workflow Suggestions (documented in output)

| Command | Suggests Next |
|---------|---------------|
| `/observe failure` | `/decompose failure` → `/journal error` |
| `/observe execution` | `/abstract` |
| `/observe behavior` | `/abstract` → `/evolve` |
| `/decompose` | `/validate`, `/journal` |
| `/trace backward` | `/validate` → `/impact` → `/journal` |
| `/what-if` | `/journal`, `/proof`, `/validate` |

---

## Workflow Chains

### Chain 1: Analysis & Validation
```
/explore → /what-if → /validate → /consolidate → /journal
```
Automated by `/analysis` command.

### Chain 2: Observation & Investigation
```
/observe failure
   ↓
/decompose failure
   ↓
[Investigation]
   ↓
/journal error
   ↓
/abstract (multiple failures)
   ↓
/evolve
```

### Chain 3: Invariant Feedback Loop
```
/invariant "goal"
   ↓
[Implementation]
   ↓
/invariant "goal"  (detect violations)
   ↓
/reconcile domain  (fix violations)
   ↓
/invariant "goal"  (verify δ = 0)
```

### Chain 4: Root Cause Analysis
```
/trace "event" backward
   ↓
/validate "hypothesis"
   ↓
/impact "fix"
   ↓
/journal error
```

### Chain 5: Thinking Tuple Protocol
```
/step "goal"
   ↓
Constraints ← context
Invariant   ← /invariant
Principles  ← CLAUDE.md
Process     ← /explore | /what-if | /reflect | ...
Actions     ← tool calls
Check       ← /validate | /reconcile
```

---

## Key Insights

### Most Fundamental Commands

1. **`/journal`** - Sink for all documented findings (Score: 5)
2. **`/observe`** - Source of all evidence capture (Score: 5)
3. **`/validate`** - Universal verification primitive (Score: 5)

### Hub Commands (Most Referenced)

1. **`/what-if`** - Used by `/analysis`, `/step`, many workflow suggestions
2. **`/validate`** - Used by `/analysis`, `/step`, `/trace`, `/decompose`
3. **`/invariant`** - Core of verification protocol, feeds `/step`

### Unique Commands

1. **`/step`** - Meta-orchestrator that can use ANY thinking mode in its Process slot
2. **`/analysis`** - Only command that chains 4 other commands sequentially
3. **`/evolve`** - Self-referential (detects drift in command usage itself)

### Alias Pattern

Commands that exist purely for discoverability:
- `/explain` → `/understand` (communication focus)
- `/summary` → `/consolidate` (synthesis focus)
- `/compare` → `/what-if` (multi-way mode)

---

## Relationship to Thinking Tuple Protocol

The Thinking Tuple Protocol (`/step`) is the **universal orchestrator** that can compose any command into its slots:

```
┌────────────────────────────────────────────────────────────────┐
│                    THINKING TUPLE                               │
├────────────────────────────────────────────────────────────────┤
│ Constraints  │ Context, previous outputs                        │
│ Invariant    │ ← /invariant "goal"                             │
│ Principles   │ ← CLAUDE.md (auto-loaded)                       │
│ Process      │ ← /explore | /what-if | /reflect | /decompose   │
│ Actions      │ ← Any tool call or command                      │
│ Check        │ ← /validate | /reconcile                        │
└────────────────────────────────────────────────────────────────┘
```

This makes `/step` the **most composable** command—it doesn't have fixed dependencies, but can incorporate any command based on the task.

---

## See Also

- [Thinking Process Architecture](thinking-process-architecture.md) - Cognitive strategy design
- [Commands README](../commands/README.md) - Command reference
- [Thinking Tuple Protocol](thinking-process-architecture.md#12-thinking-tuple-protocol) - Section 12

---

*Generated: 2026-01-13*
*Source: /understand analysis of command dependencies*
