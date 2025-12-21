# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural choices made in the Daily Report project.

## What is an ADR?

An ADR documents a significant architectural decision along with its context and consequences. It creates a historical record of why certain approaches were chosen.

## When to Write an ADR

Write an ADR when a decision:
- Changes system architecture or data flow
- Impacts cost, performance, or reliability significantly
- Involves choosing between multiple valid approaches
- Is irreversible or expensive to change later
- Affects multiple components or teams

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-adopt-semantic-layer-architecture.md) | Adopt Semantic Layer Architecture | ✅ Accepted | 2024-12-21 |
| [002](002-use-openrouter-proxy.md) | Use OpenRouter as LLM Proxy | ✅ Accepted | 2024-01 |
| [003](003-service-singletons.md) | Service Singletons vs Dependency Injection | ✅ Accepted | 2024-01 |
| [004](004-langgraph-typeddict-state.md) | LangGraph TypedDict State | ✅ Accepted | 2024-01 |
| [005](005-correlation-based-peer-comparison.md) | Correlation-Based Peer Comparison | ✅ Accepted | 2024-02 |
| [006](006-two-separate-apps.md) | Two Separate Apps (LINE + Telegram) | ✅ Accepted | 2024-03 |
| [007](007-single-root-terraform.md) | Single Root Terraform Architecture | ✅ Accepted | 2024-11 |
| [008](008-directory-structure-over-workspaces.md) | Directory Structure Over Terraform Workspaces | ✅ Accepted | 2024-11 |
| [009](009-artifact-promotion.md) | Artifact Promotion Over Per-Env Builds | ✅ Accepted | 2024-11 |
| [010](010-two-cloudfront-distributions.md) | Two CloudFront Distributions Per Environment | ✅ Accepted | 2024-12 |

## ADR Statuses

- ✅ **Accepted**: Currently active decision
- ⏸️ **Deprecated**: No longer recommended, but not replaced
- ❌ **Superseded**: Replaced by a newer decision (link to replacement)
- 🔄 **Proposed**: Under discussion, not yet accepted

## ADR Template

See below for the standard ADR template. Copy this when creating new ADRs.

---

```markdown
# ADR-XXX: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-YYY]
**Date:** YYYY-MM-DD
**Deciders:** [Team/Person]
**Replaces:** [ADR-YYY, if applicable]

## Context

What is the issue we're facing? What constraints exist? What is the current situation?

Include:
- Problem statement
- Relevant constraints (cost, performance, team knowledge)
- Current pain points or limitations

## Decision

What decision did we make? Be specific and concrete.

Include:
- Chosen approach/technology/pattern
- Key implementation details
- Scope of the decision (what it covers, what it doesn't)

## Consequences

What are the impacts of this decision?

**Positive:**
- Benefit 1
- Benefit 2

**Negative:**
- Drawback 1
- Mitigation strategy for drawback

**Neutral:**
- Trade-offs that are neither clearly positive nor negative

**Migration Required:**
- What needs to change to implement this?
- Database migrations?
- Code changes?
- Infrastructure updates?

## Alternatives Considered

What other options did we evaluate?

For each alternative:
- Brief description
- Why it was rejected
- Key differences from chosen approach

## References

- Links to related docs, research, discussions
- Migration guides
- Implementation details
```

## Usage Examples

**Creating a new ADR:**
```bash
# Copy template
cp docs/adr/README.md docs/adr/011-your-decision-title.md

# Edit the file with your decision
# Add to index table above
# Commit with message: "docs: Add ADR-011: Your Decision Title"
```

**Superseding an ADR:**
```markdown
# In the old ADR file
**Status:** ❌ Superseded by [ADR-011](011-new-approach.md)

# In the new ADR file
**Replaces:** [ADR-003](003-old-approach.md)
```

## Best Practices

1. **Write ADRs when the decision is made**, not after the fact
2. **Be honest about trade-offs** - document both benefits and drawbacks
3. **Link to implementation details** in other docs (don't duplicate)
4. **Update status when superseded** - don't delete old ADRs
5. **Use clear, specific language** - avoid vague terms like "better" or "simpler"
6. **Document the context** - future readers need to understand *why* this mattered

## Questions?

See [CLAUDE.md](../../.claude/CLAUDE.md) for the principle: "Document significant architectural decisions in ADRs."
