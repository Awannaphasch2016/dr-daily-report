# Exploration: Documentation Organization Patterns

**Date**: 2025-12-25
**Focus**: Maintainability
**Status**: Complete

---

## Problem Decomposition

**Goal**: Best practices to organize docs/, Claude skills, and CLAUDE.md for modularity, maintainability, and continuous improvement

### Core Requirements

**MUST have**:
- **Modularity**: Rules/constraints can be split into independent, cohesive units
- **Discoverability**: Easy to find relevant documentation quickly
- **Maintainability**: Changes to one area don't require updates across multiple files
- **Single Source of Truth**: No duplicate information that can drift out of sync
- **Scalability**: Structure works as documentation grows from 100 to 1000+ files

**SHOULD have**:
- Clear ownership and update responsibility
- Version history for tracking changes
- Easy to onboard new team members
- Support both AI (Claude) and human readers

### Current State Analysis

**What we have**:
- 622 lines in CLAUDE.md (monolithic, growing)
- 94 markdown files in docs/ (various topics)
- 37 markdown files across 12 skills in .claude/skills/
- 19 commands in .claude/commands/
- No clear navigation hierarchy

**Pain points**:
- CLAUDE.md is becoming too large (hard to scan, edit)
- Unclear where new content belongs (CLAUDE.md vs docs/ vs skills/)
- Risk of duplication (same principle in multiple places)
- Hard to find specific guidelines quickly
- Changes require updating multiple locations

### Constraints

**Technical**:
- Must work with Claude Code's file reading mechanism
- Skills/commands use YAML frontmatter (specific format)
- CLAUDE.md is read on every conversation start (size matters)
- Documentation should be markdown (human + AI readable)

**Team**:
- Solo developer currently, but should support future contributors
- Need balance between structure and flexibility
- Can't spend weeks reorganizing (incremental improvement)

**Performance**:
- Claude Code reads files on demand (no preloading penalty)
- Large CLAUDE.md increases initial context size
- File count doesn't significantly impact performance

### Success Criteria

**Modularity**: ✅ Can extract a principle into separate file without breaking references
**Maintainability**: ✅ Changing a rule requires editing 1 file, not 3-5
**Discoverability**: ✅ Can find relevant doc in < 30 seconds
**Clarity**: ✅ New contributor understands where to add new content
**Scalability**: ✅ Structure works at 500+ documentation files

### Stakeholders

**Claude (AI assistant)**:
- Needs: Quick access to relevant context, clear structure for search
- Cares about: File organization, cross-references, context size

**Developer (human)**:
- Needs: Quick reference during development, clear guidelines
- Cares about: Discoverability, readability, practical examples

**Future contributors**:
- Needs: Clear contribution guidelines, understand existing structure
- Cares about: Documentation of documentation, consistent patterns

---

## Solution Space (Divergent Phase)

### Option 1: Topic-Based Hierarchy (Traditional Docs)

**Description**: Organize by technical domain (Testing, Deployment, Architecture)

**Structure**:
```
docs/
├── architecture/
│   ├── semantic-layer.md
│   ├── serverless-patterns.md
│   └── data-flow.md
├── testing/
│   ├── unit-testing.md
│   ├── integration-testing.md
│   └── anti-patterns.md
├── deployment/
│   ├── lambda-versioning.md
│   ├── multi-env.md
│   └── monitoring.md
├── development/
│   ├── code-style.md
│   ├── git-workflow.md
│   └── local-setup.md
└── README.md (index with links)

.claude/
├── CLAUDE.md (10-20 lines, points to docs/)
└── skills/ (unchanged)
```

**How it works**:
- Group by technical domain
- CLAUDE.md becomes a thin index/router
- Each domain has comprehensive documentation
- Skills reference docs/ for detailed content

**Pros**:
- ✅ Familiar structure (industry standard)
- ✅ Easy to navigate for humans
- ✅ Clear boundaries between topics
- ✅ Scales well (add new domains as needed)
- ✅ Reduces CLAUDE.md to ~50 lines

**Cons**:
- ❌ Cross-cutting concerns split across files (e.g., "type safety" touches testing, architecture, development)
- ❌ No clear hierarchy for principles vs guides vs references
- ❌ Duplication risk (same pattern in testing/ and deployment/)
- ❌ Claude may need to read multiple files for related context

**Examples**:
- **Django**: docs/ organized by topic (models/, views/, testing/)
- **Kubernetes**: Docs organized by concept, task, reference
- **AWS**: Service-based organization

**Resources**:
- [Documentation System (Divio)](https://documentation.divio.com/)
- [Good Docs Project](https://thegooddocsproject.dev/)

**When to choose**:
- Team is familiar with traditional doc structures
- Clear domain boundaries (testing != deployment)
- Human readers are primary audience

---

### Option 2: CLAUDE.md as Index + Modular Includes

**Description**: Keep CLAUDE.md small by using "includes" pattern

**Structure**:
```
.claude/
├── CLAUDE.md (100 lines, high-level + includes)
├── principles/
│   ├── testing.md
│   ├── deployment.md
│   ├── type-safety.md
│   ├── error-handling.md
│   └── defensive-programming.md
├── patterns/
│   ├── state-management.md
│   ├── retry-fallback.md
│   └── validation-gates.md
├── guides/
│   ├── adding-features.md
│   ├── code-review-checklist.md
│   └── debugging-workflow.md
└── skills/ (unchanged)

# CLAUDE.md content:
---
# Core Principles
See detailed principles in `.claude/principles/*.md`
- [Testing](.claude/principles/testing.md)
- [Deployment](.claude/principles/deployment.md)
...
---
```

**How it works**:
- CLAUDE.md is the "table of contents"
- Each principle/pattern/guide is a separate file
- Claude reads CLAUDE.md first, then follows links as needed
- Skills reference specific principle files

**Pros**:
- ✅ CLAUDE.md stays small (easier to maintain)
- ✅ Single responsibility per file
- ✅ Easy to add new principles (create file + add link)
- ✅ Claude only reads what's needed (context efficiency)
- ✅ Clear separation: principles vs patterns vs guides

**Cons**:
- ❌ Requires Claude to follow links (may not always happen)
- ❌ More files to manage (40+ small files vs 1 large file)
- ❌ Risk of orphaned files (created but not linked)
- ❌ Cross-references between principle files needed

**Examples**:
- **Nx**: Modular architecture, each concept is a file
- **Storybook**: Component-based docs with index
- **Vue.js**: Guide pages with sidebar navigation

**Resources**:
- [Modular Documentation (Write the Docs)](https://www.writethedocs.org/guide/writing/referenceable-text/)
- [Documentation as Code](https://www.docslikecode.com/)

**When to choose**:
- CLAUDE.md is growing too large (>500 lines)
- Need fine-grained control over context
- Team comfortable with multi-file navigation

---

### Option 3: ADR-Inspired Decision Log

**Description**: Organize as append-only decision records (like ADRs)

**Structure**:
```
.claude/
├── CLAUDE.md (50 lines, current active principles)
├── decisions/
│   ├── 001-testing-pyramid.md
│   ├── 002-serverless-cold-start-optimization.md
│   ├── 003-defensive-programming-validation-gates.md
│   ├── 004-type-safety-at-boundaries.md
│   ├── 005-error-propagation-state-based.md
│   └── INDEX.md (chronological list)
└── skills/ (unchanged)

docs/
├── adr/ (architectural decisions)
└── practices/ (current best practices, references decisions/)
```

**How it works**:
- Each principle/pattern is a "decision" with rationale
- Numbered chronologically (001, 002, 003...)
- CLAUDE.md references active decisions
- Deprecated decisions stay but marked as superseded
- Immutable after creation (append-only)

**Pros**:
- ✅ Clear history of why principles exist
- ✅ Easy to track evolution over time
- ✅ Immutability prevents accidental edits
- ✅ Natural fit for ADRs already in docs/adr/
- ✅ Searchable by number or topic

**Cons**:
- ❌ Finding "current state" requires reading multiple decisions
- ❌ Numbers don't convey content (need index)
- ❌ Duplication between decisions/ and adr/
- ❌ Append-only feels heavy for small changes

**Examples**:
- **GitHub ADRs**: Lightweight decision records
- **Michael Nygard's ADR template**: Standard format
- **ThoughtWorks Technology Radar**: Versioned decisions

**Resources**:
- [ADR Tools](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

**When to choose**:
- Need strong auditability (why did we decide this?)
- Team values immutability and history
- Comfortable with append-only workflow

---

### Option 4: Skills-First Organization

**Description**: Move all guidelines into Claude skills (auto-discovered)

**Structure**:
```
.claude/
├── CLAUDE.md (20 lines, "See skills for detailed guidance")
├── skills/
│   ├── testing-patterns/
│   │   ├── SKILL.md (auto-discovered by Claude)
│   │   ├── unit-testing.md
│   │   ├── integration-testing.md
│   │   └── anti-patterns.md
│   ├── deployment-patterns/
│   │   ├── SKILL.md
│   │   ├── zero-downtime.md
│   │   └── monitoring.md
│   ├── code-quality/
│   │   ├── SKILL.md
│   │   ├── defensive-programming.md
│   │   └── type-safety.md
│   └── debugging/
│       ├── SKILL.md
│       └── systematic-investigation.md
└── commands/ (unchanged)

docs/ (reference only, not enforced)
```

**How it works**:
- Skills are auto-discovered by Claude
- Each skill has guidelines + tools
- CLAUDE.md minimal (just points to skills)
- Skills reference each other when needed
- Documentation lives where it's used (skills)

**Pros**:
- ✅ Auto-discovery (Claude finds relevant skills)
- ✅ Guidelines live with execution context
- ✅ Enforced by Claude's skill system
- ✅ Natural modularity (one skill = one concern)
- ✅ Reduces CLAUDE.md to absolute minimum

**Cons**:
- ❌ Skills designed for tooling, not pure documentation
- ❌ Less discoverable for humans (need to browse .claude/skills/)
- ❌ Mixing guidelines with executable logic
- ❌ Over-reliance on Claude Code's skill system

**Examples**:
- **Claude Code itself**: Skill-based organization
- **VSCode extensions**: Activation events + commands
- **Make**: Targets with embedded documentation

**Resources**:
- [Claude Code Skill Documentation](https://github.com/anthropics/claude-code)
- [Self-Documenting Code](https://martinfowler.com/bliki/SelfDocumentingCode.html)

**When to choose**:
- Heavy Claude Code users (skills are primary interface)
- Want auto-discovery without explicit references
- Prefer action-oriented documentation

---

### Option 5: Hybrid Layered Approach (Recommended)

**Description**: Layer documentation by audience and update frequency

**Structure**:
```
.claude/
├── CLAUDE.md (150 lines, stable principles + pointers)
│   ├── Core Principles (10-20 lines each)
│   ├── Quick Reference (links to detailed docs)
│   └── Extension Points (where to add new content)
│
├── principles/          # Stable, rarely change
│   ├── README.md (index)
│   ├── defensive-programming.md
│   ├── type-safety.md
│   └── necessary-condition.md
│
├── patterns/            # Semi-stable, evolve slowly
│   ├── README.md
│   ├── state-management.md
│   ├── retry-fallback.md
│   └── validation-gates.md
│
├── guides/              # Tactical, update frequently
│   ├── README.md
│   ├── adding-features.md
│   ├── code-review.md
│   └── debugging.md
│
├── skills/              # Auto-discovered, tool-focused
│   ├── testing-workflow/
│   ├── deployment/
│   └── error-investigation/
│
└── commands/            # User-invocable workflows
    ├── explore.md
    ├── validate.md
    └── journal.md

docs/                    # Reference documentation
├── README.md (complete navigation)
├── architecture/
├── deployment/
└── adr/
```

**CLAUDE.md Content Strategy**:
```markdown
# Core Principles (The Contract)
- Testing Guidelines (link to .claude/principles/testing.md)
- Deployment Philosophy (link to .claude/principles/deployment.md)
- Code Organization (link to .claude/principles/code-org.md)

# Common Patterns (The Cookbook)
See .claude/patterns/*.md for reusable solutions

# When Adding New Features
See .claude/guides/adding-features.md

# Skills & Commands
- Skills: Auto-discovered from .claude/skills/
- Commands: See .claude/commands/README.md
```

**How it works**:
1. **CLAUDE.md**: Stable contract (principles + navigation)
2. **Principles**: Rarely change (foundational truths)
3. **Patterns**: Evolve slowly (best practices)
4. **Guides**: Update frequently (tactical how-tos)
5. **Skills**: Auto-discovered (execution context)
6. **docs/**: Reference (deep dives, runbooks)

**Layering by Change Frequency**:
```
CLAUDE.md (monthly updates)
    ↓ references
Principles (quarterly updates)
    ↓ references
Patterns (monthly updates)
    ↓ references
Guides (weekly updates)
    ↓ implemented by
Skills (as needed)
```

**Pros**:
- ✅ Best of all worlds (structure + flexibility)
- ✅ Clear update strategy (where to edit based on change type)
- ✅ CLAUDE.md stays focused (principles + navigation)
- ✅ Scales well (add guides without touching principles)
- ✅ Discoverable (README in each directory)
- ✅ Separation of concerns (stable vs volatile content)

**Cons**:
- ❌ More directories to navigate
- ❌ Requires discipline to maintain boundaries
- ❌ Initial setup effort (reorganize existing content)

**Examples**:
- **Stripe API Docs**: Guides (get started) → API Reference (details) → Resources (examples)
- **MDN Web Docs**: Learn (guides) → References (API) → Tools
- **React**: Learn → API Reference → Community

**Resources**:
- [Stripe Docs Philosophy](https://stripe.com/blog/api-versioning)
- [Four Types of Documentation (Divio)](https://documentation.divio.com/)

**When to choose**:
- Need balance between structure and flexibility
- Documentation has varying update frequencies
- Want clear guidelines for where new content belongs

---

## Evaluation Matrix

**Focus**: Maintainability (weighted 2x)

| Criterion | Topic Hierarchy | CLAUDE.md Index | ADR Decisions | Skills-First | Hybrid Layers |
|-----------|-----------------|-----------------|---------------|--------------|---------------|
| **Modularity** | 7/10 | 9/10 | 8/10 | 8/10 | 9/10 |
| **Discoverability** | 8/10 | 7/10 | 6/10 | 5/10 | 9/10 |
| **Maintainability (2x)** | 6/10 (12) | 8/10 (16) | 7/10 (14) | 6/10 (12) | 9/10 (18) |
| **Scalability** | 8/10 | 7/10 | 9/10 | 7/10 | 9/10 |
| **Migration Effort** | 6/10 | 7/10 | 5/10 | 4/10 | 6/10 |
| **Total** | **41** | **46** | **42** | **36** | **51** |

### Scoring Rationale

**Topic Hierarchy (41/50)**:
- Modularity 7/10: Good separation, but cross-cutting concerns split
- Discoverability 8/10: Familiar structure, easy for humans
- Maintainability 6/10 (12): Changes ripple across topic boundaries
- Scalability 8/10: Proven pattern, works at large scale
- Migration 6/10: Medium effort (reorganize by topic)

**CLAUDE.md Index (46/50)**:
- Modularity 9/10: Each file has single responsibility
- Discoverability 7/10: Requires following links
- Maintainability 8/10 (16): Change one file, no ripple effects
- Scalability 7/10: Works well, but many small files
- Migration 7/10: Low effort (extract from CLAUDE.md, add links)

**ADR Decisions (42/50)**:
- Modularity 8/10: Clear boundaries, immutable
- Discoverability 6/10: Need to read multiple decisions for current state
- Maintainability 7/10 (14): Append-only prevents edits, but clear history
- Scalability 9/10: Unlimited growth, chronological
- Migration 5/10: High effort (rewrite as decisions)

**Skills-First (36/50)**:
- Modularity 8/10: Natural modularity via skills
- Discoverability 5/10: Auto-discovery for Claude, but hard for humans
- Maintainability 6/10 (12): Mixing docs with tooling
- Scalability 7/10: Works, but skills aren't primarily for docs
- Migration 4/10: High effort (convert docs to skills)

**Hybrid Layers (51/50)** ⭐:
- Modularity 9/10: Layered by concern and change frequency
- Discoverability 9/10: Clear navigation hierarchy + README files
- Maintainability 9/10 (18): Edit at appropriate layer, no ripples
- Scalability 9/10: Proven architecture pattern (stable vs volatile)
- Migration 6/10: Medium effort (categorize existing content)

---

## Ranked Recommendations

### 1. Hybrid Layered Approach (Score: 51/50) ⭐

**Why this is optimal**:

1. **Change Frequency Layering**: Stable principles separated from volatile guides
   - Principles change quarterly → `.claude/principles/`
   - Patterns change monthly → `.claude/patterns/`
   - Guides change weekly → `.claude/guides/`
   - CLAUDE.md stays focused on core contract

2. **Clear Update Strategy**: Know exactly where to edit based on change type
   - Adding new principle → Create `.claude/principles/{name}.md`
   - Adding pattern → Create `.claude/patterns/{name}.md`
   - Updating workflow → Edit `.claude/guides/{name}.md`
   - No ambiguity about placement

3. **Separation of Concerns**:
   - CLAUDE.md = Contract (what must be true always)
   - Principles = Foundational truths (defensive programming, type safety)
   - Patterns = Reusable solutions (retry-fallback, validation gates)
   - Guides = Tactical how-tos (adding features, debugging)
   - Skills = Execution context (auto-discovered tools)

4. **Maintains Existing Strengths**:
   - Skills remain auto-discovered (no change)
   - Commands remain user-invocable (no change)
   - docs/ remains reference documentation (no change)
   - Just adds structure to `.claude/` directory

**Trade-offs**:
- **Gain**: Clear boundaries, reduced CLAUDE.md size, easy maintenance
- **Lose**: Slightly more directories (5 vs 2), requires initial categorization effort

**Migration Path** (incremental, low risk):

```bash
# Phase 1: Extract stable principles (week 1)
mkdir .claude/principles
# Move: Defensive Programming, Type Safety, Necessary Condition
# Update CLAUDE.md to reference principles/

# Phase 2: Extract patterns (week 2)
mkdir .claude/patterns
# Move: State Management, Retry-Fallback, Validation Gates
# Update CLAUDE.md to reference patterns/

# Phase 3: Extract guides (week 3)
mkdir .claude/guides
# Move: Adding Features, Code Review, Debugging
# Update CLAUDE.md to reference guides/

# Phase 4: Add navigation (week 4)
# Create README.md in each directory
# Update CLAUDE.md with clear structure
```

**Next step**:
```bash
/specify "Hybrid Layered Documentation Architecture"
```

---

### 2. CLAUDE.md Index + Modular Includes (Score: 46/50)

**When to choose instead**:
- CLAUDE.md is currently >500 lines (urgent need to split)
- Team prefers flat structure over layered hierarchy
- Don't want to categorize content into layers

**Why it's second**:
- Simple extraction (move content → add links)
- Low cognitive load (all files at same level)
- BUT: Loses change frequency separation

---

### 3. ADR-Inspired Decision Log (Score: 42/50)

**When to choose instead**:
- Strong need for auditability ("why did we choose this?")
- Team values immutability and historical context
- Already using ADRs heavily in docs/adr/

**Why it's third**:
- Excellent for tracking evolution
- BUT: Hard to see "current state" (need to read multiple decisions)
- Better suited for architectural decisions than tactical guidelines

---

### 4. Topic-Based Hierarchy (Score: 41/50)

**When to choose instead**:
- Team is more familiar with traditional docs/ structure
- Human readers are primary audience (not Claude)
- Want to mirror standard open source project layout

**Why it's fourth**:
- Industry standard, proven
- BUT: Cross-cutting concerns split across topics
- Better for reference docs than enforced principles

---

### 5. Skills-First Organization (Score: 36/50)

**When to choose instead**:
- Only using Claude Code (no human readers)
- Want auto-discovery to be primary mechanism
- Comfortable mixing docs with executable logic

**Why it's last**:
- Skills are designed for tooling, not documentation
- Hard for humans to browse
- Over-relies on Claude Code's implementation

---

## Resources Gathered

### Official Documentation Systems

- [Divio Documentation System](https://documentation.divio.com/)
  - Four types: Tutorials, How-Tos, Reference, Explanation
  - Separates learning from reference

- [Stripe API Docs](https://stripe.com/docs)
  - Guides → API Reference → Resources
  - Layered by use case

- [MDN Web Docs](https://developer.mozilla.org/en-US/)
  - Learn → References → Tools
  - Clear navigation hierarchy

### Documentation Best Practices

- [Write the Docs Guide](https://www.writethedocs.org/guide/)
  - Documentation as Code
  - Modular documentation principles

- [Good Docs Project](https://thegooddocsproject.dev/)
  - Templates for different doc types
  - Style guides

- [Docs Like Code](https://www.docslikecode.com/)
  - Treating docs like software
  - Version control, CI/CD for docs

### Architecture Decision Records

- [ADR Tools](https://adr.github.io/)
  - Lightweight decision records
  - Standard format

- [Michael Nygard's ADR](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  - Original proposal
  - Template format

### Industry Examples

- [Django Documentation](https://docs.djangoproject.com/)
  - Topic-based hierarchy
  - Works at large scale

- [React Documentation](https://react.dev/)
  - Learn → Reference → Community
  - Layered approach

- [Kubernetes Docs](https://kubernetes.io/docs/)
  - Concepts → Tasks → Reference
  - Multiple entry points

---

## Implementation Plan

### Recommended: Hybrid Layered Approach

**Week 1: Extract Principles**
```bash
mkdir -p .claude/principles

# Move stable, foundational content
# From CLAUDE.md → .claude/principles/
- defensive-programming.md
- type-safety.md
- necessary-condition.md
- testing-philosophy.md
- deployment-philosophy.md

# Update CLAUDE.md
Add section: "Core Principles"
Link to each principle file
```

**Week 2: Extract Patterns**
```bash
mkdir -p .claude/patterns

# Move reusable solutions
- state-management.md
- retry-fallback.md
- validation-gates.md
- error-propagation.md
- workflow-state.md

# Update CLAUDE.md
Add section: "Common Patterns"
Link to patterns/ directory
```

**Week 3: Extract Guides**
```bash
mkdir -p .claude/guides

# Move tactical how-tos
- adding-features.md
- code-review-checklist.md
- debugging-workflow.md
- git-workflow.md

# Update CLAUDE.md
Add section: "Developer Guides"
Link to guides/ directory
```

**Week 4: Add Navigation**
```bash
# Create README.md in each directory
.claude/principles/README.md  # Index of principles
.claude/patterns/README.md    # Index of patterns
.claude/guides/README.md      # Index of guides

# Update CLAUDE.md final structure
- Core Principles (links)
- Common Patterns (links)
- Developer Guides (links)
- Skills & Commands (existing)
- Extension Points (where to add new content)
```

**Week 5: Validation**
```bash
# Test the new structure
- Can find relevant doc in < 30 seconds? ✅
- Adding new principle: Where does it go? ✅
- Updating workflow: One file edit? ✅
- CLAUDE.md size reduced? ✅

# Adjust based on feedback
```

---

## Next Steps

```bash
# Recommended: Converge on detailed design
/specify "Hybrid Layered Documentation Architecture"

# Alternative: Validate current pain points
/validate "CLAUDE.md is too large to maintain effectively"

# Alternative: Compare top 2 choices
/what-if "use Hybrid Layers vs CLAUDE.md Index approach"
```

---

## Appendix: Current State Mapping

**Where existing content would go**:

| Current Location | New Location (Hybrid) | Reason |
|------------------|----------------------|---------|
| CLAUDE.md "Testing Guidelines" | `.claude/principles/testing.md` | Stable, foundational |
| CLAUDE.md "Defensive Programming" | `.claude/principles/defensive.md` | Core principle |
| CLAUDE.md "Workflow State Management" | `.claude/patterns/state-management.md` | Reusable pattern |
| CLAUDE.md "When Adding New Features" | `.claude/guides/adding-features.md` | Tactical guide |
| `.claude/skills/testing-workflow/` | No change | Already modular |
| `docs/deployment/MULTI_ENV.md` | No change | Reference documentation |
| `docs/adr/001-semantic-layer.md` | No change | Architectural decision |

**CLAUDE.md NEW structure** (150 lines total):
```markdown
# Daily Report LINE Bot - Development Guide (50 lines)
## Core Principles (30 lines + links to .claude/principles/)
## Common Patterns (20 lines + links to .claude/patterns/)
## Developer Guides (20 lines + links to .claude/guides/)
## Skills & Commands (20 lines, existing)
## Extension Points (10 lines, where to add new content)
```

**Size reduction**: 622 lines → 150 lines (76% reduction)

---

## Conclusion

The **Hybrid Layered Approach** provides the best balance of:
- Modularity (9/10)
- Discoverability (9/10)
- Maintainability (9/10 weighted 2x)
- Scalability (9/10)

**Key innovation**: Layer by change frequency (stable → volatile)

**Next action**: Create specification for implementation
