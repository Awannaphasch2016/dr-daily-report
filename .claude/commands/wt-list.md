---
name: wt-list
description: List all active git worktrees with activity status and cleanup suggestions
accepts_args: false
---

# /wt-list - List Active Worktrees

List all active git worktrees with their branch names, paths, and activity metadata. Provides visibility into parallel agent workflows and identifies stale worktrees for cleanup.

## Usage

```bash
/wt-list
```

**No arguments required** - shows all worktrees.

---

## Implementation

You are tasked with listing all active git worktrees and providing cleanup suggestions.

### Step 1: Query Git Worktrees

```bash
# Parse git worktree list output
WORKTREE_DATA=$(git worktree list --porcelain | awk '
  /^worktree / { path = $2 }
  /^HEAD / { commit = substr($2, 1, 7) }
  /^branch / {
    branch = $2
    sub("refs/heads/", "", branch)
  }
  /^detached/ {
    branch = "(detached HEAD)"
  }
  /^$/ {
    if (path != "") {
      print path "|" branch "|" commit
      path = ""; branch = ""; commit = ""
    }
  }
  END {
    if (path != "") {
      print path "|" branch "|" commit
    }
  }
')

if [[ -z "$WORKTREE_DATA" ]]; then
  echo "❌ No worktrees found"
  echo ""
  echo "This should never happen (main worktree always exists)."
  echo "Possible causes:"
  echo "  - Not in a git repository"
  echo "  - Git worktree metadata corrupted"
  echo ""
  echo "Debug: git worktree list"
  exit 1
fi
```

### Step 2: Analyze Each Worktree

```bash
WORKTREE_COUNT=$(echo "$WORKTREE_DATA" | wc -l)
STALE_WORKTREES=()
MAIN_WORKTREE=$(echo "$WORKTREE_DATA" | head -1 | cut -d'|' -f1)

echo "✅ Active Worktrees ($WORKTREE_COUNT)"
echo ""

while IFS='|' read -r WORKTREE_PATH BRANCH_NAME COMMIT_SHA; do
  # Skip if empty
  [[ -z "$WORKTREE_PATH" ]] && continue

  # Check if directory exists
  if [[ ! -d "$WORKTREE_PATH" ]]; then
    echo "Worktree: broken-reference"
    echo "  Path:      $WORKTREE_PATH (MISSING)"
    echo "  Branch:    $BRANCH_NAME"
    echo "  Status:    ❌ Missing directory (broken reference)"
    echo ""
    continue
  fi

  # Get last modified time
  LAST_MODIFIED=$(git -C "$WORKTREE_PATH" log -1 --format="%at" 2>/dev/null)

  if [[ -z "$LAST_MODIFIED" ]]; then
    # No commits in this worktree, use directory mtime
    LAST_MODIFIED=$(stat -c %Y "$WORKTREE_PATH" 2>/dev/null || stat -f %m "$WORKTREE_PATH" 2>/dev/null)
  fi

  # Calculate relative time
  NOW=$(date +%s)
  DIFF=$((NOW - LAST_MODIFIED))
  MINUTES=$((DIFF / 60))
  HOURS=$((DIFF / 3600))
  DAYS=$((DIFF / 86400))

  if [[ $MINUTES -lt 1 ]]; then
    RELATIVE="just now"
  elif [[ $MINUTES -lt 60 ]]; then
    RELATIVE="$MINUTES minutes ago"
  elif [[ $HOURS -lt 24 ]]; then
    RELATIVE="$HOURS hours ago"
  else
    RELATIVE="$DAYS days ago"
  fi

  LAST_MODIFIED_DATE=$(date -d "@$LAST_MODIFIED" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -r "$LAST_MODIFIED" "+%Y-%m-%d %H:%M:%S" 2>/dev/null)

  # Determine activity status
  if [[ $MINUTES -lt 30 ]]; then
    STATUS="🟢 Active (working on task)"
  elif [[ $HOURS -lt 12 ]]; then
    STATUS="🟡 Idle (no activity in last $MINUTES min)"
  else
    STATUS="🔴 Stale (no activity in > 12 hours)"
  fi

  # Extract slug from branch name
  if [[ "$BRANCH_NAME" == wt-* ]]; then
    # Remove prefix (wt-YYYY-MM-DD-HHMMSS-)
    BRANCH_TAIL=$(echo "$BRANCH_NAME" | sed 's/^wt-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-[0-9]\{6\}-//')
    # Remove suffix (-XXXX random)
    SLUG=$(echo "$BRANCH_TAIL" | sed 's/-[a-f0-9]\{4\}$//')
  else
    SLUG="$BRANCH_NAME"
  fi

  # Get commit message
  COMMIT_MSG=$(git -C "$WORKTREE_PATH" log -1 --format="%s" "$COMMIT_SHA" 2>/dev/null)
  if [[ ${#COMMIT_MSG} -gt 60 ]]; then
    COMMIT_MSG="${COMMIT_MSG:0:57}..."
  fi

  # Format output
  if [[ "$WORKTREE_PATH" == "$MAIN_WORKTREE" ]]; then
    echo "Main Worktree:"
  else
    echo "Worktree: $SLUG"
  fi

  echo "  Path:      $WORKTREE_PATH"
  echo "  Branch:    $BRANCH_NAME"
  echo "  Commit:    $COMMIT_SHA ($COMMIT_MSG)"
  echo "  Modified:  $LAST_MODIFIED_DATE ($RELATIVE)"

  if [[ "$WORKTREE_PATH" != "$MAIN_WORKTREE" ]]; then
    echo "  Status:    $STATUS"

    # Track stale worktrees
    if [[ $HOURS -ge 12 ]]; then
      STALE_WORKTREES+=("$SLUG|$WORKTREE_PATH")
    fi
  fi

  echo ""
done <<< "$WORKTREE_DATA"
```

### Step 3: Generate Cleanup Suggestions

```bash
echo "Cleanup Suggestions:"

if [[ ${#STALE_WORKTREES[@]} -eq 0 ]]; then
  echo "  None (all worktrees recently active)"
else
  for STALE_INFO in "${STALE_WORKTREES[@]}"; do
    STALE_SLUG=$(echo "$STALE_INFO" | cut -d'|' -f1)
    STALE_PATH=$(echo "$STALE_INFO" | cut -d'|' -f2)

    echo "  ⚠️  Stale worktree detected: $STALE_SLUG"
    echo "      → Review work:  cd $STALE_PATH"
    echo "      → Merge:        /wt-merge \"$STALE_SLUG\""
    echo "      → Remove:       /wt-remove \"$STALE_SLUG\""
    echo "      → Discard work: /wt-remove \"$STALE_SLUG\" (without merge)"
    echo ""
  done
fi

# Check for broken references
BROKEN_COUNT=$(git worktree list --porcelain | grep -c "^worktree" || echo 0)
EXISTING_COUNT=$(echo "$WORKTREE_DATA" | wc -l)

if [[ $BROKEN_COUNT -gt $EXISTING_COUNT ]]; then
  echo ""
  echo "  ⚠️  Broken worktree references detected"
  echo "      → Clean up: git worktree prune"
fi
```

---

## Prompt Template

You have successfully listed all active git worktrees.

**Summary**:
- Total worktrees: `{WORKTREE_COUNT}`
- Stale worktrees (> 12 hours): `{STALE_COUNT}`
- Activity status classification:
  - 🟢 Active: Last modified < 30 minutes ago
  - 🟡 Idle: Last modified 30 min - 12 hours ago
  - 🔴 Stale: Last modified > 12 hours ago

**Cleanup Actions**:
{If stale worktrees exist, explain that they may need attention}
{If no stale worktrees, confirm all are actively maintained}

**Next Steps**:
- To create new worktree: `/wt-spin-off "description"`
- To merge worktree: `/wt-merge "slug"`
- To remove worktree: `/wt-remove "slug"`

---

## Activity Status Thresholds

**🟢 Active** (< 30 minutes):
- Typical agent task duration
- Recent git commit or file modification
- Likely still being worked on

**🟡 Idle** (30 min - 12 hours):
- Work may be paused
- Agent may have switched tasks
- Check if work is complete

**🔴 Stale** (> 12 hours):
- Likely abandoned or forgotten
- Work day boundary crossed
- Should review and clean up

---

## Edge Cases Handled

**Detached HEAD**: Shows as `(detached HEAD)` with warning status

**Missing Directory**: Marked as broken reference, suggests `git worktree prune`

**No Commits in Worktree**: Falls back to directory modification time

**Very Long Paths**: Truncates to fit terminal width (if needed)

**Non-wt Branches**: Uses branch name as slug for manually created worktrees

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-merge "slug"` - Merge worktree branch to dev
- `/wt-remove "slug"` - Remove worktree directory

---

## See Also

- [Specification: /wt-list](../specifications/workflow/2025-12-24-wt-list-command-list-active-worktrees.md)
- [What-If: Parallel agent workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
