---
name: move
description: Invariant-preserving transformation - move concepts between contexts without changing either
accepts_args: true
arg_schema:
  - name: what
    required: true
    description: "What to transform (code, infra, state) or natural description"
  - name: from
    required: false
    description: "Source context (library, environment, current state)"
  - name: to
    required: false
    description: "Target context (codebase, new environment, goal state)"
  - name: preserving
    required: false
    description: "Invariants to preserve during transformation"
---

# Move Command

**Purpose**: Execute invariant-preserving transformations across contexts.

**Derives from**: [/merge](merge.md) with `strategy=preserve`

**Theory**: [/transfer](transfer.md) (Documentation)

---

## Relationship to /merge (Foundation)

`/move` is a **specialization** of the [/merge](merge.md) foundation with fixed invariant specification:

```
/move A B = /merge A B --strategy=preserve

Where strategy=preserve means:
  preserve: [A.*]     # Keep everything from A
  protect:  [B.*]     # Don't change B
  discard:  []        # Lose nothing
  transform: []       # Modify nothing
```

**Semantic**: Transfer A into B's context without changing either. This is the "pure transfer" case.

**When to use /move vs /merge**:
- Use `/move` when you want everything preserved (most common)
- Use `/merge` when you need fine-grained control over what survives

---

## Derivation Hierarchy

```
                    /merge (Tier-0 Foundation)
                    Combine(A, B, Invariants)
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
      /move              /reconcile          /adapt
   strategy=preserve   strategy=conform    strategy=adapt
         │
         ▼
    /provision-env
    strategy=copy
```

---

## Tuple Effects (Universal Kernel Integration)

**Part of the Agent Kernel** - Transformation within the knowledge system.

**Mode Type**: `transform`

**Tier**: 1 (Specialization of Tier-0 `/merge`)

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **EXPAND**: Adds source context, target context, portable/context-bound analysis |
| **Invariant** | **SET**: `strategy=preserve` (keep A, protect B) |
| **Principles** | **LOAD**: Domain-specific cluster based on WHAT |
| **Strategy** | Routes to specializations or executes 7-step process |
| **Check** | **EVALUATE**: Verifies X' exists in B with A's properties intact |

**Local Check** (mode-specific completion):
- Source analyzed (properties identified)
- Target constraints understood
- Portable vs context-bound separated
- Transfer executed
- Invariants verified via `/invariant`

---

## The Transform Function

```
Transform(X, Context_A, Context_B, Invariants) → X'

/move executes this function with:
- X         = what you're transforming
- Context_A = where it comes from (from)
- Context_B = where it goes (to)
- Invariants = fixed to "preserve" strategy
```

---

## Quick Reference

```bash
# Full explicit syntax
/move code from "external-library" to "codebase" preserving "algorithm-essence"
/move infra from "dev" to "staging" preserving "isolation,functionality"
/move state from "current" to "goal" preserving "L0-L4-invariants"

# Natural language (auto-detected)
/move "stock-pattern library techniques" to "chart detection"
/move "dev environment" to "staging"
/move "current state" to "pattern overlay working"

# Shorthand (routes to specializations)
/move code "library" → routes to /adapt
/move infra "dev" "staging" → routes to /provision-env
/move state "goal description" → routes to /step
```

---

## Three Dimensions

Every `/move` operation is characterized by:

### Dimension 1: WHAT (Artifact Type)

| Value | Description | Default Invariants |
|-------|-------------|-------------------|
| `code` | Algorithms, patterns, techniques | Algorithm essence + CLAUDE.md |
| `infra` | Infrastructure configuration | Resource isolation + functionality |
| `state` | System state | Behavioral invariants L0-L4 |

### Dimension 2: WHERE (Context Relationship)

| Pattern | Description | Example |
|---------|-------------|---------|
| `external→internal` | From outside to inside | Library → codebase |
| `internal→internal` | Within same system | Dev → staging |
| `current→goal` | Temporal progression | Now → desired state |

### Dimension 3: HOW (Preservation Strategy)

| Value | Description | When Used |
|-------|-------------|-----------|
| `copy` | Mechanical reproduction | Infra cloning |
| `adapt` | Conceptual translation | Code adaptation |
| `preserve` | Behavioral invariants | State transformation |

---

## Auto-Detection Logic

When using natural language, `/move` detects dimensions from keywords:

```
IF source contains {"library", "github.com", "external", "npm", "pypi"}:
  → WHAT: code, WHERE: external→internal
  → Routes to: /adapt

ELIF source contains {"env", "environment", "dev", "staging", "prod"}:
  → WHAT: infra, WHERE: internal→internal
  → Routes to: /provision-env

ELIF source contains {"current", "now", "state"} AND target describes goal:
  → WHAT: state, WHERE: current→goal
  → Routes to: /step

ELIF source contains {"branch", "feature/"}:
  → WHAT: code, WHERE: internal→internal
  → Routes to: /adapt (branch mode)

ELSE:
  → Ask clarifying question
```

---

## Execution Flow

### Step 1: Parse Input

```bash
/move code from "library" to "feature" preserving "algorithm"
       ↓         ↓           ↓              ↓
      WHAT    Context_A   Context_B     Invariants
```

OR natural language:

```bash
/move "pandas rolling window technique" to "chart indicators"
       ↓                                     ↓
   Auto-detect: code, external→internal   Target description
```

### Step 2: Route or Execute

**If dimensions match a specialization** → Route to it:

| Dimensions | Routes To |
|------------|-----------|
| code + external→internal | `/adapt` |
| code + internal→internal | `/adapt` (branch mode) |
| infra + internal→internal | `/provision-env` |
| state + current→goal | `/step` |

**If no match** → Execute foundation 7-step process directly.

### Step 3: Execute Transform

Whether routed or direct, execute the [7-Step Transfer Process](transfer.md#the-7-step-transfer-process):

1. **IDENTIFY** - What's being transformed
2. **ANALYZE SOURCE** - Use `/qna` to surface assumptions
3. **ANALYZE TARGET** - Check CLAUDE.md constraints
4. **MAP** - Create source→target mapping
5. **UNTANGLE** - Separate portable from context-bound
6. **REWIRE** - Replace source-specific with target-specific
7. **VERIFY** - Use `/invariant` to confirm success

### Step 4: Verify Invariants

```bash
/invariant "{what} correctly transformed to {to}"
```

Verify through Progressive Evidence (Principle #2):
- Layer 1: Status codes, exit codes
- Layer 2: Payloads, data structures
- Layer 3: Logs, traces
- Layer 4: Ground truth (X' actually works)

---

## Integration with Specializations

`/move` can route to domain-specific commands or execute directly:

```
┌─────────────────────────────────────────────────────────────┐
│                         /move                                │
│         (parses dimensions, routes or executes)              │
├─────────────────────────────────────────────────────────────┤
│                           │                                  │
│    ┌──────────────────────┼──────────────────────┐          │
│    ▼                      ▼                      ▼          │
│ /adapt              /provision-env            /step         │
│ (code domain)       (infra domain)        (state domain)    │
│                                                              │
│ Specializations have domain-specific:                        │
│ - Default invariants                                         │
│ - Optimized workflows                                        │
│ - Domain checklists                                          │
└─────────────────────────────────────────────────────────────┘
```

**When to use `/move` directly**:
- Unusual dimension combinations
- Need explicit control over invariants
- Learning the framework

**When to use specializations**:
- Common patterns (most of the time)
- Domain-specific optimizations
- Established workflows

---

## Examples

### Example 1: Code from External Library

```bash
/move code from "pandas rolling window" to "chart indicators" preserving "algorithm"
```

**Execution**:
1. Detects: code, external→internal → Routes to `/adapt`
2. `/adapt` executes with source="pandas rolling window", goal="chart indicators"
3. Preserves algorithm essence while adapting to CLAUDE.md patterns

**Equivalent to**:
```bash
/adapt "pandas rolling window" for "chart indicators"
```

---

### Example 2: Infrastructure Clone

```bash
/move infra from "dev" to "staging" preserving "isolation"
```

**Execution**:
1. Detects: infra, internal→internal → Routes to `/provision-env`
2. `/provision-env staging from=dev` executes
3. Preserves resource isolation, functionality

**Equivalent to**:
```bash
/provision-env staging from=dev
```

---

### Example 3: State Transformation

```bash
/move state to "chart pattern overlay displays correctly"
```

**Execution**:
1. Detects: state, current→goal → Routes to `/step`
2. `/step` executes with goal="chart pattern overlay displays correctly"
3. Preserves L0-L4 behavioral invariants

**Equivalent to**:
```bash
/step "chart pattern overlay displays correctly"
```

---

### Example 4: Natural Language (Auto-detect)

```bash
/move "authentication patterns from Auth0 docs" to "our login flow"
```

**Execution**:
1. Parses: source mentions "docs" (external), target is internal
2. Detects: code, external→internal
3. Routes to `/adapt`

---

### Example 5: Ambiguous Input

```bash
/move "auth module" to "new service"
```

**Execution**:
1. Parses: source ambiguous (internal? external?)
2. Asks clarifying question:

```markdown
I see you want to move "auth module" to "new service".

Which best describes your intent?

1. **Learn from external** auth module → /adapt
2. **Clone infrastructure** for new service → /provision-env
3. **Port code** between branches → /adapt (internal)
4. **Achieve goal state** → /step

Select: [1/2/3/4]
```

---

## Thinking Tuple Integration

`/move` is a Thinking Tuple execution:

```
┌─────────────────────────────────────────────────────────────┐
│              /MOVE ↔ THINKING TUPLE MAPPING                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  /move Parameter        ←→    Tuple Slot                    │
│  ─────────────────────────────────────────────              │
│  from (Context_A)       ←→    Constraints (what we have)    │
│  to (Context_B)         ←→    (implicit in Invariant)       │
│  preserving             ←→    Invariant (what must hold)    │
│  {domain principles}    ←→    Principles (CLAUDE.md)        │
│  7-step process         ←→    Process (transform mode)      │
│  domain steps           ←→    Actions (execution)           │
│  /invariant check       ←→    Check (verification)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## When Transform Fails

Use appropriate feedback loop (Principle #9):

```
/move fails → Which loop?
│
├── RETRYING (execution error)
│   Same /move, fix parameters
│   Example: Typo in source name
│
├── INITIAL-SENSITIVE (wrong assumptions)
│   /qna "{what} transformation"
│   Surface incorrect beliefs, retry with corrected knowledge
│
├── BRANCHING (wrong approach)
│   Try different dimension values
│   Example: Thought it was code, actually infra
│
└── META-LOOP (wrong goal)
    Question if transformation is needed at all
```

**Escalation**:
```
Retry 1 → Retry 2 → /qna → Initial-sensitive → Branching → Meta-loop
```

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Intent Verbs (Future shortcuts)                   │
│  /learn → /move code external→internal                      │
│  /clone → /move infra internal→internal                     │
│  /port  → /move code internal→internal                      │
│  /converge → /move state current→goal                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Executable Foundation                  ← /move    │
│  /move {what} from {A} to {B} preserving {invariants}       │
│  Implements: Transform(X, Context_A, Context_B, Invariants) │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Specialization Commands (domain-optimized)        │
│  /adapt    = /move code with adaptation workflow            │
│  /provision-env = /move infra with env workflow             │
│  /step     = /move state with tuple workflow                │
├─────────────────────────────────────────────────────────────┤
│  Theory: /transfer.md (Documentation Only)                  │
│  Describes Transform() abstraction and theory               │
└─────────────────────────────────────────────────────────────┘
```

---

## Valid Dimension Combinations

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     VALID TRANSFORMATION MATRIX                            │
├─────────┬─────────────────────┬─────────────────────┬─────────────────────┤
│  WHAT   │ external→internal   │ internal→internal   │ current→goal        │
├─────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ code    │ ✅ /adapt           │ ✅ /adapt (branch)  │ ❌ (use state)      │
│         │ (library→codebase)  │ (feature→main)      │                     │
├─────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ infra   │ ⚠️ rare             │ ✅ /provision-env   │ ❌ (use state)      │
│         │ (template→our env)  │ (dev→staging)       │                     │
├─────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ state   │ ❌ invalid          │ ❌ invalid          │ ✅ /step            │
│         │                     │                     │ (current→goal)      │
└─────────┴─────────────────────┴─────────────────────┴─────────────────────┘

Legend:
  ✅ = Primary use case (routes to specialization)
  ⚠️ = Valid but rare (executes foundation directly)
  ❌ = Invalid combination (use different dimensions)
```

---

## Command Selection Guide

```
"I want to learn from external code"
  → /move code from "library" to "feature"
  → Routes to: /adapt

"I want to create a new environment"
  → /move infra from "dev" to "staging"
  → Routes to: /provision-env

"I want to reach a goal state"
  → /move state to "goal description"
  → Routes to: /step

"I want to port branch changes"
  → /move code from "feature/x" to "main"
  → Routes to: /adapt (internal mode)

"I want to understand the theory"
  → Read: /transfer.md
```

---

## See Also

### Foundation
- [/merge](merge.md) - Tier-0 foundation (parent)
- [/transfer](transfer.md) - Transform theory documentation

### Sibling Specializations (from /merge)
- [/adapt](adapt.md) - Code transfer with `strategy=adapt`
- [/reconcile](reconcile.md) - Compliance with `strategy=conform`
- [/provision-env](provision-env.md) - Infrastructure with `strategy=copy`
- [/step](step.md) - State transformation

### Key Integrations
- [/qna](qna.md) - Surface assumptions in ANALYZE SOURCE step
- [/invariant](invariant.md) - Verify invariants in VERIFY step

### Principles
- [CLAUDE.md - Principle #25](../CLAUDE.md) - Behavioral Invariant Verification
- [CLAUDE.md - Principle #26](../CLAUDE.md) - Thinking Tuple Protocol
- [CLAUDE.md - Principle #9](../principles/meta-principles.md) - Feedback Loop Awareness

### Guides
- [Thinking Tuple Protocol](../../docs/guides/thinking-tuple-protocol.md) - Tuple integration
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Invariant verification
