# Knowledge Evolution Report: /merge as Foundational Primitive

**Date**: 2026-01-16
**Focus**: Commands - Establishing /merge as the Tier-0 universal transformation primitive
**Type**: PARADIGM_SHIFT (architectural restructuring)

---

## Executive Summary

**Change**: Established `/merge` as the foundational transformation primitive from which all other transform commands derive.

**Impact**:
- Agent Kernel now has a clear derivation hierarchy for all transformation operations
- `/move`, `/adapt`, `/reconcile`, `/provision-env` are now formally defined as specializations of `/merge`
- Invariant-driven merge semantics provide a unified theory for all transformations

**Files Created**: 1
**Files Updated**: 5
**Principles Addressed**: #27 (Commands as Strategy Modes), #28 (Compositional Hierarchy)

---

## The Insight

**User's key insight**: All transformations are merges with different invariant constraints.

```
/move = /merge with strategy=preserve
/adapt = /merge with strategy=adapt
/reconcile = /merge with strategy=conform
/provision-env = /merge with strategy=copy
```

This unification reveals that the fundamental operation is **combining two entities with an invariant specification** that determines what survives.

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

### Built-in Strategies (Specializations)

| Strategy | Preserve | Protect | Discard | Transform | Command |
|----------|----------|---------|---------|-----------|---------|
| `preserve` | A.* | B.* | [] | [] | `/move` |
| `conform` | B.* | [] | A - B | A ∩ B | `/reconcile` |
| `adapt` | A.behavior | B.conventions | [] | A.surface | `/adapt` |
| `copy` | A.config | [] | [] | A.identifiers | `/provision-env` |

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

**Proof**: Each derived command is `/merge` with fixed strategy:

| Command | Equivalent `/merge` |
|---------|---------------------|
| `/move A to B` | `/merge A B --strategy=preserve` |
| `/reconcile A to Standard` | `/merge A Standard --strategy=conform` |
| `/adapt External to Internal` | `/merge External Internal --strategy=adapt` |
| `/provision-env Source Target` | `/merge Source Target --strategy=copy` |

---

## Files Modified

### 1. `.claude/commands/merge.md` (CREATED)

New Tier-0 foundational command with:
- Complete invariant specification syntax
- Built-in strategies (preserve, conform, adapt, copy)
- Join type shortcuts (inner, outer, left, right, anti)
- Dependency-aware merging
- Execution flow (7-step process)
- Examples for all use cases

**Key sections**:
- Tuple Effects (combine mode, Tier-0)
- The Merge Abstraction
- Built-in Strategies (Specializations)
- Derivation Hierarchy
- Invariant Specification Syntax
- Execution Flow

### 2. `.claude/commands/move.md` (UPDATED)

**Before**: "Executable Foundation"
**After**: Specialization of `/merge` with `strategy=preserve`

Added:
- Relationship to /merge (Foundation) section
- Derivation Hierarchy diagram
- Tuple Effects (transform mode, Tier-1)
- Updated See Also with foundation hierarchy

### 3. `.claude/commands/adapt.md` (UPDATED)

**Before**: Specializes `/move`
**After**: Derives from `/merge` with `strategy=adapt`, routes through `/move`

Added:
- Relationship to /merge (Foundation) section
- Derivation Hierarchy diagram
- Tuple Effects (transform mode, Tier-1)
- Equivalent calls showing merge equivalence
- Updated See Also with foundation hierarchy

### 4. `.claude/commands/reconcile.md` (UPDATED)

**Before**: Mode type `fix` only
**After**: Derives from `/merge` with `strategy=conform`

Added:
- Relationship to /merge (Foundation) section
- Derivation Hierarchy diagram
- Tuple Effects updated with Tier-1 classification
- Equivalent calls showing merge equivalence
- Updated See Also with foundation hierarchy

### 5. `.claude/commands/provision-env.md` (UPDATED)

**Before**: Specializes `/move`
**After**: Derives from `/merge` with `strategy=copy`, routes through `/move`

Added:
- Relationship to /merge (Foundation) section
- Derivation Hierarchy diagram
- Tuple Effects (transform mode, Tier-1)
- Equivalent calls showing merge equivalence
- Updated See Also with foundation hierarchy

### 6. `.claude/CLAUDE.md` (UPDATED)

**Command table (Principle #27)**:
- Added `/merge` with mode `combine`, marked as Tier-0 Foundation
- Updated `/move`, `/adapt`, `/reconcile`, `/provision-env` to reference `/merge` derivation

**Applied Across Domains table (Principle #28)**:
- Updated Commands row to show:
  - Tier-0: Foundation (/merge), Atomic (/explore, /validate)
  - Tier-1: Specialized (/move, /adapt, /reconcile)
  - Tier-2+: Orchestrated (/optimize, /analysis)

---

## Mode Type Rationale

**Why `combine` mode for /merge?**

| Mode | Purpose | Example Commands |
|------|---------|------------------|
| `clarify` | Build understanding | `/understand` |
| `verify` | Test claims | `/validate` |
| `transform` | Change representations | `/move`, `/adapt` |
| `execute` | Perform side effects | `/deploy` |
| `meta` | Operate on Agent Kernel | `/evolve` |
| `fix` | Converge to compliance | `/reconcile` |
| **`combine`** | **Merge two entities** | **`/merge`** |

`/merge` introduces a new mode type because it's the foundational operation that all transform modes derive from. It's not just "transform" because it explicitly handles the two-entity combining semantics.

---

## Tier Classification

| Command | Tier | Rationale |
|---------|------|-----------|
| `/merge` | 0 (Foundation) | All transform commands derive from it |
| `/move` | 1 (Specialized) | Fixed strategy=preserve |
| `/adapt` | 1 (Specialized) | Fixed strategy=adapt |
| `/reconcile` | 1 (Specialized) | Fixed strategy=conform |
| `/provision-env` | 1 (Specialized) | Fixed strategy=copy |

---

## Design Decision: Why Not Just Enhance /move?

The user's insight was profound: `/move` was already the "executable foundation" but it assumed a preserve-everything strategy. The more general operation is:

1. **Take two entities** (not just transfer one)
2. **Specify what survives** (not just "preserve everything")
3. **Handle overlap explicitly** (not implicitly)

This makes `/merge` the true foundation, with `/move` being the common case (preserve everything).

**Guideline**: Use derived commands for common cases, `/merge` for complex cases requiring fine-grained control.

---

## Validation

### Command Table Check

After update, CLAUDE.md command table includes:

```markdown
| `/merge` | combine | **Tier-0 Foundation**: Universal transformation primitive; all transforms derive from this |
| `/move` | transform | **Tier-1**: Specialization of `/merge` with `strategy=preserve` |
| `/adapt` | transform | **Tier-1**: Specialization of `/merge` with `strategy=adapt` |
| `/reconcile` | fix | **Tier-1**: Specialization of `/merge` with `strategy=conform` |
| `/provision-env` | transform | **Tier-1**: Specialization of `/merge` with `strategy=copy` |
```

### Derivation Consistency

All transform commands now:
- Have "Relationship to /merge (Foundation)" section
- Show derivation hierarchy diagram
- Include equivalent `/merge` calls
- Reference `/merge` in See Also

### Compositional Hierarchy

Applied Across Domains table now correctly shows:
- Commands Tier-0: Foundation (/merge), Atomic (/explore, /validate)
- Commands Tier-1: Specialized (/move, /adapt, /reconcile)

---

## Benefits

1. **Unified Theory**: All transformations explained by one primitive
2. **Clear Derivation**: Hierarchy shows why commands exist
3. **Fine-grained Control**: `/merge` available for complex cases
4. **Convenience Preserved**: Derived commands remain simple to use
5. **Compositional Hierarchy**: Tier structure now consistent across commands

---

## Future Implications

The `/merge` foundation enables:
- **Custom strategies**: Users can define their own invariant specifications
- **Dependency-aware merging**: `--protect="*.depends_on(X)"` syntax
- **Composition**: Higher-tier commands can combine merges
- **Analysis**: Understanding any transformation as "what invariants were applied"

---

## References

- [/merge command](.claude/commands/merge.md) - New foundational primitive
- [/move command](.claude/commands/move.md) - Updated to derive from /merge
- [/adapt command](.claude/commands/adapt.md) - Updated to derive from /merge
- [/reconcile command](.claude/commands/reconcile.md) - Updated to derive from /merge
- [/provision-env command](.claude/commands/provision-env.md) - Updated to derive from /merge
- [CLAUDE.md - Commands as Strategy Modes](../CLAUDE.md#27-commands-as-strategy-modes) - Command table
- [CLAUDE.md - Compositional Hierarchy](../CLAUDE.md#28-compositional-hierarchy) - Tier structure

---

*Evolution report generated by `/evolve`*
*Generated: 2026-01-16*
