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

# Transfer Command (Abstract Framework)

**Purpose**: Generalized framework for contextual transfer operations - moving concepts from one context to another while preserving essence and rewiring dependencies.

**This is an ABSTRACT command** - use domain-specific specializations:
- `/adapt` - Transfer code patterns (heterogeneous: library → codebase)
- `/provision-env` - Transfer infrastructure (homogeneous: dev → staging)

---

## Core Concept

**Contextual Transfer** is the operation of moving a concept from one context to another:

```
Transfer(concept, source_context, target_context) → adapted_concept

Where:
  - concept: What needs to be moved (the "essence")
  - source_context: Where it currently exists/works
  - target_context: Where it needs to work
  - adapted_concept: The concept rewired for target
```

---

## The 7-Step Transfer Process

### Step 1: IDENTIFY

**What concept/artifact needs to be transferred?**

Questions to answer:
- What is the **essence** that must be preserved?
- What is the **boundary** of the transfer?
- What **problem** does this concept solve?

Output: Clear definition of what we're transferring

---

### Step 2: ANALYZE SOURCE

**What is the source context?**

Questions to answer:
- What **dependencies** exist in source?
- What **assumptions** are embedded?
- What is **implicit** vs **explicit**?
- What **environment** does source expect?

Output: Dependency map of source context

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

### Step 7: VERIFY

**Confirm transfer succeeded**

Verification checklist:
- [ ] Does it **work** in target context?
- [ ] Is **essence** preserved?
- [ ] Are all **dependencies** satisfied?
- [ ] Does it follow **target principles**? (CLAUDE.md)
- [ ] Is **ground truth** verified? (Principle #2)

Output: Verification report

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
- Example: Python library → JavaScript implementation

---

## Transfer Difficulty Spectrum

```
EASIER ←────────────────────────────────────────────→ HARDER

Homogeneous                                    Heterogeneous
├────────────┬────────────┬────────────┬────────────┤
│            │            │            │            │
/provision-env  /adapt     /adapt      /adapt
(dev→staging)   (branch)   (library)   (paper)
│            │            │            │            │
Same type    Same lang    Same lang    Different
Mechanical   Similar      Different    medium
mapping      patterns     patterns     No code
└────────────┴────────────┴────────────┴────────────┘
```

---

## Common Pitfalls

### 1. Blind Copying
**Problem**: Copying without understanding → "foreign tissue" in codebase
**Solution**: Always complete Step 2 (ANALYZE SOURCE) before copying

### 2. Missing Isolation Points
**Problem**: Copying credentials/names that should be isolated
**Solution**: Explicitly identify context-bound elements in Step 5

### 3. Skipping Verification
**Problem**: Assuming transfer worked without testing
**Solution**: Always complete Step 7 with ground truth verification

### 4. Ignoring Target Principles
**Problem**: Transferred code violates CLAUDE.md principles
**Solution**: Check target constraints (Step 3) include principle compliance

---

## Specializations

Use domain-specific commands that extend this framework:

### `/adapt` - Code Transfer
- **Domain**: Code patterns, algorithms, techniques
- **Transfer type**: Heterogeneous (library → codebase)
- **Key challenge**: Preserve algorithm essence, change implementation
- See: [/adapt](adapt.md)

### `/provision-env` - Infrastructure Transfer
- **Domain**: Infrastructure configuration
- **Transfer type**: Homogeneous (env → env)
- **Key challenge**: Identify isolation points (external credentials)
- See: [/provision-env](provision-env.md)

---

## When to Use Which

```
"I want to learn from external code"
  → /adapt

"I want to create a new environment"
  → /provision-env

"I want to understand the transfer process"
  → /transfer (this document)
```

---

## See Also

- [/adapt](adapt.md) - Code transfer specialization
- [/provision-env](provision-env.md) - Infrastructure transfer specialization
- [Contextual Transfer Framework](../abstractions/workflow-2026-01-11-contextual-transfer-framework.md) - Detailed abstraction
- [CLAUDE.md](../CLAUDE.md) - Target principles for transfers
