# CLAUDE.md Layering & Skill Compatibility Exploration

**Date**: 2025-12-26
**Status**: Research Complete
**Goal**: Determine optimal CLAUDE.md structure for compatibility with public skills

---

## Problem Decomposition

### The Core Question

How should CLAUDE.md be structured to maximize compatibility with publicly shared skills while maintaining project-specific guidance?

### Two Competing Philosophies

**Philosophy 1: "Material & Physics" (Project Specifics)**
- Contains concrete "where things are" (file paths, directory structure)
- Documents "how things work together" (integration contracts, APIs)
- Project-specific, arbitrary conventions
- Like a map + instruction manual for THIS codebase

**Philosophy 2: "Principles Layer" (Abstract Guidance)**
- Contains timeless principles that guide decision-making
- Skills reference these for trade-off guidance
- More abstract, less project-specific
- Like a constitution + design philosophy

### Current State Analysis

**Our CLAUDE.md**: 622 lines, heavily principle-focused
- ~70% principles (defensive programming, error handling, testing patterns)
- ~20% architecture (domain-driven design, Aurora-first, semantic layer)
- ~10% project specifics (tech stack, branch strategy, commands)
- Extensive cross-references to skills for detailed patterns

**Community Guidance**: Keep CLAUDE.md < 300 lines, preferably < 60 lines
- Our 622 lines is 2-10x the recommended size
- But we use progressive disclosure via skills (good!)
- Most content has moved to skills already

---

## Research Findings

### 1. Official Anthropic Guidance

**Source**: [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)

**Key Findings**:
- Skills are **model-invoked** (Claude decides when to use them)
- Skills load from multiple layers: `~/.config/claude/skills/`, `.claude/skills/`, plugins
- Progressive disclosure: frontmatter → SKILL.md → supporting docs
- **CLAUDE.md and skills are complementary, not competing**

**Critical Quote** (from [HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)):
> "Use CLAUDE.md for short, always-true project conventions and standards. Use skills when you want Claude to auto-apply a richer workflow."

**Critical Quote** (from [alexop.dev](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)):
> "CLAUDE.md captures project memory you want loaded at startup; skills package rich, auto-discovered capabilities that Claude applies when relevant."

### 2. Skill-CLAUDE.md Relationship

**Source**: [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)

**Key Patterns**:

| Content Type | CLAUDE.md | Skills |
|--------------|-----------|--------|
| "Always true" rules | ✅ Yes | ❌ No |
| Project-wide conventions | ✅ Yes | ❌ No |
| Domain-specific workflows | ❌ No | ✅ Yes |
| Reference files/patterns | ❌ No | ✅ Yes |
| Tools/scripts | ❌ No | ✅ Yes |

**Skills can reference CLAUDE.md principles** but not the other way around:
- CLAUDE.md says "fail fast and visibly" (WHY)
- code-review skill shows 5 patterns for HOW to do that

### 3. Public Skill Compatibility Requirements

**Source**: [anthropics/skills GitHub](https://github.com/anthropics/skills)

**What makes skills portable**:
1. **Minimal assumptions about project structure**
   - Skills are self-contained folders
   - No dependency on specific CLAUDE.md structure
   - Universal availability (Claude Code, Claude.ai, API)

2. **Framework-agnostic**
   - Don't require specific tech stack
   - Don't assume particular file organization
   - Work via instructions + bundled scripts

3. **Composition pattern**
   - Multiple skills can stack
   - Skills can reference each other
   - Skills inherit CLAUDE.md context automatically

**External skills work if**:
- Their `description` matches your domain (auto-discovery)
- Their `allowed-tools` list doesn't conflict
- They don't contradict your CLAUDE.md conventions

### 4. Progressive Disclosure Pattern

**Source**: [Lee Hanchung's Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

**Three-layer hierarchy**:
1. **Frontmatter** (minimal): name, description, license
2. **SKILL.md** (focused): comprehensive but task-specific
3. **Supporting files** (detailed): scripts, references, assets

**CLAUDE.md fits ABOVE this** as "Layer 0: Always-loaded context"

**Why this matters**:
- Context window is shared resource
- Only skill frontmatter loaded at startup
- Full skill content loads on-demand
- CLAUDE.md competes with ALL skill frontmatter for context space

### 5. Content Engineering Trade-offs

**Source**: [Maxitect Blog](https://www.maxitect.blog/posts/maximising-claude-code-building-an-effective-claudemd)

**The 150-200 Instruction Budget**:
- Frontier LLMs reliably follow ~150-200 instructions total
- Claude Code system prompt already uses ~50 instructions
- Your CLAUDE.md + all skill frontmatter share remaining ~100-150 instructions
- Exceeding budget degrades performance uniformly

**Minimal vs Comprehensive Debate**:

**Case for Minimal** (< 60 lines):
- Leaves room for skill instructions
- Forces discipline ("is this really always-true?")
- Faster for Claude to parse
- Less maintenance burden

**Case for Strategic Comprehensiveness**:
- Progressive disclosure via separate markdown files (you're doing this!)
- High-level principles stable over time (less churn than specifics)
- Cross-references create knowledge graph
- Our 622 lines mostly principles, not specifics

**Best Practice Reconciliation**:
> "Start simple with basic project structure and build documentation, then expand based on actual friction points in your workflow." - [Apidog Blog](https://apidog.com/blog/claude-md/)

### 6. Real-World Examples Analysis

**Example 1: Full Sample File** ([GitHub Gist](https://gist.github.com/scpedicini/179626cfb022452bb39eff10becb95fa))

Structure:
- Best Practices (component design, modularity)
- Tech Stack (Node 22, PNPM, Astro 5)
- Available Tools (CLI commands)
- Planning (workflow methodology)
- Documentation References (pointers to guides)
- Final Steps (validation checklist)

**Analysis**: ~75% material/physics, 25% principles. Very procedural.

**Example 2: Next.js Template** ([GitHub Gist](https://gist.github.com/gregsantos/2fc7d7551631b809efa18a0bc4debd2a))

Structure:
- Tech stack with versions
- Directory structure
- Component organization
- Coding conventions
- Testing approach

**Analysis**: ~60% material/physics, 40% conventions. Heavy on structure.

**Pattern**: Most public examples are material-focused, but they're for SIMPLER projects (no skills!)

---

## Solution Space

### Option 1: CLAUDE.md as Material & Physics

**What it means**:
- Heavy focus on project structure ("files are here")
- Integration contracts ("service X talks to service Y like this")
- Tech stack specifics ("we use Aurora MySQL 8.0")
- Command references ("run `just test-deploy` before merging")

**Pros**:
- ✅ Onboarding: New developers get oriented fast
- ✅ Navigability: Easy to find where things are
- ✅ Concrete: Less ambiguous than principles
- ✅ Familiar: Matches most public examples

**Cons**:
- ❌ High churn: File paths change, requires updates
- ❌ Competes with skills: Duplicates skill content
- ❌ Context budget: Uses space on specifics instead of principles
- ❌ Skill compatibility: External skills expect principles, not paths

**Example content**:
```markdown
## File Organization
- `src/agent/` - Agent orchestration (state management)
- `src/data/` - Data layer (Aurora, yfinance, news)
- `src/workflow/` - LangGraph workflows
- `tests/` - Test suite (tier 0-4)

## Commands
- `just test-deploy` - Run tier 1 tests before deploy
- `just dev` - Start local development server
```

**Skill compatibility**: ⚠️ Medium
- External skills don't care about your file paths
- But they can REFERENCE your material ("in the agent/ directory...")
- Material doesn't contradict external skills, just irrelevant to them

### Option 2: CLAUDE.md as Principles Layer

**What it means**:
- Timeless architectural principles
- Design philosophies (DDD, fail-fast, defensive programming)
- Testing principles (FIRST, anti-patterns)
- Error handling strategies (multi-layer verification)

**Pros**:
- ✅ Low churn: Principles stable over time
- ✅ Skill synergy: Skills reference principles for trade-offs
- ✅ Context efficient: High information density
- ✅ Skill compatibility: External skills expect/use principles
- ✅ Reusability: Principles transfer across projects

**Cons**:
- ❌ Onboarding: New developers need concrete examples
- ❌ Navigability: "Where do I put this file?" not answered
- ❌ Completeness: Needs skills to be actionable
- ❌ Abstraction risk: Too abstract = no guidance

**Example content**:
```markdown
## Defensive Programming Principles

**Core Principle**: Fail fast and visibly when something is wrong.

**Key patterns**:
- Validate configuration at startup, not on first use
- Check operation outcomes (rowcount, status codes), not just exceptions
- No silent fallbacks: Default values explicit, not hidden recovery
- Test failure modes: After writing test, break code to verify

**See**: code-review skill (DEFENSIVE.md) for patterns
```

**Skill compatibility**: ✅ High
- External skills can reference your principles
- Skills build on shared understanding
- Principles guide skill selection (Claude knows when to use refactor skill)
- Portable: Your skills could work in other projects

### Option 3: Hybrid Approach (Sections for Both)

**What it means**:
- Separate sections for material and principles
- Material section: concise, just enough to navigate
- Principles section: detailed, explains WHY
- Clear boundaries between the two

**Pros**:
- ✅ Balanced: Serves both onboarding and guidance needs
- ✅ Flexible: Can adjust ratio over time
- ✅ Explicit: Clear what belongs where
- ✅ Compatible: External skills use principle sections

**Cons**:
- ❌ Larger: Harder to keep under 300 lines
- ❌ Maintenance: Two separate concerns to update
- ❌ Clarity: Risk of confusion about what goes where

**Example structure**:
```markdown
# CLAUDE.md

## Project Context (Material)
- Tech stack: Python 3.11, LangGraph, Aurora MySQL
- Key files: `src/agent/`, `src/workflow/`, `src/data/`
- Commands: `just test-deploy`, `just dev`

## Core Principles (Philosophy)
- Defensive programming: Fail fast and visibly
- Aurora-first: No external API fallback in read path
- Domain-driven: Organize by functionality, not layer

## Skills & Detailed Patterns
- Testing: See testing-workflow skill
- Deployment: See deployment skill
- Code review: See code-review skill
```

**Skill compatibility**: ✅ High
- Material section ignored by external skills
- Principle section referenced by skills
- Best of both worlds IF kept concise

### Option 4: Minimal CLAUDE.md + Rich Skills (Move Everything to Skills)

**What it means**:
- CLAUDE.md < 60 lines: project name, tech stack, branch strategy
- Everything else moves to skills
- Even project-specific patterns become skills
- CLAUDE.md is just "metadata" layer

**Pros**:
- ✅ Maximum context space for skills
- ✅ Fully leverages skill ecosystem
- ✅ Progressive disclosure: Only load what's needed
- ✅ External skill compatibility: Nothing to conflict with
- ✅ Follows official guidance (<60 lines)

**Cons**:
- ❌ Fragmentation: Knowledge spread across many files
- ❌ Discoverability: Need to know which skill to invoke
- ❌ Onboarding: No single source of truth
- ❌ Overhead: Creating skills for simple conventions

**Example CLAUDE.md**:
```markdown
# Daily Report - Telegram Mini App

**Tech Stack**: Python 3.11, LangGraph, Aurora MySQL, FastAPI, React
**Architecture**: Serverless Lambda with semantic layer pattern

## Branch Strategy
- `dev` → dev environment
- `main` → staging environment
- `v*.*.*` tags → production environment

## Skills
- `testing-workflow` - Test patterns, tiers, anti-patterns
- `deployment` - Zero-downtime Lambda deployments
- `code-review` - Security, performance, defensive programming
- `telegram-uiux` - React state management, UI patterns
- `database-migration` - Aurora migrations, MySQL gotchas

Run `just --list` for common commands.
```

**Skill compatibility**: ✅ Maximum
- External skills have full context budget
- No risk of conflicts
- Your skills could be published standalone
- Fully modular

---

## Evaluation Matrix

Comparing approaches on key criteria (1-5 scale, 5 = best):

| Criterion | Material/Physics | Principles | Hybrid | Minimal + Skills |
|-----------|-----------------|------------|--------|------------------|
| **Skill Compatibility** | 3 | 5 | 5 | 5 |
| **Maintenance Burden** | 2 | 4 | 3 | 5 |
| **Clarity** | 5 | 3 | 4 | 4 |
| **Reusability** | 2 | 5 | 4 | 5 |
| **Onboarding Speed** | 5 | 2 | 4 | 3 |
| **Context Efficiency** | 2 | 5 | 3 | 5 |
| **External Skill Use** | 3 | 5 | 5 | 5 |
| **Follows Best Practices** | 3 | 4 | 3 | 5 |
| **Total** | 25 | 33 | 31 | 37 |

**Analysis**:
- **Material/Physics**: Good for onboarding, poor for skills
- **Principles**: Best for skills, harder for new developers
- **Hybrid**: Balanced but larger
- **Minimal + Skills**: Winner on most criteria, aligns with best practices

---

## Public Skill Requirements

### What External Skills Need from CLAUDE.md

**Based on Anthropic official skills** ([anthropics/skills](https://github.com/anthropics/skills)):

1. **Nothing mandatory** - Skills are self-contained
2. **Optional: Principles for context** - Skills can reference your testing/error handling philosophies
3. **Optional: Domain vocabulary** - If skill mentions "Aurora", helps if CLAUDE.md defines what that means
4. **No specific structure required** - Skills don't parse CLAUDE.md, Claude does

### Standard Sections/Structure

**No standard exists**, but common patterns:

**Minimal Template** (from community examples):
```markdown
# Project Name

**Stack**: Tech1, Tech2, Tech3
**Architecture**: Brief description

## Core Conventions
- Convention 1
- Convention 2

## Development Workflow
- Command for testing
- Command for deployment

## References
- See skill-name for detailed patterns
```

**Our Current Approach**: Goldilocks Zone principle
- Principles that guide behavior
- Explain WHY (so you can adapt)
- Survive implementation changes
- Would cause bugs if not followed

**Compatibility**: ✅ Our approach already compatible
- We provide principles, not lock-in
- We cross-reference skills extensively
- We explain WHY, not just WHAT

### Conventions for Skill Discovery

**How skills are discovered**:
1. **Frontmatter `description` field** - Matched against user intent
2. **Location** - `~/.config/claude/skills/` (user), `.claude/skills/` (project), plugins
3. **Auto-invocation** - Claude decides based on task

**What this means for CLAUDE.md**:
- CLAUDE.md doesn't need to "advertise" skills
- Skills are auto-discovered
- BUT: CLAUDE.md can REFERENCE skills ("See deployment skill for zero-downtime patterns")

**Best practice** (from our README.md):
```markdown
## Skills & Detailed Patterns
- Testing: See testing-workflow skill
- Deployment: See deployment skill
```

This helps Claude know which skills are available, but not required.

---

## Recommendations

### Ranked Recommendations

#### 1. **RECOMMENDED: Gradual Migration to Minimal + Rich Skills**

**Why**: Best skill compatibility, follows official guidance, maximum flexibility

**Migration path**:

**Phase 1: Audit Current CLAUDE.md (622 lines)**
- ✅ What's already in skills? (can be removed from CLAUDE.md)
- ⚠️ What's pure project-specific? (move to project-info skill or keep minimal)
- ⚠️ What's timeless principles? (keep in CLAUDE.md, but condense)

**Phase 2: Condense CLAUDE.md to < 150 lines**
- Keep: Tech stack, architecture philosophy, branch strategy
- Keep: Core principles (defensive programming, Aurora-first, fail-fast)
- Keep: Skill references ("See X skill for detailed patterns")
- Remove: Detailed examples (move to skills)
- Remove: Testing patterns (already in testing-workflow skill)
- Remove: Deployment patterns (already in deployment skill)

**Phase 3: Create "Project Conventions" Skill**
- File organization
- Naming conventions
- CLI commands
- Common workflows

**Phase 4: Ultimate Goal (< 60 lines)**
- Project name, tech stack, architecture
- Branch strategy
- Core principles (one-liner each)
- Skill directory ("Run `ls .claude/skills` to see available skills")

**Benefits**:
- ✅ Maximizes context budget for skills
- ✅ External skills drop-in compatible
- ✅ Your skills could be published standalone
- ✅ Follows Anthropic best practices

**Example target CLAUDE.md**:
```markdown
# Daily Report - Thai Financial Ticker Analysis

**Stack**: Python 3.11, LangGraph, OpenRouter, Aurora MySQL, FastAPI, React
**Architecture**: Serverless semantic layer (Layer 1: Ground truth → Layer 2: Semantic states → Layer 3: LLM synthesis)

## Core Principles
- **Defensive programming**: Fail fast and visibly. Validate before execution.
- **Aurora-first**: Pre-compute nightly, no external API fallback in read path.
- **Domain-driven**: Organize by functionality (agent, data, workflow), not layer.
- **Progressive disclosure**: CLAUDE.md (principles) → Skills (patterns) → Docs (implementation).

## Development
- `dev` branch → dev env | `main` branch → staging env | `v*.*.*` tags → production env
- Run `just --list` for commands | Run `ls .claude/skills` for available skills

## Skills Reference
- **Testing**: testing-workflow (tiers, anti-patterns, defensive)
- **Deployment**: deployment (zero-downtime, multi-env, artifact promotion)
- **Code Review**: code-review (security, performance, defensive)
- **Frontend**: telegram-uiux (state management, React patterns)
- **Database**: database-migration (reconciliation, MySQL gotchas)
- **Debugging**: error-investigation (multi-layer verification, CloudWatch)
- **Refactoring**: refactor (complexity analysis, hotspots)

See [Skills README](.claude/skills/README.md) for complete catalog.
```

**This would be ~50 lines** (well under 60!)

---

#### 2. **ALTERNATIVE: Hybrid with Strict Section Limits**

**Why**: Balances onboarding with skill compatibility, clear boundaries

**Structure**:
```markdown
# CLAUDE.md

## Project Context (<30 lines)
[Material: stack, files, commands]

## Core Principles (<60 lines)
[Philosophy: defensive programming, Aurora-first, etc.]

## Skills & Resources (<30 lines)
[Directory of where to find detailed patterns]
```

**Total: < 120 lines** (still over recommended, but reasonable)

**Benefits**:
- ✅ Single source has both material and principles
- ✅ Section limits prevent bloat
- ✅ Still skill-compatible (principles section)

**Trade-offs**:
- ⚠️ Larger than recommended
- ⚠️ Requires discipline to maintain limits

---

#### 3. **ALTERNATIVE: Current Approach with Pruning**

**Why**: What we have mostly works, just needs trimming

**Action items**:
1. Move detailed examples to skills (already mostly done)
2. Condense repeated patterns (testing, deployment)
3. Remove anything that's ALSO in skills
4. Target: 300 lines (half current size)

**Benefits**:
- ✅ Low effort (incremental improvement)
- ✅ Preserves current organization

**Trade-offs**:
- ⚠️ Still larger than recommended
- ⚠️ Doesn't fully leverage skill ecosystem

---

### How to Layer Skills on CLAUDE.md

**Pattern 1: CLAUDE.md Principle → Skill Pattern**

CLAUDE.md says:
```markdown
**Defensive Programming**: Fail fast and visibly. Validate before execution.
```

Skill elaborates:
```markdown
# code-review/DEFENSIVE.md

## Validation Gates Pattern

Before executing operation, validate prerequisites:
- [ ] Input data exists AND non-empty
- [ ] Configuration values set
- [ ] External dependencies available

Example:
[detailed code examples]
```

**Pattern 2: CLAUDE.md Reference → Skill Detail**

CLAUDE.md says:
```markdown
**Testing**: See testing-workflow skill for tier strategy, anti-patterns, defensive patterns.
```

Skill provides:
```markdown
# testing-workflow/SKILL.md

## Test Tier Strategy
- Tier 0: Unit only (fast local)
- Tier 1: Unit + mocked (deploy gate)
[detailed tiers, commands, examples]
```

**Pattern 3: CLAUDE.md Philosophy → Skill Implementation**

CLAUDE.md says:
```markdown
**Aurora-first**: Pre-compute data nightly. No external API fallback in read path.
```

Skill provides:
```markdown
# deployment/MONITORING.md

## Aurora Pre-computation Verification

After scheduler runs:
1. Check row count in precomputed_reports
2. Verify latest report timestamp
3. Test read API with known ticker
[detailed smoke tests]
```

**Key principle**: CLAUDE.md answers "WHY", skills answer "HOW"

---

### How to Leverage Public Skill Ecosystem

#### Step 1: Identify Reusable Skills

**Categories of public skills** (from [anthropics/skills](https://github.com/anthropics/skills)):
- Document manipulation (DOCX, PDF, PPTX, XLSX)
- Testing web apps
- MCP server generation
- Communications/branding workflows

**For our project**:
- ✅ Document skills (useful for PDF reports)
- ❌ MCP server (not using MCP)
- ✅ Testing web apps (useful for Telegram Mini App)

#### Step 2: Install Public Skills

```bash
# Via Claude Code marketplace
/plugin install document-skills@anthropic-agent-skills

# Or manually
cp -r ~/.claude/skills/public/pdf .claude/skills/
```

#### Step 3: Ensure Compatibility

**Check before installing**:
1. Read skill's SKILL.md frontmatter
2. Verify `allowed-tools` don't conflict
3. Check if skill expects certain CLAUDE.md structure (rare)
4. Test in isolated branch

#### Step 4: Cross-Reference in Your Skills

Your skill can reference public skill:
```markdown
# deployment/SKILL.md

## Generating Deployment Reports

For PDF reports, use the pdf skill:
- See `pdf` skill for template-based PDF generation
- Our deployment summary template: `templates/deploy-summary.pdf.hbs`
```

#### Step 5: Contribute Back (Optional)

If you create generic skills:
1. Remove project-specific references
2. Add clear frontmatter
3. Submit to anthropics/skills or publish as plugin

**Our skills that could be generalized**:
- ❌ telegram-uiux (too specific to our Telegram app)
- ✅ testing-workflow (generic test tiers, anti-patterns)
- ✅ deployment (generic zero-downtime Lambda patterns)
- ❌ database-migration (MySQL-specific, but pattern is generic)

---

### Migration Path from Current Structure

**Current state**: 622 lines, ~70% principles, extensive skill cross-references

**Goal**: < 150 lines (stretch: < 60 lines), minimal material, core principles only

#### Phase 1: Audit & Categorize (1 week)

**Script to analyze current CLAUDE.md**:
```bash
# Count lines per section
awk '/^## / {section=$0; next} {count[section]++} END {for (s in count) print s, count[s]}' .claude/CLAUDE.md

# Find content already in skills
grep -r "CLAUDE.md" .claude/skills/*/SKILL.md
```

**Categorize each section**:
- 🟢 Core principle (keep, maybe condense)
- 🟡 Principle with examples (keep principle, move examples to skill)
- 🔴 Pure material (move to project-conventions skill OR keep minimal)
- ⚪ Duplicate (already in skill, can remove)

**Example audit**:
```
## Testing Guidelines        → 🟡 Keep tiers table, move detailed patterns to testing-workflow
## Defensive Programming     → 🟢 Keep, condense to bullet points
## Code Organization         → 🔴 Move to project-conventions skill
## Aurora VPC Access Pattern → 🔴 Move to deployment skill (AWS patterns)
## Database Migration        → 🟡 Keep principle, examples already in database-migration skill
```

#### Phase 2: Create Project-Conventions Skill (1 week)

Move all material to new skill:

```bash
mkdir -p .claude/skills/project-conventions
```

**project-conventions/SKILL.md**:
```markdown
---
name: project-conventions
description: Daily Report project-specific conventions (file structure, naming, CLI commands, branch strategy)
---

# Project Conventions

**Focus**: Project-specific material that doesn't fit in CLAUDE.md principles

## File Organization
[moved from CLAUDE.md]

## Naming Conventions
[moved from CLAUDE.md]

## CLI Commands
[moved from CLAUDE.md]

## Branch Strategy Details
[moved from CLAUDE.md]
```

#### Phase 3: Condense CLAUDE.md Principles (1 week)

**For each principle section**:
1. Reduce examples (move to skills)
2. Keep core principle (1-2 sentences)
3. Add "See X skill" reference

**Before** (CLAUDE.md):
```markdown
### Defensive Programming Principles

**Core Principle:** Fail fast and visibly when something is wrong. Silent failures hide bugs.

**Key patterns:**
- Validate configuration at startup, not on first use (prevents production surprises)
- Explicit failure detection: Check operation outcomes (rowcount, status codes), not just absence of exceptions
- No silent fallbacks: Default values should be explicit, not hidden error recovery
- Test failure modes: After writing a test, intentionally break the code to verify the test catches it

**For detailed defensive programming patterns**, see [code-review skill](.claude/skills/code-review/DEFENSIVE.md)
```

**After** (CLAUDE.md):
```markdown
**Defensive Programming**: Fail fast and visibly. Validate at startup, check outcomes (not just exceptions), no silent fallbacks. See code-review skill (DEFENSIVE.md).
```

**Condensed from ~10 lines to 1 line!**

#### Phase 4: Test with External Skill (1 week)

**Install a public skill**:
```bash
# Try anthropics document skills
/plugin install document-skills@anthropic-agent-skills
```

**Test compatibility**:
1. Does public skill work without modifications?
2. Does it conflict with our conventions?
3. Can it reference our principles?
4. Can our skills reference it?

**Success criteria**:
- ✅ Public skill works out-of-box
- ✅ No conflicts with CLAUDE.md
- ✅ Can compose with our skills

#### Phase 5: Final CLAUDE.md Polish (1 week)

**Target structure**:
```markdown
# Project Name & Stack (5 lines)

## Architecture Philosophy (10 lines)
- Core architectural principles
- Why we chose this approach

## Core Development Principles (30 lines)
- Defensive programming
- Aurora-first
- Domain-driven
- Fail-fast
[Each as 1-2 line summary + skill reference]

## Development Workflow (10 lines)
- Branch strategy
- Key commands

## Skills Directory (5 lines)
- List of available skills with one-line descriptions
```

**Total: ~60 lines** ✅

#### Validation Criteria

Before declaring migration complete:
- [ ] CLAUDE.md < 150 lines (stretch: < 60)
- [ ] All principles have skill references
- [ ] No duplicated content (CLAUDE.md vs skills)
- [ ] External skill tested and working
- [ ] Team can find information easily (not buried in skills)
- [ ] CI passes (no broken references)

---

## Key Insights & Takeaways

### 1. CLAUDE.md and Skills Are Complementary, Not Competing

**Don't think of it as**: "Should this go in CLAUDE.md OR a skill?"

**Think of it as**: "CLAUDE.md has the principle, skill has the pattern"

**Example**:
- CLAUDE.md: "Multi-layer verification: Check exit code, logs, and data state"
- error-investigation skill: "Here's the 7-step checklist for AWS Lambda debugging"

### 2. Context Budget is Real

**The math**:
- Claude can follow ~150-200 instructions
- System prompt uses ~50
- Your CLAUDE.md + all skill frontmatter share remaining ~100-150
- Every line in CLAUDE.md is a line NOT available for skills

**Implication**: Be ruthless about what goes in CLAUDE.md

### 3. Progressive Disclosure is the Pattern

**Layer 0**: CLAUDE.md (always loaded, < 60 lines)
**Layer 1**: Skill frontmatter (loaded at startup, 1-2 lines per skill)
**Layer 2**: SKILL.md (loaded on-demand, comprehensive)
**Layer 3**: Supporting docs (loaded as needed, detailed)
**Layer 4**: Scripts/tools (executed when used)

**Your current approach already does this!** Just need to shrink Layer 0.

### 4. External Skills Don't Care About Your File Paths

**Public skills are framework-agnostic** - they work via instructions, not assumptions.

**This means**:
- Your file organization doesn't affect skill compatibility
- But external skills CAN reference your organization if you describe it
- Material in CLAUDE.md is mostly for YOUR team, not for skills

### 5. Principles Travel, Material Doesn't

**Principles** (defensive programming, fail-fast, Aurora-first):
- Apply across projects
- Skills can reference them
- Stable over time
- High information density

**Material** (file paths, command syntax):
- Project-specific
- Changes frequently
- Low information density
- Doesn't help skill compatibility

**Recommendation**: Minimize material, maximize principles

---

## Resources & References

### Official Documentation
- [Using CLAUDE.MD files](https://claude.com/blog/using-claude-md-files) - Official introduction
- [Agent Skills Documentation](https://code.claude.com/docs/en/skills) - How skills work
- [Anthropic Skills Repository](https://github.com/anthropics/skills) - Public skills source code
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) - Official guidance

### Community Guides
- [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) - Best practices, progressive disclosure
- [Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/) - CLAUDE.md vs skills
- [Claude Agent Skills: Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) - Internal mechanics
- [Inside Claude Code Skills](https://mikhail.io/2025/10/claude-code-skills/) - Structure and invocation
- [Maximising Claude Code](https://www.maxitect.blog/posts/maximising-claude-code-building-an-effective-claudemd) - Context engineering

### Examples & Templates
- [Full CLAUDE.md Sample](https://gist.github.com/scpedicini/179626cfb022452bb39eff10becb95fa) - Production example
- [Next.js + TypeScript Template](https://gist.github.com/gregsantos/2fc7d7551631b809efa18a0bc4debd2a) - Framework-specific
- [ArthurClune/claude-md-examples](https://github.com/ArthurClune/claude-md-examples) - Collection of examples
- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) - Curated list of resources

### Best Practices Articles
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) - Official engineering practices
- [Context Engineering for Claude Code](https://thomaslandgraf.substack.com/p/context-engineering-for-claude-code) - Deep technical knowledge management
- [Cooking with Claude Code](https://www.siddharthbharath.com/claude-code-the-complete-guide/) - Complete guide
- [Awesome Claude Skills](https://github.com/travisvn/awesome-claude-skills) - Skill ecosystem

---

## Conclusion

**The Answer**: Your project should use **Minimal CLAUDE.md + Rich Skills** (Option 4)

**Why**:
1. ✅ Maximizes skill compatibility (both external and your own)
2. ✅ Follows Anthropic official guidance (< 60 lines)
3. ✅ Maximizes context budget for skills
4. ✅ Enables skill portability (your skills could be published)
5. ✅ Already 80% there (you have great skills!)

**Your Current CLAUDE.md**: 622 lines, ~70% principles
- **Good**: Progressive disclosure via skills, principle-focused
- **Opportunity**: Condense to < 60 lines, move material to project-conventions skill

**Migration Path**: 5-phase, 5-week plan
- Phase 1: Audit & categorize current content
- Phase 2: Create project-conventions skill (move material)
- Phase 3: Condense principles to 1-2 lines each
- Phase 4: Test with external skill
- Phase 5: Final polish to < 60 lines

**Expected Outcome**:
- CLAUDE.md: ~50 lines (tech stack + core principles + skill directory)
- Skills: 10+ focused skills (including new project-conventions)
- External skills: Drop-in compatible
- Your skills: Potentially publishable

**Next Steps**:
1. Run audit script to categorize current CLAUDE.md content
2. Identify top 5 principles that MUST stay in CLAUDE.md
3. Create project-conventions skill for material
4. Start condensing (target: < 150 lines first, then < 60)
5. Test with anthropics/skills public skill

**Remember**: CLAUDE.md is the "constitution" (WHY), skills are the "laws" (HOW). Keep the constitution short and timeless!
