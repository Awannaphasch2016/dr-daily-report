---
name: wt-spin-off
description: Create new branch and git worktree for parallel agent execution
accepts_args: true
arg_schema:
  - name: description
    required: true
    description: "Brief description of task (used for branch/directory naming)"
---

# /wt-spin-off - Create Branch and Worktree for Parallel Work

Create a new branch and git worktree for parallel agent execution. Enables multiple agents to work on different tasks simultaneously without file conflicts.

## Usage

```bash
/wt-spin-off "task description"
```

## Examples

```bash
/wt-spin-off "fix timeout bug"
/wt-spin-off "add backtester API"
/wt-spin-off "refactor workflow layer"
/wt-spin-off "investigate memory leak"
```

---

## Implementation

You are tasked with creating a new git worktree for parallel work.

### Step 1: Parse Arguments

```bash
DESCRIPTION="$1"

if [[ -z "$DESCRIPTION" ]]; then
  echo "❌ Usage: /wt-spin-off \"task description\""
  echo ""
  echo "Examples:"
  echo "  /wt-spin-off \"fix timeout bug\""
  echo "  /wt-spin-off \"add backtester API\""
  exit 1
fi
```

### Step 2: Generate Branch and Directory Names

```bash
# Generate deterministic branch name
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H%M%S)
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
RANDOM_SUFFIX=$(openssl rand -hex 2)

BRANCH_NAME="wt-${DATE}-${TIME}-${SLUG}-${RANDOM_SUFFIX}"

# Generate worktree directory path
PARENT_DIR=$(dirname "$(git rev-parse --show-toplevel)")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
WORKTREE_DIR="${PARENT_DIR}/${REPO_NAME}-wt-${SLUG}"
```

**Branch Pattern**: `wt-{date}-{time}-{slug}-{random}`
- Example: `wt-2025-12-24-143052-fix-timeout-bug-a3f2`

**Directory Pattern**: `{parent}/{repo}-wt-{slug}`
- Example: `/home/anak/dev/dr-daily-report_telegram-wt-fix-timeout-bug`

### Step 3: Check for Conflicts

```bash
# Check if branch already exists (rare collision)
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
  echo "❌ Branch ${BRANCH_NAME} already exists (collision)"
  echo ""
  echo "Workaround: Add more specific description or wait 1 second and retry"
  exit 1
fi

# Check if directory already exists
if [[ -d "$WORKTREE_DIR" ]]; then
  echo "❌ Directory ${WORKTREE_DIR} already exists"
  echo ""
  echo "Workaround: Remove directory manually or use different description"
  echo "  rm -rf ${WORKTREE_DIR}"
  exit 1
fi
```

### Step 4: Disk Space Check

```bash
# Check available disk space
AVAILABLE_MB=$(df -m "$PARENT_DIR" | awk 'NR==2 {print $4}')

if [[ $AVAILABLE_MB -lt 1024 ]]; then
  echo "⚠️  WARNING: Low disk space"
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

### Step 5: Create Branch and Worktree

```bash
# Get current branch and commit
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse HEAD)

# Create branch from current HEAD
git branch "$BRANCH_NAME" "$CURRENT_COMMIT"

if [[ $? -ne 0 ]]; then
  echo "❌ Failed to create branch"
  exit 1
fi

# Create worktree
git worktree add "$WORKTREE_DIR" "$BRANCH_NAME"

if [[ $? -ne 0 ]]; then
  echo "❌ Failed to create worktree"
  # Clean up branch if worktree creation failed
  git branch -d "$BRANCH_NAME"
  exit 1
fi
```

### Step 6: Output Success Message

```bash
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
```

---

## Prompt Template

**IMPORTANT**: After creating the worktree, DO NOT automatically switch to it. Let the user decide when to switch.

You have successfully created a git worktree for parallel agent execution.

**What was created**:
- Branch: `{BRANCH_NAME}`
- Worktree directory: `{WORKTREE_DIR}`
- Based on: `{CURRENT_BRANCH}` at commit `{CURRENT_COMMIT}`

**Independent State**: Each worktree has its own `.claude/` directory. Observations, journals, and specifications created in this worktree will be isolated from other worktrees until merged.

**Next Steps for User**:
1. `cd {WORKTREE_DIR}` - Switch to new worktree
2. Work on the task (create files, make commits)
3. `/wt-merge "{SLUG}"` - Merge changes back to dev
4. `/wt-remove "{SLUG}"` - Remove worktree when done

**Parallel Execution**: The user can now run other agents in different worktrees without conflicts. Each worktree is completely independent.

---

## Key Principles

**Deterministic Naming**: Same description at same time produces same base name (+ random suffix for collision prevention)

**Collision Resistance**: Timestamp precision (1 second) + 4-char random suffix (65536 possibilities) = ~0.0015% collision probability within same second

**Independent State**: Each worktree has separate `.claude/` directory. Work is isolated until merged.

**Disk Space**: Typical worktree ~500MB. Command warns if < 1GB available.

**Clean Failures**: If worktree creation fails, automatically cleans up the branch to prevent orphaned state.

---

## Related Commands

- `/wt-list` - List all active worktrees and their status
- `/wt-merge "slug"` - Merge worktree branch back to dev
- `/wt-remove "slug"` - Remove worktree directory after merge

---

## See Also

- [Specification: /wt-spin-off](../specifications/workflow/2025-12-24-wt-spin-off-command-create-branch-and-worktree.md)
- [What-If: Parallel agent workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
- [What-If: wt-* naming convention](../what-if/2025-12-24-worktree-command-naming-wt-prefix-vs-worktree-suffix.md)
