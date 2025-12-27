---
name: wt-remove
description: Remove git worktree directory with safety validation and optional branch deletion
accepts_args: true
arg_schema:
  - name: slug
    required: true
    description: "Slug portion of worktree name (e.g., 'investigate-lambda-timeout')"
---

# /wt-remove - Remove Worktree Directory

Remove a git worktree directory after work is complete. Optionally delete the associated branch if it has been merged to dev. Provides safe cleanup with validation to prevent data loss.

## Usage

```bash
/wt-remove "slug"
```

## Examples

```bash
/wt-remove "investigate-lambda-timeout"
/wt-remove "rest-api-for-backtester"
/wt-remove "refactor-workflow-layer"
```

**Note**: Slug must match the slug used in `/wt-spin-off`

---

## Implementation

You are tasked with removing a worktree directory with safety validation.

### Step 1: Parse Arguments and Resolve Worktree

```bash
SLUG="$1"

if [[ -z "$SLUG" ]]; then
  echo "❌ Usage: /wt-remove \"slug\""
  echo ""
  echo "Examples:"
  echo "  /wt-remove \"investigate-lambda-timeout\""
  echo "  /wt-remove \"rest-api-for-backtester\""
  echo ""
  echo "Hint: /wt-list to see all worktrees"
  exit 1
fi

# Find worktree path and branch
WORKTREE_INFO=$(git worktree list --porcelain | awk -v slug="$SLUG" '
  /^worktree / { path = $2 }
  /^branch / {
    branch = $2
    sub("refs/heads/", "", branch)
  }
  /^$/ {
    if (path != "" && branch ~ slug) {
      print path "|" branch
      path = ""; branch = ""
    }
  }
  END {
    if (path != "" && branch ~ slug) {
      print path "|" branch
    }
  }
')

if [[ -z "$WORKTREE_INFO" ]]; then
  echo "❌ No worktree found matching slug: $SLUG"
  echo ""
  echo "Available worktrees:"
  /wt-list
  exit 1
fi

WORKTREE_PATH=$(echo "$WORKTREE_INFO" | cut -d'|' -f1)
WORKTREE_BRANCH=$(echo "$WORKTREE_INFO" | cut -d'|' -f2)
```

### Step 2: Check if Main Worktree (Cannot Remove)

```bash
MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / { print $2; exit }')

if [[ "$WORKTREE_PATH" == "$MAIN_WORKTREE" ]]; then
  echo "❌ Cannot remove main worktree"
  echo "   Path: $MAIN_WORKTREE"
  echo ""
  echo "Only additional worktrees can be removed, not the main repository."
  exit 1
fi
```

### Step 3: Check if Currently Inside Worktree

```bash
CURRENT_DIR=$(pwd)

if [[ "$CURRENT_DIR" == "$WORKTREE_PATH"* ]]; then
  echo "⚠️  You are currently inside the worktree being removed"
  echo "   Current:  $CURRENT_DIR"
  echo "   Removing: $WORKTREE_PATH"
  echo ""
  echo "Switch to main worktree first:"
  echo "  cd $MAIN_WORKTREE"
  echo "  /wt-remove \"$SLUG\""
  exit 1
fi
```

### Step 4: Safety Validations

```bash
MERGED=false
BRANCH_DELETED=false

# Check if branch is merged to dev
if git merge-base --is-ancestor "$WORKTREE_BRANCH" dev 2>/dev/null; then
  MERGED=true
  echo "✅ Branch is merged to dev (safe to remove)"
else
  MERGED=false
  echo "⚠️  Branch NOT merged to dev yet"
  echo ""

  # Show unmerged commits
  UNMERGED_COMMITS=$(git log --oneline dev.."$WORKTREE_BRANCH" 2>/dev/null)
  COMMIT_COUNT=$(echo "$UNMERGED_COMMITS" | wc -l)

  if [[ $COMMIT_COUNT -gt 0 ]]; then
    echo "Unmerged commits ($COMMIT_COUNT):"
    echo "$UNMERGED_COMMITS" | sed 's/^/  /'
    echo ""
  fi

  read -p "Remove anyway? This will LOSE unmerged work! [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted (branch not removed)"
    echo ""
    echo "Next steps:"
    echo "  → Merge first: /wt-merge \"$SLUG\""
    echo "  → Then remove: /wt-remove \"$SLUG\""
    exit 1
  fi
fi

# Check for uncommitted changes (if directory exists)
if [[ -d "$WORKTREE_PATH" ]]; then
  cd "$WORKTREE_PATH"
  if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  Worktree has uncommitted changes"
    echo ""
    git status --short
    echo ""

    read -p "Remove anyway? This will LOSE uncommitted work! [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "❌ Aborted (uncommitted changes preserved)"
      echo ""
      echo "Next steps:"
      echo "  → Commit changes: cd $WORKTREE_PATH && git commit -am 'message'"
      echo "  → Or stash: git stash"
      echo "  → Then remove: /wt-remove \"$SLUG\""
      exit 1
    fi
  fi
  cd - > /dev/null
fi
```

### Step 5: Remove Worktree

```bash
echo ""
echo "Removing worktree:"
echo "  Path:   $WORKTREE_PATH"
echo "  Branch: $WORKTREE_BRANCH"
echo ""

# Handle case where directory doesn't exist (broken reference)
if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo "⚠️  Worktree directory not found: $WORKTREE_PATH"
  echo "   (git worktree reference exists, but directory is gone)"
  echo ""
  echo "Pruning stale worktree reference..."
  git worktree prune
  echo "✅ Stale reference pruned"
else
  # Remove worktree
  git worktree remove "$WORKTREE_PATH" --force

  if [[ $? -eq 0 ]]; then
    echo "✅ Worktree removed successfully"
  else
    echo "❌ Failed to remove worktree"
    echo ""
    echo "Debug:"
    echo "  git worktree list"
    echo "  git worktree remove --force $WORKTREE_PATH"
    echo "  rm -rf $WORKTREE_PATH  # Manual removal (last resort)"
    exit 1
  fi
fi
```

### Step 6: Optionally Delete Branch

```bash
echo ""
if [[ "$MERGED" == true ]]; then
  # Branch is merged - safe to delete
  read -p "Delete branch? [Y/n] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git branch -d "$WORKTREE_BRANCH"
    if [[ $? -eq 0 ]]; then
      echo "✅ Branch deleted: $WORKTREE_BRANCH"
      BRANCH_DELETED=true
    else
      echo "⚠️  Failed to delete branch (use -D to force)"
      echo "   Manual cleanup: git branch -D $WORKTREE_BRANCH"
    fi
  else
    echo "ℹ️  Branch kept: $WORKTREE_BRANCH"
    echo "   Delete manually: git branch -d $WORKTREE_BRANCH"
  fi
else
  # Branch not merged - require force delete
  echo "ℹ️  Branch NOT deleted (not merged to dev)"
  echo "   Force delete: git branch -D $WORKTREE_BRANCH"
fi
```

### Step 7: Post-Removal Summary

```bash
echo ""
echo "Cleanup complete!"
echo ""
echo "Summary:"
echo "  ✅ Worktree removed: $WORKTREE_PATH"

if [[ "$BRANCH_DELETED" == true ]]; then
  echo "  ✅ Branch deleted: $WORKTREE_BRANCH"
else
  echo "  ℹ️  Branch kept: $WORKTREE_BRANCH"
fi

echo ""
echo "Remaining worktrees:"
/wt-list
```

---

## Prompt Template

You have successfully removed a worktree directory.

**Removal Summary**:
- Worktree Path: `{WORKTREE_PATH}`
- Branch: `{WORKTREE_BRANCH}`
- Branch Merged: `{MERGED}` (Yes/No)
- Branch Deleted: `{BRANCH_DELETED}` (Yes/No)

**Safety Checks Performed**:
1. ✅ Verified not main worktree (cannot remove main repository)
2. ✅ Checked if user is inside worktree (must exit first)
3. ✅ Validated branch merge status (prevent data loss)
4. ✅ Warned about uncommitted changes (if any)
5. ✅ Prompted before destructive actions

**What Happened**:
{If merged and branch deleted}: Work was merged to dev and branch was deleted. Clean slate.
{If merged but branch kept}: Work was merged to dev but branch preserved for reference.
{If not merged}: Unmerged work was discarded (user explicitly confirmed).

**Next Steps**:
- Check remaining worktrees: `/wt-list`
- Create new worktree: `/wt-spin-off "description"`

---

## Safety Guarantees

**The command will NOT**:
- ❌ Remove main repository
- ❌ Remove worktree you're currently inside
- ❌ Delete unmerged branches without explicit confirmation
- ❌ Delete uncommitted changes without warning

**The command WILL**:
- ✅ Check if branch is merged to dev
- ✅ Warn about uncommitted changes
- ✅ Prompt before branch deletion
- ✅ Handle broken references (directory already deleted)
- ✅ Provide clear next steps if aborted

---

## Workflow Scenarios

### Scenario 1: Normal Cleanup (Merged Work)
```bash
/wt-merge "my-feature"
# ✅ Merged successfully

/wt-remove "my-feature"
# ✅ Branch is merged to dev (safe to remove)
# Delete branch? [Y/n] y
# ✅ Branch deleted
```

### Scenario 2: Discard Unmerged Work (Failed Experiment)
```bash
/wt-remove "failed-experiment"
# ⚠️  Branch NOT merged to dev yet
# Unmerged commits (5): ...
# Remove anyway? This will LOSE unmerged work! [y/N] y
# ✅ Worktree removed
# ℹ️  Branch NOT deleted (not merged to dev)
# Force delete: git branch -D wt-...-failed-experiment-...
```

### Scenario 3: Prevented Data Loss (Uncommitted Changes)
```bash
/wt-remove "my-feature"
# ✅ Branch is merged to dev
# ⚠️  Worktree has uncommitted changes
#  M src/additional_improvement.py
# Remove anyway? [y/N] n
# ❌ Aborted (uncommitted changes preserved)
# Next steps: Commit first, then remove
```

---

## Edge Cases Handled

**Broken Reference** (directory deleted manually):
- Detects missing directory
- Prunes stale git reference
- Still offers branch deletion

**Main Worktree**:
- Cannot remove main repository
- Clear error message

**Current Directory is Worktree**:
- Prevents removal (can't delete directory you're in)
- Suggests switching to main worktree first

**Uncommitted Changes**:
- Warns user before removal
- Requires explicit confirmation

**Unmerged Commits**:
- Shows count and list of commits
- Requires explicit confirmation
- Doesn't auto-delete branch (requires manual force delete)

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-list` - List all active worktrees
- `/wt-merge "slug"` - Merge worktree branch to dev (before removal)

---

## See Also

- [Specification: /wt-remove](../specifications/workflow/2025-12-24-wt-remove-command-remove-worktree-directory.md)
- [What-If: Parallel agent workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
