# Claude Code Skills

**Part of the Agent Kernel** - Auto-discovered capabilities for specialized assistance.

This directory contains 15 Claude Code skills that provide focused expertise for common development tasks in the dr-daily-report project. Skills are automatically discovered and invoked by Claude when relevant to the user's request.

> **Agent Kernel** = The complete knowledge system (`.claude/*` + `docs/*`). Skills are one layer within the Agent Kernel. See [CLAUDE.md](../CLAUDE.md#agent-kernel) for the full architecture.

**New in 2026**: Skills now support **tiered composition**. Tier-1 skills are modular, reusable units. Tier-2 skills compose Tier-1 skills for domain-specific workflows.

---

## What are Claude Code Skills?

**Skills are model-invoked capabilities** that Claude can automatically use to provide specialized assistance. Each skill:
- Has a YAML frontmatter with `name` and `description` for auto-discovery
- Contains focused documentation on a specific domain (testing, deployment, code review, etc.)
- Uses progressive disclosure (SKILL.md entry point + detailed supporting docs)
- Is automatically triggered when Claude detects a relevant task

**Example auto-discovery:**
```
User: "Review this PR for performance issues"
Claude: [Detects "review" + "performance" keywords]
      → Invokes code-review skill
      → References PERFORMANCE.md checklist
      → Provides focused review
```

---

## Available Skills

### 1. testing-workflow
**Focus**: Test patterns, anti-patterns, and defensive testing strategies

**When Claude uses this**:
- Writing or reviewing tests
- Debugging test failures
- Improving test quality
- Avoiding testing anti-patterns

**Files**:
- `SKILL.md` - Testing principles and decision tree
- `PATTERNS.md` - FIRST principles, behavior-driven testing
- `ANTI-PATTERNS.md` - The Liar, Happy Path Only, Mock Overload
- `DEFENSIVE.md` - Defensive testing patterns

**Example trigger**: "How should I test this database function?"

---

### 2. telegram-uiux
**Focus**: Telegram Mini App UI/UX patterns, state management, React/TypeScript

**When Claude uses this**:
- Building Telegram Mini App features
- State management questions
- React component design
- Property-based testing for UI

**Files**:
- `SKILL.md` - UI principles overview
- `STATE-MANAGEMENT.md` - Normalized state, selectors
- `DATA-INVARIANTS.md` - Stale-while-revalidate, monotonic data
- `COMPONENT-PATTERNS.md` - React/TypeScript patterns
- `PROPERTY-TESTING.md` - Generative testing for UI

**Example trigger**: "How do I manage state for the ticker rankings?"

---

### 3. refacter
**Focus**: Code complexity analysis, hotspot detection, refactoring patterns

**When Claude uses this**:
- Code smells and refactoring requests
- Complexity analysis
- Identifying technical debt hotspots
- Improving code maintainability

**Files**:
- `SKILL.md` - Refactoring decision tree and workflow
- `CODE-COMPLEXITY.md` - Complexity metrics (cyclomatic, cognitive, MI)
- `HOTSPOT-ANALYSIS.md` - Code churn + complexity analysis
- `REFACTORING-PATTERNS.md` - Extract Method, Replace Conditional, connascence-based refactoring
- `scripts/analyze_complexity.py` - Radon complexity analyzer
- `scripts/analyze_hotspots.py` - Git churn + complexity tool

**Example trigger**: "This function is too complex, help me refactor it"

---

### 4. deployment
**Focus**: Zero-downtime deployments, multi-environment strategy, artifact promotion

**When Claude uses this**:
- Deployment planning and execution
- CI/CD pipeline questions
- Environment configuration
- Smoke testing and validation

**Files**:
- `SKILL.md` - Deployment philosophy and patterns
- `ZERO_DOWNTIME.md` - Lambda versioning, alias promotion
- `MULTI_ENV.md` - Branch-based deployment, artifact promotion
- `MONITORING.md` - Multi-layer verification, smoke testing
- `scripts/validate_deployment_ready.sh` - Pre-deployment validation

**Example trigger**: "How do I deploy to production with zero downtime?"

---

### 5. research
**Focus**: Investigation methodology, when to research vs iterate

**When Claude uses this**:
- Complex bug investigation
- Understanding unfamiliar code
- Deciding between research and iteration
- Systematic exploration

**Files**:
- `SKILL.md` - Research vs iteration decision framework
- `WORKFLOW.md` - Step-by-step research process
- `INVESTIGATION-CHECKLIST.md` - Systematic debugging checklist

**Example trigger**: "Same bug after 2 fix attempts - what's the root cause?"

---

### 6. error-investigation
**Focus**: Multi-layer verification, CloudWatch analysis, Lambda logging

**When Claude uses this**:
- AWS service debugging
- Lambda logging issues
- CloudWatch log analysis
- Infrastructure smoke testing

**Files**:
- `SKILL.md` - Multi-layer verification principles
- `AWS-DIAGNOSTICS.md` - Layer-by-layer AWS debugging
- `LAMBDA-LOGGING.md` - Lambda logging configuration patterns

**Example trigger**: "Lambda returns 200 but no data in database - why?"

---

### 7. line-uiux (Legacy)
**Focus**: LINE Bot message patterns, Flex Messages, chat flows

**Status**: Maintenance mode only - no new features

**When Claude uses this**:
- LINE Bot bug fixes
- LINE Flex Message issues
- Legacy code maintenance

**Files**:
- `SKILL.md` - Legacy status and migration strategy
- `MESSAGE-PATTERNS.md` - LINE Flex Message patterns
- `CHAT-FLOWS.md` - Conversation flows
- `BEST-PRACTICES.md` - LINE Bot guidelines

**Example trigger**: "Fix Thai encoding bug in LINE Bot"

---

### 8. code-review
**Focus**: Security, performance, defensive programming review

**When Claude uses this**:
- PR reviews
- Code quality audits
- Security review
- Performance optimization review

**Files**:
- `SKILL.md` - Code review principles and checklist
- `SECURITY.md` - SQL injection, XSS, secrets management
- `PERFORMANCE.md` - Lambda optimization, N+1 queries, caching
- `DEFENSIVE.md` - Validation gates, silent failure detection

**Example trigger**: "Review this PR for security issues"

---

### 9. database-migration
**Focus**: Schema migrations, reconciliation patterns, MySQL gotchas

**When Claude uses this**:
- Creating database migrations
- Fixing broken migrations
- Schema drift reconciliation
- MySQL-specific issues

**Files**:
- `SKILL.md` - Migration principles and patterns
- `RECONCILIATION-MIGRATIONS.md` - Idempotent migration patterns
- `MYSQL-GOTCHAS.md` - MySQL-specific issues and solutions
- `scripts/verify_schema.py` - Schema verification tool

**Example trigger**: "Migration failed mid-execution - how do I fix the schema?"

---

### 10. data-visualization
**Focus**: Mathematically correct, visually prominent data visualizations for time-series charts

**When Claude uses this**:
- Building charts with mathematical overlays (trendlines, patterns, indicators)
- Fixing visual artifacts (wavy lines, domain mismatches)
- Validating chart correctness
- Working with Chart.js, D3.js, Recharts

**Files**:
- `SKILL.md` - Decision tree, patterns, validation workflow
- `VISUAL-HIERARCHY.md` - Layering, opacity, colors, prominence
- `MATHEMATICAL-CORRECTNESS.md` - Domain compatibility, regression formulas
- `FRAMEWORK-PATTERNS.md` - Chart.js native features, research workflow
- `VALIDATION.md` - 4-layer progressive validation (visual → code → edge → math)

**Example trigger**: "Why are my chart trendlines wavy at weekend gaps?"

---

### 11. performance-investigation
**Focus**: Web performance metrics, bottleneck identification, optimization patterns

**When Claude uses this**:
- Diagnosing slow page loads or interactions
- Investigating API latency issues
- Optimizing bundle size or rendering
- Analyzing CloudWatch metrics for bottlenecks

**Files**:
- `SKILL.md` - Investigation workflow and decision tree
- `METRICS-GLOSSARY.md` - Performance terminology (LCP, TTFB, etc.)
- `METRICS-MAP.md` - Metrics → Infrastructure → Code mapping
- `OPTIMIZATION-PATTERNS.md` - Common fixes with code examples
- `TOOLS.md` - Browser DevTools, AWS tools, libraries
- `CHECKLIST.md` - Step-by-step investigation checklist

**Example trigger**: "Why is the modal slow to open?" or "How do I improve page load time?"

---

### 12. prompt-engineering (Tier-1)
**Focus**: Techniques for designing effective LLM prompts

**When Claude uses this**:
- Designing new prompts for LLM tasks
- Debugging poor LLM output quality
- Optimizing prompts for token efficiency
- Preventing prompt injection attacks

**Files**:
- `SKILL.md` - Core principles, decision tree
- `TECHNIQUES.md` - Zero-shot, few-shot, chain-of-thought patterns
- `ANTI-PATTERNS.md` - Common mistakes to avoid
- `SECURITY.md` - Prompt injection prevention

**Example trigger**: "How do I write better prompts?" or "Add few-shot examples"

---

### 13. context-engineering (Tier-1)
**Focus**: Optimizing the information provided to LLMs through semantic layers, token optimization, and hallucination prevention

**When Claude uses this**:
- Preparing data for LLM consumption
- Reducing token usage in prompts
- Preventing hallucinations in outputs
- Building semantic layers for data

**Files**:
- `SKILL.md` - Core principles, decision tree
- `SEMANTIC-LAYER.md` - Three-layer architecture (83% accuracy pattern)
- `TOKEN-OPTIMIZATION.md` - Token efficiency strategies
- `HALLUCINATION-PREVENTION.md` - Ground truth patterns

**Example trigger**: "How do I prevent number hallucinations?" or "Optimize context tokens"

---

### 14. prompt-management (Tier-1)
**Focus**: Langfuse prompt versioning, A/B testing, and observability patterns

**When Claude uses this**:
- Versioning prompts in Langfuse
- Setting up A/B tests for prompt variants
- Tracking prompt performance metrics
- Deploying prompt changes

**Files**:
- `SKILL.md` - Core concepts, environment strategy
- `VERSIONING.md` - Version management, labels, rollback
- `AB-TESTING.md` - A/B testing setup and analysis
- `OBSERVABILITY.md` - Metrics, tracing, alerting

**Example trigger**: "How do I version prompts in Langfuse?" or "Set up A/B test"

---

### 15. report-prompt-workflow (Tier-2)
**Focus**: Composed workflow for DR report prompt engineering, context building, and management

**Tier**: 2 (Composes: prompt-engineering, context-engineering, prompt-management)

**When Claude uses this**:
- Modifying DR report prompts
- Adding new data sections to reports
- Debugging report generation issues
- A/B testing report prompts

**Files**:
- `SKILL.md` - Architecture overview, key files
- `WORKFLOW.md` - Step-by-step modification guide
- `CHECKLIST.md` - Pre-deployment validation checklist

**Example trigger**: "Improve the DR report prompt" or "Add new indicator to report"

---

## How Skills Work

### Auto-Discovery Process

1. **User makes request** with keywords (e.g., "review performance", "test database", "deploy to prod")
2. **Claude analyzes request** against skill descriptions in YAML frontmatter
3. **Claude invokes relevant skill** by reading SKILL.md
4. **Claude provides specialized help** using patterns from skill documentation

### Skill Anatomy

Every skill follows this structure:

```
.claude/skills/<skill-name>/
├── SKILL.md                 # Entry point with YAML frontmatter
├── <SUPPORTING-DOC-1>.md    # Detailed patterns
├── <SUPPORTING-DOC-2>.md    # Checklists, examples
└── scripts/                 # Optional automation scripts
    └── <tool>.py
```

**SKILL.md frontmatter**:
```yaml
---
name: skill-name
description: Brief description of what this skill helps with (1-2 sentences)
tier: 1                    # Optional: 1 (modular) or 2 (composed)
depends:                   # Optional: for Tier-2 skills
  - prompt-engineering
  - context-engineering
---
```

### Tiered Architecture

Skills support **composition** through tiers (see [Principle #28: Compositional Hierarchy](../principles/compositional-hierarchy.md)):

| Tier | Description | Example |
|------|-------------|---------|
| **Tier-1** | Modular, reusable patterns | prompt-engineering, context-engineering |
| **Tier-2** | Domain-specific, composes Tier-1 | report-prompt-workflow |

**Why tiers?**
- **Tier-1 skills** are generic and can be reused across domains
- **Tier-2 skills** combine Tier-1 skills for specific workflows
- Avoids duplication (DRY principle for skills)
- Enables skill composition (build complex from simple)

**Example composition**:
```
report-prompt-workflow (Tier-2)
├── composes: prompt-engineering (Tier-1)
├── composes: context-engineering (Tier-1)
└── composes: prompt-management (Tier-1)
```

### Relationship Taxonomy

Skills use four relationship types (replacing generic "references"):

| Relationship | Direction | Meaning | Example |
|--------------|-----------|---------|---------|
| **composes** | Higher → Lower | Builds on, combines | Tier-2 skill → Tier-1 skills |
| **depends** | Same/Cross tier | Requires, doesn't build | Skill → external library |
| **invokes** | Cross-domain | Calls as capability | Command → skill |
| **grounds** | Meta → Instance | Provides foundation | Principle → skill pattern |

**In YAML frontmatter**:
```yaml
---
name: report-prompt-workflow
tier: 2
depends:                    # Lists what this skill composes/depends on
  - prompt-engineering      # composes (Tier-1 skill)
  - context-engineering     # composes (Tier-1 skill)
  - radon                   # depends (external tool)
---
```

**In documentation** (use explicit language):
```markdown
❌ Vague: "This skill references code-review"
✅ Explicit: "This skill composes code-review's DEFENSIVE.md patterns"
```

### Progressive Disclosure

Skills use **progressive disclosure** to balance detail and navigability:

1. **SKILL.md**: Quick decision trees, when to use, core principles
2. **Supporting docs**: Detailed patterns, examples, checklists
3. **Scripts**: Automation tools (optional)

**Example** (refactor skill):
- SKILL.md → "Is code complex? Check CODE-COMPLEXITY.md"
- CODE-COMPLEXITY.md → Cyclomatic complexity > 10? Use these patterns...
- analyze_complexity.py → Run tool to measure complexity

---

## When Claude Uses Which Skill

| User Intent | Triggered Skill(s) | Why |
|-------------|-------------------|-----|
| "Test this function" | testing-workflow | Writing/reviewing tests |
| "Review this PR" | code-review | Code quality, security, performance |
| "Deploy to production" | deployment | Deployment patterns, validation |
| "This code is complex" | refacter | Complexity analysis, refactoring |
| "Lambda not logging" | error-investigation | Lambda logging config |
| "Migration failed" | database-migration | Schema reconciliation |
| "Fix LINE bot bug" | line-uiux | Legacy LINE Bot maintenance |
| "Build UI feature" | telegram-uiux | Telegram Mini App patterns |
| "Investigate root cause" | research | Investigation methodology |
| "Chart trendlines wavy" | data-visualization | Mathematical correctness |
| "Add pattern overlay" | data-visualization | Visual hierarchy, layering |
| "Page is slow" | performance-investigation | Bottleneck identification |
| "Modal takes too long" | performance-investigation | API latency, rendering |
| "Write better prompts" | prompt-engineering | Prompt design patterns |
| "Prevent hallucinations" | context-engineering | Semantic layer, ground truth |
| "Version prompts" | prompt-management | Langfuse versioning |
| "A/B test prompts" | prompt-management | Experiment tracking |
| "Improve DR report" | report-prompt-workflow | Composed workflow |

---

## Creating New Skills

### When to Create a Skill

Create a skill when:
- ✅ Topic requires specialized knowledge (deployment, testing, migrations)
- ✅ Repeated questions in similar domain (indicates need for focused guidance)
- ✅ Multiple patterns/checklists that should be centralized
- ✅ Would benefit from auto-discovery (Claude invokes when relevant)

Don't create a skill for:
- ❌ One-time tasks (use commit message or ADR)
- ❌ Project-specific file paths (those change frequently)
- ❌ Pure implementation without reusable patterns

### Skill Creation Template

```bash
# 1. Create skill directory
mkdir -p .claude/skills/my-skill

# 2. Create SKILL.md with frontmatter
cat > .claude/skills/my-skill/SKILL.md <<'EOF'
---
name: my-skill
description: Brief description of what this skill helps with
---

# My Skill

**Focus**: What this skill specializes in

**Source**: Where knowledge came from (CLAUDE.md, real debugging, etc.)

---

## When to Use This Skill

Use my-skill when:
- ✓ Scenario 1
- ✓ Scenario 2

**DO NOT use for:**
- ✗ Scenario 3
- ✗ Scenario 4

---

## Core Principles

[Principles go here]

---

## Quick Decision Tree

[Decision tree for when to use different parts of skill]

---

## File Organization

```
.claude/skills/my-skill/
├── SKILL.md          # This file
├── PATTERNS.md       # Detailed patterns
└── CHECKLIST.md      # Step-by-step checklist
```

---

## References

[External references]
EOF

# 3. Create supporting documentation
# [Add PATTERNS.md, CHECKLIST.md, etc.]

# 4. Update this README with new skill
```

### Skill Quality Checklist

Before publishing a skill, verify:

- [ ] YAML frontmatter with `name` and `description`
- [ ] Clear "When to Use This Skill" section
- [ ] Decision tree or quick reference
- [ ] Concrete examples (not just theory)
- [ ] References to existing code/docs
- [ ] File organization section
- [ ] Listed in this README

---

## Skill Usage Statistics

Want to know which skills are most useful? Check CLAUDE.md references:

| Skill | References in CLAUDE.md | Primary Trigger |
|-------|-------------------------|-----------------|
| code-review | Defensive Programming, Testing | "review", "quality" |
| error-investigation | Error Investigation, Lambda Logging | "debug", "logs", "errors" |
| testing-workflow | Testing Anti-Patterns, Testing Principles | "test", "pytest" |
| deployment | Deployment Section | "deploy", "production" |
| database-migration | Database Migration Principles | "migration", "schema" |
| refacter | (Implicit via code quality) | "refactor", "complexity" |
| telegram-uiux | UI/Frontend Principles | "UI", "state", "component" |
| research | (Implicit via investigation) | "investigate", "root cause" |
| line-uiux | (Legacy - minimal references) | "LINE", "legacy" |
| prompt-engineering | (New) | "prompt", "few-shot", "LLM" |
| context-engineering | (New) | "context", "hallucination", "semantic" |
| prompt-management | (New) | "langfuse", "version", "A/B test" |
| report-prompt-workflow | (Tier-2) | "report prompt", "DR report" |

---

## Maintenance

### Keeping Skills Updated

Skills should evolve with the project. Update when:
- ✅ New patterns emerge from real work
- ✅ Anti-patterns discovered (add to skill with examples)
- ✅ Tools/scripts created (add to skill's scripts/)
- ✅ Documentation becomes outdated

### Skill Deprecation

Mark skills as legacy when:
- Technology is deprecated (e.g., LINE Bot → Telegram)
- Patterns no longer apply
- Merged into another skill

**Pattern**: Add `**Status:** Legacy - Maintenance only` at top of SKILL.md.

---

## FAQ

### Q: Why skills instead of just docs/?

**A:** Skills are **auto-discovered and invoked by Claude**. Regular docs require user to know they exist and navigate to them. Skills are triggered automatically when relevant.

### Q: Can skills reference each other?

**A:** Yes! Example: code-review skill references testing-workflow for test review patterns. Cross-references create a knowledge graph.

### Q: How do I know if Claude used a skill?

**A:** Claude will mention the skill explicitly when it's particularly relevant (e.g., "According to the code-review skill..."). Otherwise, Claude integrates skill knowledge seamlessly into responses.

### Q: What's the difference between a skill and CLAUDE.md?

**A:**
- **CLAUDE.md**: High-level principles (the WHY) - "Goldilocks Zone" of abstraction
- **Skills**: Detailed patterns (the HOW) - concrete examples and checklists

CLAUDE.md says "fail fast and visibly." The code-review skill shows you 5 specific patterns for how to do that.

---

## Quick Reference

### All Skills at a Glance

**Tier-1 (Modular)**:
1. **testing-workflow** - Test patterns, anti-patterns, defensive testing
2. **telegram-uiux** - Telegram Mini App UI/UX, state management
3. **refacter** - Complexity analysis, hotspot detection, refactoring
4. **deployment** - Zero-downtime deployments, multi-environment
5. **research** - Investigation methodology, research vs iteration
6. **error-investigation** - Multi-layer verification, CloudWatch, Lambda logging
7. **line-uiux** (legacy) - LINE Bot maintenance
8. **code-review** - Security, performance, defensive programming
9. **database-migration** - Schema migrations, reconciliation, MySQL
10. **data-visualization** - Mathematically correct charts, trendlines, overlays
11. **performance-investigation** - Web performance metrics, bottleneck identification
12. **prompt-engineering** - LLM prompt design, few-shot, chain-of-thought
13. **context-engineering** - Semantic layers, token optimization, hallucination prevention
14. **prompt-management** - Langfuse versioning, A/B testing, observability

**Tier-2 (Composed)**:
15. **report-prompt-workflow** - DR report prompt lifecycle (composes 12-14)

### Commands

```bash
# List all skills
ls -1 .claude/skills/

# Find skills with specific content
grep -r "performance" .claude/skills/*/SKILL.md

# Verify all skills have frontmatter
for dir in .claude/skills/*/; do
  echo "Checking $dir"
  head -5 "$dir/SKILL.md" | grep -q "^name:" || echo "  ⚠️ Missing frontmatter"
done
```

---

## Contributing

When adding knowledge to skills:

1. **Extract from real work**: Best patterns come from actual debugging, not theory
2. **Show before/after**: Concrete examples beat abstract principles
3. **Explain the WHY**: Helps people adapt to new situations
4. **Cross-reference**: Link related skills (creates knowledge graph)
5. **Update this README**: Keep skill catalog current

**Remember**: Skills are living documentation. Update them as you learn!
