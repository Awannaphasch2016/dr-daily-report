# Contextual Transfer Framework

**Type**: Workflow Pattern
**Date**: 2026-01-11
**Confidence**: HIGH
**Source**: LINE bot staging deployment incident + /adapt command analysis

---

## Abstract Pattern

**Contextual Transfer** is a generalized operation for moving concepts between contexts while preserving essence and rewiring dependencies.

```
Transfer(concept, source_context, target_context) → adapted_concept

Where:
  - concept: What needs to be moved (the "essence")
  - source_context: Where it currently exists/works
  - target_context: Where it needs to work
  - adapted_concept: The concept rewired for target
```

---

## The Core Insight

**All transfer operations share the same thinking process**, regardless of domain:

1. **IDENTIFY** what to transfer
2. **ANALYZE SOURCE** context and dependencies
3. **ANALYZE TARGET** context and constraints
4. **MAP** source concepts to target equivalents
5. **UNTANGLE** portable from context-bound
6. **REWIRE** for target context
7. **VERIFY** transfer success

This process applies to:
- Code patterns (library → codebase)
- Infrastructure (dev → staging)
- Knowledge (document → implementation)
- Config (one system → another)

---

## Transfer Type Spectrum

```
HOMOGENEOUS                                    HETEROGENEOUS
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Source type = Target type     Source type ≠ Target type  │
│  Mechanical mapping            Requires understanding      │
│  Find isolation points         Preserve essence            │
│                                                            │
│  Examples:                     Examples:                   │
│  - dev → staging               - library → codebase        │
│  - staging → prod              - paper → implementation    │
│  - project A → project B       - docs → code               │
└────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### Portable vs Context-Bound

Every concept has two parts:

```
┌─────────────────────────────────────┐
│           CONCEPT                   │
├─────────────────────────────────────┤
│  PORTABLE (the essence):            │
│  - Core algorithm/logic             │
│  - Fundamental structure            │
│  - Problem-solving approach         │
│  - Can move unchanged               │
├─────────────────────────────────────┤
│  CONTEXT-BOUND (the implementation):│
│  - Dependencies on source env       │
│  - Source-specific naming           │
│  - Source-specific integrations     │
│  - Must be rewired for target       │
└─────────────────────────────────────┘
```

### Isolation Points

In homogeneous transfer, the key challenge is identifying **isolation points** - things that look copyable but actually need to be unique per context:

| Domain | Looks Copyable | Actually Isolated |
|--------|---------------|-------------------|
| Infrastructure | Credentials | Per-environment (LINE tokens) |
| Code | Import paths | Per-project structure |
| Config | API keys | Per-service account |

---

## Domain Applications

### Infrastructure (Homogeneous)

**Command**: `/provision-env`

| Aspect | Value |
|--------|-------|
| Source | Existing environment (dev) |
| Target | New environment (staging) |
| Portable | Terraform structure, IAM shapes |
| Context-bound | Names, external credentials, ARNs |
| Key risk | Credential sharing (isolation violation) |

### Code (Heterogeneous)

**Command**: `/adapt`

| Aspect | Value |
|--------|-------|
| Source | External library/repo/docs |
| Target | Our codebase |
| Portable | Algorithm logic, patterns |
| Context-bound | Language syntax, framework patterns |
| Key risk | Blind copying ("foreign tissue") |

### Future Applications

The framework can extend to:
- `/migrate-schema` - Database schema transfer
- `/port-config` - Configuration transfer
- `/clone-project` - Project template transfer

---

## Why This Matters

### Without Framework

Each transfer operation is "reinvented":
- Different checklists
- Different mental models
- Inconsistent verification
- Repeated mistakes

### With Framework

Single mental model:
- Consistent 7-step process
- Shared vocabulary (portable, context-bound, isolation points)
- Systematic verification
- Learnings transfer across domains

---

## Real-World Validation

### LINE Bot Staging Incident (2026-01-11)

**What happened**: Copied dev LINE credentials to staging Lambda. Lambda returned 200, but user received no message.

**Framework analysis**:
- Step 5 (UNTANGLE) was skipped
- LINE credentials were treated as portable (wrong)
- Actually context-bound (per-channel webhooks)
- Step 7 (VERIFY) stopped at Layer 1 (HTTP 200)
- Should have verified Layer 4 (user receives message)

**Framework would have caught it**:
1. Step 5 explicitly asks: "What is context-bound?"
2. External credentials are ALWAYS context-bound
3. Step 7 requires ground truth verification

See: [LINE Staging Lessons](../reports/2026-01-11-line-staging-credential-isolation-lessons.md)

---

## Integration with Principles

| CLAUDE.md Principle | Framework Application |
|---------------------|----------------------|
| #1 Defensive Programming | Step 7 verification checklist |
| #2 Progressive Evidence | Step 7 uses 4-layer verification |
| #15 Infrastructure Contract | Steps 2-3 analyze contracts |
| #24 Credential Isolation | Step 5 identifies isolation points |

---

## Command Hierarchy

```
/transfer (abstract framework)
    │
    ├── /adapt (heterogeneous - code)
    │   └── 6-phase workflow specialization
    │
    └── /provision-env (homogeneous - infrastructure)
        └── Infrastructure-specific checklist
```

---

## See Also

- [/transfer](../commands/transfer.md) - Abstract command
- [/adapt](../commands/adapt.md) - Code specialization
- [/provision-env](../commands/provision-env.md) - Infrastructure specialization
- [LINE Staging Lessons](../reports/2026-01-11-line-staging-credential-isolation-lessons.md) - Incident that revealed pattern
