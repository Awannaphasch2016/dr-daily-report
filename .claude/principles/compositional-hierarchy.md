# Principle #28: Compositional Hierarchy

**Tier**: 0 (Core - applies to EVERY task)

> "Everything is layered. Make the layers explicit."

---

## Core Concept

**Compositional Hierarchy** is a meta-architectural principle that replaces undifferentiated "references" with structured relationships. Instead of saying "A references B," we specify *how* A relates to B using a defined taxonomy.

**Why this matters**:
- **Clarity**: "A composes B" is more precise than "A references B"
- **Reusability**: Tier-1 modules can be composed into multiple Tier-2 solutions
- **Maintainability**: Changes to Tier-1 automatically benefit all Tier-2 dependents
- **Cognitive load**: Hierarchical structure is easier to navigate than flat references

---

## Relationship Taxonomy

Four relationship types replace the generic "reference":

| Relationship | Direction | Meaning | Example |
|--------------|-----------|---------|---------|
| **composes** | Higher → Lower | Builds on, combines | Tier-2 skill → Tier-1 skills |
| **depends** | Same/Cross tier | Requires, doesn't build | Skill → external library |
| **invokes** | Cross-domain | Calls as capability | Command → skill |
| **grounds** | Meta → Instance | Provides foundation | Principle → implementation |

### When to Use Each

**`composes`** - When building something new from existing parts:
```yaml
# report-prompt-workflow SKILL.md frontmatter
tier: 2
depends:
  - prompt-engineering      # composes this Tier-1 skill
  - context-engineering     # composes this Tier-1 skill
  - prompt-management       # composes this Tier-1 skill
```

**`depends`** - When requiring something without building on it:
```yaml
# A skill that uses an external tool
depends:
  - radon  # external complexity analyzer (not a skill)
```

**`invokes`** - When calling across domain boundaries:
```markdown
<!-- Command invoking a skill -->
composition:
  - skill: research         # invokes research skill
  - skill: code-review      # invokes code-review skill
```

**`grounds`** - When a meta-level entity provides foundation:
```markdown
<!-- Principle grounding implementation -->
Principle #1 (Defensive Programming) grounds:
- code-review skill DEFENSIVE.md
- testing-workflow skill DEFENSIVE.md
```

---

## Universal Tier Structure

The tier pattern applies across all domains:

```
Tier-0: Core/Atomic (always present, self-contained)
Tier-1: Modular (reusable, independent)
Tier-2: Composed (builds on Tier-1)
Tier-N: Higher composition (builds on lower tiers)
```

### Applied Across Domains

| Domain | Tier-0 | Tier-1 | Tier-2+ |
|--------|--------|--------|---------|
| **Principles** | Core (#1,2,18,20,23,25-28) | Domain clusters | Task-specific |
| **Skills** | — | Modular (prompt-eng, testing) | Composed (report-workflow) |
| **Commands** | Atomic (/explore, /validate) | — | Orchestrated (/optimize, /analysis) |
| **Invariants** | Level 4 (config) | Levels 3-2 (infra, data) | Levels 1-0 (service, user) |
| **Tests** | Tier-0 (unit) | Tier-1-2 (integration) | Tier-3-4 (e2e) |

---

## Principles Domain

**Tier-0 (Core)**: Always apply, documented in CLAUDE.md
- #1 Defensive Programming
- #2 Progressive Evidence
- #18 Logging Discipline
- #20 Execution Boundary
- #23 Configuration Variation
- #25 Behavioral Invariant
- #26 Thinking Tuple Protocol
- #27 Commands as Strategy Modes
- #28 Compositional Hierarchy (this principle)

**Tier-1 (Domain clusters)**: Apply when doing specific task types
- deployment-principles.md
- testing-principles.md
- data-principles.md
- configuration-principles.md
- integration-principles.md
- meta-principles.md

**Tier-2+ (Task-specific)**: Combinations loaded for complex tasks
- Deployment + Configuration (for secrets-heavy deploys)
- Data + Deployment (for migrations)

---

## Skills Domain

**Tier-1 (Modular)**: Independent, reusable expertise
- `prompt-engineering/` - LLM prompt design patterns
- `context-engineering/` - Semantic layers, token optimization
- `prompt-management/` - Langfuse versioning, A/B testing
- `testing-workflow/` - Test patterns and anti-patterns
- `code-review/` - Security, performance, defensive checks
- `error-investigation/` - Multi-layer AWS debugging
- `deployment/` - Zero-downtime deployment patterns
- `database-migration/` - Schema migration patterns
- `refacter/` - Complexity analysis, refactoring patterns
- `data-visualization/` - Chart correctness, visual hierarchy
- `performance-investigation/` - Bottleneck identification
- `research/` - Investigation methodology
- `telegram-uiux/` - Telegram Mini App patterns
- `line-uiux/` (legacy) - LINE Bot maintenance

**Tier-2 (Composed)**: Domain-specific workflows composing Tier-1
- `report-prompt-workflow/` → composes prompt-engineering + context-engineering + prompt-management

### Skill Composition Pattern

```yaml
# Tier-2 skill frontmatter
---
name: report-prompt-workflow
description: Composed workflow for DR report prompt engineering
tier: 2
depends:
  - prompt-engineering      # Tier-1
  - context-engineering     # Tier-1
  - prompt-management       # Tier-1
---
```

---

## Commands Domain

**Tier-0 (Atomic)**: Single-purpose, standalone commands
- `/explore` - Divergent option generation
- `/validate` - Verify claims with evidence
- `/observe` - Capture execution traces
- `/decompose` - Break down goals/failures
- `/journal` - Document interpreted knowledge

**Tier-2 (Orchestrated)**: Compose other commands/skills
- `/optimize` → composes `/perf` + `/design` + `/invariant` + `/reconcile`
- `/analysis` → composes `/explore` + `/what-if` + `/validate` + `/consolidate`

### Command Composition Pattern

```yaml
# Tier-2 command frontmatter
---
name: optimize
description: Performance optimization with invariant preservation
tier: 2
depends:
  - /perf
  - /design
  - /invariant
  - /reconcile
composition:
  - command: perf
  - command: design
  - command: invariant
  - skill: performance-investigation
---
```

---

## Invariants Domain

Invariant levels form a dependency hierarchy (higher depends on lower):

**Level 4 (Config)**: Foundation for everything
- Environment variables set
- Constants defined
- Doppler secrets available

**Level 3 (Infrastructure)**: Foundation for service
- Lambda → Aurora connectivity
- Lambda → S3 connectivity
- VPC security groups correct

**Level 2 (Data)**: Foundation for service behavior
- Schema valid
- Data populated
- Relationships intact

**Level 1 (Service)**: Foundation for user experience
- Lambda returns 200
- API contract honored
- Error rate within threshold

**Level 0 (User)**: Ultimate success criteria
- User can complete flow
- Response time acceptable
- Output correct

### Verification Order

Always verify bottom-up (4 → 3 → 2 → 1 → 0):
```
❌ Wrong: Fix L1 → Discover L2 broken → Fix L2 → Discover L3 broken...
✅ Right: Scan L4→L3→L2→L1→L0 → Build dependency graph → Fix in order
```

---

## Tests Domain

**Tier-0 (Unit)**: Test individual functions in isolation
- Pure function tests
- Mock all dependencies
- Fast, run on every save

**Tier-1 (Integration)**: Test component interactions
- Service layer tests
- Database integration
- External API mocks

**Tier-2 (Contract)**: Test API contracts
- Request/response validation
- Schema compatibility
- Versioning checks

**Tier-3 (System)**: Test system behavior
- Multi-service flows
- Lambda cold/warm starts
- Real AWS resources

**Tier-4 (E2E)**: Test user journeys
- Full user flows
- Browser automation
- Production-like environment

---

## Making Relationships Explicit

### In YAML Frontmatter

Skills and commands declare relationships in frontmatter:

```yaml
---
name: my-skill
tier: 2
depends:
  - skill-a       # composes
  - skill-b       # composes
  - external-lib  # depends (not a skill)
composition:
  - skill: skill-a
  - command: some-command
  - script: path/to/script.py
---
```

### In Documentation

Use explicit relationship language:

```markdown
❌ Vague: "This skill references the code-review skill"
✅ Explicit: "This skill composes the code-review skill's DEFENSIVE.md patterns"

❌ Vague: "See deployment principles"
✅ Explicit: "This command invokes the deployment skill for validation"

❌ Vague: "Based on Principle #1"
✅ Explicit: "Principle #1 (Defensive Programming) grounds this pattern"
```

---

## Benefits

### 1. Clearer Communication

Before: "A references B"
After: "A composes B" / "A depends on B" / "A invokes B" / "A is grounded by B"

### 2. Explicit Dependencies

```
report-prompt-workflow (Tier-2)
├── composes: prompt-engineering (Tier-1)
├── composes: context-engineering (Tier-1)
└── composes: prompt-management (Tier-1)
```

### 3. Reuse Without Duplication

Tier-1 skills contain knowledge once, Tier-2 skills compose without duplicating.

### 4. Maintenance Efficiency

Update Tier-1 skill → All Tier-2 dependents automatically benefit.

### 5. Cognitive Navigation

Know where to look: Tier-0 for fundamentals, Tier-1 for modules, Tier-2 for workflows.

---

## Anti-Patterns

### 1. Flat References

```markdown
❌ Bad: "See also: skill-a, skill-b, skill-c"
✅ Good: "Composes: skill-a, skill-b. Invokes: skill-c."
```

### 2. Implicit Tiers

```yaml
# ❌ Bad: Tier not specified
---
name: my-skill
---

# ✅ Good: Tier explicit
---
name: my-skill
tier: 2
depends:
  - base-skill-1
  - base-skill-2
---
```

### 3. Cross-Tier Composition

```markdown
❌ Bad: Tier-1 skill depending on Tier-2 skill (inverts hierarchy)
✅ Good: Tier-2 composes Tier-1 (proper direction)
```

### 4. Undifferentiated Dependencies

```yaml
# ❌ Bad: All dependencies look the same
depends:
  - skill-a
  - external-lib
  - command-x

# ✅ Good: Differentiated (when tooling supports)
composes:
  - skill-a
depends:
  - external-lib
invokes:
  - command-x
```

---

## See Also

- [CLAUDE.md](../../CLAUDE.md) - Principle #28 definition
- [Skills README](../skills/README.md) - Tiered skill architecture
- [Commands README](commands/README.md) - Command composition patterns
- [Principles Index](index.md) - Tier-0 core principles
- [Testing Principles](testing-principles.md) - Test tier system
