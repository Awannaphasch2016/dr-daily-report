# Content Boundaries: `docs/` vs `.claude/skills/`

**Date:** 2025-12-26
**Status:** Exploration
**Problem:** User has 622-line CLAUDE.md (target < 60 lines). Both `docs/` and `.claude/skills/` contain detailed guides. Need clear separation criteria to avoid duplication and confusion.

---

## Problem Decomposition

### Current State

**CLAUDE.md:** 622 lines
- Should be < 60 lines (minimal, principle-focused)
- References both docs/ and skills/ for details
- Goldilocks Zone: not too abstract, not too specific

**docs/:** 30+ markdown files
- Architecture overviews (README.md)
- Code conventions (CODE_STYLE.md)
- Database guides (DATABASE_MIGRATIONS.md)
- Deployment runbooks (deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md)
- Type system integration (TYPE_SYSTEM_INTEGRATION.md)
- Frontend patterns (frontend/UI_PRINCIPLES.md)
- ADRs (adr/)

**.claude/skills/:** 9 skills with detailed guides
- testing-workflow (SKILL.md, PATTERNS.md, ANTI-PATTERNS.md, DEFENSIVE.md)
- deployment (SKILL.md, ZERO_DOWNTIME.md, MULTI_ENV.md, MONITORING.md)
- database-migration (SKILL.md, RECONCILIATION-MIGRATIONS.md, MYSQL-GOTCHAS.md)
- error-investigation (SKILL.md, AWS-DIAGNOSTICS.md, LAMBDA-LOGGING.md)
- code-review (SKILL.md, DEFENSIVE.md, SECURITY.md, PERFORMANCE.md)
- telegram-uiux, line-uiux, refactor, research

### Risk: Duplication

**Observed overlaps:**
1. **Deployment patterns:**
   - docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md (1072 lines)
   - .claude/skills/deployment/SKILL.md (368 lines)
   - .claude/skills/deployment/MULTI_ENV.md

2. **Database migrations:**
   - docs/DATABASE_MIGRATIONS.md (1093 lines)
   - .claude/skills/database-migration/RECONCILIATION-MIGRATIONS.md (573 lines)

3. **Testing patterns:**
   - docs/CODE_STYLE.md has some testing conventions
   - .claude/skills/testing-workflow/PATTERNS.md (367 lines)
   - .claude/skills/testing-workflow/ANTI-PATTERNS.md (195 lines)

4. **Frontend principles:**
   - docs/frontend/UI_PRINCIPLES.md
   - .claude/skills/telegram-uiux/

**Current strategy (implicit):**
- docs/ has comprehensive reference documentation
- skills/ has actionable workflows and checklists
- Some content duplicated with different perspectives

---

## Solution Space Analysis

### Option 1: Audience-Based Separation

**Principle:** Human developers vs AI agents

**docs/:**
- Audience: Human developers
- Purpose: Onboarding, understanding, reference
- Format: Narrative, explanatory, context-rich
- Read: Linear (top to bottom)

**.claude/skills/:**
- Audience: Claude AI during active coding sessions
- Purpose: Active guidance, decision-making, workflows
- Format: Checklist, decision trees, quick reference
- Read: Random access (jump to relevant section)

**Example split:**

| Content | docs/ (Human) | skills/ (AI) |
|---------|---------------|--------------|
| **Deployment** | "Why we use Lambda versioning (zero-downtime philosophy)" | "Quick Decision: Deploy code change? Run this command..." |
| **Testing** | "Project uses class-based pytest for organization" | "Checklist: Writing a Unit Test (1. Create class... 2. Add setup...)" |
| **Migrations** | "Reconciliation vs Sequential migrations (trade-offs)" | "Pattern 3: Chunked Data Backfill (copy-paste SQL)" |

**Pros:**
- ✅ Clear mental model (who is reading?)
- ✅ Format naturally follows audience (docs prose, skills checklists)
- ✅ No arbitrary boundaries

**Cons:**
- ❌ AI skills still need context (can't be pure checklists)
- ❌ Humans also need quick reference (want checklists too)
- ❌ Overlaps inevitable (both need examples)

**Overlap handling:**
- Cross-reference: skills/ links to docs/ for "why"
- Thin vs thick: skills/ has minimal context + link to full docs/

**Migration effort:** Medium (reorganize existing content by audience)

---

### Option 2: Consumption-Based Separation

**Principle:** Read once vs Applied repeatedly

**docs/:**
- Frequency: Read once during onboarding, occasional reference
- Examples: Architecture decisions (ADRs), setup guides, technology choices
- Change rate: Stable (changes rarely)

**.claude/skills/:**
- Frequency: Applied repeatedly during development
- Examples: Deployment checklists, testing workflows, debugging steps
- Change rate: Evolving (improves with practice)

**Example split:**

| Content | docs/ (Read Once) | skills/ (Repeated Use) |
|---------|-------------------|------------------------|
| **Deployment** | Architecture decision to use Lambda (ADR), setup AWS credentials | Deploy checklist (run these 5 commands in order) |
| **Testing** | Why class-based pytest (project convention) | Test pattern template (copy-paste this structure) |
| **Database** | Migration philosophy (reconciliation vs sequential) | Reconciliation pattern (conditional SQL template) |

**Pros:**
- ✅ Clear criterion (how often used?)
- ✅ docs/ more stable (less churn)
- ✅ skills/ optimized for efficiency (quick access)

**Cons:**
- ❌ Subjective (what's "repeated"?)
- ❌ Some content both read-once AND repeated (e.g., testing anti-patterns)
- ❌ Doesn't handle explanatory content in skills

**Overlap handling:**
- Progressive disclosure: Overview in docs/, detailed workflow in skills/

**Migration effort:** Medium (analyze usage patterns per document)

---

### Option 3: Scope-Based Separation

**Principle:** Project-wide vs Task-specific

**docs/:**
- Scope: Project-wide knowledge
- Examples: Architecture overview, project structure, technology stack
- Question: "What is this project?"

**.claude/skills/:**
- Scope: Task/domain-specific knowledge
- Examples: How to deploy, how to debug AWS, how to write tests
- Question: "How do I do X?"

**Example split:**

| Content | docs/ (Project-Wide) | skills/ (Task-Specific) |
|---------|----------------------|-------------------------|
| **Architecture** | Multi-app architecture (LINE Bot + Telegram), shared backend | N/A (not task-specific) |
| **Deployment** | Environment strategy (dev/staging/prod), branch model | Deploy to staging (step-by-step) |
| **Code Style** | Naming conventions, docstring format | N/A (or minimal reference) |
| **Testing** | Test structure (directories), tier system | Write integration test (workflow) |

**Pros:**
- ✅ Aligns with purpose (understand project vs do work)
- ✅ docs/ answers "what is this place?"
- ✅ skills/ answers "how do I accomplish task X?"

**Cons:**
- ❌ Gray area: Is "testing anti-patterns" project knowledge or task guidance?
- ❌ Skills need project context to be useful
- ❌ Duplication: Task workflows reference project conventions

**Overlap handling:**
- skills/ assumes docs/ has been read (onboarding prerequisite)

**Migration effort:** Low (mostly aligns with current structure)

---

### Option 4: Stability-Based Separation

**Principle:** Stable reference vs Evolving practice

**docs/:**
- Stability: High (changes rarely, versioned)
- Examples: ADRs (never change), architecture diagrams, API contracts
- Locked: Once written, treated as immutable history

**.claude/skills/:**
- Stability: Low (evolves with team practice)
- Examples: Debugging checklists (add new steps), deployment workflows (improve efficiency)
- Living: Updated frequently based on experience

**Example split:**

| Content | docs/ (Stable) | skills/ (Evolving) |
|---------|----------------|-------------------|
| **ADRs** | ADR-009: Artifact Promotion (decision recorded 2024-11-30) | N/A |
| **Deployment** | Deployment philosophy (Lambda + versioning, stable choice) | Current deployment runbook (steps change as we optimize) |
| **Testing** | Test tier system (0-4, project convention) | Testing anti-patterns we've encountered (grows over time) |

**Pros:**
- ✅ Reflects reality (ADRs stable, workflows improve)
- ✅ Clear versioning strategy (docs/ tagged, skills/ HEAD)
- ✅ Preserves history (docs/ is audit trail)

**Cons:**
- ❌ Most content is semi-stable (not clearly one or the other)
- ❌ Documentation should also improve (false dichotomy)
- ❌ Doesn't guide where to put new content

**Overlap handling:**
- Extract principles to docs/, keep procedures in skills/

**Migration effort:** High (analyze stability of each document)

---

### Option 5: Format-Based Separation

**Principle:** Prose vs Procedural

**docs/:**
- Format: Narrative prose, explanations, context
- Style: "Here's how this works and why we chose it"
- Learn: Understanding-focused

**.claude/skills/:**
- Format: Checklists, decision trees, templates
- Style: "Do this, then this, check that"
- Do: Action-focused

**Example split:**

| Content | docs/ (Prose) | skills/ (Procedural) |
|---------|---------------|----------------------|
| **Deployment** | "Zero-downtime deployment uses Lambda versioning. $LATEST is mutable staging, Version N is immutable snapshot..." | "[ ] Update function code<br>[ ] Wait for function updated<br>[ ] Publish version<br>[ ] Update alias" |
| **Testing** | "We use class-based pytest because it provides better organization and fixtures scoping. Each test class..." | "```python<br>class TestComponent:<br>    def setup_method(self):<br>        ...<br>```" |

**Pros:**
- ✅ Clear format difference (easy to decide)
- ✅ Complements each other (read docs/, then follow skills/)
- ✅ Skills optimized for copy-paste efficiency

**Cons:**
- ❌ Skills still need some prose (pure checklists too terse)
- ❌ Docs also need examples (pure prose too abstract)
- ❌ Overlap inevitable (examples appear in both)

**Overlap handling:**
- docs/ uses examples to illustrate concepts
- skills/ uses examples as templates to modify

**Migration effort:** Medium (reformat content into checklist/prose)

---

### Option 6: Single Source of Truth + Thin Wrappers

**Principle:** Minimize duplication

**docs/:**
- Role: Single source of truth for ALL documentation
- Content: Complete, comprehensive guides
- Updates: When anything changes

**.claude/skills/:**
- Role: Thin workflow wrappers with links to docs/
- Content: Decision trees + "See docs/X.md for details"
- Updates: Only when workflow changes, NOT when details change

**Example:**

**docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md:**
```markdown
# Deployment Runbook (1072 lines)
- Complete prerequisites (tools, credentials)
- Phase 0: CI/CD workflow testing
- Phase 1: Local testing
- Phase 2: Dev environment deployment
- ... (all details)
```

**.claude/skills/deployment/SKILL.md:**
```markdown
# Deployment Skill (100 lines)

## Quick Decision Tree
What are you deploying?
├─ Code change? → See [Runbook Phase 2](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#phase-2-dev-environment)
├─ Infrastructure? → See [Runbook Phase 0.6](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#phase-06-infrastructure-tdd-testing)
└─ Rollback needed? → See [Runbook Section 4.4](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#44-rollback-if-needed)

## Core Principles (extracted from docs)
1. Zero-downtime via versioning
2. Artifact promotion (build once)
3. Multi-layer verification

For complete deployment guide, see [TELEGRAM_DEPLOYMENT_RUNBOOK.md](docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md)
```

**Pros:**
- ✅ No duplication (skills/ links to docs/)
- ✅ Single place to update (only docs/)
- ✅ Skills provide navigation (decision trees, quick links)

**Cons:**
- ❌ Skills become index files (less standalone value)
- ❌ Claude needs to read docs/ anyway (skills don't save time)
- ❌ Requires docs/ to be extremely well-organized

**Overlap handling:**
- No overlap (by design)
- skills/ is pure navigation layer

**Migration effort:** Low (mostly add cross-references)

---

## Evaluation Matrix

| Criterion | Option 1 (Audience) | Option 2 (Consumption) | Option 3 (Scope) | Option 4 (Stability) | Option 5 (Format) | Option 6 (Source of Truth) |
|-----------|---------------------|------------------------|------------------|----------------------|-------------------|----------------------------|
| **Clarity** (easy to decide where content goes) | ⭐⭐⭐ Good | ⭐⭐ Fair | ⭐⭐⭐⭐ Excellent | ⭐⭐ Fair | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Perfect |
| **Discoverability** (easy to find content) | ⭐⭐⭐ Good | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐ Fair | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Perfect |
| **Maintenance** (low duplication) | ⭐⭐ Fair | ⭐⭐ Fair | ⭐⭐⭐ Good | ⭐⭐⭐ Good | ⭐⭐ Fair | ⭐⭐⭐⭐⭐ Perfect |
| **Flexibility** (handles edge cases) | ⭐⭐⭐⭐ Excellent | ⭐⭐ Fair | ⭐⭐⭐ Good | ⭐⭐ Fair | ⭐⭐⭐ Good | ⭐⭐ Fair |
| **AI Compatibility** (works well with Claude skills) | ⭐⭐⭐⭐⭐ Perfect | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |

**Scoring:**
- Clarity: Can I easily decide where new content belongs?
- Discoverability: Can users/AI find what they need?
- Maintenance: How hard to keep both places in sync?
- Flexibility: Handles gray areas and exceptions?
- AI Compatibility: Supports Claude's skill invocation model?

**Winner:** Option 6 (Single Source of Truth) for maintenance, but lacks flexibility.

**Runner-up:** Option 1 (Audience) + Option 5 (Format) hybrid - natural separation with flexibility.

---

## Recommended Approach: Hybrid Model

**Combine Option 1 (Audience) + Option 5 (Format) + Option 6 (Minimal Duplication)**

### Decision Framework

```
New content to document?
│
├─ Is it a one-time decision? (ADR, architecture choice)
│  → docs/adr/ (never changes)
│
├─ Is it project structure/conventions? (file organization, naming)
│  → docs/ (reference manual)
│
├─ Is it a repeatable workflow? (deploy, test, debug)
│  ├─ Need full context? → docs/ (comprehensive guide)
│  └─ Need quick reference? → skills/ (decision tree + link to docs/)
│
├─ Is it a pattern/anti-pattern? (how to do X correctly)
│  ├─ Explanatory (why this pattern)? → docs/ (with examples)
│  └─ Actionable (checklist)? → skills/ (template + link to docs/)
│
└─ Is it environment-specific? (AWS setup, tool installation)
   → docs/ (setup guide)
```

### Content Distribution Strategy

**docs/:** Comprehensive reference ("What" + "Why" + "How")
- Architecture and design decisions (ADRs)
- Project structure and conventions
- Setup and configuration guides
- Technology stack explanations
- Complete workflows with context

**Example:** docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md
- Full deployment phases (0-5)
- Prerequisites explained (why each tool)
- Troubleshooting scenarios (comprehensive)
- Environment URLs and verification steps

**.claude/skills/:** Actionable workflows ("How" + "When" + Quick "Why")
- Decision trees (what to do when)
- Checklists (step-by-step)
- Pattern templates (copy-paste examples)
- Quick reference (command shortcuts)
- Links to docs/ for full context

**Example:** .claude/skills/deployment/SKILL.md
- Quick decision tree (deploy vs rollback vs infrastructure)
- Core principles (extracted, not duplicated)
- Common scenarios (with links to runbook)
- Pre-deployment checklist

### Cross-Reference Pattern

**Pattern 1: Overview + Deep Dive**

**.claude/skills/deployment/SKILL.md:**
```markdown
## Core Deployment Patterns

### Pattern 1: Zero-Downtime Lambda Deployment

**Quick:** $LATEST → Version N → live alias (atomic swap)

**When to use:** All production deployments

**For complete pattern with examples, see:**
[docs/deployment/ZERO_DOWNTIME.md](docs/deployment/ZERO_DOWNTIME.md)
```

**docs/deployment/ZERO_DOWNTIME.md:**
```markdown
# Zero-Downtime Deployment Pattern

## Context
Lambda function updates cause brief unavailability...

## Solution
Use Lambda versioning with aliases...

[Full detailed guide with examples, edge cases, troubleshooting]
```

**Pattern 2: Checklist + Reference**

**.claude/skills/testing-workflow/SKILL.md:**
```markdown
## Writing a Test: Checklist

1. [ ] Choose test location based on component
2. [ ] Use class-based structure: `class TestComponent:`
3. [ ] Follow canonical pattern → See [PATTERNS.md](PATTERNS.md#canonical-test-pattern)
4. [ ] Avoid anti-patterns → See [ANTI-PATTERNS.md](ANTI-PATTERNS.md)
```

**.claude/skills/testing-workflow/PATTERNS.md:**
```markdown
# Testing Patterns

## Canonical Test Pattern

[Full pattern with explanation, variations, edge cases]
```

**Pattern 3: Decision Tree + Details**

**.claude/skills/database-migration/SKILL.md:**
```markdown
## Quick Decision: Migration Strategy

- Unknown DB state? → Reconciliation migration (RECONCILIATION-MIGRATIONS.md)
- Known clean state? → Sequential migration (docs/DATABASE_MIGRATIONS.md#traditional-migrations)
- Fixing failed migration? → Reconciliation (RECONCILIATION-MIGRATIONS.md#real-world-example)
```

---

## Migration Plan

### Phase 1: Inventory Current Content

**Week 1: Categorize all docs/**
```bash
# Map each file to purpose
docs/README.md → Project overview (keep)
docs/CODE_STYLE.md → Conventions reference (keep)
docs/DATABASE_MIGRATIONS.md → Comprehensive guide (keep, extract principles to skills/)
docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md → Complete runbook (keep)
docs/frontend/UI_PRINCIPLES.md → Reference (keep)
```

**Week 1: Categorize all skills/**
```bash
# Map each skill to workflow
.claude/skills/deployment/ → Deployment workflows (keep, add cross-refs)
.claude/skills/testing-workflow/ → Test workflows (keep, link to CODE_STYLE.md)
.claude/skills/database-migration/ → Migration workflows (keep, link to docs/)
```

### Phase 2: Identify Duplicates

**Duplication audit:**

1. **Deployment:**
   - docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md (1072 lines) - KEEP (comprehensive)
   - skills/deployment/SKILL.md (368 lines) - REDUCE to 150 lines (decision tree + links)

2. **Database:**
   - docs/DATABASE_MIGRATIONS.md (1093 lines) - KEEP (philosophy + reference)
   - skills/database-migration/RECONCILIATION-MIGRATIONS.md (573 lines) - KEEP (actionable patterns)
   - Extract "Migration Philosophy" from docs/ → CLAUDE.md (2-3 lines)

3. **Testing:**
   - docs/CODE_STYLE.md (testing section) - KEEP (conventions)
   - skills/testing-workflow/ - KEEP (workflows, link to CODE_STYLE.md)

### Phase 3: Extract to CLAUDE.md

**Goal:** Reduce CLAUDE.md from 622 → 60 lines

**Move to docs/:**
- Code organization details → docs/CODE_STYLE.md
- Workflow state management → docs/CODE_STYLE.md#workflow-state-management
- JSON serialization → docs/CODE_STYLE.md#json-serialization
- Testing canonical pattern → skills/testing-workflow/PATTERNS.md

**Move to skills/:**
- Defensive programming checklist → skills/code-review/DEFENSIVE.md
- Error investigation steps → skills/error-investigation/AWS-DIAGNOSTICS.md
- Testing anti-patterns → skills/testing-workflow/ANTI-PATTERNS.md

**Keep in CLAUDE.md (principles only):**
- Migration philosophy (1 sentence: "Migrations are immutable, use reconciliation")
- Deployment philosophy (1 sentence: "Zero-downtime via Lambda versioning")
- Testing philosophy (1 sentence: "Fail fast, test outcomes not execution")
- Code organization philosophy (1 sentence: "Domain-driven structure")

### Phase 4: Add Cross-References

**Update skills/ SKILL.md files:**

```markdown
# Deployment Skill

**For complete deployment guide, see:**
- [Deployment Runbook](../../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md)
- [Zero-Downtime Pattern](ZERO_DOWNTIME.md)

**For deployment philosophy, see:**
- [CLAUDE.md](../../.claude/CLAUDE.md#deployment)
```

**Update docs/ files:**

```markdown
# Deployment Runbook

**Quick reference:** See [deployment skill](../../.claude/skills/deployment/SKILL.md) for decision trees and checklists.
```

### Phase 5: Update Navigation

**Create docs/README.md quick links:**

```markdown
## Quick Links by Task

| I want to... | Documentation | Skill (Quick Ref) |
|--------------|---------------|-------------------|
| Deploy to production | [Deployment Runbook](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) | [deployment skill](../.claude/skills/deployment/) |
| Write a test | [Testing Guide](testing/TESTING_GUIDE.md) | [testing-workflow skill](../.claude/skills/testing-workflow/) |
| Debug AWS issue | [AWS Operations](AWS_OPERATIONS.md) | [error-investigation skill](../.claude/skills/error-investigation/) |
```

**Create .claude/skills/README.md:**

```markdown
# Claude Code Skills

Quick reference workflows for active development.

## Available Skills

| Skill | Use When | Full Documentation |
|-------|----------|-------------------|
| deployment | Deploying or rolling back | [docs/deployment/](../../docs/deployment/) |
| testing-workflow | Writing or fixing tests | [docs/testing/](../../docs/testing/) |
| database-migration | Creating migrations | [docs/DATABASE_MIGRATIONS.md](../../docs/DATABASE_MIGRATIONS.md) |
```

---

## Decision Tree: "Should This Go in docs/ or skills/?"

```
New content to document?
│
├─ Is it explaining "WHY we chose this"? (architecture decision)
│  → docs/adr/ (if major decision)
│  → docs/ (if convention)
│
├─ Is it explaining "HOW this works"? (implementation guide)
│  ├─ Comprehensive guide (setup, context, examples, troubleshooting)
│  │  → docs/ (main guide)
│  │  → skills/ (optional: decision tree + link to docs/)
│  │
│  └─ Actionable workflow (steps, checklist, template)
│     → skills/ (main workflow)
│     → docs/ (optional: context link)
│
├─ Is it project structure/conventions? (file names, imports)
│  → docs/CODE_STYLE.md
│
├─ Is it environment setup? (install tools, configure AWS)
│  → docs/QUICKSTART.md or docs/AWS_SETUP.md
│
└─ Is it reference data? (API URLs, resource names)
   → docs/ (single source of truth)
```

---

## Examples of Good Separation

### Example 1: Testing

**CLAUDE.md (principle - 3 lines):**
```markdown
**Testing Principle:** Fail fast and visibly. Test outcomes not execution.
For testing patterns and anti-patterns, see [testing-workflow skill](.claude/skills/testing-workflow/).
```

**docs/CODE_STYLE.md (convention - 50 lines):**
```markdown
## Test Structure

tests/
├── conftest.py         # Shared fixtures ONLY
├── shared/             # Agent, workflow, data tests
...

### Naming Conventions
- Files: `test_*.py`
- Classes: `class TestComponent:`
...
```

**.claude/skills/testing-workflow/SKILL.md (workflow - 100 lines):**
```markdown
# Testing Workflow Skill

## Quick Decision: Which Test Tier?
- Fast local iteration? → `pytest --tier=0`
- Before commit? → `pytest` (default)
...

## Writing a Test: Checklist
1. [ ] Choose test location
2. [ ] Use class-based structure
...

For canonical pattern, see [PATTERNS.md](PATTERNS.md)
```

**.claude/skills/testing-workflow/PATTERNS.md (template - 200 lines):**
```markdown
# Testing Patterns

## Canonical Test Pattern

```python
class TestComponent:
    def setup_method(self):
        ...
```

[Full pattern with variations]
```

### Example 2: Deployment

**CLAUDE.md (principle - 3 lines):**
```markdown
**Deployment Philosophy:** Zero-downtime via Lambda versioning.
Build once, promote immutable image through all environments.
See [deployment skill](.claude/skills/deployment/) for workflows.
```

**docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md (comprehensive - 1072 lines):**
```markdown
# Telegram Mini App - Manual Deployment Runbook

**Purpose**: Step-by-step guide from local dev to production.

## Phase 0: Prerequisites
[Full checklist with explanations]

## Phase 1: Local Testing
[Complete setup steps]

## Phase 2: Dev Environment
[Deployment commands with context]
...
```

**.claude/skills/deployment/SKILL.md (quick ref - 150 lines):**
```markdown
# Deployment Skill

## Quick Decision Tree

What are you deploying?
├─ Code change? → [Runbook Phase 2](../../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#phase-2)
├─ Infrastructure? → [Runbook Phase 0.6](../../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#phase-06)
└─ Rollback? → [Runbook Section 4.4](../../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#44-rollback)

## Core Patterns (Quick Ref)

### Zero-Downtime
$LATEST → Version N → live alias

For details: [ZERO_DOWNTIME.md](ZERO_DOWNTIME.md)

## Common Scenarios

### Deploy Code Change to Dev
```bash
git push origin dev  # Auto-deploys
```
Verify: [Runbook Section 2.4](../../docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md#24-test-dev-endpoints)
```

### Example 3: Database Migrations

**CLAUDE.md (principle - 2 lines):**
```markdown
**Migration Principle:** Migrations are immutable once committed. Use reconciliation pattern for unknown state.
See [database-migration skill](.claude/skills/database-migration/) for patterns.
```

**docs/DATABASE_MIGRATIONS.md (comprehensive - 1093 lines):**
```markdown
# Database Migrations Guide

**Purpose:** Comprehensive guide for Aurora migrations.

## Migration Philosophy
[Full explanation of reconciliation vs sequential]

## MySQL-Specific Considerations
[Complete MySQL gotchas]

## Testing Migrations
[Integration testing patterns]
...
```

**.claude/skills/database-migration/SKILL.md (quick ref - 100 lines):**
```markdown
# Database Migration Skill

## Quick Decision

- Unknown DB state? → [Reconciliation](RECONCILIATION-MIGRATIONS.md)
- Known clean state? → [Sequential](../../docs/DATABASE_MIGRATIONS.md#traditional)
- Failed migration? → [Fix Pattern](RECONCILIATION-MIGRATIONS.md#real-world-example)

## Migration Checklist

- [ ] Uses `IF NOT EXISTS`
- [ ] No `DROP TABLE`
- [ ] Tested against empty DB
...

For complete guide: [docs/DATABASE_MIGRATIONS.md](../../docs/DATABASE_MIGRATIONS.md)
```

**.claude/skills/database-migration/RECONCILIATION-MIGRATIONS.md (patterns - 573 lines):**
```markdown
# Reconciliation Migration Patterns

## Pattern 1: Conditional Column Creation

```sql
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS ...);
SET @sql = IF(@col_exists = 0, 'ALTER TABLE ...', 'SELECT "exists"');
...
```

[Full patterns with copy-paste templates]
```

---

## Final Recommendations

### 1. Content Placement Rules

**Place in docs/ when:**
- ✅ Explaining project architecture or design decisions
- ✅ Comprehensive reference guide (setup, configuration, troubleshooting)
- ✅ Project conventions (naming, structure, patterns)
- ✅ Stable content that changes rarely
- ✅ Needs narrative flow (understanding-focused)

**Place in skills/ when:**
- ✅ Actionable workflow (step-by-step, decision tree)
- ✅ Quick reference (copy-paste templates, checklists)
- ✅ Task-specific guidance ("When X happens, do Y")
- ✅ Evolving practices (improves with team experience)
- ✅ Needs random access (jump to relevant section)

**Place in CLAUDE.md when:**
- ✅ Core principle that guides all code (< 1 paragraph)
- ✅ Links to details in docs/ or skills/
- ✅ Goldilocks Zone abstraction (not too vague, not too specific)

### 2. Duplication Strategy

**Acceptable duplication:**
- Short code examples (< 20 lines) to illustrate pattern
- Quick reference commands (with link to full guide)
- Decision trees (distilled from comprehensive guide)

**Unacceptable duplication:**
- Complete pattern explanation (pick one: docs/ or skills/)
- Troubleshooting steps (full list should be one place)
- Setup instructions (maintain in docs/ only)

**When duplication exists:**
1. Identify primary location (most complete version)
2. Secondary location links to primary
3. Secondary has minimal summary + link

### 3. Cross-Reference Conventions

**From skills/ to docs/:**
```markdown
For complete guide, see [docs/X.md](../../docs/X.md)
For philosophy, see [CLAUDE.md](../../.claude/CLAUDE.md#section)
```

**From docs/ to skills/:**
```markdown
Quick reference: See [X skill](../../.claude/skills/X/SKILL.md)
```

**From CLAUDE.md to both:**
```markdown
For detailed patterns, see [X skill](.claude/skills/X/)
For comprehensive guide, see [docs/X.md](docs/X.md)
```

### 4. Maintenance Protocol

**When updating content:**

1. **Principle changed?**
   - Update CLAUDE.md (1-2 sentences)
   - Update docs/ (full explanation)
   - Update skills/ (workflow implications)

2. **Workflow improved?**
   - Update skills/ (new steps)
   - Check docs/ (philosophy unchanged? keep as-is)

3. **Convention changed?**
   - Update docs/CODE_STYLE.md
   - Check skills/ (template still valid? update)

4. **New pattern discovered?**
   - Add to skills/ (actionable pattern)
   - Add to docs/ (explanation + context)
   - Optionally add principle to CLAUDE.md

---

## Success Metrics

**How to know this is working:**

1. **CLAUDE.md < 60 lines** (currently 622)
   - Principles only, details linked out

2. **No confusion when adding content**
   - Decision tree answers "where does this go?"
   - < 30 seconds to decide

3. **Low maintenance burden**
   - Single place to update most content
   - Cross-references stay valid

4. **High discoverability**
   - Humans find comprehensive guides in docs/
   - Claude finds actionable workflows in skills/
   - Both audiences satisfied

5. **No complaints about duplication**
   - Same info in multiple places → investigate
   - Should be primary + link, not duplicated

---

## Resources

### Projects with Good docs/ + skills/ Separation

*Research needed - search GitHub for projects with both `.claude/skills/` and `docs/`*

### Related Explorations

- [CLAUDE.md content boundaries](https://github.com/search?q=%22CLAUDE.md%22+%22docs%2F%22&type=code)
- [Skills vs documentation organization](https://docs.anthropic.com/claude/docs/claude-skills)

---

**Next Steps:**

1. Review this exploration with user
2. Get feedback on recommended approach
3. Create migration plan with specific files to move
4. Execute Phase 1 (inventory) and validate assumptions
5. Iterate based on what works in practice

**Last Updated:** 2025-12-26
**Author:** Claude (Sonnet 4.5)
**Status:** Draft for review
