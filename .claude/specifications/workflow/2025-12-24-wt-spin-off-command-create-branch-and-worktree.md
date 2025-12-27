---
title: /wt-spin-off command - create branch and worktree
focus: workflow
date: 2025-12-24
status: approved
---

# Specification: /wt-spin-off Command

## Purpose

Create a new branch and git worktree for parallel agent execution. Enables multiple agents to work on different tasks simultaneously without file conflicts.

## Use Case

**Problem**: Multiple agents need to work on different tasks in the same repository simultaneously.

**Current Limitation**: Single working directory means agents must work sequentially or risk file conflicts.

**Solution**: Git worktrees provide isolated working directories sharing the same .git database.

**Workflow**:
```bash
# Terminal 1: Agent investigating bug
/wt-spin-off "investigate lambda timeout"
# → Creates branch: wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
# → Creates worktree: ../dr-daily-report_telegram-wt-investigate-lambda-timeout
# → Agent continues work in new worktree

# Terminal 2: Agent designing API (parallel!)
/wt-spin-off "REST API for backtester"
# → Creates branch: wt-2025-12-24-143117-rest-api-for-backtester-b8d1
# → Creates worktree: ../dr-daily-report_telegram-wt-rest-api-for-backtester
# → Agent continues work in isolated worktree

# No conflicts! Each agent has independent workspace
```

---

## Command Interface

### Signature
```bash
/wt-spin-off "task description"
```

### Arguments

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `description` | Yes | String | Brief description of task (used for branch/directory naming) |

### Examples
```bash
/wt-spin-off "fix timeout bug"
/wt-spin-off "add backtester API"
/wt-spin-off "refactor workflow layer"
/wt-spin-off "investigate memory leak"
```

---

## Behavior

### 1. Branch Naming Convention

**Pattern**: `wt-{date}-{time}-{slug}-{random}`

**Components**:
- `wt-` - Prefix indicating worktree branch
- `{date}` - YYYY-MM-DD (e.g., 2025-12-24)
- `{time}` - HHMMSS (e.g., 143052)
- `{slug}` - Lowercase-dash version of description (e.g., investigate-lambda-timeout)
- `{random}` - 4-char random suffix to prevent collisions (e.g., a3f2)

**Generation Algorithm**:
```bash
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H%M%S)
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
RANDOM=$(openssl rand -hex 2)

BRANCH_NAME="wt-${DATE}-${TIME}-${SLUG}-${RANDOM}"
```

**Rationale**:
- **Deterministic**: Same description at same time produces same base name
- **Collision-resistant**: Time precision + random suffix prevents duplicates
- **Readable**: Slug preserves task description
- **Sortable**: Date/time prefix enables chronological sorting
- **Unique**: 4-char random suffix handles simultaneous invocations

**Examples**:
```
/wt-spin-off "fix timeout bug"
→ wt-2025-12-24-143052-fix-timeout-bug-a3f2

/wt-spin-off "Add REST API for backtester"
→ wt-2025-12-24-143117-add-rest-api-for-backtester-b8d1

/wt-spin-off "Investigate memory leak in Lambda cold start"
→ wt-2025-12-24-143200-investigate-memory-leak-in-lambda-cold-start-c9e3
```

---

### 2. Worktree Directory Naming

**Pattern**: `{parent-dir}/{repo-name}-wt-{slug}`

**Components**:
- `{parent-dir}` - Parent directory of current repo (e.g., /home/anak/dev/)
- `{repo-name}` - Name of current repository (e.g., dr-daily-report_telegram)
- `-wt-` - Worktree indicator
- `{slug}` - Same slug from branch name (for easy matching)

**Generation Algorithm**:
```bash
PARENT_DIR=$(dirname "$(git rev-parse --show-toplevel)")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
WORKTREE_DIR="${PARENT_DIR}/${REPO_NAME}-wt-${SLUG}"
```

**Examples**:
```
Current repo: /home/anak/dev/dr-daily-report_telegram

/wt-spin-off "fix timeout bug"
→ /home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug

/wt-spin-off "add backtester API"
→ /home/anak/dev/dr-daily-report_telegram-wt-add-backtester-api
```

**Rationale**:
- **Same parent directory**: Easy to find (ls ../dr-*-wt-*)
- **Readable**: Directory name reflects task
- **Pattern matching**: All worktrees follow same pattern
- **No timestamp in dir**: Cleaner (timestamp in branch name is sufficient)

---

### 3. Git Operations

**Step-by-Step Execution**:

```bash
# 1. Generate branch name
BRANCH_NAME="wt-${DATE}-${TIME}-${SLUG}-${RANDOM}"

# 2. Generate worktree directory path
WORKTREE_DIR="${PARENT_DIR}/${REPO_NAME}-wt-${SLUG}"

# 3. Check for conflicts
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
  echo "❌ Branch ${BRANCH_NAME} already exists (collision)"
  exit 1
fi

if [[ -d "$WORKTREE_DIR" ]]; then
  echo "❌ Directory ${WORKTREE_DIR} already exists"
  exit 1
fi

# 4. Create branch from current HEAD
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse HEAD)

git branch "$BRANCH_NAME" "$CURRENT_COMMIT"

# 5. Create worktree
git worktree add "$WORKTREE_DIR" "$BRANCH_NAME"

# 6. Verify creation
if [[ $? -eq 0 ]]; then
  echo "✅ Created worktree for parallel work"
  echo ""
  echo "Branch:    $BRANCH_NAME"
  echo "Worktree:  $WORKTREE_DIR"
  echo "From:      $CURRENT_BRANCH ($CURRENT_COMMIT)"
  echo ""
  echo "Next steps:"
  echo "  cd $WORKTREE_DIR"
  echo "  # Work on task..."
  echo "  /wt-merge \"${SLUG}\"    # When done, merge to dev"
  echo "  /wt-remove \"${SLUG}\"   # Clean up worktree"
else
  echo "❌ Failed to create worktree"
  git branch -d "$BRANCH_NAME"  # Clean up branch if worktree failed
  exit 1
fi
```

---

### 4. Disk Space Check

**Requirement**: Ensure at least 1GB available before creating worktree

**Implementation**:
```bash
PARENT_DIR=$(dirname "$(git rev-parse --show-toplevel)")
AVAILABLE_MB=$(df -m "$PARENT_DIR" | awk 'NR==2 {print $4}')

if [[ $AVAILABLE_MB -lt 1024 ]]; then
  echo "⚠️ WARNING: Low disk space"
  echo "   Available: ${AVAILABLE_MB} MB"
  echo "   Recommended: 1024 MB (1 GB)"
  echo ""
  read -p "Continue anyway? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
  fi
fi
```

**Rationale**:
- Typical worktree: ~500MB
- Buffer for dependencies/builds: ~500MB
- Total safety margin: 1GB

---

### 5. Output Format

**Success Output**:
```
✅ Created worktree for parallel work

Branch:    wt-2025-12-24-143052-fix-timeout-bug-a3f2
Worktree:  /home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug
From:      dev (6630d4c)

Next steps:
  cd /home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug
  # Work on task...
  /wt-merge "fix-timeout-bug"    # When done, merge to dev
  /wt-remove "fix-timeout-bug"   # Clean up worktree
```

**Error Output - Branch Exists**:
```
❌ Branch wt-2025-12-24-143052-fix-timeout-bug-a3f2 already exists (collision)

Workaround: Add more specific description or wait 1 second and retry
```

**Error Output - Directory Exists**:
```
❌ Directory /home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug already exists

Workaround: Remove directory manually or use different description
  rm -rf /home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug
```

**Error Output - Disk Space**:
```
⚠️ WARNING: Low disk space
   Available: 512 MB
   Recommended: 1024 MB (1 GB)

Continue anyway? [y/N]
```

---

## Edge Cases

### 1. Description with Special Characters
**Input**: `/wt-spin-off "Fix #123: API timeout (Lambda)"`

**Handling**:
```bash
# Sanitize description
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
# Result: fix-123-api-timeout-lambda
```

**Rationale**: Only alphanumeric and hyphens allowed in slugs

---

### 2. Very Long Description
**Input**: `/wt-spin-off "Investigate memory leak in Lambda cold start during high concurrency when processing large CSV files from S3"`

**Handling**:
```bash
# Truncate to 50 characters
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
# Result: investigate-memory-leak-in-lambda-cold-start-dur
```

**Rationale**: Keep directory paths reasonable

---

### 3. Simultaneous Invocations (Race Condition)
**Scenario**: Two agents invoke `/wt-spin-off "fix bug"` at exactly the same second

**Protection**:
1. **Time precision**: HHMMSS granularity (1-second resolution)
2. **Random suffix**: 4-char hex (65536 possibilities)
3. **Collision probability**: ~0.0015% within same second

**If collision occurs**:
```bash
# Git will error when trying to create duplicate branch
❌ Branch wt-2025-12-24-143052-fix-bug-a3f2 already exists
```

**User workaround**: Retry immediately (different second and random suffix)

---

### 4. Working from Non-Dev Branch
**Scenario**: User is on feature branch, not dev

**Behavior**: Create worktree from current branch (wherever you are)

**Example**:
```bash
# Currently on 'feature-telegram-api' branch
git branch  # * feature-telegram-api

/wt-spin-off "test API endpoint"
# → Creates branch from feature-telegram-api, not dev
# → Output shows "From: feature-telegram-api (abc1234)"
```

**Rationale**: Maximum flexibility - user controls base branch

---

### 5. Unstaged/Uncommitted Changes
**Scenario**: User has uncommitted work in current directory

**Behavior**: Allow (worktree starts from committed HEAD, not working directory)

**Git Behavior**:
```bash
# Current directory has uncommitted changes
git status
# modified:   src/foo.py (not staged)

/wt-spin-off "fix bug"
# ✅ Creates worktree from last commit (clean state)
# Current directory STILL has uncommitted changes (untouched)
```

**Rationale**: Git worktrees are independent - no interference

---

## Integration with Parallel Agent Workflows

### Typical Multi-Agent Workflow

**Terminal 1: Bug Investigation**
```bash
cd /home/anak/dev/dr-daily-report_telegram
/wt-spin-off "investigate lambda timeout"
cd ../dr-daily-report_telegram-wt-investigate-lambda-timeout
/bug-hunt "Lambda timeout after 30 seconds"
# ... investigation ...
# Found root cause, fixed
/wt-merge "investigate-lambda-timeout"
/wt-remove "investigate-lambda-timeout"
```

**Terminal 2: API Design (Parallel!)**
```bash
cd /home/anak/dev/dr-daily-report_telegram
/wt-spin-off "REST API for backtester"
cd ../dr-daily-report_telegram-wt-rest-api-for-backtester
/specify api "Backtester REST API with WebSocket progress updates"
# ... design spec created ...
# Implementation started
# Keep worktree open (not done yet)
```

**Terminal 3: Refactoring (Parallel!)**
```bash
cd /home/anak/dev/dr-daily-report_telegram
/wt-spin-off "refactor workflow layer"
cd ../dr-daily-report_telegram-wt-refactor-workflow-layer
/refactor src/workflow/
# ... refactoring in progress ...
```

**Benefits**:
- ✅ No file conflicts between agents
- ✅ Independent `.claude/` state per worktree
- ✅ Each agent works at own pace
- ✅ Merge when ready (no coordination needed)

---

## Independent .claude/ State

### Principle: Each Worktree Has Own State

**Main Worktree**:
```
/home/anak/dev/dr-daily-report_telegram/.claude/
├── observations/
│   └── 2025-12-24-lambda-performance-degraded.md
├── journals/
│   └── 2025-12-24-architecture-semantic-layer.md
└── specifications/
    └── api/2025-12-20-telegram-rankings-api.md
```

**Worktree 1** (independent copy):
```
/home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout/.claude/
├── observations/
│   └── (initially empty - new worktree)
├── bug-hunts/
│   └── 2025-12-24-lambda-timeout.md  (created during investigation)
└── journals/
    └── (initially empty)
```

**Worktree 2** (independent copy):
```
/home/anak/dev/dr-daily-report_telegram-wt-rest-api-for-backtester/.claude/
├── specifications/
│   └── api/2025-12-24-backtester-rest-api.md  (created during design)
└── journals/
    └── (initially empty)
```

**Implications**:
- ✅ Each agent's work is isolated
- ✅ No cross-contamination of observations/journals
- ✅ When merged to dev, `.claude/` files come with the work
- ⚠️ Observations in worktree-1 invisible to worktree-2 (by design)

**Sharing State** (if needed):
```bash
# In worktree-1: Created important observation
git add .claude/observations/2025-12-24-critical-finding.md
git commit -m "docs: Critical finding about Lambda timeouts"

# In worktree-2: Want to see the finding
git fetch origin dev  # or: cd main-worktree && git pull
git merge dev         # Brings in the observation

# Now worktree-2 has access to worktree-1's observation
```

**Recommendation**: Treat worktrees as independent until merge

---

## Implementation Checklist

- [ ] Command file: `.claude/commands/wt-spin-off.md`
- [ ] Branch naming: `wt-{date}-{time}-{slug}-{random}`
- [ ] Directory naming: `{parent}/{repo}-wt-{slug}`
- [ ] Disk space check: Warn if < 1GB available
- [ ] Conflict detection: Check branch/directory don't exist
- [ ] Git operations: Create branch → Create worktree
- [ ] Error handling: Clean up branch if worktree fails
- [ ] Output format: Show branch, path, next steps
- [ ] Edge cases: Special chars, long descriptions, collisions
- [ ] Documentation: Update README.md with worktree section
- [ ] Integration: Works with /wt-list, /wt-merge, /wt-remove

---

## Success Criteria

**Command succeeds when**:
1. ✅ New branch created with deterministic name
2. ✅ Worktree directory created in parent directory
3. ✅ Git worktree successfully added
4. ✅ Output shows clear next steps
5. ✅ No conflicts with existing branches/directories
6. ✅ Sufficient disk space available (or user confirmed)

**Command fails gracefully when**:
1. ❌ Branch name collision (rare, shows workaround)
2. ❌ Directory already exists (shows rm command)
3. ❌ Insufficient disk space (warns, offers continue)
4. ❌ Git operation fails (cleans up partial state)

---

## Related Commands

- `/wt-list` - List all active worktrees
- `/wt-merge "slug"` - Merge worktree branch back to dev
- `/wt-remove "slug"` - Remove worktree directory (after merge or to discard)

---

## See Also

- [What-If: /spin-off-worktree for parallel workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
- [What-If: wt-* prefix naming convention](../what-if/2025-12-24-worktree-command-naming-wt-prefix-vs-worktree-suffix.md)
- Git worktree documentation: `git help worktree`
