---
title: /wt-remove command - remove worktree directory
focus: workflow
date: 2025-12-24
status: approved
---

# Specification: /wt-remove Command

## Purpose

Remove a git worktree directory after work is complete. Optionally delete the associated branch if it has been merged to dev. Provides safe cleanup with validation to prevent data loss.

## Use Case

**Problem**: After merging worktree changes to dev, the worktree directory and branch still exist, consuming disk space.

**Current Limitation**: Manual cleanup is error-prone (forget to check if merged, accidentally delete unmerged work).

**Solution**: Single command that safely removes worktree with validation and optional branch deletion.

**Workflow**:
```bash
# Scenario: Work merged to dev, ready to clean up
/wt-list
# Shows: worktree "investigate-lambda-timeout" (merged to dev)

/wt-remove "investigate-lambda-timeout"

# Output:
✅ Branch is merged to dev (safe to remove)

Removing worktree:
  Path:   /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout
  Branch: wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

Worktree removed successfully.

Delete branch? [Y/n] y
✅ Branch deleted: wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

Cleanup complete!
```

---

## Command Interface

### Signature
```bash
/wt-remove "slug"
```

### Arguments

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `slug` | Yes | String | Slug portion of worktree name (e.g., "investigate-lambda-timeout") |

### Examples
```bash
/wt-remove "investigate-lambda-timeout"
/wt-remove "rest-api-for-backtester"
/wt-remove "refactor-workflow-layer"
```

---

## Behavior

### 1. Slug Resolution (Same as /wt-merge)

**Input**: Slug (e.g., "investigate-lambda-timeout")

**Resolution**: Find matching worktree and branch

**Algorithm**:
```bash
SLUG="$1"

# Find worktree path and branch
WORKTREE_INFO=$(git worktree list --porcelain | awk -v slug="$SLUG" '
  /^worktree / { path = $2 }
  /^branch / { branch = $2; sub("refs/heads/", "", branch) }
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

# Extract path and branch
WORKTREE_PATH=$(echo "$WORKTREE_INFO" | cut -d'|' -f1)
WORKTREE_BRANCH=$(echo "$WORKTREE_INFO" | cut -d'|' -f2)
```

---

### 2. Pre-Removal Validation

**Safety Checks Before Removing**:

#### Check 1: Is Branch Merged to Dev?

```bash
# Check if branch has been merged into dev
if git merge-base --is-ancestor "$WORKTREE_BRANCH" dev; then
  MERGED=true
  echo "✅ Branch is merged to dev (safe to remove)"
else
  MERGED=false
  echo "⚠️  Branch NOT merged to dev yet"
  echo ""

  # Show unmerged commits
  UNMERGED_COMMITS=$(git log --oneline dev.."$WORKTREE_BRANCH" 2>/dev/null)
  COMMIT_COUNT=$(echo "$UNMERGED_COMMITS" | wc -l)

  echo "Unmerged commits ($COMMIT_COUNT):"
  echo "$UNMERGED_COMMITS" | sed 's/^/  /'
  echo ""

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
```

**Rationale**: Prevent accidental loss of unmerged work

---

#### Check 2: Working Directory Clean?

```bash
# Check if worktree has uncommitted changes
cd "$WORKTREE_PATH"
if ! git diff-index --quiet HEAD --; then
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
```

**Rationale**: Warn about data loss from uncommitted changes

---

### 3. Removal Process

**Step 1: Remove Worktree Directory**

```bash
echo "Removing worktree:"
echo "  Path:   $WORKTREE_PATH"
echo "  Branch: $WORKTREE_BRANCH"
echo ""

git worktree remove "$WORKTREE_PATH" --force

if [[ $? -eq 0 ]]; then
  echo "✅ Worktree removed successfully"
else
  echo "❌ Failed to remove worktree"
  echo ""
  echo "Debug:"
  echo "  git worktree list"
  echo "  git worktree remove --force $WORKTREE_PATH"
  exit 1
fi
```

**Why `--force`**: Allows removal even if worktree has uncommitted changes (user already confirmed)

---

**Step 2: Optionally Delete Branch**

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

**Rationale**:
- If merged: Safe to delete, prompt user
- If not merged: Don't delete automatically (requires explicit force)

---

### 4. Post-Removal Summary

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

## Edge Cases

### 1. Worktree Path Doesn't Exist (Broken Reference)

**Scenario**: Directory was deleted manually, but git worktree reference remains

**Detection**:
```bash
if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo "⚠️  Worktree directory not found: $WORKTREE_PATH"
  echo "   (git worktree reference exists, but directory is gone)"
  echo ""
  echo "Pruning stale worktree reference..."

  git worktree prune

  echo "✅ Stale reference pruned"
  echo ""

  # Still ask about branch deletion
  read -p "Delete branch? [Y/n] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git branch -d "$WORKTREE_BRANCH" 2>/dev/null || git branch -D "$WORKTREE_BRANCH"
    echo "✅ Branch deleted: $WORKTREE_BRANCH"
  fi

  exit 0
fi
```

**Rationale**: Clean up orphaned git metadata

---

### 2. Main Worktree (Cannot Remove)

**Scenario**: User tries to remove main repository

**Detection**:
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

**Rationale**: Prevent destruction of main repository

---

### 3. Worktree is Current Directory

**Scenario**: User runs `/wt-remove` from inside the worktree being removed

**Detection**:
```bash
CURRENT_DIR=$(pwd)

if [[ "$CURRENT_DIR" == "$WORKTREE_PATH"* ]]; then
  echo "⚠️  You are currently inside the worktree being removed"
  echo "   Current: $CURRENT_DIR"
  echo "   Removing: $WORKTREE_PATH"
  echo ""

  MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / { print $2; exit }')

  echo "Switch to main worktree first:"
  echo "  cd $MAIN_WORKTREE"
  echo "  /wt-remove \"$SLUG\""
  exit 1
fi
```

**Rationale**: Can't remove directory you're standing in

---

### 4. Branch Locked (Used by Another Worktree)

**Scenario**: Branch is checked out in multiple worktrees (rare edge case)

**Git Behavior**: `git worktree remove` will fail with error

**Handling**:
```bash
if ! git worktree remove "$WORKTREE_PATH" --force 2>/dev/null; then
  echo "❌ Failed to remove worktree"
  echo ""
  echo "Possible causes:"
  echo "  - Branch is locked (checked out elsewhere)"
  echo "  - Permission denied"
  echo "  - Git worktree metadata corrupted"
  echo ""
  echo "Debug:"
  echo "  git worktree list"
  echo "  git worktree prune"
  echo "  rm -rf $WORKTREE_PATH  # Manual removal (last resort)"
  exit 1
fi
```

---

### 5. Uncommitted Changes in Worktree

**Scenario**: User forgot to commit work before removing

**Example**:
```bash
/wt-remove "my-task"

# Output:
⚠️  Worktree has uncommitted changes

 M src/foo.py
 M src/bar.py
?? new_file.py

Remove anyway? This will LOSE uncommitted work! [y/N] n
❌ Aborted (uncommitted changes preserved)

Next steps:
  → Commit changes: cd /home/.../dr-daily-report_telegram-wt-my-task && git commit -am 'message'
  → Or stash: git stash
  → Then remove: /wt-remove "my-task"
```

**User Workflow After Abort**:
```bash
# Go back to worktree
cd /home/anak/dev/dr-daily-report_telegram-wt-my-task

# Commit changes
git add .
git commit -m "Complete feature implementation"

# Merge to dev
/wt-merge "my-task"

# Now remove safely
/wt-remove "my-task"
```

---

## Comparison with Manual Removal

### Manual Process (Error-Prone)

```bash
# 1. Find worktree path (hard to remember)
git worktree list
# → /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout

# 2. Check if merged (might forget this step!)
git branch --merged dev
# → wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

# 3. Remove worktree
git worktree remove /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout

# 4. Delete branch (might forget)
git branch -d wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

# 5. Prune stale references (might forget)
git worktree prune
```

**Pain Points**:
- Long paths (hard to type)
- Easy to forget merge check (lose work!)
- Easy to forget branch deletion (clutter)
- Might delete from inside worktree (fails)

---

### With /wt-remove (Safe)

```bash
/wt-remove "investigate-lambda-timeout"
```

**Benefits**:
- ✅ Checks if merged (prevents data loss)
- ✅ Warns about uncommitted changes
- ✅ Prompts for branch deletion
- ✅ Handles all git operations
- ✅ Shows remaining worktrees after cleanup

---

## Workflow Scenarios

### Scenario 1: Normal Cleanup (Merged Work)

```bash
# Work complete and merged
/wt-merge "my-feature"
✅ Merged worktree branch to dev

# Clean up
/wt-remove "my-feature"
✅ Branch is merged to dev (safe to remove)

Removing worktree:
  Path:   /home/.../dr-daily-report_telegram-wt-my-feature
  Branch: wt-2025-12-24-...-my-feature-...

✅ Worktree removed successfully

Delete branch? [Y/n] y
✅ Branch deleted

Cleanup complete!
```

---

### Scenario 2: Discard Unmerged Work (Experimental Branch)

```bash
# Experiment failed, want to discard
/wt-remove "failed-experiment"

⚠️  Branch NOT merged to dev yet

Unmerged commits (5):
  abc1234 Try approach A
  def5678 Try approach B
  ...

Remove anyway? This will LOSE unmerged work! [y/N] y

Removing worktree:
  Path:   /home/.../dr-daily-report_telegram-wt-failed-experiment
  Branch: wt-2025-12-24-...-failed-experiment-...

✅ Worktree removed successfully

ℹ️  Branch NOT deleted (not merged to dev)
   Force delete: git branch -D wt-2025-12-24-...-failed-experiment-...

# User manually force deletes branch if desired
git branch -D wt-2025-12-24-143052-failed-experiment-a3f2
```

---

### Scenario 3: Forgot to Commit (Prevented Data Loss)

```bash
/wt-remove "my-feature"

✅ Branch is merged to dev (safe to remove)

⚠️  Worktree has uncommitted changes

 M src/additional_improvement.py

Remove anyway? This will LOSE uncommitted work! [y/N] n
❌ Aborted (uncommitted changes preserved)

Next steps:
  → Commit changes: cd /home/.../wt-my-feature && git commit -am 'message'
  → Then remove: /wt-remove "my-feature"

# User commits the forgotten changes
cd /home/.../dr-daily-report_telegram-wt-my-feature
git commit -am "Additional improvements after merge"
/wt-merge "my-feature"  # Merge again
/wt-remove "my-feature"  # Now safe to remove
```

---

## Implementation Checklist

- [ ] Command file: `.claude/commands/wt-remove.md`
- [ ] Slug resolution: Find matching worktree and branch
- [ ] Pre-removal validation:
  - [ ] Check if branch is merged to dev
  - [ ] Check for uncommitted changes
  - [ ] Prevent removal of main worktree
  - [ ] Prevent removal if inside worktree
- [ ] Removal process:
  - [ ] Remove worktree directory (git worktree remove --force)
  - [ ] Optionally delete branch (if merged)
  - [ ] Prune stale references if directory missing
- [ ] Post-removal summary:
  - [ ] Show what was removed
  - [ ] Show remaining worktrees
- [ ] Edge cases:
  - [ ] Broken reference (directory missing)
  - [ ] Main worktree (cannot remove)
  - [ ] Current directory is worktree
  - [ ] Uncommitted changes
  - [ ] Unmerged commits
  - [ ] Branch deletion (merged vs unmerged)

---

## Success Criteria

**Command succeeds when**:
1. ✅ Validates branch merge status (prevents data loss)
2. ✅ Warns about uncommitted changes
3. ✅ Removes worktree directory cleanly
4. ✅ Optionally deletes branch (if merged)
5. ✅ Shows clear summary of cleanup actions
6. ✅ Handles edge cases gracefully (broken references, main worktree, etc.)

**User can confidently**:
- Remove worktrees without fear of losing work
- Know exactly what will be deleted
- Decide whether to keep or delete branch
- See remaining worktrees after cleanup

---

## Safety Guarantees

**The command will NOT**:
- ❌ Remove main repository
- ❌ Delete unmerged branches without explicit confirmation
- ❌ Remove worktree with uncommitted changes without warning
- ❌ Remove worktree you're currently inside

**The command WILL**:
- ✅ Check if branch is merged to dev
- ✅ Warn about uncommitted changes
- ✅ Prompt before branch deletion
- ✅ Provide clear next steps if aborted
- ✅ Show summary of cleanup actions

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-list` - List all active worktrees
- `/wt-merge "slug"` - Merge worktree branch to dev (before removal)

---

## See Also

- [What-If: /spin-off-worktree for parallel workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
- [What-If: wt-* prefix naming convention](../what-if/2025-12-24-worktree-command-naming-wt-prefix-vs-worktree-suffix.md)
- [Specification: /wt-spin-off command](2025-12-24-wt-spin-off-command-create-branch-and-worktree.md)
- [Specification: /wt-list command](2025-12-24-wt-list-command-list-active-worktrees.md)
- [Specification: /wt-merge command](2025-12-24-wt-merge-command-merge-worktree-branch-to-dev.md)
- Git worktree documentation: `git help worktree`
