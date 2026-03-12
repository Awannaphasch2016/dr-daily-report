---
name: merge
description: Universal transformation primitive - combine entities A and B given invariant specification
accepts_args: true
arg_schema:
  - name: entity_a
    required: true
    description: "First entity (file, concept, spec, branch, etc.)"
  - name: entity_b
    required: true
    description: "Second entity to merge with"
  - name: strategy
    required: false
    description: "Merge strategy: preserve|conform|adapt|copy or custom invariant spec"
---

# Merge Command

**Purpose**: Universal transformation primitive for combining two entities given an invariant specification

**Core Principle**: All transformations are merges with different invariant constraints. `/merge` is the **foundation** from which `/move`, `/adapt`, `/reconcile`, and `/provision-env` derive.

**When to use**:
- Combining two partially-overlapping entities
- Any transformation where both source and target matter
- When you need fine-grained control over what survives
- When existing commands (`/move`, `/adapt`, `/reconcile`) don't fit

---

## Tuple Effects (Universal Kernel Integration)

**Part of the Agent Kernel** - The foundational transformation primitive.

**Mode Type**: `combine`

**Tier**: 0 (Foundation - other transform commands derive from this)

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **EXPAND**: Loads both entities A and B into working set |
| **Invariant** | **SET**: Merge strategy determines what must hold in result |
| **Principles** | **NONE**: Does not modify principles |
| **Strategy** | Consumes this mode; may chain with `/validate` |
| **Check** | **EVALUATE**: Verifies result satisfies invariant specification |

**Local Check** (mode-specific completion):
- Both entities loaded and understood
- Overlap identified (shared properties/concepts)
- Non-overlap handled per strategy (preserve/discard/transform)
- Result satisfies invariant specification

---

## The Merge Abstraction

```
/merge(A, B, Invariants) → C

Where Invariants = {
  preserve: [properties that MUST exist in C],
  protect:  [properties that MUST NOT change],
  discard:  [properties that CAN be lost],
  transform:[properties that CAN be modified for compatibility]
}
```

### Visual Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     MERGE OPERATION                              │
│                                                                  │
│   Entity A ───┐                                                  │
│    (source)   │     ┌──────────────────────┐                    │
│               ├────→│    Merge Engine      │────→ Entity C      │
│               │     │                      │      (result)      │
│   Entity B ───┘     │  Invariant Spec:     │                    │
│    (target)         │  ├─ preserve: [...]  │                    │
│                     │  ├─ protect:  [...]  │                    │
│                     │  ├─ discard:  [...]  │                    │
│                     │  └─ transform:[...]  │                    │
│                     └──────────────────────┘                    │
│                              ↑                                   │
│                     Dependency Graph                             │
│                     (transitive closure)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Built-in Strategies (Specializations)

These strategies are pre-defined invariant specifications:

### `preserve` (what `/move` uses)

```yaml
strategy: preserve
invariant:
  preserve: [A.*]           # Keep everything from A
  protect: [B.*]            # Don't change B
  discard: []               # Lose nothing
  transform: []             # Modify nothing
```

**Semantics**: Transfer A into B's context without changing either.

### `conform` (what `/reconcile` uses)

```yaml
strategy: conform
invariant:
  preserve: [B.*]           # B (standard) wins
  protect: []               # A can change completely
  discard: [A - B]          # Lose A's non-conforming parts
  transform: [A ∩ B]        # A's shared parts adapt to B
```

**Semantics**: Make A conform to B (standard), lose non-conforming parts.

### `adapt` (what `/adapt` uses)

```yaml
strategy: adapt
invariant:
  preserve: [A.behavior]    # Keep A's behavior
  protect: [B.conventions]  # Don't break B's conventions
  discard: []               # Lose nothing essential
  transform: [A.surface]    # Adapt A's surface to B's style
```

**Semantics**: Keep A's behavior, adapt to B's conventions.

### `copy` (what `/provision-env` uses)

```yaml
strategy: copy
invariant:
  preserve: [A.config]      # Keep A's configuration
  protect: []               # Target is new (nothing to protect)
  discard: []               # Lose nothing
  transform: [A.identifiers]# Change identifiers for new context
```

**Semantics**: Copy A with identity transformation for new context.

---

## Derivation Hierarchy

```
                        /merge (Foundation)
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

**Proof**: Each derived command is `/merge` with fixed strategy:

| Command | Equivalent `/merge` |
|---------|---------------------|
| `/move A to B` | `/merge A B --strategy=preserve` |
| `/reconcile A to Standard` | `/merge A Standard --strategy=conform` |
| `/adapt External to Internal` | `/merge External Internal --strategy=adapt` |
| `/provision-env Source Target` | `/merge Source Target --strategy=copy` |

---

## Quick Reference

```bash
# Using built-in strategies
/merge A B --strategy=preserve      # Same as /move
/merge A B --strategy=conform       # Same as /reconcile
/merge A B --strategy=adapt         # Same as /adapt
/merge A B --strategy=copy          # Same as /provision-env

# Custom invariant specification
/merge telegram-spec linebot-spec --preserve="shared.backend" --protect="telegram.miniapp"

# Dependency-aware merge
/merge feature-A feature-B --preserve="A.auth" --protect="*.depends_on(auth)"

# Join-type shorthand (for simple set operations)
/merge A B --join=inner    # Only overlap survives
/merge A B --join=outer    # Everything survives (union)
/merge A B --join=left     # A + overlap
/merge A B --join=right    # B + overlap
```

---

## Invariant Specification Syntax

### Simple (Join Types)

```bash
/merge A B --join=inner|outer|left|right|anti
```

| Join | Invariant | Result |
|------|-----------|--------|
| `inner` | `preserve: [A ∩ B]` | Only shared |
| `outer` | `preserve: [A ∪ B]` | Everything |
| `left` | `preserve: [A]` | A + compatible B |
| `right` | `preserve: [B]` | B + compatible A |
| `anti` | `preserve: [A ⊕ B]` | Only non-overlap (XOR) |

### Property-Based

```bash
/merge A B --preserve="auth,validation" --protect="api_contract" --discard="deprecated"
```

### Dependency-Aware

```bash
/merge A B --preserve="A.auth" --protect="*.depends_on(auth)"
```

Expands `*.depends_on(auth)` to include all transitive dependents.

### Full Specification

```bash
/merge A B --invariant="
  preserve:
    - A.session_handling
    - A.token_validation
  protect:
    - B.api_contract
    - shared.user_model
  discard:
    - A.deprecated_methods
  transform:
    - A.config_format → B.config_format
"
```

---

## Execution Flow

### Step 1: Load Entities

```markdown
## Entity Analysis

### Entity A: {path/concept}
**Type**: {file | concept | spec | branch | ...}
**Properties**: {list of identifiable properties}
**Dependencies**: {what A depends on}

### Entity B: {path/concept}
**Type**: {file | concept | spec | branch | ...}
**Properties**: {list of identifiable properties}
**Dependencies**: {what B depends on}
```

### Step 2: Identify Overlap

```markdown
## Overlap Analysis

**Shared (A ∩ B)**:
- {property in both}
- {property in both}

**Only in A (A - B)**:
- {property only in A}

**Only in B (B - A)**:
- {property only in B}

**Dependency Graph**:
{property} → {dependent} → {transitive dependent}
```

### Step 3: Apply Invariant Specification

```markdown
## Merge Plan

**Preserve** (must exist in result):
- {property} from A ✓
- {property} from B ✓

**Protect** (must not change):
- {property} in B (unchanged) ✓

**Discard** (can be lost):
- {property} from A (not needed)

**Transform** (adapt for compatibility):
- {A.property} → {B.style}

**Conflicts**:
- {conflict 1}: {resolution}
```

### Step 4: Generate Result

```markdown
## Merge Result: C

**From A (preserved)**:
- {property}

**From B (protected)**:
- {property}

**Transformed**:
- {property} (was: {old}, now: {new})

**Discarded**:
- {property} (reason: {why})

**Validation**:
- Invariant satisfied: ✓
- No protected properties changed: ✓
- All preserved properties exist: ✓
```

---

## Examples

### Example 1: Merge Specs (Outer Join)

```bash
/merge telegram/invariants.md linebot/invariants.md --join=outer
```

**Result**: Combined invariants document with:
- Telegram-specific invariants (Mini App)
- LINE-specific invariants (Chat-based)
- Shared backend invariants (both platforms)

### Example 2: Merge Features (Preserve Auth)

```bash
/merge feature-auth feature-api --preserve="auth.*" --protect="api.contract"
```

**Result**: Combined feature with:
- All auth logic preserved
- API contract unchanged
- Compatible parts merged

### Example 3: Custom Strategy

```bash
/merge dev-config prod-config --invariant="
  preserve:
    - prod.security_settings
    - prod.connection_strings
  protect:
    - prod.api_keys
  transform:
    - dev.debug_flags → disabled
"
```

**Result**: Production-ready config with dev convenience features disabled.

---

## Relationship to Derived Commands

### Why Keep `/move`, `/adapt`, `/reconcile`?

**Convenience**: Common patterns deserve simple names.

| Use Case | Use This | Not This |
|----------|----------|----------|
| Simple transfer | `/move A B` | `/merge A B --strategy=preserve` |
| Conform to standard | `/reconcile A Standard` | `/merge A Standard --strategy=conform` |
| Adapt to conventions | `/adapt External Internal` | `/merge External Internal --strategy=adapt` |
| Complex merge | `/merge A B --invariant="..."` | (no shorthand) |

**Guideline**: Use derived commands for common cases, `/merge` for complex cases.

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| Merge without invariant | Result undefined | Always specify strategy |
| Ignore dependencies | Break transitive properties | Use `--protect="*.depends_on(X)"` |
| Preserve everything | Conflicts unresolved | Explicitly handle non-overlap |
| Discard without review | Lose important properties | Review discard list before applying |

---

## See Also

- `/move` - Specialization: preserve strategy
- `/adapt` - Specialization: adapt strategy
- `/reconcile` - Specialization: conform strategy
- `/provision-env` - Specialization: copy strategy
- `/transfer` - Theory documentation for transformation abstraction
- [Compositional Hierarchy](.claude/principles/compositional-hierarchy.md) - Tier structure

---

## Prompt Template

You are executing the `/merge` command.

**Entity A**: $1
**Entity B**: $2
**Strategy/Invariant**: $3 (or flags)

---

### Execution Steps

1. **Load entities**: Identify properties, dependencies, types
2. **Analyze overlap**: Find A ∩ B, A - B, B - A
3. **Build dependency graph**: Identify transitive dependencies
4. **Apply invariant**: Determine what to preserve/protect/discard/transform
5. **Resolve conflicts**: Handle incompatible properties
6. **Generate result**: Create merged entity C
7. **Validate**: Verify invariant specification satisfied

**Output**: Use format above with clear merge plan and result.

---

*Command: /merge*
*Mode: combine*
*Tier: 0 (Foundation)*
*Derivations: /move, /adapt, /reconcile, /provision-env*
