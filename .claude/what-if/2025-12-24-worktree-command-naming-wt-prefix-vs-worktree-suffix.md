---
title: Worktree command naming - wt-* prefix vs *-worktree suffix
date: 2025-12-24
assumption_type: modification
status: analyzed
recommendation: yes
---

# What-If Analysis: wt-* Prefix vs *-worktree Suffix

## Assumption

**What if we use `wt-*` prefix instead of `*-worktree` suffix for worktree commands?**

**Proposed changes**:
```bash
# OLD (suffix pattern)
/spin-off-worktree → /wt-spin-off
/list-worktree     → /wt-list
/cleanup-worktree  → /wt-merge + /wt-remove
```

**Rationale**:
1. **Grouping by syntax**: Prefix groups related commands (all `wt-*` together)
2. **Shorter names**: `wt-` vs `-worktree` (less typing)
3. **Semantic clarity**: Split "cleanup" into explicit "merge" and "remove" operations
4. **Namespace organization**: Like git's `worktree add`, `worktree list`, etc.

---

## Current Reality

**Current naming pattern**: Action-Object suffix
- Examples: `/observe-failure`, `/decompose-goal`, `/abstract-pattern`
- Pattern: `/{verb}-{object}` or `/{verb}`
- Grouping: By action type (observe, decompose, abstract)

**Existing commands** (from README.md):
```bash
# Core
/journal, /validate, /proof

# Exploration
/what-if, /specify

# Meta-Operations
/observe, /decompose, /abstract, /report, /evolve

# Debugging
/bug-hunt

# Code Quality
/refactor

# Demos
/explain
```

**Pattern observation**:
- Most commands: Single verb (`/journal`, `/validate`, `/refactor`)
- Some commands: Compound (`/bug-hunt`, `/what-if`)
- **None use prefix grouping** (no `/git-*`, `/db-*`, `/aws-*`)

---

## Under New Assumption: wt-* Prefix Pattern

### What Changes Immediately

**Command naming**:
```bash
# Proposed worktree commands
/wt-spin-off "task description"   # Create worktree + branch
/wt-list                           # List all worktrees
/wt-merge "worktree-name"          # Merge worktree branch to dev
/wt-remove "worktree-name"         # Remove worktree directory
```

**Namespace organization**:
```bash
# All worktree commands grouped alphabetically
/wt-list
/wt-merge
/wt-remove
/wt-spin-off

# vs scattered (suffix pattern)
/list-worktree
/merge-worktree
/remove-worktree
/spin-off-worktree
```

**Autocomplete behavior**:
```bash
# Type /wt<TAB> → shows all worktree commands
/wt-list
/wt-merge
/wt-remove
/wt-spin-off

# vs Type /spin<TAB> → mixed results
/spin-off-worktree
... (other /spin-* commands if any)
```

---

### Cascading Effects

**Level 1 (Direct)**:
- ✅ **Shorter command names**: `/wt-list` (8 chars) vs `/list-worktree` (14 chars)
- ✅ **Clear namespace**: All worktree operations under `wt-*`
- ✅ **Semantic split**: "cleanup" → "merge" + "remove" (explicit operations)
- ⚠️ **Pattern inconsistency**: Breaks from existing single-verb convention

**Level 2 (Discoverability)**:
- ✅ **Easier to find**: Type `/wt` to see all worktree commands
- ✅ **Mental model**: "wt-* = worktree operations" (clear grouping)
- ⚠️ **Learning curve**: New pattern different from existing commands

**Level 3 (Extensibility)**:
- ✅ **Easy to add**: New worktree commands naturally fit (`/wt-switch`, `/wt-prune`)
- ⚠️ **Precedent set**: Might encourage other namespaces (`/db-*`, `/aws-*`, `/git-*`)
- ⚠️ **Namespace pollution**: If extended too far, loses simplicity

---

### Components Affected

**Command files**:
```
.claude/commands/
├── wt-spin-off.md    # NEW
├── wt-list.md        # NEW
├── wt-merge.md       # NEW
├── wt-remove.md      # NEW
└── README.md         # Update with wt-* section
```

**Documentation**:
```markdown
# In README.md
## Worktree Management (wt-*)

### `/wt-spin-off` - Create Worktree for Parallel Work
### `/wt-list` - List Active Worktrees
### `/wt-merge` - Merge Worktree Branch
### `/wt-remove` - Remove Worktree Directory
```

**User mental model**:
- **Current**: Commands are actions (`/validate`, `/refactor`, `/bug-hunt`)
- **New**: Some commands are namespaced actions (`/wt-list`, `/wt-merge`)
- **Hybrid**: Both patterns coexist

---

## What Breaks

### Pattern Consistency

**Problem**: Introduces new naming pattern
- **Current**: All commands use action-focused names
- **New**: Worktree commands use namespace prefix
- **Inconsistency**: Why `wt-*` but not `/git-*`, `/db-*`, `/aws-*`?

**Example tension**:
```bash
# Worktree (namespaced)
/wt-list        # List worktrees

# Git (not namespaced - hypothetical)
/list-branches  # Why not /git-list-branches?
/list-commits   # Why not /git-list-commits?

# AWS (not namespaced)
/check-lambda   # Why not /aws-check-lambda?
```

**Impact**: Medium (creates precedent, may lead to namespace proliferation)

---

### Discoverability Trade-off

**Problem**: Harder to discover by action
- **Current pattern**: Think action-first ("I want to list something" → search for `/list*`)
- **New pattern**: Must know namespace ("I want worktree operations" → `/wt*`)

**Example**:
```bash
# User wants to "list things"
# Current: /list-worktree (action-first, discoverable)
# New: /wt-list (namespace-first, must know wt-* exists)
```

**Impact**: Low (worktree is specialized, users know what they want)

---

## What Improves

### Namespace Clarity ✅

**Benefit**: Clear grouping of related operations
```bash
# All worktree commands together
/wt-list        # See what's active
/wt-merge       # Integrate work
/wt-remove      # Clean up
/wt-spin-off    # Create new
```

**Value**: **High** (mental model: "wt-* = worktree management")

---

### Shorter, Cleaner Names ✅

**Benefit**: Less typing, easier to remember
```bash
# Before (suffix)
/spin-off-worktree "task"   # 18 chars + task
/list-worktree              # 14 chars
/merge-worktree "name"      # 15 chars + name
/remove-worktree "name"     # 16 chars + name

# After (prefix)
/wt-spin-off "task"         # 12 chars + task (-33%)
/wt-list                    # 8 chars (-43%)
/wt-merge "name"            # 9 chars + name (-40%)
/wt-remove "name"           # 10 chars + name (-38%)
```

**Value**: **Medium** (convenience, but not critical)

---

### Semantic Clarity ✅

**Benefit**: "cleanup" split into explicit operations

**Before** (ambiguous):
```bash
/cleanup-worktree "name"
# Does this merge? Remove? Both? Neither?
```

**After** (explicit):
```bash
/wt-merge "name"    # Merge branch to dev
/wt-remove "name"   # Remove worktree directory

# User decides the order
/wt-merge "name" && /wt-remove "name"   # Merge then remove
/wt-remove "name"                       # Remove without merging (discard work)
```

**Value**: **High** (clear intent, user control)

---

### Extensibility ✅

**Benefit**: Easy to add future worktree operations
```bash
# Natural extensions
/wt-switch "name"    # Switch to different worktree
/wt-prune            # Remove stale worktrees
/wt-lock "name"      # Prevent accidental removal
/wt-unlock "name"    # Allow removal
```

**Value**: **Medium** (future-proofing)

---

## Insights Revealed

### Assumptions Exposed

**1. Command naming is purely action-first**
- **Hidden assumption**: "All commands should be verbs or action phrases"
- **Evidence**: Introducing `wt-*` reveals we can group by domain
- **Criticality**: Low (naming is flexible, not rigid constraint)

**2. Namespaces would proliferate**
- **Fear**: "If wt-*, then git-*, db-*, aws-*..."
- **Reality**: Depends on discipline (can limit to wt-* only)
- **Mitigation**: Document when namespaces are appropriate

---

### Trade-offs Clarified

**1. Discoverability vs Organization**
- **Action-first** (`/list-worktree`): Better for action-based discovery
- **Namespace-first** (`/wt-list`): Better for domain-based discovery
- **Trade-off**: Worktree users know domain (wt-*), so namespace wins

**2. Brevity vs Clarity**
- **Longer names** (`/spin-off-worktree`): Self-documenting
- **Shorter names** (`/wt-spin-off`): Requires knowing `wt = worktree`
- **Trade-off**: `wt` is clear enough abbreviation (like `git wt`)

---

### Boundary Conditions

**When to use namespace prefix**:
- **Multiple related commands** (4+ commands in same domain)
- **Clear domain abbreviation** (wt = worktree, unambiguous)
- **Specialized use case** (not all users need all worktree commands)

**When NOT to use namespace prefix**:
- **Single command** (no grouping benefit)
- **Ambiguous abbreviation** (what's "db"? database? debug?)
- **Core workflow** (all users need it, should be top-level)

---

### Design Rationale

**Why `wt-*` makes sense**:
1. **Git precedent**: Git uses `git worktree add|list|remove` (namespace pattern)
2. **Specialized domain**: Worktree operations are distinct from general workflow
3. **Multiple commands**: 4 commands justify namespace
4. **Clear abbreviation**: `wt` = worktree (unambiguous)

**Why `/cleanup-worktree` → `/wt-merge` + `/wt-remove` is better**:
1. **Single responsibility**: Each command does ONE thing
2. **User control**: User decides merge vs discard
3. **Composability**: Can combine or use separately
4. **Semantic clarity**: No ambiguity about what happens

---

## Recommendation

### Should We Use wt-* Prefix?

**Decision**: ✅ **YES**

**Rationale**:
1. ✅ **Namespace clarity**: All worktree commands grouped under `wt-*`
2. ✅ **Shorter names**: 33-43% fewer characters
3. ✅ **Semantic clarity**: Split "cleanup" into explicit "merge" and "remove"
4. ✅ **Git precedent**: Mirrors `git worktree` subcommand structure
5. ⚠️ **Pattern deviation**: Acceptable for specialized domain

**Proposed commands**:
```bash
/wt-spin-off "description"   # Create branch + worktree
/wt-list                     # List all active worktrees
/wt-merge "name"             # Merge worktree branch to dev
/wt-remove "name"            # Remove worktree directory
```

---

### Action Items

**Implementation**:
- [ ] Create `/wt-spin-off` command (replaces `/spin-off-worktree`)
- [ ] Create `/wt-list` command (replaces `/list-worktree`)
- [ ] Create `/wt-merge` command (new, replaces half of `/cleanup-worktree`)
- [ ] Create `/wt-remove` command (new, replaces half of `/cleanup-worktree`)
- [ ] Add "Worktree Management (wt-*)" section to README.md
- [ ] Document when to use namespace prefixes (in command design guidelines)

**Documentation**:
```markdown
## Worktree Management (wt-*)

**Purpose**: Manage parallel worktrees for concurrent agent execution

**Commands**:
- `/wt-spin-off` - Create new branch + worktree
- `/wt-list` - List active worktrees
- `/wt-merge` - Merge worktree branch to dev
- `/wt-remove` - Remove worktree directory

**Pattern note**: Worktree commands use namespace prefix (wt-*) to group
related operations. This is an exception to the general action-verb pattern,
justified by the specialized domain and multiple related commands.
```

---

### Guidelines for Future Namespaces

**When to create a namespace prefix** (prevent proliferation):
1. **4+ related commands** in same domain
2. **Clear, unambiguous abbreviation** (2-4 letters)
3. **Specialized use case** (not all users need all commands)
4. **Existing precedent** (git uses subcommands, aws-cli uses service names)

**Examples**:
- ✅ `wt-*` - Worktree management (4 commands, clear abbreviation, specialized)
- ❌ `git-*` - Too broad (would need `/git-commit`, `/git-push`, etc.)
- ❌ `db-*` - Ambiguous (database? debug? dashboard?)
- ⚠️ `mcp-*` - Possible if we add 4+ MCP server management commands

---

## Comparison: Old vs New

### Naming Comparison

| Operation | Old (Suffix) | New (Prefix) | Char Savings |
|-----------|-------------|--------------|--------------|
| Create worktree | `/spin-off-worktree` | `/wt-spin-off` | -6 chars (-33%) |
| List worktrees | `/list-worktree` | `/wt-list` | -6 chars (-43%) |
| Merge branch | `/cleanup-worktree` | `/wt-merge` | -9 chars (-56%) |
| Remove directory | (same command) | `/wt-remove` | N/A (new split) |

---

### Semantic Comparison

**Old**: `/cleanup-worktree "name"`
- **Ambiguous**: Does it merge? Remove? Both?
- **User confusion**: What exactly happens?
- **No control**: User can't choose merge vs discard

**New**: `/wt-merge "name"` + `/wt-remove "name"`
- **Explicit**: Clear what each does
- **User control**: Decide merge vs discard
- **Composable**: Use together or separately

---

### Workflow Comparison

**Old workflow** (ambiguous cleanup):
```bash
/spin-off-worktree "fix timeout bug"
# ... work in worktree ...
/cleanup-worktree "fix-timeout-bug"
# What happened? Merged? Removed? Both?
```

**New workflow** (explicit control):
```bash
/wt-spin-off "fix timeout bug"
# ... work in worktree ...

# Option 1: Merge and keep
/wt-merge "fix-timeout-bug"
# Branch merged to dev, worktree still exists

# Option 2: Merge and remove
/wt-merge "fix-timeout-bug"
/wt-remove "fix-timeout-bug"
# Branch merged, worktree removed

# Option 3: Discard work
/wt-remove "fix-timeout-bug"
# Worktree removed, branch not merged (discarded)
```

---

## Follow-Up

**Specify the commands**:
```bash
/specify "/wt-spin-off command - create branch and worktree"
/specify "/wt-list command - list active worktrees"
/specify "/wt-merge command - merge worktree branch to dev"
/specify "/wt-remove command - remove worktree directory"
```

**Document the pattern**:
```bash
/journal architecture "wt-* namespace pattern for worktree commands"
```

**Validate user acceptance**:
```bash
/validate "wt-* prefix is clearer than *-worktree suffix for users"
```

---

## Conclusion

**The `wt-*` prefix pattern is superior**:
1. ✅ Shorter (33-43% fewer characters)
2. ✅ Clearer namespace (all worktree ops grouped)
3. ✅ Semantic precision (merge vs remove explicit)
4. ✅ Git precedent (`git worktree` subcommands)
5. ✅ Extensible (easy to add `/wt-switch`, `/wt-prune`)

**Acceptable trade-off**:
- ⚠️ Deviates from action-verb pattern
- ✅ But justified for specialized domain with multiple related commands

**Recommendation**: Implement `wt-*` pattern with discipline (don't let namespaces proliferate without justification).
