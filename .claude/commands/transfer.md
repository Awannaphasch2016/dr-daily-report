---
name: transfer
description: Abstract framework for contextual transfer operations - moving concepts between contexts while preserving essence
accepts_args: true
arg_schema:
  - name: concept
    required: true
    description: "What to transfer (technique, infrastructure, pattern)"
  - name: source
    required: true
    description: "Source context (library, environment, document)"
  - name: target
    required: true
    description: "Target context (codebase, new environment)"
---

# Transfer Command (Foundation Layer)

**Purpose**: Unified theory for invariant-preserving transformations across contexts.

**This is the FOUNDATION LAYER** - all transformation commands are specializations:
- `/adapt` - Code patterns (heterogeneous: external → internal)
- `/provision-env` - Infrastructure (homogeneous: env → env)
- `/step` - State transformation (current → goal)

---

## The Grand Unified Theory

**Core Insight**: All transformation commands are instances of a single abstract operation:

```
Transform(X, Context_A, Context_B, Invariants) → X'

Where:
  - X         = What is being transformed (artifact)
  - Context_A = Source context (where X exists now)
  - Context_B = Target context (where X' must work)
  - Invariants = What must be preserved during transformation
  - X'        = X rewired for Context_B while preserving Invariants
```

**Pre-condition**: X satisfies constraints in Context_A
**Post-condition**: X' satisfies constraints in Context_B
**Preservation**: essence(X) ≅ essence(X')

---

## Three Dimensions of Transformation

Every transformation is characterized by three orthogonal dimensions:

### Dimension 1: WHAT (Artifact Type)

What kind of thing is being transformed?

| Value | Description | Example |
|-------|-------------|---------|
| `code` | Algorithms, patterns, techniques | Library → codebase |
| `infra` | Infrastructure configuration | Dev env → staging env |
| `state` | System state | Current → goal state |

### Dimension 2: WHERE (Context Relationship)

What is the relationship between source and target contexts?

| Value | Description | Example |
|-------|-------------|---------|
| `external→internal` | From outside to inside codebase | GitHub repo → our code |
| `internal→internal` | Within the same system | Dev → staging, branch → main |
| `current→goal` | Temporal progression | Current state → desired state |

### Dimension 3: HOW (Preservation Strategy)

How strictly must the original be preserved?

| Value | Description | Example |
|-------|-------------|---------|
| `copy` | Mechanical reproduction | Clone env (names change, structure same) |
| `adapt` | Conceptual translation | Library technique → native implementation |
| `preserve` | Behavioral invariants | State change maintaining L0-L4 invariants |

---

## Valid Dimension Combinations

Not all combinations are valid. This matrix defines what's meaningful:

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
  ✅ = Primary use case (well-defined command)
  ⚠️ = Valid but rare (use with caution)
  ❌ = Invalid combination (use different dimension)
```

---

## Command Specializations (Genus-Species)

The foundation is a **genus** (general category). Commands are **species** (specific instances):

```
Transform (genus)
│
├── /adapt (species)
│   ├── WHAT: code
│   ├── WHERE: external→internal OR internal→internal
│   ├── HOW: adapt
│   └── Invariants: {algorithm_essence, CLAUDE.md_principles}
│
├── /provision-env (species)
│   ├── WHAT: infra
│   ├── WHERE: internal→internal
│   ├── HOW: copy
│   └── Invariants: {resource_isolation, functionality, behavioral_contracts}
│
└── /step (species)
    ├── WHAT: state
    ├── WHERE: current→goal
    ├── HOW: preserve
    └── Invariants: {L0-L4_behavioral_invariants}
```

### How Each Command Maps

| Command | X (What) | Context_A (From) | Context_B (To) | Invariant_Set |
|---------|----------|------------------|----------------|---------------|
| `/adapt` | Algorithm/Pattern | External library | This codebase | Algorithm essence + CLAUDE.md |
| `/provision-env` | Env config | Working env | New env | Resource isolation + functionality |
| `/step` | System state | Current state | Goal state | Behavioral invariants (L0-L4) |

---

## Integration with Thinking Tuple (Principle #26)

The Transform function maps directly to the Thinking Tuple:

```
┌─────────────────────────────────────────────────────────────────┐
│              TRANSFORM ↔ THINKING TUPLE MAPPING                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Transform Parameter    ←→    Tuple Slot                        │
│  ─────────────────────────────────────────────                  │
│  Context_A (source)     ←→    Constraints (what we have/know)   │
│  Context_B (target)     ←→    (implicit in Invariant)           │
│  Invariants             ←→    Invariant (what must be true)     │
│  {domain principles}    ←→    Principles (what guides us)       │
│  7-step process         ←→    Process (thinking mode)           │
│  domain-specific steps  ←→    Actions (concrete steps)          │
│  verify X' works        ←→    Check (did we satisfy invariant?) │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Every transformation is a Thinking Tuple execution with:
- Constraints = Context_A (source state)
- Invariant = Invariants to preserve
- Check = Verify X' preserves Invariants in Context_B

---

## The 7-Step Transfer Process

All specializations follow this process (with domain-specific details):

### Step 1: IDENTIFY

**What concept/artifact needs to be transferred?**

Questions to answer:
- What is the **essence** that must be preserved?
- What is the **boundary** of the transfer?
- What **problem** does this concept solve?

Output: Clear definition of what we're transferring

---

### Step 2: ANALYZE SOURCE (Use `/qna` here)

**What is the source context?**

**Surface assumptions first**:
```bash
/qna "transferring {concept} from {source} to {target}"
```

Questions to answer:
- What **dependencies** exist in source?
- What **assumptions** are embedded?
- What is **implicit** vs **explicit**?
- What **environment** does source expect?

Output: Dependency map of source context + knowledge state from `/qna`

---

### Step 3: ANALYZE TARGET

**What is the target context?**

Questions to answer:
- What **equivalents** exist in target?
- What **constraints** apply in target?
- What's **missing** in target?
- What **principles** govern target? (CLAUDE.md)

Output: Constraint map of target context

---

### Step 4: MAP

**Create explicit mapping: source → target**

For each source dependency:
- Find **target equivalent**
- Classify: **adopt** / **skip** / **adapt**

| Source Concept | Target Equivalent | Gap/Conflict | Action |
|----------------|-------------------|--------------|--------|
| {concept} | {equivalent} | {none/gap/conflict} | {adopt/skip/adapt} |

Output: Explicit mapping table

---

### Step 5: UNTANGLE

**Separate portable from context-bound**

Two categories:
- **Portable**: Can move unchanged (the essence)
- **Context-bound**: Must be rewired (the implementation)

```
┌─────────────────────────────────────┐
│           SOURCE CONCEPT            │
├─────────────────────────────────────┤
│  Portable (essence):                │
│  - Core algorithm/logic             │
│  - Fundamental structure            │
│  - Problem-solving approach         │
├─────────────────────────────────────┤
│  Context-bound (implementation):    │
│  - Dependencies on source env       │
│  - Source-specific naming           │
│  - Source-specific integrations     │
└─────────────────────────────────────┘
```

Output: Categorized list of portable vs context-bound elements

---

### Step 6: REWIRE

**Replace source-specific with target-specific**

For each context-bound element:
- Replace with target equivalent
- Preserve essence
- Change implementation

```
Source-specific → Target-specific
  ├── Dependencies → Target dependencies
  ├── Naming → Target naming conventions
  ├── Patterns → Target patterns (CLAUDE.md)
  └── Integrations → Target integrations
```

Output: Transformed concept ready for target

---

### Step 7: VERIFY (Use `/invariant` here)

**Confirm transfer succeeded**

**Verify behavioral invariants**:
```bash
/invariant "transferred {concept} works correctly in {target}"
```

Verification checklist (Progressive Evidence - Principle #2):
- [ ] **Layer 1 (Surface)**: Status codes, exit codes
- [ ] **Layer 2 (Content)**: Payloads, data structures valid
- [ ] **Layer 3 (Observability)**: Logs show correct behavior
- [ ] **Layer 4 (Ground truth)**: X' actually works in Context_B

Output: Verification report with evidence at all 4 layers

---

## When Transform Fails (Principle #9 - Feedback Loops)

Not all transformations succeed on first attempt. Use appropriate feedback loop:

```
Transform fails → Which loop?
│
├── RETRYING (execution error)
│   Same transform, fix parameters
│   Example: Typo in config, missing dependency
│
├── INITIAL-SENSITIVE (wrong assumptions)
│   Use /qna to surface incorrect beliefs
│   Example: Assumed library API works differently
│
│   /qna "{concept} transformation" → Surface assumptions
│   User corrects → Retry with updated knowledge
│
├── BRANCHING (wrong approach)
│   Try different transformation type
│   Example: /adapt not working → maybe /provision-env?
│
└── META-LOOP (wrong goal)
    Question if transformation is the right approach
    Example: Maybe don't need to transfer at all
```

**Escalation pattern**:
```
Retry 1 → Retry 2 → /qna → Initial-sensitive → Branching → Meta-loop
```

---

## Observable Markers (Principle #20)

How to verify the foundation is being followed:

### During Transformation

| Step | Observable Marker |
|------|-------------------|
| IDENTIFY | Clear artifact definition documented |
| ANALYZE SOURCE | `/qna` output shows knowledge state |
| ANALYZE TARGET | CLAUDE.md principles explicitly listed |
| MAP | Concept mapping table exists |
| UNTANGLE | Portable vs context-bound categorized |
| REWIRE | Code/config changes follow target patterns |
| VERIFY | `/invariant` output with 4-layer evidence |

### In Output Artifacts

- Adaptation documents in `.claude/adaptations/`
- Invariant verification in `.claude/validations/`
- Evolution reports in `.claude/evolution/`

---

## Transfer Types

| Type | Source ≈ Target? | Mapping Difficulty | Example |
|------|------------------|-------------------|---------|
| **Homogeneous** | Same type | Mechanical (name substitution) | /provision-env |
| **Heterogeneous** | Different types | Requires understanding | /adapt |

### Homogeneous Transfer

Source and target are the **same type** (e.g., both AWS environments):
- Mapping is mostly **mechanical** (name substitution)
- Hard part: Identifying what **cannot** be copied (isolation points)
- Example: dev environment → staging environment

### Heterogeneous Transfer

Source and target are **different types** (e.g., library → codebase):
- Mapping requires **understanding** (algorithm → implementation)
- Hard part: Preserving **essence** while changing **form**
- Example: Python library → native implementation

---

## Transfer Difficulty Spectrum

```
EASIER ←────────────────────────────────────────────→ HARDER

Homogeneous                                    Heterogeneous
├────────────┬────────────┬────────────┬────────────┤
│            │            │            │            │
/provision-env  /adapt     /adapt      /adapt
(dev→staging)   (branch)   (library)   (paper)
│            │            │            │
Same type    Same lang    Same lang    Different
Mechanical   Similar      Different    medium
mapping      patterns     patterns     No code
└────────────┴────────────┴────────────┴────────────┘
```

---

## Common Pitfalls

### 1. Blind Copying
**Problem**: Copying without understanding → "foreign tissue" in codebase
**Solution**: Always complete Step 2 (ANALYZE SOURCE) with `/qna`

### 2. Missing Isolation Points
**Problem**: Copying credentials/names that should be isolated
**Solution**: Explicitly identify context-bound elements in Step 5

### 3. Skipping Verification
**Problem**: Assuming transfer worked without testing
**Solution**: Always complete Step 7 with `/invariant` and 4-layer evidence

### 4. Ignoring Target Principles
**Problem**: Transferred code violates CLAUDE.md principles
**Solution**: Check target constraints (Step 3) include principle compliance

### 5. Wrong Loop on Failure
**Problem**: Retrying when should escalate to `/qna`
**Solution**: After 2 retries, escalate to Initial-Sensitive loop

---

## Layered Architecture

The foundation supports future shortcuts without modification:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Intent Verbs (Future, Ad-hoc)                     │
│  /learn, /clone, /port, /converge                           │
│  ↓ routes to                                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Unified Command (Future, Optional)                │
│  /move "X" to "Y" [with auto-detection]                     │
│  ↓ routes to                                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: FOUNDATION (This Document)                        │
│  Transform(X, Context_A, Context_B, Invariants) → X'        │
│                                                             │
│  Dimensions:                                                │
│  • WHAT: code | infra | state                               │
│  • WHERE: external→internal | internal→internal | current→goal │
│  • HOW: copy | adapt | preserve                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Domain Commands (Current Implementation)          │
│  /adapt, /provision-env, /step                              │
└─────────────────────────────────────────────────────────────┘
```

**Adding shortcuts later**: When friction appears in usage, add intent verbs that route to existing commands. The foundation doesn't change.

---

## Command Selection Guide

```
"I want to learn from external code"
  → /adapt (code, external→internal, adapt)

"I want to create a new environment"
  → /provision-env (infra, internal→internal, copy)

"I want to reach a goal state"
  → /step (state, current→goal, preserve)

"I want to port branch changes"
  → /adapt (code, internal→internal, adapt)

"I want to understand the theory"
  → /transfer (this document)
```

---

## See Also

### Specializations (Layer 0)
- [/adapt](adapt.md) - Code transfer (heterogeneous)
- [/provision-env](provision-env.md) - Infrastructure transfer (homogeneous)
- [/step](step.md) - State transformation

### Key Integrations
- [/qna](qna.md) - Surface assumptions in Step 2 (ANALYZE SOURCE)
- [/invariant](invariant.md) - Verify invariants in Step 7 (VERIFY)

### Principles
- [CLAUDE.md - Principle #25](../CLAUDE.md) - Behavioral Invariant Verification
- [CLAUDE.md - Principle #26](../CLAUDE.md) - Thinking Tuple Protocol
- [CLAUDE.md - Principle #9](../principles/meta-principles.md) - Feedback Loop Awareness

### Guides
- [Thinking Tuple Protocol](../../docs/guides/thinking-tuple-protocol.md) - Tuple integration
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Invariant verification
