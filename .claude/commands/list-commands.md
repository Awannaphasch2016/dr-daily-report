---
name: list-commands
description: List all available slash commands grouped by category (metacognitive, workflow, decision, utility, git-worktree)
accepts_args: true
arg_schema:
  - name: quick
    required: false
    description: "Optional: Output only command names grouped by category (compact format)"
    flag: true
composition: []
---

# List Commands

**Purpose**: Display all available slash commands organized by category for easy discovery

**Core Principle**: "Discoverability enables learning" - you can't use what you don't know exists

**When to use**:
- Forgot which command exists for a task
- Looking for the right command
- Onboarding new team members
- Quick reference during development (use `--quick` for compact list)
- Exploring available capabilities

---

## Quick Reference

```bash
/list-commands           # Show all commands grouped by category (detailed)
/list-commands --quick   # Show only command names grouped by category (compact)
```

---

## Command Categories

### Metacognitive Commands (Thinking About Thinking)

**Purpose**: Analyze your own thinking process, detect patterns, improve decision-making

- `/reflect` - Analyze what happened and why you did what you did - metacognitive awareness for detecting stuck patterns
- `/decompose` - Break down goals or failures into components, dependencies, and preconditions (auto-detects mode from content)
- `/hypothesis` - Construct explanations - generate testable hypotheses to explain observations
- `/trace` - Follow causality - trace backward (why did X happen?) or forward (what will X cause?)
- `/compare` - Compare multiple alternatives - alias for /what-if (multi-way comparison mode)
- `/impact` - Assess change scope - understand ripple effects before making changes
- `/what-if` - Explore scenarios, compare alternatives, and analyze relationships between concepts

**When to use**: When stuck, repeating patterns, or need to understand your decision-making process

---

### Workflow Commands (Orchestration & Knowledge Management)

**Purpose**: Capture knowledge, manage workflows, evolve principles over time

- `/journal` - Log architecture decisions, error solutions, patterns, and process improvements with automatic category detection
- `/observe` - Capture execution traces, failure surfaces, and behavioral drift without interpretation (auto-detects mode from context)
- `/abstract` - Extract general patterns, templates, and heuristics from concrete experiences (auto-detects pattern type)
- `/evolve` - Detect drift between documented principles and actual practices, propose updates to skills and CLAUDE.md
- `/report` - Generate markdown summary of work sessions with decisions, problems solved, and next steps
- `/specify` - Create lightweight design specification without entering full plan mode - quick design sketches and alternative explorations

**When to use**: Daily knowledge capture, workflow management, principle evolution

---

### Decision Commands (Analysis Before Action)

**Purpose**: Make informed decisions through systematic exploration and validation

- `/explore` - Systematically explore ALL potential solutions before committing - divergent phase that generates, evaluates, and ranks alternatives
- `/validate` - Validate claims and assumptions with evidence before implementing (auto-detects validation type)
- `/proof` - Construct formal deductive proofs about system properties given constraints and axioms
- `/bug-hunt` - Systematic bug investigation with type-specific workflows for production errors, performance issues, race conditions

**When to use**: Before major architectural choices, when evaluating alternatives, before implementing features

---

### Utility Commands (Information Retrieval & Synthesis)

**Purpose**: Quick information lookup, understanding, and summarization

- `/locate` - Reverse-map from task/feature to implementing files - find where functionality lives in the codebase
- `/explain` - Explain concepts clearly - alias for /understand (focuses on communication step)
- `/understand` - Build mental model and explain concepts - generalizes /explain to include internal understanding
- `/consolidate` - Synthesize knowledge - gather, understand, consolidate, communicate (superset of /summary)
- `/summary` - Summarize information - alias for /consolidate (focuses on communication step)
- `/analysis` - Comprehensive analysis workflow - automates explore → what-if → validate → consolidate chain

**When to use**: Quick lookups, learning concepts, synthesizing scattered information, finding code locations

---

### Git Worktree Commands (Parallel Workflows)

**Purpose**: Manage parallel agent workflows using git worktrees

- `/wt-list` - List all active git worktrees with activity status and cleanup suggestions
- `/wt-spin-off` - Create new branch and git worktree for parallel agent execution
- `/wt-merge` - Merge worktree branch back to dev branch with safety validation
- `/wt-remove` - Remove git worktree directory with safety validation and optional branch deletion

**When to use**: When working on multiple tasks in parallel, experimenting with different approaches

---

### Research Command (Systematic Investigation)

**Purpose**: Deep investigation using research methodology

- `/refactor` - Analyze code complexity and hotspots with actionable refactoring recommendations (auto-detects analysis mode)

**When to use**: Complex bugs, unclear situations, code quality improvement

---

## Execution Flow

### Step 0: Check for --quick Flag

**If --quick flag is present**, use compact output format (see "Output Format - Quick Mode" below)

**If --quick flag is NOT present**, use detailed output format (see "Output Format - Detailed Mode" below)

---

### Step 1: Scan Command Directory

```bash
# Find all command files
COMMANDS_DIR=".claude/commands"
find "$COMMANDS_DIR" -name "*.md" -not -name "README.md" | sort
```

### Step 2: Parse Frontmatter

For each command file:
```bash
# Extract name and description from YAML frontmatter
NAME=$(awk '/^name:/ {print $2; exit}' "$FILE")
DESC=$(awk '/^description:/ {$1=""; print substr($0,2); exit}' "$FILE")
```

### Step 3: Categorize Commands

Commands are organized into 6 categories based on their purpose:

1. **Metacognitive** (7 commands) - Thinking about thinking
2. **Workflow** (6 commands) - Knowledge management
3. **Decision** (4 commands) - Analysis before action
4. **Utility** (6 commands) - Information retrieval
5. **Git Worktree** (4 commands) - Parallel workflows
6. **Research** (1 command) - Systematic investigation

### Step 4: Generate Output

**Detailed Mode** (default):
- Category name and purpose
- Command name + description
- Usage tips

**Quick Mode** (--quick flag):
- Category name only
- Command names as inline list
- No descriptions, no usage tips

---

## Output Format

### Detailed Mode (Default)

```markdown
# Available Slash Commands

## {Category Name} ({Count} commands)

**Purpose**: {Category purpose}

- `/{command-name}` - {description from frontmatter}
- `/{command-name}` - {description}
[...]

**When to use**: {Category usage guidance}
```

---

### Quick Mode (--quick flag)

**Purpose**: Compact command name listing for quick reference

```markdown
# Available Slash Commands (Quick Reference)

**Metacognitive** (7): /reflect /decompose /hypothesis /trace /compare /impact /what-if

**Workflow** (6): /journal /observe /abstract /evolve /report /specify

**Decision** (4): /explore /validate /proof /bug-hunt

**Utility** (6): /locate /explain /understand /consolidate /summary /analysis

**Git Worktree** (4): /wt-list /wt-spin-off /wt-merge /wt-remove

**Research** (1): /refactor

---

**Total**: 29 commands across 6 categories
```

---

## Quick Tips

### By Use Case

**I'm stuck in a loop**:
- `/reflect` - Analyze stuck pattern
- `/trace backward` - Find root cause
- `/decompose` - Break down the problem

**I need to make a decision**:
- `/explore` - Find all alternatives
- `/compare` - Compare options
- `/validate` - Test assumptions
- `/proof` - Prove properties

**I solved something**:
- `/journal` - Document decision/solution
- `/observe` - Capture behavior
- `/abstract` - Extract pattern

**I need information**:
- `/locate` - Find files implementing feature
- `/understand` - Learn concept
- `/consolidate` - Synthesize knowledge
- `/list-commands` - Find right command
- `/list-commands --quick` - Quick command reference (names only)

**I'm working in parallel**:
- `/wt-spin-off` - Create worktree
- `/wt-list` - See all worktrees
- `/wt-merge` - Merge back
- `/wt-remove` - Clean up

---

## Learn More

### Command Details

For detailed documentation on any command:
```bash
# View command file directly
cat .claude/commands/{command-name}.md

# Example
cat .claude/commands/validate.md
cat .claude/commands/explore.md
```

### Command System Overview

```bash
# Read command system documentation
cat .claude/commands/README.md
```

### Skills Documentation

```bash
# See available skills
cat .claude/skills/README.md
```

---

## Examples

### Example 1: Quick Command Listing

**Situation**: "I want to quickly see all available commands without descriptions"

**Usage**:
```bash
/list-commands --quick
```

**Output**:
```
# Available Slash Commands (Quick Reference)

**Metacognitive** (7): /reflect /decompose /hypothesis /trace /compare /impact /what-if

**Workflow** (6): /journal /observe /abstract /evolve /report /specify

**Decision** (4): /explore /validate /proof /bug-hunt

**Utility** (6): /locate /explain /understand /consolidate /summary /analysis

**Git Worktree** (4): /wt-list /wt-spin-off /wt-merge /wt-remove

**Research** (1): /refactor

---

**Total**: 29 commands across 6 categories
```

---

### Example 2: Finding the Right Command

**Situation**: "I want to test if my assumption is correct"

**Answer**: Use `/validate` - validates claims and assumptions with evidence

```bash
/validate "Lambda timeout is caused by API slowness"
```

---

### Example 3: Metacognitive Workflow

**Situation**: Keep trying same approach, not working

**Workflow**:
```bash
/reflect                  # Analyze stuck pattern
  ↓
/trace backward "failure" # Find root cause
  ↓
/hypothesis "observation" # Generate alternatives
  ↓
/validate "new approach"  # Test new hypothesis
```

---

### Example 4: Knowledge Capture Workflow

**Situation**: Just solved a complex problem

**Workflow**:
```bash
/observe failure "Lambda timeout"  # Capture what happened
  ↓
/journal error "Lambda timeout solution"  # Document solution
  ↓
/abstract ".claude/observations/*/failure-*.md"  # Extract pattern
  ↓
/evolve error-handling  # Update principles
```

---

## Statistics

**Total commands**: 29
- Metacognitive: 7
- Workflow: 6
- Decision: 4
- Utility: 6
- Git Worktree: 4
- Research: 1
- Documentation: 1 (README.md)

**Commands with auto-detection**: 12
- observe (mode), journal (category), decompose (mode)
- validate (type), abstract (pattern type), bug-hunt (bug type)
- refactor (analysis mode), explore (criteria)
- hypothesis, trace, what-if, impact

**Commands using research skill**: 16
- Most analysis and workflow commands

**Composition patterns**:
- Empty `[]`: 7 (simple utility commands)
- Single skill: 13
- Multiple skills: 2 (bug-hunt uses 2 skills)
- Commands chain: 6 (aliases like compare → what-if)

---

## Related Commands

- `/list-cli` - List all dr CLI commands
- `/evolve` - Detect when new commands should be added
- `.claude/commands/README.md` - Command system overview

---

## See Also

- `.claude/commands/README.md` - Command system architecture
- `.claude/skills/README.md` - Skills documentation
- `.claude/CLAUDE.md` - Core principles
- `.claude/diagrams/thinking-process-architecture.md` - Thinking process design
