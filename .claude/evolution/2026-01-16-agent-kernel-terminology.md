# Knowledge Evolution Report: Agent Kernel Terminology

**Date**: 2026-01-16
**Focus**: Terminology - Establishing "Agent Kernel" as official term
**Type**: NEW_PATTERN (terminology standardization)

---

## Executive Summary

**Change**: Established "Agent Kernel" as the official term for the complete knowledge system

**Impact**:
- Single term to refer to the entire `.claude/*` + `docs/*` architecture
- Clear distinction between Agent Kernel (whole system) and Thinking Tuple (runtime engine)
- Consistent terminology across all documentation

**Files Updated**: 5
**Principles Addressed**: #28 (Compositional Hierarchy - making layers explicit)

---

## The Change

### Before

| Term | Usage | Problem |
|------|-------|---------|
| "Universal Kernel" | Thinking Tuple Protocol | Also used loosely for whole system |
| "Knowledge System" | X-ray report | Not consistently used |
| "Claude System" | Informal | Ambiguous |
| (none) | Whole architecture | No single term existed |

**Problem**: No consistent term to refer to the complete knowledge architecture (skills + specs + commands + docs + principles + invariants).

### After

| Term | Definition | Scope |
|------|------------|-------|
| **Agent Kernel** | Complete knowledge system | `.claude/*` + `docs/*` |
| **Thinking Tuple Protocol** | Runtime reasoning engine | Principle #26 |
| **Universal Kernel** | Synonym for Thinking Tuple | (kept for backward compatibility) |

**Relationship**:
```
Agent Kernel (the whole system)
├── Thinking Tuple Protocol (runtime reasoning engine)
├── Commands Layer (40+ workflows)
├── Skills Layer (15 domain expertise modules)
├── Principles Layer (28 guidelines, Tier-0/1/2/3)
├── Specs Layer (feature contracts)
├── Invariants Layer (behavioral constraints)
├── Knowledge Artifacts (journals, observations, validations, abstractions)
└── Documentation (docs/guides, docs/adr, docs/deployment)
```

---

## Files Modified

### 1. `.claude/CLAUDE.md`

**Added** (after title, before "About This Document"):
- New "Agent Kernel" section with ASCII architecture diagram
- Key Terminology definitions
- Usage guidelines for when to use each term

**Key content**:
```markdown
## Agent Kernel

The **Agent Kernel** is the complete knowledge system that powers Claude's reasoning in this project.

**Key Terminology**:
- **Agent Kernel**: The complete system (`.claude/*` + `docs/*`)
- **Thinking Tuple Protocol**: The runtime reasoning engine (Principle #26)
- **Universal Kernel**: Synonym for Thinking Tuple Protocol

**Use "Agent Kernel" when referring to**: The whole knowledge architecture
**Use "Thinking Tuple" when referring to**: The specific reasoning protocol
```

### 2. `.claude/commands/README.md`

**Added** (line 3):
```markdown
**Part of the Agent Kernel** - The orchestration layer for composable workflows.

> **Agent Kernel** = The complete knowledge system (`.claude/*` + `docs/*`).
> Commands are one layer within the Agent Kernel.
```

### 3. `docs/guides/thinking-tuple-protocol.md`

**Updated** Overview section:
- Added terminology definitions
- Clarified that Thinking Tuple is the "runtime reasoning engine within the Agent Kernel"
- Added link to CLAUDE.md Agent Kernel definition

### 4. `.claude/reports/2026-01-13-xray-claude-knowledge-architecture.md`

**Updated**:
- Title: "X-Ray: Claude Knowledge Architecture" → "X-Ray: Agent Kernel Architecture"
- Added Agent Kernel definition reference
- Updated date to show modification

### 5. `.claude/skills/README.md`

**Added** (line 3):
```markdown
**Part of the Agent Kernel** - Auto-discovered capabilities for specialized assistance.

> **Agent Kernel** = The complete knowledge system (`.claude/*` + `docs/*`).
> Skills are one layer within the Agent Kernel.
```

---

## Validation

### Terminology Consistency

After updates, searching for "Agent Kernel" returns:
- CLAUDE.md (canonical definition)
- commands/README.md (reference)
- skills/README.md (reference)
- thinking-tuple-protocol.md (relationship)
- x-ray report (architecture description)
- evolution reports (documentation)

### Usage Guidelines Established

| Context | Term to Use |
|---------|-------------|
| Referring to whole system | "Agent Kernel" |
| Referring to reasoning protocol | "Thinking Tuple Protocol" |
| Backward compatibility | "Universal Kernel" (= Thinking Tuple) |
| Specific layer | Name the layer (Commands, Skills, Principles, etc.) |

---

## Why This Matters

### Before

- No single term for the complete system
- "Universal Kernel" used ambiguously (sometimes whole system, sometimes just Thinking Tuple)
- Difficult to discuss architecture at the right abstraction level

### After

- **Agent Kernel**: Clear term for entire knowledge architecture
- **Thinking Tuple**: Specific term for runtime reasoning engine
- Can discuss layers individually or refer to the whole with precision

### Example Usage

```markdown
❌ Before: "The skills and commands and principles work together..."
✅ After:  "The Agent Kernel orchestrates skills, commands, and principles..."

❌ Before: "Update the Universal Kernel to include new specs"
✅ After:  "Update the Agent Kernel to include new specs" (whole system)
           OR "The Thinking Tuple loads specs into Constraints" (runtime)
```

---

## References

- [CLAUDE.md - Agent Kernel](../CLAUDE.md#agent-kernel) - Canonical definition
- [Thinking Tuple Protocol](../../docs/guides/thinking-tuple-protocol.md) - Runtime engine
- [X-Ray: Agent Kernel Architecture](../reports/2026-01-13-xray-claude-knowledge-architecture.md) - Full architecture analysis

---

*Evolution report generated by `/evolve`*
*Generated: 2026-01-16*
