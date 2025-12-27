# Exploration: Skills vs MCP - Modularity Principles

**Date**: 2025-12-25
**Focus**: Comprehensive (understanding underlying patterns)
**Status**: Complete

---

## Problem Decomposition

**Goal**: Understand why browser-use is a skill rather than MCP tools, and the underlying principles/patterns that make rules/constraints/guidelines in Claude modular and easy to maintain.

### Core Questions

1. **What is the fundamental difference** between Skills and MCP tools?
2. **Why is browser-use implemented as a skill** instead of MCP?
3. **What principles determine** when to use Skills vs MCP vs other mechanisms?
4. **How do these principles** apply to making guidelines modular and maintainable?

### Current Understanding (Hypothesis)

**Initial hypothesis**: The choice between Skills and MCP is about **knowledge vs connectivity**:
- Skills = "How to do something" (procedural knowledge, workflows)
- MCP = "Access to do something" (connectivity, external systems)

### Success Criteria

**Understanding achieved when**:
- ✅ Can explain why browser-use is a skill (not MCP)
- ✅ Can identify the underlying pattern (knowledge vs access)
- ✅ Can apply principles to organize documentation
- ✅ Can determine when new content should be skill vs guideline vs tool

---

## Solution Space: Organizing Claude's Knowledge

Based on research, there are **distinct mechanisms** for extending Claude's capabilities:

### Option 1: Skills (Procedural Knowledge)

**Description**: Auto-discovered markdown files with instructions, scripts, and workflows

**What they are**:
- Markdown files in `.claude/skills/{name}/SKILL.md`
- Instructions for "how to do something"
- Auto-loaded by Claude when relevant
- Can include embedded scripts, examples, resources
- **Discovered dynamically** (Claude finds relevant skills)

**Structure**:
```
.claude/skills/browser-use/
├── SKILL.md         # Instructions for browser automation
├── examples/        # Example workflows
└── scripts/         # Helper scripts
```

**When to use**:
- ✅ Automating well-defined workflows (corporate style, SOPs)
- ✅ Domain knowledge that should apply automatically
- ✅ "How to" knowledge (formatting, analysis procedures)
- ✅ Context that Claude should discover and apply
- ✅ Combining multiple tools into a workflow

**Examples**:
- `browser-use`: How to automate browser workflows
- `excel-processor`: How to read/write Excel with formulas
- `meeting-prep`: How to prepare meeting documents from Notion

**Pros**:
- ✅ Auto-discovery (Claude finds when needed)
- ✅ Encapsulates complete workflows
- ✅ Can orchestrate multiple MCP tools
- ✅ Version-controlled knowledge
- ✅ Self-contained (instructions + scripts + examples)

**Cons**:
- ❌ No external system access (need MCP for that)
- ❌ Markdown-based (not programmatic API)
- ❌ Requires Claude to interpret instructions

---

### Option 2: MCP Tools (Connectivity)

**Description**: Standardized protocol for connecting Claude to external systems

**What they are**:
- Server processes exposing tools via MCP protocol
- Access to external systems (APIs, databases, files)
- Tools Claude can **invoke** (not instructions to follow)
- **Programmatic interface** (not natural language)

**Structure**:
```
MCP Server:
├── Tools (functions Claude can call)
│   ├── github_create_issue()
│   ├── notion_search()
│   └── database_query()
└── Resources (data Claude can access)
```

**When to use**:
- ✅ Accessing external systems (GitHub, Notion, databases)
- ✅ Performing actions (create issue, send email, update calendar)
- ✅ Reading data (query database, search files)
- ✅ System integration (file operations, API calls)

**Examples**:
- GitHub MCP: Create issues, PRs, search code
- Notion MCP: Search workspace, create pages
- Database MCP: Query, update records
- File System MCP: Read, write, search files

**Pros**:
- ✅ Direct system access (secure, controlled)
- ✅ Programmatic API (type-safe, validated)
- ✅ Reusable across workflows
- ✅ Can be combined by Skills

**Cons**:
- ❌ No procedural knowledge (just access)
- ❌ Requires separate server process
- ❌ Doesn't tell Claude "how to use it"

---

### Option 3: System Prompts (Global Context)

**Description**: Instructions in CLAUDE.md or system prompt that apply to all conversations

**What they are**:
- Markdown file read at conversation start
- Global principles and constraints
- Always active (not conditional)

**Structure**:
```
.claude/CLAUDE.md
├── Core Principles (always apply)
├── Code Style Guidelines
├── Testing Philosophy
└── When Adding Features
```

**When to use**:
- ✅ Fundamental principles (never violate)
- ✅ Code style and standards
- ✅ Project-wide conventions
- ✅ "Contract" that must always hold

**Examples**:
- Testing guidelines
- Defensive programming principles
- Type safety requirements
- Error handling patterns

**Pros**:
- ✅ Always active (no discovery needed)
- ✅ Simple (just markdown)
- ✅ Central location (easy to find)

**Cons**:
- ❌ Always loaded (increases context size)
- ❌ Not conditional (applies to everything)
- ❌ Can't be turned off per-task

---

### Option 4: Commands (User-Invocable Workflows)

**Description**: Explicit workflows users invoke with `/command`

**What they are**:
- Markdown files with YAML frontmatter
- User-invoked (not auto-discovered)
- Structured workflows with arguments

**Structure**:
```
.claude/commands/explore.md
---
name: explore
accepts_args: true
arg_schema:
  - name: goal
    required: true
---
# Instructions for exploration workflow
```

**When to use**:
- ✅ User-driven workflows (explicit invocation)
- ✅ Structured processes (journal, validate, explore)
- ✅ Multi-step procedures users control

**Examples**:
- `/explore` - Divergent solution exploration
- `/validate` - Claim validation
- `/journal` - Document decisions

**Pros**:
- ✅ User control (explicit invocation)
- ✅ Structured arguments
- ✅ Clear workflow boundaries

**Cons**:
- ❌ Requires user to know command exists
- ❌ Not auto-discovered
- ❌ Can't orchestrate external tools (need Skills+MCP for that)

---

### Option 5: Documentation (Reference Material)

**Description**: Detailed guides, runbooks, and reference documentation

**What they are**:
- Markdown files in `docs/`
- Deep dives, examples, explanations
- Read on-demand (not always loaded)

**Structure**:
```
docs/
├── deployment/
├── architecture/
├── testing/
└── guides/
```

**When to use**:
- ✅ Detailed explanations (deep dives)
- ✅ Reference material (look up when needed)
- ✅ Human-readable documentation
- ✅ Context that's too large for system prompt

**Examples**:
- Deployment runbooks
- Architecture decision records (ADRs)
- Testing patterns and anti-patterns

**Pros**:
- ✅ Unlimited size (not constrained by context)
- ✅ Human-readable
- ✅ Can be very detailed

**Cons**:
- ❌ Not auto-discovered
- ❌ Requires explicit reference
- ❌ Can become stale

---

## Why Browser-Use is a Skill (Not MCP)

### Analysis

**browser-use** is implemented as a **Skill** because:

1. **It's procedural knowledge**, not connectivity
   - Teaches Claude *how to* automate browser workflows
   - Not just "here's a tool" but "here's how to use the browser"

2. **It orchestrates multiple actions** into workflows
   - Multi-step: Navigate → Fill form → Submit → Verify
   - Requires decision-making at each step
   - Not a single API call

3. **It requires domain knowledge**
   - When to click vs type
   - How to wait for page loads
   - How to handle errors and retries
   - Form filling patterns

4. **Auto-discovery is valuable**
   - Claude should apply browser automation when relevant
   - User shouldn't need to invoke explicitly
   - Activates when task requires browser interaction

### If browser-use were MCP...

**Problems with MCP approach**:
```
# MCP would provide tools like:
- browser.click(selector)
- browser.type(selector, text)
- browser.navigate(url)

# But no knowledge of:
- WHEN to use each tool
- HOW to combine them into workflows
- WHAT patterns work for form filling
- HOW to handle errors
```

**Result**: Claude would have tools but not know how to use them effectively

### Hybrid Approach (Best Practice)

**Browser automation could use BOTH**:
```
MCP Server: browser-automation
├── Tools:
│   ├── navigate(url)
│   ├── click(selector)
│   ├── type(selector, text)
│   └── screenshot()

Skill: browser-use
├── SKILL.md (how to automate workflows)
├── Uses MCP tools above
└── Orchestrates multi-step procedures
```

**Skill wraps MCP**: The skill knows *how to use* the MCP tools to accomplish workflows.

---

## Underlying Principles for Modularity

### Principle 1: Separation of Connectivity and Knowledge

**The Core Pattern**:
```
MCP        = "I can access X"   (connectivity)
Skill      = "I know how to Y"  (knowledge)
Skill+MCP  = "I know how to Y using X"
```

**Example - Meeting Prep**:
```
MCP (Notion):     Can search Notion workspace
Skill (meeting-prep):  Knows which pages to pull, how to format

Result: Automated meeting prep workflow
```

**Why this matters**:
- MCP tools are reusable (many skills can use same MCP)
- Skills are composable (one skill can use multiple MCPs)
- Knowledge separate from access (can update independently)

---

### Principle 2: Layer by Change Frequency

**Stability Hierarchy** (most stable → most volatile):

```
1. System Prompts (CLAUDE.md)
   - Core principles (quarterly changes)
   - Project conventions
   - Foundational rules

2. Skills
   - Domain workflows (monthly changes)
   - Procedural knowledge
   - Best practices

3. MCP Tools
   - External system access (as needed)
   - API integrations
   - Platform-specific

4. Commands
   - User workflows (weekly changes)
   - Process automation
   - Task templates

5. Documentation (docs/)
   - Reference material (continuous updates)
   - Detailed guides
   - Examples
```

**Benefit**: Change one layer without affecting others

---

### Principle 3: Scope of Applicability

**When should Claude apply this knowledge?**

| Mechanism | Scope | Activation |
|-----------|-------|------------|
| **System Prompt** | Always (global) | Automatic |
| **Skills** | When relevant (contextual) | Auto-discovered |
| **Commands** | When invoked (explicit) | User-triggered |
| **MCP** | When accessed (on-demand) | Called by Claude/Skills |
| **Docs** | When referenced (manual) | Explicitly read |

**Pattern**: Match scope to intent
- Global rules → System Prompt
- Domain knowledge → Skills
- User workflows → Commands
- External access → MCP
- Deep references → Docs

---

### Principle 4: Single Responsibility

**Each mechanism has one job**:

- **CLAUDE.md**: Contract (what must always be true)
- **Skills**: Workflows (how to accomplish tasks)
- **MCP**: Connectivity (access to external systems)
- **Commands**: User control (explicit orchestration)
- **Docs**: Reference (detailed explanations)

**Anti-pattern**: Mixing responsibilities
```
❌ BAD: Putting MCP connection details in CLAUDE.md
❌ BAD: Putting core principles in a skill
❌ BAD: Putting workflows in documentation
```

**Pattern**: Right tool for the job
```
✅ GOOD: Core principles in CLAUDE.md
✅ GOOD: Workflows in skills
✅ GOOD: External access via MCP
✅ GOOD: User workflows as commands
✅ GOOD: Deep dives in docs/
```

---

### Principle 5: Modularity Through Composition

**Layered Architecture**:

```
User Invokes Command (/explore)
    ↓
Command Uses Skill (research)
    ↓
Skill Uses MCP Tools (web-search, file-read)
    ↓
MCP Accesses External Systems (APIs, files)
```

**Each layer is modular**:
- Commands compose skills
- Skills compose MCP tools
- MCP tools access systems
- Each can change independently

**Example - Code Review Workflow**:
```
Command: /code-review
    ↓
Skill: code-review-workflow
    Uses: testing-workflow skill
    Uses: github MCP (read PR files)
    Uses: file-system MCP (read local files)
    ↓
Produces: Review comments
```

---

## Evaluation Matrix

**Focus**: Maintainability

| Criterion | System Prompt | Skills | MCP | Commands | Docs |
|-----------|---------------|--------|-----|----------|------|
| **Modularity** | 5/10 | 9/10 | 9/10 | 8/10 | 7/10 |
| **Discoverability** | 10/10 | 8/10 | 6/10 | 7/10 | 5/10 |
| **Maintainability** | 6/10 | 9/10 | 8/10 | 8/10 | 7/10 |
| **Composability** | 3/10 | 9/10 | 9/10 | 7/10 | 4/10 |
| **Scope Control** | 3/10 | 9/10 | 8/10 | 9/10 | 7/10 |
| **Total** | **27** | **44** | **40** | **39** | **30** |

### Scoring Rationale

**System Prompt (27/50)**:
- Modularity 5/10: Monolithic, all or nothing
- Discoverability 10/10: Always active
- Maintainability 6/10: Changes affect everything
- Composability 3/10: Can't compose with other prompts
- Scope Control 3/10: Always applies (no filtering)

**Skills (44/50)** ⭐:
- Modularity 9/10: Each skill is independent
- Discoverability 8/10: Auto-discovered by Claude
- Maintainability 9/10: Update one skill, no ripples
- Composability 9/10: Skills can use other skills + MCP
- Scope Control 9/10: Activated when relevant

**MCP (40/50)**:
- Modularity 9/10: Tools are independent
- Discoverability 6/10: Must be called explicitly
- Maintainability 8/10: Tool changes don't affect others
- Composability 9/10: Tools can be combined
- Scope Control 8/10: Called on-demand

**Commands (39/50)**:
- Modularity 8/10: Independent workflows
- Discoverability 7/10: User must know they exist
- Maintainability 8/10: Update one command
- Composability 7/10: Can use skills, limited composition
- Scope Control 9/10: User-controlled invocation

**Docs (30/50)**:
- Modularity 7/10: Files are independent
- Discoverability 5/10: Must be referenced explicitly
- Maintainability 7/10: Can become stale
- Composability 4/10: Just reference material
- Scope Control 7/10: Read on-demand

---

## Ranked Recommendations

### 1. Use Skills for Domain Knowledge (44/50) ⭐

**When to create a Skill**:
- ✅ Automating well-defined workflows
- ✅ Domain-specific knowledge (how to format, how to analyze)
- ✅ Knowledge that should apply contextually
- ✅ Workflows that orchestrate multiple tools
- ✅ Best practices for specific domains

**Examples from this project**:
```
.claude/skills/
├── testing-workflow/     # How to write tests
├── deployment/           # How to deploy safely
├── error-investigation/  # How to debug AWS issues
├── code-review/          # How to review code
└── telegram-uiux/        # How to build Telegram UI
```

**Why this is optimal**:
- Auto-discovered (Claude finds when relevant)
- Modular (one skill = one domain)
- Composable (skills can use other skills + MCP)
- Maintainable (update skill, no global impact)

**Trade-off**: Requires discipline to keep skills focused (single responsibility)

---

### 2. Use MCP for External System Access (40/50)

**When to create MCP tools**:
- ✅ Need to access external systems (GitHub, databases, APIs)
- ✅ Performing actions (create, update, delete)
- ✅ Reading data from external sources
- ✅ Secure, controlled access required

**Examples**:
```
MCP Servers:
├── github (create issues, PRs, search code)
├── aws (query CloudWatch, Lambda config)
├── database (query Aurora via SSM tunnel)
└── notion (search workspace, create pages)
```

**Why this is second**:
- Reusable (many skills can use same MCP)
- Secure (controlled access to systems)
- BUT: Doesn't provide procedural knowledge

**Use with Skills**: Skill knows *how to use* MCP tools

---

### 3. Use Commands for User-Driven Workflows (39/50)

**When to create Commands**:
- ✅ User should control invocation (not automatic)
- ✅ Structured multi-step processes
- ✅ Workflows with specific arguments
- ✅ Explicit orchestration needed

**Examples from this project**:
```
.claude/commands/
├── explore.md    # User-driven solution exploration
├── validate.md   # User-driven claim validation
├── journal.md    # User-driven documentation
└── bug-hunt.md   # User-driven investigation
```

**Why this is third**:
- User control (explicit, predictable)
- Structured (clear inputs/outputs)
- BUT: Requires user awareness (must know command exists)

---

### 4. Use System Prompt for Core Principles (27/50)

**When to put in CLAUDE.md**:
- ✅ Fundamental principles (never violate)
- ✅ Project-wide conventions
- ✅ Core "contract" that always applies
- ✅ Navigation/index to other mechanisms

**Keep CLAUDE.md**:
- Core principles (10-20 lines each)
- Links to detailed docs
- Extension points (where to add new content)
- **Total: 150-200 lines**

**Why this is fourth**:
- Always active (good for fundamental rules)
- BUT: Limited modularity, affects everything

---

### 5. Use Docs for Reference Material (30/50)

**When to create docs/**:
- ✅ Detailed explanations (deep dives)
- ✅ Runbooks (step-by-step procedures)
- ✅ Architecture documentation (ADRs)
- ✅ Examples and tutorials

**Why this is last**:
- Good for humans
- BUT: Not auto-discovered by Claude
- Requires explicit reference

---

## Applying Principles to This Project

### Current State Analysis

**What we have**:
```
.claude/
├── CLAUDE.md (622 lines - TOO LARGE)
├── skills/ (12 skills - GOOD)
└── commands/ (19 commands - GOOD)

docs/ (94 files - GOOD)
```

**Problems**:
- CLAUDE.md too large (should be 150-200 lines)
- Unclear when to add to CLAUDE.md vs skills vs docs

### Recommended Structure

Based on the principles explored:

```
.claude/
├── CLAUDE.md (150 lines)
│   ├── Core Principles (always apply)
│   └── Links to principles/, patterns/, guides/
│
├── principles/        # Stable (quarterly updates)
│   ├── testing.md
│   ├── defensive-programming.md
│   └── type-safety.md
│
├── patterns/          # Semi-stable (monthly updates)
│   ├── state-management.md
│   ├── retry-fallback.md
│   └── validation-gates.md
│
├── guides/            # Volatile (weekly updates)
│   ├── adding-features.md
│   ├── code-review.md
│   └── debugging.md
│
├── skills/            # Auto-discovered workflows
│   ├── testing-workflow/
│   ├── deployment/
│   └── error-investigation/
│
└── commands/          # User-invocable
    ├── explore.md
    ├── validate.md
    └── journal.md
```

**Decision tree** for new content:

```
New content to add?
    │
    ├─ Does it provide external system access?
    │  YES → Create MCP tool
    │  NO  → Continue
    │
    ├─ Should it apply automatically when relevant?
    │  YES → Create Skill
    │  NO  → Continue
    │
    ├─ Should user invoke explicitly?
    │  YES → Create Command
    │  NO  → Continue
    │
    ├─ Must it ALWAYS apply?
    │  YES → Add to CLAUDE.md (or principles/)
    │  NO  → Continue
    │
    └─ Is it detailed reference material?
       YES → Add to docs/
```

---

## Resources Gathered

### Official Documentation

- [Skills explained: How Skills compares to prompts, Projects, MCP, and subagents](https://claude.com/blog/skills-explained)
  - Comprehensive comparison of all extension mechanisms
  - When to use each approach

- [Extending Claude's capabilities with skills and MCP](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
  - How Skills and MCP work together
  - Complementary, not competitive

- [What are Skills? - Claude Help Center](https://support.claude.com/en/articles/12512176-what-are-skills)
  - Official definition and usage
  - Installation and discovery

### Technical Analysis

- [Skills vs Dynamic MCP Loadouts - Armin Ronacher](https://lucumr.pocoo.org/2025/12/13/skills-vs-mcp/)
  - Deep technical comparison
  - Architecture patterns

- [Claude Skills vs. MCP: A Technical Comparison - IntuitionLabs](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
  - Decision framework
  - When to use each

- [Understanding Claude Code's Full Stack - alexop.dev](https://alexop.dev/posts/understanding-claude-code-full-stack/)
  - MCP, Skills, Subagents, Hooks
  - Complete architecture

### Community Insights

- [Claude Skills are awesome, maybe a bigger deal than MCP - Simon Willison](https://simonwillison.net/2025/Oct/16/claude-skills/)
  - Simplicity and power of Skills
  - Real-world examples

---

## Next Steps

```bash
# Apply the hybrid layered approach with clear mechanism boundaries
/specify "Modular Documentation Architecture with Skills, MCP, Commands"

# Or validate the current pain point
/validate "CLAUDE.md is too large and should be modularized"

# Or compare approaches
/what-if "use Skills for all guidelines vs layered CLAUDE.md approach"
```

---

## Conclusion

**Key Insights**:

1. **browser-use is a Skill because it's procedural knowledge** (how to automate browsers), not just connectivity

2. **The fundamental pattern is**:
   - MCP = "I can access X" (connectivity)
   - Skills = "I know how to Y" (knowledge)
   - Skills + MCP = "I know how to Y using X"

3. **Modularity comes from layering**:
   ```
   CLAUDE.md → Principles → Patterns → Guides → Skills → MCP
   (stable)    (quarterly)  (monthly)  (weekly)  (contextual) (on-demand)
   ```

4. **Each mechanism has distinct purpose**:
   - CLAUDE.md: Core contract
   - Principles: Foundational truths
   - Patterns: Reusable solutions
   - Guides: Tactical how-tos
   - Skills: Auto-discovered workflows
   - MCP: External system access
   - Commands: User-driven processes
   - Docs: Reference material

**Recommendation**: Use the **layered approach** from previous exploration, enhanced with understanding of Skills vs MCP distinction.

---

## Sources

- [Introducing Agent Skills | Claude](https://www.anthropic.com/news/skills)
- [Skills explained: How Skills compares to prompts, Projects, MCP, and subagents](https://claude.com/blog/skills-explained)
- [Extending Claude's capabilities with skills and MCP](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
- [Skills vs Dynamic MCP Loadouts | Armin Ronacher](https://lucumr.pocoo.org/2025/12/13/skills-vs-mcp/)
- [Claude Skills vs. MCP: A Technical Comparison | IntuitionLabs](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
- [Understanding Claude Code's Full Stack | alexop.dev](https://alexop.dev/posts/understanding-claude-code-full-stack/)
- [Claude Skills are awesome, maybe a bigger deal than MCP | Simon Willison](https://simonwillison.net/2025/Oct/16/claude-skills/)
