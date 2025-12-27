---
title: /wt-merge command - merge worktree branch to dev
focus: workflow
date: 2025-12-24
status: approved
---

# Specification: /wt-merge Command

## Purpose

Merge a worktree branch back to the dev branch. Integrates work completed in parallel worktree without removing the worktree directory (user decides when to remove separately).

## Use Case

**Problem**: After completing work in a worktree, need to integrate changes back to dev branch.

**Current Limitation**: Manual merge process is error-prone (easy to forget steps, merge to wrong branch).

**Solution**: Single command that safely merges worktree branch to dev with proper validation.

**Workflow**:
```bash
# Scenario: Finished bug investigation in worktree
cd /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout

# Work completed, committed
git status  # Clean working directory
git log -1  # "fix: Lambda timeout due to cold start overhead"

# Merge back to dev
/wt-merge "investigate-lambda-timeout"

# Output:
✅ Merged worktree branch to dev

Branch:       wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
Target:       dev
Merge Type:   Fast-forward
Commits:      3 new commits merged
Changes:      5 files changed, 120 insertions(+), 30 deletions(-)

Worktree still exists at:
  /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout

Next steps:
  → Continue working in worktree (if needed)
  → Remove worktree when done: /wt-remove "investigate-lambda-timeout"
```

---

## Command Interface

### Signature
```bash
/wt-merge "slug"
```

### Arguments

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `slug` | Yes | String | Slug portion of worktree name (e.g., "investigate-lambda-timeout") |

### Examples
```bash
/wt-merge "investigate-lambda-timeout"
/wt-merge "rest-api-for-backtester"
/wt-merge "refactor-workflow-layer"
```

**Note**: Slug must match the slug used in `/wt-spin-off` (lowercase-dash format)

---

## Behavior

### 1. Slug Resolution

**Input**: Slug (e.g., "investigate-lambda-timeout")

**Resolution**: Find matching worktree branch

**Algorithm**:
```bash
SLUG="$1"

# Find all wt-* branches matching this slug
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

# Single match - proceed
WORKTREE_BRANCH="$MATCHING_BRANCHES"
```

**Rationale**:
- Slug is user-friendly (short, readable)
- Branch name is deterministic but long
- Resolution links slug → branch name automatically

---

### 2. Pre-Merge Validation

**Safety Checks Before Merging**:

#### Check 1: Current Branch is Dev
```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$CURRENT_BRANCH" != "dev" ]]; then
  echo "❌ Must be on dev branch to merge worktree"
  echo "   Current branch: $CURRENT_BRANCH"
  echo ""
  echo "Switch to dev:"
  echo "  git checkout dev"
  exit 1
fi
```

**Rationale**: Only merge worktree branches into dev (not main, not other worktrees)

---

#### Check 2: Dev Branch is Clean
```bash
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
```

**Rationale**: Uncommitted changes can cause merge conflicts or accidental loss

---

#### Check 3: Dev is Up-to-Date with Remote
```bash
git fetch origin dev --quiet

LOCAL_COMMIT=$(git rev-parse dev)
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
```

**Rationale**: Merging into outdated dev creates divergent history

---

#### Check 4: Worktree Branch Exists
```bash
if ! git show-ref --verify --quiet "refs/heads/$WORKTREE_BRANCH"; then
  echo "❌ Branch does not exist: $WORKTREE_BRANCH"
  echo ""
  echo "Available worktree branches:"
  git branch --list "wt-*" | sed 's/^/  /'
  exit 1
fi
```

---

### 3. Merge Strategy

**Preferred**: Fast-Forward Merge

**Git Command**:
```bash
git merge "$WORKTREE_BRANCH" --ff-only --no-edit
```

**Why `--ff-only`**:
- Ensures linear history (no merge commits)
- If fast-forward impossible, fails gracefully
- User can then decide: rebase or merge commit

**If Fast-Forward Fails**:
```bash
if [[ $? -ne 0 ]]; then
  echo "⚠️  Fast-forward merge not possible"
  echo "   (dev and $WORKTREE_BRANCH have diverged)"
  echo ""
  echo "Options:"
  echo "  1. Rebase worktree onto dev (recommended):"
  echo "     cd <worktree-path>"
  echo "     git rebase dev"
  echo "     /wt-merge \"$SLUG\""
  echo ""
  echo "  2. Create merge commit (not recommended):"
  echo "     git merge $WORKTREE_BRANCH --no-ff"
  exit 1
fi
```

**Rationale**:
- Linear history is cleaner (easier git bisect, easier to understand)
- Worktree branches are short-lived (should rebase onto dev before merge)
- Merge commits clutter history for parallel work

---

### 4. Post-Merge Summary

**Information to Show**:

```bash
# Get merge stats
COMMITS_MERGED=$(git rev-list --count dev@{1}..dev)
MERGE_BASE=$(git merge-base dev@{1} "$WORKTREE_BRANCH")
STATS=$(git diff --stat "$MERGE_BASE"..dev)

echo "✅ Merged worktree branch to dev"
echo ""
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
  echo "Note: Worktree directory already removed"
  echo "      Only merged the branch (branch still exists)"
fi
```

---

## Edge Cases

### 1. Merge Conflicts

**Scenario**: Worktree branch conflicts with dev

**Git Behavior**: Fast-forward merge fails

**Handling**: See "If Fast-Forward Fails" above

**User Workflow**:
```bash
# Attempt merge
/wt-merge "my-feature"

# Output:
⚠️  Fast-forward merge not possible
   (dev and wt-2025-12-24-...-my-feature-... have diverged)

Options:
  1. Rebase worktree onto dev (recommended):
     cd /home/anak/dev/dr-daily-report_telegram-wt-my-feature
     git rebase dev
     /wt-merge "my-feature"

# User goes to worktree and rebases
cd /home/anak/dev/dr-daily-report_telegram-wt-my-feature
git rebase dev
# ... resolve conflicts if any ...

# Retry merge (should fast-forward now)
/wt-merge "my-feature"
✅ Merged worktree branch to dev
```

---

### 2. Slug Matches Multiple Branches

**Scenario**: User created multiple worktrees with similar slugs

**Example**:
```bash
/wt-spin-off "fix bug"        # → wt-2025-12-24-100000-fix-bug-a1b2
# ... later ...
/wt-spin-off "fix bug v2"     # → wt-2025-12-24-150000-fix-bug-v2-c3d4
```

**Slug "fix-bug" matches**:
- `wt-2025-12-24-100000-fix-bug-a1b2`
- `wt-2025-12-24-150000-fix-bug-v2-c3d4` (partial match)

**Handling**:
```bash
⚠️  Multiple branches match slug: fix-bug

  wt-2025-12-24-100000-fix-bug-a1b2
  wt-2025-12-24-150000-fix-bug-v2-c3d4

Use full branch name instead:
  git merge wt-2025-12-24-100000-fix-bug-a1b2
```

**Prevention**: Use more specific slugs

---

### 3. Worktree Directory Deleted (But Branch Exists)

**Scenario**: User manually deleted worktree directory, but branch still exists

**Detection**:
```bash
WORKTREE_PATH=$(git worktree list --porcelain | awk -v branch="$WORKTREE_BRANCH" '
  /^worktree / { path = $2 }
  /^branch / {
    if ($2 == "refs/heads/" branch) {
      print path
      exit
    }
  }
')

if [[ -z "$WORKTREE_PATH" ]]; then
  echo "⚠️  Branch exists but has no associated worktree"
  echo "   (unusual - branch may have been created manually)"
fi
```

**Behavior**: Proceed with merge anyway (branch is what matters)

**Output**:
```
✅ Merged worktree branch to dev

Branch:       wt-2025-12-24-143052-my-task-a3f2
Target:       dev
Merge Type:   Fast-forward
Commits:      2 new commits merged

Note: Worktree directory not found (may have been removed manually)
      Branch merged successfully
```

---

### 4. Branch Already Merged

**Scenario**: User runs `/wt-merge` twice on same branch

**Detection**:
```bash
# Check if branch is ancestor of dev (already merged)
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

**Rationale**: Prevent confusion, guide user to cleanup

---

### 5. Not in Main Repository

**Scenario**: User runs `/wt-merge` from inside a worktree (not main repo)

**Detection**:
```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
MAIN_WORKTREE=$(git worktree list --porcelain | awk '/^worktree / { print $2; exit }')

if [[ "$REPO_ROOT" != "$MAIN_WORKTREE" ]]; then
  echo "⚠️  You are in a worktree, not the main repository"
  echo "   Current:  $REPO_ROOT"
  echo "   Main:     $MAIN_WORKTREE"
  echo ""
  echo "Switch to main repository:"
  echo "  cd $MAIN_WORKTREE"
  echo "  /wt-merge \"$SLUG\""
  exit 1
fi
```

**Rationale**: Merges should happen from main repo (clearer workflow)

---

## Comparison with Manual Merge

### Manual Process (Error-Prone)

```bash
# 1. Find branch name (hard to remember)
git branch --list "wt-*"
# → wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

# 2. Switch to dev
git checkout dev

# 3. Pull latest
git pull origin dev

# 4. Merge (might forget --ff-only)
git merge wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

# 5. If conflicts, resolve (might merge to wrong branch)
# ... manual conflict resolution ...

# 6. Push (might forget)
git push origin dev
```

**Pain Points**:
- Long branch names (hard to type)
- Easy to forget steps (pull, ff-only, push)
- Might merge to wrong branch (not dev)
- Might have uncommitted changes (messy merge)

---

### With /wt-merge (Safe)

```bash
/wt-merge "investigate-lambda-timeout"
```

**Benefits**:
- ✅ Validates you're on dev
- ✅ Checks for uncommitted changes
- ✅ Ensures fast-forward merge
- ✅ Shows clear merge summary
- ✅ Guides next steps (remove worktree)

---

## Post-Merge Workflow Options

### Option 1: Continue Working (Don't Remove Yet)

```bash
/wt-merge "my-task"
✅ Merged worktree branch to dev

# Worktree still exists - continue working
cd /home/anak/dev/dr-daily-report_telegram-wt-my-task
# ... more work ...
git commit -am "Additional improvements"

# Merge again when done
/wt-merge "my-task"
```

**Use Case**: Iterative development (merge early, continue working)

---

### Option 2: Merge and Remove Immediately

```bash
/wt-merge "my-task"
✅ Merged worktree branch to dev

/wt-remove "my-task"
✅ Removed worktree

# All done!
```

**Use Case**: Task complete (no more work needed)

---

### Option 3: Merge and Keep Worktree for Reference

```bash
/wt-merge "my-task"
✅ Merged worktree branch to dev

# Keep worktree as reference (don't remove)
# Useful if you want to compare or reference later

# Clean up later when ready
/wt-remove "my-task"
```

**Use Case**: Want to preserve state for comparison

---

## Implementation Checklist

- [ ] Command file: `.claude/commands/wt-merge.md`
- [ ] Slug resolution: Find matching wt-* branch
- [ ] Pre-merge validation:
  - [ ] Current branch is dev
  - [ ] Dev is clean (no uncommitted changes)
  - [ ] Dev is up-to-date with remote
  - [ ] Worktree branch exists
- [ ] Merge strategy: Fast-forward only (--ff-only)
- [ ] Post-merge summary: Commits, files changed, stats
- [ ] Edge cases:
  - [ ] Fast-forward fails (suggest rebase)
  - [ ] Multiple slug matches
  - [ ] Branch already merged
  - [ ] Worktree directory missing
  - [ ] Run from worktree (not main repo)
- [ ] Next steps guidance: Continue working or remove

---

## Success Criteria

**Command succeeds when**:
1. ✅ Validates all pre-conditions (on dev, clean, up-to-date)
2. ✅ Resolves slug to correct branch name
3. ✅ Merges worktree branch using fast-forward
4. ✅ Shows clear summary of changes merged
5. ✅ Provides actionable next steps
6. ✅ Handles edge cases gracefully

**User can confidently**:
- Merge worktree changes without fear of mistakes
- Know exactly what was merged (commits, files)
- Decide whether to remove worktree or continue working

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-list` - List all active worktrees
- `/wt-remove "slug"` - Remove worktree directory (after merge or to discard)

---

## See Also

- [What-If: /spin-off-worktree for parallel workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
- [What-If: wt-* prefix naming convention](../what-if/2025-12-24-worktree-command-naming-wt-prefix-vs-worktree-suffix.md)
- [Specification: /wt-spin-off command](2025-12-24-wt-spin-off-command-create-branch-and-worktree.md)
- [Specification: /wt-list command](2025-12-24-wt-list-command-list-active-worktrees.md)
- Git merge documentation: `git help merge`
