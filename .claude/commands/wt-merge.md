---
name: wt-merge
description: Merge worktree branch back to dev branch with safety validation
accepts_args: true
arg_schema:
  - name: slug
    required: true
    description: "Slug portion of worktree name (e.g., 'investigate-lambda-timeout')"
---

# /wt-merge - Merge Worktree Branch to Dev

Merge a worktree branch back to the dev branch. Integrates work completed in parallel worktree with proper validation and safety checks.

## Usage

```bash
/wt-merge "slug"
```

## Examples

```bash
/wt-merge "investigate-lambda-timeout"
/wt-merge "rest-api-for-backtester"
/wt-merge "refactor-workflow-layer"
```

**Note**: Slug must match the slug used in `/wt-spin-off`

---

## Implementation

You are tasked with merging a worktree branch back to dev with safety validation.

### Step 1: Parse Arguments and Resolve Slug

```bash
SLUG="$1"

if [[ -z "$SLUG" ]]; then
  echo "❌ Usage: /wt-merge \"slug\""
  echo ""
  echo "Examples:"
  echo "  /wt-merge \"investigate-lambda-timeout\""
  echo "  /wt-merge \"rest-api-for-backtester\""
  echo ""
  echo "Hint: /wt-list to see all worktrees"
  exit 1
fi

# Find matching worktree branch
MATCHING_BRANCHES=$(git branch --list "wt-*-${SLUG}-*" | tr -d ' ')

if [[ -z "$MATCHING_BRANCHES" ]]; then
  echo "❌ No worktree branch found matching slug: $SLUG"
  echo ""
  echo "Available worktree branches:"
  git branch --list "wt-*" | sed 's/^/  /'
  echo ""
  echo "Hint: /wt-list to see all worktrees"
  exit 1
fi

# Count matches
MATCH_COUNT=$(echo "$MATCHING_BRANCHES" | wc -l)

if [[ $MATCH_COUNT -gt 1 ]]; then
  echo "⚠️  Multiple branches match slug: $SLUG"
  echo ""
  echo "$MATCHING_BRANCHES" | sed 's/^/  /'
  echo ""
  echo "Use full branch name instead:"
  echo "  git merge <full-branch-name>"
  exit 1
fi

WORKTREE_BRANCH="$MATCHING_BRANCHES"
```

### Step 2: Pre-Merge Validation

```bash
# Check 1: Must be on dev branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$CURRENT_BRANCH" != "dev" ]]; then
  echo "❌ Must be on dev branch to merge worktree"
  echo "   Current branch: $CURRENT_BRANCH"
  echo ""
  echo "Switch to dev:"
  echo "  git checkout dev"
  exit 1
fi

# Check 2: Dev branch must be clean
if ! git diff-index --quiet HEAD --; then
  echo "❌ Dev branch has uncommitted changes"
  echo ""
  git status --short
  echo ""
  echo "Commit or stash changes before merging:"
  echo "  git stash"
  echo "  git commit -am 'WIP'"
  exit 1
fi

# Check 3: Dev should be up-to-date with remote
git fetch origin dev --quiet 2>/dev/null

LOCAL_COMMIT=$(git rev-parse dev 2>/dev/null)
REMOTE_COMMIT=$(git rev-parse origin/dev 2>/dev/null || echo "")

if [[ -n "$REMOTE_COMMIT" ]] && [[ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]]; then
  echo "⚠️  Local dev is behind origin/dev"
  echo "   Local:  $LOCAL_COMMIT"
  echo "   Remote: $REMOTE_COMMIT"
  echo ""
  read -p "Pull latest changes first? [Y/n] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git pull origin dev
    if [[ $? -ne 0 ]]; then
      echo "❌ Failed to pull from origin/dev"
      exit 1
    fi
  fi
fi

# Check 4: Worktree branch must exist
if ! git show-ref --verify --quiet "refs/heads/$WORKTREE_BRANCH"; then
  echo "❌ Branch does not exist: $WORKTREE_BRANCH"
  echo ""
  echo "Available worktree branches:"
  git branch --list "wt-*" | sed 's/^/  /'
  exit 1
fi

# Check 5: Already merged?
if git merge-base --is-ancestor "$WORKTREE_BRANCH" dev; then
  BRANCH_HEAD=$(git rev-parse "$WORKTREE_BRANCH")
  DEV_HEAD=$(git rev-parse dev)

  if [[ "$BRANCH_HEAD" == "$DEV_HEAD" ]]; then
    echo "ℹ️  Branch already merged and up-to-date with dev"
  else
    echo "ℹ️  Branch already merged into dev"
    echo "   (branch is ancestor of dev)"
  fi

  echo ""
  echo "Next steps:"
  echo "  → Remove worktree: /wt-remove \"$SLUG\""
  echo "  → Delete branch: git branch -d $WORKTREE_BRANCH"
  exit 0
fi
```

### Step 3: Perform Fast-Forward Merge

```bash
# Store pre-merge state for stats
PRE_MERGE_COMMIT=$(git rev-parse dev)

# Attempt fast-forward merge
git merge "$WORKTREE_BRANCH" --ff-only --no-edit

if [[ $? -ne 0 ]]; then
  echo "⚠️  Fast-forward merge not possible"
  echo "   (dev and $WORKTREE_BRANCH have diverged)"
  echo ""

  # Find worktree path for helpful message
  WORKTREE_PATH=$(git worktree list --porcelain | awk -v branch="$WORKTREE_BRANCH" '
    /^worktree / { path = $2 }
    /^branch / {
      if ($2 == "refs/heads/" branch) {
        print path
        exit
      }
    }
  ')

  echo "Options:"
  echo "  1. Rebase worktree onto dev (recommended):"
  if [[ -n "$WORKTREE_PATH" ]]; then
    echo "     cd $WORKTREE_PATH"
  fi
  echo "     git rebase dev"
  echo "     /wt-merge \"$SLUG\""
  echo ""
  echo "  2. Create merge commit (not recommended):"
  echo "     git merge $WORKTREE_BRANCH --no-ff"
  exit 1
fi
```

### Step 4: Generate Post-Merge Summary

```bash
echo "✅ Merged worktree branch to dev"
echo ""

# Get merge stats
COMMITS_MERGED=$(git rev-list --count "$PRE_MERGE_COMMIT"..dev)
MERGE_BASE="$PRE_MERGE_COMMIT"
STATS=$(git diff --stat "$MERGE_BASE"..dev)

echo "Branch:       $WORKTREE_BRANCH"
echo "Target:       dev"
echo "Merge Type:   Fast-forward"
echo "Commits:      $COMMITS_MERGED new commits merged"
echo ""
echo "Changes:"
echo "$STATS" | sed 's/^/  /'
echo ""

# Find worktree path
WORKTREE_PATH=$(git worktree list --porcelain | awk -v branch="$WORKTREE_BRANCH" '
  /^worktree / { path = $2 }
  /^branch / {
    if ($2 == "refs/heads/" branch) {
      print path
      exit
    }
  }
')

if [[ -n "$WORKTREE_PATH" ]] && [[ -d "$WORKTREE_PATH" ]]; then
  echo "Worktree still exists at:"
  echo "  $WORKTREE_PATH"
  echo ""
  echo "Next steps:"
  echo "  → Continue working in worktree (if needed)"
  echo "  → Remove worktree when done: /wt-remove \"$SLUG\""
else
  echo "Note: Worktree directory not found"
  echo "      Branch merged successfully (worktree may have been removed)"
fi
```

---

## Prompt Template

You have successfully merged a worktree branch to dev.

**Merge Summary**:
- Branch: `{WORKTREE_BRANCH}`
- Target: dev
- Merge Type: Fast-forward (linear history preserved)
- Commits Merged: `{COMMITS_MERGED}`
- Files Changed: `{FILES_CHANGED}`

**Important Notes**:
1. **Linear History**: Fast-forward merge preserves clean, linear git history (no merge commits)
2. **Worktree Preserved**: The worktree directory still exists at `{WORKTREE_PATH}`
3. **Continue Working**: You can continue working in the worktree and merge again later
4. **Or Remove**: When done, run `/wt-remove "{SLUG}"` to clean up

**Why Fast-Forward Only?**
- Cleaner git history (easier to understand, easier git bisect)
- Worktree branches are short-lived (should stay in sync with dev)
- If fast-forward fails, it means dev has diverged from worktree
- Solution: Rebase worktree onto dev first, then merge

**Next Steps**:
- Continue iterative development: Keep worktree, make more changes, merge again
- Or finish work: `/wt-remove "{SLUG}"` to clean up worktree

---

## Merge Strategy: Fast-Forward Only

**Why `--ff-only`?**

Traditional merge creates merge commits:
```
    A---B---C  dev
     \       \
      D---E---M  (merge commit M)
```

Fast-forward merge maintains linear history:
```
    A---B---C---D---E  dev (no merge commit)
```

**Benefits**:
- ✅ Cleaner history (easier to read git log)
- ✅ Easier git bisect (no merge commits to skip)
- ✅ Clearer causality (commits flow in order)
- ✅ Enforces best practice (rebase before merge)

**When Fast-Forward Fails**:
Dev and worktree have diverged. Solution: Rebase worktree onto dev first.

---

## Edge Cases Handled

**Already Merged**: Detects if branch is already merged, suggests cleanup

**Diverged Branches**: Suggests rebase if fast-forward not possible

**Multiple Slug Matches**: Errors and lists all matching branches

**Uncommitted Changes**: Fails early with clear error message

**Behind Remote**: Offers to pull from origin/dev before merging

**Not on Dev**: Requires user to be on dev branch before merge

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-list` - List all active worktrees
- `/wt-remove "slug"` - Remove worktree directory after merge

---

## See Also

- [Specification: /wt-merge](../specifications/workflow/2025-12-24-wt-merge-command-merge-worktree-branch-to-dev.md)
- [What-If: Parallel agent workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
